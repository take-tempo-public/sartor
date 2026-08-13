# The N=1 baseline pipeline — contract + runbook (item 84)

> **Purpose:** the invocation contract for `.claude/workflows/n1-baseline.mjs`
> — the N=1 baseline of the C+drift chain-orchestration design
> ([`epic-a-chain-design-corrections.md`](epic-a-chain-design-corrections.md)
> §16.4–§16.5), authorized by the owner's §16.7 decision (2026-08-11, recorded
> in [`docs/dev/work/items/0084-build-n1-baseline-pipeline.md`](work/items/0084-build-n1-baseline-pipeline.md)).
> **Audience:** the invoking session (the "deterministic monitor" host) of a
> future, **separately owner-authorized** pipeline run; and reviewers of the
> pipeline's structure.
> **Status: BUILT, NEVER RUN.** Running this pipeline on a real sprint is its
> own owner opt-in — nothing in this doc, the script, or its tests authorizes
> a run.

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

1. **The Workflow-harness API this script targets has zero committed instances
   in this repo, and the script has never been executed.** Every structural
   test in [`tests/test_n1_pipeline.py`](../../tests/test_n1_pipeline.py)
   certifies self-consistency with the design docs — **not harness
   compatibility**. First-run behavior (script loading, `agent()` semantics,
   `phase()` grouping, `journal.jsonl`, `resumeFromRunId`) is unverified until
   the owner authorizes the first run.
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

Model policy (owner decision, 2026-08-11, recorded in `RELEASE_ARC.md`
§"Session models"): epics run on Opus and Sonnet — never Fable inside a sprint
pipeline. Frontmatter is the single source of truth for `agentType`-dispatched
models; the script passes `model:` explicitly on every default-type agent.

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
   - enumerates EVERY owner decision the whole run could need — the
     per-session run-start opt-in (never inherited from a handoff), scope
     calls the brief names, branch hygiene, anything its own reading
     surfaced — and asks them in **one batch, in one message**;
   - states, in the same message, the expected uninterrupted window and the
     contract for it: after kickoff the owner hears from this session only
     via the pipeline's escalation primitive (that is the pipeline working)
     or the run's completion report. A new ad-hoc question after kickoff is
     a preflight defect — file it as one at close-out.
1. **Sprint stage:**
   `Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {stage: 'sprint', sprintBriefPath, epicBriefPath, ...}})`.
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
   **and** `git status --porcelain --untracked-files=all` is empty. The tree
   the gate examined is the tree that commits — if either fails, the window
   reopened; stop and look.
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
