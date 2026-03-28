"""
Job scoring using sentence-transformers.

Flow:
  1. Encode resume text → 384-dim embedding
  2. Encode JD text     → 384-dim embedding
  3. Cosine similarity  → raw score (0.0–1.0) → scaled to 0–100
  4. Extract skills from both texts
  5. Return: score + matched_skills + missing_skills + summary
"""
from fastapi import APIRouter
from sentence_transformers import util
from loguru import logger

from app.schemas import ScoreRequest, ScoreResponse
from app.models.loader import ModelRegistry
from app.routers.skills import (
    _extract_resume_skills,
    _extract_with_dictionary,
    _extract_with_jobbert,
)

router = APIRouter()


@router.post("/score", response_model=ScoreResponse)
async def score_job(req: ScoreRequest) -> ScoreResponse:
    """
    Score how well a resume matches a job description.
    Returns 0–100 score + matched/missing skills.
    """
    registry = ModelRegistry.get()

    # Step 1: Semantic similarity via sentence-transformers
    embeddings = registry.similarity_model.encode(
        [req.resume_text, req.jd_text],
        convert_to_tensor=True,
        show_progress_bar=False,
    )
    raw_score = float(util.cos_sim(embeddings[0], embeddings[1]))

    # Scale cosine similarity (typically 0.2–0.9) to a friendlier 0–100 range
    score = _scale_score(raw_score)

    # Step 2: Skill matching
    resume_skills = set(_extract_resume_skills(registry, req.resume_text))
    jd_skills     = set(
        s.lower() for s in
        _extract_with_jobbert(registry, req.jd_text) +
        _extract_with_dictionary(req.jd_text)
    )

    matched_skills  = sorted(resume_skills & jd_skills)
    missing_skills  = sorted(jd_skills - resume_skills)

    # Boost score slightly if strong skill overlap
    if jd_skills:
        skill_overlap_ratio = len(matched_skills) / len(jd_skills)
        score = min(100.0, score + skill_overlap_ratio * 10)

    summary = _build_summary(score, matched_skills, missing_skills)

    logger.info(f"Score: {score:.1f} | Matched: {len(matched_skills)} | Missing: {len(missing_skills)}")

    return ScoreResponse(
        score=round(score, 1),
        matched_skills=matched_skills[:20],
        missing_skills=missing_skills[:10],
        summary=summary,
    )


def _scale_score(cosine: float) -> float:
    """
    Map cosine similarity to 0–100.
    Cosine of 0.3 (poor match) → ~30
    Cosine of 0.7 (great match) → ~90
    """
    # Clamp to [0, 1]
    cosine = max(0.0, min(1.0, cosine))
    # Linear scale: (cosine - 0.2) / 0.7 * 100
    scaled = (cosine - 0.2) / 0.7 * 100
    return max(0.0, min(100.0, scaled))


def _build_summary(score: float, matched: list[str], missing: list[str]) -> str:
    if score >= 85:
        strength = "Excellent match"
    elif score >= 70:
        strength = "Good match"
    elif score >= 55:
        strength = "Moderate match"
    else:
        strength = "Weak match"

    parts = [f"{strength} ({score:.0f}/100)."]
    if matched:
        parts.append(f"You have {len(matched)} matching skills: {', '.join(matched[:5])}.")
    if missing:
        parts.append(f"Missing: {', '.join(missing[:5])}.")
    return " ".join(parts)
