```toml
schema = 1
id = 7
kind = "item"
title = "PX-46 selective memory consolidation"
status = "open"
decision_owner = "user"
refs = ["RELEASE_ARC.md step 13", "docs/dev/reviews/2026-07-efficiency/prescriptions.md:53"]
summary = "Memory consolidation: 85 deleted, 16 trimmed, 12 merged, index rebuilt; further deletions await owner approval."
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

### 2026-10-18 - capture steps done on `chore/memory-consolidation` (still no deletion)

- **Backup:** the whole memory directory was copied to a sibling directory outside the one the harness loads
  (`memory-backup-2026-10-18`, 266 entries, 1,034,153 B of `.md`; `diff -rq` against the live directory read identical at the time).
  Every delete below is reversible from it until the owner removes it.
- **Capture into the repo:** `docs/dev/engineering-recipes.md` (new, registered, indexed from `docs/dev/README.md`) holds the
  re-verified, still-true parts of the 15 FOLD rows: the add-or-move-a-route steps and the typing/docstring floor steps. Each rule
  cites the test or config that enforces it (`tests/test_ux_stub_coverage.py`, `tests/test_mypy_strict_roster_gate.py`,
  `tests/test_docstring_coverage_gate.py`, `tests/test_egress_allowlist.py`, `tests/test_route_containment_gate.py`,
  `tests/test_web_infra_is_leaf.py`). **Not carried, deliberately:** the migration-era steps (Option X, transitional helper copies,
  per-seam fixture rewrites; `app.py` has no routes left), `ruff==0.15.12` and the D205-autofix counts (version-specific), and the
  interrogate `tomllib`/`S603` test-writing gotchas (the test already exists). The ruff-pin rationale already lives at
  `pyproject.toml:106-113`. Consumer enumeration for the one gated edit (`scripts/wiki_relevance.py`): `docs/dev/blast-radius/chore-memory-consolidation.md`.
- **MERGE rows applied additively (merged files NOT deleted):** unique, still-true text of `feedback_git_merge_confirm`,
  `reference-style-css-duplicate-cascade-rules`, `project-route-security-lint-scope`, `project-plan-approval-hook-scope` and
  `reference-recover-interrupted-session-from-transcript` was appended to their five survivors, each section stating its source and date.
- **Broken `[[links]]` repaired:** 31 links across 21 files (the Explore pass's "30" was a count of 12 + 2 + 16 = 30 plus one `.md`-suffixed
  link it had not listed; six items it listed turned out to be literal text, not links: `[[slug]]`, `[[backlinks]]`, `[[Application]]`,
  the TOML header `[[tool.mypy.overrides]]`, and were left alone). 25 renamed or repointed, 6 had no target anywhere and were un-bracketed
  (`roadmap-v1.0.2-v1.1.0`, `v1.0.1-real-release`, `ui-redesign-planned`, `sartor-governance-migration-pending`,
  `reference-px-band-sequencing-authority`, `reference-scroll-spy-settle-gate-audit`). After: **0 broken links, 0 MEMORY.md lines naming a missing file**.
- **Still owed:** the sweep of the other ~222 files, the approval table, the approved deletes, the `MEMORY.md` compaction.

### 2026-10-18 - full sweep of the other 222 memory files: verdicts recorded (nothing applied)

**Method.** Five read-only Explore agents each read every file of a slice in full (45 / 25 / 50 / 50 / 52 files; S1 feedback, S2 project, S3 to S5
reference) and gave one verdict per file with `path:line` cites per fact for every delete. **The agents' cites are hypotheses until checked.**
The orchestrator then re-read about 15 cites behind 12 delete verdicts (across all five slices: `tests/_controls.py` and its gate test,
`single-instance-and-quit.md:52-54` and `instance.py:73-76`, `charter.md` D-7 and C-8, `AGENTS.md:96-100` and `:203-207`, `doc-style-guide.md`
section 1 and 2, `blast_radius.py:61`, `plan_gate.py:93`, the mermaid checker, `scripts/gate.py:39-40`, items 0175 and `maintainer-lane.md:78`,
`ci_wait.py` exit codes, the avatar tests): **all existed and matched; none was contradicted.** Not checked: the many remaining per-fact cites.
The agents' own header tallies were wrong twice (S2 and the draft-list pass); the per-file labels below are what is recorded.

**Totals (222 files):** DELETE-CANDIDATE 102 (S1 11, S2 10, S3 27, S4 31, S5 23), FOLD 44, TRIM 34, MERGE 8, KEEP 34. Verdict names are the memory file
stems; `reference-`, `feedback-` and `project-` prefixes are kept where the agent kept them.

**Compaction fact to weigh before approving deletions.** Only `MEMORY.md` (20,458 B, the index) is loaded every session; the 265 files are read
on demand. Deleting a file saves disk, not context; the index lines, and the few very large files (`project-ux-scroll-flake-chip0` 34,859 B,
`feedback-schedulewakeup-not-for-background-bash` 29,057 B), are what cost context.

**Tentative batches for the approval table** (proposed, not approved):
- **A (16):** the draft list's SAFE-DELETE rows (listed in the 2026-10-18 entry above).
- **B (78):** sweep DELETE-CANDIDATEs minus batch C and minus every `feedback-*` / `feedback_*` file.
- **C (13), lower confidence, agent- or orchestrator-flagged:** `project-dependabot-docs-site-alerts`, `reference-append-order-vs-timestamp-detects-backdated-log-import`,
  `reference-eval-runner-judge-payload-trap`, `reference-atomic-context-write-windows`, `reference-epic-a-chain-orchestration-design`,
  `reference-grounding-source-union-prompt-vs-metric`, `reference-hook-receipts-spool-on-trunk`, `reference-long-run-log-lies-tee-and-pid-checks`,
  `reference-flush-stale-plan-stamp-on-branch-not-main`, `reference-plan-approval-hook-global-scope`, `reference-skill-corpus-item-dual-path`,
  `reference-ux-smart-landing-tab`, `reference-process-wide-run-slot-test-drain`.
- **D (11), the owner's own behavioural feedback, homed but kept by default:** the 11 S1 DELETE-CANDIDATEs.

**Conflict found between slices:** S3 says merge `reference-dashboard-education-ported-help` into `reference-help-opener-dedup-built`; S4 says
`reference-help-opener-dedup-built` is itself a delete (all facts in `static/help-modal.js` comments). If the survivor goes, the merged file's two
unique lines (the shared `#helpModal` id; per-tab help fires on click plus one load-time call) are unverified and should be checked before either goes.

