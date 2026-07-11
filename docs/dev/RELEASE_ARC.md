# sartor. — Release arc: v1.0.2 → v1.1.0

> **Written:** 2026-05-28 planning session
> **Status:** approved — executing phase by phase
> **Authoritative for:** branch sequence, architectural decisions, acceptance criteria
> **Do not edit without user sign-off** — changes here affect multiple future sessions
> (the sign-off gate is the charter [amendment ceremony](../governance/charter.md) applied
> to the arc; constitutional changes also need a `CHANGELOG.md` entry + owner sign-off at merge)

---

## Version map

| Version | Theme | Publicly visible? | Notes |
|---|---|---|---|
| v1.0.1 | Solid app | No | **Tagged 2026-05-28 at commit `49f2ac9`** |
| v1.0.2 | Eval apparatus | No | **Tagged 2026-05-30 at commit `2398f4e`** |
| v1.0.3 | R1 Phase 2 | No | Analyze quality recovery (✓ context_probe + typed hidden_qualities) **then** the two-pass split for speed (≤72s) without giving quality back. **Tagged 2026-06-02 at commit `59b6d9c`** |
| v1.0.4 | Eval tuning loop | No | Real-data, human-in-the-loop, model-assisted prompt improvement; internal/dev tooling. **Tagged 2026-06-02 at commit `072e290`** |
| v1.0.5 | UI/UX redesign | No (internal until v1.1.0) | Wizard redesign + WYSIWYG + diagnostics/tuning console & annotation tab; establishes the design system. **Tagged 2026-06-07** — all seven §Phase 4 tag criteria met; gate green incl. `pytest -m ux` |
| v1.0.6 | Walkthrough polish + knowledge substrate + corpus completion | No (internal until v1.1.0) | E2E-walkthrough-driven UX polish (Sprints 6.1–6.5) + the **WS-4 LLM-wiki substrate** (front-loaded; before the 6.5 sweep) + corpus-item completers (**B.4** ExperienceSummaryItem, **B.5** Skill-as-Corpus-Item) + **B.8 Part 1** (outcome capture). **Tagged 2026-06-15** — all §Phase 4.5 tag criteria met; the E2E re-walk verification pass was waived as non-blocking for this internal tag (tracked to v1.0.7); gate green incl. `pytest -m ux`. See **Phase 4.5**. |
| v1.0.7 | The app knows itself | No (internal until v1.1.0) | The autonomous self-documenting/self-tuning wiki loop + the doc-grounded **assistant** (Haiku, reuses the user's key) + pre-public hardening (grounding-calibration B · cover-letter tuning). **Not yet tagged.** See **Phase 4.7**. |
| v1.0.8 | Monolith → blueprints (WS-1) | No (internal until v1.1.0) | Decompose the 8,251-LOC / 93-route `app.py` into Flask blueprints (dedicated structural epic); **absorbs the type-annotation scan** (WS-2 increment 1). Public ships on clean blueprints. **Not yet tagged.** See **Phase 4.8**. |
| v1.0.9 | Docs, docs-site & type hardening | No (internal until v1.1.0) | The final pre-public polish epic. **Docs:** README ICP-ladder + design doc + this schedule landed in the 2026-06-29 session; dev-home depth + wiki content pass + Fumadocs adapter/deploy (+ Layer-B API spec) + doc-merge-gate CI remain. **Type hardening:** complete the `mypy --strict` ratchet so strict typing holds for all non-test code (WS-2-full's strict half, pulled pre-public — ~146 mechanical errors / 18 modules + roster 51 already-clean). Strategy: [`documentation-architecture.md`](documentation-architecture.md). See **Phase 4.9**. |
| v1.1.0 | Public release | **Yes** | **Tag owned by the user** — the public cut of the complete product (assistant + self-documenting wiki + clean blueprints + documentation & docs-site). GitHub push is part of this event |

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

#### `eval/sartor-metrics` ← after PR gate confirmed

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
- Minimal UI: "Got sartor" / "Got rejection" / "No response" outcome buttons in Prior Applications panel; auto-set `sent_at` when status → `submitted`

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

#### `eval/pareto-dashboard` ← after sartor-metrics (needs eval_composite)

New Pareto frontier panel at top of `/_dashboard`:
- X = wall-clock latency (log scale); Y = eval_composite (0–5)
- Dots: color = PROMPT_VERSION; size = cost; hover = full breakdown
- Dashed polyline connecting successive baselines chronologically
- Summary: "Most recent change (v → v): Δ composite, Δ latency, Δ cost. [Pareto-improving / On frontier / Dominated]"
- Secondary: p50/p90 latency trend + cost trend over time

---

### v1.0.2 tag criteria

- All 25 `followup.md` checklist items checked
- schema_version 3 baseline live; anchor/exploration split live; Promptfoo YAML running; PR gate confirmed on dry-run; sartor rubric + metrics live; applications tracker shipped; Pareto frontier visible
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
| `feat/run-eval-from-console` ✓ DONE (merged `3a91bea`, 2026-06-07) | grounding-scorers | Extracted a `run_suite(...)` core from `runner.main()` (`EvalRunResult` return + optional `progress` sartor; default path byte-identical, mirrors `bootstrap.py`'s `main`/`run_pipeline_over_jd_texts` split) + a localhost SSE `POST /api/eval/run`. "Run eval" control on the Quality tab (suite/subset/grounding + cost-band `confirm()` consent + reload); collate's copy-the-command dead-end replaced with a visible command **and** a "Run this fixture" button. Closes the mandatory CLI hop in the loop. No `PROMPT_VERSION` bump. **`run_suite` is the precondition `feat/tuning-tab-ab` consumes.** |
| `feat/tuning-tab-ab` ✓ DONE (merged `812e6bb`, feature `5f708f7`, 2026-06-07) | run-eval-from-console | Replaced the Tuning stub with a real in-browser A/B: pick an `analyzer._BASE_SYSTEM_PROMPTS` constant, draft/paste a candidate, run baseline+candidate evals via a dedicated localhost SSE `POST /api/tune/run` (drives `run_suite` twice + `analyzer.prompt_overrides()`), delta rendered with `evals/tune.py` (`load_scores`/`build_delta_table`/`format_delta_table`). Mirrors `/api/eval/run`'s contract incl. optional corpus-seed mode. **Promote stays the agent's job** — no route edits `analyzer.py`. No `PROMPT_VERSION` bump; no new dep. |
| `docs/tuning-loop-discoverability` ✓ DONE (merged `8c6cb7d`, 2026-06-07) | tuning-tab-ab | In-app diagnostics-modal/pill/settings copy advertises the now-interactive loop; the in-browser console-loop walkthrough lands in `evals/README.md` (the dev-doc home) with `walkthrough.md` carrying only a flag + link to it; `GROUNDING_METRIC.md` "B (deferred)" note updated to note the label-producing loop is now browser-driven. Docs only. |

**Sequencing:** these branches carry a real ordering dependency —
`feat/run-eval-from-console`'s `run_suite` extraction is the precondition for
`feat/tuning-tab-ab` — so a session owns its branch end-to-end and does not start a
later branch in an earlier one's session. (When sessions run concurrently they do so in
*separate* isolated worktrees; the working model is charter
[**W-1**](../governance/charter.md) parallelism, not global serialization.) Each branch
is independently shippable.
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
(ExperienceSummaryItem) and **B.5** (Skill-as-Corpus-Item), and **B.8 Part 1** (outcome
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
- **First run:** welcome to sartor — a career-experience manager that tracks +
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
| `feat/experience-summary-item` | **B.4** | Per-role intro paragraph as a multi-variant Corpus Item (the asymmetry-matrix #1 pain — the line a recruiter reads first). Mirrors `SummaryItem`; maps to JSON Resume `work[].summary`. *(Resolved 2026-06-12: shipped end-to-end as `ExperienceSummaryItem` (+ tag), FK → `experience.id`, migration `0008` w/ backfill from the legacy `Experience.summary` column. **Two user-directed departures from a literal `SummaryItem` mirror, settled in an interactive clarification:** (1) **opt-in, not auto-applied** — a role intro reaches the résumé only when the user turns on the Compose **"Add role intros"** toggle for that application AND picks a variant (`composition_overrides.use_experience_summaries` + `chosen_experience_summary_ids`; sentinel `0` = explicitly cleared); toggle off = byte-identical generate prompt → analyze→generate cache untouched. (2) **Full WYSIWYG** — a chosen intro is injected into the frozen `career_corpus` snapshot at generate time (`_apply_chosen_experience_summaries`, mirroring `_apply_chosen_summary`) so it reaches the LLM-tailored résumé **and** the JSON-resume/PDF preview, not the preview alone. Batched Haiku `recommend_experience_summaries` (keyed by `experience_id`, mirrors `recommend_bullets` shape); `_corpus_block` emits a conditional `<summary>` + guide; **`PROMPT_VERSION` → `2026-06-12.1`**. Experience-scoped CRUD routes + a recommend route; Compose per-role picker + corpus per-experience editor. Corpus-mode-only prompt change → covered by unit + UX + a byte-identity test, no paid smoke. **Also fixed an in-scope pre-existing Compose-save clobber** (`_togglePositioningPin` now routes through the canonical `_collectCompositionState()`, so a summary pin no longer wipes `bullet_order`/`pinned_title_ids`; regression-locked). ruff/mypy ✓, pytest **1127/1127** incl. `-m ux`. No new dep.)* |
| `feat/skill-group-item` | **B.5** | ~~Curated skill *clusters* per JD~~ → **individual skills as a Corpus Item** (the "clusters" framing was dropped in an interactive clarification with the owner — no grouping; each skill is its own item, mirroring **Bullet**, the fully-Corpus-Item type). *(Resolved 2026-06-13: the flat `Skill` row gains the bullet lifecycle — `is_active` / `is_pending_review` / `source` / `display_order` / timestamps + a `SkillTag` join — via migration `0009` (ALTER `skill` + `skill_tag` + backfill: legacy rows → `imported`/active/approved, `display_order` preserving the prior name order). **Two Haiku calls:** `recommend_skills` orders + curates the approved set per JD (auto-applied like bullets; user pins/drops/reorders), and — a **user-authorized scope addition beyond this row** — `suggest_skills` is a **grounded generator** proposing skills the JD wants AND the corpus evidences (evidence-or-nothing), landing as **pending** (`source='llm_proposed'`) for approve/deny; the human gate is the grounding backstop (pending skills never reach the recommend set / preview / prompt until approved). `composition_overrides` gains `pinned_skill_ids` / `excluded_skill_ids` / `skill_order` (persisted only when non-empty → default path byte-identical); recommend output on `llm_skill_recommendations`. **Reach: download + preview** — deterministic `_collect_skills` curates the preview `skills[]`; generate-time `_apply_recommended_skills` patches the candidate's skills list so the LLM-authored download surfaces the same set (no-op/byte-identical when nothing to apply). **`PROMPT_VERSION` → `2026-06-12.2`** (two new system prompts). Compose **Skills** card (Tailor/Suggest + pin/drop/reorder + pending lane) + Career-corpus **Skills** editor (add/retire/tag + approve/deny). 5 route families; corpus-mode-only prompt change → unit + UX + byte-identity coverage, no paid smoke. ruff/mypy ✓, pytest **1169/1169** incl. `-m ux`. No new dep.)* |

### WS-4 substrate — LLM-wiki knowledge architecture (split: WS-4a front-loaded, WS-4b after 6.6)
> From the excellence walk (WS-4). **Split** because the doc/whys content needs a home
> **early** — the preserved excellence-walk source (now tracked at
> [`excellence-walk/`](excellence-walk/)) must move into the wiki **very soon** —
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
   [`excellence-walk/excellence-walk.md`](excellence-walk/excellence-walk.md) +
   [`excellence-walk/q1-overview.md`](excellence-walk/q1-overview.md).)*
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
   [`excellence-walk/`](excellence-walk/) raw source** into synthesized wiki
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
   — this pass re-reads the architecture anyway. **✓ LANDED `a0a1cb2` (2026-06-13)** — 16
   code pages cold-ingested (`path:line`-grounded); `audience:` tags stamped; both diagram
   drifts fixed. Wiki diff-refreshed to HEAD on 2026-06-14 (`chore/wiki-refresh-px-v106`).
   **Next: Sprint 6.5.**

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
| `feat/help-pattern-component` | (mechanism) | Build the reusable a11y-safe help primitive once (per-tab description + per-panel summary + contextual tooltip; real `aria` wiring; no color-only meaning). **Kickoff KW10/KW3:** the interaction model is a first-view auto-modal (graceful fade-in, closes on click-away) + a persistent (i)-circle on every significant block that re-opens that block's modal — the modal carries the canonical pathfinding copy, the inline block text is the short form. *(Resolved 2026-06-14: shipped the **mechanism only**. ONE shared `#helpModal` (`.cb-modal` clone) + ONE generic `openHelpModal(blockId, triggerEl)` **factored from the duplicated per-modal pattern** (Esc / Tab focus-trap / backdrop click-away / focus-restore; the five existing modals untouched). A `_HELP_REGISTRY` keyed by block id is the **extension point** — the next branches add per-surface copy by adding keys, **no engine change**; this branch ships one minimal demo entry (`panelUser`), no per-surface copy. `_initHelp()` injects a `.help-info` (i)-circle into each registered `.cb-panel` header (mirrors `.compose-order-info`; `.has-help-icon` keeps title+icon left, chevron right) + an optional inline short-form (`aria-describedby`-linked). aria: icon `aria-haspopup=dialog`/`aria-controls`/`aria-expanded` + `aria-label`; **no color-only meaning** (literal "i" glyph). First-view welcome auto-modal shows **once-ever** via a `cb_help_seen:<block>` **localStorage** flag (the app's first client-side storage — owner-approved; throwing-store-safe). UX suite kept green by default-suppressing the welcome (autouse `_help_welcome_default_seen` fixture + `show_welcome` opt-in marker — a global first-view modal's z-1000 backdrop would otherwise obscure controls). `test_20260614_help_pattern.py` (6 cases) + `#helpModal` added to the axe gate + a `Help` selector class. Front-end only — no route, no LLM, no `PROMPT_VERSION` bump, no dep, no migration. ruff/mypy ✓, pytest **1197/1197** incl. `-m ux`.)* |
| `feat/education-tailor-corpus-wizard` | #1 + #18 | Apply the pattern across Tailor / Career corpus / Résumé templates / Candidate memory + each wizard step. Plain-language, assumes no technical background. **Authors into the WS-4 wiki's reserved user-facing section.** **Kickoff KW3:** the new-user first-run sequence (welcome → add-user → post-ingest → tailor → clarify/skip → recommended-corpus → template/preview → generate → live-preview → cover-letter) is fully specced in the Sprint 6.0 KW3 detail — author from there; new-users-only (empty → first-ingest). |
| `feat/education-diagnostics-annotate` | #15 + #20 + #22 | Apply across all diagnostics tabs + the annotate tab: verdict legend + per-option tooltips; annotate instructions rewritten for lay users + auto-expand the bootstrap panel when no fixtures exist; a summary on every panel. **Kickoff KW9/KW13:** a first-expand modal per diagnostics tab/panel (mirror the user-side pattern); explain the grounding box, the synthetic/smoke options, and *why* groundedness/tuning/annotate are empty + what populates them. |
| `docs/eval-stack-install-guide` | #17 | A user-facing install/prepare guide for the tuning/grounding/eval stack — **authored from the excellence walk's Q3 deliverable** (`output/_dev-notes/Q3_downloads_draft.md`; facts verified against `pyproject.toml` + `install.md` + `CONTRIBUTING.md`) — plus a README/`install.md` "what gets downloaded & why" section + an in-app pointer where the stack is needed. *(Resolved 2026-06-15: shipped the **user layer** only. The dev-tier provenance already existed — the **committed** `docs/dev/excellence-walk/q3-downloads.md` (the live source; the cited `output/_dev-notes/` draft is gitignored + absent in-clone) + the `audience:dev` wiki page `non-dependency-downloads.md` — and `CONTRIBUTING.md` "Grounding signal scorers" owns the exact eval-stack commands. So #17 = a plain-language **"What gets downloaded & why"** section in `docs/install.md` (`what-gets-downloaded` anchor) + a README "what actually downloads" pointer beside "What gets saved" + a one-sentence in-app pointer on the dashboard `dashQuality` help body. Eval stack kept as **flag-and-link** (→ `CONTRIBUTING.md`), no dev commands on user surfaces (honors the dev/user doc boundary). All figures re-verified vs `pyproject.toml` + `install.md` + `CONTRIBUTING.md`. Docs + one help-copy line — no route, LLM, prompt, dep, or migration; `PROMPT_VERSION` unchanged. ruff/mypy ✓ (162), pytest **1212/1212** incl. `-m ux`.)* |

Then: `chore/version-bump-v1.0.6` (pyproject, CHANGELOG, tag) + re-check the
RELEASE_CHECKLIST risk register.

### v1.0.6 tag criteria

> **✓ MET — tagged `v1.0.6` on 2026-06-15.** Sprints 6.1–6.6 + the a11y axe gate + B.4/B.5
> + WS-4a/4b all merged; the E2E re-walk verification pass (eval/tuning + `V1_0_5_VERIFICATION.md`
> signing + B.8 outcome-data confirmation) was waived as non-blocking for this internal tag
> (tracked to the v1.0.7 pre-public hardening pass). Gate green incl. `pytest -m ux`.

- The E2E-walkthrough findings are triaged; tag-blocking ones fixed (overflow spills
  to a later 1.0.x epic — not a new pre-commitment).
- Sprints 6.1–6.6 merged; the a11y axe gate is live and green.
- **Corpus-item completers B.4/B.5 merged** (before the 6.5 sweep so they're
  documented); **B.8 Part 1** outcome capture complete + verified end-to-end.
- **WS-4a landed early + WS-4b before the 6.5 sweep** — `docs/system-model.md` + the
  `docs/wiki/` skeleton + the wiki skills exist; the **preserved excellence-walk
  source is ingested into the wiki** (and may then retire into its `raw/` layer); the
  code architecture is cold-ingested (WS-4b ✓ `a0a1cb2`); 6.5 authors into the wiki's reserved section.
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
- **Implementation sub-decisions — RESOLVED 2026-06-15** on `design/governance-extraction`
  (the design half of 7.2); full design in
  [`governance-extraction-design.md`](governance-extraction-design.md): (i) Governance home =
  **`docs/governance/`** (a directory: `charter.md` + `enforcement.md` + `metrics.md`);
  (ii) per-doc extraction boundaries fixed by the constitution's `[src: …]` citation map
  (six source docs lose their canonical rule, keep descriptive prose + a pointer); (iii)
  `AGENTS.md` = **critical-rules-inline-with-pointer** (a pure import shell would strip
  guardrails from non-Claude agents that read it raw — F-gov-05). Graduation scope = **all
  four** draft files (the three above + `extraction-playbook.md` → `docs/dev/EXTRACTION.md`).
  The drift-reconcile (≈8 of the draft's "owed corrections" already landed in v1.0.6 →
  cite-don't-refix) + the four PX foldings (PX-23/24/27/28) are specified there. **Enforcement
  portability (owner agenda item) — DECIDED: split** — fix PX-24/PX-28 hooks in place on
  `feat/`; migrate the portable rules to a tool-agnostic shared core (git-hooks + Claude
  wrappers + CI backstop) on a follow-on branch clustered with the v1.0.8 gate epic when the
  remote/CI activates (Sprint 8.7).
- **Payoff:** vision-alignment auditing reads ONE canonical constitution; once
  `wiki-lint`'s scope is extended to `docs/governance/` + markdown links it can guard
  the home directly (today wiki-lint is `docs/wiki/`-scoped — `[[backlinks]]` +
  `path:line` existence only — so the new governance pointers are not yet gate-checked);
  "consistency tracks enforcement" (the Q2 finding) extends to the vision itself.

### The self-aware capability (built on the WS-4 wiki)
| Branch | Design-first? | Key work |
|---|---|---|
| `design/self-documenting-loop` → `feat/self-documenting-wiki` | **yes** | The **autonomous** self-documenting / self-tuning docs loop — the wiki ingests + lints itself on change so the docs track the code without a human author. Autonomy is the goal, **but designed performant + not overdone** (per the steer): a **Haiku-class** model, **bounded triggers** (not per-commit), cost-aware. The design pass settles trigger / cost / scope before any build. **Model strategy (recorded 2026-06-12 — design input, not a hard lock):** *warm-start* — the capable session model runs the WS-4b cold-ingest + a short calibration window, and its produced pages are harvested as **baked-in few-shot exemplars**; **Haiku then runs steady-state diff-passes** against `SCHEMA.md` + those exemplars + the deterministic `/wiki-lint` + `/wiki-audit` backstop. Haiku at steady-state is what makes "bounded, cost-aware autonomy" real; the from-scratch taxonomy / synthesis-boundary calls stay on the capable cold pass, which the loop never repeats. **Design half DONE 2026-06-16** (`design/self-documenting-loop`): trigger / cost / scope settled — **trigger** = bounded checkpoint (close-out / pre-tag) + the freshness witness hook escalates its message past a drift threshold (no scheduler); **cost** = Haiku diff-pass, warm-start exemplars by-reference, cost-surfaced-before-spend, per-run page cap; **scope** = `docs/wiki/`-only (the cross-document link/cite checker is the separate tracked follow-on, not absorbed). **Orchestration** = a new `/wiki-self-update` command + a Haiku `wiki-scribe` subagent + a separate Haiku read-only `wiki-grounding-auditor` subagent (author≠auditor) + `/wiki-lint` as the deterministic gate; the loop **never auto-commits** (always a reviewable diff). Full spec in [`self-documenting-loop-design.md`](self-documenting-loop-design.md). **feat/ half DONE 2026-06-16** (`feat/self-documenting-wiki`): built per the design §4 — the `/wiki-self-update` orchestrator + the Haiku `wiki-scribe` + the read-only Haiku `wiki-grounding-auditor` subagents + the freshness-hook drift escalation; dev-harness only (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Owner-approved: the loop's **first real run** performed the consolidated v1.0.7 wiki refresh on this branch ([`docs/wiki/log.md`](../wiki/log.md)). |
| `feat/doc-assistant` | (design rides the loop) | The **doc-grounded chat assistant** — *"a product that knows itself."* Both users and devs ask "how do I…" questions; it answers from the committed `docs/wiki/` **with citations** (the LLM-wiki **query** op as a chat). **Haiku model, reuses the user's existing Anthropic key** (no new credential). A public UX/DX feature → **ships in v1.1.0.** **DONE 2026-06-16** (`feat/doc-assistant`, 7.5 — the Stage-1 build per [`memory-architecture.md`](memory-architecture.md) "Stage 1"): the two free retrieval tiers + S5-P1 session buffer landed as generic, injected `Source`s in [`recall/sources/`](../../recall/) (`WikiSource` S1 / `GitGrepSource` S2 / `SessionSource`), kept project-agnostic by a new `test_recall_sources_no_hardcoded_roots` guard; the Haiku **avatar** (`analyzer.avatar_answer_streaming` + `AVATAR_SYSTEM_PROMPT`, its own `AVATAR_PROMPT_VERSION`) **honors charter C-6** (all LLM calls stay in `analyzer.py` — **owner decision D1=A**, no charter amendment); the SSE route is the first module of a new `blueprints/` package ([`blueprints/assistant.py`](../../blueprints/assistant.py), `POST /api/assistant/ask`, no `app.py` import — the v1.0.8 split is a *move*), holding the callback wiring (source roots + SCHEMA audience rules injected into the generic tiers); a minimal collapsible in-shell panel ships the UX now (the polished public UI stays the v1.1.0 epic). **Owner decisions:** D1=A (avatar in `analyzer.py`), D2=Y (sources parameterized in `recall/sources/`), UI=minimal in-shell panel. **Zero new deps; no migration; résumé `PROMPT_VERSION` unchanged.** |
| `feat/compliance-agent-pilot` | (design done — [`compliance-agent-design.md`](reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md)) | The **compliance-agent pilot** — a read-only **governance drift witness** for the *Regulation* function: the [`/wiki-lint`](../../commands/wiki-lint.md) witness posture turned on the governance surface (per-edit machine hooks → a periodic narrative read of whole-repo coherence). Composes two **existing** primitives — the read-only-subagent pattern (`agents/prompt-archaeologist.md`) + the witness-command pattern (`/wiki-lint`) — so it re-decides nothing. **DONE 2026-06-16** (`feat/compliance-agent-pilot`): new `/compliance-witness` command (`commands/compliance-witness.md`) + read-only **Sonnet** `compliance-witness` subagent (`agents/compliance-witness.md`; `Read`/`Grep`/`Glob`/`Bash` read-only git — **no `Edit`/`Write`/`Task`**, the tool grant *is* the HARD-non-goal enforcement); resolves a pinned sha (`--since` or last tag), delegates the read via `Task`, caps flags (**default 12**, `--cap N`), renders a findings-register table (FLAG/WATCH/AFFIRM + suggested direction) + a `/wiki-lint`-style gate verdict, appends a dated counts line to `docs/governance/compliance-log.md`. **Never edits, never blocks, never commits.** Dev-harness only (no product code/route/LLM-call/dep; `PROMPT_VERSION` unchanged). Lands at **repo-root** `commands/`+`agents/` (the design's `.claude-plugin/` Appendix path predates the 7.1 move). Owner-approved: one supervised **pilot run** against the freshly-graduated `docs/governance/` (born `docs/governance/compliance-log.md`; window `e299ac8`→`1741ab1`, FLAG 1 / WATCH 2 / AFFIRM 3). **Pilot PASSES** the design's self-eval rubric — the one FLAG (CW-01: the `RELEASE_CHECKLIST` 7.2 row left `[ ]` after `feat/governance-extraction` merged) was owner-scored **true drift → precision 1.0 ≥ 0.66** and corrected; the witness caught real drift on its first run against the surface that branch created. |

> **The first two rows above build on a shared substrate — the project's *Memory* function,
> form-found as a modular `recall/` package.** Retrieval is **hybrid** (prebuilt
> wiki-map + `git grep` base, agentic drill-down) and *feeds* the Haiku context with
> cited source units; a **user/dev audience toggle** + **model-detected progressive
> disclosure** gate scope; the self-documenting loop reuses the same **$0, no-LLM
> embedding/index refresh** (rides `.last_ingest_sha`). The tier model, the two
> cross-cutting planes, the staged/eval-gated build, and the **reuse/extraction
> contract** live in [`memory-architecture.md`](memory-architecture.md) — read it
> before designing either branch.
>
> **Stage 0 DONE 2026-06-16** (`feat/recall-skeleton`, 7.4): the substrate *skeleton* —
> the `recall/` package's public types (`Unit`/`Source`/`Scope`/`Context`), the two
> cross-cutting planes, and a working deterministic `assemble()` (RRF fusion + token-budget
> pack) over a shipped `InMemorySource` reference — landed stdlib-only and refactor-immune
> (AST boundary test, no hook). No real source tier yet (S1 wiki/S2 git → 7.5; S3 vector →
> 7.6); no LLM, no route, no dep. The seams the next two rows build on now exist.
>
> **Stage 1 DONE 2026-06-16** (`feat/doc-assistant`, 7.5): the doc-grounded assistant — the
> two free retrieval tiers (S1 `WikiSource` + S2 `GitGrepSource`) + the S5-P1 `SessionSource`
> as generic, injected `Source`s in `recall/sources/`, the Haiku **avatar** in `analyzer.py`
> (C-6 honored — owner D1=A; its own `AVATAR_PROMPT_VERSION`), the SSE route in a new
> `blueprints/` package, and a minimal in-shell chat panel. **Zero new deps.**
>
> **UI relocation DONE 2026-06-16** (`feat/assistant-topbar-modal`, 7.8a): the Stage-1
> in-shell `<details>` chat panel (`#panelAssistant`, parked below the wizard) moved to a
> **fixed top-bar magnifier icon** (`#assistantPill`) opening a **floating, scrollable
> modal** (`#assistantModal`) — one always-findable entry point, reusing the `.cb-modal`
> skeleton + the top-bar-pill-opens-overlay precedent. **Front-end only** — same route /
> avatar / SSE client; `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged; no dep/migration.
> First of a few small UI-polish sprints before the 7.9 tag.
>
> **UI-polish trio DONE 2026-06-17** (`fix/v107-ui-polish-trio`, 7.8b): three small,
> independent fixes from the UI-polish band. (#1) **stray browser windows** — the
> `python app.py` auto-open fired inside the Flask debug-reloader's serving child, which the
> reloader re-executes on every restart → a new window per reload; a pure
> `_should_open_browser()` now opens **exactly once** (supervisor / non-debug single process,
> never the reload child). (#3) **slow application load** — `list_applications` ran `1+2N`
> queries (lazy `Application.runs` + per-app pending count); now `selectinload` + one batched
> `group_by` count → ~3 queries regardless of N, with a constant-query-count regression
> guard. (#4) **new-user stale dropdown** — `showNewUserForm()` clears the leftover
> `#userSelect` value (Cancel restores it). **No prompt/dep/migration**;
> `PROMPT_VERSION`/`AVATAR_PROMPT_VERSION` unchanged. Adds one ledger item (assistant
> doc-coverage). The remaining named UI-polish candidate is **#2 assistant voice softening**.
>
> **Stage 2 DONE 2026-06-16** (`feat/doc-assistant-vector`, 7.6): the S3 `VectorSource`
> semantic tier — static `model2vec` embeddings (`potion-base-8M`, dim 256) + brute-force
> cosine over a rebuildable `db/vector_index/` sidecar, incremental ($0-on-unchanged
> content-hash reuse), built by `scripts/build_vector_index.py`; wired into the assistant
> **"on when available"** (model + index present). **Built ahead of the eval gate at owner
> direction** — the landed Stage-1 assistant tested *too literal / lacking semantic
> flexibility* — a deliberate, documented override: the gate's formal labeled eval stays
> v1.0.8 (Sprint 8.5). New **hard** deps `numpy` + `model2vec` (numpy + tokenizers +
> safetensors, **no torch/onnxruntime**); the `recall/sources/` stdlib boundary test was
> relaxed to admit **`numpy` only** (core `recall/` stays stdlib-only; `model2vec` lives in
> the wiring layer so the substrate stays embedder-agnostic + extractable for the standalone
> Memory package). No migration; résumé `PROMPT_VERSION` unchanged. A probe
> (`scripts/vector_index_probe.py` → `evals/TUNING_LOG.md`) corroborates the owner finding;
> the judge-scored labeled before/after eval is **owed at v1.0.8** (Carry-forward ledger).
>
> **Scope (2026-06-09 re-cut):** the previously post-v1.1.0 **vector tier (Stage 2)** and
> **S4 structure index** are pulled into v1.0.7 as **eval-gated in-epic** steps — build the
> Stage-1 assistant, measure on real questions, add them *only if* the misses justify it,
> before the v1.1.0 cut — so the **complete** memory system can ship at the public tag.
> Deeper interaction memory (**S5 P2–P4**) stays **held** pending its retention/forgetting
> policy. Details in [`memory-architecture.md`](memory-architecture.md) "Staged build".

### Plugin activation — make the dev-tool commands + agents invocable (prerequisite)

> **Flagged 2026-06-13** (owner-directed: "we need to get to this in 1.0.7 at the
> latest"). The `.claude-plugin/` plugin ships **10 commands** (`/wiki-*`, `/eval`,
> `/bench`, `/replay`, `/prompt-tune`, `/inspect-context`, `/tune-from-annotations`)
> and **6 subagents**, but **only its hooks are loaded** — hand-wired into
> `.claude/settings.json`. The commands + agents are **dormant**: never registered
> (no `marketplace.json`, no plugin install), so none surface as slash commands
> (verified 2026-06-13 — none appear in the agent's available-skill list). The "v1.0
> plugin migration" moved the hooks; command/agent activation was never done.

- **Why v1.0.7:** the **self-documenting loop** runs the `/wiki-*` ops, and the
  manifest-proposed **`feat/compliance-agent-pilot`** ships a new `/compliance-witness`
  command + subagent whose design assumes it composes "**existing** plugin primitives,
  both verified present at c6e0437" (`docs/dev/reviews/2026-06-product-excellence/`
  `03-prescriptions/compliance-agent-design.md:196-201`) — but "present" = the files
  exist, not that they load. So v1.0.7 is where the gap bites; activation must land
  **before** the compliance pilot (and ideally before the self-documenting loop, to
  drop the manual command-execution workaround used in v1.0.6).
- **Fix (decide at design time):** register the plugin properly (`marketplace.json` +
  install → commands **and** agents load, and the hooks migrate off the hand-wired
  `settings.json`) — **or** the low-ceremony path (symlink/copy commands into
  `.claude/commands/`, agents into `.claude/agents/`). Either way, correct the
  `CLAUDE.md` "Skill catalog" section, which advertises these as available today.
- **Scope:** dev-harness only, **no product code**. A small `chore/` branch, or folded
  into the compliance-pilot branch as its first step.

### Pre-public hardening (grounding + tone) — MOVED TO v1.0.8 (2026-06-15)

> **Relocated by the 2026-06-15 release-planning session.** The real-data hardening
> below (PV-1 produce labels · PV-2 grounding calibration · PV-3 cover-letter tone)
> **moves out of v1.0.7 into v1.0.8**, where the post-refactor **gated test window** runs
> the **first-ever real-data eval/tuning loop on the *decomposed* code** and a
> **correction sprint** burns its findings (see §Phase 4.8). This takes the 2026-06-12
> escape hatch below one step tighter — the work lands *inside* v1.0.8, holding the
> owner's "all work done by v1.0.8" line. **v1.0.7's tag is now defined by the feature
> set** (self-documenting loop + assistant + governance + plugin activation); the
> synthetic smoke/full eval gate still guards every v1.0.7 commit. The branch detail is
> kept here for reference.

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

> **Citation-format polish MOVED INTO v1.0.7 as a pre-tag sprint (2026-06-19)**
> (`feat/avatar-citation-format`, 7.8d): owner testing found the doc-grounded assistant's
> citations/references render inconsistently — numeric `[N]` markers (from the
> `[{i}]`-numbered context renderer, `analyzer.py:1538`), raw model-invented markdown links
> (the answer body is `textContent`), and a "Sources:" footer listing **all** retrieved units
> (`analyzer.py:1595`), not the cited set. **Moved in from a v1.0.8 deferral at owner
> direction — the last UI-polish before the tag, so 7.9 waits on it**; bumps
> `AVATAR_PROMPT_VERSION`. Requirements:
> [`avatar-citation-format-guidance.md`](avatar-citation-format-guidance.md); granular row in
> [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) (7.8d).

Then: `chore/version-bump-v1.0.7`.

### v1.0.7 tag criteria
- The self-documenting loop runs (autonomous, bounded, cost-aware), and the
  **doc-grounded assistant answers from the wiki with citations** (Haiku, user's key).
- **Governance extraction landed** (moved from v1.0.6, 2026-06-12): the canonical
  rules live in one home with agent rule-access preserved via `@import`/pointer, and
  the 3 open sub-decisions were resolved in the WS-4 design session.
- ~~PV-1 real labels exist; PV-2 calibrated groundedness; PV-3 `tone` holds~~ **→ moved
  to v1.0.8** (Sequence decision 2026-06-15): the real-data hardening runs in the v1.0.8
  gated test window + correction sprint, on the decomposed code. v1.0.7 keeps the
  synthetic smoke/full eval gate.
- **Plugin commands + agents invocable** — the `.claude-plugin/` commands (`/wiki-*`,
  `/eval`, …) and subagents load (registered, not just hooks), so the self-documenting
  loop + compliance pilot run off real slash commands and `CLAUDE.md` "Skill catalog"
  matches reality. (See §"Plugin activation" above.)
- `ruff + mypy + pytest` green.

---

## Phase 4.8 — Monolith → blueprints (v1.0.8)

> The dedicated structural epic: decompose the 8,251-LOC / 93-route `app.py` into
> Flask blueprints. Placed here — **after the product is feature-complete and before
> the public cut** — so v1.1.0 ships on clean architecture (the showcase goal) while
> the risky refactor stays out of the public-release packaging. **A new epic is
> justified** because WS-1 must be a dedicated, low-churn window — it **MUST NOT
> interleave** with any feature sprint (it rewrites routes nearly every branch
> touches; 32 test files import from `app`). **Blocked by:** v1.0.7 tag. **Blocks:**
> v1.1.0.

- `chore/ledger-reduction` (proposed **8.0**, owner-confirmed 2026-06-20) — a tiny reduction
  micro-branch run **before** the structural work: clears the two pure-hygiene carry-forward
  items (the `CONTRIBUTING.md` plugin-section drift from the 7.1 commands/agents move; the
  benign pytest-socket `UserWarning ×2`, a one-line `filterwarnings` entry), dropping the open
  carry-forward ledger below the 8–10 threshold before the blueprint epic begins. Docs/test
  hygiene only; no coupling to the seams.
- `design/app-blueprints` — **design session first** (free; can run earlier): blueprint
  seams (analysis · generation/cover-letter · corpus · dashboard · user/config ·
  templates) & naming; shared-helpers home (`_sse`, `_error_detail_payload`,
  `_safe_username`, `_within`); app-factory vs. module-global `app`; SSE routes; the
  32 test-file imports; `route-security-lint` hook compatibility (it currently targets
  `app.py`).
  **RESOLVED (8.1, owner-locked 2026-06-21 — see [`app-blueprints-design.md`](app-blueprints-design.md)):**
  **Crafted** architecture — a `create_app(config)` **application-factory** (with a retained
  module-level `app = create_app()` WSGI/console handle) + a typed injected **`Config`** (the
  paths/flags; ends the ~35-file monkeypatch-the-global test smell) + a shared **web-infra
  package** that `app.py` + every blueprint import (`assistant.py` drops its duplicated
  `_safe_username`/`_get_client`/`_sse`; `dashboard` consumes the shared `_is_localhost_request`;
  `onboarding/corpus_import.py`'s *second* path-constant front folds in too). **8 domain seams**
  (analysis · generation · corpus · templates/personas · applications · users/config ·
  diagnostics · assistant) — splitting the user-facing application tracker from the dev
  diagnostics backend. The doc carries the full 93-route→seam map + a **zero-tech-debt
  definition-of-done** (owner bar: minimum tech debt at the v1.1.0 tag).
- `refactor/app-blueprints-*` — the decomposition itself. **Per the 8.1 design:** an
  **8.3a `refactor/app-factory-and-infra`** foundation branch (factory + `Config` + web-infra
  package + helper dedup + canonical `create_app(TestConfig)` fixture + the PX-20 boundary gate;
  **no route moves**) lands first, then **one domain seam per branch** (8.3b–h; assistant =
  move-only). Preserve the `_safe_username`/`_within` gate + its (now-widened, PX-21) lint hook
  on every moved route; annotate returns with `ResponseReturnValue` (PV-4) as they move.
- **Absorbs the type-annotation scan (PV-4 = WS-2 increment 1):** annotate route
  returns with `flask.typing.ResponseReturnValue` **as the routes move** (or flip
  `check_untyped_defs = true`), scoped to the whole post-v1.0.4 surface. Doing it here
  avoids annotating the monolith and then re-doing it post-split. The full
  `mypy --strict` ratchet + a typed `context_set` is the post-public **WS-2-full**.
- **Wizard back-navigation (PX-22) — LANDED 2026-06-22 on `refactor/app-blueprints-templates`
  (8.3e).** The wizard rail (`wizardGoTo`, the `.wizard-step` buttons in `templates/index.html`)
  and per-panel "← BACK" controls already let a user step back in-app; PX-22 added the missing
  **browser Back/Forward** affordance — a first-time user who reaches for the browser Back button
  now traverses wizard steps instead of leaving the page. `wizardGoTo` pushes a `{wizardStep}`
  `history` entry (baseline `replaceState` at `wizardInit` + the resume-from-prior landings); a
  `popstate` listener restores the step. Two correctness fixes shipped with it (skip a duplicate
  same-step push; load preview iframes via `location.replace` so step-4/6 preview reloads don't
  pollute joint history). Session-only scope (no address-bar `?step=N` / deep-link-on-load).
  Originally deferred 2026-06-10 to land once the wizard seam reorganized in the blueprint split.

### Gated test window + correction (2026-06-15 — on the decomposed code)

> **The blueprint refactor OPENS a formal gated test window.** Decided in the 2026-06-15
> planning session (fork #2): features land in v1.0.7 on the monolith; v1.0.8 does the
> no-behavior-change split **first**, then the window + the first-ever real-data eval
> loop run on the **decomposed** code — so the gather tests exactly what ships and also
> catches any refactor regression. **`route-security-lint` widening leads the refactor**
> — the hook currently matches `app.py` only
> ([`route-security-lint.sh`](../../.claude-plugin/hooks/route-security-lint.sh), line 13),
> so widen it (the PX-21 prescription) *before* any route — or the v1.0.7 `recall/` /
> assistant module — moves out from under its coverage.

- **Gated test window** (after the seams land): a v1.0.6-style **E2E user+dev
  walkthrough** (app + the v1.0.7 assistant + diagnostics; R2 streaming verified live)
  **and** `eval/live-shakedown-labels` (**PV-1**) — the **first end-to-end run of the
  real-data eval/tuning loop** (clean-corpus rebuild → seed export → bootstrap →
  annotate → collate → `expected.json` + labels under `evals/fixtures/real/`, gitignored
  PII). Triage both into **one numbered findings backlog**. *Expectation: this is where
  the significant, so-far-unexercised integration issues surface.*
  - **Update (2026-06-23, `eval/live-shakedown-labels`):** the *eval half* ran and the
    expectation held. The real corpus→context→generate path **works** (3 bootstrap
    pipelines OK on `testuser`), but the never-run grounding tooling broke: **EV-1** (the
    L2/MiniCheck scorer's unpinned git dep drifted to an incompatible version) + **EV-2**
    (the optional grounding failure aborts the whole bootstrap) + **EV-3** (seed-export
    Windows-console crash) + **S3-1** (the vector index staled post-split). The **S3
    before/after labeled eval** cleared its gate-override → **KEEP** (relevance 1.12→2.58).
    Findings: [`window-8.5-findings.md`](window-8.5-findings.md). **Owner-decided at
    close-out:** PV-1 *label production* defers to **8.6** (fix EV-1's minicheck FIRST, then
    one full L0+L1+L2 annotation pass — no double annotation), and the **E2E walkthrough +
    R2-live** half defers to a run against `main` (runbook
    [`window-8.5-walkthrough.md`](window-8.5-walkthrough.md)). 8.5 delivered the findings +
    the S3 verdict + the flaky-UX stabilization; the walkthrough findings + calibration
    labels land via 8.6.
- **Correction sprint** (`fix/window-findings-*`): burn the backlog + **PV-2** grounding
  calibration + **PV-3** cover-letter tone tune (now on the decomposed code) + a
  `/wiki-ingest` to refresh the wiki's `app.py` `path:line` citations the split staled.
  May spill to a v1.0.9 epic if heavy.
  - **Update (2026-06-23) — owner-confirmed sub-branch split + first sub-branch landed.** 8.6 is
    **multiple sub-branches**: **(1) `fix/window-findings-grounding`** — the **grounding slice**
    (EV-1 minicheck pin/fix, EV-2 bootstrap fail-soft, EV-3 cp1252 print crashes, S3-1 vector-index
    freshness), **landed 2026-06-23**; EV-1 fixed + the L0+L1+L2 scorers re-validated on CPU, so
    **PV-2 is unblocked but staged** (owner-gated manual annotation; may spill to v1.0.9). **(2)
    `fix/window-findings-tone`** — **PV-3** cover-letter tone (the only `PROMPT_VERSION`-bumping
    change), a sibling branch — **landed 2026-06-23** (`PROMPT_VERSION 2026-06-13.1 → 2026-06-23.1`):
    a `WORKED EXAMPLES` OK/NOT-OK opener+close sub-block + de-cloned the single close example the
    model was copying into the v1.0.3 lapse; paired before/after `--suite synthetic --subset full`
    n=3 showed **tone holds at the 4.2 floor with no regression**; see TUNING_LOG (2026-06-23 PV-3).
    **(3) `fix/window-findings-grounding-calibration` (8.6b)** — **PV-1 label production + PV-2
    grounding calibration**, the **owner-gated** sub-branch (manual browser annotation): EV-1 is fixed
    and the L0+L1+L2 scorers are proven on CPU, so it is **unblocked but staged**, and **may spill to a
    v1.0.9 epic** (slotted explicitly 2026-06-23). **(4)** the **`/wiki-ingest` re-anchor folds into
    8.6a** (`docs/assistant-wiki-coverage`, which already rewrites wiki pages) rather than this sprint.
    Findings + resolution: [`window-8.5-findings.md`](window-8.5-findings.md).
- `docs/assistant-wiki-coverage` (proposed **8.6a**, owner-confirmed 2026-06-20) — the
  doc-authoring sprint that fills the doc-grounded assistant's "woefully uninformed" coverage
  gap (only the ~6 Sprint-6.5 `audience: user` wiki pages exist today, so many "how do I…"
  questions hit the avatar's refusal). Author the user/dev how-to pages (downloads,
  editing/refining, cover letters, multi-user, import mechanics, troubleshooting, the assistant
  itself). Content, not code — runs **after** the test-window findings settle the post-split
  route surface and **before** the public prep, so v1.1.0 ships a well-informed avatar; pairs
  with the 8.6 `/wiki-ingest`. Possibly multi-branch. **AUTHORED 2026-06-25**
  (`docs/assistant-wiki-coverage`): the all-7-topics first branch landed — 7 `audience: user`
  pages (downloads · editing/refining · cover letters · multi-user · import · troubleshooting ·
  the assistant), each grounded + per-page author≠auditor audited (6 clean / 1 re-anchored);
  content pass, `.last_ingest_sha` unchanged; clears the assistant doc-coverage ledger item
  (open count 9 → 8).

### Pre-public prep (2026-06-15 — moved up from Phase 5 so "all work is done by v1.0.8")

> **Owner decision (2026-06-15, fork #1):** the public **v1.1.0** tag stays user-owned,
> but **all the *work* lands by v1.0.8** — the owner may create + push the GitHub repo
> early (private/unpromoted) and only **promote** at v1.1.0 once integration issues are
> resolved and the product is "working as expected." So Phase 5's *build* work moves here.

- `release/public-prep` (one branch or a small split): `docs/screenshots/*.png` (+ optional
  demo.gif); fresh-clone < 5 min verification; the machine-badge set (Dependabot + lockfile,
  OpenSSF Scorecard, REUSE/SPDX — the E-2 prescription / PX-26); the UX/a11y/PDF tier as a
  **required CI check** (PX-25); a doc-link resolution sweep; **create the GitHub repo +
  push `main` (private/unpromoted)** — **DONE 2026-07-09 (repo created + `main` pushed
  private); the required-CI-check + badge-activation + PyPI/GHCR pieces are DEFERRED to
  pre-v1.1.0 (owner 2026-07-09)**.
  **Folds in here (slotted 2026-06-23 from the carry-forward ledger — re-homing, not new items):**
  (i) **`feat/portable-enforcement-core`** — lift the portable guards (`require-feature-branch`,
  `block-merge-to-main`, `block-secrets`, `route-security-lint`, `ruff-changed`, `validate-context`)
  into a tool-agnostic core invoked by BOTH committed git-hooks AND the plugin, CI as the
  server-side backstop (activate when the git remote/CI lands; plan-mode lifecycle hooks stay
  Claude-only). (ii) the **periodic cross-document link / cite checker** — the durable CI form of the
  doc-link sweep (a CI step or `wiki-lint` extended over `docs/governance/` + the contract docs), so
  the extract-don't-restate pointers are gated. (iii) **resolve the flaky Compose-wizard UX class** as
  a **PX-25 prerequisite** — the UX tier can't become a *required* CI gate while a compose-load race
  intermittently fails (the 8.5 `.compose-experience-card` fix didn't cover the second
  `bullet_texts()[0]` race; tally reset 2026-06-23); needs a broader compose-load wait or retry policy.
  (iv) the **help-opener de-dup** (`openDashHelp`/`openHelpModal`) as pre-public **UI polish**
  (owner-chosen home (a)). The **in-app rendered citation viewer** stays **deferred to v1.1.0+** (not
  in the 1.0.8 sequence; conditional on real friction).

Then: `chore/version-bump-v1.0.8`.

### v1.0.8 tag criteria
- `app.py` decomposed into blueprints; the `_safe_username`/`_within` gate + its lint
  hook hold on every moved route; all 32 test files import cleanly.
- Route returns annotated (PV-4) — `check_untyped_defs`-clean over the post-v1.0.4 surface.
- `ruff + mypy + pytest + pytest -m ux` green; **no behavior change** (pure refactor).
- **The gated test window ran on the decomposed code** (E2E walkthrough + first real-data
  eval loop); its findings backlog is burned down (or remaining items consciously deferred
  to v1.0.9); **PV-2 calibrated groundedness live + PV-3 `tone` holds** with `PROMPT_VERSION`
  bumped (the only prompt change in the two epics).
- **Pre-public prep done** (moved from Phase 5): screenshots, fresh-clone < 5 min, badge set,
  UX/a11y/PDF required CI check, doc links resolve, GitHub repo pushed (private/unpromoted).
  "All work done by v1.0.8." **(Reconciled 2026-07-09: `main` is pushed to the private repo;
  the required-CI-check activation + badge-resolution + PyPI/GHCR moved to the pre-v1.1.0
  checklist per owner — the v1.0.8 tag no longer gates on them.)**
- **Carry-forward ledger drained** (the 2026-06-20 7.9 triage): the `chore/ledger-reduction`
  (8.0) hygiene pair cleared and the `docs/assistant-wiki-coverage` (8.6a) doc sprint authored,
  so by the public cut the open ledger is down to ~the deferred in-app citation viewer.

### Big-push scope brief (2026-07-07 — durable resume anchor)

> **RELEASE_ARC edit sign-off: this write was mandated by the owner-approved
> big-push plan (2026-07-07).** This subsection is the durable in-repo anchor
> for that plan — the owner-approved sequence from the current window through
> v1.1.0's public flip, spanning the remainder of Phase 4.8 through Phase 4.9
> and into the v1.1.0 gate. It exists so a fresh session (or a resumed one)
> can reconstruct the whole plan from the repo alone, without relying on
> point-in-time chat memory.

#### Phase table

| Phase | Branch(es) | What lands |
|---|---|---|
| GATE 0 | — | **DONE.** E2E clone confirmed at `ecc8925`; session-setup (`bypassPermissions` in gitignored settings). |
| Phase 0 | `chore/px-staleness-reverify` (this branch) | 7-PX staleness re-verify → all `PARTIALLY_STALE`, dispositions in [`px-staleness-reverify-2026-07-07.md`](reviews/2026-07-efficiency/px-staleness-reverify-2026-07-07.md); mypy-strict re-measure (2821 errors / 126 of 248 files, incl. tests — normalize at Phase 6); gen-exp §6 marker reconcile (commit `6071478`); this scope brief. |
| Phase 1 | Wave 0 + packaging → **TRAIN 1** | `fix/ux-f01-keyword-score` (DONE, merged `f82fd00` 2026-07-07), `fix/ux-f02-import-skill-rows` (F-02), `fix/eval-f11-frozen-assembly` (F-11), `fix/packaging-install` (ledger #2 + PX-42 floor ≥3.11 + F-24/25/26); conditional `fix/walkthrough-p0` (owner E2E findings). |
| Phase 2 | `feat/grounding-calibration-8.6b` | Owner PV-1 annotation (30–60 min) → PV-2 calibration → ledger #10 fresh Sonnet-5 baseline (~$0.30). |
| Phase 3 | UX Waves 1–4 → **TRAIN 2** (7 branches) | `feat/ux-w1-first-run-flow` (F-12/06/05/15) · `feat/ux-w1-skills-education` (F-03/04) · `feat/ux-w1-generate-surface` (F-09/10) · `feat/ux-w3-demo-mode` (F-19) · `docs/ux-w3-contributor` (F-21/22/20/27/06d) · `feat/ux-w2-recruiter` (F-08/17/16) · `feat/ux-w4-aesthetic` (F-07/23/13/14/18). Shared `static/app.js`/templates → pre-train merge-tree preflight mandatory. |
| Phase 3b | gen-exp completion → **TRAIN 3** | (a) `fix/surgical-refinement-and-loopback` + (d) `feat/regenerate-gap-fill` in parallel, then (b) `feat/wysiwyg-source-of-truth` + (c) `feat/clarifications-to-corpus`. Spec home: [`generation-experience-rearchitecture.md`](generation-experience-rearchitecture.md) §4/§6. Corpus-mode validation on a saved context + one real generate (NOT `--suite synthetic`). |
| Phase 4 | 8.7 public-prep → **TRAIN 4** → **CODE FREEZE** | `feat/portable-enforcement-core` (ledger #6) · `ci/ux-a11y-required-check` (PX-25) · `chore/doc-link-sweep` (ledger #7). Then **[HUMAN]**: GitHub repo `take-tempo-public/sartor` (private) + PyPI Trusted Publisher + required checks. **[Reconciled 2026-07-09: repo created + `main` pushed private; PyPI/GHCR/required-checks activation DEFERRED to pre-v1.1.0 per owner — see the RELEASE_CHECKLIST [HUMAN] row.]** Then assets: `docs/screenshots-refresh` ($0.27, app running) · `docs/badges-readme-prep` (PX-26 + PX-54) → **TRAIN 4b**. |
| Phase 5 | v1.0.8 tag ceremony | `/compliance-witness` at pinned sha + `/wiki-lint` (staleness carried as accepted note; PX-41 scheduled Phase 6) + `RELEASE_CHECKLIST` sweep + `CHANGELOG` cut → owner confirms → tag **v1.0.8** → verify published wheel. |
| Phase 6 | v1.0.9 docs epic → **TRAIN 5** → v1.0.9 tag | ~~`docs/readme-icp-ladder`~~ **DONE** (`323bf6c`/`996d1c9`, on `main`; DOC-STATUS governance-boundary reconcile RESOLVED — PX-19/PX-20 closed) · `docs/dev-home-depth-wsb` (+ PX-40/48 + avatar-voice casing) · `docs/wiki-content-pass` (PX-41 catch-up ingest 150+ commits via `/wiki-self-update` + PX-50/53 + user-tier pages + `llms.txt`) · `docs/diagrams-a11y` (new `accTitle`/`accDescr` diagrams; retire the 4 drifted `.mmd`) · `feat/fumadocs-site` (projection adapter + spectree/OpenAPI Layer-B) · `ci/doc-merge-gate` (last) · `chore/mypy-strict` (burn the normalized error count) · `spike/pagedjs-design` (timeboxed doc). Voice/tone reference: Google developer style guide tone (record in `documentation-architecture.md`). <br>**[TRAIN 5 assembled 2026-07-10 — pending owner train-confirm]** landed as one chain: `docs/dev-home-depth-wsb` · `docs/wiki-content-pass` (the F-17 recruiter-Pipeline `audience: user` page; the PX-41 catch-up already landed separately as `docs/wiki-v109-refresh`) · `docs/diagrams-a11y` · `feat/fumadocs-site` (L1→MDX projection core + SFTP self-host deploy to `sartor-docs.taketempo.com`; **spectree/OpenAPI Layer-B deferred** — spectree was never wired, the "pulled into v1.0.8" note above was drift) · `ci/doc-merge-gate` · `spike/pagedjs-design`. **`chore/mypy-strict` burn** = satisfied by the mypy `--strict` §6 exit (all production modules strict + roster-gated, landed 2026-07-10); the exempt-tree (`tests/`/`evals/`/`scripts/`, ~2821 errors) burn is **deferred post-public** unless the owner directs otherwise. |
| Phase 7 | v1.1.0 gate → **TRAIN 6** | `chore/px-v110-gate-batch` (Phase-0 survivors incl. PX-37/38/43/44/45/47/49/51/55/56 as re-scoped) · PX-39 Sonnet-5 latency baseline (idle only) · `release/visual-assets` · PX-46 memory consolidation (owner-gated) → final fresh-clone-from-GitHub verify → owner acts: tag **v1.1.0** + public flip. |

#### Train schedule

Six merge-trains carry the branch-heavy phases; each train gets its own owner
confirm (manifest + diffstat + gates + spend) before merging:

- **TRAIN 1** — Phase 1 Wave 0 + packaging.
- **TRAIN 2** — Phase 3 UX Waves 1–4 (7 branches; merge-tree preflight mandatory given the shared `static/app.js`/templates surface).
- **TRAIN 3** — Phase 3b gen-exp completion (parallel pair, then sequential pair).
- **TRAIN 4 / 4b** — Phase 4 public-prep, split around the `[HUMAN]` GitHub/PyPI checkpoint (4 = code-freeze branches, 4b = post-checkpoint asset branches).
- **TRAIN 5** — Phase 6 v1.0.9 docs epic.
- **TRAIN 6** — Phase 7 v1.1.0 gate.

#### Owner checkpoints (complete list)

- GATE-0 clone confirm (done).
- PV-1 annotation.
- Train confirms T1–T6 (manifest + diffstat + gates + spend, one confirm each).
- **[HUMAN]** GitHub/PyPI config, once.
- Tag confirms v1.0.8 + v1.0.9.
- PX-46 review.
- Owner tags v1.1.0.

#### Standing grants (owner-approved)

- Merge-trains under `CLAUDE_CONFIRM_MERGE=1` per train confirm.
- Plan-marker re-arm post-train only.
- `bypassPermissions` for the push.
- $10 API spend cap with cumulative reporting.

#### Window map

| Window | Covers | Milestone |
|---|---|---|
| W1 | GATE-0 + Phase 0 + Phase 1 + Train 1 | — |
| W2 | Phase 2 + Phase 3 | — |
| W3 | Phase 3b | — |
| W4 | Phase 4 + Phase 5 | **v1.0.8 tagged** |
| W5 | Phase 6 | **v1.0.9 tagged** |
| W6 | Phase 7 | v1.1.0 gate |

Total ≈ 20–28h across ~5–6 windows.

#### Resume protocol

A fresh session reads, in order: `git worktree list` + `git branch -a` → this
brief → `RELEASE_CHECKLIST.md` train state → [`keep-ledger.md`](keep-ledger.md)
→ the newest handoff. Repo state overrides memory. Any branch without a
close-out entry gets its gate re-run. A wiped plan marker → owner
re-confirmation doubles as resume.

---

## UX Cohesion Epic (registered 2026-07-09 — slotted into v1.0.9, owner 2026-07-09)

> **Registration only — not a spec.** Surfaced by the owner's e2e round-2
> walkthrough ([`reviews/2026-07-ux-round2-findings.md`](reviews/2026-07-ux-round2-findings.md)
> has the full findings + disposition table); the six decision-free items
> from that pass landed immediately as Wave A quick-wins
> (`fix/round2-quick-wins`). Everything below needs a design/shape decision
> first, so it is parked here as a named epic rather than decided inline.
> **Version slot: v1.0.9** (owner-slotted 2026-07-09 — rolls into the v1.0.9
> epic alongside the Phase 4.9 docs-site work; may run before, after, or
> interleaved with it). Now also carries the **Diagnostics-DX + hardening**
> thread below.

Themes (each design-scoped, not yet branch-planned):

- **State-communication unification** (G2/G4/G8/Co5) — shape is fixed by
  owner decision: **strengthen the existing `_setBusy` banner** (see
  `static/app.js`) and fill its remaining gaps, not a new modal or
  mechanism. Co5 (Compose's quiet background-reload-on-save) rides this
  theme.
- **Skills redesign** (C1/Co1/Co3-adjacent) — denial semantics (C1, a
  schema question: what "Deny" does to a pending suggestion), a
  collapsible-toggle for the bounded skills lists (Wave A did CSS bounds
  only), and icon unification (Co1, with G3) folded together since they
  all touch the same skills surfaces.
- **Design-system pass** (G1/G3/G5/Co1) — modal open/close fade
  consistency (G1), iconography unification across skills/templates/chips
  (G3, paired with Co1), and caps-vs-sentence-case labeling consistency
  (G5).
- **Prior-application compact cards** (G7) — a denser roster-view card for
  prior applications.
- **Compose-reload loudness** (Co5) — listed under state-communication
  above; cross-referenced here since the owner named it separately.
- **Template-preview fidelity** (T2) — **spike-first, not a quick fix.** The
  in-app preview is architecturally single-column (`docx_to_persona_html.py`
  extracts only typography onto the Classic skeleton — python-docx can't
  represent multi-column/tables/text-boxes/shading), so colored section bars
  fall back to Classic, and multi-column + accurate paging are out of reach
  (paging is a paged.js *polyfill* preview, not real pagination).
  **Cross-referenced to the roadmap's existing paged.js design-spike** —
  Phase 6 `spike/pagedjs-design` + the Phase 4.9 preview-engine note.
  Acceptance targets: colored bars, multi-column, section spacing, accurate
  paging. Scoping caveat: verify whether the docx **download** (real template
  as style source) is already faithful while only the **preview** is lossy —
  "preview should match output" is the principle at stake. Detail in the
  findings doc's T2 deep-dive.
- **Diagnostics-DX + hardening** (round-2 items #1–#17) — the diagnostics
  console (`/_dashboard`) round-2 batch, captured in
  [`reviews/2026-07-diagnostics-round2-findings.md`](reviews/2026-07-diagnostics-round2-findings.md)
  (owner-decided 2026-07-09: **bundle into v1.0.9; nothing pre-empts the v1.0.8
  tag** — the broken fixture flow ships as-is). Fix order: **#15 → #11** (reconcile
  the anchor-JD `.txt` path + add the collate CLI `--fixture` flag — unblocks the
  whole fixture flow, currently broken end-to-end), then the **run-lock + a real
  run-cancel endpoint** (#1 + the daemon-thread run-lifecycle; owner opted **in** to
  cancel, not just a lock), the **annotate-flow persistence** (#9 localStorage draft
  + jump-to-flagged-item — pairs with the **grounding-signal persistence gap** from
  the #14 run-health review, where NLI + MiniCheck scores never wrote back to
  `annotations.json`), the **bootstrap skills parser** (#8, LLM-free) and the
  **should_omit/verdict tooltip + design-Q** (#7), then the instructional / assistant
  / progress-bar polish (#2–#6, #10, #13, #16, #17). Run-health follow-ups (0-byte-run
  guard, full-rubric coverage) ride here too
  ([`reviews/2026-07-e2e-run-health-review.md`](reviews/2026-07-e2e-run-health-review.md)).
  **Built 2026-07-09 (unattended stack, awaiting owner merge):** the four confirmed-bug
  fixes — #15, #11, #8, and the #1 client-side run-lock — are landed on stacked branches
  (`fix/diagnostics-{15,11,08,01}-*`), full suite green; the run-cancel endpoint, annotate
  persistence (#9), the #7 tooltip/design-Q, and the #2–#6/#10/#13/#16/#17 polish remain
  open. Shas + the #1 lock-scope design-Q + witness CW-117 are in the
  [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) Carry-forward diagnostics progress note.
  **Separate governance decision (NOT epic bug work):** single-threaded `app.run()`
  (`app.py`, no `threaded=True`) freezes the whole app during a diagnostics run —
  making it threaded touches the C-1-sensitive loopback-bind area, so it is an
  owner-gated governance call, deliberately kept out of this epic.

Deferred out of this epic (tracked elsewhere): **Co3** (skill-suggestion
ATS-quality) is a tune-loop question, not a code branch. **O1b** (dates
right-alignment) is **RESOLVED, no code change** — the owner chose keep
status quo after an evidence pass debunked the "never right-align for ATS"
premise as a false constraint (right tab stops are ATS-safe; the earlier
`fix/persona-fidelity-and-residuals` shipped a preview/download *parity*
fix, not an ATS fix). See the findings doc's O1b deep-dive.

---

## Phase 4.9 — Documentation & docs-site (v1.0.9)

> **Inserted 2026-06-29 (owner direction): a dedicated pre-public DOCUMENTATION epic
> between v1.0.8 and v1.1.0.** ALL product documentation — including the hosted
> **Fumadocs** site — lands here, authored against **settled v1.0.8 code**, so v1.1.0
> ships with a complete, published doc set. Publishing strategy:
> [`documentation-architecture.md`](documentation-architecture.md) (the L0–L3 layered
> source chain · the three-audience ICP ladder as the nav spine · Fumadocs as an L3
> projection of `main`, merge=publish · the `DOC-STATUS` flag convention · recursive
> grounding). **Blocked by:** v1.0.8 tag. **Blocks:** v1.1.0.
>
> **v1.0.8 tail vs v1.0.9 (owner-confirmed 2026-06-29):** only walk-through / bug-fix-
> *coupled* doc corrections (fix code + its doc together) and the routine pre-tag wiki
> *freshness* reconcile ride v1.0.8. The doc-architecture set below is **all v1.0.9**.
> **Scheduling reconcile (2026-06-29, owner-directed):**
> - **PV-2 grounding-calibration → v1.0.8** (not v1.0.9 — it's eval/code, not docs). Its
>   manual groundedness-annotation pass runs on the **same clean-corpus rebuild** as the
>   v1.0.8 E2E walkthrough (adjacent session, distinct output). Fold the stale "may spill
>   to v1.0.9" refs in §4.8 + the Carry-forward ledger into the v1.0.8 close-out.
> - **Fumadocs renders the HTTP-API spec (Layer B) — IN v1.0.9 scope** (owner-confirmed).
>   So **spectree** (the OpenAPI-emitting request boundary; kit Decisions 1/2a) is its
>   **dependency**, **pulled pre-public into v1.0.8** (code, route-boundary, post-blueprint-
>   split) — it must land before branch #4 below.
> - **paged.js engine replacement (B.13) → pulled pre-public** from §Post-public. A render-
>   engine project (**design-spike first**); preview-fidelity only (PDF is Playwright-native,
>   unaffected). Off both the v1.0.8 blueprint theme and the v1.0.9 docs theme → **owner to
>   slot its own pre-public sprint.**

Sequence (each its own branch, in dependency order):
1. ~~**`docs/readme-icp-ladder`** — MERGE the new README front door + the
   [`documentation-architecture.md`](documentation-architecture.md) design doc (already
   built off the 8.x line — commits `323bf6c` + `996d1c9`; rebase onto the v1.0.8 tag
   first). Reconcile its governance `DOC-STATUS` flags now that v1.0.8 closed PX-19/PX-20.~~
   **DONE** — on `main` (`323bf6c`/`996d1c9`); the governance-boundary `DOC-STATUS`
   flag reads `RESOLVED` (PX-19/PX-20 closed, verified against `README.md`).
2. **`docs/dev-home-depth` (WS-B)** — verify the dev-tier homes (`system-model` /
   `memory-architecture` / `architecture`) carry the depth the README hooks into,
   against settled v1.0.8 code; the 2026-06 architecture digest is the checklist.
   (WS-E unification is already in the design doc — confirm only.)
3. **`docs/wiki-content-pass`** — ICP-ladder `audience: user` pages + `overview.md`
   refresh + `llms.txt`; a bounded `/wiki-self-update` so L2 is fresh for the site
   (content pass — does **not** advance `.last_ingest_sha`).
4. **`docs/fumadocs-site`** — the projection adapter (L1 + Purpose/Audience/Authoritative-for
   frontmatter → MDX tree), `meta.json` from the ICP ladder + audience tags,
   deploy-on-merge-to-`main`; **+ renders the HTTP-API reference (Layer B) from the OpenAPI
   spec spectree emits** (dependency: spectree, pulled into v1.0.8 — see the reconcile note above).
5. **`ci/doc-merge-gate`** — the doc gates (link-integrity / frontmatter+audience /
   D5 single-home / cite-resolution / wiki-freshness) + the `DOC-STATUS`-trigger check,
   extending `block-merge-to-main` + `wiki-lint`. **Last**, because merge=publish only
   matters once the site exists. **DONE** (`ci/doc-merge-gate`): link-integrity and the
   `DOC-STATUS`-trigger check were already built (`chore/doc-link-sweep`, PX-50); this
   branch adds the remaining three — `scripts/check_doc_frontmatter.py` (frontmatter+
   audience, a new `PUBLISHED_DOC_FILES` registry), `scripts/check_doc_single_home.py` (D5,
   a documented near-duplicate-paragraph heuristic — the hardest of the five, scoped and
   proven on synthetic fixtures rather than left unautomated), and widened
   `check_doc_links.py`'s cite-check to the same registry — plus
   `scripts/wiki_freshness.py`, wired both as a pytest gate and as a genuine merge-time
   block in `block_merge_to_main.py` (no `CLAUDE_CONFIRM_MERGE=1` bypass). All green on the
   current tree, zero doc content edits required. See `CHANGELOG.md` [Unreleased] for the
   full per-gate detail and the `PUBLISHED_DOC_FILES`/`feat/fumadocs-site` convergence flag.

**Type hardening (pulled pre-public into v1.0.9 — owner 2026-06-29).** **✅ BUILT
(2026-07-10, `chore/kit-mypy-strict-*` 5-branch stack, ratchet rungs 4–8):** the
`mypy --strict` ratchet reached its **§6 exit** — every non-exempt production module
(all 81) now carries the strict override; only the Decision-7 exempt set
(`tests/`/`evals/`/`scripts/`/`db/migrations/versions`) stays permissive, and the exit
is enforced **by construction** via `tests/test_mypy_strict_roster_gate.py` (closes
compliance-witness CW-118), not a one-time proof. Rung history:
[`kit-adoption-design.md`](kit-adoption-design.md) §4/§6 + `CHANGELOG.md` `[Unreleased]`.
**Tooling-slice pull-in — ✅ LANDED (2026-07-10, `chore/mypy-strict-tooling`,
owner-directed).** Decision 7 AMENDED: the exempt set narrows to **`tests/` only** —
`scripts/` (22 errs) + `evals/` (44 errs) + `db/migrations/versions/` (6 errs) = 72
measured `mypy --strict --warn-unreachable` errors fixed and rostered (annotation-only,
zero behavior change). `tests/test_mypy_strict_roster_gate.py` updated to match
(`_EXEMPT_PREFIXES` narrowed, the migrations/versions guard inverted to assert
coverage). The remaining `tests/` strict burn (~3,252 errors measured) **stays
deferred** per owner direction 2026-07-10 — out of scope for this pull-in; see
[`kit-adoption-design.md`](kit-adoption-design.md) §6 for the full amendment record.
The original plan is retained below for the record. — Complete the
`mypy --strict` ratchet to the §6 end-state so strict typing can be claimed for all
non-test code. Empirically measured 2026-06-29: **146 errors across 18 of 69 production
modules** (the other 51 are already strict-clean → free to roster; 5 already rostered).
Concentrated — `dashboard/routes.py` (36) + `hardening.py` (32) = ~47%; the rest ≤14 each;
predominantly mechanical (`dict`/`list` → parameterized). Runs as its own module-by-module
ratchet branches (independent of the doc branches; can interleave). The typed `context_set`
spine (WS-2-full's other half) stays **post-public** — not needed to claim strict typing.

---

## Phase 5 — Public release (v1.1.0)

**Blocked until v1.0.8 tagged. The v1.1.0 tag is owned by the user** — the public cut of the **complete** product: the assistant + self-documenting wiki (v1.0.7) on **clean blueprints** (v1.0.8). There is no external deadline; completeness and polish gate the tag, not a clock.

> **Update (2026-06-15, fork #1): the build work moved earlier to v1.0.8.** Per the
> owner's "all work done by v1.0.8" line, the visual assets, fresh-clone verification,
> badge set, required-CI check, and GitHub repo create + push now live in §Phase 4.8
> "Pre-public prep" (the repo may be pushed early, **private/unpromoted**). **v1.1.0 is
> then the promotion act:** flip the repo public + cut the `v1.1.0` tag once the
> integration issues from the v1.0.8 test window are resolved and the product is "working
> as expected" — plus a final **re-verify** (fresh-clone < 5 min + doc links resolve) at
> the cut. The branches below are retained for that final verification; their build
> halves are done in v1.0.8.

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
- **paged.js engine replacement (B.13)** — **PULLED PRE-PUBLIC 2026-06-29 (owner) →
  §Phase 4.9 scheduling reconcile; owner to slot its pre-public sprint.** Replace the
  end-of-life in-browser paged.js v0.4.x pagination engine (the v1.0.5 fix only
  *contained* its throws; PDF uses Playwright natively and is unaffected). A real
  render-engine project → **design-spike first** (fidelity + constraints + replacement choice).
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
  typed spine. Builds on the v1.0.8 blueprint split. **Now Phase 2 of the kit-adoption
  arc** — the ratchet end-state + finite exit criterion are settled (strict everywhere
  except `tests/`/`evals/`/`scripts/`/`db/migrations/versions`; see
  [`kit-adoption-design.md`](kit-adoption-design.md) §6). **Split 2026-06-29 (owner):**
  the **`--strict` ratchet completion is pulled pre-public into v1.0.9** (to claim strict
  typing at launch — see §Phase 4.9); only the **typed `context_set` spine** remains
  post-public here.
- **WS-3 — recurring test-suite engineering-design pass.** Periodic review of the
  ~955-test suite (redundancy, slow tests, coverage gaps, fixture dup). Define cadence
  + what "good" looks like.
- **Agent-coding-practices kit adoption** (captured 2026-06-23,
  [`kit-adoption-design.md`](kit-adoption-design.md)) — adopt the lichen
  `agent-coding-practices-kit` (context / docs / strict-typing + the
  `context-structure-review` skill). Eight decisions settled
  ([`decisions.md`](decisions.md) KIT-1…8; full faithful adoption, "implement + flag
  promotable" — Sartor is the donor, not a blank canary). **Threads existing work
  rather than standing alone:** the strict ratchet **is** WS-2-full above; the
  mechanizable gates fold into `feat/portable-enforcement-core` (8.7 — local pre-commit
  now, CI-blocking when the remote lands); the **spectree request-boundary + OpenAPI
  emission is pulled pre-public into v1.0.8** (2026-06-29 owner — it's the v1.0.9 Fumadocs
  Layer-B dependency; see §Phase 4.9), and **Fumadocs renders the spec in v1.0.9**. Real
  cost = the mypy `--strict` ratchet (post-public) + the ~30-endpoint spectree boundary
  (now v1.0.8); the rest is reconcile-don't-build.

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
- One branch per agent session, owned end-to-end — concurrent sessions run in isolated worktrees, not serialized globally (charter [W-1](../governance/charter.md)); close, merge, hand off before reusing a session

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
