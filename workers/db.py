import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from config import DATABASE_URL
from loguru import logger


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_job(job: dict) -> bool:
    """
    Insert a job into the global jobs table.
    Skips if fingerprint already exists (dedup).
    Returns True if inserted, False if duplicate.
    """
    sql = """
        INSERT INTO jobs (
            portal, external_id, title, company, location,
            remote, description, apply_url, salary_min, salary_max,
            posted_at, fingerprint, cross_portal_fingerprint, raw_data
        ) VALUES (
            %(portal)s, %(external_id)s, %(title)s, %(company)s, %(location)s,
            %(remote)s, %(description)s, %(apply_url)s, %(salary_min)s, %(salary_max)s,
            %(posted_at)s, %(fingerprint)s, %(cross_portal_fingerprint)s, %(raw_data)s
        )
        ON CONFLICT (fingerprint) DO NOTHING
        RETURNING id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, job)
            result = cur.fetchone()
            if result:
                logger.info(f"Inserted job: {job['title']} @ {job['company']}")
                return True
            else:
                logger.debug(f"Duplicate skipped: {job['title']} @ {job['company']}")
                return False


def get_pending_jobs(user_id: str, limit: int = 100) -> list[dict]:
    """
    Fetch jobs approved (score >= threshold) for a user that haven't been
    applied to yet. Ordered by ML score descending.
    """
    sql = """
        SELECT j.id, j.title, j.company, j.apply_url, j.portal,
               j.location, j.remote, j.salary_min, j.salary_max,
               ujs.score
        FROM jobs j
        JOIN user_job_scores ujs ON ujs.job_id = j.id AND ujs.user_id = %s
        WHERE ujs.score >= 60
          AND j.id NOT IN (
              SELECT job_id FROM applications WHERE user_id = %s
          )
        ORDER BY ujs.score DESC
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id, user_id, limit))
            return [dict(row) for row in cur.fetchall()]


def mark_application(user_id: str, job_id: str, status: str, message: str = "") -> None:
    """Record an application attempt in the applications table."""
    sql = """
        INSERT INTO applications (user_id, job_id, status, notes, applied_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (user_id, job_id) DO UPDATE
            SET status = EXCLUDED.status,
                notes  = EXCLUDED.notes,
                applied_at = NOW()
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, job_id, status, message))
    logger.debug(f"Marked application: user={user_id} job={job_id} status={status}")


def get_active_users() -> list[dict]:
    """
    Fetch all users who have auto_apply enabled, a resume uploaded,
    and an active profile.
    """
    sql = """
        SELECT u.id, u.email, u.full_name,
               p.phone, p.location, p.linkedin_url, p.github_url,
               p.experience_years, p.skills,
               r.local_path AS resume_path
        FROM users u
        JOIN profiles p   ON p.user_id = u.id
        JOIN resumes r    ON r.user_id = u.id AND r.is_primary = TRUE
        WHERE p.auto_apply = TRUE
          AND u.is_active  = TRUE
        ORDER BY u.created_at
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]
