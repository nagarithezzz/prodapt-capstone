import csv
import json
import os
import tempfile
from io import StringIO

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from src.api.schemas import (
    SearchRequest,
    SearchResponse,
    ScoredCandidate,
    Requirements,
    IngestResponse,
    CandidateDetail,
)
from src.pipeline import run_pipeline, run_pipeline_stream
from src.ingestion.resume_parser import parse_resume
from src.embeddings.ingest_vectors import ingest_all

app = FastAPI(title="Resume Intelligence API", version="1.0.0")

_CANDIDATES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "resumes.json"
)

_candidates_cache: list[dict] | None = None


def _load_candidates() -> list[dict]:
    global _candidates_cache
    if _candidates_cache is None:
        with open(_CANDIDATES_PATH, "r", encoding="utf-8") as f:
            _candidates_cache = json.load(f)
    return _candidates_cache


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = run_pipeline(
        query=req.query,
        top_k_rerank=req.top_k,
        expand_queries=req.expand_queries,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    reqs = result["requirements"]
    return SearchResponse(
        query=result["query"],
        requirements=Requirements(
            skills=reqs.get("skills", []),
            seniority=reqs.get("seniority", "any"),
            category=reqs.get("category", "UNKNOWN"),
            must_have=reqs.get("must_have", []),
            nice_to_have=reqs.get("nice_to_have", []),
            years_experience=reqs.get("years_experience"),
            original_query=reqs.get("original_query", ""),
        ),
        results=[
            ScoredCandidate(
                id=r["id"],
                overall_score=r["overall_score"],
                skill_score=r["skill_score"],
                experience_score=r["experience_score"],
                justification=r["justification"],
                email_subject=r.get("email_subject", ""),
                email_body=r.get("email_body", ""),
                category=r["category"],
                skills=r["skills"],
                years_experience=r["years_experience"],
                role_category=r["role_category"],
            )
            for r in result["results"]
        ],
    )


@app.post("/search/stream")
def search_stream(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    def event_stream():
        for event in run_pipeline_stream(
            query=req.query,
            top_k_rerank=req.top_k,
            expand_queries=req.expand_queries,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/candidates/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: str):
    candidates = _load_candidates()
    for c in candidates:
        if c["id"] == candidate_id:
            return CandidateDetail(
                id=c["id"],
                category=c.get("category", ""),
                skills=c.get("skills", []),
                years_experience=c.get("years_experience"),
                role_category=c.get("role_category"),
                char_count=c.get("char_count", 0),
                sections=c.get("sections", {}),
                clean_text=(c.get("clean_text", "") or "")[:5000],
            )
    raise HTTPException(status_code=404, detail="Candidate not found")


@app.post("/ingest", response_model=IngestResponse)
async def ingest_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.reader(StringIO(decoded))
    header = next(reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    parsed_count = 0
    rows = []
    for row in reader:
        rows.append(row)
        parsed = parse_resume(row)
        if parsed:
            parsed_count += 1

    if parsed_count == 0:
        raise HTTPException(status_code=400, detail="No valid resumes found in CSV")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        writer = csv.writer(tmp)
        writer.writerow(header)
        writer.writerows(rows)
        tmp_path = tmp.name

    try:
        output_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "data", "processed", "resumes.json"
        )

        import sys
        from pathlib import Path
        base = str(Path(__file__).resolve().parent.parent.parent)
        sys.path.insert(0, base)

        from src.ingestion.ingest import ingest_resumes
        parsed = ingest_resumes(
            tmp_path,
            output_path,
            skip_errors=True,
        )

        ingest_all(output_path, recreate_index=False)
    finally:
        os.unlink(tmp_path)

    global _candidates_cache
    _candidates_cache = None

    return IngestResponse(
        status="success",
        candidates_parsed=parsed_count,
        candidates_indexed=parsed_count,
        message=f"Ingested {parsed_count} candidates into the system",
    )
