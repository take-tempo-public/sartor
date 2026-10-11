```toml
schema = 1
id = 132
kind = "item"
title = "\"Submit answers and regenerate\" may not change the résumé once Compose is saved"
status = "closed"
decision_owner = "agent"
branches = ["feat/user-docs", "fix/frozen-composition-staleness"]
refs = [
  "static/app.js:2983-3161",
  "blueprints/generation.py:837-877",
  "hardening.py:1827-1861",
  "blueprints/analysis.py:678-688",
]
summary = "Follow-up answers save, but regenerate re-assembles the frozen composition with no AI call. UNVERIFIED."
resolution = "2026-10-10, fix/frozen-composition-staleness: confirmed (byte-identical regenerate, zero LLM calls). On an approved composition the follow-up submit now saves the answers and opens Compose (Save answers and revise in Compose); a not-yet-approved context keeps the legacy regenerate, whose prompt reads the answers. UX half verified in CI (not locally: memory)."
verified_by = [
  "tests/test_frozen_composition_staleness.py::TestDesignKeptFacts::test_o1_answers_then_regenerate_returns_the_identical_resume",
  "tests/test_frozen_composition_staleness.py::TestDefects::test_d6_typed_edits_and_preview_agree_after_a_regenerate",
  "tests/ux/regression/test_20261010_compose_edit_after_freeze.py::test_frozen_followup_answers_go_to_compose_not_regenerate",
]
```

**Status of the evidence: code-read only, NOT observed.** This comes from an exploration
subagent's read, and this session has not independently traced it (charter C-12: a
subagent's unverified report is flagged as such).

**The hypothesis.**
- **The flow.** Step 6 → **Get follow-up questions** → **Submit answers and regenerate** merges
  the answers and calls `runGeneration()` (`static/app.js:3113-3154`).
- **The regenerate.** When the application has an `approved_composition`, `/api/generate`
  assembles the résumé from it deterministically (`blueprints/generation.py:837-877`,
  `hardening.py:1827-1861`).
- **Nothing resets it.** `/api/answer-clarifications` does not appear to clear that composition.
- **Where the answers go.** They reach Candidate memory (`blueprints/analysis.py:678-688`) and
  the context file, but not the regenerated body.

**Next step:** reproduce it in demo mode or with a stubbed UX run, and diff the résumé before
and after. User docs on `feat/user-docs` describe the button by its label only and make no
claim about the result.

## Updates

### 2026-09-29 — filed on `feat/user-docs` (Epic D D3)

### 2026-10-10 — reproduced and fixed on `fix/frozen-composition-staleness`

Reproduced at `76f7a44` (docs/dev/diagnosis/frozen-composition-staleness.md O4): the answers were saved to the context and Candidate
memory, and the following `/api/generate` and `/api/generate/stream` (the button calls the
stream route) returned a byte-identical résumé with no LLM call. Owner decision (2026-10-10): on
an approved composition the button becomes "Save answers and revise in Compose": it saves the
answers and opens Compose with a banner pointing at the drafting controls that read them. No new
AI path. The typed-edits drop on the same path is fixed too (O5, owner decision 4).
