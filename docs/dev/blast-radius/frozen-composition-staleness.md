# Blast radius — frozen-composition-staleness

> **Branch:** `fix/frozen-composition-staleness`
> **Status:** enumeration complete, written before the first production edit (after commit
> `da967cf`, the instrument). Evidence: `docs/dev/diagnosis/frozen-composition-staleness.md`.

---

## Surface

The frozen-composition contract: the `approved_composition` snapshot in a context file, the
predicate that says a context is frozen, and everything that reads either.

1. **`hardening.py`**
   - New `COMPOSITION_INPUT_KEYS`, `composition_inputs_digest(ctx)`, `composition_is_stale(ctx)`.
     The last one builds on `frozen_composition_doc` and never re-derives it.
   - `ContextSet` gains `compose_corpus_edits: int` (a counter, bumped by Compose-originated corpus
     edits).
   - `save_iteration_context` gains `carry_edits: bool = False` (owner decision 4: keep typed edits
     when the regenerated résumé is unchanged). The default keeps today's behavior byte for byte.
2. **`corpus_to_json_resume.freeze_approved_composition`** — stamps
   `meta.sartor.inputs_digest`.
3. **`blueprints/applications.py`**
   - `POST /api/applications/<id>/composition` adds `stale` to its response.
   - `GET /api/applications/<id>/composition` adds `has_frozen_composition` + `composition_stale`.
   - `_pre_generate_hydration` adds `composition_stale` (reaches `resume_state`).
   - New `POST /api/applications/<id>/composition/touch`.
   - `/draft-refinement` hands the drafter Compose's live document when the snapshot is stale.
4. **`blueprints/generation.py`**
   - `/api/generate` + `/api/generate/stream` refuse a stale composition with a 409.
   - Frozen path carries or discards typed edits (decision 4), and clears
     `ApplicationRun.edited_resume_text` when it discards them.
5. **`static/app.js` + `templates/index.html`** — client state, rail gate, notices, copy, item 132's
   button, the Compose entry auto-fire guard (decision 5).
6. **`ui_pages/selectors.py`** (gated) — three additions: `Compose.STALE_NOTICE`,
   `Wizard.TEMPLATE_STALE_NOTICE`, `Wizard.SUBMIT_ITERATE_CLARIFICATIONS`.

---

## Enumeration

Run at `da967cf` from the repo root. Production = everything except `tests/`, `docs/` and `*.md`.

```
for term in approved_composition frozen_composition_doc _frozen_composition has_frozen_composition \
    _compositionFrozen freeze_approved_composition save_iteration_context edited_resume_text \
    inputs_digest compose_corpus_edits composition_stale _compositionStale \
    btnSubmitIterateClarifications submitIterateClarificationsAndGenerate; do
  git grep -n -F "$term" -- ':!tests' ':!docs' ':!*.md' | awk -F: '{print $1}' | sort | uniq -c
done
```

