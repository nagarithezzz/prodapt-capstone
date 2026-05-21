import json
import os
import time

from sentence_transformers import CrossEncoder
from src.utils.log import logger

_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
_CANDIDATES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "resumes.json"
)

_encoder: CrossEncoder | None = None
_full_texts: dict[str, str] | None = None


def _load_full_texts() -> dict[str, str]:
    global _full_texts
    if _full_texts is None:
        with open(_CANDIDATES_PATH, "r", encoding="utf-8") as f:
            candidates = json.load(f)
        _full_texts = {c["id"]: c.get("clean_text", "") for c in candidates}
    return _full_texts


def _get_encoder() -> CrossEncoder:
    global _encoder
    if _encoder is None:
        logger.info(f"  Loading cross-encoder model: {_MODEL_NAME}")
        t1 = time.perf_counter()
        _encoder = CrossEncoder(_MODEL_NAME)
        logger.info(f"  Cross-encoder loaded ({time.perf_counter() - t1:.2f}s)")
    return _encoder


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
) -> list[dict]:
    if not candidates:
        logger.warning("  Rerank: no candidates to rerank")
        return []

    encoder = _get_encoder()
    full_texts = _load_full_texts()
    logger.info(f"  Reranking {len(candidates)} candidates with cross-encoder")

    pairs = []
    valid = []
    for c in candidates:
        text = full_texts.get(c["id"], c.get("text_preview", ""))
        if text:
            pairs.append((query, text[:3000]))
            valid.append(c)

    if not pairs:
        logger.warning("  Rerank: no text available, using first candidates")
        return candidates[:top_k]

    t1 = time.perf_counter()
    scores = encoder.predict(pairs)
    elapsed = time.perf_counter() - t1
    logger.debug(f"  Cross-encoder predicted {len(scores)} pairs in {elapsed:.2f}s")

    scored = []
    for c, score in zip(valid, scores):
        scored.append({
            **c,
            "rerank_score": float(score),
        })

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    result = scored[:top_k]

    for i, r in enumerate(result):
        logger.info(f"  Rerank #{i+1}: {r['id']} | rerank_score={r['rerank_score']:.4f} | "
                    f"category={r['category']} | skills={','.join(r['skills'][:4])}")

    return result
