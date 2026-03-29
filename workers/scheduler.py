"""
Scheduler — runs the scraping pipeline and apply bot on configurable intervals.
No Airflow needed for solo use. APScheduler handles it.

Schedule:
  - Scraping pipeline : every SCRAPER_INTERVAL_HOURS  (default 2h)
  - Apply bot         : every APPLY_INTERVAL_HOURS    (default 4h)
"""
import asyncio
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from pipeline import run_pipeline
from apply_worker import run_worker_pool
from config import SCRAPER_INTERVAL_HOURS

APPLY_INTERVAL_HOURS  = int(os.getenv("APPLY_INTERVAL_HOURS",  "4"))
DIGEST_HOUR_UTC       = int(os.getenv("DIGEST_HOUR_UTC",       "8"))   # 8 AM UTC daily digest


def run_pipeline_sync():
    """APScheduler requires a sync function."""
    asyncio.run(run_pipeline())


def run_apply_bot_sync():
    """Run the fair-queue worker pool for all active users."""
    asyncio.run(run_worker_pool())


def run_daily_digest_sync():
    """Send daily summary emails to all active users."""
    asyncio.run(_send_digests())


async def _send_digests():
    from db import get_active_users
    from notifier import send_daily_digest
    from queue import get_stats
    users = get_active_users()
    for u in users:
        stats = get_stats(str(u["id"]))
        if stats.get("total", 0) > 0:
            await send_daily_digest(str(u["id"]), u["email"], stats)


def main():
    scheduler = BlockingScheduler(timezone="UTC")

    # --- Scraping job ---
    scheduler.add_job(
        run_pipeline_sync,
        trigger=IntervalTrigger(hours=SCRAPER_INTERVAL_HOURS),
        id="scraping_pipeline",
        name="Job Scraping Pipeline",
        replace_existing=True,
        max_instances=1,
    )

    # --- Apply bot job ---
    scheduler.add_job(
        run_apply_bot_sync,
        trigger=IntervalTrigger(hours=APPLY_INTERVAL_HOURS),
        id="apply_bot",
        name="Apply Bot",
        replace_existing=True,
        max_instances=1,
    )

    # --- Daily digest email ---
    from apscheduler.triggers.cron import CronTrigger
    scheduler.add_job(
        run_daily_digest_sync,
        trigger=CronTrigger(hour=DIGEST_HOUR_UTC, minute=0),
        id="daily_digest",
        name="Daily Digest Email",
        replace_existing=True,
        max_instances=1,
    )

    logger.info(
        f"Scheduler started — scraping every {SCRAPER_INTERVAL_HOURS}h, "
        f"applying every {APPLY_INTERVAL_HOURS}h, "
        f"daily digest at {DIGEST_HOUR_UTC}:00 UTC"
    )
    logger.info("Running first scrape + apply immediately on startup...")

    run_pipeline_sync()
    run_apply_bot_sync()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
