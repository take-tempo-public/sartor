# Frontend wizard

> **Audience:** `dev`
> **Concept:** the browser wizard — the six-step panel rail, the Compose cards
> (bullets + B.4 role-intro picker + B.5 skills card), the paged.js live preview,
> config persistence, the smart-landing top-tab structure, the reusable in-app help
> primitive, and the KW3 new-user first-run tour.
> **Sources:** [`static/app.js`](../../../static/app.js),
> [`templates/index.html`](../../../templates/index.html),
> [`static/style.css`](../../../static/style.css).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The UI is a single page of vanilla JS + `fetch` — no framework. `onclick` handlers in
`index.html` are the binding contract to `app.js`; public functions are bare camelCase,
private helpers `_`-prefixed (the naming rules are stated in the
[`static/app.js`](../../../static/app.js) file header).

## Two structures: top tabs over a wizard rail

The page is split into four **top tabs** — `Career corpus`, `Tailor`,
`Résumé templates`, `Candidate memory` — rendered as `role="tab"` buttons in
[`templates/index.html`](../../../templates/index.html) (`topTabCorpus` / `topTabTailor`
/ `topTabPersonas` / `topTabMemory`). The displayed labels diverge from the internal tab
keys: `Résumé templates` is `personas`, `Candidate memory` is `memory` `[synthesis]`.
[`app.js:_activateTab`](../../../static/app.js) maps `{tailor,corpus,personas,memory}` to
those button ids and routes through `switchTopTab`.

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
localStorage seam (`_HELP_SEEN_PREFIX`), wrapped so a throwing store reads as "not seen"
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
- [[diagnostics-console]] — the localhost console that ports this help primitive.
