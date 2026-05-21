import json
import time
from openai import OpenAI
from src.utils.config import get_openai_api_key, get_openai_llm_model
from src.utils.log import logger


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_openai_api_key())
        logger.debug("OpenAI client initialized")
    return _client


_EXTRACT_PROMPT = """You are a hiring assistant that analyzes job requirements written in natural language.

Extract the following fields from the recruiter's query. Return ONLY valid JSON with no explanation.

Fields:
- skills (list[str]): specific technical or professional skills mentioned
- seniority (str): "junior", "mid", "senior", or "any" if not specified
- category (str): best matching job category from: INFORMATION-TECHNOLOGY, ENGINEERING, DESIGNER, FINANCE, HEALTHCARE, SALES, MARKETING, HR, EDUCATION, CONSTRUCTION, LEGAL, or "UNKNOWN"
- must_have (list[str]): critical requirements explicitly stated as required
- nice_to_have (list[str]): preferred but not required skills
- years_experience (int | null): minimum years of experience requested, or null if not specified

Recruiter query: {query}

JSON:"""

_EXPAND_PROMPT = """You are a hiring assistant. Given a job requirement, generate {n} concise alternative search queries that capture different aspects of the role. Each query should be a short phrase (5-15 words) focusing on different keywords, technologies, or angles.

Return ONLY a valid JSON object with a key "queries" containing the array of strings.

Original: {query}

JSON:"""


def expand_query(query: str, n: int = 3) -> list[str]:
    logger.info(f"  [LLM call] Generating {n} alternative query phrasings")
    client = _get_client()
    model = get_openai_llm_model()
    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _EXPAND_PROMPT.format(query=query, n=n)}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    expansions = json.loads(resp.choices[0].message.content)
    if isinstance(expansions, dict):
        for v in expansions.values():
            if isinstance(v, list):
                expansions = v
                break
    if isinstance(expansions, list):
        result = [q for q in expansions if isinstance(q, str) and len(q) > 5]
        logger.info(f"  [LLM call] Generated {len(result)} expansions: {result} "
                    f"({(time.perf_counter() - t1) * 1000:.0f}ms, "
                    f"tokens={resp.usage.total_tokens if resp.usage else '?'})")
        return result
    logger.warning("  [LLM call] Query expansion returned unexpected format")
    return []


_GUARDRAIL_PROMPT = """Determine if the following text is a valid job requirement or hiring request.

Respond with a single JSON object with keys "valid" (bool) and "reason" (str).

Text: {query}

JSON:"""


def guardrail_check(query: str) -> tuple[bool, str]:
    logger.info("  [LLM call] Checking if query is a valid job requirement")
    client = _get_client()
    model = get_openai_llm_model()
    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _GUARDRAIL_PROMPT.format(query=query)}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    result = json.loads(resp.choices[0].message.content)
    logger.info(f"  [LLM call] Guardrail result: valid={result['valid']}, "
                f"reason=\"{result.get('reason', '')}\" "
                f"({(time.perf_counter() - t1) * 1000:.0f}ms, "
                f"tokens={resp.usage.total_tokens if resp.usage else '?'})")
    return result["valid"], result.get("reason", "")


def extract_requirements(query: str) -> dict:
    logger.info("  [LLM call] Extracting structured requirements from query")
    client = _get_client()
    model = get_openai_llm_model()
    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": _EXTRACT_PROMPT.format(query=query)}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(resp.choices[0].message.content)
    logger.info(f"  [LLM call] Extraction complete: skills={parsed.get('skills')}, "
                f"seniority={parsed.get('seniority')}, category={parsed.get('category')} "
                f"({(time.perf_counter() - t1) * 1000:.0f}ms, "
                f"tokens={resp.usage.total_tokens if resp.usage else '?'})")

    return {
        "skills": parsed.get("skills", []),
        "seniority": parsed.get("seniority", "any"),
        "category": parsed.get("category", "UNKNOWN"),
        "must_have": parsed.get("must_have", []),
        "nice_to_have": parsed.get("nice_to_have", []),
        "years_experience": parsed.get("years_experience", None),
        "original_query": query,
    }


def build_search_text(requirements: dict) -> str:
    seen = set()
    parts = []
    for lst in ("must_have", "skills", "nice_to_have"):
        for item in requirements.get(lst, []):
            lower = item.lower()
            if lower not in seen:
                seen.add(lower)
                parts.append(item)
    return " ".join(parts) if parts else requirements["original_query"]
