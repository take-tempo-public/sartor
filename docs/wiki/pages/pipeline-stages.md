# Pipeline stages — one apply-run end to end

> **Audience:** `dev`
> **Concept:** the full apply-run sequence — analyze → clarify → compose → template → generate (+ optional cover letter) → iterate — and how each Flask route drives an LLM call (or none) that mutates the shared `context_set`.
> **Sources:** [`architecture.md`](../../architecture.md), [`blueprints/analysis.py`](../../../blueprints/analysis.py), [`blueprints/generation.py`](../../../blueprints/generation.py), [`blueprints/applications.py`](../../../blueprints/applications.py), [`analyzer.py`](../../../analyzer.py), [`hardening.py`](../../../hardening.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The pipeline is **two-or-more LLM calls in sequence, each gated by a human review or curation step** ([`architecture.md` §System overview](../../architecture.md)). The frontend ([`static/app.js`](../../../static/app.js)) drives the steps in order; every step is a Flask route that loads a saved `context_set`, optionally calls an analyzer function, and writes the mutated context back to disk. As of the app.py→blueprints decomposition (Sprint 8.3), `app.py` carries **zero** route handlers — it is only the `create_app` factory + WSGI/console entry point; the analyze/clarify family lives on `blueprints/analysis.py`, generate/save-edits/cover-letter on `blueprints/generation.py`, and Compose/recommend on `blueprints/applications.py` `[synthesis]`. The `context_set` JSON file is the contract that carries state between steps — see [[context-set-contract]]. The full sequence (with model + latency per call) is the pipeline sequence diagram in [`architecture.md` §System overview](../../architecture.md).

## Step 1 — Analyze (two-pass, writes iter-0 context)

[`blueprints/analysis.py:run_analysis`](../../../blueprints/analysis.py) (`POST /api/analyze`) validates `username` + `job_description`, then delegates to [`blueprints/analysis.py:_run_analysis_corpus_backed`](../../../blueprints/analysis.py) — the docstring notes the file-based legacy analyze path is gone; every call reads the DB corpus. That helper builds the context from the DB corpus (`build_context_set_from_db`), inserts the `Application` + `ApplicationRun` (iter 0) rows that anchor the audit chain `[synthesis]`, mints a 12-char `run_id`, and calls [`analyzer.py:analyze`](../../../analyzer.py). `analyze` is two-pass: a Haiku extraction phase feeds a Sonnet synthesis phase (see [[llm-call-catalog]] for the call taxonomy). The result is stored on `application_run.analysis_json`, merged into `context_set["llm_analysis"]`, stamped with `run_id` / `application_id` / `application_run_id`, and saved via [`hardening.py:save_context_set`](../../../hardening.py) — the iter-0 `context_*.json`. The response carries `context_path`, which the frontend threads into every later call `[synthesis]`. An SSE twin, [`blueprints/analysis.py:run_analysis_stream`](../../../blueprints/analysis.py) (`POST /api/analyze/stream`), streams the same result via `analyzer.py:analyze_streaming`.

## Step 2 — Clarify (optional, in-place)

[`blueprints/analysis.py:run_clarify`](../../../blueprints/analysis.py) (`POST /api/clarify`) loads the context, requires `llm_analysis` to be present, reuses the context's `run_id` (so all calls share a key in `logs/llm_calls.jsonl`), and calls [`analyzer.py:clarify`](../../../analyzer.py) for 3–5 targeted questions. The questions are persisted **back to the same context file** (no new iteration). Skipping clarify is supported — generate works on contexts that never went through it. Answers arrive via [`blueprints/analysis.py:submit_clarifications`](../../../blueprints/analysis.py) (`POST /api/answer-clarifications`), which filters answers to known question ids, merges them by id into `context_set["clarifications"]` (`merge=false` clears instead), and mirrors answered pairs into the candidate-memory table best-effort via [`blueprints/analysis.py:_persist_clarifications_to_memory`](../../../blueprints/analysis.py). These answers become first-person ground truth at generate time `[synthesis]`.

## Step 3 — Compose (recommend + curate, application-scoped)

Compose runs against the `Application` row, not the context file. [`blueprints/applications.py`](../../../blueprints/applications.py) exposes `POST /api/applications/<id>/recommend` (`recommend_application_bullets`) and `POST /api/applications/<id>/recommend-summary` (`recommend_application_summary`) — Haiku selection calls — plus `GET`/`POST /api/applications/<id>/composition` (`get_application_composition` / `save_application_composition`, curation, no LLM by default). The user pins/excludes/reorders bullets and picks a summary variant; choices are saved as `composition_overrides` `[synthesis]`. Post-2026-07-02, Compose also authors content directly — a drafted positioning summary and gap-fill bullets via Sonnet (`draft_application_summary`, `draft_application_gap_fill`, both in `blueprints/applications.py`) — and the explicit **"Save and continue"** action (`save_application_composition` with `freeze=true`) resolves everything into a frozen `context_set["approved_composition"]` snapshot via `corpus_to_json_resume.freeze_approved_composition` `[synthesis]`. How those overrides — and the freeze — reach the document is [[corpus-to-output-reach]].

## Step 4 — Template (live preview, no LLM)

The persona/template preview is a deterministic render — no LLM call. The pin choices and persona feed the live preview iframe ([`architecture.md` §System overview](../../architecture.md), pipeline diagram Step 4); document rendering itself is [[document-rendering]].

## Step 5 — Generate (writes a NEW iteration context)

[`blueprints/generation.py:run_generation`](../../../blueprints/generation.py) (`POST /api/generate`) loads the context, requires `llm_analysis`, then branches on whether Compose has frozen an `approved_composition` (Generation-experience re-architecture Phase 4):

- **Frozen composition present** (corpus mode, post-freeze): [`blueprints/generation.py:_frozen_composition`](../../../blueprints/generation.py) returns the frozen doc, and [`blueprints/generation.py:_assemble_from_frozen_composition`](../../../blueprints/generation.py) builds the `generate()`-shaped result **with zero résumé-body LLM calls** — `resume_content` is a deterministic `json_resume_to_markdown` view of the frozen doc, and `selected_bullets` (for the DB audit chain) are synthesized from the doc's `meta.sartor.work_provenance`. The cover letter, when opted in, is still a real LLM call (`generate_cover_letter_against_resume`). The résumé file itself is rendered directly from the JSON-Resume doc via `generator.py:generate_resume_from_json_resume` — no markdown round-trip, so download == preview == `approved_composition` by construction `[synthesis]`.
- **No frozen composition** (legacy file-based contexts, or corpus contexts predating the freeze — byte-identical to the pre-Phase-4 behavior): the curated choices are applied in-memory first — [`blueprints/generation.py:_apply_chosen_summary`](../../../blueprints/generation.py), `_apply_chosen_experience_summaries`, and `_apply_recommended_skills` — then [`analyzer.py:generate`](../../../analyzer.py) runs (`with_cover_letter` opt-in), and the markdown result renders through `generator.py:generate_resume` (template-path resolved by persona).

Either branch reuses `run_id`; when the context carries an `application_run_id`, the structured output is persisted to the DB audit chain via [`blueprints/generation.py:_persist_corpus_generation_to_db`](../../../blueprints/generation.py) — a no-op for file-only contexts.

Crucially, generate does **not** mutate its input context, in either branch. It calls [`hardening.py:save_iteration_context`](../../../hardening.py), which deep-copies the parent, increments `iteration`, sets `parent_context_path` to the input path, snapshots `last_generated_resume` / `last_generated_cover_letter`, and writes `context_*_iter{N}.json`. The returned `context_path` is the **new** file — the frontend must use it for any subsequent call so the iteration chain stays intact `[synthesis]`. That `parent_context_path` chain is the [[iteration-audit-chain]]. The no-invention grounding check enforced inside the non-frozen branch's `generate()` is [[generation-and-grounding]]; the frozen branch has no résumé-body LLM output to ground-check by construction `[synthesis]`. An SSE twin, [`blueprints/generation.py:run_generation_stream`](../../../blueprints/generation.py) (`POST /api/generate/stream`), mirrors this.

## Step 6 — Iterate (optional, repeatable)

[`blueprints/analysis.py:run_iterate_clarify`](../../../blueprints/analysis.py) (`POST /api/iterate-clarify`) is meaningful only after a draft exists — it requires `iteration >= 1` and returns 400 otherwise. It resolves the current draft (edited > last_generated), computes deterministic iteration signals + an edit-diff summary, pairs prior clarifications, and calls [`analyzer.py:clarify_iteration`](../../../analyzer.py) for follow-up questions tied to the draft's specific weaknesses. New questions are re-keyed (`iter{N}_q{i}`) to avoid id collisions and **appended** (not replaced) to `clarification_questions` on the same file, so every interview round is preserved. Answers go back through the same `/api/answer-clarifications` route; the next `POST /api/generate` consumes them and writes the next child context, advancing the chain `[synthesis]`.

## Optional — Cover letter

[`blueprints/generation.py:run_generate_cover_letter`](../../../blueprints/generation.py) (`POST /api/generate-cover-letter`) generates a cover letter against the **finalized résumé** (edited > last_generated > original), cheaper than re-running full generate. It calls [`analyzer.py:generate_cover_letter_against_resume`](../../../analyzer.py), writes the file, and updates `last_generated_cover_letter` on the existing context **in place** — no iteration bump — so subsequent résumé refinements preserve the letter and iterate-clarify can probe it `[synthesis]`. This route is identical in both the frozen and non-frozen generate branches — the cover letter is always an LLM call against whatever résumé text is finalized `[synthesis]`.

## State-mutation summary

Each step either writes back to the same context file (clarify, answer-clarifications, iterate-clarify, cover-letter, Compose's `save_application_composition`) or forks a new immutable child (generate, via `save_iteration_context`, in both the frozen and non-frozen branches); analyze writes the iter-0 root `[synthesis]`. Every Flask route here passes `username`/`context_path` through the security gate before any filesystem write — that gate, the deterministic/LLM boundary the rendering steps obey, and `PROMPT_VERSION` discipline are canonical in [`AGENTS.md`](../../../AGENTS.md), not restated here (design fork D5). The complete route inventory is [[route-surface]]; the analyzer functions each step calls are catalogued in [[llm-call-catalog]].

## Related

- [[code-module-map]] — where `app.py`, `analyzer.py`, `hardening.py` sit in the module graph.
- [[llm-call-catalog]] — the analyzer functions each step fires, by model.
- [[context-set-contract]] — the JSON state object every step reads and mutates.
- [[route-surface]] — the full Flask route inventory these steps are a slice of.
- [[frontend-wizard]] — the `static/app.js` driver that calls the routes in order.
- [[generation-and-grounding]] — the no-invention check inside Step 5.
