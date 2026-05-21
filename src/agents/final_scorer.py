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
        logger.debug("OpenAI scoring client initialized")
    return _client


_SCORE_PROMPT = """You are a hiring expert evaluating candidate-job fit.

Job requirement: {query}

Rank these candidates and provide a score (0-100), justification, and a shortlist email for each.

For each candidate evaluate:
1. Skill match: How well their skills match the requirements
2. Experience fit: Years and relevance of experience
3. Overall suitability: Combined assessment

Return ONLY a JSON array with objects:
[
  {{
    "candidate_id": "...",
    "overall_score": 0-100,
    "skill_score": 0-100,
    "experience_score": 0-100,
    "justification": "2-3 sentence explanation of why they fit",
    "email_subject": "Shortlist email subject line (max 10 words)",
    "email_body": "Professional email body (3-4 sentences) informing the candidate they are shortlisted for the interview, mention how their skills/experience matched the role, and that interview details will follow soon."
  }}
]

Candidates:
{candidates}
"""


def score_candidates(query: str, candidates: list[dict]) -> list[dict]:
    client = _get_client()
    model = get_openai_llm_model()

    logger.info(f"  [LLM call] Scoring {len(candidates)} candidates with GPT")
    logger.debug(f"  LLM model: {model}")

    profile_lines = []
    for c in candidates:
        skills = ", ".join(c.get("skills", []) or [])
        years = c.get("years_experience", "N/A")
        role = c.get("role_category", "N/A")
        text = (c.get("text_preview", "") or "")[:500]
        profile_lines.append(
            f"Candidate {c['id']}:\n"
            f"  Skills: {skills}\n"
            f"  Years Exp: {years}\n"
            f"  Role: {role}\n"
            f"  Resume excerpt: {text}\n"
        )

    candidates_text = "\n".join(profile_lines)
    prompt = _SCORE_PROMPT.format(query=query, candidates=candidates_text)

    prompt_tokens = len(prompt) // 4
    logger.info(f"  [LLM call] Prompt size: ~{prompt_tokens} tokens")

    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    llm_time = time.perf_counter() - t1
    usage = resp.usage
    logger.info(f"  [LLM call] Scoring done in {llm_time:.2f}s"
                f"{f' (prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens})' if usage else ''}")

    raw = json.loads(resp.choices[0].message.content)

    if isinstance(raw, dict):
        for key in ("candidates", "results", "scores", "rankings"):
            if key in raw and isinstance(raw[key], list):
                raw = raw[key]
                break

    if isinstance(raw, dict):
        raw = list(raw.values())

    scores = [s for s in raw if isinstance(s, dict) and "candidate_id" in s]
    logger.info(f"  Parsed {len(scores)} score entries from LLM response")

    result_map = {s["candidate_id"]: s for s in scores}

    ranked = []
    for c in candidates:
        score_info = result_map.get(c["id"], {})
        ranked.append({
            "id": c["id"],
            "overall_score": score_info.get("overall_score", 0),
            "skill_score": score_info.get("skill_score", 0),
            "experience_score": score_info.get("experience_score", 0),
            "justification": score_info.get("justification", ""),
            "email_subject": score_info.get("email_subject", ""),
            "email_body": score_info.get("email_body", ""),
            "category": c.get("category", ""),
            "skills": c.get("skills", []),
            "years_experience": c.get("years_experience", -1),
            "role_category": c.get("role_category", ""),
        })

    ranked.sort(key=lambda x: x["overall_score"], reverse=True)
    return ranked
