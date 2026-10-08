#!/usr/bin/env python3
"""Claude Code PreToolUse adapter for the portable enforcement core.

Reads the standard hook-input JSON from stdin once, dispatches to the named
guard's `claude_check`, and translates its `GuardResult` into the PreToolUse
exit-code contract (0 = allow, 2 = block with a stderr message) —
byte-identical to the pre-migration standalone `.claude-plugin/hooks/*.sh`
scripts (see `tests/test_enforcement_core.py`).

Every hook is launched by ``scripts/enforcement/adapters/hook.py`` (item 152: no shell
wrapper in between). The Edit|Write rules run through ``claude_dispatcher.py``'s
``edit-write-dispatcher`` hook: ``check-plan-approved`` (``scripts/enforcement/plan_gate.py``,
since ``fix/python-direct-hooks-plan-gate``) plus the seven guards (PX-37 and item 87). The
Bash rules run through ``bash_dispatcher.py``'s ``bash-dispatcher`` hook. Both route through
``dispatch()``. ``block-secrets`` is dispatched by BOTH: its ``decide()`` inspects the Bash
``command`` field and the Edit/Write ``file_path``/``new_string``/``content`` fields.
This module's per-guard CLI (``main()``, below) has no hook of its own. It stays in place for
direct use and tests.

Guard modules are imported on first dispatch, not at load. A hook process pays only for the
guards its matcher runs: importing every guard measured a median of 2974 ms against 1635 ms
for a bare ``python3`` start-up under memory pressure, and a slow PreToolUse hook gets
cancelled by the harness, which leaves it open
(``docs/dev/diagnosis/python-direct-hooks-plan-gate.md``).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# Make `scripts.enforcement.*` importable regardless of how this file is
# invoked (a direct script path, as `hook.py` and the tests do — not `-m`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.guards.result import GuardResult  # noqa: E402

#: Guard name -> the module whose ``claude_check(payload)`` decides it.
_GUARD_MODULES: dict[str, str] = {
    "check-plan-approved": "scripts.enforcement.plan_gate",
    "require-feature-branch": "scripts.enforcement.guards.require_feature_branch",
    "require-evidence-before-fix": "scripts.enforcement.guards.require_evidence_before_fix",
    "require-consumer-enumeration": "scripts.enforcement.guards.require_consumer_enumeration",
    "block-merge-to-main": "scripts.enforcement.guards.block_merge_to_main",
    "block-secrets": "scripts.enforcement.guards.block_secrets",
    "route-security-lint": "scripts.enforcement.guards.route_security_lint",
    "ruff-changed": "scripts.enforcement.guards.ruff_changed",
    "validate-context": "scripts.enforcement.guards.validate_context",
    "verify-binary-on-path": "scripts.enforcement.guards.verify_binary_on_path",
    "interrogative-witness": "scripts.enforcement.guards.interrogative_witness",
    "block-subagent-git-stash": "scripts.enforcement.guards.block_subagent_git_stash",
    "block-doubled-backslash": "scripts.enforcement.guards.block_doubled_backslash",
    "block-long-bash-command": "scripts.enforcement.guards.block_long_bash_command",
}
_GUARD_NAMES = tuple(_GUARD_MODULES)


def load_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def dispatch(name: str, payload: dict[str, Any]) -> GuardResult:
    """Route `name` (one of `_GUARD_NAMES`) to its guard's `claude_check`."""
    module_name = _GUARD_MODULES.get(name)
    if module_name is None:
        raise SystemExit(f"claude_hook.py: unknown guard '{name}' (expected one of {_GUARD_NAMES})")
    module = importlib.import_module(module_name)
    if name == "validate-context":
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
        result: GuardResult = module.claude_check(payload, repo_root)
        return result
    result = module.claude_check(payload)
    return result


def main(argv: list[str]) -> int:
    """CLI entry point: `argv[1]` is the guard name, stdin is the PreToolUse payload."""
    if len(argv) != 2:
        print(f"usage: claude_hook.py <{'|'.join(_GUARD_NAMES)}>", file=sys.stderr)
        return 2
    payload = load_payload()
    result = dispatch(argv[1], payload)
    if result.blocked:
        for line in result.messages:
            print(line, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
