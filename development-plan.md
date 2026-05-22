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
             ├─ Vector Search (Pinecone cosine sim, top-30)
             │   └─ Query embedded via text-embedding-3-small
             └─ BM25 Search (local index, top-30)
     ↓
Phase 3.3 — RRF Fusion (k=60) merge & deduplicate → top-20
     ↓
Phase 3.4 — Cross-Encoder Reranking (BAAI/bge-reranker-v2-m3, top-20 → top-K)
     ↓
Phase 3.5 — LLM Scoring (GPT-4o-mini)
             ├─ overall_score, skill_score, experience_score
             ├─ Justification (structured skill/experience breakdown)
             └─ Interview invitation email (subject + body, signed Naga Rithesh)
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
| 1.6 | Extract email from resume text | ✅ Done |
| 1.7 | Parse new CSV format with Decision/Reason_for_decision/Job_Description columns | ✅ Done |

**Output:** `data/processed/resumes.json` — 10,174 candidates, 325 MB

**Key files:**
- `src/ingestion/resume_parser.py` — HTML→text cleaner, section extractor, experience/role parser, email extractor
- `src/ingestion/skill_dict.py` — 800+ skill keywords with regex word-boundary matching across 30 domains
- `src/ingestion/ingest.py` — Pipeline: reads CSV → parses each row → writes JSON

### Enhanced Resume Fields

| Field | Source | Description |
|---|---|---|
| `id` | Generated | Unique identifier (RES-XXXXX) |
| `email` | Extracted | Candidate email from resume text |
| `skills` | Extracted | Skills via hybrid keyword matching |
| `years_experience` | Extracted | Years of experience from resume text |
| `role_category` | Inferred | Role category from resume (e.g. "E-commerce Specialist") |
| `decision` | CSV column | Hiring decision (accept/reject) |
| `reason_for_decision` | CSV column | Reason for the hiring decision |
| `job_description` | CSV column | Associated job description |

---

## Phase 2 — Embedding & Vector Store ✅ (Complete)

| Step | Task | Details | Status |
|---|---|---|---|
| 2.1 | Semantic chunking | Split resume text by sections — 54,276 chunks created from 10,174 candidates | ✅ Done |
| 2.2 | Generate embeddings | **OpenAI `text-embedding-3-small`** (1,536-dim, $0.02/1K tokens) — full-resume embeddings | ✅ Done |
| 2.3 | Store in vector DB | **Pinecone** serverless index (`resume-matcher`, cosine metric, AWS us-east-1) | ✅ Done |
| 2.4 | Metadata indexing | Indexed by `category`, `skills`, `years_experience`, `role_category`, `decision`, `reason_for_decision`, `job_description` | ✅ Done |

**Results:**
| Metric | Value |
|---|---|
| Vectors indexed | 10,174 |
| Vector dimension | 1,536 |
| Total tokens consumed | 5,866,099 |
| Embedding cost | ~$117.32 |
| Total time | ~7.5 min |

**Key Decisions:**
- **Embedding model:** OpenAI `text-embedding-3-small` — 1,536-dim, good quality-to-cost ratio
- **Chunking:** Semantic by section (not fixed-size) — preserves context for later skill evaluation
- **Vector DB:** Pinecone serverless — zero ops, built-in metadata filtering, cosine similarity
- **Pipeline:** Chunk → embed (batch 20) → upsert (batch 100)
- **Config:** All API keys in `.env` (gitignored); template in `.env.example`
- **Schema update:** Metadata includes `decision`, `reason_for_decision`, `job_description` fields

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
| 3.2.2 | Vector search | Cosine similarity search on Pinecone, top-30 per query → merged by unique candidate ID | ✅ Done |
| 3.2.3 | BM25 search | Local BM25 Okapi index (10,174 docs, ~3.6M tokens); same expanded queries searched, top-30 per query | ✅ Done |
| 3.2.4 | RRF Fusion | Reciprocal Rank Fusion (k=60) combines vector + BM25 scores into unified ranking | ✅ Done |

### Phase 3.3 — Cross-Encoder Reranking

| Step | Task | Details | Status |
|---|---|---|---|
| 3.3.1 | Load full resume text | Full text from `resumes.json` loaded for reranking context | ✅ Done |
| 3.3.2 | Cross-encoder scoring | `BAAI/bge-reranker-v2-m3` scores each candidate against query | ✅ Done |
| 3.3.3 | Top-20 → top-K | Sorted by cross-encoder logit scores, top-K returned | ✅ Done |

### Phase 3.4 — LLM Final Scoring + Email Generation

| Step | Task | Details | Status |
|---|---|---|---|
| 3.4.1 | Build prompt | GPT-4o-mini receives job query + top-K candidate profiles | ✅ Done |
| 3.4.2 | Score dimensions | `overall_score` (0-100), `skill_score`, `experience_score` per candidate | ✅ Done |
| 3.4.3 | Justification | Structured breakdown: skill match, experience fit, missing skills, role alignment, overall why | ✅ Done |
| 3.4.4 | Email generation | Interview invitation email with subject + body, signed "Best regards, Naga Rithesh" | ✅ Done |

