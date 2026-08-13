# Epic B design brief — `epic/b-render-ats` (board 37): rendering + ATS correctness

> **Purpose:** the standing context for every agent in Epic B — the epic's scope,
> sprint sequence, branch topology, cadence declarations, and experiment record.
> This is the file `epicBriefPath` points at on every pipeline invocation
> (`docs/dev/n1-baseline-pipeline.md` §"Args reference"): the escalation
> reviewers' wider view.
> **Audience:** the invoking (monitor) session of each Epic B pipeline run; the
> pipeline's agents (implementer, refuter, judge, closer, escalation reviewers);
> the owner.
> **Authoritative for:** Epic B's execution mode, sprint → run mapping, branch
> topology, close-out intervals, and coherence-drift checkpoint declaration.
> Sprint *scope* stays authoritative in `docs/dev/RELEASE_ARC.md` §"Epic B" —
> this brief cites it and does not fork it.
> **Referenced once, never restated** — sprint briefs point here (§15.4
> discipline, `docs/dev/epic-a-chain-design-corrections.md:1311`).

---

## Execution mode + authorization record

**Epic B is the first authorized test of the N=1 baseline pipeline** (item 84,
built on `feat/n1-baseline-pipeline`, PR #125 — status at authoring: BUILT,
NEVER RUN).

- **Owner decision, 2026-08-11 (session `06958323`):** run the epic as a test,
  as written in the recorded docs; the inter-sprint handoff is an explicit test
  vector; the owner watches the console and is the live interrupt.
- **Invoking-session model: the owner's choice of Fable or Opus, stated at
  invocation** — amended 2026-08-12 per `docs/dev/RELEASE_ARC.md` §"Session
  models" (dated amendment there carries the rationale). ~~Opus, no amendment
  needed~~ superseded. Sprint-internal agents are unchanged: the model table
  below and the role frontmatter stay authoritative.
- **This brief records intent; it does not discharge the run confirmation.**
  Each run session confirms the run with the owner at its start
  (`docs/dev/n1-baseline-pipeline.md` header: running is its own owner opt-in).
  Item 84 (`watching`) is where first-run evidence lands.
