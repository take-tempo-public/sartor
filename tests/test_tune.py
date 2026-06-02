"""Tests for the eval tuning delta table (evals/tune).

LLM-free. The score loader (status filtering + grouping), the delta builder
(sign, the regression-flag boundary, one-sided pairs), the table formatter, and
the CLI exit contract are tested against hand-built result JSONL files in
tmp_path. No paid LLM calls, no network. Mirrors tests/test_annotation.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals import tune

# ---------------------------------------------------------------------------
# Helpers — write a result JSONL the way evals/runner.py does.
# ---------------------------------------------------------------------------


def _record(fixture: str, rubric: str, score, status: str = "ok") -> dict:
    return {
        "schema_version": 2,
        "fixture": fixture,
        "rubric": rubric,
        "score": score,
        "status": status,
        "prompt_version": "test",
    }


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------------
# load_scores
# ---------------------------------------------------------------------------


def test_load_scores_groups_by_fixture_and_rubric(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "r.jsonl", [
        _record("pm-senior", "grounding", 4.8),
        _record("pm-senior", "tone", 4.2),
        _record("sre-mid-level", "grounding", 4.6),
    ])
    scores = tune.load_scores(p)
    assert scores == {
        ("pm-senior", "grounding"): [4.8],
        ("pm-senior", "tone"): [4.2],
        ("sre-mid-level", "grounding"): [4.6],
    }


def test_load_scores_excludes_judge_error_and_non_ok(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "r.jsonl", [
        _record("pm-senior", "grounding", 4.8),
        _record("pm-senior", "grounding", 0, status="judge_error"),
        _record("pm-senior", "tone", 0.0, status="pipeline_error"),
    ])
    scores = tune.load_scores(p)
    # judge_error (score 0) and pipeline_error are dropped, not averaged in.
    assert scores == {("pm-senior", "grounding"): [4.8]}


def test_load_scores_keeps_multiple_rows_for_mean(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "r.jsonl", [
        _record("pm-senior", "grounding", 4.8),
        _record("pm-senior", "grounding", 4.2),
        _record("pm-senior", "grounding", 4.6),
    ])
    assert tune.load_scores(p) == {("pm-senior", "grounding"): [4.8, 4.2, 4.6]}


def test_load_scores_skips_blank_lines(tmp_path: Path) -> None:
    p = tmp_path / "r.jsonl"
    p.write_text(
        json.dumps(_record("pm-senior", "grounding", 4.8)) + "\n\n   \n",
        encoding="utf-8",
    )
    assert tune.load_scores(p) == {("pm-senior", "grounding"): [4.8]}


def test_load_scores_skips_non_numeric_score(tmp_path: Path) -> None:
    p = _write_jsonl(tmp_path / "r.jsonl", [
        _record("pm-senior", "grounding", None),
        _record("pm-senior", "tone", 4.2),
    ])
    assert tune.load_scores(p) == {("pm-senior", "tone"): [4.2]}


def test_load_scores_raises_on_malformed_line(tmp_path: Path) -> None:
    p = tmp_path / "r.jsonl"
    p.write_text('{"fixture": "x"}\nnot json at all\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r":2: invalid JSON"):
        tune.load_scores(p)


# ---------------------------------------------------------------------------
# build_delta_table
# ---------------------------------------------------------------------------


def test_build_delta_table_computes_sign_and_sorts() -> None:
    baseline = {("pm-senior", "tone"): [4.2], ("a", "grounding"): [4.0]}
    candidate = {("pm-senior", "tone"): [4.7], ("a", "grounding"): [4.0]}
    rows = tune.build_delta_table(baseline, candidate)
    # Sorted by (fixture, rubric): ("a","grounding") then ("pm-senior","tone").
    assert [(r.fixture, r.rubric) for r in rows] == [
        ("a", "grounding"), ("pm-senior", "tone")
    ]
    tone = rows[1]
    assert tone.baseline_mean == 4.2
    assert tone.candidate_mean == 4.7
    assert tone.delta == pytest.approx(0.5)
    assert tone.regressed is False


def test_build_delta_table_regression_at_boundary() -> None:
    # Exactly -REGRESSION_DELTA (0.5) counts as a regression (<=).
    rows = tune.build_delta_table(
        {("f", "grounding"): [4.8]}, {("f", "grounding"): [4.3]}
    )
    assert rows[0].delta == pytest.approx(-0.5)
    assert rows[0].regressed is True


def test_build_delta_table_just_above_boundary_is_not_regression() -> None:
    rows = tune.build_delta_table(
        {("f", "grounding"): [4.8]}, {("f", "grounding"): [4.4]}
    )
    assert rows[0].delta == pytest.approx(-0.4)
    assert rows[0].regressed is False


def test_build_delta_table_uses_means_across_runs() -> None:
    rows = tune.build_delta_table(
        {("f", "g"): [4.0, 4.0]}, {("f", "g"): [5.0, 4.0]}
    )
    assert rows[0].baseline_mean == pytest.approx(4.0)
    assert rows[0].candidate_mean == pytest.approx(4.5)
    assert rows[0].delta == pytest.approx(0.5)


def test_build_delta_table_one_sided_pairs_have_no_delta() -> None:
    rows = tune.build_delta_table(
        {("only_base", "g"): [4.0]}, {("only_cand", "g"): [4.0]}
    )
    by_fixture = {r.fixture: r for r in rows}
    assert by_fixture["only_base"].candidate_mean is None
    assert by_fixture["only_base"].delta is None
    assert by_fixture["only_base"].regressed is False
    assert by_fixture["only_cand"].baseline_mean is None
    assert by_fixture["only_cand"].delta is None


# ---------------------------------------------------------------------------
# format_delta_table
# ---------------------------------------------------------------------------


def test_format_delta_table_marks_regression() -> None:
    rows = tune.build_delta_table(
        {("f", "grounding"): [4.8]}, {("f", "grounding"): [4.2]}
    )
    out = tune.format_delta_table(rows)
    assert "(REGRESSION)" in out
    assert "-0.60" in out


def test_format_delta_table_marks_new_and_missing() -> None:
    rows = tune.build_delta_table(
        {("base_only", "g"): [4.0]}, {("cand_only", "g"): [4.0]}
    )
    out = tune.format_delta_table(rows)
    assert "(new)" in out       # candidate-only pair
    assert "(missing)" in out   # baseline-only pair
    assert "n/a" in out         # ASCII placeholder for the absent mean
    assert out.isascii()        # printed to stdout; must be Windows-console safe


def test_format_delta_table_empty() -> None:
    out = tune.format_delta_table([])
    assert "no (fixture, rubric) pairs" in out


# ---------------------------------------------------------------------------
# CLI exit contract
# ---------------------------------------------------------------------------


def test_main_returns_zero_when_no_regression(tmp_path: Path, capsys) -> None:
    base = _write_jsonl(tmp_path / "b.jsonl", [_record("f", "grounding", 4.0)])
    cand = _write_jsonl(tmp_path / "c.jsonl", [_record("f", "grounding", 4.5)])
    rc = tune.main(["--baseline", str(base), "--candidate", str(cand)])
    assert rc == 0
    assert "grounding" in capsys.readouterr().out


def test_main_returns_two_on_regression(tmp_path: Path) -> None:
    base = _write_jsonl(tmp_path / "b.jsonl", [_record("f", "grounding", 4.8)])
    cand = _write_jsonl(tmp_path / "c.jsonl", [_record("f", "grounding", 4.0)])
    assert tune.main(["--baseline", str(base), "--candidate", str(cand)]) == 2


def test_main_returns_one_on_missing_file(tmp_path: Path, capsys) -> None:
    base = _write_jsonl(tmp_path / "b.jsonl", [_record("f", "grounding", 4.0)])
    rc = tune.main([
        "--baseline", str(base), "--candidate", str(tmp_path / "nope.jsonl"),
    ])
    assert rc == 1
    assert "error:" in capsys.readouterr().out


def test_main_json_output_is_parseable(tmp_path: Path, capsys) -> None:
    base = _write_jsonl(tmp_path / "b.jsonl", [_record("f", "grounding", 4.0)])
    cand = _write_jsonl(tmp_path / "c.jsonl", [_record("f", "grounding", 4.5)])
    tune.main(["--baseline", str(base), "--candidate", str(cand), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["fixture"] == "f"
    assert payload[0]["delta"] == pytest.approx(0.5)
