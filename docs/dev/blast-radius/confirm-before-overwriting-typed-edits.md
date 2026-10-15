# Blast radius — confirm-before-overwriting-typed-edits

> **Branch:** `feat/confirm-before-overwriting-typed-edits` (item 170)
> **Status:** enumeration complete, written before the first production edit (the dossier
> and the instrument are commit 1; the server handshake is commit 2; the client is commit 3).

---

## Surface

No gated surface (`scripts/enforcement/blast_radius.py`) is edited: `blueprints/generation.py`
and `static/app.js` are not in the registry, and `hardening.py` (the home of
`resolve_cover_letter_after_generate`) is **not** touched. The dossier is written anyway
because the change adds a request flag and a response shape to three routes that the client,
the eval harness, ~12 test files and several docs consume.

The change:

- **`blueprints/generation.py`**
  - a new request flag `confirm_discard_edits` on `/api/generate`, `/api/generate/stream` and
    `/api/generate-cover-letter`;
  - a new pre-LLM `409` body `{error, edits_would_be_discarded: true, discards: [...]}`, built
    by one helper next to `_stale_composition_response`;
  - one predicate, `_pending_discards`, built on the existing `_typed_edits_disposition` and
    on `resolve_cover_letter_after_generate`'s rule, so the pre-check and the post-hoc
    `edits_discarded` cannot disagree;
  - `_assemble_from_frozen_composition` gains one optional keyword so the frozen markdown is
    rendered once, not twice.
- **`static/app.js`**: `runGeneration` and `runGenerateCoverLetter` handle the new `409`
  with `cbConfirm` and re-send with the flag; `runGeneration` also calls
  `_gateEditsBeforeAction` first (case 4, unsaved editor text).

The behaviour change: a request that would lose a *saved* typed edit is refused before any LLM
spend unless it carries `confirm_discard_edits: true`.

---

## Enumeration

Run 2026-10-14 on `main` @ `13d8117`, whole tree, `git grep -c -F`, excluding `docs/**`,
`CHANGELOG.md` and `db/vector_index/**` (docs are counted separately below):

```
### edits_discarded
  blueprints/generation.py:9  static/app.js:1  tests/test_composition_staleness.py:2
  tests/test_regenerate_cover_letter.py:3  tests/test_run_row_letter_edit.py:2
### composition_stale
  blueprints/applications.py:4  blueprints/generation.py:1  hardening.py:1  static/app.js:7
  tests/test_composition_staleness.py:6  tests/test_regenerate_cover_letter.py:4
  tests/test_regenerate_persistence.py:5  tests/test_run_row_letter_edit.py:4
  tests/ux/regression/test_20261010_compose_edit_after_freeze.py:1
### _stale_composition_response       blueprints/generation.py:3
### _typed_edits_disposition          blueprints/generation.py:3
### _assemble_from_frozen_composition
  blueprints/generation.py:4  evals/runner.py:5  tests/test_deterministic_generate.py:3
  (evals/README.md:1, evals/TUNING_LOG.md:1 are prose)
### api/generate-cover-letter
  analyzer.py:3  blueprints/generation.py:6  db/persist_run.py:1  hardening.py:1
  static/app.js:3  tests/test_context_write_races.py:8  tests/test_cover_letter_detached.py:7
  tests/test_regenerate_cover_letter.py:3  tests/test_regenerate_persistence.py:1
  tests/test_run_row_letter_edit.py:2  (evals/TUNING_LOG.md:3, vision.md:1 are prose)
### api/generate/stream
  blueprints/generation.py:3  static/app.js:1  tests/test_composition_staleness.py:1
  tests/test_deterministic_generate.py:5  tests/test_frozen_composition_staleness.py:1
  tests/test_identity_override_route.py:2  tests/test_regenerate_cover_letter.py:1
  tests/test_regenerate_persistence.py:2  tests/test_run_row_letter_edit.py:1
### cbConfirm(
  static/app.js:13  templates/index.html:1
  tests/ux/regression/test_20260612_corpus_affordance_polish.py:1
  tests/ux/regression/test_20260707_ux_w4_aesthetic.py:2
### _gateEditsBeforeAction            static/app.js:3  templates/index.html:2
### confirm_discard_edits, edits_would_be_discarded    0 hits anywhere (new names)
```

