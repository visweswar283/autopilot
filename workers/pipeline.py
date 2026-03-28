"""
Scraping pipeline — runs all scrapers, saves results to DB, then triggers ML scoring.
Called by the scheduler every 2 hours.
"""
import asyncio
import json
import os
import httpx
from loguru import logger

from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.workday_scraper import WorkdayScraper
from scrapers.base import JobListing
from dedup import make_fingerprint, make_cross_portal_fingerprint
from db import upsert_job
from config import TARGET_ROLES, TARGET_LOCATIONS, HEADLESS

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml-service:8001")


async def run_pipeline():
    logger.info("=" * 50)
    logger.info("Scraping pipeline started")
    logger.info(f"Roles: {TARGET_ROLES}")
    logger.info(f"Locations: {TARGET_LOCATIONS}")
    logger.info("=" * 50)

    total_new = 0
    total_seen = 0

    scrapers = [
        LinkedInScraper(roles=TARGET_ROLES, locations=TARGET_LOCATIONS, headless=HEADLESS),
        WorkdayScraper(roles=TARGET_ROLES,  locations=TARGET_LOCATIONS, headless=HEADLESS),
    ]

    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__
        logger.info(f"Running {scraper_name}...")
        try:
            jobs: list[JobListing] = await scraper.scrape()
            new, seen = _save_jobs(jobs)
            total_new  += new
            total_seen += seen
            logger.info(f"{scraper_name}: {new} new, {seen} duplicates")
        except Exception as e:
            logger.error(f"{scraper_name} failed: {e}")

    logger.info(f"Pipeline complete — {total_new} new jobs saved, {total_seen} duplicates skipped")

    # Trigger ML scoring for new jobs
    if total_new > 0:
        await _trigger_scoring()

    return total_new


async def _trigger_scoring():
    """Notify ML service to score new jobs against all user resumes."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{ML_SERVICE_URL}/health")
            if resp.status_code == 200:
                logger.info("ML service is up — scoring will run automatically")
            else:
                logger.warning("ML service not responding — scoring skipped this run")
    except Exception as e:
        logger.warning(f"Could not reach ML service: {e} — scoring skipped")


def _save_jobs(jobs: list[JobListing]) -> tuple[int, int]:
    new = 0
    seen = 0
    for job in jobs:
        fp = make_fingerprint(job.portal, job.external_id)
        cross_fp = make_cross_portal_fingerprint(
            job.company, job.title, job.location, job.posted_at
        )
        record = {
            "portal":                    job.portal,
            "external_id":               job.external_id,
            "title":                     job.title,
            "company":                   job.company,
            "location":                  job.location,
            "remote":                    job.remote,
            "description":               job.description,
            "apply_url":                 job.apply_url,
            "salary_min":                job.salary_min,
            "salary_max":                job.salary_max,
            "posted_at":                 job.posted_at,
            "fingerprint":               fp,
            "cross_portal_fingerprint":  cross_fp,
            "raw_data":                  json.dumps(job.raw_data),
        }
        if upsert_job(record):
            new += 1
        else:
            seen += 1
    return new, seen


if __name__ == "__main__":
    asyncio.run(run_pipeline())
