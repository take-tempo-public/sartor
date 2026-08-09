# Eval harness

> **Audience:** `dev`
> **Concept:** the offline eval system — suites/subsets, the Haiku rubric judges, the
> static baseline + the frozen anchor, the corpus bootstrap engine, and prompt-override
> A/B tuning. Eval-only: it ORCHESTRATES the product pipeline but is never on the request
> hot path.
> **Sources:** [`evals/runner.py`](../../../evals/runner.py), [`evals/bootstrap.py`](../../../evals/bootstrap.py), [`evals/rubrics/`](../../../evals/rubrics), [`evals/results/baseline_v1.json`](../../../evals/results/baseline_v1.json), [`evals/anchors/anchor-v1/manifest.json`](../../../evals/anchors/anchor-v1/manifest.json), [`analyzer.py`](../../../analyzer.py), [`hardening.py`](../../../hardening.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What it is

`evals/runner.py` loads fixtures, runs the **real** analyze → clarify → generate pipeline
against each, then dispatches per-rubric grading to a Haiku judge and writes one JSONL
record per grading to `evals/results/{timestamp}.jsonl` ([`evals/runner.py:run_suite`](../../../evals/runner.py)).
Result records are at **`schema_version 3`** — v2's float scores plus
`fixture_hash` / `anchor_version` / `suite` / `rubric_version` / `model_snapshots` /
`baseline_comparison` / `phase_latencies_ms` / `grounding_signals`, and (F-14) a
`jd_label`; the dashboard normalizes all three versions at read time rather than
rewriting files ([`evals/README.md`](../../../evals/README.md) §"Interpreting results").
The harness lives under `evals/` — **off the P1 hardening boundary** — so it may
orchestrate LLM calls; it reuses the public pipeline primitives (`analyze`, `clarify`,
`generate`) rather than duplicating call logic, which still lives in `analyzer.py`
(deterministic/LLM boundary cited in [`AGENTS.md`](../../../AGENTS.md), not restated here — D5).

## Suites, subsets, fixtures

[`evals/runner.py:main`](../../../evals/runner.py) is a thin argparse wrapper over
`run_suite`. Flags: `--suite {synthetic,real,all,anchor,exploration}`, `--subset
{smoke,full}`, `--fixture <name>`, plus `--seed`, `--prompt-overrides`,
`--grounding-signals`, `--out-dir`. `_select_fixtures` resolves directories:
`synthetic` and `real` from `evals/fixtures/`, `anchor` from `anchors/anchor-v1/fixtures/`,
`exploration` from `evals/exploration/` ([`evals/runner.py:_select_fixtures`](../../../evals/runner.py)).
A fixture is a directory of `jd.txt` + `resume.{md,docx,pdf}` + `expected.json`; its SHA-256
`hash` over those bytes is stamped on every record ([`evals/runner.py:_load_fixture`](../../../evals/runner.py)).
The three synthetic fixtures are `data-scientist-junior`, `pm-senior`, `sre-mid-level`.

## Naming the posting a run graded (F-14 `jd_label`)

A fixture directory name is a slug (`pm-senior`), and `jd_file` is whatever the
browser or CLI happened to save the JD as — neither names the actual job posting. So
every eval-side artifact now carries a best-effort, **deterministic** `(title,
company)` label derived from the JD's **own header text** by
[`hardening.py:extract_jd_label`](../../../hardening.py), read at fixture load and
stamped onto every emitted record ([`evals/runner.py:_load_fixture`](../../../evals/runner.py)
sets `fixture["jd_label"]`; each `run_suite` / `_run_iteration_phase` record writes
`"jd_label": fixture["jd_label"]`).

Three properties are load-bearing and stated in the function's own docstring:

- It reads only the JD's first `_LABEL_HEADER_LINES` (6) non-blank lines, never the
  body — so it stays cheap and cannot pick up a company named in a duty bullet.
- **Title resolves before company**, because company-first misreads a title with no
  recognized title noun (e.g. "Machine Learning Practitioner") as a company.
- It is **fail-open by design** — each field is independently `""` on a miss — and
  therefore must never feed a fail-closed check. The closed check next to it,
  `ensure_anchor_covered_by_annotations`, stays keyed on `jd_file`: two different
  postings at the same company would trivially "agree" on a label
  ([`hardening.py:extract_jd_label`](../../../hardening.py)) `[synthesis]`.

It is deliberately kept a **separate scan** from
[`hardening.py:extract_company_terms`](../../../hardening.py) even though it reuses
that function's constants — `extract_company_terms` feeds `compute_keyword_overlap`
and is baselined in `evals/baseline_v1.json`, so merging the two would shift scored
behavior as a side effect of tuning a display string
([`hardening.py:extract_company_terms`](../../../hardening.py) docstring says so
outright). For the same reason `fixture_hash` never includes the label — label
derivation must not change what a rerun would hash
([`evals/README.md`](../../../evals/README.md), the `fixture_hash` row).

The label propagates without ever being re-derived downstream: `build_bootstrap_document`
projects a top-level `jd_labels` index out of `per_jd`
([`evals/bootstrap.py:build_bootstrap_document`](../../../evals/bootstrap.py)), the
annotation template mirrors that index verbatim
([`evals/annotation.py:build_annotation_template`](../../../evals/annotation.py)), and
`collate_expected` looks the **anchor's** label up from it by `anchor_name`
([`evals/annotation.py:collate_expected`](../../../evals/annotation.py)). One
derivation, three carriers — so the carriers cannot drift from each other
`[synthesis]`.

`--subset smoke` keeps only the `grounding` rubric (~grounding-only, cheap);
`full` runs every `*.md` in `evals/rubrics/` ([`evals/runner.py:_select_rubrics`](../../../evals/runner.py)).
The canonical full run is `python evals/runner.py --suite synthetic`.

## The rubric judges

Each rubric is a markdown file; `_grade` sends `(rubric text + JSON payload)` to the judge
model `claude-haiku-4-5-20251001` (`JUDGE_MODEL`) and parses a JSON verdict, force-floating
the score and tagging malformed responses `status: judge_error` so they don't fire false
regressions ([`evals/runner.py:_grade`](../../../evals/runner.py)). The rubric files are
`ats_format`, `callback_likelihood`, `clarification_quality`, `grounding`,
`iteration_quality`, `keyword_coverage`, `tone` ([`evals/rubrics/`](../../../evals/rubrics)).
Scores are 0.0–[`evals/runner.py:SCORE_MAX`](../../../evals/runner.py) (5.0, one decimal); the
module-level [`evals/runner.py:PASS_THRESHOLD`](../../../evals/runner.py) is `4.0`.
The [`grounding.md`](../../../evals/rubrics/grounding.md) rubric is the load-bearing one —
fabrication is "the single worst failure mode" — and it explicitly reads the deterministic
`grounding_overlap.missing_samples` as fabrication evidence and defines `jd_pandering` as a
subtype the bootstrap's cross-JD comparison detects `[synthesis]`.

Two rubrics are conditional: `clarification_quality` emits a `pipeline_error` row (no judge
call) when the clarify step failed; `iteration_quality` runs only on fixtures whose
`expected.json` carries an `iteration_scenarios` block — `_run_iteration_phase` applies a
scripted edit, calls `clarify_iteration`, and grades the resulting questions
([`evals/runner.py:_run_iteration_phase`](../../../evals/runner.py)).

## Composite + the ride-along metrics

After the rubrics, `run_suite` writes one `eval_composite` record per fixture — a weighted
average of the scored rubrics using `callback_weights.json` (missing rubrics excluded from
both numerator and denominator) `[synthesis]`. Every record also carries deterministic,
LLM-free post-generation metrics computed in `hardening.py`: `verb_diversity`,
`specificity_density`, `grounding_overlap`, `top_third_density`, `quantification_rate`, and
`fabricated_specifics` ([`evals/runner.py:_post_generation_metrics`](../../../evals/runner.py)).
The L0 `fabricated_specifics` check scores against the dynamic source union from
[`hardening.py:assemble_source_union`](../../../hardening.py) (primary + supplementals +
clarifications), kept separate from the `grounding_overlap` source set so its baseline isn't
perturbed `[synthesis]`. Per-eval `cost_usd` is rolled up from `logs/llm_calls.jsonl` by
tailing records tagged `eval:<fixture>` since the run started ([`evals/runner.py:_eval_cost_since`](../../../evals/runner.py))
and summing via [`hardening.py:compute_call_cost`](../../../hardening.py).

For `--suite real` fixtures with `--grounding-signals` enabled, the computed NLI and
MiniCheck scores are additionally persisted back into the fixture's `annotations.json`
(RH-1, 2026-07 e2e-run-health-review) via [`evals/annotation.py:patch_grounding_scores_by_text`](../../../evals/annotation.py),
matched by normalized bullet text rather than index — so ground-truth annotation files stay
in sync with the latest grounding evaluations without requiring a manual re-score pass
`[synthesis]`.

## Baseline + the frozen anchor

Two distinct artifacts, easy to conflate:

- **Baseline** — `evals/results/baseline_v1.json` (`schema_version 3`) is a static 5-run
  aggregate (mean/stdev/min/max per fixture×rubric) at a fixed `prompt_version`. `_load_baseline_scores`
  seeds the regression alerter from it (so comparisons are against a stable mean, not the
  noisiest prior run); real JSONL records with a later timestamp win
  ([`evals/runner.py:_load_baseline_scores`](../../../evals/runner.py)). `_detect_regression`
  flags any drop past `REGRESSION_DELTA` (default 0.5, sized for Haiku judge variance)
  ([`evals/runner.py:_detect_regression`](../../../evals/runner.py)). A non-zero
  `exit_code` (2) fires when any rubric fails OR a regression fires.
- **Anchor** — `evals/anchors/anchor-v1/` freezes the *fixtures* (jd/resume/expected) plus a
  `manifest.json` recording `prompt_version`, per-fixture `fixture_set_hash`, and the rubric
  list ([`evals/anchors/anchor-v1/manifest.json`](../../../evals/anchors/anchor-v1/manifest.json)).
  Rubric definitions are NOT frozen — all suites read the live `evals/rubrics/` as the single
  source of truth; only fixtures freeze per anchor version `[synthesis]`. `--suite anchor`
  stamps `anchor_version = "v1"` on records ([`evals/runner.py:run_suite`](../../../evals/runner.py)).

## The bootstrap engine

[`evals/bootstrap.py`](../../../evals/bootstrap.py) drives one corpus `seed.json` against
**many** JDs through the real pipeline, then deterministically collates the generated bullets
and skills across JDs into a `bootstrap.json` ([`evals/bootstrap.py:run_pipeline_over_jd_texts`](../../../evals/bootstrap.py),
[`evals/bootstrap.py:build_bootstrap_document`](../../../evals/bootstrap.py)). Cross-JD
collation is the point: a bullet near-identical across JDs is grounded core; one that re-skins
itself per JD is **JD-pandering**, visible only by comparing across JDs. `dedup_texts` is a
greedy Jaccard clusterer (default threshold 0.75) where `len(jd_files)` is the JD-invariance
signal and `size: 1` marks a JD-specific candidate to annotate ([`evals/bootstrap.py:dedup_texts`](../../../evals/bootstrap.py)).
Like the runner it orchestrates LLM calls but every collation step is LLM-free; output is
guarded under `evals/fixtures/real/` by a `_within` write check ([`evals/bootstrap.py:_resolve_output_path`](../../../evals/bootstrap.py)).

Skill extraction splits a résumé's skill line on commas / semicolons / pipes / middots
— but **only outside brackets**. `_split_skill_line` delegates to the shared
[`json_resume.py:split_outside_brackets`](../../../json_resume.py) primitive so a
parenthetical never fragments the entry it belongs to ("Eval Framework Design
(LLM-as-judge, rubric-based)" stays one skill, not two)
([`evals/bootstrap.py:_split_skill_line`](../../../evals/bootstrap.py), item 15). The
primitive is public and shared with `json_resume._parse_skills` precisely so the eval
side and the render side cannot disagree about where a skill ends — see
[[document-rendering]] `[synthesis]`.

## Annotation-pin integrity (items 11 and 13)

The bootstrap doc an `annotations.json` was built from is what its `cluster_index`
values key into, so collating against a *different* bootstrap silently grades one JD's
output against another JD's human-vetted expectations. Item 11 pinned the read to
`annotations.json`'s own `bootstrap_source` path; item 13 found that a **path** check
was not enough — a real fixture had had that same path overwritten in place, and the
eval graded a Zoox JD against Faros ground truth with nothing to catch it. Two
mechanisms now close it, both fail-closed:

- **Content, not just path.** `build_annotation_template` stamps a
  `bootstrap_fingerprint` (sha256 hex[:12] of the source's content) alongside
  `bootstrap_source` ([`evals/annotation.py:build_annotation_template`](../../../evals/annotation.py),
  [`evals/annotation.py:fingerprint`](../../../evals/annotation.py) — a deliberate copy
  of `scripts/verify_doc_template.py`'s convention rather than a cross-boundary import,
  since `evals/` must not depend on `scripts/`). Console-side resolution verifies it and
  refuses to substitute a different bootstrap — see [[diagnostics-console]].
  Annotations predating the field are unaffected; it is best-effort at write time
  (an unreadable source leaves it blank) and fail-closed only at read time.
- **The anchor must appear in the annotations.**
  [`evals/annotation.py:ensure_anchor_covered_by_annotations`](../../../evals/annotation.py)
  raises `ValueError` unless `pick_anchor_jd`'s result is a member of the annotated
  bullets' `jd_files`. It is a plain membership check with no normalization, because
  `_bullet_item_template` copies the name verbatim from the same cluster — so when the
  annotations really were built from the bootstrap just read, the strings are
  byte-identical. It runs **before** `collate_expected` in both drivers
  ([`evals/annotation.py:_cmd_collate`](../../../evals/annotation.py) and the console
  route), so a mismatch aborts instead of writing a corrupt fixture.

## Prompt-override A/B tuning

The primitive that A/Bs a candidate system prompt **without editing the persona constants**:
[`analyzer.py:prompt_overrides`](../../../analyzer.py) is a context manager that, for its
duration, makes `_resolve_system_prompt` return the candidate text for the named constants in
the `_BASE_SYSTEM_PROMPTS` registry, and makes [`analyzer.py:effective_prompt_version`](../../../analyzer.py)
return a stable `candidate:<sha256[:12]>` so the run is **quarantined** from score-over-time.
The default (empty/None) path is byte-identical — the resolver returns the identical constant
object and the version stays `PROMPT_VERSION` (`2026-07-08.4` at HEAD), so the analyze→generate
cache is untouched `[synthesis]`. `run_suite` enters the context over the whole fixture loop
when `--prompt-overrides` supplies a name→text mapping
([`evals/runner.py:run_suite`](../../../evals/runner.py)); unknown constant names raise
`ValueError` inside [`analyzer.py:prompt_overrides`](../../../analyzer.py) before any paid call.
Override scope is the named system-prompt constants only, not the dynamic user-prompt builders.

## Two entry points, one core

`run_suite` is the importable core; `main` is the CLI wrapper. The same core also backs the
localhost `POST /api/eval/run` console route, which passes a `progress` callback to stream
per-fixture/per-rubric milestones to the browser dashboard; the default `progress=None` path
makes every `_emit` a no-op so the written bytes are unchanged `[synthesis]`
([`evals/runner.py:run_suite`](../../../evals/runner.py)). An optional `cancel_check`
callable, when set, is polled before each paid LLM call (fixture start, before clarify,
before generate/assemble, before grading judges) — the first `True` reading stops the run
early and sets `EvalRunResult.cancelled=True`; already-written JSONL records are kept
`[synthesis]` ([`evals/runner.py:run_suite`](../../../evals/runner.py),
[`evals/bootstrap.py:run_pipeline_over_jd_texts`](../../../evals/bootstrap.py)).

A zero-result-record guard (RH-2, 2026-07 e2e-run-health-review) detects runs where every
matched fixture failed to load or grade, leaving a silent 0-byte JSONL on disk with no error
trace. The run now deletes the empty file and raises `RuntimeError` so the caller (CLI `main()`
or console SSE routes) surfaces a real error instead of a phantom "0 pass / 0 fail" done event
([`evals/runner.py:run_suite`](../../../evals/runner.py)) `[synthesis]`.

## Related

- [[code-module-map]] — where `evals/` sits in the module graph.
- [[generation-and-grounding]] — the grounding contract the `grounding` rubric scores against.
- [[prompt-version-discipline]] — why `PROMPT_VERSION` and `candidate:<hash>` matter for attribution.
- [[deterministic-llm-boundary]] — why `hardening.extract_jd_label` lives on the
  LLM-free side even though only the eval path uses it.
- [[diagnostics-console]] — the dashboard + `/api/eval/run` route that share `run_suite`;
  where the `bootstrap_fingerprint` check fails closed and where `jd_label` is rendered.
- [[document-rendering]] — `json_resume.split_outside_brackets`, the skill-split
  primitive `evals/bootstrap.py` shares with the render path.
- [[non-dependency-downloads]] — the optional `--grounding-signals` model weights extra.
