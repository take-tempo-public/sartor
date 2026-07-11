"""require-feature-branch guard.

Blocks code changes while HEAD is `main`/`master` — the deterministic
enforcement point for "create a feature branch before executing a plan".
Ported from `.claude-plugin/hooks/require-feature-branch.sh` (behavior
preserved byte-for-byte; see `tests/test_enforcement_core.py`).

Exemptions:
- the plans dir (`.claude/plans`) — plan files must stay writable
- not a git repo / detached HEAD — never wedge the caller on edge cases
- env `CLAUDE_ALLOW_MAIN_EDITS=1` — explicit opt-in (mirrors the
  `CLAUDE_CONFIRM_MERGE=1` escape hatch in `block_merge_to_main.py`)
"""

from __future__ import annotations

import os
import posixpath
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.gitutil import git_branch
from scripts.enforcement.guards.result import GuardResult

_MESSAGE_TEMPLATE = (
    "BLOCKED (require-feature-branch): on '{branch}'.",
    "Create a feature branch before code changes:",
    "  git checkout -b <type>/<short-desc>   (e.g. feat/foo, fix/bar)",
    "Escape hatch (intentional main edit): export CLAUDE_ALLOW_MAIN_EDITS=1",
)


def _resolve_existing_dir(norm_path: str) -> str:
    """Walk up from `norm_path`'s parent to the nearest existing directory.

    Mirrors the bash loop `DIR=$(dirname "$NORM_PATH"); while [ ! -d "$DIR" ]
    ...`: a `Write` may target a not-yet-created parent directory, so the
    branch check must climb to a directory that actually exists (the target
    file's directory is a fine proxy for "which worktree/clone is this?").
    """
    directory = posixpath.dirname(norm_path)
    while directory and directory not in ("/", ".") and not Path(directory).is_dir():
        directory = posixpath.dirname(directory)
    return directory or "."


def decide(file_path: str, env: Mapping[str, str]) -> GuardResult:
    """Pure decision: does writing to `file_path` require a feature branch?"""
    norm_path = (file_path or "").replace("\\", "/")
    if ".claude/plans" in norm_path:
        return GuardResult.allow()
    if env.get("CLAUDE_ALLOW_MAIN_EDITS") == "1":
        return GuardResult.allow()

    directory = _resolve_existing_dir(norm_path)
    branch = git_branch(directory)
    if not branch or branch == "HEAD":
        return GuardResult.allow()
    if branch in ("main", "master"):
        return GuardResult.block(*(line.format(branch=branch) for line in _MESSAGE_TEMPLATE))
    return GuardResult.allow()


def claude_check(payload: dict[str, Any], env: Mapping[str, str] | None = None) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.file_path`."""
    if env is None:
        env = os.environ
    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    return decide(file_path, env)


def git_precommit_check(env: Mapping[str, str] | None = None) -> GuardResult:
    """Native git pre-commit adapter.

    No target file to resolve a worktree from — the hook already runs with
    cwd at the committing worktree's root (git's own contract), so `"."` is
    unambiguous here (unlike the Claude adapter's cwd concern in
    `block_merge_to_main.py`, this path has no cross-process cwd handoff).
    """
    if env is None:
        env = os.environ
    if env.get("CLAUDE_ALLOW_MAIN_EDITS") == "1":
        return GuardResult.allow()
    branch = git_branch(".")
    if not branch or branch == "HEAD":
        return GuardResult.allow()
    if branch in ("main", "master"):
        return GuardResult.block(*(line.format(branch=branch) for line in _MESSAGE_TEMPLATE))
    return GuardResult.allow()
