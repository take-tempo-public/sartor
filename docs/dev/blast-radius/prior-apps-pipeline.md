# Blast radius — prior-apps-pipeline

> **Branch:** `feat/prior-apps-pipeline` (Epic A, sprint A4)
> **Status:** enumeration complete — written BEFORE the first edit to
> `ui_pages/selectors.py`, `static/app.js`'s `activate()`, or any other file
> named below. Branch base: `9f446e8` (A3's tip + the stop-4 record commit).

---

## Surface

**The ARC brief's framing ("remove a panel + rewrite one function + rewrite one
test") undercounts this by a wide margin.** The panel's markup and the pinned
test are real, but `ui_pages/prior_apps.py`'s `PriorAppsPage.open_detail()` —
the ONLY way most UX regression tests reach the shared application-detail
modal — navigates by clicking a card **inside the panel being removed**. That
is a hard break for every test that calls it, discovered only by grepping
`PriorApps` project-wide rather than trusting the brief's named scope. This is
exactly the "bigger than you thought" case C-10 exists to catch.

Five production surfaces change on this branch, plus test-only consumers:

1. **`templates/index.html`** — `#panelApplications` (`:172-208` at this
   branch's base — **the brief's own cite is exact, not drifted**, verified by
   direct read), the "Prior applications" section: filter row, `#applicationsList`,
   refresh button, show-retired checkbox. Removed whole.
2. **`static/app.js`** — the Applications-list render path (`refreshApplications`,
   `_renderApplicationsList`, `_renderApplicationCard`, `toggleApplicationsRetired`,
   `_setApplicationsCount`, `_applicationsShowRetired`) removed. The **shared**
   detail-modal path (`_showApplicationDetail`, `_renderAppDetailStatusActions`,
   `_renderAppDetailAdminRow`, `_setApplicationRetired`, `_putApplicationStatus`,
   `_formatRelativeDate`, `resumeApplicationIntoWizard`, `_resumeIntoStep6`,
   `_resumeIntoPreGenerateStep`) is **kept** — it is what "open in place" opens.
   `_renderPipelineRow`'s `activate()` (`:263-277` at base — **also exact, not
   drifted**, verified by direct read) rewritten to stay on the Pipeline tab.
   Three call sites inside kept code reference removed/changed state and are
   fixed as part of this same surface (see `## The consumer this enumeration
   almost missed` below): `onUserSelect()`'s `show('panelApplications')` /
   `_applyFoldableDefault('panelApplications', …)`, `hideAllPanels()`'s panel
   list, `_FOLDABLE_PANEL_IDS`, and `_saveMeta`'s `refreshApplications()` call
   inside the **kept** `_showApplicationDetail`.
3. **`static/style.css`** — the `.application-card*` / `.application-list` /
   `.applications-show-retired` rule family (Phase D.3 block, `:1754-1989`
   region at base) removed; the `.app-status-chip*` / `.outcome-*` /
   `.app-admin-btn` / `.application-admin-row` / `.app-detail-*` rules in the
   **same block** are kept — Pipeline's column headers and the shared modal
   both still use them.
