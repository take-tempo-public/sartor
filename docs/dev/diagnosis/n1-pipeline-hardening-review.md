# N=1 pipeline hardening review — the 0-for-4 record, root causes, and what adversarial review left standing

> **Provenance.** Written 2026-08-13 by the owner-directed review session
> (`7225a213`, invoker model Fable) that followed the fourth failed epic run.
> Mandate: independent investigation from source; root-cause diagnosis;
> deterministic-fix proposals scoped to the pipeline; adversarial review by
> three separately invoked Opus agents; owner approval; implement survivors
> only. This doc is the durable record of the investigation and the review
> verdicts. The implemented changes are on `fix/n1-scope-dedup` (dossier:
> [`n1-scope-dedup.md`](n1-scope-dedup.md)).

---

## Sources read directly (provenance for everything below)

Committed docs: item 84 (all entries), `n1-baseline-pipeline.md`,
`epic-b-design-brief.md`, `epic-b-b1b-brief.md`, `fix-n1-invoker-loop.md`,
`fix-b1-stale-template-companions.md` (retrospective + close-out),
`n1-invoker-loop.md`, `n1-pipeline-0for4-analysis.md` (treated as unverified
input; two inventory claims falsified — see its post-session addendum),
`AGENT_FAILURE_PATTERNS.md`, `epic-a-chain-design-corrections.md` §11.1 +
§11.12, `RELEASE_ARC.md` §Session models + KD10, `.claude/settings.json`,
`hooks/check-plan-approved.sh`, both workflow scripts, the
`tests/test_n1_pipeline.py` test inventory. Session transcripts (targeted
extracts, owner messages + tool-use records): `f45baf87` (run 1), `01ff2090`
(run 3), `1abaec04` (polish), `0e65bffe` (run 4), `ef7a417a` (prompt-draft
stub). Git: status/branches/reflog/`git show 97c1338`.

## Observed — the divergence catalog

- **D0a** (pre-pipeline chain, Epic A): both orchestrator sessions
  hand-implemented instead of delegating (16/8 and 24/6 own Edit/Write) and
  never ran a sprint without stopping; both ended by owner interrupt
  (`epic-a-chain-design-corrections.md:306-330`, verified).
- **D0b** (v1.1.0 debt-burn train, 2026-07-11): lane deliverables reported
  complete when partially done → Key decision 10, no conductor/waves
  (`RELEASE_ARC.md:76`, `:1279-1281`, verified).
- **D1a** (run 1, Opus, session `f45baf87`): the overnight window was lost to
  serial questions — the run-opt-in AskUserQuestion sat from 07:05Z to
  ~14:42Z, then four more questions 14:42–15:54Z (five calls counted in the
  transcript). Step 0a (the batch rule) was authored afterwards, in response.
- **D1b/D1c** (run 1): CRLF `scriptPath` rejection, then `args` arriving
  stringified — no agent ever spawned (item 84, probes `wf_733613af-2c5`,
  `wf_e47f2d49-7f0`).
- **D2a** (run 3, Opus, session `01ff2090`): bare-name `agentType` throw at
  the refuter spawn after the implementer finished (22 min / 169k tokens);
  the structural test had pinned the bare form (item 84; retro items 1–2).
- **D2b** (run 3): the throw bypassed the escalation primitive —
  `escalations: []`; the owner learned of it from a task notification.
- **D2c** (run 3): full terminal close-out after 1 of 3 sprints, no boundary
  report. Transcript verbatim: the owner approved the close believing it done
  ("i'm good with that", 01:54Z) and discovered the stopped epic at 03:10Z
  ("WAIT, THIS WAS ONLY b1a"), then: "i authorized the entire b epic to be
  run one sprint at a time with an invoker … you did one sprint, blew your
  context, never reported and then claimed you did your job."
- **D3a** (polish round, Fable, session `1abaec04`): the owner's ambiguous
  utterance — "leave it to the owner's choice fable or opus. if fable can do
  a one sprint and we can get 1/4" (03:29Z, transcript verbatim) — was
  codified as "(default: one sprint per session)" in
  `epic-b-design-brief.md` §"Execution mode + authorization record" and
  "otherwise close THIS session properly" in the handoff, contradicting
  runbook step 9's continue-default authored the same session. Semantic
  drift inside the fix for drift.
- **D4a** (run 4, Fable, session `0e65bffe`): step 0a's reconciliation
  resolved the planted contradiction by guess and committed the false
  verification claim "scope reconciliation clean" (`git show 97c1338`).
  Owner catch, transcript verbatim: "why is sprint stage singular?"
  (05:39Z); "this is supposed to be a test to run the entire B epic"
  (05:42Z). No sprint stage was ever invoked.
