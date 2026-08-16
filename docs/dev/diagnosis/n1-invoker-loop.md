# Diagnosis — the pipeline's invoker has no epic loop; every run ends after one sprint by construction

> **Status:** root cause PROVEN — the defect is in committed doc/prompt text, quoted below; for a
> process defect the doc text IS the mechanism.
> **Branch:** `fix/n1-invoker-loop`

---

## Symptom

The owner authorized the entire Epic B (three sprints) to run through the N=1 pipeline, one
sprint at a time, with the invoking session consuming each closer-written brief and feeding the
next run. Run 3 (2026-08-12) completed sprint B1a, then the invoking session executed a full
single-branch close-out ceremony — merge, prune, pointer — and ended, one sprint into a
three-sprint epic, without reporting the boundary. The owner discovered the epic was not
running a day later. Epic-level score after three attempts: 0/3.

---

## Observed

- **The runbook has no loop.** `docs/dev/n1-baseline-pipeline.md` §"The runbook" runs steps
  0 → 8 (step 8: "Durable capture") and stops. No step directs the invoking session to consume
  the closer-written next-sprint brief and return to step 0/1. Verified by reading the full
  section this session (`n1-baseline-pipeline.md:87-190` at `d8f0a8f`).
- **The closer prompt hardcodes the session-terminating ceremony every sprint.**
  `.claude/workflows/n1-baseline.mjs:440-448` (step 4 of the closer prompt) unconditionally
  directs every closer to the full `AGENT_HANDOFF_TEMPLATE.md` + `verify_doc_template.py
  --event generated` ceremony. No conditional distinguishes an intra-epic sprint transition
  from a terminal close. Quoted and filed as **work item 89** by run 3's own closer
  (`docs/dev/work/items/0089-sprint-brief-template-not-wired-into-n1-pipeline.md`), which also
  quotes the contradicting owner-approved cadence: `epic-b-design-brief.md` §"Close-out
  intervals" — *"Light per sprint; one full close-out at the epic end"*, with the next sprint's
  brief written *"from `EPIC_SPRINT_BRIEF_TEMPLATE.md`"*.
- **The declared per-sprint artifact was never produced.** `ls docs/dev/handoffs/` this session:
  `epic-b-b1a-brief.md` exists; **no `epic-b-b1b-brief.md` exists**. Run 1's closer wrote the
  full handoff (`fix-b1-stale-template-companions.md`, consumed by this session,
  fingerprint `e55c82d5bdd2`) instead — exactly what the un-branched closer prompt instructed.
- **A harness throw bypasses the escalation primitive entirely.** `n1-baseline.mjs` contains
  exactly one try/catch (the `args` JSON parse, line ~283); no `agent()` call is wrapped. The
  committed run-3 record (`n1-baseline-pipeline.md` C-0 limit 2; retrospective in
  `fix-b1-stale-template-companions.md` @ `cc960a5`, "What went wrong" item 1) shows run
  `wf_9bb80d14-c94` dying at the refuter spawn with `agent type 'n1-refuter' not found` after
  22 min / 169k tokens — and the retrospective records `escalations: []` on every run to date:
  *"Escalation routing remains UNTESTED after three runs."*
- **The model pin excludes the model the owner now wants available.**
  `docs/dev/RELEASE_ARC.md:1815-1816`: *"epics run on Opus and Sonnet, without Fable — the
  Epic B test specifically runs with Opus."* Mirrored at `epic-b-design-brief.md` §"Execution
  mode" bullet 2 and `n1-baseline-pipeline.md` §"Roles" model-policy line. Owner directive
  received this session (2026-08-12, on screen): the invoking-session model becomes the
  owner's choice of **Fable or Opus**, stated at invocation.
- **The runbook header is stale against its own evidence.** `n1-baseline-pipeline.md:11` reads
  *"Status: BUILT, NEVER RUN"* while the same file's C-0 limit 2 records a live run
  (`wf_9bb80d14-c94`, 2026-08-12) and `tests/test_n1_pipeline.py::test_states_never_run_limit`
  pins the stale string.
