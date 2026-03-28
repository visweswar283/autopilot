"""
Workday ATS adapter.
Works for ALL companies using Workday (Google, Amazon, Microsoft, Salesforce, etc.)
because Workday has a standardized UI across all companies.
"""
import asyncio
from loguru import logger
from playwright.async_api import Page

from adapters.base import BaseAdapter, JobInfo, UserProfile, ApplicationResult, ApplyResult
from browser.stealth import apply_stealth, human_type, human_click, random_delay


class WorkdayAdapter(BaseAdapter):

    async def login(self, credentials: dict) -> bool:
        # Workday uses company-specific SSO — no global login needed.
        # Bot navigates directly to the job URL and fills the application form.
        return True

    async def apply(self, job: JobInfo, profile: UserProfile) -> ApplicationResult:
        context = await self.session_manager.get_context("workday")
        page    = await context.new_page()
        await apply_stealth(page)

        try:
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)
            await random_delay(2, 3)

            # Check already applied
            if await page.query_selector('[data-automation-id="Applied"]'):
                return ApplicationResult(ApplyResult.ALREADY_APPLIED, "Already applied on Workday")

            # Click Apply button
            apply_btn = await page.query_selector(
                '[data-automation-id="applyButton"], button:has-text("Apply"), button:has-text("Apply Now")'
            )
            if not apply_btn:
                return ApplicationResult(ApplyResult.UNSUPPORTED, "No Apply button found on Workday page")

            await apply_btn.click()
            await random_delay(2, 3)

            # Handle the multi-section Workday application
            result = await self._complete_workday_application(page, profile)
            await self.session_manager.save_session(context, "workday")
            return result

        except Exception as e:
            logger.error(f"Workday apply failed for {job.title} @ {job.company}: {e}")
            return ApplicationResult(ApplyResult.FAILED, str(e))
        finally:
            await page.close()

    async def _complete_workday_application(self, page: Page, profile: UserProfile) -> ApplicationResult:
        """Step through Workday's multi-section application form."""
        max_steps = 15

        for step in range(max_steps):
            await random_delay(1.5, 2.5)

            # CAPTCHA check
            if await page.query_selector("iframe[src*='recaptcha'], .g-recaptcha"):
                return ApplicationResult(ApplyResult.CAPTCHA, "reCAPTCHA on Workday")

            # Success check
            if await page.query_selector('[data-automation-id="confirmation"], h2:has-text("Thank you")'):
                logger.success(f"Workday application submitted")
                return ApplicationResult(ApplyResult.SUCCESS, "Application submitted via Workday")

            # Fill current visible section
            await self._fill_my_information(page, profile)
            await self._fill_my_experience(page, profile)
            await self._fill_application_questions(page)
            await self._handle_resume_upload(page, profile)
            await self._handle_voluntary_disclosures(page)

            # Navigate to next section
            next_btn   = await page.query_selector('[data-automation-id="bottom-navigation-next-btn"]')
            submit_btn = await page.query_selector('[data-automation-id="bottom-navigation-next-btn"]:has-text("Submit")')

            if submit_btn or (next_btn and await next_btn.inner_text() in ["Submit", "Review and Submit"]):
                await (submit_btn or next_btn).click()
                await random_delay(2, 4)
                # Check for confirmation
                if await page.query_selector('[data-automation-id="confirmation"]'):
                    return ApplicationResult(ApplyResult.SUCCESS, "Workday application submitted")
            elif next_btn:
                await next_btn.click()
            else:
                generic = await page.query_selector('button:has-text("Next"), button:has-text("Save and Continue")')
                if generic:
                    await generic.click()
                else:
                    break

        return ApplicationResult(ApplyResult.FAILED, "Could not complete Workday application")

    async def _fill_my_information(self, page: Page, profile: UserProfile):
        """Fill the 'My Information' section — name, address, phone."""
        fields = {
            '[data-automation-id="firstName"]':   profile.full_name.split()[0],
            '[data-automation-id="lastName"]':    profile.full_name.split()[-1],
            '[data-automation-id="email"]':       profile.email,
            '[data-automation-id="phone"]':       profile.phone,
            '[data-automation-id="city"]':        profile.location.split(",")[0].strip(),
            'input[data-automation-id="addressSection_addressLine1"]': profile.location,
        }
        for selector, value in fields.items():
            el = await page.query_selector(selector)
            if el and not await el.input_value():
                await el.fill(value)
                await asyncio.sleep(0.3)

    async def _fill_my_experience(self, page: Page, profile: UserProfile):
        """Fill work experience and skills sections."""
        # LinkedIn profile URL if asked
        linkedin_el = await page.query_selector('input[data-automation-id*="linkedIn"], input[placeholder*="LinkedIn"]')
        if linkedin_el and not await linkedin_el.input_value():
            await linkedin_el.fill(profile.linkedin_url)

        # How did you hear about us — select first option
        source_sel = await page.query_selector('[data-automation-id="sourceOfHire"]')
        if source_sel:
            await source_sel.select_option(index=1)

        # Years of experience numeric fields
        year_inputs = await page.query_selector_all('input[data-automation-id*="Years"], input[placeholder*="years"]')
        for inp in year_inputs:
            if not await inp.input_value():
                await inp.fill(str(profile.experience_years or 3))

    async def _fill_application_questions(self, page: Page):
        """Answer screening questions: yes/no, radio, dropdowns."""
        # Radio buttons — prefer affirmative answers
        radios = await page.query_selector_all('input[type="radio"]')
        for radio in radios:
            label_id  = await radio.get_attribute("id") or ""
            label_el  = await page.query_selector(f'label[for="{label_id}"]')
            label_txt = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label_txt for w in ["yes", "authorized", "legally", "eligible", "citizen", "18"]):
                if not await radio.is_checked():
                    await radio.check()
                    await asyncio.sleep(0.3)

        # Dropdowns
        selects = await page.query_selector_all('select:visible')
        for sel in selects:
            opts = await sel.query_selector_all('option')
            current = await sel.input_value()
            if not current and len(opts) > 1:
                await sel.select_option(index=1)

        # Salary expectation text inputs
        salary_inputs = await page.query_selector_all(
            'input[data-automation-id*="salary"], input[placeholder*="salary"], input[placeholder*="Salary"]'
        )
        for inp in salary_inputs:
            if not await inp.input_value():
                await inp.fill("150000")

    async def _handle_resume_upload(self, page: Page, profile: UserProfile):
        """Upload resume to Workday file upload widget."""
        from pathlib import Path
        file_input = await page.query_selector('input[type="file"]')
        if file_input and Path(profile.resume_path).exists():
            await file_input.set_input_files(profile.resume_path)
            await random_delay(2, 3)

            # Click confirm/upload button if it appears
            confirm = await page.query_selector(
                'button:has-text("Upload"), button[data-automation-id="upload-button"]'
            )
            if confirm:
                await confirm.click()
                await random_delay(1, 2)
            logger.debug("Resume uploaded to Workday")

    async def _handle_voluntary_disclosures(self, page: Page):
        """Handle EEO/veteran/disability voluntary disclosure forms."""
        # These are usually dropdowns with "Prefer not to disclose" or "Decline to specify"
        selects = await page.query_selector_all('select:visible')
        for sel in selects:
            label_el  = await page.query_selector(f'label[for="{await sel.get_attribute("id")}"]')
            label_txt = (await label_el.inner_text()).lower() if label_el else ""
            if any(w in label_txt for w in ["gender", "race", "ethnicity", "veteran", "disability"]):
                opts = await sel.query_selector_all('option')
                # Find "prefer not to disclose" option
                for opt in opts:
                    opt_text = (await opt.inner_text()).lower()
                    if "prefer" in opt_text or "decline" in opt_text or "not" in opt_text:
                        await sel.select_option(value=await opt.get_attribute("value"))
                        break

    async def is_already_applied(self, job: JobInfo) -> bool:
        return False
