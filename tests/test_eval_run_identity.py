"""Item 181: an eval run is one trace; its records and call rows share ids; its spend is read by id.

Drives the real `run_suite` on the committed synthetic fixtures with every paid hop stubbed. The
stubbed `analyze` makes a real `_call_llm` against a fake stream client and the stubbed `_grade`
writes a real judge row, so the rows carry the ids the analyzer stamps inside the run's trace
context. `tests/conftest.py` points both the analyzer's and the runner's log path at one tmp
file, so nothing reaches the developer's real `logs/llm_calls.jsonl`.

Bodies are untyped like the rest of tests/.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import analyzer
import call_identity as ci
import hardening
from evals import runner
from evals.runner import JUDGE_MODEL, run_suite
from tests._fake_llm import FakeClient, FakeStream, FakeUsage


class _JudgeResponse:
    usage = FakeUsage()
    model = JUDGE_MODEL
    stop_reason = "end_turn"
    _request_id = "req_judge"


def _stub_pipeline(monkeypatch, tmp_path):
    """Paid hops stubbed; the stubs still write real call-log rows through the analyzer."""
    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")

    def fake_analyze(client, context, *, username="", run_id="", **kwargs):
        analyzer._call_llm(
            FakeClient(FakeStream('{"a": "x"}')),
            "p",
            call_kind="analyze_synthesis",
            username=username,
            run_id=run_id,
        )
        return {"overall_strategy": "ok"}

    def fake_grade(client, *args, fixture_name="", **kwargs):
        analyzer.log_judge_call(
            call_kind="judge_grade",
            username=f"eval:{fixture_name}",
            model=JUDGE_MODEL,
            request_kwargs={"model": JUDGE_MODEL, "system": "grader", "messages": []},
            response=_JudgeResponse(),
            elapsed_ms=1,
        )
        return {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"}

    monkeypatch.setattr(runner, "analyze", fake_analyze)
    monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
    monkeypatch.setattr(
        runner,
        "generate",
        lambda *a, **k: {
            "resume_content": "- Led a project\n- Built a system",
            "cover_letter_content": "Dear team,",
        },
    )
    monkeypatch.setattr(runner, "_grade", fake_grade)
    monkeypatch.setattr(
        runner, "_score_distinctiveness", lambda *a, **k: {"score": 4.0, "summary": "ok"}
    )


def _records(result):
    return [
        json.loads(ln)
        for ln in result.out_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def _log_rows():
    path = analyzer.LOG_PATH
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


@pytest.fixture
def run(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    result = run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())
    return result


# ---------- the id tree ------------------------------------------------------------------


def test_the_run_has_one_trace_id_and_every_record_carries_it(run):
    assert ci.is_trace_id(run.trace_id)
    records = _records(run)
    assert records
    assert {r["trace_id"] for r in records} == {run.trace_id}


def test_each_record_names_its_case_and_the_case_span(run):
    for rec in _records(run):
        assert rec["case_id"] == rec["fixture"]
        assert ci.is_span_id(rec["span_id"])
    spans = {}
    for rec in _records(run):
        spans.setdefault(rec["fixture"], set()).add(rec["span_id"])
    # One case span per fixture, never shared between fixtures.
    assert all(len(v) == 1 for v in spans.values())
    assert len({next(iter(v)) for v in spans.values()}) == len(spans)


def test_call_rows_are_children_of_the_case_span_they_belong_to(run):
    case_span = {r["fixture"]: r["span_id"] for r in _records(run)}
    rows = _log_rows()
    assert any(r["call"] == "analyze_synthesis" for r in rows)
    assert any(r["call"] == "judge_grade" for r in rows)
    for row in rows:
        assert row["trace_id"] == run.trace_id
        assert row["parent_span_id"] == case_span[row["case_id"]]
        assert ci.is_span_id(row["span_id"])
        assert row["span_id"] != row["parent_span_id"]


def test_two_runs_have_different_trace_ids(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    first = run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())
    second = run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())
    assert first.trace_id != second.trace_id


def test_the_trace_context_does_not_outlive_the_run(run):
    assert analyzer.current_trace_context() is None


# ---------- cost by id, not by window ------------------------------------------------------


def test_a_concurrent_run_on_the_same_fixture_is_not_summed_in(monkeypatch, tmp_path):
    """The leak: cost was the sum of rows for `eval:<fixture>` after a start time, so a second
    run on the same fixture whose rows landed in the window was added to this run's cost."""
    _stub_pipeline(monkeypatch, tmp_path)
    real_analyze = runner.analyze
    foreign_rows = []

    def analyze_with_a_foreign_run_alongside(*a, username="", **k):
        # Another run's call for this same fixture, written inside this fixture's cost window.
        foreign = {
            "username": username,
            "model": analyzer.SONNET_MODEL,
            "call": "generate",
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "trace_id": ci.new_trace_id(),
            "case_id": username.removeprefix("eval:"),
        }
        with analyzer.LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(foreign) + "\n")
        foreign_rows.append(foreign)
        return real_analyze(*a, username=username, **k)

    monkeypatch.setattr(runner, "analyze", analyze_with_a_foreign_run_alongside)

    result = run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())

    assert foreign_rows
    assert hardening.compute_call_cost(foreign_rows[0]) > 10  # the leak would be unmissable
    grounding = [r for r in _records(result) if r.get("rubric") == "grounding"]
    assert len(grounding) == len(foreign_rows)
    assert all(r["cost_usd"] < 0.01 for r in grounding)
    assert result.total_cost_usd < 0.01


