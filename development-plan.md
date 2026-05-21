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
     ↓  Extracts: skills, seniority, domain, must-haves, nice-to-haves
     ↓
Phase 3.2 — Query Embedding → Vector Search (cosine sim, top-20)
     ↓                      + Metadata pre-filtering (category, exp level)
Phase 3.3 — Cross-Encoder Reranking (top-20 → top-5)
     ↓
Phase 3.4 — LLM Scoring (GPT-4o-mini): top-5 + job query → score + justification
     ↓
[Ranked output with explanations]
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

**Real example:**
```
Input:  "need a website maker with good design skills"
Output: {
  "skills": ["website making", "design skills"],
  "seniority": "any",
  "category": "DESIGNER",
  "must_have": ["website making"],
  "nice_to_have": ["design skills"]
}
```

### Phase 3.2 — Semantic Candidate Retrieval

| Step | Task | Details | Status |
|---|---|---|---|
| 3.2.1 | Query embedding | Enriched query (deduplicated skills + must_have + nice_to_have) embedded via `text-embedding-3-small` | ✅ Done |
| 3.2.2 | Vector search | Cosine similarity search on Pinecone, top-20 candidates | ✅ Done |
| 3.2.3 | Metadata pre-filtering | Pre-filter Pinecone by `category` if extracted from query | ✅ Done |

**Note:** BM25 hybrid search skipped for now — Pinecone supports it natively via sparse-dense if needed later.

### Phase 3.3 — Reranking

| Step | Task | Details | Status |
|---|---|---|---|
| 3.3.1 | Rerank top-20 → top-5 | Fallback: vector score sort when cross-encoder unavailable | ✅ Done |
| 3.3.2 | Cross-encoder ready | `cross-encoder/ms-marco-MiniLM-L-6-v2` available when VC++ redist installed | 🔧 Optional |

### Phase 3.4 — LLM Final Scoring

| Step | Task | Details | Status |
|---|---|---|---|
| 3.4.1 | Build prompt | GPT-4o-mini receives job query + top-5 candidate profiles (skills, experience, resume excerpt) | ✅ Done |
| 3.4.2 | Score dimensions | overall_score (0-100), skill_score, experience_score per candidate | ✅ Done |
| 3.4.3 | Justification | 2-3 sentence natural language explanation for each recommendation | ✅ Done |

**Real output:**
```json
{
  "candidate_id": "25061645",
  "overall_score": 90,
  "skill_score": 95,
  "experience_score": 85,
  "justification": "This candidate has a strong skill set that directly aligns with the job requirements, including web design and various design software.",
  "category": "DESIGNER",
  "skills": ["web design", "photoshop", "html", "illustrator", "css"]
}
```

### Verified Test Results

| # | Query | Top Match | Score |
|---|---|---|---|
| 1 | "backend web developer, services connecting systems" | IT candidate with 9yr full-stack exp | 75 |
| 2 | "early career data analyst, business data, reports" | Candidate with Python, R, stats analysis | 80 |
| 3 | "senior cloud architect, microservices" | IT PM with cloud infra background | 55 |
| 4 | "visual and interactive web components" | Designer with HTML, prototyping, UX | 75 |
| 5 | "need a website maker with good design skills" | Designer with web design, Photoshop, CSS | 90 |

---

## Phase 4 — API & Frontend

| Step | Task | Details | Est. Time |
|---|---|---|---|
| 4.1 | FastAPI endpoints | `POST /search` (query → ranked results), `POST /ingest` (upload resume), `GET /candidates/{id}` | 1 day |
| 4.2 | Pydantic schemas | Request/response validation | 0.5 day |
| 4.3 | Streamlit UI | Text input for query, dropdown for filters, results table with expandable explanations | 1 day |
| 4.4 | Docker setup | `Dockerfile` + `docker-compose.yml` for one-command startup | 0.5 day |

---

## Phase 5 — Advanced Features (Requirement 2)

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
│   │   ├── vector_search.py         # Pinecone search + metadata filtering
│   │   └── reranker.py             # Cross-encoder reranking (top-20→top-5)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── query_understanding.py  # GPT-4o-mini: guardrail + structured extraction
│   │   └── final_scorer.py         # GPT-4o-mini: score + justification
│   ├── pipeline.py                 # Orchestrator: guardrail → extract → search → rerank → score
│   ├── api/                        # ⏳ Phase 4
│   │   └── __init__.py
│   ├── evaluation/                 # ⏳ Phase 5
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       └── config.py               # Central config loader from .env
├── frontend/                       # ⏳ Phase 4
├── tests/
├── requirements.txt
├── requirements.md
├── development-plan.md
└── README.md
```

---

## Progress & Estimated Timeline

| Phase | Description | Status | Est. Time |
|---|---|---|---|---|
| 1 | Data Ingestion & Processing | ✅ **Complete** | ~2 days |
| 2 | Embedding & Vector Store | ✅ **Complete** | ~1 day |
| 3 | Retrieval & Matching Pipeline | ✅ **Complete** | ~1 day |
| 4 | API & Frontend | ⏳ **Pending** | 2-3 days |
| 5 | Advanced Features (R2) | ⏳ **Pending** | 3-4 days |

**Completed:** Phases 1-3 (~4 days)
**Remaining:** Phases 4-5 (~5-7 days)

---

## Suggestions for Improvement

### 1. Query Expansion
A vague prompt like "website maker" is too short. Generate **3-4 alternative phrasings** via LLM (e.g., "frontend web developer", "React UI engineer"), embed all, and aggregate results. Significantly improves recall.

### 2. Weighted Chunk Scoring
Not all sections carry equal weight. Assign:
- Skills section → **3x weight**
- Experience → **2x weight**
- Education → **1x weight**

### 3. Experience Level Parsing
Map years-to-level:
| Years | Level |
|---|---|
| 0-2 | Junior |
| 3-5 | Mid |
| 6+ | Senior |

Use as metadata pre-filter so "senior" query doesn't return freshers.

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