| Term | Production files (hits) | tests / docs files |
|---|---|---|
| `approved_composition` | analyzer.py 3, blueprints/applications.py 5, blueprints/generation.py 11, blueprints/templates.py 2, corpus_to_json_resume.py 2, evals/runner.py 7, generator.py 2, hardening.py 6, json_resume.py 2, static/app.js 4, ui_pages/selectors.py 1 | 13 / 31 |
| `frozen_composition_doc` | blueprints/applications.py 5, blueprints/generation.py 3, hardening.py 1, static/app.js 1 | 2 / 16 |
| `_frozen_composition` (substring; also matches `has_frozen_composition` and `_frozen_composition(`) | applications.py 3, generation.py 7, evals/runner.py 9, hardening.py 2, static/app.js 6, templates/index.html 1 | 7 / 32 |
| `has_frozen_composition` | applications.py 2, hardening.py 1, static/app.js 3 | 1 / 7 |
| `_compositionFrozen` | applications.py 2 (comments), static/app.js 11, templates/index.html 1 (comment) | 4 / 11 |
| `freeze_approved_composition` | applications.py 2, corpus_to_json_resume.py 1, evals/runner.py 7, hardening.py 1 | 3 / 11 |
| `save_iteration_context` | applications.py 1 (docstring), generation.py 5, hardening.py 1 | 3 / 13 |
| `edited_resume_text` | analyzer.py 2, applications.py 2, generation.py 9, templates.py 4, db/models.py 1, evals/runner.py 2, hardening.py 4 | 9 / 11 |
| `inputs_digest`, `compose_corpus_edits`, `_compositionStale` | **0** (new names) | 0 / 0 |
| `composition_stale` | **0** in production | 0 / 1 (the diagnosis doc's test-file name) |
| `btnSubmitIterateClarifications`, `submitIterateClarificationsAndGenerate` | static/app.js 1, templates/index.html 1 | 0 / 0 and 0 / 2 |

Further greps:
- `git grep -c "api/generate" -- 'static/*'` → `static/app.js:13`. The generate callers are
  `static/app.js:1703` (`runGeneration` → `/api/generate/stream`) and `:2762` (legacy Refine →
  `/api/generate`); the rest are comments and `/api/generate-cover-letter`. (A first
  `git grep -n "/api/generate" -- static templates ui_pages scripts` returned nothing; the negative
  was a pathspec artifact, re-checked with the quoted form above.)
- `meta.sartor` readers: `git grep -n -E "\[.sartor.\]|get\(.sartor.\)" -- '*.py' 'static/*.js' ':!tests'`
  → `analyzer.py:4853`, `blueprints/generation.py:896`, `json_resume.py:333`, `:945-948`. Each reads
  named keys. None iterates or serializes the whole block, so a new key is invisible to them.
- Whole-document equality on a frozen doc in tests: `git grep -n -E "approved_composition.{0,6}\] ?==|freeze_approved_composition\(" -- tests evals`
  → `tests/test_eval_runner.py:966` compares `json_resume_to_markdown(...)` output. Markdown drops
  `meta`, so a digest there is invisible.
- `git grep -n -F "composition/touch"` → 0 (the new route's path is unused).
- Schema: `evals/schemas/context_set.schema.json` — `additionalProperties: true` and no
  `approved_composition` model, so the new context key needs no schema edit.

---

## Consumers

| # | Site (`path:line` at `da967cf`) | Decision | Rationale |
|---|---|---|---|
| 1 | `hardening.py:1827` `frozen_composition_doc` | no change | Stays the single "is frozen" predicate; `composition_is_stale` calls it first. |
| 2 | `hardening.py:156-261` `ContextSet` | update | Adds `compose_corpus_edits: int` (`total=False`; absent = 0). |
| 3 | `hardening.py:2038` `save_iteration_context` | update | `carry_edits=False` default = unchanged; the deep copy at `:2074` carries `compose_corpus_edits` and the snapshot's digest forward, so an iteration child inherits the parent's freshness. |
| 4 | `hardening.py:1897` (`edited_resume_text` in a source-union tuple) | no change | Grounding source union; unaffected by whether edits survive a regenerate. |
| 5 | `corpus_to_json_resume.py:363` `freeze_approved_composition` | update | Stamps `meta.sartor.inputs_digest` from the `context_data` it was given (or the file it read). |
| 6 | `evals/runner.py:993` (freeze call) | no change | Gains the digest via site 5; nothing in the runner reads meta. |
| 7 | `evals/runner.py` `_frozen_composition` uses (9) | no change | Eval contexts are never edited after the freeze, so never stale. |
| 8 | `evals/runner.py:765` (`edited_resume_text`) | no change | Legacy iteration-eval path; does not take the frozen branch. |
| 9 | `blueprints/applications.py:368` `_pre_generate_hydration` | update | Adds `composition_stale`; `has_frozen_composition` keeps its meaning (the item-20 contract). |
| 10 | `blueprints/applications.py:1060` GET `/composition` | update | Adds `has_frozen_composition` + `composition_stale` from one context read (no extra parse beyond one). |
| 11 | `blueprints/applications.py:1844-1924` POST `/composition` | update | Adds `stale`, computed in-lock on the dict about to be written. `frozen` unchanged. |
| 12 | `blueprints/applications.py:3204` `/draft-refinement` | update | When stale, `ctx["approved_composition"]` is replaced in memory by Compose's live doc for this request only (route never writes ctx). |
| 13 | `blueprints/applications.py:285, 409` (`edited_resume_text` on runs) | no change | Readers of the DB column; correct once site 16 clears it on discard. |
| 14 | `blueprints/applications.py` new `POST /composition/touch` | new | `_load_application_owned` + `_safe_username` + `resolve_within`; bumps the counter in `context_transaction` only when the context is frozen. |
| 15 | `blueprints/generation.py:837-853` `_frozen_composition` | no change | Still the gate; the stale check sits right after it. |
| 16 | `blueprints/generation.py:973` + `:1281` (frozen gate, both routes) | update | Stale → 409 `composition_stale: true` before the month block, via one shared helper; never returns None to the legacy path. |
| 17 | `blueprints/generation.py:111-142` `_persist_edited_text_to_db` | update | Needs an explicit clear (`None` today means "no change"). |
| 18 | `blueprints/generation.py:1181, 1469` (audit summary on edits) | no change | Text-only audit string. |
| 19 | `blueprints/generation.py:1185, 1473` `save_iteration_context` calls | update | Pass `carry_edits` when the frozen body equals the parent's `last_generated_resume`; return the edited text / `edits_discarded`. |
| 20 | `blueprints/generation.py:733` `/api/save-edits` | no change | Writer of the edits; unchanged. |
| 21 | `blueprints/generation.py:1609` cover-letter route reads `edited_resume_text` | no change | Reads the current context; a carried edit is the right input. |
| 22 | `blueprints/templates.py:1086-1100` preview | no change | Owner-accepted design: the preview keeps serving the approved snapshot; a carried edit (site 19) makes the existing `edited` branch serve it. |
| 23 | `analyzer.py:4837-4877, 4943` `_current_composition_block` / drafter | no change | Reads `basics`, `work`, `work_provenance` only; site 12 swaps its input. No prompt text changes → no `PROMPT_VERSION` bump. |
| 24 | `analyzer.py:875-887` (`edited_resume_text` in the legacy generate prompt) | no change | Legacy path only. |
| 25 | `generator.py:195-203`, `json_resume.py:333, 708-721, 945-948` | no change | Consume the doc they are handed; read named meta keys only. |
| 26 | `db/models.py:830` `ApplicationRun.edited_resume_text` | no change | Column unchanged; site 17 writes it. |
| 27 | `static/app.js:7301` `_compositionFrozen` + its assignments `:524, :1098, :6650, :9657` | update | `_compositionStale` added beside it, reset at the same sites; one `_applyCompositionState` funnel. |
| 28 | `static/app.js:7120` `_wizardReachable` (rail gate) + lock reason | update | `step === 5 && (!_compositionFrozen \|\| _compositionStale)`; stale lock reason. |
| 29 | `static/app.js:1703` `runGeneration` | update | Handles a 409 `composition_stale` (message + way back to Compose). |
| 30 | `static/app.js:2762` legacy Refine `/api/generate` | no change | Already `reportError(...data.error)` on non-OK; the 409 message carries the instruction. Recorded, not rewritten. |
| 31 | `static/app.js` Compose corpus calls (`_editComposeBullet` `:9376`, bullet accept `:9337`, title add `:9168`, role intro `:8712`, skill approve/deny `:8390/:8393`) | update | Routed through one `_composeCorpusFetch` that calls touch first. Re-read at edit time. |
| 32 | `static/app.js` Compose entry auto-fires (`:7573-7594`, `:7633`, `:7643`, per the Plan agent) | update | Skipped when the composition is frozen (decision 5). Re-read at edit time. |
| 33 | `static/app.js:3064, 3143-3184` follow-up questions | update | Item 132 relabel and frozen branch. |
| 34 | `static/app.js:9363-9369` edit-bullet modal copy; `templates/index.html:318-321` Compose hint; `:991-995` edits modal; `:314` notice slot; `:692` submit button | update | Copy and notices. |
| 35 | `ui_pages/selectors.py:226` `Wizard`, `:526` `Compose` | update | Four new constants (`Wizard.TEMPLATE_STALE_NOTICE`, `Wizard.SUBMIT_ITERATE_CLARIFICATIONS`, `Compose.STALE_NOTICE`, `Compose.ANSWERS_BANNER`; the fourth added before its edit, for item 132's UX test); existing constants untouched, so its 14 importers are unaffected. |

**Tests that assert on these surfaces** (run after the change, decided per failure):
`tests/test_composition_summary.py`, `test_deterministic_generate.py`,
`test_live_preview_route.py`, `test_application_routes.py` (frozen-flag tests ~`:1556-1680`),
`test_hardening_iteration.py` (`:166-187`, edits consumed), `test_corpus_to_json_resume.py`
(named meta keys), `test_eval_runner.py:966` (markdown equality), `test_call_kind_route_telemetry.py:205`,
`test_draft_surgical_refinement.py`, `test_route_containment_gate.py` (new route),
`test_ux_stub_coverage.py`; UX `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py`,
`test_20260707_generate_surface_download.py`, `test_20260611_wizard_flow_polish.py`.

---

## Deferred

- **`GET /composition` parses the context file about ten times per request** (Plan agent read,
  `blueprints/applications.py:1088-1146`). Pre-existing; this branch adds at most one read and
  files the consolidation as a work item rather than widening scope.
- **A résumé-only regenerate may blank a separately generated cover letter**
  (`hardening.py:2078`). Not instrumented; carried forward, out of scope.
- **Legacy snapshots (frozen before this branch, no digest)** detect only Compose corpus edits
  until re-frozen. Declared in the diagnosis doc's fix section.