4. **`ui_pages/selectors.py`** — GATED (`scripts/enforcement/blast_radius.py:141-146`:
   *"the one selector registry; 14 non-test importers, consumed by the whole
   `pytest -m ux` tier AND `scripts/capture_screenshots.py`"*). `PriorApps.PANEL`,
   `.LIST`, `.PENDING_PILL`, `.card()`, `.card_company()` removed (no DOM left to
   select); `.MODAL`, `.RESUME_BUTTON`, `.TITLE_INPUT`, `.COMPANY_INPUT` kept
   (the shared modal). `Help.TOUR_STOP_BLOCKS`'s comment (`:94`) updated — it
   names `panelApplications` as an example of an on-demand-only panel that is
   now gone entirely, not merely absent from the tour list.
5. **`ui_pages/prior_apps.py`** — `PriorAppsPage.open_detail()` rewritten (see
   `## The consumer this enumeration almost missed`).

Test/copy surfaces that change with them: six regression test files (enumerated
below), `CHANGELOG.md` (new entry), two backend docstrings in
`blueprints/applications.py` referencing "the Applications tab" by name.

---

## Enumeration

All commands run from the repo root against this branch's base (`9f446e8`),
whole tree, via the `Grep` tool (ripgrep, no path restriction unless noted).

```
rg -n "PriorApps"                    -> 18 files (class def + 1 selectors.py
                                         self-comment + 1 page-object module +
                                         13 test files + 3 docs)
rg -n "panelApplications"            -> selectors.py(2, one in a comment),
                                         templates/index.html(1), static/app.js(4),
                                         tests/ux/regression/
                                           test_20260614_education_help.py(1),
                                         docs/dev/reviews/2026-07-ux-review/
                                           40-friction-register.md(1)
rg -n "applicationsList|applicationsHeaderCount|applicationsStatusFilter|
       applicationsShowRetired|applicationsCount"
                                      -> static/app.js only (10 hits, all inside
                                         the functions being removed)
rg -n "_renderPipelineRow\b"          -> static/app.js:249 (call site, unchanged),
                                         static/app.js:254 (def, activate() edited)
rg -n "class PriorApps" -A 20 ui_pages/selectors.py
                                      -> PANEL, LIST, MODAL, RESUME_BUTTON,
                                         TITLE_INPUT, COMPANY_INPUT, PENDING_PILL,
                                         card(), card_company() — 9 members
rg -n "PriorApps\." tests/ -g "*.py"  -> 6 files, itemized in ## Consumers below
rg -n "PriorAppsPage" -g "*.py"       -> ui_pages/__init__.py (export),
                                         ui_pages/prior_apps.py (def),
                                         5 test files calling .resume_application()
                                         / .open_detail()
rg -n "application-card|application-list|applications-show-retired" static/style.css
                                      -> 16 rule blocks; cross-checked each
                                         against JS producers below (## Surface #3)
rg -n "\.app-status-chip|\.outcome-|\.app-admin-btn|\.application-admin-row|
       \.app-detail-" static/app.js
                                      -> confirms all 4 families are set by KEPT
                                         functions (_renderPipelineBoard,
                                         _renderAppDetailStatusActions,
                                         _renderAppDetailAdminRow,
                                         _showApplicationDetail) — none removed
rg -n "Prior applications|applications panel|Applications tab"
                                      -> 16 files; sorted into live-code (2, fixed),
                                         historical/dated (deferred), sketch-doc
                                         (no change) in ## Consumers section E
rg -n "PriorApps|panelApplications|applicationsList|application-card"
    scripts/capture_screenshots.py    -> 0 hits — negative result
rg -n "_needsOnboarding\(|_renderCorpusEmptyCTA\(|_setLoadingPlaceholder\("
    static/app.js                     -> 57 call sites across the whole file;
                                          confirms these are shared helpers, NOT
                                          deleted, only their 6 call sites INSIDE
                                          refreshApplications() go away
rg -n "_application_summary_dict\(" blueprints/applications.py
                                      -> 1 definition + 1 call site (the
                                         GET /api/users/<u>/applications route,
                                         kept — see Deferred)
```

**Negative results (findings, recorded deliberately):**

- **`scripts/capture_screenshots.py` has zero references** to any name on this
  surface — the brief explicitly asked this be checked; it consumes page
  objects (`PipelinePage`, not `PriorAppsPage` directly for navigation), so it
  inherits whatever `PriorAppsPage`/`Pipeline` do and needs no edit.
- **`.app-status-chip*`, `.outcome-*`, `.app-admin-btn`, `.application-admin-row`,
  `.app-detail-*` are NOT orphaned** — despite living in the same CSS block
  comment ("Phase D.3") as the classes being removed, each is set by a function
  that stays (`_renderPipelineBoard` for the chip family; `_showApplicationDetail`
  and its two sub-renderers for the rest). A block-level removal would have
  deleted live styling for the Pipeline board and the surviving modal — checked
  before cutting, not after.
- **No raw SQL / DB column** named after any removed JS/CSS symbol — this is a
  pure frontend + page-object surface change; `_application_summary_dict`
  (the one backend function whose docstring names the retired tab) is
  otherwise untouched — its route, fields, and callers are unaffected.
- **`ui_pages/pipeline.py` needed no new selector or method.** The chosen fix
  for `PriorAppsPage.open_detail()` (below) does not route through the
  Pipeline board's DOM at all, so `Pipeline.ROW`/`click_row()` are unaffected
  and no `Pipeline.row(app_id)`-style addition was needed — considered and
  rejected, see `## Deferred`.

---

## The consumer this enumeration almost missed

**`_saveMeta` inside the KEPT `_showApplicationDetail` calls `refreshApplications()`.**
Grepping symbol names that are being *deleted* (`refreshApplications`,
`_renderApplicationCard`, …) surfaces every definition and every direct call —
but `_saveMeta` is defined *inside* `_showApplicationDetail`'s closure and its
`refreshApplications()` call only shows up as "yet another call site of the
function being deleted," easy to file under "removed, done" without noticing
it sits inside code that is NOT being deleted. This is the same class of trap
A3's dossier flagged in its own "consumer this enumeration missed" section (a
local reference inside surviving code, invisible to a search scoped to the
symbol being touched rather than the code around it) — caught here by
re-reading the full 250-line span of `_showApplicationDetail` before editing,
specifically because that precedent said to. **Fix:** `_saveMeta`'s
`refreshApplications()` → `refreshPipeline()`, so a title/company edit made in
the modal still refreshes the one remaining list view behind it, matching the
existing "fire-and-forget, harmless if the tab isn't visible" pattern
`refreshApplications()` already had (`refreshPipeline()` early-returns if
`#pipelineBoard` — always present in the DOM — were ever absent; it is not).

**`PriorAppsPage.open_detail()` cannot navigate through the panel it used to
click into**, and rerouting it through a live Pipeline-row click was
considered and rejected (`## Deferred`) because `_renderPipelineRow`'s
`activate()` re-runs the FULL `onUserSelect()` cascade (`loadConfig`,
`_resetIterationState`, `wizardInit`, …) — several consuming tests
(`test_analyze_only_application_resumes_to_step_1`,
`resume_application()` callers) select a user and build up wizard state
*before* opening the modal, and replaying that cascade on top of an
already-selected same user risks resetting state those tests depend on. Since
`_showApplicationDetail(app_id)` is a plain global function — called
identically today whether a (removed) panel card or a (kept) Pipeline row
triggers it, and already invoked directly via `page.evaluate` for other
internals throughout this suite (`switchTopTab`, `_setBusy`,
`_maybeFireTourStop`, confirmed by grep — not a new pattern) —
`open_detail()` now calls it directly: `page.evaluate("(id) =>
_showApplicationDetail(id)", app_id)`. This is a **more correct** isolation
than before, not a workaround: callers that only need "this application's
modal is open" no longer implicitly depend on `currentUser` already matching
the application's owner, a coupling the old panel-click path had for free
(clicking a card in "my" list) and that the ONE test which actually exercises
the click-through UX (`test_20260707_recruiter_roster_pipeline.py`) still
covers end-to-end.

---

## Consumers

### A. `ui_pages/selectors.py` — the gated surface, `PriorApps` class

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `ui_pages/selectors.py:290` `PriorApps.PANEL` | **remove** | `#panelApplications` no longer exists in the DOM. Every consumer either removed or rewritten below. |
| 2 | `ui_pages/selectors.py:291` `PriorApps.LIST` | **remove** | `#applicationsList` no longer exists. **Zero test consumers found** (checked before cutting — negative result, not assumed). |
| 3 | `ui_pages/selectors.py:292` `PriorApps.MODAL` | **no change** | `#appDetailModal` is the shared, kept modal. |
| 4 | `ui_pages/selectors.py:293` `PriorApps.RESUME_BUTTON` | **no change** | Kept modal control. |
| 5 | `ui_pages/selectors.py:295-296` `TITLE_INPUT` / `COMPANY_INPUT` | **no change** | Kept modal controls. |
| 6 | `ui_pages/selectors.py:298` `PriorApps.PENDING_PILL` | **remove** | `.application-card-pending` lived on the removed card only; no Pipeline-row equivalent exists and the brief does not ask for one (scope discipline — see row 20). Underlying `pending_proposals` value stays covered at the route level (`tests/test_application_routes.py::test_pending_proposals_per_run`, `::TestListApplications` line ~257). |
| 7 | `ui_pages/selectors.py:300-303` `PriorApps.card()` | **remove** | `#app-card-{id}` no longer exists. |
| 8 | `ui_pages/selectors.py:305-308` `PriorApps.card_company()` | **remove** | Same; see row 20 for the test-side replacement. |
| 9 | `ui_pages/selectors.py:288` class docstring | **update** | "Selectors for the Prior Applications panel and detail modal" → describes the shared modal only, opened from Pipeline. |
| 10 | `ui_pages/selectors.py:94` `Help.TOUR_STOP_BLOCKS` comment | **update** | Currently lists `panelApplications` as an example of an on-demand-only panel absent from the auto-fire list. It is not merely absent from that list now — the panel itself is gone. Comment reworded; `TOUR_STOP_BLOCKS` tuple itself never named it, so no tuple edit. |

