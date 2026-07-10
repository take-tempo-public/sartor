# Product shape — sartor.

> **Purpose:** the architectural intent. The unified Corpus Item pattern,
> the v1 → v2 sequencing ladder, the locked-in technology choices
> (JSON Resume v1.0 as the canonical intermediate, Playwright for PDF,
> SQLite + Alembic for persistence).
> **Audience:** humans and LLMs planning features that touch the corpus,
> the rendering pipeline, or future schema work.
> **Authoritative for:** which architectural patterns the codebase
> converges toward; what is deferred to v1.1 / v1.2 / v2; the asymmetry
> matrix that explains why each remaining gap exists.
>
> **Companion** to [`docs/dev/RELEASE_CHECKLIST.md`](dev/RELEASE_CHECKLIST.md).
> That doc is *what we ship*. This doc is *what shape we're aiming
> for* — the unified data model the product converges toward and the
> sequencing ladder that gets us there without schema breaks.

This file captures a conversation that produced a unifying product
pattern (every curatable résumé element is a "Corpus Item") plus
five addendums that shape the v1 → v2 roadmap. It survives turn
boundaries so future contributors — human or LLM — can pick up the
intent without re-deriving it.

---

## 1. The asymmetry matrix (where we are today)

Bullets get the full corpus treatment. Everything else is second-
class. This matrix is the diagnosis.

| Property | `Bullet` | `Experience.summary` | `Candidate.profile_text` | `Skill` | Cover letter | `ExperienceTitle` |
|---|---|---|---|---|---|---|
| Own DB table | ✓ ([`db/models.py:134`](../db/models.py)) | ✗ column on `Experience` ([`db/models.py:87`](../db/models.py)) | ✗ column on `Candidate` ([`db/models.py:54`](../db/models.py)) | ✓ `Skill` | ✗ (LLM-generated only) | ✓ `ExperienceTitle` |
| Multiple variants per parent | ✓ | ✗ one row, one value | ✗ one row, one value | n/a | ✗ | ✓ |
| Tagged | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Scored against JD | ✓ `recommend_bullets` ([`analyzer.py`](../analyzer.py)) | ✗ | ✗ | ✗ | ✗ | ✗ |
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

## 2. Six asymmetries worth naming

1. **Summaries are second-class.** One freeform field per experience
   ([`db/models.py:87`](../db/models.py)) and one for the candidate
   ([`db/models.py:54`](../db/models.py)). No per-JD curation, no
   multi-variant, no recommend call.
2. **Cover letters are write-only.** Generated from scratch each
   time. Your best paragraph from last month is gone unless you
   remember it. Nothing captures reusable cover-letter chunks.
3. **Generated résumés are write-only too.**
   `output/{user}/resume_{ts}.docx` is saved but the system can't
   know which one you actually sent, let alone which earned an
   interview. No outcome feedback loop.
4. **Skills are structured but un-curatable.** A `Skill` row exists
   but it's all-or-nothing per résumé. A senior candidate with 30
   skills can't say "for THIS JD surface these 10 in this order."
5. **Templates are structured but isolated.** Persona Templates are
   DB-backed; no record of "this candidate + this template family +
   this JD class scored well." Could be a recommendation surface
   (B2 evals already track score by template).
6. **Compose overrides don't compound.** Pinning bullet X for one JD
   doesn't bias recommend in future JDs that look similar. The corpus
   stays static; learning from applications doesn't flow back in.

## 3. The unifying pattern — "Corpus Item"

A single conceptual base every curatable element inherits:

```
CorpusItem
  text or markdown content
  variants[]              ← alternate phrasings of the same idea
  tags
  score (vs current JD)
  has_outcome             ← bullets, achievement-style summaries
  is_active               ← soft-retire
  parent_kind / parent_id ← experience, candidate, application
  composition state       ← pinned / excluded / added per application
```

Specializations:

