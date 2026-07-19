"""WizardOutputPage — Step 6 (panelOutput): WYSIWYG preview + downloads."""

from __future__ import annotations

from playwright.sync_api import FrameLocator, Locator
from playwright.sync_api import TimeoutError as PWTimeout

from ui_pages.base import DEFAULT_TIMEOUT_MS, LLM_TIMEOUT_MS, BasePage
from ui_pages.selectors import Output


class WizardOutputPage(BasePage):
    """Page Object for Step 6 — the WYSIWYG output preview and downloads."""

    def wait_loaded(self) -> WizardOutputPage:
        """Wait for the Output panel to be visible."""
        self.page.wait_for_selector(Output.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        return self

    def download_resume_button(self) -> Locator:
        """Return the 'Download résumé' button locator."""
        return self.page.locator(Output.DOWNLOAD_RESUME)

    def preview_frame(self) -> FrameLocator:
        """Return the output-preview iframe's frame locator."""
        return self.page.frame_locator(Output.PREVIEW_FRAME)

    def preview_body(self) -> Locator:
        """The rendered résumé inside the WYSIWYG preview iframe."""
        return self.preview_frame().locator("body")

    def generate_cover_letter(self) -> bool:
        """Click '+ Generate cover letter' and wait for the CL preview.

        Returns False when the button is absent (nothing to capture).
        """
        btn = self.page.locator(Output.GENERATE_COVER)
        if btn.count() == 0:
            return False
        btn.click()
        try:
            self.page.wait_for_selector(Output.COVER_TAB_ACTIVE, timeout=DEFAULT_TIMEOUT_MS)
        except PWTimeout:
            self.page.click(Output.COVER_TAB)
        # #coverLetterPreview's home location is hidden by default — the
        # generation call populates it but only openEditDrawer('cover')
        # (the "Edit before downloading" button) relocates it into the
        # visible drawer host (templates/index.html:586).
        self.page.wait_for_selector(
            Output.OPEN_COVER_EDIT_DRAWER, state="visible", timeout=LLM_TIMEOUT_MS
        )
        self.page.click(Output.OPEN_COVER_EDIT_DRAWER)
        self.page.wait_for_selector(
            Output.COVER_PREVIEW, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        return True
