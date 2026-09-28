# Epic C sprint brief — C1b: `feat/dashboard-polish` (run 2 of 4)

> Written by C1a's closer (`fix/dashboard-run-lock-gaps`), 2026-09-23, from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`, per the epic's declared intra-epic
> sprint-transition cadence (item 89; `epic-b-design-brief.md` §"Close-out intervals",
> restated for Epic C in `epic-c-design-brief.md` §"Close-out intervals").

## Sprint identity

- **Sprint:** C1b, run 2 of 4 (`epicSprintIndex: 2`, `epicSprintCount: 4`)
- **Branch to create:** `feat/dashboard-polish`
- **Stacked on:** `fix/dashboard-run-lock-gaps` — **committed as `150bfb9`** (verified by
  C1b's invoking session, 2026-09-23; ff-merged into `epic/c-diagnostics`, whose tip
  `3e29527` adds only a ledger receipt). The closer's original note, kept for the record:
  not yet committed as of this brief.
  This closer staged the fix (`git add -A`) but does not commit; per the corrected close
  ordering (`docs/dev/epic-a-chain-design-corrections.md` §11.9.4 / §2), the commit and the
  gate belong to the invoking session, which runs after this brief is written. The invoking
  session must record the actual commit sha here (or verify it directly) before starting
  C1b — **do not start C1b against an uncommitted tip.**
- **Implementer model + effort:** `sonnet`, per `epic-c-design-brief.md` §"Sprint →
  pipeline-run mapping" (RELEASE_ARC §"Session models": C1 = Sonnet, "small, fully specified
  fixes").

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md`. **Read in full**, including the ratified scope sentence and the no-prune rule in §"Branch topology". |
| Authorization envelope (run vector, halt points, flag stops, seam) | `epic-c-design-brief.md` §"Execution mode + authorization record" and §"Escalation + envelope"; `docs/dev/epic-a-chain-design-corrections.md` §11.4-§11.9 (the envelope this closer itself ran under). |
| Close-out cadence for this epic | `epic-c-design-brief.md` §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", C1 at `:1955-1961`; row 2 of `epic-c-design-brief.md` §"Sprint → pipeline-run mapping" (`:106`) |
| Pre-verified UX checklist | `docs/dev/reviews/epic-c-console-ux-audit.md`, **UX-2 through UX-6**, plus **UX-24** (owner fold-in, 2026-09-23) |

## What just landed

C1a (`fix/dashboard-run-lock-gaps`), staged but **not yet committed** by this closer:

- `LOCK_BTN_IDS` (`dashboard/templates/dashboard.html:1393`) gains `'annCollate'` — the
  static "Collate → fixture + brief" button is now covered by `acquireRunLock()` /
  `releaseRunLock()`'s existing `forEach`, for all four independently-wired paid-run entry
  points at once.
- `acquireRunLock()` now returns `true`/`false` instead of implicit `undefined`, and
  exposes `window.sartorRunLock.isLocked()`.
- `renderCollateResult()` sets the freshly-built `#annCollateRunBtn`'s `.disabled` from
  `isLocked()` at creation time, closing the "button built after the lock already ran"
  gap.
- The shared `run()` streamer now checks `acquireRunLock()`'s return value and refuses to
  start a second fetch when already locked, showing "A diagnostics run is already in
  progress." instead.
- Scope decision recorded in the C1a dossier: the tuning/bootstrap/grounding-score inline
  `acquire()` call sites are **not** given the same return-value hardening this sprint —
  their trigger buttons are static and already covered by `LOCK_BTN_IDS`, so `run()`'s
  fix is the only reachable path a stray enabled button could exploit. This is a within-
  brief implementation decision (§11.8), not a scope conflict.
- This closer additionally corrected a wrong citation in the diagnosis dossier
  (`docs/dev/diagnosis/dashboard-run-lock-gaps.md:107-110`): the "no server-side lock"
  claim had cited `dashboard/routes.py` (the read-only observability blueprint, which has
  no collate route at all — grep confirms zero matches), when the real route is
  `blueprints/diagnostics.py:372` (`annotation_collate`). The route body (`:372-472`) was
  read directly to confirm it in fact has no in-flight-run check — the dossier's
  conclusion was already correct; only the citation was false (C-12 evidence-integrity
  fix, not a scope change).
