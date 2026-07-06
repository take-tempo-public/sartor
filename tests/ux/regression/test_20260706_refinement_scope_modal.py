"""Regression: the refinement scope warning is an in-app modal, not native confirm().

Bug (Preview #3): when a refinement looked like it might change facts,
``submitRefinement()`` fired a browser-native ``confirm()`` — an OS dialog in a
different visual format from every other modal in the app, which read as jarring
/ untrustworthy. Fix: ``_showRefinementScopeModal()`` renders the same
``.cb-modal`` shell as ``editModal`` (focus trap, Esc-to-cancel, backdrop
dismiss, focus restored to the trigger) and resolves ``'proceed'`` / ``'cancel'``.
It still FLAGS-not-BLOCKS — the user may be correcting a fabricated fact.

LLM-free: drives the promise-based modal helper directly, so it needs neither a
generated résumé nor a stubbed ``/api/validate-refinement``. The ``page``
fixture's sentinel also proves no JS error on load.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS

_MODAL = "#refinementScopeModal"


@pytest.mark.ux
@pytest.mark.slow
def test_refinement_scope_modal_shows_reason_and_resolves(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    BasePage(page, live_server).load()

    # Open the modal via its promise helper; stash the resolution on window.
    page.evaluate(
        "() => { window.__refine = 'PENDING';"
        " _showRefinementScopeModal('Adds a metric you did not provide.', null)"
        "   .then(r => { window.__refine = r; }); }"
    )
    page.wait_for_selector(f"{_MODAL}:not(.hidden)", timeout=DEFAULT_TIMEOUT_MS)
    # The flagged reason is shown in-modal (case-insensitive per the CSS-uppercase note).
    body = page.text_content("#refinementScopeBody") or ""
    assert "metric you did not provide" in body.lower()

    # Cancel resolves 'cancel' and hides the modal.
    page.click("#btnRefineCancelScope")
    page.wait_for_function("() => window.__refine === 'cancel'", timeout=DEFAULT_TIMEOUT_MS)
    page.wait_for_selector(f"{_MODAL}.hidden", state="attached", timeout=DEFAULT_TIMEOUT_MS)

    # Re-open and Proceed resolves 'proceed' (flags, never blocks).
    page.evaluate(
        "() => { window.__refine2 = 'PENDING';"
        " _showRefinementScopeModal('x', null).then(r => { window.__refine2 = r; }); }"
    )
    page.wait_for_selector(f"{_MODAL}:not(.hidden)", timeout=DEFAULT_TIMEOUT_MS)
    page.click("#btnRefineProceed")
    page.wait_for_function("() => window.__refine2 === 'proceed'", timeout=DEFAULT_TIMEOUT_MS)
