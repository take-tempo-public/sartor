# Iteration audit chain

> **Audience:** `dev`
> **Concept:** every `/api/generate` writes a NEW timestamped child context file; the `parent_context_path` pointer back to the file it was derived from forms an immutable audit trail. The parent is never mutated; `iteration`, `edited_*`, and `last_generated_*` fields carry the loop's state forward.
> **Sources:** [`hardening.py`](../../../hardening.py), [`app.py`](../../../app.py), [`docs/architecture.md`](../../architecture.md) §context_set lifecycle, [`docs/diagrams/data-flow.mmd`](../../diagrams/data-flow.mmd).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The invariant

A generation is recorded, not overwritten. [`hardening.py:save_iteration_context`](../../../hardening.py) deep-copies the parent context (a JSON round-trip, to avoid aliasing the live dict the caller may still read), then writes the copy to a brand-new file — `context_{ts}_iter{N}.json` — leaving the parent file on disk untouched. The chain of `parent_context_path` back-pointers across those files **is** the audit trail; nothing in the loop edits a prior generation's file `[synthesis]`. The architecture doc states the same as a "Key invariant": *"One file per iteration… the parent is never mutated"* ([`docs/architecture.md`](../../architecture.md)).

## What `save_iteration_context` writes into the child

In a single deterministic pass ([`hardening.py:save_iteration_context`](../../../hardening.py)) — no LLM call (P1 hardening boundary, see [`AGENTS.md`](../../../AGENTS.md)):

- **`iteration`** ← `parent.get("iteration", 0) + 1`. The parent default `0` (analyze-only) becomes child `1`; each generate bumps it by one. The [`ContextSet`](../../../hardening.py) TypedDict documents `0 = analyze-only; 1+ = state AFTER the Nth generation`.
- **`parent_context_path`** ← the parent file's path passed in by the caller. This is the single link that makes the chain walkable.
- **`last_generated_resume` / `last_generated_cover_letter`** ← the exact text the LLM just produced. The [`ContextSet`](../../../hardening.py) header calls these the *"frozen-at-generation snapshot"* the frontend diffs the live preview against to detect user edits.
- **`last_generated_json_resume`** ← `md_to_json_resume(last_generated_resume)` — the deterministic JSON-Resume of the markdown just written, cached so the preview route serves *exactly* the future download (WYSIWYG Option 1). Derived from the markdown above, so the two cannot drift; still no LLM ([`hardening.py:save_iteration_context`](../../../hardening.py)).
- **`edited_resume_text` / `edited_cover_letter_text`** are **popped**. They fed the prompt that produced this generation; carrying them forward would double-apply on the next round ([`hardening.py:save_iteration_context`](../../../hardening.py)).
- **`iteration_notes`** gets one appended `IterationNote` (`timestamp`, `action`, `summary`) — append-only, so a dashboard can reconstruct the path ([`hardening.py:save_iteration_context`](../../../hardening.py); [`ContextSet`](../../../hardening.py) marks the list *"Append-only; never rewritten"*).

The output filename keeps the iteration count visible at the filesystem level (`context_{ts}_iter{N}.json`); pre-iteration files (`context_{ts}.json`, no suffix) stay on disk ([`hardening.py:save_iteration_context`](../../../hardening.py)) `[synthesis]`.

## Who calls it, and what the route returns

[`app.py:run_generation`](../../../app.py) (the `/api/generate` handler) and its SSE twin [`app.py:run_generation_stream`](../../../app.py) both invoke `save_iteration_context` with `parent_path=str(cp)` (the input context), `action="generate"`, and a `summary` it composes from whether refinement notes or an edited baseline were present. The route then returns the **new** child path as `context_path`, plus `iteration` and `parent_context_path`, in its JSON (and the stream's `done` event) ([`app.py:run_generation`](../../../app.py)). The handler docstring is explicit that *"the frontend must use \[the new context_path] for any subsequent calls… so the iteration chain is preserved"* ([`app.py:run_generation`](../../../app.py)).

## Edits vs. generations — two different write modes

Not every write advances the chain. `/api/save-edits` ([`app.py`](../../../app.py)) merges the user's typed `edited_resume_text` / `edited_cover_letter_text` into the **current** context and rewrites that **same** file in place (`cp.write_text`), appending a `save_edits` `IterationNote` but **not** incrementing `iteration` `[synthesis]`. So:

- **save-edits** = in-place mutation of the *working* (latest) file, staging a baseline for the next generate.
- **generate** = a new child file, parent left frozen.

These do not conflict: the file mutated in place is the leaf of the chain, never an ancestor a later generation derives from — once a file becomes a `parent_context_path` target, the only thing that reads it is `save_iteration_context`'s deep copy `[synthesis]`.

## Why `iteration ≥ 1` matters downstream

The counter is not just bookkeeping. The [`ContextSet`](../../../hardening.py) comment notes that `context_set.get("iteration", 0) >= 1` is the condition that flips the next generate into iteration mode — the original primary + supplementals become historical references and the current draft becomes the `<resume>` block. (How the prompt assembles that block is the generation page's concern, not this one — see D5, [`SCHEMA.md`](../SCHEMA.md).) The data-flow diagram embeds this as the `LLM6 generate iter ≥ 1 … historical_resumes block` branch ([`docs/architecture.md`](../../architecture.md)).

## How the chain is consumed

Because each file carries `parent_context_path`, a reader can walk leaf→root to reconstruct the whole session: every generation, the edits that fed it (via the consumed-then-cleared `edited_*` fields recorded in `iteration_notes`), and the verbatim output snapshot (`last_generated_*`). The architecture doc's same-named **self-referential `parent_run_id`** on the `ApplicationRun` table is the database mirror of this file-level chain ([`docs/architecture.md`](../../architecture.md)) — the persistent audit trail for the corpus path, where this file chain is the per-session one `[synthesis]`. The containment guard (`_within(path, OUTPUT_DIR)`) on every context read/write is canonical in [`AGENTS.md`](../../../AGENTS.md); cited, not restated here (D5).

## Related

- [[context-set-contract]] — the JSON contract this chain is made of, field by field.
- [[application-audit-chain]] — the DB-side `parent_run_id` mirror of this file chain.
- [[pipeline-stages]] — where `/api/generate` sits in the analyze → generate → iterate flow.
- [[code-module-map]] — `hardening.py` (deterministic lifecycle) vs. `app.py` (routes).
