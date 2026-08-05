"""Deterministic CI-wait wrapper — the single definition of "this PR is green".

`scripts/gate.py` (PX-55) exists because "gate green" had been defined independently in
three places with nothing keeping them in sync. This module is the same move for the other
half of the close-out: **waiting for a PR's checks**. Before it, every session hand-rolled
its own watcher, and two of them failed in the same expensive way.

Two observed failures motivate it (both real, both on this repo):

1. **Silent watchers.** Two 30-minute `Monitor` watches on PR #99 emitted *zero* events
   while a required check was already red — ~1 hour lost, and the silence read as "still
   running, all fine". Contributing causes: the system `jq` binary does not exist on this
   machine, and `gh pr checks` exits **nonzero** on failure, so the common
   ``gh pr checks ... | jq ... || echo '[]'`` shape discards the real output at exactly
   the moment it matters.

2. **Green-after-retries is indistinguishable from green.** Verified directly against
   PR #99's ux job (`92148736760`): ``gh pr checks 99 --required`` reports bucket
   ``pass``, while that same job's log contains::

       [ux] rerun-rate alarm: 1 test(s) needed a retry this run:
         tests/ux/regression/test_20260708_busy_states_and_chip.py::
           test_scroll_spy_attributes_overlapping_refresh_corpus_calls - 2 attempt(s) failed

   The repo has emitted that alarm since `feat/rerun-rate-alarm` and **nothing read it**.
   Charter **C-7** rule 3 ("green CI is not evidence if the test needed a retry") was
   going unenforced at the point of use.

Design commitments, each traceable to one of the above:

* **No poll loop is written here.** ``gh pr checks --watch --required --fail-fast``
  already does this correctly; a hand-rolled loop is the thing being replaced.
* **Silence is structurally impossible.** `main` prints exactly one terminal
  ``ci-wait: <VERDICT> (exit N)`` line from a ``finally`` block — including on an
  unexpected exception.
* **A nonzero `gh` exit never discards output.** `_gh_checks` parses stdout regardless of
  return code, because nonzero is `gh`'s *normal* way of saying "failing" (1) or "pending"
  (8). Treating it as an error is precisely the PR #99 defect.
* **Never `jq`.** No system `jq` exists here, and even ``gh --jq`` is avoided: parsing is
  ``--json`` plus Python's `json`, so every decision is testable without a subprocess.
* **An unverifiable rerun scan never reads as clean.** A log fetch that fails exits 2
  rather than reporting green.

Exit codes:

===  ============================================================================
  0  all required checks green, and zero reruns were absorbed
  1  a required check failed, was cancelled, or reported `skipping`
  2  wrapper error — `gh` missing, PR unresolvable, or the rerun scan could not run
  3  all required checks green, **but** reruns were absorbed — stop and look
  8  still pending when the deadline expired
===  ============================================================================

Exit 3 applies C-7 rule 3 at the wrapper boundary without disturbing CI's deliberately
report-only rerun policy (owner decision 2026-07-20, `docs/scroll-flake-ci-data-rerun-policy`):
the build still passes, the *caller* is simply told the difference.

Usage::

    python -m scripts.ci_wait            # the current branch's PR
    python -m scripts.ci_wait 101
    python -m scripts.ci_wait 101 --timeout-minutes 45
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass

EXIT_GREEN = 0
EXIT_FAILED = 1
EXIT_ERROR = 2
EXIT_GREEN_WITH_RERUNS = 3
EXIT_PENDING = 8

_VERDICT_LABELS: dict[int, str] = {
    EXIT_GREEN: "GREEN",
    EXIT_FAILED: "NOT GREEN - required check failed",
    EXIT_ERROR: "ERROR",
    EXIT_GREEN_WITH_RERUNS: "GREEN WITH RERUNS",
    EXIT_PENDING: "PENDING AT DEADLINE",
}

# `gh pr checks --json link` yields either
#   .../actions/runs/<run_id>/job/<job_id>   (a workflow job)
#   .../runs/<check_run_id>                  (a bare check run, e.g. CodeQL's roll-up)
# so the job pattern must be anchored on `/job/` and the run pattern on `/actions/runs/`.
_JOB_LINK_RE = re.compile(r"/job/(\d+)")
_RUN_LINK_RE = re.compile(r"/actions/runs/(\d+)")

# Emitted by `tests/ux/conftest.py::pytest_terminal_summary`. Deliberately matched with
# `search`, not `match`: `gh run view --log` prefixes every line with
# "<job name>\t<step>\t<timestamp> ". Deliberately the ASCII summary lines, NOT the
# sibling "[ux] RERUN - this attempt FAILED:" line, whose em dash is an encoding hazard
# on this machine's cp1252 console (the same hazard `_safe_print` exists to absorb).
_RERUN_ALARM_RE = re.compile(r"\[ux\] rerun-rate alarm: (\d+) test\(s\) needed a retry")
_RERUN_DETAIL_RE = re.compile(r"(\S+::\S+) - (\d+) attempt\(s\) failed")

_PASSING_BUCKETS = frozenset({"pass"})
_PENDING_BUCKETS = frozenset({"pending"})


@dataclass(frozen=True)
class Check:
    """One row of `gh pr checks --json name,state,bucket,link`."""

    name: str
    state: str
    bucket: str
    link: str


@dataclass(frozen=True)
class RunScan:
    """Result of scanning one workflow run's log for the ux rerun-rate alarm."""

    run_id: str
    ok: bool
    error: str
    declared: list[int]
    tests: list[tuple[str, int]]


