import asyncio
import re
import json
from datetime import date, timedelta
from playwright.async_api import async_playwright, Page, BrowserContext
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from scrapers.base import BaseScraper, JobListing
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD, MAX_JOBS_PER_SEARCH, HEADLESS


class LinkedInScraper(BaseScraper):
    """
    Scrapes LinkedIn job listings using your account.
    Searches each (role, location) pair and collects job cards.
    """

    LOGIN_URL   = "https://www.linkedin.com/login"
    JOBS_URL    = "https://www.linkedin.com/jobs/search/"
    SESSION_KEY = "linkedin_cookies.json"

    async def scrape(self) -> list[JobListing]:
        jobs: list[JobListing] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await self._get_context(browser)

            for role in self.roles:
                for location in self.locations:
                    self.log(f"Searching: '{role}' in '{location}'")
                    try:
                        found = await self._search(context, role, location)
                        jobs.extend(found)
                        self.log(f"Found {len(found)} jobs for '{role}' in '{location}'")
                    except Exception as e:
                        logger.error(f"LinkedIn search failed for {role}/{location}: {e}")
                    await asyncio.sleep(2)  # polite delay between searches

            await browser.close()

        # Deduplicate by external_id within this run
        seen = set()
        unique = []
        for job in jobs:
            if job.external_id not in seen:
                seen.add(job.external_id)
                unique.append(job)

        self.log(f"Total unique jobs found: {len(unique)}")
        return unique

    async def _get_context(self, browser) -> BrowserContext:
        """Return an authenticated browser context."""
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        # Try restoring saved cookies
        try:
            with open(self.SESSION_KEY) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            self.log("Restored LinkedIn session from cookies")
        except FileNotFoundError:
            await self._login(context)

        return context

    async def _login(self, context: BrowserContext):
        """Log into LinkedIn and save session cookies."""
        if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")

        page = await context.new_page()
        await page.goto(self.LOGIN_URL, wait_until="networkidle")

        await page.fill("#username", LINKEDIN_EMAIL)
        await page.fill("#password", LINKEDIN_PASSWORD)
        await asyncio.sleep(1)
        await page.click('[type="submit"]')
        await page.wait_for_url("**/feed/**", timeout=15000)

        # Save cookies for next run
        cookies = await context.cookies()
        with open(self.SESSION_KEY, "w") as f:
            json.dump(cookies, f)

        self.log("LinkedIn login successful, session saved")
        await page.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _search(self, context: BrowserContext, role: str, location: str) -> list[JobListing]:
        page = await context.new_page()
        jobs = []

        try:
            # Build search URL with filters: Easy Apply + past 24h + relevant experience
            params = {
                "keywords": role,
                "location": location,
                "f_AL": "true",      # Easy Apply only
                "f_TPR": "r86400",   # Posted in last 24 hours
                "f_E": "3,4",        # Mid-senior + Senior level
                "sortBy": "DD",      # Most recent
            }
            query = "&".join(f"{k}={v}" for k, v in params.items())
            await page.goto(f"{self.JOBS_URL}?{query}", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Scroll to load more jobs
            await self._scroll_jobs_list(page)

            # Extract job cards
            job_cards = await page.query_selector_all(".job-card-container, .jobs-search-results__list-item")
            self.log(f"Found {len(job_cards)} job cards on page")

            for card in job_cards[:MAX_JOBS_PER_SEARCH]:
                try:
                    job = await self._parse_card(page, card, role, location)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Failed to parse card: {e}")

        finally:
            await page.close()

        return jobs

    async def _scroll_jobs_list(self, page: Page):
        """Scroll the job list panel to load more results."""
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(1.5)

    async def _parse_card(self, page: Page, card, role: str, location: str) -> JobListing | None:
        """Extract job info from a LinkedIn job card."""
        try:
            # Get job ID from data attribute
            job_id = await card.get_attribute("data-job-id") or await card.get_attribute("data-entity-urn") or ""
            job_id = re.sub(r"[^0-9]", "", job_id)
            if not job_id:
                return None

            # Extract title
            title_el = await card.query_selector(".job-card-list__title, .job-card-container__link")
            title = (await title_el.inner_text()).strip() if title_el else ""

            if not title or not self._is_relevant(title):
                return None

            # Extract company
            company_el = await card.query_selector(".job-card-container__company-name, .job-card-list__company-name")
            company = (await company_el.inner_text()).strip() if company_el else ""

            # Extract location
            loc_el = await card.query_selector(".job-card-container__metadata-item")
            job_location = (await loc_el.inner_text()).strip() if loc_el else location

            # Build apply URL
            apply_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

            is_remote = any(word in job_location.lower() for word in ["remote", "anywhere"])

            return JobListing(
                portal="linkedin",
                external_id=job_id,
                title=title,
                company=company,
                location=job_location,
                apply_url=apply_url,
                remote=is_remote,
                posted_at=date.today(),
                raw_data={"role_searched": role, "location_searched": location},
            )

        except Exception as e:
            logger.debug(f"Card parse error: {e}")
            return None
