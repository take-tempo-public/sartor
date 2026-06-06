"""UX walk — the redesigned /_dashboard diagnostics console.

Seeds eval + call telemetry by monkeypatching the dashboard blueprint's
module-level data paths (it reads EVAL_RESULTS_DIR / LLM_LOG as globals at
request time, so a patch is visible to the live server thread), then drives the
tabbed console: every tab activates, tiles open the shared drawer, the
groundedness evidence + trace waterfall render, Esc/close works — and the
unconditional console-error sentinel (conftest `page`) proves it renders clean.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, expect

from ui_pages import DashboardConsolePage

# One eval record carrying the 2026-06-06 groundedness contract.
_GROUNDED_RECORD = {
    "schema_version": 3,
    "source": "eval",
    "fixture": "pm-senior",
    "rubric": "grounding",
    "score": 4.5,
    "status": "ok",
    "prompt_version": "2026-06-06.1",
    "run_id": "uxrun01",
    "timestamp": "2026-06-06T12:00:00Z",
    "failed_rules": [],
    "deterministic_metrics": {
        "groundedness": {
            "layers": ["L0"],
            "fabricated_specifics_rate": 0.18,
            "flagged_count": 2,
            "score": 4.1,
        },
        "fabricated_specifics": {
            "total_bullets": 8,
            "total_specifics": 11,
            "flagged": 2,
            "fabricated_specifics_rate": 0.18,
            "per_bullet": [
                {"bullet": "Led a $5M platform migration", "n_specifics": 2, "flagged": ["$5M"]},
            ],
            "flagged_samples": ["$5M", "Kubernetes"],
        },
    },
}

# A minimal baseline so the health tile/drawer renders rows (pm-senior/grounding
# mean 4.6 vs the seeded 4.5 → delta -0.1 → ok).
_BASELINE = {
    "baseline_id": "v1.0.2_ux",
    "prompt_version": "2026-05-24.4",
    "fixtures": {"pm-senior": {"grounding": {"mean": 4.6}}},
}

# A few calls sharing a run_id so the trace waterfall has spans to draw.
_CALLS = [
    {"timestamp": "2026-06-06T12:00:01Z", "username": "eval:pm-senior", "run_id": "uxrun01",
     "call": "analyze_extraction", "model": "claude-haiku-4-5-20251001", "prompt_version": "2026-06-06.1",
     "input_tokens": 1200, "output_tokens": 400, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 0, "latency_ms": 8000, "stop_reason": "end_turn", "status": "ok"},
    {"timestamp": "2026-06-06T12:00:09Z", "username": "eval:pm-senior", "run_id": "uxrun01",
     "call": "analyze_synthesis", "model": "claude-sonnet-4-6", "prompt_version": "2026-06-06.1",
     "input_tokens": 3000, "output_tokens": 900, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 2000, "latency_ms": 32000, "stop_reason": "end_turn", "status": "ok"},
    {"timestamp": "2026-06-06T12:00:41Z", "username": "eval:pm-senior", "run_id": "uxrun01",
     "call": "generate", "model": "claude-sonnet-4-6", "prompt_version": "2026-06-06.1",
     "input_tokens": 4000, "output_tokens": 1500, "cache_creation_input_tokens": 0,
     "cache_read_input_tokens": 3500, "latency_ms": 41000, "stop_reason": "end_turn", "status": "ok"},
]


@pytest.mark.ux
def test_dashboard_console_tabs_and_drawer(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    from dashboard import routes as dash_routes

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "seed.jsonl").write_text(json.dumps(_GROUNDED_RECORD) + "\n", encoding="utf-8")
    (results_dir / "baseline_v1.json").write_text(json.dumps(_BASELINE), encoding="utf-8")
    llm_log = tmp_path / "llm_calls.jsonl"
    llm_log.write_text("\n".join(json.dumps(c) for c in _CALLS) + "\n", encoding="utf-8")

    # The route reads these module globals at request time → visible to the
    # already-running live server thread (same process).
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", results_dir)
    monkeypatch.setattr(dash_routes, "LLM_LOG", llm_log)

    dash = DashboardConsolePage(page, live_server).load()

    # All four tabs present; pipeline is the default active pane.
    for name in ("pipeline", "quality", "groundedness", "tuning"):
        expect(dash.tab(name)).to_be_visible()
    expect(dash.active_pane("pipeline")).to_be_visible()

    # Pipeline → open the trace tile; the waterfall + run_id render in the drawer.
    dash.open_tile("trace")
    expect(dash.drawer_open()).to_be_visible()
    expect(dash.drawer_body()).to_contain_text("uxrun01")
    dash.close_drawer()
    expect(dash.drawer_open()).to_have_count(0)

    # Quality → health tile drawer shows the baseline comparison row.
    dash.activate_tab("quality")
    expect(dash.active_pane("quality")).to_be_visible()
    dash.open_tile("health")
    expect(dash.drawer_open()).to_be_visible()
    expect(dash.drawer_body()).to_contain_text("grounding")
    dash.close_drawer()

    # Groundedness → the marquee surface: flagged-samples evidence in the drawer.
    dash.activate_tab("groundedness")
    expect(dash.active_pane("groundedness")).to_be_visible()
    dash.open_tile("groundedness")
    expect(dash.drawer_open()).to_be_visible()
    expect(dash.drawer_body()).to_contain_text("$5M")
    # Esc closes the drawer.
    page.keyboard.press("Escape")
    expect(dash.drawer_open()).to_have_count(0)

    # Tuning tab renders the read-only scaffold banner.
    dash.activate_tab("tuning")
    expect(dash.active_pane("tuning")).to_be_visible()
    expect(dash.active_pane("tuning")).to_contain_text("Read-only scaffold")
