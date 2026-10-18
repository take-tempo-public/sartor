```toml
schema = 1
id = 7
kind = "item"
title = "PX-46 selective memory consolidation"
status = "deferred"
decision_owner = "user"
blocked_on = "owner sign-off on the keep/consolidate/delete list required first - judged irreversible if botched"
refs = ["RELEASE_ARC.md step 13", "docs/dev/reviews/2026-07-efficiency/prescriptions.md:53"]
summary = "Selective, not wholesale, memory consolidation - present the list, act only after explicit approval."
```

Prescription: fold the ≥3 unique-recipe memories into a durable `docs/dev/`
reference, delete only genuinely redundant completion logs, shrink the freed
`MEMORY.md` index lines. Never actioned — owner sign-off on the specific
keep/consolidate/delete list was never sought. Memory file count grows
session to session; re-verify the count fresh before acting.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, not new)

### 2026-10-02 — draft keep/consolidate/delete list presented; awaiting owner sign-off (`chore/release-v1.1.0`)

**Status: not approved, nothing applied.** The owner asked to see the list.

**Provenance.** A read-only Explore subagent drafted the list. The orchestrator spot-checked
7 of its claims:
- **Held:** the file count, `CHANGELOG.md:6229`, `archive/kit-adoption-design.md:223`, four
  cited evidence paths, and `AGENTS.md:44`.
- **Wrong:** one claim. It said the `warn_unreachable` gotcha has no repo home, but
  `archive/kit-adoption-design.md` mentions `warn_unreachable` 22 times.

Treat every "not in the repo" claim below as a hypothesis. **Applying this list starts with
re-grepping every DELETE row.**

**Counts.** 244 memory files plus `MEMORY.md`. That is up from about 153 on 2026-07-21.

| Class | Count |
|---|---|
| KEEP | 206 (18 of them lack a `MEMORY.md` index line) |
| FOLD-TO-DOCS | 15 |
| MERGE-INTO | 5 |
| DELETE-CANDIDATE | 18 |

**FOLD-TO-DOCS** → a new `docs/dev/` reference. No live dev doc holds these today.
- *Seam-move recipe (8):*
  - reference-app-blueprints-seam-move-mechanics
  - reference-app-factory-infra-built
  - reference-app-blueprints-{generation,corpus,templates,applications,users,diagnostics}-seam-built
- *Lint/typing verify recipes (7):*
  - reference-kit-phase2-mypy-strict-leaves-built
  - reference-kit-phase2-ruff-d-built
  - reference-kit-phase2-ruff-ann-built
  - reference-kit-phase2-interrogate-built
  - reference-kit-phase1-sim-ruf-triage-built
  - reference-kit-phase1-ruff-format-built
  - reference-ruff-version-pin-ci-format-gate

**MERGE-INTO** (merged file → survivor). The survivor takes in the merged file's unique text.
- feedback_git_merge_confirm → feedback_branch_discipline
- reference-style-css-duplicate-cascade-rules → reference-css-cascade-per-property-not-per-rule
- project-route-security-lint-scope → reference-route-security-lint-widen-8-2
- project-plan-approval-hook-scope → project-plan-approved-marker (keep its chicken-and-egg lesson)
- reference-recover-interrupted-session-from-transcript → reference-recover-past-session-transcripts

**DELETE-CANDIDATE.** Each one cites the repo home of its facts; the subagent's report holds the
line numbers.
- excellence-walk-llm-wiki
- reference-kit-phase1-pydantic-mypy-built
- reference-app-blueprints-design
- project-:
  - 2026-07-unusable-remediation
  - 2026-07-ux-review
  - bigpush-opus-handoff
  - config-drift-batch-px47
  - context-write-lost-update-gap
  - diagnostics-run-cancel-landed
  - handoff-pointer-verification
  - hook-dispatcher-px37
  - scrub-local-eval-paths-parked
  - v108-walkthrough-epic
  - v108-window-8.5-to-8.6
  - v110-close-out-sequence
  - v110-compose-frozen-composition
  - v110-css-cascade-collapse
  - large-corpus-scalability

**Ordering constraint.** Fold before you delete. Otherwise `[[links]]` from the seam and kit
memories to excellence-walk-llm-wiki dangle.

**Also surfaced:**
- About 15 `[[links]]` inside memory bodies point at files that don't exist.
- ux-scroll-flake-chip0 (33 KB) should be trimmed, not deleted.
- Two KEEP memories still carry open owed items:
  - the 10P backbone pointer (`AGENTS.md:44`);
  - a handoff-template note about markdown links inside verbatim sections.

### 2026-10-02 — APPROVED by the owner (`chore/release-v1.1.0`)

The owner approved the list above as it stands. It is applied on its own branch: the memory
edits plus the new `docs/dev/` reference for the 15 fold-ins. It is not applied on this branch.

**Step one of that branch:** re-grep every DELETE row's evidence, because a spot-check found one
"not in the repo" claim was wrong. Then fold, merge, delete, and shrink the index, in that
order. Status stays `deferred` until that branch starts; the `blocked_on` sign-off is now given.

### 2026-10-17 - owner directed it in chat; deliberately not started on `fix/model-pricing-rates`

**Status: still not approved for any deletion; nothing applied.** While closing item 174 the owner said: "capture whatever is in
memory that is still useful into durable locations before doing the compaction and do so so that you can compact the memory
more significantly". Asked where and how far, the owner chose **the next session** (not on the pricing branch: one branch per
session, and the capture is a different item) and **"fold the index, delete only approved rows"**.

- **What the owner chose:** (1) move durable recipes into repo docs first; (2) compact `MEMORY.md` hard, one line per theme,
  leaving details in their files; (3) delete a memory **file** only for a row of the draft list that the owner approves after
  every DELETE row is re-grepped (the 2026-10-02 draft already had one wrong "not in the repo" claim).
- **Measured 2026-10-17, this machine:** 266 files in the memory directory (47 `feedback`, 43 `project`, 174 `reference`, plus
  `MEMORY.md` and one other), 1.66 MB total, `MEMORY.md` 20,458 bytes. The hook that flagged it reported a 24.4 KB read limit
  and a 17.1 KB target; **those two figures are the hook's message, not something I checked.** The count was 244 on 2026-10-02.
- **Why the next session starts here, not from scratch:** the 2026-10-02 draft list above is the starting point, not a
  decision. Re-derive the counts fresh, re-grep every DELETE row, then show the owner the rows before any file is deleted.
  The index compaction and the capture into docs are additive and reversible; a file deletion is not.
