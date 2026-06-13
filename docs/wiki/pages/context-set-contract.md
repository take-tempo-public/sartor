# The context_set contract

> **Audience:** `dev`
> **Concept:** the `context_set` JSON artifact — the single contract every pipeline
> stage reads and writes; how it is built, what fields it carries, and the
> resolved-path containment guard that gates every route touching it.
> **Sources:** [`hardening.py`](../../../hardening.py) (`ContextSet`, `build_context_set`,
> `assemble_source_union`, `save_iteration_context`), [`app.py`](../../../app.py)
> (`_within`), [`db/build_context.py`](../../../db/build_context.py),
> [`docs/architecture.md`](../../architecture.md) §"context_set lifecycle",
> [`docs/diagrams/data-flow.mmd`](../../diagrams/data-flow.mmd).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What it is

`context_set` is a single JSON object — a `TypedDict` — that is the contract between
every pipeline stage. The wizard's analyze → clarify → recommend → compose → generate →
iterate flow never passes Python objects stage-to-stage; each route loads the JSON file
from disk, mutates it, and writes it back, so the file IS the inter-stage state
`[synthesis]`. The type is declared as
[`hardening.py:ContextSet`](../../../hardening.py), split into a required base
([`hardening.py:_ContextSetRequired`](../../../hardening.py)) and the optional fields
the routes layer on (`class ContextSet(_ContextSetRequired, total=False)`).

## The required core

[`hardening.py:_ContextSetRequired`](../../../hardening.py) names exactly six fields,
all present from the first build: `timestamp`, `candidate`
([`CandidateInfo`](../../../hardening.py): name/email/phone/linkedin_url/website_url/
skills/certifications/education_summary/notes/profile_text), `resume`
([`ResumeInfo`](../../../hardening.py): format/sections/text/filename/path),
`supplemental_resumes` (list of [`SupplementalResume`](../../../hardening.py)),
`job_description`, and `deterministic_analysis`
([`DeterministicAnalysisBlock`](../../../hardening.py): jd_keywords / resume_keywords /
keyword_overlap / ats_warnings). [`hardening.py:build_context_set`](../../../hardening.py)
is the deterministic builder — it assembles exactly these six from the parsed résumé,
config, profile text, and the keyword/ATS analysis. It contains no LLM call; the
analyze LLM output is attached afterward by the route, not by the builder `[synthesis]`.

## The optional fields routes layer on (`total=False`)

Everything past analyze is added on demand, so older context files round-trip unchanged
`[synthesis]`. The notable members of [`hardening.py:ContextSet`](../../../hardening.py):

- `llm_analysis`, `run_id` — written by `app.py` after `analyze()` returns.
- `clarification_questions` / `clarifications` — the surfaced questions and the user's
  free-form answers (treated as first-person ground truth by `generate()`).
- `iteration` (0 = analyze-only; N = state after the Nth generation) and
  `parent_context_path` — the back-pointer that forms the audit chain.
- `edited_resume_text` / `edited_cover_letter_text` — typed preview edits consumed by
  the next `generate()`, then cleared.
- `last_generated_resume` / `last_generated_cover_letter` / `last_generated_json_resume`
  — the frozen-at-generation snapshot the frontend diffs the live preview against; the
  cached `md_to_json_resume()` makes preview == download with no LLM call.
- `career_corpus` (list of [`CorpusExperience`](../../../hardening.py)),
  `application_id` / `application_run_id`, `composition_overrides`, and
  `llm_recommendations` — the corpus-mode / DB-backed members (B.2–B.3 + the Compose
  step). Absent on file-based contexts.

## Two builders, one shape

There are two producers. The file-based [`hardening.py:build_context_set`](../../../hardening.py)
(used by the legacy path and by [`evals/runner.py`](../../../evals/runner.py), which
calls it to construct fixtures so the eval set is the real artifact `[synthesis]`), and
the DB-backed [`db/build_context.py:build_context_set_from_db`](../../../db/build_context.py).
The latter is documented as producing a ContextSet whose SHAPE matches the file-based
output exactly — same TypedDict keys, equivalent semantics — so existing prompts work
unchanged; only the data sourcing differs (`resume.text` synthesized from DB bullets,
`resume.format` "md", `resume.path` "", `supplemental_resumes` always `[]`). It also
creates the `application` + `application_run` rows that anchor the audit chain — see
[[application-audit-chain]].

## The source union (grounding's ground truth)

[`hardening.py:assemble_source_union`](../../../hardening.py) derives, from the
context_set, the exact set of texts that count as legitimate source material: the
primary `resume.text`, every supplemental's `text`, and every clarification answer. It
is the single shared definition consumed by both the iteration clarifier
([`hardening.py:compute_iteration_signals`](../../../hardening.py)) and the eval-time
fabricated-specifics check, so the two can never score against divergent source sets
`[synthesis]`. The carve-out that widens the grounding check to accept clarifications is
canonical in AGENTS.md "LLM prompts" — cited, not restated here (D5). See
[[generation-and-grounding]].

## Persistence and the iteration chain

`save_context_set` writes iteration 0 (`context_<ts>.json`).
[`hardening.py:save_iteration_context`](../../../hardening.py) writes every subsequent
iteration as a NEW immutable child file (`context_<ts>_iter<N>.json`) rather than
mutating the parent: it deep-copies via a JSON round-trip, increments `iteration`, sets
`parent_context_path` to the parent, caches the frozen generation snapshot, clears the
consumed edit fields, and appends an [`IterationNote`](../../../hardening.py). The chain
of `parent_context_path` pointers IS the audit trail — see [[iteration-audit-chain]].

## The containment guard

Because the context path arrives from the client, every route that loads or writes one
first checks [`app.py:_within`](../../../app.py): it resolves the path and asserts it
sits under `OUTPUT_DIR` (`path.resolve().relative_to(parent.resolve())`), returning
`403` otherwise. This is the resolved-path half of the project's filesystem gate
(alongside `_safe_username` + `secure_filename`); the gate itself is canonical in
AGENTS.md "Key patterns" and enforced by the `route-security-lint` hook — cited, not
duplicated (D5). The guard recurs at dozens of context-loading routes in `app.py`
`[synthesis]`.

## Related

- [[code-module-map]] — where `hardening.py` and the builders sit in the module graph.
- [[iteration-audit-chain]] — how `parent_context_path` threads the iteration files.
- [[pipeline-stages]] — the analyze→generate→iterate stages that read/write this file.
- [[deterministic-llm-boundary]] — why `build_context_set` carries no LLM call.
- [[corpus-data-model]] — the DB rows the `_from_db` builder projects into this shape.
