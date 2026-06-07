"""Regression: a brand-new (config-only, not-yet-onboarded) user produces no
client-visible 4xx across the tab sweep — just the import CTA.

Reported during v1.0.5 verification: creating the first user and clicking
across the tabs logged a cascade of `409 (CONFLICT)` console errors, one per
passive tab load::

    GET /api/users/<u>/personas       (template picker + owned grid)
    GET /api/users/<u>/applications
    GET /api/users/<u>/clarifications
    GET /api/users/<u>/experiences

The GET *read* endpoints were signalling "no corpus row yet" with a 409, which
the browser logs red regardless of how the JS handled it.

Fix (refactor/needs-onboarding-200-on-reads): GET reads now signal
needs-onboarding via ``200 + {needs_onboarding: true, <empty>}`` — a read
precondition is not a conflict — so the console stays clean and the import CTA
still renders. POST *writes* keep 409.

The `page` fixture's sentinel deliberately ignores benign 4xx console noise
(see conftest), so this test captures responses directly and asserts ZERO 4xx
on any ``/api/users/<u>/...`` call across the full select + tab sweep.

LLM-free: seeds a config-only user (no Candidate row) directly — the exact
brand-new-user state.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, Response

from tests.ux.seeding import write_user_config
from ui_pages import BasePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Corpus, Memory, Onboarding, Personas, PriorApps, TopTabs


@pytest.mark.ux
@pytest.mark.slow
def test_new_user_tab_sweep_has_no_4xx(page: Page, live_server: str,
                                       ux_app: ModuleType) -> None:
    # Config only, NO Candidate row — the brand-new-user state that used to
    # 409 across every read endpoint.
    write_user_config(ux_app, "robert")

    read_4xx: list[str] = []

    def _on_response(resp: Response) -> None:
        if 400 <= resp.status < 500 and "/api/users/" in resp.url:
            read_4xx.append(f"{resp.status} {resp.request.method} {resp.url}")

    page.on("response", _on_response)

    BasePage(page, live_server).load()
    # onUserSelect fires the eager reads (applications + personas) immediately.
    UserPickerPage(page, live_server).select("robert")
    page.wait_for_load_state("networkidle")

    # Sweep every tab that fires a passive read on activation.
    for tab, panel in (
        (TopTabs.CORPUS, Corpus.PANEL),          # GET /experiences (+ /duplicates)
        (TopTabs.PERSONAS, Personas.PANEL),      # GET /personas (owned + picker)
        (TopTabs.MEMORY, Memory.PANEL),          # GET /clarifications
        (TopTabs.APPLICATION, PriorApps.PANEL),  # GET /applications
    ):
        page.click(tab)
        page.wait_for_selector(panel, state="visible", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_load_state("networkidle")

    assert read_4xx == [], f"new-user 4xx across the tab sweep: {read_4xx}"

    # The graceful path is positively present, not merely silent: the Corpus
    # tab shows the shared import CTA (was "Failed to load…" before the fix).
    page.click(TopTabs.CORPUS)
    page.wait_for_selector(Corpus.PANEL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.get_by_role("button", name=Onboarding.CTA_NAME).first.wait_for(
        state="visible", timeout=DEFAULT_TIMEOUT_MS
    )
