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

## Career corpus panel — corpus list and soft-retire management

The **Career corpus** tab (`#tab-corpus`) renders [`#panelCorpus`](../../../templates/index.html) with
a list of experiences, skill/education/certification editors, and import affordances.

**Section order** (owner-decided 2026-08-08, Epic A sprint A1a): Summary →
**Work Experience** → Education → Certifications → Skills. Work Experience leads
because it is the corpus's substance and the section users edit most; the credential
sections stay adjacent; Skills closes the panel. Every `ui_pages/` selector for these
is **ID-based**, so the order is presentational only — the markup comment in
[`templates/index.html`](../../../templates/index.html) says to keep it that way and
introduce no `:nth-child` coupling `[synthesis]`.

The same sprint **compacted the skill rows**. `.skill-editor-row` had inherited
`.summary-variant-row`'s two-column grid, so chip, tags and actions each claimed their
own line and a short skill list read as a wall of cards; it now borrows
`.pipeline-row`'s density (8px/10px padding, tight margin) and lays out as one wrapping
flex line ([`static/style.css`](../../../static/style.css)). Three constraints are
recorded in the rule's own comment and are the reusable part:

- **`cursor: pointer`, the hover border-color change and the `translateY` lift were
  deliberately NOT borrowed.** Those belong to a row that is itself clickable; a skill
  row's affordances are the buttons *inside* it, so a lift would be a false affordance.
  Density is the shared idiom, not interactivity.
- The new selectors must stay **after** `.summary-variant-row` — both are single-class
  selectors, so the cascade resolves the tie on source order.
- `.skill-editor-head` is styled **descendant-scoped** (`.skill-editor-row
  .skill-editor-head`) because that class is reused by the denied-skill, education and
  certification row renderers; a bare rule would have restyled sections this sprint
  does not touch.

Within
the experiences list, a **"Show retired" toggle** (`toggleCorpusRetired`,
[`app.js:toggleCorpusRetired`](../../../static/app.js)) manages visibility of soft-retired
roles (those with `is_active: false`). The toggle is **async**: it calls
[`app.js:refreshCorpus`](../../../static/app.js) to reload the entire experiences list
from the server, then re-expands the cards the user had open before the reload —
without re-expansion, toggling the box would silently close the user's place
in the corpus `[synthesis]`.

Both experiences-list fetches (`refreshCorpus` and [`refreshCorpusSummaryFor`](../../../static/app.js))
use a shared query-string helper, [`app.js:_corpusListQuery`](../../../static/app.js), so the two
cannot drift apart and leave the list view and the experience count disagreeing about
what is visible `[synthesis]`. With "Show retired" unticked, the suffix is empty;
ticked, it appends `?include_retired=1` to the fetch URL.

The experience count displayed below the toolbar — "N experiences" — is calculated
by [`app.js:_corpusLiveCountText`](../../../static/app.js), which counts only
*active* experiences (those with `is_active !== false`). This is intentional: with
"Show retired" ticked, the list carries both active and retired roles, but the count
reflects only the roles that can reach a résumé during generation, so the count never
overstates the usable corpus size `[synthesis]`.

Retired role cards render with a `retired` CSS class (set by [`app.js:_renderCorpusSummary`](../../../static/app.js)
when `is_active === false`) and carry a `RETIRED` flag. The styling applies `opacity: 0.6` to
the entire card and a strikethrough to the company name, dimming the whole subtree
as a group (opacity composites children; no descendant can opt back out) — see
[`static/style.css:.corpus-card.retired`](../../../static/style.css). The action button
on a retired card's detail view becomes **Restore experience** (calling [`app.js:restoreExperience`](../../../static/app.js),
which PUTs `{is_active: true}` to the experience), replacing the usual Soft-retire action.
Restoring a role resurrects only the role itself; bullets the user had retired individually
remain retired `[synthesis]`.

## Smart landing

