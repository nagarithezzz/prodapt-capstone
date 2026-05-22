# AI Resume Intelligence & Candidate Matching

An end-to-end resume search and scoring system that takes natural language job requirements and returns ranked candidates with AI-generated justifications and interview invitation emails.

## Architecture

```
[Natural Language Query]
         ↓
Query Understanding (GPT-4o-mini)
  ├─ Guardrail validation
  ├─ Structured extraction (skills, seniority, must-haves)
  └─ Query expansion (3 alternative phrasings)
         ↓
Hybrid Retrieval
  ├─ Vector Search (Pinecone cosine sim, top-30)
  └─ BM25 Keyword Search (local index, top-30)
         ↓
RRF Fusion (k=60) → top-20
         ↓
Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3) → top-K
         ↓
LLM Scoring (GPT-4o-mini)
  ├─ overall_score, skill_score, experience_score
  ├─ Justification
  └─ Interview invitation email (subject + body)
         ↓
[FastAPI → Streamlit UI]
```

## Features

- **Natural Language Search** — "find a senior Python developer with AWS experience"
- **Hybrid Retrieval** — Vector similarity + BM25 keyword search fused via RRF
- **Query Expansion** — LLM generates 3 alternative phrasings to improve recall
- **Cross-Encoder Reranking** — `BAAI/bge-reranker-v2-m3` for precise relevance scoring
- **LLM Scoring** — GPT-4o-mini scores candidates with detailed justification
- **Interview Email Generation** — Auto-drafted invitation emails requesting time setup, signed as Naga Rithesh
- **Resume Email Extraction** — Candidate email addresses extracted from resume text and pre-filled in email popup
- **Streaming Pipeline** — Real-time progress updates via SSE to the frontend
- **Interactive UI** — Streamlit frontend with candidate cards, justification, and email popup

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Pinecone API key + index

### Setup

```bash
git clone https://github.com/nagarithezzz/prodapt-capstone.git
cd prodapt-capstone

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your OpenAI and Pinecone keys
```

### Run

```bash
# Terminal 1: FastAPI backend
.venv/bin/uvicorn src.api.server:app --reload

# Terminal 2: Streamlit frontend
.venv/bin/streamlit run frontend/app.py
```

Open http://localhost:8501 in your browser.

### Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/search` | Search candidates by job requirement |
| `POST` | `/search/stream` | Streaming search with real-time progress |
| `GET` | `/candidates/{id}` | Get full candidate details |
| `POST` | `/ingest` | Ingest resumes from CSV |
| `GET` | `/health` | Health check |

### Search Example

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "senior Python developer with AWS", "top_k": 5}'
```

## Dataset

10,174 resumes parsed from a varied dataset — HTML cleaned, sections extracted, skills identified via 800+ keyword patterns across 30 domains. Stored as structured JSON (325 MB) and indexed in Pinecone (10,174 vectors, 1,536-dim).

### Enhanced Resume Fields

| Field | Description |
|---|---|
| `id` | Unique resume identifier (RES-XXXXX) |
| `email` | Extracted candidate email from resume text |
| `skills` | Extracted skills via hybrid keyword matching |
| `years_experience` | Extracted years of experience |
| `role_category` | Inferred role category from resume |
| `decision` | Hiring decision label (accept/reject) |
| `reason_for_decision` | Reason for the hiring decision |
| `job_description` | Associated job description |

## Project Structure

```
src/
├── ingestion/          # CSV → JSON pipeline, HTML parsing, skill extraction
├── embeddings/         # Chunking, embedding, Pinecone ingestion
├── retrieval/          # Vector search, BM25, hybrid RRF fusion, reranking
├── agents/             # LLM: query understanding, scoring, email generation
├── api/                # FastAPI server + Pydantic schemas
├── pipeline.py         # 6-step orchestration pipeline
├── evaluation/         # Retrieval evaluation (precision, recall, MRR, nDCG)
└── utils/              # Config, logging
frontend/               # Streamlit UI
```

## Retrieval Evaluation

Three retrieval methods compared across 10 test queries:

| Method | P@3 | P@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| Vector Only | 0.800 | 0.820 | 0.858 | 0.891 |
| Hybrid (Vec+BM25) | 0.867 | 0.900 | 0.900 | 0.935 |
| Hybrid + Rerank | **0.867** | **0.920** | **0.900** | **0.940** |

## Key Decisions

- **Hybrid search** — Vector (semantic) + BM25 (keyword) with RRF fusion outperforms either alone
- **Query expansion** — 3 LLM-generated alternatives significantly improve recall for vague prompts
- **No category pre-filter** — Removing it improved cross-domain matching (e.g. web dev → IT candidates)
- **Email in same LLM call** — Avoids extra latency/cost of a separate API call
- **Cross-encoder reranking** — Full resume text used (not truncated metadata) for richer scoring