| Kind | Parent | Status | Notes |
|---|---|---|---|
| `BulletItem` | Experience | ✓ exists as `Bullet` | The reference implementation |
| `SummaryItem` | Candidate | New (v1.0) | Multiple positioning variants per candidate |
| `ExperienceSummaryItem` | Experience | New (v1.1) | Per-role intro paragraph, multi-variant |
| `Skill` (Corpus Item) | Candidate | ✓ exists (B.5, v1.0.6) | Individual skill as a Corpus Item — taggable, recommend-curated + pin/drop/reorder per JD, suggested→approved/denied. (The earlier "`SkillGroupItem` / curated clusters" framing was dropped: no grouping — each skill is its own item, mirroring `Bullet`.) |
| `CoverLetterChunkItem` | Candidate | New (v1.2) | intro / why-them / why-me / close |
| `TitleVariantItem` | Experience | ✓ exists as `ExperienceTitle` | |

What every kind gets for free once the pattern is in place:

1. **Recommend call** — Haiku, same shape as
   [`recommend_bullets`](../analyzer.py) (system prompt: no
   near-duplicates rule, deterministic Jaccard dedup safety net per
   [TUNING_LOG `2026-05-22.2`](../evals/TUNING_LOG.md)).
2. **Compose-step UI affordance** — score pill, pin/exclude buttons,
   "find more" drawer.
3. **Tag composer.**
4. **Soft-retire affordance** in the Career Corpus tab.
5. **Eval coverage** — keyword overlap + has_outcome metrics map
   identically.

That's the consistency dividend: users learn the pattern once and it
applies everywhere.

## 4. Use value at each stage of the process

| Stage | What the user produces or curates | Use value at this stage |
|---|---|---|
| **Import** | Raw résumé → structured corpus (one-time cost) | Set-up amortizes across every future application |
| **Onboarding review** | Accept / reject extracted corpus items | Establishes ground truth; everything later trusts this |
| **Career Corpus** | Edit evergreen story (bullets / summaries / skills / cover chunks) | Investment compounds — every new item improves every future application |
| **Master résumés** | Promote a curated set as the "master for Design IC" / "master for PM" | New applications in that role pre-seed from the master |
| **Prior Applications** | History of what you've sent + iterated | Reuse winning patterns; spot template + summary combos that land interviews |
| **Job + Analyze** | Paste JD, see fit + gaps | Pre-write self-assessment; primes the LLM with the strategy |
| **Clarify** | Answer 3–5 LLM questions | Surfaces real-but-undocumented truth → grows the corpus over time |
| **Compose** | Curate per-layer: bullets + **summaries** + **skill groups** + **cover chunks** | Same UI pattern across all corpus kinds — predictable, fast |
| **Template + Live preview** | Pick visual presentation; preview live updates | WYSIWYG HTML — what you see is what becomes the PDF |
| **Generate + Download** | Choose output format(s) | Multi-select OK; format choice deferred until after preview |
| **(Optional) Cover letter** | "Also generate a cover letter for this résumé" | Detached from critical path; saves LLM cost when skipped |
| **Review + iterate** | Refine via prompt or interview | Tightens to voice; iteration becomes part of the corpus signal |
| **Download** | Send-ready file | End of one application |
| **(Future v2) Mark sent + outcome** | "I sent this on 2026-05-24. They invited me to interview on 2026-06-02." | **Closes the loop.** Recommend can now weight by outcome, not just LLM judgment. |

The **"Mark sent"** row is v2 territory but flagged here as the
killer-feature gap that would close the outcome feedback loop. Today
the corpus → recommend → generate loop is closed only at the LLM-
judgment level. The system has no idea which generated résumés
actually landed work.

## 5. Addendums

### 5.1 Cover letters as optional

**The ask:** "I almost never use cover letters. Instead of generating
one every time, let's make that an optional step after the résumé is
complete so the cover letter can be generated optionally as a match
to the finished résumé."

**Decision (v1.0):**

- Move cover-letter generation off the critical path.
- `/api/generate` gains a `generate_cover_letter: bool` flag,
  default `false`.