**Repo defects and gaps the sweep found (to file or fix, none fixed here):** `scripts/gate.py:39-40` cites a nonexistent item file
(`0108-gate-memory-preflight-refusal.md`; the real file is `0108-gate-preflight-resource-check.md`); `evals/README.md:97,153` say per-fixture `min_*_score`
thresholds exist but `evals/runner.py` never reads them (tracked nowhere); `reference-workflow-relays-triggering-prompt` names a C-11 guardrail owed with no
work item; tracked files still mention `sartor-e2e` (`RELEASE_ARC.md:1351`, `RELEASE_CHECKLIST.md:718,2623,2633`, `handoffs/chore-scrub-local-eval-paths.md:85`) against a memory
rule that nothing committed may reference it; `AGENTS.md:44` still points at a charter section that does not exist (`project-sartor-10p-backbone-pointer-stale`);
`MEMORY.md` lines for `v11-final-march`, `concurrent-agents-worktree` and `doc-style-guide` are stale; `AGENT_HANDOFF_TEMPLATE.md:228` names `feedback_hook_discipline`
and `CLAUDE.local.md:30` names `feedback-interrogative-is-not-a-work-order` by path, so neither may be deleted without rewording.

#### Per-slice verdict lists (agent reports, condensed by the orchestrator; cites live in the agents' reports and the memory files' repo homes)

