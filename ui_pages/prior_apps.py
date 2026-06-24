"""PriorAppsPage — the Prior Applications panel + resume-into-wizard flow."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import PriorApps


class PriorAppsPage(BasePage):
    def open_detail(self, app_id: int) -> None:
        """Open a prior-app card's detail modal."""
        self.page.wait_for_selector(PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        card = self.page.locator(PriorApps.card(app_id))
        card.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        card.click()
        self.page.wait_for_selector(PriorApps.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    def resume_visible(self) -> bool:
        """Whether the modal's 'Resume in wizard' button is offered. Hidden for
        applications with nothing to resume; shown once any analysis exists (#4)."""
        return self.page.locator(PriorApps.RESUME_BUTTON).is_visible()

    def resume(self) -> None:
        """Click 'Resume in wizard' (detail modal already open)."""
        btn = self.page.locator(PriorApps.RESUME_BUTTON)
        btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        btn.click()

    def resume_application(self, app_id: int) -> None:
        """Card → detail modal → 'Resume in wizard', which rehydrates the wizard
        at the application's FURTHEST step with data — Step 1 (analyze) through
        Step 6 (download), not only Step 6 (#4 robustness)."""
        self.open_detail(app_id)
        self.resume()

    def set_company(self, value: str) -> None:
        """Type a company into the detail modal's company field and blur to save
        it via PUT /api/applications/<id>/meta (#24)."""
        field = self.page.locator(PriorApps.COMPANY_INPUT)
        field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        field.fill(value)
        field.blur()