### B. `ui_pages/prior_apps.py` — the page object

| # | Site | Decision | Rationale |
|---|---|---|---|
| 11 | `open_detail(app_id)` | **rewrite** | Panel-card-click navigation replaced with a direct `page.evaluate` call into `_showApplicationDetail(app_id)` — see `## The consumer this enumeration almost missed`. Signature unchanged, so no caller needs its own edit. |
| 12 | `resume_visible()`, `resume()`, `resume_application()`, `set_company()` | **no change** | Unaffected — they only assume the modal is already open, which `open_detail()` still guarantees. |
| 13 | Module docstring | **update** | "the Prior Applications panel + resume-into-wizard flow" → describes the shared modal, reached via Pipeline now. |

### C. `static/app.js`

| # | Site (`path:line` at base) | Decision | Rationale |
|---|---|---|---|
| 14 | `:263-277` `_renderPipelineRow`'s `activate()` | **rewrite** | Replace the forced `switchTopTab('tailor', tailorBtn)` with `switchTopTab('pipeline', pipelineBtn)` — mirrors the OLD code's own shape (force the tab AFTER `onUserSelect()` resolves, since `onUserSelect()`'s own `_landingTab()` routing can otherwise land on 'corpus' or 'tailor' first) rather than introducing a new suppression mechanism. Comment updated to name A4. |
| 15 | `:6227-6245` Phase D.3 header comment, `_applicationsShowRetired`, `toggleApplicationsRetired`, `_setApplicationsCount` | **remove** | Panel-only state/helpers. |
| 16 | `:6247-6294` `refreshApplications` | **remove** | Panel-only. Its fetch target (`GET /api/users/<u>/applications`) is no longer called from the frontend at all after this — the route itself is kept (see row 24). |
| 17 | `:6296-6305` `_renderApplicationsList` | **remove** | Panel-only. |
| 18 | `:6316-6364` `_renderApplicationCard` | **remove** | Panel-only. |
| 19 | `:6377-6428` `_renderAppDetailStatusActions`, `_renderAppDetailAdminRow` | **no change** | Render INTO the kept modal; independently confirmed neither references `applicationsList`/`panelApplications`. |
| 20 | `:6432-6486` `_setApplicationRetired`, `_putApplicationStatus`, `_formatRelativeDate` | **no change** | Shared; `_formatRelativeDate` is also used directly by `_renderPipelineRow` (row 14), so it cannot be removed. |
| 21 | `_showApplicationDetail`'s `_saveMeta` closure, `_renderAppDetailStatusActions` (2 call sites), `_renderAppDetailAdminRow` (2 call sites), `_wizardRender`'s completion handler (analyze), the generate-completion handler, `markCurrentApplicationSubmitted()` | **update — 7 call sites, not 1** | **This row was originally written after grepping only DOM-id strings (`applicationsList`, etc.), which is why it undercounted.** A second grep for the bare symbol `refreshApplications` (done mid-implementation, before finishing this surface, per `## Consumers found only after editing began`) found SEVEN live call sites, not the one inside `_saveMeta` this row originally named. All seven → `refreshPipeline()`. `markCurrentApplicationSubmitted()`'s toast copy ("report the outcome from its Applications card") also updated — see row F. |
| 22 | `:6682-…` `resumeApplicationIntoWizard`, `_resumeIntoStep6`, `_resumeIntoPreGenerateStep` | **no change** | Shared "Resume in wizard" flow; independent of the panel. |
| 23 | `:428` `show('panelApplications')`, `:432` `_applyFoldableDefault('panelApplications', true)` (inside `onUserSelect()`) | **remove** | The element these calls target no longer exists; leaving them is a guaranteed no-op today (`show()`/`_applyFoldableDefault()` both null-guard on a missing element) but is dead intent left in a widely-shared function — removed rather than left as harmless-but-stale. |
| 24 | `:3485` `hideAllPanels()`'s array | **remove `'panelApplications'`** | Same reasoning; the array is otherwise unaffected (7 other entries untouched). |
| 25 | `:3617` `_FOLDABLE_PANEL_IDS` | **remove `'panelApplications'`, keep `'panelUser'`** | The shared fold-persistence mechanism (`_applyFoldableDefault`) stays live for the one remaining foldable panel. |
| 26 | `:2176-2182` `_HELP_REGISTRY.panelApplications` | **remove** | Orphaned help-content entry — `_initHelp()` no-ops gracefully on a missing DOM target (checked, not assumed: `static/app.js:2350-2354`), so leaving it would not error, but it is dead configuration data describing a retired feature. |

### D. `static/style.css`

| # | Site (`path:line` at base, "Phase D.3" block, `:1754-1989`) | Decision | Rationale |
|---|---|---|---|
| 27 | `.application-list`, `.application-card`, `.application-card:hover`, `.application-card-header`, `.application-card-title`, `.application-card-company`, `.application-card.retired`, `.application-card.retired:hover`, `.applications-show-retired`, `.applications-show-retired input[type="checkbox"]`, `.application-card-iter`, `.application-card-date`, `.application-card-pending` | **remove** | Exclusively set by the JS being removed (rows 15-18, 26). `.application-card-iter` has no JS producer at all (grep found zero — likely already dead before this branch); removed alongside its grouped sibling `.application-card-date` rather than left as a second, now-doubly-orphaned rule. |
| 28 | `.app-status-chip` + 6 `.status-*` variants, `.application-admin-row`, `.app-admin-btn`, `.app-admin-btn:hover`, `.app-admin-btn.retire:hover`, `.app-detail-jd`, `.app-detail-scores`, `.app-detail-score-row`, `.outcome-action-row`, `.outcome-btn`, `.outcome-btn:hover` | **no change** | Verified live producers, not assumed: `.app-status-chip.status-*` is set by `_renderPipelineBoard`'s column header (kept) AND `_showApplicationDetail`'s status chip (kept); the rest are set by `_renderAppDetailStatusActions`/`_renderAppDetailAdminRow`/`_showApplicationDetail` (all kept). Cutting the whole "Phase D.3" comment block by name would have deleted live styling for the Pipeline board and the surviving modal. |

### E. Tests

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 29 | `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py:135-147` | **rewrite (the named pinned test)** | See implementer's report for the exact new assertions and the A/B proof against the old behavior. |
| 30 | `tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_analyze_only_application_resumes_to_step_1` | **no change needed** | Uses `prior.open_detail(aid)` only — transparent once row 11 lands. |
| 31 | `tests/ux/regression/test_20260611_prior_app_resume_robustness.py::test_card_company_editable_and_pill_relabeled` | **rewrite** | `PriorApps.PENDING_PILL` assertion removed (row 6 — no DOM home; route-level coverage cited there). `PriorApps.card_company(aid)` assertion removed (row 8 — no DOM home) and replaced with a **reopen-the-modal round trip**: `set_company` → wait for the "Company saved" toast → `open_detail(aid)` again → assert `PriorApps.COMPANY_INPUT` now has the saved value. This is not a downgrade: it proves the save AND the modal's own re-hydration from a fresh `GET`, which the old card-echo assertion did not exercise. |
| 32 | `tests/ux/regression/test_20260612_corpus_first_landing.py:68` | **rewrite** | `page.wait_for_selector(PriorApps.PANEL, …)` → `page.wait_for_selector(Wizard.JD_TEXT, …)`. Both existed purely as "prove the Tailor tab's content actually rendered, not just its button state" on top of the `_wait_tab_active` check the line above already does; `Wizard.JD_TEXT` (`#jdText`, hidden by the same `hideAllPanels()` that hides `panelJD`, shown by the same `wizardInit()` that shows the rail) is an equally valid, already-existing proxy. |
| 33 | `tests/ux/regression/test_20260612_logo_home_route.py:50,67` | **rewrite** | Same substitution (`Wizard.JD_TEXT`) for both the "panel is up" wait (line 50) and the "flow panel is gone after going home" assertion (line 67) — `panelJD` is in `hideAllPanels()`'s list (unchanged member, row 24 only removed `panelApplications`), so it still turns invisible on deselect exactly as `panelApplications` used to. |
| 34 | `tests/ux/regression/test_20260606_new_user_no_4xx.py:63-68` | **rewrite (remove one row)** | The `(TopTabs.TAILOR, PriorApps.PANEL)` row existed specifically to exercise `GET /api/users/<u>/applications`'s no-409 behavior on tab activation. That call site is gone (row 16) — **verified zero remaining frontend callers of that endpoint** (`## Enumeration`) — so the row now tests nothing a browser can still trigger. Removed with a comment; the route's needs-onboarding behavior stays covered server-side (`tests/test_application_routes.py::test_missing_candidate_returns_200_needs_onboarding`). |
| 35 | `tests/ux/regression/test_20260707_ux_w4_aesthetic.py::test_tailor_tab_folds_ambient_panels_by_default` | **trim** | Remove the `PriorApps.PANEL` wait + collapsed-class assertion and the now-pointless `seed_application(...)` call; keep the `UserPicker.PANEL` collapsed-by-default assertion and `Wizard.RAIL` visibility. Docstring updated: F-23 now folds User selection only. |
| 36 | `tests/ux/regression/test_20260707_ux_w4_aesthetic.py::test_applications_panel_expand_choice_persists_across_reload` | **repurpose, not delete** | This is the **only** test in the suite exercising the shared `_applyFoldableDefault` localStorage-persistence mechanism end-to-end. Deleting it outright would silently drop coverage of a still-live mechanism (now serving `panelUser` alone) rather than of the retired panel specifically. Renamed `test_user_panel_expand_choice_persists_across_reload`; same shape, targets `UserPicker.PANEL` instead of `PriorApps.PANEL`. |
| 37 | `tests/ux/regression/test_20260707_ux_w4_aesthetic.py:34` import | **update** | Drop `PriorApps` from the selector import (no longer referenced in this file after rows 35-36); `Wizard`/`UserPicker` already imported. |
| 38 | `tests/ux/regression/test_20260707_generate_surface_download.py:204,239`, `test_20260708_step6_full_hydration.py:113`, `test_20260809_wizard_rail_frozen_gate.py:343`, `tests/ux/flows/test_output_surface_seeded.py:74` | **no change, but coverage mode shifted — see below** | All call `PriorAppsPage(...).resume_application(aid)` only — none reference `PriorApps.PANEL`/`.card()`/`.PENDING_PILL`/`.card_company()` directly (verified — grep-complete list in `## Enumeration`), so none error. But `resume_application()` calls `open_detail()`, and row 11's rewrite of `open_detail()` changed *what these four files actually exercise*: before, each drove a real click through the panel into the modal; after, each opens the modal via `page.evaluate("(id) => _showApplicationDetail(id)", app_id)` — no click, no DOM traversal, no panel-card render. "Transparent" was true for whether the tests still pass; it was not true for what they still cover, and this row originally conflated the two. `test_output_surface_seeded.py:74`'s own docstring is now stale evidence of the shift: it still reads *"click the prior app → 'Resume in wizard' → Step 6"*, but no click occurs anywhere in that path post-A4. Post-A4, `test_20260707_recruiter_roster_pipeline.py::test_pipeline_board_groups_by_status_and_switches_candidate` (row 29) is the **only** remaining test that drives the real click journey into the modal — A/B-verified by the orchestrator to fail against the pre-A4 behavior, so it is a real pin, not a hollow one. Cross-referenced from `## Deferred` #3, which named the abstract "Pipeline is now the sole entry point" risk without connecting it to these four specific files. Tracked as `docs/dev/work/items/0073-open-detail-coverage-mode-shift.md`. |
| 39 | `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py:24` import | **no change needed beyond the rewrite in row 29** | Already imports `Pipeline, PriorApps, UserPicker` — `PriorApps` stays imported for `.MODAL`. |

### F. Copy / docstrings

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 40 | `templates/index.html:176-179` panel body copy ("Past applications stored in the DB…") | **removed with the panel** | Lives entirely inside the deleted `<section>`. |
| 40a | `static/app.js`, `markCurrentApplicationSubmitted()` toast copy ("report the outcome from its Applications card") | **update** | Found alongside row 21 (same function). Now says "its Pipeline row." |
| 40b | `.application-card-date` CSS rule | **restore (found only after removing it)** | Cut in the first pass of `## Surface #3` as an Applications-card-only rule; a broader post-edit grep found `_renderMemoryRow` (Memory tab, unrelated feature) also sets `className: 'application-card-date'`. Restored with a corrected comment. `.application-card-iter`, its original paired selector, really is orphaned (re-verified: zero producers anywhere) and stays removed. See `## Consumers found only after editing began`. |
| 40c | `tests/ux/regression/test_20260707_first_run_flow.py::test_application_card_shows_company_from_analyze` | **rewrite** | Uses a raw `.application-card-company` selector string (not `PriorApps.card_company()`), so it was invisible to the `PriorApps`-scoped grep in `## Enumeration` and only surfaced via a broader post-edit sweep for the raw class name. Rewritten against a new `Pipeline.ROW_COMPANY` selector (`.pipeline-row-company`, added to the `Pipeline` class) instead. See `## Consumers found only after editing began`. |
| 40d | `tests/ux/regression/test_20260614_education_help.py`'s `_ALL_HELP_PANELS` list | **update — remove `"panelApplications"`** | Asserts every listed panel gets a help icon; `panelApplications`'s `_HELP_REGISTRY` entry (row 26) is gone, so `_initHelp()` never injects one for it and this assertion would time out. Found via the same post-edit sweep. |
| 40e | `tests/ux/regression/test_20260708_busy_states_and_chip.py:759-767` docstring | **update (prose only)** | A C-7 instrument's docstring traces `onUserSelect()`'s async call chain by name (`loadConfig -> _landingTab -> _activateTab -> refreshApplications -> _loadPersonaOptions -> wizardInit`) as scroll-timing context. `refreshApplications` is no longer a step in that chain (row 23) — the step removed from the prose, not the test logic. |
| 41 | `blueprints/applications.py:104` `_application_summary_dict` docstring | **update** | "Compact application row for the Applications tab list view" names a UI surface that no longer exists; reworded to name the route instead (`GET /api/users/<username>/applications`). Function and route are unaffected — this route stays a legitimate, tested API surface even though the frontend no longer calls it (row 16). |
| 42 | `blueprints/applications.py:236-237` `get_application` docstring | **update** | "Used by the Applications tab when the user opens a card…" → "Used by the application detail modal (opened from the Pipeline board)…". |
| 43 | `docs/PRODUCT_SHAPE.md:383` "Prior applications" bullet | **no change** | A "Library lens" IA *sketch* naming a data domain, not a description of today's implemented panel — not stale, just abstract. |
| 44 | `docs/dev/reviews/2026-07-ux-review/40-friction-register.md:184`, `docs/dev/handoffs/{wizard-rail-frozen-composition-gate,docs-epic-a-wave-orchestration-design}.md`, `V1_0_5_VERIFICATION.md`, `50-oss-polish-plan.md`, `CHANGELOG-archive.md` | **no change (historical)** | Dated records describing the state at their own time; C-8 forbids rewriting them. |
| 45 | `db/build_context.py:609` `_infer_application_title` docstring ("the Applications tab (Phase D)") | **deferred** | See `## Deferred`. |
| 46 | `scripts/backfill_application_titles.py:15` ("Applications tab, `PUT /api/applications/<id>/meta`") | **deferred** | See `## Deferred`. |
| 47 | `docs/wiki/pages/code-module-map.md` (panelApplications reference, exact line not re-derived here) | **deferred to epic close** | Wiki pass is scheduled at the Epic A close per §15.2, not per sprint; named here so the closer does not have to re-derive it. |
| 48 | `CHANGELOG.md` | **add — new `[Unreleased]` entry** | Matches A3's own precedent (`role-summary-drafting`'s dossier/commit added its own entry rather than deferring it). |

