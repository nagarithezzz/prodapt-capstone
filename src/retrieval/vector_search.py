import time

from pinecone import Pinecone
from src.utils.config import (
    get_pinecone_api_key,
    get_pinecone_index_name,
    get_openai_embedding_model,
)
from openai import OpenAI
from src.utils.config import get_openai_api_key
from src.utils.log import logger


_embed_client: OpenAI | None = None
_pc_index = None


def _get_embedder() -> OpenAI:
    global _embed_client
    if _embed_client is None:
        _embed_client = OpenAI(api_key=get_openai_api_key())
        logger.debug("OpenAI embedding client initialized")
    return _embed_client


def _get_index():
    global _pc_index
    if _pc_index is None:
        pc = Pinecone(api_key=get_pinecone_api_key())
        _pc_index = pc.Index(get_pinecone_index_name())
        logger.debug(f"Pinecone index '{get_pinecone_index_name()}' connected")
    return _pc_index


def embed_query(text: str) -> list[float]:
    client = _get_embedder()
    model = get_openai_embedding_model()
    t1 = time.perf_counter()
    resp = client.embeddings.create(input=text, model=model)
    elapsed = (time.perf_counter() - t1) * 1000
    tokens = resp.usage.total_tokens if resp.usage else "?"
    logger.debug(f"    [Embedding] {elapsed:.0f}ms, {tokens} tokens")
    return resp.data[0].embedding


def search_candidates(
    query_text: str,
    requirements: dict | None = None,
    top_k: int = 20,
) -> list[dict]:
    index = _get_index()
    logger.debug(f"    Embedding query: \"{query_text[:60]}...\"")
    t1 = time.perf_counter()
    query_vec = embed_query(query_text)
    embed_time = time.perf_counter() - t1

    logger.debug(f"    Pinecone query (top_k={top_k})...")
    t1 = time.perf_counter()
    results = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
    )
    query_time = time.perf_counter() - t1

    candidates = []
    for r in results.matches:
        meta = r.metadata
        candidates.append({
            "id": r.id,
            "score": r.score,
            "category": meta.get("category", ""),
            "skills": meta.get("skills", "").split(",") if meta.get("skills") else [],
            "years_experience": meta.get("years_experience", -1),
            "role_category": meta.get("role_category", ""),
            "text_preview": meta.get("text_preview", ""),
            "decision": meta.get("decision", ""),
            "reason_for_decision": meta.get("reason_for_decision", ""),
            "job_description": meta.get("job_description", ""),
        })

    logger.debug(f"    Pinecone returned {len(candidates)} matches "
                 f"(embed={embed_time:.2f}s, query={query_time:.2f}s)")

    if candidates:
        top_scores = [(c["id"], f"{c['score']:.4f}") for c in candidates[:3]]
        logger.debug(f"    Top vector matches: {top_scores}")

    return candidates
