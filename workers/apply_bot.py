"""
Apply Bot Orchestrator
Fetches approved/pending jobs from DB, loads user profiles, and applies using
the correct ATS adapter for each portal.
"""
import asyncio
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from adapters import (
    JobInfo, UserProfile, ApplicationResult, ApplyResult,
    LinkedInAdapter, WorkdayAdapter, GreenhouseAdapter, LeverAdapter,
)
from browser.session_manager import SessionManager
from db import get_pending_jobs, mark_application

# Map portal identifier → adapter class
ADAPTER_MAP = {
    "linkedin":   LinkedInAdapter,
    "workday":    WorkdayAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever":      LeverAdapter,
}

# Portals where we detect the ATS from the URL
ATS_URL_HINTS = {
    "workday":    ["myworkdayjobs.com", "wd1.myworkday", "wd3.myworkday", "wd5.myworkday"],
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io/job"],
    "lever":      ["jobs.lever.co"],
    "linkedin":   ["linkedin.com/jobs"],
}


def detect_portal(url: str) -> Optional[str]:
    """Infer the ATS from the apply URL."""
    url_lower = url.lower()
    for portal, hints in ATS_URL_HINTS.items():
        if any(h in url_lower for h in hints):
            return portal
    return None


async def load_user_profile(user: dict) -> Optional[UserProfile]:
    """
    Build a UserProfile from user data dict (from DB row).
    Returns None if essential fields are missing.
    """
    resume_path = user.get("resume_path", "")
    if not resume_path or not Path(resume_path).exists():
        logger.warning(f"No valid resume for user {user.get('id')} — skipping")
        return None

    return UserProfile(
        user_id          = str(user["id"]),
        full_name        = user.get("full_name", ""),
        email            = user.get("email", ""),
        phone            = user.get("phone", ""),
        location         = user.get("location", ""),
        linkedin_url     = user.get("linkedin_url", ""),
        github_url       = user.get("github_url", ""),
        resume_path      = resume_path,
        skills           = user.get("skills", []),
        experience_years = user.get("experience_years"),
    )


async def run_apply_bot(
    users: list[dict],
    max_per_user: int = 20,
    headless: bool = True,
):
    """
    Main entry point. Iterates over all users, fetches their approved jobs,
    and applies using the appropriate adapter.

    Args:
        users:        List of user dicts from DB (id, email, full_name, etc.)
        max_per_user: Maximum applications to submit per user per run.
        headless:     Run browser in headless mode.
    """
    session_manager = SessionManager(headless=headless)
    await session_manager.start()

    try:
        for user in users:
            await _apply_for_user(user, session_manager, max_per_user)
    finally:
        await session_manager.stop()


async def _apply_for_user(
    user: dict,
    session_manager: SessionManager,
    max_per_user: int,
):
    """Process all pending jobs for one user."""
    profile = await load_user_profile(user)
    if not profile:
        return

    user_id = str(user["id"])
    jobs    = await get_pending_jobs(user_id, limit=max_per_user)

    if not jobs:
        logger.info(f"No pending jobs for user {user_id}")
        return

    logger.info(f"Applying to {len(jobs)} jobs for user {user_id}")
    applied = 0

    for job_row in jobs:
        job = JobInfo(
            id        = str(job_row["id"]),
            title     = job_row.get("title", ""),
            company   = job_row.get("company", ""),
            apply_url = job_row.get("apply_url", ""),
            portal    = job_row.get("portal", ""),
            location  = job_row.get("location", ""),
        )

        # Determine portal if not stored
        portal = job.portal or detect_portal(job.apply_url)
        if not portal:
            logger.warning(f"Unknown portal for job {job.id} ({job.apply_url}) — skipping")
            await mark_application(user_id, job.id, "unsupported", "Unknown ATS portal")
            continue

        adapter_cls = ADAPTER_MAP.get(portal)
        if not adapter_cls:
            logger.warning(f"No adapter for portal '{portal}' — skipping job {job.id}")
            await mark_application(user_id, job.id, "unsupported", f"No adapter for {portal}")
            continue

        adapter = adapter_cls(session_manager)
        logger.info(f"Applying to '{job.title}' @ {job.company} via {portal}")

        try:
            result: ApplicationResult = await adapter.apply(job, profile)
            status  = result.status.value
            message = result.message

            await mark_application(user_id, job.id, status, message)

            if result.status == ApplyResult.SUCCESS:
                applied += 1
                logger.success(f"[{applied}/{max_per_user}] Applied: {job.title} @ {job.company}")
            elif result.status == ApplyResult.CAPTCHA:
                logger.warning(f"CAPTCHA hit on {job.title} @ {job.company} — pausing 60s")
                await asyncio.sleep(60)
            elif result.status == ApplyResult.ALREADY_APPLIED:
                logger.info(f"Already applied: {job.title} @ {job.company}")
            else:
                logger.error(f"Failed: {job.title} @ {job.company} — {message}")

        except Exception as e:
            logger.error(f"Unexpected error applying to {job.title}: {e}")
            await mark_application(user_id, job.id, "failed", str(e))

        # Polite delay between applications to avoid rate-limiting
        await asyncio.sleep(_inter_apply_delay())

    logger.info(f"Done for user {user_id}: {applied} applications submitted")


def _inter_apply_delay() -> float:
    """Random delay (seconds) between applications."""
    import random
    return random.uniform(8, 18)


# ---------------------------------------------------------------------------
# Standalone runner (called by scheduler or CLI)
# ---------------------------------------------------------------------------

async def main():
    """Fetch all active users from DB and run apply bot."""
    from db import get_active_users
    users = await get_active_users()
    if not users:
        logger.info("No active users — nothing to apply")
        return
    await run_apply_bot(users, max_per_user=int(os.getenv("MAX_APPLIES_PER_USER", "20")))


if __name__ == "__main__":
    asyncio.run(main())
