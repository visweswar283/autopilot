"""
Browser session manager — maintains persistent per-portal sessions.
Saves/restores cookies so the bot doesn't need to log in every run.
"""
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext
from loguru import logger

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/tmp/sessions"))
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class SessionManager:
    def __init__(self, headless: bool = True):
        self.headless  = headless
        self._browser: Browser | None = None
        self._pw       = None

    async def start(self):
        self._pw      = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1280,800",
            ],
        )
        logger.info("Browser launched")

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        logger.info("Browser closed")

    async def get_context(self, portal: str) -> BrowserContext:
        """Return a browser context with saved cookies for the given portal."""
        import random
        context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Restore saved cookies if they exist
        cookie_file = SESSIONS_DIR / f"{portal}_cookies.json"
        if cookie_file.exists():
            try:
                cookies = json.loads(cookie_file.read_text())
                await context.add_cookies(cookies)
                logger.debug(f"Restored session for {portal}")
            except Exception as e:
                logger.warning(f"Could not restore {portal} session: {e}")

        return context

    async def save_session(self, context: BrowserContext, portal: str):
        """Persist cookies for reuse in the next run."""
        cookies = await context.cookies()
        cookie_file = SESSIONS_DIR / f"{portal}_cookies.json"
        cookie_file.write_text(json.dumps(cookies))
        logger.debug(f"Session saved for {portal}")

    async def clear_session(self, portal: str):
        cookie_file = SESSIONS_DIR / f"{portal}_cookies.json"
        if cookie_file.exists():
            cookie_file.unlink()
            logger.info(f"Cleared session for {portal}")
