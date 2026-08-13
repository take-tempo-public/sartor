# The N=1 baseline pipeline — contract + runbook (item 84)

> **Purpose:** the invocation contract for `.claude/workflows/n1-baseline.mjs`
> — the N=1 baseline of the C+drift chain-orchestration design
> ([`epic-a-chain-design-corrections.md`](epic-a-chain-design-corrections.md)
> §16.4–§16.5), authorized by the owner's §16.7 decision (2026-08-11, recorded
> in [`docs/dev/work/items/0084-build-n1-baseline-pipeline.md`](work/items/0084-build-n1-baseline-pipeline.md)).
> **Audience:** the invoking session (the "deterministic monitor" host) of a
> future, **separately owner-authorized** pipeline run; and reviewers of the
> pipeline's structure.
> **Status: BUILT; FIRST RUN 2026-08-12** (Epic B run 1, sprint B1a — run
> `wf_9bb80d14-c94` died at the refuter spawn, its `resumeFromRunId`
> continuation completed all five phases; item 84 holds the evidence trail and
> the run-3 retrospective in
> `docs/dev/handoffs/fix-b1-stale-template-companions.md` holds the cost
> accounting). Running this pipeline on a real sprint remains a **per-session
> owner opt-in** — nothing in this doc, the script, or its tests authorizes a
> run by itself. An epic's own authorization record (e.g.
> `epic-b-design-brief.md` §"Execution mode + authorization record") can
> pre-authorize the epic's remaining sprints; step 0a below says how to
> consume that record without re-asking for what it already grants.

---

## What this is, and is not

**Is:** implementer → Sonnet refuter → judge → closer for exactly ONE ordinary
sprint, as a Workflow script. At N=1 this *is* the normal one-branch-one-session
handoff process, plus the adversarial refuter (proven — it caught the item-20
defect) and a structured, correlated run report — provably at least as robust
as today's process, since the boundary reviewer is still the owner, exactly as
today (§16.5.1).

**Is not** (each its own later, owner-gated decision — §16.7 decision point 3):

- Not authorized to **run**. Even a "smoke run" spawns agents and is a run.
- Not the provenance-ledger event extension (§16.5.2.2). The script never
  touches `docs/dev/ledger/`; the only ledger write in the whole flow is the
  closer's ordinary `verify_doc_template.py --event generated` — the same
  SPEC §3 surface every manual close-out already uses.
- Not a widening of N past 1 (`N = 1` is pinned in the script and by test).
- Not a retirement or merge of `AGENT_HANDOFF_TEMPLATE.md`.
- Not the §14.7 delegation-seam gate.

## Stated limits (C-0) — read these before trusting anything below

