"""Tests for `scripts/flake_rates.py`.

Every function under test is pure -- log-line splitting, session parsing, summary
parsing, roster digesting, Wilson bounds -- so this suite needs no network, no `gh`,
and no live run. The single network seam (`scripts.flake_rates._gh`) is deliberately
not exercised here, mirroring `tests/test_ci_wait.py`.

Fixtures below are **verbatim captured output** from `gh run view 31047661015 --log`
(PR #102, 2026-08-05 -- the run in which item 30 recurred), not synthesized text, for
the same reason `test_ci_wait.py` pins real log samples: a hand-written fixture tests
the author's mental model of the format, not the format.

Three classes are load-bearing rather than incidental:

* `TestParseSessionAgainstTheRealRun` reproduces item 30's captured evidence
  independently -- `test_keyboard_reorder_persists_and_reset_reverts`, 1 of 2 attempts
  failed, terminal PASSED, tier `ux`. This is the module's own acceptance bar (see the
  approved plan's Verification section).
* `TestReconciliationHasTeeth` mutates each pinned fixture (drops the summary, drops an
  outcome line, reduces a rerun count) and asserts the session is excluded, not
  silently reported clean -- "a gate that has not been shown to REJECT a bad input is
  not evidence of anything" (`tests/test_work_items_closure_bar.py`).
* `TestEmitterScannerContract` extends `test_ci_wait.py`'s drift guard to the two new
  emitters this module reads: `tests/ux/conftest.py`'s rerun hooks and
  `tests/ux/rerun_report.py`'s `##[warning]` annotation text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.flake_rates import (
    FlakeRate,
    RunMeta,
    Session,
    SummaryCounts,
    _compute_rates,
    _iter_store_records,
    _write_shard,
    classify_tier,
    encode_run,
    encode_session,
    group_by_job,
    parse_run_list,
    parse_run_log,
    parse_session,
    parse_summary,
    rank,
    roster_digest,
    split_log_line,
    split_sessions,
    wilson_lower_bound,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

_UX_JOB = "UX / a11y / PDF (Playwright, py3.12)"
_QUAL_JOB = "Lint, type-check, test (py3.12)"
_QUAL_STEP = "Quality gate (ruff check + ruff format --check + mypy + pytest)"
_RERUN_NODEID = (
    "tests/ux/regression/test_20260604_bullet_drag_reorder.py::"
    "test_keyboard_reorder_persists_and_reset_reverts"
)

# --------------------------------------------------------------------------------
# Verbatim real-log lines (full `<job>\t<step>\t<timestamp> <body>` shape), grouped
# into ready-to-parse session windows. Every line below was read back from a real
# `gh run view 31047661015 --log` fetch -- none were hand-typed.
# --------------------------------------------------------------------------------

_UX_SESSION_LINES = [
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:13:42.5951695Z "
    "============================= test session starts ==============================",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:13:53.2701070Z "
    "tests/ux/a11y/test_axe_smoke.py::test_axe_landing_and_new_user PASSED    [  1%]",
    # O-4: the rerun window -- orphan fragment, marker (real em dash), traceback body,
    # bare RERUN line with no nodeid.
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2120859Z {_RERUN_NODEID} ",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2123107Z "
    f"[ux] RERUN — this attempt FAILED: {_RERUN_NODEID}",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2124993Z "
    "tests/ux/regression/test_20260604_bullet_drag_reorder.py:253: in "
    "test_keyboard_reorder_persists_and_reset_reverts",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2126397Z "
    '    assert compose.bullet_texts()[0].startswith("Attended"), "order did not persist"',
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2127379Z            ^^^^^^^^^^^^^^^^^^^^^^",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:50.2224937Z RERUN [ 11%]",
    # O-5: terminal attempt is intact.
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:14:54.0679259Z {_RERUN_NODEID} PASSED [ 11%]",
    # O-6/O-9: alarm block + warning-retry annotation.
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:18:18.3324722Z "
    "[ux] rerun-rate alarm: 1 test(s) needed a retry this run:",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:18:18.3325629Z   {_RERUN_NODEID} - 1 attempt(s) failed",
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:18:18.3347255Z "
    f"##[warning]{_RERUN_NODEID} needed a retry (1 of 3 attempts failed) - see the step summary",
    # The real run's summary was "138 passed, ... 2 xpassed, 1 rerun in 275.45s
    # (0:04:35)" -- this fixture is a deliberately truncated 2-outcome-line excerpt of
    # that session, so the passed/xpassed counts are adjusted to match what the
    # excerpt actually contains (2 passed, 0 xpassed) rather than the real session's
    # full 140. Duration, the skipped/deselected counts, and every other line are
    # untouched real text -- this is the ONE place a count is deliberately edited, and
    # it exists so the reconciliation-teeth tests below have something to compare
    # against; `TestParseSummary` separately locks in the real unedited summary line.
    f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:18:18.3355281Z "
    "= 2 passed, 1 skipped, 2223 deselected, 1 rerun in 275.45s (0:04:35) =",
]

_QUAL_XDIST_SESSION_LINES = [
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0123579Z "
    "============================= test session starts ==============================",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0150843Z "
    "platform linux -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0 -- "
    "/opt/hostedtoolcache/Python/3.12.13/x64/bin/python",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0177246Z cachedir: .pytest_cache",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0207180Z rootdir: /home/runner/work/sartor/sartor",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0207692Z configfile: pyproject.toml",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0237240Z testpaths: tests",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0247556Z "
    "plugins: anyio-4.14.2, xdist-3.8.0, socket-0.8.0, rerunfailures-16.4",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0248040Z created: 4/4 workers",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0248309Z 4 workers [2223 items]",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0248657Z scheduling tests via LoadScheduling",
    # ordinary pair: dispatch echo (O-11), then the xdist result line.
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0249210Z "
    "tests/test_a11y_floor_guards.py::test_live_region_present_and_polite ",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:15.0249788Z "
    "[gw0] [  0%] PASSED tests/test_a11y_floor_guards.py::test_live_region_present_and_polite ",
    # O-13: a parametrize id containing a literal space.
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:17.0162293Z "
    'tests/test_analyzer.py::test_strip_fences_variants[{"a": 1}-{"a": 1}] ',
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:17.0170404Z "
    '[gw0] [  7%] PASSED tests/test_analyzer.py::test_strip_fences_variants[{"a": 1}-{"a": 1}] ',
    # Real summary was "2218 passed, 6 skipped in 44.63s"; adjusted to match this
    # excerpt's 2 actual outcome lines -- see the identical note on the ux fixture
    # above. `skipped` is deliberately left at the real 6 (0 actual SKIPPED lines in
    # this excerpt) to also exercise O-12's non-blocking mismatch on the xdist path.
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:50.8878152Z "
    "======================= 2 passed, 6 skipped in 44.63s =======================",
]

_QUAL_SKIP_SESSION_LINES = [
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:51.1250739Z "
    "============================= test session starts ==============================",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:53.1666710Z "
    "collecting ... collected 2363 items / 2223 deselected / 1 skipped / 140 selected",
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:53.4704079Z "
    "tests/ux/a11y/test_announce_live_region.py::test_announce_fires_on_analysis_complete "
    "SKIPPED [  0%]",
    # O-8: the declared skipped count has no "passed" substring at all.
    f"{_QUAL_JOB}\t{_QUAL_STEP}\t2026-08-05T21:14:53.6734669Z "
    "==================== 141 skipped, 2223 deselected in 2.44s =====================",
]


def _make_session(job: str, index: int, lines: list[str]) -> Session:
    body_lines = [split_log_line(line)[2] for line in lines]  # type: ignore[index]
    return parse_session(job, index, body_lines)


class TestSplitLogLine:
    def test_splits_the_three_tab_fields(self) -> None:
        parsed = split_log_line(f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:13:42.5951695Z hello")
        assert parsed == (_UX_JOB, "UNKNOWN STEP", "hello")

    def test_strips_the_leading_timestamp(self) -> None:
        # O-1: the timestamp and body share the SAME tab field.
        _job, _step, body = split_log_line(  # type: ignore[misc]
            f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:13:42.5951695Z RERUN [ 11%]"
        )
        assert body == "RERUN [ 11%]"

    def test_missing_tab_fields_return_none(self) -> None:
        """A line with fewer than 3 tab fields must surface as unparseable, never
        silently absorbed as if field 1 were the body."""
        assert split_log_line("no tabs here at all") is None
        assert split_log_line("only\tone tab") is None


class TestGroupByJob:
    def test_groups_and_counts_unparsed(self) -> None:
        text = "\n".join([*_UX_SESSION_LINES[:2], "garbage with no tabs"])
        jobs, unparsed = group_by_job(text)
        assert list(jobs) == [_UX_JOB]
        assert len(jobs[_UX_JOB]) == 2
        assert unparsed == 1

    def test_blank_lines_are_skipped_not_counted(self) -> None:
        jobs, unparsed = group_by_job("\n\n" + _UX_SESSION_LINES[0] + "\n\n")
        assert unparsed == 0
        assert len(jobs[_UX_JOB]) == 1


class TestSplitSessions:
    def test_bounds_at_the_summary_not_the_next_banner(self) -> None:
        """The trap this exists to avoid: a naive banner-to-banner split would fold
        trailing non-pytest Actions lines (git cleanup, ci_backstop, ...) into the
        LAST session's window and inflate its `unparsed_lines`."""
        bodies = [split_log_line(line)[2] for line in _QUAL_XDIST_SESSION_LINES]  # type: ignore[index]
        trailing_noise = ["[command]/usr/bin/git version", "Cleaning up orphan processes"]
        chunks = split_sessions([*bodies, *trailing_noise])
        assert len(chunks) == 1
        assert chunks[0][-1].strip().startswith("=")  # ends at the summary line
        assert all("git version" not in line for line in chunks[0])

    def test_two_sessions_in_one_job(self) -> None:
        bodies = [
            split_log_line(line)[2]  # type: ignore[index]
            for line in (*_QUAL_XDIST_SESSION_LINES, *_QUAL_SKIP_SESSION_LINES)
        ]
        chunks = split_sessions(bodies)
        assert len(chunks) == 2


