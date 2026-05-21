# AI Resume Intelligence & Candidate Matching

An end-to-end resume search and scoring system that takes natural language job requirements and returns ranked candidates with AI-generated justifications and shortlist emails.

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
  ├─ Vector Search (Pinecone cosine sim, top-60)
  └─ BM25 Keyword Search (local index, top-60)
         ↓
RRF Fusion (k=60) → top-20
         ↓
Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3) → top-K
         ↓
LLM Scoring (GPT-4o-mini)
  ├─ overall_score, skill_score, experience_score
  ├─ Justification
  └─ email_subject + email_body
         ↓
[FastAPI → Streamlit UI]
```

## Features

- **Natural Language Search** — "find a senior Python developer with AWS experience"
- **Hybrid Retrieval** — Vector similarity + BM25 keyword search fused via RRF
- **Query Expansion** — LLM generates 3 alternative phrasings to improve recall
- **Cross-Encoder Reranking** — `BAAI/bge-reranker-v2-m3` for precise relevance scoring
- **LLM Scoring** — GPT-4o-mini scores candidates with detailed justification
- **Email Generation** — Auto-drafted shortlist outreach emails per candidate
- **Interactive UI** — Streamlit frontend with clickable candidate details
- **FastAPI Backend** — RESTful endpoints for search, candidate details, and ingestion

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Pinecone API key + index

### Setup

```bash
# Clone the repo
git clone https://github.com/nagarithezzz/prodapt-capstone.git
cd prodapt-capstone

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
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
| `GET` | `/candidates/{id}` | Get full candidate details |
| `POST` | `/ingest` | Ingest a new resume |
| `GET` | `/health` | Health check |

### Search Example

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "senior Python developer with AWS", "top_k": 5}'
```

## Dataset

2,484 resumes parsed from Kaggle's "Resume Dataset" — HTML cleaned, sections extracted, skills identified via 800+ keyword patterns across 30 domains. Stored as structured JSON (29 MB) and indexed in Pinecone (2,483 vectors, 1,536-dim).

## Project Structure

```
src/
├── ingestion/          # CSV → JSON pipeline, HTML parsing, skill extraction
├── embeddings/         # Chunking, embedding, Pinecone ingestion
├── retrieval/          # Vector search, BM25, hybrid RRF fusion, reranking
├── agents/             # LLM: query understanding, scoring, email generation
├── api/                # FastAPI server + Pydantic schemas
├── pipeline.py         # 6-step orchestration pipeline
└── utils/              # Config, logging
frontend/               # Streamlit UI
```

## Key Decisions

- **Hybrid search** — Vector (semantic) + BM25 (keyword) with RRF fusion outperforms either alone
- **Query expansion** — 3 LLM-generated alternatives significantly improve recall for vague prompts
- **No category pre-filter** — Removing it improved cross-domain matching (e.g. web dev → IT candidates)
- **Email in same LLM call** — Avoids extra latency/cost of a separate API call
- **Session state UI** — Persists search results across Streamlit reruns so modals/popups work reliably
