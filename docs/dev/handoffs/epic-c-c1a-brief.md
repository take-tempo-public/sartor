# Epic C sprint brief — C1a: `fix/dashboard-run-lock-gaps` (run 1 of 4)

> Written at Epic C kickoff (`docs/epic-c-kickoff`, session `0ea1b8bf`, 2026-09-22) from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`. Later sprint briefs are written by each
> run's closer.

## Sprint identity

- **Sprint:** C1a, run 1 of 4 (`epicSprintIndex: 1`, `epicSprintCount: 4`)
- **Branch to create:** `fix/dashboard-run-lock-gaps`
- **Stacked on:** `epic/c-diagnostics` at its tip when the run starts. That tip is `main`
  once `docs/epic-c-kickoff` has merged. The invoker records the exact sha in its step-0a
  preflight. It is never `main` itself.
- **Implementer model + effort:** `sonnet`, per `epic-c-design-brief.md` §"Sprint →
  pipeline-run mapping" (RELEASE_ARC §"Session models": C1 = Sonnet, "small, fully specified
  fixes").

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md`. **Read in full**, including the ratified scope sentence and the no-prune rule in §"Branch topology". |
| Authorization envelope (run vector, halt points, flag stops) | `epic-c-design-brief.md` §"Execution mode + authorization record" and §"Escalation + envelope"; `docs/dev/n1-baseline-pipeline.md` §"Escalation — the unified primitive" |
| Close-out cadence for this epic | `epic-c-design-brief.md` §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", C1 at `:1949` (first item only: "Lock-gate the real Collate button") |
| Pre-verified UX checklist | `docs/dev/reviews/epic-c-console-ux-audit.md`, **UX-1** |

## What just landed

- `f755920` (PR #143, item 94): the interrogative-witness pause skips subagent payloads.
  **Verified:** repro test plus a live re-probe.
- `a078ca1` (PR #144, item 110): plan-approval retirement is kill-safe, and a fresh
  approval clears the stale stamp. **Verified:** repro tests plus a live check.
- `docs/epic-c-kickoff` (merged before this run): the item 96 fix (`implementerModel`
  required), this brief and the design brief, the UX audit, the corrected runbook step 9
  (no pruning at sprint boundaries), and the `.gitignore` for `.isidium/` + `.agents/`.
- **Not verified:** UX-1 is a **code trace** by the audit subagent. The kickoff session
  confirmed its cites (`dashboard.html:615`, `:1388`, `:1396`) at `a078ca1` but did **not**
  reproduce the double-run in a browser.

## What this sprint builds

**In scope (RELEASE_ARC C1, first item; UX-1):**
- `#annCollate` (`dashboard/templates/dashboard.html:615`, click handler `:2093`) is locked
  while any run is live.
- An `annCollateRunBtn` created *during* a live run (`renderCollateResult`, around
  `:1941-1948`) renders disabled.
- A second paid eval cannot start while one is live.
- The lock today only disables buttons that exist when it is acquired
  (`acquireRunLock`, `:1394-1398`), and its `if (locked) return;` makes a second acquire
  a silent no-op.

**Out of scope, deliberately:**
- the other C1 items: sticky tabs, header, banner, wait states. Those are **C1b**.
- UX-31 (`annSave`, `bsExportSeed` absent from `LOCK_BTN_IDS`; `fixtureSelect` has no lock
  check). The audit classified it out of scope and it is in item 113. If the implementer
  thinks it is the same defect, that is a flag for the owner, not a fold-in.
- a server-side run lock (no backstop exists in `blueprints/diagnostics.py`). RELEASE_ARC
  C1 names the client lock only. File an item if the refuter or judge finds it load-bearing.

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** The implementer
> verifies the named mechanism is reachable on the failing path, by reproducing the defect,
> before implementing it.

## First move

For the **implementer**: this is a `fix/*` branch, so `require-evidence-before-fix` is live.
The first artifact is `docs/dev/diagnosis/dashboard-run-lock-gaps.md` with a filled
`## Observed`: a reproduction of UX-1. The preferred form is a UX test (`pytest -m ux`,
the analyzer stubbed as elsewhere in the suite) that starts a stubbed run, clicks Collate,
and shows `#annCollate` enabled and/or a second `annCollateRunBtn` enabled. Commit the
reproduction (xfail-strict) **before** the fix. If it will not reproduce, that is the
finding: stop and flag it.

For the **invoking session**: runbook step 0 + 0a (preconditions; the batched preflight,
including the live dispatch probe `n1-agent-probe.mjs` → `ok_to_run`, the scope
reconciliation against the authorization record, and deliberate witness-pause
consumption), then:

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c1a-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 1,
  epicSprintCount: 4,
  nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c1b-brief.md',
  implementerModel: 'sonnet',
}})
```

## Decisions taken alone last sprint that this one inherits

None from a prior sprint, since this is run 1. Kickoff-session decisions that bind:
- UX-22..UX-41 are excluded from Epic C (items 112, 113);
- sprint branches are kept until the epic PR merges (runbook step 9 correction);
- the wiki pass is deferred to the epic close, with a backstop at drift 60.

## Open risks handed forward

- **UX-1 reproduction:** reported by the audit, not reproduced. See above.
- **The UX suite's flake history** (memory / carry-forward ledger): the rerun sweep is
  mandatory, and a green-after-retries result is a stop-and-look, not a pass.
- **Plan-approval hook speed** (item 111): each Edit/Write costs ~2 s on this machine. It
  is expected, not a hang.

## Flag-stop state

None.

## Gate + verification state

- Last gate run: the `docs/epic-c-kickoff` branch gate (see that branch's handoff for the
  verbatim terminal line).
- Rerun sweep: see the same handoff.
- Wiki drift at handoff: **39 of 75** (`python -m scripts.wiki_freshness`, 2026-09-22). The
  epic's backstop is 60.

---

## Close-out obligations this sprint still owes

- **Owed now:** the diagnosis dossier (C-7), a substantive commit message, the **C1b brief**
  at `docs/dev/handoffs/epic-c-c1b-brief.md` (the closer, from the template, whose First
  move must pass `implementerModel: 'sonnet'` and `epicSprintIndex: 2`), work items for
  anything discovered and not chased, BOARD regeneration, the invoker's two gate runs with
  a `RERUN` sweep, and the refuter pass.
- **Deferred to epic close:** the wiki pass (unless drift reaches 60), full grounding
  audits, the full `AGENT_HANDOFF_TEMPLATE.md` ceremony, and the epic-level adversarial
  review.
