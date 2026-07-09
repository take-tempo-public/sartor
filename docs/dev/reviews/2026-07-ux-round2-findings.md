# sartor. — UX round-2 e2e feedback (owner, 2026-07-09)

> **What this is.** A short capture of the owner's second end-to-end
> walkthrough (round 2, 2026-07-09 — the same session the
> `docs/dev/RELEASE_CHECKLIST.md` "owner e2e round-2" resolutions cite for
> the R2-live-analyze-streaming and merge-suggestion-threshold facts). This
> pass surfaced UX friction across generate/compose/templates/corpus, coded
> below by surface. It is a findings + disposition capture, not a full
> persona study like [`2026-07-ux-review/`](../2026-07-ux-review/) — see
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
- **T2** — template-preview feedback from the owner's session was truncated/unclear in transcription; needs the owner to restate before it's actionable.

**Compose (Co):**
- **Co1** — skill icons need the same iconography pass as G3.
- **Co2** — the "Tailor skills to this JD" button (`_fireRecommendSkills`) has no working-state — a user can click it again or think it's a no-op while the Haiku call is in flight, unlike its sibling "Suggest skills from this JD" (`_fireSuggestSkills`), which already disables + relabels.
- **Co3** — suggested skills sometimes read as ATS-shaped but low quality — a prompt/tuning-loop question, not a code branch.
- **Co4** — the corpus-wide "suggest skills from my corpus" capability exists server-side (`analyzer.suggest_skills_from_corpus` + the `/api/users/<username>/skills/suggest-from-corpus` route, already built and tested) but has no UI entry point — a candidate can't populate Skills before their first application.
- **Co5** — Compose's background reload-on-save is too quiet; the owner wants the "did that actually save" moment to feel louder — a design question about degree, not a bug.

**Output (O):**
- **O1a** — the downloaded/previewed `.docx` runs sections and work entries together with no blank-line separation, reading as a dense wall of text.
- **O1b** — dates should right-align in the entry-header line — reopened generally by the owner (a prior narrower fix landed honest date-column layout on `fix/persona-fidelity-and-residuals`, but the owner wants the broader question re-examined) — evidence-first research pending, not yet a code branch.

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
| T2 | template-preview | → owner-clarify (feedback truncated) |
| Co1 | skill icons | → Epic (with G3) |
| **Co2** | tailor-skills-state | **→ Wave A** |
| Co3 | skill-ATS-quality | → tune-loop (not a code branch) |
| **Co4** | wire corpus-groomer | **→ Wave A** |
| Co5 | compose-reload-loudness | → Epic |
| **O1a** | docx blank-lines | **→ Wave A** |
| O1b | dates-right-align | → research-first (owner reopened generally) |

## Owner decisions (2026-07-09)

1. **Sequencing.** Land the six decision-free quick wins now (Wave A, this
   branch); everything that needs a design/shape decision moves to its own
   epic rather than being decided inline mid-branch.
2. **State-communication shape.** The fix is to **strengthen the existing
   non-blocking banner** (`_setBusy` in `static/app.js`) and fill its
   remaining gaps (starting with G6 here) — **not** to introduce a new
   modal or a different mechanism. The epic's G2/G4/G8/Co5 items inherit
   this same shape constraint.
3. **Dates.** O1b is **reopened generally** — the owner wants the
   right-alignment question re-examined from evidence rather than assumed;
   this is research-first, not yet scoped as a branch.

## Wave A — what actually landed here

See `CHANGELOG.md` `[Unreleased]` and the per-fix commits on
`fix/round2-quick-wins` for the landed detail: G6 (`_setBusy` wrap on
`runClarify()`/`runIterateClarify()`), C2 (bounded-scroll CSS on the two
skills surfaces), T1 (`flex-wrap` on `.persona-card-actions`), Co2 (working-
state on `_fireRecommendSkills()`), Co4 (wired "Suggest skills from my
corpus" into the Corpus-tab skills editor), O1a (blank-line section/entry
spacing in `generator.py:_write_docx_from_json_resume`).
