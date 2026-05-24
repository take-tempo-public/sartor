# Product shape — callback.

> Companion to [`docs/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).
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
| `SkillGroupItem` | Candidate | New (v1.1) | Curated skill clusters per JD |
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

**Surprise finding from exploration:**
`PersonaTemplate.is_default` + `primary_role_tag_id` columns already
exist in [`db/models.py:359, 368-372`](../db/models.py). A partial
unique index enforces at most one `is_default = 1` per candidate per
role tag. **But [`app.py:1403-1423`](../app.py)
`_resolve_default_persona_template_path()` never consults them** —
the default resolution hardcodes to bundled Classic Single-Column.
This is a 5-line fix and a v1.0 quick win.

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

**Decision (v1.0):** WeasyPrint.

**Why WeasyPrint over alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **WeasyPrint** ✓ | Python-native, pip-installable (~20MB), no system deps, mature (used by Mozilla), HTML+CSS templates pair with the live HTML preview | Slightly less perfect CSS fidelity than Chromium |
| LibreOffice headless | Reuses existing `.docx` template 1:1, highest fidelity to existing personas | Requires LibreOffice installed system-wide (Docker / CI friction) |
| Playwright (headless Chromium) | Perfect CSS, web fonts | ~100MB browser binary, heaviest dep |

**Implementation sketch:**

- New dependency: `weasyprint` in [`pyproject.toml`](../pyproject.toml)
- New rendering path: `generate_resume(content, ".pdf", ...)` —
  parse markdown → JSON Resume (§5.4) → render HTML via Jinja2
  template → WeasyPrint to PDF
- Persona Templates evolve from `.docx`-only to a *pair*: existing
  `.docx` for Word output AND an HTML/CSS pair for HTML preview +
  PDF output. Existing bundled templates need HTML companions.
- Live preview (§5.5) re-uses the HTML render — same Jinja2
  template, displayed in-app.
- **Backward compat:** `.docx` output stays the same (existing
  `_write_docx` flow in [`generator.py`](../generator.py) with
  python-docx). PDF and HTML are new parallel paths.

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
| `skills[]` | `Skill` rows (grouped via `SkillGroupItem`, v1.1) |
| `education[]`, `projects[]`, `certificates[]`, `languages[]` | future |

**Extension namespace.** Our corpus-only fields (tags, scores,
is_active, variants, has_outcome) live under
`meta.callback.{ext_fields}` so the JSON still validates against the
standard schema. Themes that don't know about callback. extensions
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

- Preview lives at [`/api/personas/<id>/preview`](../app.py)
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
- **Reuses the WeasyPrint HTML render** (§5.3) — the live preview
  IS the same HTML that will become the PDF. True WYSIWYG.

## 6. Wizard flow — current vs sketched + clarified

### 6.1 Current (today)

```
1. Job description (paste)
2. Analyze (LLM)        — Sonnet 4.6
3. Clarify (optional)   — Sonnet 4.6
4. Compose              — Haiku 4.5 recommend_bullets + user curation
5. Template             — pick persona
6. Generate             — Sonnet 4.6, produces BOTH résumé + cover
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
                                WeasyPrint HTML→PDF, python-docx,
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

Build the unified pattern in stages, no schema breaks between stages.

### v1.0 (next branch after `feat/release-visual-ia`)

- `SummaryItem` table with `parent_kind` / `parent_id` extensibility
- `recommend_summaries` Haiku call (same shape as
  `recommend_bullets` per
  [TUNING_LOG `2026-05-22.2`](../evals/TUNING_LOG.md), including
  the no-near-duplicate rule + Jaccard dedup safety net)
- Compose step gets a "Positioning" card above the experience cards
- JSON Resume v1.0 intermediate format introduced
- WeasyPrint PDF output path added
- Live HTML preview component
- Cover-letter detachment + dedicated button + full refine/iterate
- Operationalize `PersonaTemplate.is_default` (bug fix from §5.2)

### v1.1 (immediately after v1.0; no schema break)

- `ExperienceSummaryItem` (parent = Experience) — same shape, same
  recommend call pattern
- `SkillGroupItem` — curated skill clusters per JD
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
unique index ([`db/models.py:359, 368-372`](../db/models.py)) — but
[`app.py:1403-1423`](../app.py)
`_resolve_default_persona_template_path()` never consults it. The
default resolver hardcodes to bundled Classic Single-Column. Five-
line fix; ship as part of operationalizing master résumés in §5.2.

---

## External references

- [JSON Resume v1.0 schema](https://jsonresume.org/schema/) — canonical
  intermediate format adopted in v1.0
- [WeasyPrint](https://weasyprint.org/) — HTML→PDF rendering library
- [schema.org/Person](https://schema.org/Person) — structured profile
  fields (not adopted; complementary to JSON Resume's `basics`)
- [HR-Open Standards](https://www.hropenstandards.org/) — enterprise
  ATS standards (evaluated, not adopted; wrong shape for a developer
  tool)

## Related project docs

- [`docs/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — the *what we
  ship for v1* checklist (PII scrub, cleanup pass, docs)
- [`CLAUDE.md`](../CLAUDE.md) — agent and contributor contract; the
  10-principles framework references
- [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) — institutional
  memory of prompt iterations; the `recommend_bullets` pattern this
  doc proposes mirroring lives there
- [`SECURITY.md`](../SECURITY.md) — single-tenant threat model

---

*This file lives in `docs/` so it ships with the repo. Its sibling
`docs/RELEASE_CHECKLIST.md` is the execution lens; this one is the
shape lens. Update either when the corresponding lens shifts.*
