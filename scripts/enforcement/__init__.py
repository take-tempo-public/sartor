"""Portable enforcement core (`feat/portable-enforcement-core`, 2026-07-08).

One guard implementation per rule, three consumers:

- `adapters/claude_hook.py` — the Claude Code PreToolUse JSON-stdin contract.
  Every guard it dispatches runs inside one of two dispatcher processes
  (`adapters/claude_dispatcher.py` for Edit|Write, `adapters/bash_dispatcher.py`
  for Bash), each launched by `adapters/hook.py`, the one entry point every
  `.claude/settings.json` hook names (item 152: no shell wrappers).
- `adapters/git_hook.py` — native git hooks (`.githooks/`, opt-in via
  `git config core.hooksPath .githooks` — see `.githooks/README.md`).
- `ci_backstop.py` — a repo-wide secrets scan wired into `.github/workflows/ci.yml`,
  authored now and inert until the git remote activates (Sprint 8.7).

See `docs/governance/enforcement.md` for the gate/witness/tribal split this
package implements the "gate" side of, and `RELEASE_CHECKLIST.md`'s
"Portable-enforcement-core migration" ledger row for the decision record.

The plan gate (`plan_gate.py`: `check-plan-approved`, `mark-plan-approved`,
`plan-write-landed`) lives in this package but is Claude-only by design: plan
mode has no git-hook or CI equivalent, so `git_hook.py` and `ci_backstop.py`
never call it.
"""

from __future__ import annotations
