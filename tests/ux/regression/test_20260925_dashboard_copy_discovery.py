"""UX regression — Epic C C3 (`feat/dashboard-copy-discovery`): lay copy +
progressive discovery (UX-9, UX-10, UX-13, UX-14; the copy-content checks for
UX-11/15..21/42 live in `tests/test_dashboard_copy.py`, which needs no browser).

Scope: `docs/dev/handoffs/epic-c-c3-brief.md`, `docs/dev/RELEASE_ARC.md`
§Epic C (C3), `docs/dev/reviews/epic-c-console-ux-audit.md`; consumer
enumeration + re-derived cites: `docs/dev/blast-radius/dashboard-copy-discovery.md`.

The route-level test proves every `data-help` id is a key of the registry. This
one proves the key actually OPENS something in a real browser: for every tile on
every tab, its sibling (i) opens the shared `#helpModal` with the registered
title (compared against the (i)'s own accessible name — never hardcoded copy)
and a non-empty body. It also drives UX-14's live spend estimate, the one piece
of new JS behaviour.

Seeds eval + call telemetry by monkeypatching the dashboard blueprint's module
globals (read at request time -> visible to the live server thread), the idiom
of `tests/ux/flows/test_dashboard_console.py`.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage
from ui_pages.base import DEFAULT_TIMEOUT_MS
from ui_pages.selectors import Dashboard, Help

_RECORD = {
    "schema_version": 3,
    "source": "eval",
    "fixture": "pm-senior",
    "rubric": "grounding",
    "score": 4.5,
    "status": "ok",
    "prompt_version": "2026-09-25.1",
    "run_id": "uxc3run1",
    "timestamp": "2026-09-25T12:00:00Z",
    "failed_rules": ["invented_metric"],
    "deterministic_metrics": {
        "groundedness": {
            "layers": ["L0"],
            "fabricated_specifics_rate": 0.1,
            "flagged_count": 1,
            "score": 4.2,
        },
        "fabricated_specifics": {
            "total_bullets": 4,
            "total_specifics": 10,
            "flagged": 1,
            "fabricated_specifics_rate": 0.1,
            "per_bullet": [],
            "flagged_samples": ["$5M"],
        },
    },
}
_BASELINE = {
    "baseline_id": "v1-ux",
    "prompt_version": "2026-09-01.1",
    "fixtures": {"pm-senior": {"grounding": {"mean": 4.6}}},
}
_CALLS = [
    {
        "timestamp": "2026-09-25T12:00:01Z",
        "username": "eval:pm-senior",
        "run_id": "uxc3run1",
        "call": "generate",
        "model": "claude-sonnet-5",
        "prompt_version": "2026-09-25.1",
        "input_tokens": 1000,
        "output_tokens": 400,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 4000,
        "stop_reason": "end_turn",
        "status": "ok",
    },
]

# Tiles rendered per tab with the data above (the audit's UX-9 count).
_TILES_PER_TAB = {"pipeline": 5, "quality": 7, "groundedness": 2, "tuning": 2}


def _seed(monkeypatch, tmp_path) -> None:
    from dashboard import routes as dash_routes

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "seed.jsonl").write_text(json.dumps(_RECORD) + "\n", encoding="utf-8")
    (results_dir / "baseline_v1.json").write_text(json.dumps(_BASELINE), encoding="utf-8")
    log = tmp_path / "llm_calls.jsonl"
    log.write_text("\n".join(json.dumps(c) for c in _CALLS) + "\n", encoding="utf-8")
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", results_dir)
    monkeypatch.setattr(dash_routes, "LLM_LOG", log)


def _assert_help_opens(page: Page, dash: DashboardConsolePage, icon) -> None:
    expected = (icon.get_attribute("aria-label") or "").removeprefix("Help: ").strip()
    assert expected, icon.get_attribute("data-help")
    icon.click()
    page.wait_for_selector(Help.MODAL, state="visible", timeout=DEFAULT_TIMEOUT_MS)
    assert (page.locator(Help.MODAL_TITLE).text_content() or "").strip() == expected
    assert (page.locator(Help.MODAL_BODY).text_content() or "").strip()
    dash.close_help()
    page.wait_for_selector(Help.MODAL, state="hidden", timeout=DEFAULT_TIMEOUT_MS)


@pytest.mark.ux
@pytest.mark.slow
def test_every_tile_shows_lay_line_and_its_help_opens(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """UX-9: every tile on every tab shows a lay line on screen, and its (i)
    opens the registered explainer."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()
    for tab, n_tiles in _TILES_PER_TAB.items():
        if tab != "pipeline":
            dash.activate_tab(tab)
        pane = dash.active_pane(tab)
        expect(pane).to_be_visible()
        tiles = pane.locator(Dashboard.TILE)
        expect(tiles).to_have_count(n_tiles)
        lays = pane.locator(Dashboard.TILE_LAY)
        expect(lays).to_have_count(n_tiles)
        for i in range(n_tiles):
            expect(lays.nth(i)).to_be_visible()
            assert (lays.nth(i).text_content() or "").strip(), (tab, i)
        icons = pane.locator(Dashboard.TILE_HELP)
        expect(icons).to_have_count(n_tiles)
        for i in range(n_tiles):
            _assert_help_opens(page, dash, icons.nth(i))


@pytest.mark.ux
@pytest.mark.slow
def test_filter_scope_note_and_percentile_explainer(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """UX-13: the filter-scope note is on screen next to the filters and its (i)
    opens. UX-10: the latency detail carries a percentile explainer one click
    away."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()
    note = page.locator(Dashboard.FILTER_SCOPE)
    expect(note).to_be_visible()
    expect(note).to_contain_text("Pipeline")
    _assert_help_opens(page, dash, note.locator(Help.ICON))

    dash.open_tile("latency")
    expect(dash.detail_panel_open()).to_be_visible()
    _assert_help_opens(page, dash, dash.detail_body().locator(Help.ICON).first)


@pytest.mark.ux
@pytest.mark.slow
def test_bootstrap_spend_estimate_tracks_filled_jd_rows(
    page: Page, live_server: str, ux_app: ModuleType
) -> None:
    """UX-14: the no-confirmation warning is on screen, and the live estimate
    counts only rows with BOTH a name and text (exactly what runBootstrap()
    sends), updating as rows are filled, added and removed."""
    dash = DashboardConsolePage(page, live_server).load()
    dash.activate_tab("annotate")
    page.locator(Dashboard.ANN_BOOTSTRAP_SECTION).evaluate("el => { el.open = true; }")
    expect(page.locator("#bsNoConfirm")).to_contain_text("No confirmation step")
    spend = page.locator(Dashboard.ANN_BS_SPEND)
    expect(spend).to_contain_text("nothing will be spent")

    rows = page.locator(".ann-jd-row")
    rows.nth(0).locator(".bs-jd-name").fill("acme-pm")
    expect(spend).to_contain_text("nothing will be spent")  # name alone isn't a run
    rows.nth(0).locator(".bs-jd-text").fill("Senior PM at Acme.")
    expect(spend).to_contain_text("1 paid pipeline run")

    page.locator(Dashboard.ANN_BS_ADD_JD).click()
    rows.nth(1).locator(".bs-jd-name").fill("zeta-pm")
    rows.nth(1).locator(".bs-jd-text").fill("PM at Zeta.")
    expect(spend).to_contain_text("2 paid pipeline runs")

    rows.nth(1).locator("button[aria-label='Remove JD']").click()
    expect(spend).to_contain_text("1 paid pipeline run")