- **Not verified by this closer:** the full gate (`pytest`, the UX suite included) has
  **not** been run on this branch by this closer — that is the invoking session's job
  (§11.9.4). This closer ran only the three static gate steps on the current tree: `ruff
  check .` (clean), `ruff format --check .` (clean, 362 files), `python -m mypy .`
  (`Success: no issues found in 378 source files`). The invoking session still owes gate
  run #1 (pre-refuter) and #2 (post-fix) with the `RERUN` sweep.
- **Filing obligations this sprint:** none. The judge payload's single verdict (F1, a
  citation fix) carried no ordered filing beyond the dossier correction itself (an
  "optionally add a finding" note, folded directly into the same citation-fix edit above
  rather than filed as a separate work item); the judge's deferred-verdicts list was
  empty; no implementer report handed this closer anything to file. `BOARD.md` was
  regenerated (`python -m scripts.work_items board --write`) and produced **no diff** —
  consistent with zero filings.
- **Wiki:** scoped no-edit check recorded at `docs/wiki/log.md`'s 2026-09-23 C1a entry.
  Drift at C1a's tip: **39 of 75**, unchanged from kickoff, well under the epic's 60
  backstop — the full wiki pass stays deferred to the epic close.

## What this sprint builds

**In scope (RELEASE_ARC C1, second branch `feat/dashboard-polish`; UX-2..UX-6, UX-24):**
- Sticky `.dash-tabs` (UX-2) — stacks correctly with the sticky run-lock banner, stays
  visible and clickable several screens down.
- Correct the false "Read-only observability" header at `dashboard/templates/
  dashboard.html:230` (UX-3), plus the false "only write surface" claims at `:526`,
  `:1055`, `:168` (UX-24 — owner fold-in, 2026-09-23 preflight, session `1b9d9ef1`;
  Annotate and Tuning are read-write).
- Opaque + pulsing run-in-progress banner (UX-4, `:146-152`, `:213-216`) — computed alpha
  1, pulses unless `prefers-reduced-motion`.
- Port `.btn-pending` / `cb-status-pulse-strong` (`static/style.css:3226`, `:3154`) to
  every wait state (UX-5), including disabling in-flight Save/Collate.
- The terminal Cancel state reaches a visible, non-pending end (UX-6).
- Honor `prefers-reduced-motion` throughout the above.

**Out of scope, deliberately:**
- C2 (`feat/run-detail-modal`) and C3 (`feat/dashboard-copy-discovery`) — later runs.
- UX-22..UX-41 except UX-24 — excluded from Epic C per the kickoff-session decisions
  (items 112, 113). If the implementer thinks a UX-3x finding is the same defect as one
  named above, that is a flag for the owner, not a fold-in.
