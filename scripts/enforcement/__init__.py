"""Portable enforcement core (`feat/portable-enforcement-core`, 2026-07-08).

One guard implementation per rule, three consumers:

- `adapters/claude_hook.py` — the Claude Code PreToolUse JSON-stdin contract.
  Since PX-37 (`chore/hook-dispatcher`), five of the seven guards it can
  dispatch run via `adapters/claude_dispatcher.py`'s single `hooks/
  edit-write-dispatcher.sh` entry rather than each having its own wrapper;
  `block-merge-to-main` and `ruff-changed` (Bash-matcher only) still have
  their own `hooks/*.sh` wrapper naming this module directly.
- `adapters/git_hook.py` — native git hooks (`.githooks/`, opt-in via
  `git config core.hooksPath .githooks` — see `.githooks/README.md`).
- `ci_backstop.py` — a repo-wide secrets scan wired into `.github/workflows/ci.yml`,
  authored now and inert until the git remote activates (Sprint 8.7).

See `docs/governance/enforcement.md` for the gate/witness/tribal split this
package implements the "gate" side of, and `RELEASE_CHECKLIST.md`'s
"Portable-enforcement-core migration" ledger row for the decision record.

Plan-mode lifecycle hooks (`check-plan-approved`, `mark-plan-approved`,
`cleanup-plan-on-merge`) are Claude-only by design and are NOT part of this
package — they stay standalone scripts, re-homed to root `hooks/` alongside
the rest (kit-adoption commitment 3).
"""

from __future__ import annotations
