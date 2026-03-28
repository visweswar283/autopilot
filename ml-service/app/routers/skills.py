"""
Skill extraction using two models:
  1. spaCy — extracts skills/titles from resume text
  2. JobBERT — extracts skills from job descriptions (NER)
"""
import re
from fastapi import APIRouter
from loguru import logger

from app.schemas import SkillsRequest, SkillsResponse, ResumeParseRequest, ResumeParseResponse
from app.models.loader import ModelRegistry

router = APIRouter()

# Curated tech skill dictionary for matching
TECH_SKILLS = {
    # Languages
    "python", "go", "golang", "java", "javascript", "typescript", "rust", "c++", "c#",
    "ruby", "scala", "kotlin", "swift", "r", "matlab", "bash", "shell",
    # Frontend
    "react", "next.js", "vue", "angular", "tailwind", "html", "css", "webpack",
    # Backend
    "django", "fastapi", "flask", "gin", "fiber", "spring", "node.js", "express",
    "graphql", "rest", "grpc", "microservices",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "dynamodb", "sqlite", "bigquery", "snowflake",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "ci/cd", "github actions", "jenkins", "helm", "airflow",
    # ML/AI
    "machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn",
    "nlp", "computer vision", "llm", "transformers", "pandas", "numpy",
    # Other
    "kafka", "rabbitmq", "celery", "spark", "hadoop", "git", "linux",
    "system design", "distributed systems", "data structures", "algorithms",
}

EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*years?\s+of\s+experience",
    r"(\d+)\+?\s*years?\s+experience",
    r"experience\s+of\s+(\d+)\+?\s*years?",
]

EDUCATION_KEYWORDS = [
    "bachelor", "master", "phd", "b.s.", "m.s.", "b.e.", "m.e.",
    "computer science", "software engineering", "information technology",
    "electrical engineering", "mathematics", "statistics",
]


@router.post("/extract-skills", response_model=SkillsResponse)
async def extract_skills(req: SkillsRequest) -> SkillsResponse:
    """Extract skills from any text using JobBERT + dictionary matching."""
    registry = ModelRegistry.get()
    skills = _extract_with_jobbert(registry, req.text)
    skills += _extract_with_dictionary(req.text)
    unique = sorted(set(s.lower() for s in skills if len(s) > 1))
    return SkillsResponse(skills=unique)


@router.post("/parse-resume", response_model=ResumeParseResponse)
async def parse_resume(req: ResumeParseRequest) -> ResumeParseResponse:
    """
    Full resume parser — extracts:
      - Skills (tech stack)
      - Years of experience
      - Job titles held
      - Education degrees
    """
    registry = ModelRegistry.get()
    text = req.text

    skills        = _extract_resume_skills(registry, text)
    exp_years     = _extract_experience_years(text)
    job_titles    = _extract_job_titles(registry, text)
    education     = _extract_education(text)

    logger.info(f"Resume parsed: {len(skills)} skills, {exp_years} yrs exp, {len(job_titles)} titles")

    return ResumeParseResponse(
        skills=skills,
        experience_years=exp_years,
        job_titles=job_titles,
        education=education,
    )


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _extract_with_jobbert(registry: ModelRegistry, text: str) -> list[str]:
    """Use JobBERT NER to find skill entities in text."""
    try:
        # Truncate to 512 tokens to stay within model limits
        truncated = text[:2000]
        entities = registry.jobbert(truncated)
        return [
            e["word"].strip()
            for e in entities
            if e.get("entity_group") in ("SKILL", "B-SKILL", "I-SKILL")
            and len(e["word"].strip()) > 1
        ]
    except Exception as e:
        logger.warning(f"JobBERT extraction failed: {e}")
        return []


def _extract_with_dictionary(text: str) -> list[str]:
    """Simple dictionary lookup for known tech skills."""
    text_lower = text.lower()
    return [skill for skill in TECH_SKILLS if skill in text_lower]


def _extract_resume_skills(registry: ModelRegistry, text: str) -> list[str]:
    skills = _extract_with_jobbert(registry, text)
    skills += _extract_with_dictionary(text)
    return sorted(set(s.lower() for s in skills if len(s) > 1))


def _extract_experience_years(text: str) -> int | None:
    for pattern in EXPERIENCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_job_titles(registry: ModelRegistry, text: str) -> list[str]:
    """Use spaCy NER to find job titles (PERSON → ORG heuristic)."""
    doc = registry.nlp(text[:5000])
    titles = []
    title_patterns = [
        "engineer", "developer", "architect", "manager", "lead",
        "scientist", "analyst", "designer", "director", "vp", "head of"
    ]
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if any(p in sent_text.lower() for p in title_patterns) and len(sent_text) < 80:
            titles.append(sent_text)
    return list(set(titles))[:10]


def _extract_education(text: str) -> list[str]:
    text_lower = text.lower()
    lines = text.split("\n")
    results = []
    for line in lines:
        if any(kw in line.lower() for kw in EDUCATION_KEYWORDS):
            clean = line.strip()
            if 5 < len(clean) < 150:
                results.append(clean)
    return list(set(results))[:5]
