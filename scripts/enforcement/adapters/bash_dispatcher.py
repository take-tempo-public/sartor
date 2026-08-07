#!/usr/bin/env python3
"""Claude Code PreToolUse dispatcher for the Bash guard set (`feat/verify-dont-
assume-guard`, mirroring PX-37's `claude_dispatcher.py` for Edit|Write).

Runs all four Bash-matcher guards — block-secrets, block-merge-to-main,
ruff-changed, verify-binary-on-path — in one process against one stdin read,
replacing the separate settings.json hook entries that each execed
`claude_hook.py <name>` on their own (`hooks/block-secrets.sh`,
`hooks/block-merge-to-main.sh`, `hooks/ruff-changed.sh` — all three deleted by
this fold; `verify-binary-on-path` never had a standalone file, it is new).

Same no-short-circuit contract as `claude_dispatcher.py`: every guard runs,
and every blocked guard's messages are concatenated before exiting — a
command tripping two guards at once (e.g. an embedded secret in a `git merge
main` command) surfaces both problems together, not just the first one this
dispatcher happened to check.

`block-secrets` is intentionally in BOTH this dispatcher's `_GUARD_ORDER` and
`claude_dispatcher.py`'s (Edit|Write) — the guard's own `decide()` inspects
`tool_input.command` (Bash) as well as `file_path`/`new_string`/`content`
(Edit/Write), so it needs to run on both matchers; it no longer needs its own
standalone `.sh` file to do so on either one.

Guard decision logic is untouched: this module only orchestrates the same
`claude_hook.dispatch()` routing `claude_hook.py`'s own per-guard CLI already
uses.
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

# The Bash guards this dispatcher replaces one settings.json entry each for.
# Order matches the pre-consolidation PreToolUse/Bash array (block-secrets,
# block-merge-to-main, ruff-changed), with the new verify-binary-on-path
# guard appended last.
_GUARD_ORDER: tuple[str, ...] = (
    "block-secrets",
    "block-merge-to-main",
    "ruff-changed",
    "verify-binary-on-path",
)


def run_all(payload: dict[str, Any]) -> list[GuardResult]:
    """Run every guard in `_GUARD_ORDER` against `payload`; never short-circuits."""
    return [claude_hook.dispatch(name, payload) for name in _GUARD_ORDER]


def main(argv: list[str]) -> int:
    """CLI entry point: no arguments — always runs every guard in `_GUARD_ORDER`."""
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
