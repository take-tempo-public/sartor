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
| v1.0.6 | Walkthrough polish + knowledge substrate + corpus completion | No (internal until v1.1.0) | E2E-walkthrough-driven UX polish (Sprints 6.1–6.5) + the **WS-4 LLM-wiki substrate** (front-loaded; before the 6.5 sweep) + corpus-item completers (**B.4** ExperienceSummaryItem, **B.5** SkillGroupItem) + **B.8 Part 1** (outcome capture). **Not yet tagged** — opens with a fresh end-to-end walkthrough. See **Phase 4.5**. |
| v1.0.7 | The app knows itself | No (internal until v1.1.0) | The autonomous self-documenting/self-tuning wiki loop + the doc-grounded **assistant** (Haiku, reuses the user's key) + pre-public hardening (grounding-calibration B · cover-letter tuning). **Not yet tagged.** See **Phase 4.7**. |
| v1.0.8 | Monolith → blueprints (WS-1) | No (internal until v1.1.0) | Decompose the 6,290-LOC / 75-route `app.py` into Flask blueprints (dedicated structural epic); **absorbs the type-annotation scan** (WS-2 increment 1). Public ships on clean blueprints. **Not yet tagged.** See **Phase 4.8**. |
| v1.1.0 | Public release | **Yes** | **Tag owned by the user** — the public cut of the complete product (assistant + self-documenting wiki + clean blueprints). GitHub push is part of this event |

**Versioning model (2026-06-08).** The **patch digit is an epic** — a bounded set of
one-branch-per-session sprints (1.0.6, 1.0.7, 1.0.8 …; ≤10 before a bump). The
**minor digit is a tag marker** for a *significant / public* version — **1.1.0 is the
public release.** Pre-public work is the **1.0.x** epic series; post-public work is
the **1.1.x** epic series (1.1.1, 1.1.2 …) until **1.2.0** is the next marker. Pack
sprints into existing epics; spawn a new epic only when the work justifies it; items
may flow forward/back across epics as circumstances change.

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

**The walkthrough is also a real-data capture.** Running it by really applying to
jobs produces, in one pass: the **UX findings**, the **real corpus + annotation
labels** the v1.0.7 grounding calibration (PV-1/PV-2) depends on, and the **first
outcome data** (B.8). The existing tracker already captures submit → interview /
rejection, so that data starts accruing immediately — verify it end-to-end as the
first act.

**This epic also lands** (beyond the polish sprints): the **WS-4 wiki substrate**
(front-loaded — see below), the **corpus-item completers** **B.4**
(ExperienceSummaryItem) and **B.5** (SkillGroupItem), and **B.8 Part 1** (outcome
capture, riding Sprint 6.1).

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

**Kickoff-walk harvest (2026-06-10).** The first kickoff run reached cover-letter
generation — sprint-1 blockers (`fix/onboarding-e2e-blockers`) cleared the hard
stops — so this pass is the Sprint 6.0 *harvest*, not new blockers. 11 findings,
triaged below into the existing 6.x buckets. Numbered `KW#` to stay distinct from
the v1.0.5 walk's `#1–#24` (the user's own numbering; KW11/KW12 unused).

| KW# | Finding | → bucket | Severity |
|---|---|---|---|
| KW1 | New-user submit lands on JD entry, not résumé import, when the corpus is empty (correct once a corpus exists) | 6.4 smart-landing | Med |
| KW2 | No corpus-wide "accept all pending" — senior résumés = many roles approved one by one | 6.3 affordance | Med · prereq for KW3 copy |
| KW3 | New-user first-run onboarding modal sequence (detail below) | 6.5 education + help primitive | High value |
| KW4 | Clarify asks questions but adds no new bullets (verify on a 2nd clarify) | 6.1 | Med-High · investigate |
| KW5 | Interview question-gen doesn't auto-scroll → looks like nothing happened | 6.1 | Low-Med |
| KW6 | `generate()` altered/duplicated job **dates** (two titles got the same range) though the corpus is correct | 6.1 (+ prompt) | **HIGH · output integrity** |
| KW7 | Applications block never updates after a completed tailor+download; candidate memory stays empty after clarify+interview | 6.1 / B.8 | **HIGH · B.8 tag gate** |
| KW8 | "Interview" link wording inconsistent with clarify's "application" language | 6.1/6.5 copy | Low |
| KW9 | Diagnostics: first-expand onboarding modals for technical users (mirror the user-side pattern) | 6.5 | Med |
| KW10 | Persistent help: an (i)-circle on every significant block re-opens that block's first-view modal (modal = canonical pathfinding copy; inline text = short form) | 6.5 help primitive | Defines the primitive |
| KW13 | Diagnostics panels under-use the space + no explanations (grounding box, synthetic/smoke options, *why* groundedness/tuning/annotate are empty) | 6.2 layout + 6.5 copy | Med |

**KW3 detail — new-user first-run modal sequence** (new users only: empty corpus →
first successful ingest; graceful fade-in, closes on click-away). Each stop fires
once on first view and is re-openable via its (i)-circle (KW10):
- **First run:** welcome to callback — a career-experience manager that tracks +
  manages your career data (not locked in a file you hand-edit per job); what the app
  does from the user's view; point to **Add new user** to start.
- **On add-user:** import a résumé to start; your initial career corpus is derived
  from it; ATS-friendly résumés recommended (we do what we can otherwise).
- **On successful ingest:** your résumé is now a **Career Corpus** of titles + bullets
  the app uses to generate tailored résumés; you can make variations + tag; review the
  corpus — everything is pending; accept one at a time, by title, or all at once (KW2);
  reviewing/accepting improves outputs; then click **Tailor** for a specific JD.
- **On first Tailor load:** paste a JD + hit **Analyze** to analyze your corpus
  against it.
- **On first clarify/skip:** what each button does + what clarify will do for you.
- **On recommended corpus (after clarify):** titles chosen per role-variant + bullets
  selected/ordered for the JD + new bullets generated by clarify (added to the corpus;
  acceptable now or reviewed later); these populate the JD-specific résumé; you can
  edit/add/remove; what "continue" does; the numbered steps move you back/forward.
- **On first template-step preview:** your selected résumé data is loaded; a small +
  growing template set on the left; you can upload a `.docx` to digest into a template
  (ATS-safe strongly recommended); click **Generate** to apply the template.
