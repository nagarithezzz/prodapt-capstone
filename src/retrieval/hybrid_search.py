import time

from src.retrieval.vector_search import search_candidates as vector_search
from src.retrieval.bm25_search import search_bm25
from src.utils.log import logger


RRF_K = 60


def _rrf_merge(
    vector_results: list[dict],
    bm25_results: list[dict],
    top_k: int,
) -> list[dict]:
    logger.info(f"    RRF merging {len(vector_results)} vector + {len(bm25_results)} BM25 results")
    rrf_scores: dict[str, float] = {}
    result_map: dict[str, dict] = {}

    for rank, c in enumerate(vector_results):
        cid = c["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank + 1)
        result_map[cid] = c

    for rank, c in enumerate(bm25_results):
        cid = c["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank + 1)
        if cid not in result_map:
            result_map[cid] = c

    overlap = len(vector_results) + len(bm25_results) - len(rrf_scores)
    logger.info(f"    RRF done: {len(rrf_scores)} unique, {overlap} overlapping candidates")

    scored = []
    for cid, rrf_score in rrf_scores.items():
        c = dict(result_map[cid])
        c["score"] = rrf_score
        scored.append(c)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]
    top_summary = " | ".join(f"{c['id']}:{c['score']:.4f}" for c in top[:5])
    logger.info(f"    Top {len(top)} after RRF: {top_summary}")
    return top


def search_hybrid(
    query_text: str,
    top_k: int = 20,
    vector_top_k: int = 30,
    bm25_top_k: int = 30,
) -> list[dict]:
    t1 = time.perf_counter()
    logger.info(f"    Vector search (Pinecone, top_k={vector_top_k})...")
    t2 = time.perf_counter()
    vector_results = vector_search(query_text, top_k=vector_top_k)
    vec_time = time.perf_counter() - t2

    logger.info(f"    BM25 search (local, top_k={bm25_top_k})...")
    t2 = time.perf_counter()
    bm25_results = search_bm25(query_text, top_k=bm25_top_k)
    bm25_time = time.perf_counter() - t2

    logger.info(f"    Search times — Vector: {vec_time:.2f}s, BM25: {bm25_time:.2f}s")

    merged = _rrf_merge(vector_results, bm25_results, top_k=top_k)

    logger.info(f"    Hybrid search complete ({time.perf_counter() - t1:.2f}s)")
    return merged