---

## Consumers found only after editing began (disclosed, not smoothed over)

**The enumeration above was NOT complete before the first edit, despite the
dossier's own header claiming so at the time.** Stated plainly per C-12: five
real consumers surfaced only through broader greps run mid-implementation,
after `ui_pages/selectors.py` and `templates/index.html` had already been
edited. In order found:

1. Six of `refreshApplications()`'s seven live call sites (row 21) — the
   original enumeration grepped DOM-id strings, not the bare function symbol.
2. `.application-card-date` (row 40b) — sharing a CSS class name with an
   unrelated feature (Memory rows), briefly deleted, restored.
3. `.application-card-company` raw-string test consumer (row 40c) — invisible
   to a `PriorApps`-scoped grep because it never went through the registry.
4. `panelApplications` in a help-icon inventory test (row 40d).
5. A stale docstring trace in an unrelated flake-diagnosis test (row 40e).

**Why this matters more than the individual fixes.** The dossier's own
opening line ("written BEFORE the first edit... to any file named below")
was accurate for `ui_pages/selectors.py` specifically (the gated file), but
the SURFACE enumeration under it was not grep-complete by the time editing
started on `static/app.js` and `static/style.css` — it was completed
*during* that editing, via repeated broader sweeps, not before it. Each of
the five was caught before commit, each is fixed, and a final whole-tree
sweep (see `## Verification`) found nothing further as of this writing — but
the ORDERING guarantee C-10 exists to provide (enumerate, then decide, then
edit) held for the gated file and did not fully hold for the ungated ones
this branch also touches. Recorded here rather than quietly folded into the
tables above as if they had been foreseen.

