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

## Prompt-override A/B tuning

The primitive that A/Bs a candidate system prompt **without editing the persona constants**:
[`analyzer.py:prompt_overrides`](../../../analyzer.py) is a context manager that, for its
duration, makes `_resolve_system_prompt` return the candidate text for the named constants in
the `_BASE_SYSTEM_PROMPTS` registry, and makes [`analyzer.py:effective_prompt_version`](../../../analyzer.py)
return a stable `candidate:<sha256[:12]>` so the run is **quarantined** from score-over-time.
The default (empty/None) path is byte-identical — the resolver returns the identical constant
object and the version stays `PROMPT_VERSION` (`2026-06-12.2` at HEAD), so the analyze→generate
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
([`evals/runner.py:run_suite`](../../../evals/runner.py)).

## Related

- [[code-module-map]] — where `evals/` sits in the module graph.
- [[generation-and-grounding]] — the grounding contract the `grounding` rubric scores against.
- [[prompt-version-discipline]] — why `PROMPT_VERSION` and `candidate:<hash>` matter for attribution.
- [[diagnostics-console]] — the dashboard + `/api/eval/run` route that share `run_suite`.
- [[non-dependency-downloads]] — the optional `--grounding-signals` model weights extra.