After a user is selected, [`app.js:_landingTab`](../../../static/app.js) fetches
`/api/users/<u>/experiences` and returns `'corpus'` when the corpus is empty (zero
experiences) else `'tailor'` — so a brand-new user lands on onboarding and a returning
user lands straight on the wizard `[synthesis]`. It is deliberately side-effect-free
(it must not seed the corpus-loaded guard). On error it falls back to `'tailor'` to avoid
stranding mid-onboard. `goHome` deselects the user, then re-resolves through the same
`_landingTab` (the single source of truth for "home") so the logo click and a cold start
show the same view.

**Detecting stale landings during async flows.** While `onUserSelect`
([`app.js:onUserSelect`](../../../static/app.js)) awaits for config and landing
computation, an explicit user navigation (tab click calling
[`switchTopTab`](../../../static/app.js)) can race ahead. To prevent the stale
landing decision from flip-flopping the tab back out from under the user, `onUserSelect`
snapshots a navigation-generation counter ([`_navGen`](../../../static/app.js))
before the awaits and checks it after; if an explicit tab switch bumped the counter
during the awaits, the stale side effects (`_armHelpTour`, `_activateTab`,
`_maybeFireTourStop`) are skipped but state work continues ([`app.js:onUserSelect`](../../../static/app.js)
`[synthesis]`).

