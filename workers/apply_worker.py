"""
Apply Worker Pool — fair round-robin multi-user job applicator.

Architecture:
  - N concurrent workers, each pulling jobs round-robin from all active users
  - CAPTCHA → exponential backoff, then requeue
  - Failure  → requeue (up to MAX_RETRIES times)
  - Success  → notify user, record in DB

Run standalone:   python apply_worker.py
Run via scheduler: imported and called as asyncio task
"""
import asyncio
import os
import time
from loguru import logger

from adapters import (
    JobInfo, UserProfile, ApplicationResult, ApplyResult,
    LinkedInAdapter, WorkdayAdapter, GreenhouseAdapter, LeverAdapter,
)
from browser.session_manager import SessionManager
from db import mark_application, get_active_users as db_get_active_users
from queue import (
    get_active_users, dequeue_job, mark_in_flight, clear_in_flight,
    requeue_job, increment_stat, queue_length,
)
from notifier import notify_application

WORKER_CONCURRENCY  = int(os.getenv("WORKER_CONCURRENCY", "3"))
CAPTCHA_BACKOFF_S   = int(os.getenv("CAPTCHA_BACKOFF_S",  "120"))  # 2 min pause on CAPTCHA
INTER_APPLY_MIN_S   = float(os.getenv("INTER_APPLY_MIN_S", "8"))
INTER_APPLY_MAX_S   = float(os.getenv("INTER_APPLY_MAX_S", "18"))

ADAPTER_MAP = {
    "linkedin":   LinkedInAdapter,
    "workday":    WorkdayAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever":      LeverAdapter,
}

ATS_URL_HINTS = {
    "workday":    ["myworkdayjobs.com", "wd1.myworkday", "wd3.myworkday", "wd5.myworkday"],
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io/job"],
    "lever":      ["jobs.lever.co"],
    "linkedin":   ["linkedin.com/jobs"],
}


def _detect_portal(url: str) -> str | None:
    url_lower = url.lower()
    for portal, hints in ATS_URL_HINTS.items():
        if any(h in url_lower for h in hints):
            return portal
    return None


def _build_profile(user: dict) -> UserProfile | None:
    from pathlib import Path
    resume = user.get("resume_path", "")
    if not resume or not Path(resume).exists():
        return None
    return UserProfile(
        user_id          = str(user["id"]),
        full_name        = user.get("full_name", ""),
        email            = user.get("email", ""),
        phone            = user.get("phone", ""),
        location         = user.get("location", ""),
        linkedin_url     = user.get("linkedin_url", ""),
        github_url       = user.get("github_url", ""),
        resume_path      = resume,
        skills           = user.get("skills", []),
        experience_years = user.get("experience_years"),
    )


# ---------------------------------------------------------------------------
# Single worker coroutine
# ---------------------------------------------------------------------------

async def _worker(worker_id: int, session_manager: SessionManager, user_profiles: dict[str, UserProfile]):
    """
    One worker: iterates active users round-robin, pops one job per user,
    applies, then moves on. Loops until all queues are empty.
    """
    import random
    logger.info(f"Worker-{worker_id} started")

    while True:
        active_users = get_active_users()
        if not active_users:
            logger.info(f"Worker-{worker_id}: no active users — sleeping 10s")
            await asyncio.sleep(10)
            continue

        processed_any = False

        for user_id in active_users:
            profile = user_profiles.get(user_id)
            if not profile:
                continue

            job = dequeue_job(user_id, timeout=0)
            if not job:
                continue

            processed_any = True
            mark_in_flight(user_id, job["id"])

            portal = job.get("portal") or _detect_portal(job.get("apply_url", ""))
            if not portal or portal not in ADAPTER_MAP:
                logger.warning(f"Worker-{worker_id}: no adapter for portal '{portal}' — skipping")
                clear_in_flight(user_id)
                await mark_application(user_id, job["id"], "unsupported", f"No adapter for {portal}")
                continue

            adapter = ADAPTER_MAP[portal](session_manager)
            job_info = JobInfo(
                id        = str(job["id"]),
                title     = job.get("title", ""),
                company   = job.get("company", ""),
                apply_url = job.get("apply_url", ""),
                portal    = portal,
                location  = job.get("location", ""),
            )

            try:
                result: ApplicationResult = await adapter.apply(job_info, profile)
                await _handle_result(worker_id, user_id, job, result)
            except Exception as e:
                logger.error(f"Worker-{worker_id}: exception applying {job['id']}: {e}")
                requeue_job(job)
                increment_stat(user_id, "failed")
            finally:
                clear_in_flight(user_id)

            # Polite delay between applies
            await asyncio.sleep(random.uniform(INTER_APPLY_MIN_S, INTER_APPLY_MAX_S))

        if not processed_any:
            await asyncio.sleep(5)


async def _handle_result(worker_id: int, user_id: str, job: dict, result: ApplicationResult):
    status  = result.status
    message = result.message

    if status == ApplyResult.SUCCESS:
        increment_stat(user_id, "applied")
        await mark_application(user_id, job["id"], "applied", message)
        logger.success(f"Worker-{worker_id}: applied → {job['title']} @ {job['company']}")
        await notify_application(user_id, job, status="applied")

    elif status == ApplyResult.ALREADY_APPLIED:
        await mark_application(user_id, job["id"], "already_applied", message)
        logger.info(f"Worker-{worker_id}: already applied → {job['title']}")

    elif status == ApplyResult.CAPTCHA:
        increment_stat(user_id, "captcha")
        logger.warning(f"Worker-{worker_id}: CAPTCHA on {job['title']} — backing off {CAPTCHA_BACKOFF_S}s")
        requeue_job(job)
        await asyncio.sleep(CAPTCHA_BACKOFF_S)

    elif status == ApplyResult.UNSUPPORTED:
        await mark_application(user_id, job["id"], "unsupported", message)
        logger.warning(f"Worker-{worker_id}: unsupported — {message}")

    else:  # FAILED
        increment_stat(user_id, "failed")
        requeue_job(job)
        await mark_application(user_id, job["id"], "failed", message)
        logger.error(f"Worker-{worker_id}: failed — {job['title']} @ {job['company']}: {message}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_worker_pool():
    """
    Start N concurrent workers sharing one browser session manager.
    Load all active user profiles once, then fan out across workers.
    """
    users = db_get_active_users()
    if not users:
        logger.info("No active users with auto-apply enabled")
        return

    # Build profile map once
    user_profiles: dict[str, UserProfile] = {}
    for u in users:
        p = _build_profile(u)
        if p:
            user_profiles[str(u["id"])] = p

    if not user_profiles:
        logger.info("No users with valid resumes")
        return

    # Enqueue pending jobs for all users
    from db import get_pending_jobs
    from queue import enqueue_jobs
    for user_id in user_profiles:
        jobs = get_pending_jobs(user_id, limit=50)
        if jobs:
            enqueue_jobs(user_id, jobs)

    session_manager = SessionManager(headless=True)
    await session_manager.start()

    try:
        workers = [
            asyncio.create_task(_worker(i, session_manager, user_profiles))
            for i in range(WORKER_CONCURRENCY)
        ]
        # Run workers until all queues are empty (or KeyboardInterrupt)
        await asyncio.gather(*workers, return_exceptions=True)
    finally:
        await session_manager.stop()


if __name__ == "__main__":
    asyncio.run(run_worker_pool())