### Phase 3.5 — Retrieval Evaluation

| Metric | Vector Only | Hybrid | Hybrid + Rerank |
|---|---|---|---|
| P@3 | 0.800 | 0.867 | 0.867 |
| P@5 | 0.820 | 0.900 | 0.920 |
| MRR | 0.858 | 0.900 | 0.900 |
| nDCG@5 | 0.891 | 0.935 | 0.940 |

---

## Phase 4 — API & Frontend ✅ (Complete)

| Step | Task | Details | Status |
|---|---|---|---|
| 4.1 | FastAPI endpoints | `POST /search`, `POST /search/stream` (SSE), `POST /ingest`, `GET /candidates/{id}`, `GET /health` | ✅ Done |
| 4.2 | Pydantic schemas | `ScoredCandidate`, `CandidateDetail`, `SearchRequest`, `SearchResponse` with all fields | ✅ Done |
| 4.3 | Streamlit UI | Search input, candidate cards with scores, expandable justification, full resume viewer | ✅ Done |
| 4.4 | Email popup | Click "Send Email" → inline popup with pre-filled recipient email, subject, and interview invitation body | ✅ Done |
| 4.5 | Email fallback | Default interview scheduling email if LLM output is empty — requests time setup, signed Naga Rithesh | ✅ Done |
| 4.6 | SSE streaming pipeline | Real-time step-by-step progress updates (guardrail → extraction → expansion → search → rerank → score) | ✅ Done |
| 4.7 | Docker setup | `Dockerfile` + `docker-compose.yml` for one-command startup | ✅ Done |
| 4.8 | Structured logging | Timestamped logging across all 6 pipeline steps with email content logged to console | ✅ Done |

**API Response Fields:**
| Field | Description |
|---|---|
| `id` | Candidate ID |
| `overall_score` | Combined score (0-100) |
| `skill_score` | Skill match score (0-100) |
| `experience_score` | Experience fit score (0-100) |
| `justification` | Structured reasoning |
| `email_subject` | Interview invitation subject |
| `email_body` | Interview invitation body (signed Naga Rithesh) |
| `email` | Extracted candidate email |
| `decision` | Hiring decision label |
| `reason_for_decision` | Reason for decision |
| `job_description` | Associated job description |

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
│   ├── raw/Resume.csv              # Original dataset with Decision/Reason columns
│   └── processed/resumes.json      # Cleaned structured output (325 MB, 10,174 resumes)
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingest.py               # CSV → JSON pipeline
│   │   ├── resume_parser.py        # HTML cleaner + section extractor + email extractor
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
│   │   ├── server.py               # FastAPI (5 endpoints)
│   │   └── schemas.py              # Pydantic models
│   ├── pipeline.py                 # Orchestrator: 6-step pipeline with SSE streaming
│   ├── evaluation/
│   │   └── evaluate.py             # Retrieval evaluation (P@k, R@k, MRR, nDCG)
│   └── utils/
│       ├── __init__.py
│       ├── config.py               # Central config loader from .env
│       └── log.py                  # Logging configuration
├── frontend/
│   └── app.py                      # Streamlit UI with email popup
├── evaluation_output/
│   └── retrieval_comparison.png    # Evaluation chart
├── requirements.txt
├── requirements.md
├── development-plan.md
├── test_pipeline.py
└── README.md
```

---

## Progress Summary

| Phase | Description | Status |
|---|---|---|
| 1 | Data Ingestion & Processing (10,174 resumes) | ✅ **Complete** |
| 2 | Embedding & Vector Store (Pinecone, 10,174 vectors) | ✅ **Complete** |
| 3 | Retrieval & Matching Pipeline | ✅ **Complete** |
| 4 | API & Frontend (with email popup) | ✅ **Complete** |
| 5 | Advanced Features (R2) | ⏳ **Pending** |

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
| **Cross-encoder:** `BAAI/bge-reranker-v2-m3` | Better suited for resume-job text pairs; clean HuggingFace repo |
| **Full resume text for reranking** | Using full text (6K+ chars) vs 2K Pinecone metadata snippet for richer cross-encoder scoring |
| **Email in same LLM call as scoring** | Avoids extra latency and cost of a separate API call |
| **Email extraction from resume** | Candidate email extracted via regex from resume text for pre-filling in email popup |
| **Signed as Naga Rithesh** | Interview invitation emails signed with "Best regards, Naga Rithesh" |

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

### 4. Feedback Loop
Add `POST /feedback` endpoint. Store accept/reject per result. Use data later to fine-tune cross-encoder or adjust score weights.

### 5. Caching
Cache embeddings for frequent queries. If same/similar prompt searched again, skip LLM call and just retrieve + rerank.

### 6. Multi-Agent Pipeline (Future)
Extend to specialized agents:
| Agent | Responsibility |
|---|---|
| Resume Parsing Agent | Extract structured info from raw text |
| Skill Matching Agent | Semantic skill comparison |
| Experience Evaluation Agent | Career trajectory analysis |
| Technical Evaluation Agent | Technical depth assessment |
| Culture Fit Agent | Communication & soft skill indicators |
