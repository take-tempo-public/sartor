"""Item 182: the eval runner's call plan, `--list`, `--estimate` and `--max-spend`.

Drives the real runner with every paid hop stubbed. Nothing here makes a paid call, reads a key or builds
a client; `_get_client` is patched to raise wherever a flag must not need one.

The estimate is a plan priced from `evals/catalog/costs.json`, so its expected values are derived from
that file and `hardening.compute_call_cost` (the one pricing function), never hard-coded: re-measuring
the costs does not break these tests.

The fail-closed tie is `test_plan_matches_the_calls_a_stubbed_run_fires_*`: `runner._FIXTURE_CALLS` is a
declared table, and these tests fail when the flow it describes changes.

Bodies are untyped like the rest of tests/.
"""

from __future__ import annotations

import json
from collections import Counter
from unittest.mock import MagicMock

import pytest

import analyzer
import hardening
from evals import eval_catalog as cat
from evals import runner
from tests.test_eval_run_identity import _stub_pipeline
from tests.test_eval_runner import (
    TestAssembleMode as _AssembleFixtures,  # underscore: not collected here
)

SRE_EDIT_TARGET = "error budget burn by tightening retry semantics in the ingress layer"


def _boom(*_a, **_k):
    raise AssertionError("this path must not build a client or start a run")


def _synthetic():
    return runner._select_fixtures("synthetic", None)


def _plan(subset, *, mode="generate", seed_mode=False, fixtures=None):
    return runner._call_plan(
        fixtures if fixtures is not None else _synthetic(),
        runner._select_rubrics(subset),
        mode=mode,
        seed_mode=seed_mode,
    )


def _price(call, model):
    row = cat.read_costs()[call]
    return hardening.compute_call_cost(
        {
            "model": model,
            "input_tokens": row["input"],
            "output_tokens": row["output"],
            "cache_creation_input_tokens": row["cache_write"],
            "cache_read_input_tokens": row["cache_read"],
        }
    )


# ---------- the call plan ----------------------------------------------------------------------


def test_the_smoke_plan_for_three_loadable_fixtures_and_one_that_is_not():
    counts, conditional, skipped = _plan("smoke")
    assert counts == {
        "analyze_extraction": 3,
        "analyze_synthesis": 3,
        "clarify": 3,
        "generate": 3,
        "judge_distinctiveness": 3,
        "judge_grade": 3,  # grounding only
    }
    assert conditional == {}
    assert skipped == ["corpus"]  # synthetic/corpus has no jd.txt: _load_fixture would fail on it


def test_the_full_plan_grades_every_rubric_and_iterates_only_where_a_scenario_exists():
    counts, _, _ = _plan("full")
    rubrics = [p.stem for p in runner._select_rubrics("full")]
    non_iteration = len([s for s in rubrics if s != "iteration_quality"])
    assert counts["judge_grade"] == 3 * non_iteration + 1  # +1: the one fixture with a scenario
    assert counts["iterate_clarify"] == 1


def test_assemble_swaps_generate_for_recommend_and_the_cover_letter_and_flags_the_conditional_call():
    counts, conditional, _ = _plan("smoke", mode="assemble", seed_mode=True)
    assert "generate" not in counts
    assert counts["recommend"] == 3 and counts["generate_cover_letter"] == 3
    assert list(conditional) == ["recommend_summary"]
    assert "recommend_summary" not in counts


def test_seed_mode_does_not_need_a_resume_file(tmp_path):
    fixture = tmp_path / "synthetic" / "no-resume"
    fixture.mkdir(parents=True)
    (fixture / "jd.txt").write_text("a job", encoding="utf-8")
    (fixture / "expected.json").write_text("{}", encoding="utf-8")
    assert runner._fixture_iterates(fixture, seed_mode=False) is None
    assert runner._fixture_iterates(fixture, seed_mode=True) is False


@pytest.mark.parametrize("bad", ["not json", "[1, 2]"])
def test_an_unreadable_expected_json_is_a_fixture_that_will_not_load(tmp_path, bad):
    fixture = tmp_path / "fx"
    fixture.mkdir()
    (fixture / "jd.txt").write_text("a job", encoding="utf-8")
    (fixture / "resume.md").write_text("cv", encoding="utf-8")
    (fixture / "expected.json").write_text(bad, encoding="utf-8")
    # A non-dict expected.json loads but cannot carry scenarios; invalid JSON does not load at all.
    expected = None if bad == "not json" else False
    assert runner._fixture_iterates(fixture, seed_mode=False) is expected


# ---------- pricing ----------------------------------------------------------------------------


