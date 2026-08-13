# Epic B sprint brief — B1b: education rendering (`fix/b1-education-render`)

> Written from [`EPIC_SPRINT_BRIEF_TEMPLATE.md`](EPIC_SPRINT_BRIEF_TEMPLATE.md) — the
> declared intra-epic cadence artifact (`epic-b-design-brief.md` §"Close-out intervals").
> Authored 2026-08-12 on `fix/n1-invoker-loop` (the run-3 polish round), standing in for
> run 1's closer, whose script-directed output was the full session handoff instead (item
> 89, since fixed — the pipeline's closer now writes this artifact itself via
> `closeoutKind: 'intra_epic'`). The content below derives from the same sources that
> closer used: `epic-b-design-brief.md` row 2, `RELEASE_ARC.md` §Epic B (B1, second
> bullet), and the B1a handoff's "What this branch should build" section.

---

## Sprint identity

- **Sprint:** B1b — Epic B run 2 of 3
- **Branch to create:** `fix/b1-education-render` (name fixed in
  `epic-b-design-brief.md` row 2 — do not rename)
- **Stacked on:** `epic/b-render-ats` @ the tip **after** `fix/n1-invoker-loop`'s
  ff-merge — resolve with `git rev-parse epic/b-render-ats` at cut time and record the
  real sha in this sprint's own successor brief. Do **not** cut from `d8f0a8f` (the
  pre-polish tip) — verify `git log -1 epic/b-render-ats` shows the polish-round commit
  before cutting.
- **Implementer model + effort:** Opus (`epic-b-design-brief.md` row 2 /
  `RELEASE_ARC.md` session-models table, B1). The **invoking session's** model is the
  owner's choice of Fable or Opus, stated at invocation (RELEASE_ARC §"Session models",
  2026-08-12 amendment).

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-b-design-brief.md` — read in full; skipping this is the most expensive mistake this chain has made |
| Authorization envelope (run vector, halt points, flag stops, epic-remainder authorization) | `epic-b-design-brief.md` §"Execution mode + authorization record" (incl. the 2026-08-12 owner decision authorizing B1b/B2/epic-close without epic-level re-asking) + `docs/dev/n1-baseline-pipeline.md` §"Escalation" |
| Close-out cadence for this epic | `epic-b-design-brief.md` §"Close-out intervals" (light per sprint; full ceremony once at the epic close; board regen per-sprint — gate-bound) |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic B — `epic/b-render-ats`" (B1, second bullet, education discipline) as re-anchored by `epic-b-design-brief.md` row 2 |
| The invoker's own loop | `docs/dev/n1-baseline-pipeline.md` §"The runbook" — step 0a (preflight batch + scope reconciliation) through step 9 (the epic loop) |

## What just landed

- `d8f0a8f` — sprint B1a merged (stale imported-template companions fixed on a
  skeleton-version stamp; refuter finding F1 applied; F2 deferred as item 88; item 89
  filed). Both gates were reported green by the run-3 session; this brief's author did
  not re-run them (**I have not verified this** beyond the committed record).
- `fix/n1-invoker-loop` (the commit this file rides in) — the run-3 polish round:
  harness throws now convert to `kind: 'harness_throw'` escalations instead of killing
  the workflow silently; the closer ceremony branches on `closeoutKind` (item 89 fixed);
  the closer self-verifies with the gate's static steps (ruff / format / mypy); paths
  report repo-relative; the runbook gained the epic loop (step 9) and the step-0a scope
  reconciliation; the model policy and authorization records were amended
  (owner-directed, 2026-08-12). **Escalation routing — reviewers, halt points, the new
  harness_throw boundary — remains untested by any live run**; if a flag fires this
  sprint, it is the primitive's first live exercise. Treat its behavior as evidence to
  record, whichever way it goes.

## What this sprint builds

From `RELEASE_ARC.md` §Epic B (B1, second bullet) via `epic-b-design-brief.md` row 2:

1. **Verify the repro live FIRST, before touching any code.** The reported docx
   education-rendering behavior **conflicts with the code trace** — the docx writer is
   said to read only institution + area, never `studyType` (`generator.py:883-896`).
   That citation was **not re-verified by run 1's closer** — re-check it against HEAD
   before trusting it (C-7/C-12). If observation contradicts the reported behavior, the
   diagnosis dossier records what was actually seen and the judge/escalation path
   handles any scope implication — do not silently substitute either story.
2. Render `studyType` in the `classic`/`spacious` skeletons, the docx education block,
   and the markdown round-trip.
3. **Render-both — never flip** the documented `area`/`studyType` inversion without a
   data audit. Cite `corpus_to_json_resume.py:909-932` (the design brief's verified
   re-anchor; RELEASE_ARC's `855-878` is stale — its "Cite-drift note" says why it was
   flagged, not fixed).
4. Close the docx font-name capture gap: `_capture_proto` captures bold/size but not
   `run.font.name` (`generator.py:498-514`).

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** Reproduce the
> defect and verify the named mechanism is reachable on the failing path before
> implementing. B1a's brief named an unreachable guard; only the implementer's own
> repro caught it (run-3 retrospective, "What went wrong" #3).

**Explicitly OUT of scope:** everything in B2 (`feat/ats-conformance` — dates,
month hard-block, fonts, structural ATS tests; design brief row 3); pre-authoring
B2's brief by hand (this run's **closer** writes `epic-b-b2-brief.md` via
`closeoutKind: 'intra_epic'`); widening N past 1 (owner-reserved, §16.7); the
watching-bucket triage; any refactor beyond the numbered list above.

## First move

For the **invoking session**: runbook step 0 + 0a — preconditions, the batched
preflight (including the live dispatch probe and the scope reconciliation against the
authorization record), then:

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-b-b1b-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-b-design-brief.md',
  closeoutKind: 'intra_epic',
  nextSprintBriefPath: 'docs/dev/handoffs/epic-b-b2-brief.md',
}})
```

