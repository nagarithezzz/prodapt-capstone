import time
from openai import OpenAI
from src.utils.config import get_openai_api_key, get_openai_embedding_model


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_openai_api_key())
    return _client


def embed_text(text: str, model: str | None = None) -> list[float]:
    client = _get_client()
    model = model or get_openai_embedding_model()
    resp = client.embeddings.create(input=text, model=model)
    return resp.data[0].embedding


def embed_texts(
    texts: list[str],
    model: str | None = None,
    batch_size: int = 20,
    max_retries: int = 3,
    show_progress: bool = False,
) -> list[list[float]]:
    client = _get_client()
    model = model or get_openai_embedding_model()
    all_embeddings: list[list[float]] = []

    batch_iter = range(0, len(texts), batch_size)
    if show_progress:
        from tqdm import tqdm
        batch_iter = tqdm(batch_iter, desc="Embedding", unit="batch")

    for i in batch_iter:
        batch = texts[i : i + batch_size]
        for attempt in range(max_retries):
            try:
                resp = client.embeddings.create(input=batch, model=model)
                batch_embeddings = [d.embedding for d in resp.data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
                else:
                    raise e

        if show_progress and hasattr(batch_iter, "set_postfix"):
            ...

    return all_embeddings


def estimate_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4
