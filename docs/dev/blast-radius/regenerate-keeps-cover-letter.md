# Blast radius — regenerate-keeps-cover-letter

> **Branch:** `fix/regenerate-keeps-cover-letter`
> **Status:** enumeration complete, written before the first production edit (charter C-10);
> the fix landed against it, and the Deferred section was corrected after the final design.
> `hardening.py` is *watched, not gated* in `scripts/enforcement/blast_radius.py`
> (`ACKNOWLEDGED_NOT_GATED`), so no hook fires; the helper is still the context_set write
> contract, so this dossier is the receipt. The owner's decisions are D1-D4 in
> [`../diagnosis/regenerate-keeps-cover-letter.md`](../diagnosis/regenerate-keeps-cover-letter.md).

---

## Surface

1. **`hardening.py` `save_iteration_context`** — the context_set iteration write helper.
   Behavior changes (signature unchanged):
   - `last_generated_cover_letter` is replaced only when the generate produced a letter;
     otherwise the parent's letter rides along in the deep copy (D1);
   - `edited_cover_letter_text` is popped only by a generate that produced a letter (and
     not under `carry_edits`, as today); a résumé-only generate leaves it (D2, and D4's
     "even when résumé edits are discarded").
   - New pure function **`resolve_cover_letter_after_generate(parent, generated,
     carry_edits)`** returns `(letter, typed_edit)`: the one definition, applied by the
     helper and read by both routes so the response never disagrees with the file.
2. **`blueprints/generation.py`**
   - `_typed_edits_disposition`: decides carry/discard from the **résumé** edit only
     (D4: the letter edit is independent).
   - `_clear_run_edits`: nulls `edited_resume_text` only; leaves `edited_cover_letter_text`.
   - `/api/generate` JSON body and `/api/generate/stream` `done` payload:
     `cover_letter_preview` becomes the effective generated letter (was
     `result["cover_letter_content"]`); gains additive `edited_cover_letter_text`, mirroring
     `edited_resume_text`.
   - The two `summary_parts` "from edited baseline" tests: a letter edit counts only when
     this generate produced a letter.
3. **`static/app.js` `_renderOutput`** — the editor prefers the echoed typed letter edit,
   as it already does for the résumé.
4. **`templates/index.html` `#editsDiscardedNotice`** — copy says the *résumé* edits
   weren't carried over and that typed cover letter edits are kept (D4).

---

## Enumeration

Grep tool (ripgrep) over the whole tree, excluding `node_modules/`, `output/`, `.git/`,
2026-10-12. Code means outside `docs/`, `CHANGELOG*` and (where noted) `tests/`:

```
edited_cover_letter_text
  -> code: blueprints/templates.py:1220 (preview reader), blueprints/generation.py:737
     (save-edits writer), :871 (_typed_edits_disposition), :894 (_clear_run_edits, DB column),
     :1257 and :1569 (summary_parts), :1783 (cover-letter route pop), :113-143 (DB persist of
     an edit), analyzer.py:2379 (_current_cover_letter_draft), hardening.py:183 (TypedDict),
     :1959 (summarize_recent_edits), :2128/:2160 (helper), blueprints/applications.py:286/:445
     and db/models.py:831 (the ApplicationRun COLUMN: same name, separate store).
last_generated_cover_letter   (outside tests/)
  -> analyzer.py:2382, blueprints/templates.py:1221, blueprints/generation.py:1271/:1583
     (helper callers), :1780 (cover-letter route writer), hardening.py:190 (TypedDict),
     :1959, :2145 (helper), evals/runner.py:764 (sets the key directly).
lastGeneratedCoverLetter | cover_letter_preview   (outside tests/)
  -> blueprints/generation.py:1294, :1607 (payloads), :1806 (cover-letter route);
     static/app.js:38, :490, :1801, :1829, :1864, :1872, :1915, :2684, :3283, :6755.
save_iteration_context
  -> 31 occurrences / 6 .py files: blueprints/generation.py (5: import, 2 calls, 2
     comments), hardening.py (def), blueprints/applications.py:484 (docstring),
     tests/test_hardening_iteration.py (20), tests/test_cover_letter_detached.py (3, stubs
     the helper with **kwargs), tests/test_live_preview_route.py (1, docstring).
edits_discarded | editsDiscardedNotice | _typed_edits_disposition | _clear_run_edits
  -> blueprints/generation.py (10), static/app.js (2), templates/index.html (2),
     tests/test_composition_staleness.py (2), docs (wiki frontend-wizard, route-surface,
     iteration-audit-chain; earlier dossiers).
lastCoverLetterPath
  -> 7 hits, all assignments (static/app.js:27, 522, 1770, 1863, 2792, 6744, 6828); no reader.
```

