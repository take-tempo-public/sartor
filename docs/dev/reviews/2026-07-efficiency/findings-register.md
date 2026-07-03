---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Findings register — 2026-07 efficiency review

> Master register for the four-area efficiency/optimization review of
> **sartor.** All evidence pinned at `4196d0c`. Honors C-0 claims discipline
> (mechanism-and-effort language; no absolutes about LLM behavior).
>
> **Leverage tiers** are 10-Principles references (P0 = Survival, P1 =
> Hardening, P2/P3 = lower-altitude craft), used as the review's priority
> axis. The **verdict** column carries the adversarial verification result
> for every P0/P1 finding (`-` for P2/P3, which were not adversarially
> re-verified). **WEAKENED** findings keep their place but MUST be read with
> the revised claim in [`verification-log.md`](verification-log.md).
>
> Per-finding detail lives in [`findings/<area>.md`](findings/); per-verdict
> detail in [`verification-log.md`](verification-log.md).

---

## Register (sorted by leverage, then domain)

| F-id | Domain | Title | Disp. | Lev. | Verdict | Coordinate | Charter trace | Evidence (one-line) |
|---|---|---|---|---|---|---|---|---|
| F-adx-01 | process-dx | 5 serial PreToolUse hooks cost ~10.9s measured per Edit/Write (process-spawn tax) | FIX | P0 | pending | v1.0.9 | C-1, E-2 | .claude/settings.json:12-38; per-hook timings measured on-machine |
| F-adx-02 | process-dx | Hook timeouts (5s) too close to measured runtime (3.5s) — silent gate-failure risk | WATCH | P1 | pending | v1.0.9 | C-1 | settings.json:17-21,26-30 vs measured block-secrets 3.481s |
| F-adx-06 | process-dx | CLAUDE.md skill+subagent catalogs (47% of file) duplicate harness auto-injection | FIX | P1 | pending | new-branch: chore/claude-md-catalog-trim @ v1.1.0-gate | D-5 | CLAUDE.md:101-190 vs harness-injected skill/agent listings |
| F-adx-07 | process-dx | 16 memory files (~79KB) log completed work already durable in RELEASE_CHECKLIST | FIX | P1 | pending | new-branch: chore/memory-consolidation @ v1.1.0-gate | D-5, W-1 | memory/reference-app-blueprints-*.md + kit-phase*.md vs RELEASE_CHECKLIST.md:82,612-765 |
| F-run-01 | runtime | Split analyze adoption 40% — 60% of calls bypass the two-pass optimization | FIX | P1 | pending | v1.0.9 | P-9, D-4 | llm_calls.jsonl: 195 analyze vs 78 split pairs; PERFORMANCE_HISTORY:197-204 |
| F-run-02 | runtime | Generate cache-miss rate 38% across mixed prompt versions | WATCH | P1 | pending | v1.1.0-gate | C-6, D-4 | llm_calls.jsonl by prompt_version: 0% hit pre-2026-06-01.3, ~100% after |
| F-run-03 | runtime | Analyze p95 latency 126s vs documented 67s target (25 calls >60s) | WATCH | P1 | pending | v1.1.0-gate | D-4 | llm_calls.jsonl 2026-05-24.4 rows 86-122s; PERFORMANCE_HISTORY:75-100 |
| F-run-06 | runtime | Compose route N+1: per-experience lazy bullets/titles + per-bullet tags | FIX | P1 | pending | v1.0.9 | C-6 | blueprints/applications.py:898-903,913,916,965 |
| F-doc-01 | docs-wiki | PRODUCT_SHAPE claims app.py "6,290-LOC / 75-route" — false at HEAD (241 ln, ~0 routes) | FIX | P1 | pending | v1.0.9 | D-5 | PRODUCT_SHAPE.md:720 vs app.py (241 lines, 2 decorator hits) |
| F-doc-07 | docs-wiki | Wiki 119 commits + 337 files behind; blueprint split unrecorded | FIX | P1 | pending | 8.6 /wiki-ingest (scheduled) | D-5 | .last_ingest_sha 3561657; route-surface.md:13 "93 routes" vs 101 actual |
| F-doc-10 | docs-wiki | D-5 cite-don't-restate discipline HOLDING across the drift (47 sources → 1 page) | KEEP | P1 | pending | 8.6 /wiki-ingest | D-5 | wiki/log.md:322-331; SCHEMA.md:33-48 |
| F-tci-01 | tests-ci | No fast test lane; 4.9% of tests consume ~95% of the 309s suite; CONTRIBUTING double-runs ux | FIX | P1 | pending | new-branch: docs/fast-test-lane | - | pyproject:285-297 (no addopts); CONTRIBUTING.md:88-89; measured 0.46s vs 18.3s |
| F-tci-04 | tests-ci | No CI concurrency group — force-pushes run stale matrix jobs to completion | FIX | P1 | pending | v1.1.0-gate | - | ci.yml:1-67 (no concurrency block) |
| F-tci-05 | tests-ci | Python 3.10 floor untested: requires-python >=3.10, matrix 3.11-3.13 | FIX | P1 | pending | v1.1.0-gate | E-2 | pyproject:11,18-21 vs ci.yml:19 |
| F-adx-03 | process-dx | plugin.json version 1.0.6 stale vs pyproject 1.0.7 and v1.0.8-era tree | FIX | P2 | - | v1.0.9 | C-0 | .claude-plugin/plugin.json:4 vs pyproject.toml:7 |
| F-adx-04 | process-dx | settings.local.json: ~9 dead pre-rename path entries + 6 one-shot debug payloads | DEBUFF | P2 | - | new-branch: chore/prune-settings-local @ v1.0.9 | C-1 | settings.local.json:24-29,48-53 (stale), :8-11,38-40 (one-off) |
| F-adx-05 | process-dx | Subagent model pins mix dated snapshots (Haiku) vs undated aliases (Sonnet) | FIX | P2 | - | v1.0.9 | D-4 | agents/eval-judge.md:4 vs agents/git-flow.md:4 |
| F-adx-08 | process-dx | CLAUDE.local.md: dead /c/Dev/callback path + already-landed hook-migration note | FIX | P2 | - | new-branch: chore/claude-local-refresh @ v1.1.0-gate | C-1 | CLAUDE.local.md:12,27 vs actual tree |
| F-adx-10 | process-dx | Carry-forward ledger head-note = unbounded branch-by-branch history narrative | FIX | P2 | - | new-branch: docs/ledger-headnote-trim @ v1.1.0-gate | W-1, D-5 | RELEASE_CHECKLIST.md:490 (~500+ words of chronology) |
| F-run-04 | runtime | Sonnet 91.3% of spend; Haiku call kinds 0 errors across 2,118 calls | BOOST | P2 | - | v1.1.0-gate | P-9, P-6 | llm_calls.jsonl cost-by-model; error rows 79,241,242,375,920 |
| F-run-05 | runtime | 28.3% of telemetry still on 2026-05-24.4 baseline (eval anchoring vs stale paths) | KEEP | P2 | - | v1.1.0-gate | D-4, W-1 | llm_calls.jsonl Counter(prompt_version) |
| F-run-07 | runtime | 9 of 11 system-prompt overrides pay undocumented cache miss; AGENTS.md names 2 | FIX | P2 | - | v1.0.9 | D-4, D-5 | analyzer.py 12 system_prompt= call sites vs AGENTS.md LLM-prompts section |
| F-run-08 | runtime | style.css ~780-line duplicate "restyle" cascade layer restates 7+ selectors | FIX | P2 | - | v1.0.9 | D-1 | style.css:157-300 vs :3019-3789 |
| F-run-09 | runtime | analyzer.py 3,874 LOC: clean split seams (models/prompts/client) stay merged | WATCH | P2 | - | v1.0.9 | D-1 | analyzer.py:150-360,1081-1424, prompts 442-3778 |
| F-doc-02 | docs-wiki | Ledger header "Open count: 7" vs 8 actual open items | WATCH | P2 | - | v1.0.9 (fixed at this review's close-out as ledger maintenance) | W-1, D-5 | RELEASE_CHECKLIST.md:490 vs 8 bullets at :492-811 |
| F-doc-03 | docs-wiki | app-blueprints-design.md banners "APPROVED design" though all 8 seams shipped | FIX | P2 | - | v1.0.9 | D-5 | app-blueprints-design.md:3 vs RELEASE_CHECKLIST.md:93-97 |
| F-doc-04 | docs-wiki | CHANGELOG oldest 5 releases (~585 ln, 14%) are write-only — archive split | FIX | P2 | - | v1.0.9 | D-5 | CHANGELOG.md:3502-4087 |
| F-doc-05 | docs-wiki | Corpus/pipeline mechanics restated as paragraphs in 3 of 4 top docs | FIX | P2 | - | v1.0.9 | D-5 | PRODUCT_SHAPE.md:73 vs README pointer style (:144) |
| F-doc-08 | docs-wiki | wiki-freshness hook escalates every commit (337 files vs 10-file threshold) | WATCH | P2 | - | with 8.6 ingest | - | wiki-freshness-reminder.sh:57; 337 non-wiki files since pin |
| F-doc-09 | docs-wiki | DOC-STATUS convention: 16 markers placed, zero enforcement gate | FIX | P2 | - | v1.0.9 CI merge-gate item #4 (scheduled) | D-5 | documentation-architecture.md:105-119,162; git grep = 16 |
| F-doc-11 | docs-wiki | Symbol-keyed cites survive drift; bare line numbers don't — enforce universally | BOOST | P2 | - | 8.6 /wiki-ingest lint pass | - | wiki/log.md:345-349; SCHEMA.md:68-69 |
| F-tci-02 | tests-ci | _imported_roots() AST walker triplicated across 3 boundary-gate tests | FIX | P2 | - | v1.0.9 | D-5 | test_construction_boundary.py:40-51; test_web_infra_is_leaf.py:21-31; test_recall_boundary.py:50-65 |
| F-tci-03 | tests-ci | UX tier repeats app reload + SQLite + server + context on all 67 tests | WATCH | P2 | - | v1.1.0-gate | - | tests/ux/conftest.py:22-101 (only _browser session-scoped) |
| F-tci-06 | tests-ci | eval-smoke job duplicates quality's pip-install boilerplate | FIX | P2 | - | post-v1.1.0 | - | ci.yml:24-28 vs :52-56 |
| F-tci-07 | tests-ci | fail-fast disabled in quality matrix (see-all-failures trade-off) | WATCH | P2 | - | post-v1.1.0 | - | ci.yml:16-17 |
| F-tci-08 | tests-ci | arm64 docker rides QEMU with no measurement or deferral rationale | WATCH | P2 | - | post-v1.1.0 | - | docker.yml:28-30,53 |
| F-tci-09 | tests-ci | No pip-audit/dependency scan in CI (~10-30s to add) | BOOST | P2 | - | v1.1.0-gate — COORDINATE with PX-26 | D-1 | ci.yml (absent); pyproject:64-73 |
| F-adx-09 | process-dx | AGENTS.md restates 8-file deterministic-boundary list verbatim twice | FIX | P3 | - | rides chore/claude-md-catalog-trim | D-5, C-6 | AGENTS.md:50 vs :166 |
| F-adx-11 | process-dx | No unified quality-gate script (triad restated in AGENTS.md + CI) | FIX | P3 | - | new-branch: chore/quality-gate-script @ v1.1.0-gate | E-2 | AGENTS.md:95; ci.yml:36,39,42 |
| F-run-10 | runtime | Application composite index omits is_active (default list-query predicate) | FIX | P3 | - | v1.0.9 | - | db/models.py:774 vs applications.py:148-155 |
| F-doc-06 | docs-wiki | kit-adoption-design.md complete but no top-of-file closure banner | WATCH | P3 | - | v1.0.9 | D-5 | kit-adoption-design.md:155,499 |
| F-tci-10 | tests-ci | Release artifacts: no retention policy (90-day default) | WATCH | P3 | - | post-v1.1.0 | - | release.yml:53-56 |
| F-tci-11 | tests-ci | No Windows CI runner — KEEP Linux-only pre-public, revisit on user feedback | KEEP | P3 | - | post-public | - | ci.yml:15; window-8.5 EV-3 note |

**Counts:** 43 findings — 1×P0, 13×P1, 23×P2, 6×P3. Dispositions: 26 FIX,
10 WATCH, 3 KEEP, 3 BOOST, 1 DEBUFF. Simplification (delete/merge/shrink)
flagged on 14 rows.
