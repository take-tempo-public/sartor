# Compose-time rewrite latitude — the "generate but don't invent" dial

> **Status:** findings + design input for a future tuning pass. **Nothing here is
> built, scheduled, or approved.** Sourced 2026-07-21 from an owner-led analysis of
> a real application artifact (see "Provenance" below).
> **Purpose:** record why bullet re-rendering disappeared, what machinery already
> exists to restore it, and the grounding model any tuning pass must respect.
> **Audience:** whoever picks up the tuning phase. Read before touching
> `draft_surgical_refinement`, `draft_gap_fill_bullets`, or the grounding contract.
> **Related:** [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) (grounding layers),
> `RELEASE_CHECKLIST.md` Carry-forward ledger (the tracked item pointing here).

---

## The question

Bullets selected from the corpus render **verbatim** into the generated résumé. They
are never re-worded to fit the job description they are being submitted against.
Should they be — and if so, how far, without re-opening the fabrication hole that
discipline was built to close?

The owner's framing: *"generate but don't invent … this is a delicate dance."* The
project has already been at both extremes — wide generation with weak grounding
early on, then over-corrected to verbatim-only. This document is about the setting
in between.

## Provenance (why this is not an n=1 hunch)

Three independent lines of evidence converged:

1. **A real, externally-graded artifact.** An owner résumé + the job description it
   was written against (owner-local files, not in this repo — they contain real
   personal data, see AGENTS.md). It did not win that specific role, but it was
   strong enough that the employer routed the candidate into a separate, unposted
   pipeline for a role *family* (AI-adjacent design). So: **strong positive signal
   scoped to a role category; no reliable signal about fit to that one JD**, whose
   outcome is confounded by timing and a competing offer.
2. **The corpus can reproduce it.** Every substantive fact and named
   credibility anchor in that résumé exists in the current canonical corpus —
   frequently stated *more* precisely there than in the shipped document. There are
   **zero fact gaps**. The delta is entirely **selection and phrasing**.
3. **The capability was documented, then lost.** See the next section.

That artifact is therefore a **reproducible test case with a real-world grade** — the
only one this project has. Every other fixture is synthetic or self-graded.

**Do not over-read it.** n=1, with no content-level attribution: the employer never
said which parts of the document worked. Any claim about *what* made it effective is
a hypothesis, not a finding.

## What was lost, and why it was not a grounding decision

`RELEASE_CHECKLIST.md` (the v1.0.2 WYSIWYG section, ~L3496-3504, 2026-05-26)
describes the then-current download path:

> **Download path**: `analyzer.generate()` produces markdown the LLM wrote (informed
> by the same corpus + curation, but **free to reword each bullet for sharpness / JD
> relevance**). … So the LLM rewrite can change bullet wording, ordering within an
> experience, and sometimes the summary phrasing — **the preview doesn't see any of
> that.**

Re-wording was an explicit, known capability. It was given up as **collateral from
fixing WYSIWYG divergence** (preview was corpus-rendered and verbatim; download was
LLM-reworded; they disagreed). The fix made them agree, settling on deterministic
assembly from a frozen composition (`blueprints/generation.py`'s
`_assemble_from_frozen_composition`). At the time this was framed as repairing a
*defect*, never as trading away a capability — so no ledger item records the loss.

**The trade-off may be false.** It assumed re-wording happens at *generate/render*
time, where it necessarily breaks preview==download. If it happens at **compose**
time — before the freeze — then the JD-fitted text is what gets frozen, preview and
download both read the frozen composition and still match exactly, assembly stays
deterministic (charter **C-6** intact), and rewrites stay ephemeral in the
application layer rather than being written back to corpus.

## What already exists (inventory — do not rebuild)

The "middle dial" was largely built already; what it lacks is a trigger.

| Piece | Where | What it already does |
|---|---|---|
| Evidence-anchored rewrite | `analyzer.py` `draft_gap_fill_bullets` | Emits `{text, pattern_kind, evidence:{bullet_id, quote}}` — grounding enforced by citation to a real source bullet |
| Sharpen-in-place rewrite | `analyzer.py` `draft_surgical_refinement` (~L4430) | Rewrites one bullet's phrasing; its own worked example's rationale reads *"Sharpens passive phrasing into an ownership-forward action verb; **no new facts**"* |
| Lineage link | `supersedes_bullet_id` (same call; `blueprints/applications.py`) | Distinguishes "sharpened existing bullet" (id) from "genuinely new bullet" (`null`) |
| Mutual exclusion | accept path, covered by `tests/test_accept_refinement.py::test_accept_supersedes_excludes_old_bullet` | Accepting a superseding rewrite **excludes the source bullet** from the composition |
| Structural variety | `bullet.pattern_kind` (`xyz`/`star`/`car`/`manual`, CHECK-constrained in `db/models.py`) | A schema-level taxonomy — variety is enforceable as a *distribution*, not a new concept |
| Human gate | proposal/accept flow | Rewrites are **proposed**, never auto-applied |