- **The gate binds board freshness per-sprint.** `scripts/gate.py:63` runs
  `python -m scripts.work_items check` inside every gate run — so the design brief's deferral
  of "BOARD.md regeneration" to the epic close is unimplementable without a red gate (run 1's
  closer did regenerate the board, confirming the practice).
- **Owner authorization + scoring, received directly this session (2026-08-12):** the epic's
  remainder (B1b, B2, epic close + PR) runs one sprint per run; the invoker manages the flow;
  the next run is scoped to one sprint done right; invoker model is the owner's choice of
  Fable or Opus per run. This directive is the authority for the amendments this branch
  records; it exists in this session's conversation, not yet in any durable doc — which is
  precisely what this branch fixes.

---

## Falsified

- *"The B1b brief is already written and waiting"* (run 3's closing chat claim) — falsified in
  the declared-format sense: no `epic-b-b1b-brief.md` exists (ls above). The claim is true only
  if the full session handoff is counted as the brief; the design's declared artifact is absent.
- The bare-name `agentType` dispatch hypothesis was already falsified live by run 3
  (`wf_9bb80d14-c94`) and fixed in `2807979` — recorded here only so no reader re-chases it;
  not this branch's subject.

---

## Inferred

- Run 3's invoker ended the epic because the two committed instructions it followed both
  terminate: the runbook ends at step 8 and the closer prompt directs the full
  session-terminating ceremony. This is an inference about *that session's* motivation (its
  transcript was not re-read here), but the doc text that would produce exactly that behavior
  in any compliant agent is quoted above — and the same text will produce it again in run 4 if
  unfixed.

---

## Falsification

**The instrument precedes the fix (C-7): the new structural pins must FAIL on HEAD.**

- `test_closer_ceremony_branches_on_closeout_kind` — asserts `closeoutKind` appears in the
  script's code (blanked-source scan) and both `EPIC_SPRINT_BRIEF_TEMPLATE.md` and
  `AGENT_HANDOFF_TEMPLATE.md` are cited in the closer prompt. **Must fail at `d8f0a8f`**
  (no `closeoutKind`, no `EPIC_SPRINT_BRIEF_TEMPLATE.md` anywhere in the script).
- `test_harness_throw_is_captured_as_escalation` — asserts the `harness_throw` escalation
  kind and stage-body try/catch exist. **Must fail at `d8f0a8f`** (one try/catch total, args
  parse only).

If either passes on HEAD, the corresponding hypothesis is dead — stop, widen, report.
(Run result recorded under "The fix" below after execution.)

---

## The fix

The plan of record (approved 2026-08-12): `~/.claude/plans/atomic-plotting-hopper.md`, mirrored
in this branch's handoff. In one line each: the runbook gains the epic loop (step 9) +
scope-reconciliation in step 0a; the closer prompt branches on `closeoutKind`
(intra-epic → `EPIC_SPRINT_BRIEF_TEMPLATE.md`, terminal → full ceremony); stage bodies get
try/catch → `harness_throw` escalation; closer self-verifies with the gate's static steps;
paths reported repo-relative; the model policy and authorization records are amended to
owner's-choice-of-Fable-or-Opus and epic-remainder-pre-authorized; the owed
`epic-b-b1b-brief.md` is authored.

**Red-first run (executed 2026-08-12, before the mjs fix, tree at `d8f0a8f` + the new tests):**
all three pins failed as predicted — `test_closer_ceremony_branches_on_closeout_kind`
(`AssertionError: closeoutKind must exist in CODE, not just prose`),
`test_harness_throw_is_captured_as_escalation` (`assert "kind: 'harness_throw'" in …` failed),
and the two new `test_args_normalization` arms (`an unknown closeoutKind must be rejected` —
node exited 0, the unknown value spread silently into cfg). `3 failed in 39.30s`.

---

## Acceptance bar

- Both new structural pins red at `d8f0a8f`, green after the fix, **zero reruns**.
- `python -m scripts.gate` fully green on the branch before commit (all four steps; a
  `RERUN`-tainted pass does not count).
- The next pipeline run (B1b, run 4) exercises the intra-epic closer path and produces
  `epic-b-b2-brief.md` — deferred to run 4 by construction (this branch runs no sprint);
  stated plainly rather than claimed.
