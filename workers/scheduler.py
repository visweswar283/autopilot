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
from apply_bot import main as run_apply_bot_main
from config import SCRAPER_INTERVAL_HOURS

APPLY_INTERVAL_HOURS = int(os.getenv("APPLY_INTERVAL_HOURS", "4"))


def run_pipeline_sync():
    """APScheduler requires a sync function."""
    asyncio.run(run_pipeline())


def run_apply_bot_sync():
    """Run the apply bot for all active users (sync wrapper)."""
    asyncio.run(run_apply_bot_main())


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

    logger.info(f"Scheduler started — scraping every {SCRAPER_INTERVAL_HOURS}h, applying every {APPLY_INTERVAL_HOURS}h")
    logger.info("Running first scrape + apply immediately on startup...")

    run_pipeline_sync()
    run_apply_bot_sync()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
