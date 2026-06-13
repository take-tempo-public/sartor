# Generation and grounding

> **Audience:** `dev`
> **Concept:** how `generate()` produces the tailored résumé / cover-letter
> markdown, and the deterministic post-generation metrics that score whether it
> stayed grounded — the product enforcing on itself the same no-invention rule
> this wiki follows.
> **Sources:** [`analyzer.py`](../../../analyzer.py) (`generate`, the generate
> prompt's GROUNDING CHECK + worked examples), [`hardening.py`](../../../hardening.py)
> (the post-gen metric functions + `assemble_source_union`),
> [`evals/runner.py`](../../../evals/runner.py) (the groundedness composite).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The generate call

[`analyzer.py:generate`](../../../analyzer.py) is "Call 2: Generation" — the heavy
Sonnet call that turns the analysis + context_set into tailored `resume_content`
and (optionally) `cover_letter_content`. It is thin: it builds the prompt via
`_build_generate_prompt`, then hands off to `_parse_or_retry` with
`call_kind="generate"` and a `cached_user_prefix` from `_stable_user_prefix`
([`analyzer.py:generate`](../../../analyzer.py)). The same prompt powers the
token-streaming `generate_streaming` counterpart so SSE routes and non-streaming
callers share one prompt builder `[synthesis]`. When `with_cover_letter` is False
the cover-letter rules + schema line are dropped and the result still carries an
empty `cover_letter_content` so renderers never KeyError
([`analyzer.py:generate`](../../../analyzer.py)).

## The grounding check is the load-bearing prompt section

The résumé prompt's `<resume_rules>` opens with a **GROUNDING CHECK** applied
"before writing every bullet": each claim — *every number, technology, title,
company, and timeframe* — must trace to the résumé draft, a historical /
supplemental résumé, or a clarification answer; if YES the model may reframe and
keyword-align freely, if NO it must omit ([`analyzer.py`](../../../analyzer.py),
the GROUNDING CHECK block). First-person typed edits **and** clarification answers
are explicitly admitted as ground truth even when the original primary résumé did
not mention them — the carve-out AGENTS.md describes, kept surgical (the
no-invention rule still applies beyond that union) `[synthesis]`.

The teaching signal is the **worked-examples block** — OK / NOT-OK pairs that name
the failure mode in each NOT-OK line ([`analyzer.py`](../../../analyzer.py)):

- paraphrase OK; **inventing a technique / audience** not in source ("time-series
  forecasting", "executive stakeholders") NOT OK;
- restating tooling OK; **naming a vendor / cadence** not in source ("Jenkins",
  "nightly regression") NOT OK;
- "streamlined a workflow" OK; **scope inflation** ("team" → "organization-wide")
  NOT OK;
- echoing a typed edit OK; **extending it with a headcount** the candidate never
  typed ("50 enterprise customers") NOT OK;
- reordering experiences for relevance OK; **reconciling two roles' date ranges**
  onto one NOT OK (dates are immutable).

This pairing — a rule plus a concrete OK/NOT-OK example — is the convention
AGENTS.md mandates extending whenever a new failure mode is added `[synthesis]`.

## Corpus mode tightens grounding to verbatim selection

When the candidate has a corpus, `_build_generate_prompt` prepends a
`<corpus_mode>` block: every emitted bullet must EITHER reproduce a `<bullet>`
verbatim (recording its `id` in `selected_bullets`) OR be listed in
`proposed_new_bullets` for human review — "no other bullets are permitted"
([`analyzer.py`](../../../analyzer.py), the `corpus_mode_block` /
`GROUNDING for corpus mode` text). Dates carry an IMMUTABLE-ground-truth clause,
pinned titles/bullets are forced into the output, and an optional `<summary>` role
intro is verbatim ground truth too. The legacy GROUNDING CHECK still governs the
cover letter and any reframing language between bullets `[synthesis]`.

## The deterministic metrics that score grounding

The prompt is the *ask*; the deterministic metrics in
[`hardening.py`](../../../hardening.py) are the *audit* — no LLM, hot-path-safe,
so they can run on every generation. They share constants (`BULLET_LINE_RE`,
`METRIC_RE`, `STOP_WORDS`) so definitions never drift between metrics `[synthesis]`:

- [`hardening.py:compute_verb_diversity`](../../../hardening.py) — unique
  leading-verbs ÷ bullets; surfaces `top_repeated` offenders (recycled verbs).
- [`hardening.py:compute_specificity_density`](../../../hardening.py) — fraction of
  bullets carrying a metric; high density + low grounding = invented numbers.
- [`hardening.py:compute_top_third_density`](../../../hardening.py) — do the first
  3 bullets of the experience section surface the JD's top-3 essentials.
- [`hardening.py:compute_quantification_rate`](../../../hardening.py) — single float
  for the eval composite; shares `METRIC_RE` with specificity.
- [`hardening.py:compute_grounding_overlap`](../../../hardening.py) — fraction of
  generated 3-grams appearing verbatim in any source; the actionable output is
  `missing_samples` (non-stopword 3-grams absent from every source). The ratio
  alone is **not** pass/fail — legitimate rewriting lowers overlap.
- [`hardening.py:compute_fabricated_specifics`](../../../hardening.py) — the
  sharpened successor to `missing_samples`: per-bullet it extracts typed specifics
  (numbers / %, $, dates, durations, entity tokens), checks each against the source
  union with numeric tolerance + entity alias-normalization, and returns a
  severity-weighted `fabricated_specifics_rate` (numeric > entity) plus
  `flagged_samples`. A flag-for-review signal, not a hard gate (UNCALIBRATED).
- [`hardening.py:compute_date_grounding`](../../../hardening.py) — the KW6 guard:
  bullet scans miss `### Company, Title\tStart – End` heading dates, so this
  multiset-compares heading year ranges against true corpus ranges, catching both
  **alteration** (a range in no experience) and **duplication** (one true range
  stamped on two headings). Warn-only — it never mutates the LLM output.

## One source union, one composite

[`hardening.py:assemble_source_union`](../../../hardening.py) is the *single*
definition of what counts as ground truth — primary résumé + supplementals +
clarification answers — and it deliberately mirrors what `generate()`'s widened
grounding check admits, so the iteration clarifier and the eval-time
fabricated-specifics check can never score against divergent source sets. It is
recomputed per iteration because the union grows as clarifications arrive
([`hardening.py:assemble_source_union`](../../../hardening.py)).

The reportable signal is the **groundedness composite** in
[`evals/runner.py:_groundedness_composite`](../../../evals/runner.py): it folds the
L0 `fabricated_specifics_rate` into a 0–5 projection (`5 * (1 - rate)`) that plugs
into the dashboard's score-over-time chart, attributable by `prompt_version`.
`_enrich_groundedness` later layers in the eval-only L1/L2 (NLI + MiniCheck)
signals when `--grounding-signals` runs; default runs stay honest L0-only
([`evals/runner.py:_enrich_groundedness`](../../../evals/runner.py)).
`_post_generation_metrics` is where all of the above ride along on every eval
record ([`evals/runner.py:_post_generation_metrics`](../../../evals/runner.py)).

## The recursion worth naming

The wiki's own grounding rule (a page may not assert past its sources — see
[`SCHEMA.md`](../SCHEMA.md)) is the *same rule* the product enforces on its LLM
output: synthesis may select, condense, and reframe, but never invent past the
source. `generate()`'s GROUNDING CHECK is to a tailored bullet what this wiki's
grounding contract is to a synthesized page `[synthesis]`. These metrics are
deterministic by mandate — the no-LLM boundary AGENTS.md draws around
`hardening.py` — referenced here, not restated (D5).

## Related

- [[code-module-map]] — where `generate()` and the metrics sit in the module map.
- [[llm-call-catalog]] — the full set of LLM call kinds; `generate` is Call 2.
- [[deterministic-llm-boundary]] — why the metrics live in `hardening.py` (no LLM).
- [[eval-harness]] — the runner that assembles these metrics + the composite.
- [[document-rendering]] — what consumes the `# / ## / ###` markdown `generate()` emits.