def test_the_estimate_prices_each_measured_kind_at_its_pin_and_lists_the_rest_unmeasured():
    est = runner.estimate_spend(
        _synthetic(), runner._select_rubrics("smoke"), mode="generate", seed_mode=False
    )
    assert est.per_kind_usd["clarify"] == pytest.approx(
        3 * _price("clarify", analyzer.HAIKU_MODEL), abs=1e-6
    )
    assert est.per_kind_usd["generate"] == pytest.approx(
        3 * _price("generate", analyzer.SONNET_MODEL), abs=1e-6
    )
    assert est.total_usd == pytest.approx(sum(est.per_kind_usd.values()), abs=1e-6)
    # The judge has logged no rows yet, so it is named, not priced at zero by accident.
    assert set(est.unmeasured) == {"judge_distinctiveness", "judge_grade"}
    assert est.skipped_fixtures == ("corpus",)


def test_a_model_override_reprices_the_pin_it_moves_and_never_the_judge():
    fixtures, rubrics = _synthetic(), runner._select_rubrics("smoke")
    base = runner.estimate_spend(fixtures, rubrics, mode="generate", seed_mode=False)
    moved = runner.estimate_spend(
        fixtures,
        rubrics,
        mode="generate",
        seed_mode=False,
        model_overrides_map={
            "SONNET_MODEL": "claude-sonnet-4-6",
            "JUDGE_MODEL": "claude-haiku-5-5",
        },
    )
    assert moved.per_kind_usd["generate"] == pytest.approx(
        3 * _price("generate", "claude-sonnet-4-6"), abs=1e-6
    )
    assert moved.per_kind_usd["generate"] != base.per_kind_usd["generate"]
    assert (
        moved.per_kind_usd["clarify"] == base.per_kind_usd["clarify"]
    )  # the Haiku pin did not move
    assert runner._pin_models({"JUDGE_MODEL": "x"})["JUDGE_MODEL"] == runner.JUDGE_MODEL


def test_the_estimate_parses_only_the_catalog_entries_it_prices(monkeypatch):
    parsed = []
    real = cat._read_toml
    monkeypatch.setattr(cat, "_read_toml", lambda p: (parsed.append(p.name), real(p))[1])
    est = runner.estimate_spend(
        _synthetic(), runner._select_rubrics("smoke"), mode="generate", seed_mode=False
    )
    # Four measured kinds are priced; the two unmeasured judge kinds are never loaded, and the other 17
    # entries are never touched (charter C-13: a run pays for the entries it was asked for).
    assert sorted(parsed) == sorted(f"{call}.toml" for call in est.per_kind_usd)
    assert len(parsed) == 4


def test_the_assemble_mode_check_matches_run_suite_s():
    with pytest.raises(ValueError, match="requires --seed"):
        runner.estimate_spend(_synthetic(), [], mode="assemble", seed_mode=False)
    with pytest.raises(ValueError, match="Unknown mode"):
        runner.estimate_spend(_synthetic(), [], mode="bogus", seed_mode=False)


def test_the_formatted_estimate_says_it_is_a_floor_and_what_it_left_out():
    est = runner.estimate_spend(
        _synthetic(), runner._select_rubrics("smoke"), mode="generate", seed_mode=False
    )
    text = runner.format_estimate(est, max_spend=0.0001)
    assert "floor" in text and "retries" in text
    assert "judge_grade" in text and "unmeasured" in text
    assert "corpus" in text  # the fixture that will not load
    assert "OVER the cap" in text
    assert "within the cap" in runner.format_estimate(est, max_spend=1000.0)
    assembled = runner.estimate_spend(
        _synthetic(), runner._select_rubrics("smoke"), mode="assemble", seed_mode=True
    )
    assert "recommend_summary" in runner.format_estimate(assembled)


def test_the_catalog_listing_has_one_line_per_call_kind():
    lines = runner.format_catalog_list().splitlines()
    assert len(lines) == 1 + len(cat.names())
    clarify = next(line for line in lines if line.startswith("clarify "))
    assert "covered" in clarify and "HAIKU_MODEL" in clarify
    judge = next(line for line in lines if line.startswith("judge_grade "))
    assert " - " in judge  # unmeasured: shown as a dash, not as $0.0000


# ---------- main(): no client, no key, the right exit code --------------------------------------


@pytest.fixture
def no_run(monkeypatch):
    monkeypatch.setattr(runner, "_get_client", _boom)
    monkeypatch.setattr(runner, "run_suite", _boom)


def test_list_prints_the_catalog_and_builds_nothing(no_run, capsys):
    assert runner.main(["--list"]) == 0
    out = capsys.readouterr().out
    for call in cat.names():
        assert call in out