**The same shape, on the status/history axis (item 31).** `_navGen` deliberately does
not cover status writes, and `onUserSelect`'s tail could resolve *after* a different
action had already set a more meaningful status (a refinement's `ERROR`) and recorded
its own history entry — overwriting it with a generic `READY` and wiping the record.
[`app.js:setStatus`](../../../static/app.js) now bumps a second counter,
`_statusGen`; `onUserSelect` snapshots it before its awaits and skips **both** the
status write and the history reset when a newer status landed meanwhile. The
mechanism was capability-proven with a deterministic `page.route()` probe, and the
post-fix rerun showed the stale write suppressed entirely — no `READY` entry at all
(`040b665`). The harness half of the same fix is `UserPicker.SELECT_READY`
(`#userSelect[data-user-select-ready]`,
[`ui_pages/selectors.py`](../../../ui_pages/selectors.py)): the attribute is removed
synchronously before the first await and set **last**, after the guard has run, so a
settle wait can neither observe a stale "ready" from a prior selection nor race ahead
of the cascade `[synthesis]`.

`switchTopTab` also cancels any in-flight smooth-scroll animation by
invoking the raw scroll primitive ([`_scrollRestoreNative.scrollTo`](../../../static/app.js))
to prevent viewport drift when an explicit navigation is issued while a smooth scroll
from a prior action is still animating `[synthesis]`.

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
mirrors `Step N of 6 · <label>` into the floating bottom statusbar, and — except when
called with `{scroll:false}` — scrolls the active panel into view ([`app.js:_wizardRender`](../../../static/app.js))
`[synthesis]`. The `scroll` option suppresses the scroll-to-active-panel behavior when a stale
landing decision would otherwise move the viewport away from where the user has explicitly
navigated ([`wizardInit`](../../../static/app.js) / [`_wizardRender`](../../../static/app.js) opts param). Forward motion is gated by
[`app.js:_wizardReachable`](../../../static/app.js): step ≥ 2 needs a successful analysis
(`lastContextPath`), **step 5 needs a frozen composition** (`_compositionFrozen`), step 6
needs a generation (`lastResumePath`) `[synthesis]`.
[`app.js:wizardGoTo`](../../../static/app.js) lazy-loads on entry — `loadComposition()` on
step 3, `_loadTemplatePicker()` on step 4.

**Step 5's gate is a hard gate, and its condition is the server's** (Epic A item 20).
Step 5 previously opened on nothing but a context path, so a rail click that skipped
Compose reached Generate with no `approved_composition` and the retired full-LLM
`generate()` fired underneath Step-5 copy promising deterministic assembly. The
condition is now exactly "the server will assemble this deterministically" —
[`hardening.py:frozen_composition_doc`](../../../hardening.py), the same predicate
`/api/generate` applies (see [[corpus-to-output-reach]]) — and **not** the weaker
"Save-and-continue completed", which would still admit runs the server refuses. The
client never re-derives it: `_compositionFrozen` carries the server's answer from both
of its setters (below). A candidate whose analyze-time `career_corpus` snapshot is empty
is locked out of Step 5 by design, and is not walled in — steps 1–4 stay reachable off
`lastContextPath` alone, so Compose is one click away. Step 6 stays gated on
`lastResumePath` alone so an already-generated run remains downloadable even when its
freeze state can't be recovered ([`app.js:_wizardReachable`](../../../static/app.js)).

A locked step now says **why**. [`app.js:_wizardLockReason`](../../../static/app.js) is
the single message source for both refusals a locked step can produce — the toast
[`wizardGoTo`](../../../static/app.js) raises on an attempted navigation, and the `title`
[`_wizardRender`](../../../static/app.js) sets on the greyed rail button (which
previously had its tooltip *removed*, leaving the lock unexplained). Step 5's reason
names Compose specifically rather than inheriting the generic "Run ANALYZE first",
because its lock is a flow requirement, not a missing analysis `[synthesis]`.

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
`#composeBgChip` makes the in-flight background work visible rather than silent; as
of sprint A2 `_markComposeBgReload` takes an **optional label**, so the chip names
whichever leg of the cascade is running instead of always reading "Updating
suggestions…". The label list (`_composeBgLabels`) is explicitly a *parallel,
presentational* structure — `_composeBgReloads` remains the only thing that sets or
clears `data-compose-bg-pending`, and a call site passing no label increments exactly
as before ([`app.js:_markComposeBgReload`](../../../static/app.js)). Decrements
remove **their own** label by `lastIndexOf` rather than popping, because the arrival
volley overlaps and decrements do not arrive in increment order.
Gap-fill proposals render per-role with accept/retire;
[`app.js:_renderGapFillControls`](../../../static/app.js) also exposes an
always-visible "Regenerate suggestions" control that re-fires the same draft route
on demand, excluding (route-side) any key already retired or already accepted so a
decided-on proposal never resurfaces.

**The "Composing…" wait gate (Epic A, sprint A2).** `wizardGoTo(3)` makes the Compose
panel visible at the moment the background volley *starts*, not when it finishes — so
the step read as done while cards were still being torn down and rebuilt underneath.
[`app.js:_holdComposingBusy`](../../../static/app.js) raises a visible wait state
across that window, reusing the two idioms already in the file rather than inventing a
third: `_setBusy` (the app-wide "don't navigate away" banner, text "Composing your
tailored résumé") and the analyze/generate in-panel block (`#composePending`, on the
same `.analysis-pending` shape as `#analysisPending` / `#generatePending`).

The gate **reads** the two signals
[`ui_pages/selectors.py`](../../../ui_pages/selectors.py) already encodes
(`Compose.READY` = `#composeList[data-compose-ready]`, `Compose.SETTLED` = that
`:not([data-compose-bg-pending])`) and deliberately redefines neither. The one
guarantee it adds is **ordering**:
[`app.js:_flushComposeSettleWaiters`](../../../static/app.js) runs *synchronously,
immediately before* whichever DOM mutation makes `SETTLED` observable, so a reader
that observes `SETTLED` can never also observe the overlay still up. Widening
`SETTLED` to include the banner was considered and rejected in writing — it would
invert the contract and break `test_20260722_compose_bare_reload_settle.py`, which
observes an unsettled state on purpose (`ui_pages/selectors.py`'s own comment records
this) `[synthesis]`.

Three details are load-bearing and easy to get wrong:

- The hold is raised only when the navigation actually took **and**
  `_composeApplicationId != null`. `loadComposition` is `async`, so its
  `_composeApplicationId == null` early return is the one exit with no `await` before
  it — it completes (flushing an empty waiter list) before the hold would be raised,
  which would strand the banner until its cap. The commit records this as closing a
  logic hole, **not** a fix to an observed failure: no live path was found where
  `lastContextPath` is truthy while `_composeApplicationId` is null there (`2a0b37a`).
- `submitClarifications` / `skipClarifications` end with their own `_setBusy(false)`
  belonging to an *earlier* phase of the same click, so both now route through
  [`app.js:_clearBusyUnlessComposing`](../../../static/app.js), which no-ops while any
  hold is live.
- The hold is bounded by `_COMPOSE_SETTLE_CAP_MS` (20 s) so a POST that never reaches a
  terminal render cannot strand the banner over a usable page. Past the cap the panel
  reads as done while the render may still cascade — a **declared, unquantified**
  tradeoff, filed as Deferred in
  [`docs/dev/blast-radius/compose-wait-ux.md`](../../../docs/dev/blast-radius/compose-wait-ux.md),
  not an unnoticed one.

Selectors added alongside it (values only, no contract change to READY/SETTLED):
`Compose.PENDING`, `BUSY_BANNER`, `BUSY_BANNER_TEXT`, `SKILL_PIN`, `BULLET_EDIT`,
`BULLET_APPROVE` ([`ui_pages/selectors.py`](../../../ui_pages/selectors.py)). The same
sprint moved the skills pin/drop affordances from glyph buttons to the word-button
idiom the bullet rows already use — the `.skill-pin` / `.skill-drop` **classes are
kept**, because `Compose.SKILL_DROP` selects on them and nothing selected on the
glyphs — and made in-place Edit available on *every* compose bullet rather than only
`is_pending_review` ones, surviving approval; the modal subtitle branches, because on
an already-approved bullet the corpus-wide effect is no longer self-evident and has to
be said before the user commits to it.

**Freezing on Save-and-continue.** `saveCompositionThenNext`
([`static/app.js`](../../../static/app.js)) POSTs the collected composition state
with `freeze: true`; the server resolves it into `approved_composition` — a
resolved JSON-Resume snapshot plus a `meta.sartor` provenance block — via
`corpus_to_json_resume.freeze_approved_composition`. `_compositionFrozen` then makes
Step 5's copy state-aware: [`app.js:_renderGenerateStepCopy`](../../../static/app.js)
shows one of two copy blocks (`#generateStepCopyFrozen` /
`#generateStepCopyLegacy`) depending on whether Generate is about to run a real
LLM call or deterministically assemble the frozen content — so the app never
claims a determinism guarantee it isn't about to honor `[synthesis]`. Since item 20
that same flag also **gates the rail** (above), which is why neither of its two
setters is a client-side guess:

- **In-session**, [`app.js:_postComposition`](../../../static/app.js) returns the
  freeze response's `frozen` field rather than a bare "the POST succeeded", and
  [`saveCompositionThenNext`](../../../static/app.js) assigns from it. A
  `freeze: true` save can land `200` and still write a document `/api/generate`
  refuses to assemble; the guard's other exits (no application / no context path,
  e.g. a degraded resume with no live context file) still read false, and an HTTP
  failure still throws.
- **On resume**, [`app.js:resumeApplicationIntoWizard`](../../../static/app.js)
  reads `has_frozen_composition` off the resume payload
  ([`blueprints/applications.py:_pre_generate_hydration`](../../../blueprints/applications.py)).
  It previously reset to a conservative hard `false` — harmless while Step 5 was
  ungated, a lock-out the moment it wasn't. Absent field still reads false, so a
  degraded resume and every pre-freeze-era application stay honest `[synthesis]`.

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
localStorage seam (the durable string form; the UX suite names it
[`ui_pages/selectors.py:Help.SEEN_PREFIX`](../../../ui_pages/selectors.py)), wrapped so a
throwing store reads as "not seen"
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
- [[corpus-to-output-reach]] — how composition overrides reach the generated document, and the one `frozen_composition_doc` predicate Step 5's rail gate shares with `/api/generate`.
- [[context-set-contract]] — the `approved_composition` key the freeze writes and the rail gate reads.
- [[career-corpus]] — the user-facing guide to the career corpus and soft-retire.
- [[tailoring-a-resume]] — the user-facing walk through the same six steps.
- [[diagnostics-console]] — the localhost console that ports this help primitive.
