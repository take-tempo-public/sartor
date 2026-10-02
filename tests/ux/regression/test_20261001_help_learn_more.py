"""Regression: help bubbles link to their published doc page (Epic D, D4).

`static/help-modal.js` renders an entry's `learnMore` target as a "Read more in the docs"
link inside the shared help modal. That the slug and anchor exist is checked without a
browser by `tests/test_help_learn_more.py`. This file checks what only a browser can: the
link shows with the right URL, opens in a new tab without leaking the local referrer, joins
the modal's Tab cycle, and stays hidden for an entry without a target.
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Help

_ICON = Help.icon("panelUser")
_EXPECTED = "https://sartor-docs.taketempo.com/docs/user-walkthrough/#setup-before-the-wizard"


@pytest.mark.ux
@pytest.mark.slow
def test_bubble_links_to_its_doc_section(page: Page, live_server: str, ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()
    page.wait_for_selector(_ICON, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.click(_ICON)
    page.wait_for_selector(Help.MODAL_LEARN_MORE, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    link = page.locator(Help.MODAL_LEARN_MORE)
    assert link.get_attribute("href") == _EXPECTED
    assert link.get_attribute("target") == "_blank"
    assert set((link.get_attribute("rel") or "").split()) >= {"noopener", "noreferrer"}
    assert "new tab" in (link.get_attribute("aria-label") or "")

    # Opening focuses "Got it", the last control; Tab wraps to the first, the link.
    page.keyboard.press("Tab")
    active = page.evaluate("() => document.activeElement && document.activeElement.id")
    assert active == "helpModalLearnMore"


@pytest.mark.ux
@pytest.mark.slow
def test_entry_without_target_hides_the_link(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    BasePage(page, live_server).load()
    page.wait_for_selector(_ICON, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    # Open with a target first, so the second open has to clear it, not merely start empty.
    page.click(_ICON)
    page.wait_for_selector(Help.MODAL_LEARN_MORE, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    page.evaluate("() => window.cbOpenHelpModal({ title: 'T', body: 'B' }, null)")
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    link = page.locator(Help.MODAL_LEARN_MORE)
    assert link.is_hidden()
    assert link.get_attribute("href") is None
