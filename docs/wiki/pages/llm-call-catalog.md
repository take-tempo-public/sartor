# LLM call catalog

> **Audience:** `dev`
> **Concept:** the full set of LLM call kinds sartor. makes, which model tier each routes to (Sonnet 5 = heavy reasoning; Haiku 4.5 = structured selection), and the two-pass analyze (Haiku extraction → Sonnet synthesis) that anchors the analyze→generate cache.
> **Sources:** [`analyzer.py`](../../../analyzer.py), [`onboarding/extract_experiences.py`](../../../onboarding/extract_experiences.py), [`blueprints/applications.py`](../../../blueprints/applications.py), [`blueprints/corpus/skills.py`](../../../blueprints/corpus/skills.py), [`architecture.md` §"LLM routing + cost"](../../architecture.md), [`architecture.md` §"System overview"](../../architecture.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## Two tiers, one helper

Every call in this catalog routes through `_call_llm` / `_parse_or_retry`, which take
an optional `model` arg that **defaults to `SONNET_MODEL`** — the resolution
`effective_model = model or SONNET_MODEL` lives in
[`analyzer.py:_call_llm_streaming`](../../../analyzer.py), which the non-streaming
[`analyzer.py:_call_llm`](../../../analyzer.py) wraps. The two model constants are
[`analyzer.py:SONNET_MODEL`](../../../analyzer.py) (`"claude-sonnet-5"`) and
[`analyzer.py:HAIKU_MODEL`](../../../analyzer.py) (`"claude-haiku-4-5-20251001"`).
A call is Sonnet when it passes **no** `model=` (the default); it is Haiku when it
explicitly passes `model=HAIKU_MODEL` `[synthesis]`. The legacy `MODEL` alias still
points at `SONNET_MODEL` but new code references the tier constants directly
([`analyzer.py:MODEL`](../../../analyzer.py)).

The split is deliberate: **Sonnet 5 for heavy reasoning** (large JSON, strategy,
prose); **Haiku 4.5 for structured selection / classification** (cheap, fast, ~5 s
median per [`architecture.md`](../../architecture.md) §"LLM routing + cost"). Every
call carries a `call_kind` string for JSONL telemetry + the dashboard, with a
`<kind>_retry` sibling on the retry path ([`analyzer.py:_parse_or_retry`](../../../analyzer.py)).

## Sonnet 5 — heavy reasoning (default tier)

| call_kind | Function | Notes |
|---|---|---|
| `analyze_synthesis` | [`analyze`](../../../analyzer.py) | Pass 2 of analyze; runs under the default `SYSTEM_PROMPT` (no override). |
| `generate` | [`generate`](../../../analyzer.py) / [`generate_streaming`](../../../analyzer.py) | The tailored-résumé producer. |
| `generate_cover_letter` | [`generate_cover_letter_against_resume`](../../../analyzer.py) | Optional cover-letter pass. |
| `iterate_clarify` | [`clarify_iteration`](../../../analyzer.py) | Iteration-time interview; **no `model=` override → Sonnet** `[synthesis]`. |
| `draft_summary` | [`draft_positioning_summary`](../../../analyzer.py) | Generation-experience re-architecture: drafts the JD-tailored two-sentence positioning summary ONCE at Compose. Fired by `POST /api/applications/<id>/draft-summary` ([`blueprints/applications.py:draft_application_summary`](../../../blueprints/applications.py)). Explicit `model=SONNET_MODEL`, not the bare default. Short-circuits without a call when there is no JD `[synthesis]`. |
| `draft_gap_fill` | [`draft_gap_fill_bullets`](../../../analyzer.py) | Generation-experience re-architecture Phase 3: drafts GROUNDED gap-fill bullets (evidence-or-nothing) for JD requirements the corpus doesn't cover, for accept/retire. Fired by `POST /api/applications/<id>/draft-gap-fill` ([`blueprints/applications.py:draft_application_gap_fill`](../../../blueprints/applications.py)), both the once-per-application auto-fire and the explicit "Regenerate suggestions" affordance. Explicit `model=SONNET_MODEL`. Short-circuits without a call when there is no corpus or no JD `[synthesis]`. |
| `draft_surgical_refinement` | [`draft_surgical_refinement`](../../../analyzer.py) | Generation-experience re-architecture item (a): drafts ONE scoped, single-item refinement (a sharpened bullet or the positioning summary — never a whole-document rewrite) from a free-text note against the frozen `approved_composition`. Fired by `POST /api/applications/<id>/draft-refinement` ([`blueprints/applications.py:draft_application_refinement`](../../../blueprints/applications.py)). Explicit `model=SONNET_MODEL`. Short-circuits without a call when there is no frozen composition, no JD, or no note `[synthesis]`. |

Note the name mismatch: the function is `clarify_iteration()` but its `call_kind`
string is `"iterate_clarify"` ([`analyzer.py:clarify_iteration`](../../../analyzer.py)).
The first four omit `model=` and inherit the Sonnet default; the three Compose
drafting calls (`draft_summary`, `draft_gap_fill`, `draft_surgical_refinement`) pass
`model=SONNET_MODEL` explicitly instead `[synthesis]`.

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
| `suggest_skill_from_corpus` | [`suggest_skills_from_corpus`](../../../analyzer.py) | Sibling of `suggest_skills` for the "Suggest skills from my corpus" affordance — no JD in view, so the evidence gate drops the AND-with-JD condition down to evidence-alone. Fired by `POST /api/users/<username>/skills/suggest-from-corpus` ([`blueprints/corpus/skills.py:suggest_skills_from_corpus_route`](../../../blueprints/corpus/skills.py)). Same pending-review approve/deny gate as `suggest_skill` `[synthesis]`. |
| `critique_proposal` | [`critique_proposal`](../../../analyzer.py) | Structured critique of a proposal. |
| `promote_clarification_to_bullet` | [`analyzer.py` promote helper](../../../analyzer.py) | Turns a confirmed clarification into a bullet. |
| `extract_experiences` | [`onboarding/extract_experiences.py:extract_experiences`](../../../onboarding/extract_experiences.py) | Onboarding/corpus résumé ingest — **lives outside `analyzer.py`** `[synthesis]`. |
| `avatar_answer` | [`avatar_answer_streaming`](../../../analyzer.py) | **Memory/recall subsystem only** — the doc-grounded assistant, answering questions over a `recall.Context` (not a `context_set`). Avatar-prompt revisions track a separate source constant [`AVATAR_PROMPT_VERSION`](../../../analyzer.py); telemetry still stamps `PROMPT_VERSION` — see [[prompt-version-discipline]] `[synthesis]`. |

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
the `recommend_*`/`suggest_skills`/`suggest_skills_from_corpus` family, `extract_experiences`,
and the three Compose drafting calls `draft_positioning_summary` / `draft_gap_fill_bullets` /
`draft_surgical_refinement`) pay one cache-miss on the system block; the cheap small calls
also pass `cached_user_prefix=""` because there is no long static block worth caching
([`analyzer.py:_call_llm`](../../../analyzer.py)) `[synthesis]`.
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
