"""Pure rendering helpers for the `ux` tier's rerun-rate alarm.

`ci.yml`'s `ux` job runs `pytest -m ux --reruns 2 --reruns-delay 1` (retry a failed test up to
twice — 3 attempts total — before it counts as a real failure). `pytest-rerunfailures` reports a
fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the log** — the exact mechanism
that let a 64%-broken test read green for 11 CI runs (`docs/dev/RELEASE_CHECKLIST.md` carry-forward
ledger item 1). The owner decided (2026-07-20, `docs/scroll-flake-ci-data-rerun-policy`): keep
`--reruns 2`, add a rerun-rate alarm that *reports* every absorbed rerun rather than letting it
pass silently — and never fails the build over it (that would collapse back into the rejected
"drop reruns, let load flakes go red" option).

This module renders that report from plain data; `tests/ux/conftest.py` supplies the data (a
module-level tally populated by the existing `pytest_runtest_logreport` hook) and does the I/O
(the `$GITHUB_STEP_SUMMARY` file write, the stdout `::warning::` prints). Kept pure and
pytest-free so it's testable without a live pytest session or a browser — see
`tests/test_ux_rerun_report.py`.

Deliberately does **not** distinguish "reran then passed" from "reran and still failed all
`MAX_ATTEMPTS`": a full-red failure is already visible via the job's own exit status, so folding
it in here would just duplicate that signal. This report's only job is to surface the *absorbed*
retries a green run would otherwise hide.
"""

from __future__ import annotations

# 1 initial attempt + `--reruns 2` (ci.yml:228) = 3 total. Kept as a named constant so the
# table's "N of 3" column and the docstring above stay in sync with the CI flag by construction,
# not by two independently-maintained literals.
MAX_ATTEMPTS = 3


def render_step_summary(reruns: list[tuple[str, int]]) -> str:
    """Markdown for `$GITHUB_STEP_SUMMARY` — a table of every test that needed a retry.

    `reruns` is `(nodeid, failed_attempts)` pairs, `failed_attempts` being how many of the
    (at most `MAX_ATTEMPTS`) attempts failed before pytest stopped retrying. Returns `""` when
    `reruns` is empty — the caller skips the file write entirely on a clean run, so a green `ux`
    job leaves no trace in the summary.
    """
    if not reruns:
        return ""
    rows = "\n".join(f"| `{nodeid}` | {failed} of {MAX_ATTEMPTS} |" for nodeid, failed in reruns)
    plural = "test" if len(reruns) == 1 else "tests"
    return (
        f"# UX rerun report (this run)\n\n"
        f"⚠️ {len(reruns)} {plural} needed a retry (`--reruns 2` absorbed "
        f"{'it' if len(reruns) == 1 else 'them'}):\n\n"
        f"| test | attempts failed |\n"
        f"|------|------------------|\n"
        f"{rows}\n\n"
        f"(reported, not silently passed — `docs/dev/RELEASE_CHECKLIST.md` carry-forward "
        f"ledger item 1)\n"
    )


def render_annotations(reruns: list[tuple[str, int]]) -> list[str]:
    """One GitHub Actions `::warning::` workflow command per reran test.

    GitHub auto-parses `::warning::` lines printed to stdout into checks-UI annotations — this
    is what makes each rerun visible on the PR/run page without failing the step (a `::warning::`
    never changes exit status; only `::error::` combined with a genuine failing command does).
    The `title=` property is kept static (no dynamic content, so no colon/comma to escape) —
    the nodeid goes in the message instead, where GitHub's simpler *data* escaping
    (`%`/`\\r`/`\\n` only) applies cleanly; a pytest nodeid routinely contains `::`
    (`file.py::test_name`), which would need the stricter *property* escaping if it sat in
    `title=`. Returns `[]` for a clean run.

    ASCII-only message text, deliberately: `pytest_terminal_summary` prints these lines to the
    console via `_safe_print` (`tests/ux/conftest.py`) — a defensive fallback for arbitrary
    captured content that a console's active code page can't represent, reproduced directly on a
    Windows `cp1252` console during this feature's own end-to-end smoke test (a rerun's captured
    section happened to contain "β", crashing the whole session with an `INTERNALERROR` before
    `_safe_print` was added). Sticking to ASCII here means the common case never needs that
    fallback at all — belt AND suspenders, not either/or. `render_step_summary`'s markdown, by
    contrast, is only ever written to the `$GITHUB_STEP_SUMMARY` file with an explicit
    `encoding="utf-8"`, so it keeps the richer typography.
    """
    return [
        f"::warning title=UX rerun::{_escape_data(nodeid)} needed a retry "
        f"({failed} of {MAX_ATTEMPTS} attempts failed) - see the step summary"
        for nodeid, failed in reruns
    ]


def _escape_data(value: str) -> str:
    """Escape a workflow-command *data* field per GitHub's documented percent-encoding.

    https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
    — `%` must be escaped first so the later replacements' own `%` characters aren't re-escaped.
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