- Any change to `LOCK_BTN_IDS` / `acquireRunLock()` / the run-lock mechanics C1a just
  landed — C1b is CSS/copy/animation only. If C1b's implementer finds the lock itself
  needs a further change to support a wait-state idiom, that is a flag stop (scope
  question the vector does not answer — §11.6, "silence is a stop, not a licence").

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** The implementer
> verifies each named line/selector is still accurate (line numbers move after C1a's own
> edit — re-derive, do not assume `epic-c-design-brief.md`'s cite is still exact) and that
> the described defect is reachable, before implementing against it.

## First move

C1b is a `feat/*` branch, not `fix/*` — `require-evidence-before-fix` does not gate it,
and none of the touched surfaces (`dashboard/templates/dashboard.html`, `static/style.css`)
appear in `scripts/enforcement/blast_radius.py`'s gated-surface registry, so
`require-consumer-enumeration` does not gate it either (verified: neither `dashboard` nor
`style.css` appears in that file as of C1a's tip).

For the **implementer**: re-derive every cited line number against the actual branch tip
first (C1a's edits already moved several of them). Confirm each of UX-2..UX-6/UX-24's
described defects is still present by driving the running dashboard (the `run` skill /
`docs/dev/reference-sandbox-ux-walkthrough-method` pattern from memory — drive the real
app, sandboxed, rather than trust the audit's screenshots alone) before writing CSS. Then
implement, and add or extend a UX regression test per defect where the existing suite
doesn't already cover it (the acceptance criteria below are the test targets).

For the **invoking session**: runbook step 0 + 0a first (preconditions, batched preflight,
scope reconciliation, witness-pause consumption — as C1a's own kickoff-brief described),
**then verify C1a's commit landed and record its sha above** before this:

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c1b-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 2,
  epicSprintCount: 4,
  nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c2-brief.md',
  implementerModel: 'sonnet',
}})
```

## Decisions taken alone last sprint that this one inherits

From C1a, under §11.8 (decided and recorded, not surfaced mid-run):
- The tuning/bootstrap/grounding-score inline `acquire()` call sites were left without
  return-value hardening (see "What just landed" above) — C1b's wait-state work
  (`.btn-pending`/pulse idioms, UX-5) touches these same three buttons' *styling*, not
  their lock logic; do not conflate the two.
- The C1a dossier's server-side-lock citation was corrected in place (C-12 fix) rather
  than filed as a separate work item, since it corrects an in-flight sprint's own
  artifact rather than changing shipped scope.

## Open risks handed forward

- **C1a's gate has not run yet, reported by this closer, not verified end-to-end:** only
  the three static steps (ruff check/format, mypy) were run by this closer. The
  invoking session's gate #1/#2 and `RERUN` sweep are still owed and could surface an
  issue in C1a's `pytest -m ux` coverage that this brief cannot see.
- **Line-number drift:** every cite above from `epic-c-design-brief.md`'s C1b row
  predates C1a's edits to `dashboard.html`. Re-derive before relying on any of them
  (matches the design brief's own "Cite-drift note").
- **UX suite flake history** (memory / carry-forward ledger): the rerun sweep is
  mandatory; a green-after-retries result is a stop-and-look per C-7, not a pass.

## Flag-stop state

None. C1a hit no halt point and no flag stop; its only correction (the citation fix) was
an in-envelope §11.8 decision, not a stop.

## Gate + verification state

- Last gate run: **not run by this closer.** The invoking session owes gate #1 (pre-
  refuter) and gate #2 (post-fix, pre-commit) for C1a; report the verbatim terminal
  summary line here once run.
- This closer's own static checks (2026-09-23, on the staged C1a tree): `ruff check .` →
  "All checks passed!"; `ruff format --check .` → "362 files already formatted";
  `python -m mypy .` → "Success: no issues found in 378 source files".
- Rerun sweep: not yet applicable — no full gate run has happened on this branch yet.
- Wiki drift at handoff: **39 of 75** (`python -m scripts.wiki_freshness`, 2026-09-23,
  unchanged from kickoff). The epic's backstop is 60; C1b should re-check this at its own
  close, since it touches more wiki-relevant surface (`static/style.css`) than C1a did.

---

## Close-out obligations this sprint still owes

- **Owed now:** a substantive commit message, the **C2 brief** at
  `docs/dev/handoffs/epic-c-c2-brief.md` (the closer, from the template, whose First move
  must pass `implementerModel: 'sonnet'` and `epicSprintIndex: 3`), work items for
  anything discovered and not chased, `BOARD.md` regeneration, the invoker's two gate runs
  with a `RERUN` sweep, and the refuter pass. No C-7/C-10 dossier is expected (neither hook
  gates this branch as scoped above), but if the implementer's diff turns out to touch a
  gated surface or needs a `fix/*` branch after all, the corresponding dossier becomes
  owed at that point, not skipped.
- **Deferred to epic close:** the wiki pass (unless drift reaches 60), full grounding
  audits, the full `AGENT_HANDOFF_TEMPLATE.md` ceremony, and the epic-level adversarial
  review.
