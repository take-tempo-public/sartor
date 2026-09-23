# Epic C design brief — `epic/c-diagnostics` (board 38): diagnostics console

> **Purpose:** the standing context for every agent in Epic C: the epic's authorization
> record, sprint → run mapping, branch topology, cadence declarations, and experiment
> record. This is the file `epicBriefPath` points at on every pipeline invocation
> (`docs/dev/n1-baseline-pipeline.md` §"Args reference"), which is the escalation
> reviewers' wider view.
> **Audience:** the invoking (monitor) session of the Epic C run, the pipeline's agents
> (implementer, refuter, judge, closer, escalation reviewers), and the owner.
> **Authoritative for:** Epic C's execution mode and authorization record (including the
> owner-ratified scope sentence, whose single home is here), the sprint → run mapping,
> branch topology, close-out intervals, and the coherence-drift declaration. Sprint *scope*
> stays authoritative in `docs/dev/RELEASE_ARC.md` §"Epic C" (`RELEASE_ARC.md:1945-1974`).
> This brief cites it and does not fork it.
> **Referenced once, never restated.** Sprint briefs point here.

---

## Execution mode + authorization record

**Epic C runs through the N=1 baseline pipeline as one long, continuous run.** Epic B was
the first pipeline test (`epic-b-design-brief.md`). Epic C repeats it, which that brief
names as "a later owner decision", and that decision is recorded here.

