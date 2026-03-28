"""
Lever ATS adapter.
Works for all companies using Lever (Netflix, Shopify, GitHub, etc.)
Lever job pages: jobs.lever.co/<company>/<job-id>
"""
import asyncio
from loguru import logger
from playwright.async_api import Page

from adapters.base import BaseAdapter, JobInfo, UserProfile, ApplicationResult, ApplyResult
from browser.stealth import apply_stealth, human_type, human_click, random_delay


class LeverAdapter(BaseAdapter):

    async def login(self, credentials: dict) -> bool:
        # Lever is application-only — no account login required.
        return True

    async def apply(self, job: JobInfo, profile: UserProfile) -> ApplicationResult:
        context = await self.session_manager.get_context("lever")
        page    = await context.new_page()
        await apply_stealth(page)

        try:
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(2, 3)

            # Check for confirmation page
            if await page.query_selector(".thanks, h2:has-text(\"Thank you\"), h1:has-text(\"application received\")"):
                return ApplicationResult(ApplyResult.ALREADY_APPLIED, "Already applied via Lever")

            # Lever has an "Apply" button on the job description page
            apply_btn = await page.query_selector(
                'a[href*="/apply"], button:has-text("Apply"), .postings-btn'
            )
            if apply_btn:
                await apply_btn.click()
                await random_delay(2, 3)

            result = await self._fill_lever_form(page, profile)
            return result

        except Exception as e:
            logger.error(f"Lever apply failed for {job.title} @ {job.company}: {e}")
            return ApplicationResult(ApplyResult.FAILED, str(e))
        finally:
            await page.close()

    async def _fill_lever_form(self, page: Page, profile: UserProfile) -> ApplicationResult:
        """Fill Lever's application form (single page)."""
        await random_delay(1, 2)

        # CAPTCHA check
        if await page.query_selector("iframe[src*='recaptcha'], .g-recaptcha"):
            return ApplicationResult(ApplyResult.CAPTCHA, "reCAPTCHA on Lever")

        # --- Name fields ---
        name_parts = profile.full_name.split()
        await self._fill_field(page, 'input[name="name"], #name', profile.full_name)
        await self._fill_field(page, 'input[name="first_name"], #first_name, input[placeholder*="First"]', name_parts[0])
        await self._fill_field(page, 'input[name="last_name"],  #last_name,  input[placeholder*="Last"]',  name_parts[-1])

        # --- Contact ---
        await self._fill_field(page, 'input[name="email"], #email, input[type="email"]',    profile.email)
        await self._fill_field(page, 'input[name="phone"], #phone, input[type="tel"]',       profile.phone)
        await self._fill_field(page, 'input[name="location"], #location, input[placeholder*="location" i]', profile.location)

        # --- Resume upload ---
        await self._handle_resume_upload(page, profile)

        # --- URLs ---
        await self._fill_urls(page, profile)

        # --- Cover letter / additional info ---
        await self._fill_cover_letter(page, profile)

        # --- Custom questions ---
        await self._fill_custom_questions(page, profile)

        # --- EEO disclosures ---
        await self._handle_eeo(page)

        # --- Submit ---
        submit_btn = await page.query_selector(
            'button[type="submit"]:has-text("Submit"), '
            'input[type="submit"], '
            'button:has-text("Submit application"), '
            'button.postings-btn:has-text("Submit")'
        )
        if not submit_btn:
            return ApplicationResult(ApplyResult.FAILED, "No submit button found on Lever form")

        await submit_btn.click()
        await random_delay(3, 5)

        # Confirmation check
        if await page.query_selector(".thanks, h2:has-text(\"Thank you\"), h1:has-text(\"received\")"):
            logger.success("Lever application submitted")
            return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via Lever")

        if "thank" in page.url.lower() or "thanks" in page.url.lower() or "/confirmation" in page.url:
            logger.success("Lever application submitted (URL redirect)")
            return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via Lever")

        return ApplicationResult(ApplyResult.FAILED, "Submit clicked but confirmation not detected")

    async def _fill_field(self, page: Page, selectors: str, value: str):
        """Try multiple CSS selectors until one matches and fills."""
        for sel in selectors.split(","):
            sel = sel.strip()
            el = await page.query_selector(sel)
            if el and not await el.input_value():
                await el.fill(value)
                await asyncio.sleep(0.3)
                return

    async def _handle_resume_upload(self, page: Page, profile: UserProfile):
        """Upload resume to Lever's file drop zone."""
        from pathlib import Path
        for sel in ['input[name="resume"]', 'input[type="file"][id*="resume"]', 'input[type="file"]']:
            file_input = await page.query_selector(sel)
            if file_input and Path(profile.resume_path).exists():
                await file_input.set_input_files(profile.resume_path)
                await random_delay(1, 2)
                logger.debug("Resume uploaded to Lever")
                return

    async def _fill_urls(self, page: Page, profile: UserProfile):
        """Fill LinkedIn, GitHub, portfolio URL fields."""
        mappings = [
            ('input[name*="linkedin" i], input[placeholder*="linkedin" i]', profile.linkedin_url),
            ('input[name*="github" i],   input[placeholder*="github" i]',   profile.github_url),
            ('input[name*="website" i],  input[placeholder*="website" i]',  profile.github_url),
            ('input[name*="portfolio" i]',                                   profile.github_url),
        ]
        for selector, value in mappings:
            if not value:
                continue
            for sel in selector.split(","):
                sel = sel.strip()
                el = await page.query_selector(sel)
                if el and not await el.input_value():
                    await el.fill(value)
                    await asyncio.sleep(0.2)
                    break

    async def _fill_cover_letter(self, page: Page, profile: UserProfile):
        """Fill cover letter / additional info textarea."""
        for sel in ['textarea[name*="cover" i]', 'textarea[name*="additional" i]', 'textarea[name*="comment" i]']:
            el = await page.query_selector(sel)
            if el and not await el.input_value():
                text = (
                    f"I am excited to apply for this role. With {profile.experience_years or 3}+ years of "
                    f"experience and expertise in {', '.join(profile.skills[:4])}, I am confident I will "
                    "make a meaningful contribution to your team. I look forward to the opportunity to discuss "
                    "how my background aligns with your needs."
                )
                await el.fill(text)
                await asyncio.sleep(0.3)
                return

    async def _fill_custom_questions(self, page: Page, profile: UserProfile):
        """Answer custom screening questions."""
        # Text inputs by label
        for inp in await page.query_selector_all('input[type="text"]:visible, input[type="number"]:visible'):
            label_id = await inp.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            val      = await inp.input_value()
            if val:
                continue
            if "year" in label or "experience" in label:
                await inp.fill(str(profile.experience_years or 3))
            elif "salary" in label or "compensation" in label:
                await inp.fill("150000")
            elif "city" in label or "location" in label:
                await inp.fill(profile.location)

        # Radio buttons — prefer yes/authorized
        for radio in await page.query_selector_all('input[type="radio"]:visible'):
            label_id = await radio.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label for w in ["yes", "authorized", "legally", "eligible", "citizen", "18"]):
                if not await radio.is_checked():
                    await radio.check()
                    await asyncio.sleep(0.2)

        # Checkboxes — agree/terms
        for cb in await page.query_selector_all('input[type="checkbox"]:visible'):
            label_id = await cb.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label for w in ["agree", "terms", "certify", "consent"]):
                if not await cb.is_checked():
                    await cb.check()
                    await asyncio.sleep(0.2)

        # Dropdowns (non-EEO)
        for sel in await page.query_selector_all('select:visible'):
            label_id = await sel.get_attribute("id") or ""
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label for w in ["gender", "race", "ethnicity", "veteran", "disability"]):
                continue
            opts    = await sel.query_selector_all('option')
            current = await sel.input_value()
            if not current and len(opts) > 1:
                await sel.select_option(index=1)

    async def _handle_eeo(self, page: Page):
        """Handle EEO voluntary disclosure sections."""
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
