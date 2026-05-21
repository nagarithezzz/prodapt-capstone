# AI-Powered Resume Intelligence & Candidate Matching System

## 1. Problem Statement

Traditional applicant tracking systems rely on keyword matching, which overlooks strong candidates whose resumes use different terminology to describe similar skills or experiences. Recruiters must manually interpret natural-language hiring requirements and evaluate complex aspects including technical skills depth, career progression, role transitions, education, location, and transferable skills — all from resumes in varied formats (PDF, structured profiles, portfolio links). This manual process is time-consuming, inconsistent, and prone to missing valuable candidates.

## 2. Objective

Build an AI-powered resume intelligence and candidate matching system that:

- Interprets recruiter queries written in natural language
- Evaluates candidate resumes against job requirements using semantic understanding
- Returns ranked candidates with explainable matching scores
- Reduces manual screening effort while improving consistency and quality of candidate evaluation

## 3. Key Capabilities

| Capability | Description |
|---|---|
| **Semantic Job Requirement Understanding** | Interpret natural-language recruiter queries to extract underlying skills, technologies, and experience levels |
| **Intelligent Candidate Matching** | Evaluate alignment between candidate profile and job description beyond keyword overlap |
| **Context-Aware Skill Evaluation** | Distinguish basic familiarity from deep expertise based on skill usage context |
| **Career Progression Analysis** | Analyze professional journey, role transitions, and seniority levels |
| **Transferable Skill Identification** | Recommend candidates with adjacent/related skills who could successfully perform the role |
| **Structured Candidate Insights** | Provide summaries highlighting key strengths, relevant experience, and notable achievements |
| **Explainable Matching Scores** | Deliver transparent reasoning for each candidate recommendation |

## 4. Functional Requirements

### 4.1 Basic Tier (Requirement 1)

| ID | Requirement | Description |
|---|---|---|
| FR1.1 | Resume Ingestion | Parse resumes from CSV, JSON, PDF formats into structured candidate profiles |
| FR1.2 | Basic RAG for Candidate Retrieval | Retrieve relevant candidates using vector embeddings and semantic search |
| FR1.3 | Skills-Based Semantic Matching | Match job requirements to candidate skills using semantic similarity (not just keyword overlap) |
| FR1.4 | Simple Ranking Agent | Rank candidates by skill overlap score |
| FR1.5 | Job Category Filtering | Filter candidates by predefined job categories/roles |
| FR1.6 | Basic Job-Resume Alignment Scoring | Compute an overall alignment score between a job query and each candidate |
| FR1.7 | Input Guardrails | Validate job requirements input (reject empty, malformed, or non-job-related queries) |
| FR1.8 | Resume Parsing Validation | Detect and reject unparseable or invalid resume files |
| FR1.9 | Metadata Filtering | Filter candidates by experience level, role category, education |
| FR1.10 | REST API | Expose all core functionality through a documented API endpoint |

### 4.2 Advanced Tier (Requirement 2)

| ID | Requirement | Description |
|---|---|---|
| FR2.1 | DeepEval Integration | Measure matching quality and diversity using DeepEval metrics |
| FR2.2 | Custom Evaluation Metrics | Implement skill coverage, experience fit, and culture match scores |
| FR2.3 | Fine-Tuned Embedding Rerank | Rerank candidates using fine-tuned job-resume embedding models |
| FR2.4 | LLM-as-Judge | Use LLM to assess soft skills and candidate potential |
| FR2.5 | Token Usage Optimization | Optimize token consumption for high-volume screening scenarios |
| FR2.6 | Performance Benchmarking | Measure and report candidates processed per second |
| FR2.7 | Bias Detection Guardrails | Detect demographic and language bias in matching results |
| FR2.8 | Front-End Interface | Build a simple UI demonstrating end-to-end interaction with the service |

### 4.3 Hybrid Candidate Retrieval

| ID | Requirement | Description |
|---|---|---|
| FR3.1 | Hybrid Search | Combine vector embedding search with keyword matching (BM25/lexical) |
| FR3.2 | Dynamic Filtering | Filter candidates by experience, skills, education, and industry in real-time |
| FR3.3 | Cross-Encoder Reranking | Rerank initial retrieval results using cross-encoder relevance scoring |

### 4.4 Multi-Stage Hiring Agent Pipeline

| ID | Agent | Responsibility |
|---|---|---|
| FR4.1 | Resume Parsing Agent | Extract structured information (skills, experience, education, projects) from raw resume text |
| FR4.2 | Skill Matching Agent | Compare job description skills against candidate skills using semantic matching |
| FR4.3 | Experience Evaluation Agent | Analyze years of experience, career trajectory, and seniority progression |
| FR4.4 | Technical Evaluation Agent | Estimate depth of technical expertise for each relevant skill |
| FR4.5 | Culture Fit Agent | Evaluate communication quality, teamwork indicators, and soft skills from resume text |

