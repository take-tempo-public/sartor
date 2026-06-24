"""WizardTemplatePage — Step 4 (persona picker + live preview).

The live preview is curation-gated (it needs `llm_recommendations`, or a
prior generate's `last_generated_json_resume`), so the *rendered* preview is
covered by the seeded Walk B (`test_output_surface_seeded.py`), not here.
This POM covers reaching the step and the picker being populated.
"""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Wizard


class WizardTemplatePage(BasePage):
    def open(self) -> WizardTemplatePage:
        self.goto_step(4)
        self.page.wait_for_selector(
            Wizard.PANEL_TEMPLATE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        self.page.wait_for_selector(Wizard.TEMPLATE_OPTIONS, timeout=DEFAULT_TIMEOUT_MS)
        return self

    def template_option_count(self) -> int:
        return self.page.locator(Wizard.TEMPLATE_OPTIONS).count()

    def pick_template(self, index: int = 1) -> None:
        """Pick a template by index (Modern is typically the 2nd card)."""
        options = self.page.locator(Wizard.TEMPLATE_OPTIONS)
        if options.count() > index:
            options.nth(index).click()

    def wait_live_preview(self) -> None:
        self.page.wait_for_selector(
            Wizard.LIVE_PREVIEW_FRAME, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )

    def continue_to_generate(self) -> None:
        self.page.click(Wizard.CONTINUE_TO_GENERATE)
        self.page.wait_for_selector(
            Wizard.PANEL_GENERATE, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
