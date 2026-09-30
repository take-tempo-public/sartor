# Product shape — historical sections

> **Archived 2026-09-30 (Epic D, D3).** These sections of
> [`PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md) describe the product as it was before v1.0 and
> the plans made then: the pre-v1.0 asymmetry matrix (§1), the stage ladder (§7), the
> `is_default` bug (§9), and the items deferred during the v1.0.0 cut (§10). They are kept
> for their rationale and are no longer maintained. Section numbers match the original, so
> older citations of "PRODUCT_SHAPE §10" still find their section here. Open work is
> tracked in [`work/BOARD.md`](../work/BOARD.md); the schedule is
> [`RELEASE_ARC.md`](../RELEASE_ARC.md). Links were rebased for this directory when the
> sections moved.

---

## 1. The asymmetry matrix (where we are today)

Bullets get the full corpus treatment. Everything else is second-
class. This matrix is the diagnosis.

| Property | `Bullet` | `Experience.summary` | `Candidate.profile_text` | `Skill` | Cover letter | `ExperienceTitle` |
|---|---|---|---|---|---|---|
| Own DB table | ✓ ([`db/models.py:134`](../../../db/models.py)) | ✗ column on `Experience` ([`db/models.py:87`](../../../db/models.py)) | ✗ column on `Candidate` ([`db/models.py:54`](../../../db/models.py)) | ✓ `Skill` | ✗ (LLM-generated only) | ✓ `ExperienceTitle` |
| Multiple variants per parent | ✓ | ✗ one row, one value | ✗ one row, one value | n/a | ✗ | ✓ |
| Tagged | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Scored against JD | ✓ `recommend_bullets` ([`analyzer.py`](../../../analyzer.py)) | ✗ | ✗ | ✗ | ✗ | ✗ |
| Pinnable / excludable per application | ✓ `composition_overrides` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `has_outcome` flag | ✓ | n/a | n/a | n/a | n/a | n/a |
| Soft-retire | ✓ `is_active` | ✗ | ✗ | ✓ | ✗ | ✓ |
| Edit at Compose time | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| LLM recommend call | ✓ Haiku 4.5 | ✗ | ✗ | ✗ | ✗ | ✗ |
| Eval rubric covers it | ✓ keyword overlap + has_outcome | ✗ | ✗ | partial | ✓ overall | ✗ |

**The asymmetry shows up most painfully in summaries** — the opening
paragraph is often the only thing a recruiter reads before deciding
to scan the rest, yet it's a single freeform field with no per-JD
curation.

---

## 7. v1.0 → v1.x → v2 sequencing ladder

> **Version labels superseded (2026-06-08).** The "v1.0 / v1.1 / v1.2 / v2" stage
> labels below predate the **epic/tag versioning model** (patch digit = epic; minor
> digit = the public tag marker — see [`dev/RELEASE_ARC.md`](../RELEASE_ARC.md)).
> Read them as *data-model stages*, not release versions. Current dispositions: the
> **v1.0 stage shipped** (SummaryItem, JSON Resume, PDF, live preview, CL detachment,
> the `is_default` resolver — all done); **ExperienceSummaryItem (B.4) + Skill-as-Corpus-Item
> (B.5)** shipped in **v1.0.6** (corpus completion; B.5 dropped the "SkillGroupItem /
> clusters" framing for individual skills); the rest are dispositioned in §10
> and [`dev/nursery.md`](../nursery.md).

> **Canonical governance.** This prescriptive ladder and the seven-functions
> self-model (§11) are descriptive planning detail; the *binding* rules they rest on
> — the defaults D-1…D-6 and the W-2 "governance is constitution-building" stance —
> live once in [`governance/charter.md`](../../governance/charter.md). The ladder stays
> here; on any conflict the charter governs.

Build the unified pattern in stages, no schema breaks between stages.

### v1.0 (next branch after `feat/release-visual-ia`)

- `SummaryItem` table with `parent_kind` / `parent_id` extensibility
- `recommend_summaries` Haiku call (same shape as
  `recommend_bullets` per
  [TUNING_LOG `2026-05-22.2`](../../../evals/TUNING_LOG.md), including
  the no-near-duplicate rule + Jaccard dedup safety net)
- Compose step gets a "Positioning" card above the experience cards
- JSON Resume v1.0 intermediate format introduced
- Playwright PDF output path added (Chromium-based, see §5.3)
- Live HTML preview component
- Cover-letter detachment + dedicated button + full refine/iterate
- Operationalize `PersonaTemplate.is_default` (bug fix from §5.2)

### v1.1 (immediately after v1.0; no schema break)

- `ExperienceSummaryItem` (parent = Experience) — same shape, same
  recommend call pattern
- `Skill` as a Corpus Item — individual skills, recommend-curated + pin/drop/
  reorder per JD + grounded suggestion (shipped B.5, v1.0.6; the "clusters" idea was dropped)
- Master résumé surfacing — new "Masters" Library sub-tab; new-
  application pre-seed flow from the role's master

### v1.2

- `CoverLetterChunkItem` — reusable cover-letter paragraphs by role
  (intro / why-them / why-me / close)
- Cover-letter generation pulls from chunks instead of from scratch

### v2

- `ApplicationOutcome` table linking Application → outcome events
  (submitted / rejected / interview / offer / accepted)
- Recommend calls gain an outcome-weighting prior
- Template recommendation based on past outcomes per JD class

---

## 9. Bug found during exploration (file under v1.0)

`PersonaTemplate.is_default` is in the schema and has a partial
unique index ([`db/models.py:359, 368-372`](../../../db/models.py)) — but at
the time, `_resolve_default_persona_template_path()` (now in
[`blueprints/templates.py`](../../../blueprints/templates.py) post-8.3e, not
`app.py`) never consulted it. The default resolver hardcoded to bundled
Classic Single-Column. Five-line fix; **deferred during v1.0.0 cut**
(see §10) to v1.1 along with the rest of the master-résumé surfacing
in §5.2.

---

## 10. Deferred during v1.0.0 release cut

> **Reconciled 2026-06-08 (backlog grooming).** Several items below shifted on status
> verification or were dispositioned into the epic ladder / nursery / cut: the
> **Post-v1.0.5** items (cover-letter opener tuning, grounding calibration B) are now
> scheduled as **v1.0.7** pre-public hardening (PV-3 / PV-2); **R2 stream analyze
> shipped** (v1.0.3); **paged.js elimination → post-public 1.1.x** (design-spike);
> **master-résumés + field-filter chips → [`dev/nursery.md`](../nursery.md)**;
> **Dockerfile → cut.** See [`dev/RELEASE_ARC.md`](../RELEASE_ARC.md) for the
> authoritative schedule; entries below are kept for their rationale/context.

Items that surfaced during the v1.0.0 release work and were
explicitly deferred to keep the v1.0.0 scope honest. Captured here
so v1.0.1 / v1.1 / v2 planning can pick them up without
re-deriving the context. Each entry: **what / why deferred /
acceptance criteria / target version**.

### v1.0.1 (point release after v1.0.0)

**Visual assets — screenshots, demo GIF, onboarding HTML page.**
- *Why deferred:* the user has a full UI redesign planned (memory
  note: "current LCARS UI is throwaway"). Capturing screenshots of
  a UI that's about to be replaced wastes effort.
- *Acceptance:* after the v1.1 UI redesign, a `scripts/screenshot.py`
  + `docs/screenshots/*.png` + optional `docs/demo.gif` cycle is
  added; `docs/onboarding.html` adapts the new design system.
- *Target:* v1.0.1 if UI redesign slips; otherwise rolled into v1.1.

**`docs/diagrams/data-flow.mmd` / `docs/diagrams/llm-routing.mmd`.**
- *Why deferred (original plan):* `pipeline.mmd` + `persistence.mmd`
  were the minimum-viable diagram set. *Override on 2026-05-25:* user
  promoted both diagrams INTO v1.0.0 by personal preference. **No
  longer deferred** — both ship with v1.0.0.

**BACK/Continue spacing polish on Compose step.**
- *Why deferred:* cosmetic; the existing layout reads cleanly even
  if the `←` arrow on BACK visually neighbors the `Continue →` button.
- *Acceptance:* one CSS rule on `.form-row` separates BACK from
  next-step actions via either `margin-right: auto` on BACK or a
  wider `gap`.

### v1.1 (next minor release)

**R2 — stream `analyze()` output. ✓ SHIPPED (v1.0.3).** ([docs/dev/perf/PERF_ANALYZE.md](../perf/PERF_ANALYZE.md))
- *Status:* **shipped in v1.0.3** (commit `c8762bc`) — the SSE
  `/api/analyze/stream` route + incremental frontend render are live.
  Reconciled here per the §10 banner above; **no longer deferred**, kept
  for the record. Now a *verify-the-wiring* item for the v1.0.8 E2E window
  (checklist 8.5 "R2 verified live"), not a build.
- *Acceptance (met):* Anthropic SSE streaming wired through the analyze
  route; frontend renders tokens incrementally; perceived latency
  90 s → 10-15 s with total latency unchanged.
- *Cost:* zero; same call, different transport.

**R1 — split `analyze()` into Haiku-fast + Sonnet-deep passes.**
([docs/dev/perf/PERF_ANALYZE.md](../perf/PERF_ANALYZE.md))
- *Why deferred:* touches the prompt, the response schema, and the
  frontend ordering — not a one-commit change. Needs an eval cycle
  before / after so we know we didn't regress analyze quality.
- *Acceptance:* Haiku-fast returns essential_skills + role_family +
  seniority + JD breakdown in 5-8 s; Sonnet-deep returns
  ideal_resume_summary + comparison + keyword_strategy in the
  background. Frontend unlocks Clarify on the fast pass.
- *Cost:* +1 Haiku call (~$0.002 per application).

**Field-filter chips above source chips on the Step 4 Template chooser.**
- *Why deferred:* `PersonaTemplate.primary_role_tag_id` already
  exists in the schema, but the bundled set of 4 templates doesn't
  have meaningful role-tag coverage yet. Filter chips with one
  template each per chip is worse UX than no chips.
- *Acceptance:* user has uploaded ≥ 3 owned templates spanning
  ≥ 2 role tags. The chip row appears above the source chips and
  filters the chooser list.

**Master résumés operationalization** (the §9 bug).
- *Why deferred:* user explicitly deferred during 2026-05-25 plan
  revision (originally listed in §5.2 for v1.0; pulled out to keep
  v1.0.0 focused on docs + bug fixes).
- *Acceptance:* `_resolve_default_persona_template_path()`
  consults `PersonaTemplate.is_default` filtered by JD role tag;
  the "Masters" Library sub-tab lists pinned masters per role.

**`Dockerfile` + `docker-compose.yml` for one-command run.**
- *Why deferred:* `pip install -e .` + `python app.py` works
  cleanly per `docs/user/install.md`. Docker adds maintenance overhead
  without clear v1.0 user demand.
- *Acceptance:* a contributor or external user requests it; image
  builds in CI; image size < 1 GB including Chromium.

### v2 (next major release)

**`recommend_template` Haiku call per JD class.**
- *Why deferred:* needs outcome data we don't have yet. Without
  signal from past applications ("this template + this JD class →
  interview"), template recommendation reduces to deterministic
  scoring against template metadata — already implementable as a
  v1.1 nice-to-have but the LLM call adds no value without outcome
  feedback.
- *Acceptance:* `ApplicationOutcome` table exists (also v2);
  enough rows for the recommend prompt to ground against; eval
  rubric for "template appropriateness" exists.

### Post-v1.0.5 (deferred from the v1.0.5 UI/UX stream)

**`generate_cover_letter` opener tuning — throat-clearing / hedging.**
- *What:* a throat-clearing / hedging opener ("I am writing to be
  considered for…") tripped the `tone` rubric in 1 of 5 shipped v1.0.3
  runs — a pre-existing `generate_cover_letter` adherence lapse surfaced
  during R1 Phase 2 eval (see [`RELEASE_ARC.md`](../RELEASE_ARC.md)
  §Phase 2 "Documentation debt" item 2). The `/tune-from-annotations`
  machinery to fix it shipped in v1.0.4, but the live run was never
  executed — so this entry also stands in for the v1.0.4 "live shakedown"
  that was tagged in machinery but never exercised end-to-end on real data.
- *Why deferred:* it edits `analyzer.py` and **bumps `PROMPT_VERSION`**,
  costs a paid eval (~$0.90), and needs an explicit "promote" — out of
  scope for the rendering-only v1.0.5 stream. User intent: run it AFTER a
  clean-corpus rebuild — a clean git **clone** (NOT a folder copy, which
  drags the gitignored `db/resume.sqlite`) → regenerate the corpus from
  real JDs → annotate → tune.
- *Override-scope note:* the rule lives in the non-overridable
  `_COVER_LETTER_RULES_BLOCK`, so the A/B candidate must be a
  `SYSTEM_PROMPT` worked example (OK / NOT-OK pair), not a rules-block edit.
- *Acceptance:* `tone` holds at or above its `evals/TUNING_LOG.md` floor
  across n≥3 `--suite real` runs with the new opener discipline;
  `PROMPT_VERSION` bumped in the same commit; a TUNING_LOG entry recorded;
  user promotes.
- *Target:* its own branch after the v1.0.5 tag.

**Grounding / hallucination metric — calibrated layers (B), pre-v1.1.0.**
- *What:* the **calibrated** half of the grounding metric. The deterministic,
  label-free L0 fabricated-specifics rate ships *during* v1.0.5
  (`eval/grounding-metric-l0`, A — see [`RELEASE_ARC.md`](../RELEASE_ARC.md)
  §Phase 4 + [`docs/dev/GROUNDING_METRIC.md`](../GROUNDING_METRIC.md)). This
  entry is the follow-up: (1) run the v1.0.4 loop **end-to-end on the real
  corpus** — the live shakedown that was tagged in machinery but never executed
  (seed → bootstrap → annotate) — to produce `annotations.json` labels;
  (2) **calibrate** the L0 tolerance bands + the eval-only L1/L2 NLI/MiniCheck
  thresholds (`evals/grounding_signals.py`) against those labels
  (precision/recall per detector); (3) **update the eval suite** to report the
  calibrated cross-class groundedness score (`eval_composite` / score-over-time
  by `PROMPT_VERSION`); (4) **update the tuning interface** to gate on the
  calibrated metric.
- *Why deferred:* the calibrated metric depends on human-labeled real bullets,
  and as of 2026-06-05 there are **none** (`evals/fixtures/real/` empty; no
  `bootstrap.json` / `annotations.json`). Producing them is the never-run v1.0.4
  live loop — real LLM cost + annotation labor — so it is staged behind the
  free, deterministic L0 slice rather than blocking v1.0.5 on it. Shares the
  same prerequisite as the cover-letter opener-tuning entry above (a
  clean-corpus rebuild from a real git **clone**, then regenerate the corpus).
- *Hot-path discipline:* L1/L2 are model-based and stay **eval-only** (RELEASE_ARC
  Key Decision #4). Only the deterministic L0 may ever touch the hot path.
- *Acceptance:* each detector's precision/recall reported against the annotation
  labels; the calibrated groundedness score is live on `--suite real` and on the
  dashboard's score-over-time chart; the tuning loop consumes it; no model scorer
  in the hot path.
- *Target:* pre-v1.1.0, after the v1.0.5 UI stream — ideally alongside the
  cover-letter opener-tuning live run (shared corpus-rebuild prerequisite).

**paged.js preview-render fragility — contained, not eliminated.**
- *What:* the vendored paged.js v0.4.3 polyfill (`static/vendor/paged.polyfill.js`,
  the in-browser preview pagination engine — NOT the PDF path, which uses
  Playwright's native `page.pdf()`) throws internally on certain content
  shapes: `Cannot read getBoundingClientRect of null` (async, from its
  un-`catch`-ed `await preview()`) and `node.getAttribute is not a function`
  (sync, from an off-chain layout sartor). `feat/template-pagination`
  (v1.0.5) **contained** both — the injection (`_PAGED_PREVIEW_INJECTION`,
  now in [`blueprints/templates.py`](../../../blueprints/templates.py) post-8.3e,
  not `app.py`) drives `preview()` itself with `try/catch` +
  `.catch()` and narrowly swallows the two known paged-origin throws — so the
  console is clean and the tests run with no allowlist. But the throws still
  fire inside the library; we catch-and-ignore them. This is safe **only
  because the render completes correctly despite the throws** (the v1.0.5
  pagination regression test asserts every bundled template paginates with
  content on every page, no blanks). The suppression is narrow + self-policing:
  any *new/different* paged.js error is NOT swallowed and WILL fail the
  unconditional UX sentinel.
- *Why deferred:* root-cause elimination means leaving paged.js — option (c)
  in the old `RELEASE_CHECKLIST.md` paged.js item: *"replace paged.js with a
  simpler pagination approach"*. paged.js does real CSS Paged Media layout
  (page boxes, break rules); replacing it is a substantial project,
  disproportionate to a CSS-pagination bugfix branch, and v0.4.x is the end of
  that library's line (effectively unmaintained). A lighter intermediate step
  (host paged.js outside the iframe + message-pass) is already noted against
  the v1.0.1 sandbox item.
- *Acceptance (when picked up):* preview pagination renders with **zero**
  internal paged.js throws (no suppression filter needed) across all four
  bundled templates on sparse + dense content; the
  [`blueprints/templates.py`](../../../blueprints/templates.py) paged-origin
  `window.error` / `unhandledrejection` swallows are removed; the UX sentinel
  stays green.
- *Target:* a deliberate, separately-scoped render-engine decision — v2, or
  whenever preview fidelity / maintenance cost justifies the swap. Not a
  bugfix-branch drive-by.