## Deferred

1. **`ui_pages/pipeline.py` gains no new selector or method** (`Pipeline.row(app_id)`
   was drafted, then rejected). Routing `PriorAppsPage.open_detail()` through a
   live Pipeline-row click was the first design considered; rejected because
   it would re-run `onUserSelect()`'s full cascade (`loadConfig`,
   `_resetIterationState`, `wizardInit`, …) as a side effect of "just open this
   application's modal," risking wizard-state resets in tests that build up
   state before calling `resume_application()`. The direct-`page.evaluate`
   design (row 11) avoids this entirely. **Gap this leaves:** the Pipeline
   row's own click journey — including the user-switch cascade — is exercised
   by exactly one test now (`test_20260707_recruiter_roster_pipeline.py`,
   row 29). That was already true before this branch (it was the only test
   pinning the OLD tab-switch behavior too), so this is not a new coverage
   loss, but it is worth naming since Pipeline is now the sole production
   entry point into the modal.
2. **`db/build_context.py:609` and `scripts/backfill_application_titles.py:15`**
   — both reference "the Applications tab" by name in a docstring. Left
   untouched: `build_context.py`'s is a passing mention with no functional
   stake, and `backfill_application_titles.py`'s is inside a **SAFETY RULE**
   paragraph for a manual, already-conservative one-off script — editing the
   parenthetical UI-attribution risked disturbing the surrounding reasoning
   for a compliance-relevant safety invariant with no runtime benefit. Filed
   here rather than silently skipped; a documentation-only pass can fold
   these in along with row 47's wiki page.
