---
status: review-artifact
evidence_sha: 4196d0c
graduation: none (action layer; feeds RELEASE_ARC via normal dev branches)
---

# Prescriptions — 2026-07 efficiency review

> The action layer. Every actionable CONFIRMED/WEAKENED finding becomes one
> PX row; KEEP/BOOST findings land in the consolidated affirmation row. **PX
> ids continue the global sequence — this review runs PX-37..PX-56** (the
> 2026-06 review ended at PX-36). Each Landing names exactly ONE release-arc
> spot. WEAKENED sources are prescribed on their REVISED claims (see
> [`verification-log.md`](verification-log.md)); the refuted F-run-01 issues
> no prescription.
>
> **Band panel — 2-judge variant.** The 2026-06 review banded with a
> three-judge panel; this review used two judges plus an orchestrator
> tiebreak, a deliberate budget deviation: **Throughput-Value** (tokens/
> minutes/LOC saved per unit of landing effort; rewards deletion) and
> **Stability-Risk** (would landing destabilize in-flight sprints or weaken
> an existing gate/contract; penalizes ceremony). Mechanics: agreement →
> band stands; 1-band spread → orchestrator tiebreak, taking the LATER band
> unless that contradicts an existing arc commitment or a correctness
> exposure; >1-band spread → CONTESTED + conservative band + callout.
> **Outcome: 9 agreements, 11 one-band tiebreaks, 0 CONTESTED.** The only
> commitment-override tiebreak is PX-41 (deferring the already-scheduled 8.6
> ingest would contradict its own coordinate).
>
> **Standing constraint (owner-stated 2026-07-03):** the AGENTS.md /
> CLAUDE.md pair is deliberately two files because the project plans for
> LLM-agnostic agents — AGENTS.md must remain a complete standalone contract
> readable raw by non-Claude agents. No prescription may reduce it to an
> import shell or move its guardrails somewhere only Claude sessions load.

---

## Prescription table (sorted by band, then leverage)