- **On first generation screen:** choose a format + click **Generate** to see the
  custom résumé.
- **On live preview:** keep the existing instructional copy; add that edit-in-place is
  text editing only, **not** a corpus change (**verified 2026-06-10:** edits/interview
  persist to the context file, download-edited only renders — the sole post-analyze
  corpus write is the explicit clarification→bullet *promotion*, which lands
  `is_pending_review=1`; [app.py:1940](../../app.py)); explain the text box + the
  interview buttons.
- **On first Generate click:** what's happening; you can download when complete (+
  where); you can also generate an editable cover letter.
- **On first cover-letter generation:** how it works + how editing works.

### Sprint 6.1 — Wizard-flow correctness
| Branch | Finding | Key work |
|---|---|---|
| `fix/clarify-double-question` | #6 | Collapse the duplicate clarify/skip; "Continue to clarify" initiates clarification directly. *(Resolved 2026-06-11: the analysis gate already presented clarify-vs-skip, but the CTA only navigated to Step 2 and re-showed the `#clarifyStartRow` "Get clarifying questions / Skip" row — the second prompt. The CTA now fetches questions directly via a new `continueToClarify()` wrapper (pending indicator during the call; row restored on failure; idempotency guard so re-entry doesn't re-spend `/api/clarify`). Direct rail-click / back-nav into Step 2 keeps `#clarifyStartRow` as its single legitimate prompt; KW4 `merge:true`/`merge:false` semantics untouched. UX-tier regression in `tests/ux/regression/test_20260611_clarify_no_double_prompt.py`. No `PROMPT_VERSION` bump, no new dep — front-end flow only.)* |
| `feat/prior-app-resume-robustness` | #4 + #24 | Resume from the most-advanced state even when generation never ran; add JD title/company to prior-app cards; relabel the opaque "N pending" pill. *(Resolved 2026-06-11: **#4** — `_build_resume_state` ([app.py](../../app.py)) now classifies a `target_step` (1 analyze · 2 clarify · 3 compose · 6 download) from the rediscovered iter-0 context file and ships the per-step payload; `resumeApplicationIntoWizard` ([static/app.js](../../static/app.js)) dispatches on it — Steps 1–3 rehydrate the analysis panel (+ saved clarify Q&A for Step 2) with **no** `/api/clarify` or `/api/generate` re-spend, Step 6 unchanged. The Resume button is now offered for every analyzed application. **#24** — title + company are user-editable in the app-detail modal (save-on-blur via the new DB-only `PUT /api/applications/<id>/meta`, mirroring `/notes`; `Application.company` was never populated before — user-chosen approach over a heuristic JD parse); the proposal pill reads "N to review". Route tests (`target_step` + `/meta`) + UX regression `tests/ux/regression/test_20260611_prior_app_resume_robustness.py`. No `PROMPT_VERSION` bump, no new dep — UI + one deterministic route.)* |
| `feat/outcome-capture-complete` (**B.8 Part 1**) | outcome tracking | Complete the outcome-capture surface (rides the same prior-app surface): make submit → interview / rejection / withdrawn solid + queryable. The capture UI already exists ([app.py:4669](../../app.py), [app.js:3383](../../static/app.js)); this *completes* it so it's not partial and **unblocks the learning layer** (B.8 Part 2 + nursery #1/#3). Data-model call — lean single-status vs an `ApplicationOutcome` event table — made at sprint design. **Kickoff KW7:** apps block shows "no applications" after a completed tailor+download + candidate memory stays empty after clarify+interview — verify/fix the outcome read+persist path here (and whether candidate memory is expected to populate yet). *(Resolved 2026-06-10 on this branch: the Application row WAS created at analyze — the block simply never re-rendered mid-wizard, and no UI path ever set `submitted`, so the outcome buttons were unreachable; candidate memory was designed-but-unwired — nothing wrote `clarification` rows from the wizard. Fixed with wizard-milestone refreshes, draft→submitted affordances, a `?status=` filter, and the live memory write path. Data model: lean single-status, `interview` terminal — user-approved.)* |
| `feat/compose-add-title` | #7 | Add an alternative title in Step 3 **written into the corpus** (sourced, not a context-only override). *(Resolved 2026-06-11: a Compose "+ Add title" affordance writes a sourced, immediately-eligible `ExperienceTitle` (`source=user_added`, `truthful_enough_to_use=1`, `is_pending_review=0`) via the existing `POST /api/experiences/<id>/titles` — a corpus item, not a context override. **User-approved scope extension:** the titles became a per-JD radio whose pick persists as `composition_overrides.pinned_title_ids` and is honored in **both** the live preview (`build_json_resume_from_corpus`: pin→official→first) **and** the generated download (the chosen `<eligible_title pinned="true">` + a new `<corpus_mode>` rule; `PROMPT_VERSION` → `2026-06-11.1`). Because generate reads a **frozen** corpus snapshot, the composition save re-syncs `career_corpus[exp].eligible_titles` from the DB for pinned experiences so a post-analyze title reaches generate (shared `db.build_context.eligible_titles_for` helper). Route/unit (`TestCompositionTitlePin`, `TestTitlePin`, `TestTitlePinEmission`) + UX regression `tests/ux/regression/test_20260611_compose_add_title.py`; smoke eval clean (TUNING_LOG 2026-06-11). No new dep.)* |
| `fix/compose-order-no-recommendations` | v1.0.5 deferred | Honor the GET array order on the no-recommendations fallback in `_renderComposeCard` instead of re-sorting by score; add a regression test. *(Resolved 2026-06-11: the GET (`get_application_composition`) already ranked bullets by `bullet_order` + stamped `in_custom_order`, but `_renderComposeCard`'s no-recommendations branch re-sorted the fallback by score via `_dropoffPick`, reverting the on-screen order on reload — the persisted order was always intact. Fix: when `has_custom_order`, the fallback now reuses the GET-returned order (`exp.bullets.filter(in_custom_order === true)`) instead of `_dropoffPick`. Render-only — no backend change, no `PROMPT_VERSION` bump, no new dep. UX regression `tests/ux/regression/test_20260611_compose_order_no_recommendations.py`; the common path stays covered by `test_20260604_bullet_drag_reorder.py`.)* |
| `fix/step4-template-copy` | #8 | Verify the four bundled templates actually differ; correct the Step-4 copy. *(Resolved 2026-06-11: defect-vs-expected settled first — the four bundled templates **genuinely differ** in typography AND layout (Classic/Modern sans-serif vs Spacious/Tech serif; Modern's blue header band; Tech's float two-column item rows; varied margins/line-heights/heading treatments/accents — per the four `personas/bundled/*.css`), so the Step-4 line "Same content, different typography and layout" ([templates/index.html](../../templates/index.html)) is accurate and **unchanged**. The actionable drift was a stale **count**: migration 0005 curated the set 5 → 4 at v1.0.0 but the Résumé-templates settings copy still said "Five bundled" → fixed to "Four"; `docs/bundled_templates_LICENSE.md` inventory (listing the nonexistent `compact.docx`/`hybrid_tech.docx`) corrected to the curated four. Copy/doc only — no `PROMPT_VERSION` bump, no route, no new dep, no DB change. Canonical count of 4 is pinned at the data layer by `tests/test_bundled_templates.py`; new UX regression `tests/ux/regression/test_20260611_step4_template_copy.py` guards the copy↔rendered-set consistency.)* |
| `fix/generate-date-grounding` | KW6 | `generate()` altered/duplicated job dates (two titles ended on the same range) though the corpus is correct. Likely a SYSTEM_PROMPT worked-example (OK/NOT-OK date-handling pair) + **`PROMPT_VERSION` bump in the same commit** + a smoke/grounding eval check. **HIGH — the core no-invention value prop.** |
| `fix/clarify-generates-bullets` | KW4 | Clarify asks questions but adds no new bullets to the corpus — confirm defect vs expected first, verify across two clarify rounds, then fix. **Start from the `feat/outcome-capture-complete` discovery (2026-06-10):** `/api/answer-clarifications` does a whole-map replace (`context["clarifications"] = cleaned`), but `_collectIterateClarifyAnswers` ([static/app.js](../../static/app.js)) submits **only** the iterate-round textareas — so a 2nd-round submit drops the analyze-round answers from the new context file, and `generate` (iter≥1) loses them as ground truth (the JS comment claims "merges by id"; the route does not). This is the most likely mechanism behind "a later clarify round adds nothing." Candidate memory is unaffected (DB rows are additive). Fix shape: merge into the existing answers map instead of replacing it (mind the legitimate "skip clears prior answers" path), + a regression test across two rounds. *(Resolved 2026-06-11: defect-vs-expected settled — auto-bullets are by-design (promotion only); the real defect was the answers-overwrite. `/api/answer-clarifications` now merges by id (default `merge:true`); the skip path passes `merge:false`; merge intent declared at the three JS call sites; two-round regression test in `tests/test_app_clarify.py`. No `PROMPT_VERSION` bump, no new dep.)* |
| `fix/run-cover-letter-persistence` | discovered 2026-06-10 | `application_run.generated_cover_letter_md` is never populated — the run write-back (`db/persist_run.persist_corpus_generation`) stores résumé md + bullets + titles + ATS json but not the cover-letter md, so a generated+downloaded cover letter leaves no DB trace (confirmed against the e2e walkthrough run row). Low-risk persistence fix. **Schedule within v1.0.6** so the cover-letter signal is captured *while real outcome data starts accruing this epic* — B.8 Part 2 (post-public, outcome-weighted recommend) will want to correlate interviews with the cover letters that earned them, and rows generated now without it can't be backfilled. Small; may ride another 6.1/6.2 branch. *(Resolved 2026-06-11: defect-vs-expected settled — the gap was exclusively the detached `POST /api/generate-cover-letter` route, which wrote the letter to disk + context but did **no** DB write; `/api/generate` with `with_cover_letter=True` already persisted via `persist_corpus_generation`. Fix: after writing the letter, the route persists `generated_cover_letter_md` onto the **same** run row the résumé wrote to (`context_set["application_run_id"]`), via a new surgical single-column write-back `db.persist_run.persist_cover_letter_md` + `app._persist_cover_letter_to_db` (mirrors `_persist_corpus_generation_to_db`). **Deliberately NOT `persist_corpus_generation`** — its line 95 unconditionally writes `generated_resume_md = result.get("resume_content")`, so a cover-letter-only result would have nulled the already-saved résumé md. Corpus-backed mode only (legacy/no-run-id contexts skip it, as `/api/generate` does); best-effort so a DB hiccup never fails a downloaded letter. No LLM call, no `PROMPT_VERSION` bump, no route, no new dep, no migration (column existed). Unit no-clobber test (`tests/test_persist_run.py`) + route end-to-end test (`tests/test_cover_letter_detached.py`); pipeline + data-flow diagrams synced to show the write-back.)* |
| `fix/wizard-flow-polish` | KW5 + KW8 | Auto-scroll to the interview questions when generation completes (KW5 — today it looks like nothing happened); make the "Interview" link wording consistent with clarify's "application" language (KW8). Small; may ride another 6.1 branch. *(Resolved 2026-06-11 — final Sprint 6.1 row. Both confirmed defect-vs-expected first. **KW5:** `runIterateClarify()` ([static/app.js](../../static/app.js)) rendered the questions into `#iterateClarifyArea` but never scrolled, so they landed below the fold; it now scrolls the revealed section into view in the success path (`scrollIntoView({behavior:'smooth',block:'start'})`, the existing wizard-nav idiom), covering both the questions and "no follow-up questions surfaced" branches. **KW8:** standardized on the clarify vocabulary (user-chosen "follow-up" framing) — button "Get interview questions" → **"Get follow-up questions"**, divider "Iteration interview" → **"Follow-up clarification"** ([templates/index.html](../../templates/index.html)); `#btnIterateClarify` id unchanged so selectors/POMs are unaffected; the tracker "Got interview" outcome status (a different concept) untouched. Front-end only — no `PROMPT_VERSION` bump, no route, no new dep, no migration. UX regression `tests/ux/regression/test_20260611_wizard_flow_polish.py`: a cheap static copy guard + a full analyze→generate→follow-up drive that verifies the scroll by spying on `scrollIntoView` — the first UX test to drive the generate route, which needed two new offline stubs (`fake_generate_streaming` + `fake_clarify_iteration` in `tests/ux/stubs.py`). Diagram-sync intentionally **not** done: the diagrams' "GET INTERVIEW QUESTIONS" labels the Step-2 `/api/clarify` action (a different button), and the Step-6 iterate flow is already labeled "follow-up questions" — so no diagram references the renamed button. **Closes Sprint 6.1.**)* |

