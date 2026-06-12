# Changelog

All notable changes to callback. are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed — diagnostics-console chart + layout corrections (`fix/diagnostics-chart-corrections`)

Three `/_dashboard` defects from the v1.0.6 kickoff walkthrough harvest (Sprint
6.2; findings #11 + #12 + #13), plus the KW13 space-usage restructure. Front-end
+ deterministic-aggregation only — no LLM call, no `PROMPT_VERSION` bump, no new
route, no new dependency, no migration.

- **KW13 + #12 — panels now use the page width; the Calls table no longer
  horizontal-scrolls.** The detail surface was a cramped 560px right-hand side
  drawer, so the 10-column **Calls** (throughput) table overflowed with a
  horizontal scrollbar (#12). The drawer is replaced by a **full-width inline
  detail panel** rendered in the page flow beneath the tabs: the selected tile's
  detail block is moved into it from `#detailStore` (reusing the existing
  move-the-node + lazy-`initCharts` machinery — only the destination changed) and
  scrolled into view. Every detail (Calls, heatmap, health, reliability, pareto,
  trace, all charts) now renders at full width (KW13), and the Calls table fits
  with no scroll (a defensive `word-break` on its cells guards narrow viewports).
- **#13 — latest-trace bars now render and scale to the longest span.** Two
  problems compounded into "bars look empty": the `.wf-bar` was a `<span>` left
  at `display:inline`, so its `width` never applied and **every bar rendered at
  0px**; and the width was each span's share of the run *total*, so even once
  visible a short span (e.g. a 4s `clarify` beside a 60s `analyze_synthesis`) was
  a sliver. Fix: `.wf-bar` is now `display:block` with a 2px `min-width` floor,
  and `dashboard/routes._run_trace` emits `bar_pct` scaled to the **longest
  span** (max → 100%); the template binds bar width to `bar_pct`, keeps the
  share-of-total `pct` on hover, and keeps `latency_ms` as the absolute truth.
- **#11 — cost-by-kind chart tooltip is now unambiguous.** The walkthrough read
  the cost chart's tooltip as "Total" but plotting the mean. It always plotted
  the **total** (`total_cost_usd = sum`, unchanged since the console was built);
  the confusion was an unlabeled default tooltip beside a `mean $` table column.
  The chart now carries an explicit tooltip naming the value as the total with
  count + mean for context (e.g. `generate — total $0.02340 · 12 calls · mean
  $0.00195`). Data unchanged.
- Covered by a deterministic unit test for `bar_pct`
  (`tests/test_dashboard_routes.py::TestRunTrace`) and a UX-tier regression
  (`tests/ux/regression/test_20260611_diagnostics_chart_corrections.py`): the
  detail panel uses the page width with no horizontal overflow on Calls, the
  trace bars scale to the longest span, and the cost tooltip names total + mean.
  The dashboard POM + selectors moved from `drawer` to `detail-panel` handles.

### Fixed — wizard-flow polish: follow-up-question auto-scroll + copy alignment (`fix/wizard-flow-polish`)

Two small Output-panel polish fixes from the v1.0.5 walkthrough harvest
(Sprint 6.1, final row; findings KW5 + KW8):

- **KW5 — auto-scroll.** Clicking the post-generation **"Get follow-up
  questions"** button rendered the iteration questions *below the fold*, so it
  looked like nothing happened. `runIterateClarify()` now scrolls the revealed
  `#iterateClarifyArea` section into view in its success path (reusing the
  existing `scrollIntoView({behavior:'smooth',block:'start'})` idiom), covering
  both the questions and the "no follow-up questions surfaced" branches.
- **KW8 — copy alignment.** The button label and section divider used
  "interview" wording inconsistent with the clarify vocabulary (the button's own
  tooltip already said "clarifying questions"). They now read **"Get follow-up
  questions"** and **"Follow-up clarification"**. The `#btnIterateClarify` id is
  unchanged, so selectors / page objects are unaffected. The tracker "Got
  interview" outcome status is a different concept and was left untouched.
- Front-end only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no migration. Covered by a UX-tier regression
  (`tests/ux/regression/test_20260611_wizard_flow_polish.py`): a cheap static
  copy guard plus a full analyze→generate→follow-up drive that verifies the
  scroll deterministically by spying on `scrollIntoView`. That drive needed two
  new UX stubs (`fake_generate_streaming` + `fake_clarify_iteration` in
  `tests/ux/stubs.py`) — the first UX test to exercise the generate route.

### Fixed — a detached cover letter is now persisted to its run row (`fix/run-cover-letter-persistence`)

Generating a cover letter via the Step-6 "+ Generate cover letter" button left
**no DB trace**: `ApplicationRun.generated_cover_letter_md` stayed empty even
after the letter was generated and downloaded (confirmed against the e2e
walkthrough run row, which had résumé md + bullets + titles + ATS json but no
cover-letter md). The detached route `POST /api/generate-cover-letter` wrote the
letter to disk and into the context file but never touched the database. (The
*other* path — `/api/generate` with `with_cover_letter=True` — already persisted
it; the gap was exclusively the detached, common-case route.)

- **Fix.** After writing the letter, the route now persists
  `generated_cover_letter_md` onto the **same** run row the résumé generation
  wrote to (identified by `context_set["application_run_id"]`), via a new
  surgical single-column write-back (`db.persist_run.persist_cover_letter_md` +
  the `app._persist_cover_letter_to_db` wrapper, mirroring
  `_persist_corpus_generation_to_db`). Corpus-backed mode only (legacy contexts
  without a run id skip it, as `/api/generate` does), and best-effort — a DB
  hiccup logs but never fails a letter the user already downloaded.
- **Why a dedicated helper, not `persist_corpus_generation`.** That function
  unconditionally writes `generated_resume_md = result.get("resume_content")`;
  a cover-letter result carries no résumé content, so reusing it would have
  *nulled out the already-saved résumé md*. The new helper writes one column and
  leaves the résumé md untouched.
- **Why now.** B.8 Part 2 (post-public, outcome-weighted recommend) will
  correlate interviews with the cover letters that earned them; rows generated
  now without the write-back can't be backfilled, so the signal is captured
  during v1.0.6 while real outcome data accrues.
- No LLM call (the persist module stays deterministic), no `PROMPT_VERSION` bump,
  no new route, no new dependency, no migration (the column already exists).
  Covered by a unit test (no-clobber surgical write,
  `tests/test_persist_run.py`) and a route test (run-row populated end-to-end,
  `tests/test_cover_letter_detached.py`). The architecture pipeline + data-flow
  diagrams were synced to show the new write-back.

### Fixed — Step-4 / Résumé-templates copy now matches the real bundled set (`fix/step4-template-copy`, #8)

Walk finding #8 asked whether the Step-4 template-chooser copy ("Same content,
different typography and layout") still describes the bundled templates
accurately. **Verified: yes** — the four bundled templates genuinely differ in
typography *and* layout (Classic/Modern are sans-serif, Spacious/Tech serif;
Modern carries a blue header band; Tech uses float-based two-column item rows;
margins, line-heights, heading treatments and accents all vary), so that Step-4
line is left unchanged.

The verification surfaced a stale **count**, fixed here. Migration 0005 curated
the bundled set from 5 → 4 at v1.0.0 (dropped Compact, renamed Hybrid Tech →
Tech), but the Résumé-templates settings copy still claimed "Five bundled
ATS-safe templates ship with the app." → corrected to "Four". The
`docs/bundled_templates_LICENSE.md` inventory (which still listed the
nonexistent `compact.docx` / `hybrid_tech.docx` and omitted `tech.docx`) was
corrected to the curated four.

- Copy/doc only — no LLM call, no `PROMPT_VERSION` bump, no new route, no new
  dependency, no DB change. The canonical count of 4 is already pinned at the
  data layer by `tests/test_bundled_templates.py`; the new UX regression
  `tests/ux/regression/test_20260611_step4_template_copy.py` guards the *copy*
  against drifting from the rendered bundled set.

### Fixed — Compose custom bullet order no longer reverts on reload for a no-recommendations experience (`fix/compose-order-no-recommendations`)

A saved custom Compose bullet order *visually reverted* after a Compose reload —
but only for an experience that had **no LLM recommendations**. The persisted
order was always intact (`composition_overrides.bullet_order` round-trips through
POST/GET `/composition`, and `generate()` honors it via `_stable_user_prefix`);
only the on-screen render regressed.

- **Root cause (render-only).** `_renderComposeCard` (`static/app.js`) routed a
  no-recommendations experience through `_dropoffPick`, which re-sorted the
  fallback bullets by **score** — discarding the saved order the GET had already
  applied (`get_application_composition` ranks bullets by `bullet_order` and
  stamps `in_custom_order`). The common path (recommendations present → bullets
  land in the `visible` set, preserving GET order) was unaffected.
- **Fix.** On the no-recommendations fallback path, when the experience has a
  saved order (`has_custom_order`) honor the GET-returned order (the
  `in_custom_order` bullets, already in saved sequence) instead of re-deriving a
  score sort. No backend change, no `PROMPT_VERSION` bump, no new dependency.
- Covered by a UX regression
  (`tests/ux/regression/test_20260611_compose_order_no_recommendations.py`) on a
  seeded no-recommendations experience; the companion
  `test_20260604_bullet_drag_reorder.py` continues to guard the common path.

### Added — add an alternative job title in Compose + pin it per-JD (`feat/compose-add-title`, #7)

In Step 3 (Compose) a user often realizes a *different framing* of a role fits
this JD. Until now they couldn't act on it in the wizard: the Compose titles
list was read-only, the only way to add a title was the separate Career-corpus
tab (which added it as a *non-eligible* alternate), and titles had **no** per-JD
selection at all — the generate LLM picked one by fit and the preview showed
official-or-first (walk finding #7).

- **Add a title, written into the corpus.** A "+ Add title" affordance on each
  Compose experience card writes a **sourced, immediately-eligible**
  `ExperienceTitle` (`source=user_added`, `truthful_enough_to_use=1`,
  `is_pending_review=0`) via the existing `POST /api/experiences/<id>/titles` —
  a first-class corpus item, **not** a context-only override. It appears at once
  as a selectable option for this résumé.
- **Pin which title this JD uses.** Each card's titles are now a radio group; the
  pick persists as `composition_overrides.pinned_title_ids`
  (`{experience_id: title_id}`), collected by the existing debounced composition
  autosave. Only an explicit pin is sent (mirrors `bullet_order`'s
  `data-custom-order`), so an untouched default never persists a pin or busts the
  analyze→generate cache.
- **Honored in both the preview and the generated download.** The live preview /
  corpus render (`build_json_resume_from_corpus`) resolves the title as
  **pin → official → first**; generate marks the chosen `<eligible_title
  pinned="true">` in the corpus block and a new `<corpus_mode>` rule requires the
  model to use it as that experience's `chosen_title_id` and heading (dates stay
  immutable). Because generate reads a **frozen** corpus snapshot, the
  composition save **re-syncs** `career_corpus[exp].eligible_titles` from the DB
  for pinned experiences, so a title added after analyze still reaches generate.
- `PROMPT_VERSION` → `2026-06-11.1` (the `<corpus_mode>` rule changed). Per-JD
  pin scope was a user-approved extension of the #7 row.
- Covered by route/unit tests (`tests/test_career_corpus_routes.py` add contract;
  `tests/test_application_routes.py` `TestCompositionTitlePin` persist/validate/
  re-sync; `tests/test_corpus_to_json_resume.py` `TestTitlePin`;
  `tests/test_corpus_mode_prompt.py` `TestTitlePinEmission` + the rule) and a UX
  regression (`tests/ux/regression/test_20260611_compose_add_title.py` — add a
  title, pin it, persist across a Compose reload). No new dependency.

### Added — prior applications resume from their furthest step + editable cards (`feat/prior-app-resume-robustness`, #4 + #24)

The v1.0.5 click-to-resume only offered "Resume in wizard" when a résumé had
been generated, so an application abandoned at analyze / clarify / compose was a
dead card. And prior-app cards never showed which job they were for — the
company was never captured and the proposal pill read an opaque "N pending"
(walk findings #4 + #24).

- **#4 — resume from the furthest step with data.** `_build_resume_state`
  (`app.py`) now classifies a `target_step` (1 analyze · 2 clarify · 3 compose ·
  6 download) from the rediscovered iter-0 context file — `llm_analysis`,
  `clarification_questions`/`clarifications`,
  `llm_recommendations`/`composition_overrides`, generated résumé — and ships the
  per-step payload. `resumeApplicationIntoWizard` (`static/app.js`) dispatches on
  it: Steps 1–3 rehydrate the analysis panel (and, for Step 2, the saved clarify
  Q&A) **without re-spending** `/api/clarify` or `/api/generate`; Step 6 is the
  unchanged generated-résumé path. The Resume button is now offered for every
  analyzed application, not only generated ones.
- **#24 — editable cards + legible pill.** Job title and company are now
  user-editable in the app-detail modal (save-on-blur via the new DB-only
  `PUT /api/applications/<id>/meta`, mirroring `/notes`), so a card can finally
  carry the job it's for (`Application.company` was never populated). The
  proposal pill reads **"N to review"** (was the opaque "N pending").
- Covered by route tests (`tests/test_application_routes.py` — `target_step`
  classification + `/meta`) and a UX regression
  (`tests/ux/regression/test_20260611_prior_app_resume_robustness.py` —
  analyze-only resume to Step 1; editable company + relabeled pill).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — UI + a
deterministic DB-only route; no LLM call added).

### Fixed — "Continue to Clarify" no longer asks clarify/skip twice (`fix/clarify-double-question`, #6)

The analyze→clarify gate presented the clarify-vs-skip choice **twice**. The
analysis panel already shows it ("Continue to Clarify →" / "Skip to Compose →"),
but "Continue to Clarify" only navigated to Step 2 and showed the
`#clarifyStartRow` row — a second "Get clarifying questions / Skip" prompt for a
user who had already chosen to clarify. The onboarding walk (finding #6) flagged
this as feeling broken.

- **One action:** "Continue to Clarify →" now navigates to Step 2 **and** fetches
  the questions directly (new `continueToClarify()` wrapper). A pending indicator
  fills the panel while `/api/clarify` runs; the row is restored on failure so
  the user can retry. An idempotency guard skips re-fetching when the current
  analysis already produced questions (back-nav / re-click never re-spends the
  LLM call).
- **Untouched paths:** a direct rail click / back-nav into Step 2 still shows the
  `#clarifyStartRow` row as its single, legitimate prompt; the post-question
  `Skip` and `Submit answers, continue →` controls are unchanged. The KW4
  `merge:true` / `merge:false` answer semantics are preserved byte-for-byte
  (this fix only changes how clarify is *entered*).
- Regression-tested in the UX tier
  (`tests/ux/regression/test_20260611_clarify_no_double_prompt.py`): the CTA
  renders questions with no second click and `#clarifyStartRow` is hidden.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — front-end flow
only; no LLM route or template touched).

### Fixed — iterate-round clarify answers no longer drop analyze-round answers (`fix/clarify-generates-bullets`, KW4)

`/api/answer-clarifications` (`submit_clarifications`) did a whole-map replace
of `context["clarifications"]`. The iteration interview submits **only** its own
textareas (`_collectIterateClarifyAnswers`), so a 2nd-round submit wiped the
analyze-round answers from the new context file — and `generate()` at iter≥1
lost them as first-person ground truth (the JS comment claimed "merges by id";
the route did not). Surfaced 2026-06-10 while building
`feat/outcome-capture-complete`; this is the mechanism behind the KW4 report
that "a later clarify round adds nothing".

- **Merge by id (default):** the route now merges answers into the existing map
  (`merge` defaults to `True`), so a later round preserves earlier answers. The
  deliberate skip-clear path passes `merge:false` to replace/clear, and the
  three JS call sites (`submitClarifications`,
  `submitIterateClarificationsAndGenerate`, `skipClarifications`) declare their
  merge intent explicitly. Whitespace-only answers are dropped and cannot
  un-answer a prior key — use `merge:false` to clear.
- **Candidate-memory mirror unaffected** — the additive DB upsert is keyed by
  question and persisted independently of the context-map merge.
- Regression-tested across two clarify rounds (`tests/test_app_clarify.py`).

No new dependency. No prompt change (`PROMPT_VERSION` unchanged — only the data
`generate()` reads is corrected, not the prompt template).

### Added — outcome capture completed + candidate memory goes live (`feat/outcome-capture-complete`, B.8 Part 1 + KW7)

The Sprint 6.0 kickoff walk found the Applications block showing "no
applications" after a completed tailor+download, and candidate memory empty
after clarify+interview (KW7). Diagnosis against the walkthrough evidence:
the `Application` row **was** created (at analyze) but the UI never
re-rendered the block after user-select; worse, nothing in the UI could ever
set `status='submitted'`, and the outcome buttons render only on submitted
cards — so the whole outcome funnel was unreachable. Candidate memory was
designed-but-unwired: the table, read route, panel, and promote path all
existed, but no code wrote `clarification` rows from the wizard.

- **KW7 fix (UI sync):** `refreshApplications()` now fires when analyze
  creates the row and when generation updates it — the block tracks the
  wizard instead of its pre-analyze snapshot.
- **Outcome funnel entry (B.8 Part 1):** draft cards gain a **Mark
  submitted** action, and Step 6 surfaces a "Submitted this application?"
  nudge after a successful download — the moment the user takes the file to
  go apply. Outcome buttons (interview / rejection / withdrew) are unchanged
  and now reachable. **Data-model decision (user-approved 2026-06-10): lean
  single-status, `interview` is terminal** — the product's signal is "this
  résumé got a callback", not job-hunt bookkeeping past that point. No
  schema change; the v2 `ApplicationOutcome` event table remains open.
- **Queryable:** `GET /api/users/<u>/applications` accepts a validated
  `?status=` filter (single or comma-separated) — the programmatic query
  surface for the B.8 Part 2 learning layer — and the Prior-applications
  panel gains a status filter select driving it.
- **Candidate memory write path:** `/api/answer-clarifications` now mirrors
  answered Q&A into the `clarification` table (additive upsert keyed on
  candidate + application + normalized question; promoted rows never
  clobbered; legacy file-only contexts unaffected; best-effort — a memory
  failure never fails the submit). The memory panel populates live after
  clarify/interview answers, and the existing promote-to-bullet path is now
  reachable for wizard-sourced answers. LLM `context_probe` questions file
  under `experience_probe` (the DB kind enum predates them); `target_gap`
  keeps the provenance.

No new dependency. No prompt change (`PROMPT_VERSION` unchanged).

### Fixed — generate() can no longer silently alter or duplicate job dates (`fix/generate-date-grounding`, KW6)

The Sprint 6.0 kickoff walk caught the iteration regenerate "reconciling"
employment dates: it reordered experiences by JD relevance and rewrote one
role's range onto its neighbor (two titles sharing `2016 – 2018` while
`2012 – 2016` vanished), though the corpus was correct. Root cause: the
corpus-mode prompt contract made *bullets* immutable but never mentioned
*dates*, and every deterministic check scanned bullet lines only — heading
date ranges were ungoverned on both sides.

- **Prompt** (`analyzer.py`): new SYSTEM_PROMPT ALWAYS/NEVER rule (dates are
  immutable facts; reordering never rewrites them), the `<corpus_mode>`
  contract now names the `dates` attribute immutable ground truth, and the
  GROUNDING CHECK gains an OK / NOT-OK worked date pair.
  **`PROMPT_VERSION` `2026-06-01.4` → `2026-06-10.1`** (same commit). Smoke
  eval: no grounding regression (mean 4.70, all fixtures pass; see
  `evals/TUNING_LOG.md` 2026-06-10 entry).
- **Guard** (`hardening.compute_date_grounding`, deterministic, warn-only):
  heading date ranges in the generated experience section must be a
  sub-multiset of the corpus's true ranges — catches both alteration and
  duplication. Both generate routes surface flags as plain-language
  `proofread_notes` warnings (no frontend change needed) plus a structured
  `date_grounding` response field; the LLM output itself is never mutated and
  generation is never blocked. Validated against the real walkthrough chain:
  the corrupted iteration draft flags, the clean fresh draft passes.

No new dependency.

### Docs — Sprint 6.0 kickoff-walk harvest recorded (`docs/sprint6-walkthrough-findings`)

The first v1.0.6 kickoff walkthrough completed end-to-end (sprint-1 blockers
cleared the hard stops) and produced **11 findings (KW1–KW13)**, now recorded in
`docs/dev/RELEASE_ARC.md` §Phase 4.5 under Sprint 6.0 and triaged into the
existing 6.x buckets: three correctness defects (KW6 generate-date integrity,
KW7 applications/memory not updating → B.8 gate, KW4 clarify-no-bullets) join
Sprint 6.1 as new branches; KW2 bulk accept-all-pending joins 6.3; KW1 confirms
the 6.4 smart-landing; KW3/KW9/KW10 fully spec the 6.5 help primitive
(first-view modal + persistent (i)-circle) and the new-user first-run modal
sequence; KW13 panel redesign joins 6.2. Docs only — no code change.

### Fixed — onboarding E2E-walkthrough blockers, sprint 1 (`fix/onboarding-e2e-blockers`)

Five first-run onboarding issues surfaced by the end-to-end walkthrough:

- **Résumé ingest silently did nothing (the critical one).** A table/column-laid-out
  `.docx` parsed to empty text because `parser._parse_docx` read only body
  paragraphs, never table cells — so extraction got nothing and zero experiences
  landed. The ingest route nonetheless returned `201` with the error buried in the
  body, and the uploader showed a green "ready" toast over an empty corpus and never
  refreshed the list in place. Now: the parser walks the document in order and reads
  table cells (recursing into nested tables, deduping merged cells); the route
  returns `422` when a parse/extract failure lands nothing; and the uploader
  refreshes the corpus in place on success and shows an honest "No experiences found"
  warning (not a success toast) on a zero result.
- **User-selection box collapsed on an accidental header click**, stranding
  first-time users with the dropdown hidden. It is now locked open
  (`.not-collapsible`, no chevron/pointer) until a user is selected.
- **"New user" button was a confusing toggle.** It now reveals the form (not
  toggles), hides itself, and focuses the username field; a **Cancel** button
  restores it.
- **Website/LinkedIn URL boxes were ambiguous and intolerant of format.** Added a
  tolerant client-side format checker (normalizes a bare `linkedin.com/in/you` to
  `https://`, flags genuine non-URLs), clearer placeholders, and a matching tolerant
  `validate_config` server-side (accepts bare dotted hosts; still rejects `not-a-url`).
- **Wizard back-navigation** is acknowledged as missing but **deferred** to the
  monolith→blueprints split (RELEASE_ARC Phase 4.8); no behavior change this branch.

No `PROMPT_VERSION` change and no new dependency.

### Fixed — profile URLs without a scheme no longer silently fail to fetch (`fix/normalize-url-scheme`)

A site address pasted without `http://`/`https://` (e.g. `github.com/you`) made
`requests.get` raise `MissingSchema`, which `scraper.fetch_url_content` caught
and swallowed as an empty result — the URL was silently dropped from the LLM
profile context with no user-visible error. The LinkedIn/Website fields are
`type="url"` (browser-enforced scheme), but the Portfolio URLs textarea has no
such guard, so bare hosts slipped through. `scraper._ensure_scheme()` now
normalizes at the fetch boundary: a bare host gets `https://` prepended; an
explicit scheme (`http://`, `https://`, …) is left untouched. One fix covers
all three URL sources since they all flow through `fetch_url_content`. No
`PROMPT_VERSION` change and no new dependency.

## [1.0.5] — 2026-06-07

The UI/UX redesign + the diagnostics/tuning console — establishes the design
system. **Local tag** (the project stays local-only until the user-owned v1.1.0
public release). Highlights: WYSIWYG (live preview = downloaded résumé), the
Step 6 (Output) redesign, cover letters in `.docx` / `.pdf` / `.md`,
prior-application click-to-resume, user-driven Compose bullet ordering, a
Playwright UX regression suite, the template-pagination fix across all four
bundled templates, the deterministic L0 grounding metric, and the tabbed
diagnostics + tuning + annotation console — including the browser-driven
"finish the faceplate" interactive tuning loop and the standalone, LLM-free
corpus-seed export. **No `PROMPT_VERSION` change across the stream** (no
persona-constant edit landed) and **no new runtime dependency**. Deferred to
later releases by design: the calibrated grounding layers (B, pre-v1.1.0), the
no-recommendations Compose-render order edge case, and the R1-Phase-2
architecture-doc debt.

### Added — standalone one-click corpus-seed export (`feat/seed-export-button`)

Producing a corpus `seed.json` is now a one-click, **LLM-free** action in the browser.
Previously the only in-browser trigger was bundled inside the **paid** Annotate-tab
bootstrap (`POST /api/annotation/bootstrap`, ~70s/JD of Sonnet/Haiku spend); the only
no-cost path was the `python -m scripts.export_corpus_seed --user <name>` CLI. This adds
a dedicated no-cost surface. No `PROMPT_VERSION` bump (no prompt touched) and no new
dependency.

- **`POST /api/annotation/seed/export`** (`app.py`, localhost-only, synchronous JSON —
  no SSE) — reads the live DB via `scripts.export_corpus_seed.export_seed` (read-only, no
  model calls) and writes `evals/fixtures/real/<slug>/seed.json` (the source the eval
  runner's `--seed` path and the grounding backfill score against). Mirrors the score
  route's guard structure: `_is_localhost_request()` + the security trio
  (`_safe_username()` + `secure_filename()` + `_within(seed_path, ANNOTATION_ROOT)`).
  Unknown user → 400; a config-only user with no provisioned corpus → 409 (same
  needs-onboarding shape as `/api/analyze`). Default slug `<user>-bootstrap` so an
  exported seed lands where a later bootstrap / `runner.py --seed` already looks.
- **Annotate-tab "Export seed (no LLM)" button** (`dashboard/templates/dashboard.html`) —
  sits in the bootstrap section's actions row next to the paid "Run bootstrap"; reuses the
  same candidate-username / fixture-slug inputs and reports the written path + corpus
  counts. A plain fetch + status line (no SSE) since the export is fast and synchronous.
- **`_write_seed_json(fixture_dir, seed)`** (`app.py`) — factored the seed.json dump out
  of the bootstrap route so the bootstrap and standalone export share one canonical writer
  (no duplicated `json.dumps` shape). Bootstrap behavior is byte-identical.

### Docs — tuning-loop discoverability (`docs/tuning-loop-discoverability`)

Step 4 (docs only) closes the "finish the diagnostics faceplate" arc: every durable
doc and the in-app entry points now point at the now-interactive `/_dashboard`
console instead of the pre-arc read-only world. No code, no `PROMPT_VERSION` bump,
no new dependency.

- **`evals/README.md`** — new "The in-browser tuning console (`/_dashboard`)" section
  walks the four shipped surfaces as one browser-driven loop (produce → annotate →
  grounding-score → run eval → A/B → read deltas), ending at the irreversible manual
  **promote**; it is the dev-doc home for the console walkthrough.
- **`docs/walkthrough.md`** — a short "See also" flag + link telling
  users/maintainers the local diagnostics & tuning console exists and that the LLM
  prompts can be tuned there (content lives in `evals/README.md`, not embedded here).
- **`docs/dev/GROUNDING_METRIC.md`** — the deferred-calibration ("B") note now records
  that the label-*producing* loop is browser-driven (no longer CLI-only); the
  calibration itself stays the open B work.
- **`docs/dev/RELEASE_ARC.md` / `RELEASE_CHECKLIST.md`** — merge hashes backfilled
  (`feat/run-eval-from-console` `3a91bea`, `feat/tuning-tab-ab` `812e6bb`/`5f708f7`);
  the arc's checklist item is checked complete; the standalone one-click corpus-seed
  export (`feat/seed-export-button`) is tracked as the next small `feat/` branch.
- **`templates/index.html`** — the Diagnostics modal, the Diagnostics-pill tooltip,
  and the Settings-drawer line are refreshed from "Read-only telemetry" to advertise
  the interactive eval/tuning console (copy only — no behavior/layout/route change).

### Added — in-browser prompt A/B on the Tuning tab (`feat/tuning-tab-ab`)

Step 3 of the "finish the diagnostics faceplate" arc replaces the Tuning tab's
read-only stub with a real candidate-vs-baseline A/B: pick an
`analyzer._BASE_SYSTEM_PROMPTS` constant, edit its text, and run baseline +
candidate evals in the browser, then read the per-(fixture, rubric) delta. The
irreversible **promote** (edit the constant + bump `PROMPT_VERSION` + log
`TUNING_LOG.md`) stays a human/agent step — **no route edits `analyzer.py`**. No
`PROMPT_VERSION` bump (no prompt template changed) and no new dependency.

- **`POST /api/tune/run`** (`app.py`, localhost-only, SSE) — drives
  `evals.runner.run_suite` **twice** in one worker (baseline with no overrides,
  then candidate with the pasted override map), then computes the delta with the
  LLM-free `evals.tune` helpers (`load_scores` + `build_delta_table` +
  `format_delta_table`) and streams it. The candidate run self-stamps
  `prompt_version=candidate:<hash>` via `analyzer.prompt_overrides()`, so it never
  pollutes score-over-time. Mirrors `/api/eval/run`'s input contract, including the
  optional corpus-seed mode (`slug` + `username` → `evals/fixtures/real/<slug>/seed.json`,
  reusing `_safe_username` + `_within(seed, ANNOTATION_ROOT)` + `secure_filename`).
  All eager validation — bad suite, empty/missing override, an unknown prompt-constant
  name (via the canonical `prompt_overrides()` validator), unknown user, missing seed —
  returns a JSON 4xx **before any paid call** (load-bearing: baseline runs first, so a
  doomed candidate key must be caught up front).
- **Tuning-tab UI** (`dashboard/templates/dashboard.html`) — a constant picker
  (with "Load current text" to prefill the baseline), a candidate textarea,
  suite/subset/grounding controls + an optional real-seed disclosure, a 2×-cost
  `confirm()` gate (~$0.20 smoke / ~$0.60 full), phased progress, and the rendered
  delta table + a manual-promote reminder. The shared SSE streamer is generalized to
  `window.callbackEval.stream(url, params, onEvent)` (the eval-run control now rides
  it too). The `dashboard/routes.py` index passes `tune_prompts` (read-only use of
  `analyzer._BASE_SYSTEM_PROMPTS`) for the picker + prefill.

### Added — run an eval from the console; `run_suite()` core extracted (`feat/run-eval-from-console`)

Step 2 of the "finish the diagnostics faceplate" arc closes the mandatory CLI hop
in the tuning loop: you can now run an eval **from the browser** instead of
dropping to a terminal, and the collate step's paste-this `run_command` dead-end
becomes a real button. No `PROMPT_VERSION` bump (no prompt template changed) and
no new dependency.

- **`evals.runner.run_suite(...)`** — the eval orchestration is extracted from
  `runner.main()` into an importable core taking structured args (`suite`,
  `subset`, `fixture_name`, `seed_data`, `prompt_overrides_map`,
  `grounding_signals`, `out_dir`, `client`) plus an optional `progress` callback,
  returning an `EvalRunResult`. `main()` is now a thin argparse wrapper. The
  no-flag default path is **byte-identical** (empty overrides are a no-op,
  `progress=None` makes every emit a no-op, the analyze→generate cache and the
  result-record bytes are unchanged) — mirrors how `evals/bootstrap.py` already
  splits `main()` from `run_pipeline_over_jd_texts`.
- **`POST /api/eval/run`** (`app.py`, localhost-only, SSE) — drives `run_suite`
  in a worker thread (the `annotation_bootstrap_stream` threading/queue/`_sse`
  pattern) and streams `start` / `fixture_start` / `analyzing` / `clarifying` /
  `generating` / `rubric_done` / `fixture_done` / `done` / `error`. Two modes: the
  Quality-tab run (synthetic/anchor, no seed) and the Annotate-tab "Run this
  fixture" run (`--suite real --seed <slug>/seed.json`, the in-browser collate
  command). Guarded by `_is_localhost_request()` + `secure_filename` +
  `_within(seed, ANNOTATION_ROOT)` + `_safe_username`; all validation returns a
  JSON 4xx before any paid call.
- **Console UI** (`dashboard/templates/dashboard.html`) — a "Run eval" control on
  the **Quality** tab (suite/subset/grounding, a cost-band caption, a `confirm()`
  consent gate showing the ~$0.10 smoke / ~$0.30 full estimate, reload on done);
  on the **Annotate** tab the collate result now shows the CLI command **and** a
  "Run this fixture" button. Promote stays the agent's job — no route edits
  `analyzer.py`.

### Added — run the grounding scorers from the console; bootstraps capture a seed (`feat/grounding-scorers-in-console`)

Found during a v1.0.5 walkthrough: a dev-user installed the offline grounding
scorers (`pip install -e '.[eval-grounding]'`, DeBERTa NLI + MiniCheck-FT5) and
had **no interface to use them** — the only trigger was the CLI
`--grounding-signals` flag, and the browser bootstrap hard-coded `grounding_fn=None`.
Step 1 of the "finish the diagnostics faceplate" arc makes the scorers reachable
from the `/_dashboard` **Annotate** tab, keeping them eval-time (the L1/L2
hot-path discipline in `docs/dev/GROUNDING_METRIC.md` is unchanged):

- **Opt-in on the browser bootstrap** (`app.py`, `/api/annotation/bootstrap`) — a
  "Run grounding scorers" checkbox passes `grounding_signals: true`, which wires
  `evals.grounding_signals.run_grounding_signals` into `build_bootstrap_document`.
  The scorers are pure-Python to import but lazy-load heavy deps, so a missing
  `[eval-grounding]` extra (or any scoring failure) **degrades to an un-scored
  bootstrap + a streamed `warning`**, never a 500 — the paid pipeline output is
  always preserved.
- **"Score grounding" backfill** (`/api/annotation/fixture/<user>/<slug>/score`,
  SSE) — scores an existing bootstrap's deduped bullet representatives **without
  re-running the paid pipeline**, writes them under `grounding_signals`, and
  patches any in-progress `annotations.json` score fields **by `cluster_index`
  without touching human verdicts/notes**. The annotation editor's MiniCheck/NLI
  pre-scores now light up.
- **Bootstraps capture a `seed.json`** — the browser bootstrap now snapshots the
  entire approved corpus via `scripts.export_corpus_seed.export_seed` (non-fatal
  if it can't). This is the durable source the backfill scores against (imported
  via `evals.seed_import.seeded_session`, faithful even if the live corpus is
  later edited) and the file the collate step's `--seed` run-command already
  assumed but the in-browser path never produced.

No new dependency; no `PROMPT_VERSION` bump (deterministic, no prompt change).

### Added — auto-open the default browser on launch (`feat/auto-open-browser`)

`python app.py` (and the `callback` console script) now opens
`http://localhost:5000` in the user's default browser once the server is
listening, so they land straight on the app instead of copying the URL by hand.
A short daemon `Timer` defers the open until the socket is up; under Flask's
reloader (`FLASK_DEBUG=1`, the default) the open fires only in the serving child
(`WERKZEUG_RUN_MAIN=true`) so there's no double tab; and the call is wrapped so a
missing browser can never crash startup. Set `CALLBACK_NO_BROWSER=1` to skip it
on headless / remote / CI runs.

### Changed — retire the broken "legacy import" onboarding; the corpus self-provisions (`fix/retire-legacy-import-onboarding`)

Found during the v1.0.1 → v1.0.5 walkthrough: the **Import into corpus** modal
read like pre-migration cruft, its button `POST`ed to a route that no longer
exists (`/api/users/<u>/import-legacy` → HTTP 404), and there was **no working
way to populate the corpus**. Root cause: `create_user` writes a config but
never a `Candidate` DB row, so *every* user — not just pre-migration ones — landed
in the `needs_onboarding` state whose only UI exit was that broken modal.

The onboarding gate is removed; the candidate row is now provisioned on demand:

- **Self-provisioning** — a new `_get_or_provision_candidate()` helper (`app.py`)
  creates the `Candidate` row from the user's config on the first corpus *write*
  (résumé ingest, add-experience, add-summary, persona upload, analyze), reusing
  the idempotent `import_candidate_from_config`. Both onboarding paths are open to
  a brand-new user immediately: **import a résumé** (AI extraction) **or** add
  experiences/bullets by hand — and you can mix them. The five write routes that
  returned `409 + needs_onboarding` (and summaries' `404`) now just succeed.
- **Frontend** (`static/app.js`, `templates/index.html`) — the onboarding modal,
  the `import-legacy` fetch, `openOnboardingModal` / `_renderNeedsOnboarding`, and
  the "Legacy import" error labels are deleted. The Career corpus tab always shows
  its toolbar (import **and** add-experience) with a unified empty-state hint; the
  read-only tabs (Memory / Applications / Templates) show a non-modal "Go to
  Career corpus" CTA via `_renderCorpusEmptyCTA`. All "database migration" /
  "run onboarding" / "Select a user above" copy is rewritten.
- **Tab rename** — the first tab **Application → Tailor** everywhere (label, ids
  `topTabApplication`/`tab-application` → `topTabTailor`/`tab-tailor`, the
  `switchTopTab('tailor')` handler, and `ui_pages/selectors.py` `TopTabs.TAILOR`).
- **Module rename** — `onboarding/import_legacy.py` → `onboarding/corpus_import.py`
  (and its test file) so no "legacy" name remains in the runtime path; the CLI is
  now `python -m onboarding.corpus_import`. Behavior unchanged.
- **Tests** — the four write-route "missing candidate → 4xx" tests now assert
  auto-provision success and that the row was created; their fixtures patch
  `corpus_import.CONFIGS_DIR`. The new-user UX regression asserts the working
  "+ Import résumé" affordance instead of the removed CTA.

No prompt / `PROMPT_VERSION` change, no new dependency. (Shipped CHANGELOG /
architecture / benchmark mentions of the old file-based "legacy" pipeline are
left as accurate history.)

### Changed — needs-onboarding GET reads return `200`, not `409` (`refactor/needs-onboarding-200-on-reads`, v1.0.5)

Found during v1.0.5 verification: creating the first user and clicking across
the tabs logged a cascade of `409 (CONFLICT)` console errors — one per passive
tab load (`GET …/personas`, `…/applications`, `…/clarifications`,
`…/experiences`). The read endpoints were signalling "no corpus row yet" with a
`409`, which the browser logs red regardless of how the JS handled it (every
handler already rendered the import CTA — except the persona template picker,
which showed a misleading "Failed to load templates").

A `409 Conflict` on a **read** is a misuse: asking for a not-yet-onboarded
user's list is an unmet precondition, not a state conflict. The contract now
splits by method — **reads → `200`, writes → `409`**:

- **`GET` read endpoints** (`…/personas`, `…/applications`, `…/clarifications`,
  `…/experiences`, `…/duplicates`) return `200` with an empty, success-shaped
  body plus `needs_onboarding: true`. The console stays clean and the import CTA
  still renders; a naive consumer just sees empty lists. (Mirrors the
  pre-existing `pending-counts` / `summaries` `200`-empty precedent.)
- **`POST` write endpoints** (analyze, corpus ingest, experience/persona
  create, persona preview) keep `409 + needs_onboarding` — a write precondition
  failure reasonably *is* a conflict, and they never fire on a passive load. The
  live-preview `GET` also keeps `409` (it serves an HTML iframe, not a list, and
  isn't fired pre-onboarding).
- **Frontend** (`static/app.js`): `_needsOnboarding()` is now status-agnostic
  (keys off the body flag), so the one helper covers both the `200` reads and
  the `409` writes; the six read handlers branch on the flag before treating the
  body as a collection, and two secondary `/experiences` consumers are
  `Array.isArray`-guarded against the discriminated shape.
- **Tests**: the five GET-read route tests flip `409 → 200`; a new dated UX
  regression (`tests/ux/regression/test_20260606_new_user_no_4xx.py`) seeds a
  config-only user, sweeps all four tabs, and asserts **zero** `4xx` on any
  `/api/users/<u>/…` call plus a visible import CTA. Two tab selectors
  (`TopTabs.PERSONAS` / `TopTabs.MEMORY`) + the shared CTA name were added to the
  `ui_pages` registry.

No prompt / `PROMPT_VERSION` change, no new dependency.

### Added — annotation tab + browser bootstrap wrapper: the console's first read-write surface (`feat/annotation-tab`, v1.0.5)

The last branch of the v1.0.5 stream puts the v1.0.4 eval tuning loop on the
design system: a fifth `/_dashboard` tab — **Annotate** — that produces and
labels real annotation material in-browser, ending the need to hand-edit JSON.
It reads/writes the durable Phase 3 `annotations.json` contract **verbatim**
(reusing `evals.annotation` — schema not forked), so the labels it produces are
exactly what the deferred grounding calibration needs. **No prompt /
`PROMPT_VERSION` change, no new dependency, no new LLM-call shape** (the wrapper
reuses the existing `analyze`/`clarify`/`generate` primitives unchanged).

- **The console's first READ-WRITE routes** — added to `app.py` (not the
  read-only dashboard blueprint, which stays read-only). Every route is
  **localhost-only** and gated by the security pattern: `_safe_username()` (real
  candidate) + `secure_filename(slug)` + `_within(path, ANNOTATION_ROOT)`, writing
  ONLY under `evals/fixtures/real/` (gitignored, PII-bearing):
  - `GET /api/annotation/fixtures` — list bootstrap fixtures.
  - `GET`·`POST /api/annotation/fixture/<user>/<slug>` — load the working doc
    (existing `annotations.json` or a fresh `build_annotation_template`) / save it.
    Save runs the **fail-closed `validate_annotations`** (same contract the CLI
    uses), so the on-disk file is always collation-ready.
  - `POST /api/annotation/fixture/<user>/<slug>/collate` — deterministic
    `collate_expected` + `build_improvement_brief` → `expected.json` +
    `improvement_brief.md` + an anchor `jd.txt` (runnable by `runner.py --suite real`).
  - `POST /api/annotation/bootstrap` — **browser bootstrap wrapper (SSE)**: drives
    `analyze → clarify → generate` over N pasted JDs against the live corpus
    (reusing the `/api/analyze/stream` streaming pattern + the deterministic
    `build_bootstrap_document` dedup), streaming per-JD progress, then writes
    `bootstrap.json` + the pasted JDs. Paid (Sonnet/Haiku) + slow (~70s/JD).
- **`evals/bootstrap.py`** — `run_pipeline_over_jds` refactored to delegate to a
  new `run_pipeline_over_jd_texts` (in-memory `(name, text)` JD pairs + an optional
  `progress` callback), so the browser wrapper needs no JD temp files. CLI path is
  behavior-preserving.
- **Annotate tab UI** (`dashboard/templates/dashboard.html`) on the cb-* tokens:
  bootstrap wrapper sub-panel → fixture picker → per-cluster verdict editor
  (`keep`/`fix`/`omit`/`fabricated`, `failed_rules` constrained to the rubric
  vocabulary, `should_omit`, conditional `honest_rewrite`/`forbidden_pattern`) +
  clarification ratings; Save + Collate. Vanilla JS; fetch-streamed SSE for the
  wrapper; validation errors surfaced inline (no `console.error`).
- **Tests** — `tests/test_annotation_routes.py` (fail-closed save, traversal-slug
  containment, localhost guard, collate shape, bootstrap SSE with the LLM pipeline
  stubbed). `tests/ux/flows/test_annotation_tab.py` drives the tab in headless
  Chromium against the unconditional console-error sentinel (seed bootstrap → pick
  → fill verdicts → Save → Collate). `Dashboard` selectors + `DashboardConsolePage`
  POM extended.

### Changed — diagnostics console redesign: tabbed observability on the cb-* design system (`feat/diagnostics-console-redesign`, v1.0.5)

`/_dashboard` moves from a single long-scroll page with its own hardcoded palette
to a **tabbed diagnostics + tuning console on the cb-* design system**. Read-only
throughout — **no new Flask route, no write affordances** (the localhost
host-header guard is preserved verbatim); **no `PROMPT_VERSION` bump, no new
dependency, no LLM call.** Chart.js still loads from CDN; tabs + drawer are vanilla
JS.

- **Four tabs, each a bento of summary tiles → shared right-hand drawer.**
  Pipeline · Quality · Groundedness · Tuning. A tile shows a headline stat;
  clicking it opens one shared drawer with the full chart/table + detail. Charts
  **lazy-init on drawer-open** (never into a hidden/zero-size canvas). Every tile's
  summary *and* detail are server-rendered, so the surface degrades gracefully
  with JS off (panes stack, details show inline).
- **Groundedness tab (the marquee surface)** — designed *around* the 2026-06-06
  metric contract, not retrofitted. New `dashboard/routes.py` helpers
  `_groundedness_trend` (L0 `groundedness.score` 0–5 over time by `prompt_version`,
  **deduped by `run_id`** so a run's value isn't plotted once per rubric) and
  `_latest_groundedness_detail` (the `fabricated_specifics` drill-down:
  `flagged_samples` + `per_bullet` as the actionable evidence).
- **Tier-0 observability over data we already log** (no new data emitted):
  `_run_trace` (per-`run_id` span waterfall from `call` + `latency_ms`),
  `_reliability` (error + `max_tokens`-truncation rates, split by call kind),
  `_cost_by_call_kind` (per-stage cost rollup), and `_baseline_health` /
  `_load_baseline` (health-vs-baseline drift badges: regressed Δ<−0.5 = the
  merge-block gate, watch Δ<−0.3, else ok — read from the in-repo
  `evals/results/baseline_v1.json`).
- **Tuning tab is a read-only scaffold** — documents the `analyzer.prompt_overrides()`
  A/B primitive + links to `/prompt-tune`, `/tune-from-annotations`, and
  `evals/TUNING_LOG.md`. No forms that POST; a banner states write affordances land
  in a later, sign-off-gated branch.
- **Tests** — `tests/test_dashboard_routes.py` gains pure-helper unit coverage for
  every new aggregator (dedup-by-run_id, empty/missing-block paths, verdict bands).
  `tests/ux/flows/test_dashboard_console.py` drives the tabs + drawer in headless
  Chromium against the unconditional console-error sentinel (seeds telemetry by
  monkeypatching the blueprint's `EVAL_RESULTS_DIR` / `LLM_LOG`); a
  `DashboardConsolePage` POM joins `ui_pages/`.

### Added — L0 grounding metric: deterministic fabricated-specifics rate + groundedness composite (`eval/grounding-metric-l0`, v1.0.5)

The first slice of the grounding/hallucination metric, defined *before* the
diagnostics console is redesigned around it ("data model before the view"). This
is the **deterministic, label-free, hot-path-safe** layer (L0); the calibrated
model-based layers are deferred to pre-v1.1.0 because no labeled data exists yet
(`evals/fixtures/real/` is empty). **Deterministic only**: no `analyzer.py`/prompt
edits, no `PROMPT_VERSION` bump, no new dependency, no LLM call.

- **`hardening.py`** — new `compute_fabricated_specifics(generated_text, source_texts)`:
  a typed, severity-weighted successor to `compute_grounding_overlap`'s lossy
  `missing_samples` n-gram heuristic. Per bullet it extracts the verifiable
  *specifics* (numbers / % / $ / years / durations / named-entity & tool tokens)
  and checks each for membership in the candidate's ground-truth source union
  **with tolerance**: numeric formatting variants (`~30` / `30` / `30+`) and light
  rounding (`$2.4M ≈ $2,400,000`) read as grounded; a different magnitude
  (`~30 → 100+`) is flagged; entity tokens are alias-normalized (`k8s ≡ kubernetes`)
  first. A fabricated number outweighs a fabricated entity in the rate.
- **`hardening.py`** — new `assemble_source_union(context_set)` factored out of
  `compute_iteration_signals` (behavior-preserving): the single definition of the
  dynamic ground-truth union (primary résumé + supplementals + clarification
  answers), now shared by the iteration clarifier and the L0 check so the two can
  never score against divergent source sets.
- **`evals/runner.py`** — `_post_generation_metrics` now rides `fabricated_specifics`
  (L0 detail) and a single reportable `groundedness` composite along on **every**
  eval record (nested in `deterministic_metrics`, so attributable by
  `prompt_version` on the dashboard's score-over-time chart). The composite is
  **L0-only by default**; it enriches in place to L0+L1+L2 (NLI entailment +
  MiniCheck) only when `--grounding-signals` produced real scores. The existing
  `grounding_overlap` source set is left untouched (L0 scores against the wider
  union via a separate `source_union` arg), so existing baselines are unperturbed.
  L1/L2 behavior is read, never re-tuned.
- **Precision caveat (honest by design):** L0 is high-precision on genuinely-novel
  specifics but **will false-positive on paraphrase / implication** (source
  "managed a small team" → output "led a 4-person team" flags "4"). It is a
  **flag-for-review** signal, **not a gate**; tolerance bands are deliberately
  conservative and its precision/recall is **unproven until calibration against
  `annotations.json`** (deferred-B). See `docs/dev/GROUNDING_METRIC.md` and the
  `evals/TUNING_LOG.md` note.
- **Tests** — `tests/test_hardening.py::TestFabricatedSpecifics` (exact match → 0;
  novel number → flagged; within/out-of tolerance; `k8s`≡`Kubernetes` aliasing;
  embedded-digit non-leak; severity weighting) + `TestAssembleSourceUnion`;
  `tests/test_eval_runner.py::TestGroundednessComposite` (L0-only default +
  graceful L1/L2 enrichment). Deterministic — default `pytest`, no LLM/Chromium.

### Fixed — template pagination: blank pages + paged.js console error (`feat/template-pagination`, v1.0.5)

Blank/short pages in the **Modern**, **Spacious**, and **Tech** bundled
templates are gone, and the long-standing cosmetic paged.js console error is
fixed at the source. **Rendering-only**: no `analyzer.py`/prompt edits, no
`PROMPT_VERSION` bump, no new dependency.

- **`personas/bundled/{modern,spacious,tech}.css`** — dropped
  `section { page-break-inside: avoid; }` (present in both the base rule and the
  `@media print` block), keeping the correct per-entry
  `article { page-break-inside: avoid }`. Telling paged.js never to break inside
  a *whole section* meant any Experience section taller than the space left on
  the page got shoved wholesale onto the next page, leaving a blank/short page.
  This matches **Classic**'s proven break model (which never had the section
  rule); also added Classic's `h2 { page-break-after: avoid }` so a section
  heading is never orphaned at the foot of a page.
- **`app.py`** (`_PAGED_PREVIEW_INJECTION`) — the preview iframe now drives
  paged.js **manually** (`window.PagedConfig = { auto: false }` +
  `new Paged.Previewer().preview()` inside `try/catch` + `.catch()`). The
  bundled polyfill's auto-run `await`s `preview()` with no `.catch()`, so a
  sparse-content layout throw escaped as the uncaught
  *"getBoundingClientRect of null"* console noise; driving it ourselves contains
  it. The `pagedjs_rendered` page-count `postMessage` contract is preserved.
- **`tests/ux/`** — new regression test
  `regression/test_20260604_template_pagination.py` renders a deliberately
  multi-page résumé through all four bundled templates via the real preview
  route and asserts every `.pagedjs_page` carries content (no blank page) with a
  clean console. The `getBoundingClientRect` **allowlist in
  `tests/ux/conftest.py` is removed** — the sentinel is now unconditional, so any
  paged.js console regression fails the suite.

### Added — Playwright UX regression suite + shared `ui_pages` driver (`feat/playwright-ux-suite`, v1.0.5)

Browser-level UI regression coverage so the 2026-05-26 punch-list bugs — which
lived in JS render paths the `pytest` unit suite can't reach — can't return.
**Test-only** change: no `analyzer.py`/prompt edits, no `PROMPT_VERSION` bump,
no new dependency (Playwright was already a dependency).

- **`ui_pages/`** (new package) — a shared, framework-free Page Object Model
  over a single selector registry, consumed by *both* the new test suite and
  `scripts/capture_screenshots.py` (converged onto it, so there is **one**
  navigation source rather than two drifting copies). `base_url` is injected,
  so the same POMs drive the ephemeral-port test server and the screenshot
  script's `:5000`.
- **`tests/ux/`** — a threaded live-server + headless-Chromium harness with a
  console-error + HTTP-5xx **sentinel**; LLM-free (analyzer functions stubbed
  at the public-streaming-fn seam, so the real Flask routes still run). One
  stubbed happy-path walk (analyze → compose → template), one seeded Step-6
  WYSIWYG walk (via the prior-app-resume path), and five regression tests
  (`test_<YYYYMMDD>_<slug>.py`, never deleted): import-résumé label, rail
  re-enable after analyze, corpus-tab render, the personas-500 → iframe →
  paged.js cascade root (AGENT_FAILURE_PATTERNS §5b), and Compose bullet
  drag/keyboard reorder persistence + reset.
- **`pyproject.toml`** — new `ux` pytest marker (`pytest -m ux`); ux tests are
  also `slow`/real-Chromium and skip when the browser binary is absent, so the
  default `pytest` stays green everywhere. `tests/*` ruff ignore widened to
  `tests/**` for the nested suite.

### Added — user-driven bullet ordering on Compose (`feat/bullet-drag-reorder`, v1.0.5)

Drag-and-drop (and keyboard) reordering of bullets within each experience on
the Compose step. The chosen order is **authoritative** — it propagates into
the `<career_corpus>` block fed to `generate()`, so it shapes which bullets the
LLM keeps in a length-limited résumé, not just the on-screen list. A data-order
change, **not a prompt-template change → `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (captured as a behavior note in
[`evals/TUNING_LOG.md`](evals/TUNING_LOG.md) instead of a version bump).

- **`analyzer.py`** — `_stable_user_prefix` honors
  `composition_overrides.bullet_order = {experience_id: [bullet_id, ...]}`,
  reordering each experience's bullets before the corpus block is emitted.
  Bullets absent from a saved order keep their relative position at the end
  (covers a bullet added via the drawer *after* ordering — never silently
  re-sorted). Absent/empty order ⇒ output byte-identical, so the
  analyze→generate prompt cache is untouched.
- **`app.py`** — the existing `POST /api/applications/<id>/composition` threads
  and validates an optional `bullet_order` into the persisted overrides; `GET`
  returns bullets in the saved order with a per-experience `has_custom_order`
  and per-bullet `in_custom_order` flag. Existing `_safe_username` + `_within`
  guards unchanged; no new route.
- **`static/app.js` + `static/style.css`** — native HTML5 drag with a grab
  handle (`≡`, grab/grabbing cursors), an Up/Down keyboard path with
  `aria-label`s (the a11y floor; no deprecated
  `aria-grabbed`/`aria-dropeffect`), a one-sentence in-interface instruction
  plus an "(i)" depth affordance, a per-experience "Reset to AI ranking"
  button, and a "newly added — drag to reposition" hint. Reorders persist via a
  debounced (~300 ms) optimistic autosave.
- **Behavior change (consistency win):** pin / exclude / add now also persist on
  the debounced autosave, not only when you click Next — the autosave sends the
  full composition state, so it can't clobber those flags.

### Added — WYSIWYG live preview (Option 1) (`feat/wysiwyg-option1`, v1.0.5)

The application preview is now byte-for-byte the future downloaded résumé once a
generate has run. A pure rendering/caching change per RELEASE_ARC Key decision 5 —
**no prompt change, `PROMPT_VERSION` unchanged, no new dependency, no LLM call.**

- **`hardening.py`** — `save_iteration_context()` caches `last_generated_json_resume`,
  the deterministic `json_resume.md_to_json_resume()` of the markdown the LLM just
  wrote, into every post-generate context. Derived from `last_generated_resume`, so
  the preview source can never drift from the download. Added to the `ContextSet`
  TypedDict.
- **`app.py`** — `GET /api/applications/<id>/preview` serves
  `last_generated_json_resume` directly when the context carries it (preview ==
  download), bypassing the pre-generate curation gate. Pre-generate it still builds
  the JSON Resume from the corpus and gates on `llm_recommendations`. A new
  `_json_resume_has_content()` guard falls back to the corpus-direct render if the
  cached doc is an empty skeleton.

### Added — Step 6 (Output) redesign + styled cover-letter preview (`feat/step6-redesign`, v1.0.5)

Finishes the Step 6 output panel and gives the cover letter a styled live preview.
A UI/rendering change — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency** (`markdown` was already a dependency), no LLM call on the new path.

- **`personas/cover_letter.html` (new)** — a shared, persona-agnostic
  business-letter shell for the cover-letter preview: terser header (no name
  banner), dense single-spaced body, addressee block inline with the body, and the
  chosen persona's font (plainly) injected via a template variable. Honors
  `@page { size: letter }` so paged.js paginates it like the résumé.
- **`pdf_render.py`** — `render_cover_letter_html()` renders generated
  cover-letter text into that shell (`markdown` + `nl2br`, so header lines keep
  single-line breaks while blank-line-separated paragraphs become `<p>` blocks);
  `persona_font_family()` extracts a persona CSS's base `font-family` (multi-line
  values normalized) with a neutral fallback. Both deterministic — no LLM.
- **`app.py`** — `GET /api/applications/<id>/cover-letter-preview` serves the
  styled cover letter from a context's `last_generated_cover_letter`, returning an
  honest placeholder until one is generated. Same guard pattern as the résumé
  preview (`_safe_username` + `_within(OUTPUT_DIR)`).
- **Frontend** — the Cover-letter tab gains a styled paged.js preview iframe with
  a "Page N of M" chip; the Step 6 résumé preview gains the same chip (reusing
  `_updatePreviewPageCount`, now source-keyed so multiple preview frames don't
  cross-talk). The "Edit before downloading" drawer is parameterized to host either
  the résumé or cover-letter editor; edits still flow through `/api/save-edits`.
  Stale "WYSIWYG coming in v1.0.2" / "styled CL lands in B3" hint copy corrected.
- The cover letter still downloads as **`.docx`**; PDF/Markdown cover-letter output
  is the next branch.

### Added — Cover-letter output formats (`feat/cover-letter-formats`, v1.0.5)

The cover-letter download now honors a chosen output format — `.docx`, `.pdf`, or
`.md` — closing the v1.0.1 placeholder (which shipped only a UI hint). An
output-format change only — **no prompt change, `PROMPT_VERSION` unchanged, no new
dependency, no LLM call** (the renderers are deterministic, P1 Hardening).

- **`generator.py`** — `generate_cover_letter()` gains an `output_format` (+
  `template_path`) param and branches like `generate_resume()`: `.md` writes the
  normalized markdown; `.pdf` renders through the shared `personas/cover_letter.html`
  business-letter shell via Playwright (`_render_cover_letter_pdf`), so the `.pdf` is
  byte-faithful to the Step-6 preview (WYSIWYG); `.docx` uses a new
  `_write_cover_letter_docx()` aligned to the 2026-05-26 business-letter decisions
  (persona font matching the chosen résumé template, dense near-single spacing, no
  name banner, inline addressee). The `.docx` and `.pdf` share one font source (the
  persona CSS). The now-unused `is_cover_letter` param was removed from `_write_docx`
  (résumé output unchanged).
- **`pdf_render.py`** — `render_cover_letter_pdf()` mirrors `render_pdf`: renders the
  shell HTML (via the existing `render_cover_letter_html`) to a temp file and prints
  it through headless Chromium, letting the shell's `@page` rule govern page geometry
  (`prefer_css_page_size`) so the PDF matches the paged.js preview. Deterministic.
- **`app.py`** — `/api/download-edited` threads the chosen format and resolved persona
  template into `generate_cover_letter` for cover-letter downloads (no new route; the
  existing `_safe_username` / `_within` / `secure_filename` guards cover the path).
- **Frontend** — a dedicated DOCX / PDF / Markdown picker in the Step-6 cover-letter
  tab (independent of the résumé's Step-5 picker — résumé and cover letter can use
  different formats); `downloadCoverLetter()` sends the chosen format + persona id.
  The satisfied "PDF & Markdown coming next" hint copy was removed.

### Added — Resume a prior application into the wizard (`feat/prior-app-resume`, v1.0.5)

Clicking a prior application now offers **Resume in wizard**, which reloads that
application's last generated state — context + persona + generated résumé/cover
letter — into the live wizard and jumps to Step 6, closing the D.3.1 placeholder.
A UI state-hydration change only — **no prompt change, `PROMPT_VERSION` unchanged,
no new dependency, no LLM call, no schema migration.**

- **`app.py`** — `GET /api/applications/<id>` gains a `resume_state` block (latest
  run's generated/edited markdown, persona, rediscovered `context_path`, iteration,
  `resumable` flag). A new deterministic, LLM-free helper
  `_find_context_path_for_run()` rediscovers the run's on-disk `context_*.json`
  (ApplicationRun has no `context_path` column) by matching the `application_run_id`
  each context file embeds, newest by iteration then mtime; every candidate path is
  `_within(OUTPUT_DIR)`-guarded. No new route — `get_application`'s existing
  `_safe_username` guard covers it.
- **Frontend** — a "Resume in wizard" button on the application-detail modal (shown
  only when a run produced a résumé). `resumeApplicationIntoWizard()` reuses
  `_onGenerationComplete` + `_renderOutput` (converging on the exact post-generate
  state, not forking it): binds the preview routes to the application, reselects the
  persona, hydrates the editors, and advances the rail to Step 6. When the on-disk
  context file is gone it degrades gracefully — editors still hydrate from the DB
  markdown and downloads work; a toast notes that the styled preview + further
  iteration need a re-generate.

## [1.0.4] — 2026-06-02

The eval tuning loop: a real-data, human-in-the-loop, model-assisted
prompt-improvement loop, gated by the offline grounding scorers and the eval
suite. Internal/dev tooling — **no user-facing pipeline change** across the
stream, and `PROMPT_VERSION` is unchanged (no persona-constant edit landed; the
loop *promotes* edits under explicit user approval, which is when a bump occurs).
Six sequential branches: the prompt-override primitive, corpus seed
export/import, the corpus-backed runner, the bootstrap engine, the annotation
contract, and the draft-and-gate tuning skill.

### Added — Eval prompt-override primitive (`eval/prompt-override-primitive`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, and `PROMPT_VERSION` is unchanged (no prompt-constant edit).

- **`analyzer.py`** — a runtime prompt-override primitive. `prompt_overrides()`
  (a context manager) injects a candidate system prompt **by name** without
  editing the persona constants; `effective_prompt_version()` returns
  `PROMPT_VERSION` on the default path but a stable `candidate:<hash>` while an
  override is active, so candidate runs are quarantined from the dashboard's
  score-over-time. The default (no-override) path is **byte-identical**: the
  call-site resolver returns the *identical* constant object and the logged
  version is unchanged, so the analyze→generate prompt cache and the
  `PROMPT_VERSION` attribution discipline are untouched.
- **`evals/runner.py`** — `--prompt-overrides PATH` threads a JSON
  `{prompt-name: override-text}` file through a run; eval result records and
  telemetry stamp the candidate version. Eager-validated — bad JSON, wrong shape,
  or an unknown prompt name exits non-zero before any paid LLM call.
- **`/prompt-tune`** — retrofitted onto the primitive: the A/B trial injects the
  candidate via `--prompt-overrides` instead of editing `analyzer.py` in place
  (removing the fragile clean-revert dependency); the constant is edited only if
  you choose Keep.

### Added — Corpus seed export (`eval/corpus-seed-export`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls.

- **`scripts/export_corpus_seed.py`** — a deterministic, LLM-free CLI
  (`python -m scripts.export_corpus_seed --user <name>`) that snapshots one
  candidate's corpus (Candidate / Experience / ExperienceTitle / Bullet /
  SummaryItem / Skill / Education / Certification + the candidate-scoped Tag
  registry and tag links) into a `seed.json` under the gitignored
  `evals/fixtures/real/`. Original DB primary keys are preserved so foreign-key
  relationships round-trip; the export is a faithful snapshot (active + inactive
  rows) — the active-only / JD-aware filtering stays in
  `build_context_set_from_db`. The `seed.json` shape (`seed_schema_version: 1`)
  is the contract the upcoming corpus-backed eval runner imports into an
  in-memory SQLite.
- **Write-path guard** — a `_within`-style resolved-path check (mirroring
  `app.py:_within`) refuses to emit anywhere except `evals/fixtures/real/`, and
  `secure_filename` sanitizes the username directory component, so the snapshot
  (which carries real PII) can't escape the gitignored tree.

### Added — Corpus-backed eval runner (`eval/corpus-backed-runner`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based eval path is **byte-for-byte untouched** when `--seed` is absent.

- **`evals/seed_import.py`** — a deterministic, LLM-free importer: the faithful
  inverse of `scripts/export_corpus_seed.py`. Reads a `seed.json`
  (`seed_schema_version: 1`), validates the schema version against the versions
  the importer itself supports (drift is rejected, not half-imported), and
  reconstructs the candidate's corpus into a fresh in-memory SQLite —
  **preserving the original primary keys** so the seed's tag links stay
  FK-correct with no remap table. `seeded_session()` is the ergonomic
  context-manager entry (builds the engine + schema, imports, yields
  `(session, username)`, disposes on exit). The importer does NOT pre-filter —
  inactive rows are reconstructed too; the active-only / JD-aware filtering stays
  inside `build_context_set_from_db`.
- **`evals/runner.py`** — `--seed PATH` builds each fixture's context via
  `db.build_context.build_context_set_from_db` over the imported corpus (the REAL
  corpus→context product path) instead of parsing the fixture's resume file; the
  fixture's `jd.txt` + `expected.json` still drive grading. Eager-validated — a
  bad path, malformed JSON, or unsupported schema version exits non-zero before
  any paid LLM call. Absent flag → the resolver, `_load_fixture`, and the
  context-build branch are all byte-identical to today.

### Added — Corpus bootstrap engine (`eval/bootstrap-engine`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency. The bootstrap engine
*orchestrates* LLM calls (it lives in `evals/`, off the P1 hardening boundary,
like `evals/runner.py`), but every collation step is deterministic and LLM-free.
The runner's file-based and `--seed` paths are **untouched** (zero edits to
`evals/runner.py`).

- **`evals/bootstrap.py`** — drives **one corpus seed against N JDs**
  (`--jd-dir` of `*.txt`/`*.jd` files) through the REAL product pipeline
  (`analyze` → `clarify` → `generate`, reusing the public primitives + an
  in-memory `seeded_session` import + `build_context_set_from_db`), then
  deterministically dedups the generated bullets and skills across JDs at a
  Jaccard threshold (default 0.75). The cross-JD cluster span (`size` /
  `len(jd_files)`) is the JD-invariance signal: a wide-span cluster is grounded
  core; a `size: 1` cluster is JD-specific — a `jd_pandering` candidate the next
  branch annotates. Output is a `bootstrap.json` (`bootstrap_schema_version: 1`)
  written under the gitignored `evals/fixtures/real/<candidate>/`; a `_within`
  write-path guard (mirroring `scripts/export_corpus_seed.py`) refuses to emit
  the PII-bearing snapshot anywhere else. The seed + `--jd-dir` are
  eager-validated before any paid LLM call.
- **Second `run_grounding_signals` call site** — `--grounding-signals` scores the
  deduplicated bullet cluster representatives against the corpus source text
  (DeBERTa NLI + MiniCheck-FT5, eval-only), gated on the same opt-in as the
  runner.
- **`evals/rubrics/grounding.md`** — adds the `jd_pandering` slug to the
  `failed_rules` vocabulary (a fabrication subtype: re-skinning source experience
  with a JD's domain terms not present in source). Rubric-vocabulary edits are
  eval-apparatus, **not** a prompt change — `PROMPT_VERSION` is not bumped.

### Added — Eval annotation contract (`eval/annotation-contract`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, `PROMPT_VERSION` unchanged, no new dependency, no LLM calls. The
file-based, `--seed`, and bootstrap paths are **untouched**. Deterministic
collation only — it consumes `bootstrap.json`, it does not call models (P1
hardening posture, like `evals/seed_import.py`).

- **`evals/annotation.py`** — the headless, file-based annotation contract: the
  human-in-the-loop seam between `bootstrap.json` and a `--suite real` regression
  fixture. It declares `annotation_schema_version: 1` and a fail-closed
  `validate_annotations` (mirroring `evals/seed_import.py`: an unsupported version,
  missing collections, an unknown verdict, an unknown `failed_rules` slug, or a
  verdict whose required payload is absent is rejected, not half-collated).
- **Verdict enum** — `keep` / `fix` / `omit` / `fabricated`. Disposition verbs,
  each mapping 1:1 to a collation action. **Verdict-aware** requirements: `fix`
  must carry an `honest_rewrite`; `fabricated` must carry a compilable
  `forbidden_pattern` regex. The grounding *subtype* of a finding
  (`jd_pandering`, `invented_metric`, …) rides in `failed_rules`, which **reuses
  the existing rubric vocabulary** in `evals/rubrics/` — that reuse is not a
  prompt change and bumps no `PROMPT_VERSION`.
- **Template emitter** (`build_annotation_template`) — `bootstrap.json` → a blank
  `annotations.json` skeleton pre-filled with every bullet/skill cluster +
  clarification question + the inline MiniCheck/NLI pre-scores (joined by index
  from the bootstrap's `grounding_signals`), so a human annotates with the model
  pre-scores in view. The headless stand-in for the v1.0.5 annotation UI, which
  wraps this same file format — so the format is the durable contract.
- **Deterministic collation** — a completed `annotations.json` (+ its
  `bootstrap.json`) produces (a) an `expected.json` fixture matching the schema
  `evals/runner.py:_load_fixture` reads (`must_keywords` from `keep`-verdict
  skills; `forbidden_inventions` from `fabricated`-verdict patterns; `min_*_score`
  defaults/overrides; `candidate_name`; provenance `notes`) and (b) an improvement
  brief (fabrication patterns, `fix` rewrites as worked-example seeds, omissions,
  clarification ratings, and a human-vs-scorer agreement section) — the source
  material for the next branch's prompt edits.
- **CLI** — `python -m evals.annotation --bootstrap PATH --emit-template` writes
  the skeleton beside the bootstrap; `… --collate --annotations PATH --jd-dir PATH`
  **auto-writes a runnable `--suite real` fixture directory** (`expected.json` +
  the widest-span anchor `jd.txt`) plus the brief. A `_within` write-path guard
  (mirroring `evals/bootstrap.py`) refuses to emit the PII-bearing artifacts
  anywhere except `evals/fixtures/real/`.

### Added — Tune-from-annotations skill (`tuning/draft-and-gate-skill`, v1.0.4)

Internal/dev tooling for the eval tuning loop — **no user-facing pipeline
change**, no new dependency. `PROMPT_VERSION` is **unchanged by this branch**:
only a user-approved *promote* edits a persona constant and bumps the version (in
that promote commit), never the skill itself. Closes the v1.0.4 loop (export →
bootstrap → annotate → collate → **draft / eval / promote**).

- **`/tune-from-annotations`** (`.claude-plugin/commands/tune-from-annotations.md`)
  — the annotations-driven sibling of `/prompt-tune`. It reads an
  `improvement_brief.md`, drafts a candidate system-prompt edit, A/Bs it against
  the annotation-produced `--suite real` fixture (via `--seed`) **plus an
  `--suite anchor` canary**, and presents the delta tables. Built on the
  prompt-override primitive, so `analyzer.py` is untouched during the trial and
  the candidate run is logged as `prompt_version=candidate:<hash>` (quarantined
  from score-over-time). Promotion — `Edit` the constant + bump `PROMPT_VERSION`
  in one commit + a `TUNING_LOG.md` entry — happens only on an explicit "promote."
- **`tune-drafter` subagent** (`.claude-plugin/agents/tune-drafter.md`) — drafts
  the full candidate constant text from the brief + the current constant. It is
  **read-only** (`Read`/`Grep`/`Glob`; no `Edit`/`Write`) by design: it cannot
  edit `analyzer.py`, so the baseline it drafts against stays intact for an
  honest A/B, and promotion stays a user-gated step in the command — not the
  drafter's job.
- **`evals/tune.py`** — a deterministic, LLM-free delta-table helper + CLI
  (`python -m evals.tune --baseline A.jsonl --candidate B.jsonl [--json]`). Reads
  eval result JSONL, groups `status == "ok"` scores by `(fixture, rubric)`, and
  emits per-pair baseline-vs-candidate deltas (regression flag at the runner's
  `REGRESSION_DELTA`). Standalone — it consumes result files only and imports
  nothing from `runner.py`/`annotation.py`/`bootstrap.py`/`seed_import.py`, so
  their paths are untouched. `tests/test_tune.py` covers it (LLM-free).

## [1.0.3] — 2026-06-02

R1 Phase 2 stream — two-pass analyze split (speed without quality loss) +
`clarify()` → Haiku 4.5. `analyze` p50 103.2s → 67.7s (−34%), per-run cost
−12%, `clarification_quality` recovered to ≥4.20 (pm-senior) with all other
rubrics held at or above the v1.0.2 baseline. No user-facing pipeline shape
change. `PROMPT_VERSION` `2026-05-24.4` → `2026-06-01.4`.

### Changed — Two-pass analyze split, gated for speed without quality loss (`r1/analyze-split-retry`)

- **`analyzer.py`** — `analyze()` is now a two-pass orchestrator instead of one
  Sonnet call:
  - **Pass 1 — extraction (Haiku 4.5, new `EXTRACTION_SYSTEM_PROMPT`):**
    `essential_skills`, `preferred_skills`, `industry_keywords`,
    `hidden_qualities` (the typed `HiddenQualityItem` shape), `professional_vocabulary`,
    `keyword_placement`. Enforced by the new `AnalyzeExtractionResponse` model — a
    bare-string `hidden_qualities` item or out-of-enum category triggers a parse-time
    retry (the guardrail that prevents the original split's `clarification_quality`
    regression).
  - **Pass 2 — synthesis (Sonnet 4.6, under the shared default `SYSTEM_PROMPT`):**
    `comparison`, `suggestions`, `overall_strategy`, grounded on Pass 1 via an
    `<extracted_signal>` block (`AnalyzeSynthesisResponse`). Synthesis runs under
    `SYSTEM_PROMPT` (not a dedicated persona) so its cached prefix is byte-identical
    to `generate()`'s — this **reclaims the analyze→generate prompt cache** (a
    dedicated synthesis persona diverges at the system block and forces `generate`
    to re-prefill the whole corpus). The synthesis-specific framing lives in the
    user prompt, after the cached prefix.
  - `analyze()` merges both passes into the existing `AnalyzeResponse` contract.
- **`analyzer.py` `analyze_streaming()`** — re-introduces the
  `("phase", {"phase": "extraction"|"synthesis"})` SSE sentinel before each pass;
  emits a single merged `done`.
- **`app.py`** — `/api/analyze/stream` forwards the new `phase` event.
- **`static/app.js`** — the analyze stream swaps its status label per phase
  ("Extracting JD signals…" → "Analyzing positioning…").
- **Removed two unconsumed analyze keys** — `ats_improvements` and
  `ideal_resume_profile` were produced but never read (no consumer in `static/app.js`,
  `app.py`, `clarify()`, `generate()`, or any eval rubric). Actionable ATS guidance
  remains in `keyword_placement`, the deterministic `ats_warnings`, and
  `comparison.gaps` / `suggestions`.
- **`PROMPT_VERSION`** `2026-06-01.1` → `2026-06-01.3` (`.2` was the dedicated-persona
  synthesis build; `.3` moves synthesis under the shared `SYSTEM_PROMPT` to reclaim the cache).

### Changed — `clarify()` moved to Haiku 4.5 (`r1/clarify-model-trial`)

- **`analyzer.py`** — `clarify()` now runs on Haiku 4.5 (was Sonnet 4.6); a one-keyword
  change (`model=HAIKU_MODEL`), no prompt-text change. Interview-question generation is short
  structured output (3–5 questions) that Haiku handles well; the post-R1-split
  `clarification_quality` floor (ds 4.20 / pm 4.26 / sre 4.02) was the precondition the prior
  model-selection note parked the switch behind. n=5 anchor eval: `clarification_quality` held
  (medians 4.2 = the Sonnet floor; means ds 4.00 / pm 4.20 / sre 4.00, all inside the 0.5
  drop-tolerance), `clarify_retry` rate 0/15, and the parse-time `ClarifyResponse` rules
  (`context_probe` + ≥60%-combined) satisfied on every call. Per clarify call: **~57% cheaper**
  ($0.0167 → $0.0072) and **~37% faster** (p50 11.9s → 7.5s). `clarify_iteration()` stays on
  Sonnet (iteration_quality not yet stably ≥ 4.0).
- **`PROMPT_VERSION`** `2026-06-01.3` → `2026-06-01.4` (model change recorded for telemetry
  attribution).

---

## [1.0.2] — 2026-05-30

Eval apparatus stream — internal tooling establishing the regression floor
and callback-quality measurement layer before v1.0.3 R1 prompt engineering.
No user-facing pipeline changes; `PROMPT_VERSION` unchanged at `2026-05-24.4`.

Nine branches merged since v1.0.1 (newest first):

### Added — Offline grounding signal scorers (`eval/grounding-signals`)

- **`evals/grounding_signals.py`** — new eval-only module with two offline
  grounding scorers, gated behind `python evals/runner.py --grounding-signals`:
  - `score_nli_bullets`: DeBERTa-v3-base-mnli-fever-anli (Apache 2.0, ~180 MB)
    runs NLI entailment per bullet vs source material →
    `nli_entailment_score` (0–1) + `nli_contradiction_flag` (bool).
  - `score_minicheck_bullets`: MiniCheck flan-t5-large (~3 GB on first download)
    runs factual grounding check per bullet → `minicheck_grounding_score` (0–1).
  - Both models are lazy-loaded on first `--grounding-signals` run; model weights
    are cached in the OS HuggingFace cache dir (never in the repo).
- **`pyproject.toml`** — new `eval-grounding` optional-dependency group
  (`transformers`, `minicheck`). torch must be installed separately (CPU or CUDA
  variant); see CONTRIBUTING.md.
- **`evals/runner.py`** — `--grounding-signals` flag; per-bullet results ride
  along as `grounding_signals` key on every JSONL record (null when flag absent).
- **CONTRIBUTING.md** — new "Grounding signal scorers" section documenting the
  install sequence, MiniCheck license, and model download size.

### Added — Pareto frontier dashboard panel (`eval/pareto-dashboard`)

- **`dashboard/routes.py:_pareto_data()`** — aggregates `eval_composite` JSONL
  records, joins `cost_usd` by `run_id`, computes per-version p50/p90 latency +
  cost, builds Chart.js bubble-scatter + trend datasets and a most-recent-change
  summary (Δ composite, Δ latency, Δ cost, Pareto verdict).
- **`/_dashboard` Eval Quality section** gains a Pareto frontier panel at the
  top: quality (Y, 0–5) vs wall-clock latency (X, log scale); dot size = cost;
  dashed polyline connects successive baselines. Graceful empty-state when no
  `eval_composite` records exist yet.
- 8 new tests in `tests/test_dashboard_routes.py` cover empty input, None-score
  skip, single-version, cost join, missing-cost fallback, two-version delta,
  Pareto-improving, and Dominated classifications.

### Changed — Canonical 5-status tracker schema (`chore/tracker-status-schema-cleanup`)

- **Migration 0007** — backfills `no_response → submitted` (clears wrongly-stamped
  `outcome_at`), deletes `offer` and `accepted` rows (pre-release, no real data),
  tightens `CHECK` constraint to the canonical 5-value set:
  `draft | submitted | interview | rejected | withdrawn`.
- **`app.py`** — valid set reduced to 5 values; `outcome_at` stamps on
  `{interview, rejected, withdrawn}` (adds `interview`, which the JS
  `outcomeStatuses` already expected but the Python handler never wrote).
- **`static/style.css`** — removes `.status-no_response`, `.status-offer`,
  `.status-accepted` blocks.
- **`static/app.js`** — decouples chip CSS class from chip label so `submitted`
  cards show `status-submitted` styling + "NO RESPONSE" text; removes
  `no_response` from `sentStatuses`.

### Added — Application detail modal + card timestamps (`feat/tracker-notes-and-timestamps`)

- **`PUT /api/applications/<id>/notes`** — saves freeform notes to the
  `Application` row; `GET /api/applications/<id>` now returns `sent_at`,
  `outcome_at`, `notes`.
- **Card timestamp display** — `submitted`/`no_response` cards show
  "Sent · X ago"; `interview`/`rejected`/`withdrawn` cards show
  "Outcome · X ago" using the semantic timestamp rather than `updated_at`.
- **Application detail modal** replaces the prior toast on card click: shows
  title, company, status chip, timestamps, and a notes textarea that saves on
  blur via the new endpoint.

### Added — Application outcome tracking (`eval/applications-tracker`)

- **Migration 0006** — adds `sent_at TEXT`, `outcome_at TEXT`, `notes TEXT`
  to the `application` table; expands `status CHECK` to include
  `offer | accepted | rejected | no_response`; backfills `closed → withdrawn`.
- **`app.py`** — auto-stamps `sent_at` on `submitted` transition;
  `outcome_at` on any outcome transition; summary dict exposes both timestamps.
- **`static/app.js`** — `submitted` cards gain inline "Got callback /
  Got rejection / No response" action buttons calling
  `PUT /api/applications/<id>/status`.
- 8 new tests covering timestamp stamping, new valid statuses, and rejection
  of the removed `closed` value.

### Added — Callback-likelihood rubric + post-generation metrics (`eval/callback-metrics`)

- **`evals/rubrics/callback_likelihood.md`** — Haiku judge with a senior
  in-house recruiter persona (200-person company, 80 résumés, 7-second skim,
  1–5 scale). Sixth rubric in the anchor suite.
- **`hardening.py`** — two new deterministic helpers (no LLM calls):
  `compute_top_third_density(resume, jd_keywords)` and
  `compute_quantification_rate(resume)`. Both ride on `_post_generation_metrics`.
- **`evals/runner.py`** — `_score_distinctiveness()` (eval-time-only Haiku call
  with graceful fallback); `_post_generation_metrics()` extended to accept
  `jd_keywords`; `eval_composite` JSONL record written per fixture after all
  rubrics grade, weighted by `evals/callback_weights.json`.
- **`evals/callback_weights.json`** — recruiter-informed prior weights:
  `keyword_coverage×2, callback_likelihood×3, ats_format×1, tone×1,
  grounding×1, clarification_quality×0.5`.
- 12 new tests for `compute_top_third_density` and `compute_quantification_rate`.

### Added — Anchor fixture suite + PR gate + JSONL schema v3 (`eval/anchor-and-pr-gate`)

- **`evals/anchors/anchor-v1/`** — immutable copy of the 3 synthetic fixtures
  (`data-scientist-junior`, `pm-senior`, `sre-mid-level`) + rubrics +
  `manifest.json`. Anchor/exploration split documented in `evals/exploration/README.md`.
- **JSONL `schema_version 3`** — per-record additions:
  `anchor_version`, `suite` (anchor|exploration), `fixture_hash`,
  `rubric_version`, `model_snapshots`, `baseline_comparison`
  (pre-computed `delta` + `within_1_stdev`), `phase_latencies_ms`.
- **`.github/PULL_REQUEST_TEMPLATE.md`** — requires eval evidence (n=3 runs,
  mean ± stdev table, Δ vs baseline, latency + cost Δ) on any `analyzer.py` /
  `evals/` prompt PR. Regression > 0.5 = blocked; latency p50 regression > 20% =
  blocked; cost regression > 20% = blocked.
- **`evals/runner.py`** — `--suite anchor|exploration` flag; regression
  alerter exits code 2 on regression (previously just a log line).
- TUNING_LOG anchor-v1 promotion-rule entry.

### Changed — Schema-version 3 baseline + 5-run aggregate (`eval/baseline-v1-0-2`)

- **`evals/results/baseline_v1.json`** — upgraded schema_version 2 → 3; adds
  per-rubric `mean / stdev / min / max / n` across 5 back-to-back synthetic runs
  at `PROMPT_VERSION 2026-05-24.4`; adds `deterministic_metrics_baseline` and
  `performance_baseline` blocks; adds `fixture_set_hash` and `model_snapshots`.
- **`evals/runner.py`** — `_load_baseline_scores` now seeds from the stable
  5-run aggregate mean (rather than the noisiest single prior run), halving
  false-alarm rate from Haiku judge variance.
- **`evals/TUNING_LOG.md`** — new `## BASELINE — v1.0.2 — 2026-05-28` entry
  with full run metadata, raw scores, deterministic metrics, green-light criteria
  status, and "known below-threshold (pre-existing)" exceptions.
- Known below-threshold at this baseline (not new regressions; recovery targets
  for v1.0.3 `r1/structural-context-probe`):
  `data-scientist-junior × clarification_quality` (mean 3.92),
  `sre-mid-level × iteration_quality` (mean 3.73, n=3 fixture fragility),
  `data-scientist-junior grounding_overlap_ratio` 0.228 (< 0.25 threshold).
- Zero judge_errors across 90 gradings; cost CV < 5% per fixture.

### Changed — Pydantic v2 response models (`eval/pydantic-response-models`)

- **`pydantic>=2.0,<3.0`** added to `pyproject.toml` dependencies.
- **Pydantic response models** in [`analyzer.py`](analyzer.py) replace the
  six `frozenset *_REQUIRED_KEYS` presence checks in `_parse_or_retry` and
  `_parse_or_retry_streaming`:
  `AnalyzeResponse`, `GenerateResponse` / `GenerateNoCLResponse`,
  `ClarifyResponse`, `RecommendResponse`, `RecommendSummariesResponse`,
  `GenerateCorpusResponse` / `GenerateCorpusNoCLResponse`.
  Collateral models for the remaining callers:
  `CoverLetterOnlyResponse`, `CritiqueResponse`, `PromoteBulletResponse`.
- **`ExtractResponse`** in [`onboarding/extract_experiences.py`](onboarding/extract_experiences.py)
  mirrors the same pattern for the Haiku extraction call.
- `_parse_or_retry` and `_parse_or_retry_streaming` now accept
  `response_model: type[BaseModel]` (replaces `required_keys: frozenset[str]`).
  On `ValidationError`, the full Pydantic error text is appended to the retry
  prompt, giving the model richer feedback than the old "missing required keys" message.

---

## [1.0.1] — 2026-05-28

User-documentation overhaul + UX polish + bug fixes surfaced by a
Playwright-driven screenshot pass against a synthetic candidate,
plus an SSE streaming pass on `analyze()` and `generate()` for
perceived-latency improvement (R2). No prompt changes —
`PROMPT_VERSION` unchanged at `2026-05-24.4` (R1 split was attempted
and reverted; see "Attempted and deferred" below).

### Added — Performance (R2 streaming)

- **`/api/analyze/stream` and `/api/generate/stream` SSE routes**
  ([`app.py`](app.py)) — wrap the existing `_call_llm` /
  `_parse_or_retry` machinery with new streaming counterparts
  (`_call_llm_streaming`, `_parse_or_retry_streaming`,
  `analyze_streaming`, `generate_streaming` in
  [`analyzer.py`](analyzer.py)). Frontend consumes via a new
  `_consumeSSE` helper in [`static/app.js`](static/app.js) that
  parses Server-Sent Events off `fetch` + ReadableStream (POST-
  capable, unlike `EventSource`).
- **Spinner-default UX with collapsible "Show progress" toggle**
  on Step 1 (Analyze) and Step 5 (Generate). The token counter
  ticks during the call so the user knows the app isn't frozen;
  the raw stream is hidden by default and revealed via a small
  toggle button. `aria-live="polite"` regions announce progress
  to screen readers. Total LLM duration is unchanged; perceived
  latency improves from "90s of blank screen" to "alive within
  ~1s and showing progress throughout."
- **3 streaming tests** in [`tests/test_analyzer.py`](tests/test_analyzer.py)
  pin the chunk → retry → done event shape (happy path, retry-
  on-parse-failure, exhausted-retry failure).

### Added — `.claude-plugin/agents/headhunter.md`

- New subagent (Sonnet 4.6, restrictive tools: Read / Grep / Glob)
  for recruiting-domain quality consultations. Reasons from
  recruiting-domain expertise (10+ years placing engineers / PMs /
  SREs at mid-to-senior levels) to diagnose what would actually
  move a candidate from ATS-pass to scheduled interview. Returns
  recruiting-domain recommendations the engineer translates into
  prompt / schema edits; does NOT propose code or prompt fragments
  itself. Created in service of the R1 quality work and retained
  for v1.0.2's prompt-tune cycles.

### Attempted and deferred to v1.0.2 — R1 analyze split

- **R1 (split `analyze()` into Haiku extraction + Sonnet synthesis)**
  was attempted on 2026-05-26 with two iterations
  (`2026-05-26.1` naive split, `2026-05-26.2` atomic-extraction +
  `context_probe` clarify fix following a headhunter-agent
  consultation). Performance was a real win (analyze p50 103s →
  ~72s, ~30% reduction) but `clarification_quality` regressed on
  both pm-senior (4.2 → 3.2 → 2.1) and ds-junior (4.2 → 4.2 → 3.2)
  fixtures vs. the clean pre-R1 baseline. The "no quality loss"
  floor was hard-binding; the R1.2 code state is preserved on the
  `r1-attempted-2026-05-26` branch as the starting point for a
  focused v1.0.2 sprint using `/prompt-tune` smaller iteration
  cycles. Full diagnosis in [`evals/TUNING_LOG.md`](evals/TUNING_LOG.md)
  entries `2026-05-24.4 → 2026-05-26.1` and `2026-05-26.1 →
  2026-05-26.2`.

### Added — User documentation

- **`docs/walkthrough.md`** — screen-by-screen guide for first-time users.
  Two Mermaid flow diagrams (user-flow + information-flow), per-step
  educational depth ("What you see / What you do / Under the hood / Verify
  before continuing"), two human review gates explicit. Each step names the
  Flask route, the `analyzer.py` function, the model (Sonnet 4.6 vs.
  Haiku 4.5), cost band, latency. Includes a `## If something goes
  wrong mid-wizard` section covering tab-close / next-day return / LLM
  errors / start-over.
- **`docs/walkthrough_example.md`** — worked example threading a synthetic
  candidate (Priya, senior backend engineer) through all six wizard steps
  against a synthetic JD (Vertica Logistics Platform, Kafka-heavy). Concrete
  decisions per step, per-call cost table summing to ~$0.22.
- **10 wizard screenshots** embedded into [`README.md`](README.md) (1 hero),
  [`docs/install.md`](docs/install.md) (1 user-picker), and
  [`docs/walkthrough.md`](docs/walkthrough.md) (8 per-step). Captured at
  1440×900 light mode from a clean app state with the synthetic Priya
  corpus. Plain-git tracked (~1.2 MB total).
- **`docs/ux/onboarding_audit_2026-05-25.md`** — first UX audit pass via the
  new `ux-onboarding-designer` subagent. Seven fixed sections (Diagram
  Critique, Screenshot Manifest, Readability Pass, Decision-Point
  Inventory, Worked-Example Specification, Failure-Mode Coverage, Rewrite
  Ladder with 8 sequenced batches).
- **`docs/ux/screenshot_capture.md`** — capture checklist + filename
  convention + post-capture markdown-insertion pattern.
- **`scripts/capture_screenshots.py`** — Playwright harness that drives the
  wizard end-to-end against a synthetic corpus, captures the 10 manifest
  PNGs, and cleans up the demo user/artefacts. ~$0.27 per full run; runs
  via `python -m scripts.capture_screenshots --headless`.
- **`.claude-plugin/agents/ux-onboarding-designer.md`** — new subagent
  (Sonnet 4.6, restrictive tool list, scope-locked Write) for future UX
  audits of user-facing documentation. Auto-discovered from the
  `.claude-plugin/agents/` directory.

### Changed — Documentation polish

- **[`README.md`](README.md)** — canonical cost anchor (`<a name="cost">`)
  added so [`docs/install.md`](docs/install.md) and [`docs/walkthrough.md`](docs/walkthrough.md)
  link to a single source of truth instead of citing inconsistent ranges
  ($0.05–$0.10 vs. $0.15–$0.25 vs. $0.30–$0.50). LLM, JD, ATS, and corpus
  defined on first use in the README body (the walkthrough already had a
  glossary at line 28, but the README is read standalone). Line-5
  disclaimer rewritten in second person to remove the double negative.
  "The two human review gates" lifted to its own subsection so the load-
  bearing UX claim isn't buried under the wizard ASCII diagram.
- **[`docs/install.md`](docs/install.md)** — cost paragraph now links to
  the README anchor. "First-run walkthrough" intro flipped from
  reference-voice to teaching-voice ("By the end of these eight steps
  you'll have your first tailored résumé"). Ubuntu 22.04+ Playwright
  `apt install` fallback added (libnss3 / libatk1.0-0 / libxkbcommon0 /
  etc.). Commit-SHA reference dropped from the malformed-JSON
  troubleshooting entry. New Anthropic-API-error troubleshooting block
  covering 4xx/5xx, network drop, rate limit, key not picked up, and
  monthly cap.
- **[`vision.md`](vision.md)** — the "one question, honestly" quote
  lifted above the Purpose metadata block so the punch lands on the
  first screen. Acronym block under the H1 defining JD/LLM/ATS.
  `PERF_ANALYZE.md` link soft-gated as `(dev-facing)`.
- **[`docs/architecture.md`](docs/architecture.md)** — the four Mermaid
  diagrams (`pipeline.mmd`, `persistence.mmd`, `data-flow.mmd`,
  `llm-routing.mmd`) embedded inline so GitHub renders them natively.
- **AGENTS.md is now canonical**; [`CLAUDE.md`](CLAUDE.md) imports it
  via `@AGENTS.md` and layers only Claude-Code-specific overrides (skill
  catalog, plan-mode hook, `CLAUDE.local.md` machine-local file).

### Fixed — UI/UX

- **Corpus import button label** — `+ Drop résumé (AI extract)` →
  `+ Import résumé`. The old label conflated drag-and-drop (one input
  affordance) with the action, and the parenthetical leaked the AI-
  extract technique into a button label. The internal route
  `/api/users/<u>/import-legacy` keeps its name (route rename deferred
  to v1.1).
- **Wizard rail step 2 stays disabled after analyze** — `runAnalysis()`
  set `lastContextPath` but did not re-render the rail, so the step-2
  button stayed `disabled class="upcoming"` until the user clicked the
  in-flow "Continue to Clarify →" button. Now `runAnalysis()`'s success
  path calls `_wizardRender()` directly. `runGeneration()` was already
  fine via its existing `_wizardAdvanceTo(6)` call.
- **Bullet-dedup gap on same-file corpus re-import** — the dedup key
  flipped from `(source, text)` to `_normalize(text)` so the source-
  prefix flip from `primary:<file>` to `supplemental:<file>` on the
  merge path doesn't slip identical text through as a new bullet.
  Observed before the fix: a 22-bullet first import became 44 bullets
  on the second import of the same `.docx`.

### Fixed — Eval harness

- **Malformed judge JSON mis-categorized as `status=ok`** — when the
  judge's response wasn't parseable JSON, [`evals/runner.py`](evals/runner.py)
  returned `{"score": 0, "reasons": [...]}` without setting
  `status: "judge_error"`. The caller's `grade.setdefault("status",
  "ok")` then silently labelled the record as a successful grading,
  firing false-positive WARN regressions against the baseline. Now the
  return dict carries `"status": "judge_error"` and the existing
  `_detect_regression` / summary-roll-up skip path handles it.

### Changed — Observability

- **`_renderCorpusList()` and `_renderCorpusSummary()` wrapped in
  try/catch with element-presence guards + per-row guards.** A silent
  throw was observed during the screenshot pass (`_corpusExperiences`
  populated with length 3, DOM never updated, list `innerHTML.length`
  ~65 chars / placeholder-sized). The instrumentation surfaces any
  future trigger via `console.error`; root cause TBD on next repro
  with DevTools open. Workaround in
  [`scripts/capture_screenshots.py`](scripts/capture_screenshots.py)
  is `page.reload()` + re-select user, which clears the bad state.

### Tests

- **[`tests/test_onboarding_import_legacy.py`](tests/test_onboarding_import_legacy.py)** — 24/24 pass.
  `test_merge_dedupes_identical_bullet_text_across_sources` replaces
  `test_merge_skips_exact_duplicate_bullet_same_source` (which
  codified the bullet-dedup bug — its name said "skips" but its
  assertion expected `len == 2`).
- **[`tests/test_eval_runner.py`](tests/test_eval_runner.py)** — 25/25
  pass. New `test_unparseable_json_marks_status_judge_error` pins the
  `judge_error` categorization.
- **Full suite:** 633 passed in ~2 min. `ruff` + `mypy` clean.

### Carried forward to next release

Items tracked in [`docs/dev/RELEASE_CHECKLIST.md`](docs/dev/RELEASE_CHECKLIST.md) as
v1.0.1 "Should do (deferred)" / v1.1 work:

- Accessibility scan of all user-facing documentation (deferred actual
  scan; alt-text drafts already in screenshots).
- Playwright UX clickthrough regression suite under `tests/ux/` (specification only).
- Corpus tab render-after-refresh bug — root-cause chase pending a
  manual repro with DevTools open.
- Eval baseline re-cut against the v1.0.1 prompt landscape (the
  `baseline_v1.json` was sourced on `prompt_version=2026-05-12.1`;
  v1.0.1 ships on `2026-05-24.4`).

---

## [1.0.0] — 2026-05-25

**First public release.** Local-first résumé tailor with:
- Unified Corpus Item pattern (Bullet + SummaryItem + ExperienceTitle as variants-with-tags-with-score-with-recommend-call)
- JSON Resume v1.0 as canonical intermediate format
- Three output formats: `.md`, `.docx` (python-docx), `.pdf` (Playwright + Chromium)
- **Four curated bundled persona templates**, all ATS-safe by construction — `classic` (Arial 11pt baseline), `modern` (rebuilt from the official jsonresume-theme-class with blue accent header band), `spacious` (Arial 11pt with generous whitespace for early-career), `tech` (rebuilt from jsonresume-theme-dev-ats with Georgia serif + centered name + underlined sections for engineering / data / AI roles). Compact and Hybrid Tech retired as not-actually-ATS-safe (sidebar layouts / inline `<code>` chips both break parsers).
- ATS-safety badges on every template card in the Template step UI — green "ATS · safe" for the 4 bundled templates; neutral "ATS · unverified" for user-uploaded `.docx` files (which we can't introspect)
- **Real in-iframe pagination** via paged.js (MIT v0.4.3, self-hosted at `static/vendor/paged.polyfill.js`) — preview shows discrete Letter-sized page boxes, not a scroll-height estimate. The "Page 1 of N" toolbar reflects the real count via postMessage.
- Live HTML preview, corpus-direct (no sidecar dependency); surfaced in Step 4 (Template) and Step 6 (Output). The Step 3 (Compose) preview was removed after hands-on testing showed it competed for attention with the bullet-curation work.
- Six-step wizard: Job → Clarify (opt) → Compose → Template → Generate → Download
- Cover-letter detachment (opt-in, post-résumé) with full refine/iterate parity
- Iterative refinement with edit-aware baselines and per-iteration audit trail
- LLM eval harness with 0.0–5.0 rubric scoring (`baseline_v1.json` pinned)
- Read-only `/_dashboard` blueprint for score trends, cost cards, failure-mode clustering

**Visual assets** (screenshots, demo GIF, onboarding HTML page) deferred to v1.0.1, after the planned UI redesign — see [`docs/PRODUCT_SHAPE.md §10`](docs/PRODUCT_SHAPE.md) for the full v1.0.1 / v1.1 / v2 deferred list.

### Changed — Phase β.6 post-review: corpus-direct live preview + PDF format + ubiquitous iframe (2026-05-24)

The β.6 hands-on review surfaced five issues, three of which shared an
architectural root cause: the live preview was coupled to a generate-
time `resume_*.jsonresume.json` sidecar, so it couldn't render until
the user had paid for at least one `/api/generate` and afterwards
reflected the last-GENERATED résumé even as the corpus kept changing.
This commit breaks that coupling and tightens the surrounding surface.

- **`corpus_to_json_resume.build_json_resume_from_corpus(session, candidate_id, *, application_id=None, context_path=None)`** — new module that builds a JSON Resume v1.0 document directly from `Candidate` + `Experience` + `Bullet` + `SummaryItem` rows. Resolves the chosen SummaryItem variant through the priority chain pinned > recommended > first-active > `Candidate.profile_text` and applies `composition_overrides` (pin / exclude / added, `pinned_summary_id`) + `llm_recommendations` from `context_path` when present. Corpus-only fields (chosen variant id, `summary_source`, `bullet_overrides_active`) live under `meta.callback.*` so themes that don't know about callback. extensions ignore them. 18 new tests in `tests/test_corpus_to_json_resume.py` pin the resolution chain, the bullet override math, the soft-retire skip behavior, and the empty-document fallback.
- **`/api/applications/<id>/preview` refactored** — now reads from the corpus builder instead of locating a sidecar. Drops the 409 `needs_generate` path entirely; the preview works before any generate has run. Accepts an optional `context_path` query param (validated under `OUTPUT_DIR` via `_within`) so composition state shapes the preview output.
- **`/api/users/<u>/preview` added** — the same render pipeline scoped to a user without an application. Answers the "let me see how my résumé looks through Classic / Modern" question from the Library / pre-application flow. 409 surfaces `needs_onboarding=true` when a config exists but no candidate row.
- **`_inline_persona_css` extracted** — pulls the `<link rel="stylesheet">` inlining out of the preview route body so the two preview routes share it. `_latest_jsonresume_sidecar` removed; nothing in `app.py` reads sidecars anymore.
- **PDF output format** — Step 5's format picker gains a PDF button alongside DOCX / Markdown. `/api/download-edited` now accepts `.pdf` and threads the persona's HTML+CSS companions through `generate_resume` → `pdf_render.render_pdf`. Falls back to the bundled Classic HTML when the chosen persona doesn't ship an `.html` sibling yet (same fallback the in-process generator uses).
- **Live preview ubiquitous in the wizard** — Compose (Step 3) and Output (Step 6) gain inline preview iframes alongside the existing Template (Step 4) iframe. Compose's refreshes after every pin / exclude / add (driven through `loadComposition` → `_refreshComposePreview`); Output's refreshes after every generate (`_onGenerationComplete` → `_refreshOutputPreview`). All three iframes consume the same corpus-direct route, so the WYSIWYG promise holds across steps.
- **Replaced the "PREVIEW WITH MY RESUME" .docx download** — Library tab's button label is now `OPEN PREVIEW` and opens the corpus-direct HTML in a new tab via `window.open(/api/users/<u>/preview?template_id=<id>)`. Step 4's redundant button removed; the inline iframe right below the template grid already updates on every card click.
- **PROMPT_VERSION unchanged** — no LLM prompts touched in this commit.
- **Tests** — `tests/test_live_preview_route.py` rewritten end-to-end against the new corpus-direct shape (11 cases: happy path from corpus, CSS inline, pinned-summary override via `context_path`, 404 / 400 failure modes, explicit `template_id`, the new `/api/users/<u>/preview` route). Project test count 605 → 627; `ruff` + `mypy` clean.

### Added — Phase D: Career Corpus + Candidate Memory Frontend (2026-05-14)
- **Top-level tab navigation** — four tabs replace the prior single-page layout: APPLICATION (the legacy job-flow, still wired to the file-based pipeline pending Phase F), CAREER CORPUS, PERSONA TEMPLATES, CANDIDATE MEMORY. Tabs reuse the LCARS palette; `switchTopTab()` is the central dispatch (`static/app.js`).
- **Career Corpus tab (D.1 + D.2 + D.6)** — DB-backed editor for experiences, bullets, alternate titles. Compact card list sorted by `start_date DESC` with click-to-expand; inline edit on every scalar field with save-on-change toasts; per-title atomic SET OFFICIAL that clears the prior official sibling (matches the schema's partial unique index); per-bullet auto-detect of `has_outcome` via `METRIC_RE` on save; soft-retire (`is_active=0` / non-eligible flags) preserves the `application_bullet` audit chain. Pending-review banner at the top of the tab pulls aggregate counts from `GET /api/users/<u>/pending-counts` and surfaces a REVIEW NOW button that expands + scrolls to the first card with pending content. Per-row ACCEPT and per-experience ACCEPT ALL PENDING buttons appear only when relevant content is pending.
- **Applications tab (D.3)** — within the APPLICATION tab, a PRIOR APPLICATIONS panel above the legacy chip UI lists every `application` row newest-first with status chip (color-coded across the five `application.status` values), iteration count, pending-proposal violet badge, and relative timestamp. Detail click surfaces a summary toast; resuming an application into the live editing flow defers to D.3.1.
- **Persona Templates tab (D.4)** — two-section gallery: BUNDLED (the 5 ATS-safe templates shipped in C.1, read-only DOWNLOAD) and MY TEMPLATES (user-uploaded `.docx` files with DOWNLOAD / RENAME / DELETE). Upload widget validates `.docx` and is disabled until a user is selected. Thumbnails + "set default per role tag" defer to a follow-up.
- **Candidate Memory tab (D.5)** — searchable index of every `clarification` row. 250 ms-debounced text search across question + answer; kind dropdown; outcome-rich-only toggle (`METRIC_RE` match); show-promoted toggle (hidden by default). Each card: KIND chip, OUTCOME flag (when applicable), PROMOTED badge (after promotion), origin application title, relative date; PROMOTE TO BULLET button prompts for an experience and calls the existing B.4 endpoint.
- **Backend routes added in Phase D**:
  - D.1: `GET/POST /api/users/<u>/experiences`, `GET/PUT/DELETE /api/experiences/<id>`, `POST /api/experiences/<id>/bullets`, `PUT/DELETE /api/bullets/<id>`, `POST /api/experiences/<id>/titles`, `PUT/DELETE /api/experience-titles/<id>`, `GET /api/users/<u>/tags` (autocomplete by usage count)
  - D.3: `GET /api/users/<u>/applications`, `GET /api/applications/<id>`, `PUT /api/applications/<id>/status`
  - D.5: `GET /api/users/<u>/clarifications` (q / kind / only_outcome_rich / include_promoted filters)
  - D.6: `POST /api/bullets/<id>/accept`, `POST /api/experience-titles/<id>/accept`, `POST /api/experiences/<id>/accept-all`, `GET /api/users/<u>/pending-counts`
- **Security model preserved** — every mutating route validates the candidate via `_safe_username(candidate.username)` before any write; the existing `_within()` guard continues to gate persona file writes; soft-retire (`is_active=0`) is preferred to hard-delete on bullets and titles so historical `application_bullet` / `application_run_title` joins keep their referential integrity.
- **XSS hygiene** — the new tab DOM is constructed via a small `_el(tag, props, children, attrs)` helper that uses `textContent` exclusively. No new `innerHTML` writes on user-derived values across Phases D.1–D.6.
- **Tests** — 73 new cases across `test_career_corpus_routes.py` (D.1, 35), `test_application_routes.py` (D.3, 11), `test_clarifications_list.py` (D.5, 9), `test_pending_review_routes.py` (D.6, 9). Total project test count now 446; `ruff` + `mypy` + `pytest` all clean.
- **Deferred follow-ups**: interactive tag chip editing (D.2.1), resume-application-into-edit-flow (D.3.1), persona thumbnails + per-role-tag defaults (D.4.1), focused walk-through review modal (D.6.1). Phase F will delete the file-based primary/supplemental chip UI in `static/app.js` and the corresponding `app.py` plumbing.

### Added — Iterative Refinement Loop with Edit-Aware Baselines (2026-05-11)
- **Iteration data model in `hardening.py:ContextSet`** — seven new optional fields (`iteration`, `parent_context_path`, `edited_resume_text`, `edited_cover_letter_text`, `iteration_notes`, `last_generated_resume`, `last_generated_cover_letter`), all `total=False` so pre-iteration saved contexts continue to round-trip. `save_iteration_context()` helper deep-copies a parent into a new timestamped child file (`context_{ts}_iter{N}.json`), increments the counter, links via `parent_context_path`, snapshots the freshly generated text, consumes any pending edits, and appends an `iteration_note` for audit. The chain of parent_context_path pointers is the iteration audit trail.
- **`_supplemental_block(iteration=0)` in `analyzer.py`** switches its wrapper to `<historical_resumes>` at iteration ≥ 1, folding the original primary in alongside supplementals under demotion language ("EARLIER VERSIONS ... NEVER let a historical resume override or contradict the current draft"). The `<resume>` block in the cached prefix becomes the current draft via `_current_draft_text()` (precedence: edited > last_generated > primary). `_current_cover_letter_draft()` provides the parallel for the cover letter, surfacing as a `<current_cover_letter_draft>` prompt block when iterating. `generate()` widens the grounding check to accept first-person typed edits as ground truth, with a new OK/NOT-OK worked example: "Shipped V2 to enterprise" — typed edits are citable but never extensible with specifics the candidate didn't write.
- **`clarify_iteration()` in `analyzer.py`** — fourth LLM call kind (`call_kind="iterate_clarify"`) using a dedicated `CLARIFY_ITERATION_SYSTEM_PROMPT`. Takes four signal sources documented in the plan: current draft (resume + cover letter), `recent_edits_summary` (short unified diff), `deterministic_signals` (verb diversity / specificity / grounding overlap / keyword coverage on the current draft), and `prior_clarifications` (paired question + answer for already-confirmed truths the LLM must build on, not re-ask). Introduces `iteration_probe` as a third question kind alongside `experience_probe` / `scope_probe`.
- **Three new Flask routes in `app.py`**: `POST /api/save-edits` (stores typed edits on the current context, no iteration advance, appends an iteration_note); `POST /api/iterate-clarify` (rejects iteration-0 contexts with a 400 pointing at `/api/clarify`, computes signals via `summarize_recent_edits` + `compute_iteration_signals`, calls `clarify_iteration`, appends questions with iteration-prefixed ids `iter1_q1` / `iter2_q1` so they don't collide with prior `/api/clarify` ids); `POST /api/generate` updated to write a NEW iteration context per call via `save_iteration_context` (rather than mutating in place) and return `context_path` / `iteration` / `parent_context_path` so the frontend adopts the latest snapshot.
- **`summarize_recent_edits` and `compute_iteration_signals` in `hardening.py`** — pure deterministic helpers shared between the live `/api/iterate-clarify` route and the eval harness's iteration phase. The diff helper caps at ~60 unified-diff lines per document so prompt tokens stay predictable when users rewrite large sections.
- **Frontend iteration UI** — `templates/index.html` adds a violet iteration counter pill in the top bar (hidden until iteration ≥ 1), a `GET INTERVIEW QUESTIONS` button next to `REFINE` in the Output panel, an `iterateClarifyArea` panel below the refinement controls, and an edit-detection modal (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`). `static/app.js` adds iteration state (`currentIteration`, `lastGeneratedResume`, `lastGeneratedCoverLetter`), `_detectEdits` / `_showEditModal` (Promise-based with focus trap, Esc cancel, focus restored to trigger), `_gateEditsBeforeAction` common gate used by both REFINE and INTERVIEW QUESTIONS, `runIterateClarify` / `_renderIterateClarifyQuestions` / `submitIterateClarificationsAndGenerate` / `skipIterateClarifications`, and `_onGenerationComplete` which adopts the new `context_path` per iteration. `_resetIterationState` runs on user switch and on fresh analyze so edit-detection doesn't compare against stale prior-run baselines. CSS adds `.iteration-pill`, `.iterate-clarify-area`, `.clarify-kind-badge.iteration` (teal), `.lcars-modal*` with backdrop and slide-in animation respecting `prefers-reduced-motion`.
- **Latent bug fix in `static/app.js:runGeneration`** — `refinement_notes` serialization stringified `{note,status}` entries as `"[object Object]"`. The bug was dormant (only fired with non-empty `refinementHistory`, which never happened in pre-iteration paths) but the new iterate-clarify→regenerate flow exposed it. Now filters to applied notes and uses the same shape as `submitRefinement`.
- **Accessibility pass** — skip link as first focusable, hidden `aria-live="polite"` `#srAnnounce` region with sparse meaningful announcements (analysis complete, questions ready, iteration ready, edits saved), `aria-live="polite"` on `#statusPill`, `aria-busy="true"` on the active panel during long-running LLM calls, `aria-label` on the iteration pill, `for`/`id` association on every Config form label, `aria-label` on user/JD inputs, `role="textbox" aria-multiline="true" aria-label aria-describedby` on contenteditable previews, `role="tablist"`/`role="tab"`/`aria-controls`/`aria-selected` on output tabs (with `aria-selected` maintained by `showTab`), `:focus-visible` outline rings on `.lcars-btn`, `.tab-btn`, `.view-btn`, `.format-btn`, inputs, `.preview-editable`, and `.file-chip`. The hidden `#resumeSelect` is now `aria-hidden="true" tabindex="-1"`. Manual NVDA/VoiceOver smoke pass, 200% zoom layout reflow, and color-contrast verification of the LCARS palette must be done by a human and documented when complete.
- **`evals/rubrics/iteration_quality.md`** — fifth rubric grading whether iteration questions build on prior clarifications (no `redundant_question`), reference recent edits when present (no `missed_recent_edit`), target current-draft weaknesses (no `targets_stale_draft`), and cite signal-source values accurately (no `fabricated_gap`). Same 0.0–5.0 scale and slug taxonomy as `clarification_quality.md`.
- **`evals/runner.py` iteration phase** — when a fixture has `iteration_scenarios` in `expected.json` AND `iteration_quality` is in the rubric set, the runner: (a) applies the scripted edit_target_substring → edit_replacement to the freshly generated resume, (b) builds an iteration-1 context via the same shape `save_iteration_context` would write, (c) calls `clarify_iteration` with the four signal sources, (d) grades the questions against `iteration_quality`. Re-generation from the iteration context plus re-grading against grounding/keyword_coverage is deferred to a follow-up — see the 2026-05-11.2 TUNING_LOG entry. When the scenario edit_target_substring isn't found in the LLM's actual output, the runner emits a `scenario_misaligned` row (rather than silently degrading) so the dashboard surfaces the misalignment.
- **`evals/fixtures/synthetic/sre-mid-level/expected.json`** gains `iteration_scenarios` with one scenario (`user_typed_slo_ownership`) and `expected_iteration_themes` lists tailored to it, plus `min_iteration_quality_score: 4`. The other two fixtures defer to the next eval cycle.
- **`PROMPT_VERSION` 2026-05-11.1 → 2026-05-11.2** because the new `CLARIFY_ITERATION_SYSTEM_PROMPT` shipped, the generate prompt grew the `<current_cover_letter_draft>` block and the typed-edits worked example, and `_supplemental_block` produces a different prompt at iteration ≥ 1.
- **49 new tests across `test_hardening_iteration.py`, `test_analyzer_iteration.py`, `test_app_iteration.py`** covering `save_iteration_context` lineage and edit consumption, `_supplemental_block` demotion, `_current_draft_text` precedence, `generate` consuming edited text and including the cover-letter-draft block, `clarify_iteration` system prompt threading and signal-source inclusion, `/api/save-edits` security guards, `/api/generate` writing a new iteration file with parent_context_path, `/api/iterate-clarify` rejecting iteration-0 contexts, prefix-renaming question ids to avoid collisions, and threading the four signal sources to the clarifier. All 178 tests pass.

### Added — Optional Clarification Interview Between Analyze and Generate (2026-05-11)
- **`clarify()` in `analyzer.py`** — third LLM call (optional, between `analyze()` and `generate()`) that produces 3-5 targeted questions: experience probes surfacing JD-required skills missing or weak in the resume, and scope probes disambiguating ambiguity flagged by the analyzer. Uses a dedicated short `CLARIFY_SYSTEM_PROMPT` rather than the hiring-manager `SYSTEM_PROMPT` — narrower task, tighter grounding, cheaper tokens. Reuses `_parse_or_retry` for telemetry parity; emits `call: "clarify"` in `logs/llm_calls.jsonl`.
- **`POST /api/clarify` and `POST /api/answer-clarifications`** in `app.py`, between the existing `/api/analyze` and `/api/generate`. Both routes use the standard `_safe_username` + `_within(OUTPUT_DIR)` security guards. Questions and answers persist back to the same `context_*.json` file (no new timestamped files) so the UI is refresh-safe and `/api/generate` picks up clarifications by simply reloading the existing context. `run_id` propagates from analyze through clarify to generate so all three calls share a correlation key.
- **`generate()` injects `<candidate_clarifications>` block** when `context_set["clarifications"]` is non-empty. The grounding check widens to accept clarification answers as first-person ground truth — citable in the resume even when not present in the source — but the no-invention rule still applies beyond the union of (resume + clarifications).
- **`ContextSet` TypedDict gained two optional fields** in `hardening.py`: `clarification_questions: list[ClarificationQuestion]` and `clarifications: dict[str, str]`. Both `total=False` so pre-clarify saved contexts continue to round-trip without errors. New regression test in `test_hardening.py::TestContextSetClarificationFields` proves both directions.
- **Frontend "Clarifying Interview" panel** inside the existing Analysis panel: `templates/index.html` adds a collapsible section with `GET CLARIFYING QUESTIONS` / `SUBMIT ANSWERS & GENERATE` / `SKIP` controls. `static/app.js` adds `runClarify()`, `submitClarificationsAndGenerate()`, `skipClarifications()`, and a `_renderClarifyQuestions()` helper that uses safe DOM construction (`textContent`, `appendChild`) for all LLM-supplied strings — defense-in-depth on top of `esc()`. `static/style.css` adds the violet-accented divider and question-card styles, with amber `SCOPE` badges to visually distinguish scope from experience probes.
- **`evals/rubrics/clarification_quality.md`** — new rubric grading question composition (3-5 total, ≥50% experience probes), gap citation specificity (must cite a concrete source from `essential_skills`, `comparison.gaps`, `keyword_placement`, or `keyword_overlap.missing_from_resume`), word limit (≤25 per question), no compound or leading questions, and theme coverage against the new `expected_clarification_themes` field on each fixture.
- **`evals/runner.py` runs `clarify()` between analyze and generate** on every fixture; if clarify fails, the runner logs a warning, emits a `pipeline_error` row for `clarification_quality`, and continues with the existing four rubrics ungated. The clarification questions are added to every per-rubric payload (other rubrics ignore them).
- **`evals/fixtures/synthetic/{data-scientist-junior,pm-senior,sre-mid-level}/expected.json`** each gained `expected_clarification_themes` with `experience_probes` and `scope_probes` lists tailored to the fixture's real gaps, plus `min_clarification_quality_score: 4`.
- **`_call_llm` and `_parse_or_retry` gained an optional `system_prompt` arg** so narrowly-scoped calls like `clarify` can override the hiring-manager persona without code duplication. Default behavior unchanged; the existing `analyze()` and `generate()` calls keep using `SYSTEM_PROMPT` and continue to hit the system-block prompt cache.
- **`PROMPT_VERSION` 2026-05-09.3 → 2026-05-11.1** because new system prompt, new prompt template (clarify), and the generate prompt grew the `<candidate_clarifications>` injection point.
- **New tests**: `tests/test_app_clarify.py` (route handlers, security guards, persistence, idempotency, ID filtering); `tests/test_analyzer.py` expanded with `clarify()` happy-path, retry, `system_prompt` threading, and generate's three injection paths (present, absent, all-skipped); `tests/test_hardening.py` round-trip regression for ContextSet with and without the new fields. All 129 tests pass.

### Added — Response Validation & Typed Context (2026-05-09 follow-up)
- **`_parse_or_retry` helper in `analyzer.py`** replacing the silent `{"raw_response": raw, "parse_error": True}` fallback in `analyze()` and `generate()`. The helper strips markdown fences, runs `json.loads`, and checks the response against a per-call `frozenset` of required keys (`ANALYZE_REQUIRED_KEYS`, `GENERATE_REQUIRED_KEYS`). On `JSONDecodeError` or missing keys, it re-prompts via `_call_llm` with a `<retry_reason>` block appended (`call_kind="<kind>_retry"`) — the cached user prefix is byte-identical so the retry hits prompt cache and adds ~1 cached read instead of full input tokens. After `max_attempts=2` failures it raises `LLMResponseError(raw, validation_error)` rather than degrading silently.
- **`LLMResponseError` exception** carrying the raw response and validation error. Handled in `app.py` at both LLM call sites — returns HTTP 502 with a user-readable message and the validation detail. The eval runner's existing `except Exception` block catches it and records `pipeline_error` unchanged.
- **`ContextSet` `TypedDict` and four nested TypedDicts (`CandidateInfo`, `ResumeInfo`, `SupplementalResume`, `DeterministicAnalysisBlock`)** in `hardening.py`. `build_context_set` now returns `ContextSet`; `analyze`, `generate`, `_stable_user_prefix`, `_supplemental_block`, `save_context_set`, and the `context_set` locals in `app.py` and `evals/runner.py` are all annotated. mypy now catches field-name typos at access sites instead of letting them surface as runtime `KeyError`s. No new runtime dependency — pure stdlib `typing.TypedDict`. The two app-added keys (`llm_analysis`, `run_id`) are expressed via a `total=False` subclass rather than `typing.NotRequired` to keep Python 3.10 compatibility (`NotRequired` is 3.11+).
- **12 new unit tests** in `tests/test_analyzer.py` covering `_strip_fences` across five fence patterns and `_parse_or_retry` happy path, fence-stripped happy path, missing-key recovery, invalid-JSON recovery, missing-key exhaustion, invalid-JSON exhaustion, and `_retry` call_kind attribution. Mocks `analyzer._call_llm` directly — no Anthropic SDK in the test path.
- **`PROMPT_VERSION` 2026-05-09.2 → 2026-05-09.3** because retry attempts now carry a `<retry_reason>` block in the per-call user prompt, and JSONL telemetry uses `prompt_version` for attribution.
- **`_strip_fences` consolidates** the previously-duplicated fence-stripping logic that lived in both `analyze()` and `generate()`. Net deletion of ~16 lines. Uses a single regex (`^```(?:[a-zA-Z]+)?\s*\n?(.*?)\n?\s*```$`) that handles multiline and single-line fenced blocks with or without a language tag.

### Added — Eval & Dashboard Gap-Closing (2026-05-09 follow-up)
- **`run_id` correlation** between `logs/llm_calls.jsonl` and `evals/results/*.jsonl`. The runner mints one 12-hex UUID per fixture pipeline; both the analyze and generate calls share it in telemetry, and every per-rubric eval result inherits it. Live `app.py` traffic also generates run_ids and persists them on the saved `context_set` so `/api/analyze` and `/api/generate` from a single user session correlate. New "Run" column in both dashboard tables.
- **p50 / p95 latency and per-call cost percentiles** in `_summarize_calls`. A new `_percentile` helper does linear-interpolation percentiles over sorted lists. Surfaces tail behavior that means alone hide.
- **Local regression alerting** in `evals/runner.py`. Before a run starts, `_load_baseline_scores` walks every prior result file and builds a `{(fixture, rubric): most_recent_record}` baseline. After each grading, `_detect_regression` compares the new score to baseline; drops greater than `REGRESSION_DELTA` (default 0.5, env-overridable via `REGRESSION_DELTA`) log a `WARNING` with the prior `prompt_version` and accumulate into an end-of-run summary table.
- **`evals/rubrics/keyword_coverage.md` "covered in cover letter" rule** for keywords that match `expected.forbidden_inventions` (domain experience the candidate genuinely lacks). Prevents the no-win situation where the model is forced to choose between fabricating experience (loses grounding) or omitting keywords (loses keyword_coverage). The judge now credits a B2B PM applying to healthtech for placing `EHR` and `HIPAA` in the cover letter as transferable understanding rather than fabricated experience.
- **`SYSTEM_PROMPT` "metrics" rule expanded** with concrete examples: counts ("three reports"), durations ("one year", "monthly cadence"), team or scope sizes, GitHub stars, frequencies ("week over week", "24/7 on-call"). The previous narrower rule was being read as "only %s and $s" and dropping legitimate small numbers. `PROMPT_VERSION` 2026-05-09.1 → 2026-05-09.2.
- **TUNING_LOG entry for 2026-05-09.2** documenting the gap-closing iteration: 12/12 still pass, two +0.5 improvements, two -0.6 tone "regressions" flagged by the new alerter (within Haiku judge variance band; to be confirmed across the next 2-3 runs).
- **13 new unit tests** for `_normalize_eval_record` run_id default, `_percentile` interpolation/edge-cases, `_summarize_calls` percentile fields, `_detect_regression` baseline behaviors, and `_load_baseline_scores` excluding the current file. 96/96 tests passing total.

### Added — Eval & Dashboard Refinement (2026-05-09)
- **Float scoring (0.0–5.0, one-decimal precision)** across all four rubrics. Replaces the previous integer 0–5 scale; same band semantics, ~10× the granularity. The Haiku judge can now express "stronger than 4 but short of 5" as `4.3` instead of collapsing to `4` or `5`. Rationale: integer scoring hid real prompt-tuning progress and forced false equivalence between near-passing and clean-passing runs.
- **`schema_version` field** on every eval result (`schema_version: 2`). Old integer-score records load through `dashboard.routes._normalize_eval_record` which coerces them to floats and fills defaults; stored files are never rewritten.
- **Four deterministic post-generation metrics in `hardening.py`** computed on every eval run:
  - `compute_verb_diversity` — unique leading verbs / total bullets; flags repetition that the SYSTEM_PROMPT already discourages
  - `compute_specificity_density` — fraction of bullets containing a quantifier; pairs with grounding (high density + low grounding = invented numbers)
  - `compute_grounding_overlap` — 3-gram overlap between generated output and source. Returns up to 10 `missing_samples` 3-grams that the LLM produced but source doesn't contain — these are the actionable fabrication signals. Stopword-only n-grams excluded.
  - `compute_call_cost` — per-call USD using a `MODEL_PRICING` table for Sonnet 4.6 and Haiku 4.5
- **`prompt_version`, `deterministic_metrics`, `cost_usd`, `pipeline_latency_ms` fields** on every eval result, enabling regression attribution to specific prompt revisions.
- **Dashboard charts and aggregations** (no new Python deps; Chart.js loaded from CDN):
  - Per-rubric pass-rate bar chart
  - Score-over-time line chart with per-point `prompt_version` tooltip
  - Rubric × fixture heatmap (HSL color, red→green)
  - Top failure-modes table (per-record dedup of `failed_rules` slugs)
  - Total-cost and mean-cost-per-call summary cards
  - Graceful degradation: heatmap and failure-mode table render server-side; only bar/line charts require JS
- **Anti-invention prompt edits** in `analyzer.py` (`SYSTEM_PROMPT` and `generate()` GROUNDING CHECK): three new ALWAYS/NEVER rules and three OK/NOT-OK worked-example pairs targeting the failure patterns observed on `data-scientist-junior` (advanced-technique substitution, tool-vendor specificity, scope adjective escalation). `PROMPT_VERSION` bumped from `2026-05-06.5` to `2026-05-09.1` in the same commit.
- **`evals/TUNING_LOG.md`** — institutional-memory document recording each prompt iteration with what changed, why, scores before/after, and what we learned. Seeded with the 2026-05-09 anti-invention iteration (12/12 pass on synthetic suite, $1.46 total cost).
- **`dashboard/README.md`** — what the dashboard shows, how to launch it, schema-version compatibility notes, instructions for adding a new chart.
- **35+ new unit tests** (`tests/test_eval_runner.py`, extended `tests/test_hardening.py`, new `tests/test_dashboard_routes.py`) covering float coercion at the judge boundary, deterministic-metric edge cases, dashboard aggregations, and graceful-degradation rendering with no eval data.
- `pyproject.toml` replacing `requirements.txt` (pinned dep ranges + `[dev]` extras)
- `tests/` with 28 unit tests covering the deterministic helpers and path-traversal defenses
- GitHub Actions CI workflow (`ruff` + `mypy` + `pytest`, label-gated synthetic eval smoke)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub issue and PR templates
- `.claude-plugin/` scaffold: `plugin.json` manifest, three migrated plan-mode hooks, five new deterministic hooks (`block-secrets`, `ruff-changed`, `block-merge-to-main`, `validate-context`, `route-security-lint`)
- Three project subagents: `eval-judge` (Haiku, grading), `prompt-archaeologist` (Sonnet, prompt-failure diagnosis), `git-flow` (Sonnet, conventional-commit workflow)
- Five project skills: `/eval`, `/replay`, `/prompt-tune`, `/bench`, `/inspect-context`
- Eval harness under `evals/`: `runner.py`, four rubrics (grounding, keyword_coverage, ats_format, tone), three synthetic fixtures (sre-mid-level, pm-senior, data-scientist-junior), JSON Schema for `context_set`
- LLM telemetry: `analyzer.py` emits one JSONL record per call to `logs/llm_calls.jsonl` with timestamps, tokens (including `cache_creation_input_tokens` / `cache_read_input_tokens`), latency, prompt version, status
- Prompt caching: stable user-message prefix (resume + JD + supplementals + candidate profile) sent as a cacheable text block per call. Verified live: ~4,300 cached input tokens read on every generate call within the 5-minute TTL, ~37% input-token cost reduction across an analyze + generate + refinement-generate sequence
- Template-faithful docx output: `generator._write_docx` now walks the original resume's first ~30 paragraphs and captures formatting prototypes per role (name, subtitle, contact, section_heading, job_title, job_subtitle, body), then applies them to the matching markdown elements. Right-aligned date column on `### ` lines is preserved via the captured tab stop. Required for templates that use direct paragraph formatting rather than Word named styles.
- Dashboard blueprint at `/_dashboard` reading the JSONL telemetry and eval results into two filterable tables; localhost-only
- `PROMPT_VERSION` constant in `analyzer.py`; bumped on any `SYSTEM_PROMPT` change so eval results trace to a specific revision
- Project allowlist in `.claude/settings.json` for the `ruff`/`mypy`/`pytest`/`pip show` dev loop

### Changed
- `app.py` Flask debug flag is now env-driven (`FLASK_DEBUG`, default-on for dev). Set `FLASK_DEBUG=0` to disable for any future hosted deployment.
- Type annotations cleaned up across `analyzer.py`, `generator.py`, and `parser.py` to satisfy `mypy --strict-optional`.
- `CLAUDE.md` is now project-shared (committed) — was machine-local. Per-clone overrides moved to `CLAUDE.local.md` (gitignored).
- `.claude/launch.json` removed from tracking (had a hardcoded Windows path); kept locally and gitignored.
- `.gitignore` rewritten for `.claude/*` allow-list pattern: future Claude Code internals (worktrees, caches) auto-ignored; only `settings.json` is tracked.
- README install commands now use `pip install -e .` instead of `pip install -r requirements.txt`.
- README gains a "Claude Code Plugin" discovery section listing all commands, agents, and hooks.
- Hook wiring lives in `.claude/settings.json` rather than the plugin manifest, since Claude Code v2.1.131 in VSCode doesn't support `/plugin install` for local paths. The `.claude-plugin/` layout is preserved for future marketplace publication.
- `analyzer.py:MODEL` upgraded from `claude-sonnet-4-20250514` (May 2025 Sonnet 4) to `claude-sonnet-4-6`. Same per-token price; better structured-output adherence and instruction-following on the long generate prompt. Rationale comment added near the constant documenting the model-selection trade-offs (Sonnet for analyze/generate, Haiku for high-volume structured grading, no Opus for cost reasons). `PROMPT_VERSION` bumped to `2026-05-06.5` so telemetry distinguishes pre-/post-bump runs.
- `analyzer.py:MAX_TOKENS` raised from 4096 to 8192. Sonnet 4.6's analyze() output is more verbose than older Sonnet 4 was on detail-rich real inputs and was hitting the 4096 cap mid-JSON, surfacing as a downstream "non-JSON response" error. 8192 leaves headroom; the model still uses what it needs.

### Removed
- `requirements.txt` (superseded by `pyproject.toml`)

### Fixed
- `generate()` prompt now requires explicit `# / ## / ### / -` markdown markers on resume_content output. Without these markers the document writer fell back to undifferentiated plain paragraphs, losing template heading visual styles. Prompt was unchanged across the v0.1.x line; making the marker requirement loud is the fix.
- `_write_docx` no longer materializes empty markdown lines as empty paragraphs. The resulting double-gap between `## SECTION` headings and their body content was visible in every multi-section docx output. Templates' per-paragraph `space_after` provides the visual rhythm; empty paragraphs were stacking on top of it.
- `_call_llm` now logs a warning and records a `stop_reason` field in `logs/llm_calls.jsonl` whenever the model hits `max_tokens`. Previously a truncated JSON response surfaced as a confusing parse error in the UI; now truncations are visible directly in the telemetry stream.

### Known issues
- Junior-level fixtures (e.g., `evals/fixtures/synthetic/data-scientist-junior`) can score below the grounding rubric's pass threshold of 4 due to the model inflating an analyst's actual scope to match a more senior JD (slugs: `scope_inflation`, `verb_overreach`, `invented_metric`). Pre-existing across the v0.1.x line — surfaced for the first time by the new eval harness. To be addressed via prompt tightening in v0.2.1; the `prompt-archaeologist` subagent is the intended workflow.

---

## [0.1.0] — 2026-05-06

Initial public release.

### Added
- Two-call LLM pipeline (`analyze()` + `generate()`) producing tailored resume + cover letter from a job description
- Refinement scope validation via Haiku classifier
- Streaming LLM calls for warm-connection long-running generations
- Multi-resume source pool with primary/supplemental selection in the UI
- Full candidate profile injection into both LLM calls (skills, certifications, education, notes, scraped LinkedIn/portfolio content)
- Deterministic hardening layer: keyword extraction, ATS format checks, keyword overlap scoring, context-set assembly
- Resume parsing for `.docx`, `.pdf`, `.md` with section inference
- Document generation preserving the original `.docx` as a style template
- Two human-gated review checkpoints (analysis review, output review) per the P8 Strategic Human Gate principle
- LCARS-styled single-page UI
- MIT license, comprehensive `.gitignore`, `SECURITY.md`, `README.md`, `vision.md`
