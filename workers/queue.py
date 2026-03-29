"""
Redis-backed per-user job queue with fair round-robin scheduling.

Queue layout in Redis:
  apply:queue:<user_id>   → Redis List  (LPUSH to add, BRPOP to consume)
  apply:processing        → Redis Hash  user_id → job_id (in-flight tracking)
  apply:users:active      → Redis Set   (all users that have pending work)
  apply:stats:<user_id>   → Redis Hash  applied/failed/captcha counts

Fair scheduling: worker iterates active users round-robin so one heavy user
never starves others.
"""
import json
import time
import redis
import os
from typing import Optional
from loguru import logger

REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_TTL   = 86400 * 3          # jobs expire from queue after 3 days
MAX_RETRIES = 3


def _redis() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Producer helpers (called by scheduler after scoring)
# ---------------------------------------------------------------------------

def enqueue_jobs(user_id: str, jobs: list[dict]) -> int:
    """
    Push a list of job dicts onto the user's apply queue.
    Skips jobs already in the queue (dedup by job_id).
    Returns number of jobs actually enqueued.
    """
    r     = _redis()
    key   = f"apply:queue:{user_id}"
    added = 0

    for job in jobs:
        payload = json.dumps({**job, "user_id": user_id, "retries": 0, "enqueued_at": time.time()})
        # Use a Set for dedup check alongside the List
        dedup_key = f"apply:queued:{user_id}:{job['id']}"
        if r.set(dedup_key, "1", ex=QUEUE_TTL, nx=True):
            r.lpush(key, payload)
            r.expire(key, QUEUE_TTL)
            added += 1

    if added:
        r.sadd("apply:users:active", user_id)
        logger.info(f"Enqueued {added} jobs for user {user_id}")

    return added


def queue_length(user_id: str) -> int:
    return _redis().llen(f"apply:queue:{user_id}")


def clear_queue(user_id: str):
    r = _redis()
    r.delete(f"apply:queue:{user_id}")
    r.srem("apply:users:active", user_id)
    logger.info(f"Cleared queue for user {user_id}")


# ---------------------------------------------------------------------------
# Consumer helpers (called by apply worker)
# ---------------------------------------------------------------------------

def get_active_users() -> list[str]:
    """Return all user IDs that currently have queued work."""
    r     = _redis()
    users = list(r.smembers("apply:users:active"))
    # Filter out users whose queues are actually empty
    active = [u for u in users if r.llen(f"apply:queue:{u}") > 0]
    # Clean up stale entries
    stale = set(users) - set(active)
    if stale:
        r.srem("apply:users:active", *stale)
    return active


def dequeue_job(user_id: str, timeout: int = 1) -> Optional[dict]:
    """
    Non-blocking pop of the next job for a user.
    Returns None if the queue is empty.
    """
    r      = _redis()
    result = r.brpop(f"apply:queue:{user_id}", timeout=timeout)
    if not result:
        return None
    _, payload = result
    return json.loads(payload)


def mark_in_flight(user_id: str, job_id: str):
    _redis().hset("apply:processing", user_id, job_id)


def clear_in_flight(user_id: str):
    _redis().hdel("apply:processing", user_id)


def requeue_job(job: dict):
    """Put a failed job back in the queue for retry (up to MAX_RETRIES)."""
    retries = job.get("retries", 0)
    if retries >= MAX_RETRIES:
        logger.warning(f"Job {job['id']} for user {job['user_id']} exhausted retries — dropping")
        return

    job["retries"] = retries + 1
    r   = _redis()
    key = f"apply:queue:{job['user_id']}"
    r.lpush(key, json.dumps(job))
    r.sadd("apply:users:active", job["user_id"])
    logger.debug(f"Requeued job {job['id']} (retry {job['retries']}/{MAX_RETRIES})")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def increment_stat(user_id: str, field: str):
    """Increment a counter in the user's stats hash (applied/failed/captcha)."""
    r = _redis()
    r.hincrby(f"apply:stats:{user_id}", field, 1)
    r.hincrby(f"apply:stats:{user_id}", "total", 1)


def get_stats(user_id: str) -> dict:
    r    = _redis()
    data = r.hgetall(f"apply:stats:{user_id}")
    return {k: int(v) for k, v in data.items()}


def get_all_stats() -> dict[str, dict]:
    r     = _redis()
    users = r.smembers("apply:users:active")
    return {u: get_stats(u) for u in users}