### Sprint 6.2 — Diagnostics-console correctness
| Branch | Findings | Key work |
|---|---|---|
| `fix/diagnostics-chart-corrections` | #11 + #12 + #13 | Cost tooltip "Total" must plot the sum not the mean; widen the Calls panel (no horizontal scroll); rescale the latest-trace bar axis so populated bars are visible. **Kickoff KW13:** also redesign the panels to use the available space better (beyond the three chart fixes); the explanatory copy rides Sprint 6.5. *(Resolved 2026-06-11: defect-vs-expected settled first. **#11** does **not** reproduce as stated — the cost-by-kind chart has plotted `total_cost_usd` (label "total $") since the console was built (`edde81d`); it never plotted the mean. The real issue was an unlabeled default tooltip beside a `mean $` table column, so the fix is an explicit, unambiguous tooltip (total + count + mean), not a data change. **#12 + KW13 (larger restructure, user-approved):** the cramped 560px side drawer is replaced by a **full-width inline detail panel** rendered in the page flow beneath the tabs (reusing the existing `#detailStore` move-the-node + lazy-`initCharts` machinery — only the destination element changed; `data-tab`/`data-pane`/`data-detail` kept stable), so every detail uses the page width and the 10-column Calls table no longer horizontal-scrolls (a defensive cell `word-break` guards narrow viewports). **#13:** the trace `.wf-bar` was a `<span>` at `display:inline`, so its width never applied and bars rendered at 0px ("look empty") — now `display:block` (+ 2px min-width), and `dashboard/routes._run_trace` emits `bar_pct` scaled to the longest span (max → 100%; share-of-total `pct` kept on hover, `latency_ms` the truth label), so bars render and short spans stay visible. Front-end + deterministic aggregation only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new dep, no migration. `bar_pct` unit test (`tests/test_dashboard_routes.py`) + UX regression `tests/ux/regression/test_20260611_diagnostics_chart_corrections.py`; the dashboard POM/selectors moved from `drawer` to `detail-panel` handles. Explanatory/help copy stays deferred to Sprint 6.5.)* |

