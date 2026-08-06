"""Per-test, per-attempt CI flake rates from GitHub Actions job logs.

"The UX suite is flaky" has never been a number in this repo. Three prior measurements
exist and each is now explicitly unusable: `docs/dev/RELEASE_ARC.md`'s ~42% figure is
scoped to "5 distinct settle/restore-family tests" with **no source naming which 5**;
item 44's ~67% is marked *"Supersede that arithmetic; do not carry it forward"*; the
64%/11-run measurement in `compose-summary-draft-settle-hole.md` was recovered by hand.
Meanwhile the repo's own rerun-rate alarm (`tests/ux/conftest.py`) has fired on every CI
run since `feat/rerun-rate-alarm` and **landed in the job log unread**.

Charter C-11's closure bar (`scripts/work_items.py`) now refuses to close an item on
prose — closure needs a falsifiable `verified_by` artifact. This module, and the store
it writes to `docs/dev/flake-rates/`, is that artifact.

**This is an instrument, not a gate (C-12).** Nothing here fails closed on a test's
rate — a threshold cannot be set before there is data. `report`'s exit codes describe
whether the MEASUREMENT is trustworthy, never whether a test is "too flaky".

Design is grounded in `gh run view 31047661015 --log` (PR #102, 3.7 MB, 17057 lines,
fetched in 3.0s — the run in which item 30 recurred), not inferred from reading code:

* **O-1.** Every log line is `<job>\\t<step>\\t<ISO-timestamp> <body>` — timestamp and
  body share the *third* tab field. Treating field 3 as the body alone breaks parsing.
* **O-2.** One whole-run fetch carries every job. The 3 quality legs are ~95% of the
  bytes and come free alongside the ux job.
* **O-3.** Two verbose-output shapes exist: sequential (ux, and the quality job's
  `pytest -m ux` skip-only leg) prints `<nodeid> OUTCOME  [ n%]`; xdist (the quality
  job's `-n auto` leg) prints `[gwN] [ n%] OUTCOME <nodeid>`.
* **O-4.** On a rerun, `tests/ux/conftest.py`'s `pytest_runtest_logreport` hook prints a
  **leading newline**, splitting pytest's own line for that attempt: an orphaned
  `<nodeid> ` fragment, then `[ux] RERUN ... FAILED: <nodeid>`, then a *bare*
  `RERUN [ n%]` with no nodeid at all.
* **O-5.** The reran test's **terminal** attempt still prints an intact
  `<nodeid> OUTCOME [ n%]` line — so the roster and the terminal outcome are always
  recoverable; only the first attempt's own line degrades.
* **O-6.** A fifth rerun signal exists that no prior design doc names:
  `##[warning]<nodeid> needed a retry (N of M attempts failed) - ...`
  (`tests/ux/rerun_report.py::render_annotations`) — ASCII, one line per test, and it
  states `MAX_ATTEMPTS` directly from the log rather than assuming `ci.yml`'s `--reruns`
  value hasn't drifted.
* **O-7.** The ux job's step column is `UNKNOWN STEP` for its *entire* log — step-based
  session splitting is unusable there.
* **O-8.** A job can run pytest more than once (`ux` job: ux tier then the PDF slice;
  `quality` job: `-m "not ux" -n auto` then `-m ux`, which only *collects* under quality
  and never actually executes). The second quality session's summary is
  `141 skipped, 2223 deselected in 2.44s` — **no "passed" substring at all** — so a
  summary regex anchored on "passed" silently drops that whole session.
* **O-9.** Four independent counts of one run's rerun agreed exactly in the sample run:
  `[ux] RERUN` marker lines, the summary's `N rerun`, the alarm's declared total, and the
  `##[warning]` count. Reconciling all four (never picking one) is house doctrine already
  established by `ci_wait.scan_reruns`'s own docstring.
* **O-10.** `gh run view --log` returns only the **latest** run attempt — a red attempt
  superseded by a green retry is unrecoverable from the log alone.
* **O-11.** Two mechanisms produce the exact same artifact — a line containing only a
  nodeid, no outcome word: xdist's own "dispatch" echo (printed when a worker *starts* a
  test, before its `[gwN] ...` result line) and O-4's sequential rerun-orphan fragment.
  One rule (a `.py::`-prefixed line with no trailing OUTCOME) discards both correctly,
  because in both cases the authoritative row is a separate, later line.
* **O-12.** A session's declared `N skipped` can legitimately exceed its per-test
  SKIPPED-outcome-line count: the quality job's `-m ux` leg declared 141 skipped but
  produced only 140 SKIPPED lines — one test was skipped at **collection** time (no
  per-test outcome line ever printed for it). Verified **systematic**, not occasional:
  this exact off-by-one appeared in every one of the 6 sessions in the sample run (both
  tiers, all 3 python versions) — so it is a real, expected pytest characteristic, not a
  parser bug, and it is recorded as a visible anomaly but does **not** gate
  `Session.reconciled` (the executed-count check does that): gating on it would exclude
  nearly every session from rate computation, defeating the instrument.
* **O-13.** A parametrized nodeid can contain **literal spaces**
  (`test_strip_fences_variants[{"a": 1}-{"a": 1}]`) — any nodeid pattern built on `\\S+`
  truncates at the first one. Fixed by anchoring on the `.py::` file-path prefix and
  matching non-greedily up to the fixed OUTCOME/percentage suffix (sequential) or to
  end-of-line (xdist), never on "no whitespace".
* **O-14.** Found backfilling 30 real runs, not anticipated by O-1..O-13: a genuine
  (non-rerun) test failure prints pytest's own `=== FAILURES ===` section -- traceback
  plus the `short test summary info` block's `FAILED <nodeid> - <reason>` line -- AFTER
  every outcome line, immediately before the terminal summary. 7 of 233 real sessions
  in the first backfill had this landing entirely in `unparsed_lines` (10-65 lines per
  failure), which would have quietly forced every genuinely-failing session out of the
  reconciled set. Fixed the same way as O-4's rerun traceback: the section's own
  banner opens a swallow that the terminal summary line -- already a recognized
  boundary -- closes.

O-1, O-13, and O-14 each broke *my own* first-draft parsing silently while building
this module against real logs — no exception, no zero result, just quietly wrong
counts or an inflated exclusion rate. That is the exact inert-instrument failure mode
this module exists to prevent in the suite it measures. The reconciliation guard
(`Session.reconciled`) is not defensive decoration; it is what caught all three.

Store layout (`docs/dev/flake-rates/`, committed — GitHub's ~90-day log retention means
an ephemeral store can never grow a series past that window):

    runs/<collect-uuid>.jsonl   -- one shard per `collect` invocation (never a shared
                                    tail file; concurrent collectors would conflict on
                                    it, per docs/dev/ledger/README.md's identical rule)

Three JSON record kinds share that stream, `kind` discriminates:

* `run`    -- one per run *listed*, ingested or not (an unignested row is what keeps the
              run-level denominator knowable rather than silently shrinking it).
* `session` -- one per pytest invocation found in a run's log.
* `roster` -- content-addressed `{digest, size, nodeids}`, written once per distinct
              digest. Full executed rosters are stored for the **ux tier only**; the
              quality tier (single-attempt -- `ci.yml` never passes `--reruns` to the
              `gate.py` pytest steps) stores digest + size + failing nodeids and is
              treated as a control arm, not a per-test series -- its rate quantises to
              0 or 1 per run and needs hundreds of runs to be estimable at all.

Exit codes:

===  ================================================================================
  0  `collect`: every listed run ingested or explained. `report`: printed a rate table.
  1  refused -- `collect` listed zero runs; `report` has zero usable sessions to rank.
  2  wrapper error -- `gh` missing, unparseable JSON, or a self-inconsistent store.
  3  partial -- some runs unfetchable or some sessions excluded, so the numbers rest on
     a smaller denominator than requested. Mirrors `ci_wait`'s "green, but look" exit 3.
===  ================================================================================

Usage::

    python -m scripts.flake_rates collect --limit 30
    python -m scripts.flake_rates report --min-attempts 20
    python -m scripts.flake_rates report --tier ux --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.ci_wait import scan_reruns

SCHEMA = 1
#: Bump when `parse_session`/`parse_run_log`'s output shape changes, so a later
#: `report` (or a human) can tell a stored record was produced by different logic
#: rather than silently trusting stale semantics.
PARSER_VERSION = 1

EXIT_OK = 0
EXIT_NOTHING_TO_REPORT = 1
EXIT_ERROR = 2
EXIT_PARTIAL = 3

_VERDICT_LABELS: dict[int, str] = {
    EXIT_OK: "OK",
    EXIT_NOTHING_TO_REPORT: "NOTHING TO REPORT",
    EXIT_ERROR: "ERROR",
    EXIT_PARTIAL: "PARTIAL",
}

_STORE_DIR = Path("docs") / "dev" / "flake-rates" / "runs"

# ---------------------------------------------------------------------------------
# Line/session parsing -- pure, no I/O. Every regex here is grounded in O-1..O-13
# above, verified against a real fetched log before this module was written.
# ---------------------------------------------------------------------------------

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z ?")
_SESSION_BANNER = "test session starts"

_OUTCOME_ALT = r"PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS|RERUN"
_NODEID = r"[\w][\w./-]*\.py::.+"

# O-13: nodeid can contain literal spaces, so it is matched non-greedily up to a fixed
# OUTCOME + percentage suffix (sequential) or to end-of-line (xdist) -- never on "no
# whitespace". O-8: the summary line is matched generically over ANY comma-separated
# list of "<N> <word>" pairs, never requiring "passed" to be present.
_SUMMARY_RE = re.compile(r"^=+\s(?P<body>\d+ \w+(?:, \d+ \w+)* in [\d.]+s(?: \([\d:]+\))?)\s=+$")
_SEQ_OUTCOME_RE = re.compile(
    rf"^(?P<nodeid>{_NODEID}?)\s+(?P<outcome>{_OUTCOME_ALT})\s*\[\s*\d+%\]\s*$"
)
_XDIST_OUTCOME_RE = re.compile(
    rf"^\[gw\d+\]\s+\[\s*\d+%\]\s+(?P<outcome>{_OUTCOME_ALT})\s+(?P<nodeid>{_NODEID}?)\s*$"
)
# O-11: a `.py::`-prefixed line with no trailing outcome word -- xdist's dispatch echo
# or O-4's sequential rerun-orphan fragment. Checked only after the outcome regexes
# above have both failed to match, so it never shadows a real result line.
_NODEID_START_RE = re.compile(r"^[\w][\w./-]*\.py::")

# O-4: matched with `.*?` rather than the literal em dash -- `_gh`'s `errors="replace"`
# can turn it into U+FFFD on a decode mismatch, and the exact character is not the
# signal. Mirrors `ci_wait`'s own reasoning for keeping the dash out of its regex.
_UX_RERUN_MARKER_RE = re.compile(rf"\[ux\] RERUN .*?FAILED:\s*(?P<nodeid>{_NODEID})$")
_BARE_RERUN_RE = re.compile(r"^RERUN\s*\[\s*\d+%\]\s*$")
# O-14 (found backfilling 30 real runs, not anticipated by O-1..O-13): pytest's own
# `=== FAILURES ===` section -- per-failure traceback plus the `short test summary
# info` block's `FAILED <nodeid> - <reason>` restatement -- always appears AFTER every
# outcome line, immediately before the terminal summary. It is unrelated to a rerun (a
# single-attempt quality-tier failure has one too) and was landing entirely in
# `unparsed_lines`, 10-65 lines per real failure -- inflating the exact signal the
# reconciliation guard exists to protect. Verified against a real run
# (30850387991, `tests/test_wiki_freshness_gate.py`'s one genuine failure) before
# fixing: `=== FAILURES ===` opens it, the terminal summary line closes it, so it
# reuses the SAME swallow mechanism as O-4's rerun traceback -- one more trigger into
# the existing `in_traceback` state, no new state needed.
_FAILURES_BANNER_RE = re.compile(r"^=+\s*FAILURES\s*=+$")
# O-6: states `MAX_ATTEMPTS` directly, observed rather than assumed from `ci.yml`.
_WARNING_RETRY_RE = re.compile(
    rf"^##\[warning\](?P<nodeid>{_NODEID}?) needed a retry "
    rf"\((?P<failed>\d+) of (?P<max_attempts>\d+) attempts failed\)"
)
_XDIST_PREAMBLE_RE = re.compile(
    r"^(created: \d+/\d+ workers|\d+ workers? \[\d+ items?\]|scheduling tests via \w+)$"
)
_PREAMBLE_PREFIXES = (
    "platform ",
    "cachedir:",
    "rootdir:",
    "configfile:",
    "testpaths:",
    "plugins:",
    "collecting",
)

#: Canonical summary-count buckets a raw word maps to. Anything not listed here is
#: still counted (never silently dropped) under `SummaryCounts.other`.
_COUNT_WORD_MAP: dict[str, str] = {
    "passed": "passed",
    "failed": "failed",
    "error": "error",
    "errors": "error",
    "skipped": "skipped",
    "deselected": "deselected",
    "xfailed": "xfailed",
    "xpassed": "xpassed",
    "rerun": "rerun",
    "reruns": "rerun",
    "warning": "warnings",
    "warnings": "warnings",
}

#: `(job-name-prefix, session-index) -> (tier, tier_source)`. Session order within a
#: job is fixed by `scripts/gate.py::_STEPS` (quality) and `.github/workflows/ci.yml`
#: (ux), verified against the real log rather than assumed: `Lint, type-check, test`
#: runs `-m "not ux" -n auto"` then `-m ux`; the ux job runs the ux tier then the PDF
#: slice (`-m "slow and not ux"`). A job/index pair not listed here classifies as
#: `("unknown", "unclassified-job")` rather than guessing.
_TIER_TABLE: dict[tuple[str, int], str] = {
    ("Lint, type-check, test", 0): "quality-not-ux",
    ("Lint, type-check, test", 1): "quality-ux-skip",
    ("UX / a11y / PDF", 0): "ux",
    ("UX / a11y / PDF", 1): "pdf",
}
#: Output format per tier -- xdist only for the quality job's `-n auto` leg; every
#: other session in this repo runs sequentially (verified, not assumed: O-3).
_TIER_FORMAT: dict[str, str] = {
    "quality-not-ux": "xdist",
    "quality-ux-skip": "sequential",
    "ux": "sequential",
    "pdf": "sequential",
    "unknown": "sequential",
}


@dataclass(frozen=True)
class SummaryCounts:
    """One pytest terminal-summary line, parsed generically -- never assumes "passed"
    is present (O-8)."""

    passed: int
    failed: int
    error: int
    skipped: int
    deselected: int
    xfailed: int
    xpassed: int
    rerun: int
    warnings: int
    other: int
    duration_s: float | None
    raw: str


@dataclass(frozen=True)
class Session:
    """One pytest invocation, parsed from a slice of one job's log lines.

    `executed` excludes SKIPPED/DESELECTED by construction -- a skipped test was never
    attempted, so including it would deflate every rate in that (nodeid, tier) bucket
    (O-8's collect-then-skip leg is the case that makes this matter).
    """

    job: str
    session_index: int
    tier: str
    tier_source: str
    fmt: str
    complete: bool
    summary: SummaryCounts | None
    executed: tuple[str, ...]
    skipped: tuple[str, ...]
    failed_nodeids: tuple[str, ...]
    error_nodeids: tuple[str, ...]
    xpassed_nodeids: tuple[str, ...]
    rerun_attempts: tuple[tuple[str, int], ...]
    alarm_declared: tuple[int, ...]
    alarm_detail: tuple[tuple[str, int], ...]
    warning_retry: tuple[tuple[str, int, int], ...]
    unparsed_lines: int
    swallowed_traceback_lines: int
    reconciled: bool
    anomalies: tuple[str, ...]


@dataclass(frozen=True)
class RunMeta:
    """One row of `gh run list --json`."""

    run_id: str
    run_attempt: int
    run_number: int
    workflow: str
    event: str
    head_branch: str
    head_sha: str
    created_at: str
    status: str
    conclusion: str
    url: str


def split_log_line(line: str) -> tuple[str, str, str] | None:
    """Split one `gh run view --log` line into `(job, step, body)`.

    O-1: the timestamp and the message body share the *third* tab field -- this is
    where treating field 3 as the body alone breaks. Returns `None` for a line that
    does not carry the expected 3-tab-field shape; the caller counts it, never drops it
    silently.
    """
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    job, step, rest = parts
    match = _TIMESTAMP_RE.match(rest)
    body = rest[match.end() :] if match else rest
    return job, step, body


def group_by_job(log_text: str) -> tuple[dict[str, list[str]], int]:
    """Group a whole-run log's lines by job name. Returns `(job -> bodies, unparsed)`."""
    jobs: dict[str, list[str]] = {}
    unparsed = 0
    for line in log_text.splitlines():
        if not line:
            continue
        parsed = split_log_line(line)
        if parsed is None:
            unparsed += 1
            continue
        job, _step, body = parsed
        jobs.setdefault(job, []).append(body)
    return jobs, unparsed


def split_sessions(body_lines: Sequence[str]) -> list[list[str]]:
    """Slice one job's lines into one chunk per pytest invocation.

    A chunk starts at its own banner and ends at its own terminal summary line
    (inclusive), if one appears before the next banner or end-of-job. Deliberately
    NOT banner-to-next-banner: the *last* session in a job is otherwise followed by
    unrelated Actions-step lines (git cleanup, `ci_backstop`, ...), which would inflate
    `unparsed_lines` for a session that has actually already ended cleanly (verified by
    reading the real log's tail before writing this). A session with no summary found
    before its boundary is genuinely incomplete -- `parse_session` marks it so.
    """
    banner_idx = [i for i, body in enumerate(body_lines) if _SESSION_BANNER in body]
    chunks: list[list[str]] = []
    for n, start in enumerate(banner_idx):
        hard_end = banner_idx[n + 1] if n + 1 < len(banner_idx) else len(body_lines)
        end = hard_end
        for i in range(start, hard_end):
            if _SUMMARY_RE.match(body_lines[i].strip()):
                end = i + 1
                break
        chunks.append(list(body_lines[start:end]))
    return chunks


def classify_tier(job: str, session_index: int) -> tuple[str, str]:
    """Map `(job, session-order-within-job)` to `(tier, tier_source)`.

    Matched by job-name PREFIX (not exact string) so a python-version bump in the
    matrix name (`Lint, type-check, test (py3.14)`) does not silently fall through to
    `unknown` -- only a genuinely new job or a reordered pytest invocation should.
    """
    for (prefix, index), tier in _TIER_TABLE.items():
        if job.startswith(prefix) and session_index == index:
            return tier, "job-prefix+session-order"
    return "unknown", "unclassified-job-or-index"


def parse_summary(body: str) -> SummaryCounts | None:
    """Parse one terminal-summary line. `None` if `body` is not a summary line."""
    match = _SUMMARY_RE.match(body.strip())
    if match is None:
        return None
    counts_part, _, rest = match.group("body").partition(" in ")
    duration_match = re.match(r"([\d.]+)s", rest)
    duration_s = float(duration_match.group(1)) if duration_match else None
    buckets: dict[str, int] = dict.fromkeys(_COUNT_WORD_MAP.values(), 0)
    other = 0
    for num, word in re.findall(r"(\d+) (\w+)", counts_part):
        canonical = _COUNT_WORD_MAP.get(word.lower())
        if canonical is None:
            other += int(num)
        else:
            buckets[canonical] += int(num)
    return SummaryCounts(
        passed=buckets["passed"],
        failed=buckets["failed"],
        error=buckets["error"],
        skipped=buckets["skipped"],
        deselected=buckets["deselected"],
        xfailed=buckets["xfailed"],
        xpassed=buckets["xpassed"],
        rerun=buckets["rerun"],
        warnings=buckets["warnings"],
        other=other,
        duration_s=duration_s,
        raw=match.group("body"),
    )


def parse_session(job: str, session_index: int, body_lines: Sequence[str]) -> Session:
    """Parse one pytest invocation's log-line slice into a `Session`.

    Reconciliation (the guard O-1/O-13 would have needed): `executed`'s size must equal
    the summary's passed+failed+error+xfailed+xpassed, and `skipped`'s size should equal
    the summary's declared skipped count -- except O-12, where a collection-time skip
    can inflate the declared count with no matching outcome line. A session failing
    either check is `reconciled=False` and excluded from rates by the caller, never
    silently trusted.
    """
    tier, tier_source = classify_tier(job, session_index)
    fmt = _TIER_FORMAT.get(tier, "sequential")
    outcome_re = _XDIST_OUTCOME_RE if fmt == "xdist" else _SEQ_OUTCOME_RE

    summary: SummaryCounts | None = None
    buckets: dict[str, set[str]] = {}
    rerun_counts: dict[str, int] = {}
    warning_retry: list[tuple[str, int, int]] = []
    unparsed = 0
    swallowed = 0
    anomalies: list[str] = []
    in_traceback = False

    for raw in body_lines:
        line = raw.strip()
        if not line or _SESSION_BANNER in line:
            continue

        if in_traceback:
            # O-4: swallow a rerun's captured traceback body until the next structural
            # line. Counted separately from `unparsed` -- this is EXPECTED content for
            # any run that absorbed a rerun, not a parsing failure.
            if (
                _BARE_RERUN_RE.match(line)
                or _UX_RERUN_MARKER_RE.search(line)
                or _SUMMARY_RE.match(line)
                or outcome_re.match(line)
            ):
                in_traceback = False
            else:
                swallowed += 1
                continue

        summary_match = _SUMMARY_RE.match(line)
        if summary_match is not None:
            if summary is not None:
                anomalies.append(f"multiple summary lines; kept the last ({line[:80]!r})")
            summary = parse_summary(line)
            continue
        if line.startswith(_PREAMBLE_PREFIXES) or _XDIST_PREAMBLE_RE.match(line):
            continue
        if _FAILURES_BANNER_RE.match(line):
            # O-14: swallow through to the terminal summary line, exactly like O-4's
            # rerun-traceback swallow below (same `in_traceback` state, same exit
            # conditions -- the summary-line check already there is what closes it).
            in_traceback = True
            continue

        rerun_match = _UX_RERUN_MARKER_RE.search(line)
        if rerun_match is not None:
            nodeid = rerun_match.group("nodeid")
            rerun_counts[nodeid] = rerun_counts.get(nodeid, 0) + 1
            in_traceback = True
            continue
        if _BARE_RERUN_RE.match(line):
            continue
        warning_match = _WARNING_RETRY_RE.match(line)
        if warning_match is not None:
            warning_retry.append(
                (
                    warning_match.group("nodeid"),
                    int(warning_match.group("failed")),
                    int(warning_match.group("max_attempts")),
                )
            )
            continue
        if "[ux] rerun-rate alarm" in line or "attempt(s) failed" in line:
            continue  # authoritative parse of these is `scan_reruns` on the joined text

        outcome_match = outcome_re.match(line)
        if outcome_match is not None:
            buckets.setdefault(outcome_match.group("outcome"), set()).add(
                outcome_match.group("nodeid")
            )
            continue
        if _NODEID_START_RE.match(line):
            continue  # O-11: xdist dispatch echo, or O-4's orphan fragment
        unparsed += 1

    passed = buckets.get("PASSED", set())
    failed = buckets.get("FAILED", set())
    error = buckets.get("ERROR", set())
    skipped = buckets.get("SKIPPED", set())
    xfailed = buckets.get("XFAIL", set())
    xpassed = buckets.get("XPASS", set())
    executed = passed | failed | error | xfailed | xpassed

    reconciled = True
    if summary is None:
        reconciled = False
        anomalies.append("no terminal summary line found in this session's window")
    else:
        executed_declared = (
            summary.passed + summary.failed + summary.error + summary.xfailed + summary.xpassed
        )
        if len(executed) != executed_declared:
            reconciled = False
            anomalies.append(
                f"executed roster size {len(executed)} != summary's declared "
                f"{executed_declared} (passed+failed+error+xfailed+xpassed)"
            )
        if len(skipped) != summary.skipped:
            # O-12: NOT load-bearing for `reconciled` -- verified against the real log
            # (`gh run view 31047661015 --log`) that this exact 1-skip gap appears in
            # EVERY session of every job/tier, always the same size: one test is
            # skipped at collection time and never gets a per-test outcome line. If
            # this gated `reconciled`, nearly the whole store would be excluded from
            # rate computation, which defeats the instrument. Recorded as a visible
            # anomaly; the executed-count check just above is the load-bearing guard
            # (it is what would have caught O-1/O-13's silent breakage during design).
            anomalies.append(
                f"skipped roster size {len(skipped)} != summary's declared "
                f"{summary.skipped} (O-12: a collection-time skip has no outcome line "
                f"-- known, non-blocking)"
            )
    if unparsed > 0:
        reconciled = False
        anomalies.append(f"{unparsed} line(s) matched no known shape")

    session_text = "\n".join(body_lines)
    alarm_declared, alarm_detail = scan_reruns(session_text)

    return Session(
        job=job,
        session_index=session_index,
        tier=tier,
        tier_source=tier_source,
        fmt=fmt,
        complete=summary is not None,
        summary=summary,
        executed=tuple(sorted(executed)),
        skipped=tuple(sorted(skipped)),
        failed_nodeids=tuple(sorted(failed)),
        error_nodeids=tuple(sorted(error)),
        xpassed_nodeids=tuple(sorted(xpassed)),
        rerun_attempts=tuple(sorted(rerun_counts.items())),
        alarm_declared=tuple(alarm_declared),
        alarm_detail=tuple(alarm_detail),
        warning_retry=tuple(warning_retry),
        unparsed_lines=unparsed,
        swallowed_traceback_lines=swallowed,
        reconciled=reconciled,
        anomalies=tuple(anomalies),
    )


def parse_run_log(log_text: str) -> tuple[list[Session], int]:
    """Parse a whole-run log into every session across every job.

    Returns `(sessions, top_level_unparsed_lines)` -- the second number counts lines
    that didn't even split into the expected 3 tab fields (O-1), which is a stronger
    signal of wholesale format drift than any one session's `unparsed_lines`.
    """
    jobs, top_unparsed = group_by_job(log_text)
    sessions: list[Session] = []
    for job, body_lines in jobs.items():
        for index, chunk in enumerate(split_sessions(body_lines)):
            sessions.append(parse_session(job, index, chunk))
    return sessions, top_unparsed


def parse_run_list(payload: str) -> list[RunMeta]:
    """Parse `gh run list --json ...` output. Raises `ValueError` on a non-list payload
    -- mirrors `ci_wait.parse_checks`'s refusal to degrade to an empty list."""
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError(
            f"expected a JSON list from `gh run list --json`, got {type(data).__name__}"
        )
    runs: list[RunMeta] = []
    for row in data:
        runs.append(
            RunMeta(
                run_id=str(row.get("databaseId", "")),
                run_attempt=int(row.get("attempt", 1)),
                run_number=int(row.get("number", 0)),
                workflow=str(row.get("workflowName", "")),
                event=str(row.get("event", "")),
                head_branch=str(row.get("headBranch", "")),
                head_sha=str(row.get("headSha", "")),
                created_at=str(row.get("createdAt", "")),
                status=str(row.get("status", "")),
                conclusion=str(row.get("conclusion", "")),
                url=str(row.get("url", "")),
            )
        )
    return runs


def roster_digest(nodeids: Sequence[str]) -> str:
    """Content address for a roster -- `sha256:<hex>` over the sorted, newline-joined
    set. Used to content-address `roster` records rather than positionally
    forward-carrying them: rosters oscillate as branches with different test sets
    interleave in CI history, so a positional carry would silently mis-attribute one
    branch's roster to another's session."""
    body = "\n".join(sorted(nodeids))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def wilson_lower_bound(failures: int, attempts: int, *, z: float = 1.959963984540054) -> float:
    """95% Wilson score lower bound for a failure rate. `z` defaults to the two-sided
    95% critical value. Ranking by this (not the raw rate) is what stops a test at 1/1
    from outranking one at 12/300."""
    if attempts <= 0:
        return 0.0
    p_hat = failures / attempts
    denom = 1 + z * z / attempts
    center = p_hat + z * z / (2 * attempts)
    spread = z * ((p_hat * (1 - p_hat) / attempts + z * z / (4 * attempts * attempts)) ** 0.5)
    return float(max(0.0, (center - spread) / denom))


# ---------------------------------------------------------------------------------
# Store encoding -- turns parsed Sessions + RunMeta into the committed JSONL shape.
# ---------------------------------------------------------------------------------

#: Tiers whose executed roster is stored in FULL (content-addressed). The quality
#: tier is single-attempt (no `--reruns` in `scripts/gate.py`'s pytest steps) and needs
#: hundreds of runs to estimate a rate at all -- it is a control arm, not a per-test
#: series, so only its failing/error/xpassed nodeids (always small) are stored inline.
_FULL_ROSTER_TIERS = frozenset({"ux", "pdf"})


def encode_run(
    meta: RunMeta, *, ingested: bool, skip_reason: str, log_lines: int, jobs_seen: Sequence[str]
) -> dict[str, Any]:
    """Build a `kind: "run"` record."""
    return {
        "schema": SCHEMA,
        "kind": "run",
        "run_id": meta.run_id,
        "run_attempt": meta.run_attempt,
        "run_number": meta.run_number,
        "workflow": meta.workflow,
        "event": meta.event,
        "head_branch": meta.head_branch,
        "head_sha": meta.head_sha,
        "created_at": meta.created_at,
        "status": meta.status,
        "conclusion": meta.conclusion,
        "url": meta.url,
        "ingested": ingested,
        "skip_reason": skip_reason,
        "log_lines": log_lines,
        "jobs_seen": list(jobs_seen),
        "parser_version": PARSER_VERSION,
    }


def encode_session(session: Session, meta: RunMeta) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build a `kind: "session"` record plus any new `kind: "roster"` records it needs.

    Returns `(session_record, roster_records)` -- the caller is responsible for only
    writing a roster record once per distinct digest across the whole store, but this
    function always returns one so a fresh store never has a dangling digest.
    """
    digest = roster_digest(session.executed)
    roster_records: list[dict[str, Any]] = []
    if session.tier in _FULL_ROSTER_TIERS:
        roster_records.append(
            {
                "schema": SCHEMA,
                "kind": "roster",
                "digest": digest,
                "size": len(session.executed),
                "nodeids": list(session.executed),
            }
        )
    summary = session.summary
    record = {
        "schema": SCHEMA,
        "kind": "session",
        "run_id": meta.run_id,
        "run_attempt": meta.run_attempt,
        "head_sha": meta.head_sha,
        "head_branch": meta.head_branch,
        "job": session.job,
        "session_index": session.session_index,
        "tier": session.tier,
        "tier_source": session.tier_source,
        "fmt": session.fmt,
        "complete": session.complete,
        "reconciled": session.reconciled,
        "summary_raw": summary.raw if summary else "",
        "duration_s": summary.duration_s if summary else None,
        "counts": {
            "passed": summary.passed if summary else 0,
            "failed": summary.failed if summary else 0,
            "error": summary.error if summary else 0,
            "skipped": summary.skipped if summary else 0,
            "deselected": summary.deselected if summary else 0,
            "xfailed": summary.xfailed if summary else 0,
            "xpassed": summary.xpassed if summary else 0,
            "rerun": summary.rerun if summary else 0,
            "warnings": summary.warnings if summary else 0,
            "other": summary.other if summary else 0,
        }
        if summary
        else None,
        "roster_digest": digest,
        "roster_size": len(session.executed),
        "skipped_nodeids": list(session.skipped),
        "failed_nodeids": list(session.failed_nodeids),
        "error_nodeids": list(session.error_nodeids),
        "xpassed_nodeids": list(session.xpassed_nodeids),
        "rerun_attempts": [list(item) for item in session.rerun_attempts],
        "alarm_declared": list(session.alarm_declared),
        "alarm_detail": [list(item) for item in session.alarm_detail],
        "warning_retry": [list(item) for item in session.warning_retry],
        "unparsed_lines": session.unparsed_lines,
        "swallowed_traceback_lines": session.swallowed_traceback_lines,
        "anomalies": list(session.anomalies),
        "parser_version": PARSER_VERSION,
    }
    return record, roster_records


# ---------------------------------------------------------------------------------
# I/O seam -- everything above this line is pure and unit-tested without a subprocess.
# `_gh` is deliberately duplicated from `scripts/ci_wait.py` rather than imported or
# shared: importing a private name across modules makes `ci_wait`'s internals an
# unstated public contract, and fan-in for a shared module would be 2 (far below
# `blast_radius.FAN_IN_THRESHOLD = 8`) -- not worth editing a module cited across
# multiple handoffs for a ~10-line function. `scripts/gate.py` already sets the
# precedent of inlining its own `subprocess.run` rather than sharing with `ci_wait`.
# Promote to a shared module WHEN A THIRD `gh`-consuming script appears, and register
# it in `scripts/enforcement/blast_radius.py` at that time -- a scheduled decision
# beats a silent default.
# ---------------------------------------------------------------------------------


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


def _fetch_run_list(workflow: str, limit: int) -> list[RunMeta]:
    args = [
        "run",
        "list",
        "--workflow",
        workflow,
        "--limit",
        str(limit),
        "--json",
        "databaseId,attempt,number,workflowName,event,headBranch,headSha,createdAt,status,conclusion,url",
    ]
    result = _gh(args)
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(
            f"`gh {' '.join(args)}` produced no JSON (exit {result.returncode}): "
            f"{result.stderr.strip() or '<no stderr>'}"
        )
    return parse_run_list(stdout)


def _fetch_run_log(run_id: str) -> tuple[str, str]:
    """Fetch one run's full log. Returns `(log_text, error)` -- `error` is non-empty on
    failure, `log_text` empty in that case. O-10: only the LATEST attempt is fetchable
    this way; a superseded red attempt's log is gone."""
    result = _gh(["run", "view", run_id, "--log"], timeout=120.0)
    if result.returncode != 0 or not result.stdout:
        return "", (result.stderr.strip() or f"exit {result.returncode}, empty log")
    return result.stdout, ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_store_records(store_dir: Path) -> Iterator[dict[str, Any]]:
    """Join every shard in the store, oldest file first (stable, not meaningful order
    beyond "deterministic"). Malformed lines are skipped with a printed warning rather
    than aborting the whole read -- one bad shard must not blind `report` to every
    other one."""
    if not store_dir.is_dir():
        return
    for path in sorted(store_dir.glob("*.jsonl")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"flake-rates: WARNING - {path}:{lineno} is not valid JSON ({exc}), skipped")


def _write_shard(path: Path, records: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" -- Windows `core.autocrlf=true` would otherwise commit CRLF into a
    # JSONL store (mirrors `scripts/work_items.py`'s BOARD.md write for the same reason).
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def _known_ingested_runs(store_dir: Path) -> set[tuple[str, int]]:
    """`(run_id, run_attempt)` pairs already ingested. A listed-but-not-ingested run is
    retried on every future `collect` regardless of its prior `skip_reason` -- simpler
    than classifying which failure reasons are permanent, and the extra cost of
    re-attempting a stale-cancelled run's log fetch is one cheap `gh` call."""
    known: set[tuple[str, int]] = set()
    for record in _iter_store_records(store_dir):
        if record.get("kind") == "run" and record.get("ingested"):
            known.add((str(record.get("run_id", "")), int(record.get("run_attempt", 1))))
    return known


def _collect(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    store_dir = repo_root / _STORE_DIR

    try:
        listed = _fetch_run_list(args.workflow, args.limit)
    except (RuntimeError, ValueError) as exc:
        print(f"flake-rates: could not list runs: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if not listed:
        print("flake-rates: `gh run list` returned zero runs - nothing to collect")
        return EXIT_NOTHING_TO_REPORT

    known = _known_ingested_runs(store_dir)
    to_fetch = [meta for meta in listed if (meta.run_id, meta.run_attempt) not in known]
    print(f"flake-rates: listed {len(listed)} run(s), {len(to_fetch)} new")

    records: list[dict[str, Any]] = []
    fetch_failures = 0
    unreconciled_sessions = 0
    for meta in to_fetch:
        if meta.status != "completed":
            records.append(
                encode_run(
                    meta,
                    ingested=False,
                    skip_reason=f"status={meta.status}",
                    log_lines=0,
                    jobs_seen=[],
                )
            )
            continue
        log_text, error = _fetch_run_log(meta.run_id)
        if error:
            fetch_failures += 1
            records.append(
                encode_run(
                    meta,
                    ingested=False,
                    skip_reason=f"log-unavailable: {error}",
                    log_lines=0,
                    jobs_seen=[],
                )
            )
            print(f"flake-rates: could not fetch log for run {meta.run_id}: {error}")
            continue
        sessions, top_unparsed = parse_run_log(log_text)
        jobs_seen = sorted({s.job for s in sessions})
        records.append(
            encode_run(
                meta,
                ingested=True,
                skip_reason="",
                log_lines=len(log_text.splitlines()),
                jobs_seen=jobs_seen,
            )
        )
        if top_unparsed > 0:
            print(
                f"flake-rates: NOTE - run {meta.run_id}: {top_unparsed} top-level line(s) unparsed"
            )
        seen_digests: set[str] = set()
        for session in sessions:
            if not session.reconciled:
                unreconciled_sessions += 1
            record, roster_records = encode_session(session, meta)
            records.append(record)
            for roster in roster_records:
                digest = roster["digest"]
                if digest not in seen_digests:
                    seen_digests.add(digest)
                    records.append(roster)

    if records:
        shard_path = repo_root / _STORE_DIR / f"{uuid.uuid4()}.jsonl"
        _write_shard(shard_path, records)
        print(f"flake-rates: wrote {len(records)} record(s) to {shard_path.relative_to(repo_root)}")

    if fetch_failures or unreconciled_sessions:
        print(
            f"flake-rates: PARTIAL - {fetch_failures} run(s) unfetchable, "
            f"{unreconciled_sessions} session(s) unreconciled"
        )
        return EXIT_PARTIAL
    return EXIT_OK


# ---------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class FlakeRate:
    nodeid: str
    tier: str
    attempts: int
    failures: int
    runs_seen: int
    runs_failed: int
    distinct_shas_failed: int
    first_seen: str
    last_seen: str
    present_in_latest_roster: bool


def _compute_rates(records: Sequence[dict[str, Any]]) -> list[FlakeRate]:
    """Aggregate `session` records into per-`(nodeid, tier)` rates.

    `attempts`/`failures` come from `rerun_attempts` (O-4/O-5's primary signal: exact,
    no clamp) reconciled against the roster -- a test that appears in `executed`
    (roster comes from a separate `roster` record, joined by digest) but not in
    `rerun_attempts` had exactly 1 attempt and 0 failures. A test in `failed_nodeids`/
    `error_nodeids` whose terminal attempt itself failed (full exhaustion, not merely
    absorbed) adds one more failure than `rerun_attempts` alone would show -- this is
    exactly the case `tests/ux/rerun_report.py`'s own conflation would under-count.
    """
    rosters: dict[str, tuple[str, ...]] = {}
    for record in records:
        if record.get("kind") == "roster":
            rosters[record["digest"]] = tuple(record.get("nodeids", ()))

    agg: dict[tuple[str, str], dict[str, Any]] = {}
    latest_roster_digest: dict[str, str] = {}
    latest_created_at: dict[str, str] = {}

    session_records = [r for r in records if r.get("kind") == "session" and r.get("reconciled")]
    for record in session_records:
        tier = str(record.get("tier", "unknown"))
        digest = str(record.get("roster_digest", ""))
        roster = rosters.get(digest)
        if roster is None:
            # Quality tier stores digest-only; its per-test series is not tracked here,
            # only its failing/error/xpassed nodeids (small, always available).
            roster = tuple(record.get("failed_nodeids", [])) + tuple(
                record.get("error_nodeids", [])
            )
        rerun_map = dict((n, c) for n, c in record.get("rerun_attempts", []))
        failed_set = set(record.get("failed_nodeids", [])) | set(record.get("error_nodeids", []))
        head_sha = str(record.get("head_sha", ""))
        created_at = str(record.get("created_at", record.get("run_id", "")))

        if head_sha and created_at >= latest_created_at.get(tier, ""):
            latest_created_at[tier] = created_at
            latest_roster_digest[tier] = digest

        for nodeid in roster:
            key = (nodeid, tier)
            bucket = agg.setdefault(
                key,
                {
                    "attempts": 0,
                    "failures": 0,
                    "runs_seen": 0,
                    "runs_failed": 0,
                    "shas_failed": set(),
                    "first_seen": created_at,
                    "last_seen": created_at,
                },
            )
            rerun_count = rerun_map.get(nodeid, 0)
            terminal_failed = nodeid in failed_set
            attempts = rerun_count + 1
            failures = rerun_count + (1 if terminal_failed else 0)
            bucket["attempts"] += attempts
            bucket["failures"] += failures
            bucket["runs_seen"] += 1
            if failures > 0:
                bucket["runs_failed"] += 1
                bucket["shas_failed"].add(head_sha)
            bucket["first_seen"] = min(bucket["first_seen"], created_at)
            bucket["last_seen"] = max(bucket["last_seen"], created_at)

    rates: list[FlakeRate] = []
    for (nodeid, tier), bucket in agg.items():
        present = nodeid in rosters.get(latest_roster_digest.get(tier, ""), ())
        rates.append(
            FlakeRate(
                nodeid=nodeid,
                tier=tier,
                attempts=bucket["attempts"],
                failures=bucket["failures"],
                runs_seen=bucket["runs_seen"],
                runs_failed=bucket["runs_failed"],
                distinct_shas_failed=len(bucket["shas_failed"]),
                first_seen=bucket["first_seen"],
                last_seen=bucket["last_seen"],
                present_in_latest_roster=present,
            )
        )
    return rates


def rank(
    rates: Sequence[FlakeRate], *, min_attempts: int
) -> tuple[list[FlakeRate], list[FlakeRate]]:
    """Split into `(ranked, insufficient_data)`, ranked by Wilson lower bound
    descending. Never drops a low-attempt test silently -- it goes to the second list."""
    enough = [r for r in rates if r.attempts >= min_attempts]
    thin = [r for r in rates if r.attempts < min_attempts]
    enough.sort(key=lambda r: wilson_lower_bound(r.failures, r.attempts), reverse=True)
    thin.sort(key=lambda r: (-r.failures, r.nodeid))
    return enough, thin


def _render_table(ranked: Sequence[FlakeRate], thin: Sequence[FlakeRate]) -> str:
    lines = [
        f"{'rate':>7}  {'wilson':>7}  {'fail/att':>10}  {'runs':>6}  {'shas':>5}  tier  nodeid",
    ]
    for row in ranked:
        rate = row.failures / row.attempts if row.attempts else 0.0
        wilson = wilson_lower_bound(row.failures, row.attempts)
        lines.append(
            f"{rate:>6.1%}  {wilson:>6.1%}  {row.failures:>4}/{row.attempts:<5}  "
            f"{row.runs_seen:>6}  {row.distinct_shas_failed:>5}  {row.tier:<16}  {row.nodeid}"
        )
    if thin:
        lines.append("")
        lines.append(f"-- insufficient data ({len(thin)} test(s), below --min-attempts) --")
        for row in thin:
            lines.append(f"{row.failures}/{row.attempts} attempts  {row.tier:<16}  {row.nodeid}")
    return "\n".join(lines)


def _report(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    store_dir = repo_root / _STORE_DIR
    records = list(_iter_store_records(store_dir))
    if not records:
        print("flake-rates: store is empty - run `collect` first")
        return EXIT_NOTHING_TO_REPORT

    session_records = [r for r in records if r.get("kind") == "session"]
    reconciled = [r for r in session_records if r.get("reconciled")]
    unreconciled = len(session_records) - len(reconciled)

    rates = _compute_rates(records)
    if args.tier:
        rates = [r for r in rates if r.tier == args.tier]
    if not rates:
        print("flake-rates: zero usable sessions to rank - refusing to report a rate")
        return EXIT_NOTHING_TO_REPORT

    ranked, thin = rank(rates, min_attempts=args.min_attempts)

    if args.json:
        payload = {
            "sessions_total": len(session_records),
            "sessions_reconciled": len(reconciled),
            "sessions_excluded": unreconciled,
            "ranked": [r.__dict__ for r in ranked],
            "insufficient_data": [r.__dict__ for r in thin],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"flake-rates: {len(reconciled)}/{len(session_records)} session(s) reconciled "
            f"({unreconciled} excluded)"
        )
        print(_render_table(ranked, thin))

    return EXIT_PARTIAL if unreconciled else EXIT_OK


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.flake_rates",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect_parser = sub.add_parser("collect", help="fetch new CI runs into the store")
    collect_parser.add_argument("--workflow", default="ci.yml", help="workflow file name")
    collect_parser.add_argument("--limit", type=int, default=30, help="max runs to list")

    report_parser = sub.add_parser("report", help="rank stored sessions by flake rate")
    report_parser.add_argument("--min-attempts", type=int, default=20)
    report_parser.add_argument("--tier", default=None, help="restrict to one tier")
    report_parser.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run `collect` or `report` and print a single, never-silent verdict line."""
    args = _parse_args(argv)
    code = EXIT_ERROR
    try:
        if args.command == "collect":
            code = _collect(args)
        elif args.command == "report":
            code = _report(args)
    except FileNotFoundError:
        print("flake-rates: `gh` not found on PATH - install the GitHub CLI", file=sys.stderr)
        code = EXIT_ERROR
    except KeyboardInterrupt:
        print("\nflake-rates: interrupted", file=sys.stderr)
        code = EXIT_ERROR
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"flake-rates: {type(exc).__name__}: {exc}", file=sys.stderr)
        code = EXIT_ERROR
    finally:
        print(f"flake-rates: {_VERDICT_LABELS.get(code, 'UNKNOWN')} (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