1. ~~**The Workflow-harness API this script targets has zero committed instances
   in this repo, and the script has never been executed.**~~ — **PARTIALLY
   ATTESTED 2026-08-12 (run 3).** Script loading, `agent()` semantics,
   `phase()` grouping, `journal.jsonl`, and `resumeFromRunId` (a cache replay
   with 0 new tokens after an opts-only change) were all observed live on the
   B1a run. What has NOT changed: every structural test in
   [`tests/test_n1_pipeline.py`](../../tests/test_n1_pipeline.py) certifies
   self-consistency with the design docs — **not harness compatibility** — and
   **escalation routing remains UNTESTED after three runs** (`escalations: []`
   every time; no halt-point, hook-block, or flag-stop has ever traveled the
   primitive live). The `harness_throw` error boundary added 2026-08-12
   (retro #1) is likewise untested until something actually throws inside a
   run — stated plainly rather than claimed.
2. ~~**Agent-type resolution by bare name (`n1-refuter` / `n1-judge`) is likewise
   unverified until first run**~~ — **FALSIFIED 2026-08-12, run `wf_9bb80d14-c94`.**
   Bare names do **not** resolve. The harness rejected `'n1-refuter'` and listed
   `sartor:n1-refuter` / `sartor:n1-judge` among the available agents: dispatch
   requires the **plugin namespace**, the same one `CLAUDE.md` documents for
   commands and subagents (`/sartor:…`, `sartor:…`). The script now dispatches
   `sartor:n1-refuter` / `sartor:n1-judge` at all three call sites, and
   `tests/test_n1_pipeline.py` pins the namespaced form (its previous
   assertion pinned the bare form, and so pinned the defect). Cost: 22 minutes
   and 169k subagent tokens, spent *after* the implementer had finished a full
   sprint — the throw happened at the refuter spawn. Two mechanisms answer this
   under C-11; see step 0a below and `unregistered_agent_types` in
   `tests/test_n1_pipeline.py`.
3. **The read-only-Bash boundary on the refuter and judge is instruction, not
   construction.** Their tool grant removes `Edit`/`Write`/`Task` by
   construction; nothing mechanically stops a `Bash` write. Both role files
   state this the way `agents/compliance-witness.md` does.
4. **Resume caches a blocked agent's block-description as success.** If an
   agent is hook-blocked but returns a structured object describing the block,
   `resumeFromRunId` replays that object instantly. The resuming session must
   eyeball `journal.jsonl` before trusting a cached result.
5. The §11.9 accounting check (below) verifies **reported** writes; a file
   written and deliberately unreported defeats it. It catches drift, not
   dishonesty — the same limit C-12 states for citations.

## Roles

| Role | Dispatch | Model | Tree access | Spec |
|---|---|---|---|---|
| Implementer | default agent | `args.implementerModel` (default `opus`) | full — writes code/tests/dossiers, stages; **commits nothing** | §11.9.1 |
| Refuter | `agentType: 'sartor:n1-refuter'` | frontmatter: `claude-sonnet-5` (owner's call) | read-only grant | §11.9.2, [`agents/n1-refuter.md`](../../agents/n1-refuter.md) |
| Judge | `agentType: 'sartor:n1-judge'` | frontmatter: `claude-opus-5` | read-only grant | §11.9.3 / §16.4.1, [`agents/n1-judge.md`](../../agents/n1-judge.md) |
| Closer | default agent | `args.closerModel` (default `sonnet`) | full — applies confirmed fixes, files items, board, handoff, stages; **no commit, no gate** | §11.9.4 |
| Escalation reviewer(s) | default agent | `args.reviewerModel` (default `opus`) | read via instruction (spawned with a wider view) | §16.4.1 item 4 |
| Finalize closer | default agent | `args.closerModel` | commit only | §11.9.4 (commit step) |

Model policy (owner decision 2026-08-11 plus the 2026-08-12 amendment, both
recorded in `RELEASE_ARC.md` §"Session models"): **sprint-internal agents** run
on Opus and Sonnet — never Fable inside a sprint pipeline; the **invoking
session's** model is the **owner's choice of Fable or Opus, stated at
invocation** and recorded per run in item 84. Frontmatter is the single source
of truth for `agentType`-dispatched models; the script passes `model:`
explicitly on every default-type agent.

## The runbook — what the invoking session does

The gate belongs to the **invoking session**, never to any agent — a
subagent's gate dies with the agent (§11.9, learned twice on A2). The script
therefore runs in two stages bracketing the main-loop gate:

0. **Preconditions.** A live plan-approval marker for this project exists
   (`hooks/check-plan-approved.sh` blocks every subagent `Edit`/`Write`
   without one; the pipeline then stops correctly rather than proceeding —
   never create or touch the marker to unblock it). The feature branch exists
   and is checked out. The sprint brief and epic design brief exist as files.
0a. **Preflight decision batch — ONE batch, BEFORE the first Workflow call
   (added 2026-08-12; Epic B run 1's overnight window was lost to serial
   owner questions at 5–10 minute intervals, and the run never started).**
   The chain exists to exploit long uninterrupted windows; a question asked
   mid-window forfeits the window. So, at kickoff, the invoking session:
   - reads the sprint brief, the epic design brief, and this runbook **in
     full, before asking anything** — a question answerable from those files
     or the repo is not an owner question, and asking it anyway is the
     failure mode this step exists to close;
   - runs the pipeline's own structural gate cheaply
     (`python -m pytest tests/test_n1_pipeline.py tests/test_gitattributes_coverage.py -q`)
     so invocability failures surface at kickoff, not overnight;
   - **runs the live dispatch probe and STOPS unless it returns
     `verdict: "ok_to_run"`** —
     `Workflow({scriptPath: '.claude/workflows/n1-agent-probe.mjs', args: {agentTypes: ['sartor:n1-refuter', 'sartor:n1-judge']}})`.
     The structural gate above certifies self-consistency with the design docs;
     it cannot certify that the harness resolves an `agentType`, and three runs
     have now died at that boundary. Only a real spawn answers that question.
     Measured: 6.2s, ~67k subagent tokens (run `wf_d5ab3682-071`) — the
     system-prompt floor of two spawns, against the 169k tokens and 22 minutes
     run `wf_9bb80d14-c94` spent before throwing. Keep `agentTypes` equal to the
     literals `tests/test_n1_pipeline.py::test_every_agent_type_literal_resolves_to_a_registered_agent`
     pins;
   - **reconciles the scope BEFORE asking anything: the epic's authorization
     record vs. this run's sprint brief.** The two must name the same unit of
     work for this session; a conflict is surfaced verbatim in the batch,
     never resolved by guess (run 3's tenth failure — item 84: an epic-level
     authorization and a sprint-scoped handoff, never reconciled; the invoker
     ran one sprint, executed a session-terminating ceremony, and the epic
     silently stopped). The inverse discipline binds equally: a decision the
     epic's authorization record ALREADY grants — which sprints may run, the
     invoker's license to continue to the next sprint at each boundary, the
     invoking model the owner stated at launch — is **not re-asked**;
     re-asking a recorded authorization is itself a preflight defect (the
     "needed authorization" stall the owner has already rejected on screen,
     2026-08-12);
   - enumerates EVERY owner decision the whole run could genuinely still
     need — the per-session run-start opt-in (never inherited from a
     handoff), scope calls the brief names but the record does not settle,
     branch hygiene, anything its own reading surfaced — and asks them in
     **one batch, in one message**;
   - **consumes the item-87 interrogative-witness pause deliberately, with its
     own `Edit`/`Write`, before the first `Workflow` call.** That witness
     refuses the first edit after an armed prompt turn with exit 2 and
     self-clears. If the refusal instead lands on a subagent's first edit, the
     agent is told (correctly, per Binding rule 3) to return
     `kind: "hook_block"`, and `escalate()` short-circuits that straight to
     `escalated_to_owner` with no reviewer — so a benign, self-clearing witness
     stops the whole run. Recording the branch's base sha or a work-item note
     is a natural edit to spend it on. Residual risk is a mid-run task
     notification re-arming it (observed arming on most, but not all,
     notifications — counts in work item 84); that case is the owner's call,
     not a thing to route around;
   - states, in the same message, the expected uninterrupted window and the
     contract for it: after kickoff the owner hears from this session only
     via the pipeline's escalation primitive (that is the pipeline working)
     or the run's completion report. A new ad-hoc question after kickoff is
     a preflight defect — file it as one at close-out.
1. **Sprint stage:**
   `Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {stage: 'sprint', sprintBriefPath, epicBriefPath, epicSprintIndex, epicSprintCount, nextSprintBriefPath, ...}})`
   — the close-out ceremony is **derived** from the sprint's position, never
   chosen: `epicSprintIndex < epicSprintCount` (a successor sprint exists) →
   the intra-epic next-sprint brief, and `nextSprintBriefPath` is required;
   `epicSprintIndex == epicSprintCount` (the epic's last sprint, or a
   standalone 1-of-1 branch) → the terminal full ceremony. A caller-supplied
   `closeoutKind` is **rejected by name** (`fix/n1-scope-dedup` — run 3's
   epic ended one sprint in on a caller default; item 84, tenth failure).
   On `status: 'escalated_to_owner'`: surface the escalation's **verbatim**
   text to the owner and stop — that is the pipeline working, not failing.
   On `status: 'ready_for_gate'`, continue.
2. **Accounting check (§11.9):** compare the report's
   `accounting.claimedFilesWritten` against `git status --porcelain` —
   the union of agents' reported writes must cover it exactly. An unreported
   tracked file means the run drifted; stop and look.
3. **Gate #1 — in the main loop, literally this, no variants** (item 83's six
   findings F1–F13 are the graveyard of variants; that item is the future
   consolidation, not yet built):
   `nohup python -m scripts.gate > gate1.log 2>&1 &` from a **foreground**
   call; wait on the gate's **own terminal line** —
   `until grep -qE "^gate: (all steps passed|FAILED)" gate1.log; do sleep 20; done`
   (`scripts/gate.py` prints exactly one of those two) — **never** `| tee`,
   **never** `kill -0`, **never** the harness's `run_in_background`, and
   **never** process-name polling: `tasklist | grep python.exe` matches
   nothing on this machine (the interpreter is `python3.13.exe`), so the wait
   loop returns instantly and a mid-run log reads as finished (observed
   2026-08-12, twice).
4. **Step-6 assertion** (the corrected close ordering's actual mechanism —
   "Without it this is vigilance, not enforcement"): `git diff --quiet` passes
   **and** `git status --porcelain --untracked-files=all` shows no untracked
   files and no working-tree-column changes. The tree the gate examined is the
   tree that commits — if either fails, the window reopened; stop and look.
   (The assertion runs with the sprint's work already staged, so "empty" means
   *no drift since the pre-gate `git add -A`* — staged entries are expected.)
   **Known benign drift source, observed 2026-08-12 (run 3):** the session's
   own `docs/dev/ledger/<session>.jsonl` can gain a `compacted` receipt
   *during* the gate, because the `capture-before-compact` PreCompact hook
   appends on the harness's schedule, not yours. That trips this assertion
   without any content having changed. "Stop and look" still applies — look,
   confirm the delta is exactly one hook-written audit row, say so, then
   re-stage and let **gate #2** examine the committed tree, which is precisely
   the gap the second gate run closes. Do not pre-authorize the pattern: a
   ledger row is benign, an unexplained edit to a tracked source file is not.
5. **Finalize stage:**
   `Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {stage: 'finalize', commitMessage, sprintBriefPath, epicBriefPath}})`
   — commit only; the handoff is already in the tree from the Close phase.
6. **Gate #2 — post-commit, main loop, same literal invocation** (the
   `RELEASE_ARC.md` second-gate amendment: the committed tree is re-gated).
