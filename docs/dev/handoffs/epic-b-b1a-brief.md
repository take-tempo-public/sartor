# Epic B sprint brief — B1a: stale imported-template companions

> From `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md` — an intra-epic sprint
> transition, NOT a session handoff. Authored at epic planning (2026-08-11) as
> run 1's brief; every later sprint's brief is written by the previous run's
> closer.

---

## Sprint identity

- **Sprint:** B1a (run 1 of 3 — see the epic design brief's mapping table)
- **Branch to create:** `fix/b1-stale-template-companions`
- **Stacked on:** `epic/b-render-ats` tip — at run 1 this equals the `main`
  commit the epic branch was just cut from; the invoking session records the
  actual sha here at branch-cut time: `<filled by the invoking session>`
- **Implementer model + effort:** Opus (epic model table — design brief +
  `RELEASE_ARC.md:1829`); refuter/judge per agent frontmatter

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-b-design-brief.md` — read in full; skipping standing context is the most expensive mistake the Epic A chain made |
| Pipeline contract + escalation envelope | `docs/dev/n1-baseline-pipeline.md` (runbook, roles, escalation routing, args) |
| Close-out cadence for this epic | design brief §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic B" (B1, `RELEASE_ARC.md:1899`) — B1a takes only the stale-companion item |

## What just landed

Nothing — this is the epic's first sprint. `epic/b-render-ats` is freshly cut
from `main`; no epic commits exist. (Stated explicitly per the template rule:
an absent section reads as "nothing to report," a deleted one as "never
considered.")

## What this sprint builds

**In scope (the whole sprint):** imported-template preview companions go stale
because the regen guard checks only the `.docx` mtime
(`docx_to_persona_html.py:438-444`) — companions generated before 2026-07-09
lack the `date_range` Jinja global and lose `– Present` in previews, and no
code change ever refreshes them. Fix = a skeleton-version stamp written into
the `.persona.json` sidecar (`docx_to_persona_html.py:435`) and
regenerate-on-mismatch, so companion regeneration keys on the skeleton the app
ships, not on the user's file timestamps. Deterministic module — no LLM calls
(charter C-6).

**Explicitly OUT of scope:** the education/`studyType` work and the docx
font-name capture gap (both B1b, run 2); everything in B2 (run 3); any refactor
of `docx_to_persona_html.py` beyond the guard + stamp. The chain has already
lost a sprint to scope drift — file discoveries as work items instead.

## First move

This is a `fix/*` branch: the first artifact is the diagnosis dossier at
`docs/dev/diagnosis/b1-stale-template-companions.md` (template:
`docs/dev/diagnosis/TEMPLATE.md`; the hook wants the slug without the `fix/`
prefix) with a filled-in `## Observed` — reproduce a frozen companion (an
imported `.docx` whose `.html`/`.css` predate the `date_range` global; the
guard at `docx_to_persona_html.py:438-444` returning early is the mechanism to
demonstrate, not assert). **Never the fix first** — the
`require-evidence-before-fix` hook blocks production edits until the dossier
exists, and a hook block goes to the owner via the escalation primitive, not
around it.

## Decisions taken alone last sprint that this one inherits

None — first sprint. The epic-planning decisions this sprint operates under
(topology, cadence, run mapping) are in the design brief, taken with the owner
on 2026-08-11, not "alone."

## Open risks handed forward

- **[reported] The Workflow-harness API is unverified** — the pipeline script
  has never executed (contract doc, C-0 limits 1–2). This run IS the
  compatibility test; a load/dispatch failure is an experiment result, not a
  sprint failure.
- **[reported] The education docx repro conflict** (reported behavior vs. code
  trace, `generator.py:883-896`) stays with B1b — do not chase it this sprint.
- **[verified] Two RELEASE_ARC §Epic B cite anchors drifted** — re-anchored in
  the design brief's mapping table (C-0 note there); trust the brief's anchors.

## Flag-stop state

None. Nothing is waiting on the owner at sprint start; the run-start
confirmation itself is the invoking session's precondition, not a flag.

## Gate + verification state

- Last gate run: none on this epic — branch not yet cut. `main` at `31d2574`
  merged green through PR #125's required checks.
- Rerun sweep: n/a — first gate happens after this sprint's implementation
  (invoking session, detached, log swept for `RERUN`).
- Wiki drift at authoring: **11 of 75** (design brief §"Close-out intervals";
  backstop threshold 40 — re-check at this run's gate).

---

## Close-out obligations this sprint still owes

Per the design brief's cadence declaration (light per sprint, full at epic
close):

- **Owed now (this run):** the C-7 dossier (hook-gated); substantive commit
  message; the **B1b sprint brief**, written by this run's closer from
  `EPIC_SPRINT_BRIEF_TEMPLATE.md` (the inter-sprint handoff under test — it
  must clear the recoverability bar: a fresh agent + the brief + pointers, no
  transcript); work items for anything discovered-and-not-chased; both gate
  runs by the invoking session, `RERUN`-swept; refuter verdict dispositioned;
  ff-merge of this branch into `epic/b-render-ats` after gate #2.
- **Deferred to epic close:** wiki pass + checkpoint advance, grounding audits,
  full handoff ceremony, `BOARD.md` regeneration, epic-level adversarial
  review, experiment-outcome recording.
