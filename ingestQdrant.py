import os
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

load_dotenv()

projectDir = os.path.dirname(os.path.abspath(__file__))

qdrantUrl = os.getenv("QDRANT_URL", "http://localhost:6333")
collectionName = os.getenv("QDRANT_COLLECTION", "finsolve_rag")
embedModelName = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

dataDir = os.path.join(projectDir, "data")
hrCsvPath = os.path.join(projectDir, "data", "hr", "hr_data.csv")

docDepartments = ["engineering", "finance", "marketing", "general"]


def readText(filePath: str) -> str:
    with open(filePath, "r", encoding="utf-8") as f:
        return f.read()


def extractYear(text: str, fileName: str) -> Optional[int]:
    m = re.search(r"(20\d{2})", fileName)
    if m:
        return int(m.group(1))

    m2 = re.search(r"\b(20\d{2})\b", text)
    if m2:
        return int(m2.group(1))

    return None


def extractQuarter(text: str, fileName: str) -> Optional[str]:
    m = re.search(r"\bq([1-4])\b", fileName.lower())
    if m:
        return f"Q{m.group(1)}"

    m2 = re.search(r"\bQ([1-4])\b", text)
    if m2:
        return f"Q{m2.group(1)}"

    return None


def detectDocType(department: str, fileName: str) -> str:
    name = fileName.lower()
    if department == "finance":
        return "finance_report"
    if department == "marketing":
        return "marketing_report"
    if department == "engineering":
        return "engineering_doc"
    if department == "general":
        return "handbook" if "handbook" in name else "general_doc"
    return "doc"


def detectTopics(text: str) -> List[str]:
    t = text.lower()
    topics = []

    if any(k in t for k in ["revenue", "top-line", "sales"]):
        topics.append("revenue")
    if any(k in t for k in ["gross margin", "margin"]):
        topics.append("gross_margin")
    if any(k in t for k in ["operating income", "operating profit", "ebit"]):
        topics.append("operating_income")
    if any(k in t for k in ["net income", "profit after tax", "pat"]):
        topics.append("net_income")
    if any(k in t for k in ["cash flow", "cashflow", "cash from operations"]):
        topics.append("cash_flow")
    if any(k in t for k in ["vendor", "vendor costs", "subscription", "software"]):
        topics.append("vendor_costs")
    if any(k in t for k in ["marketing spend", "ad spend", "campaign spend"]):
        topics.append("marketing_spend")
    if any(k in t for k in ["risk", "mitigation", "exposure", "compliance risk"]):
        topics.append("risk")

    if any(k in t for k in ["roi", "conversion", "cac", "acquisition", "ctr"]):
        topics.append("campaign_performance")
    if any(k in t for k in ["retention", "churn", "lifecycle"]):
        topics.append("retention")

    if any(k in t for k in ["leave", "attendance", "payroll", "performance review"]):
        topics.append("hr_policy")

    if any(k in t for k in ["architecture", "microservice", "microservices", "api gateway"]):
        topics.append("architecture")
    if any(k in t for k in ["ci/cd", "pipeline", "devops"]):
        topics.append("cicd")
    if any(k in t for k in ["security", "encryption", "auth", "rbac", "oauth", "jwt"]):
        topics.append("security")
    if any(k in t for k in ["gdpr", "dpdp", "pci-dss", "compliance"]):
        topics.append("compliance")

    return sorted(list(set(topics)))


def chunkMarkdownByHeadings(markdown: str, maxChars: int = 1200) -> List[Tuple[str, str]]:
    text = markdown.strip()
    if not text:
        return []

    text = re.sub(r"\r\n", "\n", text)
    lines = text.split("\n")

    sections: List[Tuple[str, List[str]]] = []
    currentTitle = "Document"
    currentLines: List[str] = []

    headingPattern = re.compile(r"^(#{1,4})\s+(.*)\s*$")

    for line in lines:
        m = headingPattern.match(line)
        if m:
            if currentLines:
                sections.append((currentTitle, currentLines))
            currentTitle = m.group(2).strip() or "Section"
            currentLines = []
        else:
            currentLines.append(line)

    if currentLines:
        sections.append((currentTitle, currentLines))

    chunks: List[Tuple[str, str]] = []
    for title, secLines in sections:
        secText = "\n".join(secLines).strip()
        secText = re.sub(r"\n{3,}", "\n\n", secText)
        if not secText:
            continue

        if len(secText) <= maxChars:
            chunks.append((title, secText))
        else:
            start = 0
            while start < len(secText):
                end = min(start + maxChars, len(secText))
                part = secText[start:end].strip()
                if part:
                    chunks.append((title, part))
                start += maxChars - 150

    return chunks


