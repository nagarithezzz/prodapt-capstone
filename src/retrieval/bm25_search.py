import json
import re
import os
import time
from rank_bm25 import BM25Okapi
from src.utils.log import logger


_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "resumes.json")
_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_+#.-]{2,}")

_bm25: BM25Okapi | None = None
_candidate_map: dict[str, dict] = {}
_index_built = False


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def _build_index():
    global _bm25, _candidate_map, _index_built
    if _index_built:
        return
    t1 = time.perf_counter()
    logger.info("    BM25 building index from resumes.json...")
    with open(_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    corpus = []
    for c in candidates:
        text = c.get("clean_text", "")
        if text:
            tokens = _tokenize(text)
        else:
            tokens = []
        corpus.append(tokens)
        _candidate_map[c["id"]] = c

    _bm25 = BM25Okapi(corpus)
    _index_built = True
    logger.info(f"    BM25 index built: {len(_candidate_map)} documents, "
                f"{sum(len(d) for d in corpus):,} tokens "
                f"({time.perf_counter() - t1:.2f}s)")


def search_bm25(
    query_text: str,
    top_k: int = 20,
) -> list[dict]:
    global _bm25
    _build_index()

    query_tokens = _tokenize(query_text)
    if not query_tokens:
        logger.debug("    BM25: no query tokens found")
        return []

    t1 = time.perf_counter()
    scores = _bm25.get_scores(query_tokens)
    doc_ids = list(_candidate_map.keys())

    scored = []
    for i, doc_id in enumerate(doc_ids):
        score = scores[i]
        if score > 0:
            c = _candidate_map[doc_id]
            scored.append({
                "id": doc_id,
                "score": float(score),
                "category": c.get("category", ""),
                "skills": c.get("skills", []),
                "years_experience": c.get("years_experience", -1),
                "role_category": c.get("role_category", ""),
                "text_preview": (c.get("clean_text", "") or "")[:2000],
                "decision": c.get("decision", ""),
                "reason_for_decision": c.get("reason_for_decision", ""),
                "job_description": c.get("job_description", ""),
                "email": c.get("email", ""),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[:top_k]
    elapsed = time.perf_counter() - t1

    if result:
        top_hits = [(c["id"], f"{c['score']:.1f}") for c in result[:3]]
    else:
        top_hits = []

    logger.debug(f"    BM25 search: {len(result)} matches in {elapsed:.2f}s "
                 f"(query tokens: {query_tokens})")
    if top_hits:
        logger.debug(f"    Top BM25: {top_hits}")

    return result
