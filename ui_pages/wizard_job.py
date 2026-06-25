"""WizardJobPage — Step 1 (paste the JD, run Analyze)."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import TopTabs, Wizard


class WizardJobPage(BasePage):
    """Page Object for Step 1 — paste the JD and run Analyze."""

    def open(self) -> WizardJobPage:
        """Switch to the Tailor tab and select wizard Step 1."""
        self.page.click(TopTabs.TAILOR)
        self.page.click(Wizard.step_button(1))
        self.page.wait_for_selector(Wizard.JD_TEXT, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        return self

    def fill_jd(self, jd_text: str) -> WizardJobPage:
        """Fill the job-description textarea."""
        self.page.fill(Wizard.JD_TEXT, jd_text)
        return self

    def analyze(self, jd_text: str | None = None) -> WizardJobPage:
        """Run Analyze (filling the JD first if given); wait for the render."""
        if jd_text is not None:
            self.page.fill(Wizard.JD_TEXT, jd_text)
        self.page.click(Wizard.ANALYZE_BUTTON)
        self.page.wait_for_selector(
            f"{Wizard.ANALYSIS_CONTENT} > *",
            state="attached",
            timeout=LLM_TIMEOUT_MS,
        )
        return self

    def continue_to_clarify(self) -> None:
        """Click 'Continue to Clarify' and wait for the Clarify panel."""
        self.page.click(Wizard.CONTINUE_TO_CLARIFY)
        self.page.wait_for_selector(
            Wizard.PANEL_CLARIFY, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
