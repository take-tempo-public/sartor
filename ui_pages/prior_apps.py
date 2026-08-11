"""PriorAppsPage — the shared application-detail modal + resume-into-wizard flow."""

from __future__ import annotations

from ui_pages.base import DEFAULT_TIMEOUT_MS, BasePage
from ui_pages.selectors import PriorApps


class PriorAppsPage(BasePage):
    """Page Object for the shared application-detail modal + resume-into-wizard flow.

    A4 (`feat/prior-apps-pipeline`): the per-candidate Applications panel that
    used to host card-click navigation into this modal was removed — the
    Pipeline board (`ui_pages.pipeline.PipelinePage`) is now the sole UI
    journey into it, exercised end-to-end by
    `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py`. Callers
    here only need "this application's detail modal is open" as a setup step
    (Resume in wizard, meta edits, …), so `open_detail()` calls the same
    global JS function production code calls either way,
    `_showApplicationDetail(app_id)`, directly — decoupled from `currentUser`
    and from replaying the Pipeline row's `onUserSelect()` cascade, which
    would otherwise risk perturbing wizard state a caller may have already
    built up before opening the modal.
    """

    def open_detail(self, app_id: int) -> None:
        """Open an application's detail modal directly, by id."""
        self.page.evaluate("(id) => _showApplicationDetail(id)", app_id)
        self.page.wait_for_selector(PriorApps.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    def resume_visible(self) -> bool:
        """Return whether the modal's 'Resume in wizard' button is offered.

        Hidden for applications with nothing to resume; shown once any analysis
        exists (#4).
        """
        return self.page.locator(PriorApps.RESUME_BUTTON).is_visible()

    def resume(self) -> None:
        """Click 'Resume in wizard' (detail modal already open)."""
        btn = self.page.locator(PriorApps.RESUME_BUTTON)
        btn.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        btn.click()

    def resume_application(self, app_id: int) -> None:
        """Navigate card → detail modal → 'Resume in wizard' to rehydrate the wizard.

        Rehydrates at the application's FURTHEST step with data — Step 1 (analyze)
        through Step 6 (download), not only Step 6 (#4 robustness).
        """
        self.open_detail(app_id)
        self.resume()

    def set_company(self, value: str) -> None:
        """Type a company into the detail modal's company field and blur to save it.

        Saves via PUT /api/applications/<id>/meta (#24).
        """
        field = self.page.locator(PriorApps.COMPANY_INPUT)
        field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
        field.fill(value)
        field.blur()
