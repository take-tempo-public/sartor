# callback. — Release arc: v1.0.2 → v1.1.0

> **Written:** 2026-05-28 planning session
> **Status:** approved — executing phase by phase
> **Authoritative for:** branch sequence, architectural decisions, acceptance criteria
> **Do not edit without user sign-off** — changes here affect multiple future sessions

---

## Version map

| Version | Theme | Publicly visible? | Notes |
|---|---|---|---|
| v1.0.1 | Solid app | No | **Tagged 2026-05-28 at commit `49f2ac9`** |
| v1.0.2 | Eval apparatus | No | **Tagged 2026-05-30 at commit `2398f4e`** |
| v1.0.3 | R1 Phase 2 | No | Analyze quality recovery (✓ context_probe + typed hidden_qualities) **then** the two-pass split for speed (≤72s) without giving quality back. **Tagged 2026-06-02 at commit `59b6d9c`** |
| v1.0.4 | Eval tuning loop | No | Real-data, human-in-the-loop, model-assisted prompt improvement; internal/dev tooling. **Tagged 2026-06-02 at commit `072e290`** |
| v1.0.5 | UI/UX redesign | No (internal until v1.1.0) | Wizard redesign + WYSIWYG + diagnostics/tuning console & annotation tab; establishes the design system. **Tagged 2026-06-07** — all seven §Phase 4 tag criteria met; gate green incl. `pytest -m ux` |
| v1.0.6 | Walkthrough polish + knowledge substrate | No (internal until v1.1.0) | E2E-walkthrough-driven UX polish (Sprints 6.1–6.5) + the **WS-4 LLM-wiki substrate** (lands before the 6.5 education sweep). **Not yet tagged** — opens with a fresh end-to-end walkthrough. See **Phase 4.5**. |
| v1.0.7 | Pre-public hardening | No (internal until v1.1.0) | Sprint PV: live grounding shakedown → calibration → cover-letter opener tuning → type-annotation scan (= **WS-2 increment 1**). **Not yet tagged.** See **Phase 4.7**. |
| v1.1.0 | Public release | **Yes** | **Tag owned by the user** — applied when the product is judged showcase-ready; GitHub push is part of this event |

Public release = the **v1.1.0 tag, applied by the user** when the product is judged complete and polished enough to showcase (portfolio + open-source + personal tool). GitHub push is part of that release event. There is no external deadline — completeness and polish gate the tag, not a clock.

---

## Key decisions (load-bearing for all phases)

1. **Eval before R1.** All 25 items from `C:\Users\iam\.claude\research\resume-eval-2026-05\followup.md` checklist must be checked before any prompt engineering work starts.
2. **Pydantic migration.** 6 `*_REQUIRED_KEYS` frozensets in `analyzer.py` → Pydantic models. `ContextSet` TypedDicts in `hardening.py` stay as TypedDicts — internal contracts, not LLM boundary.
3. **Promptfoo.** Wrap 3 anchor fixtures in Promptfoo YAML for CI diff table on prompt-change PRs.
4. **MiniCheck + DeBERTa.** Belt+suspenders offline grounding scorers; eval-only, never in hot path. MiniCheck license documented in `CONTRIBUTING.md`.
5. **WYSIWYG Option 1.** Post-generate: run `md_to_json_resume()` on `last_generated_resume`, store as `last_generated_json_resume` in context; preview route serves this. No prompt change, no PROMPT_VERSION bump.
6. **Applications tracker.** Extend `Application` table: add `sent_at`, `outcome_at`, `notes`; expand `status` CHECK to include `rejected | offer | accepted | no_response`; rename `closed` → `withdrawn`. No separate table.
7. **Sequential streams.** One branch at a time per `docs/dev/AGENT_FAILURE_PATTERNS.md` discipline.
8. **Eval tuning loop (v1.0.4).** Real-data, human-in-the-loop, model-assisted prompt improvement, gated by the Phase 1 grounding scorers + the eval suite. Engine + a headless annotation contract land in v1.0.4; the polished annotation UI lands in v1.0.5 on the new design system — **no throwaway**, because the annotation file format is the durable contract the UI later wraps. Approved 2026-06-01.
9. **v1.1.0 tag is user-owned.** The public release is tagged by the user when the product is judged showcase-ready. No external deadline — completeness and polish gate the tag, not a clock.

---

## Phase 1 — Eval apparatus (v1.0.2)

**Blocked by:** v1.0.1 tag ✅ done.
**Blocks:** Phase 2 (R1).

All changes live in `evals/`, `analyzer.py` (Pydantic only), `db/` (tracker), `dashboard/`, and `docs/`. No user-facing pipeline changes.

### Branch sequence

#### `eval/pydantic-response-models` ← execute first

Replace 6 frozenset `*_REQUIRED_KEYS` checks in `analyzer.py` with Pydantic v2 models:

| Model | Replaces |
|---|---|
| `AnalyzeResponse` | `ANALYZE_REQUIRED_KEYS` |
| `GenerateResponse` | `GENERATE_REQUIRED_KEYS` |
| `GenerateNoCLResponse` | `GENERATE_NO_CL_REQUIRED_KEYS` |
| `ClarifyResponse` | `CLARIFY_REQUIRED_KEYS` |
| `RecommendResponse` | `RECOMMEND_REQUIRED_KEYS` |
| `RecommendSummariesResponse` | `RECOMMEND_SUMMARIES_REQUIRED_KEYS` |
| `GenerateCorpusResponse` / `GenerateCorpusNoCLResponse` | corpus variants |

`_parse_or_retry`: replace `missing = required_keys - data.keys()` with `ResponseModel.model_validate(data)`; `ValidationError` → append error text to retry prompt.

Add `pydantic>=2.0` to `pyproject.toml` + CHANGELOG entry.

**Acceptance:** 632 tests green; mypy clean; eval smoke (`--subset smoke`) passes with no rubric drops > 0.5 vs `TUNING_LOG.md` v1.0.1 baseline.

---

#### `eval/baseline-v1-0-2` ← after Pydantic merged

Upgrade `evals/results/baseline_v1.json` schema_version 2 → 3:

```json
{
  "schema_version": 3,
  "baseline_id": "v1.0.2_YYYY-MM-DD",
  "prompt_version": "2026-05-24.4",
  "model_snapshots": {"sonnet": "claude-sonnet-4-6", "haiku_judge": "claude-haiku-4-5-20251001"},
  "fixture_set_hash": "<sha256 of jd.txt+resume.md+expected.json>",
  "runs_aggregated": 5,
  "source_runs": [...],
  "fixtures": {
    "pm-senior": {
      "ats_format": {"mean": 4.60, "stdev": 0.20, "n": 5, "min": 4.4, "max": 4.8}
    }
  },
  "deterministic_metrics_baseline": {},
  "performance_baseline": {}
}
```