- If Epic B succeeds, Epic C repeats the experiment (monitor model again the
  owner's per-run choice). That is a later owner decision, not authorized here.

**Owner decision, 2026-08-12 (on screen, after run 1 closed sprint B1a):** the
**remainder of Epic B — run 2 (B1b), run 3 (B2), then the epic close-out and
the epic PR — is authorized to run through the pipeline, one sprint per run,**
and this record is the authorization: an invoking session does not ask for
epic-level permission again. What the invoker still confirms per session is
the **run opt-in** (the bullet above — "may I start this run now") and any
genuine decision the records do not settle; what it never re-asks is what this
paragraph grants — which sprints may run, the license to continue to the next
sprint at each boundary per the runbook's epic loop
(`docs/dev/n1-baseline-pipeline.md` step 9), and the invoking model the owner
stated at launch. **The invoking session's job between runs is to MANAGE THE
FLOW:** consume the closer-written next-sprint brief, run the sprint,
ff-merge on gate #2 green, **report the boundary to the owner immediately**,
and continue — or stop cleanly on a degraded context with the exact resume
state named. Per-session sprint scope is whatever the owner's invocation
message states (default: one sprint per session). Context for the record:
run 1's invoker instead performed a session-terminating close-out after one
sprint and reported nothing — the owner lost a day to a stopped epic that
read as running (item 84, tenth failure; the scoping conflict this paragraph
now closes).

## Goal + scope

Rendering + ATS correctness — board item 37. The sprint-level scope of record is
`docs/dev/RELEASE_ARC.md` §"Epic B — `epic/b-render-ats`" (B1 at
`RELEASE_ARC.md:1899`, B2 at `RELEASE_ARC.md:1912`). Nothing outside that
section is in scope for this epic; discovered-and-not-chased work gets filed as
work items, not folded in.

## Sprint → pipeline-run mapping

One run = one sprint = one branch (N=1 is structural — `const N = 1` is pinned
in the script and by test). Epic B is **three runs**:

| Run | Sprint | Branch | Implementer | Scope (cite — RELEASE_ARC §Epic B) |
|---|---|---|---|---|
| 1 | B1a | `fix/b1-stale-template-companions` | Opus | Stale imported-template companions: previews clone `classic.html` at import and the regen guard checks only mtime (`docx_to_persona_html.py:438-444`), freezing pre-2026-07-09 companions without the `date_range` global (the "– Present" loss). Fix = skeleton-version stamp in `.persona.json` + regenerate on mismatch. Deterministic. |
| 2 | B1b | `fix/b1-education-render` | Opus | Education discipline: **verify the repro live first** — the reported docx behavior conflicts with the code trace (the docx writer reads only institution + area, never `studyType` — `generator.py:883-896`). Then render `studyType` in the `classic`/`spacious` skeletons, the docx education block, and the markdown round-trip; render-both — never flip the documented `area`/`studyType` inversion (`corpus_to_json_resume.py:909-932`) without a data audit. Plus the docx font-name capture gap (`_capture_proto` captures bold/size but not `run.font.name`, `generator.py:498-514`). |
| 3 | B2 | `feat/ats-conformance` | Sonnet | ATS conformance: dates to `MM/YYYY` with the en-dash range separator retained, via the single canonical helper (`json_resume.format_month_year`/`format_date_range`, `json_resume.py:582-616` — currently `MM-YYYY`); month hard block at generate time for included experience roles with year-only dates (education exempt — owner decision) + "month needed" corpus badge + month-required create/edit validation (`blueprints/corpus/experiences.py:119-122,222-227`) + import-path surfacing (year-only roles enter with no warning — `onboarding/extract_experiences.py:85`, `onboarding/corpus_import.py:670-677`; the import summary must report "N roles need month precision and will block generation"). Approved fonts [Arial, Calibri, Georgia]. Structural tests: single column, no tables/text boxes/headers/footers, standard headings only. |

Refuter (Sonnet) and judge (Opus) models are pinned in `agents/n1-refuter.md` /
`agents/n1-judge.md` frontmatter — the single source of truth for
agentType-dispatched models.

**Cite-drift note (C-0):** two RELEASE_ARC §Epic B anchors had drifted at
authoring and are re-anchored above from HEAD `31d2574`: the education inversion
(RELEASE_ARC says `corpus_to_json_resume.py:855-878`; actual `909-932`) and the
create/edit validation (RELEASE_ARC says `118-122,214-220`; actual
`119-122,222-227`). RELEASE_ARC deliberately not edited — flagged here per the
standing flag-don't-fix precedent for inherited cite drift; this brief's anchors
are the verified ones.

## Branch topology

`epic/b-render-ats` off `main`. **Each sprint runs on its own real branch**
(named in the table above), stacked on the epic branch tip and fast-forward
merged into `epic/b-render-ats` after that run's gate #2. One epic PR to `main`
at the epic close — owner-gated, halt point 1, as always.

**This deliberately diverges from Epic A's topology** (sprints as commit
sequences directly on `epic/a-app-core`), and the reason is enforcement, not
taste: B1's work is evidence-first `fix/*` work, and the
`require-evidence-before-fix` hook keys on the `fix/*` branch name. On the epic
branch it would never fire — silently downgrading C-7 from enforced to advisory,
the exact failure `docs/dev/epic-a-chain-design-corrections.md` §5 records
(folding item 20 into `feat/compose-wait-ux` switched off C-7). Real `fix/*`
branches keep the hook live inside the pipeline; if it blocks an agent, the
unified escalation primitive routes the block to the owner verbatim — that is
the pipeline working, not failing.

## Close-out intervals — declaration (required by RELEASE_ARC epic-planning rule)