Client senders of the three routes, by string form (`git grep -n -F api/generate -- '*.js'
'*.html' ':!tests' ':!docs'`; run **without** a leading `/`, which Git Bash rewrites to a
Windows path and matches nothing):

```
static/app.js:1708  '/api/generate/stream'      runGeneration
static/app.js:1847  '/api/generate-cover-letter' runGenerateCoverLetter
static/app.js:2773  '/api/generate'             submitRefinement (legacy mode only)
```

Harness drivers (no URL strings; they click the buttons): `ui_pages/selectors.py:266`
(`#btnGenerate`), `:416` (`#btnGenerateCover`), driven by `ui_pages/wizard_generate.py`,
`ui_pages/wizard_output.py` and `scripts/capture_screenshots.py`.

Docs naming the contract (`git grep -c -F` over `docs/wiki/pages docs/user
docs/dev/architecture.md`): `edits_discarded` in `frontend-wizard.md`,
`iteration-audit-chain.md`, `route-surface.md`; `composition_stale` in
`corpus-to-output-reach.md` (2), `frontend-wizard.md` (2), `route-surface.md` (2);
`editsDiscardedNotice` in `frontend-wizard.md`; `api/generate-cover-letter` in
`docs/dev/architecture.md` (3), `pipeline-stages.md`, `route-surface.md`; "Your edits aren't
saved yet" in `docs/user/iterating.md`.

Names searched: the request keys `generate_cover_letter`, `confirm_discard_edits`; the
response keys `edits_discarded`, `edits_would_be_discarded`, `composition_stale`,
`edited_cover_letter_text`, `edited_resume_text`; the helpers `_stale_composition_response`,
`_typed_edits_disposition`, `_assemble_from_frozen_composition`,
`resolve_cover_letter_after_generate`; the three route strings; the client's `cbConfirm` and
`_gateEditsBeforeAction`.

