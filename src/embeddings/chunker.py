CHUNK_TYPES = {
    "header": "header",
    "summary": "summary",
    "experience": "experience",
    "education": "education",
    "skills": "skills",
    "projects": "projects",
    "certifications": "certifications",
    "other": "other",
}


def chunk_resume(candidate: dict) -> list[dict]:
    chunks = []
    sections = candidate.get("sections", {})
    candidate_id = candidate["id"]

    if not sections:
        full = candidate.get("clean_text", "")
        if full:
            chunks.append({
                "candidate_id": candidate_id,
                "chunk_id": f"{candidate_id}_full",
                "chunk_type": "full",
                "text": full,
                "order": 0,
            })
        return chunks

    order = 0
    for section_type, section_text in sections.items():
        st = section_type.strip().lower()
        norm_type = CHUNK_TYPES.get(st, "other")
        text = section_text.strip()
        if text:
            chunks.append({
                "candidate_id": candidate_id,
                "chunk_id": f"{candidate_id}_{norm_type}",
                "chunk_type": norm_type,
                "text": text,
                "order": order,
            })
            order += 1

    full_text = candidate.get("clean_text", "")
    if full_text:
        chunks.append({
            "candidate_id": candidate_id,
            "chunk_id": f"{candidate_id}_full",
            "chunk_type": "full",
            "text": full_text,
            "order": order,
        })

    return chunks


def chunk_all_resumes(candidates: list[dict]) -> list[dict]:
    all_chunks = []
    for c in candidates:
        all_chunks.extend(chunk_resume(c))
    return all_chunks