**Light per sprint; one full close-out at the epic end.** This is Epic A's
cadence **re-argued for B, not inherited** (RELEASE_ARC:1782 — "each epic's own
brief must state its own answer"):

- H-6's limb 1 held on Epic A: no defect escaped that the deferred ceremony
  would have caught, and the full-epic adversarial review at the close is where
  both real findings (items 75, 76) came from
  (`epic-a-chain-design-corrections.md` §15.6.1).
- The pipeline itself adds per-sprint checks Epic A's light cadence lacked: an
  adversarial refuter on every sprint's staged diff, a judge, and a structured
  run report with the §11.9 accounting check.
- Owner cost tolerance (RELEASE_ARC:1782–1788): 10–20% comfortable, 40% only if
  it prevents compounded failure. Full ceremony three times in a three-sprint
  epic would land at the wrong end of that trade.

**Per-sprint floor** (non-negotiable, §15.2's list): C-7/C-10 dossiers where
triggered (hook-gated), a substantive commit message, the **next sprint's brief**
(from `EPIC_SPRINT_BRIEF_TEMPLATE.md`, written by that run's closer — this is
the inter-sprint handoff under test), work items filed for anything
discovered-and-not-chased, the invoking session's two gate runs with the log
swept for `RERUN`, the refuter pass.

**Deferred to the epic close** (scheduled, not skipped): the wiki pass +
`.last_ingest_sha` advance, full grounding audits, the full
`AGENT_HANDOFF_TEMPLATE.md` ceremony with `verify_doc_template.py` validation,
~~`BOARD.md` regeneration~~ (correction 2026-08-12: board regeneration cannot
be deferred — the gate's own `work_items check` step binds board freshness on
every gate run, `scripts/gate.py`, so it stays per-sprint; run 1's closer
already regenerated it, correctly), the epic-level adversarial review,
experiment outcomes recorded (below).

**Wiring note, 2026-08-12 (item 89 fixed):** this cadence is now enacted by
the pipeline itself — `n1-baseline.mjs` branches its closer on
`args.closeoutKind` (`'intra_epic'` → the next sprint's brief from
`EPIC_SPRINT_BRIEF_TEMPLATE.md`; `'terminal'` → the full handoff ceremony),
pinned by `tests/test_n1_pipeline.py::TestScriptStructure::test_closer_ceremony_branches_on_closeout_kind`.
The invoking session passes `'intra_epic'` + `nextSprintBriefPath` on every
sprint with a successor (B1b → names `epic-b-b2-brief.md`) and `'terminal'`
on the epic's last (B2).

**Wiki backstop, re-derived not inherited:** drift is **11 of 75** at authoring
(`python -m scripts.wiki_freshness`, 2026-08-11). Each run's monitor re-runs it
at the sprint gate; if drift exceeds **40** (deliberate margin, same logic as
§15.2's, against the same 75 threshold), the wiki pass runs **that sprint**, not
at the epic close.

## Coherence-drift checkpoints — declaration: none scheduled, and why

The epic-planning rule requires checkpoints or a written justification
(RELEASE_ARC:1771). **Justification for none:**

- At N=1 the drift layer is inert by construction — coherence drift is evaluated
  at intra-run sprint boundaries, and a one-sprint run has none. The reactive
  counters (`driftBackstop`, `deferredDriftThreshold`) stay at defaults and
  cannot fire.
- Every inter-sprint boundary in this epic is an owner-visible session boundary:
  the boundary reviewer is the owner, exactly as in today's process
  (`epic-a-chain-design-corrections.md` §16.5.1), and for this first test the
  owner is additionally watching the console live.
- The epic is three sprints. The shortest recorded drift backstop (3 sprints)
  would fire at most once, at a boundary the owner already reviews.

If Epic B's outcomes show trajectory wandering the owner had to catch manually,
that is evidence **for** scheduling checkpoints in Epic C's brief — record it,
don't retrofit it mid-epic.

## Escalation + envelope

The unified escalation primitive, halt points, and flag stops are authoritative
in `docs/dev/n1-baseline-pipeline.md` §"Escalation" (routing:
`halt_point`/`hook_block` short-circuit to the owner with no reviewer spawned;
`flag_stop`/`coherence_drift` get one independent Opus reviewer, then one more
before a full stop). Push, PR, and merge are owner-only (halt point 1) — the
run's "no intervention" target ends at PR-ready, per §15.1 decision 1.

## Acceptance criteria (epic-level)

From RELEASE_ARC §Epic B, restated as testable outcomes:

- **B1a:** a pre-2026-07-09 imported template's companion regenerates on next
  use (skeleton-version stamp mismatch), restoring `– Present` in previews; a
  current companion is not needlessly regenerated.
- **B1b:** the education repro is settled by observation first;
  `studyType` renders in classic/spacious skeletons, the docx education block,
  and the markdown round-trip; the `area`/`studyType` mapping is unchanged
  unless a data audit says otherwise; docx font names survive capture.
- **B2:** all rendered dates read `MM/YYYY` (range separator ` – ` retained,
  `– Present` for current) across preview/PDF/docx/markdown; generation
  hard-blocks on year-only included experience roles with a visible badge +
  validation + import-summary surfacing; bundled templates use approved fonts
  with off-list mapping + notice; structural ATS tests pass.
- Gate green (both runs per sprint), every sprint's refuter verdict dispositioned,
  one epic PR at the end.

## What the experiment measures (recorded at epic close, including failures)

Per the §15.6.1 precedent — outcomes are the deliverable:

1. **Harness compatibility** — the contract doc's C-0 limits 1–2 (Workflow API
   and bare-name agentType dispatch, both unverified until run 1). Run 1 is the
   compatibility test.
2. **Escalation behavior** — do halt points / hook blocks / flag stops route as
   designed, with verbatim text surfacing to the owner?
3. **Inter-sprint brief sufficiency** — H-7 at n>1: can each fresh cast execute
   from the closer-authored brief + pointers alone, without a transcript?
4. **Run-report/accounting fidelity** — does `claimedFilesWritten` cover
   `git status --porcelain` exactly, run after run?
5. **Owner interruption count** — how many console interventions the epic
   actually needed, and at which points (the H-9 question, re-scoped to a
   pipeline that is *allowed* to escalate).
