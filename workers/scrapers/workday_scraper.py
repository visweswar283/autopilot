import asyncio
import json
import re
from datetime import date
from playwright.async_api import async_playwright, BrowserContext
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from scrapers.base import BaseScraper, JobListing
from config import WORKDAY_COMPANIES, MAX_JOBS_PER_SEARCH, HEADLESS


class WorkdayScraper(BaseScraper):
    """
    Scrapes Workday ATS career portals directly.
    Workday has a standardized URL structure — one scraper works for ALL Workday companies.

    URL pattern: https://{company}.wd5.myworkdayjobs.com/en-US/{portal}
    """

    async def scrape(self) -> list[JobListing]:
        jobs: list[JobListing] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
            )

            for company_name, subdomain, portal in WORKDAY_COMPANIES:
                for role in self.roles:
                    self.log(f"Searching {company_name} Workday for: '{role}'")
                    try:
                        found = await self._search_company(context, company_name, subdomain, portal, role)
                        jobs.extend(found)
                        self.log(f"Found {len(found)} jobs at {company_name}")
                    except Exception as e:
                        logger.error(f"Workday scrape failed for {company_name}: {e}")
                    await asyncio.sleep(2)

            await browser.close()

        # Deduplicate within this run
        seen = set()
        unique = []
        for job in jobs:
            if job.external_id not in seen:
                seen.add(job.external_id)
                unique.append(job)

        self.log(f"Total unique Workday jobs: {len(unique)}")
        return unique

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=3, max=10))
    async def _search_company(
        self,
        context: BrowserContext,
        company_name: str,
        subdomain: str,
        portal: str,
        role: str,
    ) -> list[JobListing]:
        page = await context.new_page()
        jobs = []

        try:
            url = f"https://{subdomain}.wd5.myworkdayjobs.com/en-US/{portal}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Try to use Workday's search box
            search_box = await page.query_selector(
                'input[data-automation-id="searchBox"], input[placeholder*="Search"], input[aria-label*="Search"]'
            )
            if search_box:
                await search_box.click()
                await search_box.fill(role)
                await asyncio.sleep(1)

                # Press Enter or click search button
                search_btn = await page.query_selector(
                    'button[data-automation-id="searchButton"], button[aria-label*="Search"]'
                )
                if search_btn:
                    await search_btn.click()
                else:
                    await search_box.press("Enter")

                await asyncio.sleep(3)

            # Scroll to load all results
            for _ in range(2):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1.5)

            # Extract job listings
            job_items = await page.query_selector_all(
                '[data-automation-id="jobTitle"], .css-1q2dra3, li[class*="job"]'
            )

            for item in job_items[:MAX_JOBS_PER_SEARCH]:
                try:
                    job = await self._parse_job_item(page, item, company_name, subdomain)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse Workday job item: {e}")

        finally:
            await page.close()

        return jobs

    async def _parse_job_item(self, page, item, company_name: str, subdomain: str) -> JobListing | None:
        try:
            # Get job title
            title_el = await item.query_selector('a[data-automation-id="jobTitle"], a')
            if not title_el:
                title_text = (await item.inner_text()).strip()
                href = None
            else:
                title_text = (await title_el.inner_text()).strip()
                href = await title_el.get_attribute("href")

            if not title_text or not self._is_relevant(title_text):
                return None

            # Build job URL and extract ID
            if href:
                job_url = f"https://{subdomain}.wd5.myworkdayjobs.com{href}" if href.startswith("/") else href
                # Extract job ID from URL path
                match = re.search(r"/job/([^/]+)/", href)
                external_id = match.group(1) if match else href.split("/")[-1]
            else:
                return None

            # Get location from nearby element
            location_el = await item.query_selector(
                '[data-automation-id="locations"], .css-129m7dg, [class*="location"]'
            )
            location = (await location_el.inner_text()).strip() if location_el else "Unknown"

            is_remote = any(w in location.lower() for w in ["remote", "anywhere", "virtual"])

            return JobListing(
                portal="workday",
                external_id=f"{subdomain}_{external_id}",
                title=title_text,
                company=company_name,
                location=location,
                apply_url=job_url,
                remote=is_remote,
                posted_at=date.today(),
                raw_data={"subdomain": subdomain},
            )

        except Exception as e:
            logger.debug(f"Workday parse error: {e}")
            return None
