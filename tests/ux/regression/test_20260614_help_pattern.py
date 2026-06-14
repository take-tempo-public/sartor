"""Regression: the reusable in-app help primitive (Sprint 6.5,
feat/help-pattern-component — the MECHANISM, branch 1 of the education sweep).

Covers the primitive's behaviour against its single demo registry entry on
``#panelUser`` (no LLM, no user needed — the panel is the landing block):

- first-view auto-modal opens on first view (``show_welcome`` opt-in), with
  real, non-empty canonical copy;
- it closes on click-away (the ``data-help-dismiss`` backdrop);
- it shows once-ever — a reload does not re-fire it (the ``cb_help_seen:*``
  localStorage gate the feature ships);
- the injected ``.help-info`` (i)-circle re-opens that block's modal, with
  correct aria wiring and no color-only meaning (literal "i" glyph + aria-label);
- closing restores focus to the icon (keyboard users keep their place);
- the inline short-form is injected and associated via ``aria-describedby``.

The welcome auto-modal is default-suppressed for the rest of the UX suite by the
``_help_welcome_default_seen`` autouse fixture; tests here that need the genuine
first view opt in with ``@pytest.mark.show_welcome`` (see tests/ux/conftest.py).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Help

_ICON = Help.icon("panelUser")


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_welcome
def test_welcome_auto_opens_on_first_view(page: Page, live_server: str,
                                          ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()

    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    # Canonical copy is present, not an empty shell. text_content() (not
    # inner_text) reads the raw DOM regardless of any CSS text-transform.
    title = (page.locator(Help.MODAL_TITLE).text_content() or "").strip()
    body = (page.locator(Help.MODAL_BODY).text_content() or "").strip()
    assert title, "welcome modal title is empty"
    assert body, "welcome modal body is empty"
    assert "welcome" in title.lower()


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_welcome
def test_welcome_closes_on_click_away(page: Page, live_server: str,
                                      ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    # Click the backdrop near a corner — the centered content sits over the
    # middle, so an offset click lands on the dismiss backdrop, not the content.
    page.click(Help.BACKDROP, position={"x": 5, "y": 5})
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_welcome
def test_welcome_shows_once_only(page: Page, live_server: str,
                                 ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()
    # First view fires (and the app stamps the cb_help_seen flag)...
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    # ...so a reload in the same browser context must NOT re-open it.
    page.reload()
    page.wait_for_selector(Help.MODAL_TITLE, state="attached",
                           timeout=DEFAULT_TIMEOUT_MS)
    assert page.locator(Help.MODAL).is_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_icon_reopens_block_modal(page: Page, live_server: str,
                                  ux_app: ModuleType) -> None:
    # Welcome suppressed (no show_welcome marker) → the landing has no overlay.
    BasePage(page, live_server).load()
    page.wait_for_selector(_ICON, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert page.locator(Help.MODAL).is_hidden()

    # The icon's accessible name carries the block's title; the modal it opens
    # must show that same title — a consistency check that doesn't hardcode copy.
    icon_label = page.get_attribute(_ICON, "aria-label") or ""
    expected_title = icon_label.removeprefix("Help: ").strip()
    assert expected_title

    page.click(_ICON)
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert (page.locator(Help.MODAL_TITLE).text_content() or "").strip() == expected_title
    assert page.get_attribute(_ICON, "aria-expanded") == "true"


@pytest.mark.ux
@pytest.mark.slow
def test_closing_restores_focus_to_icon(page: Page, live_server: str,
                                        ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()
    page.wait_for_selector(_ICON, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    page.click(_ICON)
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    active_id = page.evaluate("() => document.activeElement && document.activeElement.id")
    assert active_id == "help-icon-panelUser"
    assert page.get_attribute(_ICON, "aria-expanded") == "false"


@pytest.mark.ux
@pytest.mark.slow
def test_help_aria_wiring_and_no_color_only_meaning(page: Page, live_server: str,
                                                    ux_app: ModuleType) -> None:
    BasePage(page, live_server).load()
    page.wait_for_selector(_ICON, state="visible", timeout=DEFAULT_TIMEOUT_MS)

    # Icon: real semantics, and a text glyph + label carry the meaning (not color).
    assert page.get_attribute(_ICON, "aria-haspopup") == "dialog"
    assert page.get_attribute(_ICON, "aria-controls") == "helpModal"
    assert (page.get_attribute(_ICON, "aria-label") or "").startswith("Help: ")
    assert (page.locator(_ICON).text_content() or "").strip() == "i"

    # Modal: dialog semantics, and labelledby/describedby resolve to the live nodes.
    assert page.get_attribute(Help.MODAL, "role") == "dialog"
    assert page.get_attribute(Help.MODAL, "aria-modal") == "true"
    assert page.get_attribute(Help.MODAL, "aria-labelledby") == "helpModalTitle"
    assert page.get_attribute(Help.MODAL, "aria-describedby") == "helpModalBody"

    # Inline short-form is injected atop the panel and associated for AT.
    inline = page.locator(Help.INLINE).first
    assert (inline.text_content() or "").strip()
    described_by = page.get_attribute("#panelUser", "aria-describedby") or ""
    assert "help-inline-panelUser" in described_by
