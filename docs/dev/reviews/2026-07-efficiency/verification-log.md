---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Verification log — 2026-07 efficiency review

> One entry per P0/P1 finding: the refute-framed falsification attempt, the
> counter-evidence found (if any), the verdict, and — for WEAKENED — the
> revised claim that governs the prescription. Verifier verdicts of
> WEAKENED/REFUTED were ratified by the orchestrating (main-loop) reviewer
> against primary evidence before landing here (ratification spot-checks
> noted inline). Three sonnet verifiers worked mixed-area batches of 4–5.

---

## F-adx-02 — hook timeouts vs measured runtime — **CONFIRMED**

- **Falsification attempt:** re-measured both hooks warm (byte-correct JSON, 1 warmup + 5–8 timed runs): block-secrets.sh 2.14–3.40s (warm runs still spike near the cited 3.481s — not a cold-start artifact); validate-context.sh 1.97–3.33s. Verified per-hook `timeout: 5` wiring.
- **Counter-evidence:** none against the substance. One artifact defect found and fixed: the register's evidence cite pointed at the wrong settings.json lines — actual timeout wiring at `.claude/settings.json:43-45,48-50`.
- **Note:** harness fail-open/fail-closed behavior on timeout is undocumented; the finding's hedge ("depending on the harness's timeout default") stands as written.

## F-run-02 — generate cache-miss 38% — **WEAKENED**

- **Falsification attempt:** recomputed from logs/llm_calls.jsonl: 92/249 = 36.9% (not 38%); last-30-day window = 0 misses (verifier: 31/31 hits; ratifier re-check: 37/37 from 2026-06-02) — the cache is currently perfectly healthy. The "step function at 2026-06-01.3" is also false: 2026-05-06.2/.3, 2026-05-22.2, 2026-05-30.1, 2026-06-01.1 already hit 100%. First-call cache-warming does NOT explain the historical misses (91 of 92 misses were non-first calls) — they were a real coherence problem, since resolved.
- **Revised claim (governs):** historical miss rate ~37% is a RESOLVED legacy artifact; every generate call in the last 4+ weeks hits cache at 100%. WATCH disposition defensible for monitoring only; not a current-state concern.

## F-doc-07 — wiki 119 commits behind; route counts — **WEAKENED**

- **Falsification attempt:** re-verified every number. Drift confirmed exactly (119 commits; 337 non-wiki files). Route correction was itself wrong: app.py has **0** real @app.route decorators (both grep hits are comments; ratifier re-count confirms), blueprints/ = 99 (incl. corpus/ subpackage), dashboard/routes.py = 1 → true total **100**, not 101.
- **Revised claim (governs):** drift figures stand; the staleness is MORE dramatic than stated — route-surface.md's "93 @app.route in app.py" is wrong in kind, not just count (routes collapsed to zero in app.py and live entirely in blueprints). Mitigation note: the 8.6a content pass kept 7 user-facing pages fresh post-checkpoint; staleness concentrates in dev/code-grounded pages.

## F-tci-05 — Python 3.10 floor untested — **CONFIRMED (escalated)**

- **Falsification attempt:** confirmed pyproject floor + classifier + matrix gap exactly. Hunted for mitigation (no tox/pre-commit; ruff target-version=py310 is syntax-only). Found the claim is UNDERSTATED: `tests/test_docstring_coverage_gate.py:47` does an unconditional `import tomllib` (stdlib 3.11+ only, no fallback, module scope) — pytest collection itself fails on a real 3.10 interpreter (ratifier re-read confirms).
- **Escalation (governs):** the floor is not merely unverified — it is actively false. Either add 3.10 to the matrix AND fix the tomllib import, or (cheaper, truer) raise requires-python to >=3.11 and drop the 3.10 classifier.

## F-adx-06 — CLAUDE.md catalogs duplicate auto-injection — **WEAKENED**

- **Falsification attempt:** confirmed the stats exactly (90/190 lines, 4,399 bytes). Diffed all 21 catalog entries against commands/agents frontmatter: ~19/21 are compressed paraphrases (some even DROP safety guarantees the frontmatter carries); 2 entries (compliance-witness command + agent) carry facts absent from frontmatter (cap default 12, log path, FLAG/WATCH/AFFIRM taxonomy, tool-grant-is-enforcement rationale). Auto-injection is real but has a documented gap window (fresh clone before marketplace-trust + reload) where the catalog is the only in-repo discoverability.
- **Revised claim (governs):** partial trim, not wholesale removal — compress to a compact pointer list, fold the 2–3 unique facts into the frontmatter itself, keep a one-line fallback note for the plugin-not-yet-loaded window.

