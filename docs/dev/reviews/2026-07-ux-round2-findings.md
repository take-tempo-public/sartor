# sartor. — UX round-2 e2e feedback (owner, 2026-07-09)

> **What this is.** A short capture of the owner's second end-to-end
> walkthrough (round 2, 2026-07-09 — the same session the
> `docs/dev/RELEASE_CHECKLIST.md` "owner e2e round-2" resolutions cite for
> the R2-live-analyze-streaming and merge-suggestion-threshold facts). This
> pass surfaced UX friction across generate/compose/templates/corpus, coded
> below by surface. It is a findings + disposition capture, not a full
> persona study like [`2026-07-ux-review/`](2026-07-ux-review/README.md) — see
> that review for the fuller three-persona methodology this one doesn't
> repeat.
>
> **What this is not.** No design spec. Findings that need a shape decision
> (state-communication unification, skills redesign, iconography, caps-vs-
> sentence-case) are registered as an epic (see
> [`RELEASE_ARC.md`](../RELEASE_ARC.md) "UX Cohesion Epic"), not designed
> here. Findings that are decision-free, small, and code-verified land on
> `fix/round2-quick-wins` (this branch) as Wave A.

## Finding themes (by surface)

**Global (G):**
- **G1** — modal open/close fades read as abrupt / inconsistent across the app's several modal surfaces.
- **G2** — state-communication gaps: some long-running actions don't clearly signal "working" the way the `_setBusy` banner does elsewhere.
- **G3** — iconography is inconsistent (mixed metaphors / no consistent icon set) across skills, templates, and other chips.
- **G4** — (paired with G2) additional state-communication gaps found on a different surface during the walkthrough.
- **G5** — inconsistent capitalization: ALL-CAPS labels sit next to sentence-case labels with no evident rule.
- **G6** — the clarify / "more questions" flow has a busy-state gap: `runClarify()` and `runIterateClarify()` show a local pending indicator but never engage the app-wide `_setBusy` banner the way analyze/generate/compose do.
- **G7** — prior-application cards are too large/verbose for a roster view; want a compact card.
- **G8** — (paired with G2/G4) a third state-communication gap.

