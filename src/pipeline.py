import time

from src.agents.query_understanding import (
    guardrail_check,
    extract_requirements,
    build_search_text,
    expand_query,
)
from src.retrieval.hybrid_search import search_hybrid
from src.retrieval.reranker import rerank
from src.agents.final_scorer import score_candidates
from src.utils.log import logger


def _merge_results(results_list: list[list[dict]]) -> list[dict]:
    seen = {}
    for results in results_list:
        for c in results:
            cid = c["id"]
            if cid in seen:
                seen[cid]["score"] = max(seen[cid]["score"], c["score"])
            else:
                seen[cid] = c
    merged = list(seen.values())
    merged.sort(key=lambda x: x.get("score", 0), reverse=True)
    return merged


def run_pipeline(
    query: str,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    expand_queries: bool = True,
    verbose: bool = False,
) -> dict:
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info(f"PIPELINE START — Query: {query}")
    logger.info("=" * 60)

    logger.info("STEP 1/6: Guardrail validation")
    t1 = time.perf_counter()
    valid, reason = guardrail_check(query)
    if not valid:
        logger.warning(f"Guardrail REJECTED: {reason}")
        return {"error": f"Invalid query: {reason}", "results": []}
    logger.info(f"Guardrail: PASSED ({time.perf_counter() - t1:.2f}s)")

    logger.info("STEP 2/6: LLM requirement extraction")
    t1 = time.perf_counter()
    requirements = extract_requirements(query)
    logger.info(f"Extraction: skills={requirements['skills']}, "
                f"seniority={requirements['seniority']}, "
                f"category={requirements['category']} "
                f"({time.perf_counter() - t1:.2f}s)")

    search_texts = [build_search_text(requirements)]
    logger.info(f"Search text: {search_texts[0]}")

    if expand_queries:
        logger.info("STEP 3/6: Query expansion (LLM)")
        t1 = time.perf_counter()
        expansions = expand_query(query)
        logger.info(f"Expansions ({len(expansions)}): {expansions} "
                    f"({time.perf_counter() - t1:.2f}s)")
        search_texts.extend(expansions)

    logger.info("STEP 4/6: Hybrid search (Vector + BM25 + RRF)")
    t1 = time.perf_counter()
    all_retrieved = []
    for i, st in enumerate(search_texts):
        t2 = time.perf_counter()
        logger.info(f"  Search #{i+1}/{len(search_texts)}: \"{st}\"")
        retrieved = search_hybrid(st, top_k=top_k_retrieve)
        logger.info(f"  -> {len(retrieved)} candidates ({time.perf_counter() - t2:.2f}s)")
        all_retrieved.append(retrieved)

    merged = _merge_results(all_retrieved)
    logger.info(f"Merged: {len(merged)} unique candidates "
                f"({time.perf_counter() - t1:.2f}s)")

    logger.info("STEP 5/6: Cross-encoder reranking")
    t1 = time.perf_counter()
    reranked = rerank(query, merged, top_k=top_k_rerank)
    logger.info(f"Reranked {len(reranked)} candidates "
                f"({time.perf_counter() - t1:.2f}s)")

    logger.info("STEP 6/6: LLM final scoring")
    t1 = time.perf_counter()
    scored = score_candidates(query, reranked)
    logger.info(f"Scored {len(scored)} candidates "
                f"({time.perf_counter() - t1:.2f}s)")

    for r in scored:
        logger.info(f"  RESULT: {r['id']} | Score={r['overall_score']}/100 "
                    f"| Skills={','.join(r['skills'][:5])}")

    elapsed = time.perf_counter() - t0
    logger.info("=" * 60)
    logger.info(f"PIPELINE DONE in {elapsed:.2f}s")
    logger.info("=" * 60)

    return {
        "query": query,
        "requirements": requirements,
        "results": scored,
    }
