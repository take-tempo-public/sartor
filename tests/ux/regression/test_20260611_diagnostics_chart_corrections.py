"""UX regression — Sprint 6.2 diagnostics-console chart/layout corrections.

Guards the three v1.0.6 kickoff-walkthrough findings on `/_dashboard`, plus the
KW13 space-usage restructure:

  KW13 — tile details render in a **full-width inline panel** (was a 560px side
         drawer), so they use the available page width.
  #12  — the Calls (throughput) detail fits with **no horizontal scrollbar**.
  #13  — the latest-trace bars scale to the **longest span** (max → 100%), so a
         short span stays visible instead of collapsing to an invisible sliver
         (the old share-of-total scaling).
  #11  — the cost-by-kind chart plots the **total** with an explicit tooltip
         naming total + count + mean, so it can't be misread as a per-call mean.

Seeds call telemetry by monkeypatching the dashboard blueprint's module globals
(EVAL_RESULTS_DIR / LLM_LOG read at request time → visible to the live server
thread), the same idiom as tests/ux/flows/test_dashboard_console.py.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage

# One run whose spans differ sharply in latency: synthesis (60s) dominates, so
# clarify (4s) would be an invisible sliver if bars scaled to the run total
# instead of the longest span. Tokens are present so the cost rollup has data.
_RUN = "uxr62trace"
_CALLS = [
    {"timestamp": "2026-06-11T00:00:01Z", "username": "eval:pm-senior", "run_id": _RUN,
     "call": "analyze_extraction", "model": "claude-haiku-4-5-20251001", "prompt_version": "2026-06-11.1",
     "input_tokens": 1200, "output_tokens": 400, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 0, "latency_ms": 5000, "stop_reason": "end_turn", "status": "ok"},
    {"timestamp": "2026-06-11T00:00:06Z", "username": "eval:pm-senior", "run_id": _RUN,
     "call": "analyze_synthesis", "model": "claude-sonnet-4-6", "prompt_version": "2026-06-11.1",
     "input_tokens": 3000, "output_tokens": 2600, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 2000, "latency_ms": 60000, "stop_reason": "end_turn", "status": "ok"},
    {"timestamp": "2026-06-11T00:01:06Z", "username": "eval:pm-senior", "run_id": _RUN,
     "call": "clarify", "model": "claude-haiku-4-5-20251001", "prompt_version": "2026-06-11.1",
     "input_tokens": 1500, "output_tokens": 600, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 0, "latency_ms": 4000, "stop_reason": "end_turn", "status": "ok"},
    {"timestamp": "2026-06-11T00:01:10Z", "username": "eval:pm-senior", "run_id": _RUN,
     "call": "generate", "model": "claude-sonnet-4-6", "prompt_version": "2026-06-11.1",
     "input_tokens": 4000, "output_tokens": 2300, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 3500, "latency_ms": 50000, "stop_reason": "end_turn", "status": "ok"},
]


@pytest.mark.ux
def test_diagnostics_chart_corrections(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    from dashboard import routes as dash_routes

    results_dir = tmp_path / "results"  # empty: the Pipeline tab needs only call telemetry
    results_dir.mkdir()
    llm_log = tmp_path / "llm_calls.jsonl"
    llm_log.write_text("\n".join(json.dumps(c) for c in _CALLS) + "\n", encoding="utf-8")
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", results_dir)
    monkeypatch.setattr(dash_routes, "LLM_LOG", llm_log)

    dash = DashboardConsolePage(page, live_server).load()

    # --- KW13 + #12: open Calls in the full-width inline panel, no h-scroll ---
    dash.open_tile("throughput")
    expect(dash.detail_panel_open()).to_be_visible()
    panel_w = dash.detail_panel().evaluate("el => el.clientWidth")
    assert panel_w > 700, f"detail panel should use the page width, got {panel_w}px (drawer was 560)"
    overflow = dash.detail_body().evaluate("el => el.scrollWidth - el.clientWidth")
    assert overflow <= 1, f"Calls panel overflows horizontally by {overflow}px (#12)"
    dash.close_detail()
    expect(dash.detail_panel_open()).to_have_count(0)

    # --- #13: trace bars scale to the longest span, short spans stay visible ---
    dash.open_tile("trace")
    expect(dash.detail_panel_open()).to_be_visible()
    bars = dash.detail_body().locator(".wf-bar")
    expect(bars).to_have_count(len(_CALLS))
    rows = bars.evaluate_all(
        """els => els.map(e => {
            const track = e.closest('.wf-track');
            const row = e.closest('.wf-row');
            return {
                barPx: e.offsetWidth,
                trackPx: track ? track.offsetWidth : 0,
                label: row ? row.querySelector('.lbl').textContent.trim() : '',
            };
        })"""
    )
    # Every populated bar is at least the 2px min-width floor (none collapses).
    assert all(r["barPx"] >= 2 for r in rows), f"a populated trace bar is invisible: {rows}"
    # The longest span (analyze_synthesis, 60s) fills its track (~100%). Under the
    # old share-of-total scaling it would be ~60000/119000 ≈ 50% — this ratio is
    # the discriminator between the fix and the regression.
    synth = next(r for r in rows if r["label"] == "analyze_synthesis")
    assert synth["trackPx"] > 0 and synth["barPx"] / synth["trackPx"] >= 0.97, (
        f"longest span should fill the bar (share-of-max), got {synth}"
    )
    dash.close_detail()

    # --- #11: cost-by-kind plots the total, with an unambiguous tooltip ---
    dash.open_tile("cost")
    expect(dash.detail_panel_open()).to_be_visible()
    # Server-rendered evidence (always present, no Chart.js needed): the cost
    # table lists call kinds with both a total and a mean column.
    expect(dash.detail_body().locator("table")).to_contain_text("generate")
    # Chart.js loads from a CDN; when unavailable (offline CI) the chart degrades
    # to the table above, so the chart-internal tooltip assertion is best-effort.
    tip = page.evaluate(
        """() => {
            if (typeof Chart === 'undefined') return null;
            const ch = Chart.getChart('chart-cost-by-kind');
            if (!ch) return null;
            return ch.options.plugins.tooltip.callbacks.label({dataIndex: 0});
        }"""
    )
    if tip is not None:
        assert "total $" in tip and "mean $" in tip, f"ambiguous cost tooltip: {tip!r}"