#### S1 feedback-* (45 files) - agent report, UNVERIFIED until spot-checked
DELETE-CANDIDATE (11): feedback-consume-handoff-dont-reconstruct (CAUTION: 0007 says project-hook-dispatcher-px37 SAFE label depends on it), feedback-cumulative-open-ledger, feedback-doc-style-guide, feedback-durable-before-deep (minor unhomed corollaries), feedback-handoff-process, feedback-instrument-before-fixing (28 inbound links), feedback-maintain-durable-docs-inline, feedback-no-waves-until-reliable, feedback-verify-completeness-before-done, feedback-verify-hash-before-citing-in-handoff-pointer, feedback_hook_discipline (TPL:228 names it by name; owner quotes lost; 142 tracked files cite the name)
FOLD (12): ab-fix, attribute-the-subject, measure-the-ordinary-case, trace-fix-design, check-for-superseding, trace-stated-mechanism, verify-handoffs-sequencing, verify-rollup -> ONE new AGENT_FAILURE_PATTERNS.md section (e.g. 5g); enumerate-by-class -> blast-radius/TEMPLATE.md; corpus-mode-eval-coverage -> evals/README.md (re-verify premise first); no-baked-in-absolute-paths -> CONTRIBUTING.md; project-docs-not-personal -> doc-style-guide.md
TRIM (5): cleanup-own-processes(~40%), concurrent-agents-worktree(~45% + fold mode-3 into work/SCHEMA.md), dont-trust-self-context-judgment(~45%), interrogative-is-not-a-work-order(~55%; CLAUDE.local.md:30 points to it by path), schedulewakeup-not-for-background-bash(~92%, 29KB->2KB)
MERGE (4): answer-before-acting + dont-announce-and-act-same-breath -> interrogative-is-not-a-work-order; design-sprint-interactive-elicitation -> dont-overcommit-to-time-based-decisions; instrument-hooks-against-throwaway-repo -> reference-hook-manual-testing
KEEP (13): adversarial-review-before-pivoting-scope, be-other-than-default, dev-content-in-dev-docs, dont-overcommit..., external-ventures-out-of-scope, form-finding-vs-tending, narrate-findings-before-decision-questions, never-suggest-wsl-shutdown, performance-metrics-docs, scope-is-quoted-never-derived, solve-dont-chunk-workaround, verify-against-durable-docs, verify-existence-before-asserting-absence
Notes: feedback files are small; largest wins are the TRIMs. MEMORY.md lines to fix: concurrent-agents-worktree, doc-style-guide.

#### S2 project-* (25 files) - agent report, UNVERIFIED until spot-checked
DELETE-CANDIDATE (10): project-2026-06-excellence-review, project-2026-07-efficiency-review, project-autonomous-drawdown-2026-10-03-uncommitted, project-avatar-voice-tone-guidance, project-dependabot-docs-site-alerts, project-deterministic-ci-wait-governance, project-epic-a-authorization-envelope, project-llm-call-provenance-requirement, project-v110-fork-owner-gated, project-verify-dont-assume-enforcement-gap
KEEP (6): project-context-mode-revisit, project-dx-install-test-macos12, project-e2e-instance-location, project-laptop-memory-pressure-is-transitional, project-robert-job-search-positioning, project-sartor-10p-backbone-pointer-stale
TRIM (6): project-chain-execution-experiment-and-vectoring-directives(~85%), project-go-public-ci-state(~85%, keep gh MSYS gotcha), project-item97-design-sprint-decisions(~90%, keep spolia-naming rule), project-launch-requirements-launcher-pushbutton(~80%, keep WSL2/ext4 decision), project-ux-scroll-flake-chip0(~93%), project-v11-final-march(~85%, keep /model-print convention)
FOLD (2): project-ci-infrastructure-sprint-sequence -> item 0003 Updates (enforce_admins rationale); project-handoff-integrity-kit -> AGENT_HANDOFF_TEMPLATE.md (no markdown links inside verbatim sections)
MERGE (1): project-enforcement-first-governance -> feedback-be-other-than-default (owner-trust tone paragraph)
Other findings: scripts/gate.py:39-40 cites nonexistent item file 0108-gate-memory-preflight-refusal.md (real: 0108-gate-preflight-resource-check.md); tracked files still mention sartor-e2e (RELEASE_ARC.md:1351 etc); MEMORY.md:142 stale "D on epic/d-docs-ia"
Index fallout of the 10 deletes: MEMORY.md lines 155,159,114,150,147,145,148,153,149 need editing.

