import re
from bs4 import BeautifulSoup
from src.ingestion.skill_dict import extract_skills_hybrid


_UNICODE_CLEAN = re.compile(r"[^\x00-\x7F]+")


def clean_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = _UNICODE_CLEAN.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


_SECTION_KEYWORDS = {
    "skills": ["skill", "technical", "competenc", "expertise", "proficien"],
    "experience": ["experience", "work history", "employment", "professional background", "career"],
    "education": ["education", "academic", "degree", "university", "college", "school", "qualification"],
    "projects": ["project", "portfolio"],
    "certifications": ["certif", "license"],
    "summary": ["summary", "profile", "objective", "about"],
}


def extract_sections(text: str) -> dict[str, str]:
    lines = text.split("\n")
    sections: dict[str, str] = {}
    current_section = "header"
    current_lines: list[str] = []

    def flush():
        nonlocal current_section, current_lines
        body = "\n".join(current_lines).strip()
        if body:
            sections.setdefault(current_section, "")
            sections[current_section] += body + "\n"
        current_lines = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        matched = None
        for sec_name, keywords in _SECTION_KEYWORDS.items():
            for kw in keywords:
                if lower.startswith(kw) or lower == kw or f" {kw}" in lower:
                    matched = sec_name
                    break
            if matched:
                break

        if matched:
            flush()
            current_section = matched
        elif stripped:
            current_lines.append(stripped)
        else:
            current_lines.append("")

    flush()
    return {k: v.strip() for k, v in sections.items() if v.strip()}


def extract_section_skills(sections: dict[str, str], full_text: str) -> list[str]:
    skills_section = sections.get("skills", "")
    if skills_section:
        return extract_skills_hybrid(skills_section, skills_section)
    return extract_skills_hybrid(full_text)


def extract_years_of_experience(text: str) -> int | None:
    patterns = [
        r"(?:over|more than|about|around|~)?\s*(\d{1,2})\+?\s*(?:years?\s*(?:of)?\s*experience)",
        r"(\d{1,2})\+?\s*years?\s*(?:of\s*)?experience",
        r"experience\s*(?:of|:)?\s*(\d{1,2})\+?\s*(?:years?|yrs)",
        r"(\d{1,2})\s*\+\s*years?\s+experience",
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            nums = [int(m) for m in matches if m.isdigit()]
            if nums:
                return max(nums)
    return None


def extract_role_category(text: str) -> str | None:
    roles = [
        "software engineer", "data scientist", "product manager", "designer",
        "developer", "engineer", "analyst", "consultant", "manager",
        "director", "specialist", "associate", "coordinator", "lead",
        "architect", "administrator", "executive", "intern",
    ]
    found = []
    for role in roles:
        if re.search(rf"\b{re.escape(role)}\b", text, re.IGNORECASE):
            found.append(role.title())
    return ", ".join(found[:3]) if found else None


def parse_resume(csv_row: list[str]) -> dict | None:
    if len(csv_row) < 4:
        return None

    resume_id = csv_row[0].strip()
    resume_str = csv_row[1].strip() if len(csv_row) > 1 else ""
    resume_html = csv_row[2].strip() if len(csv_row) > 2 else ""
    category = csv_row[3].strip().upper() if len(csv_row) > 3 else "UNKNOWN"

    if not resume_html and not resume_str:
        return None

    clean_text = clean_html_to_text(resume_html) if resume_html else resume_str

    sections = extract_sections(clean_text)
    skills = extract_section_skills(sections, clean_text)
    experience_years = extract_years_of_experience(clean_text)
    role_category = extract_role_category(clean_text)

    return {
        "id": resume_id,
        "category": category,
        "clean_text": clean_text,
        "sections": sections,
        "skills": skills,
        "years_experience": experience_years,
        "role_category": role_category,
        "char_count": len(clean_text),
    }
