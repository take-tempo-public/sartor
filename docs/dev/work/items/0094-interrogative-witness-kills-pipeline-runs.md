```toml
schema = 1
id = 94
kind = "item"
title = "The item-87 interrogative-witness pause kills N=1 pipeline runs: subagents share the invoker's session_id and eat its one-shot pause"
status = "open"
decision_owner = "user"
branches = ["feat/ats-conformance"]
refs = [
  "scripts/enforcement/guards/interrogative_witness.py",
  "scripts/enforcement/adapters/claude_context_hook.py:195-202",
  "docs/dev/work/items/0084-build-n1-baseline-pipeline.md",
  "docs/dev/work/items/0087-interrogative-prompt-witness-hook.md",
  "docs/dev/n1-baseline-pipeline.md",
]
summary = "Run 6 died to a benign self-clearing witness; the fix needs a discriminator whose existence is unverified."
```

**What happened.** Epic B run 6 (`wf_44350cb5-6b2`, 2026-08-14) stopped at
`escalated_to_owner` after 14.5 min / 163k subagent tokens with **no production code
written**. The implementer's first `Edit` to `json_resume.py` drew the item-87
interrogative-witness PAUSE; per Binding rule 3 (un-narrowed for this pipeline) it
returned `kind: "hook_block"`, and `escalate()` short-circuits that to the owner with
**no reviewer spawned**. A benign, self-clearing momentum witness killed a run.

This is the third counted encounter (run-3 preflight observed it; run 5 counted two
re-arms and survived; run 6 died of one), so it is a **recurrence**, not a first.

**Mechanism — read from code, not inferred (C-7).**

- `record_prompt` (UserPromptSubmit) resets `witnessed: False` — it re-arms on every
  prompt event.
- `decide` / `claude_check` key the pause on **`session_id` only**
  (`interrogative_witness.py:198-200`).
- The guard's own docstring states the limit at `:35-37`: *"PreToolUse also fires for
  subagents' Edit/Write calls, so a subagent's first edit can consume the turn's one
  pause on the main agent's behalf."*
- **Subagents share the invoker's `session_id` — VERIFIED by run 6**, closing a limit
  item 84 had explicitly left open ("inherited, not re-derived ... remains untested").
  The implementer was blocked, so it resolved *this* session's state file; a differing
  id would have found no state and failed open.
- State at the stop: `{"prompt_seq": 4, "interrogative": false, "witnessed": false}`
  against **3** genuine user turns — so non-user events arm it too. Re-confirmed
  minutes later when the invoker's own next `Edit` ate the identical pause.

**Therefore it is structural.** Any prompt-like event during a run — *including the
owner speaking to the invoker mid-run, which the authorization record explicitly
invites as the live-interrupt role* — arms a one-shot pause that the running subagent
eats. Runbook step 0a's "consume the pause deliberately" only covers arming **before**
the first `Workflow` call; nothing covers arming **during** a run.

**C-11 DECLARED GAP — no mechanism authored on this branch, and here is the reason.**
The obvious fix (skip subagent-originated edits) needs a discriminator, and the only
candidates are `agent_id` / `agent_type`. Their presence in a **PreToolUse** payload is
asserted from the Claude Code hooks reference in a code comment
(`claude_context_hook.py:195-202`), never observed here: the one test covering it
(`tests/test_c12_disclosure_gate.py:243-260`) feeds a **synthetic** payload, and **83
real `compacted` rows in `docs/dev/ledger/` carry zero `agent_id`**. That is not proof
of absence — those are PreCompact payloads and a subagent may simply never have
compacted — but it means the enrichment path has never fired once in 83 real
opportunities. Authoring a fix on an unverified discriminator is precisely the C-7
"plausible mechanism" trap. **The first commit on any branch that takes this item must
be the instrument, not the fix.**

**The instrument (cheap, decisive).** Spawn one trivial subagent that attempts a single
`Edit`, and log the raw PreToolUse payload — the `n1-agent-probe.mjs` shape, seconds and
one spawn. It either hands over the discriminator or kills the approach outright.

**Blast radius if the discriminator exists** (enumerated 2026-08-14, pre-implementation
per C-10; the guard is **not** on the gated-surface registry, so no dossier is
hook-forced):

- *Code:* `interrogative_witness.py` `decide`/`claude_check` + the now-wrong docstring
  limit at `:35-37`. The dispatcher already passes the whole payload; likely untouched.
- *Tests:* `tests/test_interrogative_witness.py` (17 test functions). **Trap:** none of
  them set `agent_id`, so keying the skip on that field leaves every existing test green
  while proving nothing about the new path — a new real-payload-shaped test is required.
  `tests/test_governance_hooks_gate.py` should stay green (the witness is
  `BLOCKER_RULE_NAMES` member #10; scoping changes *when* it blocks, not *whether* it is
  a blocker; the direct exercise at `:414-423` uses a main-session payload).
- *Docs (~8):* `docs/governance/enforcement.md:142,158`;
  `docs/wiki/pages/consistency-tracks-enforcement.md:138-139`;
  `docs/wiki/pages/governance-extraction.md:135-138`; `CLAUDE.md:133`;
  `CHANGELOG.md:58-62`; item 87 itself; `docs/dev/n1-baseline-pipeline.md:168`. Wiki
  pages carry grounding-audit obligations, so the branch owes a scoped
  `/wiki-self-update`.
- *Process:* item 87 is **closed**; reopening needs a `guardrail` per the closure bar.

**Semantic note.** Item 87 exists because the *main agent* treats the owner's question
as a work order. A pipeline subagent never receives the owner's prompt — it receives a
task brief — so the pause landing on it protects nothing and only misfires. Scoping it
out is a **precision improvement, not a weakening**. The one real risk is to the guard's
fail-open discipline: a discriminator that misclassifies a main-agent edit would
*silently* skip the pause, which argues for keying the skip on the **presence** of
`agent_id` so an absent or malformed field falls back to pausing.

## Updates

### 2026-08-14 — filed at the close of run 6 (`feat/ats-conformance`)

Filed with the gap declared rather than papered over, per C-11's "if no mechanism is
possible, say so explicitly, with the reason." The reason here is not impossibility but
**unverified premise** — see the instrument above. Note this item may be overtaken by
the owner's 2026-08-14 strategic redirect (item 97): if chain orchestration moves out of
sartor to an external runner with fresh per-item agents, the mid-run re-arm case may
stop existing rather than needing a fix.
