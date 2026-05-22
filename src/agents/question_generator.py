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
    return _client


_QUESTIONS_PROMPT = """You are an expert technical interviewer. Based on the candidate's profile below, generate {num_questions} interview questions.

Requirements:
- At least 5 must be HR/behavioral questions (type="hr")
- The remaining must be technical/skill-based questions (type="technical")
- Questions should be relevant to the candidate's skills, experience, and role
- Each question should be specific to this candidate (not generic)

Candidate Profile:
Skills: {skills}
Years of Experience: {years_experience}
Role: {role_category}
Resume Sections:
{resume_sections}

Return ONLY a JSON object with this structure:
{{
  "questions": [
    {{
      "type": "hr",
      "question": "Tell me about a time you resolved a conflict in your team."
    }},
    {{
      "type": "technical",
      "question": "Explain how you would design a scalable API for a high-traffic application."
    }}
  ]
}}
"""


def generate_questions(candidate: dict, num_questions: int = 12) -> dict:
    client = _get_client()
    model = get_openai_llm_model()

    skills = ", ".join(candidate.get("skills", []) or [])
    years = candidate.get("years_experience", "N/A")
    role = candidate.get("role_category", "N/A")

    sections = candidate.get("sections", {})
    resume_lines = []
    for sec_name in ["summary", "experience", "skills", "projects", "education", "certifications"]:
        content = sections.get(sec_name, "")
        if content:
            resume_lines.append(f"--- {sec_name.title()} ---\n{content[:800]}")
    resume_text = "\n\n".join(resume_lines) if resume_lines else (candidate.get("clean_text", "")[:2000])

    prompt = _QUESTIONS_PROMPT.format(
        num_questions=num_questions,
        skills=skills or "Not specified",
        years_experience=years if years is not None else "Not specified",
        role_category=role or "Not specified",
        resume_sections=resume_text,
    )

    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    llm_time = time.perf_counter() - t1
    usage = resp.usage
    logger.info(f"  [LLM] Questions generated in {llm_time:.2f}s"
                f"{f' (prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens})' if usage else ''}")

    raw = json.loads(resp.choices[0].message.content)
    questions = raw.get("questions", []) if isinstance(raw, dict) else []

    hr_qs = [q["question"] for q in questions if q.get("type") == "hr"]
    tech_qs = [q["question"] for q in questions if q.get("type") == "technical"]

    logger.info(f"  Generated {len(hr_qs)} HR + {len(tech_qs)} technical questions")

    return {
        "hr_questions": hr_qs,
        "technical_questions": tech_qs,
        "total": len(hr_qs) + len(tech_qs),
    }
