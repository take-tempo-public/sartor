// n1-baseline.mjs — the N=1 baseline chain-orchestration pipeline (work item 84).
//
// Authorization: docs/dev/epic-a-chain-design-corrections.md §16.7, owner decision
// 2026-08-11 (recorded in docs/dev/work/items/0084-build-n1-baseline-pipeline.md).
// Design: §16.4 (structure), §16.5 (staged rollout). Contract + runbook:
// docs/dev/n1-baseline-pipeline.md — read it before invoking this script.
//
// BUILT, NEVER RUN. Executing this pipeline on a real sprint is a separate,
// explicitly owner-gated step (§16.5.2.3). The structural tests in
// tests/test_n1_pipeline.py certify self-consistency with the design docs,
// not harness compatibility — C-0 limit 1 in the contract doc.
//
// THE GATE NEVER RUNS INSIDE THIS SCRIPT OR ITS AGENTS. "python -m scripts.gate"
// belongs to the invoking session's main loop (epic-a-chain-design-corrections.md
// §11.9 — a subagent's gate dies with the agent). That string appears in this
// file only in this banner and inside prompt text BANNING it (every such line
// carries the word NEVER; tests/test_n1_pipeline.py pins this).
//
// N IS PINNED TO 1. Widening N past 1 is §16.7 decision point 3 — owner-reserved.
// The inter-sprint drift boundary below is therefore unreachable by construction.

export const meta = {
  name: 'n1-baseline',
  description: 'N=1 baseline sprint pipeline: implementer -> refuter -> judge -> closer (item 84)',
  whenToUse: 'Only with explicit owner authorization for a run; see docs/dev/n1-baseline-pipeline.md',
  phases: [
    { title: 'Implement', detail: 'one fresh implementer: dossiers, code, tests, stage — commits nothing' },
    { title: 'Refute', detail: 'Sonnet refuter reads the STAGED diff, told to refute' },
    { title: 'Judge', detail: 'fresh judge: per-finding fix / defer / escalate' },
    { title: 'Close', detail: 'closer: apply fixes, file items, board, handoff — no commit, no gate' },
    { title: 'Finalize', detail: 'commit-only, after the main loop reports gate #1 green + step-6 assertion' },
  ],
}

// ---------------------------------------------------------------------------
// Envelope citation block, embedded in every prompt (cite, don't restate —
// agents read the sections themselves; docs/dev/ORCHESTRATION_PLAYBOOK.md
// "cite this section in every lane prompt" precedent).
// ---------------------------------------------------------------------------

const ENVELOPE = `
Before doing anything else, read these sections of
docs/dev/epic-a-chain-design-corrections.md — they are your operating envelope:
- §11.5 (halt points — unconditional, owner-only, no judgment)
- §11.6 (flag stops — conditional "need a human if I hit this" triggers)
- §11.8 (what you decide alone inside the envelope, and record rather than surface)
- §11.9 (the delegation seam and your role's exact boundary)

Binding rule, verbatim and NOT narrowed for this pipeline (the dated 2026-08-09
narrowing in §11.6 is scoped "Epic A chain only" and does not apply here):
if a hook blocks you, surface the hook name and its message, and STOP — return
a flag of kind "hook_block" with the hook's own message in your verbatim field.
NEVER bypass a hook, never hand-create a file a hook checks for, and never
create or touch the plan-approval marker: a "NO EDIT APPROVAL" block from
check-plan-approved.sh is an immediate structured return, not a problem to solve.

NEVER run "python -m scripts.gate" — the gate belongs to the invoking session
(§11.9: a subagent's gate dies with the agent). Never pipe a long-running
command through tee; never trust "kill -0" on this machine (§11.9).

Flags: report anything matching §11.5 as kind "halt_point", a blocking hook as
kind "hook_block", anything matching §11.6 as kind "flag_stop". Your flag's
"verbatim" field is YOUR OWN WORDS and is carried to the reviewer and the
owner unparaphrased — write it as the sentence you would say to a human.
`