**Two owner-stated constraints are therefore already satisfied:**

- *"Don't present a JD-tuned bullet AND the bullet that inspired it in the same
  compose"* — enforced by `supersedes_bullet_id` + accept-time exclusion. It is a
  **lineage** relationship, not a similarity one.
- *"Dedup must not rule out a bullet generation at compose"* — not a risk: the
  Jaccard-0.75 dedup lives in `blueprints/corpus/curation.py` (corpus curation /
  duplicate-role merge), **not** in the compose path, so it cannot suppress a rewrite
  for resembling its source.

**The actual gap:** `draft_surgical_refinement` is **note-driven** (a user note about
one bullet) and **per-bullet**. There is no **JD-driven, compose-wide** pass that asks
"which selected bullets could be re-rendered against this JD's requirements?" reusing
the same contract, evidence discipline, `pattern_kind`, and supersede semantics.

## The grounding model this needs (the load-bearing part)

Any rewrite contract must distinguish **three** categories, not two. Collapsing the
middle one into the third *is* the over-conservative setting:

1. **Restatement** — the same facts, rearranged. Always safe.
2. **Categorization** — naming the recognized discipline or category that stated
   facts already belong to. The repo's own example: *"Migrated 40 services to
   Kubernetes"* → *"container orchestration at scale."* **Grounded, provided the
   category genuinely follows from stated facts.**
3. **Invention** — asserting facts (scale, outcome, method, validation) not derivable
   from any source. Always blocked.

**Category 2 is the high-value zone.** It is how output matches JD vocabulary without
inventing anything: the JD asks for a competency, the candidate's stated work
genuinely *is* that competency, so the match is real. Blocking it is what makes
output read as untailored.

**The grounding unit is the source union, not the single bullet.** `assemble_source_union`
already defines grounding against résumé + clarifications + typed edits (+
`prior_clarifications` in corpus mode). Checking a rewrite only against the one bullet
it supersedes is too narrow and will reject legitimate category-2 language.

> **Worked cautionary note.** During the 2026-07-21 analysis, this exact error was
> made *in the middle of a discussion about avoiding it*: a category-2 phrase was
> called ungrounded drift because it did not appear lexically in the single source
> bullet, when the corpus supported it plainly. The failure mode is subtle and
> recurs under time pressure — hence writing it down.

### The metric conflict — do not skip this

`grounding_overlap` is a **lexical** overlap metric. Category-2 language will register
as `missing` (the categorizing word is by definition not in the source text) even when
it is legitimately grounded. **A tuning pass that widens rewrite latitude will fight
its own deterministic metric**, and naive metric-watching will read the desired
behavior as a regression. Any such pass must decide up front whether to widen the
source union, add a category-2-aware signal, or accept and annotate the divergence.

## Open design questions (unresolved — decide with the owner)

1. **Trigger + scope.** Which selected bullets get offered for re-render — all, or
   only those matched to an uncovered/weakly-covered JD requirement?
2. **Contract wording.** How `draft_surgical_refinement`'s "no new facts" is restated
   to permit category 2 while still excluding scale/validation additions
   (*"…research **with 200 participants**"*, *"**award-winning**…"*).
3. **Variety enforcement.** Whether `pattern_kind` distribution is enforced, nudged,
   or merely reported — the owner explicitly flagged *"not overuse the same one."*
   (The artifact analysed used one syntactic device in ~55% of its bullets, versus
   ~9% in the corpus's own voice — plausibly an LLM tic rather than a success factor.)
4. **Metric handling.** See the metric conflict above.
5. **Cost + latency.** A compose-wide pass adds LLM calls to a step that is currently
   zero-LLM.

## What would validate this before any dial moves

The PX-39 real-corpus baseline (`RELEASE_ARC.md` step 12) is already scheduled to run
real analyze→clarify→generate cycles against the owner's real corpus. **If one of
those runs uses this JD against this corpus**, the same paid runs yield both PX-39's
latency/cost deliverable *and* a side-by-side: what current verbatim-selection
produces from these exact inputs, versus the artifact that actually cleared the bar.

That comparison is the evidence that would justify (or kill) this work — which keeps
it off the n=1 overfitting trap. **Evidence first, then the dial.**

## Where further material lands

The owner has additional material for this that fits the existing annotation
workflow (`evals/annotation.py`, the Annotate tab, `/tune-from-annotations`). That is
the right channel: it produces `annotations.json` + an improvement brief, which is
already the durable contract a tuning pass consumes. This document is the design
context for that work, not a substitute for it.