- New `/api/generate-cover-letter` route: takes an existing
  `application_id`, generates against the latest résumé draft,
  returns the same shape as résumé generate.
- The Download step gains a quiet "Also generate a cover letter for
  this résumé" button with its own pending state.
- **The cover letter inherits the full refine / iterate /
  clarify-iteration / edit-detect flow that résumés have today.**
  Specifically:
  - [`submitRefinement`](../static/app.js) + `runIterateClarify`
    operate on cover letters as well as résumés
  - `lastGeneratedCoverLetter` is already tracked in `app.js`
  - The edit-detect modal already handles
    `edited_cover_letter_text`
  - No new pattern — just wiring the existing P8 Human Gates
    ([`CLAUDE.md`](../CLAUDE.md)) to the cover-letter generation
    path
- **Saving:** the deferred call eliminates the cover-letter LLM cost
  on the common path (résumé-only generation), which is what the
  user said is their default.

### 5.2 Master résumés per role

**The ask:** "I sometimes re-use resumes or promote them to a sort of
master resume for design IC or product management. Let's consider
how those resumes are revealed and utilized as part of the flow or
library."

**Surprise finding from exploration (v1.0-era; `_resolve_default_persona_template_path()`
now lives in [`blueprints/templates.py`](../blueprints/templates.py) post-8.3e, not
`app.py`):**
`PersonaTemplate.is_default` + `primary_role_tag_id` columns already
exist in [`db/models.py:359, 368-372`](../db/models.py). A partial
unique index enforces at most one `is_default = 1` per candidate per
role tag. **At the time, `_resolve_default_persona_template_path()` never
consulted them** — the default resolution hardcoded to bundled Classic
Single-Column. This is a 5-line fix and a v1.0 quick win.

**Recommended UX (v1.1):**

- "Master résumé" = the canonical set of curated CorpusItem rows
  (summary variant + bullets per experience + skill group) for a
  role tag (e.g. "Design IC", "Product Management"). Stored as an
  `ApplicationRun` row tagged `is_master: true` for a given role.
- When the user starts a new Application, the Compose step pre-seeds
  pin/exclude state from the master résumé for the JD's inferred
  role tag (the analyze step already tags JDs by role). User can
  override per-application.
- Library gains a "Masters" sub-section listing pinned masters per
  role.
- The existing `PersonaTemplate.is_default` column gets
  operationalized so each master can also pre-select its preferred
  template family.

### 5.3 PDF output — gap to close

**The ask:** "PDF is a gap. It is a dead-end format but the most
used for submissions for jobs because of its fixed presentation. We
need this as an output format."

**Decision (v1.0):** Playwright + headless Chromium.

**Decision history.** The original choice was WeasyPrint on the
belief that it had no system dependencies. In practice WeasyPrint
requires GTK3 / Pango system libs on Windows + macOS — `pip install`
alone fails to render. Mid-build in β.3 we reassessed and switched
to Playwright, which has a one-time browser-binary download that's
pip-driven and cross-platform.

| Option | Pros | Cons |
|---|---|---|
| **Playwright + Chromium** ✓ | Perfect CSS + web fonts; pip-installable; Chromium auto-downloads via `python -m playwright install chromium`; same template feeds both PDF + live preview (WYSIWYG); unlocks future visual-regression testing | ~150MB browser binary in the OS user cache (NOT in the repo); heaviest dep among the candidates |
| WeasyPrint | Mature, Python-native, used by Mozilla | Requires GTK3 / Pango system libs on Windows + macOS; `pip install` alone is not enough |
| LibreOffice headless | Reuses existing `.docx` template 1:1 | Requires LibreOffice installed system-wide |

**Implementation (shipped in β.3):**

- New dependency: `playwright>=1.40,<2.0` in `pyproject.toml`. The
  Chromium binary is a one-time `python -m playwright install
  chromium`; binary lives in the OS user cache, NOT in the repo.
  `.gitignore` has defensive entries for `ms-playwright/` etc.
