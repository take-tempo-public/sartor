# paged.js preview-render engine — design spike

> **Purpose:** a timeboxed design/spike document for the paged.js render-engine
> replacement (B.13) — the current-state fidelity gap, what a swap would change,
> an explicit scope fence, and bounded de-risking tasks. This is a **spike doc
> only**: no product code, no dependency change, no `PROMPT_VERSION` bump ships
> on this branch.
> **Audience:** dev (the agent/owner who eventually slots and executes the
> replacement sprint).
> **Authoritative for:** the scope fence (preview-only, PDF untouched) and the
> spike task list below. Defers to
> [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) "paged.js preview-render
> fragility — contained, not eliminated" for the original fragility diagnosis,
> and to [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.9 / §Post-public for
> scheduling. On conflict, `RELEASE_ARC.md` governs scheduling; this doc
> governs the spike's technical shape.
>
> **Status (2026-07-10):** design-spike only, written per the owner's
> 2026-06-29 decision to pull B.13 pre-public but keep it **off** both the
> v1.0.8 blueprint theme and the v1.0.9 docs theme
> ([`RELEASE_ARC.md`](RELEASE_ARC.md):1227-1230). **Not built in v1.0.9** — see
> §5.

---

## 1. Current-state fidelity gap

The in-app live preview (β.4, [`docs/PRODUCT_SHAPE.md` §5.3](../PRODUCT_SHAPE.md))
renders a résumé/cover-letter as discrete Letter-sized "page cards" inside a
sandboxed iframe, using the vendored **Paged.js v0.4.3** polyfill
(`static/vendor/paged.polyfill.js`, MIT license — first line of the file
carries the version stamp). The polyfill is injected by
`_inject_paged_polyfill()` / `_PAGED_PREVIEW_INJECTION` in
[`blueprints/templates.py`](../../blueprints/templates.py):406-508, called from
four preview routes in that module (`grep -n _inject_paged_polyfill
blueprints/templates.py` → lines 1133, 1244, 1354, 1436). The frontend wiring —
the `#livePreviewFrame` (Step 4 Template) and `#outputPreviewFrame` (Step 6
Output) iframes, both `sandbox="allow-scripts allow-same-origin"` — lives in
[`templates/index.html`](../../templates/index.html):412-556, and the
page-count chip (`_wirePreviewPageCount` / `_updatePreviewPageCount`) in
[`static/app.js`](../../static/app.js):8966-9010.

**What's wrong today**, per the standing diagnosis in
[`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) ("paged.js preview-render
fragility — contained, not eliminated") and
[`docs/dev/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) (the "paged.js
polyfill 'Cannot read getBoundingClientRect of null'" entry in the Archive):

- The vendored polyfill throws internally on certain content shapes: an
  **async** `Cannot read getBoundingClientRect of null` (from its own
  un-`catch`-ed `await previewer.preview()`, `static/vendor/paged.polyfill.js`
  ~L33239) and a **sync** `node.getAttribute is not a function` (an off-chain
  layout pass). `feat/template-pagination` (v1.0.5) **contained** both by
  disabling the polyfill's auto-run (`window.PagedConfig = { auto: false }`),
  driving `new Paged.Previewer().preview()` itself inside `try/catch` +
  `.catch()`, and narrowly swallowing the two known paged-origin errors via
  `window.addEventListener('unhandledrejection'/'error', …)`
  (`blueprints/templates.py`:444-457). This is **suppression, not a fix** —
  the throws still fire inside the library on every affected render; the app
  just catches and ignores them. It is safe only because the render happens
  to complete correctly despite the throws, pinned by
  `tests/ux/regression/test_20260604_template_pagination.py` (asserts every
  bundled template paginates with no blank pages and a clean console — any
  *new/different* paged.js error is unconditionally NOT swallowed and WILL
  fail that test).
- **v0.4.x is the end of that library's release line** (effectively
  unmaintained upstream) — verifying current upstream status is itself spike
  task 1 below, not asserted here as settled fact.
- The iframe sandbox is `allow-scripts allow-same-origin` together, which
  "effectively neutralizes the sandbox per spec" (load-bearing comment,
  `templates/index.html`:420-435) — accepted only because the iframe content
  is our own generated HTML (corpus + persona template + injected polyfill),
  never user-supplied markup. A lighter architecture (host paged.js outside
  the iframe, message-pass the layout back) was noted as a future option
  against this same item and never built.
- Net effect on the user: pagination *works* today (no known blank-page
  regression across the four bundled personas), but the mechanism is fragile,
  the failure mode is "swallow and hope," and any content shape outside the
  test fixtures' coverage could regress silently past the suppression filters
  before the UX sentinel catches a *different* error message.

## 2. What swapping the engine would change — preview only

A replacement render engine would touch exactly three integration points, all
in the preview path:

1. `_inject_paged_polyfill()` / `_PAGED_PREVIEW_INJECTION`
   (`blueprints/templates.py`:406-508) — the injected `<script>`/`<style>`
   block that turns flowing HTML into discrete page boxes inside the iframe.
2. The `pagedjs_rendered` `postMessage` contract
   (`blueprints/templates.py`:460-489 → `static/app.js`:8966-9010) — whatever
   engine replaces paged.js must still report a page count back to the parent
   frame so the "Page N of M" toolbar chip keeps working, or that chip needs
   its own redesign.
3. The `.pagedjs_page` / `.pagedjs_page_content` DOM structure the pagination
   regression test asserts against
   (`tests/ux/regression/test_20260604_template_pagination.py`:109-161) and
   the CSS overrides that style the page-card look
   (`_PAGED_PREVIEW_INJECTION`'s `<style>` block, `blueprints/templates.py`:406-425).

Everything upstream of the iframe — the Jinja2 templates
(`personas/bundled/*.html` + `.css`), `render_html_string()` in
[`pdf_render.py`](../../pdf_render.py):185-210, the `@page` CSS rules the
personas already define — is engine-agnostic and would **not** need to
change, provided the replacement also honors standard CSS Paged Media
(`@page`, `page-break-*`/`break-*`) the way the personas are already
authored.

## 3. Scope fence — PDF export stays Playwright-native, untouched

**Explicit and load-bearing:** `pdf_render.render_pdf()` and
`render_cover_letter_pdf()` (`pdf_render.py`:90-182, 281-356) generate the
downloadable `.pdf` via Playwright's headless-Chromium `page.pdf()`, which
handles `@page` CSS **natively** — it does not load, and never has loaded,
the paged.js polyfill. The module docstring is explicit: *"The PDF render
path does NOT go through this helper — `pdf_render.render_pdf()` uses
Playwright's `page.pdf()` … Paged.js is browser-preview only"*
(`blueprints/templates.py`:501-503, echoed at `pdf_render.py`:1-35). A
replacement preview engine is therefore **entirely isolated from PDF
correctness** — the worst-case outcome of a bad spike or a bad rollout is a
degraded in-app *preview*, never a broken PDF download. Any future work in
this lane must preserve that isolation: the PDF path must not gain a paged.js
(or replacement-engine) dependency, and the preview path's engine choice must
not require changing `page.pdf()`'s `prefer_css_page_size` /
`print_background` invocation. `.docx` pagination is a separate, pre-existing
accepted limitation (Word lays out pages itself at open time — content-level
parity only, per D3, [`docs/PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md):343-350)
and is likewise out of scope here.

## 4. Risks, unknowns, and bounded spike tasks

The actual replacement is **not** built on this branch. The tasks below are
what the owner's future pre-public sprint should timebox to reach a build/no-
build decision, in rough execution order:

1. **Survey the current engine landscape.** Confirm paged.js's real upstream
   status as of the spike date (active fork vs. dormant; whether a
   community fork past v0.4.3 exists) and shortlist 2-3 real alternatives —
   candidates worth evaluating include an upgraded/forked paged.js, a
   different CSS-Paged-Media implementation (e.g. Vivliostyle-class engines),
   or a hand-rolled pagination pass using native CSS multi-column /
   `break-*` properties measured via `getClientRects()` (no polyfill
   dependency at all). Each candidate's license, maintenance activity, and
   bundle size are in scope; none of this is pre-decided by this doc.
2. **Reproduce the two known throws on a controlled fixture.** Build a
   minimal sparse-content and dense-content fixture pair that reliably
   triggers the `getBoundingClientRect`/`getAttribute` throws under current
   paged.js, so a candidate replacement has a concrete regression target
   (today's coverage — `test_20260604_template_pagination.py` — only proves
   the *current* four bundled personas render clean; it does not prove the
   throws are unreachable on other content shapes).
3. **Prototype the `postMessage` contract on one candidate.** Verify a
   candidate engine can report page count (or an equivalent signal) back to
   the parent frame without requiring `allow-same-origin`, which would let a
   future iteration drop that sandbox flag — closing the deferred
   "host paged.js outside the iframe" item from
   [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md).
4. **Measure fidelity against Playwright's own `page.pdf()` output** for the
   same JSON-Resume + persona combination — the acceptance bar from
   `docs/PRODUCT_SHAPE.md` §10 is "preview pagination renders with **zero**
   internal throws … across all four bundled templates on sparse + dense
   content," and the replacement should not regress preview/PDF visual
   parity (§3 above) in the process.
5. **Cost the migration.** Estimate: vendoring/licensing the new engine, CSS
   rework in the four bundled persona stylesheets (if the replacement's
   `@page`/`break-*` support diverges from paged.js's), the
   `_PAGED_PREVIEW_INJECTION` block rewrite, the `.pagedjs_page` DOM/CSS
   selector rewrite (test + style dependents), and whether the sandboxed-
   iframe architecture changes at all.

**Known unknowns going in:** whether any shortlisted alternative is
meaningfully more actively maintained than paged.js v0.4.x; whether a
hand-rolled measurement-based approach (no polyfill) is cheaper *and* as
fidelity-accurate as a library; and how much of the current CSS
(`page-break-inside: avoid` on `article`, `page-break-after: avoid` on `h2`,
per the v1.0.5 pagination fix) is paged.js-specific vs. standard CSS Paged
Media that transfers to any spec-following engine.

## 5. Recommendation

**Recommendation:** proceed with the replacement as a **deliberate, separately-
scoped render-engine project**, not a drive-by fix — consistent with the
existing `docs/PRODUCT_SHAPE.md` §10 disposition ("a deliberate, separately-
scoped render-engine decision … not a bugfix-branch drive-by"). The current
containment is stable enough (self-policing via the unconditional UX
sentinel — any new/different paged.js error fails the suite outright) that
there is no correctness fire to fight; the case for replacement is
maintenance risk (an unmaintained v0.4.x dependency) and long-term preview
fidelity, not a live user-facing bug. Task 1 above (survey the current
engine landscape) is cheap and should run first — it may change the
shortlist or even close this out as "paged.js is still the best option,
re-vendor a maintained fork" rather than a full engine swap.

**This is owner-slotted for its own pre-public sprint — it is explicitly NOT
built in v1.0.9.** Per
[`RELEASE_ARC.md`](RELEASE_ARC.md):1227-1230, B.13 was pulled pre-public from
the post-public 1.1.x epic series but kept off both the v1.0.8 blueprint
theme and the v1.0.9 docs theme; "owner to slot its own pre-public sprint."
This branch (`spike/pagedjs-design`) delivers **only** this design/spike
document — no code, no dependency, no `PROMPT_VERSION` change.
