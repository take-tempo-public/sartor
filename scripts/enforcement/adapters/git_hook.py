#!/usr/bin/env python3
"""Native git-hook adapter for the portable enforcement core.

Dispatches `pre-commit` / `pre-merge-commit` / `pre-push` to the same guard
implementations the Claude PreToolUse adapter uses. Activation is opt-in —
see `.githooks/README.md` for the one-time `git config core.hooksPath
.githooks` step; this repo does NOT auto-activate it.

Usage (invoked by the wrapper scripts in `.githooks/`):
    git_hook.py pre-commit
    git_hook.py pre-merge-commit
    git_hook.py pre-push <remote-name> <remote-url>   (stdin: pre-push ref lines)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `scripts.enforcement.*` importable regardless of how this file is
# invoked (a direct script path, as the wrapper hooks in `.githooks/` do).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement import gitutil  # noqa: E402
from scripts.enforcement.guards import (  # noqa: E402
    block_merge_to_main,
    block_secrets,
    require_feature_branch,
    route_security_lint,
    ruff_changed,
    validate_context,
)
from scripts.enforcement.guards.result import GuardResult  # noqa: E402

_EVENTS = ("pre-commit", "pre-merge-commit", "pre-push")


def _emit(result: GuardResult) -> int:
    """Print a blocked guard's messages to stderr; return the git-hook exit code."""
    if not result.blocked:
        return 0
    for line in result.messages:
        print(line, file=sys.stderr)
    return 1  # git hooks: any non-zero exit blocks the operation


def _pre_commit() -> int:
    checks = (
        require_feature_branch.git_precommit_check,
        block_secrets.git_precommit_check,
        route_security_lint.git_precommit_check,
        ruff_changed.git_precommit_check,
        lambda: validate_context.git_precommit_check(_REPO_ROOT),
    )
    for check in checks:
        code = _emit(check())
        if code:
            return code
    return 0


def _pre_merge_commit() -> int:
    branch = gitutil.git_branch(".")
    return _emit(block_merge_to_main.git_operation_check(branch))


def _pre_push() -> int:
    # git pre-push stdin: "<local ref> <local sha1> <remote ref> <remote sha1>" per line.
    for line in sys.stdin:
        parts = line.split()
        if len(parts) < 3:
            continue
        remote_ref = parts[2]
        code = _emit(block_merge_to_main.git_push_check(remote_ref))
        if code:
            return code
    return 0


def main(argv: list[str]) -> int:
    """CLI entry point: `argv[1]` is the git-hook event name."""
    if len(argv) < 2 or argv[1] not in _EVENTS:
        print(f"usage: git_hook.py <{'|'.join(_EVENTS)}> [args...]", file=sys.stderr)
        return 1
    event = argv[1]
    if event == "pre-commit":
        return _pre_commit()
    if event == "pre-merge-commit":
        return _pre_merge_commit()
    return _pre_push()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