- New module: [`pdf_render.py`](../pdf_render.py) — Jinja2 renders
  HTML, Playwright loads it via `file://` URL (so the relative CSS
  link resolves), `page.pdf()` emits bytes. Letter format,
  0.6in/0.65in margins.
- New rendering path: `generate_resume(content, ".pdf", ...)` uses
  the JSON Resume document from β.2 (no markdown reparse).
- Persona Templates evolve from `.docx`-only to `.docx + .html +
  .css` triples. Convention: `personas/bundled/classic.docx` →
  `personas/bundled/classic.html` + `personas/bundled/classic.css`.
  `pdf_render.html_template_path_for()` resolves the companion.
  Personas without HTML companions fall back to the bundled Classic
  template.
- Bundled Classic HTML+CSS shipped in β.3: ATS-friendly single-
  column, semantic HTML, system-stack typography (no webfonts), B&W
  safe, 0.6in margins, brand-amber h2 underline as the only color
  accent. Reused as the live preview source (§5.5).
- **Backward compat:** `.docx` output stays the same (`_write_docx`
  via python-docx). `.md` stays the same. PDF and HTML are new
  parallel paths.

### 5.4 Canonical intermediate format — JSON Resume v1.0

**The ask:** "Is it worth producing a resume format to hold the data
for a resume that is then parsed into MD, DOCX or PDF? Is there a
standard for this? Some sort of standardized HR format or XML?"