**Negative results:** `evals/schemas/`, `web_infra/` (OpenAPI), `dashboard/` and `scripts/`
have 0 hits for `last_generated_cover_letter`, `edited_cover_letter_text` and
`cover_letter_preview`. No test asserts the `#editsDiscardedNotice` title text.

Docs naming the helper or the keys (84 occurrences / 21 files, excluding this branch's own
dossiers and handoffs): wiki `context-set-contract` (5), `iteration-audit-chain` (12),
`pipeline-stages` (3), `code-module-map` (1), `frontend-wizard`, `route-surface`;
`docs/dev/architecture.md` (8), `PRODUCT_SHAPE.md` (2), earlier diagnoses and dossiers.

---

## Consumers

The behavior, by path (parent has letter `L` and typed edit `E`; the generate produces no
letter unless stated). Today vs after:

| Path | `last_generated_cover_letter` | `edited_cover_letter_text` | Notice |
|---|---|---|---|
| LLM path, résumé-only | `""` → **`L`** | popped → **kept** | none |
| Frozen, same résumé (`carry`) | `""` → **`L`** | kept (unchanged) | none |
| Frozen, different résumé, résumé edit present (`discard`) | `""` → **`L`** | popped + DB nulled → **kept, DB kept** | shown (résumé wording) |
| Frozen, different résumé, only a letter edit present | `""` → **`L`** | popped + DB nulled + notice shown → **kept, DB kept, no notice** | none |
| Any path, generate produces a letter | replaced (unchanged) | popped, or kept under `carry` (unchanged) | unchanged |

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `hardening.py` `save_iteration_context` (`hardening.py:2145`, `:2159-2160`) | update | The fix (D1, D2). |
| 2 | `hardening.py` new `resolve_cover_letter_after_generate` | add | One definition shared by the helper and the routes; pure, no I/O. |
| 3 | `blueprints/generation.py:858` `_typed_edits_disposition` | update | D4. A letter edit alone must not raise `edits_discarded`. |
| 4 | `blueprints/generation.py:878` `_clear_run_edits` | update | D4. Context and DB must agree: the DB keeps the letter edit. |
| 5 | `blueprints/generation.py:1267` `/api/generate` helper call + body | update | Effective `cover_letter_preview`; `edited_cover_letter_text` echo. |
| 6 | `blueprints/generation.py:1579` `/api/generate/stream` helper call + `done` | update | Same as 5. |
| 7 | `blueprints/generation.py:1257`, `:1569` `summary_parts` | update | Otherwise the iteration note says "from edited baseline" on every résumé-only regenerate while a letter edit lingers. |
| 8 | `blueprints/generation.py:1783` cover-letter route pop | no change | A generate that produced a letter consumes the edit: the same rule. |
| 9 | `static/app.js:3283` `_renderOutput` | update | Editor prefers `edited_cover_letter_text`, as for the résumé (`:3281-3282`). |
| 10 | `static/app.js:1801` `_onGenerationComplete` | no change | `lastGeneratedCoverLetter` stays the generated letter, so edit-detect (`:1915`) sees a typed edit as an edit, as it does for the résumé. |
| 11 | `static/app.js:1829` `_updateCoverLetterButtons`, `:2684` `_discardEdits` | no change | Both follow `lastGeneratedCoverLetter`, which is now non-empty. |
| 12 | `templates/index.html:546-552` notice copy | update | D4: résumé-specific wording, plus that typed letter edits are kept. |
| 13 | `blueprints/templates.py:1220` cover-letter preview | no change | Reads `edited_cover_letter_text or last_generated_cover_letter`; correct once both are kept. |
| 14 | `analyzer.py:2364-2385` `_current_cover_letter_draft` | no change | Reads the same keys. The next with-letter generate now gets the draft (B6). |
| 15 | `hardening.py:1959` `summarize_recent_edits` | no change | Reads the same keys; I2 is inferred, not run. |
| 16 | `evals/runner.py:764` | no change | Sets the key directly, outside the helper. |
| 17 | `blueprints/applications.py:286`, `:445`, `db/models.py:831` | no change | The `ApplicationRun` column, a separate store; row 4 keeps it. |
| 18 | `tests/test_hardening_iteration.py` (20 refs) | update | Add: carry vs replace, letter edit kept vs consumed. Existing tests pass a non-empty letter, or a parent with none. |
| 19 | `tests/test_app_iteration.py:487` `test_generate_consumes_edits_from_context` | **update** | It pins today's contract (a résumé-only generate pops the letter edit). It asserts `"edited_cover_letter_text" not in child`; D2 reverses that. Changed with the reason stated. |
| 20 | `tests/test_cover_letter_detached.py` | no change | Stubs the helper with `*args, **kwargs`. |
| 21 | `tests/test_composition_staleness.py:263`, `:283` | no change | Assert `edits_discarded` for a résumé edit; unchanged by row 3. |
| 22 | `tests/test_regenerate_cover_letter.py`, `tests/ux/regression/test_20261012_*` | update | Delete only the `xfail` markers. |
| 23 | `docs/wiki/pages/context-set-contract.md`, `iteration-audit-chain.md`, `frontend-wizard.md`, `route-surface.md`, `pipeline-stages.md` | deferred to close-out | Scoped `/wiki-self-update` at the pre-close sweep. |
| 24 | `docs/dev/architecture.md`, `docs/dev/PRODUCT_SHAPE.md` | check at close-out | Update where they describe the letter being replaced on each generate. |

