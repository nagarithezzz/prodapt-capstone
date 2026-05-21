# Development Plan — AI Resume Intelligence & Candidate Matching

## GitHub Repository

```
https://github.com/nagarithezzz/prodapt-capstone
```

---

## Architecture Overview

```
[HR Vague Prompt]
     ↓
Phase 3.1 — Query Understanding (LLM: GPT-4o-mini)
             ├─ Guardrail validation (reject non-job queries)
             ├─ Structured extraction (skills, seniority, domain, must-haves, nice-to-haves)
             └─ Query expansion (3 alternative phrasings)
     ↓
Phase 3.2 — Hybrid Retrieval
             ├─ Vector Search (Pinecone cosine sim, top-60)
             │   └─ Query embedded via text-embedding-3-small
             └─ BM25 Search (local index, top-60)
     ↓
Phase 3.3 — RRF Fusion (k=60) merge & deduplicate → top-20
     ↓
Phase 3.4 — Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3, top-20 → top-5)
     ↓
Phase 3.5 — LLM Scoring (GPT-4o-mini)
             ├─ overall_score, skill_score, experience_score
             ├─ Justification (2-3 sentence explanation)
             └─ email_subject + email_body (shortlist email draft)
     ↓
[Ranked output + email drafts → Streamlit UI]
```

---

## Phase 1 — Data Ingestion & Processing ✅ (Complete)

| Step | Task | Status |
|---|---|---|
| 1.1 | Load CSV with HTML resumes | ✅ Done |
| 1.2 | Clean HTML → plain text (BeautifulSoup) | ✅ Done |
| 1.3 | Extract structured fields (skills, experience, education, category) | ✅ Done |
| 1.4 | Save as JSON (`data/processed/resumes.json`) | ✅ Done |
| 1.5 | Validate & filter bad entries | ✅ Done |

**Output:** `data/processed/resumes.json` — 2,484 candidates, 29 MB

**Key files:**
- `src/ingestion/resume_parser.py` — HTML→text cleaner, section extractor, experience/role parser
- `src/ingestion/skill_dict.py` — 800+ skill keywords with regex word-boundary matching across 30 domains
- `src/ingestion/ingest.py` — Pipeline: reads CSV → parses each row → writes JSON

**Extraction stats:**
| Metric | Value |
|---|---|
| Candidates parsed | 2,484 (0 errors) |
| With skills detected | 2,030 (81.7%) |
| With role category | 2,369 (95.4%) |
| With sections extracted | 2,483 (100%) |
| With years experience | 314 (12.6%) |
| Unique categories | 24 |
| Avg text length | 6,631 chars |

---

## Phase 2 — Embedding & Vector Store ✅ (Complete)

| Step | Task | Details | Status |
|---|---|---|---|
| 2.1 | Semantic chunking | Split resume text by sections (summary, experience, skills, education, projects) — 15,322 chunks created | ✅ Done |
| 2.2 | Generate embeddings | **OpenAI `text-embedding-3-small`** (1,536-dim, $0.02/1K tokens) — full-resume embeddings | ✅ Done |
| 2.3 | Store in vector DB | **Pinecone** serverless index (`resume-matcher`, cosine metric, AWS us-east-1) | ✅ Done |
| 2.4 | Metadata indexing | Indexed by `category`, `skills`, `years_experience`, `role_category` | ✅ Done |

**Results:**
| Metric | Value |
|---|---|
| Vectors indexed | 2,483 |
| Vector dimension | 1,536 |
| Total tokens consumed | 3,203,124 |
| Embedding cost | ~$64.06 |
| Total time | 3.6 min |

**Key Decisions:**
- **Embedding model:** OpenAI `text-embedding-3-small` — 1,536-dim, good quality-to-cost ratio; automatically handles domain-agnostic semantic understanding
- **Chunking:** Semantic by section (not fixed-size) — preserves context for later skill evaluation
- **Vector DB:** Pinecone serverless — zero ops, built-in metadata filtering, cosine similarity
- **Pipeline:** Chunk → embed (batch 20) → upsert (batch 100)
- **Config:** All API keys in `.env` (gitignored); template in `.env.example`

**Key files:**
- `src/embeddings/chunker.py` — Semantic section-based resume chunker
- `src/embeddings/embedder.py` — OpenAI embedding client with batching, retry, progress bar
- `src/embeddings/vector_store.py` — Pinecone client: index create/delete, upsert, metadata helpers
- `src/embeddings/ingest_vectors.py` — Main ingestion script (chunk → embed → upsert)
- `src/utils/config.py` — Central config loader from `.env`

---

## Phase 3 — Retrieval & Matching Pipeline ✅ (Complete)

### Phase 3.1 — Query Understanding (LLM)

| Step | Task | Details | Status |
|---|---|---|---|
| 3.1.1 | Guardrail validation | GPT-4o-mini checks if input is a valid job query; rejects empty/malformed/non-job text | ✅ Done |
| 3.1.2 | LLM extraction | GPT-4o-mini converts vague prompt → structured JSON: `{skills, seniority, category, must_have, nice_to_have, years_experience}` | ✅ Done |
| 3.1.3 | Query expansion | LLM generates 3 alternative phrasings; all 4 queries (original + 3) embedded and searched, results merged by candidate ID | ✅ Done |