// ---------------------------------------------------------------------------
// Structured-output schemas
// ---------------------------------------------------------------------------

const FLAG = {
  type: 'object',
  required: ['kind', 'clause', 'verbatim'],
  properties: {
    kind: { type: 'string', enum: ['halt_point', 'hook_block', 'flag_stop'] },
    clause: { type: 'string', description: 'the §11.5/§11.6 clause number this flag invokes' },
    verbatim: { type: 'string', description: 'the flagging agent own words, carried unparaphrased' },
  },
}

const IMPLEMENTER_SCHEMA = {
  type: 'object',
  required: ['summary', 'filesWritten', 'dossierPaths', 'stagedDiffStat', 'flags'],
  properties: {
    summary: { type: 'string' },
    filesWritten: { type: 'array', items: { type: 'string' } },
    dossierPaths: { type: 'array', items: { type: 'string' } },
    stagedDiffStat: { type: 'string' },
    flags: { type: 'array', items: FLAG },
  },
}

const REFUTER_SCHEMA = {
  type: 'object',
  required: ['findings', 'structuralReport', 'flags'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'severity', 'claim', 'evidence'],
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['HIGH', 'MED', 'LOW'] },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'path:line or command output — no citation, no finding' },
        },
      },
    },
    structuralReport: { type: 'string', description: 'item-52 re-check result: doc links, hook modes, work_items check' },
    flags: { type: 'array', items: FLAG },
  },
}

const JUDGE_SCHEMA = {
  type: 'object',
  required: ['verdicts', 'flags'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['findingId', 'decision', 'rationale'],
        properties: {
          findingId: { type: 'string' },
          decision: { type: 'string', enum: ['fix', 'defer', 'escalate'] },
          rationale: { type: 'string' },
        },
      },
    },
    flags: { type: 'array', items: FLAG },
  },
}

const CLOSER_SCHEMA = {
  type: 'object',
  required: ['fixesApplied', 'itemsFiled', 'boardRegenerated', 'handoffPath', 'handoffValidated', 'filesWritten', 'flags'],
  properties: {
    fixesApplied: { type: 'array', items: { type: 'string' } },
    itemsFiled: { type: 'array', items: { type: 'string' } },
    boardRegenerated: { type: 'boolean' },
    handoffPath: { type: 'string' },
    handoffValidated: { type: 'boolean', description: 'verify_doc_template.py --event generated passed' },
    filesWritten: { type: 'array', items: { type: 'string' } },
    flags: { type: 'array', items: FLAG },
  },
}

const RECHECK_SCHEMA = {
  type: 'object',
  required: ['reconfirmed', 'cleared', 'flags'],
  properties: {
    reconfirmed: { type: 'array', items: { type: 'string' }, description: 'finding ids still failing after the fix' },
    cleared: { type: 'array', items: { type: 'string' } },
    flags: { type: 'array', items: FLAG },
  },
}

const REVIEW_SCHEMA = {
  type: 'object',
  required: ['decision', 'rationale'],
  properties: {
    decision: { type: 'string', enum: ['clear', 'targeted_fix', 'escalate'] },
    rationale: { type: 'string' },
  },
}

const FINALIZE_SCHEMA = {
  type: 'object',
  required: ['commitSha', 'filesWritten', 'flags'],
  properties: {
    commitSha: { type: 'string' },
    filesWritten: { type: 'array', items: { type: 'string' } },
    flags: { type: 'array', items: FLAG },
  },
}

// ---------------------------------------------------------------------------
// The unified escalation primitive (§16.4.1 item 4).
//
// kind 'halt_point' and 'hook_block' SHORT-CIRCUIT straight to the owner:
// §11.5 is "unconditional, no judgment involved" and a hook block is Binding
// rule 3 verbatim — no LLM reviewer may clear either. Only 'flag_stop' and
// 'coherence_drift' get the reviewer path, with the owner-decided refinement
// of one further independent review before fully stopping.
// ---------------------------------------------------------------------------