### Sprint 6.3 — Forms, affordances & a11y *(the a11y gate lands first, guarding every later branch)*
| Branch | Findings | Key work |
|---|---|---|
| `fix/form-field-labels-a11y` | #3 | Add `id`/`name` + label/`aria-label` to the ~150 flagged fields; **add the never-shipped `tests/ux/a11y/test_axe_smoke.py`** (no serious/critical axe violations). Land early. *(Resolved 2026-06-12: defect-vs-expected settled first — the "~150 flagged fields" predated the v1.0.5/v1.0.6 redesign; the gate found **zero** label/name serious/critical violations on the current markup. Delivered the never-shipped **axe gate** `tests/ux/a11y/test_axe_smoke.py` — **vendored** axe-core 4.10.2 (`tests/ux/a11y/vendor/axe.min.js`, **no pip dep**) injected per panel via Playwright `add_script_tag`, asserting no serious/critical across landing / new-user form / the four top tabs / Settings drawer / a stubbed Compose+Template drive / every `/_dashboard` tab; new `a11y` pytest marker (tests are also `ux`, so they run inside `pytest -m ux`). The gate's only serious findings were **pre-existing color-contrast** (muted text sub-AA on the dark surfaces) — **user-approved scope add** fixed them at the token level: `--fg-2`/`--fg-3` → `#9b9ba7`/`#8f8f9b` (≥4.5:1, incl. the warm selected template-row bg) and `.edit-hint` drops `opacity:0.7` (which composited `--fg-1` to a sub-AA `#7c7d88`). #3 completion: `sr-only` labels on the 3 hidden file inputs + `name`/`autocomplete` on the new-user & Settings personal fields (the "missing autofill" half). Front-end + one test tier only — no `PROMPT_VERSION` bump, no route, no new pip dep, no migration. Gate covers the major panels; wizard Step-2/5/6 + modals are a future extension. ruff/mypy ✓, pytest **1072/1072** incl. `-m ux`.)* |
| `feat/required-field-and-dropdown-pattern` | #21 + #20(dropdown) | Reusable required-field marker + auto-populatable-input→dropdown convention; first consumer = annotate candidate-username dropdown. *(Resolved 2026-06-12: defect-vs-expected settled — no required-field convention existed anywhere (0 CSS hits), so the pattern was built fresh. **#21** is a reusable `.required-marker` + `.form-required-legend` in `static/style.css` (shared; the dashboard loads it) + the convention `required` + `aria-required="true"` on the input, decorative `aria-hidden` asterisk on the label. Applied across **three render paths** (user-chosen broadest scope): the static new-user form ([templates/index.html](../../templates/index.html) — username/name/email; optional contact fields unmarked), the JS-rendered `openFormModal` ([static/app.js](../../static/app.js) — every `required:true` field gets the marker + `aria-required`), and the console dropdown label. **#20** converts `#bsUser`/`#tuneUser` ([dashboard/templates/dashboard.html](../../dashboard/templates/dashboard.html)) from free-text inputs to `<select data-user-source>` auto-filled on load by a reusable `populateUserSelects()` that fetches the existing `GET /api/users` (no new route; `.value` read sites unchanged); `#bsUser` carries the required marker, `#tuneUser` (optional section) does not. Front-end + tests only — no `PROMPT_VERSION` bump, no route, no new dep, no migration. New regression `tests/ux/regression/test_20260612_required_field_and_dropdown.py`; the dashboard axe scan now seeds a candidate + opens the collapsed sub-panels so the populated dropdowns are scanned; selector registry gains a shared `Forms` class + Tuning username handles.)* |
| `fix/corpus-affordance-polish` | #2 + #5 | Surface the corpus Add-variant control (`SummaryItem` exists); fix misleading empty-state copy; enlarge the expand/collapse tick arrows ~50%. **Kickoff KW2:** add a corpus-wide "accept all pending" (by-title + all-at-once) — senior résumés have many roles; prereq for KW3's "accept all" onboarding copy. |

