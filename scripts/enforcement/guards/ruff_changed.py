"""ruff-changed guard.

Staged Python must be ruff-clean AND ruff-formatted before a commit lands.
Ported from `.claude-plugin/hooks/ruff-changed.sh` (behavior preserved
byte-for-byte on the block/allow decision and the fix-it guidance; exact ruff
diagnostic text is naturally environment-dependent, so the equivalence tests
compare block-message *substance*, not a byte-exact ruff transcript — see
`tests/test_enforcement_core.py`).
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

from scripts.enforcement import gitutil
from scripts.enforcement.guards.result import GuardResult

_GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b")


def _run_ruff(mode: str, files: list[str]) -> tuple[bool, str]:
    """Run `python -m ruff <mode> [--check] --force-exclude <files>`; returns (ok, output).

    `--force-exclude` matters here specifically: ruff's default (`force-exclude = false`)
    ignores `[tool.ruff] exclude`/`extend-exclude` for explicitly-named file arguments — it
    only applies excludes during its OWN directory-recursion discovery. Passing individual
    staged paths (as this guard does) is exactly that explicit-argument case, so without
    this flag a staged edit to an excluded path (e.g. `db/migrations/versions/*.py`) would
    lint/format-check *inside* a tree the committed config deliberately excludes tree-wide —
    diverging from the plain `ruff check .` / `ruff format --check .` gate this guard's
    docstring says it mirrors. `--force-exclude` makes both paths agree.
    """
    args = [sys.executable, "-m", "ruff", mode]
    if mode == "format":
        args.append("--check")
    args.append("--force-exclude")
    args.extend(files)
    result = subprocess.run(  # noqa: S603 - fixed argv (interpreter + ruff + trusted staged paths)
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0, (result.stdout or "") + (result.stderr or "")


def check_files(files: list[str]) -> GuardResult:
    """Pure(ish) decision over an explicit staged-`.py`-file list."""
    if not files:
        return GuardResult.allow()

    ok, output = _run_ruff("check", files)
    if not ok:
        return GuardResult.block(
            output,
            "",
            "BLOCKED (ruff-changed): ruff reported issues on staged Python files.",
            "Fix them (or auto-fix many: python -m ruff check --fix), re-stage, then re-commit.",
        )

    ok, output = _run_ruff("format", files)
    if not ok:
        return GuardResult.block(
            output,
            "",
            "BLOCKED (ruff-changed): staged Python files are not ruff-formatted.",
            "Run: python -m ruff format <files>  (or: python -m ruff format .), re-stage, then re-commit.",
        )

    return GuardResult.allow()


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: only act on `git commit` Bash invocations."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    if not _GIT_COMMIT_RE.search(command):
        return GuardResult.allow()
    files = gitutil.staged_files(pathspec="*.py")
    return check_files(files)


def git_precommit_check() -> GuardResult:
    """Native git pre-commit adapter: always applies (the hook only fires when a
    commit is actually happening), so no `git commit` substring detection is
    needed at all — one of the cases where the git-native path is simpler than
    the Claude Bash-command-string path it replaces."""
    files = gitutil.staged_files(pathspec="*.py")
    return check_files(files)