class TestClassifyTier:
    def test_ux_and_pdf_by_session_order(self) -> None:
        assert classify_tier(_UX_JOB, 0) == ("ux", "job-prefix+session-order")
        assert classify_tier(_UX_JOB, 1) == ("pdf", "job-prefix+session-order")

    def test_quality_legs_by_session_order(self) -> None:
        assert classify_tier(_QUAL_JOB, 0)[0] == "quality-not-ux"
        assert classify_tier(_QUAL_JOB, 1)[0] == "quality-ux-skip"

    def test_python_version_bump_does_not_fall_through(self) -> None:
        """Matched by prefix, not exact string -- a matrix bump to py3.14 must not
        silently reclassify as `unknown`."""
        assert classify_tier("Lint, type-check, test (py3.14)", 0)[0] == "quality-not-ux"

    def test_unknown_job_is_explicit_not_guessed(self) -> None:
        assert classify_tier("pip-audit (advisory, non-blocking)", 0) == (
            "unknown",
            "unclassified-job-or-index",
        )


class TestParseSummary:
    def test_parses_the_reran_uxsession_summary(self) -> None:
        counts = parse_summary(
            "= 138 passed, 1 skipped, 2223 deselected, 2 xpassed, 1 rerun in 275.45s (0:04:35) ="
        )
        assert counts == SummaryCounts(
            passed=138,
            failed=0,
            error=0,
            skipped=1,
            deselected=2223,
            xfailed=0,
            xpassed=2,
            rerun=1,
            warnings=0,
            other=0,
            duration_s=275.45,
            raw="138 passed, 1 skipped, 2223 deselected, 2 xpassed, 1 rerun in 275.45s (0:04:35)",
        )

    def test_parses_a_summary_with_no_passed_substring(self) -> None:
        """O-8: the quality job's collect-then-skip leg. A regex anchored on `passed`
        would silently drop this whole session."""
        counts = parse_summary(
            "==================== 141 skipped, 2223 deselected in 2.44s ====================="
        )
        assert counts is not None
        assert (counts.passed, counts.skipped, counts.deselected) == (0, 141, 2223)

    def test_non_summary_line_returns_none(self) -> None:
        assert parse_summary("tests/x.py::test_y PASSED [ 1%]") is None