#### S3 reference_a (50 files) - agent report, UNVERIFIED until spot-checked
DELETE-CANDIDATE (27): alembic-batch-parent-fk-cascade, append-order-vs-timestamp (low conf; dated handoff links slug), assistant-wiki-coverage-built, atomic-context-write-windows (bgDraftFiring "reverted" claim unverified), avatar-citation-format-built, bash-to-python3-path-gotchas-windows, compose-bare-reload-race-free, compose-bullet-edit-not-refrozen, compose-composition-save-clobbering, compose-settle-bg-reload-built, consumer-enumeration-gate-c10, context-transaction-delta-trap, corpus-import-curation-ux, cover-letter-tone-tuning-built, deterministic-generate-built, diagnosis-doc-slug-strips-fix-prefix, doc-assistant-built, doc-assistant-vector-built, doc-registry-and-move-policy, docs-site-build-check, documentation-architecture, driving-the-app-outside-the-ux-suite, egress-allowlist-gate, epic-a-chain-orchestration-design (Epic A merged #117), eval-results-dir-heterogeneous-files, eval-runner-judge-payload-trap (medium conf: test pins jd_label only), f01-keyword-cleaning-built
FOLD (8): alembic-downgrade-then-seed-needs-stamp, app-loggers-silent-under-pytest, cpu-saturation-flake-repro, deterministic-capability-probes-for-rival-hypotheses -> engineering-recipes.md (needs header edit: currently "authoritative for the two recipes"); capture-screenshots-demo-state -> screenshot-capture.md; claude-allow-main-edits-scope -> AGENTS.md:201 (+CLAUDE.md:104); dark-factory-research -> item 0097 Updates or archive appendix; eval-harness-auth-and-cost -> evals/README.md cost section
TRIM (8): agent-worktree-autoclean-trap(~30%), avatar-voice-tuning-built(~65%), axe-a11y-gate(~55%), background-bash-kill-ceiling(~80%), background-task-exit-code-unreliable(~65%), codeql-path-injection-chokepoint(~75%), compliance-witness-built(~85%), eval-smoke-gate-exit2-contract(~75%; keeps unfiled README min_* doc gap)
MERGE (2): conductor-tip-gate-worktree-hygiene -> conductor-verify-lanes; dashboard-education-ported-help -> help-opener-dedup-built (but help-opener-dedup-built is a DELETE in S4 -> conflict, resolve)
KEEP (5): bash-tool-no-coreutils-monitor-busyloop, bypass-permissions-session-binding, conductor-verify-lanes, enforcing-test-tighten-on-removal, fake-client-tests-must-redirect-telemetry (diagnosis doc defers destructive-delete rule to this memory)
CONFLICT NOTE: S3 #32 merges dashboard-education-ported-help into help-opener-dedup-built, but S4 marks help-opener-dedup-built DELETE (all homed in static/help-modal.js comments) -> then both are delete; dashboard-education unique line is unverified.

#### S4 reference_b (50 files) - agent report, UNVERIFIED until spot-checked
DELETE-CANDIDATE (31): flask-reloader-browser-open, flush-stale-plan-stamp-on-branch-not-main (rests on item 0056 "watching"), frozen-composition-mechanics, gap-fill-bullets-built, gate-memory-preflight-built, gate-result-file-and-hookspath, gh-actions-log-parsing-gotchas (mirror of flake_rates.py docstring), git-grep-self-match-test-gotcha, github-status-incident-diagnosis, grounding-source-union-prompt-vs-metric (LOW confidence: doc-coupling point 4 unhomed), help-opener-dedup-built, help-pattern-primitive, hook-receipts-spool-on-trunk (-k trap + ls-files trap only instance-homed), hooks-python-direct, keep-ledger-guards-built, kw3-tour-and-education-help, list-applications-n-plus-1, long-run-log-lies-tee-and-pid-checks (repo cites stem at epic-a-chain-design-corrections.md:755), maintained-classification-list-pattern, march-session-model-rules-drift, mermaid-parse-needs-dom, minicheck-grounding-loop-drift, monitor-silence-is-not-success, native-checkbox-css-gotcha, npm-override-vs-bump-and-ts-esm-detection, per-session-hook-state-kills-orchestrated-runs, plan-approval-hook-global-scope (stem cited at diagnosis/plan-approval-hook-scope.md:13), plan-approval-retire-timeout-and-epic-prune, playwright-beforeunload-and-drawer-stacking, playwright-capability-probe-mechanics, playwright-networkidle-order-dependence
FOLD (8): flask-test-client-sse-drain-required + function-local-import-defeats-module-patch + model-upgrade-playbook -> engineering-recipes.md (Test-writing traps / Bump a model pin); gate-from-powershell-hits-wsl-bash -> CONTRIBUTING.md Quick start; handoff-template-verbatim-drift-found -> AGENT_HANDOFF_TEMPLATE.md header; hook-manual-testing -> tooling.md "Hand-testing a guard"; n1-pipeline-no-review-only-stage -> n1-baseline-pipeline.md; openssf-scorecard-hardening -> doc-style-guide.md:122-125
TRIM (7): flask-stream-teardown-and-reloader-watch(~60%), gitattributes-pin-stale-worktree(~45%), governance-extraction-design(~70%), heredoc-escaping-and-first-match-anchors(~60%), merge-commit-parent-order-gotcha (headline WRONG vs its own evidence -> ~4 lines), n1-baseline-pipeline-built(~85%), plugin-activation(~65%; repo cites stem keep-ledger.md:135; many stale names callback->sartor)
MERGE (1): git-diff-trailing-slash-quoting -> git-bash-leading-slash-arg-rewrite (claim NOT reproducible today)
KEEP (3): git-bash-leading-slash-arg-rewrite (reproduced today), hpiq-case-study-artifact, isidium-tracking-part-bdd-fit
Stem cited from live repo docs (would dangle on delete): plan-approval-hook-global-scope, long-run-log-lies-tee, plugin-activation, model-upgrade-playbook (items/0173:72), openssf-scorecard-hardening (items/0171:94)

#### S5 reference_c (52 files) - agent report, UNVERIFIED until spot-checked
DELETE-CANDIDATE (23): process-wide-run-slot-test-drain, profile-text-vs-online-profile, recall-skeleton-built (no index line), release-versioning-d7, sartor-rename-recruiting-pun, scroll-anchoring-dy-equals-dh, scroll-spy-hardening-mechanics, scroll-spy-settle-gate-leak, self-documenting-loop-design, settle-wait-vs-deliberate-racers, skill-corpus-item-dual-path (medium), smooth-scroll-survives-navigation, sse-disconnect-simulation-technique, stream-route-needs-generate-streaming-stub, ux-compose-ready-wait, ux-copy-assertions, ux-generate-drive-and-scroll-spy, ux-select-option-attached (no index line), ux-smart-landing-tab (medium), wiki-freshness-single-branch-threshold, windows-port-double-bind-and-probe-cost, work-item-tracking-system, xfail-strict-masks-broken-controls
KEEP (7): pytest-exit-through-pipe, substrate-projection-layering, taskoutput-nonblocking-stale-preview, tending-pass-method (path stale: now C:\Dev\lichen\methodology\tending-pass.md), webfetch-quotes-are-summarized, werkzeug-reloader-orphan-child, workflow-relays-triggering-prompt (guardrail owed C-11, no work item -> recommend filing)
FOLD (14): prescription-metrics-can-restale->AFP 5e line; preserve-cross-item-evidence, pytest-in-process-loop-and-mutation-plugins, sandbox-ux-walkthrough-method (needs rewrite around SARTOR_HOME), tests-package-conftest-import -> engineering-recipes.md Testing recipes; rerun-masking-chronic-flake->flake-rates/README.md; review-charter-clause-location->charter.md "What this is"; subagent-pretooluse-agent-id->item 0169 Updates (peer hand-backs still arm witness, seen 3x 2026-10-16); user-docs-verify-against-live-labels->skills/doc-writing/SKILL.md; wiki-auditor-has-no-bash + wiki-scribe-cannot-create-pages + wiki-scribe-head-vs-working-tree -> commands/wiki-self-update.md gotchas block; wiki-checkpoint-ratchet-defect->item 0098 (unchosen option); wiki-freshness-detect-vs-correct->item 0065 Updates
TRIM (8): self-documenting-wiki-built(~80%), shared-machine-oom-kills-bg-runs(~55%), spolia-board-comparison(~40%), subagent-background-wait-gotcha(~40%), ux-flake-ci-runner-not-local-load(~60%), windows-console-unicode-print-crash(~35%), witness-pause-stale-plan-approval(~50%), workflow-subagent-gotchas(~55%)
Note: many repo files cite memory stems (handoffs, 5 diagnosis dossiers, items 0030/0062/0079/0098/0143, block_subagent_git_stash.py:22) -> dangling on delete.

### 2026-10-18 - owner decisions on the approval table; batch A applied

**Owner decisions (chat, 2026-10-18):** (1) **Batch A: delete**, with fixes from the sweep's findings. (2) **Batch B: not yet deleted**; first a close adversarial
read "so we optimize without lossiness to useful memory; but bad memories are worse than no memories because we act as if we already know the state instead of
investigating". (3) **Batches C and D: review for accuracy; no deletions unless an inaccuracy is found.** Also chosen: **trim only the large files** (plus the 8 merges,
done additively) and **defer the 44 fold-ins** to one follow-up item; those 44 files stay as they are.