def hrCsvToTextChunks(df: pd.DataFrame, maxRowsPerChunk: int = 12) -> List[str]:
    rows = []
    for _, row in df.iterrows():
        employeeId = str(row.get("employee_id", "")).strip()
        fullName = str(row.get("full_name", "")).strip()
        dept = str(row.get("department", "")).strip()
        title = str(row.get("role", "")).strip()
        location = str(row.get("location", "")).strip()
        attendance = str(row.get("attendance_pct", "")).strip()
        perf = str(row.get("performance_rating", "")).strip()
        leaveTaken = str(row.get("leaves_taken", "")).strip()

        rows.append(
            f"employee_id: {employeeId}, full_name: {fullName}, department: {dept}, job_title: {title}, "
            f"location: {location}, attendance_pct: {attendance}, performance_rating: {perf}, leaves_taken: {leaveTaken}"
        )

    chunks = []
    for i in range(0, len(rows), maxRowsPerChunk):
        block = "HR employee records:\n" + "\n".join(rows[i:i + maxRowsPerChunk])
        chunks.append(block)

    return chunks


def ensureCollection(client: QdrantClient, vectorSize: int):
    existing = [c.name for c in client.get_collections().collections]
    if collectionName in existing:
        return

    client.create_collection(
        collection_name=collectionName,
        vectors_config=qmodels.VectorParams(
            size=vectorSize,
            distance=qmodels.Distance.COSINE,
        ),
    )


def clearCollection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if collectionName in existing:
        client.delete_collection(collectionName)


def upsertChunks(
    client: QdrantClient,
    model: SentenceTransformer,
    chunks: List[str],
    payloads: List[Dict[str, Any]],
):
    vectors = model.encode(chunks, normalize_embeddings=True).astype(np.float32)

    points = []
    for i, chunk in enumerate(chunks):
        points.append(
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i].tolist(),
                payload={**payloads[i], "text": chunk},
            )
        )

    client.upsert(collection_name=collectionName, points=points)


def ingest(clearFirst: bool = True):
    client = QdrantClient(url=qdrantUrl)
    model = SentenceTransformer(embedModelName)

    if clearFirst:
        clearCollection(client)

    ensureCollection(client, vectorSize=model.get_sentence_embedding_dimension())

    chunkCounter = 0

    for department in docDepartments:
        deptDir = os.path.join(dataDir, department)
        if not os.path.isdir(deptDir):
            continue

        for fileName in os.listdir(deptDir):
            if not fileName.endswith(".md"):
                continue

            filePath = os.path.join(deptDir, fileName)
            rawText = readText(filePath)

            year = extractYear(rawText, fileName)
            quarter = extractQuarter(rawText, fileName)
            docType = detectDocType(department, fileName)

            sectionChunks = chunkMarkdownByHeadings(rawText, maxChars=1200)
            if not sectionChunks:
                continue

            chunks: List[str] = []
            payloads: List[Dict[str, Any]] = []

            for idx, (sectionTitle, sectionText) in enumerate(sectionChunks):
                chunkText = f"Section: {sectionTitle}\n\n{sectionText}".strip()
                topics = detectTopics(chunkText)

                payloads.append(
                    {
                        "source": f"{department}/{fileName}",
                        "department": department,
                        "docType": docType,
                        "year": year,
                        "quarter": quarter,
                        "topics": topics,
                        "sectionTitle": sectionTitle,
                        "chunkId": chunkCounter + idx,
                    }
                )
                chunks.append(chunkText)

            upsertChunks(client, model, chunks, payloads)

            print(f"Ingested {department}/{fileName} → {len(chunks)} chunks (year={year}, quarter={quarter}, docType={docType})")
            chunkCounter += len(chunks)

    if os.path.exists(hrCsvPath):
        df = pd.read_csv(hrCsvPath)
        hrChunks = hrCsvToTextChunks(df)

        hrPayloads = []
        for i in range(len(hrChunks)):
            hrPayloads.append(
                {
                    "source": "hr/hr_data.csv",
                    "department": "hr",
                    "docType": "hr_dataset",
                    "year": None,
                    "quarter": None,
                    "topics": ["hr_dataset"],
                    "sectionTitle": "HR Records",
                    "chunkId": chunkCounter + i,
                }
            )

        upsertChunks(client, model, hrChunks, hrPayloads)
        print(f"Ingested hr/hr_data.csv → {len(hrChunks)} chunks")
        chunkCounter += len(hrChunks)

    print(f"Done. Total chunks indexed: {chunkCounter}")


if __name__ == "__main__":
    ingest(clearFirst=True)