Update `_load_baseline_scores` in `runner.py` to read schema_version 3. Run 5 back-to-back synthetic runs to populate it.

**Green-light criteria (all must pass before next branch):**
- Every (fixture × rubric) mean ≥ 4.0
- No (fixture × rubric) stdev > 0.6
- Cost variance < 15% of mean
- Zero `judge_error` records across 90 baseline gradings
- `grounding_overlap_ratio` ≥ 0.25 per fixture

---

#### `eval/anchor-and-pr-gate` ← after baseline _(consolidated from anchor-exploration-split + pr-gate)_

**Anchor structure:**
- `evals/anchors/anchor-v1/`: copy of 3 synthetic fixtures + rubrics + `manifest.json` (immutable, versioned)
- `evals/exploration/`: initially empty; adversarial/real fixtures go here with `README.md` describing promotion rule
- JSONL schema_version 3 additions per record: `anchor_version`, `suite` (anchor|exploration), `fixture_hash`, `rubric_version`, `model_snapshots`, `baseline_comparison`, `phase_latencies_ms`
- `runner.py`: add `--suite anchor` (default) vs `--suite exploration`
- Promotion rule in TUNING_LOG.md: 3 stable runs + discriminating across ≥2 PROMPT_VERSIONs + documented failure mode

**PR gate:**
- `.github/pull_request_template.md`: require eval evidence on `analyzer.py`/`evals/` prompt PRs (n=3 runs; mean ± stdev table; regression > 0.5 = blocked; latency p50 regression > 20% = blocked; cost regression > 20% = blocked)
- `promptfooconfig.yaml` at repo root: 3 anchor fixtures wrapped in Promptfoo YAML; CI Markdown diff table
- `runner.py`: exit code 2 on regression (currently just a log line)
- Dry-run the gate with a no-op test PR before moving on

**Validation:** one `--suite anchor --subset smoke` run (~$0.10). Anchor and gate are tightly coupled — anchor structure is what the gate wraps; no benefit to separate sessions.

---

#### `eval/callback-metrics` ← after PR gate confirmed

- `evals/rubrics/callback_likelihood.md`: recruiter-persona Haiku judge (200-person company, 80 résumés, 7-second skim, 1–5 scale)
- `hardening.py _post_generation_metrics()`: 3 new deterministic metrics:
  - `top_third_density`: ratio of first 3 bullets of first job that contain JD's top 3 essentials
  - `quantification_rate`: % of bullets with number / % / $ / scale word
  - `distinctiveness`: lightweight Haiku call at eval time only
- `evals/callback_weights.json`: `keyword_coverage 2×, callback_likelihood 3×, ats_format 1×, tone 1×, grounding 1×, clarification_quality 0.5×`
- `eval_composite` written to JSONL records at eval time

---

#### `eval/applications-tracker` ← independent (can slot here or earlier)

- Alembic migration: add `sent_at TEXT`, `outcome_at TEXT`, `notes TEXT` to `application`
- Expand `status` CHECK: add `offer | accepted | rejected | no_response`; rename `closed` → `withdrawn` (backfill)
- `db/models.py`: update `Application` model
- Minimal UI: "Got callback" / "Got rejection" / "No response" outcome buttons in Prior Applications panel; auto-set `sent_at` when status → `submitted`

---

#### `feat/tracker-notes-and-timestamps` ← after applications-tracker ✓ done

- `PUT /api/applications/<id>/notes` endpoint; `GET /api/applications/<id>` returns `notes`, `sent_at`, `outcome_at`
- Application detail modal replaces toast: title, status chip, timestamps, notes textarea (saves on blur)
- Card timestamp display: `submitted`/`no_response` → "Sent · X ago"; `interview`/`rejected`/`withdrawn` → "Outcome · X ago"
- `submitted` cards display chip as "NO RESPONSE"; outcome buttons: "Got Interview" / "Got Rejection" / "Withdrew"
- `withdrawn` now stamps `outcome_at`

**Status semantics agreed 2026-05-29** (canonical for all future tracker work):

| DB status  | Card label  | Timestamp       |
|------------|-------------|-----------------|
| draft      | DRAFT       | updated_at      |
| submitted  | NO RESPONSE | Sent · X ago    |
| interview  | INTERVIEW   | Outcome · X ago |
| rejected   | REJECTED    | Outcome · X ago |
| withdrawn  | WITHDRAWN   | Outcome · X ago |

`sent_at IS NOT NULL` = was ever submitted. `outcome_at IS NOT NULL` = has a resolved outcome.

---

#### `chore/tracker-status-schema-cleanup` ← after feat/tracker-notes-and-timestamps

Schema correction to align the DB with the canonical status semantics above.
`offer` and `accepted` were added in an early draft but are out of scope for this app.
`no_response` is redundant — `submitted` IS the "no response" state.

- **Migration 0007:**
  - Backfill `no_response` → `submitted`; clear their `outcome_at` (wrongly stamped)
  - Delete `offer` and `accepted` records (pre-release, no real data)
  - Update `CHECK` constraint: `status IN ('draft','submitted','interview','rejected','withdrawn')`
- **`app.py` `update_application_status`:**
  - Valid set: `{draft, submitted, interview, rejected, withdrawn}`
  - `outcome_at` stamps on: `interview`, `rejected`, `withdrawn` only
- **Cleanup:** remove `status-no_response`, `status-offer`, `status-accepted` CSS classes;
  remove those three values from all JS and Python references

---

#### `eval/grounding-signals` ← independent

- DeBERTa-v3-base-mnli-fever-anli (Apache 2.0): NLI entailment per bullet vs (resume + clarifications) → `nli_entailment_score`, `nli_contradiction_flag`
- MiniCheck-FT5 (eval-only): `minicheck_grounding_score` per bullet
- Both run only with `--grounding-signals` flag; MiniCheck license in `CONTRIBUTING.md`

---

#### `eval/pareto-dashboard` ← after callback-metrics (needs eval_composite)

New Pareto frontier panel at top of `/_dashboard`:
- X = wall-clock latency (log scale); Y = eval_composite (0–5)
- Dots: color = PROMPT_VERSION; size = cost; hover = full breakdown
- Dashed polyline connecting successive baselines chronologically
- Summary: "Most recent change (v → v): Δ composite, Δ latency, Δ cost. [Pareto-improving / On frontier / Dominated]"
- Secondary: p50/p90 latency trend + cost trend over time

---

### v1.0.2 tag criteria

