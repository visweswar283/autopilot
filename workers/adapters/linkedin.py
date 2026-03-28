"""
LinkedIn Easy Apply adapter.
Handles the full Easy Apply flow including multi-step modals.
"""
import asyncio
import os
from pathlib import Path
from loguru import logger
from playwright.async_api import BrowserContext, Page

from adapters.base import BaseAdapter, JobInfo, UserProfile, ApplicationResult, ApplyResult
from browser.stealth import apply_stealth, human_type, human_click, random_delay

LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")


class LinkedInAdapter(BaseAdapter):

    async def login(self, credentials: dict) -> bool:
        context = await self.session_manager.get_context("linkedin")
        page    = await context.new_page()
        await apply_stealth(page)

        try:
            # Check if already logged in
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
            if "feed" in page.url:
                logger.info("LinkedIn: already logged in via saved session")
                await self.session_manager.save_session(context, "linkedin")
                await page.close()
                return True

            # Login flow
            await page.goto("https://www.linkedin.com/login", wait_until="networkidle", timeout=20000)
            await human_type(page, "#username", credentials.get("email", LINKEDIN_EMAIL))
            await human_type(page, "#password", credentials.get("password", LINKEDIN_PASSWORD))
            await random_delay(0.5, 1.0)
            await human_click(page, '[type="submit"]')
            await page.wait_for_url("**/feed/**", timeout=20000)

            await self.session_manager.save_session(context, "linkedin")
            logger.info("LinkedIn: login successful")
            await page.close()
            return True

        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            await page.close()
            return False

    async def apply(self, job: JobInfo, profile: UserProfile) -> ApplicationResult:
        context = await self.session_manager.get_context("linkedin")
        page    = await context.new_page()
        await apply_stealth(page)

        try:
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(2, 3)

            # Check if already applied
            if await page.query_selector(".jobs-s-apply__application-link"):
                already = await page.inner_text(".jobs-s-apply__application-link")
                if "applied" in already.lower():
                    return ApplicationResult(ApplyResult.ALREADY_APPLIED, "Already applied via LinkedIn")

            # Find Easy Apply button
            easy_apply_btn = await page.query_selector(
                'button.jobs-apply-button, button[aria-label*="Easy Apply"], .jobs-s-apply button'
            )
            if not easy_apply_btn:
                return ApplicationResult(ApplyResult.UNSUPPORTED, "No Easy Apply button found")

            await human_click(page, 'button.jobs-apply-button, button[aria-label*="Easy Apply"]')
            await random_delay(1.5, 2.5)

            # Handle multi-step application modal
            result = await self._handle_easy_apply_modal(page, profile)
            await self.session_manager.save_session(context, "linkedin")
            return result

        except Exception as e:
            logger.error(f"LinkedIn apply failed for {job.title} at {job.company}: {e}")
            return ApplicationResult(ApplyResult.FAILED, str(e))
        finally:
            await page.close()

    async def _handle_easy_apply_modal(self, page: Page, profile: UserProfile) -> ApplicationResult:
        """Walk through all steps of LinkedIn Easy Apply modal."""
        max_steps = 10

        for step in range(max_steps):
            await random_delay(1.0, 2.0)

            # Check for CAPTCHA
            if await page.query_selector("iframe[src*='captcha'], .challenge-dialog"):
                logger.warning("CAPTCHA detected on LinkedIn")
                return ApplicationResult(ApplyResult.CAPTCHA, "CAPTCHA encountered")

            # Check if submitted
            if await page.query_selector('[data-test-modal="post-apply-modal"], h2:has-text("application was sent")'):
                logger.success("LinkedIn Easy Apply submitted successfully")
                return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via LinkedIn Easy Apply")

            # Fill visible fields
            await self._fill_contact_info(page, profile)
            await self._fill_text_fields(page, profile)
            await self._fill_dropdowns(page)
            await self._handle_resume_upload(page, profile)
            await self._answer_screening_questions(page)

            # Try to advance or submit
            next_btn   = await page.query_selector('button[aria-label="Continue to next step"]')
            review_btn = await page.query_selector('button[aria-label="Review your application"]')
            submit_btn = await page.query_selector('button[aria-label="Submit application"]')

            if submit_btn:
                await human_click(page, 'button[aria-label="Submit application"]')
                await random_delay(2, 3)
                return ApplicationResult(ApplyResult.SUCCESS, "Application submitted")
            elif review_btn:
                await human_click(page, 'button[aria-label="Review your application"]')
            elif next_btn:
                await human_click(page, 'button[aria-label="Continue to next step"]')
            else:
                # Try generic next/submit buttons
                generic_next = await page.query_selector('button:has-text("Next"), button:has-text("Continue")')
                generic_submit = await page.query_selector('button:has-text("Submit")')
                if generic_submit:
                    await generic_submit.click()
                    await random_delay(2, 3)
                    return ApplicationResult(ApplyResult.SUCCESS, "Application submitted")
                elif generic_next:
                    await generic_next.click()
                else:
                    break

        return ApplicationResult(ApplyResult.FAILED, "Could not complete Easy Apply flow")

    async def _fill_contact_info(self, page: Page, profile: UserProfile):
        """Fill phone number and other contact fields if visible."""
        phone_sel = 'input[id*="phoneNumber"], input[name*="phone"]'
        phone_el  = await page.query_selector(phone_sel)
        if phone_el:
            val = await phone_el.input_value()
            if not val:
                await human_type(page, phone_sel, profile.phone)

    async def _fill_text_fields(self, page: Page, profile: UserProfile):
        """Fill generic text inputs based on label context."""
        inputs = await page.query_selector_all('input[type="text"]:visible, input[type="number"]:visible')
        for inp in inputs:
            label_el = await page.query_selector(f'label[for="{await inp.get_attribute("id")}"]')
            label    = (await label_el.inner_text()).lower() if label_el else ""
            val      = await inp.input_value()
            if val:
                continue
            if "year" in label or "experience" in label:
                await inp.fill("3")
            elif "salary" in label or "compensation" in label:
                await inp.fill("150000")
            elif "city" in label or "location" in label:
                await inp.fill(profile.location)
            elif "linkedin" in label:
                await inp.fill(profile.linkedin_url)
            elif "github" in label or "portfolio" in label:
                await inp.fill(profile.github_url)
            elif "website" in label or "url" in label:
                await inp.fill(profile.github_url)

    async def _fill_dropdowns(self, page: Page):
        """Select first valid option for visible dropdowns."""
        selects = await page.query_selector_all('select:visible')
        for sel in selects:
            options = await sel.query_selector_all('option')
            if len(options) > 1:
                await sel.select_option(index=1)

    async def _handle_resume_upload(self, page: Page, profile: UserProfile):
        """Upload resume if a file input is visible."""
        file_input = await page.query_selector('input[type="file"]')
        if file_input and Path(profile.resume_path).exists():
            await file_input.set_input_files(profile.resume_path)
            await random_delay(1, 2)
            logger.debug("Resume uploaded")

    async def _answer_screening_questions(self, page: Page):
        """Answer yes/no and radio questions intelligently."""
        # Handle radio buttons — prefer "Yes" for eligibility questions
        radios = await page.query_selector_all('input[type="radio"]:visible')
        for radio in radios:
            label_id = await radio.get_attribute("id")
            label_el = await page.query_selector(f'label[for="{label_id}"]')
            label_text = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label_text for w in ["yes", "authorized", "eligible", "citizen", "legally"]):
                await radio.check()
                break

        # Handle checkboxes — check required ones
        checkboxes = await page.query_selector_all('input[type="checkbox"]:visible')
        for cb in checkboxes:
            if not await cb.is_checked():
                label_id = await cb.get_attribute("id")
                label_el = await page.query_selector(f'label[for="{label_id}"]')
                label_text = (await label_el.inner_text()).lower() if label_el else ""
                if "agree" in label_text or "terms" in label_text or "certify" in label_text:
                    await cb.check()

    async def is_already_applied(self, job: JobInfo) -> bool:
        return False  # Handled inside apply() by checking status text
