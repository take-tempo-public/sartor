"""Shared git subprocess helpers for the enforcement core.

Every call is a fixed, trusted argv (`git` resolved from `PATH`, no shell) —
mirrors the existing `scripts/build_vector_index.py:_git` / `recall/sources/
git_grep_source.py` pattern.
"""

from __future__ import annotations

import subprocess


def _run(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
        ["git", *args],  # noqa: S607 - `git` intentionally resolved from PATH
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def git_branch(cwd: str) -> str:
    """Abbreviated current branch at `cwd`.

    Returns "" on any failure (not a git repo, detached HEAD, `git` missing) —
    callers treat an empty/`"HEAD"` result as "don't know, allow" rather than
    wedging the caller on an edge case.
    """
    try:
        result = _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd or None)
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def staged_files(diff_filter: str = "ACM", pathspec: str | None = None) -> list[str]:
    """Staged (index) file paths, repo-root-relative.

    `diff_filter="ACM"` (Added/Copied/Modified) excludes deletions by default,
    matching the original `ruff-changed.sh` / `block-secrets.sh` intent — a
    deleted file has no staged content left to lint or scan.
    """
    args = ["diff", "--cached", "--name-only", f"--diff-filter={diff_filter}"]
    if pathspec:
        args += ["--", pathspec]
    result = _run(args)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def staged_content(path: str) -> str:
    """The staged (index) content of `path`; "" if unreadable."""
    result = _run(["show", f":{path}"])
    if result.returncode != 0:
        return ""
    return result.stdout
