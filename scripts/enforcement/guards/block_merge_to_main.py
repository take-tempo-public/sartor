"""block-merge-to-main guard.

Blocks `git merge`/`git push` targeting `main`/`master` unless the command (or
the caller's environment, for the git-native adapters) opts in with
`CLAUDE_CONFIRM_MERGE=1`. Ported from
`.claude-plugin/hooks/block-merge-to-main.sh` — and fixes the two defects
filed against it (`docs/dev/RELEASE_CHECKLIST.md`, "Portable-enforcement-core
migration" ledger row, Train-1 note, 2026-07-07):

(i) **merge-base/merge-tree false positive.** The original
    `\\bgit[[:space:]]+merge\\b` pattern's trailing `\\b` is satisfied at the
    `e`→`-` transition (both are non-word-adjacent), so a READ-ONLY
    `git merge-base main HEAD` (or `git merge-tree`) matched as if it were a
    real merge. Fixed with a negative lookahead: `merge` must NOT be
    immediately followed by `-` (a real `git merge` invocation is always
    followed by whitespace, an option, a ref, or end of string).

(ii) **cwd resolved in the hook's own process, not the caller's worktree.**
     The dominant "checkout main, then `git merge feature --no-ff`" direction
     resolved HEAD via a bare `git rev-parse --abbrev-ref HEAD`, which runs in
     the hook *process's* ambient cwd. Under W-1 (parallel worktree sessions)
     that cwd is not guaranteed to be the invoking agent's own worktree, so a
     session working in a feature-branch worktree could be judged against
     whatever branch the main checkout happens to sit on (or vice versa).
     Fixed by resolving against the invocation's own working directory, taken
     from the PreToolUse hook-input `cwd` field every hook receives alongside
     `tool_input` (see `plugin-dev:hook-development`) — never the hook
     process's own ambient cwd.

The git-native adapters (`git_operation_check` / `git_push_check`) don't need
either fix: git itself supplies the exact operation (a real merge/push, never
`merge-base`) and resolves HEAD in the invoking worktree by construction, so
there is no regex to tighten and no cwd to hand off.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

from scripts.enforcement.gitutil import git_branch
from scripts.enforcement.guards.result import GuardResult

_CONFIRM_TOKEN = "CLAUDE_CONFIRM_MERGE=1"  # noqa: S105 - not a credential; the literal escape-hatch token this guard's command-string parser matches

# Defect (i): `(?!-)` refuses to match when `merge` is immediately followed by
# `-` (merge-base / merge-tree / any future `git merge-*` plumbing subcommand).
_MERGE_MAIN_RE = re.compile(r"\bgit\s+merge(?!-)\b.*\b(?:main|master)\b")
_MERGE_RE = re.compile(r"\bgit\s+merge(?!-)\b")
_PUSH_MAIN_RE = re.compile(r"\bgit\s+push\b.*\borigin\s+(?:main|master)\b")

_MESSAGE_LINES = (
    "BLOCKED (block-merge-to-main): git merge/push targeting main or master.",
    "If you really intend this, prefix the command with: CLAUDE_CONFIRM_MERGE=1",
    "Example: CLAUDE_CONFIRM_MERGE=1 git merge feature-branch --no-ff -m '...'",
)


def targets_main(command: str, invocation_cwd: str) -> bool:
    """True if `command` is a merge/push that lands on `main`/`master`.

    `invocation_cwd` is consulted ONLY for the dominant "checkout main, then
    `git merge feature`" direction (defect ii) — it must be the invoking
    agent's own working directory (the PreToolUse `cwd` field), never the
    hook process's ambient cwd.
    """
    if _MERGE_MAIN_RE.search(command):
        return True
    if _PUSH_MAIN_RE.search(command):
        return True
    if _MERGE_RE.search(command):
        branch = git_branch(invocation_cwd or ".")
        if branch in ("main", "master"):
            return True
    return False


def decide(command: str, invocation_cwd: str) -> GuardResult:
    """Pure decision for the Claude Bash-command-string path."""
    if not targets_main(command, invocation_cwd):
        return GuardResult.allow()
    if _CONFIRM_TOKEN in command:
        return GuardResult.allow()
    return GuardResult.block(*_MESSAGE_LINES)


def claude_check(payload: dict) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.command` + top-level `cwd`."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    invocation_cwd = payload.get("cwd", "") or ""
    return decide(command, invocation_cwd)


def git_operation_check(current_branch: str, env: Mapping[str, str] | None = None) -> GuardResult:
    """Native git `pre-merge-commit` adapter.

    Git already knows this IS a real merge (plumbing commands like
    `merge-base`/`merge-tree` never invoke this hook) and already resolves
    HEAD correctly in the invoking worktree — no regex, no cwd handoff.
    """
    if env is None:
        env = os.environ
    if current_branch not in ("main", "master"):
        return GuardResult.allow()
    if env.get("CLAUDE_CONFIRM_MERGE") == "1":
        return GuardResult.allow()
    return GuardResult.block(*_MESSAGE_LINES)


def git_push_check(remote_ref: str, env: Mapping[str, str] | None = None) -> GuardResult:
    """Native git `pre-push` adapter.

    Git supplies the exact remote ref being updated (e.g. `refs/heads/main`)
    on stdin — no shell-string regex parsing needed at all.
    """
    if env is None:
        env = os.environ
    branch = remote_ref.removeprefix("refs/heads/")
    if branch not in ("main", "master"):
        return GuardResult.allow()
    if env.get("CLAUDE_CONFIRM_MERGE") == "1":
        return GuardResult.allow()
    return GuardResult.block(*_MESSAGE_LINES)