**Negative results:** 0 hits for the new names; `static/assistant.js` and
`static/help-modal.js` have no generate, `409` or `cbConfirm` references; `ui_pages/` and
`scripts/` hold no `/api/generate` URL string (they drive the DOM); the one other `409`
branch in `static/app.js` (`:10208`) is a preview GET probe, unrelated.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `blueprints/generation.py` `run_generation` (`/api/generate`) | **update** | Discard check after the month block, before any LLM work; accepts `confirm_discard_edits`. |
| 2 | `blueprints/generation.py` `run_generation_stream` (`/api/generate/stream`) | **update** | Same check as #1, as plain JSON before the stream opens (the stale-409 contract). The two routes duplicate this preamble; parity is tested. |
| 3 | `blueprints/generation.py` `run_generate_cover_letter` | **update** | `409` when a typed letter edit exists and the flag is absent; before the LLM call. |
| 4 | `blueprints/generation.py` `_assemble_from_frozen_composition` | **update (additive)** | One optional keyword so the caller's already-rendered markdown is reused. The default recomputes it, so `evals/runner.py:1002` and `tests/test_deterministic_generate.py` are unaffected. |
| 5 | `blueprints/generation.py` `_typed_edits_disposition`, `resolve_cover_letter_after_generate` (`hardening.py`) | no change | The rules the pre-check mirrors. Read, not edited. The pre-check calls the first and restates the second's one-line rule in a helper that a parity test pins. |
| 6 | `static/app.js:1707` `runGeneration` + `_consumeSSE` `http_error` | **update** | Handles `edits_would_be_discarded`: `cbConfirm`, then one re-run with the flag. Calls `_gateEditsBeforeAction` first (case 4). |
| 7 | `static/app.js:1847` `runGenerateCoverLetter` | **update** | Same `409` handling. Its generic `!res.ok` path would otherwise show the new `409` as an error modal. |
| 8 | `static/app.js:2773` `submitRefinement` (legacy mode) | no change | Reached only when `_composeApplicationId == null` (legacy, never frozen), after `_gateEditsBeforeAction` has already saved or discarded the editors, and it never sends `generate_cover_letter`. No predicate can fire there. If one ever did, the generic `reportError` shows the server's message: loud, not silent. |
| 9 | `static/app.js:3242` `submitIterateClarificationsAndGenerate` -> `runGeneration` | no change (inherits #6) | Calls `runGeneration()` on non-frozen contexts; picks up the case-4 gate. That adds a gate in front of a path that already ran `runIterateClarify`'s own gate; double-prompt is possible only when the user typed between the two. See Deferred. |
| 10 | `static/app.js:3277-3292` `_renderOutput`, `#editsDiscardedNotice` (`templates/index.html:543-556`) | no change | The after-the-fact notice stays as the record after a Continue. Its copy ("typed letter edits are kept") is checked against the new flow at close-out. |
| 11 | `static/app.js:6754` `_resumeIntoStep6` | no change | Builds a synthetic response; sends no request. |
| 12 | `static/app.js:2022` `cbConfirm` | no change | Reused as is: `danger: false`, `confirmLabel`, `triggerEl`. Esc and backdrop resolve false (= Cancel). |
| 13 | `templates/index.html` `#cbConfirmModal` (`:1059-1070`) | no change | Existing modal markup. |
| 14 | `evals/runner.py:1002` | no change | Calls the assembler directly with no typed-edit state; no HTTP, so no `409`. Pinned by Verification. |
| 15 | `ui_pages/wizard_generate.py:14-19`, `ui_pages/wizard_output.py:32-56`, `scripts/capture_screenshots.py:355-371` | no change | They click `#btnGenerate` / `#btnGenerateCover` on a fresh run with no typed edit; no dialog appears. A walkthrough that types an edit first would now meet the dialog. Re-checked at close-out. |
| 16 | `tests/test_composition_staleness.py:267-283`, `tests/test_regenerate_cover_letter.py` B8 and C3, `tests/test_run_row_letter_edit.py` C3 and A1/A2 | **update (drive)** | Each drives a with-discard generate and asserts `200`. They gain `confirm_discard_edits: True`: the user's Continue. Their assertions are unchanged. |
| 17 | `tests/test_run_row_letter_edit.py` A3 (detached letter over a typed edit) | **update (drive)** | Same: Continue flag on the second `/api/generate-cover-letter`. |
| 18 | `tests/test_run_row_letter_edit.py` A5, `tests/test_frozen_composition_staleness.py:837-866` (D6), `tests/test_regenerate_cover_letter.py` B5, `tests/test_app_iteration.py:460-495` | no change | Carry or résumé-only: nothing is discarded, so no `409`. They become **controls** that the pre-check does not over-fire. |
| 19 | `tests/test_cover_letter_detached.py`, `tests/test_context_write_races.py:177-242`, `tests/test_deterministic_generate.py`, `tests/test_identity_override_route.py`, `tests/test_regenerate_persistence.py`, `tests/test_app_iteration.py` | no change | Checked by grep on 2026-10-14, not assumed. `test_cover_letter_detached.py`, `test_deterministic_generate.py`, `test_identity_override_route.py` and `test_regenerate_persistence.py` contain no `save-edits` call and no `edited_*` key (0 hits), so no typed edit exists when they generate. `test_context_write_races.py` has 12 `save-edits` hits but no `edited_cover_letter` (0 hits) and posts only the detached route and iterate-clarify, never a generate route, so neither a letter edit nor a frozen discard exists there. `test_app_iteration.py` does stage edits (16 `save-edits` hits) but posts no `generate_cover_letter` flag and not the detached route; its one letter-edit-then-generate arm (`:460-495`) is résumé-only on the legacy path, where `_typed_edits_disposition` returns `(False, False)` because the typed résumé edit is consumed into the prompt, not discarded. No pre-check can fire. Re-run in Verification regardless. |
| 19a | `tests/test_analyzer_iteration.py`, `test_app_iterate_clarify.py`, `test_application_routes.py`, `test_corpus_mode_prompt.py`, `test_hardening_iteration.py`, `test_live_preview_route.py` | no change | They stage `edited_*` keys but post none of the three routes (0 hits for the route strings in each). |
| 20 | `tests/ux/regression/test_20261010_compose_edit_after_freeze.py:115-127` | no change | Records any request URL containing `/api/generate` and asserts none fired; the new `409` is a request too, and no edit is typed there. Re-run. |
| 21 | `tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py` | no change | Types no edit. The template for the new UX test. |
| 22 | `docs/wiki/pages/route-surface.md`, `frontend-wizard.md`, `iteration-audit-chain.md`, `corpus-to-output-reach.md`, `pipeline-stages.md`, `cover-letters.md`, `application-audit-chain.md`, `context-set-contract.md` | **check at close-out** | They describe the generate request/response and the edit lifecycle. A scoped wiki pass decides, per the close-out checklist. |
| 23 | `docs/user/iterating.md:107-112`, `docs/dev/architecture.md` (Step 5 sequence, `api/generate-cover-letter` x3) | **update** | User-facing description of the warning; architecture's route table gains the `409`. |
| 24 | `CHANGELOG.md` | **update** | New request flag and response key on three routes. |

---

## Deferred

- **Whether the frozen `carry_edits=True` path should keep a typed letter edit over a newly
  produced letter.** Item 163's O5. The pre-check treats `carry_edits` as "nothing lost", the
  behaviour as it stands, so it neither warns nor decides. Not changed here.
- **Cases 2 and 3 have no shipped client trigger.** The client never sends
  `generate_cover_letter`, and `#btnGenerateCover` is hidden once a letter exists
  (`_updateCoverLetterButtons`). Read from code, not driven. The server floor is built and
  tested at the route; case 3 also gets its client handler (row 7), but its UX path is
  unreachable today, so the UX tier covers cases 1 and 4 only. Recorded in item 170's
  `## Updates`.
- **Double prompt on iterate-clarify, legacy mode.** Row 9: the user is gated once by
  `runIterateClarify` and could be gated again in `runGeneration` if they type between. Rare;
  not engineered around. A user who just chose "use edits" has no unsaved editor text, so the
  second gate is silent.
- **The other un-handled pre-LLM refusals** (`needs_reanalyze`, `needs_resume`, the month
  `422`) still fall through to the generic error modal. Out of scope.
- **A route-level `409` for the legacy `submitRefinement` path.** Row 8: unreachable.

**One observation declared, not decided here:** only `/api/generate` runs
`strip_cover_letter_block` on the résumé before `_typed_edits_disposition`
(`blueprints/generation.py:1177`); the stream route's `done` branch compares the assembled
markdown as is. For a frozen doc the assembled markdown contains no salutation, so the two
agree in practice, but the pre-check must use the **same** comparand as each route's own
post-hoc check or it can disagree with `edits_discarded`. The parity test pins both routes.

---

## Verification

A missed consumer would surface as:

- `tests/test_confirm_overwrite_edits.py`: the arms drive the real routes (json and stream)
  and the detached route, assert the `409` body, zero LLM calls, and a byte-identical context
  file and run row after a refused request. Its controls pin the cases where the pre-check
  must **not** fire (carry, résumé-only, no typed edit, flag with nothing to discard);
- the existing suites in rows 16-20, re-run after commit 2, which fail loudly with a `409`
  where a drive was not updated;
- the grep above, re-derived at close-out and diffed against this table: a new hit is a site
  not yet decided.
