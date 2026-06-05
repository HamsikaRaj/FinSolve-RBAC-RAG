import os
import re
import time
from typing import Dict, Any, List, Optional

import anthropic
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

app = FastAPI()

jwtSecret = os.getenv("JWT_SECRET", "change_me_in_env")
jwtAlgo = os.getenv("JWT_ALGO", "HS256")
jwtExpirySeconds = int(os.getenv("JWT_EXP_SECONDS", "3600"))

qdrantUrl = os.getenv("QDRANT_URL", "http://localhost:6333")
collectionName = os.getenv("QDRANT_COLLECTION", "finsolve_rag")

embedModelName = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

anthropicModel = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

projectDir = os.path.dirname(os.path.abspath(__file__))
hrCsvPath = os.path.join(projectDir, "data", "hr", "hr_data.csv")
authUsersPath = os.path.join(projectDir, "data", "hr", "auth_users.csv")

# Use pbkdf2 to avoid bcrypt issues on some setups
pwdContext = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2Scheme = OAuth2PasswordBearer(tokenUrl="login")

embedModel = SentenceTransformer(embedModelName)
qdrantClient = QdrantClient(url=qdrantUrl)


class LoginRequest(BaseModel):
    employeeId: str
    password: str


class ChatRequest(BaseModel):
    message: str


def loadHrDf() -> pd.DataFrame:
    if not os.path.exists(hrCsvPath):
        raise RuntimeError(f"Missing HR CSV at {hrCsvPath}")
    return pd.read_csv(hrCsvPath)


def loadAuthDf() -> pd.DataFrame:
    if not os.path.exists(authUsersPath):
        raise RuntimeError(f"Missing auth_users.csv at {authUsersPath}")
    return pd.read_csv(authUsersPath)


def normalizeDept(dept: str) -> str:
    d = (dept or "").strip().lower()
    if d == "human resources":
        return "hr"
    if d == "quality assurance":
        return "engineering"
    return d


def roleFromDepartment(department: str) -> str:
    d = normalizeDept(department)
    if d == "finance":
        return "finance"
    if d == "marketing":
        return "marketing"
    if d == "hr":
        return "hr"
    if d in ["engineering", "it", "devops"]:
        return "engineering"
    return "employee"


def allowedDepartmentsForRole(role: str) -> List[str]:
    r = (role or "").strip().lower()
    if r == "exec":
        return ["finance", "marketing", "hr", "engineering", "general"]
    if r == "finance":
        return ["finance", "general"]
    if r == "marketing":
        return ["marketing", "general"]
    if r == "hr":
        return ["hr", "general"]
    if r == "engineering":
        return ["engineering", "general"]
    return ["general"]


def createJwt(employeeId: str, role: str, department: str) -> str:
    now = int(time.time())
    payload = {
        "sub": employeeId,
        "role": role,
        "department": department,
        "iat": now,
        "exp": now + jwtExpirySeconds,
    }
    return jwt.encode(payload, jwtSecret, algorithm=jwtAlgo)


def decodeJwt(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, jwtSecret, algorithms=[jwtAlgo])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def getCurrentUser(token: str = Depends(oauth2Scheme)) -> Dict[str, Any]:
    claims = decodeJwt(token)
    employeeId = claims.get("sub")
    role = claims.get("role")
    department = claims.get("department")
    if not employeeId or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {"employeeId": employeeId, "role": role, "department": department}


def extractQueryQuarter(message: str) -> Optional[str]:
    m = re.search(r"\bq([1-4])\b", (message or "").lower())
    if m:
        return f"Q{m.group(1)}"
    return None


def extractQueryTopics(message: str) -> List[str]:
    t = (message or "").lower()
    topics = []

    if "revenue" in t:
        topics.append("revenue")
    if "marketing spend" in t or "ad spend" in t:
        topics.append("marketing_spend")
    if "cash flow" in t or "cashflow" in t:
        topics.append("cash_flow")
    if "gross margin" in t or "margin" in t:
        topics.append("gross_margin")
    if "operating income" in t:
        topics.append("operating_income")
    if "net income" in t or "profit" in t:
        topics.append("net_income")
    if "risk" in t:
        topics.append("risk")
    if "roi" in t or "conversion" in t or "ctr" in t:
        topics.append("campaign_performance")
    if "architecture" in t or "microservice" in t:
        topics.append("architecture")
    if "security" in t or "rbac" in t:
        topics.append("security")
    if "leave" in t or "attendance" in t or "payroll" in t:
        topics.append("hr_policy")

    return topics


def buildRbacFilterStrict(allowedDepts: List[str], message: str) -> qmodels.Filter:
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="department",
                match=qmodels.MatchAny(any=allowedDepts),
            )
        ]
    )


