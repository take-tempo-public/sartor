"""UX regression — Epic C C2 (`feat/run-detail-modal`): UX-7, UX-8.

Diagnosis/scope: `docs/dev/handoffs/epic-c-c2-brief.md`,
`docs/dev/reviews/epic-c-console-ux-audit.md` (UX-7, UX-8).

Guards `dashboard/templates/dashboard.html` + `dashboard/routes.py`:

- UX-7: every run id shown in the console (the trace detail's "Latest run"
  line, the calls table, the "Recent runs" fold, the recent-evals table) is a
  button that opens a composite run-detail modal backed by
  `GET /_dashboard/api/run/<run_id>`, showing that run's spans, latency, cost
  and errors.
- UX-8: a nonzero error count in the reliability table is a button that opens
  the same modal, filtered to that call kind's recent error records, now
  showing each record's real `error_type`/`error_message` (Epic C C1c;
  `analyzer._call_llm_streaming` + `_redact_error_message`) when the row
  carries them, and an explicit "no message logged" state — never a
  fabricated one — for a row that predates C1c or otherwise lacks them.

Seeds call telemetry by monkeypatching the dashboard blueprint's module
globals (`LLM_LOG` / `EVAL_RESULTS_DIR`, read at request time -> visible to
the live server thread), the same idiom as
`test_20260611_diagnostics_chart_corrections.py`.
"""

from __future__ import annotations

import json
from types import ModuleType

import pytest
from playwright.sync_api import Page, Route, expect

from ui_pages import DashboardConsolePage
from ui_pages.selectors import Dashboard

_RUN = "uxc2run1"
_CALLS = [
    {
        "timestamp": "2026-09-24T00:00:01Z",
        "username": "eval:pm-senior",
        "run_id": _RUN,
        "call": "analyze_extraction",
        "model": "claude-haiku-4-5-20251001",
        "prompt_version": "2026-09-24.1",
        "input_tokens": 1200,
        "output_tokens": 400,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 5000,
        "stop_reason": "end_turn",
        "status": "ok",
    },
    {
        "timestamp": "2026-09-24T00:00:06Z",
        "username": "eval:pm-senior",
        "run_id": _RUN,
        "call": "generate",
        "model": "claude-sonnet-5",
        "prompt_version": "2026-09-24.1",
        "input_tokens": 3000,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 12000,
        "stop_reason": "max_tokens",
        "status": "error",
        "error_type": "LLMConfigurationError",
        "error_message": "call=generate could not be sent — no credential configured",
    },
    # A second run must never leak into the first run's modal. Timestamped
    # BEFORE _RUN's own latest call so _RUN stays the "latest run" the trace
    # tile/detail shows by default -- _run_trace picks the run with the
    # greatest max-timestamp among its own calls (dashboard/routes.py).
    {
        "timestamp": "2026-09-24T00:00:03Z",
        "username": "eval:pm-senior",
        "run_id": "uxc2run2",
        "call": "generate",
        "model": "claude-sonnet-5",
        "prompt_version": "2026-09-24.1",
        "input_tokens": 2000,
        "output_tokens": 900,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "latency_ms": 9000,
        "stop_reason": "end_turn",
        "status": "ok",
    },
]


def _seed(monkeypatch, tmp_path) -> None:
    from dashboard import routes as dash_routes

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    llm_log = tmp_path / "llm_calls.jsonl"
    llm_log.write_text("\n".join(json.dumps(c) for c in _CALLS) + "\n", encoding="utf-8")
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", results_dir)
    monkeypatch.setattr(dash_routes, "LLM_LOG", llm_log)


