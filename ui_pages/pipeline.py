"""PipelinePage — the cross-candidate Pipeline board (Wave 2 recruiter tier, F-17)."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import Pipeline, TopTabs


class PipelinePage(BasePage):
    """Page Object for the read-only cross-candidate Pipeline tab."""

    def open(self) -> PipelinePage:
        """Switch to the Pipeline tab and wait for the board to render."""
        self.page.click(TopTabs.PIPELINE)
        self.page.wait_for_selector(Pipeline.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        self.page.wait_for_selector(Pipeline.BOARD, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        return self

    def row_count(self) -> int:
        """Return the number of application rows currently rendered on the board."""
        return self.page.locator(Pipeline.ROW).count()

    def click_row(self, title: str) -> None:
        """Click the pipeline row whose title text matches (switches candidate + tab)."""
        row = self.page.locator(Pipeline.ROW, has_text=title).first
        row.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        row.click()