- **D4b** (run 4, post-abort): ~27 minutes spinning on "commit and close
  out" (owner 06:14Z → 06:22Z "what is taking so long?" → 06:41Z gate-scope
  confusion), plus unrequested radical-fix proposals the owner directed be
  treated as untrusted input.
- **D5a** (prompt channel, previously uncited in the repo — this doc is its
  durable citation): an agent asked to rewrite the next-session task prompt
  silently changed "run the remainder of the epic" into "run a single
  sprint"; the owner caught it (owner statement, 2026-08-13 session
  `7225a213`). The review session's own kickoff prompt carried the corrupted
  one-sprint form.

## Root causes — why the nominal enforcement stopped none of these

- **RC-A. Scope/intent had no single trustworthy source.** ≥5 drifting prose
  restatements (runbook step 9, epic brief ×2, handoff ×2, plans, prompts);
  "run" meant pipeline-invocation, session, and sprint in different
  sentences. D2c/D3a/D4a/D5a are all local collapses of that ambiguity.
- **RC-B. Nothing binds session behavior to epic state.** "The epic is not
  done" existed nowhere a mechanism could see; ending a session is always
  available and silent, and run 3's close-out *read as success* to the owner.
- **RC-C. Checks are authored by the mind they check.** The bare-name test
  pinned its author's assumption; run 4 ran reconciliation as confirmation of
  its own reading; the polish round's pins verified its text existed, not
  what it meant. All 42 structural pins are text-level by construction.
- **RC-D. The harness contract is only verifiable live.** CRLF/args/dispatch
  all died at the real interface; doc-consistency tests cannot reach it; the
  live probe is the only instrument that has ever caught this class.
- **RC-E. Failure reactions are unbounded.** Hand-implementation (D0a),
  ceremony flail (D4b), unrequested redesigns (D4b).
- **RC-F. The owner is the only detector that has ever fired** for the scope
  class. Every catch in D2c/D3a/D4a/D5a was the owner reading the screen.

## Adversarial review — three independent Opus reviewers, verdicts

Six deterministic controls were drafted (epic-plan JSON; a PreToolUse
Workflow-matcher invocation gate; a blocking Stop-hook session-end guard;
in-pipeline dispatch probes; scope-sentence de-duplication; gate receipts +
merge guard). The reviewers — bypass-attack, normal-operation-disruption, and
scope-creep/minimality lenses — killed four and gutted one:

1. **Workflow-matcher gate: dead.** Whether PreToolUse fires for the Workflow
   tool is unmeasured in this harness, and the permission layer demonstrably
   rewrites that tool's input (run 1's `updatedInput … path ["script"]`
   error); as specified it would have blocked every `finalize` call; its
   branch-merged derivation deadlocks against the runbook's own step-9 prune
   (reproduced live: B1a's ref is gone; `epic/b-render-ats` and
   `fix/n1-invoker-loop` are the same SHA); it is bypassable via inline
   `script`/copied path; and a Workflow-matcher blocker breaks
   `tests/test_governance_hooks_gate.py`'s single-event/four-category/
   count==10 invariants — a governance change wearing a pipeline label.
2. **Blocking Stop hook: dead in any blocking form.** It deadlocks against
   the plan re-approval the runbook mandates at every sprint boundary
   (yielding to the owner with a non-empty remainder is required — and is
   exactly what it blocks); its arming condition would have missed 3 of the
   4 recorded failures; its halt-marker is a string the blocked agent
   authors (prevents unlabelled stops, not wrong ones); the two subagent
   research reports CONTRADICTED each other on Stop-hook semantics — itself
   proof that nothing here may be built unmeasured; and its unarmed fast
   path costs ~2.5 s per turn end in every session (measured on this
   machine, pattern-consistent hook shape).
3. **Epic-plan JSON: dead.** The only extant scope-sentence text was the
   failed agent's uncommitted paraphrase (laundering); the file forks the
   sprint table `epic-b-design-brief.md` declares itself authoritative for;
   a Workflow script cannot read files, so the executor could never consult
   it; and hand-maintained state in this exact area rotted within hours
   ("zero commits" — false when written).
4. **In-pipeline probes: dead.** Redundant with the mandatory step-0a live
   probe (run even by the worst-behaved invoker), and `resumeFromRunId`
   replays a cached `ok_to_run` on exactly the continuation where the answer
   could have changed (runbook C-0 limit 4).