7. **PR ceremony — §11.5.1 halt point, owner-gated, outside the pipeline:**
   push/PR/merge only with the owner's confirmation, waited on with
   `python -m scripts.ci_wait <n>` (exit 3 = green-after-retries — stop and
   look, never merge on it reflexively).
8. **Durable capture (C-8):** the run report and the Workflow `journal.jsonl`
   are the audit trail; write the report (or its path) into the branch's
   durable record in the turn you receive it, not at close-out.
9. **The epic loop — an epic is SEVERAL runs, and managing the flow between
   them is the invoking session's job** (added 2026-08-12: run 3 ended the
   session after one sprint of a three-sprint epic, and the owner lost a day
   believing the epic was running — item 84, tenth failure). After gate #2 is
   green for a sprint that is NOT the epic's last:
   - **ff-merge the sprint branch into the epic branch**
     (`git checkout <epic-branch> && git merge --ff-only <sprint-branch>`),
     then prune the sprint branch. This is intra-epic housekeeping, not the
     owner-gated PR ceremony — that fires once, at the epic close (step 7
     stays owner-only, unchanged).
   - **verify the next-sprint brief exists** — the intra-epic closer wrote it
     (`closeoutKind: 'intra_epic'` + `nextSprintBriefPath`). If it is
     missing, that is a pipeline defect: stop and surface it; do not
     improvise a brief (the pipeline never invents one).
   - **report the sprint boundary to the owner NOW, in one short message:**
     sprint done, both gates green (rerun-sweep result included), epic
     progress (run n of m), what starts next. This report is per-sprint and
     immediate — never deferred to a session-end summary. Run 3's missing
     boundary report is exactly how a stopped epic read as a running one for
     a day.
   - **assess context budget as a first-class constraint (C-8), on external
     signals only** — a `compacted` receipt in the session's ledger shard, a
     harness context warning; never a self-assessed "feels fine". If the
     context is degraded: STOP here cleanly. The next-sprint brief is already
     on disk, so the resume state is exactly three things — the epic branch
     tip, the next sprint's brief path, this runbook. Say them to the owner
     and end the session; a fresh invoker resumes with zero loss. Continuing
     degraded is how run 3 spent its remaining budget on close-out ceremony
     instead of the epic.
   - **otherwise: cut the next sprint branch off the epic tip and return to
     step 0** with the next sprint's `sprintBriefPath` and its position args
     (`epicSprintIndex` advanced by one; on the epic's LAST sprint
     index == count derives the terminal full-handoff ceremony — no
     ceremony arg exists to get wrong). Step 0's preconditions are re-checked
     each iteration; in particular the plan-approval marker retires when a
     branch merges, so expect one marker re-approval per sprint boundary —
     that is the reconciler working, not a blocker (never hand-create the
     marker).

   **The full close-out ceremony — `AGENT_HANDOFF_TEMPLATE.md` +
   `verify_doc_template.py`, the wiki pass + `.last_ingest_sha` advance, the
   epic-level adversarial review, the PR — runs ONCE, at the epic close,
   never at an intra-epic boundary.** Per-sprint, the epic brief's own
   "per-sprint floor" list is the whole obligation.

