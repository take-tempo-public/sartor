# Blast radius — enforcement-first-governance

> **Branch:** `feat/enforcement-first-governance`
> **Status:** enumeration complete — re-derived on this branch, before the first gated edit.

---

## Surface

One gated surface:

- **`docs/dev/AGENT_HANDOFF_TEMPLATE.md`** — **adding** a new required `##` section,
  `## Recurrences observed this session → guardrail authored` (M4). No existing section's
  text or heading changes. Because `scripts/verify_doc_template.py` requires every template
  `##` heading to be present *and in relative order*, adding a section makes it mandatory in
  every future handoff — that is the enforcement, and it is also the blast radius.

Not gated, changed on the same branch: `docs/governance/charter.md` (C-11, C-12),
`AGENTS.md`, `scripts/work_items.py`, `docs/dev/work/SCHEMA.md`,
`scripts/enforcement/evidence.py`, `scripts/enforcement/guards/require_evidence_before_fix.py`,
`scripts/enforcement/adapters/{claude_dispatcher,claude_context_hook}.py`, `CHANGELOG.md`.

---

## Enumeration

**Re-derived on this branch, not copied.** The previous session (`feat/ci-wait-wrapper`)
enumerated this same surface; C-10 rule 3 says a hand-maintained consumer list is stale
until re-derived, and it was — **the counts changed** (56 → 65 handoff files, and the
close-out text those files carry has since diverged into two generations).

```
rg -l "AGENT_HANDOFF_TEMPLATE" --glob '*.py'   -> 5 files
ls docs/dev/handoffs/*.md                      -> 65 files
rg -l "wait for the required checks with" docs/dev/handoffs/  -> 1 file
rg -l "Recurrences observed|guardrail authored"              -> 0 files
```

The last one is the load-bearing negative: **the section name is not currently used
anywhere**, so adding it cannot collide with existing prose or an existing heading.

| Set | Count | Note |
|---|---|---|
| `docs/dev/handoffs/*.md` | 65 | archived handoffs; **64** predate the current close-out text |
| Python referencing the template | 5 | enumerated individually below |

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md` | **update** | the surface — one new required section appended before `## Binding rules` |
| 2 | `scripts/verify_doc_template.py` (`match_headings`, `required_headings`) | **no change** | this is *the enforcement*. It already requires every `##` heading in relative order, so a new section is mandatory by construction with no code edit. Verified by reading `required_headings()` — it selects `level >= 2` with no allowlist |
| 3 | `tests/test_verify_doc_template.py::TestRealTemplate` | **update** | it pins the exact set of four `<!-- verbatim -->` **titles**. The new section is deliberately **not** marked verbatim (its content is per-session, not boilerplate), so that assertion stays valid — but a new test is added asserting the new heading is required |
| 4 | 65 × `docs/dev/handoffs/*.md` | **no change (deliberate)** | historical artifacts are never rewritten — see Deferred |
| 5 | `scripts/print_handoff_pointer.py` | **no change** | operates on path/branch/commit; never reads section structure |
| 6 | `scripts/wiki_relevance.py` | **no change to the file** — but it classifies both `AGENTS.md` and the template as **wiki-relevant**, so this branch owes the scoped close-out wiki check |
| 7 | `scripts/enforcement/blast_radius.py` | **no change** | the registry entry for this surface is already correct |
| 8 | `scripts/enforcement/guards/require_consumer_enumeration.py` | **no change** | it reads *this dossier*; it is the guard being satisfied, not a consumer of the template's structure |

### Non-gated surfaces this branch changes, enumerated anyway

| Site | Decision | Rationale |
|---|---|---|
| `scripts/work_items.py` allowed-key set | **update** | 4 new optional keys; unknown keys are a hard error today, so omitting this breaks every item using them |
| `docs/dev/work/SCHEMA.md` | **update** | the schema doc is the contract `work_items.py` implements; they must not drift |
| 48 × `docs/dev/work/items/*.md` | **no change** | M1's new rules are grandfathered — see Deferred |
| `scripts/enforcement/evidence.py` | **update** | shared by the PreToolUse guard *and* the SessionStart replay; both call sites re-verified before editing |
| `tests/test_evidence_gate.py` | **update** | gates C-7/C-8 today; extended to gate M2/M3 |

---

## Deferred

**1. The 65 archived handoffs are not retro-edited.** Same decision and same reason as the
previous branch's dossier: rewriting history would make 65 records say something their
authors did not write, and would invalidate every `generated` fingerprint on the ledger.
Consequence, recorded rather than discovered: re-running
`verify_doc_template.py --event consumed` against **any** handoff generated before this
commit now fails on the *missing section* as well as the close-out text. Safe here only
because the working posture is strictly serial (charter W-1) and no handoff is in flight —
this branch's own outgoing handoff is written against the updated template.

**2. M1's new closure rules are grandfathered for the 21 existing closed items.** Requiring
`verified_by` retroactively would force either fabricating artifacts for closures made
before the rule existed, or 21 edits asserting things nobody verified — both worse than the
problem. The allowlist is dated and finite, follows the maintained-list + audit-test shape of
`tests/test_egress_allowlist.py`, and an audit test fails if an id is added to it after the
cutoff. **New closures get no grandfathering.**

**3. M2 and M3 do not bind non-Claude agents.** They are Claude Code PreToolUse/SessionStart
hooks. Codex/Cursor/Aider read `AGENTS.md` raw and get the *prose* of C-11/C-12 with no
mechanism behind it. M1 rides `scripts/gate.py` + CI, so it binds every agent. This split is
recorded here rather than papered over, and it is the same gap the README's pending
tool-agnostic-enforcement decision already tracks.

---

## Verification

How a missed consumer surfaces:

1. `python scripts/verify_doc_template.py docs/dev/handoffs/<this-branch>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated` — close-out step 2. If the template
   gained a section this branch's own handoff lacks, this **fails loudly**. Consumer #1 and
   #2 are checked against each other by construction.
2. `python -m scripts.work_items check` — unknown-key and rule failures are hard errors; it
   runs in `scripts/gate.py` and CI, so consumer set #9/#10 cannot drift silently.
3. `python -m scripts.gate` — runs `tests/test_verify_doc_template.py` (consumer #3) and
   `tests/test_evidence_gate.py`.
4. **RED-then-GREEN for every new rule.** Per this repo's own standard, a gate not shown to
   reject a bad input is not evidence. Each of M1–M4 gets a deliberately non-compliant
   fixture that must be rejected *and* a compliant one that must pass — the teeth are the
   deliverable, not the clause text.