class TestParseSessionAgainstTheRealRun:
    """The module's own acceptance bar: reproduce item 30's captured evidence from a
    real log independently of how that evidence was originally captured by hand."""

    def test_reproduces_the_absorbed_rerun(self) -> None:
        session = _make_session(_UX_JOB, 0, _UX_SESSION_LINES)
        assert session.reconciled
        assert session.tier == "ux"
        assert session.rerun_attempts == ((_RERUN_NODEID, 1),)
        assert _RERUN_NODEID in session.executed
        assert _RERUN_NODEID not in session.failed_nodeids  # terminal attempt PASSED
        assert session.warning_retry == ((_RERUN_NODEID, 1, 3),)
        assert session.alarm_detail == ((_RERUN_NODEID, 1),)
        assert session.swallowed_traceback_lines == 3  # the 3 traceback body lines
        assert session.unparsed_lines == 0

    def test_reconciles_the_xdist_session_with_a_space_in_a_parametrize_id(self) -> None:
        session = _make_session(_QUAL_JOB, 0, _QUAL_XDIST_SESSION_LINES)
        assert session.fmt == "xdist"
        assert session.reconciled
        assert session.unparsed_lines == 0
        assert 'tests/test_analyzer.py::test_strip_fences_variants[{"a": 1}-{"a": 1}]' in (
            n.rstrip() for n in session.executed
        )

    def test_reconciles_the_collect_then_skip_session(self) -> None:
        session = _make_session(_QUAL_JOB, 1, _QUAL_SKIP_SESSION_LINES)
        assert session.reconciled  # O-12's 1-skip gap is a non-blocking anomaly
        assert any("O-12" in a for a in session.anomalies)
        assert session.executed == ()