**Answer:** Yes. The answer is [JSON Resume v1.0](https://jsonresume.org/).

It is:
- A real community standard with a published JSON schema
- An ecosystem of themes that render to HTML / PDF
- Cleanly mappable to our existing DB schema (and explicitly
  extensible via `meta`)

The HR-XML / HR-Open Standards exist but are enterprise-ATS-flavored
and a poor fit for a developer-tool single-tenant product.
schema.org/Person has structured profile fields but no résumé-
specific shape.

**Decision (v1.0):** Adopt JSON Resume v1.0 as canonical intermediate.

**Mapping:**

| JSON Resume field | Our source |
|---|---|
| `basics.name`, `email`, `phone` | `Candidate` columns |
| `basics.summary` | `SummaryItem` (active variant for this application) |
| `basics.profiles[]` | `Candidate.linkedin_url`, `website_url` |
| `work[].name`, `position`, `startDate`, `endDate` | `Experience` + active `ExperienceTitle` |
| `work[].summary` | `ExperienceSummaryItem` (v1.1) |
| `work[].highlights[]` | active `Bullet` rows respecting `composition_overrides` |
| `skills[]` | `Skill` rows as Corpus Items — recommend-curated + pin/drop/reorder per JD (B.5, v1.0.6); no grouping |
| `education[]` | `Education` rows (`_collect_education`, fix/output-identity-and-dates) — active/display_order, mirrors `skills[]`'s shape |
| `certificates[]` | `Certification` rows (`_collect_certificates`, fix/output-identity-and-dates) — same shape |
| `projects[]`, `languages[]` | future |

**Extension namespace.** Our corpus-only fields (tags, scores,
is_active, variants, has_outcome) live under
`meta.sartor.{ext_fields}` so the JSON still validates against the
standard schema. Themes that don't know about sartor. extensions
ignore them; our own renderer reads them.

**Markdown becomes a render target, not the source of truth:**

- LLM still emits markdown for the body (preserves the existing
  prompt + the no-near-duplicate rule + the markdown normalizer
  per TUNING_LOG `2026-05-24.1`)
- Deterministic post-pass `_md_to_json_resume` lifts the markdown
  into a JSON Resume document (uses the same `#` / `##` / `###`
  dispatch that `_write_docx` uses today)
- All renderers (md / docx / pdf / html-preview) consume the JSON
  Resume document, not the markdown
- Eval rubric gets a new dimension: schema validity of the JSON
  Resume output

This is a coherence win disproportionate to the implementation cost
— we get a standard format, validators, and a path to PDF + live
preview all in one move.

### 5.5 Live updatable preview

**The ask:** "We need a better preview of the final resume with the
correct content and template. A live updatable preview with
different templates would be ideal."

**Today** (from exploration):

- Preview lives at [`/api/personas/<id>/preview`](../blueprints/templates.py)
  (moved off `app.py` in the v1.0.8 blueprint decomposition, Sprint 8.3e —
  `app.py` is a zero-route composition root today; see §11.2 WS-1)
- Streams a generated `.docx` file (`send_file`)
- Requires user to have called `/api/generate` at least once first
  (pulls the most-recent `ApplicationRun.generated_resume_md`)
- No in-app render — user has to download and open in Word

**Decision (v1.0):**

- New route: `/api/applications/<id>/preview?template_id=<id>` →
  returns rendered HTML (not docx).
- Compose, Template, and Download steps all gain an embedded
  preview panel showing the current state.
- Template switcher in the preview panel lets the user A/B
  templates without re-generating LLM content (same JSON Resume,
  different Jinja2 + CSS render).
- Preview re-renders when:
  - **Composition (pin/exclude/add) changes** — JSON Resume
    rebuilds from corpus + overrides; cheap, no LLM call
  - **Template selection changes** — pure CSS swap
- **Reuses the Playwright HTML render** (§5.3) — the live preview
  IS the same HTML that becomes the PDF. True WYSIWYG. This parity is
  between preview and PDF specifically — both paginate via the same
  CSS + paged.js engine. A `.docx` download shares the same *content*
  but paginates through Word at open time (its own layout engine), so
  exactly where a page breaks can differ from the preview; parity
  there is content-level (D3), not pixel/pagination-level. Accepted
  limitation, not scheduled — see the paged.js fragility note below.

## 6. Wizard flow — current vs sketched + clarified

### 6.1 Current (today)

```
1. Job description (paste)
2. Analyze (LLM)        — Sonnet 5 (two-pass: Haiku 4.5 extraction → Sonnet synthesis)
3. Clarify (optional)   — Haiku 4.5
4. Compose              — Haiku 4.5 recommend_bullets + user curation
5. Template             — pick persona
6. Generate             — Sonnet 5, produces BOTH résumé + cover
7. Output / Download    — .docx or .md, preview = .docx download
```

### 6.2 User's sketched flow

```
1. Analyze experience corpus to match JD
2. Refinement phase
3. Produce summary (optional) + titles + bullets
4. Produce résumé in markdown intermediate
5. Apply template to data format → preview
6. Choose output format + template
7. Produce résumé content in template to target format
```

### 6.3 Clarified flow (current + sketched + addendums)

The sketch is accurate in spirit and resolves the asymmetries.
Proposed final shape:

```
0. Library lens (always available, not a wizard step)
   - Career corpus (bullets / summaries / skills / cover chunks)
   - Master résumés (per role tag)
   - Prior applications
   - Résumé templates

1. Job + Analyze              — Sonnet, ATS + JD breakdown
2. Clarify (optional)         — Sonnet, surfaces real-but-undoc'd
3. Compose                    — Haiku recommend_X per kind:
                                  summary, titles, bullets, skills
                                user curates with pin/exclude/add
4. Template + Live Preview    — pick template; preview live updates
                                WYSIWYG HTML render (Jinja2 + CSS)
5. Generate + Download        — choose output format(s);
                                Playwright HTML→PDF, python-docx,
                                raw .md; multi-select OK
6. (Optional) Cover letter    — Sonnet, against the finalized
                                résumé; same refine / iterate
                                affordances as the résumé
7. (Future v2) Mark sent +    — closes the outcome feedback loop
   outcome
```

**Key differences from today:**

- **Compose is enriched** — summaries + skills join bullets as
  curatable corpus items (the unified pattern)
- **Template + Preview is one step** with live HTML updates —
  no need to "generate to see"
- **Generate + Download is one step** — format choice deferred
  until the user has seen the preview
- **Cover letter is detached** — optional, AFTER résumé, with the
  full refine/iterate affordance
- **Mark sent** is the v2 placeholder

## 7. v1.0 → v1.x → v2 sequencing ladder

> **Version labels superseded (2026-06-08).** The "v1.0 / v1.1 / v1.2 / v2" stage
> labels below predate the **epic/tag versioning model** (patch digit = epic; minor
> digit = the public tag marker — see [`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md)).
> Read them as *data-model stages*, not release versions. Current dispositions: the
> **v1.0 stage shipped** (SummaryItem, JSON Resume, PDF, live preview, CL detachment,
> the `is_default` resolver — all done); **ExperienceSummaryItem (B.4) + Skill-as-Corpus-Item
> (B.5)** shipped in **v1.0.6** (corpus completion; B.5 dropped the "SkillGroupItem /
> clusters" framing for individual skills); the rest are dispositioned in §10
> and [`dev/nursery.md`](dev/nursery.md).

> **Canonical governance.** This prescriptive ladder and the seven-functions
> self-model (§11) are descriptive planning detail; the *binding* rules they rest on
> — the defaults D-1…D-6 and the W-2 "governance is constitution-building" stance —
> live once in [`governance/charter.md`](governance/charter.md). The ladder stays
> here; on any conflict the charter governs.

Build the unified pattern in stages, no schema breaks between stages.

### v1.0 (next branch after `feat/release-visual-ia`)

- `SummaryItem` table with `parent_kind` / `parent_id` extensibility
- `recommend_summaries` Haiku call (same shape as
  `recommend_bullets` per
  [TUNING_LOG `2026-05-22.2`](../evals/TUNING_LOG.md), including
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

## 8. Asymmetries logged but not building yet

- **Outcome tracking** — no "this application got me an interview"
  signal today. v2.
- **Template recommendation** per JD class. v2.
- **Compose overrides don't compound** — a bullet pinned across 5
  similar JDs should surface as a candidate for default-include.
  Maybe v2; depends on whether the recurring-pin signal is strong
  enough to be useful.
- **Cross-candidate insights** — impossible by design (local-first
  single-tenant). Will not build. Documented in
  [`SECURITY.md`](../SECURITY.md) as part of the threat model.

## 9. Bug found during exploration (file under v1.0)

`PersonaTemplate.is_default` is in the schema and has a partial
unique index ([`db/models.py:359, 368-372`](../db/models.py)) — but at
the time, `_resolve_default_persona_template_path()` (now in
[`blueprints/templates.py`](../blueprints/templates.py) post-8.3e, not
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
> **master-résumés + field-filter chips → [`dev/nursery.md`](dev/nursery.md)**;
> **Dockerfile → cut.** See [`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) for the
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

**R2 — stream `analyze()` output. ✓ SHIPPED (v1.0.3).** ([docs/dev/perf/PERF_ANALYZE.md](dev/perf/PERF_ANALYZE.md))
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
([docs/dev/perf/PERF_ANALYZE.md](dev/perf/PERF_ANALYZE.md))
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
  cleanly per `docs/install.md`. Docker adds maintenance overhead
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
  during R1 Phase 2 eval (see [`RELEASE_ARC.md`](dev/RELEASE_ARC.md)
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
  (`eval/grounding-metric-l0`, A — see [`RELEASE_ARC.md`](dev/RELEASE_ARC.md)
  §Phase 4 + [`docs/dev/GROUNDING_METRIC.md`](dev/GROUNDING_METRIC.md)). This
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
  now in [`blueprints/templates.py`](../blueprints/templates.py) post-8.3e,
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
  [`blueprints/templates.py`](../blueprints/templates.py) paged-origin
  `window.error` / `unhandledrejection` swallows are removed; the UX sentinel
  stays green.
- *Target:* a deliberate, separately-scoped render-engine decision — v2, or
  whenever preview fidelity / maintenance cost justifies the swap. Not a
  bugfix-branch drive-by.

---

## 11. System self-model + engineering workstreams (the excellence walk)

> Added 2026-06-08 from the "excellence walk" — a codebase self-assessment +
> engineering-excellence design pass. §1–9 describe the shape of the **product
> data model** (the Corpus Item). This section names the shape of the **whole
> system** and the structural levers that move it toward a polished production
> codebase. Sequencing is authoritative in [`RELEASE_ARC.md`](dev/RELEASE_ARC.md)
> §Phase 4.5 / §Phase 4.7 / "Post-v1.1.0 workstreams"; this section is the *shape
> intent*, not the schedule.

### 11.1 The seven-functions self-model → [`docs/system-model.md`](system-model.md)

The system is described by **seven functions + one law**, split across two
subjects (the Corpus-Item pattern is a piece of the first):

- **The Product** — **Production** (the pipeline: read JD → clarify → recommend →
  generate → iterate; all LLM calls isolated in `analyzer.py`, the deterministic
  core kept LLM-free) over its **Substrate** (`configs/`, `resumes/`, `output/`,
  `db/`, `context_*.json`).
- **The Work** that evolves it — **Evaluation** (`tests/`, `evals/`, `dashboard/`),
  **Operation** (`.claude-plugin/` commands + agents; humans + AI agents),
  **Memory** (`docs/`, the planned wiki, `CHANGELOG`), **Regulation** (hooks, the
  quality gate, branch/release discipline).
- **Governance** — the prescriptive north-star (`vision.md`, the 10 Principles)
  the Work answers to.

**The one law:** every dependency points inward toward **Production**; Production
answers only upward to **Governance** — the codebase's own one-way dependency rule
(P1 deterministic/LLM boundary; production ↛ `evals/`) scaled up to the whole
system. The canonical write-up lives in [`docs/system-model.md`](system-model.md)
(the WS-4 wiki `overview.md` seed); §11 here is the one-paragraph summary that
defers to it.

### 11.2 The four workstreams (structural intent)

> **Snapshot — updated as these land; canonical schedule:**
> [`RELEASE_ARC.md`](dev/RELEASE_ARC.md) §Phase 4.8 / §"Recurring / continuing
> workstreams". Status column as of 2026-07-10.

| WS | Shape lever | Status | What | Sequenced |
|---|---|---|---|---|
| **WS-1** | split the monolith | ✓ **SHIPPED (v1.0.8)** | decomposed the monolithic `app.py` (pre-split size per [`RELEASE_ARC.md`](dev/RELEASE_ARC.md) §Phase 4.8: 8,251 LOC / 93 routes) into Flask blueprints across Sprints 8.3a–h, preserving the `_safe_username`/`_within` gate + its lint hook (since widened to `blueprints/**.py`, PX-29). `app.py` is now a ~296-line application-factory composition root with **zero** `@app.route` handlers — every route lives on a domain blueprint (`blueprints/` + the read-only `dashboard/`), per [`app.py`](../app.py)'s own module docstring. | **v1.0.8** — landed as a dedicated *pre-public* epic (so v1.1.0 ships clean); absorbed PV-4; was never interleaved with a sprint stream |
| **WS-2** | model the contracts as types | ◐ **PARTIAL** | strict-typing ratchet + a typed `context_set` (TypedDict/dataclass/Pydantic) — the contract becomes a *type*, not prose + JSON-schema | increment 1 = PV-4 ✓ shipped **v1.0.8** (rode WS-1); the strict-typing ratchet itself ✓ shipped **v1.0.9** (the `mypy --strict` §6 exit criterion was reached 2026-07-10 — every non-exempt production module now type-checks under full `--strict`, see [`kit-adoption-design.md`](dev/kit-adoption-design.md) §6); the **typed `context_set` spine** is still **PLANNED**, post-public 1.1.x |
| **WS-3** | keep the test suite lean | **PLANNED** | recurring engineering-design pass over the ~955-test suite (redundancy, slow tests, fixture dup) | not yet started; recurring, post-public (1.1.x) |
| **WS-4** | a knowledge substrate | ✓ **SHIPPED** | committed `docs/wiki/` (git-as-engine) + `llms.txt` + `/wiki-*` skills + a canonical **Governance** extraction | substrate (WS-4a/b) shipped **v1.0.6**; the self-documenting loop + the doc-grounded assistant shipped **v1.0.7** |

<!-- DOC-STATUS(ws-workstreams): WS-2's typed `context_set` spine and WS-3 (test-suite engineering-design pass) are PLANNED, not started as of 2026-07-10 — update this table's Status column when either lands. Canonical: docs/dev/RELEASE_ARC.md "Recurring / continuing workstreams". -->

### 11.3 Consistency tracks enforcement (the Q2 finding → why WS-1 + WS-2)

The consistency audit found the codebase is uniform *exactly where a hook or the
linter guards a pattern* (security gate, import order, `call_kind` taxonomy, LLM
instrumentation) and inconsistent only where convention is left to discipline —
and both real gaps are already named here: **return-type annotations + the
`dict`-typed payloads/`context_set`** (→ WS-2) and the **75-route monolith**
(→ WS-1). The fix is not "be more disciplined" — it is **extend the enforcement
surface**: model the contracts (WS-2) and split the monolith (WS-1) so the
machinery, not vigilance, keeps them consistent.

### 11.4 Capabilities the substrate enables

- **The doc-grounded assistant (v1.0.7; ships in v1.1.0).** *"A product that knows
  itself."* A chat — for **both users and devs** — that answers "how do I…" questions
  from the committed `docs/wiki/` **with citations** (the LLM-wiki `query` op as a
  chat). A **Haiku** model reusing the user's **existing Anthropic key**; the
  self-documenting loop keeps the wiki it reads current. A public UX/DX value prop.
- **Local + alternative LLM providers (post-public, 1.1.x).** A provider abstraction
  at the single LLM boundary (`analyzer.py`) so users pick **local** (Ollama /
  llama.cpp) or **alternative** (OpenAI / Gemini / …) models — strong local-first /
  privacy fit. Architectural → a design-spike first; generalizes every call,
  including the assistant.

> **Disposition pointers.** Scheduled work lives in
> [`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) (the epic/tag ladder); deferred-but-alive
> ideas live in [`dev/nursery.md`](dev/nursery.md); the raw reasoning behind all of
> this is preserved in [`dev/excellence-walk/`](dev/excellence-walk/).

---

## External references

- [JSON Resume v1.0 schema](https://jsonresume.org/schema/) — canonical
  intermediate format adopted in v1.0
- [Playwright](https://playwright.dev/python/) — headless Chromium
  driver for the v1 PDF + live-preview render pipeline (§5.3)
- [schema.org/Person](https://schema.org/Person) — structured profile
  fields (not adopted; complementary to JSON Resume's `basics`)
- [HR-Open Standards](https://www.hropenstandards.org/) — enterprise
  ATS standards (evaluated, not adopted; wrong shape for a developer
  tool)

## Related project docs

- [`docs/dev/RELEASE_CHECKLIST.md`](dev/RELEASE_CHECKLIST.md) — the *what we
  ship for v1* checklist (PII scrub, cleanup pass, docs)
- [`CLAUDE.md`](../CLAUDE.md) — agent and contributor contract; the
  10-principles framework references
- [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) — institutional
  memory of prompt iterations; the `recommend_bullets` pattern this
  doc proposes mirroring lives there
- [`SECURITY.md`](../SECURITY.md) — single-tenant threat model

---

*This file lives in `docs/` so it ships with the repo. Its sibling
`docs/dev/RELEASE_CHECKLIST.md` is the execution lens; this one is the
shape lens. Update either when the corresponding lens shifts.*