@pytest.mark.ux
def test_run_id_buttons_open_composite_modal_scoped_to_that_run(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """UX-7: a run-id button opens the modal via GET /api/run/<run_id>,
    showing only that run's spans/cost/errors -- not the other run's."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()

    # The "Latest run" line inside the trace detail panel.
    dash.open_tile("trace")
    expect(dash.detail_panel_open()).to_be_visible()
    dash.open_run_detail(_RUN)

    expect(dash.run_modal_open()).to_be_visible()
    expect(page.locator(Dashboard.RUN_MODAL_TITLE)).to_contain_text(_RUN)
    body = dash.run_modal_body()
    # Two spans for this run (analyze_extraction + generate); the OTHER run's
    # single span must not appear.
    expect(body.locator(".wf-row")).to_have_count(2)
    expect(body).to_contain_text("analyze_extraction")
    expect(body).to_contain_text("generate")
    expect(body).to_contain_text("1 error")
    # The one error on this run is listed with its known metadata, including
    # the real C1c error_type/error_message fields -- not a fabricated one.
    expect(body).to_contain_text("max_tokens")
    expect(body).to_contain_text("LLMConfigurationError")
    expect(body).to_contain_text("no credential configured")

    # Close via the Close button; focus returns to the trigger.
    dash.close_run_modal()
    expect(dash.run_modal_open()).to_have_count(0)


@pytest.mark.ux
def test_run_modal_closes_on_escape_and_restores_focus(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """UX-7: Esc closes the modal too (matches every other .cb-modal here)."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()
    dash.open_tile("trace")
    trigger = dash.run_link(_RUN)
    dash.open_run_detail(_RUN)
    expect(dash.run_modal_open()).to_be_visible()

    page.keyboard.press("Escape")
    expect(dash.run_modal_open()).to_have_count(0)
    expect(trigger).to_be_focused()


@pytest.mark.ux
def test_error_count_button_lists_that_call_kinds_errors_only(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """UX-8: clicking a nonzero error count opens the SAME modal filtered to
    that call kind's recent error records, with the real error message, and
    scoped to the clicked call kind (not every error)."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()

    dash.open_tile("reliability")
    expect(dash.detail_panel_open()).to_be_visible()
    err_btn = dash.err_link("generate")
    expect(err_btn).to_be_visible()
    dash.open_errors_for_kind("generate")

    expect(dash.run_modal_open()).to_be_visible()
    expect(page.locator(Dashboard.RUN_MODAL_TITLE)).to_contain_text("generate")
    body = dash.run_modal_body()
    expect(body).to_contain_text("1 of the 200 most recent calls")
    expect(body).to_contain_text("max_tokens")
    expect(body).to_contain_text("LLMConfigurationError")
    expect(body).to_contain_text("no credential configured")
    dash.close_run_modal()


# Resolves a custom property the way the browser does for the anchor's own cascade scope:
# a probe in the anchor's parent takes `color: var(<name>)` and reports its computed color.
_RESOLVE_COLOR_VAR = """(el, name) => {
    const probe = document.createElement('span');
    probe.style.color = `var(${name})`;
    el.parentElement.appendChild(probe);
    const color = getComputedStyle(probe).color;
    probe.remove();
    return color;
}"""


@pytest.mark.ux
def test_failing_error_count_keeps_danger_color_and_hover_affordance(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """Item 115 (UX-8's F3 fix): a failing call kind's error count renders in the
    danger color, not the run-link info color, and hovering still shows the brand
    color. Measured with getComputedStyle, because the fix was a specificity
    contest (`td.fail button.err-link` over `button.err-link`) that reading the
    rules cannot settle (memory: css-cascade-per-property-not-per-rule)."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()
    dash.open_tile("reliability")
    expect(dash.detail_panel_open()).to_be_visible()
    err_btn = dash.err_link("generate")  # status=error in _CALLS, so its <td> is .fail
    expect(err_btn).to_be_visible()

    danger, info, brand = (
        err_btn.evaluate(_RESOLVE_COLOR_VAR, name) for name in ("--danger", "--info", "--brand")
    )
    # Precondition: three distinct colors, or the assertions below prove nothing.
    assert len({danger, info, brand}) == 3, (danger, info, brand)

    expect(err_btn).to_have_css("color", danger)  # not `info`: the cue the fix restored
    err_btn.hover()
    expect(err_btn).to_have_css("color", brand)  # the hover affordance the fix kept


@pytest.mark.ux
def test_error_with_no_captured_message_shows_no_message_logged(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """A pre-C1c (or otherwise message-less) error row renders an honest
    "no message logged" state -- never a blank cell, never a fabricated
    string standing in for a message that was never captured."""
    from dashboard import routes as dash_routes

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    llm_log = tmp_path / "llm_calls.jsonl"
    legacy_run = "uxc2legacyrun"
    records = [
        {
            "timestamp": "2026-09-24T00:00:01Z",
            "username": "eval:pm-senior",
            "run_id": legacy_run,
            "call": "generate",
            "model": "claude-sonnet-5",
            "prompt_version": "2026-09-24.1",
            "latency_ms": 4000,
            "stop_reason": "max_tokens",
            "status": "error",
            # No error_type/error_message -- a pre-C1c row.
        },
    ]
    llm_log.write_text("\n".join(json.dumps(c) for c in records) + "\n", encoding="utf-8")
    monkeypatch.setattr(dash_routes, "EVAL_RESULTS_DIR", results_dir)
    monkeypatch.setattr(dash_routes, "LLM_LOG", llm_log)

    dash = DashboardConsolePage(page, live_server).load()
    dash.open_tile("reliability")
    expect(dash.detail_panel_open()).to_be_visible()
    dash.open_errors_for_kind("generate")

    expect(dash.run_modal_open()).to_be_visible()
    body = dash.run_modal_body()
    expect(body).to_contain_text("no message logged")
    dash.close_run_modal()


@pytest.mark.ux
def test_unknown_run_id_shows_no_record_state(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch, tmp_path
) -> None:
    """A run id with no matching log record (404 {"found": false} from the
    endpoint) degrades to an honest empty state, never a stuck spinner or a
    raw error. Intercepts a REAL run-link's request and fulfills it as the
    server would for an unlogged run id, so this exercises the actual click
    -> fetch -> render path rather than a synthetic DOM node with no wiring."""
    _seed(monkeypatch, tmp_path)
    dash = DashboardConsolePage(page, live_server).load()
    dash.open_tile("trace")

    def _fulfill_not_found(route: Route) -> None:
        route.fulfill(
            status=404,
            content_type="application/json",
            body=json.dumps({"found": False, "run_id": "no-such-run"}),
        )

    page.route("**/_dashboard/api/run/*", _fulfill_not_found)
    dash.open_run_detail(_RUN)
    expect(dash.run_modal_open()).to_be_visible()
    expect(dash.run_modal_body()).to_contain_text("No log record for run")
