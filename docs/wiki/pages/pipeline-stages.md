# Pipeline stages — one apply-run end to end

> **Audience:** `dev`
> **Concept:** the full apply-run sequence — analyze → clarify → compose → template → generate (+ optional cover letter) → iterate — and how each Flask route drives an LLM call (or none) that mutates the shared `context_set`.
> **Sources:** [`pipeline.mmd`](../../diagrams/pipeline.mmd), [`architecture.md`](../../architecture.md), [`app.py`](../../../app.py), [`analyzer.py`](../../../analyzer.py), [`hardening.py`](../../../hardening.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The pipeline is **two-or-more LLM calls in sequence, each gated by a human review or curation step** ([`architecture.md` §System overview](../../architecture.md)). The frontend ([`static/app.js`](../../../static/app.js)) drives the steps in order; every step is a Flask route that loads a saved `context_set`, optionally calls an analyzer function, and writes the mutated context back to disk. The `context_set` JSON file is the contract that carries state between steps — see [[context-set-contract]]. The full sequence (with model + latency per call) is the [`pipeline.mmd`](../../diagrams/pipeline.mmd) diagram.

## Step 1 — Analyze (two-pass, writes iter-0 context)

[`app.py:run_analysis`](../../../app.py) (`POST /api/analyze`) validates `username` + `job_description`, then delegates to [`app.py:_run_analysis_corpus_backed`](../../../app.py). That helper builds the context from the DB corpus (`build_context_set_from_db`), inserts the `Application` + `ApplicationRun` (iter 0) rows that anchor the audit chain `[synthesis]`, mints a 12-char `run_id`, and calls [`analyzer.py:analyze`](../../../analyzer.py). `analyze` is two-pass: a Haiku extraction phase feeds a Sonnet synthesis phase (see [[llm-call-catalog]] for the call taxonomy). The result is stored on `application_run.analysis_json`, merged into `context_set["llm_analysis"]`, stamped with `run_id` / `application_id` / `application_run_id`, and saved via [`hardening.py:save_context_set`](../../../hardening.py) — the iter-0 `context_*.json`. The response carries `context_path`, which the frontend threads into every later call `[synthesis]`.

## Step 2 — Clarify (optional, in-place)

[`app.py:run_clarify`](../../../app.py) (`POST /api/clarify`) loads the context, requires `llm_analysis` to be present, reuses the context's `run_id` (so all calls share a key in `logs/llm_calls.jsonl`), and calls [`analyzer.py:clarify`](../../../analyzer.py) for 3–5 targeted questions. The questions are persisted **back to the same context file** (no new iteration). Skipping clarify is supported — generate works on contexts that never went through it. Answers arrive via [`app.py:submit_clarifications`](../../../app.py) (`POST /api/answer-clarifications`), which filters answers to known question ids, merges them by id into `context_set["clarifications"]` (`merge=false` clears instead), and mirrors answered pairs into the candidate-memory table best-effort via [`app.py:_persist_clarifications_to_memory`](../../../app.py). These answers become first-person ground truth at generate time `[synthesis]`.

## Step 3 — Compose (recommend + curate, application-scoped)

Compose runs against the `Application` row, not the context file. [`app.py`](../../../app.py) exposes `POST /api/applications/<id>/recommend` and `POST /api/applications/<id>/recommend-summary` (Haiku selection calls) plus `POST /api/applications/<id>/composition` (curation, no LLM). The user pins/excludes/reorders bullets and picks a summary variant; choices are saved as composition overrides `[synthesis]`. How those overrides reach the document is [[corpus-to-output-reach]].

## Step 4 — Template (live preview, no LLM)

The persona/template preview is a deterministic render — no LLM call. The pin choices and persona feed the live preview iframe ([`pipeline.mmd`](../../diagrams/pipeline.mmd) Step 4); document rendering itself is [[document-rendering]].

## Step 5 — Generate (writes a NEW iteration context)

[`app.py:run_generation`](../../../app.py) (`POST /api/generate`) loads the context, requires `llm_analysis`, and — before the LLM sees anything — applies the curated choices in-memory: [`app.py:_apply_chosen_summary`](../../../app.py), [`app.py:_apply_chosen_experience_summaries`](../../../app.py), and [`app.py:_apply_recommended_skills`](../../../app.py). It reuses `run_id`, calls [`analyzer.py:generate`](../../../analyzer.py) (`with_cover_letter` opt-in), then hands `result["resume_content"]` to the deterministic document layer (`generate_resume`, template path resolved by persona). When the context carries an `application_run_id`, the structured output is persisted to the DB audit chain (`_persist_corpus_generation_to_db`) — a no-op for file-only contexts.

Crucially, generate does **not** mutate its input context. It calls [`hardening.py:save_iteration_context`](../../../hardening.py), which deep-copies the parent, increments `iteration`, sets `parent_context_path` to the input path, snapshots `last_generated_resume` / `last_generated_cover_letter`, and writes `context_*_iter{N}.json`. The returned `context_path` is the **new** file — the frontend must use it for any subsequent call so the iteration chain stays intact `[synthesis]`. That `parent_context_path` chain is the [[iteration-audit-chain]]. The no-invention grounding check enforced inside generate is [[generation-and-grounding]].

## Step 6 — Iterate (optional, repeatable)

[`app.py:run_iterate_clarify`](../../../app.py) (`POST /api/iterate-clarify`) is meaningful only after a draft exists — it requires `iteration >= 1` and returns 400 otherwise. It resolves the current draft (edited > last_generated), computes deterministic iteration signals + an edit-diff summary, pairs prior clarifications, and calls [`analyzer.py:clarify_iteration`](../../../analyzer.py) for follow-up questions tied to the draft's specific weaknesses. New questions are re-keyed (`iter{N}_q{i}`) to avoid id collisions and **appended** (not replaced) to `clarification_questions` on the same file, so every interview round is preserved. Answers go back through the same `/api/answer-clarifications` route; the next `POST /api/generate` consumes them and writes the next child context, advancing the chain `[synthesis]`.

## Optional — Cover letter

[`app.py:run_generate_cover_letter`](../../../app.py) (`POST /api/generate-cover-letter`) generates a cover letter against the **finalized résumé** (edited > last_generated > original), cheaper than re-running full generate. It calls [`analyzer.py:generate_cover_letter_against_resume`](../../../analyzer.py), writes the file, and updates `last_generated_cover_letter` on the existing context **in place** — no iteration bump — so subsequent résumé refinements preserve the letter and iterate-clarify can probe it `[synthesis]`.

## State-mutation summary

Each step either writes back to the same context file (clarify, answer-clarifications, iterate-clarify, cover-letter) or forks a new immutable child (generate, via `save_iteration_context`); analyze writes the iter-0 root `[synthesis]`. Every Flask route here passes `username`/`context_path` through the security gate before any filesystem write — that gate, the deterministic/LLM boundary the rendering steps obey, and `PROMPT_VERSION` discipline are canonical in [`AGENTS.md`](../../../AGENTS.md), not restated here (design fork D5). The complete route inventory is [[route-surface]]; the analyzer functions each step calls are catalogued in [[llm-call-catalog]].

## Related

- [[code-module-map]] — where `app.py`, `analyzer.py`, `hardening.py` sit in the module graph.
- [[llm-call-catalog]] — the analyzer functions each step fires, by model.
- [[context-set-contract]] — the JSON state object every step reads and mutates.
- [[route-surface]] — the full Flask route inventory these steps are a slice of.
- [[frontend-wizard]] — the `static/app.js` driver that calls the routes in order.
- [[generation-and-grounding]] — the no-invention check inside Step 5.