async function escalate(flag, context) {
  if (flag.kind === 'halt_point' || flag.kind === 'hook_block') {
    return { outcome: 'stop', flag, reviews: [] }
  }
  const reviewPrompt = (priorReview) => `
You are an independent escalation reviewer for the N=1 baseline pipeline
(docs/dev/n1-baseline-pipeline.md — read it, plus
docs/dev/epic-a-chain-design-corrections.md §16.4.1 item 4 and §11.6).

A ${flag.kind} flag was raised. The flagging agent's OWN WORDS, verbatim:
---
${flag.verbatim}
---
Clause invoked: ${flag.clause}. Source role: ${context.source}.

Wider view for your judgment:
- Epic design brief: ${context.epicBriefPath}
- Sprint brief: ${context.sprintBriefPath}
- Findings so far this run: ${JSON.stringify(context.findingsSoFar)}
- Inspect the diff since the last review yourself (git diff — read-only).
${priorReview ? `- A first independent reviewer already judged this flag: ${JSON.stringify(priorReview)}. You are the second, final review before the run stops for the owner.` : ''}

Decide: "clear" (the flag does not warrant stopping — say exactly why),
"targeted_fix" (name the precise fix the closer should apply), or "escalate"
(this needs the owner). When uncertain, escalate — stopping for input at a
significant decision beats a mistake that poisons the system (§16.0).
`
  const first = await agent(reviewPrompt(null), {
    label: `review:${flag.kind}`,
    phase: context.phase,
    model: context.reviewerModel,
    schema: REVIEW_SCHEMA,
  })
  if (!first) return { outcome: 'stop', flag, reviews: [{ decision: 'escalate', rationale: 'reviewer agent failed' }] }
  if (first.decision !== 'escalate') {
    return { outcome: first.decision === 'clear' ? 'cleared' : 'fix', flag, reviews: [first] }
  }
  const second = await agent(reviewPrompt(first), {
    label: `review2:${flag.kind}`,
    phase: context.phase,
    model: context.reviewerModel,
    schema: REVIEW_SCHEMA,
  })
  if (!second || second.decision === 'escalate') {
    return { outcome: 'stop', flag, reviews: [first, second].filter(Boolean) }
  }
  return { outcome: second.decision === 'clear' ? 'cleared' : 'fix', flag, reviews: [first, second] }
}

// Route every flag an agent returned; collect targeted-fix requests; stop on
// the first stop outcome (the run report carries everything gathered so far).
async function routeFlags(flags, context, escalations) {
  const fixRequests = []
  for (const flag of flags || []) {
    const result = await escalate(flag, context)
    escalations.push(result)
    if (result.outcome === 'stop') return { stopped: true, fixRequests }
    if (result.outcome === 'fix') fixRequests.push(result)
  }
  return { stopped: false, fixRequests }
}

// ---------------------------------------------------------------------------
// The pipeline
// ---------------------------------------------------------------------------

// §16.7 decision point 3: widening N past 1 is owner-reserved. Do not change
// this constant without that recorded decision.
const N = 1