## Escalation — the unified primitive (§16.4.1 item 4)

Any agent returns `flags[]`; every flag carries the agent's **own words in
`verbatim`, never paraphrased on the way through**. Routing by `kind`:

- **`halt_point` (§11.5) and `hook_block` (Binding rule 3):** short-circuit
  **directly** to `escalated_to_owner`. **No reviewer is spawned — no LLM may
  clear a halt point or a hook block.** §11.5 is "unconditional, no judgment
  involved," and the dated 2026-08-09 narrowing of Binding rule 3 in §11.6 is
  scoped "Epic A chain only" and does **not** carry into this pipeline.
- **`flag_stop` (§11.6) and `coherence_drift` (§16.4.1.3):** one independent
  Opus reviewer with a wider view (epic brief, sprint brief, findings so far,
  the diff, the verbatim flag) rules `clear` / `targeted_fix` / `escalate`;
  on `escalate`, **one more independent reviewer** (the owner-decided
  refinement) before the run stops for the owner.

A judge `escalate` verdict (§11.6.3 — a confirmed finding whose fix would
change sprint *scope*) and a re-confirmed finding after its one bounded fix
round both stop the run the same way, rationale carried verbatim.

## Coherence-drift triggers (§16.4.1.3)

Evaluated **only at the inter-sprint boundary — which at N=1 does not exist**,
so the layer is inert by construction (pinned by test, not asserted from
hope). The machinery exists so widening N later — if the owner ever decides
it — is a config change, not a rebuild: pre-scheduled `args.driftCheckpoints`
(declared at epic planning, the same act that declares close-out intervals —
`RELEASE_ARC.md` cadence rule), plus two reactive counters
(`args.driftBackstop` sprints since the last review, default 3;
`args.deferredDriftThreshold` cumulative deferred findings, default 5). All
three route into the escalation primitive as `kind: 'coherence_drift'`.

