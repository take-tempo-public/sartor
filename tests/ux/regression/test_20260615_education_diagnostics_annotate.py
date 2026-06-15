"""Regression: in-app education for the /_dashboard diagnostics console
(Sprint 6.5, feat/education-diagnostics-annotate — KW9 + KW13).

The console is self-contained (it never loads static/app.js), so it carries its
own PORT of the wizard help primitive: a #helpModal, a per-tab _DASH_HELP
registry, a per-pane summary line + (i)-circle, and a first-expand explainer that
auto-opens once-ever per tab. These tests cover that application:

- every diagnostics tab has a summary line + an (i) with real dialog aria;
- a pane's (i) opens the shared #helpModal, shows its registered title, and
  restores focus to the icon on close;
- the per-tab explainer auto-fires once on first view (Pipeline on load) and never
  re-fires (the cb_help_seen once-ever seam);
- the annotate verdict legend reads in plain language;
- the bootstrap panel auto-expands when there are no fixtures to annotate;
- the per-tab "why empty" copy explains what populates each panel.

The auto-firing explainers are default-suppressed for the rest of the UX suite by
the ``_help_welcome_default_seen`` autouse fixture (the five ``dash*`` ids were
added to ``_TOUR_STOP_BLOCKS``). Tests that need a modal to fire opt in with
``@pytest.mark.show_tour`` — on the dashboard that marker simply means "don't seed
the cb_help_seen ids"; there is no KW3 arming path here (the wizard's once-ever
tour-arming is a separate, user-facing mechanism).
"""

from __future__ import annotations

from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Dashboard, Help

_TABS = ["pipeline", "quality", "groundedness", "tuning", "annotate"]


@pytest.mark.ux
@pytest.mark.slow
def test_every_dash_pane_has_help_icon(page: Page, live_server: str,
                                       ux_app: ModuleType) -> None:
    """Each diagnostics tab carries an (i) with real dialog semantics and a
    non-empty accessible name — the meaning rides the glyph + label, not colour.

    The icons are static markup present at load regardless of pane visibility, so
    one page load covers every tab (inactive panes are display:none, so assert on
    the attached element)."""
    dash = DashboardConsolePage(page, live_server).load()
    for tab in _TABS:
        icon = Help.icon(dash._HELP_ID[tab])
        page.wait_for_selector(icon, state="attached", timeout=DEFAULT_TIMEOUT_MS)
        assert page.get_attribute(icon, "aria-haspopup") == "dialog", tab
        assert page.get_attribute(icon, "aria-controls") == "helpModal", tab
        label = page.get_attribute(icon, "aria-label") or ""
        assert label.startswith("Help: "), tab
        assert label.removeprefix("Help: ").strip(), tab
        assert (page.locator(icon).text_content() or "").strip() == "i", tab
        assert (page.get_attribute(icon, "title") or "").strip(), tab  # tip


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.parametrize("tab", ["pipeline", "groundedness", "annotate"])
def test_dash_help_opens_and_restores_focus(page: Page, live_server: str,
                                            ux_app: ModuleType, tab: str) -> None:
    """A pane's (i) opens the ported #helpModal with the registered title and
    restores focus to the icon on close. The first-view auto-modal is suppressed
    for this test, so opening it via the (i) is independent of the localStorage
    gate."""
    dash = DashboardConsolePage(page, live_server).load()
    if tab != "pipeline":  # pipeline is the default-active pane
        dash.activate_tab(tab)
    expect(dash.active_pane(tab)).to_be_visible()
    # Activating the tab must not auto-fire (suppressed) — drive the icon instead.
    assert dash.help_modal().is_hidden()

    icon = dash.help_icon(tab)
    # The icon's accessible name carries the block title; the modal must show the
    # same title — a consistency check that never hardcodes copy.
    expected = (page.get_attribute(Help.icon(dash._HELP_ID[tab]), "aria-label")
                or "").removeprefix("Help: ").strip()
    assert expected, tab

    dash.open_help(tab)
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert (page.locator(Help.MODAL_TITLE).text_content() or "").strip() == expected
    assert (page.locator(Help.MODAL_BODY).text_content() or "").strip()
    assert icon.get_attribute("aria-expanded") == "true"

    dash.close_help()
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)
    assert icon.get_attribute("aria-expanded") == "false"
    active_id = page.evaluate("() => document.activeElement && document.activeElement.id")
    assert active_id == f"help-icon-{dash._HELP_ID[tab]}"


