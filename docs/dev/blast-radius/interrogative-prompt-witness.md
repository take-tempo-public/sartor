# Blast radius — interrogative-prompt-witness

> **Branch:** `feat/interrogative-prompt-witness`
> **Status:** enumeration complete (written before the first code edit)

---

## Surface

Work item 87 adds a guard to the Edit|Write guard registry and a new hook
event to the settings wiring. Neither surface is in
`scripts/enforcement/blast_radius.py`'s `GATED` table (so the
`require-consumer-enumeration` hook does not fire), but both are shared
contracts with exact-set pin tests, which is what charter C-10 is about —
this dossier is written on that rule, not on the hook.

1. **The guard registry** — `scripts/enforcement/adapters/claude_hook.py`
   (`_GUARD_NAMES`, `dispatch()`, guard imports) and
   `scripts/enforcement/adapters/claude_dispatcher.py` (`_GUARD_ORDER`):
   one new guard name, `interrogative-witness`, backed by a new module
   `scripts/enforcement/guards/interrogative_witness.py`.
2. **The hook wiring** — `.claude/settings.json` gains a `UserPromptSubmit`
   event entry running a new shim `hooks/interrogative-prompt-witness.sh`
   → `scripts/enforcement/adapters/prompt_witness_hook.py`.

---

## Enumeration

Ripgrep over the whole tracked tree (gitignore-respecting), every name the
surfaces go by:

```
rg -l "_GUARD_ORDER|_GUARD_NAMES|DISPATCHED_GUARD_NAMES"     → 10 files
  (3 adapters, 4 tests, 3 docs — full list in the table below)
rg -l "six Edit|six guards|exactly six"                       → 9 files
  (the guard-count prose: CLAUDE.md, both dispatcher files, the shim,
   item 0050, 2 historical handoffs, 1 wiki page, 1 design doc)
rg -l "UserPromptSubmit"                                      → 2 files
  (item 0087 + the incoming handoff — no existing wiring; new event)
rg -l "settings\.json"  (tests/)                              → 4 files
  (test_plan_approval_scoping.py:891, test_governance_hooks_gate.py,
   test_consumer_enumeration_gate.py:217, test_evidence_gate.py:211-222 —
   the last three are presence-only assertions on existing hooks; verified
   none pins an exact event-key set that a new UserPromptSubmit key breaks)
guards/*.py globbers: tests/test_enforcement_coverage.py
  (_guard_modules_on_disk) and tests/test_governance_hooks_gate.py
  (hooks/*.sh globber _hook_stems)
```

Negative results (findings): no `UserPromptSubmit` wiring exists anywhere
today; `scripts/enforcement/adapters/git_hook.py` imports guards only via
the package import at `git_hook.py:27` (no registry constant of its own to
update); no non-test consumer reads `_GUARD_ORDER` besides the two
dispatchers themselves.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/enforcement/adapters/claude_hook.py:62` `_GUARD_NAMES` + `dispatch()` + imports + docstring ("six") | update | the registry itself |
| 2 | `scripts/enforcement/adapters/claude_dispatcher.py:42` `_GUARD_ORDER` + docstrings ("six") | update | the Edit\|Write dispatch order |
| 3 | `hooks/edit-write-dispatcher.sh:2` comment ("six Edit/Write guards") | update | wiring comment names the count |
| 4 | `tests/test_enforcement_core.py:992` exact-set assertion on `_GUARD_ORDER` | update | exact-set pin fails on the new member |
| 5 | `tests/test_governance_hooks_gate.py` `BLOCKER_RULE_NAMES` (+ `len == 9` assert), `DISPATCHED_GUARD_NAMES`, hook classification union, wiring pins | update | the deliberate-amendment gate; the new shim is unclassified and the new guard is undeclared until edited here. The pause guard goes in `BLOCKER_RULE_NAMES` (count → 10): mechanically it reaches exit 2 (once per prompt, self-clearing), and this file's taxonomy is mechanical — calling it a never-exit-2 witness would be the exact "gate quietly becomes a nudge" dishonesty the file exists to block. A new event category is added for the UserPromptSubmit shim (always exit 0). |
| 6 | `tests/test_enforcement_coverage.py:41` `_BINDS_NON_CLAUDE_AGENTS` + `test_gap_membership_is_pinned_exactly` | update | new guard module must declare reach: `False` (Claude-only) and joins the pinned `EXTRACTION_GAP` |
| 7 | `docs/governance/enforcement.md` "Enforcement reach" section | update | `test_gap_is_documented_where_the_extraction_will_look` requires the gap member named there |
| 8 | `.claude/settings.json` hooks | update | new `UserPromptSubmit` entry |
| 9 | `CLAUDE.md:118-146` hook list + "six Edit\|Write guards" wiring note | update | the at-session-start hook mirror |
| 10 | `scripts/enforcement/adapters/bash_dispatcher.py` `_GUARD_ORDER` | no change | Bash matcher — the pause is Edit\|Write-only; a Bash command is not the momentum shape item 87 targets |
| 11 | `scripts/enforcement/adapters/git_hook.py:27` guard imports | no change | the witness is a Claude-session concept (a "triggering user prompt" has no git pre-commit equivalent); reach declared `False` in consumer 6 instead |
| 12 | `tests/test_consumer_enumeration_gate.py:217`, `tests/test_evidence_gate.py:211-229`, `tests/test_plan_approval_scoping.py:891` | no change | presence-only assertions on other hooks; verified unaffected by an added event key or guard |
| 13 | `docs/dev/work/items/0050-c7-c10-enforcement-is-claude-code-only.md:23` ("exactly six guards") | no change | historical statement about the git-hook path at its writing date; git_hook.py is untouched, so its six stays six — the item's point (Claude-only enforcement reach) is *extended* by this branch and is already tracked by the derived test in consumer 6 |
| 14 | `docs/dev/handoffs/feat-verify-dont-assume-guard.md`, `docs/dev/handoffs/feat-enforcement-first-governance.md`, `docs/dev/blast-radius/consumer-enumeration-gate.md`, `docs/dev/epic-a-chain-design-corrections.md`, `docs/wiki/pages/context-set-contract.md` | no change | historical artifacts (handoffs / dossiers / design docs are never rewritten — Epic D link policy); the wiki page's "six" is about context-set consumers, not this registry |

---

## Deferred

Nothing deferred. (Consumer 5's known, pre-existing `BLOCKER_RULE_NAMES`
undercount — `require-consumer-enumeration` was never added when C-10
landed, per that file's own 2026-08-06 docstring note — is deliberately NOT
fixed on this branch: it is a separate governance-count correction already
declared in `test_governance_hooks_gate.py`'s docstring, and folding it in
here would silently absorb a second governance change into an unrelated
count bump. The count goes 9 → 10 for this branch's own guard only.)

---

## Verification

Every "update" row above is behind a failing test before the edit:
`test_every_guard_on_disk_is_classified` (consumer 6),
`test_every_hook_is_classified` + `test_dispatcher_guard_list_matches_the_dispatched_names`
+ `test_blockers_reach_exit_2`'s count assert (consumer 5),
`test_guard_order_is_exactly_the_edit_write_guards` (consumer 4), and
`test_gap_is_documented_where_the_extraction_will_look` (consumer 7) — so a
missed site fails `python -m scripts.gate` loudly rather than landing
silently. The "no change" decisions for consumers 10–11 are pinned by
`test_bash_dispatcher_guard_list_matches_the_dispatched_names` and
`test_derived_routing_matches_the_declared_table` respectively: if a later
branch moves the guard into either path, those exact-set tests force a new
deliberate edit.
