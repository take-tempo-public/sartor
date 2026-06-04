"""WizardOutputPage — Step 6 (panelOutput): WYSIWYG preview + downloads."""

from __future__ import annotations

from playwright.sync_api import FrameLocator, Locator
from playwright.sync_api import TimeoutError as PWTimeout

from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import Output


class WizardOutputPage(BasePage):
    def wait_loaded(self) -> WizardOutputPage:
        self.page.wait_for_selector(
            Output.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        return self

    def download_resume_button(self) -> Locator:
        return self.page.locator(Output.DOWNLOAD_RESUME)

    def preview_frame(self) -> FrameLocator:
        return self.page.frame_locator(Output.PREVIEW_FRAME)

    def preview_body(self) -> Locator:
        """The rendered résumé inside the WYSIWYG preview iframe."""
        return self.preview_frame().locator("body")

    def generate_cover_letter(self) -> bool:
        """Click '+ Generate cover letter' and wait for the CL preview.
        Returns False when the button is absent (nothing to capture)."""
        btn = self.page.locator(Output.GENERATE_COVER)
        if btn.count() == 0:
            return False
        btn.click()
        try:
            self.page.wait_for_selector(
                Output.COVER_TAB_ACTIVE, timeout=DEFAULT_TIMEOUT_MS
            )
        except PWTimeout:
            self.page.click(Output.COVER_TAB)
        self.page.wait_for_selector(
            Output.COVER_PREVIEW, state="visible", timeout=LLM_TIMEOUT_MS
        )
        return True