def test_cost_usd_is_generation_only_and_the_judge_spend_is_reported_separately(run):
    grounding = [r for r in _records(run) if r.get("rubric") == "grounding"]
    own = hardening.compute_call_cost(
        {"model": analyzer.SONNET_MODEL, "call": "analyze_synthesis", **vars(FakeUsage)}
    )
    assert own > 0
    assert all(r["cost_usd"] == pytest.approx(own) for r in grounding)
    judge_each = hardening.compute_call_cost({"model": JUDGE_MODEL, **vars(FakeUsage)})
    composites = [r for r in _records(run) if r.get("rubric") == "eval_composite"]
    assert composites
    assert all(r["judge_cost_usd"] == pytest.approx(judge_each) for r in composites)


def test_run_totals_are_generation_plus_judge_for_the_trace(run):
    n = len({r["fixture"] for r in _records(run)})
    own = hardening.compute_call_cost({"model": analyzer.SONNET_MODEL, **vars(FakeUsage)})
    judge_each = hardening.compute_call_cost({"model": JUDGE_MODEL, **vars(FakeUsage)})
    assert run.judge_cost_usd == pytest.approx(n * judge_each, abs=1e-6)
    assert run.total_cost_usd == pytest.approx(n * (own + judge_each), abs=1e-6)


# ---------- the scan --------------------------------------------------------------------


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _row(trace, case, call="generate", model=analyzer.SONNET_MODEL):
    return {
        "model": model,
        "call": call,
        "input_tokens": 1000,
        "output_tokens": 1000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "trace_id": trace,
        "case_id": case,
    }


def test_the_scan_starts_at_the_offset_and_skips_older_rows(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    trace = ci.new_trace_id()
    _write(log, [_row(trace, "fx")])
    offset = log.stat().st_size
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_row(trace, "fx")) + "\n")
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)

    since_offset, _ = runner._trace_cost(offset, trace)
    from_start, _ = runner._trace_cost(0, trace)

    assert from_start == pytest.approx(2 * since_offset)


def test_an_offset_past_the_end_means_the_log_was_rotated_and_is_read_from_the_start(
    monkeypatch, tmp_path
):
    log = tmp_path / "llm_calls.jsonl"
    trace = ci.new_trace_id()
    _write(log, [_row(trace, "fx")])
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)

    rotated, _ = runner._trace_cost(10_000_000, trace)
    full, _ = runner._trace_cost(0, trace)

    assert rotated == full > 0


def test_a_scan_selects_by_trace_and_case_and_survives_bad_lines(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    mine, other = ci.new_trace_id(), ci.new_trace_id()
    log.write_text(
        json.dumps(_row(mine, "a"))
        + "\nnot json\n\n[1, 2]\n"
        + json.dumps(_row(mine, "b"))
        + "\n"
        + json.dumps(_row(other, "a"))
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)

    one_row = hardening.compute_call_cost(_row(mine, "a"))
    assert runner._trace_cost(0, mine, "a")[0] == pytest.approx(one_row)
    assert runner._trace_cost(0, mine)[0] == pytest.approx(2 * one_row)
    assert runner._trace_cost(0, ci.new_trace_id()) == (0.0, 0.0)


def test_a_missing_log_costs_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "LLM_LOG_PATH", tmp_path / "absent.jsonl")
    assert runner._trace_cost(0, ci.new_trace_id()) == (0.0, 0.0)
    assert runner._log_offset() == 0


def test_case_cost_outside_a_trace_context_is_zero():
    assert runner._case_cost(0) == 0.0
    assert runner._trace_fields() == {}
