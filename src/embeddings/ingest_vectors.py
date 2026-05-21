import json
import sys
import time
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.embeddings.chunker import chunk_all_resumes
from src.embeddings.embedder import embed_texts, estimate_tokens
from src.embeddings.vector_store import (
    ensure_index,
    delete_index,
    upsert_vectors,
    create_metadata,
)


def ingest_all(
    json_path: str,
    recreate_index: bool = False,
    batch_size: int = 20,
):
    print("=" * 60)
    print("Phase 2: Embedding & Vector Store Ingestion")
    print("=" * 60)

    start = time.perf_counter()

    print(f"\nLoading candidates from: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    print(f"  Loaded {len(candidates)} candidates")

    print(f"\nChunking resumes...")
    chunks = chunk_all_resumes(candidates)
    print(f"  Created {len(chunks)} chunks from {len(candidates)} candidates")

    chunk_map = {ch["candidate_id"]: ch for ch in chunks}
    skipped_ids = set()

    text_per_candidate = []
    token_counts = []
    valid_candidates = []
    for c in candidates:
        text = c.get("clean_text", "")
        if not text:
            full_chunk = chunk_map.get(c["id"], {})
            text = full_chunk.get("text", "")
        if not text:
            skipped_ids.add(c["id"])
            continue
        text_per_candidate.append(text)
        token_counts.append(estimate_tokens(text))
        valid_candidates.append(c)

    candidates = valid_candidates
    if skipped_ids:
        print(f"  Skipped {len(skipped_ids)} candidates with empty text")

    total_tokens = sum(token_counts)
    avg_tokens = total_tokens / len(token_counts) if token_counts else 0
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Avg tokens/candidate: {avg_tokens:.0f}")
    print(f"  Est. OpenAI cost (text-embedding-3-small @ $0.02/1K tokens): ${total_tokens * 0.02 / 1000:.4f}")

    print(f"\nEnsuring Pinecone index...")
    if recreate_index:
        print("  Deleting existing index...")
        delete_index()
    index_name = ensure_index()
    print(f"  Index '{index_name}' ready")

    print(f"\nGenerating embeddings ({batch_size} at a time)...")
    embeddings = embed_texts(text_per_candidate, batch_size=batch_size, show_progress=True)
    print(f"  Generated {len(embeddings)} embeddings")
    print(f"  Dim: {len(embeddings[0]) if embeddings else 'N/A'}")

    print(f"\nPreparing vectors for Pinecone...")
    vectors = []
    for c, emb in zip(candidates, embeddings):
        metadata = create_metadata(c)
        # Limit text in metadata to avoid size limits
        clean_preview = c.get("clean_text", "")[:3000]
        metadata["text_preview"] = clean_preview
        vectors.append({
            "id": c["id"],
            "values": emb,
            "metadata": metadata,
        })
    print(f"  Prepared {len(vectors)} vectors")

    print(f"\nUpserting to Pinecone...")
    upserted = upsert_vectors(vectors, batch_size=100)
    print(f"  Upserted {upserted} vectors")

    elapsed = time.perf_counter() - start
    print(f"\n{'=' * 60}")
    print(f"Done in {elapsed:.2f}s ({elapsed / 60:.1f} min)")
    print(f"Candidates indexed: {upserted}")
    print(f"Cost: ~${total_tokens * 0.02 / 1000:.4f} for embeddings")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    json_path = "C:\\Users\\vmuser\\Documents\\ProdaptCapstone\\data\\processed\\resumes.json"

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate index")
    args = parser.parse_args()

    ingest_all(json_path, recreate_index=args.recreate)
