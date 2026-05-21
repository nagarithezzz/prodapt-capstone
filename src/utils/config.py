import os
from dotenv import load_dotenv

load_dotenv()


def get_openai_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or key == "sk-your-openai-api-key-here":
        raise ValueError(
            "OPENAI_API_KEY not set. Create a .env file with your key."
        )
    return key


def get_openai_embedding_model() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def get_openai_llm_model() -> str:
    return os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")


def get_pinecone_api_key() -> str:
    key = os.getenv("PINECONE_API_KEY", "")
    if not key or key.startswith("pcsk-your-pinecone"):
        raise ValueError(
            "PINECONE_API_KEY not set. Create a .env file with your key."
        )
    return key


def get_pinecone_environment() -> str:
    return os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")


def get_pinecone_index_name() -> str:
    return os.getenv("PINECONE_INDEX_NAME", "resume-matcher")


def get_embedding_dim() -> int:
    return int(os.getenv("EMBEDDING_DIM", "1536"))
