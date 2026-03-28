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


def get_pending_jobs(limit: int = 100) -> list[dict]:
    """Fetch jobs that have not been applied to yet."""
    sql = """
        SELECT j.id, j.title, j.company, j.apply_url, j.portal,
               j.location, j.remote, j.salary_min, j.salary_max
        FROM jobs j
        WHERE j.id NOT IN (
            SELECT job_id FROM applications
        )
        ORDER BY j.scraped_at DESC
        LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(row) for row in cur.fetchall()]