def parse_checks(payload: str) -> list[Check]:
    """Parse `gh pr checks --json ...` output into `Check` rows.

    Raises `ValueError` on anything that is not a JSON list of objects — an unparseable
    payload must surface, never degrade to an empty list (the `|| echo '[]'` defect).
    """
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError(
            f"expected a JSON list from `gh pr checks --json`, got {type(data).__name__}"
        )
    return [
        Check(
            name=str(row.get("name", "")),
            state=str(row.get("state", "")),
            bucket=str(row.get("bucket", "")),
            link=str(row.get("link", "")),
        )
        for row in data
    ]


def parse_job_id(link: str) -> str | None:
    """Extract the workflow job id from a check's link, or `None` if it carries none."""
    match = _JOB_LINK_RE.search(link)
    return match.group(1) if match else None


def parse_run_id(link: str) -> str | None:
    """Extract the workflow run id from a check's link, or `None` if it carries none."""
    match = _RUN_LINK_RE.search(link)
    return match.group(1) if match else None


def distinct_run_ids(checks: Sequence[Check]) -> list[str]:
    """Run ids across `checks`, de-duplicated, in first-seen order.

    De-duplicating by **run** rather than by job is the whole efficiency story. Measured
    on this repo (2026-08-05): a whole-run log (4 jobs, 2.88 MB) took 4.7 s; a single-job
    log (133 KB) took 4.4 s — so `gh` log fetches are latency-bound per request, not
    payload-bound. The six required checks span three runs (one CI run holding four jobs,
    plus two CodeQL runs), so scanning per-run costs three round-trips where a per-job
    scan would cost six, for the same coverage.
    """
    seen: dict[str, None] = {}
    for check in checks:
        run_id = parse_run_id(check.link)
        if run_id is not None:
            seen.setdefault(run_id, None)
    return list(seen)


def scan_reruns(log_text: str) -> tuple[list[int], list[tuple[str, int]]]:
    """Find the ux tier's rerun-rate alarm in a fetched job/run log.

    Returns `(declared_counts, tests)` — the counts each alarm line *declares*, and the
    `(nodeid, failed_attempts)` pairs parsed from the detail lines beneath them. Both are
    returned rather than reconciled here so the caller can report a disagreement instead
    of silently trusting one; a parser that quietly picked one number would be the same
    class of defect this whole module exists to fix.
    """
    declared = [int(m.group(1)) for m in _RERUN_ALARM_RE.finditer(log_text)]
    tests: dict[str, int] = {}
    for match in _RERUN_DETAIL_RE.finditer(log_text):
        nodeid, attempts = match.group(1), int(match.group(2))
        tests[nodeid] = max(tests.get(nodeid, 0), attempts)
    return declared, sorted(tests.items())