### Sprint 6.4 — Information architecture + onboarding
| Branch | Findings | Key work |
|---|---|---|
| `fix/logo-home-route` | #23 | Logo click routes to the main page with no user selected. |
| `feat/corpus-first-tab-onboarding` | #16 + #1 | Reorder tabs to Career corpus (1) → Tailor (2) → …; smart landing (empty → Corpus, non-empty → Tailor); "Start tailoring →" hand-off CTA replaces the dead-end. Lands **before** the 6.5 education sweep so per-tab summaries are written against the final tab order. **Kickoff KW1 confirms this:** a new-user submit currently lands on JD entry with an empty corpus — the smart-landing fix routes them to Corpus instead. *(Resolved 2026-06-12: tabs reordered to Career corpus → Tailor → Résumé templates → Candidate memory — **button order only**; `#topTabTailor` keeps the default `active`/`aria-selected` because the user picker (`#panelUser`) lives in `#tab-tailor` and the no-user landing must show it (there is no picker in the Corpus tab; the handoff's "default-active = Corpus" would require relocating the picker — out of scope). A new **side-effect-free** `_landingTab()` (must not seed `_corpusLoadedForUser`/`_corpusExperiences` or the corpus render is skipped) reads `GET /api/users/<u>/experiences` and returns `'corpus'` for an empty corpus / `'tailor'` otherwise (and `'tailor'` when no user / on fetch error); `onUserSelect()` routes through it (KW1 fixed), and `goHome()` now routes through it too — single source of truth for "which tab is home" — resolving to `'tailor'` since it deselects first. The **"Start tailoring →"** CTA rides the existing `#onboardingBanner`: at 0 pending on a non-empty corpus it flips to an `is-ready` success state with the CTA (→ Tailor); the `refreshCorpus()` banner refresh was moved to **after** `_renderCorpusList()` so the ready/empty check reads fresh `_corpusExperiences`. Front-end only — no route, no `PROMPT_VERSION` bump, no dep, no migration. UX regression `test_20260612_corpus_first_landing.py`; `test_20260612_logo_home_route.py` reseeded non-empty; new `Corpus.START_TAILORING_BUTTON` + `CorpusPage.start_tailoring_button()`.)* |

### Sprint 6.6 — Corpus-item completion (finishes the unified Corpus-Item vision)
> From the excellence-walk backlog (B.4/B.5). Both follow the existing `SummaryItem`
> pattern (model + `recommend_*` Haiku call + Compose card), so they're **low-risk
> extensions** — land them **before Sprint 6.5** so the education sweep documents the
> new Compose cards. Together they make the Corpus-Item vision *visibly complete* for
> the public cut.