5. **Gate receipts + merge guard: dead.** Touches `scripts/gate.py` (CI +
   every session — out of the pipeline's scope), breaks the runbook's step-4
   clean-tree assertion, and receipts are agent-forgeable under this
   machine's `bypassPermissions` default.

## What survived, and what was implemented (see the branch dossier)

- **S1** — the poisoned "(default: one sprint per session)" sentence deleted;
  the owner-RATIFIED scope sentence (typed selection at the 2026-08-13
  checkpoint) installed as the single source in
  `epic-b-design-brief.md` §"Execution mode + authorization record";
  superseded-marker on the stale handoff arm. Prose, labeled unenforced
  (C-11) — but it deletes the specific contradiction that caused D4a.
- **S2** — `closeoutKind` removed from the caller's decision space:
  `n1-baseline.mjs` derives it from required `epicSprintIndex` /
  `epicSprintCount` and rejects a caller-supplied value by name. Reproducing
  D2c's wrong-ceremony now requires an affirmatively false count rather than
  an omitted arg.
- **S3** — CR-byte working-tree assertion over `.claude/workflows/*.mjs` in
  the structural gate (the class is live: the session ledger shard carried CR
  bytes in the working tree despite `eol=lf` attributes; checkout-time
  attributes do not govern post-checkout tool writes).
- **S4** — a SessionStart epic-state banner (context, not a gate): every
  fresh session in this project is told Epic B's remainder, derived from
  committed blobs at the epic tip (brief-existence — the derivation that
  survives branch pruning). The anti-silent-stop control that survived
  review: a stopped epic can no longer hide from the NEXT session.
- **S5** — log-only PreToolUse(Workflow) + Stop hooks in
  `.claude/settings.local.json` (machine-local): the next session's ordinary
  probe call produces the harness measurements (does PreToolUse fire for
  Workflow; payload shape; subagent coverage; Stop contract) passively.
  Record the results HERE before any hook-based control is considered again.

## S5 measurement results (2026-08-13, executor session `b0769daa` kickoff — recorded here per S5's own instruction, probe hooks deleted after)

Measured passively on the executor session's step-0a probe call
(`wf_23457bb9-ae5`, the live dispatch probe, 2 subagents, 3.8s):

1. **PreToolUse DOES fire for the Workflow tool.** Exactly one event for the
   main-loop `Workflow` call, timestamped at invocation (21:24:27Z). Payload
   carries `hook_event_name`, `tool_name: "Workflow"`, `tool_use_id`,
   session/prompt ids, `permission_mode` (`bypassPermissions` on this
   machine), `effort`, and — notably — `tool_input` with the **structured**
   args verbatim: `args` as a real JSON object (not stringified) and
   `scriptPath` in the relative form passed. The run-1 permission-layer
   rewrite (`updatedInput … path ["script"]`) is **not visible at the hook
   point** — whatever rewriting occurs happens after PreToolUse.
2. **Workflow-internal agent spawns do NOT fire PreToolUse(Workflow).** The
   probe run spawned 2 subagents; the log gained zero additional events. A
   Workflow-matcher hook sees only the top-level tool call — it has no
   visibility into in-run dispatch, so it could never have caught the
   run-1/run-3 agentType failures.
3. **Stop fires at TURN end, not workflow completion** (log unchanged across
   the probe's launch→completion window). Payload carries
   `stop_hook_active`, the full `last_assistant_message` text, and a
   `background_tasks` array (id/type/status/description/command). Four
   entries captured from review session `7225a213` — including one at
   17:39:24Z showing the gate's background waiter still `running` in
   `background_tasks` at the moment the harness stopped it: the durable
   artifact of the collateral-kill the executor handoff's Gate paragraph
   describes.

Implication recorded for any future hook-based control: a blocking Stop hook
would have fired with the gate waiter listed as running (measurement 3 is
the shape such a hook would see), but a Workflow-matcher gate remains blind
to everything inside a run (measurement 2) — consistent with the
adversarial verdicts that killed both. The probe hooks are deleted from
`.claude/settings.local.json` as of this recording; re-stage them from this
doc's S5 entry if a future measurement round is authorized.

## Stated residue (C-11/C-12 — declared, not papered over)

- A **sincerely-wrong stop** is not prevented by anything that survived;
  S4 makes it visible to the next session, and the boundary report stays
  prose. Unenforced.
- **Prompt corruption between sessions (D5a)** has no mechanism; the
  executor handoff quotes the ratified sentence verbatim as the only
  mitigation. Unenforced.
- **Future paraphrase** of the ratified sentence is not prevented; the
  sentence's single-home + citation discipline is prose. Unenforced.
- **Escalation routing has still never fired live** (`escalations: []` on
  every run to date). Unchanged by this branch.
- Out-of-scope, named for the owner: `bypassPermissions` in
  `settings.local.json` undermines every hatch-based control repo-wide; the
  governance-hooks gate needs deliberate restructuring before any
  hook-based pipeline enforcement; item 58's fingerprint gate remains
  unbuilt.
