"""
Greenhouse ATS adapter.
Works for all companies using Greenhouse (Stripe, Airbnb, Dropbox, etc.)
Greenhouse has a standardized embed at boards.greenhouse.io/<company>/jobs/<id>
"""
import asyncio
from loguru import logger
from playwright.async_api import Page

from adapters.base import BaseAdapter, JobInfo, UserProfile, ApplicationResult, ApplyResult
from browser.stealth import apply_stealth, human_type, human_click, random_delay


class GreenhouseAdapter(BaseAdapter):

    async def login(self, credentials: dict) -> bool:
        # Greenhouse is application-only — no account login required.
        return True

    async def apply(self, job: JobInfo, profile: UserProfile) -> ApplicationResult:
        context = await self.session_manager.get_context("greenhouse")
        page    = await context.new_page()
        await apply_stealth(page)

        try:
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(2, 3)

            # Check for confirmation (already submitted or success page)
            if await page.query_selector(".confirmation, #confirmation, h1:has-text(\"Thank you\")"):
                return ApplicationResult(ApplyResult.ALREADY_APPLIED, "Already applied via Greenhouse")

            result = await self._fill_greenhouse_form(page, profile)
            return result

        except Exception as e:
            logger.error(f"Greenhouse apply failed for {job.title} @ {job.company}: {e}")
            return ApplicationResult(ApplyResult.FAILED, str(e))
        finally:
            await page.close()

    async def _fill_greenhouse_form(self, page: Page, profile: UserProfile) -> ApplicationResult:
        """Fill Greenhouse's single-page application form."""
        await random_delay(1, 2)

        # CAPTCHA check
        if await page.query_selector("iframe[src*='recaptcha'], .g-recaptcha"):
            return ApplicationResult(ApplyResult.CAPTCHA, "reCAPTCHA on Greenhouse")

        # --- Basic info ---
        await self._fill_field(page, "#first_name", profile.full_name.split()[0])
        await self._fill_field(page, "#last_name",  profile.full_name.split()[-1])
        await self._fill_field(page, "#email",      profile.email)
        await self._fill_field(page, "#phone",      profile.phone)

        # Location / city
        await self._fill_field(page, "#location",   profile.location)

        # --- Resume upload ---
        await self._handle_resume_upload(page, profile)

        # --- LinkedIn / portfolio URLs ---
        await self._fill_urls(page, profile)

        # --- Custom questions ---
        await self._fill_custom_questions(page, profile)

        # --- Voluntary EEO disclosures ---
        await self._handle_eeo(page)

        # --- Submit ---
        submit_btn = await page.query_selector(
            "#submit_app, input[type=\"submit\"], button[type=\"submit\"]:has-text(\"Submit\")"
        )
        if not submit_btn:
            return ApplicationResult(ApplyResult.FAILED, "No submit button found on Greenhouse form")

        await submit_btn.click()
        await random_delay(3, 5)

        # Confirmation check
        if await page.query_selector(".confirmation, #confirmation, h1:has-text(\"Thank you\"), h2:has-text(\"application\")"):
            logger.success("Greenhouse application submitted")
            return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via Greenhouse")

        # URL-based confirmation
        if "confirmation" in page.url or "thank" in page.url.lower():
            logger.success("Greenhouse application submitted (URL redirect)")
            return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via Greenhouse")

        return ApplicationResult(ApplyResult.FAILED, "Submit clicked but confirmation not detected")

    async def _fill_field(self, page: Page, selector: str, value: str):
        """Fill a field only if it exists and is empty."""
        el = await page.query_selector(selector)
        if el and not await el.input_value():
            await el.fill(value)
            await asyncio.sleep(0.3)

    async def _handle_resume_upload(self, page: Page, profile: UserProfile):
        """Upload resume to Greenhouse file input."""
        from pathlib import Path
        # Greenhouse resume upload: #resume or input[name="resume"]
        for sel in ['#resume', 'input[name="resume"]', 'input[type="file"][name*="resume"]']:
            file_input = await page.query_selector(sel)
            if file_input and Path(profile.resume_path).exists():
                await file_input.set_input_files(profile.resume_path)
                await random_delay(1, 2)
                logger.debug("Resume uploaded to Greenhouse")
                return

        # Fallback: any file input
        file_input = await page.query_selector('input[type="file"]')
        if file_input and Path(profile.resume_path).exists():
            await file_input.set_input_files(profile.resume_path)
            await random_delay(1, 2)
            logger.debug("Resume uploaded to Greenhouse (fallback)")

    async def _fill_urls(self, page: Page, profile: UserProfile):
        """Fill LinkedIn, GitHub, portfolio URL fields."""
        url_fields = {
            'input[name*="linkedin"], input[id*="linkedin"]':   profile.linkedin_url,
            'input[name*="github"],   input[id*="github"]':     profile.github_url,
            'input[name*="website"],  input[id*="website"]':    profile.github_url,
            'input[name*="portfolio"],input[id*="portfolio"]':  profile.github_url,
            'input[name*="twitter"],  input[id*="twitter"]':    "",
        }
        for selector, value in url_fields.items():
            if not value:
                continue
            for sel in selector.split(","):
                sel = sel.strip()
                el = await page.query_selector(sel)
                if el and not await el.input_value():
                    await el.fill(value)
                    await asyncio.sleep(0.2)
                    break

    async def _fill_custom_questions(self, page: Page, profile: UserProfile):
        """Answer Greenhouse custom questions — text, radio, select."""
        # Text/textarea fields with label context
        for inp in await page.query_selector_all('input[type="text"]:visible, textarea:visible'):
            label_id = await inp.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            val      = await inp.input_value()
            if val:
                continue
            if "year" in label or "experience" in label:
                await inp.fill(str(profile.experience_years or 3))
            elif "salary" in label or "compensation" in label or "pay" in label:
                await inp.fill("150000")
            elif "city" in label or "location" in label:
                await inp.fill(profile.location)
            elif "cover" in label or "summary" in label or "tell us" in label:
                await inp.fill(
                    f"I am excited to apply for this role. With {profile.experience_years or 3}+ years "
                    f"of experience and strong skills in {', '.join(profile.skills[:3])}, "
                    "I am confident I can contribute significantly to your team."
                )

        # Radio buttons — prefer yes/authorized answers
        for radio in await page.query_selector_all('input[type="radio"]:visible'):
            label_id = await radio.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label for w in ["yes", "authorized", "legally", "eligible", "citizen", "18"]):
                if not await radio.is_checked():
                    await radio.check()
                    await asyncio.sleep(0.2)

        # Dropdowns
        for sel in await page.query_selector_all('select:visible'):
            opts    = await sel.query_selector_all('option')
            current = await sel.input_value()
            if not current and len(opts) > 1:
                # Check label for EEO keywords — skip those here (handled in _handle_eeo)
                label_id = await sel.get_attribute("id") or ""
                label_el = await page.query_selector(f'label[for="{label_id}"]')
                label    = (await label_el.inner_text()).lower() if label_el else ""
                if not any(w in label for w in ["gender", "race", "ethnicity", "veteran", "disability"]):
                    await sel.select_option(index=1)

    async def _handle_eeo(self, page: Page):
        """Handle EEO / demographic voluntary disclosure dropdowns."""
        for sel in await page.query_selector_all('select:visible'):
            label_id = await sel.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label for w in ["gender", "race", "ethnicity", "veteran", "disability"]):
                opts = await sel.query_selector_all('option')
                for opt in opts:
                    opt_text = (await opt.inner_text()).lower()
                    if "prefer" in opt_text or "decline" in opt_text or "not" in opt_text:
                        await sel.select_option(value=await opt.get_attribute("value"))
                        break

    async def is_already_applied(self, job: JobInfo) -> bool:
        return False
