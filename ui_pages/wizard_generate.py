"""WizardGeneratePage — Step 5 (generate the documents) + Step-6 refine note."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PWTimeout

from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import Wizard


class WizardGeneratePage(BasePage):
    def generate(self) -> None:
        self.page.click(Wizard.GENERATE_BUTTON)
        self.page.wait_for_selector(
            Wizard.OUTPUT_PREVIEW_BLOCK, state="visible", timeout=LLM_TIMEOUT_MS
        )

    def refine(self, note: str, delay: int = 8) -> bool:
        """Type a refine note if the refinement input is present (post-generate).

        Returns False when it isn't visible, so the caller can proceed.
        """
        try:
            self.page.wait_for_selector(
                Wizard.REFINEMENT_INPUT, state="visible", timeout=DEFAULT_TIMEOUT_MS
            )
        except PWTimeout:
            return False
        inp = self.page.locator(Wizard.REFINEMENT_INPUT)
        inp.click()
        inp.type(note, delay=delay)
        return True