def test_estimate_prints_the_plan_and_builds_nothing(no_run, capsys):
    assert runner.main(["--suite", "synthetic", "--subset", "smoke", "--estimate"]) == 0
    out = capsys.readouterr().out
    assert "analyze_extraction" in out and "floor" in out


def test_estimate_does_not_run_when_the_cap_is_also_given(no_run, capsys):
    assert (
        runner.main(
            ["--suite", "synthetic", "--subset", "smoke", "--estimate", "--max-spend", "0.0001"]
        )
        == 0
    )
    assert "OVER the cap" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["--fixture", "no-such-fixture", "--estimate"],
        ["--mode", "assemble", "--estimate"],  # assemble needs --seed
        ["--model-override", "SONNET_MODEL=claude-not-a-model", "--estimate"],
    ],
)
def test_estimate_fails_with_exit_1_before_any_spend(no_run, argv):
    assert runner.main(["--suite", "synthetic", "--subset", "smoke", *argv]) == 1


def test_max_spend_refuses_a_run_whose_estimate_is_over_the_cap(no_run, capsys):
    # `no_run` makes run_suite and _get_client raise, so reaching exit 4 proves nothing was started.
    code = runner.main(["--suite", "synthetic", "--subset", "smoke", "--max-spend", "0.0001"])
    assert code == runner.EXIT_OVER_BUDGET == 4
    assert "OVER the cap" in capsys.readouterr().out  # the estimate was printed before the refusal


def test_max_spend_within_the_estimate_forwards_the_cap_to_run_suite(monkeypatch):
    seen = {}

    def fake_run_suite(**kwargs):
        seen.update(kwargs)
        return runner.EvalRunResult(0, None, 0, 0, [], [])

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)
    monkeypatch.setattr(runner, "_get_client", _boom)
    assert runner.main(["--suite", "synthetic", "--subset", "smoke", "--max-spend", "1000"]) == 0
    assert seen["max_spend_usd"] == 1000.0


def test_without_the_flags_nothing_is_estimated_and_the_cap_is_none(monkeypatch):
    """The default path is unchanged: no costs.json read, no catalog parse, `max_spend_usd=None`."""
    seen = {}

    def fake_run_suite(**kwargs):
        seen.update(kwargs)
        return runner.EvalRunResult(0, None, 0, 0, [], [])

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)
    monkeypatch.setattr(cat, "read_costs", _boom)
    monkeypatch.setattr(cat, "_read_toml", _boom)
    assert runner.main(["--suite", "synthetic", "--subset", "smoke"]) == 0
    assert seen["max_spend_usd"] is None


@pytest.mark.parametrize("bad", ["-1", "nan", "inf", "abc", ""])
def test_a_cap_that_is_not_a_finite_non_negative_amount_is_refused(bad):
    with pytest.raises(SystemExit) as exc:
        runner.main(["--max-spend", bad])
    assert exc.value.code == 2  # argparse's own usage error


# ---------- the runtime cap --------------------------------------------------------------------


def _count_clarify(monkeypatch):
    calls = []
    inner = runner.clarify

    def counting(*a, **k):
        calls.append(1)
        return inner(*a, **k)

    monkeypatch.setattr(runner, "clarify", counting)
    return calls