| Branch | Item | Key work |
|---|---|---|
| `feat/experience-summary-item` | **B.4** | Per-role intro paragraph as a multi-variant Corpus Item (the asymmetry-matrix #1 pain — the line a recruiter reads first). Mirrors `SummaryItem`; maps to JSON Resume `work[].summary`. |
| `feat/skill-group-item` | **B.5** | Curated skill clusters per JD ("surface these 10, in this order") as a Corpus Item; a `recommend_skills` Haiku call; maps to JSON Resume `skills[]`. |

### WS-4 substrate — LLM-wiki knowledge architecture (split: WS-4a front-loaded, WS-4b after 6.6)
> From the excellence walk (WS-4). **Split** because the doc/whys content needs a home
> **early** — the preserved excellence-walk source (now tracked at
> [`../excellence-walk/`](../excellence-walk/)) must move into the wiki **very soon** —
> while the **code** cold-ingest wants route-churn settled (**after 6.6** — re-sequenced
> 2026-06-12 so the cold pass also captures the B.4/B.5 corpus-completer Compose cards).
> The wiki's hard deadline is **Sprint 6.5**: the education sweep authors **into** the
> wiki, not into throwaway prose.

**WS-4a — front-loaded (start of the epic, right after the walkthrough; depends on no churn):**
1. `docs/system-model` ✓ **DONE (this branch)** — authored **[`docs/system-model.md`](../system-model.md)** from the seven-functions
   language: **Substrate · Production · Evaluation · Operation · Memory · Regulation ·
   Governance**, the one-way dependency law (every dependency points inward toward
   Production; Production answers only upward to Governance), and the **Product / Work**
   split. The canonical self-model + the wiki `overview.md` seed. *(Source:
   [`../excellence-walk/excellence-walk.md`](../excellence-walk/excellence-walk.md) +
   [`../excellence-walk/q1-overview.md`](../excellence-walk/q1-overview.md).)*
2. `docs/wiki-skeleton` ✓ **DONE (this branch)** — committed the `docs/wiki/` skeleton
   (`SCHEMA.md`, `index.md`, `overview.md` ← seeded from + deferring to
   `docs/system-model.md` as canonical, carrying its 4 revision points; `log.md`;
   `.last_ingest_sha` sentinel; empty `pages/`) + a root `llms.txt`. **Git HEAD is the
   source**, diff-driven ingest. `SCHEMA.md` **references** AGENTS.md / CLAUDE.md /
   vision; it does not duplicate them. `raw/` starts at zero (introduced later by
   Governance extraction).
3. `feat/wiki-skills` — adapt `kfchou/wiki-skills` ops into `.claude-plugin/` skills
   (`/wiki-ingest`, `/wiki-query`, `/wiki-lint`, `/wiki-audit`); manual trigger + a
   lightweight commit-time freshness **reminder** hook (NOT auto-ingest — per-commit
   LLM cost); `wiki-lint` as a periodic + pre-release gate.
4. `wiki/ingest-excellence-walk` — **ingest the preserved
   [`../excellence-walk/`](../excellence-walk/) raw source** into synthesized wiki
   pages (system-model · the five-question deliverables · the WS-4/Governance design).
   This makes "minimally operational" real and lets the raw folder retire into the
   wiki's `raw/` constitutional layer. **The temp source is now safe in git — but
   ingest it early so the wiki, not a flat folder, becomes its home.**

**WS-4b — after Sprint 6.6** (route-churn settled **+ the B.4/B.5 corpus-completer cards
landed**, so the cold pass ingests them too; re-sequenced 2026-06-12)**:**
5. `wiki/cold-ingest-code` — cold-ingest the code architecture (module map, the P1
   deterministic/LLM boundary, the `context_set` contract, pipeline flows, routes,
   the eval harness), `path:line`-grounded. **Reserve a user-facing section** that
   Sprint 6.5 authors into. This tier is the **vocabulary-bridge / map** layer the
   doc-grounded assistant retrieves over (S1); as it ingests, it also **stamps each
   page's `audience:` tag** (user|dev) — the boundary the assistant's access plane
   gates on, authored once here + by governance-extraction. Design:
   [`memory-architecture.md`](memory-architecture.md). **Also folds in the two tracked
   architecture-diagram drifts** (the `pipeline.mmd` / `architecture.md` Step-2
   "GET INTERVIEW QUESTIONS" → "GET CLARIFYING QUESTIONS" mislabel + the data-flow
   cover-letter artifact-node mismatch), per [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)
   — this pass re-reads the architecture anyway.

**Then — Governance extraction → moved to v1.0.7** (Phase 4.7; decided 2026-06-12).
It depends on the wiki proving out (which completes at the v1.0.6 tag), pairs with "the
app knows itself," and is off v1.0.6's critical path. **v1.0.6 retains only the
`audience:` tag convention** — authored in WS-4b + the wiki `SCHEMA.md` before the 6.5
sweep, because the assistant's access plane and the 6.5 user/dev split need it within
this epic. The full extraction detail (the ⚠ `@import` rule-access hard constraint, what
extracts, the 3 open sub-decisions, the payoff) now lives in **§Phase 4.7 → Governance
extraction**.

### Sprint 6.5 — In-app education (full sweep) + install docs
| Branch | Findings | Key work |
|---|---|---|
| `feat/help-pattern-component` | (mechanism) | Build the reusable a11y-safe help primitive once (per-tab description + per-panel summary + contextual tooltip; real `aria` wiring; no color-only meaning). **Kickoff KW10/KW3:** the interaction model is a first-view auto-modal (graceful fade-in, closes on click-away) + a persistent (i)-circle on every significant block that re-opens that block's modal — the modal carries the canonical pathfinding copy, the inline block text is the short form. |
| `feat/education-tailor-corpus-wizard` | #1 + #18 | Apply the pattern across Tailor / Career corpus / Résumé templates / Candidate memory + each wizard step. Plain-language, assumes no technical background. **Authors into the WS-4 wiki's reserved user-facing section.** **Kickoff KW3:** the new-user first-run sequence (welcome → add-user → post-ingest → tailor → clarify/skip → recommended-corpus → template/preview → generate → live-preview → cover-letter) is fully specced in the Sprint 6.0 KW3 detail — author from there; new-users-only (empty → first-ingest). |
| `feat/education-diagnostics-annotate` | #15 + #20 + #22 | Apply across all diagnostics tabs + the annotate tab: verdict legend + per-option tooltips; annotate instructions rewritten for lay users + auto-expand the bootstrap panel when no fixtures exist; a summary on every panel. **Kickoff KW9/KW13:** a first-expand modal per diagnostics tab/panel (mirror the user-side pattern); explain the grounding box, the synthetic/smoke options, and *why* groundedness/tuning/annotate are empty + what populates them. |
| `docs/eval-stack-install-guide` | #17 | A user-facing install/prepare guide for the tuning/grounding/eval stack — **authored from the excellence walk's Q3 deliverable** (`output/_dev-notes/Q3_downloads_draft.md`; facts verified against `pyproject.toml` + `install.md` + `CONTRIBUTING.md`) — plus a README/`install.md` "what gets downloaded & why" section + an in-app pointer where the stack is needed. |

Then: `chore/version-bump-v1.0.6` (pyproject, CHANGELOG, tag) + re-check the
RELEASE_CHECKLIST risk register.

### v1.0.6 tag criteria
- The E2E-walkthrough findings are triaged; tag-blocking ones fixed (overflow spills
  to a later 1.0.x epic — not a new pre-commitment).
- Sprints 6.1–6.6 merged; the a11y axe gate is live and green.
- **Corpus-item completers B.4/B.5 merged** (before the 6.5 sweep so they're
  documented); **B.8 Part 1** outcome capture complete + verified end-to-end.
- **WS-4a landed early + WS-4b before the 6.5 sweep** — `docs/system-model.md` + the
  `docs/wiki/` skeleton + the wiki skills exist; the **preserved excellence-walk
  source is ingested into the wiki** (and may then retire into its `raw/` layer); the
  code architecture is cold-ingested; 6.5 authors into the wiki's reserved section.
- `ruff + mypy + pytest + pytest -m ux` green.

---

## Phase 4.7 — The app knows itself (v1.0.7)

> The epic where the product becomes **self-documenting** and gains a **doc-grounded
> assistant** — both built on the v1.0.6 wiki substrate — plus the pre-public quality
> hardening (the old "Sprint PV", minus the type scan, which moves to Phase 4.8 with
> the blueprint split). **Blocked by:** v1.0.6 tag (the wiki must exist). **Blocks:**
> v1.0.8.

### Governance extraction (moved from v1.0.6 — lands early)

> **Moved here 2026-06-12** from v1.0.6 §Phase 4.5. Lands **early in v1.0.7**,
> before/alongside `feat/self-documenting-wiki`, so the self-documenting loop has **one
> canonical constitution to lint against**. Depends on the wiki proving out (the v1.0.6
> tag). The `audience:` tag convention it shares with the access plane already landed in
> v1.0.6 (WS-4b + `SCHEMA.md`); this is the rule-extraction half.

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
- **Open implementation sub-decisions (resolved in the WS-4 design session at the top
  of v1.0.7):** (i) Governance home name/location — `raw/` vs `docs/governance/` vs
  root `GOVERNANCE.md` (lean: `docs/governance/`); (ii) per-doc extraction
  boundaries (exact spans); (iii) `AGENTS.md` = critical-rules-inline-with-pointer
  vs pure-shell-import.
- **Payoff:** vision-alignment auditing reads ONE canonical constitution; the
  pre-release `wiki-lint` gate can guard it directly; "consistency tracks
  enforcement" (the Q2 finding) extends to the vision itself.

### The self-aware capability (built on the WS-4 wiki)
| Branch | Design-first? | Key work |
|---|---|---|
| `design/self-documenting-loop` → `feat/self-documenting-wiki` | **yes** | The **autonomous** self-documenting / self-tuning docs loop — the wiki ingests + lints itself on change so the docs track the code without a human author. Autonomy is the goal, **but designed performant + not overdone** (per the steer): a **Haiku-class** model, **bounded triggers** (not per-commit), cost-aware. The design pass settles trigger / cost / scope before any build. **Model strategy (recorded 2026-06-12 — design input, not a hard lock):** *warm-start* — the capable session model runs the WS-4b cold-ingest + a short calibration window, and its produced pages are harvested as **baked-in few-shot exemplars**; **Haiku then runs steady-state diff-passes** against `SCHEMA.md` + those exemplars + the deterministic `/wiki-lint` + `/wiki-audit` backstop. Haiku at steady-state is what makes "bounded, cost-aware autonomy" real; the from-scratch taxonomy / synthesis-boundary calls stay on the capable cold pass, which the loop never repeats. |
| `feat/doc-assistant` | (design rides the loop) | The **doc-grounded chat assistant** — *"a product that knows itself."* Both users and devs ask "how do I…" questions; it answers from the committed `docs/wiki/` **with citations** (the LLM-wiki **query** op as a chat). **Haiku model, reuses the user's existing Anthropic key** (no new credential). A public UX/DX feature → **ships in v1.1.0.** |

> **Both rows above build on a shared substrate — the project's *Memory* function,
> form-found as a modular `recall/` package.** Retrieval is **hybrid** (prebuilt
> wiki-map + `git grep` base, agentic drill-down) and *feeds* the Haiku context with
> cited source units; a **user/dev audience toggle** + **model-detected progressive
> disclosure** gate scope; the self-documenting loop reuses the same **$0, no-LLM
> embedding/index refresh** (rides `.last_ingest_sha`). The tier model, the two
> cross-cutting planes, the staged/eval-gated build, and the **reuse/extraction
> contract** live in [`memory-architecture.md`](memory-architecture.md) — read it
> before designing either branch.
>
> **Scope (2026-06-09 re-cut):** the previously post-v1.1.0 **vector tier (Stage 2)** and
> **S4 structure index** are pulled into v1.0.7 as **eval-gated in-epic** steps — build the
> Stage-1 assistant, measure on real questions, add them *only if* the misses justify it,
> before the v1.1.0 cut — so the **complete** memory system can ship at the public tag.
> Deeper interaction memory (**S5 P2–P4**) stays **held** pending its retention/forgetting
> policy. Details in [`memory-architecture.md`](memory-architecture.md) "Staged build".

### Pre-public hardening (grounding + tone; the old Sprint PV, minus the type scan)
**Shared prerequisite (human, not a branch):** a clean-corpus rebuild from a real git
**clone** (NOT a folder copy — it drags the gitignored `db/resume.sqlite`), then
regenerate the corpus from real JDs. The v1.0.6 walkthrough already starts producing
the real labels these consume.

| Branch | Depends on | Key work |
|---|---|---|
| `eval/live-shakedown-labels` (PV-1) | corpus rebuild + v1.0.6 capture | Run the v1.0.4 loop end-to-end on the real corpus: Annotate-tab bootstrap with grounding scorers → annotate → collate → `expected.json`. Deliverable: real `bootstrap.json` + `annotations.json` under `evals/fixtures/real/` (gitignored, PII) + a `TUNING_LOG.md` entry. **Unblocks PV-2.** |
| `eval/grounding-calibration` (PV-2) | PV-1 | The **calibrated layers (B)**: calibrate the L0 tolerance bands (`hardening.py`) + the eval-only L1/L2 NLI/MiniCheck thresholds (`evals/grounding_signals.py`) against the PV-1 labels; report precision/recall per detector; wire the calibrated groundedness score into `eval_composite` / score-over-time + the tuning gate; close the [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) "B (deferred)" note. **L0 stays hot-path-safe; L1/L2 stay eval-only** (Key Decision #4). |
| `tune/cover-letter-opener` (PV-3) | corpus rebuild + tuning loop | Fix the throat-clearing/hedging opener (tripped `tone` 1/5 in v1.0.3). A worked-example `SYSTEM_PROMPT` candidate (the rule lives in the **non-overridable** `_COVER_LETTER_RULES_BLOCK`) via the in-browser A/B; A/B `--suite real` (n≥3); **user promotes** → edit `analyzer.py` + **bump `PROMPT_VERSION`** + TUNING_LOG entry. After PV-2 so groundedness is calibrated. |

> **Sequence decision (2026-06-12): hardening stays in v1.0.7, *before* the v1.0.8
> blueprint split.** Freeze behavior → do the no-behavior-change refactor → ship; the
> surfaces barely overlap (hardening lives in `evals/` · `analyzer.py` · `hardening.py`
> · a thin dashboard slice, while blueprints decomposes `app.py` routes). If this epic
> overflows, the hardening sprints (PV-1…PV-3) are the clean cut to a later 1.0.x epic
> **after v1.0.8** — safe precisely *because* the overlap is low (calibration lands
> cleanly on the new structure). Don't pre-create that epic until needed.

Then: `chore/version-bump-v1.0.7`.

### v1.0.7 tag criteria
- The self-documenting loop runs (autonomous, bounded, cost-aware), and the
  **doc-grounded assistant answers from the wiki with citations** (Haiku, user's key).
- **Governance extraction landed** (moved from v1.0.6, 2026-06-12): the canonical
  rules live in one home with agent rule-access preserved via `@import`/pointer, and
  the 3 open sub-decisions were resolved in the WS-4 design session.
- PV-1 real labels exist; PV-2 calibrated groundedness live on `--suite real` + the
  dashboard + consumed by the tuning gate; PV-3 `tone` holds with `PROMPT_VERSION` bumped.
- `ruff + mypy + pytest` green.

---

## Phase 4.8 — Monolith → blueprints (v1.0.8)

> The dedicated structural epic: decompose the 6,290-LOC / 75-route `app.py` into
> Flask blueprints. Placed here — **after the product is feature-complete and before
> the public cut** — so v1.1.0 ships on clean architecture (the showcase goal) while
> the risky refactor stays out of the public-release packaging. **A new epic is
> justified** because WS-1 must be a dedicated, low-churn window — it **MUST NOT
> interleave** with any feature sprint (it rewrites routes nearly every branch
> touches; 67 test files import from `app`). **Blocked by:** v1.0.7 tag. **Blocks:**
> v1.1.0.

- `design/app-blueprints` — **design session first** (free; can run earlier): blueprint
  seams (analysis · generation/cover-letter · corpus · dashboard · user/config ·
  templates) & naming; shared-helpers home (`_sse`, `_error_detail_payload`,
  `_safe_username`, `_within`); app-factory vs. module-global `app`; SSE routes; the
  67 test-file imports; `route-security-lint` hook compatibility (it currently targets
  `app.py`).
- `refactor/app-blueprints-*` — the decomposition itself, one seam per branch where
  feasible. Preserve the `_safe_username`/`_within` gate + its lint hook on every
  moved route.
- **Absorbs the type-annotation scan (PV-4 = WS-2 increment 1):** annotate route
  returns with `flask.typing.ResponseReturnValue` **as the routes move** (or flip
  `check_untyped_defs = true`), scoped to the whole post-v1.0.4 surface. Doing it here
  avoids annotating the monolith and then re-doing it post-split. The full
  `mypy --strict` ratchet + a typed `context_set` is the post-public **WS-2-full**.
- **Deferred UX: wizard back-navigation.** The wizard rail (`wizardGoTo`, the
  `.wizard-step` buttons in `templates/index.html`) advances forward but offers no
  per-step **back** affordance — a first-time user who misclicks a step has no way to
  step back. Deferred here (decided 2026-06-10, during the onboarding E2E-blocker
  sprint) because back-nav is cleanest to add once the wizard's route/state handling
  is reorganized in the blueprint split, rather than bolted onto the monolith. Add a
  visible "← Back" control wired to the existing step model when the wizard seam moves.

Then: `chore/version-bump-v1.0.8`.

### v1.0.8 tag criteria
- `app.py` decomposed into blueprints; the `_safe_username`/`_within` gate + its lint
  hook hold on every moved route; all 67 test files import cleanly.
- Route returns annotated (PV-4) — `check_untyped_defs`-clean over the post-v1.0.4 surface.
- `ruff + mypy + pytest + pytest -m ux` green; **no behavior change** (pure refactor).

---

## Phase 5 — Public release (v1.1.0)

**Blocked until v1.0.8 tagged. The v1.1.0 tag is owned by the user** — the public cut of the **complete** product: the assistant + self-documenting wiki (v1.0.7) on **clean blueprints** (v1.0.8). There is no external deadline; completeness and polish gate the tag, not a clock.

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
- **Type-annotation scan of all post-v1.0.4 changes** — **delivered by Phase 4.8
  (WS-1, PV-4 = WS-2 increment 1)**, where route returns are annotated as the monolith
  splits into blueprints. At the v1.1.0 cut this is a *verify-it-held* check, not fresh
  work: confirm a full `mypy` pass with `check_untyped_defs` enabled (or the annotated
  signatures) stays clean over everything that landed across the post-v1.0.4 stream
  (through the blueprint split), so no untyped function body slipped through unchecked.
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

## Post-public — the 1.1.x epic series

> After the v1.1.0 public tag, work resumes as the **1.1.x epic series** (1.1.1,
> 1.1.2 …; the patch digit is the epic, exactly as pre-public). These are
> **scheduled** — distinct from the [`nursery.md`](nursery.md) deferred-idea bed.
> Each heavy lever gets its own **design-spike** before code. Ordering across 1.1.x is
> decided when we arrive; items may pull earlier if circumstances change.

**1.1.1 (first post-public epic) — candidates:**
- **paged.js engine replacement (B.13)** — replace the end-of-life in-browser
  paged.js v0.4.x pagination engine (the v1.0.5 fix only *contained* its throws; PDF
  uses Playwright natively and is unaffected). A real render-engine project →
  **design-spike first** (fidelity + constraints + replacement choice).
- **Local + alternative LLM providers** — a **provider abstraction** so users pick
  **local** (Ollama / llama.cpp) or **alternative** (OpenAI / Gemini / …) models, not
  just Anthropic. Strong local-first/privacy fit (local = nothing leaves the machine).
  Architectural — touches `analyzer.py` (the single LLM boundary) → **design-spike
  first**. Generalizes every call, including the v1.0.7 assistant.
- **B.8 Part 2 — outcome-weighted recommend** — boost bullets / summaries / templates
  that came from applications that actually got interviews (closes the loop). Data-gated
  on the outcomes accruing from v1.0.6 onward; **nominally 1.1.1, but may pull earlier
  into a late 1.0.x sprint if enough real feedback lands first.**

**Recurring / continuing workstreams:**
- **WS-2-full — strict typing ratchet.** Continue PV-4 (delivered in v1.0.8): mypy
  toward `strict = true` (per-module ratchet) + model the `context_set` contract as a
  typed spine. Builds on the v1.0.8 blueprint split.
- **WS-3 — recurring test-suite engineering-design pass.** Periodic review of the
  ~955-test suite (redundancy, slow tests, coverage gaps, fixture dup). Define cadence
  + what "good" looks like.

*(WS-1 (the monolith split) and the doc-grounded assistant are **not** here — they
moved **pre-public** into v1.0.8 and v1.0.7 respectively, so v1.1.0 ships with both.)*

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
| `docs/dev/nursery.md` | Deferred-but-alive feature ideas (value/effort/risk-tagged) |
| `docs/dev/excellence-walk/` | Preserved raw source from the 2026-06-07 excellence walk (→ WS-4 wiki) |
| `docs/PRODUCT_SHAPE.md` §11 | The seven-functions system self-model + the WS-1…WS-4 workstreams |
| `evals/TUNING_LOG.md` | Baseline floors; prompt change history |
| `docs/dev/AGENT_FAILURE_PATTERNS.md` | Failure patterns to avoid |
| `docs/architecture.md` | Module map, LLM routing |
| `C:\Users\iam\.claude\research\resume-eval-2026-05\followup.md` | 25-item Phase 1 checklist |
| `docs/dev/perf/R1_BENCHMARK_2026-05-26.md` | R1 diagnosis (Phase 2 start point) |
| `C:\Users\iam\.claude\research\resume-eval-2026-05\report.md` | Tool recs (Promptfoo, MiniCheck, DeBERTa) |