- **Owner direction, 2026-09-22 (recorded in the `fix-ci-wait-required-from-protection`
  handoff and restated in item 97's update):** Epics C/D/E finish as **long runs** under
  the original epic design, not as isidium factory cards.
- **Owner decision, 2026-09-22 (item 93, AskUserQuestion selection, session `0ea1b8bf`):**
  the invoker session shape is **(b) a continuous window**, one invoking session for the
  whole epic. Its tripwire is runbook step 9's external-signal stop, and the context
  reducers from `fix/n1-invoker-context-budget` apply. Per-sprint fresh sessions were
  considered and not chosen.
- **Owner decision, 2026-09-22 (item 95, "adopt as proposed"):** the mid-run
  interrogative-witness recovery is the amended pre-authorization in
  `docs/dev/n1-baseline-pipeline.md` §"Escalation — the unified primitive". Consume the
  pause with a deliberate invoker edit, then re-invoke the sprint stage fresh. **Never
  `resumeFromRunId` for a `hook_block`.**
- **Invoking-session model: the owner's choice, stated at launch** (RELEASE_ARC §"Session
  models": epics run on Opus and Sonnet, without Fable, and the invoker's model is the
  owner's call). Sprint-internal agents follow the table below and the role frontmatter.
- **This record grants, and an invoker never re-asks:** which sprints may run (all four,
  in order), the license to continue to the next sprint at each boundary per runbook
  step 9, and the invoking model stated at launch. **The invoker still confirms per
  session:** the run opt-in ("may I start this run now"), in runbook step 0a's single
  preflight batch, and any genuine decision these records do not settle.
- **Prerequisites landed before this brief (2026-09-22):**
  - item 94, PR #143: the witness pause skips subagent payloads, so run 6's death mode is
    gone;
  - item 110, PR #144: plan approvals are no longer retired mid-branch, and live-checked;
  - item 96, on this brief's own branch: `implementerModel` is required, never defaulted.

**The owner-ratified scope sentence (2026-09-22, typed selection "Ratify draft as written"
at the `docs/epic-c-kickoff` planning checkpoint). This is the SINGLE source for session
scope: cite it, never restate it:**

> The pipeline run is the ENTIRE Epic C — C1a, C1b, C2, C3, then the epic close-out to
> PR-ready — run continuously by one invoking session that manages the flow at every
> boundary. Stopping before PR-ready is a failure unless an escalation is awaiting the
> owner, runbook step 9's external signal has fired, or the owner has said stop; partial
> completion is not success.

**The invoking session's job between runs is to manage the flow:**
1. consume the closer-written next-sprint brief;
2. run the sprint with the args from the table below;
3. ff-merge into `epic/c-diagnostics` on gate #2 green;
4. report the boundary immediately (runbook step 9's report: sprint closed, gate result,
   the refuter disposition, and the next sprint);
5. continue, or stop cleanly with the exact resume state named.

The owner is not watching live overnight. The boundary reports in the session are the
record they read in the morning.

## Goal + scope

Diagnostics console fixes, per-run observability, and lay-reader copy (board item 38).
The sprint scope of record is `docs/dev/RELEASE_ARC.md` §"Epic C" (C1 at `:1949`, C2 at
`:1956`, C3 at `:1962`, verified at HEAD `a078ca1`). Nothing outside that section is in
scope. Anything discovered and not chased gets filed as a work item, not folded in.

**Pre-epic UX audit (RELEASE_ARC: Epic C "opens with an end-user-UX-expert audit of the
console"): done.** It is at `docs/dev/reviews/epic-c-console-ux-audit.md`, verified at
`a078ca1`.
- **Findings UX-1..UX-21 and UX-42 are classified in scope.** They are the sprints' concrete
  checklist, cited per sprint below. The kickoff session spot-checked 25 of their cites at
  HEAD, and all matched.
- **UX-22..UX-41 are out of scope** and are **not** part of this epic:
  - UX-22 (the Since filter raises TypeError, independently reproduced) is item 112;
  - the other 19 are item 113 (owner triage).
- If the invoker thinks one belongs in a sprint (the audit suggests UX-24 for C1b), that
  is an owner question for the preflight batch, never a silent fold-in.

## Sprint → pipeline-run mapping

One run = one sprint = one branch (N=1 is structural). Epic C is **four runs**. Models
are from RELEASE_ARC §"Session models" (C1/C2 Sonnet, C3 Opus). **Every invocation passes
`implementerModel` explicitly**, because the script rejects a sprint stage without it
(item 96).

| Run | Sprint | Branch | `implementerModel` | Position | Scope (cite RELEASE_ARC §Epic C) + audit checklist |
|---|---|---|---|---|---|
| 1 | C1a | `fix/dashboard-run-lock-gaps` | `sonnet` | 1 of 4 | Lock-gate the real Collate button (`annCollate`, button at `dashboard/templates/dashboard.html:615`, absent from `LOCK_BTN_IDS` at `:1388`). **UX-1 (blocker):** Collate stays clickable mid-run and builds a new, *enabled* `annCollateRunBtn`, whose `acquire()` returns early (`:1396`), so a second paid eval can start. There is no server-side lock. Evidence-first `fix/*` branch: the first artifact is the diagnosis dossier's `## Observed`, which reproduces the double-run in a UX test, never the fix. |
| 2 | C1b | `feat/dashboard-polish` | `sonnet` | 2 of 4 | Sticky `.dash-tabs` (UX-2; stacks with the sticky run banner). Correct the false "Read-only observability" header at `:230` (UX-3). Opaque + pulsing run-in-progress banner (UX-4, `:146-152`, `:213-216`). Port `.btn-pending` / `cb-status-pulse-strong` (`static/style.css:3226`, `:3154`) to every wait state (UX-5, including disabling in-flight Save/Collate). The terminal Cancel state (UX-6). Honor `prefers-reduced-motion`. |
| 3 | C2 | `feat/run-detail-modal` | `sonnet` | 3 of 4 | `GET /_dashboard/api/run/<run_id>` on the same blueprint (inherits `_localhost_guard`, `dashboard/routes.py:982-990`): one bounded JSONL pass reusing `_run_trace` (`:822`), `_reliability` (`:776`), `_cost_by_call_kind` (`:745`). Clickable run ids in all four places → composite modal (UX-7). Clickable error-rate rows → recent error records with messages (UX-8). |
| 4 | C3 | `feat/dashboard-copy-discovery` | `opus` | 4 of 4 (terminal) | A lay one-line summary + `_DASH_HELP` bubble for every module on every tab (UX-9, registry `:1003-1152`). Quality-tab lay rewrite (UX-11). p50/p95/median/mean explainers (UX-10). Filter-scoping explainer (UX-13). The full Annotate instruction set per RELEASE_ARC (UX-14..UX-20). Fix the wrong Score-grounding help (UX-18). Groundedness + Tuning module copy (UX-21, UX-42). Doc-page links wait for D4. |

Next-brief paths the invoker passes as `nextSprintBriefPath`:
`docs/dev/handoffs/epic-c-c1b-brief.md` (run 1), `epic-c-c2-brief.md` (run 2),
`epic-c-c3-brief.md` (run 3). Run 4 is terminal and passes none. Run 1's brief is
`docs/dev/handoffs/epic-c-c1a-brief.md`, written at kickoff. The later three are written
by each run's closer.

Refuter and judge models are pinned in `agents/n1-refuter.md` / `agents/n1-judge.md`
frontmatter.

**Cite-drift note (C-0):** every RELEASE_ARC §Epic C anchor was re-derived at `a078ca1` by
the audit and spot-checked by the kickoff session, with **no drift**. One clarification:
RELEASE_ARC's `dashboard.html:1388` names the `LOCK_BTN_IDS` array, and the button itself
is at `:615`. Line numbers move after run 1's first edit. Every run re-derives before
relying on one.

## Branch topology

`epic/c-diagnostics` off `main` (created at kickoff and pushed; it carries no edits). **Each
sprint runs on its own real branch** (named in the table), stacked on the epic branch tip,
and is fast-forward merged into `epic/c-diagnostics` after that run's gate #2. There is one
epic PR to `main` at the epic close, owner-gated (halt point 1). **Sprint branches are NOT
pruned at the boundaries.** Keep all four until the epic PR has merged to `main`. Pruning a
stamped sprint branch retires the plan approval, so the next sprint's implementer hits
`PLAN RETIRED` and the run stops (runbook step 9, corrected 2026-09-22; pinned by
`test_epic_sprint_boundary_*`). This is Epic B's topology,
kept for the same reason: C1a is an evidence-first `fix/*` branch, and
`require-evidence-before-fix` keys on the `fix/*` name. On the epic branch it would never
fire.

## Close-out intervals — declaration (required by RELEASE_ARC epic-planning rule)

**Light per sprint; one full close-out at the epic end.** This is re-argued for C, not
inherited (`RELEASE_ARC.md:1788`, "each epic's own brief must state its own answer"):

- The pipeline supplies per-sprint checks a light cadence would otherwise lack: an
  adversarial refuter on every staged diff, a judge, and the §11.9 accounting check.
- In a continuous window, the full ceremony per sprint would spend the invoker's context
  on exactly the reading the item-93 decision was trying to bound. Run 5's measurement
  was 11–14 compactions for multi-sprint continuous windows.
- Owner cost tolerance (RELEASE_ARC): 10–20% comfortable. Four full ceremonies land on
  the wrong side of that.

**Per-sprint floor** (non-negotiable):
- C-7/C-10 dossiers where triggered (hook-gated);
- a substantive commit message;
- the **next sprint's brief** (closer-written, from `EPIC_SPRINT_BRIEF_TEMPLATE.md`, whose
  First move now carries a copy-paste invocation with `implementerModel`);
- work items for anything discovered and not chased;
- the invoker's two gate runs, with the log swept for `RERUN`;
- the refuter pass;
- BOARD regeneration (the gate binds it).

**Deferred to the epic close** (scheduled, not skipped): the wiki pass, full grounding
audits, the full `AGENT_HANDOFF_TEMPLATE.md` ceremony with `verify_doc_template.py`, the
epic-level adversarial review, and the experiment outcomes (below).

**Wiki backstop, re-derived:** drift is **39 of 75** at authoring
(`python -m scripts.wiki_freshness`, 2026-09-22), far higher than Epic B's 11. Every C
sprint touches wiki-relevant files (`dashboard/templates/dashboard.html`,
`dashboard/routes.py`, `static/style.css` all classify relevant), and
`docs/wiki/pages/diagnostics-console.md` covers them. The page's content changes
materially in every sprint, so updating it per sprint would churn it four times. The
wiki pass therefore runs **once at the epic close**. **Backstop:** the invoker runs
`python -m scripts.wiki_freshness` at each sprint gate. If drift reaches **60** (a margin
of 15 below the 75-file merge block, roughly three sprints' worth), the wiki pass runs
**that sprint**.

## Coherence-drift checkpoints — declaration: none scheduled, and why

The rule requires checkpoints or a written justification (`RELEASE_ARC.md:1771`). **None:**

- At N=1 the drift layer is inert by construction. The reactive counters stay at defaults
  and cannot fire.
- **The owner is not the live boundary reviewer tonight**, which is different from Epic B.
  The compensating control is the per-boundary report (Execution mode, step 4), which the
  owner reads afterwards, plus the epic-close adversarial review before the owner-gated
  PR.
- The sprints are loosely coupled: C1a and C1b touch the lock and CSS, C2 adds an endpoint
  and modal, C3 is copy. The audit gives each a concrete, pre-verified checklist, which
  bounds trajectory wandering at authoring time.

If Epic C's outcomes show trajectory wandering that the epic-close review had to catch,
that is evidence **for** scheduling checkpoints in Epic D's brief. Record it; don't retrofit
it mid-epic.

## Escalation + envelope

Authoritative in `docs/dev/n1-baseline-pipeline.md` §"Escalation — the unified
primitive", including the item-95 amendment. `halt_point`/`hook_block` short-circuit to
the owner with no reviewer spawned. `flag_stop`/`coherence_drift` get one independent
Opus reviewer, then one more before a full stop. Push, PR, and merge to `main` are
owner-only (halt point 1). The run ends at PR-ready.

## Acceptance criteria (epic-level)

From RELEASE_ARC §Epic C, restated as testable outcomes; the audit's per-finding acceptance
checks are the detailed form:

- **C1a:** during a stubbed run, `#annCollate` is disabled, and an `annCollateRunBtn`
  created mid-run renders disabled. No second eval can start while one is live. A UX test
  pins both.
- **C1b:** the tab bar stays visible and clickable 3 screens down and doesn't overlap the
  banner. No page copy claims "Read-only". The banner is opaque (computed alpha 1) and
  pulses unless `prefers-reduced-motion`. Every async control shows an animated, disabled
  pending state for its whole request. Cancel reaches a terminal state.
- **C2:** every run id opens the modal from `GET /_dashboard/api/run/<run_id>`, one bounded
  JSONL pass. A non-localhost request gets 403. Error-rate rows list recent error records
  with messages.
- **C3:** every `.tile` / module has an on-screen lay line plus a `data-help` id that
  resolves in `_DASH_HELP` (a test iterates `.tile`). No raw file or field name appears
  unglossed in Quality tiles. The Annotate instruction set covers every RELEASE_ARC C3
  item. The Score-grounding help matches server behavior.
- The gate is green (both runs per sprint, zero reruns or dispositioned), every refuter
  verdict is dispositioned, and there is one epic PR at the end.

## What the experiment measures (recorded at epic close, including failures)

1. **The continuous window (item 93, choice b):** compactions per sprint, whether step 9
   fired, and at which boundary. This is the direct test of the owner's choice.
2. **Prerequisite fixes holding:** count of interrogative-witness `hook_block`s (item 94;
   expected 0) and of `NO EDIT APPROVAL` / `PLAN RETIRED` inside a run (item 110; expected
   0). Also: did the item-95 recovery path ever fire?
3. **Model-arg adherence (item 96):** did every invocation pass the table's
   `implementerModel`, and did closer-written briefs carry it?
4. **Inter-sprint brief sufficiency** at n=4: could each fresh cast execute from the
   closer-authored brief alone?
5. **Run-report/accounting fidelity:** did `claimedFilesWritten` cover
   `git status --porcelain` exactly?
6. **Owner interruption count** for the epic, and at which points.