def test_a_run_stops_before_the_next_phase_once_the_cap_is_reached(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    clarify_calls = _count_clarify(monkeypatch)
    # Any positive spend reaches this. The stubbed analyze writes a real, priced call-log row.
    result = runner.run_suite(
        suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock(), max_spend_usd=1e-9
    )
    assert result.cancelled and result.stop_reason == "max_spend"
    assert result.exit_code == runner.EXIT_OVER_BUDGET
    assert clarify_calls == []  # the poll after analyze stopped the run before clarify
    assert result.total_cost_usd > 0  # what was spent before the stop is still reported


def test_a_cap_above_the_spend_changes_nothing(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    clarify_calls = _count_clarify(monkeypatch)
    result = runner.run_suite(
        suite="synthetic",
        subset="smoke",
        out_dir=tmp_path,
        client=MagicMock(),
        max_spend_usd=1000.0,
    )
    assert not result.cancelled and result.stop_reason is None
    assert result.exit_code == 0
    assert len(clarify_calls) == 3


def test_no_cap_is_the_historical_run(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    result = runner.run_suite(
        suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock()
    )
    assert result.stop_reason is None and not result.cancelled


def test_a_callers_cancel_is_reported_as_cancelled_not_as_a_spend_stop(monkeypatch, tmp_path):
    _stub_pipeline(monkeypatch, tmp_path)
    result = runner.run_suite(
        suite="synthetic",
        subset="smoke",
        out_dir=tmp_path,
        client=MagicMock(),
        cancel_check=lambda: True,
        max_spend_usd=1000.0,
    )
    assert result.cancelled and result.stop_reason == "cancelled"
    assert result.exit_code != runner.EXIT_OVER_BUDGET


# ---------- the spend meter --------------------------------------------------------------------


def _row(trace, call="generate", model=analyzer.SONNET_MODEL):
    return {
        "model": model,
        "call": call,
        "input_tokens": 1000,
        "output_tokens": 1000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "trace_id": trace,
    }


def _line(row):
    return json.dumps(row) + "\n"


def test_the_meter_sums_only_its_own_trace_and_only_what_is_new(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    mine, other = "a" * 32, "b" * 32
    log.write_text(_line(_row(mine)) + _line(_row(other)), encoding="utf-8")
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)
    one = hardening.compute_call_cost(_row(mine))

    meter = runner._SpendMeter(0, mine)
    assert meter.poll() == pytest.approx(one)
    assert meter.poll() == pytest.approx(one)  # a second poll with nothing new adds nothing
    with log.open("a", encoding="utf-8") as f:
        f.write(
            _line(_row(mine, call="judge_grade", model=runner.JUDGE_MODEL)) + _line(_row(other))
        )
    judge = hardening.compute_call_cost(_row(mine, call="judge_grade", model=runner.JUDGE_MODEL))
    assert meter.poll() == pytest.approx(one + judge)  # the judge's rows count toward the cap


def test_the_meter_starts_where_it_is_told_and_agrees_with_trace_cost(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    trace = "c" * 32
    log.write_text(_line(_row(trace)), encoding="utf-8")  # before the run: must not be counted
    start = log.stat().st_size
    with log.open("a", encoding="utf-8") as f:
        f.write(
            _line(_row(trace)) + _line(_row(trace, call="judge_grade", model=runner.JUDGE_MODEL))
        )
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)
    generation, judge = runner._trace_cost(start, trace)
    assert runner._SpendMeter(start, trace).poll() == pytest.approx(generation + judge, abs=1e-6)


def test_a_half_written_line_is_left_for_the_next_poll(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    trace = "d" * 32
    whole, partial = _line(_row(trace)), _line(_row(trace))
    log.write_text(whole + partial[:-15], encoding="utf-8")  # the second line has no newline yet
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)
    one = hardening.compute_call_cost(_row(trace))
    meter = runner._SpendMeter(0, trace)
    assert meter.poll() == pytest.approx(one)
    with log.open("a", encoding="utf-8") as f:
        f.write(partial[-15:])
    assert meter.poll() == pytest.approx(2 * one)  # counted once, when it completed


def test_an_offset_past_the_end_means_the_log_rotated(monkeypatch, tmp_path):
    log = tmp_path / "llm_calls.jsonl"
    trace = "e" * 32
    log.write_text(_line(_row(trace)), encoding="utf-8")
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)
    assert runner._SpendMeter(10_000_000, trace).poll() == pytest.approx(
        hardening.compute_call_cost(_row(trace))
    )


def test_a_missing_or_garbled_log_costs_nothing_and_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "LLM_LOG_PATH", tmp_path / "absent.jsonl")
    assert runner._SpendMeter(0, "f" * 32).poll() == 0.0
    log = tmp_path / "llm_calls.jsonl"
    log.write_text("not json\n\n[1]\n", encoding="utf-8")
    monkeypatch.setattr(runner, "LLM_LOG_PATH", log)
    assert runner._SpendMeter(0, "f" * 32).poll() == 0.0


# ---------- the fail-closed tie: _FIXTURE_CALLS vs the calls a run really fires ------------------


class _Fired:
    """Counts the call kinds a stubbed `run_suite` fires, by the entry point that fires them.

    The entry-point-to-kinds mapping below is DECLARED here (a stated limit): `analyze` fires two kinds, and
    so on. What this test verifies is that the plan equals the calls the real flow makes through them.
    """

    def __init__(self):
        self.counts = Counter()

    def hit(self, *kinds):
        self.counts.update(kinds)


def _wire(monkeypatch, tmp_path, fired, *, generate_resume):
    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")

    def analyze(*a, **k):
        fired.hit("analyze_extraction", "analyze_synthesis")
        return {"overall_strategy": "ok"}

    def clarify(*a, **k):
        fired.hit("clarify")
        return {"questions": [], "reasoning": ""}

    def generate(*a, **k):
        fired.hit("generate")
        return {"resume_content": generate_resume, "cover_letter_content": "Dear team,"}

    def clarify_iteration(*a, **k):
        fired.hit("iterate_clarify")
        return {"questions": [], "reasoning": ""}

    def grade(*a, **k):
        fired.hit("judge_grade")
        return {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"}

    def distinctiveness(*a, **k):
        fired.hit("judge_distinctiveness")
        return {"score": 4.0, "summary": "ok"}

    monkeypatch.setattr(runner, "analyze", analyze)
    monkeypatch.setattr(runner, "clarify", clarify)
    monkeypatch.setattr(runner, "generate", generate)
    monkeypatch.setattr(runner, "clarify_iteration", clarify_iteration)
    monkeypatch.setattr(runner, "_grade", grade)
    monkeypatch.setattr(runner, "_score_distinctiveness", distinctiveness)


@pytest.mark.parametrize("subset", ["smoke", "full"])
def test_plan_matches_the_calls_a_stubbed_run_fires_in_generate_mode(monkeypatch, tmp_path, subset):
    fired = _Fired()
    # The sre persona's scripted edit must land in the résumé, or its iteration phase exits early.
    resume = f"- Led a project\n- Reduced {SRE_EDIT_TARGET}\n"
    _wire(monkeypatch, tmp_path, fired, generate_resume=resume)

    runner.run_suite(suite="synthetic", subset=subset, out_dir=tmp_path, client=MagicMock())

    planned, conditional, skipped = _plan(subset)
    assert fired.counts == Counter(planned), (
        f"runner._FIXTURE_CALLS no longer describes what run_suite calls (subset={subset}); "
        f"update the table and the estimate with it"
    )
    assert conditional == {} and skipped == ["corpus"]


def test_plan_matches_the_calls_a_stubbed_run_fires_in_assemble_mode(
    db_session, monkeypatch, tmp_path
):
    import blueprints.generation as bgen

    fired = _Fired()
    seed_data, exp_id, b1_id, b2_id, summary_id = _AssembleFixtures()._seed_corpus(db_session)
    _wire(monkeypatch, tmp_path, fired, generate_resume="unused in assemble mode")

    def generate_must_not_run(*a, **k):
        raise AssertionError("generate() must not run in mode='assemble'")

    def recommend_bullets(*a, **k):
        fired.hit("recommend")
        return {
            "recommendations": [
                {"experience_id": exp_id, "bullet_ids": [b1_id, b2_id], "rationale": "fit"}
            ]
        }

    def recommend_summaries(*a, **k):
        fired.hit("recommend_summary")
        return {
            "recommendation": {"summary_item_id": summary_id, "rationale": "fit"},
            "alternates": [],
        }

    def cover_letter(client, ctx, analysis, resume_content, username="", run_id=""):
        fired.hit("generate_cover_letter")
        return {"cover_letter_content": "Dear hiring manager, ..."}

    monkeypatch.setattr(runner, "generate", generate_must_not_run)
    monkeypatch.setattr(runner, "recommend_bullets", recommend_bullets)
    monkeypatch.setattr(runner, "recommend_summaries", recommend_summaries)
    monkeypatch.setattr(bgen, "generate_cover_letter_against_resume", cover_letter)

    fixture = runner.FIXTURES_DIR / "synthetic" / "sre-mid-level"
    runner.run_suite(
        suite="synthetic",
        subset="smoke",
        fixture_name="sre-mid-level",
        seed_data=seed_data,
        mode="assemble",
        out_dir=tmp_path,
        client=MagicMock(),
    )

    planned, conditional, _ = _plan("smoke", mode="assemble", seed_mode=True, fixtures=[fixture])
    fired_certain = Counter({k: v for k, v in fired.counts.items() if k not in conditional})
    assert fired_certain == Counter(planned), (
        "runner._FIXTURE_CALLS no longer describes what run_suite calls in assemble mode"
    )
    # A conditional kind may fire, but only one the plan declared as conditional.
    assert set(fired.counts) - set(fired_certain) <= set(conditional)


def test_the_tie_can_fail(monkeypatch, tmp_path):
    """Control arm: if the flow gained a call the table does not list, the tie must go red."""
    fired = _Fired()
    _wire(monkeypatch, tmp_path, fired, generate_resume="- x\n")
    inner = runner.clarify

    def clarify_twice(*a, **k):
        inner(*a, **k)
        return inner(*a, **k)

    monkeypatch.setattr(runner, "clarify", clarify_twice)
    runner.run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())
    assert fired.counts != Counter(_plan("smoke")[0])
