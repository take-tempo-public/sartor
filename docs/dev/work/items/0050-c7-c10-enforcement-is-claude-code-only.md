```toml
schema = 1
id = 50
kind = "item"
status = "open"
decision_owner = "user"
title = "C-7 and C-10 are enforced by Claude Code hooks only - the clauses do not travel to other agents or an extracted governance package"
refs = [
  "docs/governance/enforcement.md",
  "tests/test_enforcement_coverage.py",
  "scripts/enforcement/adapters/git_hook.py",
]
summary = "C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents."
```

Found 2026-08-05 on `feat/enforcement-first-governance`, by reading the adapters rather than
by inference. **Owner-directed to be filed** so the planned governance extraction cannot
inherit it silently.

## Observed

`scripts/enforcement/adapters/git_hook.py` — the opt-in `.githooks/` adapter, the only
tool-agnostic path — imports and routes exactly six guards:

```
block_merge_to_main · block_secrets · require_feature_branch
route_security_lint · ruff_changed · validate_context
```

**`require_evidence_before_fix` and `require_consumer_enumeration` are not among them.**
Both are wired only through `adapters/claude_dispatcher.py` (Claude Code PreToolUse). The
same is true of C-8's `restore-evidence`/`capture-before-compact` and C-12's compaction
disclosure, which are SessionStart/PreCompact hooks with no non-Claude equivalent.

Derived, not asserted: `tests/test_enforcement_coverage.py::_guards_routed_by_git_hook`
introspects the adapter module at runtime.

## Why it matters

- **Today:** a Codex, Cursor or Aider session — or a human on the CLI — can edit production
  code on a `fix/*` branch with no diagnosis dossier, and can change a gated surface with no
  blast-radius enumeration. `AGENTS.md` states both rules in prose (those agents read it
  raw), but nothing blocks them.
- **At extraction:** a governance package whose clauses depend on one vendor's harness is not
  portable. Of the C-11/C-12 mechanisms added the same day, **only the closure bar
  (`scripts/work_items.py`, via `gate.py` + CI) binds every agent.**

## Guardrail already in place (charter C-11)

This item is **not** the mechanism — the mechanism landed with it:

- [`docs/governance/enforcement.md`](../../../governance/enforcement.md) §"Enforcement reach"
  is the canonical statement, written where an extraction would look.
- [`tests/test_enforcement_coverage.py`](../../../../tests/test_enforcement_coverage.py) makes
  it unmissable: it **derives** routing from `git_hook.py`, and fails if a guard is added
  without declaring its reach, if the declared table drifts from the adapter, or if
  `enforcement.md` stops naming the gapped guards. Proven RED-then-GREEN with a throwaway
  probe guard.

So the gap is now **pinned and self-checking**. What remains open is the decision below.

## The open decision (owner-gated, not an agent call)

Should C-7 and C-10 get a `git_hook.py` path?

**Not obvious, and deliberately not decided here.** Both guards key off the file being
edited and the current branch. A git `pre-commit` hook sees a *different slice* of that than
a PreToolUse hook: it sees the staged set after the fact, not the edit before it. A
pre-commit C-7 check would block the *commit* rather than the *edit* — weaker in ordering
(the fix is already written) but still a real gate, and arguably the right trade for
portability.

This overlaps the README's still-pending **tool-agnostic-enforcement decision**, which is
why `.claude/settings.json` wires the hooks directly rather than through the plugin manifest.
Resolve them together.

## Updates

### 2026-08-05 — filed during feat/enforcement-first-governance, owner-directed

Filed at the owner's explicit request: *"make sure that we document that so that when
governance is extracted that is flagged as a gap that won't be missed."* Documented in the
canonical enforcement home **and** pinned by a test, rather than recorded only here — a note
alone would be the exact non-compliance C-11 was adopted the same day to forbid.