**Batch A applied (16 files deleted from the memory directory; the pre-change copy is the sibling `memory-backup-2026-10-18`):** `reference-kit-phase1-pydantic-mypy-built`,
`reference-app-blueprints-design`, `project-2026-07-unusable-remediation`, `project-2026-07-ux-review`, `project-bigpush-opus-handoff`, `project-config-drift-batch-px47`,
`project-context-write-lost-update-gap`, `project-diagnostics-run-cancel-landed`, `project-handoff-pointer-verification`, `project-hook-dispatcher-px37`,
`project-scrub-local-eval-paths-parked`, `project-v108-walkthrough-epic`, `project-v108-window-8.5-to-8.6`, `project-v110-compose-frozen-composition`,
`project-v110-css-cascade-collapse`, `project-large-corpus-scalability`. Fixes applied with it: 18 inbound `[[links]]` in 14 kept files were **repointed to the deleted
file's repo home** (not left dead and not just un-bracketed); the `MEMORY.md` lines naming them were edited (`app-blueprints-design` line removed; the sibling mentions of
`handoff-pointer-verification` and `project-large-corpus-scalability` removed); the stale `v11-final-march` index line ("D on `epic/d-docs-ia`", but Epic D merged) was
rewritten to say epics A to D merged and to point at `BOARD.md`. `project-hook-dispatcher-px37`'s two facts that have no repo home live in kept memories
(`reference-hook-manual-testing` Gotcha 3, the `/c/` path false-ALLOW; `feedback-consume-handoff-dont-reconstruct`), so those two stay. **Left alone on purpose:** dated
repo records that cite deleted stems by name (e.g. `RELEASE_CHECKLIST.md:2175`, `handoffs/chore-merge-channel-alignment.md:179`, `handoffs/fix-handoff-pointer-verification.md:69`). After:
**250 entries (249 memory files + `MEMORY.md`), 0 broken `[[links]]`, 0 `MEMORY.md` links to missing files.**
The batch A homes rest on the first Explore pass's cites plus the orchestrator's sample; batch A was not put through the adversarial read below.