### 4.5 Additional Hiring Intelligence

| ID | Requirement | Description |
|---|---|---|
| FR5.1 | Explainable Ranking | Provide score breakdown (skills, experience, education, culture) for each candidate |
| FR5.2 | Recruiter Feedback Loop | Capture recruiter feedback (accept/reject/flag) to improve ranking models over time |
| FR5.3 | Hiring Analytics Dashboard | Show skill demand trends, candidate pool statistics, and matching distribution |
| FR5.4 | Interview Scheduling Agent Handoff | Pass shortlisted candidates to an interview scheduling agent |
| FR5.5 | Agent-to-Agent (A2A) Communication | Enable communication between recruiter agents and hiring manager agents |

## 5. Technical Requirements

### 5.1 Stack Recommendations

| Component | Technology |
|---|---|
| Backend Framework | Python (FastAPI) |
| Vector Database | ChromaDB / FAISS / Qdrant |
| Embedding Model | sentence-transformers (e.g., `all-MiniLM-L6-v2` or fine-tuned variant) |
| LLM | OpenAI / Anthropic / local (Ollama) for LLM-as-judge |
| Search | Hybrid: vector embeddings + BM25 (via Elasticsearch or custom) |
| Evaluation | DeepEval |
| Frontend | React / Streamlit / Gradio |
| Document Parsing | PyMuPDF (fitz), pdfplumber, python-docx |

### 5.2 Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR1 | API Response Time | < 5s for retrieval + ranking (up to 1000 candidates) |
| NFR2 | Throughput | Support batch screening of 10,000+ resumes |
| NFR3 | Modularity | Each agent must be independently swappable/testable |
| NFR4 | Explainability | Every match score must include a human-readable explanation |
| NFR5 | Extensibility | New agent types can be added without modifying existing pipeline code |
| NFR6 | Bias Mitigation | System must report demographic distribution of ranked results |

## 6. Dataset

**Name:** Resume Dataset Collection

**Primary Link:** https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset

**Alternative Links:**
- https://www.kaggle.com/datasets/jillanisofttech/updated-resume-dataset
- https://www.kaggle.com/datasets/suriyaganesh/resume-dataset-structured (54k)
- https://www.kaggle.com/datasets/pranavvenugo/resume-and-job-description
- https://www.kaggle.com/datasets/towhidultonmoy/resume-parsing-summarizer-dataset-for-ats-system

**Format:** CSV, JSON, PDF

**Key Fields:** `skills`, `experience`, `education`, `category`, `resume_text`

## 7. Deliverables

### 7.1 Architecture Diagram (JPEG/PDF)
High-level system diagram showing:
- Resume ingestion and parsing pipeline
- Document chunking and embedding generation
- Hybrid candidate retrieval system
- Multi-agent evaluation pipeline
- Final candidate ranking and explanation generation

### 7.2 Design Document
Articulate system design decisions and trade-offs:
- Embedding model selection for resumes
- Chunking strategy for long resumes
- Hybrid search vs semantic-only search trade-offs
- Agent orchestration design pattern (sequential, parallel, or hybrid)
- Bias mitigation strategies

### 7.3 Full Executable Code (Microservice)
- Modular, clear Python codebase
- README covering:
  - Project setup (installation and run instructions)
  - Resume ingestion and indexing process
  - Example job description query
  - Example ranked candidate output with explanation

### 7.4 Panel Presentation (10 minutes)
- Demo of working solution (8 minutes)
  - Recruiter enters natural-language job description
  - System retrieves candidate resumes
  - Multi-agent pipeline evaluates suitability
  - System returns ranked candidates with explanations
- Q&A with panel (2 minutes)

## 8. Architecture Overview (Conceptual)

```
[Recruiter Query] → [Input Guardrails] → [Query Understanding]
                                               ↓
[Resume PDF/CSV] → [Parsing Agent] → [Chunking] → [Embedding] → [Vector DB]
                                                                       ↓
[Hybrid Retrieval] ←─── [Keyword Search (BM25)] ←─── [Candidate Pool]
       ↓
[Reranking (Cross-Encoder)]
       ↓
[Multi-Agent Pipeline]
    ├── Skill Matching Agent
    ├── Experience Evaluation Agent
    ├── Technical Evaluation Agent
    └── Culture Fit Agent
       ↓
[Explainable Scoring & Ranking]
       ↓
[REST API / Frontend UI]
```

## 9. Success Criteria

1. System correctly retrieves relevant candidates for natural-language job descriptions with >80% precision@10
2. Matching scores include interpretable breakdowns (skill coverage, experience fit, education match, culture fit)
3. Multi-agent pipeline processes candidate in <2s average per candidate
4. Bias detection guardrails flag mismatches in demographic representation
5. Frontend demo demonstrates full flow: query → retrieval → evaluation → ranking → explanation