- All 25 `followup.md` checklist items checked
- schema_version 3 baseline live; anchor/exploration split live; Promptfoo YAML running; PR gate confirmed on dry-run; callback rubric + metrics live; applications tracker shipped; Pareto frontier visible
- `ruff + mypy + pytest` green

---

## Phase 2 — R1 Phase 2 (v1.0.3)

**Blocked until v1.0.2 tagged.**

**Start point:** branch each R1 sub-branch from **main** — the Pydantic migration and other work these branches need landed after `r1-attempted-2026-05-26` was cut. `r1-attempted-2026-05-26` is a **read-only reference** for prompt language only (`context_probe` wording, `hidden_qualities` redefinition in `EXTRACTION_SYSTEM_PROMPT`), preserved in `evals/TUNING_LOG.md` (2026-05-26 entries). *(Corrected 2026-05-30; was: "start from `r1-attempted-2026-05-26`, do NOT start from main" — that branch predates the Pydantic migration the R1 work extends.)*

**Budget per hypothesis:** 3 prompt-tune iterations via `/prompt-tune`. After 3 without clearing the gate, document as "rejected for now" in TUNING_LOG.md.

**Between iterations:** invoke `headhunter` agent to diagnose which recruiting-domain dimension regressed.

### Branches

> **R1 = quality first, then speed.** The two diagnosed root causes of the
> original split's `clarification_quality` regression (2.1) were: context_probe
> never emitted, and `hidden_qualities` shape mismatch (`docs/dev/perf/R1_BENCHMARK_2026-05-26.md`).
> Both are now fixed on `main` (the two ✓ branches below). With those guardrails
> in place, `r1/analyze-split-retry` re-introduces the two-pass split to land the
> **speed** half — gated so it cannot give the recovered quality back. The
> v1.0.3 "≤72s combined" perf criterion is **not** to be relaxed.

**`r1/structural-context-probe`** ✓ DONE (merged `9386c33`, PROMPT_VERSION `2026-05-30.1`)
- If `hidden_qualities` non-empty, at least one `context_probe` required in clarify output; enforced at parse time by `ClarifyResponse` Pydantic model (missing → retry)
- PROMPT_VERSION bump in same commit
- Target: `pm-senior / clarification_quality` ≥ 4.0 (was 2.1 on R1.2; 3.73 mean at v1.0.1 baseline) — **achieved: 4.20 across all fixtures**
- n=3 eval runs on branch before any merge request

**`r1/hidden-qualities-schema`** ✓ DONE (merged `b216fd3`, PROMPT_VERSION `2026-06-01.1`)
- Add `category` sub-field to each `hidden_qualities` item: `{"category": "operating_context"|"scope_of_ownership"|"stakeholder_gravity"|"resilience", "signal": "..."}`
- `HiddenQualityItem` Pydantic model enforces category enum
- PROMPT_VERSION bump — **anchor n=3 PASS, max drop −0.17 vs the 2026-05-30 floor**

**`r1/analyze-split-retry`** ← **NEXT** (the speed half of R1; runs before `r1/clarify-model-trial`)
- Re-introduce the two-pass analyze **on `main`**: `analyze_extraction` (Haiku 4.5 — structured lists incl. the now-typed `hidden_qualities` `HiddenQualityItem` shape) + `analyze_synthesis` (Sonnet 4.6 — `comparison` / `suggestions` / `overall_strategy`). `analyze()` stays a thin orchestrator merging into the existing `AnalyzeResponse` contract; `analyze_streaming` keeps the `phase` sentinel.
- **Rebuild on `main` — do NOT cherry-pick `r1-attempted-2026-05-26`** (it predates the Pydantic migration, the `context_probe` enforcement, and the typed `hidden_qualities`). The extraction pass MUST emit the typed `HiddenQualityItem`, and the parse-time `context_probe` enforcement MUST stay intact — those two merged branches are exactly the guardrails that prevent the original 2.1 regression.
- Carry forward R1's two phantom-key deletions (`ats_improvements`, `ideal_resume_profile`) only after re-auditing they're still unconsumed.
- PROMPT_VERSION bump in the same commit.
- **Dual gate (n=3 `--suite anchor` before any merge request):**
  - **Speed:** `analyze` p50 **≤ 72s combined** (extraction + synthesis). Tight — synthesis was 61s p50 on R1; keep the synthesis prompt lean.
  - **Quality held:** `clarification_quality` no drop > 0.5 vs the `2026-06-01 — r1/hidden-qualities-schema` TUNING_LOG floor; `pm-senior / clarification_quality` ≥ 4.0; all other rubrics within 1 stdev of the v1.0.2 baseline; `tone` + `grounding` flat (no hidden_qualities leak into generate).
  - 3-iteration `/prompt-tune` budget per hypothesis; `headhunter` agent between iterations. If 3 iterations don't clear the **dual** gate, document "rejected for now" in TUNING_LOG and **escalate to the user** — this branch delivers the v1.0.3 "≤72s combined" criterion, which is not to be relaxed.

**`r1/clarify-model-trial`** ← after `r1/analyze-split-retry` (evaluated against the post-split pipeline)
- Side-by-side eval: Sonnet vs Haiku for `clarify()` only
- Haiku saves ~$0.03/application if quality holds (no `clarification_quality` drop > 0.5 vs the 2026-06-01 floor; Haiku must still satisfy the parse-time `context_probe` + ≥60%-combined rules — watch the `clarify_retry` rate)

### v1.0.3 tag criteria

- `r1/structural-context-probe` ✓, `r1/hidden-qualities-schema` ✓, and `r1/analyze-split-retry` all merged and passing their gates (`r1/clarify-model-trial` optional — non-tag-gating cost trial)
- `pm-senior / clarification_quality` ≥ 4.0 at the final PROMPT_VERSION
- **Analyze p50 ≤ 72s combined** — delivered by `r1/analyze-split-retry`; this perf bar is not relaxed
- All other rubrics within 1 stdev of v1.0.2 baseline
- `ruff + mypy + pytest` green

> **Note (2026-06-01):** the speed half landed via **`r1/analyze-split-cache-reclaim`**,
> which supersedes `r1/analyze-split-retry` — it contains the full two-pass split AND a
> follow-up that runs synthesis under the shared `SYSTEM_PROMPT` to reclaim the
> analyze→generate prompt cache the dedicated-persona build had broken. Final
> `PROMPT_VERSION 2026-06-01.3`. Results (speed/cost/eval before vs after) are recorded
> in [`docs/dev/perf/R1_PHASE2_RESULTS.md`](perf/R1_PHASE2_RESULTS.md).

### Documentation debt (from R1 Phase 2) — schedule a later doc pass

