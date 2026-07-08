"""Per-guard decision logic for the portable enforcement core.

Each module exposes a pure `decide(...)` function (no I/O beyond the git
subprocess calls a guard genuinely needs, e.g. resolving the current branch)
plus one or more thin adapters:

- `claude_check(payload, ...)` — extracts the fields the Claude PreToolUse
  JSON contract carries and calls `decide`.
- `git_precommit_check(...)` / `git_operation_check(...)` / `git_push_check(...)`
  — extracts the fields a native git hook invocation carries.

Keeping `decide` adapter-free is what makes the equivalence tests in
`tests/test_enforcement_core.py` possible: they exercise the pure function
directly, and separately exercise each adapter's field-extraction.
"""

from __future__ import annotations