const defaults = {
  stage: 'sprint',
  implementerModel: 'opus',
  closerModel: 'sonnet',
  reviewerModel: 'opus',
  // Item 89 + fix/n1-scope-dedup: which close-out ceremony the closer runs is
  // DERIVED from the sprint's position in its epic, never chosen by the
  // caller. Run 3's invoker ended a three-sprint epic after one sprint
  // because the ceremony was a caller decision with a session-terminating
  // default (item 84, tenth failure); the decision point is removed rather
  // than re-instructed. epicSprintIndex < epicSprintCount → a successor
  // sprint exists → 'intra_epic' (the NEXT sprint's brief from
  // EPIC_SPRINT_BRIEF_TEMPLATE.md, per the epic's declared light cadence —
  // epic-b-design-brief.md "Close-out intervals"); index === count → the
  // epic's LAST sprint → 'terminal' (the full AGENT_HANDOFF_TEMPLATE.md
  // ceremony). Reproducing the wrong ceremony now requires an affirmatively
  // false count, not an omitted arg.
  epicSprintIndex: 0, // REQUIRED for stage 'sprint': this sprint's 1-based position in the epic
  epicSprintCount: 0, // REQUIRED for stage 'sprint': total sprints in the epic
  nextSprintBriefPath: '', // required when a successor sprint exists; named by the invoking session
  driftCheckpoints: [], // pre-scheduled review sprints, declared at epic planning (RELEASE_ARC cadence rule)
  driftBackstop: 3, // reactive: sprints since the last coherence review
  deferredDriftThreshold: 5, // reactive: cumulative deferred refuter findings since the last review
}
// The Workflow contract documents `args` as reaching the script verbatim, and
// warns callers NOT to pass a JSON-encoded string. Observed 2026-08-12 (Epic B
// run 1, probe wf_733613af-2c5): the harness delivers `typeof args === 'string'`
// anyway, even when the caller passes a real object. Spreading a string yields
// index-keyed characters, so every required-arg guard below fired and the
// pipeline could not be invoked at all. Normalize defensively in both
// directions rather than trusting the documented contract: a JSON object
// string is parsed, a real object passes through untouched, an empty string
// counts as absent args (so the required-arg guard below names what is
// actually missing), and anything else is a loud caller error naming `args`.
let rawArgs = args
if (typeof rawArgs === 'string') {
  const trimmed = rawArgs.trim()
  if (trimmed === '') {
    rawArgs = undefined
  } else {
    try {
      rawArgs = JSON.parse(trimmed)
    } catch (err) {
      throw new Error(`args arrived as a string that is not valid JSON: ${err.message}`)
    }
  }
}
if (Array.isArray(rawArgs) || (rawArgs !== undefined && rawArgs !== null && typeof rawArgs !== 'object')) {
  throw new Error(`args must be a plain object (or a JSON object string); got ${Array.isArray(rawArgs) ? 'array' : typeof rawArgs}`)
}
if (rawArgs && 'closeoutKind' in rawArgs) {
  throw new Error("args.closeoutKind is no longer accepted — the ceremony is derived from epicSprintIndex/epicSprintCount (fix/n1-scope-dedup: a caller-chosen ceremony ended run 3's epic one sprint in; item 84, tenth failure)")
}
const cfg = { ...defaults, ...(rawArgs || {}) }

if (!cfg.sprintBriefPath || !cfg.epicBriefPath) {
  throw new Error('args.sprintBriefPath and args.epicBriefPath are required — the pipeline never invents its own brief')
}
if (cfg.stage === 'finalize' && !cfg.commitMessage) {
  throw new Error('args.commitMessage is required for stage "finalize" — the commit message is composed by the invoking session from the run report, never invented by an agent')
}
if (cfg.stage === 'sprint') {
  const idx = cfg.epicSprintIndex
  const count = cfg.epicSprintCount
  if (!Number.isInteger(idx) || !Number.isInteger(count) || idx < 1 || count < 1 || idx > count) {
    throw new Error(`args.epicSprintIndex and args.epicSprintCount are required for stage "sprint" (1-based integers, index <= count); got index=${JSON.stringify(cfg.epicSprintIndex)} count=${JSON.stringify(cfg.epicSprintCount)} — the ceremony derives from the sprint's position, never from a caller default`)
  }
  cfg.closeoutKind = idx < count ? 'intra_epic' : 'terminal'
  if (cfg.closeoutKind === 'intra_epic' && !cfg.nextSprintBriefPath) {
    throw new Error("args.nextSprintBriefPath is required when a successor sprint exists (epicSprintIndex < epicSprintCount) — the closer writes the NEXT sprint's brief there, and the pipeline never invents its own paths")
  }
} else {
  // finalize commits only; no ceremony is run, and the closer prompt that
  // reads closeoutKind is never built. Set the conservative value anyway so
  // the field is never undefined in the report.
  cfg.closeoutKind = 'terminal'
}

