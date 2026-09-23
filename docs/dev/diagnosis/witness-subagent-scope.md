# Diagnosis — the item-87 witness pause is consumed by pipeline subagents (item 94)

> **Status:** discriminator OBSERVED (2026-09-22 instrument, below). A subagent's PreToolUse
> payload carries `agent_id`/`agent_type`; the main agent's does not.
> **Branch:** `fix/witness-subagent-scope`

---

## Symptom

Epic B run 6 (`wf_44350cb5-6b2`, 2026-08-14) stopped at `escalated_to_owner` after
14.5 min with no production code written. The implementer's first `Edit` drew the
interrogative-witness PAUSE, it returned `kind: "hook_block"`, and `escalate()`
short-circuited to the owner. Work item 94 has the full record.

---

## Observed

- Run 6 stop, recorded at `docs/dev/work/items/0094-interrogative-witness-kills-pipeline-runs.md`
  §"What happened": run `wf_44350cb5-6b2`, `escalated_to_owner`, implementer `kind: "hook_block"`
  on its first `Edit` to `json_resume.py`.
- The pause is keyed on `session_id` only: `scripts/enforcement/guards/interrogative_witness.py`
  `claude_check` → `decide(str(payload.get("session_id") or ""), env)` (read at HEAD `9cafbde`).
- `record_prompt` resets `"witnessed": False` on every UserPromptSubmit event
  (`interrogative_witness.py` `record_prompt`, read at HEAD `9cafbde`).
- Run-6 state file at the stop: `{"prompt_seq": 4, "interrogative": false, "witnessed": false}`
  against 3 genuine user turns (item 94 §"Mechanism").
- The presence of `agent_id` in a PreToolUse payload has **never been observed in this repo**.
  `scripts/enforcement/adapters/claude_context_hook.py:195-202` asserts it from the hooks
  reference. Measured this session: `grep -c '"compacted"' docs/dev/ledger/*.jsonl` sums to
  **99** rows, and `grep -l agent_id docs/dev/ledger/*.jsonl` matches **0** files. (Those
  are PreCompact payloads, so this is not proof of absence on PreToolUse.)
- **Instrument result, 2026-09-22, session `0ea1b8bf`.** This is the key-only trace in
  `claude_check`, file `%TEMP%/sartor-interrogative-witness/payload-keys.jsonl`. It captured
  one main-agent `Edit` followed by one general-purpose subagent `Edit` (Haiku) on the same
  scratch file:

  ```
  {"tool": "Edit", "keys": ["cwd", "effort", "hook_event_name", "permission_mode", "prompt_id", "scratchpad_dir", "session_id", "tool_input", "tool_name", "tool_use_id", "transcript_path"]}
  {"tool": "Edit", "keys": ["agent_id", "agent_type", "cwd", "hook_event_name", "permission_mode", "prompt_id", "scratchpad_dir", "session_id", "tool_input", "tool_name", "tool_use_id", "transcript_path"]}
  ```

  The subagent row carries `agent_id` and `agent_type`, and the main-agent row carries
  neither. This is the first observation of the discriminator in this repo.
- The subagent `Edit` was **not** paused. The main agent's first `Edit` after the prompt
  had already consumed this turn's pause, so this run does not exercise the eaten-pause
  path itself. Run 6 above is the observation of that path.
- **Non-user events re-arm the pause, observed live in the same session.** The subagent's
  hand-back message arrived as a new turn. My next main-agent `Edit` (to this dossier)
  drew `PAUSE (interrogative-witness): first Edit/Write since the last user prompt.`, even
  though no user prompt came in between. This matches item 94's `prompt_seq: 4` vs 3 user
  turns. A subagent's completion is a re-arm event.

---

## Falsified

_(Nothing yet.)_

---

## Inferred

UNPROVEN: a subagent's PreToolUse payload carries `agent_id` (and/or `agent_type`), and
the main agent's payload does not. If so, skipping the pause when `agent_id` is present
scopes the witness to the main agent without weakening it. What I would have to SEE:
the raw top-level key set of one subagent `Edit` payload and one main-agent `Edit`
payload from this harness.

---

## Falsification

Instrument: a key-only trace in `interrogative_witness.claude_check`. It appends
`sorted(payload.keys())` plus `tool_name` to a JSONL file under the witness state dir.
It never records values. Then:

1. the main agent performs one `Edit`,
2. one trivial general-purpose subagent performs one `Edit` on a scratch doc,
3. read the trace.

- **If the subagent row has `agent_id` and the main row does not:** hypothesis confirmed;
  build the fix.
- **If neither row has it, or both do:** hypothesis dead. There is no discriminator; the
  fallback is the item-95 amendment plus runbook step 0a, declared to the owner as a C-11 gap.

---

## The fix

_Pending the experiment._

---

## Acceptance bar

_Pending the experiment._