---

## Deferred

- **`carry_edits=True` with a letter produced keeps the typed edit (existing).** `carry` now
  needs a typed *résumé* edit (row 3), so this is the frozen, same-résumé, with-letter case
  where a résumé edit also exists: the helper pops nothing, so a typed letter edit shadows
  the new letter in the preview (edited beats generated). Not observed on this branch and
  not changed: the rule for that case is decision 4's, and the fix doesn't depend on it.
- **I2, the edit-detect diff** (`hardening.py:1959`): unobserved. The fix restores the value
  it reads.
- **The DB edit shadows a newly generated letter (observed, O10; pre-existing).** A
  with-letter generate consumes the typed edit in the context but not on the `ApplicationRun`
  row, and `resume_state` reads `edited_cover_letter_text or generated_cover_letter_md`
  (`blueprints/applications.py:445`), so resuming from Pipeline shows the typed text, not the
  new letter. Control C3 records it. Out of this item's scope (item 162 is the context file);
  filed at close-out as its own item.

---

## Verification

- A missed consumer of the changed keys surfaces in `tests/test_regenerate_cover_letter.py`
  (B1-B6 on both routes), `tests/ux/regression/test_20261012_*` (B7), and a new set of
  `save_iteration_context` unit tests covering the table above, one per row.
- Row 19 is the one existing test that must change; any other test failing is a consumer this
  enumeration missed, so it is investigated, not edited.
- The grep above is re-run at the pre-close sweep; a hit not in the table is a defect in this
  document.