**Adversarial read (batch B, 78 files) and accuracy audit (batches C and D, 24 files): launched.** Five refuter agents try to prove each B delete loses a fact or that the memory is
wrong; two auditors check every claim in C and D against the current repo. Every cite must carry a verbatim quote, and a script (`verify_quotes.py` in the session scratchpad)
checks each quote appears in the cited file within three lines. A fabricated or paraphrased quote fails mechanically.

### 2026-10-18 - batches B, C and D executed; MEMORY.md rebuilt (memory counts below)

**How batch B was read.** Five refuter agents, each told to prove a delete loses something or that the memory is wrong, produced
JSONL with a verbatim quote per cited home. A script (`verify_quotes.py`, session scratchpad) checked every quote against the
cited file: **844 file-quote citations across the five outputs (319 + 156 + 181 + 188, B1 and B4 counted together), 0 fabricated, 0 missing**. (Three refuters, B1, B2 and B4, generated their JSONL with builder scripts, and B4 says its script corrected cited line numbers to the quote's real line, so for those the position check may pass trivially; the quotes still prove the text exists in the file.) The orchestrator then read every fact-to-quote pair for all 78 files and the memory's wrong-in-memory list. Quotes
prove text exists, not that it supports the fact; that second check was the orchestrator's read.

**Batch B result: 69 deleted, 9 trimmed, 0 left as they were.** Seventy-eight files were read; 69 were deleted
(68 DELETE-CONFIRMED, plus `reference-gate-memory-preflight-built`, which a refuter would have trimmed to an unsourced
"55 min" figure that contradicts `scripts/gate.py:113-116`). **Nine files had a real remainder and were rewritten to it instead
of deleted:** `project-verify-dont-assume-enforcement-gap`, `reference-docs-site-build-check`, `reference-help-pattern-primitive`,
`reference-march-session-model-rules-drift`, `project-deterministic-ci-wait-governance`, `reference-native-checkbox-css-gotcha`,
`reference-npm-override-vs-bump-and-ts-esm-detection`, `reference-f01-keyword-cleaning-built`, `reference-sartor-rename-recruiting-pun`.
Sixty-three inbound `[[links]]` in 54 kept files were repointed to each deleted file's primary repo home. **The still-unhomed
leftover lines of the deleted files (26) are preserved verbatim in work item 176**, so nothing was dropped silently.

**Bad memories removed or corrected.** The refuters found claims in files marked for deletion that were false today, so deleting
them removed false beliefs as well as redundancy: `reference-per-session-hook-state-kills-orchestrated-runs` said `agent_id` was
never observed (item 94 observed it); `reference-ux-compose-ready-wait` gave a `networkidle`-first rule that had been superseded;
`reference-egress-allowlist-gate` said "exactly 8 files incl. app.py" (the test lists 15); `reference-mermaid-parse-needs-dom`
said real rendering happens in the docs-site build (the build cannot catch a broken diagram); `reference-doc-assistant-built`
said the blueprint inline-copies helpers that now live in `web_infra`.

**Batches C and D (24 files): audited for accuracy, none deleted.** Two auditors checked every claim against the repo and
machine. **9 accurate, 15 corrected in place, 0 with a false central claim, so by the owner's rule none was deleted.** Fifteen
files received exact-substring replacements (each `old` text matched exactly once). Notable corrections: `feedback-handoff-process`
(the handoff is now written on the branch before the merge); `reference-grounding-source-union-prompt-vs-metric` (the metric union
is five sources, not three); `reference-skill-corpus-item-dual-path` (the "pending skills excluded from the prompt" claim is false
for the no-recommendation baseline path); `project-dependabot-docs-site-alerts` (the six alerts were fixed; 23 different ones are
open, confirmed with a read-only `gh api` call); `reference-atomic-context-write-windows` (its "production is single-threaded"
claim is marked UNVERIFIED, because Flask 3.1.3's `run()` does `setdefault("threaded", True)`; filed as item 177 point 1, **a
possible product-impacting contradiction in `hardening.py:1992`**). Where an incidental detail was stale the file was
corrected rather than deleted; this reads the owner's "no deletions unless you find inaccuracies" as "delete only a file whose
central claim is false".

**MEMORY.md rebuilt**, not patched: 35 lines pointed at deleted files; it is now pure pointers, states no current state (no
"BUILT", "RESOLVED" or dated status), lists every kept file by name (the six per-seam files by brace shorthand), and points
to `BOARD.md` for status. **20,458 B to 16,127 B**, under the hook's 17.1 KB target.

**Follow-ups filed:** item 176 (the 44 deferred fold-ins, the 26 unhomed leftover lines, the 9 trimmed files) and item 177 (11
repo defects and gaps found by the sweep).

**Still open on this item at this point:** the sweep's large trims and its 8 MERGE rows (owner chose "trim only the large ones"
and "the 8 merges done additively"); the 15 draft-list FOLD files and 5 draft-list merged files, which were folded or merged
additively but not deleted (no approval for those deletions was given); the two PARTIAL draft rows; and the close-out.