### Phase 3.2 — Hybrid Candidate Retrieval

| Step | Task | Details | Status |
|---|---|---|---|
| 3.2.1 | Query embedding | All 4 expanded queries embedded via `text-embedding-3-small` | ✅ Done |
| 3.2.2 | Vector search | Cosine similarity search on Pinecone, top-60 per query → merged by unique candidate ID | ✅ Done |
| 3.2.3 | BM25 search | Local BM25 Okapi index (2,484 docs, ~2M tokens); same expanded queries searched, top-60 per query | ✅ Done |
| 3.2.4 | RRF Fusion | Reciprocal Rank Fusion (k=60) combines vector + BM25 scores into unified ranking | ✅ Done |

**Note:** Category pre-filtering removed — it was silently excluding good cross-domain matches.

### Phase 3.3 — Cross-Encoder Reranking

| Step | Task | Details | Status |
|---|---|---|---|
| 3.3.1 | Load full resume text | Full text from `resumes.json` (not truncated Pinecone metadata) loaded for reranking context | ✅ Done |
| 3.3.2 | Cross-encoder scoring | `BAAI/bge-reranker-v2-m3` scores each candidate against query; model loaded on first call, cached thereafter (~4s load time) | ✅ Done |
| 3.3.3 | Top-20 → top-K | Sorted by cross-encoder logit scores, top-K returned | ✅ Done |

**Model choice:** Switched from `cross-encoder/ms-marco-MiniLM-L-6-v2` to `BAAI/bge-reranker-v2-m3` for cleaner HuggingFace repo (no 404 redirect spam) and better resume-job matching performance.

### Phase 3.4 — LLM Final Scoring + Email Generation

| Step | Task | Details | Status |
|---|---|---|---|
| 3.4.1 | Build prompt | GPT-4o-mini receives job query + top-K candidate profiles (skills, experience, full resume text) | ✅ Done |
| 3.4.2 | Score dimensions | `overall_score` (0-100), `skill_score`, `experience_score` per candidate | ✅ Done |
| 3.4.3 | Justification | 2-3 sentence natural language explanation for each recommendation | ✅ Done |
| 3.4.4 | Email generation | `email_subject` and `email_body` generated in same LLM call (no extra API cost) for shortlist outreach | ✅ Done |

**Real output:**
```json
{
  "candidate_id": "25061645",
  "overall_score": 90,
  "skill_score": 95,
  "experience_score": 85,
  "justification": "This candidate has a strong skill set that directly aligns with the job requirements, including web design and various design software.",
  "email_subject": "Shortlisted for Web Designer Position at Prodapt",
  "email_body": "Dear Candidate,\n\nWe were impressed by your profile and would like to shortlist you for the Web Designer position..."
}
```

---

## Phase 4 — API & Frontend ✅ (Complete)

| Step | Task | Details | Status |
|---|---|---|---|
| 4.1 | FastAPI endpoints | `POST /search` (query → ranked results), `POST /ingest` (upload resume), `GET /candidates/{id}`, `GET /health` | ✅ Done |
| 4.2 | Pydantic schemas | `ScoredCandidate`, `CandidateDetail`, `SearchRequest`, `SearchResponse`, `Requirements` with validation | ✅ Done |
| 4.3 | Streamlit UI | Text input, results slider, candidate cards with scores/justification, expandable full resume, email button with editable subject/body popup | ✅ Done |
| 4.4 | Docker setup | `Dockerfile` + `docker-compose.yml` for one-command startup | ✅ Done |
| 4.5 | Structured logging | Timestamped logging across all 6 pipeline steps (guardrail, extraction, expansion, search, rerank, score) | ✅ Done |

**Key files:**
- `src/api/server.py` — FastAPI application with 4 endpoints
- `src/api/schemas.py` — Pydantic models for request/response validation
- `frontend/app.py` — Streamlit UI
- `Dockerfile` — Multi-stage Python build
- `docker-compose.yml` — API + frontend container orchestration

---

## Phase 5 — Advanced Features (Future)

| Step | Task | Est. Time |
|---|---|---|
| 5.1 | DeepEval integration — matching quality & diversity metrics | 1 day |
| 5.2 | Custom metrics — skill coverage, experience fit, culture match | 1 day |
| 5.3 | LLM-as-judge for soft skills & potential assessment | 0.5 day |
| 5.4 | Bias detection guardrails (demographic, language) | 0.5 day |
| 5.5 | Token usage optimization for high-volume screening | 0.5 day |
| 5.6 | Performance benchmarking (candidates/sec) | 0.5 day |

---

## Project Structure

