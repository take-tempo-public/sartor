"""PriorAppsPage — the Prior Applications panel + resume-into-wizard flow."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import PriorApps


class PriorAppsPage(BasePage):
    def resume_application(self, app_id: int) -> None:
        """Click a prior-app card → app-detail modal → 'Resume in wizard',
        which rehydrates the wizard at Step 6 from the run's last state."""
        self.page.wait_for_selector(
            PriorApps.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        card = self.page.locator(PriorApps.card(app_id))
        card.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        card.click()
        self.page.wait_for_selector(
            PriorApps.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS
        )
        resume = self.page.locator(PriorApps.RESUME_BUTTON)
        resume.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        resume.click()
