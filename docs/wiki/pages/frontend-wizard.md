# Frontend wizard

> **Audience:** `dev`
> **Concept:** the browser wizard — the six-step panel rail, the Compose cards
> (bullets + B.4 role-intro picker + B.5 skills card + Compose-authored summary and
> gap-fill drafting), the frozen-composition / WYSIWYG-as-source re-architecture,
> the paged.js live preview, config persistence, the smart-landing top-tab
> structure, the reusable in-app help primitive, and the KW3 new-user first-run
> tour.
> **Sources:** [`static/app.js`](../../../static/app.js),
> [`templates/index.html`](../../../templates/index.html),
> [`static/style.css`](../../../static/style.css),
> [`docs/dev/generation-experience-rearchitecture.md`](../../../docs/dev/generation-experience-rearchitecture.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The UI is a single page of vanilla JS + `fetch` — no framework. `onclick` handlers in
`index.html` are the binding contract to `app.js`; public functions are bare camelCase,
private helpers `_`-prefixed (the naming rules are stated in the
[`static/app.js`](../../../static/app.js) file header).

## Two structures: top tabs over a wizard rail

The page is split into five **top tabs** — `Career corpus`, `Tailor`,
`Résumé templates`, `Candidate memory`, `Pipeline` — rendered as `role="tab"` buttons in
[`templates/index.html`](../../../templates/index.html) (`topTabCorpus` / `topTabTailor`
/ `topTabPersonas` / `topTabMemory` / `topTabPipeline`). The displayed labels diverge from the internal tab
keys: `Résumé templates` is `personas`, `Candidate memory` is `memory`, `Pipeline` is
`pipeline` `[synthesis]`. [`app.js:_activateTab`](../../../static/app.js) (the smart-landing
router) maps only the first four — `{tailor,corpus,personas,memory}` — to their button ids;
`Pipeline` ([`topTabPipeline`](../../../templates/index.html)) is reached only by clicking its
own tab button, which calls [`switchTopTab`](../../../static/app.js) directly — the smart-landing
router never lands on it. Its cards navigate the other way: a card click in
[`_renderPipelineRow`](../../../static/app.js) switches the candidate and opens **Tailor** on
their applications list `[synthesis]`.

The **Tailor** tab (`#tab-tailor`) hosts the wizard. A rail of `.wizard-step` buttons
(`data-wstep="1".."6"`) sits above six `.cb-panel` sections, each tagged
`data-wstep-body`.

## Smart landing

After a user is selected, [`app.js:_landingTab`](../../../static/app.js) fetches
`/api/users/<u>/experiences` and returns `'corpus'` when the corpus is empty (zero
experiences) else `'tailor'` — so a brand-new user lands on onboarding and a returning
user lands straight on the wizard `[synthesis]`. It is deliberately side-effect-free
(it must not seed the corpus-loaded guard). On error it falls back to `'tailor'` to avoid
stranding mid-onboard. `goHome` deselects the user, then re-resolves through the same
`_landingTab` (the single source of truth for "home") so the logo click and a cold start
show the same view.

## The six wizard steps

[`app.js:_WIZARD_PANELS`](../../../static/app.js) is the step→panel map, and
[`app.js:_WIZARD_STEP_LABELS`](../../../static/app.js) the labels:

| Step | Label | Panel(s) |
|---|---|---|
| 1 | Job + Analyze | `panelJD`, `panelAnalysis` |
| 2 | Clarify | `panelClarify` |
| 3 | Compose | `panelCompose` |
| 4 | Template | `panelTemplate` |
| 5 | Generate | `panelGenerate` |
| 6 | Download | `panelOutput` |

Step 1 spans two panels because the user reviews the analysis before advancing.
[`app.js:_wizardRender`](../../../static/app.js) shows only the active step's panels and
hides the rest, recomputes the rail's done/active/upcoming classes + connector ink-trail,
mirrors `Step N of 6 · <label>` into the floating bottom statusbar, and scrolls the active
panel into view. Forward motion is gated by
[`app.js:_wizardReachable`](../../../static/app.js): step ≥ 2 needs a successful analysis
(`lastContextPath`), step 6 needs a generation (`lastResumePath`) `[synthesis]`.
[`app.js:wizardGoTo`](../../../static/app.js) lazy-loads on entry — `loadComposition()` on
step 3, `_loadTemplatePicker()` on step 4.

## Step 3 — the Compose cards

`#composeList` holds one card per experience, plus a skills card. The card renderer adds
the **B.4 role-intros toggle** ([`app.js:_renderRoleIntrosToggle`](../../../static/app.js))
when any role has summary variants — an opt-in `composeRoleIntrosToggle` checkbox; when on,
each role section (`.compose-role-intro[data-exp-id]`) exposes a per-role intro picker. The
**B.5 skills card** ([`app.js:_renderSkillsCard`](../../../static/app.js)) carries pin/drop
rows plus a recommend-skills (Haiku ordering) and a grounded suggest-skills review lane.

Every save funnels through one gatherer,
[`app.js:_collectCompositionState`](../../../static/app.js), which snapshots bullets
(`pinned`/`excluded`/`added`), `bullet_order` (only lists flagged `data-custom-order`),
`pinned_title_ids` (only `data-user-pinned` lists), then spreads in
[`_collectExperienceSummaryState`](../../../static/app.js) (B.4 toggle + chosen intro ids)
and [`_collectSkillState`](../../../static/app.js) (B.5 pin/drop/order). The POST to
`/api/applications/<id>/composition` **rebuilds `composition_overrides` wholesale**, so a
partial body would drop every omitted field — routing every path (debounced autosave in
[`_scheduleCompositionSave`](../../../static/app.js), the role-intro toggle, the summary-pin
in [`_togglePositioningPin`](../../../static/app.js), and
[`saveCompositionThenNext`](../../../static/app.js)) through the one collector is what keeps
sibling override families intact `[synthesis]`. The `data-custom-order` / `data-user-pinned`
gates mean an untouched card sends nothing, keeping the default path (and the generate
cache) byte-identical `[synthesis]`. The override schema itself lives in
[[corpus-to-output-reach]] — not restated here.

## The generation-experience re-architecture: frozen composition + deterministic Generate

Compose is no longer just a curation surface — it is where content is *authored*.
The full design record (locked owner decisions D1–D6, the build sequence, and the
as-built record for every phase) lives in
[`docs/dev/generation-experience-rearchitecture.md`](../../../docs/dev/generation-experience-rearchitecture.md);
this section is the frontend's view of it.

**Auto-drafting on arrival.** `loadComposition()` fires up to three background
content-authoring calls the first time Compose loads for an application: the
2-sentence positioning summary
([`app.js:_fireDraftSummary`](../../../static/app.js), Sonnet
`draft_positioning_summary`), skills recommendation
([`_fireRecommendSkills`](../../../static/app.js)), and — deferred to a pass where
neither of those is in flight — grounded gap-fill bullet proposals for JD
requirements the corpus doesn't cover
([`_fireDraftGapFill`](../../../static/app.js), Sonnet `draft_gap_fill_bullets`).
A local `bgDraftFiring` flag inside `loadComposition` and the persisted
`data-compose-bg-pending` counter (`_markComposeBgReload`) serialize these so two
calls never read-modify-write the same context file at once — a real clobber bug
this serialization exists to prevent `[synthesis]`. While the counter is nonzero, a
`#composeBgChip` ("Updating suggestions…") makes the in-flight background work
visible rather than silent. Gap-fill proposals render per-role with accept/retire;
[`app.js:_renderGapFillControls`](../../../static/app.js) also exposes an
always-visible "Regenerate suggestions" control that re-fires the same draft route
on demand, excluding (route-side) any key already retired or already accepted so a
decided-on proposal never resurfaces.

**Freezing on Save-and-continue.** `saveCompositionThenNext`
([`static/app.js`](../../../static/app.js)) POSTs the collected composition state
with `freeze: true`; the server resolves it into `approved_composition` — a
resolved JSON-Resume snapshot plus a `meta.sartor` provenance block — via
`corpus_to_json_resume.freeze_approved_composition`. `_compositionFrozen` (a
client-side flag mirroring the server's `_frozen_composition` gate) then makes
Step 5's copy state-aware: [`app.js:_renderGenerateStepCopy`](../../../static/app.js)
shows one of two copy blocks (`#generateStepCopyFrozen` /
`#generateStepCopyLegacy`) depending on whether Generate is about to run a real
LLM call or deterministically assemble the frozen content — so the app never
claims a determinism guarantee it isn't about to honor `[synthesis]`.

**Surgical refinement loops back to Compose, not a rewrite.** In corpus mode
(`_composeApplicationId != null`), `submitRefinement` routes to
[`app.js:_submitSurgicalRefinement`](../../../static/app.js) instead of the legacy
full-regenerate path: it runs the same `/api/validate-refinement` scope check,
then drafts exactly ONE scoped proposal (`POST .../draft-refinement`) — a
sharpened existing bullet, a genuinely new grounded bullet, or a rewritten
summary — and routes back to Compose with a banner
([`_renderComposeLoopbackBanner`](../../../static/app.js)) showing the actual
proposed change for accept/retire. A note the model can't scope to one item
("rewrite everything") falls back to plain "go adjust it yourself" copy. Legacy
(file-based, non-corpus) applications keep the original LLM full-regenerate.

**WYSIWYG-as-source: the preview always matches what Download would produce.**
Editing `#resumePreview` / `#coverPreviewFrame`'s companion editor debounces
(300ms) into [`app.js:_refreshLiveEditPreview`](../../../static/app.js), which
POSTs the live editor text to `POST /api/applications/<id>/preview-edited` (new
route, `blueprints/templates.py`) and swaps the iframe's `srcdoc` — nothing is
persisted by this call. This closes the gap where a typed edit was visible to
`/api/download-edited` immediately but the styled preview only picked it up after
the separate explicit `/api/save-edits` gate — preview and download could
disagree in between `[synthesis]`. The existing "your edits aren't saved yet"
modal and `/api/save-edits` persistence are unchanged; the live route is a pure,
non-persisting display refresh layered on top.

## The paged.js live preview

Three sandboxed iframes render the real document: `livePreviewFrame` (Step 4 template
picker), `outputPreviewFrame` (Step 6 résumé), `coverPreviewFrame` (Step 6 cover letter).
Each loads a server-rendered HTML route (`/api/applications/<id>/preview` etc.) and is
wired through [`app.js:_wirePreviewPageCount`](../../../static/app.js), installed once per
frame (sentinel flag). The iframe's paged.js layout posts a `pagedjs_rendered` message
upstream → a "Page N of M" chip; messages are routed by
`ev.source === frame.contentWindow` so the three frames don't cross-talk `[synthesis]`. A
load-time fallback, [`_updatePreviewPageCount`](../../../static/app.js), estimates the count
from `scrollHeight` against an 11"×96-DPI Letter page until paged.js's real count arrives.

## Config persistence

[`app.js:saveConfig`](../../../static/app.js) PUTs the settings form to
`/api/users/<u>/config`. It conditionally spreads `included_resumes` from `currentConfig`
so a settings save never clobbers that array. Note the AGENTS.md "Frontend config
persistence" helpers `_savePrimaryResume` / `_saveIncludedResumes` are **no longer present
under those names** in [`static/app.js`](../../../static/app.js): the legacy
primary/supplemental résumé-chip selection was removed in Workstream E (comment at
[`uploadFile`](../../../static/app.js)) — the DB corpus is now the single source of truth,
and `resume_filename` is ignored server-side (comment at
[`runAnalysis`](../../../static/app.js)) `[synthesis]`. `saveConfig`'s `included_resumes`
spread is the surviving remnant of that path `[synthesis]`.

## In-app help + the KW3 first-run tour

A single shared `#helpModal` ([`templates/index.html`](../../../templates/index.html)) is
the whole help surface; [`app.js:openHelpModal`](../../../static/app.js) swaps its
title/body per block from [`app.js:_HELP_REGISTRY`](../../../static/app.js) (one entry per
`.cb-panel`: a title, pathfinding body, optional inline short-form, and a `welcome` flag).
On load [`app.js:_initHelp`](../../../static/app.js) injects a `.help-info` `(i)`-circle
into each registered block's `.panel-header` (idempotent; adds `.has-help-icon` so the
title + icon group left and the collapse chevron stays right — see
[`static/style.css`](../../../static/style.css)) and, where a short-form exists, an inline
`.help-inline` line as the first `.panel-body` child wired into `aria-describedby`. The
`panelUser` welcome block auto-opens once-ever via
[`app.js:_maybeAutoOpenHelp`](../../../static/app.js), gated by the `cb_help_seen:`
localStorage seam (`CB_HELP_SEEN_PREFIX`), wrapped so a throwing store reads as "not seen"
`[synthesis]`. The same primitive is **ported** (not imported) into the localhost console
— see [[diagnostics-console]].

Layered on top is the **KW3 new-user first-run tour** — a once-ever guided sequence shown
only to new users. Its only new state is an in-memory armed flag
([`app.js:_helpTourArmed`](../../../static/app.js) /
[`_armHelpTour`](../../../static/app.js)): `createUser` and an empty-corpus `_landingTab()`
arm it; a returning user never is, so the tour never re-walks onboarding `[synthesis]`.
[`app.js:_maybeFireTourStop`](../../../static/app.js) fires a stop once-ever, only while
armed and with no modal already open (so stops never stack);
[`app.js:_fireWizardTourStop`](../../../static/app.js) fires the active step's stop from
[`_wizardRender`](../../../static/app.js) and on wizard entry, guarding
`offsetParent === null` so a panel on a hidden top tab doesn't fire early `[synthesis]`.

## Related

- [[code-module-map]] — where `app.js` / `index.html` sit in the module map.
- [[pipeline-stages]] — the analyze→compose→generate flow the wizard steps drive.
- [[route-surface]] — the `/api/...` routes each step calls.
- [[corpus-to-output-reach]] — how composition overrides reach the generated document.
- [[tailoring-a-resume]] — the user-facing walk through the same six steps.
- [[diagnostics-console]] — the localhost console that ports this help primitive.