## F-adx-07 — 16 memory files superseded — **WEAKENED**

- **Falsification attempt:** verifier read 5–6 of the named memory files and diffed against RELEASE_CHECKLIST narrative. Count/size confirmed (16 files, ~79KB). But ≥3 files (seam-move-mechanics, kit-phase2-mypy-strict, kit-phase2-ruff-d) carry unique reusable recipes — exact stub-rebinding rules, verify commands, drain commands — reproduced nowhere in RELEASE_CHECKLIST (grep: 0 hits).
- **Revised claim (governs):** selective consolidation — fold the reusable recipes into a durable docs/dev/ reference (or keep those memories), delete/merge only the genuinely redundant completion logs. Not a blanket delete-as-superseded.

## F-run-06 — Compose route N+1 — **CONFIRMED**

- **Falsification attempt:** read the route fully + grepped db/models.py for any eager-load configuration: zero `lazy='selectin'`/`joinedload` anywhere — nothing neutralizes the pattern. Full accounting found an additional uncited per-title tag_links load (~:978): the true query count is slightly HIGHER than the O(3E+B) cited. Minor cite imprecision (:899-906 vs :898-903), immaterial.
- **Counter-evidence:** none.

## F-doc-10 — D-5 discipline holding (KEEP) — **WEAKENED**

- **Falsification attempt:** the cited 47-sources→1-page evidence (log.md, 2026-06-16) PREDATES the 8.3a-h blueprint split (merged 2026-06-21/22) — the largest chunk of the ~354-file drift. The post-split re-anchor is explicitly logged as owed-not-done, and route-surface.md currently asserts a materially false architecture fact with ~20 dead app.py: cites.
- **Revised claim (governs):** the design principle is sound and pages authored post-split follow it; but the empirical "holding" affirmation is unverified post-split and contradicted by at least one page. Re-affirm only after the 8.6 /wiki-ingest re-anchor.

## F-tci-01 — fast test lane (~20× claim) — **WEAKENED**

- **Falsification attempt:** verifier confirmed no fast lane is documented anywhere and CONTRIBUTING.md:88-89 does double-run pytest + pytest -m ux. It then MEASURED the proposed lane: `-m "not slow and not ux"` = 1,378 tests in 294.57s — nowhere near the projected <15s. Slow-tier count corrected: 75 (71 ux + 4 slow), not ~71.
- **Ratifier confound note:** the 294.57s measurement ran while two other verifiers plus a full pytest gate were loading the same machine (the same gate that measures 308.9s idle measured 570.8s under that load). The verifier's "~5% saving" compares a loaded fast-lane run against an idle full-run baseline — the true idle fast-lane time is re-measured before this review seals and recorded here: **see addendum below**.
- **Revised claim (governs):** documentation gap and double-run confirmed; the <15s/~20× projection is wrong — the ~1,378 non-slow tests carry substantial Flask/SQLite per-test fixture cost of their own. The speedup opportunity is real but smaller, and the higher-leverage target is per-test fixture scoping (see F-tci-03).

## F-adx-01 — 5 serial hooks ~10.9s per Edit/Write (P0) — **WEAKENED**

- **Falsification attempt:** verifier confirmed the matcher scope (all 5 fire on every Edit/Write, no path filters) and re-timed every hook cold (1.8–4.0s each — same order as claimed; require-feature-branch may be UNDER-measured since the escape hatch skipped its git walk). Then checked the harness's documented execution model instead of assuming.
- **Counter-evidence:** Claude Code's official Hook Execution Model: "All matching hooks run in parallel" — five entries under one matcher is the mechanism FOR concurrency, not a serial pipeline.
- **Revised claim (governs):** per-Edit/Write wall tax ≈ the slowest hook (~3.5–4s, block-secrets) + dispatch, not a 10.9s sum — a ~3× overstatement. The process-spawn tax (each hook spawning bash + 1–4 python3 children re-parsing the same JSON) and the consolidation opportunity fully survive; effective leverage P1, not P0. Register row keeps its place per convention; prescriptions band on the revised claim.

## F-run-01 — split analyze adoption 40% — **REFUTED → row dropped**