**Corpus (C):**
- **C1** — skill denial semantics are unclear (what "Deny" actually does to a pending suggestion isn't obvious from the UI) — a schema/labeling question, not a quick CSS fix.
- **C2** — the Corpus skills editor and the Compose skills card/list have no scroll bound — a candidate with many skills gets an editor that grows to take over the window instead of scrolling internally.

**Templates (T):**
- **T1** — owned-template cards overflow: the 5 action buttons (including Delete, rendered last) don't fit the ~280–320px card width and spill out.
- **T2** — template-preview fidelity: the preview shows "odd spacing (gaps between sections sometimes)", "fallback to parts of classic single column (the colored bars)", and inaccurate paging. See the T2 deep-dive below — this is the preview's architectural ceiling, not a quick fix.

**Compose (Co):**
- **Co1** — skill icons need the same iconography pass as G3.
- **Co2** — the "Tailor skills to this JD" button (`_fireRecommendSkills`) has no working-state — a user can click it again or think it's a no-op while the Haiku call is in flight, unlike its sibling "Suggest skills from this JD" (`_fireSuggestSkills`), which already disables + relabels.
- **Co3** — suggested skills sometimes read as ATS-shaped but low quality — a prompt/tuning-loop question, not a code branch.
- **Co4** — the corpus-wide "suggest skills from my corpus" capability exists server-side (`analyzer.suggest_skills_from_corpus` + the `/api/users/<username>/skills/suggest-from-corpus` route, already built and tested) but has no UI entry point — a candidate can't populate Skills before their first application.
- **Co5** — Compose's background reload-on-save is too quiet; the owner wants the "did that actually save" moment to feel louder — a design question about degree, not a bug.

**Output (O):**
- **O1a** — the downloaded/previewed `.docx` runs sections and work entries together with no blank-line separation, reading as a dense wall of text.
- **O1b** — dates right-alignment in the entry-header line — reopened "generally" by the owner. **RESOLVED, no code change** (owner decision 2026-07-09: keep status quo). See the O1b deep-dive below.

## Disposition table

| Finding | Theme | Disposition |
|---|---|---|
| G1 | modal-fade | → Epic (design-system) |
| G2 / G4 / G8 | state-comm | → Epic (shape = strengthen the existing `_setBusy` banner) |
| G3 | iconography | → Epic |
| G5 | caps-vs-sentence-case | → Epic |
| **G6** | clarify / more-Q busy-gap | **→ Wave A (this branch)** |
| G7 | compact prior-app cards | → Epic |
| C1 | denial semantics | → Epic (schema) |
| **C2** | skills bounded-scroll | **→ Wave A (CSS bounds only; collapsible-toggle deferred to the epic)** |
| **T1** | templates overflow | **→ Wave A** |
| T2 | template-preview fidelity | → Epic (spike-first; cross-ref roadmap paged.js design-spike) |
| Co1 | skill icons | → Epic (with G3) |
| **Co2** | tailor-skills-state | **→ Wave A** |
| Co3 | skill-ATS-quality | → tune-loop (not a code branch) |
| **Co4** | wire corpus-groomer | **→ Wave A** |
| Co5 | compose-reload-loudness | → Epic |
| **O1a** | docx blank-lines | **→ Wave A** |
| O1b | dates-right-align | → RESOLVED, no code change (owner: keep status quo; false-constraint conclusion recorded) |

## Owner decisions (2026-07-09)

1. **Sequencing.** Land the six decision-free quick wins now (Wave A, this
   branch); everything that needs a design/shape decision moves to its own
   epic rather than being decided inline mid-branch.
2. **State-communication shape.** The fix is to **strengthen the existing
   non-blocking banner** (`_setBusy` in `static/app.js`) and fill its
   remaining gaps (starting with G6 here) — **not** to introduce a new
   modal or a different mechanism. The epic's G2/G4/G8/Co5 items inherit
   this same shape constraint.
3. **Dates.** O1b was reopened generally, an evidence pass ran, and the
   owner chose **keep status quo** — no proactive right-alignment; respect
   the imported template. The "never right-align for ATS" premise was found
   to be a **false constraint** (see the O1b deep-dive), and that conclusion
   is recorded so it can't be re-litigated. **RESOLVED, no code change.**

## Wave A — what actually landed here

See `CHANGELOG.md` `[Unreleased]` and the per-fix commits on
`fix/round2-quick-wins` for the landed detail: G6 (`_setBusy` wrap on
`runClarify()`/`runIterateClarify()`), C2 (bounded-scroll CSS on the two
skills surfaces), T1 (`flex-wrap` on `.persona-card-actions`), Co2 (working-
state on `_fireRecommendSkills()`), Co4 (wired "Suggest skills from my
corpus" into the Corpus-tab skills editor), O1a (blank-line section/entry
spacing in `generator.py:_write_docx_from_json_resume`).

## O1b deep-dive — dates right-alignment (RESOLVED, no code change)

**Decision (owner, 2026-07-09): keep status quo.** No proactive
right-alignment; respect whatever the imported template does. Recorded here
so the "never right-align for ATS" premise can't quietly return as a
constraint on a future branch.

**The evidence pass (read-only).** The finding was reopened "generally" on a
suspicion that dates *should* be right-aligned but that ATS parsers would
choke on it. A read-only ATS-evidence pass found the opposite:

- **Right-aligned dates via a right *tab stop* are ATS-safe** (high
  confidence). The established ATS-parsing risk is **tables, multi-column
  layouts, and text-boxes** — not a tab stop. A right tab stop keeps the job
  entry as **one paragraph with a single `\t`**, which an ATS reads as one
  coherent string tied to that entry; it is not a column. The University at
  Buffalo School of Management ATS-résumé guide states the
  tab-stop-vs-column distinction explicitly, and OOXML models a tab stop as
  a `w:tabs`/`w:tab` paragraph property (datypic.com OOXML `w:tabs` spec) —
  not a table cell. python-docx exposes exactly this via
  `paragraph_format.tab_stops` (python-docx text docs).
- So **"never right-align for ATS" was a FALSE constraint.** It conflated
  "right-aligned via a right tab stop" (safe) with "laid out in a
  table/column" (the actual risk). Workable's "how an ATS reads resumes" and
  Jobscan's resume-dates + tables/columns guides corroborate that the risk
  lives in tables/columns/text-boxes, not tab stops.

**What `fix/persona-fidelity-and-residuals` actually shipped.** That earlier
branch is sometimes remembered as an "ATS date fix"; it was not. It was a
**preview/download PARITY** fix: the preview must not *idealize* a
right-alignment the download won't actually produce. The owner's three real
templates simply **lack a right tab stop**, so the honest layout is
left-flowed — and forcing a right-align into the preview would make the
preview lie about the download. That parity rationale stands independently of
the (now-debunked) ATS concern.

**Net.** Both the ATS worry and the "must right-align" impulse dissolve: the
tool should reproduce the template faithfully (parity), a template that
*does* carry a right tab stop is ATS-safe to reproduce as-is, and sartor.
should not inject a right-alignment the source template doesn't have. No
code change; the status quo already does the right thing.

**Sources (for a future re-scoper who doubts the false-constraint call):**
OOXML `w:tabs` element spec (datypic.com); python-docx text /
`paragraph_format.tab_stops` docs; Workable "how an ATS reads resumes";
University at Buffalo School of Management ATS-résumé guide (tab-stop vs
column); Jobscan resume-dates guide + Jobscan tables/columns guide.

## T2 deep-dive — template-preview fidelity (spike-first, → Epic)

**Owner's actual symptom** (the earlier transcription was truncated): the
in-app preview shows **odd spacing** ("gaps between sections sometimes"), a
**fallback to parts of Classic single-column** ("the colored bars"), and
**inaccurate paging**.

**Root cause = the preview's architectural ceiling.**
`docx_to_persona_html.py` **always renders single-column**: per its own
docstring, python-docx cannot represent multi-column layouts, tables,
text-boxes, or shading, so the preview extracts only *typography* from the
persona template and lays it onto the **Classic single-column skeleton**.
Consequences:

- **Colored section bars** are docx **shading** — not extracted — so a
  template that uses them drops to the plain Classic bars in preview.
- **Multi-column** persona layouts and **accurate paging** are out of reach
  of the current preview path entirely.
- **Paging** in preview is a **paged.js polyfill** — an approximation, not
  the real pagination engine, so page breaks in preview ≠ the real output.

**Disposition: spike-first, not a quick fix.** Cross-referenced to the
roadmap's **existing paged.js design-spike** — `RELEASE_ARC.md` Phase 6
`spike/pagedjs-design` + the Phase 4.9 preview-engine note. Acceptance
targets for whatever the spike proposes: **colored bars, multi-column,
section spacing, and accurate paging** all faithful in preview.

**Caveat to verify when scoping.** Confirm whether the **docx DOWNLOAD** —
which uses the *real* template as its style source via
`_write_docx_from_json_resume(template_path=…)` — is already **faithful**
while only the in-app **PREVIEW** is lossy. If so, the gap is preview-only,
and the principle at stake is **"preview should match output"**: the fix is
to raise the preview's fidelity to the download's, not to change the
download. That distinction determines the spike's scope and must be checked
against the real download before the spike commits to an approach.
