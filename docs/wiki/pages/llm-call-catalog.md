# LLM call catalog

> **Audience:** `dev`
> **Concept:** the full set of LLM call kinds sartor. makes, which model tier each routes to (Sonnet 5 = heavy reasoning; Haiku 4.5 = structured selection), and the two-pass analyze (Haiku extraction → Sonnet synthesis) that anchors the analyze→generate cache.
> **Sources:** [`analyzer.py`](../../../analyzer.py), [`onboarding/extract_experiences.py`](../../../onboarding/extract_experiences.py), [`blueprints/applications.py`](../../../blueprints/applications.py), [`blueprints/corpus/skills.py`](../../../blueprints/corpus/skills.py), [`architecture.md` §"LLM routing + cost"](../../dev/architecture.md), [`architecture.md` §"System overview"](../../dev/architecture.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## Two tiers, one helper

Every call in this catalog reaches the API through [`analyzer.py:_call_llm_streaming`](../../../analyzer.py): the non-streaming
calls via `_call_llm` / `_parse_or_retry`, the streaming `analyze` and `generate` passes via
[`analyzer.py:_parse_or_retry_streaming`](../../../analyzer.py), and the doc-grounded assistant
([`analyzer.py:avatar_answer_streaming`](../../../analyzer.py)) directly, with no response validation `[synthesis]`.
These helpers take an optional `model` arg that **defaults to `SONNET_MODEL`** — the resolution
happens in [`analyzer.py:_call_llm_streaming`](../../../analyzer.py) (which the non-streaming
[`analyzer.py:_call_llm`](../../../analyzer.py) wraps): first `requested_model = model or SONNET_MODEL`,
then `effective_model = _resolve_model(requested_model)` to apply any active model overrides
([`analyzer.py:_resolve_model`](../../../analyzer.py)) `[synthesis]`. The two model constants are
[`analyzer.py:SONNET_MODEL`](../../../analyzer.py) (`"claude-sonnet-5"`) and
[`analyzer.py:HAIKU_MODEL`](../../../analyzer.py) (`"claude-haiku-4-5-20251001"`).
A call is Sonnet when it passes **no** `model=` (the default); it is Haiku when it
explicitly passes `model=HAIKU_MODEL` `[synthesis]`. The legacy `MODEL` alias still
points at `SONNET_MODEL` but new code references the tier constants directly
([`analyzer.py:MODEL`](../../../analyzer.py)).

The split is deliberate: **Sonnet 5 for heavy reasoning** (large JSON, strategy,
prose); **Haiku 4.5 for structured selection / classification** (cheap, fast; routing in
[`architecture.md`](../../dev/architecture.md) §"LLM routing + cost", which carries no latency figures). Every
call carries a `call_kind` string for JSONL telemetry + the dashboard; calls through [`analyzer.py:_parse_or_retry`](../../../analyzer.py) / [`analyzer.py:_parse_or_retry_streaming`](../../../analyzer.py) have a
`<kind>_retry` sibling on the retry path, while [`analyzer.py:avatar_answer_streaming`](../../../analyzer.py) calls `_call_llm_streaming` directly with no retry variant `[synthesis]`.

On the retry path, both `_parse_or_retry` and `_parse_or_retry_streaming` accept an optional `validation_context` dict that carries a handle guard — built by [`analyzer.py:_handle_guard`](../../../analyzer.py), [`analyzer.py:_corpus_guard`](../../../analyzer.py), or [`analyzer.py:_block_guard`](../../../analyzer.py) at call time. The pydantic after-validator [`analyzer.py:_LLMResponse.reject_handle_leaks`](../../../analyzer.py) rejects any prose that names an id handle the prompt shipped, except id-typed fields (matching the pattern in [`hardening.py:_HANDLE_ID_KEY_RE`](../../../hardening.py)) which are always permitted `[synthesis]`. If validation fails on the first attempt, the retry is re-asked with the error appended; if it fails again, [`analyzer.py:_accept_soft_leaks`](../../../analyzer.py) decides the outcome. Leaks in top-level fields listed in the guard's `hard_fields` (e.g., `resume_content`, `cover_letter_content` — see [`analyzer.py:_SHIPPED_FIELDS`](../../../analyzer.py)) still raise `LLMResponseError`; a leak elsewhere is accepted with a logged warning, but only when every validation failure on that attempt is itself a handle leak: a leak alongside a missing key or malformed JSON still raises `LLMResponseError`. Four `analyzer.py` calls forward no guard because their prompts ship no id handles: `check_refinement_scope`, `critique_proposal`, `promote_clarification_to_bullet`, and `draft_summary` — enumerated in [`tests/test_handle_guard.py:EXEMPT_CALL_KINDS`](../../../tests/test_handle_guard.py) with reasons `[synthesis]`.

## Sonnet 5 — heavy reasoning (default tier)

| call_kind | Function | Notes |
|---|---|---|
| `analyze_synthesis` | [`analyze`](../../../analyzer.py) | Pass 2 of analyze; runs under the default `SYSTEM_PROMPT` (no override). |
| `generate` | [`generate`](../../../analyzer.py) / [`generate_streaming`](../../../analyzer.py) | The tailored-résumé producer. |
| `generate_cover_letter` | [`generate_cover_letter_against_resume`](../../../analyzer.py) | Optional cover-letter pass. |
| `iterate_clarify` | [`clarify_iteration`](../../../analyzer.py) | Iteration-time interview; **no `model=` override → Sonnet** `[synthesis]`. |
| `draft_summary` | [`draft_positioning_summary`](../../../analyzer.py) | Generation-experience re-architecture: drafts the JD-tailored two-sentence positioning summary ONCE at Compose. Fired by `POST /api/applications/<id>/draft-summary` ([`blueprints/applications.py:draft_application_summary`](../../../blueprints/applications.py)). Explicit `model=SONNET_MODEL`, not the bare default. Short-circuits without a call when there is no JD `[synthesis]`. |
| `draft_gap_fill` | [`draft_gap_fill_bullets`](../../../analyzer.py) | Generation-experience re-architecture Phase 3: drafts GROUNDED gap-fill bullets (evidence-or-nothing) for JD requirements the corpus doesn't cover, for accept/retire. Fired by `POST /api/applications/<id>/draft-gap-fill` ([`blueprints/applications.py:draft_application_gap_fill`](../../../blueprints/applications.py)), both the once-per-application auto-fire and the explicit "Regenerate suggestions" affordance. Explicit `model=SONNET_MODEL`. Short-circuits without a call when there is no corpus or no JD `[synthesis]`. |
| `draft_experience_summary` | [`draft_experience_summaries`](../../../analyzer.py) | Epic A sprint A3: drafts a GROUNDED, JD-fitted one-line intro for EACH included role, BATCHED — one call for every role, never one call per role. Fired by `POST /api/applications/<id>/draft-experience-summaries` ([`blueprints/applications.py:draft_application_experience_summaries`](../../../blueprints/applications.py)), gated on the "Add role intros" opt-in (not an arrival auto-fire, unlike gap-fill — most applications never turn this on). Explicit `model=SONNET_MODEL`. Short-circuits without a call when there is no JD or no staged role target `[synthesis]`. |
| `draft_surgical_refinement` | [`draft_surgical_refinement`](../../../analyzer.py) | Generation-experience re-architecture item (a): drafts ONE scoped, single-item refinement (a sharpened bullet or the positioning summary — never a whole-document rewrite) from a free-text note against `approved_composition`: the frozen snapshot, or one rebuilt from the corpus first when `hardening.py:composition_is_stale` finds Compose has changed since the freeze. Fired by `POST /api/applications/<id>/draft-refinement` ([`blueprints/applications.py:draft_application_refinement`](../../../blueprints/applications.py)). Explicit `model=SONNET_MODEL`. Short-circuits without a call when there is no frozen composition, no JD, or no note `[synthesis]`. |

Note the name mismatch: the function is `clarify_iteration()` but its `call_kind`
string is `"iterate_clarify"` ([`analyzer.py:clarify_iteration`](../../../analyzer.py)).
The first four omit `model=` and inherit the Sonnet default; the four Compose
drafting calls (`draft_summary`, `draft_gap_fill`, `draft_experience_summary`,
`draft_surgical_refinement`) pass `model=SONNET_MODEL` explicitly instead
`[synthesis]`.

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
| `avatar_answer` | [`avatar_answer_streaming`](../../../analyzer.py) | **Memory/recall subsystem only** — the doc-grounded assistant, answering questions over a `recall.Context` (not a `context_set`). Avatar-prompt revisions track a separate source constant [`AVATAR_PROMPT_VERSION`](../../../analyzer.py); its telemetry rows are stamped with it (passed as `prompt_version`), not with `PROMPT_VERSION` — see [[prompt-version-discipline]] `[synthesis]`. |
| `check_refinement_scope` | [`check_refinement_scope`](../../../analyzer.py) | Fail-open scope classifier for a free-text refinement note (`POST /api/validate-refinement`). Fixed item 21 (2026-08-02): now routes through `_parse_or_retry` like every other Haiku call, with a `max_tokens=128` cap (the shared helper's `max_tokens` kwarg, defaulting to `MAX_TOKENS` for every other call site) and a named `SCOPE_CHECK_SYSTEM_PROMPT` `[synthesis]`. |

Watch the function-name vs. `call_kind` drift in the recommend family: the functions
are plural (`recommend_bullets`, `recommend_summaries`, …) but the `call_kind` strings
are singular and `recommend_bullets` emits the bare `"recommend"` kind
([`analyzer.py:recommend_bullets`](../../../analyzer.py)) `[synthesis]`.

Every Haiku call now reaches `_emit_call_log` through the shared funnel — as of
item 21 (2026-08-02), `check_refinement_scope` was the last exception and is no
longer one. Its own outer `except Exception` fail-open contract (an outage or
unparseable response still returns `{"valid": true}`) is unchanged; the difference
is that outage now ALSO produces a `status="error"` telemetry row instead of
vanishing silently — see [[deterministic-llm-boundary]] `[synthesis]`.

## Error capture — status="error" telemetry rows (Epic C C1c)

All LLM calls emit one JSONL record per call to `logs/llm_calls.jsonl` via
[`analyzer.py:_emit_call_log`](../../../analyzer.py). When a call fails, the
`status` field is set to `"error"` and two additional fields are appended
(in the record built in [`analyzer.py:_call_llm_streaming`](../../../analyzer.py)) `[synthesis]`:

- **`error_type`** — the exception class name (`"APIError"`, `"TypeError"`,
  `"LLMConfigurationError"`, etc.), captured via
  [`analyzer.py:type(exc).__name__`](../../../analyzer.py).
- **`error_message`** — a redacted, 500-character-truncated string representation
  of the exception, produced by
  [`analyzer.py:_redact_error_message(_safe_exc_str(exc))`](../../../analyzer.py).
  Redaction collapses whitespace, masks API-key-shaped substrings and any
  `x-api-key`/`Authorization` header values, then truncates with a trailing
  `"…[truncated]"` marker if needed ([`analyzer.py:_redact_error_message`](../../../analyzer.py),
  deterministic and safe to run on every error row). The captured `str(exc)`
  can never replace the caller's exception — it is re-raised after telemetry is
  recorded, unchanged except on the SDK no-credential path, where
  `analyzer.py:_call_llm_streaming` re-labels the `TypeError` as
  `LLMConfigurationError` (chained with `from exc`) `[synthesis]`.

These two fields ride ONLY on `status="error"` rows. Every row (both `status="ok"` and `status="error"`) carries six provenance fields added by item 175 ([`analyzer.py:_provenance_fields`](../../../analyzer.py)) `[synthesis]`:

- **`answered_model`** — the `model` the API response reports. `model` keeps meaning "the id requested" (pricing and the dashboard key on it). On the two live calls observed (2026-10-19), the response echoed the requested alias, so this field does not name a dated version behind an alias; the request id below is the per-call handle `[synthesis]`.
- **`api_request_id`** — the SDK stream's request id for that call, read as soon as the stream opens so a call that fails mid-stream still logs it.
- **`request_settings`** — every request kwarg except prompt content (`system` / `messages`), taken from the kwargs actually sent.
- **`served_as`** — a fixed-shape dict of `service_tier`, `speed` and `inference_geo` (each `None` if the response's usage does not carry it), or `None` entirely when it carries none of the three.
- **`thinking_tokens`** — `usage.output_tokens_details.thinking_tokens` when the response carries it, else `None`; it was `None` on both live calls observed, neither of which thinks `[synthesis]`.
- **`attempt`** — `1` for a first pass, `2` for the `<kind>_retry` pass.

Additionally, **`pinned_model`** (model-override calls only) — when a call's `effective_model` differs from its `requested_model` (because `model_overrides()` replaced the pin with a candidate), this field records the pin that was replaced. On ordinary calls (no override active), the field is absent so the row remains byte-identical to pre-override rows ([`analyzer.py:_call_llm_streaming`](../../../analyzer.py)) `[synthesis]`.

Eval judges ([`evals/runner.py:_judge_create`](../../../evals/runner.py)) now also write telemetry rows via [`analyzer.py:log_judge_call`](../../../analyzer.py) under call kinds `judge_grade` and `judge_distinctiveness`, with the same row shape and provenance fields `[synthesis]`.

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
and the four Compose drafting calls `draft_positioning_summary` / `draft_gap_fill_bullets` /
`draft_experience_summaries` / `draft_surgical_refinement`) pay one cache-miss on the system
block; the cheap small calls
also pass `cached_user_prefix=""` because there is no long static block worth caching
([`analyzer.py:_call_llm`](../../../analyzer.py)) `[synthesis]`.
Only `analyze_synthesis` and `generate` ride the heavy corpus-prefix cache — see
[`architecture.md`](../../dev/architecture.md) §"LLM routing + cost" for the green/red
cache map. That diagram deliberately carries no per-call latency numbers as of
2026-07-28 — the prior figures were pre-Sonnet-5 synthetic measurements and were
removed rather than left to mislead; for current real-corpus latency/cost, see
[`docs/dev/perf/PERFORMANCE_HISTORY.md`](../../dev/perf/PERFORMANCE_HISTORY.md)'s
Era 4 baseline `[synthesis]`.

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
- [[keyless-client-refusal]] — what happens to any of these calls when no API key is configured.
