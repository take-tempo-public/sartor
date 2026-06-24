"""Regression: the in-app education sweep (Sprint 6.5,
feat/education-tailor-corpus-wizard — the COPY/CONTENT, branch 2 of the sweep).

The mechanism branch (feat/help-pattern-component) shipped the reusable help
primitive against a single demo entry; this branch authors the per-surface copy
and the KW3 new-user first-run tour. These tests cover the *application* of the
primitive, not the primitive itself (that lives in test_20260614_help_pattern):

- every user-facing panel got its (i)-circle with correct aria wiring;
- a representative panel of each header type (regular + wizard step header)
  opens its modal, shows the registered title, and restores focus on close;
- the KW3 tour is new-users-only: a stop fires only while the tour is *armed*,
  fires once-ever, and a wizard stop fires only when its panel is on screen
  (never while it sits on a hidden top tab).

The auto-firing welcome + tour stops are default-suppressed for the rest of the
UX suite by the ``_help_welcome_default_seen`` autouse fixture; tour tests here
opt in with ``@pytest.mark.show_tour`` (see tests/ux/conftest.py).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page

from ui_pages import BasePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Help

# Every panel that carries an on-demand (i) help icon (injected at load by
# _initHelp into each registered .cb-panel, visible or not).
_ALL_HELP_PANELS = [
    "panelUser",
    "panelApplications",
    "panelJD",
    "panelAnalysis",
    "panelClarify",
    "panelCompose",
    "panelTemplate",
    "panelGenerate",
    "panelOutput",
    "panelCorpus",
    "panelPersonas",
    "panelMemory",
]


@pytest.mark.ux
@pytest.mark.slow
def test_every_panel_has_help_icon(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """Each registered panel gets an (i) with real dialog semantics and a
    non-empty accessible name — the meaning rides the glyph + label, not colour.

    Icons are injected at load regardless of panel visibility, so one page load
    covers every surface (no per-panel navigation needed)."""
    BasePage(page, live_server).load()
    for block_id in _ALL_HELP_PANELS:
        icon = Help.icon(block_id)
        page.wait_for_selector(icon, state="attached", timeout=DEFAULT_TIMEOUT_MS)
        assert page.get_attribute(icon, "aria-haspopup") == "dialog", block_id
        assert page.get_attribute(icon, "aria-controls") == "helpModal", block_id
        label = page.get_attribute(icon, "aria-label") or ""
        assert label.startswith("Help: "), block_id
        assert label.removeprefix("Help: ").strip(), block_id
        assert (page.locator(icon).text_content() or "").strip() == "i", block_id
        assert (page.get_attribute(icon, "title") or "").strip(), block_id  # tip


# (block_id, top-tab button to click first, reveal-via-class) — one panel per
# header style reachable WITHOUT a user: panelUser (regular header, landing),
# panelCorpus (regular header, Career corpus tab — no-user-safe), panelJD
# (wizard STEP header — exercises the .cb-step-header align-self CSS).
_OPEN_CYCLE = [
    ("panelUser", None, False),
    ("panelCorpus", "#topTabCorpus", False),
    ("panelJD", None, True),
]


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.parametrize("block_id, tab_btn, reveal", _OPEN_CYCLE)
def test_panel_help_opens_and_restores_focus(
    page: Page,
    live_server: str,
    ux_app: ModuleType,
    block_id: str,
    tab_btn: str | None,
    reveal: bool,
) -> None:
    BasePage(page, live_server).load()
    if reveal:  # step panels start hidden until the wizard reveals them
        page.evaluate(f"() => document.getElementById('{block_id}').classList.remove('hidden')")
    if tab_btn:
        page.click(tab_btn)

    icon = Help.icon(block_id)
    page.wait_for_selector(icon, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert page.locator(Help.MODAL).is_hidden()

    # The icon's accessible name carries the block's title; the modal must show
    # that same title — a consistency check that never hardcodes copy.
    expected = (page.get_attribute(icon, "aria-label") or "").removeprefix("Help: ").strip()
    assert expected, block_id

    page.click(icon)
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert (page.locator(Help.MODAL_TITLE).text_content() or "").strip() == expected
    assert (page.locator(Help.MODAL_BODY).text_content() or "").strip()
    assert page.get_attribute(icon, "aria-expanded") == "true"

    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)
    assert page.get_attribute(icon, "aria-expanded") == "false"
    active_id = page.evaluate("() => document.activeElement && document.activeElement.id")
    assert active_id == f"help-icon-{block_id}"


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_tour
def test_welcome_autoopens_under_tour(page: Page, live_server: str, ux_app: ModuleType) -> None:
    """With the tour opted in (nothing pre-seeded), the welcome still fires on
    first view — it is the entry point of the KW3 sequence."""
    BasePage(page, live_server).load()
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    title = (page.locator(Help.MODAL_TITLE).text_content() or "").strip()
    assert "welcome" in title.lower()


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_tour
def test_tour_stop_requires_arming_and_fires_once(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """A tour stop is gated by the in-memory armed flag (new-users-only) and the
    once-ever cb_help_seen seam: returning users (never armed) never see it, and
    an armed stop never re-fires after it has been shown once."""
    BasePage(page, live_server).load()
    # Dismiss the welcome that show_tour lets fire on load.
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Not armed (the returning-user case) → the stop does nothing.
    page.evaluate("() => _maybeFireTourStop('panelCorpus', null)")
    assert page.locator(Help.MODAL).is_hidden()

    # Arm → the stop fires.
    page.evaluate("() => { _armHelpTour(); _maybeFireTourStop('panelCorpus', null); }")
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert (page.locator(Help.MODAL_TITLE).text_content() or "").strip()
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Once-ever: a second fire (still armed) does NOT reopen it.
    page.evaluate("() => _maybeFireTourStop('panelCorpus', null)")
    assert page.locator(Help.MODAL).is_hidden()


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_tour
def test_wizard_stop_fires_only_when_panel_visible(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """A wizard step's tour stop must not fire while its panel sits on a hidden
    top tab (offsetParent === null), only once the Tailor tab brings it on
    screen."""
    BasePage(page, live_server).load()
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    page.click(Help.CLOSE)
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Arm + reveal step 1's panel, then move to a DIFFERENT top tab so the panel
    # is hidden by its parent → the stop must NOT fire.
    page.evaluate(
        "() => { _armHelpTour(); _wizardStep = 1;"
        " document.getElementById('panelJD').classList.remove('hidden');"
        " switchTopTab('corpus', document.getElementById('topTabCorpus'));"
        " _fireWizardTourStop(); }"
    )
    assert page.locator(Help.MODAL).is_hidden()

    # Back on the Tailor tab the panel is on screen → switchTopTab fires the stop.
    page.evaluate("() => switchTopTab('tailor', document.getElementById('topTabTailor'))")
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert "Step 1" in (page.locator(Help.MODAL_TITLE).text_content() or "")
