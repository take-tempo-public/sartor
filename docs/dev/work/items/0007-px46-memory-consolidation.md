```toml
schema = 1
id = 7
kind = "item"
title = "PX-46 selective memory consolidation"
status = "open"
decision_owner = "user"
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

### 2026-10-18 - started on `chore/memory-consolidation`; draft list re-grepped (evidence, nothing applied)

**Status: now `open` (the sign-off the `blocked_on` waited on was given 2026-10-02; the owner directed the work 2026-10-17).
No memory file has been deleted; no row is approved for deletion in this session yet.**

**Owner choices this session (chat, 2026-10-18):** scope = **the draft list plus a full sweep** of the other memory files;
home for the folded recipes = **a new `docs/dev/` how-to**. Plan: `~/.claude/plans/handoff-docs-dev-handoffs-model-55-eval-partitioned-wilkes.md`.

**Measured 2026-10-18 (`ls`, `du -cb`, `wc -c` over the memory directory):** 266 entries = 265 memory files (47 `feedback`, 43
`project`, 174 `reference`, `excellence-walk-llm-wiki`) + `MEMORY.md`. The `.md` files total 1,034,153 bytes; `du -sh`
reports 1.7M (on-disk), which is the "1.66 MB" above. `MEMORY.md` is 20,458 bytes. 50 files have no `MEMORY.md` line.
21 files are new since 2026-10-02 (265 minus 244). `[[links]]` whose target is missing: 12 point at no file, 2 use a wrong
name, 16 omit the prefix. Largest files: `project-ux-scroll-flake-chip0` 34,859 B, `feedback-schedulewakeup-not-for-background-bash` 29,057 B.

**Re-grep of the 2026-10-02 DELETE rows, against `main` at `de47905` (read-only Explore pass; the orchestrator has NOT yet
spot-checked these cites, so each is a hypothesis until the sweep's spot-check step).** All 38 named files exist.
- **Tally.** The pass's own header said "15 SAFE-DELETE, 3 PARTIAL", but its 18 per-row labels give **16 SAFE-DELETE and 2
  PARTIAL**; the per-row labels are what is recorded here (the header was a miscount, found by the orchestrator when listing
  the rows).
- **SAFE-DELETE (every fact has a repo home), 16:** `reference-kit-phase1-pydantic-mypy-built`,
  `reference-app-blueprints-design`, `project-2026-07-unusable-remediation`, `project-2026-07-ux-review`,
  `project-bigpush-opus-handoff`, `project-config-drift-batch-px47`, `project-context-write-lost-update-gap`,
  `project-diagnostics-run-cancel-landed`, `project-handoff-pointer-verification`, `project-hook-dispatcher-px37`,
  `project-scrub-local-eval-paths-parked`, `project-v108-walkthrough-epic`, `project-v108-window-8.5-to-8.6`,
  `project-v110-compose-frozen-composition`, `project-v110-css-cascade-collapse`, `project-large-corpus-scalability`.
  `project-hook-dispatcher-px37` is labelled SAFE although two of its facts have no repo home; both are already in kept
  memories (`reference-hook-manual-testing`, `feedback-consume-handoff-dont-reconstruct`), so the label holds only while
  those stay.
- **PARTIAL (a fact with no repo home), 2:** `excellence-walk-llm-wiki` (the wiki clean-lint commit-order recipe: non-wiki
  commits first, advance `.last_ingest_sha` to the non-wiki tip, one wiki-only commit; only trace is one run at
  `docs/wiki/log.md:413-419`; possibly obsolete under the PR-side freshness check, `block_merge_to_main.py:55-70`, unverified)
  and `project-v110-close-out-sequence` (the `docs/RELEASE_ARC.md` vs `docs/dev/RELEASE_ARC.md` path trap; the general
  lesson is in kept `feedback-verify-existence-before-asserting-absence`).
- **Tensions to resolve before any delete:** `MEMORY.md:88` indexes `reference-app-blueprints-design` as a live line;
  `MEMORY.md:159` folds `project-large-corpus-scalability` in as a "RESOLVED" sibling. Repo records cite memory slugs a
  deletion would orphan: `docs/dev/RELEASE_CHECKLIST.md:2175` (`project-v110-css-cascade-collapse`),
  `docs/dev/handoffs/chore-merge-channel-alignment.md:179` (`project-scrub-local-eval-paths-parked`),
  `docs/dev/handoffs/fix-handoff-pointer-verification.md:69` (`project-handoff-pointer-verification`),
  `docs/dev/handoffs/epic-a-chain-design-corrections.md:180` (`reference-recover-interrupted-session-from-transcript`),
  `docs/dev/reviews/2026-06-product-excellence/02-assessment/findings/governance-memory-incubation.md:49`
  (`feedback_git_merge_confirm`). Handoffs and reviews are dated records; `RELEASE_CHECKLIST.md` is live.
- **MERGE rows:** all 5 survivors exist. The one fact found nowhere else in memory or the repo is the chicken-and-egg
  self-edit trap in `project-plan-approval-hook-scope` (land the dependency files first and the gating file last; recover with
  `git checkout -- <path>`). Parts of the other merged files are out of date (the `.sh` hook path, `CONFIGS_DIR` in the
  route-security token list, the `.panel-header::after` example after PX-51, the "cleanup-on-merge wipes the marker" hook,
  which is gone).
- **FOLD rows (15):** no live `docs/dev` doc holds either recipe. Closest homes are archived and frozen
  (`docs/dev/archive/app-blueprints-design.md`, `docs/dev/archive/kit-adoption-design.md`). Several memory claims are stale
  and must be re-verified against code when folded: `.claude-plugin/hooks/*.sh` no longer exists, ruff is pinned to
  `0.15.22` (`pyproject.toml:113`), not `0.15.12`, and `CONFIGS_DIR` was dropped from the route-security regex
  (`scripts/enforcement/guards/route_security_lint.py:25-28`).

**Docs-IA facts for the fold (Explore pass, unverified by the orchestrator):** the doc process is `skills/doc-writing/SKILL.md:20-65`;
a new loose `docs/dev/*.md` must be classified in `scripts/wiki_relevance.py`
(`tests/test_wiki_relevance_classification.py:69-99`), and that file is a C-10 gated surface
(`scripts/enforcement/blast_radius.py:167-172`), so the consumer dossier comes first.

**Not verified:** that the 1.66 MB figure is on-disk size (inferred from `du -sh` 1.7M vs `du -cb` 1,034,153 B); the
clean-lint recipe's obsolescence; the full CHANGELOG seam entries for 8.3c to 8.3h.
