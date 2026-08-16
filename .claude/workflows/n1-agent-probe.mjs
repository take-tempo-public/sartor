export const meta = {
  name: 'n1-agent-probe',
  description: 'Preflight: prove every agentType the N=1 pipeline dispatches actually resolves',
  whenToUse:
    'Runbook step 0a, before the first n1-baseline sprint invocation of a session. Measured cost (run wf_d5ab3682-071): 6.2s and ~67k subagent tokens for two types — the system-prompt floor of a spawn, not free. Against run wf_9bb80d14-c94 (169k tokens, 22 min, sprint discarded) it is still the cheap arm, and it is the only check that exercises the real dispatch path.',
  phases: [{ title: 'Probe', detail: 'one trivial agent per configured agentType' }],
}

// ---------------------------------------------------------------------------
// Why this exists (work item 84, charter C-11).
//
// Three consecutive Epic B runs died at the invocation boundary, each on a
// harness-contract assumption that had been verified only against
// documentation or repo convention:
//
//   1. CRLF line endings rejected by the permission layer (.gitattributes gap)
//   2. `args` delivered as a JSON string despite a "verbatim" contract
//   3. bare-name `agentType` dispatch not resolving  <- run wf_9bb80d14-c94
//
// Failure 3 cost 22 minutes and 169k subagent tokens: the implementer had
// already finished a full sprint before the refuter spawn threw. None of the
// three was catchable by tests/test_n1_pipeline.py, whose own stated scope is
// self-consistency with the design docs, NOT harness compatibility.
//
// The deterministic half of the response lives in that test file
// (`unregistered_agent_types`, which fails closed on a bare name or a name
// with no agents/<name>.md). It has a real limit, stated rather than papered
// over: it encodes what we NOW know the namespace rule to be, so it would not
// have caught failure 3 before the fact. This probe is the half that would
// have -- it asks the harness itself, which is the only authority on whether
// a name resolves.
//
// Deliberately NOT a pytest: resolution can only be observed by spawning, and
// no agent harness exists in CI. That is a stated scope limit of the
// mechanism, not an oversight.
// ---------------------------------------------------------------------------

const PROBE_SCHEMA = {
  type: 'object',
  required: ['ack'],
  properties: {
    ack: { type: 'string', description: "the literal string 'ok'" },
  },
}

// The agentTypes n1-baseline.mjs actually dispatches. Kept in sync by
// tests/test_n1_pipeline.py, which pins the same three call sites.
const defaults = {
  agentTypes: ['sartor:n1-refuter', 'sartor:n1-judge'],
}

// Same defensive normalization as n1-baseline.mjs: the harness delivers
// `typeof args === 'string'` even when the caller passes a real object
// (observed 2026-08-12, probe wf_733613af-2c5). Duplicated rather than shared
// because a Workflow script has no filesystem access and cannot import.
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
const cfg = { ...defaults, ...(rawArgs || {}) }

if (!Array.isArray(cfg.agentTypes) || cfg.agentTypes.length === 0) {
  throw new Error('args.agentTypes must be a non-empty array of agentType strings')
}

phase('Probe')
log(`probing ${cfg.agentTypes.length} agentType(s): ${cfg.agentTypes.join(', ')}`)

// Each probe is individually caught: an unresolvable agentType THROWS out of
// agent() (that is exactly how run wf_9bb80d14-c94 died), and the point of
// this script is to REPORT every such name, not to die on the first one.
const outcomes = await parallel(
  cfg.agentTypes.map((agentType) => async () => {
    try {
      const reply = await agent(
        `Dispatch probe. Do not read any file, run any command, or edit anything.
Return through the structured output tool with ack set to the literal string "ok".`,
        { label: `probe:${agentType}`, phase: 'Probe', agentType, schema: PROBE_SCHEMA },
      )
      if (reply === null) {
        return { agentType, resolved: false, detail: 'agent() returned null (skipped or terminal API error)' }
      }
      return { agentType, resolved: true, detail: `ack=${reply.ack}` }
    } catch (err) {
      return { agentType, resolved: false, detail: String((err && err.message) || err) }
    }
  }),
)

// parallel() maps a thrown thunk to null; every thunk here catches its own
// error, so a null would mean the harness failed the thunk itself -- report
// it rather than silently dropping the row (no silent caps).
const results = outcomes.map((o, i) =>
  o === null ? { agentType: cfg.agentTypes[i], resolved: false, detail: 'probe thunk failed inside the harness' } : o,
)

const failed = results.filter((r) => !r.resolved)
for (const r of results) log(`${r.resolved ? 'RESOLVED' : 'FAILED  '} ${r.agentType} — ${r.detail}`)

return {
  probed: cfg.agentTypes,
  results,
  failed,
  allResolved: failed.length === 0,
  // The invoking session STOPS on allResolved === false: every configured
  // agentType must resolve before a real sprint is worth starting.
  verdict: failed.length === 0 ? 'ok_to_run' : 'do_not_run',
}