### 2026-10-18 - large trims and sweep merges applied; final counts; what is still the owner's

**Large trims (7 files), planned by two more independent agents and checked the same way** (123 verbatim quotes verified, 85 for the first planner and 38 for the second, 0
fabricated; kept text copied by line range from the pre-change backup, new text marked "as of 2026-10-18"):
`project-ux-scroll-flake-chip0` 34,859 B to 2,940 B; `feedback-schedulewakeup-not-for-background-bash` 29,057 B to 3,799 B;
`project-item97-design-sprint-decisions` 18,058 B to 2,883 B (its decisions are homed in the **sister repo** `C:/Dev/the-factory`, so that
pointer breaks if the sister repo moves; stated in the file); `reference-background-bash-kill-ceiling` 16,534 B to 7,333 B;
`project-chain-execution-experiment-and-vectoring-directives` 16,505 B to 4,458 B; `reference-n1-baseline-pipeline-built` 15,993 B to
1,381 B; `feedback-interrogative-is-not-a-work-order` 13,948 B to 6,054 B (kept the rules, the 2026-08-12 incident in the owner's own
words, and the owner's causal framing; `CLAUDE.local.md:30` names this file by path). Each trim also **corrects** what the audit
found false: the kill-ceiling note's "35-40 min `run_in_background` works reliably" is marked an overclaim (OOM kills and the
`nohup` finding are real); the `ScheduleWakeup` note's claim that the call "can kill that task" is marked retracted; the chain note's
"NOT yet executed" is narrowed (only directive 1, a charter-level grammar, is unexecuted).

