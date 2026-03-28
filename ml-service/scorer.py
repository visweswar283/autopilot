"""
Standalone scorer — called by the scraping pipeline after jobs are saved.
Scores each new job against the user's resume and stores result in user_job_scores.
"""
import os
import httpx
import psycopg2
import psycopg2.extras
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL  = os.environ["DATABASE_URL"]
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")


def get_user_resume(user_id: str) -> str | None:
    """Fetch the default resume text for a user from DB."""
    sql = """
        SELECT r.s3_key FROM resumes r
        WHERE r.user_id = %s AND r.is_default = true
        LIMIT 1
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return row[0] if row else None


def get_unscored_jobs(user_id: str, limit: int = 50) -> list[dict]:
    """Get jobs not yet scored for this user."""
    sql = """
        SELECT j.id, j.title, j.company, j.description, j.portal
        FROM jobs j
        WHERE j.id NOT IN (
            SELECT job_id FROM user_job_scores WHERE user_id = %s
        )
        ORDER BY j.scraped_at DESC
        LIMIT %s
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, limit))
            return [dict(row) for row in cur.fetchall()]


def save_score(user_id: str, job_id: str, score: float):
    """Save score to user_job_scores table."""
    sql = """
        INSERT INTO user_job_scores (user_id, job_id, score, status)
        VALUES (%s, %s, %s, 'new')
        ON CONFLICT (user_id, job_id) DO UPDATE SET score = EXCLUDED.score
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, job_id, score))
        conn.commit()


def score_jobs_for_user(user_id: str, resume_text: str):
    """Score all unscored jobs for a user against their resume."""
    jobs = get_unscored_jobs(user_id)
    if not jobs:
        logger.info(f"No new jobs to score for user {user_id}")
        return

    logger.info(f"Scoring {len(jobs)} jobs for user {user_id}...")
    scored = 0

    for job in jobs:
        jd_text = f"{job['title']} at {job['company']}\n{job.get('description', '')}"
        try:
            resp = httpx.post(
                f"{ML_SERVICE_URL}/score",
                json={"resume_text": resume_text, "jd_text": jd_text},
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
            score  = result["score"]
            save_score(user_id, str(job["id"]), score)
            scored += 1
            logger.debug(f"{job['title']} @ {job['company']} → {score:.1f}")
        except Exception as e:
            logger.error(f"Failed to score job {job['id']}: {e}")

    logger.info(f"Scored {scored}/{len(jobs)} jobs for user {user_id}")