def classify(required: Sequence[Check]) -> tuple[int, list[Check]]:
    """Map the required-check set to a verdict exit code plus the offending rows.

    A required check reporting `skipping` counts as **not green**: branch protection will
    not accept a skipped required context, so calling it green would hand the caller a
    merge that cannot happen.
    """
    if not required:
        return EXIT_ERROR, []
    blocking = [c for c in required if c.bucket not in _PASSING_BUCKETS | _PENDING_BUCKETS]
    if blocking:
        return EXIT_FAILED, blocking
    pending = [c for c in required if c.bucket in _PENDING_BUCKETS]
    if pending:
        return EXIT_PENDING, pending
    return EXIT_GREEN, []


def _gh(args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run a `gh` subcommand, capturing output. The single network seam in this module."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["gh", *args],  # noqa: S607 - `gh` intentionally resolved from PATH
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )


def _gh_checks(pr_args: list[str], *, required: bool) -> list[Check]:
    """Query check state as JSON.

    **A nonzero return code is not an error here.** `gh pr checks` documents exit 8 for
    "checks pending" and exits nonzero on failure — both are states this wrapper must
    report, not states it may discard. So stdout is parsed whenever it is non-empty, and
    only an unparseable/empty payload raises.
    """
    args = ["pr", "checks", *pr_args, "--json", "name,state,bucket,link"]
    if required:
        args.append("--required")
    result = _gh(args)
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(
            f"`gh {' '.join(args)}` produced no JSON (exit {result.returncode}): "
            f"{result.stderr.strip() or '<no stderr>'}"
        )
    return parse_checks(stdout)


def _scan_run(run_id: str) -> RunScan:
    """Fetch one run's full log and scan it for the rerun alarm.

    `--log` (not `--log-failed`): on a green run there are no failed steps, so
    `--log-failed` returns nothing and the scan would pass vacuously — the inert-instrument
    trap that item 44's own probe hit before its control arm caught it.
    """
    result = _gh(["run", "view", run_id, "--log"])
    if result.returncode != 0 or not result.stdout:
        return RunScan(
            run_id=run_id,
            ok=False,
            error=result.stderr.strip() or f"exit {result.returncode}, empty log",
            declared=[],
            tests=[],
        )
    declared, tests = scan_reruns(result.stdout)
    return RunScan(run_id=run_id, ok=True, error="", declared=declared, tests=tests)


def _print_checks(label: str, checks: Sequence[Check]) -> None:
    if not checks:
        print(f"ci-wait: {label}: (none)")
        return
    print(f"ci-wait: {label}:")
    for check in sorted(checks, key=lambda c: c.name):
        print(f"    [{check.bucket:>8}] {check.name}")


def _report_failures(blocking: Sequence[Check], tail_lines: int) -> None:
    """Print each failing required check with the tail of its own failed-step log."""
    for check in blocking:
        print(f"\nci-wait: FAILING REQUIRED CHECK - {check.name} ({check.state})")
        print(f"    {check.link}")
        job_id = parse_job_id(check.link)
        if job_id is None:
            print("    (no job log available - this check's link carries no /job/<id>)")
            continue
        result = _gh(["run", "view", "--job", job_id, "--log-failed"])
        if result.returncode != 0 or not result.stdout.strip():
            print(f"    (could not fetch failed-step log: {result.stderr.strip() or 'empty'})")
            continue
        lines = result.stdout.splitlines()
        shown = lines[-tail_lines:]
        if len(lines) > tail_lines:
            print(f"    ... ({len(lines) - tail_lines} earlier lines omitted)")
        for line in shown:
            print(f"    {line}")