class TestReconciliationHasTeeth:
    """Mutate a known-good fixture; the session must be excluded, not silently clean.

    'A gate that has not been shown to REJECT a bad input is not evidence of anything'
    (tests/test_work_items_closure_bar.py).
    """

    def test_missing_summary_is_not_reconciled(self) -> None:
        lines = [line for line in _UX_SESSION_LINES if "passed," not in line]
        session = _make_session(_UX_JOB, 0, lines)
        assert not session.reconciled
        assert session.summary is None

    def test_dropped_outcome_line_is_not_reconciled(self) -> None:
        """Drop the terminal PASSED line -- the executed-count check must catch it."""
        lines = [line for line in _UX_SESSION_LINES if "PASSED [ 11%]" not in line]
        session = _make_session(_UX_JOB, 0, lines)
        assert not session.reconciled
        assert any("executed roster size" in a for a in session.anomalies)

    def test_garbage_line_is_not_reconciled(self) -> None:
        lines = [
            *_UX_SESSION_LINES,
            f"{_UX_JOB}\tUNKNOWN STEP\t2026-08-05T21:20:00Z ???unshaped???",
        ]
        session = _make_session(_UX_JOB, 0, lines)
        assert not session.reconciled
        assert session.unparsed_lines == 1

    def test_a_clean_fixture_is_the_positive_control(self) -> None:
        """Negative control's mirror: the un-mutated fixture must actually pass, or
        the mutation tests above would be vacuous."""
        assert _make_session(_UX_JOB, 0, _UX_SESSION_LINES).reconciled


class TestRosterDigest:
    def test_deterministic_and_order_independent(self) -> None:
        assert roster_digest(["b", "a"]) == roster_digest(["a", "b"])

    def test_different_rosters_differ(self) -> None:
        assert roster_digest(["a"]) != roster_digest(["a", "b"])

    def test_empty_roster_is_stable(self) -> None:
        assert roster_digest([]) == roster_digest([])


class TestWilsonLowerBound:
    def test_zero_attempts_is_zero(self) -> None:
        assert wilson_lower_bound(0, 0) == 0.0

    def test_more_failures_at_equal_attempts_ranks_higher(self) -> None:
        assert wilson_lower_bound(20, 100) > wilson_lower_bound(2, 100)

    def test_small_n_is_not_blindly_trusted(self) -> None:
        """A single-attempt 100% failure must not report full confidence -- the whole
        point of using the LOWER bound rather than the raw rate."""
        assert wilson_lower_bound(1, 1) < 1.0


class TestRank:
    def test_thin_samples_are_separated_not_dropped(self) -> None:
        rates = [
            FlakeRate("a", "ux", 1, 1, 1, 1, 1, "t", "t", True),
            FlakeRate("b", "ux", 100, 10, 100, 10, 5, "t", "t", True),
        ]
        ranked, thin = rank(rates, min_attempts=20)
        assert [r.nodeid for r in ranked] == ["b"]
        assert [r.nodeid for r in thin] == ["a"]

    def test_ranked_is_sorted_by_wilson_descending(self) -> None:
        rates = [
            FlakeRate("low", "ux", 100, 2, 100, 2, 1, "t", "t", True),
            FlakeRate("high", "ux", 100, 40, 100, 40, 10, "t", "t", True),
        ]
        ranked, _thin = rank(rates, min_attempts=20)
        assert [r.nodeid for r in ranked] == ["high", "low"]


