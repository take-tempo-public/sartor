"""Shared git subprocess helpers for the enforcement core.

Every call is a fixed, trusted argv (`git` resolved from `PATH`, no shell) —
mirrors the existing `scripts/build_vector_index.py:_git` / `recall/sources/
git_grep_source.py` pattern.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path


def repo_root(start: str | Path, env: Mapping[str, str], default: str | Path = ".") -> Path:
    """The checkout that holds `start` (a file or directory, existing or not).

    Walks up from the nearest existing directory to the first one containing `.git` — a
    directory in a main checkout, a *file* in a `git worktree` — so a guard judging an edit
    reads the dossier of the worktree being edited, not the session's main checkout (item
    148). For a path in no repo at all: `CLAUDE_PROJECT_DIR` if set, else `default`. A caller
    whose `start` is a payload `cwd` passes that `cwd` as `default`, so a non-repo directory
    never resolves to the hook process's own cwd (the real repo, where a ledger write lands
    in a tracked shard).

    This is the one place a guard or context hook may read `CLAUDE_PROJECT_DIR` for a repo
    root; `tests/test_enforcement_core.py` fails if another one starts to. No subprocess: a
    stat per ancestor, run once per hook call.
    """
    path = Path(start).absolute()
    while not path.is_dir() and path.parent != path:
        path = path.parent
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path(env.get("CLAUDE_PROJECT_DIR") or default)


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
