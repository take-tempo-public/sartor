"""Tests for `scripts/ci_wait.py`'s pure decision logic.

Every function under test is pure — parsing, classification, log scanning — so this suite
needs no network, no `gh`, and no live PR. The single network seam (`scripts.ci_wait._gh`)
is deliberately not exercised here.

Two of these tests are load-bearing rather than incidental:

* `TestScanRerunsAgainstRealLogText` uses **verbatim captured output** from PR #99's ux job
  (`92148736760`), the run whose `gh pr checks --required` bucket said `pass` while its log
  recorded two failed attempts. That case is the reason the module exists.
* `TestEmitterScannerContract` reads `tests/ux/conftest.py` as text and asserts the format
  strings it prints are the ones these regexes match — so the emitter and the scanner
  cannot drift apart silently. Same shape as the maintained-list + audit-test pattern in
  `tests/test_egress_allowlist.py` and `scripts/wiki_relevance.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.ci_wait import (
    EXIT_ERROR,
    EXIT_FAILED,
    EXIT_GREEN,
    EXIT_PENDING,
    Check,
    classify,
    distinct_run_ids,
    parse_checks,
    parse_job_id,
    parse_run_id,
    scan_reruns,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent

_JOB_LINK = "https://github.com/take-tempo-public/sartor/actions/runs/30955903558/job/92148736760"
_BARE_RUN_LINK = "https://github.com/take-tempo-public/sartor/runs/92190739902"

# Verbatim from `gh run view --job 92148736760 --log` (PR #99, 2026-08-04). Tab-separated
# "<job name>\t<step>\t<timestamp> " prefix is exactly what `gh` emits — the scanner must
# match mid-line, which is the whole reason these samples are kept unedited.
_JOB = "UX / a11y / PDF (Playwright, py3.12)"
_NODEID = (
    "tests/ux/regression/test_20260708_busy_states_and_chip.py::"
    "test_scroll_spy_attributes_overlapping_refresh_corpus_calls"
)
_REAL_RERUN_LOG = (
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T22:23:00.8958304Z [ux] RERUN — "
    f"this attempt FAILED: {_NODEID}\n"
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T22:23:00.8987315Z RERUN [ 87%]\n"
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T22:23:32.8937172Z [ux] rerun-rate alarm: "
    f"1 test(s) needed a retry this run:\n"
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T22:23:32.8938235Z   {_NODEID} - 2 attempt(s) failed\n"
)

# A clean ux job's shape (PR #100, job 92190542690 — verified to contain zero markers).
_CLEAN_LOG = (
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T23:10:01.0000000Z 138 passed, 1 xfailed in 297.11s\n"
    f"{_JOB}\tUNKNOWN STEP\t2026-08-04T23:10:02.0000000Z Post job cleanup.\n"
)


def _check(name: str, bucket: str, link: str = _JOB_LINK) -> Check:
    return Check(name=name, state=bucket.upper(), bucket=bucket, link=link)


class TestParseLinks:
    def test_job_link_yields_both_ids(self) -> None:
        assert parse_job_id(_JOB_LINK) == "92148736760"
        assert parse_run_id(_JOB_LINK) == "30955903558"

    def test_bare_run_link_has_no_job_id(self) -> None:
        """CodeQL's roll-up check links to /runs/<id> with no /job/ segment.

        The wrapper must report "no job log available" for these rather than skip them
        silently, so `parse_job_id` returning None is the contract, not an oversight.
        """
        assert parse_job_id(_BARE_RUN_LINK) is None
        assert parse_run_id(_BARE_RUN_LINK) is None

    def test_empty_link_is_tolerated(self) -> None:
        assert parse_job_id("") is None
        assert parse_run_id("") is None


class TestParseChecks:
    def test_parses_rows(self) -> None:
        checks = parse_checks(
            '[{"name":"Lint","state":"SUCCESS","bucket":"pass","link":"' + _JOB_LINK + '"}]'
        )
        assert checks == [Check(name="Lint", state="SUCCESS", bucket="pass", link=_JOB_LINK)]

    def test_missing_fields_default_to_empty(self) -> None:
        assert parse_checks('[{"name":"X"}]') == [Check(name="X", state="", bucket="", link="")]

    def test_non_list_payload_raises(self) -> None:
        """An unparseable payload must surface, never degrade to an empty list.

        Degrading to `[]` is the PR #99 defect (`|| echo '[]'`) — it converts "I could not
        tell" into "nothing is wrong".
        """
        with pytest.raises(ValueError, match="expected a JSON list"):
            parse_checks('{"name":"X"}')


class TestDistinctRunIds:
    def test_dedupes_by_run_not_job(self) -> None:
        """Four jobs in one CI run plus two CodeQL runs collapse to three fetches."""
        base = "https://github.com/take-tempo-public/sartor/actions/runs"
        checks = [
            _check("py3.11", "pass", f"{base}/1/job/11"),
            _check("py3.12", "pass", f"{base}/1/job/12"),
            _check("py3.13", "pass", f"{base}/1/job/13"),
            _check("ux", "pass", f"{base}/1/job/14"),
            _check("codeql-py", "pass", f"{base}/2/job/21"),
            _check("codeql-js", "pass", f"{base}/3/job/31"),
        ]
        assert distinct_run_ids(checks) == ["1", "2", "3"]

    def test_links_without_run_ids_are_dropped(self) -> None:
        assert distinct_run_ids([_check("bare", "pass", _BARE_RUN_LINK)]) == []


class TestClassify:
    def test_all_pass_is_green(self) -> None:
        verdict, offenders = classify([_check("a", "pass"), _check("b", "pass")])
        assert (verdict, offenders) == (EXIT_GREEN, [])

    def test_one_failure_is_failed(self) -> None:
        verdict, offenders = classify([_check("a", "pass"), _check("b", "fail")])
        assert verdict == EXIT_FAILED
        assert [c.name for c in offenders] == ["b"]

    def test_cancelled_is_failed(self) -> None:
        verdict, offenders = classify([_check("a", "cancel")])
        assert verdict == EXIT_FAILED
        assert [c.name for c in offenders] == ["a"]

    def test_pending_is_pending(self) -> None:
        verdict, offenders = classify([_check("a", "pass"), _check("b", "pending")])
        assert verdict == EXIT_PENDING
        assert [c.name for c in offenders] == ["b"]

    def test_failure_outranks_pending(self) -> None:
        """A red check must not be reported as merely 'still waiting'."""
        verdict, _ = classify([_check("a", "pending"), _check("b", "fail")])
        assert verdict == EXIT_FAILED

    def test_required_skipping_is_not_green(self) -> None:
        """Branch protection will not accept a skipped required context.

        Calling it green would hand the caller a merge that cannot actually happen.
        """
        verdict, offenders = classify([_check("a", "pass"), _check("b", "skipping")])
        assert verdict == EXIT_FAILED
        assert [c.name for c in offenders] == ["b"]

    def test_empty_required_set_is_an_error(self) -> None:
        assert classify([])[0] == EXIT_ERROR


class TestScanRerunsAgainstRealLogText:
    """The case that motivates the module: bucket `pass`, log says two attempts failed."""

    def test_finds_the_absorbed_rerun(self) -> None:
        declared, tests = scan_reruns(_REAL_RERUN_LOG)
        assert declared == [1]
        assert tests == [(_NODEID, 2)]

    def test_clean_log_scans_to_zero(self) -> None:
        """Negative control.

        Without this, a scanner that matched nothing at all would look identical to a
        clean result — the inert-instrument trap item 44's own probe hit before its
        control arm caught it.
        """
        assert scan_reruns(_CLEAN_LOG) == ([], [])

    def test_rerun_marker_line_alone_yields_no_detail_row(self) -> None:
        """The em-dash `[ux] RERUN` line contains `::` but is not a detail line.

        It is deliberately not the scan target — its em dash is an encoding hazard on this
        machine's cp1252 console.
        """
        only_marker = (
            f"{_JOB}\tUNKNOWN STEP\t2026-08-04T22:23:00Z [ux] RERUN — "
            f"this attempt FAILED: {_NODEID}\n"
        )
        assert scan_reruns(only_marker) == ([], [])

    def test_multiple_tests_are_sorted_and_deduped(self) -> None:
        log = (
            "x\t y\t z [ux] rerun-rate alarm: 2 test(s) needed a retry this run:\n"
            "x\t y\t z   pkg/b.py::test_b - 1 attempt(s) failed\n"
            "x\t y\t z   pkg/a.py::test_a - 2 attempt(s) failed\n"
            "x\t y\t z   pkg/a.py::test_a - 1 attempt(s) failed\n"
        )
        declared, tests = scan_reruns(log)
        assert declared == [2]
        assert tests == [("pkg/a.py::test_a", 2), ("pkg/b.py::test_b", 1)]


class TestEmitterScannerContract:
    """Drift guard: the scanner's regexes vs. the format strings `conftest.py` prints.

    `tests/ux/conftest.py` is read as **text** rather than imported — importing it would
    pull in `playwright.sync_api` at module scope, which this non-ux test must not require.
    """

    CONFTEST = _REPO_ROOT / "tests" / "ux" / "conftest.py"

    def test_emitter_still_prints_the_strings_the_scanner_matches(self) -> None:
        source = self.CONFTEST.read_text(encoding="utf-8")
        alarm = "[ux] rerun-rate alarm: {len(reruns)} test(s) needed a retry this run:"
        detail = "  {nodeid} - {failed} attempt(s) failed"
        assert alarm in source, "conftest's rerun-alarm summary line was reworded"
        assert detail in source, "conftest's rerun detail line was reworded"

    def test_rendering_the_emitters_literals_round_trips_through_the_scanner(self) -> None:
        """Substitute real values into conftest's own literals and scan the result."""
        source = self.CONFTEST.read_text(encoding="utf-8")
        alarm_literal = re.search(r"\[ux\] rerun-rate alarm: \{[^}]+\} test\(s\)[^\"']*", source)
        detail_literal = re.search(r"\{nodeid\} - \{failed\} attempt\(s\) failed", source)
        assert alarm_literal is not None and detail_literal is not None

        rendered = (
            f"job\tstep\tts {alarm_literal.group(0).replace('{len(reruns)}', '1')}\n"
            f"job\tstep\tts   "
            f"{detail_literal.group(0).replace('{nodeid}', _NODEID).replace('{failed}', '2')}\n"
        )
        declared, tests = scan_reruns(rendered)
        assert declared == [1]
        assert tests == [(_NODEID, 2)]