const report = { stage: cfg.stage, escalations: [], agents: {} }
const ctxBase = {
  sprintBriefPath: cfg.sprintBriefPath,
  epicBriefPath: cfg.epicBriefPath,
  reviewerModel: cfg.reviewerModel,
  findingsSoFar: [],
}

// Error boundary (retro #1, built 2026-08-12). A throw from the harness itself
// (an unresolvable agentType, an API failure surfacing as an exception)
// previously killed the whole workflow OUTSIDE the escalation primitive — the
// invoking session saw only a task notification and `escalations: []` (three
// consecutive runs died at an invocation boundary this way; wf_9bb80d14-c94
// alone spent 22 min + 169k tokens before its throw surfaced). The try below
// converts any stage-body throw into the same structured stop every other
// owner-bound signal uses. The caller-error guards above stay OUTSIDE it on
// purpose: a misinvocation should still throw loudly at invocation time,
// before any agent spawns. The stage bodies keep their original indentation —
// the wrapper is an error boundary, not a scope.
try {
if (cfg.stage === 'finalize') {
  // Invoked ONLY after the main loop reports gate #1 green AND the step-6
  // assertion passed (git diff --quiet, and git status --porcelain
  // --untracked-files=all empty — see the runbook). Commit only: the handoff
  // is already in the tree from the Close phase, so the post-commit gate #2
  // examines exactly the tree that lands.
  phase('Finalize')
  const fin = await agent(`
${ENVELOPE}
You are the finalize closer (§11.9.4, commit step only). The working tree is
staged, gated, and asserted unchanged since the gate. Your ONLY job: run
exactly one "git commit" with this message, verbatim:
---
${cfg.commitMessage}
---
Do NOT push, do NOT open a PR, do NOT merge (§11.5.1 — owner halt points).
Do NOT edit any file. You NEVER run "python -m scripts.gate".
Report the commit sha.
`, { label: 'finalize', phase: 'Finalize', model: cfg.closerModel, schema: FINALIZE_SCHEMA })
  report.agents.finalize = fin
  if (!fin) {
    report.status = 'agent_failed'
  } else {
    const routed = await routeFlags(fin.flags, { ...ctxBase, source: 'finalize', phase: 'Finalize' }, report.escalations)
    if (routed.stopped) {
      report.status = 'escalated_to_owner'
    } else {
      report.status = 'ready_for_postcommit_gate'
      report.commitSha = fin.commitSha
    }
  }
}

if (cfg.stage === 'sprint') {
  let cumulativeDeferred = 0
  let lastReviewSprint = 0

  sprintLoop: for (let sprint = 0; sprint < N && !report.status; sprint++) {
    // -- Implement ---------------------------------------------------------
    phase('Implement')
    const implementer = await agent(`
${ENVELOPE}
You are the implementer (§11.9.1). Read the sprint brief at
${cfg.sprintBriefPath} and the epic design brief at ${cfg.epicBriefPath}.
The invoking session has already created the feature branch — verify with
"git branch --show-current" and STOP with a halt_point flag if it is wrong.

The brief's named fix site is a HYPOTHESIS under C-0, not a spec: reproduce
the defect and verify the named mechanism is reachable on the failing path
BEFORE implementing it. Run 3's brief named an unreachable guard —
implementing it literally would have shipped green with the user-visible
defect intact.

Do the sprint's work: blast-radius dossier and (on a fix/* branch) diagnosis
dossier as the hooks require, code, tests. When done: "git add -A". Then STOP.
You COMMIT NOTHING — never run "git commit".
You NEVER run "python -m scripts.gate".
Report every file you wrote in filesWritten, as repo-RELATIVE paths with
forward slashes (never absolute) — the run's accounting invariant is that the
union of all agents' filesWritten covers "git status --porcelain" exactly; a
file you wrote but did not report reads as hand-implementation drift (§11.9).
`, { label: 'implementer', phase: 'Implement', model: cfg.implementerModel, schema: IMPLEMENTER_SCHEMA })
    report.agents.implementer = implementer
    if (!implementer) { report.status = 'agent_failed'; break sprintLoop }
    let routed = await routeFlags(implementer.flags, { ...ctxBase, source: 'implementer', phase: 'Implement' }, report.escalations)
    if (routed.stopped) { report.status = 'escalated_to_owner'; break sprintLoop }

    // -- Refute ------------------------------------------------------------
    phase('Refute')
    const refuter = await agent(`
${ENVELOPE}
You are the adversarial refuter (§11.9.2). Read the sprint brief at
${cfg.sprintBriefPath}. Read the STAGED diff ("git diff --staged") — that
diff, not the implementer's summary, is your subject. Your job is to REFUTE:
assume the implementation is wrong somewhere and find it. Every finding
carries evidence (path:line or command output) — no citation, no finding.
Fold in item 52's structural re-check: doc links resolve, hook modes intact,
and "python -m scripts.work_items check" passes (read-only validation — run
it). Implementer's report, for orientation only:
${JSON.stringify({ filesWritten: implementer.filesWritten, dossierPaths: implementer.dossierPaths })}
`, { label: 'refuter', phase: 'Refute', agentType: 'sartor:n1-refuter', schema: REFUTER_SCHEMA })
    report.agents.refuter = refuter
    if (!refuter) { report.status = 'agent_failed'; break sprintLoop }
    ctxBase.findingsSoFar = refuter.findings
    routed = await routeFlags(refuter.flags, { ...ctxBase, source: 'refuter', phase: 'Refute' }, report.escalations)
    if (routed.stopped) { report.status = 'escalated_to_owner'; break sprintLoop }

    // -- Judge -------------------------------------------------------------
    phase('Judge')
    const judge = await agent(`
${ENVELOPE}
You are the judge (§11.9.3) — this is the judgment pause the design exists to
protect. Read the real code+tests diff yourself ("git diff --staged"); do not
judge from summaries. For each refuter finding decide: "fix" (confirmed, must
land before commit), "defer" (real but outside this sprint's scope — it will
be filed as a work item), or "escalate" (a CONFIRMED finding whose fix would
change sprint SCOPE rather than correct implementation — §11.6.3; also raise
it as a flag_stop flag, in your own words).
Refuter findings: ${JSON.stringify(refuter.findings)}
`, { label: 'judge', phase: 'Judge', agentType: 'sartor:n1-judge', schema: JUDGE_SCHEMA })
    report.agents.judge = judge
    if (!judge) { report.status = 'agent_failed'; break sprintLoop }
    routed = await routeFlags(judge.flags, { ...ctxBase, source: 'judge', phase: 'Judge' }, report.escalations)
    if (routed.stopped) { report.status = 'escalated_to_owner'; break sprintLoop }
    const escalatedVerdicts = judge.verdicts.filter((v) => v.decision === 'escalate')
    if (escalatedVerdicts.length > 0) {
      // A judge 'escalate' verdict stops the run even without its own flag —
      // it is a §11.6.3 boundary by definition, and the rationale is the
      // judge's own words, carried unparaphrased.
      for (const v of escalatedVerdicts) {
        report.escalations.push({
          outcome: 'stop',
          flag: { kind: 'flag_stop', clause: '11.6.3', verbatim: v.rationale },
          reviews: [],
        })
      }
      report.status = 'escalated_to_owner'
      break sprintLoop
    }
    const toFix = judge.verdicts.filter((v) => v.decision === 'fix')
    const toDefer = judge.verdicts.filter((v) => v.decision === 'defer')
    const reviewerFixes = report.escalations.filter((e) => e.outcome === 'fix')

    // -- Close -------------------------------------------------------------
    phase('Close')
    // Item 89 (fixed 2026-08-12): the ceremony branches on closeoutKind — the
    // epic's declared cadence is light per sprint, full ceremony once at the
    // epic close. Board regen (step 3) deliberately stays in BOTH branches:
    // the gate's own "work_items check" step binds board freshness on every
    // gate run (scripts/gate.py), so deferring it is unimplementable.
    const closeoutStep = cfg.closeoutKind === 'intra_epic'
      ? `4. Intra-epic sprint transition (item 89 — the epic's declared light
   cadence, epic-b-design-brief.md §"Close-out intervals"): write the NEXT
   sprint's brief at ${cfg.nextSprintBriefPath} from
   docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md (READ IT FIRST — it is a
   floor, not a form: every section present, "none" stated explicitly rather
   than deleted; a fresh agent must be able to run the next sprint from the
   brief plus its pointers alone, without a transcript). Do NOT write the
   full docs/dev/AGENT_HANDOFF_TEMPLATE.md ceremony — that is owed ONCE, at
   the epic close, not per sprint. Report the brief's path as handoffPath
   and set handoffValidated to false (verify_doc_template.py validation is
   deferred to the epic close by design).`
      : `4. Write the next-agent handoff at docs/dev/handoffs/<branch-slug>.md from
   docs/dev/AGENT_HANDOFF_TEMPLATE.md (READ IT FIRST; reproduce every
   verbatim-marked section byte-for-byte), stamped per docs/dev/prov/SPEC.md
   §1 — the stamp's commit field is HEAD at generation time; the doc's own
   commit does not exist yet, and that is correct (SPEC §1). Validate it:
   "python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent-id>".
   A failed result is authoring corruption in the handoff — fix the file,
   never silence the check.`
    const closer = await agent(`
${ENVELOPE}
You are the closer (§11.9.4). The corrected close ordering
(epic-a-chain-design-corrections.md §2 steps 1-5 — the gate and the commit
are NOT yours) governs. In order:
1. Apply exactly these confirmed fixes (judge verdicts + reviewer-requested
   targeted fixes) — nothing else:
   ${JSON.stringify({ judge: toFix, reviewers: reviewerFixes.map((r) => r.reviews[r.reviews.length - 1]?.rationale) })}
2. File each deferred finding as a work item under docs/dev/work/items/:
   ${JSON.stringify(toDefer)}
3. Regenerate the board: "python -m scripts.work_items board --write".
${closeoutStep}
5. Run the wiki-relevance check on this branch's diff
   (scripts/wiki_relevance.py classification); make any required scoped wiki
   edit now, or record the explicit verified-no-edit finding in
   docs/wiki/log.md.
6. Before reporting: run the gate's STATIC steps on your own work — "ruff
   check" and "ruff format --check" on every file you touched, and
   "python -m mypy ." — and fix what they flag. Run 3's gate #1 failed on a
   mypy union-attr error in closer-authored test code; these three checks
   are yours. The full gate is NOT (see the ban below).
Then "git add -A" (the handoff, any filed items, the board, and the session
ledger shard all ride the same staging) and STOP. You COMMIT NOTHING — never
run "git commit"; the commit happens in the finalize stage after the invoking
session's gate #1 and step-6 assertion.
You NEVER run "python -m scripts.gate".
Report every file you wrote in filesWritten, as repo-RELATIVE paths with
forward slashes (never absolute — the accounting comparison runs on
repo-relative form).
`, { label: 'closer', phase: 'Close', model: cfg.closerModel, schema: CLOSER_SCHEMA })
    report.agents.closer = closer
    if (!closer) { report.status = 'agent_failed'; break sprintLoop }
    routed = await routeFlags(closer.flags, { ...ctxBase, source: 'closer', phase: 'Close' }, report.escalations)
    if (routed.stopped) { report.status = 'escalated_to_owner'; break sprintLoop }

    // -- Bounded fix re-check (one round; §11.6.3 on a re-confirmation) ----
    if (toFix.length > 0 || reviewerFixes.length > 0) {
      const recheck = await agent(`
${ENVELOPE}
You are the refuter again, re-checking ONLY the fixes the closer just applied
(staged diff, "git diff --staged"). Findings under re-check:
${JSON.stringify(toFix)}
For each: "cleared" (the fix holds) or "reconfirmed" (still failing — cite
the evidence). A reconfirmed finding is a §11.6.3 boundary: also raise it as
a flag_stop flag in your own words. This is the ONE bounded re-check round —
there is not another.
`, { label: 'refuter-recheck', phase: 'Close', agentType: 'sartor:n1-refuter', schema: RECHECK_SCHEMA })
      report.agents.recheck = recheck
      if (!recheck) { report.status = 'agent_failed'; break sprintLoop }
      routed = await routeFlags(recheck.flags, { ...ctxBase, source: 'refuter-recheck', phase: 'Close' }, report.escalations)
      if (routed.stopped) { report.status = 'escalated_to_owner'; break sprintLoop }
      if (recheck.reconfirmed.length > 0) {
        for (const id of recheck.reconfirmed) {
          report.escalations.push({
            outcome: 'stop',
            flag: { kind: 'flag_stop', clause: '11.6.3', verbatim: `finding ${id} reconfirmed after its one bounded fix round` },
            reviews: [],
          })
        }
        report.status = 'escalated_to_owner'
        break sprintLoop
      }
    }

    // -- Coherence-drift boundary (§16.4.1.3) ------------------------------
    // Evaluated ONLY between sprints: at N=1 `sprint < N - 1` is `0 < 0`,
    // so this block is unreachable by construction — pinned by
    // tests/test_n1_pipeline.py, not asserted from hope.
    cumulativeDeferred += toDefer.length
    if (sprint < N - 1) {
      const sprintIndex = sprint + 1
      const preScheduled = cfg.driftCheckpoints.includes(sprintIndex)
      const backstop = sprintIndex - lastReviewSprint >= cfg.driftBackstop
      const deferredHeavy = cumulativeDeferred >= cfg.deferredDriftThreshold
      if (preScheduled || backstop || deferredHeavy) {
        const result = await escalate(
          {
            kind: 'coherence_drift',
            clause: '16.4.1.3',
            verbatim: `deterministic drift trigger: preScheduled=${preScheduled} backstop=${backstop} cumulativeDeferred=${cumulativeDeferred}`,
          },
          { ...ctxBase, source: 'drift-monitor', phase: 'Close' },
        )
        report.escalations.push(result)
        if (result.outcome === 'stop') { report.status = 'escalated_to_owner'; break sprintLoop }
        lastReviewSprint = sprintIndex
        cumulativeDeferred = 0
      }
    }
  }

  if (!report.status) {
    // Accounting invariant (§11.9's owner-check, restored to falsifiability):
    // the runbook compares this union against "git status --porcelain" — both
    // sides on repo-relative, forward-slash form (retro #4: run 3's check
    // passed only because a hand normalization bridged the implementer's
    // relative paths and the closer's absolute ones).
    const normalizeReportedPath = (p) => String(p).replace(/\\/g, '/').replace(/^\.\//, '')
    const claimed = [
      ...(report.agents.implementer?.filesWritten || []),
      ...(report.agents.closer?.filesWritten || []),
    ].map(normalizeReportedPath)
    report.status = 'ready_for_gate'
    report.accounting = { claimedFilesWritten: [...new Set(claimed)] }
  }
}
} catch (err) {
  report.escalations.push({
    outcome: 'stop',
    flag: {
      kind: 'harness_throw',
      clause: 'C-0 limit 1 (docs/dev/n1-baseline-pipeline.md "Stated limits")',
      verbatim: `harness throw in stage '${cfg.stage}': ${err && err.message ? err.message : String(err)}`,
    },
    reviews: [],
  })
  report.status = 'escalated_to_owner'
}

return report
