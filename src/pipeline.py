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


def _report(step: str, status: str, **kwargs) -> dict:
    return {"type": "step", "step": step, "status": status, **kwargs}


def run_pipeline(
    query: str,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    expand_queries: bool = True,
    verbose: bool = False,
) -> dict:
    result = None
    for event in run_pipeline_stream(query, top_k_retrieve, top_k_rerank, expand_queries):
        if event.get("type") == "result":
            result = event
    if result is None:
        return {"error": "Pipeline did not complete", "results": []}
    if "error" in result:
        return {"error": result["error"], "results": []}
    return {
        "query": result.get("query", query),
        "requirements": result.get("requirements", {}),
        "results": result.get("results", []),
    }


def run_pipeline_stream(
    query: str,
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    expand_queries: bool = True,
) -> dict:
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info(f"PIPELINE START — Query: {query}")
    logger.info("=" * 60)

    yield _report("Guardrail", "running")
    logger.info("STEP 1/6: Guardrail validation")
    t1 = time.perf_counter()
    valid, reason = guardrail_check(query)
    if not valid:
        logger.warning(f"Guardrail REJECTED: {reason}")
        yield {"type": "error", "message": f"Invalid query: {reason}"}
        return
    dt = time.perf_counter() - t1
    logger.info(f"Guardrail: PASSED ({dt:.2f}s)")
    yield _report("Guardrail", "done", time=round(dt, 2))

    yield _report("Extraction", "running")
    logger.info("STEP 2/6: LLM requirement extraction")
    t1 = time.perf_counter()
    requirements = extract_requirements(query)
    dt = time.perf_counter() - t1
    logger.info(f"Extraction: skills={requirements['skills']}, "
                f"seniority={requirements['seniority']}, "
                f"category={requirements['category']} ({dt:.2f}s)")
    yield _report("Extraction", "done", time=round(dt, 2),
                  detail=f"skills={requirements['skills']}")

    search_texts = [build_search_text(requirements)]
    logger.info(f"Search text: {search_texts[0]}")

    yield _report("Query Expansion", "running")
    if expand_queries:
        logger.info("STEP 3/6: Query expansion (LLM)")
        t1 = time.perf_counter()
        expansions = expand_query(query)
        dt = time.perf_counter() - t1
        expansions_str = " | ".join(expansions)
        logger.info(f"Expansions ({len(expansions)}): {expansions} ({dt:.2f}s)")
        search_texts.extend(expansions)
        yield _report("Query Expansion", "done", time=round(dt, 2),
                      detail=f"3 expansions: {expansions_str}")
    else:
        yield _report("Query Expansion", "skipped")

    yield _report("Hybrid Search", "running")
    logger.info("STEP 4/6: Hybrid search (Vector + BM25 + RRF)")
    t1 = time.perf_counter()
    all_retrieved = []
    for i, st in enumerate(search_texts):
        t2 = time.perf_counter()
        logger.info(f"  Search #{i+1}/{len(search_texts)}: \"{st}\"")
        retrieved = search_hybrid(st, top_k=top_k_retrieve)
        dt2 = time.perf_counter() - t2
        logger.info(f"  -> {len(retrieved)} candidates ({dt2:.2f}s)")
        all_retrieved.append(retrieved)

    merged = _merge_results(all_retrieved)
    dt = time.perf_counter() - t1
    logger.info(f"Merged: {len(merged)} unique candidates ({dt:.2f}s)")
    yield _report("Hybrid Search", "done", time=round(dt, 2),
                  detail=f"{len(merged)} unique candidates")

    yield _report("Reranking", "running")
    logger.info("STEP 5/6: Cross-encoder reranking")
    t1 = time.perf_counter()
    reranked = rerank(query, merged, top_k=top_k_rerank)
    dt = time.perf_counter() - t1
    logger.info(f"Reranked {len(reranked)} candidates ({dt:.2f}s)")
    yield _report("Reranking", "done", time=round(dt, 2),
                  detail=f"top-{top_k_rerank} candidates")

    yield _report("LLM Scoring", "running")
    logger.info("STEP 6/6: LLM final scoring")
    t1 = time.perf_counter()
    scored = score_candidates(query, reranked)
    dt = time.perf_counter() - t1
    logger.info(f"Scored {len(scored)} candidates ({dt:.2f}s)")
    yield _report("LLM Scoring", "done", time=round(dt, 2))

    for r in scored:
        logger.info(f"  RESULT: {r['id']} | Score={r['overall_score']}/100 "
                    f"| Skills={','.join(r['skills'][:5])}")
        logger.info(f"  EMAIL Subject: {r.get('email_subject', '')}")
        logger.info(f"  EMAIL Body: {r.get('email_body', '')}")

    elapsed = time.perf_counter() - t0
    logger.info("=" * 60)
    logger.info(f"PIPELINE DONE in {elapsed:.2f}s")
    logger.info("=" * 60)

    yield {
        "type": "result",
        "query": query,
        "requirements": requirements,
        "results": scored,
        "elapsed": round(elapsed, 2),
    }
