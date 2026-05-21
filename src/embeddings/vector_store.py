from pinecone import Pinecone, ServerlessSpec
from src.utils.config import (
    get_pinecone_api_key,
    get_pinecone_environment,
    get_pinecone_index_name,
    get_embedding_dim,
)


_client: Pinecone | None = None
_index = None


def _get_client() -> Pinecone:
    global _client
    if _client is None:
        _client = Pinecone(api_key=get_pinecone_api_key())
    return _client


def ensure_index() -> str:
    client = _get_client()
    index_name = get_pinecone_index_name()
    dim = get_embedding_dim()

    existing = [i.name for i in client.list_indexes()]
    if index_name not in existing:
        client.create_index(
            name=index_name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=get_pinecone_environment().replace("-aws", ""),
            ),
        )
    return index_name


def delete_index() -> None:
    client = _get_client()
    index_name = get_pinecone_index_name()
    existing = [i.name for i in client.list_indexes()]
    if index_name in existing:
        client.delete_index(index_name)


def get_index():
    global _index
    if _index is None:
        client = _get_client()
        index_name = get_pinecone_index_name()
        _index = client.Index(index_name)
    return _index


def upsert_vectors(vectors: list[dict], batch_size: int = 100) -> int:
    index = get_index()
    total = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch)
        total += len(batch)
    return total


def create_metadata(candidate: dict) -> dict:
    return {
        "category": candidate.get("category", ""),
        "skills": ",".join(candidate.get("skills", [])),
        "years_experience": candidate.get("years_experience") or -1,
        "role_category": candidate.get("role_category") or "",
    }
