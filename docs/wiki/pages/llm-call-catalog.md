# LLM call catalog

> **Audience:** `dev`
> **Concept:** the full set of LLM call kinds callback. makes, which model tier each routes to (Sonnet 4.6 = heavy reasoning; Haiku 4.5 = structured selection), and the two-pass analyze (Haiku extraction → Sonnet synthesis) that anchors the analyze→generate cache.
> **Sources:** [`analyzer.py`](../../../analyzer.py), [`onboarding/extract_experiences.py`](../../../onboarding/extract_experiences.py), [`architecture.md` §"LLM routing + cost"](../../architecture.md), [`llm-routing.mmd`](../../diagrams/llm-routing.mmd), [`pipeline.mmd`](../../diagrams/pipeline.mmd).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## Two tiers, one helper

Every call in this catalog routes through `_call_llm` / `_parse_or_retry`, which take
an optional `model` arg that **defaults to `SONNET_MODEL`** — the resolution
`effective_model = model or SONNET_MODEL` lives in
[`analyzer.py:_call_llm_streaming`](../../../analyzer.py), which the non-streaming
[`analyzer.py:_call_llm`](../../../analyzer.py) wraps. The two model constants are
[`analyzer.py:SONNET_MODEL`](../../../analyzer.py) (`"claude-sonnet-4-6"`) and
[`analyzer.py:HAIKU_MODEL`](../../../analyzer.py) (`"claude-haiku-4-5-20251001"`).
A call is Sonnet when it passes **no** `model=` (the default); it is Haiku when it
explicitly passes `model=HAIKU_MODEL` `[synthesis]`. The legacy `MODEL` alias still
points at `SONNET_MODEL` but new code references the tier constants directly
([`analyzer.py:MODEL`](../../../analyzer.py)).

The split is deliberate: **Sonnet 4.6 for heavy reasoning** (large JSON, strategy,
prose); **Haiku 4.5 for structured selection / classification** (cheap, fast, ~5 s
median per [`architecture.md`](../../architecture.md) §"LLM routing + cost"). Every
call carries a `call_kind` string for JSONL telemetry + the dashboard, with a
`<kind>_retry` sibling on the retry path ([`analyzer.py:_parse_or_retry`](../../../analyzer.py)).

## Sonnet 4.6 — heavy reasoning (default tier)

| call_kind | Function | Notes |
|---|---|---|
| `analyze_synthesis` | [`analyze`](../../../analyzer.py) | Pass 2 of analyze; runs under the default `SYSTEM_PROMPT` (no override). |
| `generate` | [`generate`](../../../analyzer.py) / [`generate_streaming`](../../../analyzer.py) | The tailored-résumé producer. |
| `generate_cover_letter` | [`generate_cover_letter_against_resume`](../../../analyzer.py) | Optional cover-letter pass. |
| `iterate_clarify` | [`clarify_iteration`](../../../analyzer.py) | Iteration-time interview; **no `model=` override → Sonnet** `[synthesis]`. |

Note the name mismatch: the function is `clarify_iteration()` but its `call_kind`
string is `"iterate_clarify"` ([`analyzer.py:clarify_iteration`](../../../analyzer.py)).
All four omit `model=`, so they inherit the Sonnet default `[synthesis]`.

## Haiku 4.5 — structured selection (explicit `model=HAIKU_MODEL`)

| call_kind | Function | Notes |
|---|---|---|
| `analyze_extraction` | [`analyze`](../../../analyzer.py) | Pass 1 of analyze; JD keyword/vocabulary extraction. |
| `clarify` | [`clarify`](../../../analyzer.py) | Analyze-time interview — **now Haiku** (r1/clarify-model-trial, eval-gated) `[synthesis]`. |
| `recommend` | [`recommend_bullets`](../../../analyzer.py) | Per-application bullet selection (Compose). |
| `recommend_summary` | [`recommend_summaries`](../../../analyzer.py) | Summary-variant selection. |
| `recommend_experience_summary` | [`recommend_experience_summaries`](../../../analyzer.py) | Per-role intro selection. |
| `recommend_skill` | [`recommend_skills`](../../../analyzer.py) | Skill-item selection. |
| `suggest_skill` | [`suggest_skills`](../../../analyzer.py) | Proposes NEW canonical skills (grounded; human approve/deny gate). |
| `critique_proposal` | [`critique_proposal`](../../../analyzer.py) | Structured critique of a proposal. |
| `promote_clarification_to_bullet` | [`analyzer.py` promote helper](../../../analyzer.py) | Turns a confirmed clarification into a bullet. |
| `extract_experiences` | [`onboarding/extract_experiences.py:extract_experiences`](../../../onboarding/extract_experiences.py) | Onboarding/corpus résumé ingest — **lives outside `analyzer.py`** `[synthesis]`. |