@pytest.mark.ux
@pytest.mark.slow
@pytest.mark.show_tour
def test_dash_explainer_autoopens_once_per_tab(page: Page, live_server: str,
                                               ux_app: ModuleType) -> None:
    """With the explainers opted in (nothing seeded), the Pipeline explainer
    auto-opens on first load, each other tab's auto-opens on its first click, and
    none re-fires (the cb_help_seen once-ever seam)."""
    dash = DashboardConsolePage(page, live_server).load()

    # Pipeline is the welcome-equivalent: auto-opens on first view.
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert "Pipeline" in (page.locator(Help.MODAL_TITLE).text_content() or "")
    dash.close_help()
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # First click on another tab fires that tab's explainer once.
    dash.activate_tab("quality")
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert "Quality" in (page.locator(Help.MODAL_TITLE).text_content() or "")
    dash.close_help()
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # Once-ever: returning to a seen tab does NOT re-fire (pipeline already fired
    # on load; quality already fired above).
    dash.activate_tab("pipeline")
    assert dash.help_modal().is_hidden()
    dash.activate_tab("quality")
    assert dash.help_modal().is_hidden()


@pytest.mark.ux
@pytest.mark.slow
def test_dash_verdict_legend_is_plain_language(page: Page, live_server: str,
                                               ux_app: ModuleType) -> None:
    """The annotate verdict legend keeps the contract codes but glosses each in
    lay terms. The legend lives in the (initially hidden) editor, so read its
    text_content rather than requiring it on screen."""
    DashboardConsolePage(page, live_server).load()
    legend = page.text_content("#annEditor .legend") or ""
    low = legend.lower()
    # contract codes still present...
    for code in ("keep", "fix", "omit", "fabricated"):
        assert code in low, code
    # ...now with a plain-language gloss (not just the raw field names).
    assert "true and usable as written" in low
    assert "not supported by the candidate" in low


@pytest.mark.ux
@pytest.mark.slow
def test_dash_bootstrap_autoexpands_when_no_fixtures(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """With no bootstraps to annotate, step ① auto-expands so the user sees how to
    produce one. Point ANNOTATION_ROOT at an empty dir so the fixtures list is
    deterministically empty (it's read at request time → visible to the live
    server thread)."""
    empty_root = tmp_path / "no_fixtures"
    empty_root.mkdir()
    monkeypatch.setattr(ux_app, "ANNOTATION_ROOT", empty_root)

    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    # loadFixtures() runs on IIFE init, fetches the (empty) list, and opens the
    # <details>; the `open` attribute reflects regardless of pane visibility.
    page.wait_for_selector(
        f"{Dashboard.ANN_BOOTSTRAP_SECTION}[open]", state="attached",
        timeout=DEFAULT_TIMEOUT_MS,
    )


@pytest.mark.ux
@pytest.mark.slow
def test_dash_why_empty_copy_explains_what_populates(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """Each empty-state says what the panel is and what populates it (KW13). Point
    the eval/log paths at empty temps so the empty-states render regardless of any
    real results in the repo working tree."""
    from dashboard import routes as dash_routes

    empty_results = tmp_path / "results"
    empty_results.mkdir()
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", empty_results)
    monkeypatch.setattr(dash_routes, "LLM_LOG", tmp_path / "no_calls.jsonl")

    dash = DashboardConsolePage(page, live_server).load()
    expect(dash.active_pane("pipeline")).to_contain_text("Nothing to chart yet")

    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_contain_text("No eval scores yet")

    dash.activate_tab("groundedness")
    expect(dash.active_pane("groundedness")).to_contain_text("No groundedness scores yet")