| PX-id | Title | Finding refs | Disposition of source | Landing | Band | Gist |
|---|---|---|---|---|---|---|
| PX-42 | Make the Python floor true before the first PyPI tag | F-tci-05 | CONFIRMED (escalated) | rides ledger #1 packaging branch @ v1.0.8 tail | now-v1.0.8-tail | requires-python ships in the wheel metadata: raise to >=3.11 + drop the 3.10 classifier (recommended — the suite already can't collect on 3.10 via tests/test_docstring_coverage_gate.py:47 tomllib) or fix the import and add a 3.10 CI job. Both judges independently ranked this the must-land item: a false floor published to PyPI is a correctness bug that costs a re-tag to fix. |
| PX-40 | Reconcile PRODUCT_SHAPE.md to the post-split reality | F-doc-01 | CONFIRMED | existing: v1.0.9 docs epic — COORDINATE | v1.0.9 | Fix the WS-1 row (app.py = 241-line factory, 0 routes), the two dead app.py:1403-1423 cites (:186,:481), and add as-of/status markers distinguishing planned vs completed workstreams. Judges agreed: zero new moving parts inside an epic already in flight. |
| PX-41 | Run the scheduled 8.6 wiki catch-up ingest as a bundle | F-doc-07 (WEAKENED), F-doc-08, F-doc-10 (WEAKENED), F-doc-11 | WEAKENED ×2 + WATCH + BOOST | existing: 8.6 /wiki-ingest — COORDINATE | v1.0.9 | Re-anchor the 119-commit backlog (route-surface.md first: 0 app.py + 99 blueprint + 1 dashboard routes); tighten bare-line cites to symbol form during the pass; recalibrate the freshness hook's escalation for large known backlogs; re-affirm D-5 empirically AFTER the ingest. Tiebreak kept the existing 8.6 coordinate — deferring already-scheduled work would contradict the arc. |
| PX-53 | Consolidate the triplicated _imported_roots() AST helper | F-tci-02 | FIX | new-branch: `test/shared-ast-helper` @ v1.0.9 | v1.0.9 | One shared helper (resolve-relative parameter for the recall variant) under tests/; three gate files import it. Judges agreed: fails closed, and de-duplicating the walk logic reduces exactly the cross-gate drift risk a prior egress-gate gap came from. |
| PX-48 | Dev-doc staleness batch: closure banners, CHANGELOG archive, ledger head-note | F-doc-03, F-doc-04, F-doc-06, F-adx-10 | FIX ×2 + WATCH + FIX | existing: v1.0.9 docs epic — COORDINATE | v1.0.9 | SUPERSEDED/SHIPPED banners on app-blueprints-design.md + kit-adoption-design.md; split CHANGELOG 0.1.0-1.0.3 (~585 ln) to an archive file; compress the ledger's ~500-word chronological head-note to a 3-line current-state note (git holds the history; W-1-adjacent — careful hand, no gate surface). |
| PX-50 | Build the DOC-STATUS grep gate (already scheduled) | F-doc-09 | FIX | existing: v1.0.9 CI merge-gate item #4 — COORDINATE | v1.0.9 | Affirm the schedule; the convention has 16 markers and zero enforcement — the gate greps for markers whose trigger sprint has tagged and fails the build. No ceremony beyond what's already designed. |
| PX-37 | Consolidate the 5 Edit/Write PreToolUse hooks into one dispatcher | F-adx-01 (WEAKENED), F-adx-02 | WEAKENED + CONFIRMED | new-branch: `chore/hook-dispatcher` @ v1.1.0-gate (after 8.7 portable-core) | v1.1.0-gate | One script parses stdin JSON once (single spawn) and fans in the 5 checks; per-Edit/Write tax drops from ~3.5-4s (slowest parallel hook) toward ~0.3-0.5s and the timeout-margin problem collapses to one budget. Tiebreak to gate: ledger #5's 8.7 restructure touches the same security surface (block-secrets, route-security-lint) — design the dispatcher AS the portable core's entry point, once, not twice. |
| PX-38 | Fix the Compose-route N+1 + the is_active index gap | F-run-06, F-run-10 | CONFIRMED + FIX (P3) | new-branch: `perf/compose-selectinload` @ v1.1.0-gate | v1.1.0-gate | selectinload bullets/titles/tag_links on get_application_composition (mirror the list_applications fix); add is_active to the composite index; N+1 guard test per the established after_cursor_execute pattern. Tiebreak to gate: proven pattern, but pre-public traffic makes it insurance, not an active loss. **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-39 | Establish a real-corpus latency baseline; retire legacy-population numbers | F-run-03 (WEAKENED), F-run-02 (WEAKENED), F-run-05 | WEAKENED ×2 + KEEP | existing: scripts/perf_baseline.py refresh @ v1.1.0-gate — COORDINATE | v1.1.0-gate | Measure split-era real-corpus p50/p95 (current: 69.7s/84.6s mixed traffic vs the synthetic-only 67s reference); update PERFORMANCE_HISTORY with population labels so defunct pre-split rows can't seed future false alarms; record the cache-healthy state (0 misses in 30d). **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-44 | Document the measured fast lane; investigate suite-wide fixture scoping | F-tci-01 (WEAKENED), F-tci-03 | WEAKENED + WATCH | new-branch: `test/fixture-scoping` @ v1.1.0-gate | v1.1.0-gate | Document the honest fast-lane numbers (idle measurement in verification-log addendum) + fix CONTRIBUTING's double-run; then profile per-test Flask/SQLite fixture cost — verifier data shows fixture overhead across ~1,378 "fast" tests dominates wall time; module-scope the read-mostly candidates (personas-500 keeps isolation). Tiebreak to gate: fixture-scoping touches test isolation mid-epic. |
| PX-45 | Agent-contract trim & accuracy pass (CLAUDE.md catalogs + AGENTS.md corrections) | F-adx-06 (WEAKENED), F-adx-09, F-run-07 | WEAKENED + FIX ×2 | new-branch: `chore/claude-md-catalog-trim` @ v1.1.0-gate | v1.1.0-gate | Per the revised claim: compress the 90-line catalogs to a pointer list, fold the 2-3 unique facts (compliance-witness cap/taxonomy) into frontmatter, keep a one-line fresh-clone fallback note; pointer-ize AGENTS.md's second 8-file boundary list (:166→:50); correct the cache-miss doc claim to cover all 11 override sites. AGENTS.md stays a full standalone contract (standing constraint). **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-46 | Selective memory consolidation (not wholesale deletion) | F-adx-07 (WEAKENED) | WEAKENED | new-branch: `chore/memory-consolidation` @ v1.1.0-gate | v1.1.0-gate | Owner-gated: fold the ≥3 unique-recipe memories (seam-move mechanics, mypy-strict + ruff-D verify commands) into a durable docs/dev/ reference, delete only the genuinely redundant completion logs, shrink the freed MEMORY.md index lines. Judges agreed: irreversible if botched — no urgency justifies the busy window. |
| PX-43 | CI hygiene batch: concurrency group, setup dedup, retention, fail-fast + arm64 decisions | F-tci-04 (WEAKENED), F-tci-06, F-tci-07, F-tci-08, F-tci-10 | WEAKENED + FIX + WATCH ×3 | new-branch: `ci/hygiene-batch` @ v1.1.0-gate | v1.1.0-gate | Add concurrency+cancel-in-progress (latent-risk close, cheap); factor eval-smoke's duplicate setup; set artifact retention-days; record explicit one-line decisions on fail-fast and arm64-QEMU. Tiebreak to gate: don't touch the CI that gates every merge in the same window as the first tag. **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-47 | Config-drift micro-batch | F-adx-03, F-adx-04, F-adx-05, F-adx-08 | FIX ×3 + DEBUFF | new-branch: `chore/config-drift-batch` @ v1.1.0-gate | v1.1.0-gate | plugin.json version bump; one model-pin convention (dated snapshots) across all 9 subagents; CLAUDE.local.md refresh; prune the ~15 dead/one-shot settings.local.json entries. Tiebreak to gate: model-pin changes alter which model subagents run while the v1.0.9 epic is actively exercising them. **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-49 | Corpus/pipeline canonical-home dedup across the top-4 docs | F-doc-05 | FIX | existing: v1.0.9 docs epic (late) / v1.1.0-gate — COORDINATE | v1.1.0-gate | architecture.md becomes the canonical home for corpus/pipeline mechanics; vision.md + PRODUCT_SHAPE.md reduce restatements to README-style pointer + one line (D-5). Tiebreak to gate: restructuring the top-4 docs concurrently with the in-flight docs epic is avoidable churn — land after the epic's current pass. |
| PX-51 | Collapse the style.css duplicate cascade layer | F-run-08 | FIX | new-branch: `refactor/css-cascade-collapse` @ v1.1.0-gate | v1.1.0-gate | Merge the ~780-line restyle block into the primary definitions (~20% file shrink, removes the later-rule-wins footgun); gate with the UX tier + screenshot capture. Tiebreak to gate: known cascade-fragility gotcha; don't compete with the docs epic + imminent tag. **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-54 | pip-audit in CI — fold into the pending badge set | F-tci-09 | BOOST | existing: PX-26 (`chore/e2-machine-badges`) @ v1.1.0-gate — COORDINATE | v1.1.0-gate | The minimal in-CI audit step rides PX-26's Dependabot work; land deliberately — a CVE-triggered CI failure is a new triage source for a solo maintainer. |
| PX-55 | Unified quality-gate wrapper script | F-adx-11 | FIX | new-branch: `chore/quality-gate-script` @ v1.1.0-gate | v1.1.0-gate | One scripts/ wrapper running ruff+mypy+pytest; AGENTS.md + CONTRIBUTING + ci.yml all invoke it (single definition of "gate green" — derived from CI, not restated, to avoid a second drift surface); sized not to pre-empt ledger #5's portable core. **[Re-verified 2026-07-07: PARTIALLY_STALE — see px-staleness-reverify-2026-07-07.md]** |
| PX-56 | Affirm-and-protect ledger | F-run-04 (BOOST), F-run-05 (KEEP), F-tci-11 (KEEP), F-doc-10 (conditional KEEP) | BOOST + KEEP ×3 | new-branch: `docs/efficiency-keep-notes` @ v1.1.0-gate | v1.1.0-gate | Do-not-regress notes: Haiku call kinds' zero-error record (consider Haiku for more structured calls), eval anchoring on old prompt versions is deliberate, Linux-only CI is a decision with a revisit trigger, and D-5's re-affirmation is owed AFTER the 8.6 ingest. |
| PX-52 | analyzer.py split — design-first, deferred | F-run-09 | WATCH | defer: post-v1.1.0 (trigger: next major prompt-surface work) | post-public | Extract prompts.py + client.py along the identified seams when prompt work next opens the file; not a standalone pre-public refactor. Judges agreed. |

---

## Notes

- **Effective-leverage demotions from verification** (register rows keep
  their tier per convention; bands reflect reality): F-adx-01 P0→P1
  (parallel hook execution), F-tci-04 P1→P2 (latent, not routine), F-run-02
  P1→monitor-only (resolved legacy), F-tci-01 P1→P2 (speedup smaller than
  projected).
- **Interactions:** PX-37 ↔ ledger #5 (portable core) — the dispatcher is
  designed as its entry point, landing after 8.7. PX-42 ↔ ledger #1 (wheel
  packaging) — floor truth must precede the first tag. PX-54 ↔ PX-26.
  PX-44's fixture investigation may reshape PX-43's cost assumptions.
- **Band distribution:** 1 now · 5 v1.0.9 · 13 v1.1.0-gate · 1 post-public.
  The judges' systematic pattern: doc-only work riding the in-flight epic
  lands now; anything touching gates, CI, security surfaces, or test
  isolation waits for the dedicated pre-public hardening window.
- The ledger's 7-vs-8 header count (F-doc-02) is corrected at this review's
  close-out as normal ledger maintenance, not via a PX.