- **Falsification attempt:** verifier read analyze() in full and computed the temporal distribution of legacy vs split telemetry.
- **Counter-evidence (ratifier-confirmed):** `analyzer.py:1425` docstring + body: the two-pass split is UNCONDITIONAL, single call site (blueprints/analysis.py:368), landed 2026-06-01 (commit 3cbcc72). Legacy `analyze` rows: n=195, LAST at 2026-06-01T16:37Z — zero after the feature landed. Split pairs run 2026-05-26 (A/B candidates) → 2026-07-02. The "40% adoption" compared two time-disjoint populations.
- **Disposition:** the claimed live adoption gap does not exist; savings were realized a month before the review. Row removed from the register; the F-run-01 id is retired (not reused). B1's underlying aggregation remains valid as data; its adoption inference was the error.

## F-doc-01 — PRODUCT_SHAPE stale app.py claim — **CONFIRMED**

- **Falsification attempt:** verifier hunted for planning-tense framing or completion markers that would redeem the sentence; checked git blame (line last touched 2026-06-08, BEFORE the split completed 2026-06-22) and found the doc was edited after completion (2026-07-02) for another section without reconciling this one.
- **Compounding evidence:** the doc also cites `app.py:1403-1423` twice (PRODUCT_SHAPE.md:186, 481) — a line range that no longer exists in the 241-line file. No as-of/status markers distinguish planned vs completed workstreams anywhere in the doc.

## F-tci-04 — no CI concurrency group — **WEAKENED**

- **Falsification attempt:** verifier read all 3 workflows (no `concurrency:` anywhere — premise confirmed), then tested the waste scenario against the repo's actual workflow: ci.yml triggers only on push-to-main + PRs-to-main; CONTRIBUTING/AGENTS document a local merge-then-push model; zero GitHub-style PR-merge commits across 191 merges; no remote configured in this clone.
- **Revised claim (governs):** the missing concurrency group is a real but LATENT gap — the routine force-push-during-PR-iteration waste scenario is not this project's demonstrated pattern. Cheap to add; effective leverage P2.

## F-run-03 — analyze p95 126s vs 67s target — **WEAKENED**

- **Falsification attempt:** verifier recomputed latency for the CURRENT architecture (split pairs summed per run_id, n=78): p50 = 69.7s, p95 = **84.6s** — the 126.2s figure belongs to the defunct pre-split population (ended 2026-06-01). Also: the 67s "target" is a synthetic-fixture-only measurement that PERFORMANCE_HISTORY itself caveats as unvalidated on real corpus; and the finding's own "25/195 (12.8%) exceed 60s" was arithmetically impossible given its p50 of 90.9s (real legacy count: ~95% exceeded 60s).
- **Revised claim (governs):** current split-era p95 ≈ 84.6s vs an unvalidated synthetic 67s reference; 68% of split-era calls exceed it. A real but much smaller gap than 126s-vs-67s implied; the actionable item is a real-corpus latency baseline, not alarm.

---

### Addendum — idle fast-lane re-measurement (F-tci-01)

Re-measured at seal on an otherwise-idle machine (all background agents
complete), same invocation the verifier used:

| Run | Tests | Wall time |
|---|---|---|
| Full suite (baseline, idle, stage-1 gate) | 1,453 | 308.9s |
| `-m "not slow and not ux"` (idle) | 1,378 | **163.1s** |
| `-m "slow or ux"` (idle) | 75 | 248.0s |

Resolution: the finder's ~20×/<15s projection AND the verifier's ~5% counter
were both wrong — the verifier's 294.57s run was inflated ~1.8× by three
concurrent verification agents plus a full pytest gate on the same machine
(the same gate that measures 308.9s idle measured 570.8s under that load).
**A documented fast lane cuts the inner dev loop roughly in half (309s →
163s).** The 163s floor ≈ per-test Flask/SQLite fixture overhead across
1,378 tests (~0.12s/test) — confirming fixture scoping (F-tci-03 / PX-44) as
the follow-on target, and confirming the slow tier (75 tests, 248s alone,
~3.3s/test) still deserves its marker split. Note the tiers sum to more than
the full run (411s vs 309s) because separate invocations pay collection +
browser setup twice.

Method lesson recorded for future reviews: never compare a measurement taken
under concurrent agent load against an idle baseline — serialize perf
measurements or re-measure idle before sealing a number.