class TestEncodeSessionRosterPolicy:
    def test_ux_tier_stores_full_roster(self) -> None:
        session = _make_session(_UX_JOB, 0, _UX_SESSION_LINES)
        meta = RunMeta("1", 1, 1, "CI", "push", "main", "sha", "t", "completed", "success", "u")
        _record, rosters = encode_session(session, meta)
        assert len(rosters) == 1
        assert rosters[0]["nodeids"] != []

    def test_quality_tier_stores_digest_only(self) -> None:
        session = _make_session(_QUAL_JOB, 0, _QUAL_XDIST_SESSION_LINES)
        meta = RunMeta("1", 1, 1, "CI", "push", "main", "sha", "t", "completed", "success", "u")
        _record, rosters = encode_session(session, meta)
        assert rosters == []  # quality tier is a control arm, not a per-test series


class TestParseRunList:
    def test_parses_rows(self) -> None:
        payload = (
            '[{"databaseId":1,"attempt":1,"number":5,"workflowName":"CI","event":"push",'
            '"headBranch":"main","headSha":"abc","createdAt":"t","status":"completed",'
            '"conclusion":"success","url":"u"}]'
        )
        runs = parse_run_list(payload)
        assert runs == [
            RunMeta("1", 1, 5, "CI", "push", "main", "abc", "t", "completed", "success", "u")
        ]

    def test_non_list_payload_raises(self) -> None:
        with pytest.raises(ValueError, match="expected a JSON list"):
            parse_run_list('{"run": 1}')


class TestParseRunLogEndToEnd:
    """Assembles the four session windows above as if they were one whole-run log,
    checking `parse_run_log`'s job-grouping + session-splitting glue, not just the
    per-session parser exercised above."""

    def test_all_sessions_reconcile_with_zero_top_level_unparsed(self) -> None:
        text = "\n".join(
            [*_UX_SESSION_LINES, *_QUAL_XDIST_SESSION_LINES, *_QUAL_SKIP_SESSION_LINES]
        )
        sessions, top_unparsed = parse_run_log(text)
        assert top_unparsed == 0
        assert len(sessions) == 3
        assert all(s.reconciled for s in sessions)


class TestStoreRoundTrip:
    def test_write_reload_and_compute_rates(self, tmp_path: Path) -> None:
        ux_session = _make_session(_UX_JOB, 0, _UX_SESSION_LINES)
        meta = RunMeta(
            "31047661015",
            1,
            102,
            "CI",
            "pull_request",
            "feat/x",
            "deadbeef",
            "2026-08-05T21:12:00Z",
            "completed",
            "success",
            "https://x",
        )
        record, rosters = encode_session(ux_session, meta)
        run_record = encode_run(
            meta, ingested=True, skip_reason="", log_lines=100, jobs_seen=[_UX_JOB]
        )
        records = [run_record, record, *rosters]

        _write_shard(tmp_path / "shard.jsonl", records)
        reloaded = list(_iter_store_records(tmp_path))
        assert len(reloaded) == len(records)

        rates = _compute_rates(reloaded)
        by_id = {r.nodeid: r for r in rates}
        assert by_id[_RERUN_NODEID].failures == 1
        assert by_id[_RERUN_NODEID].attempts == 2
        assert by_id[_RERUN_NODEID].distinct_shas_failed == 1

    def test_malformed_line_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        shard = tmp_path / "bad.jsonl"
        shard.write_text('{"kind": "run", "run_id": "1"}\nnot json at all\n', encoding="utf-8")
        records = list(_iter_store_records(tmp_path))
        assert len(records) == 1


class TestEmitterScannerContract:
    """Drift guard, extended from `test_ci_wait.py`'s: this module reads TWO emitters
    that repo doesn't otherwise cross-check -- `tests/ux/conftest.py`'s rerun hooks
    (shared with ci_wait) and `tests/ux/rerun_report.py`'s `##[warning]` annotation.
    """

    CONFTEST = _REPO_ROOT / "tests" / "ux" / "conftest.py"
    RERUN_REPORT = _REPO_ROOT / "tests" / "ux" / "rerun_report.py"

    def test_conftest_still_prints_the_marker_this_module_matches(self) -> None:
        source = self.CONFTEST.read_text(encoding="utf-8")
        assert '_safe_print(f"\\n[ux] RERUN — this attempt FAILED: {report.nodeid}")' in source

    def test_rerun_report_still_prints_the_annotation_this_module_matches(self) -> None:
        source = self.RERUN_REPORT.read_text(encoding="utf-8")
        assert "needed a retry " in source
        assert "of {MAX_ATTEMPTS} attempts failed) - see the step summary" in source