These are tracked, NOT blockers for the v1.0.3 tag. Fold into the next docs-focused branch
(or the v1.0.5 redesign's doc work):

1. **`docs/architecture.md` + `docs/diagrams/pipeline.mmd` + `docs/diagrams/llm-routing.mmd`** —
   `analyze` is now **two passes** (Haiku `analyze_extraction` → Sonnet `analyze_synthesis`),
   not one Sonnet call. Update the sequence diagram, the LLM-routing diagram (add the Haiku
   extraction node; mark synthesis as the cache writer), and the module/routing prose. *(The
   "analyze and generate share a cached prefix" claim is accurate again post-reclaim — no change
   needed there; only the single-call shape is stale.)*
2. **`generate` cover-letter opener discipline** — the `tone` rubric caught a throat-clearing
   opener ("I am writing to be considered for…") + hedging in 1 of 5 shipped-build runs. This is
   a pre-existing `generate_cover_letter` adherence lapse (independent of the analyze change),
   surfaced during R1 Phase 2 eval. Candidate for a `generate`-tuning pass — natural fit for the
   v1.0.4 eval-tuning loop.

---

## Phase 3 — Eval tuning loop (v1.0.4)

**Blocked until v1.0.3 tagged.** Internal/dev tooling — no user-facing pipeline change. Approved 2026-06-01.

Real-data, human-in-the-loop, model-assisted prompt improvement, verified by the offline grounding scorers from Phase 1. The loop generates ground truth with the **actual product pipeline** (corpus-backed via `build_context_set_from_db`), the user annotates the produced bullets/skills, and the annotations become both a permanent regression fixture and the source material for prompt edits. The loop is fully functional **headless** in this phase (file-based annotation); its polished UI lands in Phase 4 on the new design system — **no throwaway**, because the `annotations.json` format is the durable contract the UI later wraps.

### Branches (sequential)

| Branch | Depends on | Key work |
|---|---|---|
| `eval/prompt-override-primitive` | main | `analyzer.py` reads optional prompt overrides; default path **byte-identical** (cache + PROMPT_VERSION discipline intact); candidate runs log a `candidate:<hash>` version so they never pollute score-over-time; runner `--prompt-overrides` flag. Retrofits `/prompt-tune`. |
| `eval/corpus-seed-export` | independent | Tracked `scripts/export_corpus_seed.py` → gitignored `seed.json` under `evals/fixtures/real/`; write-path guard refuses to emit elsewhere |
| `eval/corpus-backed-runner` | seed-export | Runner builds context via `build_context_set_from_db` from a seed (in-memory SQLite import); file-based path untouched |
| `eval/bootstrap-engine` | corpus-backed-runner | seed + N JDs → analyze+clarify+generate per JD → dedup bullets/skills (Jaccard-0.75) → `run_grounding_signals` (2nd call site) → `bootstrap.json`; adds the `jd_pandering` slug to the rubric vocabulary |
| `eval/annotation-contract` | bootstrap-engine | `annotations.json` schema (verdict enum; reused `failed_rules` slugs; verdict-aware note; "should-omit"; optional honest rewrite; clarification-question rating; inline MiniCheck/NLI pre-scores) + deterministic collation → `expected.json` + improvement brief |
| `tuning/draft-and-gate-skill` | override-primitive + annotation-contract | `/tune-from-annotations`: agent reads brief → drafts candidate into overrides → candidate-vs-baseline eval → user promotes (writes `analyzer.py` + bumps `PROMPT_VERSION` + TUNING_LOG entry) |

Per-branch docs land with each branch (not now): CHANGELOG; TUNING_LOG on each promotion; AGENTS.md "Eval observability" (override primitive); `evals/README.md` (`--prompt-overrides`, seed import, bootstrap); CONTRIBUTING.md (seed script + tune workflow).

### v1.0.4 tag criteria

- Loop runnable end-to-end on a real seed: export → bootstrap → annotate → collate → draft/eval/promote
- Override primitive proven: a candidate prompt run produces a candidate-vs-baseline delta table; default path byte-identical (cache_read unchanged)
- Grounding scorers run on real generated output (first real-data use of DeBERTa + MiniCheck)
- Real fixtures form a permanent `--suite real` regression set; annotations validate the automated scorers
- `ruff + mypy + pytest` green

---

## Phase 4 — UI/UX redesign (v1.0.5)

**Blocked until v1.0.4 tagged.** Establishes the design system. Internal until the v1.1.0 public tag.

**WYSIWYG:** Option 1 confirmed — post-generate `md_to_json_resume()` caching; no prompt change.

This phase carries the product redesign **and** the polished home for the Phase 3 tuning loop: the diagnostics dashboard is redesigned into a tabbed diagnostics+tuning console, and the annotation surface becomes a rich browser tab (reading/writing the Phase 3 `annotations.json` contract). Both ride the new design system — built once.

### Branches

| Branch | Depends on | Key work |
|---|---|---|
| `feat/wysiwyg-option1` | main | `md_to_json_resume()` after generate; preview route updated; corpus fallback |
| `feat/step6-redesign` | wysiwyg | Cut tabs/toggle; preview top; edit-raw modal; CL "+ Generate" button |
| `feat/cover-letter-formats` | step6 | `.pdf` and `.md` CL output; `generator.generate_cover_letter` gains format param |
| `feat/prior-app-resume` | wysiwyg | Click prior app → load context + persona + resume → Step 6 (`app.js:3404` D.3.1) |
| `feat/bullet-drag-reorder` | independent | HTML5 drag on Compose bullets; `bullet_order` in `composition_overrides`; `_stable_user_prefix` honors it; reset button |
| `feat/playwright-ux-suite` | independent | `tests/ux/conftest.py`; POM classes; ≥5 regression tests for 2026-05-26 bugs |
| `feat/template-pagination` | wysiwyg | Modern/Spacious/Tech blank page fix |
| `eval/grounding-metric-l0` | independent | **Inserted 2026-06-05 — see note below.** Deterministic L0 fabricated-specifics rate (sharpen `missing_samples` → typed numeric/entity extractor with tolerance) + aggregate existing eval-time L1/L2 grounding signals into one reportable groundedness signal. Hot-path-safe; `hardening.py` + `evals/`; no LLM, no `PROMPT_VERSION` bump, no new dep. Design: [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) |
| `feat/diagnostics-console-redesign` | design system **+ `eval/grounding-metric-l0` (metric contract)** | Tabbed read-only panels + tuning shell + cost meter on the new design system; localhost + PII guards (the dashboard's first read-write surface). Surfaces the L0 groundedness signal — designed *around* the metric contract, not retrofitted |
| `feat/annotation-tab` | diagnostics-console + Phase 3 `annotation-contract` | Browser bootstrap wrapper (reuses `/api/analyze/stream` SSE) + rich annotation surface writing the `annotations.json` contract |

> **Re-sequence note (user-approved 2026-06-05).** `eval/grounding-metric-l0`
> was inserted **before** `feat/diagnostics-console-redesign`. Rationale: don't
> design the diagnostics panels around — or steer the grounding-gated tuning
> loop by — a hallucination metric that isn't yet defined ("data model before
> the view"). The binding constraint was found to be **missing labels**, not the
> metric code: `evals/fixtures/real/` is empty and the v1.0.4 live loop was never
> run, so the *calibrated* cross-class metric can't be built yet. We therefore
> split the work: the **deterministic, label-free L0 slice ships now** (gives the
> dashboard a real metric contract), and the **calibrated model-based layers +
> the v1.0.4 live loop + the evals/tuning update are deferred to pre-v1.1.0** —
> tracked in [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) "Grounding /
> hallucination metric — calibrated layers (B)". Full design rationale, the
> detector ladder, and the hard parts live in
> [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md). This deviation pushes the v1.0.5
> tag by one branch; it does not touch any prompt or `PROMPT_VERSION`.

#### Diagnostics console — interactive completion (the "finish the faceplate" arc)

> **Sourced 2026-06-06** (walkthrough finding, user-approved). `feat/diagnostics-console-redesign`
> + `feat/annotation-tab` above shipped the console's *surfaces*, but several are
> read-only or stop at a CLI hand-off: the grounding scorers were reachable only via
> the `--grounding-signals` CLI flag (the browser bootstrap hard-coded
> `grounding_fn=None`), the Tuning tab is a labeled stub, and `collate` returns a
> `run_command` string to paste into a terminal. This arc completes the console into
> a **browser-driven self-tuning loop** — produce → annotate → grounding-score → run
> eval → A/B a prompt candidate → see deltas — leaving only the irreversible
> **promote** (edit `analyzer.py` + bump `PROMPT_VERSION` + TUNING_LOG entry) as the
> agent's job. The heavy L1/L2 scorers stay **eval-time** (Key Decision #4 +
> [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) hot-path discipline unchanged).

| Branch | Depends on | Key work |
|---|---|---|
| `feat/grounding-scorers-in-console` ✓ DONE (merged `bc29a07`, 2026-06-06) | annotation-tab | Opt-in grounding on the browser bootstrap + a "Score grounding" backfill route (`POST /api/annotation/fixture/<u>/<slug>/score`); browser bootstraps now snapshot a `seed.json` via `scripts.export_corpus_seed.export_seed` (the source the backfill scores against via `seeded_session`, and the file collate's `--seed` run-command already assumed but never produced). Missing `[eval-grounding]` extras or any scoring failure degrades to un-scored + a streamed `warning` — never a 500. No `PROMPT_VERSION` bump. |
| `feat/run-eval-from-console` ✓ DONE (merged `3a91bea`, 2026-06-07) | grounding-scorers | Extracted a `run_suite(...)` core from `runner.main()` (`EvalRunResult` return + optional `progress` callback; default path byte-identical, mirrors `bootstrap.py`'s `main`/`run_pipeline_over_jd_texts` split) + a localhost SSE `POST /api/eval/run`. "Run eval" control on the Quality tab (suite/subset/grounding + cost-band `confirm()` consent + reload); collate's copy-the-command dead-end replaced with a visible command **and** a "Run this fixture" button. Closes the mandatory CLI hop in the loop. No `PROMPT_VERSION` bump. **`run_suite` is the precondition `feat/tuning-tab-ab` consumes.** |
| `feat/tuning-tab-ab` ✓ DONE (merged `812e6bb`, feature `5f708f7`, 2026-06-07) | run-eval-from-console | Replaced the Tuning stub with a real in-browser A/B: pick an `analyzer._BASE_SYSTEM_PROMPTS` constant, draft/paste a candidate, run baseline+candidate evals via a dedicated localhost SSE `POST /api/tune/run` (drives `run_suite` twice + `analyzer.prompt_overrides()`), delta rendered with `evals/tune.py` (`load_scores`/`build_delta_table`/`format_delta_table`). Mirrors `/api/eval/run`'s contract incl. optional corpus-seed mode. **Promote stays the agent's job** — no route edits `analyzer.py`. No `PROMPT_VERSION` bump; no new dep. |
| `docs/tuning-loop-discoverability` ✓ DONE (merged `8c6cb7d`, 2026-06-07) | tuning-tab-ab | In-app diagnostics-modal/pill/settings copy advertises the now-interactive loop; the in-browser console-loop walkthrough lands in `evals/README.md` (the dev-doc home) with `walkthrough.md` carrying only a flag + link to it; `GROUNDING_METRIC.md` "B (deferred)" note updated to note the label-producing loop is now browser-driven. Docs only. |

**Sequencing:** strictly sequential, one branch per session. Each is independently
shippable; `feat/run-eval-from-console`'s `run_suite` extraction is the precondition
for `feat/tuning-tab-ab` — do not start a later branch in an earlier one's session.
This arc rides within the v1.0.5 stream (or a v1.0.6 cut per the size note below —
user's call). It also advances the deferred grounding calibration ("B"): the
in-browser annotation loop is what *produces the labels* `GROUNDING_METRIC.md` /
[`PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) need.

*If this phase is too large for clean small-stepping, the natural cut is v1.0.5 = redesign + WYSIWYG + tuning UI; v1.0.6 = formats + prior-app + reorder + playwright + pagination. User's call.*

### v1.0.5 tag criteria

- WYSIWYG confirmed (preview = download)
- Cover letters: .docx / .pdf / .md
- Prior-app click resumes wizard
- Playwright: ≥1 happy-path-stubbed + ≥5 regression tests
- Pagination fixed for all 4 bundled templates
- Diagnostics+tuning console redesigned; annotation tab live on the design system
- `ruff + mypy + pytest + pytest -m ux` green

---

## Phase 4.5 — Walkthrough polish + knowledge substrate (v1.0.6)

> **Added 2026-06-08**, folding two temporary planning artifacts (now retired)
> into this arc: the v1.0.5 walk-through sprint plan (24 UX findings → topical
> sprints) and the "excellence walk" engineering workstreams (WS-1…WS-4).
> Numbered **4.5** to slot between the v1.0.5 tag (Phase 4) and the v1.1.0 public
> release (Phase 5) **without renumbering Phase 5**, which other docs cross-
> reference (`RELEASE_CHECKLIST.md`, `PRODUCT_SHAPE.md`).
> **Blocked by:** v1.0.5 tag ✅. **Blocks:** v1.0.7 (Phase 4.7).

**Opens with a full end-to-end walkthrough.** Like the v1.0.5 cut, v1.0.6 begins
with the user driving the whole product — app + evals + tuning — to COLLECT
bug/issue findings. Those findings decompose into the topical sprints below (the
v1.0.5 method) and JOIN the backlog carried from the v1.0.5 walk-through. The named
V5-B parity fixes (#9 download ≠ preview, #10 step-6 edit not reflected in preview)
have **no matching fix branch in git history** and `V1_0_5_VERIFICATION.md` is
**unsigned**, so the kickoff walkthrough is also the signing / re-confirmation pass
for them — anything still broken re-enters the buckets here.

### Cut-line decisions (carried from the walk-through reconciliation)
1. Education (#18/#22) is a **full sweep in one release** — every tab + panel +
   diagnostics gets plain-language, a11y-safe summaries (Sprint 6.5).
2. All remaining walk-through items = **one combined v1.0.6**; v1.0.7 is the spill
   valve, not a pre-commitment. If v1.0.6 balloons, **Sprint 6.5 (the education
   sweep) is the clean cut** to break out as its own point release.
3. **Onboarding IA = corpus-first + smart landing** (Sprint 6.4): Career corpus
   becomes tab 1 + the landing tab for an empty corpus; Tailor becomes tab 2 + the
   landing tab when a corpus exists; finishing corpus review hands forward with a
   "Start tailoring →" CTA.

### Sprint 6.0 — E2E walkthrough (kickoff; operation, not a code branch)
User-driven full run on a real corpus; capture findings; decompose into the 6.x
buckets. Mirrors the v1.0.5 walk-through that produced 24 findings.

### Sprint 6.1 — Wizard-flow correctness
| Branch | Finding | Key work |
|---|---|---|
| `fix/clarify-double-question` | #6 | Collapse the duplicate clarify/skip; "Continue to clarify" initiates clarification directly. |
| `feat/prior-app-resume-robustness` | #4 + #24 | Resume from the most-advanced state even when generation never ran; add JD title/company to prior-app cards; relabel the opaque "N pending" pill. |
| `feat/compose-add-title` | #7 | Add an alternative title in Step 3 **written into the corpus** (sourced, not a context-only override). |
| `fix/compose-order-no-recommendations` | v1.0.5 deferred | Honor the GET array order on the no-recommendations fallback in `_renderComposeCard` instead of re-sorting by score; add a regression test. |
| `fix/step4-template-copy` | #8 | Verify the four bundled templates actually differ; correct the Step-4 copy. |

### Sprint 6.2 — Diagnostics-console correctness
| Branch | Findings | Key work |
|---|---|---|
| `fix/diagnostics-chart-corrections` | #11 + #12 + #13 | Cost tooltip "Total" must plot the sum not the mean; widen the Calls panel (no horizontal scroll); rescale the latest-trace bar axis so populated bars are visible. |

### Sprint 6.3 — Forms, affordances & a11y *(the a11y gate lands first, guarding every later branch)*
| Branch | Findings | Key work |
|---|---|---|
| `fix/form-field-labels-a11y` | #3 | Add `id`/`name` + label/`aria-label` to the ~150 flagged fields; **add the never-shipped `tests/ux/a11y/test_axe_smoke.py`** (no serious/critical axe violations). Land early. |
| `feat/required-field-and-dropdown-pattern` | #21 + #20(dropdown) | Reusable required-field marker + auto-populatable-input→dropdown convention; first consumer = annotate candidate-username dropdown. |
| `fix/corpus-affordance-polish` | #2 + #5 | Surface the corpus Add-variant control (`SummaryItem` exists); fix misleading empty-state copy; enlarge the expand/collapse tick arrows ~50%. |

### Sprint 6.4 — Information architecture + onboarding
| Branch | Findings | Key work |
|---|---|---|
| `fix/logo-home-route` | #23 | Logo click routes to the main page with no user selected. |
| `feat/corpus-first-tab-onboarding` | #16 + #1 | Reorder tabs to Career corpus (1) → Tailor (2) → …; smart landing (empty → Corpus, non-empty → Tailor); "Start tailoring →" hand-off CTA replaces the dead-end. Lands **before** the 6.5 education sweep so per-tab summaries are written against the final tab order. |

### WS-4 substrate — LLM-wiki knowledge architecture (NEW; lands in the 6.4 → 6.5 window)
> From the excellence walk (WS-4). The wiki's only deadline is **Sprint 6.5**: the
> education sweep must author **into** the wiki, not into throwaway prose. Build
> after 6.4 so most route churn has settled. Runs parallel to the sprint stream and
> does not gate or threaten the earlier sprints. **Source drafts live in the
> gitignored `output/_dev-notes/` on the working clone — re-author from them, do not
> expect them in a fresh clone.**

**Build sequence (each its own branch/session):**
1. `docs/system-model` — author **`docs/system-model.md`** from the excellence
   walk's seven-functions language: **Substrate · Production · Evaluation ·
   Operation · Memory · Regulation · Governance**, the one-way dependency law (every
   dependency points inward toward Production; Production answers only upward to
   Governance), and the **Product / Work** split. The canonical system self-model +
   the WS-4 wiki `overview.md` seed. *(Source: the "SETTLED" box in
   `excellence-walk.md` + `Q1_overview_draft.md`.)*
2. `docs/wiki-skeleton` — stand up a committed `docs/wiki/` (`SCHEMA.md`,
   `index.md`, `overview.md` ← the Q1 draft + its 4 open revision points, `log.md`,
   `.last_ingest_sha`, `pages/`) + a root `llms.txt`. Codebase variant: **git HEAD
   is the source**, diff-driven ingest, no code copies. `SCHEMA.md` **references**
   AGENTS.md / CLAUDE.md / vision; it does not duplicate them.
3. `feat/wiki-skills` — adapt `kfchou/wiki-skills` ops into `.claude-plugin/` skills
   (`/wiki-ingest`, `/wiki-query`, `/wiki-lint`, `/wiki-audit`); manual trigger + a
   lightweight commit-time freshness **reminder** hook (NOT auto-ingest — per-commit
   LLM cost); `wiki-lint` as a periodic + pre-release gate.
4. `wiki/cold-ingest-code` — cold-ingest the code architecture (module map, the P1
   deterministic/LLM boundary, the `context_set` contract, pipeline flows, routes,
   the eval harness), `path:line`-grounded. **Reserve a user-facing section** that
   Sprint 6.5 authors into.

**Then — Governance extraction** (its own carefully-gated branch, after the wiki
proves out; the 3 open sub-decisions below resolved in a short WS-4 design session
first):

> ⚠ **HARD CONSTRAINT.** `AGENTS.md` / `CLAUDE.md` are **harness-auto-loaded** — the
> agent's operating instructions at session start. Lifting the prescriptive
> **Governance** rules into one canonical home MUST preserve agent rule-access via
> `@import` / pointer (CLAUDE.md already does `@AGENTS.md`) — or **every future agent
> loses its guardrails.** `AGENTS.md` stays the entry point; it imports/links
> Governance, it does not lose the rules.

- **What extracts:** the `vision.md` core; the 10 Principles (frozen in Governance);
  and the hard RULES scattered across `AGENTS.md` (security gate, `PROMPT_VERSION`-
  bump, deterministic/LLM boundary, what-NOT-to-do, branch conventions),
  `CONTRIBUTING.md` (the ruff+mypy+pytest bar, commit/branch conventions),
  `SECURITY.md` (API-key rules, `_safe_username`/`_within` mandate),
  `PRODUCT_SHAPE.md` (the prescriptive v1→v2 ladder + Corpus-Item rules), and **this
  arc** (the "Hard constraints (all phases)" + the "Do not edit without sign-off"
  gate). Each rule is stated **once** in Governance; the others **reference** it.
  Mixed docs keep their descriptive content + a pointer.
- **Open implementation sub-decisions (NOT resolved here — for the WS-4 design
  session):** (i) Governance home name/location — `raw/` vs `docs/governance/` vs
  root `GOVERNANCE.md` (lean: `docs/governance/`); (ii) per-doc extraction
  boundaries (exact spans); (iii) `AGENTS.md` = critical-rules-inline-with-pointer
  vs pure-shell-import.
- **Payoff:** vision-alignment auditing reads ONE canonical constitution; the
  pre-release `wiki-lint` gate can guard it directly; "consistency tracks
  enforcement" (the Q2 finding) extends to the vision itself.

### Sprint 6.5 — In-app education (full sweep) + install docs
| Branch | Findings | Key work |
|---|---|---|
| `feat/help-pattern-component` | (mechanism) | Build the reusable a11y-safe help primitive once (per-tab description + per-panel summary + contextual tooltip; real `aria` wiring; no color-only meaning). |
| `feat/education-tailor-corpus-wizard` | #1 + #18 | Apply the pattern across Tailor / Career corpus / Résumé templates / Candidate memory + each wizard step. Plain-language, assumes no technical background. **Authors into the WS-4 wiki's reserved user-facing section.** |
| `feat/education-diagnostics-annotate` | #15 + #20 + #22 | Apply across all diagnostics tabs + the annotate tab: verdict legend + per-option tooltips; annotate instructions rewritten for lay users + auto-expand the bootstrap panel when no fixtures exist; a summary on every panel. |
| `docs/eval-stack-install-guide` | #17 | A user-facing install/prepare guide for the tuning/grounding/eval stack — **authored from the excellence walk's Q3 deliverable** (`output/_dev-notes/Q3_downloads_draft.md`; facts verified against `pyproject.toml` + `install.md` + `CONTRIBUTING.md`) — plus a README/`install.md` "what gets downloaded & why" section + an in-app pointer where the stack is needed. |

Then: `chore/version-bump-v1.0.6` (pyproject, CHANGELOG, tag) + re-check the
RELEASE_CHECKLIST risk register.

### v1.0.6 tag criteria
- The E2E-walkthrough findings are triaged; tag-blocking ones fixed (the rest spill
  to v1.0.7).
- Sprints 6.1–6.5 merged; the a11y axe gate is live and green.
- **WS-4 substrate landed before the 6.5 education sweep** — `docs/system-model.md`
  + the `docs/wiki/` skeleton + the wiki skills exist; the code architecture is
  cold-ingested; 6.5's education content is authored into the wiki's reserved
  user-facing section.
- `ruff + mypy + pytest + pytest -m ux` green.

---

## Phase 4.7 — Pre-public hardening (v1.0.7)

> **Sprint PV** from the walk-through plan: the pre-public obligations from
> [`PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md) §10 "Post-v1.0.5" + the v1.1.0 tag
> criteria, scheduled as real branches. **Blocked by:** v1.0.6 tag. **Blocks:**
> v1.1.0 (Phase 5).

**Shared prerequisite (human, not a branch):** a clean-corpus rebuild from a real
git **clone** — NOT a folder copy, which drags the gitignored `db/resume.sqlite` —
then regenerate the corpus from real JDs. Required by PV-1/PV-2/PV-3. The v1.0.5
faceplate arc made the loop browser-driven, so most of this runs from the
Annotate / Quality / Tuning tabs rather than the CLI.

| Branch | Depends on | Key work |
|---|---|---|
| `eval/live-shakedown-labels` (PV-1) | corpus rebuild | Run the v1.0.4 loop **end-to-end on the real corpus** (tagged-in-machinery-but-never-executed): Annotate-tab bootstrap with grounding scorers → annotate verdicts → collate → `expected.json`. Deliverable: real `bootstrap.json` + `annotations.json` under `evals/fixtures/real/` (gitignored, PII) + a `TUNING_LOG.md` entry. Mostly an operation, not new code. **Unblocks PV-2.** |
| `eval/grounding-calibration` (PV-2) | PV-1 | The **calibrated layers (B)**: calibrate the L0 tolerance bands (`hardening.py`) + the eval-only L1/L2 NLI/MiniCheck thresholds (`evals/grounding_signals.py`) against the PV-1 labels; report precision/recall per detector; wire the calibrated groundedness score into `eval_composite` / score-over-time and have the tuning gate consume it; close the [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) "B (deferred)" note. **L0 stays hot-path-safe; L1/L2 stay eval-only** (Key Decision #4). |
| `tune/cover-letter-opener` (PV-3) | corpus rebuild + tuning loop | Fix the throat-clearing/hedging opener (tripped `tone` in 1/5 v1.0.3 runs). A worked-example `SYSTEM_PROMPT` candidate (the rule lives in the **non-overridable** `_COVER_LETTER_RULES_BLOCK`, so it must be a worked example, not a rules-block edit) via the in-browser A/B; A/B against `--suite real` (n≥3); **user promotes** → edit `analyzer.py` SYSTEM_PROMPT + **bump `PROMPT_VERSION` in the same commit** + TUNING_LOG entry. Run after PV-2 so groundedness is calibrated when judging. |
| `chore/type-annotation-scan` (PV-4 = **WS-2 increment 1**) | independent | The explicit v1.1.0 tag criterion (see Phase 5). Annotate Flask route returns with `flask.typing.ResponseReturnValue` (~15+ functions, surgical) **or** flip `check_untyped_defs = true` (broader — surfaces real new errors first). **Scope to the whole post-v1.0.4 diff** (v1.0.5 **and** v1.0.6 routes); slot last so it covers every new route. **This is the first, modest increment of the excellence walk's WS-2 (strict typing)** — it absorbs the original PV-4 type scan. The full `mypy --strict` ratchet + a typed `context_set` spine is the post-v1.1.0 **WS-2-full** workstream, not this branch. |

Then: `chore/version-bump-v1.0.7` (pyproject, CHANGELOG, tag).

### v1.0.7 tag criteria
- PV-1 real labels exist under `evals/fixtures/real/`; PV-2 calibrated groundedness
  is live on `--suite real` + the dashboard and consumed by the tuning gate.
- PV-3 cover-letter `tone` holds at/above its TUNING_LOG floor with the new opener
  discipline; `PROMPT_VERSION` bumped in the same commit; user promoted.
- PV-4 type scan complete across the post-v1.0.4 surface.
- `ruff + mypy + pytest` green.

---

## Phase 5 — Public release (v1.1.0)

**Blocked until v1.0.7 tagged. The v1.1.0 tag is owned by the user** — applied when the product is judged complete and polished enough to showcase (portfolio + open-source + personal tool). There is no external deadline; completeness and polish gate the tag, not a clock.

### Branches

| Branch | Depends on | Key work |
|---|---|---|
| `release/visual-assets` | UI stable | `docs/screenshots/*.png`; optional demo.gif |
| `release/fresh-clone-v1-1-0` | visual assets | Clean clone → pip install → run → one application < 5 min |
| `chore/release-v1.1.0` | fresh-clone | `version = "1.1.0"`; CHANGELOG; create GitHub repo; push + tag — **executed on the user's go** |

### v1.1.0 tag criteria

- Everything from the v1.0.5 criteria, holding green
- Visual assets in `docs/screenshots/`
- Fresh-clone < 5 min
- GitHub URL live; all doc links resolve
- **Type-annotation scan of all v1.0.5-stream changes** — **delivered by Phase 4.7
  `chore/type-annotation-scan` (PV-4 = WS-2 increment 1)** during v1.0.7, scoped to
  the whole post-v1.0.4 diff (v1.0.5 **and** v1.0.6 routes). At the v1.1.0 cut this
  is a *verify-it-held* check, not fresh work: confirm a full `mypy` pass with
  `check_untyped_defs` enabled (or the annotated signatures) stays clean over
  everything that landed across the v1.0.5 + v1.0.6 streams, so no untyped function
  body slipped through unchecked during the redesign.
  *Origin:* `feat/wysiwyg-option1` (2026-06-02) surfaced ~15 pre-existing
  `annotation-unchecked` notes in `app.py` — Flask route handlers whose
  *signatures* are unannotated, so mypy skips their bodies by default (these are
  notes, not errors; the gate stayed green). The public-release cut is the right
  point to clear them. **Lower-risk path:** annotate the route returns with
  `flask.typing.ResponseReturnValue` (surgical, ~15 functions). **Broader path:**
  flip `check_untyped_defs = true` in the mypy config globally — checks every
  untyped body at once but will surface real new errors to fix first. Either way,
  scope the scan to the v1.0.5 diff, not the whole pre-existing surface.
- **User judges it showcase-ready**

---

## Post-v1.1.0 workstreams (the heavy structural levers — parked off the release stream)

> From the excellence walk. These are the biggest *code* and *capability* levers,
> deliberately sequenced **after** the public release so they don't churn the
> release stream. None gate v1.1.0. Each gets its own design pass before code.

- **WS-1 — decompose the `app.py` monolith into Flask blueprints.** The 6,290-LOC /
  75-route file is the clearest structural smell (Q1/Q2 finding). Split into domain
  blueprints (candidate seams: analysis, generation/cover-letter, corpus, dashboard,
  user/config, templates), preserving the `_safe_username`/`_within` gate + the
  `route-security-lint` hook that lints it. **Needs its own design session + Q&A**
  (blueprint seams & naming; shared-helpers home; app-factory vs. module-global
  `app`; SSE routes; the 67 test files that import from `app`; hook compatibility).
  **MUST NOT interleave with an active sprint stream** — it rewrites routes nearly
  every other branch touches. Run it in a dedicated low-churn window.
- **WS-2-full — strict typing ratchet.** The continuation of PV-4 (v1.0.7): move
  mypy toward `strict = true` incrementally (per-module overrides as a ratchet) and
  model the `context_set` contract + the `dict`-typed request/response payloads as
  TypedDict/dataclass/Pydantic — turning runtime-only guarantees into edit-time
  ones. Likely sequenced **with/after WS-1** (the blueprint split changes route
  signatures). Decide the ratchet order and whether a single `ContextSet` Pydantic
  model becomes the spine.
- **WS-3 — recurring test-suite engineering-design pass.** A periodic design review
  of the ~955-test suite for efficiencies, redundancies, slow tests, coverage gaps,
  fixture duplication — to keep the suite from accreting cost as it grows. Define
  the cadence and what "good" looks like.
- **Codebase / docs Q&A assistant.** The post-v1.1.0 capability the WS-4 wiki
  substrate is built for: LLM-queryable answers over the repo + docs ("how do I
  rename a job-experience title" ↔ "how does the grounding suite work, set it up"),
  i.e. the LLM-wiki **query** op over the committed `docs/wiki/`. Built on WS-4, not
  before it.

---

## Hard constraints (all phases)

- Branch before any code edit
- Quality gate before every commit: `ruff check . + mypy . + pytest`
- PROMPT_VERSION bumped in same commit as any prompt change
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py`
- New dependency = `pyproject.toml` + CHANGELOG entry (Pydantic is the only new dep in this plan)
- Security pattern on every new Flask route: `_safe_username() + _within() + secure_filename()`
- If a hook blocks you: surface the hook name + error to the user, do not bypass, wait for authorization
- One branch per agent session — close, merge, hand off before starting the next

## Reference documents

| Document | What it's authoritative for |
|---|---|
| `docs/dev/RELEASE_CHECKLIST.md` | Open items per release |
| `evals/TUNING_LOG.md` | Baseline floors; prompt change history |
| `docs/dev/AGENT_FAILURE_PATTERNS.md` | Failure patterns to avoid |
| `docs/architecture.md` | Module map, LLM routing |
| `C:\Users\iam\.claude\research\resume-eval-2026-05\followup.md` | 25-item Phase 1 checklist |
| `docs/dev/perf/R1_BENCHMARK_2026-05-26.md` | R1 diagnosis (Phase 2 start point) |
| `C:\Users\iam\.claude\research\resume-eval-2026-05\report.md` | Tool recs (Promptfoo, MiniCheck, DeBERTa) |