def buildRbacFilterLoose(allowedDepts: List[str]) -> qmodels.Filter:
    normalized_depts = [d.lower().strip() for d in allowedDepts]
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="department",
                match=qmodels.MatchAny(any=normalized_depts),
            )
        ]
    )


def qdrantSearchSafe(queryVector: List[float], queryFilter: qmodels.Filter, topK: int):
    try:
        return qdrantClient.search(
            collection_name=collectionName,
            query_vector=queryVector,
            limit=topK,
            query_filter=queryFilter,
            with_payload=True,
        )
    except AttributeError:
        res = qdrantClient.query_points(
            collection_name=collectionName,
            query=queryVector,
            limit=topK,
            query_filter=queryFilter,
            with_payload=True,
        )
        return res.points


def dedupeHitsBySourceChunk(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for h in hits:
        key = (h.get("source"), h.get("chunkId"))
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def enforceRbacOnHits(hits: List[Dict[str, Any]], allowedDepts: List[str]) -> List[Dict[str, Any]]:
    allowed = set(d.lower().strip() for d in allowedDepts)
    return [h for h in hits if (h.get("department") or "").lower().strip() in allowed]


def retrieveChunks(query: str, allowedDepts: List[str], topK: int = 8) -> List[Dict[str, Any]]:
    queryVector = embedModel.encode([query], normalize_embeddings=True)[0].tolist()

    strictFilter = buildRbacFilterStrict(allowedDepts, query)
    hits = qdrantSearchSafe(queryVector, strictFilter, topK)

    if not hits:
        looseFilter = buildRbacFilterLoose(allowedDepts)
        hits = qdrantSearchSafe(queryVector, looseFilter, topK)

    results: List[Dict[str, Any]] = []
    for h in hits:
        payload = getattr(h, "payload", None) or {}
        score = getattr(h, "score", None)
        results.append(
            {
                "text": payload.get("text", ""),
                "source": payload.get("source", "unknown"),
                "department": payload.get("department", "unknown"),
                "chunkId": payload.get("chunkId"),
                "sectionTitle": payload.get("sectionTitle"),
                "score": float(score) if score is not None else None,
            }
        )

    results = dedupeHitsBySourceChunk(results)
    results = enforceRbacOnHits(results, allowedDepts)
    return results


def buildPrompt(userRole: str, userQuestion: str, contexts: List[Dict[str, Any]]) -> str:
    contextBlocks = []
    for c in contexts:
        src = c.get("source")
        dept = c.get("department")
        chunkId = c.get("chunkId")
        contextBlocks.append(
            f"[source={src} dept={dept} chunk={chunkId}]\n{c.get('text','')}"
        )

    contextText = "\n\n".join(contextBlocks).strip()

    return f"""
You are an internal enterprise assistant for a FinTech company.
The user role is: {userRole}

Rules:
- Answer using ONLY the context provided below.
- If the answer is not in the context, say: "I don't have enough information in the provided documents."
- Do not guess numbers.
- Do not mention or print "Sources used".
- Do not repeat the context headers like [source=...].

User question:
{userQuestion}

Context:
{contextText}
""".strip()


def generateWithClaude(prompt: str) -> str:
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model=anthropicModel,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        return f"LLM generation failed: {str(e)}"


@app.post("/login")
def login(req: LoginRequest):
    hrDf = loadHrDf()
    authDf = loadAuthDf()

    employeeId = (req.employeeId or "").strip()
    password = req.password or ""

    row = hrDf[hrDf["employee_id"] == employeeId]
    if row.empty:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    userRow = authDf[authDf["employee_id"] == employeeId]
    if userRow.empty:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    passwordHash = str(userRow.iloc[0]["password_hash"])
    if not pwdContext.verify(password, passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    fullName = str(row.iloc[0]["full_name"])
    department = str(row.iloc[0]["department"])
    role = roleFromDepartment(department)

    token = createJwt(employeeId, role, department)

    return {
        "employeeId": employeeId,
        "fullName": fullName,
        "role": role,
        "department": department,
        "accessToken": token,
        "tokenType": "bearer",
    }


@app.post("/chat")
def chat(req: ChatRequest, user=Depends(getCurrentUser)):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    role = user["role"]
    allowedDepts = allowedDepartmentsForRole(role)

    hits = retrieveChunks(message, allowedDepts=allowedDepts, topK=8)

    if not hits:
        return {
            "answer": "I don't have enough authorized information to answer this question.",
            "sources": [],
            "debug": {"role": role, "allowedDepartments": allowedDepts},
        }

    prompt = buildPrompt(role, message, hits)
    answer = generateWithClaude(prompt)

    sources = [
        {
            "source": h["source"],
            "department": h["department"],
            "chunkId": h["chunkId"],
            "score": h["score"],
        }
        for h in hits
    ]

    return {
        "answer": answer,
        "sources": sources,
        "debug": {"role": role, "allowedDepartments": allowedDepts},
    }