3. **No pending-proposals indicator was added to the Pipeline row.** The
   removed panel's `.application-card-pending` pill (row 6) has no Pipeline
   equivalent. The ARC brief does not ask for one, and adding a new indicator
   to `_renderPipelineRow` (plus its own selector, plus a new UX assertion)
   is feature work beyond "remove the panel, rewrite `activate()`" — out of
   scope for this sprint, but a real, user-visible reduction in what's
   discoverable at a glance (the count is still reachable inside the detail
   modal via `runs[].pending_proposals`, just not on the row). Worth a work
   item at epic close if the owner wants parity restored. Tracked as
   `docs/dev/work/items/0072-pipeline-row-no-pending-indicator.md`. This
   entry named the abstract risk of Pipeline becoming the sole entry point
   into the modal; row 38 in `## Consumers` §E now names the concrete four
   test files whose coverage mode shifted as a result, tracked separately as
   `docs/dev/work/items/0073-open-detail-coverage-mode-shift.md`.

---

## Efficiency

**Disclosed, not discovered later: this branch widens every trigger of the
Pipeline refetch from one candidate's applications to the entire cross-candidate
roster.** The panel's `refreshApplications()` fetched `GET
/api/users/<u>/applications` — one candidate. Its replacement, `refreshPipeline()`
(`static/app.js:203`), fetches `GET /api/candidates/roster` — every candidate's
applications, on every call. All **7** call sites converted from the former to
the latter (`static/app.js:1101` inside `runAnalysis`'s completion handler,
`:1794` the generate-completion handler, `:3458`
`markCurrentApplicationSubmitted()`, `:6272` inside
`_renderAppDetailStatusActions`, `:6289`/`:6303` — restore and retire, both
inside `_renderAppDetailAdminRow` — and `:6506` the `_saveMeta` closure — see
row 21) now trigger a full-roster refetch
on every analyze completion, generate completion, status change, restore,
retire, and meta-save. `refreshPipeline()`'s own `if (!board) return` guard
(`static/app.js:206`) never actually short-circuits this in practice, because
`#pipelineBoard` (`templates/index.html:940`) sits inside a `.hidden` tab panel
that is never removed from the DOM — the element is always present, whether or
not the Pipeline tab is visible.

**This is a deliberate trade, not a regression left unnamed.** The panel this
replaced is gone, and no per-candidate endpoint remains wired to any surviving
frontend surface to fetch against instead — a narrower refetch is not available
without adding one back. The trade is also mitigated, not raw: `GET
/api/candidates/roster` (`blueprints/users.py::candidate_roster`) is a fixed
2-query aggregate regardless of candidate or application count, guarded by
`test_roster_avoids_n_plus_1_query_growth`. So the cost of this widening is a
**wider payload per trigger, not an algorithmic regression** — no N+1 was
introduced by this branch. Worth revisiting if the candidate roster grows large
enough that a 2-query fixed-cost fetch on every status-change becomes a real
per-request cost; tracked as
`docs/dev/work/items/0074-refresh-pipeline-roster-wide-refetch.md`.

---

## Verification

**How a missed consumer would surface, and what was run.**

- **Every `PriorApps.PANEL`/`.LIST`/`.card()`/`.card_company()`/`.PENDING_PILL`
  removal is a Python `AttributeError` at import or first use** if any test
  file still references it — not a silent pass. `pytest -m ux` collection
  itself fails loudly (`ImportError`/`AttributeError` at module load) for any
  file whose import list still names a removed member, so a missed consumer
  in this specific family cannot pass silently.
- **A missed `refreshApplications()` reference inside kept code
  (`_saveMeta`) would throw `ReferenceError: refreshApplications is not
  defined`** the first time a company/title edit fires — caught by re-reading
  `_showApplicationDetail` end-to-end before editing (see `## The consumer
  this enumeration almost missed`), and independently re-checked afterward by
  re-running `test_card_company_editable_and_pill_relabeled` (row 31), which
  exercises exactly that path.
- **A missed `hideAllPanels()`/`_FOLDABLE_PANEL_IDS` cleanup would not error**
  (`hide()`/`_applyFoldableDefault()` both null-guard) — this is the
  category A3's dossier calls out as *not* self-announcing. Mitigated by
  `test_20260612_logo_home_route.py` (row 33), which asserts the flow-panel
  proxy is gone after logout, and `test_user_panel_expand_choice_persists_across_reload`
  (row 36), which exercises `_applyFoldableDefault` directly.
- **`pytest -m ux` full tier, run after every edit on this branch**, is the
  actual backstop for the JS-side blind spot `blast_radius.py`'s own
  docstring names (computed offenders are first-party Python import fan-in
  only). Terminal counts reported in the implementer's report for this
  sprint, per the same convention the A2/A3 dossiers used.

---

# Second surface (same branch) — the unhandled keyless-client 500

