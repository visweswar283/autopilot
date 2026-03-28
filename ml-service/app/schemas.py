from pydantic import BaseModel
from typing import Optional


class ScoreRequest(BaseModel):
    resume_text: str
    jd_text:     str


class ScoreResponse(BaseModel):
    score:           float        # 0–100
    matched_skills:  list[str]
    missing_skills:  list[str]
    summary:         str


class SkillsRequest(BaseModel):
    text: str


class SkillsResponse(BaseModel):
    skills: list[str]


class ResumeParseRequest(BaseModel):
    text: str


class ResumeParseResponse(BaseModel):
    skills:       list[str]
    experience_years: Optional[int]
    job_titles:   list[str]
    education:    list[str]