## Args reference

| Arg | Required | Default | Meaning |
|---|---|---|---|
| `stage` | no | `'sprint'` | `'sprint'` or `'finalize'` |
| `sprintBriefPath` | **yes** | — | the sprint's brief (the pipeline never invents one) |
| `epicBriefPath` | **yes** | — | the epic design brief (the escalation reviewers' wider view) |
| `commitMessage` | finalize only | — | composed by the invoking session from the run report |
| `implementerModel` | no | `'opus'` | per-sprint, from the RELEASE_ARC session-models table |
| `closerModel` | no | `'sonnet'` | |
| `reviewerModel` | no | `'opus'` | |
| `driftCheckpoints` | no | `[]` | pre-scheduled drift-review sprint indices |
| `driftBackstop` | no | `3` | reactive counter (inert at N=1) |
| `deferredDriftThreshold` | no | `5` | reactive counter (inert at N=1) |
| `epicSprintIndex` | sprint stage | — | this sprint's 1-based position in its epic (a standalone branch is 1 of 1). The ceremony DERIVES from it — index < count → the closer writes the next sprint's brief from `EPIC_SPRINT_BRIEF_TEMPLATE.md` (the declared light cadence — item 89); index == count → the full `AGENT_HANDOFF_TEMPLATE.md` ceremony. `closeoutKind` is **no longer a caller arg** and is rejected by name (`fix/n1-scope-dedup`) |
| `epicSprintCount` | sprint stage | — | total sprints in the epic (from the epic brief's Sprint → run table) |
| `nextSprintBriefPath` | when index < count | — | where the closer writes the next sprint's brief (e.g. `docs/dev/handoffs/epic-b-b2-brief.md`) — named by the invoking session, never invented by the pipeline |