Watch the function-name vs. `call_kind` drift in the recommend family: the functions
are plural (`recommend_bullets`, `recommend_summaries`, …) but the `call_kind` strings
are singular and `recommend_bullets` emits the bare `"recommend"` kind
([`analyzer.py:recommend_bullets`](../../../analyzer.py)) `[synthesis]`.

One Haiku call sits deliberately **outside** this funnel and so carries no `call_kind`:
the fail-open refinement-scope classifier
[`analyzer.py:check_refinement_scope`](../../../analyzer.py) (hardcoded
[`analyzer.py:SCOPE_CHECK_MODEL`](../../../analyzer.py)) opens its own
`client.messages.create` with no telemetry, caching, or retry — the lone by-design
exception, detailed in [[deterministic-llm-boundary]] `[synthesis]`.

## The two-pass analyze (the cache-defining detail)

`analyze()` is **not one Sonnet call** — it is Haiku extraction → Sonnet synthesis
([`analyzer.py:analyze`](../../../analyzer.py), mirrored in
[`analyze_streaming`](../../../analyzer.py)):

1. **Pass 1 — `analyze_extraction` (Haiku).** Keyword/vocabulary signals only, no
   strategy. Runs under its own [`analyzer.py:EXTRACTION_SYSTEM_PROMPT`](../../../analyzer.py),
   wired in at the `analyze()` call site via
   `system_prompt=_resolve_system_prompt("EXTRACTION_SYSTEM_PROMPT")`
   ([`analyzer.py:analyze`](../../../analyzer.py)); the *user* prompt is built by
   [`analyzer.py:_analyze_extraction_prompt`](../../../analyzer.py).
2. **Pass 2 — `analyze_synthesis` (Sonnet).** Strategy + positioning, grounded in
   Pass 1's `<extracted_signal>`. Runs under the **default `SYSTEM_PROMPT`** — *not* a
   dedicated synthesis persona ([`analyzer.py:analyze`](../../../analyzer.py)).

Both passes share one `cached_user_prefix` (`_stable_user_prefix(context_set)`), and
because synthesis uses the shared `SYSTEM_PROMPT`, its `[SYSTEM_PROMPT][prefix]` block
is **byte-identical to `generate()`'s** — synthesis WRITES the prompt-cache block that
the later `generate` call READS. A distinct synthesis persona would diverge at the
system block and force `generate` to re-prefill the whole corpus `[synthesis]`. The
rationale is annotated inline as P6 (Specialized Review) for the two narrow personas
and P9 (Token Economy) for keeping the cache intact ([`analyzer.py:analyze`](../../../analyzer.py)).

The merged result `{**extraction, **synthesis}` is the single `AnalyzeResponse` shape
every downstream consumer expects (frontend renderer, `clarify`, `generate`, eval
rubrics) ([`analyzer.py:analyze`](../../../analyzer.py)) `[synthesis]`.

## Cache + system-prompt overrides

Calls that pass a non-default `system_prompt` (the `clarify` variants, `critique_proposal`,
the `recommend_*`/`suggest_skills` family, `extract_experiences`) pay one cache-miss on
the system block; the cheap small calls also pass `cached_user_prefix=""` because there
is no long static block worth caching ([`analyzer.py:_call_llm`](../../../analyzer.py)) `[synthesis]`.
Only `analyze_synthesis` and `generate` ride the heavy corpus-prefix cache — see
[`architecture.md`](../../architecture.md) §"LLM routing + cost" for the green/red
cache map and real p50 latencies.

The deterministic/LLM boundary (which modules may make these calls), the
`PROMPT_VERSION`-bump discipline, and the prompt-override A/B primitive are
canonical in [`AGENTS.md`](../../../AGENTS.md) — referenced here, not restated (D5).

## Related

- [[code-module-map]] — where `analyzer.py` sits among the modules.
- [[deterministic-llm-boundary]] — which modules may (and may not) make these calls.
- [[prompt-version-discipline]] — bump `PROMPT_VERSION` when any of these prompts change.
- [[pipeline-stages]] — the route → call sequence these kinds fire in.
- [[generation-and-grounding]] — what the `generate` call must not invent.
- [[route-surface]] — the Flask routes that invoke each call kind.
