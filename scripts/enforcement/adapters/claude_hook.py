#!/usr/bin/env python3
"""Claude Code PreToolUse adapter for the portable enforcement core.

Reads the standard hook-input JSON from stdin once, dispatches to the named
guard's `claude_check`, and translates its `GuardResult` into the PreToolUse
exit-code contract (0 = allow, 2 = block with a stderr message) —
byte-identical to the pre-migration standalone `.claude-plugin/hooks/*.sh`
scripts (see `tests/test_enforcement_core.py`).

Invoked by the thin wrapper left in place at each `.claude-plugin/hooks/
<guard-name>.sh` (so `.claude/settings.json` wiring stays valid):

    exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" <guard-name>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Make `scripts.enforcement.*` importable regardless of how this file is
# invoked (a direct script path, as the wrapper `.sh` files do — not `-m`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.guards import (  # noqa: E402
    block_merge_to_main,
    block_secrets,
    require_evidence_before_fix,
    require_feature_branch,
    route_security_lint,
    ruff_changed,
    validate_context,
)
from scripts.enforcement.guards.result import GuardResult  # noqa: E402

_GUARD_NAMES = (
    "require-feature-branch",
    "require-evidence-before-fix",
    "block-merge-to-main",
    "block-secrets",
    "route-security-lint",
    "ruff-changed",
    "validate-context",
)


def _load_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def dispatch(name: str, payload: dict[str, Any]) -> GuardResult:
    """Route `name` (one of `_GUARD_NAMES`) to its guard's `claude_check`."""
    if name == "require-feature-branch":
        return require_feature_branch.claude_check(payload)
    if name == "require-evidence-before-fix":
        return require_evidence_before_fix.claude_check(payload)
    if name == "block-merge-to-main":
        return block_merge_to_main.claude_check(payload)
    if name == "block-secrets":
        return block_secrets.claude_check(payload)
    if name == "route-security-lint":
        return route_security_lint.claude_check(payload)
    if name == "ruff-changed":
        return ruff_changed.claude_check(payload)
    if name == "validate-context":
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
        return validate_context.claude_check(payload, repo_root)
    raise SystemExit(f"claude_hook.py: unknown guard '{name}' (expected one of {_GUARD_NAMES})")


def main(argv: list[str]) -> int:
    """CLI entry point: `argv[1]` is the guard name, stdin is the PreToolUse payload."""
    if len(argv) != 2:
        print(f"usage: claude_hook.py <{'|'.join(_GUARD_NAMES)}>", file=sys.stderr)
        return 2
    payload = _load_payload()
    result = dispatch(argv[1], payload)
    if result.blocked:
        for line in result.messages:
            print(line, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
