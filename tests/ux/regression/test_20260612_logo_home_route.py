"""Regression: clicking the wordmark routes home (#23, Sprint 6.4).

Bug: the `.cb-wordmark` logo was an inert `<a href="#">` — clicking it did
nothing, so once a user was selected (and the wizard/another tab engaged) there
was no way back to the landing state. Fix wires it to ``goHome()``: clear the
selected user via ``onUserSelect()``'s no-user branch (hides the flow panels,
re-locks the picker open, resets iteration state) and snap back to the default
Tailor tab.

This test drives a user → off-tab → wordmark click and asserts the home state:
default tab restored, user deselected, picker re-locked, flow panel hidden. The
`page` fixture's sentinel additionally proves ``goHome()`` raises no JS error and
fires no 5xx.

Sprint 6.4 smart landing: ``goHome()`` now routes through ``_landingTab()``.
Since it deselects the user first, that resolves to the picker's home — the
Tailor tab — so the "lands on Tailor" assertion below still holds. alice is now
seeded **non-empty** so selecting her lands on Tailor/applications (an empty
corpus would smart-land on the Career corpus tab instead).

LLM-free: seeds a user + one experience directly; no analyzer entry points are
hit.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from tests.ux.seeding import seed_exp_with_bullets, seed_user
from ui_pages import BasePage, UserPickerPage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Header, PriorApps, TopTabs, UserPicker


@pytest.mark.ux
@pytest.mark.slow
def test_wordmark_routes_home(page: Page, live_server: str,
                              ux_app: ModuleType) -> None:
    # Non-empty corpus so smart landing puts alice on Tailor/applications
    # (an empty corpus would land on Career corpus — see test_20260612_corpus_first_landing).
    cid = seed_user(ux_app, "alice")
    seed_exp_with_bullets(cid)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    # A user is selected → the applications panel is up. Move off the default
    # tab so "home" has a tab to restore, not just a user to deselect.
    page.wait_for_selector(PriorApps.PANEL, state="visible",
                           timeout=DEFAULT_TIMEOUT_MS)
    page.click(TopTabs.CORPUS)

    # Click the wordmark — the home route.
    page.click(Header.WORDMARK)

    # Back on the default Tailor tab...
    page.wait_for_function(
        "() => document.getElementById('topTabTailor')"
        ".getAttribute('aria-selected') === 'true'",
        timeout=DEFAULT_TIMEOUT_MS,
    )
    # ...with NO user selected and the picker re-locked open as the landing view.
    assert page.eval_on_selector(UserPicker.SELECT, "el => el.value") == ""
    panel = page.locator(UserPicker.PANEL)
    assert panel.is_visible()
    assert "not-collapsible" in (panel.get_attribute("class") or "")
    # The flow panel that was up while a user was selected is gone.
    assert page.locator(PriorApps.PANEL).is_hidden()
