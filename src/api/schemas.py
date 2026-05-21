from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    expand_queries: bool = True


class ScoredCandidate(BaseModel):
    id: str
    overall_score: float
    skill_score: float
    experience_score: float
    justification: str
    email_subject: str = ""
    email_body: str = ""
    category: str
    skills: list[str]
    years_experience: int | None
    role_category: str


class Requirements(BaseModel):
    skills: list[str]
    seniority: str
    category: str
    must_have: list[str]
    nice_to_have: list[str]
    years_experience: int | None
    original_query: str


class SearchResponse(BaseModel):
    query: str
    requirements: Requirements
    results: list[ScoredCandidate]


class IngestResponse(BaseModel):
    status: str
    candidates_parsed: int
    candidates_indexed: int
    message: str


class CandidateDetail(BaseModel):
    id: str
    category: str
    skills: list[str]
    years_experience: int | None
    role_category: str | None
    char_count: int
    sections: dict[str, str]
    clean_text: str