**Merges (12), all additive, merged files NOT deleted:** the 5 draft-list pairs (earlier entry) and 7 sweep pairs: `feedback-answer-before-acting`
and `feedback-dont-announce-and-act-same-breath` into `feedback-interrogative-is-not-a-work-order`;
`feedback-design-sprint-interactive-elicitation` into `feedback-dont-overcommit-to-time-based-decisions`;
`feedback-instrument-hooks-against-throwaway-repo` into `reference-hook-manual-testing`; `reference-conductor-tip-gate-worktree-hygiene` into
`reference-conductor-verify-lanes`; `reference-git-diff-trailing-slash-quoting` into `reference-git-bash-leading-slash-arg-rewrite` (the
trailing-slash mechanism **did not reproduce** on 21 commit pairs and is carried only as a "run a control" warning);
`project-enforcement-first-governance` into `feedback-be-other-than-default`. A planned eighth merge (`reference-dashboard-education-ported-help`
into `reference-help-opener-dedup-built`) was dropped because the survivor was deleted in batch B.

**New memories written (pre-close sweep):** `feedback-bad-memory-is-worse-than-none` (the owner's principle) and
`feedback-explain-tradeoffs-before-batch-approval` (how the owner wants multi-batch approvals presented). Work item 0169 gained a
dated note: the interrogative witness paused five `Write`/`Edit` calls this session right after peer hand-backs arrived.

**Final numbers (`ls`, `du -cb` over the memory directory, 2026-10-18):**

| | before | after |
|---|---|---|
| entries (files + `MEMORY.md`) | 266 | 183 |
| bytes of `.md` | 1,034,153 | 648,462 |
| `MEMORY.md` bytes | 20,458 | 16,427 |
| broken `[[links]]` (real ones; 6 literal `[[...]]` texts excluded) | 31 | 0 |
| `MEMORY.md` lines naming a missing file | 0 | 0 |

Totals: **85 deleted** (16 batch A + 69 batch B), **16 trimmed** (9 to their unhomed remainder, 7 large), **12 merged additively**, 0 deleted for
inaccuracy (24 files in C and D audited; none had a false central claim), 2 new memories written. The undo for any step is
the sibling `memory-backup-2026-10-18` directory (266 entries); **it is outside the repo and the owner should delete it when satisfied**.

**What is still the owner's (nothing below was done):**
1. Whether to delete the **12 merged files** whose text now sits in survivors (5 draft-list, 7 sweep).
2. Whether to delete the **15 draft-list FOLD files** (the app-factory and seam records and the ruff/mypy/interrogate ratchet records). Their
   surviving how-to is `docs/dev/engineering-recipes.md`; the rest is migration history. They are listed in the index by brace shorthand.
3. The **2 PARTIAL draft rows** (`excellence-walk-llm-wiki`, `project-v110-close-out-sequence`), each with one unhomed fact.
4. Batches C and D (24 files) stay, corrected where wrong.
5. The **44 FOLD files** are deferred to item 176; the sweep's STALE flags on the other kept files (path and count drift) were reported but
   **not applied** (this session corrected the 24 files in C and D and the batch-B trims only). Applying them is the next pass if you want it.
6. Closing this item needs a falsifiable `verified_by` artifact or an owner-named `closure_exception`; I left it `open`.
