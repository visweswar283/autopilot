"""
Scheduler — runs the scraping pipeline every N hours automatically.
No Airflow needed for solo use. APScheduler handles it.
"""
import asyncio
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from pipeline import run_pipeline
from config import SCRAPER_INTERVAL_HOURS


def run_pipeline_sync():
    """APScheduler requires a sync function."""
    asyncio.run(run_pipeline())


def main():
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        run_pipeline_sync,
        trigger=IntervalTrigger(hours=SCRAPER_INTERVAL_HOURS),
        id="scraping_pipeline",
        name="Job Scraping Pipeline",
        replace_existing=True,
        max_instances=1,         # never run two scrapes at once
    )

    logger.info(f"Scheduler started — pipeline runs every {SCRAPER_INTERVAL_HOURS} hour(s)")
    logger.info("Running first scrape immediately on startup...")

    # Run once immediately on startup, then on schedule
    run_pipeline_sync()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