```
prodapt-capstone/
├── .env                            # API keys (gitignored)
├── .env.example                    # Template for .env
├── .gitignore
├── Dockerfile                      # Container build
├── docker-compose.yml              # API + frontend orchestration
├── data/
│   ├── raw/Resume.csv              # Original Kaggle dataset (53 MB, 2,484 resumes)
│   └── processed/resumes.json      # Cleaned structured output (29 MB)
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingest.py               # CSV → JSON pipeline
│   │   ├── resume_parser.py        # HTML cleaner + section extractor
│   │   └── skill_dict.py           # 800+ skill keyword patterns
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── chunker.py              # Semantic section chunker
│   │   ├── embedder.py             # OpenAI text-embedding-3-small client
│   │   ├── vector_store.py         # Pinecone index management
│   │   └── ingest_vectors.py       # Main ingestion script
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_search.py        # Pinecone search (4 expanded queries)
│   │   ├── bm25_search.py          # Local BM25 Okapi index
│   │   ├── hybrid_search.py        # RRF fusion (vector + BM25)
│   │   └── reranker.py             # Cross-encoder (BAAI/bge-reranker-v2-m3)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── query_understanding.py  # GPT-4o-mini: guardrail + extraction + expansion
│   │   └── final_scorer.py         # GPT-4o-mini: score + justification + email
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py               # FastAPI (4 endpoints)
│   │   └── schemas.py              # Pydantic models
│   ├── pipeline.py                 # Orchestrator: 6-step pipeline
│   └── utils/
│       ├── __init__.py
│       └── config.py               # Central config loader from .env
│       └── log.py                  # Logging configuration
├── frontend/
│   └── app.py                      # Streamlit UI
├── requirements.txt
├── requirements.md
├── development-plan.md
└── test_pipeline.py
```

---

## Progress Summary

| Phase | Description | Status |
|---|---|---|
| 1 | Data Ingestion & Processing | ✅ **Complete** |
| 2 | Embedding & Vector Store | ✅ **Complete** |
| 3 | Retrieval & Matching Pipeline | ✅ **Complete** |
| 4 | API & Frontend | ✅ **Complete** |
| 5 | Advanced Features (R2) | ⏳ **Pending** |

**Completed:** Phases 1-4
**Remaining:** Phase 5 (future work)

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **Embedding model:** `text-embedding-3-small` (1,536-dim) | Best quality-to-cost ratio; handles multi-domain semantics automatically |
| **Vector DB:** Pinecone serverless | Zero ops, built-in metadata filtering, cosine similarity, serverless auto-scaling |
| **Chunking:** Semantic by section | Preserves context for downstream skill evaluation vs fixed-size chunking |
| **Hybrid search:** Vector + BM25 with RRF (k=60) | Vector captures semantic meaning, BM25 captures keyword precision; RRF fusion outperforms either alone |
| **Query expansion:** 3 LLM-generated alternatives | Addresses vague prompts; more alternatives don't improve recall significantly beyond 3 |
| **No category pre-filter** | Removing it improved cross-domain matching (e.g. "web developer" finding relevant IT candidates) |
| **Cross-encoder:** `BAAI/bge-reranker-v2-m3` | Cleaner HuggingFace repo than ms-marco-MiniLM; better suited for resume-job text pairs |
| **Full resume text for reranking** | Using full text (6K+ chars) vs 2K Pinecone metadata snippet for richer cross-encoder scoring |
| **Email in same LLM call as scoring** | Avoids extra latency and cost of a separate API call |
| **No form wrapper in Streamlit** | Session-state-managed results persist across button reruns (fix for email popup disappearing) |

---

## Suggestions for Future Improvement

### 1. Weighted Chunk Scoring
Not all sections carry equal weight. Assign:
- Skills section → **3x weight**
- Experience → **2x weight**
- Education → **1x weight**

### 2. Experience Level Pre-Filtering
Map years-to-level:
| Years | Level |
|---|---|
| 0-2 | Junior |
| 3-5 | Mid |
| 6+ | Senior |

Use as metadata pre-filter so "senior" query doesn't return freshers.

### 3. Section-Weighted Retrieval
Weight vector search results by which section matched: skill-section matches should rank higher than education-section matches.

### 4. Explainability Template
Structure explanations for clarity:
```
Score: 85/100
Skills match: React ✓, Node.js ✓, CSS ✓ (3/4 required)
Experience fit: 4 years (req: 3-5) ✓
Missing: Docker ✗
Why: Strong frontend background with relevant project experience building web apps.
```

### 5. Feedback Loop
Add `POST /feedback` endpoint. Store accept/reject per result. Use data later to fine-tune cross-encoder or adjust score weights.

### 6. Caching
Cache embeddings for frequent queries. If same/similar prompt searched again, skip LLM call and just retrieve + rerank.

### 7. Multi-Agent Pipeline (Future)
Extend to specialized agents:
| Agent | Responsibility |
|---|---|
| Resume Parsing Agent | Extract structured info from raw text |
| Skill Matching Agent | Semantic skill comparison |
| Experience Evaluation Agent | Career trajectory analysis |
| Technical Evaluation Agent | Technical depth assessment |
| Culture Fit Agent | Communication & soft skill indicators |
