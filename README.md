# FinSolve RBAC RAG

An internal chatbot for FinSolve Technologies that lets employees ask questions about company documents but only see answers from data their role is allowed to access.

Built this as a project to explore how RAG and RBAC can work together. The idea is simple: a finance employee should be able to ask about quarterly revenue, but shouldn't be able to see HR records or the engineering architecture. Access control is enforced at the vector search level, not just in the prompt.

---

## What it does

- Employees log in with their employee ID and password
- A JWT is issued with their role and department baked in
- When they ask a question, the backend only retrieves document chunks from departments they're allowed to see
- Claude Sonnet answers using only those chunks if the answer isn't in the allowed documents, it says so

---

## Stack

- **FastAPI** — backend API (login + chat endpoints)
- **Qdrant** — vector database, stores document chunks with department tags
- **sentence-transformers/all-MiniLM-L6-v2** — embedding model
- **Claude Sonnet** (Anthropic) — LLM for answer generation
- **Streamlit** — frontend chat UI
- **JWT + PBKDF2** — authentication

---

## Access control

Roles are assigned automatically based on the employee's department in `hr_data.csv`.

| Role | Who gets it | Can read |
|------|------------|---------|
| `exec` | C-level | Everything |
| `finance` | Finance dept | Finance + General |
| `marketing` | Marketing dept | Marketing + General |
| `hr` | HR dept | HR + General |
| `engineering` | Engineering, IT, QA, DevOps | Engineering + General |
| `employee` | Everyone else | General only |

"General" is the employee handbook — visible to all roles.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment variables

Create a `.env` file:

```
ANTHROPIC_API_KEY=your_key_here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=finsolve_rag
```

### 3. Start Qdrant

```bash
# via Docker
docker run -p 6333:6333 qdrant/qdrant

# or download the binary from qdrant.tech and run it directly
```

### 4. Generate passwords for employees

```bash
python createAuthUsers.py
```

This reads `data/hr/hr_data.csv` and creates `data/hr/auth_users.csv` with hashed passwords. Password format is `Fin@<last4digits of employee ID>` — so `FINEMP1001` → `Fin@1001`.

### 5. Ingest documents into Qdrant

```bash
python ingestQdrant.py
```

Chunks all the markdown files and HR CSV, embeds them, and stores them in Qdrant with department metadata.

### 6. Run the API

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 7. Run the UI

```bash
streamlit run streamlitApp.py
```

Open `http://localhost:8501`.

---

## Test accounts

| Employee ID | Password | Role |
|-------------|----------|------|
| FINEMP1001 | Fin@1001 | finance |
| FINEMP1004 | Fin@1004 | marketing |
| FINEMP1010 | Fin@1010 | hr |
| FINEMP1006 | Fin@1006 | engineering |
| FINEMP1000 | Fin@1000 | employee (general only) |

---

## Project structure

```
app.py                 — FastAPI backend
streamlitApp.py        — Streamlit UI
ingestQdrant.py        — ingestion script
createAuthUsers.py     — password generator

data/
  finance/             — quarterly financial reports (2024)
  marketing/           — quarterly marketing reports (2024)
  engineering/         — engineering architecture doc
  general/             — employee handbook
  hr/                  — employee records + auth credentials
```

