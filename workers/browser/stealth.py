"""
Anti-detection helpers — makes the bot look like a real human browser.
"""
import asyncio
import random
from playwright.async_api import Page


async def apply_stealth(page: Page):
    """Patch browser fingerprint to avoid bot detection."""
    await page.add_init_script("""
        // Remove webdriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        // Fake languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });

        // Fake chrome object
        window.chrome = { runtime: {} };

        // Fake permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
    """)


async def human_type(page: Page, selector: str, text: str):
    """Type text with randomized human-like delays."""
    await page.click(selector)
    await page.fill(selector, "")  # clear first
    for char in text:
        await page.type(selector, char, delay=random.randint(40, 120))
    await asyncio.sleep(random.uniform(0.2, 0.5))


async def human_click(page: Page, selector: str):
    """Click with a small random offset + delay."""
    element = await page.query_selector(selector)
    if element:
        box = await element.bounding_box()
        if box:
            x = box["x"] + box["width"]  * random.uniform(0.3, 0.7)
            y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.mouse.click(x, y)
    await asyncio.sleep(random.uniform(0.5, 1.0))


async def random_delay(min_s: float = 1.0, max_s: float = 3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def scroll_into_view(page: Page, selector: str):
    element = await page.query_selector(selector)
    if element:
        await element.scroll_into_view_if_needed()
        await asyncio.sleep(0.3)