> **Status:** enumeration below written BEFORE the first edit to `analyzer.py`.
> **Trigger:** PR #117's required check went red on
> `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py::test_resumed_application_with_a_frozen_composition_can_reach_step5`,
> which omits `install_llm_stubs` and therefore drives the real
> `analyzer.draft_positioning_summary` through `POST
> /api/applications/<id>/draft-summary`.
> **Gate status:** `blueprints/applications.py` and `analyzer.py` are **not** in
> `scripts/enforcement/blast_radius.py`'s gated registry — verified, no
> `require-consumer-enumeration` hook fires here. This section exists because a
> handler pattern repeated across five blueprint modules is a shared contract
> regardless of whether a hook agrees (C-10's ordering discipline is the rule;
> the hook is only one enforcement of it).

## Surface

**Observed mechanism (from the sprint's diagnosis, not re-derived here):** with
no `ANTHROPIC_API_KEY` and no `.api_key` file, `web_infra.clients._get_client()`
returns `anthropic.Anthropic(api_key="")`. The SDK accepts that at construction
time and only refuses at request-build time, inside
`anthropic/_client.py::_validate_headers`, with a bare **`TypeError`**
("Could not resolve authentication method…"). Confirmed against the installed
SDK (`anthropic==0.88.0`): `_api_key_auth` returns `{"X-Api-Key": ""}` for an
empty key, `_validate_headers` sees a falsy header value, and falls through to
the `raise TypeError`. `TypeError` matches neither of the two handlers every LLM
route pairs (`anthropic.APIConnectionError`, `analyzer.LLMResponseError`), so it
escapes to Flask as a **500**.

The single production surface changed is therefore **`analyzer._call_llm_streaming`**
— the one place in the codebase that touches `client.messages` (grep-verified:
`analyzer.py:1247` is the only `client.messages.*` outside `evals/runner.py`,
which has its own client factory). `_call_llm` is a thin drain of that
generator, so covering the generator covers both.

**One new symbol:** `analyzer.LLMConfigurationError`, a **subclass of
`analyzer.LLMResponseError`**. The subclassing is the load-bearing design
decision, not an incidental one — see `## Options weighed` below.

## Enumeration

Whole tree, `Grep`/ripgrep, run before the first edit:

```
rg -n "client\.messages" -g "*.py"        -> analyzer.py:1247 (the only call
                                             site behind every blueprint route)
                                             evals/runner.py:369,554 (separate
                                             client factory, evals only)
                                             + test doubles only
rg -n "except anthropic.APIConnectionError" blueprints/
                                          -> 20 sites / 6 modules
rg -n "except LLMResponseError" blueprints/
                                          -> 19 sites / 5 modules
rg -n "LLMResponseError" -g "*.py"        -> analyzer (def + 7 raise/doc sites),
                                             blueprints/{analysis,applications,
                                             generation,corpus/proposals,
                                             corpus/skills}, evals/runner.py:817,
                                             scripts/smoke_phase_b1.py:151,175,
                                             onboarding/extract_experiences.py
                                             (docstring), 6 test modules
rg -n "_get_client" -g "*.py"             -> web_infra/clients.py (def) +
                                             8 blueprint modules + evals +
                                             scripts/vector_before_after_eval.py
```

**Correction to the sprint brief's own count (recorded, not smoothed over):**
the brief states the two-exception pattern repeats *"17 times across 4 files"*.
The grep-complete count is **19 `except LLMResponseError` sites across 5
modules** — the brief's enumeration omitted `blueprints/corpus/proposals.py`
(2) and `blueprints/corpus/skills.py` (1), and `blueprints/assistant.py` (which
it counted) actually has **no** `LLMResponseError` handler at all. This is the
"any hand-maintained consumer list is stale until re-derived" case C-10 names.

## Consumers

Every site below inherits the new behavior **without an edit**, because
`LLMConfigurationError` subclasses the exception each already catches.

| # | Site | Decision | Rationale |
|---|---|---|---|
| 49 | `analyzer.py:1149` `_call_llm_streaming` | **edit** | Pre-check the client's resolvable auth inside the existing `try:` (so the `finally:` still emits the `status="error"` telemetry row it emits today) and raise `LLMConfigurationError`; plus a message-matched conversion of the SDK's own `TypeError` as a version-drift backstop. |
| 50 | `analyzer.py:35` `LLMResponseError` | **no change** | Untouched; the new class extends it. Nothing anywhere does `type(exc) is LLMResponseError` (grep-verified) so no `isinstance`-vs-identity trap. |
| 51 | `analyzer.py:1299` `_call_llm` | **no change** | Pure drain of #49 — inherits the behavior. |
| 52 | `analyzer.py:1431/1349` `_parse_or_retry` / `_parse_or_retry_streaming` | **no change** | Both catch only `(json.JSONDecodeError, ValidationError)`, so a config error propagates on the **first** attempt and is never re-tried into a second (would-be) call. Checked before editing, not assumed. |
| 53 | `blueprints/analysis.py:277,375,476,813` | **no change** | 4 `except LLMResponseError` sites → 502 + `detail=exc.validation_error`, which now carries the credential cause verbatim. |
| 54 | `blueprints/applications.py:1996,2140,2272,2395,2938,3251,3599,3703,3788` | **no change** | 9 sites; `:2272` is the one the failing UX test hits. |
| 55 | `blueprints/generation.py:970,1444,1568` | **no change** | 3 sites (`:1444` is inside the SSE generator → emits an `error` event with `http_status: 502` rather than a 500). |
| 56 | `blueprints/corpus/proposals.py:143,398` | **no change** | 2 sites the brief's list omitted. |
| 57 | `blueprints/corpus/skills.py:322` | **no change** | 1 site the brief's list omitted. |
| 58 | `blueprints/assistant.py:270-278` | **no change** | Has **no** `LLMResponseError` handler, but its SSE generator already ends in a blanket `except Exception` → `_sse("error", …, http_status 500)`. It never produced an unhandled Flask 500 for this defect and does not now; behavior is unchanged there. Named rather than silently omitted. |
| 59 | `evals/runner.py:817` | **no change** | Records `iter_status="pipeline_error"` with `exc.validation_error` as the reason; a credential failure now lands there with a clear reason instead of in the adjacent `except Exception` with a raw `TypeError` string. Strictly better, no semantic damage. |
| 60 | `scripts/smoke_phase_b1.py:151,175` | **no change** | Same: a clearer message on the same branch. |
| 61 | `web_infra/clients.py:47` `_get_client` | **no change — deliberately** | See `## Options weighed` (a). |
| 62 | `tests/ux/stubs.py:488` `install_llm_stubs` | **no change** | Patches `_get_client` to `lambda: None`. `None` exposes neither credential slot, so the pre-check passes it straight through and an unstubbed call still fails with the same `AttributeError` → 500 it always did. The missing-stub signal is deliberately **not** relabeled: `tests/ux/conftest.py:216` red-lines the `page` fixture on `resp.status >= 500` either way, but keeping the original shape means the next omission looks exactly like this one did. "Did the fix mask its own defect class?" is the question that matters here, and the answer is no. |
| 62a | `tests/test_extract_experiences.py` (9 tests), `tests/test_analyzer_model_selection.py` | **no change — but ONLY because the check was tightened for them** | **Found by direct probe before running anything, not after a red suite.** These pass `MagicMock(spec=anthropic.Anthropic)`. The SDK sets `api_key` as an *instance* attribute, so it is absent from `dir(anthropic.Anthropic)` and a spec'd mock raises `AttributeError` for it — a naive `getattr(client, "api_key", None)` pre-check reads that as "no credential" and would have failed all of them. The shipped check therefore refuses only on **present-and-falsy** slots and passes through anything exposing neither. Probe: `'api_key' in dir(anthropic.Anthropic)` → `False`; `MagicMock(spec=anthropic.Anthropic).api_key` → `AttributeError`; `anthropic.Anthropic(api_key="").api_key` → `''`, `.auth_token` → `None`. |
| 63 | `analyzer.py`'s 21 `_demo_mode_active()` short-circuits | **no change** | Every call kind returns canned output before reaching #49, so `_DemoClient` (which has no `api_key`) never trips the new pre-check. |

**Negative results (findings, recorded deliberately):**

- **No `PROMPT_VERSION` bump is required.** No prompt text, persona constant,
  or user-prompt builder changes — grep-verified: the edit touches only the
  pre-flight of `_call_llm_streaming`, above `stream_kwargs`.
- **No route file changes at all.** Zero edits under `blueprints/`, so
  `route-security-lint` has nothing to fire on and no route's happy path,
  status code, or body shape moves.
- **`tests/test_egress_allowlist.py:SANCTIONED_EGRESS_FILES` is unaffected** —
  no module gains or loses an `anthropic` import (`analyzer.py` already
  imports it).

## Options weighed (and why the two rejected ones were rejected)

**(a) Fail fast in `web_infra.clients._get_client()` — REJECTED, and not merely
as "broader".** It is *wrong at that boundary*: several routes call
`_get_client()` eagerly and then hand the client to an analyzer function that
**short-circuits without any LLM call**. `analyzer.draft_positioning_summary`
(`analyzer.py:4222-4223`) returns the source summary unchanged when the context
carries no JD; `analyzer.py` has **21** `_demo_mode_active()` short-circuits of
the same shape. Raising in `_get_client()` would convert those
currently-working, deliberately-free, keyless paths into errors — a real
regression traded for the fix. Worse, the raised error would have to subclass
something the 17-plus sites already catch anyway, so it buys no coverage that
(b) does not, while adding blast radius across `evals/`, `scripts/`, and
`blueprints/diagnostics.py`.

**(c) Per-route catch at `/draft-summary` only — REJECTED.** It fixes the one
red check and leaves the identical hole at the other 18 `LLMResponseError`
sites plus every future one. C-11: the recurrence is the whole point; a fix
scoped to the instance that happened to be observed is the note-instead-of-gate
failure mode.

**(b) Catch at the analyzer boundary — CHOSEN.** It is the narrowest place that
is also complete: one function, the only `client.messages` call site, reached by
every one of the 19 handler sites. A blanket `except TypeError` there was
explicitly **not** used — it would swallow genuine programming errors (a wrong
argument, a `None` where a dict is expected) and turn real bugs into polite
messages. Instead:

1. A **pre-check** on the client's resolvable auth (`api_key` / `auth_token`),
   raising before any SDK call — deterministic, no message matching. It refuses
   only on a **positive determination** (both slots present and falsy) and
   passes through any object exposing neither, which is what keeps row 62 and
   row 62a's existing behaviors intact. This covers every path to the observed
   `TypeError` in `anthropic==0.88.0` (`_api_key_auth`/`_bearer_auth` are the
   only two contributors to the headers `_validate_headers` inspects).
2. A **message-matched conversion** of `TypeError` (only when
   `"Could not resolve authentication method"` is in the message) as the
   SDK-version-drift backstop. Narrow by construction: any other `TypeError`
   re-raises untouched and still reaches the developer as a 500.

**Known limits (stated, not papered over — C-0):**

- The pre-check reads `api_key`/`auth_token` attributes. A future auth mode
  that resolves through neither (e.g. `AnthropicBedrock` / `AnthropicVertex`)
  would be a **false positive**. Not a live risk today: `_get_client()`
  constructs `anthropic.Anthropic(api_key=...)` and nothing else, and
  `_call_llm_streaming` is typed `client: anthropic.Anthropic`.
- The resulting HTTP status is **502**, and the route's user-facing `error`
  string still says "malformed" (it is the existing `LLMResponseError` copy at
  19 untouched sites). The *cause* is carried verbatim in the response `detail`
  and in the route's own `logger.error` line. Making the status a 503 with
  "AI service is not configured" copy would require editing all 19 sites —
  deferred rather than done silently; see `## Deferred` #4.

## Deferred

4. **The 19 handler sites keep 502/"malformed" copy for a configuration
   error.** Correct status/copy would be 503 + "the AI service is not
   configured". Doing it means 19 edits across 5 modules on a branch whose job
   is a red check, so it is filed, not done. The information is not lost — the
   `detail` field and the server log both name the cause exactly.

## Verification (this surface)

- **`tests/test_llm_credential_gate.py`** (new) pins all four halves: the
  keyless client raises `LLMConfigurationError` **and never touches
  `client.messages`**; a keyed client's path is untouched; a genuine `TypeError`
  raised from inside the stream is **not** converted (the anti-blanket-catch
  assertion); and `POST /api/applications/<id>/draft-summary` with a keyless
  client returns a deliberate non-500 naming the cause.
- A missed consumer here **cannot be silent**: every site either catches
  `LLMResponseError` (inherits the new class) or already has a blanket
  `except Exception`. The failure mode of getting this wrong is a *louder*
  error, not a quieter one.