def _run(args: argparse.Namespace) -> int:
    pr_args: list[str] = [str(args.pr)] if args.pr else []
    target = f"PR #{args.pr}" if args.pr else "the current branch's PR"

    required = _gh_checks(pr_args, required=True)
    print(f"ci-wait: watching {len(required)} required check(s) on {target}")
    _print_checks("required", required)

    timeout_s = args.timeout_minutes * 60.0
    watch_cmd = [
        "pr",
        "checks",
        *pr_args,
        "--watch",
        "--required",
        "--fail-fast",
        "--interval",
        str(args.interval),
    ]
    print(f"ci-wait: gh {' '.join(watch_cmd)}  (deadline {args.timeout_minutes:g} min)")
    try:
        # Output is deliberately NOT captured — `--watch` renders live progress, and
        # passing it through untouched matches `scripts/gate.py`'s convention.
        subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            ["gh", *watch_cmd],  # noqa: S607 - `gh` intentionally resolved from PATH
            check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        print(
            f"\nci-wait: deadline of {args.timeout_minutes:g} min expired while checks were running"
        )
        return EXIT_PENDING

    # `gh`'s own exit code is deliberately ignored: re-query and decide from the
    # authoritative JSON, so the verdict never depends on interpreting a watch exit.
    required = _gh_checks(pr_args, required=True)
    everything = _gh_checks(pr_args, required=False)
    required_names = {c.name for c in required}
    advisory = [c for c in everything if c.name not in required_names]

    verdict, offenders = classify(required)
    print()
    _print_checks("required (final)", required)
    _print_checks("advisory (reported, never gating)", advisory)

    if verdict == EXIT_ERROR:
        print("ci-wait: no required checks found - is branch protection configured?")
        return EXIT_ERROR
    if verdict == EXIT_FAILED:
        _report_failures(offenders, args.tail)
        return EXIT_FAILED
    if verdict == EXIT_PENDING:
        print("ci-wait: still pending after the watch returned:")
        for check in offenders:
            print(f"    {check.name}")
        return EXIT_PENDING

    if args.no_rerun_scan:
        print("ci-wait: rerun scan SKIPPED (--no-rerun-scan) - absorbed reruns NOT ruled out")
        return EXIT_GREEN

    run_ids = distinct_run_ids(required)
    print(f"\nci-wait: scanning {len(run_ids)} run log(s) for absorbed reruns")
    scans = [_scan_run(run_id) for run_id in run_ids]

    broken = [s for s in scans if not s.ok]
    if broken:
        for scan in broken:
            print(f"ci-wait: could not fetch log for run {scan.run_id}: {scan.error}")
        print("ci-wait: rerun scan incomplete - refusing to report a clean green")
        return EXIT_ERROR

    tests = sorted({t for scan in scans for t in scan.tests})
    declared_total = sum(sum(scan.declared) for scan in scans)
    if not tests and declared_total == 0:
        print("ci-wait: no absorbed reruns found in any required run log")
        return EXIT_GREEN

    print(f"ci-wait: RERUN ALARM - {len(tests)} test(s) needed a retry")
    for nodeid, attempts in tests:
        print(f"    {nodeid} - {attempts} of 3 attempts failed")
    if declared_total != len(tests):
        print(
            f"ci-wait: NOTE - alarm lines declared {declared_total} test(s) but "
            f"{len(tests)} detail line(s) parsed; reporting both rather than guessing"
        )
    return EXIT_GREEN_WITH_RERUNS


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.ci_wait",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pr", nargs="?", default=None, help="PR number (default: current branch)")
    parser.add_argument("--timeout-minutes", type=float, default=30.0, help="hard deadline")
    parser.add_argument("--interval", type=int, default=10, help="gh watch poll interval, seconds")
    parser.add_argument("--tail", type=int, default=60, help="failed-log tail lines to print")
    parser.add_argument(
        "--no-rerun-scan",
        action="store_true",
        help="skip the absorbed-rerun scan (saves round-trips; says so loudly)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Wait for a PR's required checks and report a single, never-silent verdict."""
    args = _parse_args(argv)
    code = EXIT_ERROR
    try:
        code = _run(args)
    except FileNotFoundError:
        print("ci-wait: `gh` not found on PATH - install the GitHub CLI", file=sys.stderr)
        code = EXIT_ERROR
    except KeyboardInterrupt:
        print("\nci-wait: interrupted", file=sys.stderr)
        code = EXIT_ERROR
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ci-wait: {type(exc).__name__}: {exc}", file=sys.stderr)
        code = EXIT_ERROR
    finally:
        # The one guarantee this module makes: exactly one terminal line, always.
        # Silence is the defect being fixed, so it is made structurally impossible.
        print(f"ci-wait: {_VERDICT_LABELS.get(code, 'UNKNOWN')} (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
