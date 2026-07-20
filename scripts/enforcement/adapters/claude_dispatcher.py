#!/usr/bin/env python3
"""Claude Code PreToolUse dispatcher for the Edit|Write guard set (PX-37 hook-dispatcher).

Runs all five Edit|Write guards — require-feature-branch, require-evidence-
before-fix, block-secrets, validate-context, route-security-lint — in one
process against one stdin read, replacing the five separate settings.json
hook entries that each execed `claude_hook.py <name>` on their own.
`check-plan-approved.sh` is NOT one of these five (different mechanism, not a
scripts/enforcement/guards/ guard) and stays wired as its own top-level entry.

Claude Code runs a matcher's PreToolUse hooks in parallel and aggregates
every blocking hook's output — a user tripping two guards at once sees both
problems at once. Collapsing five entries into one process must preserve
that: every guard runs (no short-circuit — contrast git_hook.py's
`_pre_commit()`, which may short-circuit because git's pre-commit model only
ever needs the first failure), and every blocked guard's messages are
concatenated before exiting.

Guard decision logic is untouched: this module only orchestrates the same
`claude_hook.dispatch()` routing `claude_hook.py`'s own per-guard CLI already
uses, so that CLI (and the guard imports `git_hook.py`/`ci_backstop.py` rely
on) stays in place unmodified.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.adapters import claude_hook  # noqa: E402
from scripts.enforcement.guards.result import GuardResult  # noqa: E402

# The five Edit|Write guards this dispatcher replaces one settings.json entry
# each for. Order matches the pre-consolidation PreToolUse/Edit|Write array
# (check-plan-approved excluded — it stays its own separate top-level hook).
_GUARD_ORDER: tuple[str, ...] = (
    "require-feature-branch",
    "require-evidence-before-fix",
    "block-secrets",
    "validate-context",
    "route-security-lint",
)


def run_all(payload: dict[str, Any]) -> list[GuardResult]:
    """Run every guard in `_GUARD_ORDER` against `payload`; never short-circuits."""
    return [claude_hook.dispatch(name, payload) for name in _GUARD_ORDER]


def main(argv: list[str]) -> int:
    """CLI entry point: no arguments — always runs all five guards on stdin."""
    del argv
    payload = claude_hook.load_payload()
    blocked = [result for result in run_all(payload) if result.blocked]
    if not blocked:
        return 0
    for result in blocked:
        for line in result.messages:
            print(line, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