For the **implementer**: this is a `fix/*` branch — the first artifact is the diagnosis
dossier's `## Observed` at `docs/dev/diagnosis/b1-education-render.md` (the
`require-evidence-before-fix` hook blocks production edits until it exists). "Verify
the repro live first" above IS that first artifact, not optional framing.

## Decisions taken alone last sprint that this one inherits

- **F2 deferred as item 88** (no integration test asserting the four
  companion-resolution call sites pass the *refreshed* companion) — a
  test-architecture decision deliberately left open; do not fold it in here.
- **Item 89 filed rather than fixed** by run 1's closer (correctly, per §11.6.5) —
  since fixed on `fix/n1-invoker-loop`; this brief's existence is the fix working.
- Run 1's closer wrote the full handoff ceremony for an intra-epic transition
  (following the then-unbranched script prompt) — superseded; do not imitate.

## Open risks handed forward

- **The education repro conflict** (`generator.py:883-896` — docx writer never reads
  `studyType`): **reported**, not verified. The sprint's own step 1 settles it by
  observation.
- **The `area`/`studyType` inversion** (`corpus_to_json_resume.py:909-932`):
  **verified** re-anchor (design brief, from HEAD `31d2574`); the render-both rule is
  an owner-set constraint, not a suggestion.
- **The font-name capture gap** (`generator.py:498-514`): **reported** by the epic
  planning docs; re-verify the line anchor at HEAD before citing it in the dossier.
- **Escalation routing untested** (see "What just landed"): **verified absence** —
  `escalations: []` on every run to date.
- **Item-87 witness pause mid-run:** task notifications can re-arm the
  interrogative-witness, and its refusal landing on a subagent's first edit becomes a
  `hook_block` short-circuit stop (run-3 preflight, `acdb737`). The invoker consumes
  the pause deliberately before the first Workflow call (runbook step 0a); a mid-run
  re-arm that stops the run is the owner's call, not a thing to route around.

## Flag-stop state

None waiting. No halt point is pending; the epic PR (halt point 1) is owed only at the
epic close, after B2.

## Gate + verification state

- Last gate run: `fix/n1-invoker-loop`'s close gate, 2026-08-12 — terminal line quoted
  verbatim in `docs/dev/handoffs/fix-n1-invoker-loop.md` (written after that gate ran,
  per the close-out ordering; re-verify cheaply at step 0a with the structural suite).
- Rerun sweep: recorded in the same handoff alongside the gate line.
- Wiki drift at handoff: **17 of 75** (`python -m scripts.wiki_freshness`, 2026-08-12)
  — under the epic's 40-file deferral margin, so the wiki pass correctly stays deferred
  to the epic close. Each run's monitor re-runs the check at the sprint gate.

---

## Close-out obligations this sprint still owes

- **Owed now (per-sprint floor, `epic-b-design-brief.md` §"Close-out intervals"):**
  C-7/C-10 dossiers where triggered (hook-gated); a substantive commit message
  (composed by the invoking session for the finalize stage); **the next sprint's brief
  at `docs/dev/handoffs/epic-b-b2-brief.md`** (written by this run's closer — the
  intra-epic path); work items filed for anything discovered-and-not-chased; board
  regeneration (gate-bound); the invoking session's two gate runs with the log swept
  for `RERUN`; the refuter pass; the scoped wiki-relevance check on this sprint's own
  diff; **the invoker's sprint-boundary report to the owner** (runbook step 9 — never
  deferred to session end).
- **Deferred to epic close:** the wiki pass + `.last_ingest_sha` advance, full
  grounding audits, the full `AGENT_HANDOFF_TEMPLATE.md` ceremony with
  `verify_doc_template.py` validation, the epic-level adversarial review, experiment
  outcomes recorded, the epic PR (owner-gated halt point 1).
