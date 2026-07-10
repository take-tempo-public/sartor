# The deterministic / LLM boundary

> **Audience:** `dev`
> **Concept:** the P1 Hardening boundary — every LLM call funnels through one
> module (`analyzer.py`); every other core module is deterministic by contract,
> so the fuzzy and the verifiable parts of the pipeline never blur.
> **Sources:** [`analyzer.py`](../../../analyzer.py),
> [`hardening.py`](../../../hardening.py), [`parser.py`](../../../parser.py),
> [`generator.py`](../../../generator.py), [`scraper.py`](../../../scraper.py),
> [`json_resume.py`](../../../json_resume.py),
> [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py),
> [`pdf_render.py`](../../../pdf_render.py),
> [`docx_to_persona_html.py`](../../../docx_to_persona_html.py),
> [`AGENTS.md`](../../../AGENTS.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The rule (canonical elsewhere)

The boundary itself is a binding project rule, stated once in
[`AGENTS.md`](../../../AGENTS.md) ("Architecture at a glance" + "What NOT to do")
and is **not** restated here (design fork D5). This page documents *how the code
embodies it* so a reader can verify the rule holds at HEAD. On any conflict,
AGENTS.md wins and this page is the thing that is wrong.

The shape: **all** LLM calls live in `analyzer.py`; `hardening.py`, `parser.py`,
`generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`,
`pdf_render.py`, and `docx_to_persona_html.py` are deterministic and **must
not** call an LLM. AGENTS.md frames this as the **P1 Hardening** boundary (the
10 Principles annotations are load-bearing, per
[`AGENTS.md`](../../../AGENTS.md)) and now enumerates all eight modules by
name (`AGENTS.md` "Architecture at a glance") — this page's module list
previously stopped at seven; `docx_to_persona_html.py` (the persona-upload
HTML/CSS preview companion generator, added since) closes that gap `[synthesis]`.

## The main funnel: `_call_llm_streaming`

Almost every model call passes through a single funnel. The streaming Anthropic
request is opened in [`analyzer.py:_call_llm_streaming`](../../../analyzer.py) via
`client.messages.stream(...)`. The non-streaming
[`analyzer.py:_call_llm`](../../../analyzer.py) is a thin wrapper that drains the
generator and returns the accumulated text, and
[`analyzer.py:_parse_or_retry`](../../../analyzer.py) (plus its streaming twin)
sits on top of `_call_llm`, adding JSON-parse + Pydantic-validate + one retry.
So the call graph is a funnel: the public verbs (analyze, generate, clarify,
recommend, …) reach the network through this one helper `[synthesis]`.

**The one exception** is the fail-open refinement-scope classifier
[`analyzer.py:check_refinement_scope`](../../../analyzer.py), which opens its own
`client.messages.create(...)` with a hardcoded
[`analyzer.py:SCOPE_CHECK_MODEL`](../../../analyzer.py) and deliberately bypasses
the funnel — so it gets no telemetry, no prompt caching, and no parse/retry. It
still lives **inside** `analyzer.py`, so the P1 boundary (no LLM call outside
`analyzer.py`) holds; what it skips is the funnel's conveniences, not the boundary
`[synthesis]`.

Funnelling through one door is what makes the boundary *enforceable* rather than
aspirational: caching, telemetry, model selection, and retry are defined once and
cannot be forgotten by any call site that routes through it (the standalone scope
check is the lone by-design exception) `[synthesis]`. The single
`_emit_call_log` block in the `finally` of
[`analyzer.py:_call_llm_streaming`](../../../analyzer.py) writes one JSONL
telemetry record per funnelled call (stamped with the call kind under the JSON key
`call`, plus `model` and `prompt_version`), so observability is a property of the
funnel, not of each caller.

## Two models, one funnel

Model selection is also centralized. The funnel resolves
`effective_model = model or SONNET_MODEL` —
[`analyzer.py:SONNET_MODEL`](../../../analyzer.py) (`"claude-sonnet-5"`) is the
default; a caller opts a cheap structured call into
[`analyzer.py:HAIKU_MODEL`](../../../analyzer.py)
(`"claude-haiku-4-5-20251001"`) by passing `model=HAIKU_MODEL`. Sonnet carries
the heavy reasoning calls; Haiku carries structured selection / extraction —
the per-call split is enumerated in [`AGENTS.md`](../../../AGENTS.md) and the
full catalog lives in [[llm-call-catalog]]. A legacy `MODEL = SONNET_MODEL`
alias remains for historical call sites
([`analyzer.py:MODEL`](../../../analyzer.py)) `[synthesis]`.

## The deterministic side, verified

Each non-`analyzer` core module is deterministic *by construction* — no
`anthropic` client, no `_call_llm`, no `import analyzer`. Their module
docstrings declare it, and the code matches:

- [`hardening.py`](../../../hardening.py) — "Deterministic analysis tools — P1
  Hardening." Keyword extraction, ATS checks, context assembly, and the
  post-generation metrics (verb diversity, specificity density, n-gram overlap,
  fabricated-specifics + date-grounding checks, cost — the full set is in
  [[generation-and-grounding]]). The only `anthropic` mention is a pricing-table
  *comment*, not a call.
- [`parser.py`](../../../parser.py) — "Deterministic resume parsing — P1
  Hardening." `.docx`/`.pdf`/`.md` → structured text.
- [`generator.py`](../../../generator.py) — "Document output generation — P1
  Hardening … Deterministic conversion of LLM-generated content into
  downloadable documents."
- [`scraper.py`](../../../scraper.py) — "URL content fetcher — P1 Hardening …
  Deterministic extraction of text from web pages."
- [`json_resume.py`](../../../json_resume.py) — lifts the LLM's markdown into a
  JSON Resume document "via deterministic parsing — no LLM call."
- [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py) — builds a JSON
  Resume document directly from corpus DB rows; reads the DB, emits structured
  JSON, no model.
- [`pdf_render.py`](../../../pdf_render.py) — Playwright/Chromium + Jinja2 HTML→PDF
  render; purely mechanical.
- [`docx_to_persona_html.py`](../../../docx_to_persona_html.py) — "Deterministic
  — no LLM (charter **C-6**)." Reads an uploaded persona `.docx` with
  `python-docx` and emits an HTML+CSS live-preview companion (margins, fonts,
  heading treatment) so uploaded templates preview faithfully instead of
  falling back to the default persona.

A live grep over these eight modules finds **zero** `anthropic` / `_call_llm` /
`client.messages` call sites — the single hit is the pricing comment in
`hardening.py` `[synthesis]`.

## Why the line is drawn here

The boundary separates the *unverifiable* (model output) from the *verifiable*
(everything that can be checked deterministically), so the fuzzy stage is
sandwiched between hardened input assembly and hardened output rendering
`[synthesis]`. The same modules that are kept LLM-free also host the
deterministic safety net that *checks* the LLM — `hardening.py`'s grounding /
overlap / specificity metrics — which only works because that checker can never
itself drift into generation `[synthesis]`. This is the structural reason the
no-invention grounding contract (see [[generation-and-grounding]]) is
enforceable: the judge lives on the deterministic side of the line.

## Related

- [[code-module-map]] — where each module sits; this page draws the LLM line through it.
- [[llm-call-catalog]] — the full inventory of call kinds routed through the funnel.
- [[context-set-contract]] — the JSON contract handed across the boundary at each stage.
- [[generation-and-grounding]] — the no-invention rule the deterministic checker enforces.
- [[prompt-version-discipline]] — `PROMPT_VERSION` stamped by the same funnel's telemetry.
- [[consistency-tracks-enforcement]] — LLM-call instrumentation as an enforced-consistency win.
- [[project-self-assessment]] — the boundary as a state-of-the-work strength.
