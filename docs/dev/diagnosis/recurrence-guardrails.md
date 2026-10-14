# Diagnosis — four recurrences from the regenerate-keeps-cover-letter handoff had no fail-closed mechanism

> **Status:** O1-O8 observed. **A2** (re-arm only on a human prompt) has its discriminator: the
> `prompt` begins with `<task-notification>` (O6, n=2). **A3** as designed (siblings from the
> transcript) is falsified (O7); the replacement mechanism is an owner decision, below.
> **Branch:** `fix/recurrence-guardrails`
> **Items:** 164 (witness), 165 (ledger rows), 166 (wiki cites), 167 (xfail controls).

---

## Symptom

`docs/dev/handoffs/regenerate-keeps-cover-letter.md` §"Recurrences observed this session"
records four recurrences. Three say "No mechanism authored" and the fourth is labeled
UNENFORCED. Charter C-11 asks for a mechanism that fails closed on the branch that recognizes a
recurrence, or an explicit statement that none is possible.

---

## Observed

**O1 — the witness re-arms on turns the owner did not type.** This session's transcript
(`~/.claude/projects/C--Dev-sartor/8463b4af-b6eb-492e-9744-c3e4acdadb39.jsonl`, read with a
Python one-off that prints every non-`tool_result` `type == "user"` line):

```
4   origin={'kind': 'human'}                                                   '<pasted_content …'
50  origin={'kind': 'human'}                                                   'Handoff: docs/dev/handoffs/regenerate-keeps-cover-letter.md @ main (d9'
97  origin={'kind': 'task-notification', 'producer': 'session-task', …}        '<task-notification>\n<task-id>aac855100d84e7f69</task-id>…'
```

The witness state file for the same session, read at the same time:

```
{"prompt_seq": 5, "interrogative": false, "witnessed": false}
```

`prompt_seq` is 5 against 2 typed prompts. `record_prompt`
(`scripts/enforcement/guards/interrogative_witness.py:132-151`) writes `witnessed: false` for
every `UserPromptSubmit` and never inspects `prompt`. The first Write of the session after
those events (the plan file) was refused with the witness's `PAUSE` text.

**O2 — a parallel batch is paused once.** `decide()`
(`scripts/enforcement/guards/interrogative_witness.py:176-198`) writes `witnessed = True`
(`:190-191`) before returning the block, so a later call reads `witnessed: true` and is
allowed (`:188`). In the transcript, one assistant message with several `tool_use` blocks is
stored as one JSONL line per block, all sharing `message.id` (script grouping by
`message.id`, this session: `msg_011Cg2C5McDuVvaM` → 3 `Agent` blocks at lines 58, 59, 60).

**O3 — hook-written rows go to the tracked shard on any branch.**
`record_compaction` (`scripts/enforcement/adapters/claude_context_hook.py:173-226`) resolves
its path in `_ledger_shard` (`:153-158`) as `docs/dev/ledger/<session>.jsonl` and appends
(`:222-223`); it never reads the branch before writing (the branch is only recorded as a field,
`:194`). `plan_gate.py:276-292` does the same for `plan-archived`. History:

```
$ git show --stat --format='%h %s' 71d0d17 7bcbc3a 2097a40
71d0d17 docs(ledger): compaction receipt during C1c gate #2
 docs/dev/ledger/93ed5108-6347-4192-a19a-2ec4c9f7a4b8.jsonl | 1 +
7bcbc3a test(persist): instrument - a regenerate of the same run never reaches the DB (item 160)
2097a40 test(item 162): instrument a resume-only regenerate blanking the cover letter
```

(`7bcbc3a` and `2097a40` each carry the previous session's `compacted` row per their commit
messages, per the handoff's Recurrence 1.) `git check-ignore -v .claude/state/ledger/x.jsonl`
→ `.gitignore:104:.claude/*`.

**O4 — the wiki loop has no deterministic cite check, and its auditor is Haiku.**
`agents/wiki-grounding-auditor.md:4` and `agents/wiki-scribe.md:4` both read
`model: claude-haiku-4-5-20251001`. `docs/wiki/log.md` records orchestrator review catching
what the auditor passed in three consecutive scoped passes — `:2699` (3 missed), `:2737`
(3 missed, auditor caught 0 of 3 pages), `:2784` (5 missed, auditor caught 1) — each ending in
a "Retune signal" (`:2705`, `:2747`, `:2800`). The pass at `:2619` (`fix/bash-tool-transport`)
caught nothing either way (`:2639-2641`). An earlier pass (`:2588`, `fix/heredoc-escape-guard`)
also caught a scribe overreach by review: the scribe removed a cite outside its brief
(`:2598-2601`). In the `:2737` pass the scribe added `generation.py:1232` and `:1546` as line
cites and review re-anchored them **before** the audit (`:2738-2740`), so the auditor never saw
them: those two are review catches of a mechanically checkable class, not auditor passes. The
unsourced intent claim the auditor did pass is at `:2743-2745`. The handoff's "fourth pass in a
row" counts the earlier one. The count of bare `path.ext:digits` cites currently in the pages:

```
$ grep -rEo "[A-Za-z0-9_/.-]+\.(py|js|html|md|css):[0-9]+" docs/wiki/pages | wc -l
9
```

**O5 — the xfail convention is prose only.**
`tests/test_regenerate_cover_letter.py:61-67` and
`tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py:70-76` each define
`class ControlFailed` and `_control`. `grep -rn "xfail(" tests | grep -i "strict=True"` returns
only docstring mentions of markers that were deleted
(`tests/test_frozen_composition_staleness.py:22`, `tests/test_regenerate_persistence.py:21`,
`tests/test_regenerate_cover_letter.py:26`,
`tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py:22`); `grep -n xfail_strict
pyproject.toml pytest.ini setup.cfg` returns nothing.

**O6 — a notification's `UserPromptSubmit` payload (the A1 instrument, commit `d3e5296`,
read from `<OS temp>/sartor-interrogative-witness/8463b4af-….trace.jsonl`; two background
tasks, 2026-10-14).** No `origin` field reaches the hook; the `prompt` text begins with the tag:

```
{"event": "prompt", "keys": ["cwd","hook_event_name","permission_mode","prompt","prompt_id","scratchpad_dir","session_id","transcript_path"], "prompt_head": "<task-notification>", "meta": {"hook_event_name": "UserPromptSubmit", "permission_mode": "auto", ...}}
{"event": "prompt", "ts": 1791985669.255, "keys": [same 8], "prompt_head": "<task-notification>", ...}
```

The witness state moved `prompt_seq: 6 → 7, witnessed: false` on the first of them, and the
next Write was refused with the `PAUSE` text. The transcript's `origin.kind` (O1) is **not**
in the hook payload, so it cannot be the discriminator.

**O7 — at PreToolUse time the paused call is not in the transcript yet.** Both probes (a
parallel batch of two Writes after a notification), `batch_siblings` over the payload's
`transcript_path`, 256 KB tail:

```
{"event": "pause", "tool_use_id": "toolu_018F4A7c…", "batch": {"found": false, "sibling_ids": [], "tail_bytes": 262001}}
{"event": "pause", "ts": 1791985673.756, "tool_use_id": "toolu_01AZkEm4…", "batch": {"found": false, "sibling_ids": [], "tail_bytes": 262072}}
```

**Control** (so `found: false` is a timing fact and not a broken lookup): the same function on
the same transcript after the turn, for the first probe's id, returned
`found: True, message_id: msg_011Cg2EQvYtGjrUdJgcEEd6g, sibling_ids: [toolu_018F4A7c…, toolu_01E1PG8M…]`.

**O8 — a batch sibling reached its hook 1.133 s after the pause.** From the timestamped
records of the second probe:

```
{"event": "pause", "ts": 1791985673.756, "tool_use_id": "toolu_01AZkEm4…", "blocked": true}
{"event": "call",  "ts": 1791985674.889, "tool_use_id": "toolu_01TwGQ8u…", "blocked": false}
```

n = 1 for the gap. Each hook is a fresh Python process, so part of that 1.1 s is interpreter
start-up; the figure bounds nothing from above.

---

## Falsified

- **A3 as designed: find the paused call's siblings by reading `transcript_path` from the
  PreToolUse hook.** Killed by O7: 2 of 2 pauses found nothing at hook time, with the lookup
  proven working by its control. No per-call transcript read can see the batch the call
  belongs to, because the assistant message is written after PreToolUse hooks run.
- **The transcript's `origin.kind == "task-notification"` as the witness's discriminator.**
  Killed by O6: the hook payload has no such field.

---

## Inferred

- **That a notification arriving mid-turn does not fire `UserPromptSubmit`.** The memory note
  `feedback-interrogative-is-not-a-work-order` records 2 of 3 notifications arming and calls the
  cause unresolved. Not tested here.
- **That an `AskUserQuestion` answer does not re-arm.** Memory note
  `reference-subagent-pretooluse-agent-id` records 0 of 3; the trace has not yet seen one.
- **That a window of a few seconds after a pause separates a batch sibling from the model's
  re-run.** O8 gives one sibling gap (1.133 s). A re-run needs a full model turn, which is
  longer in every case seen, but no distribution has been measured.

---

## Falsification

The A1 instrument writes, per `UserPromptSubmit`, the payload's key names, any
`origin`-like field, and the leading tag of `prompt`; and per pause, whether the paused call's
`tool_use_id` and its siblings are in the transcript tail.

- **A2 stands (O6)** if a notification's payload carries a field or a leading tag that a human
  prompt never does. Then the witness skips arming on it.
- **A2 is dead** if notification and human payloads are indistinguishable. Then stop and
  bring the owner the observation: the fix would have to live elsewhere (for example keying on
  `transcript_path`'s last user line).
- **A3 stands** if the sibling ids are in the tail at first-`PreToolUse` time. **A3 is dead**
  if they are not; then no per-call hook can see the batch and the declared "no mechanism
  possible" for the batched half stays, with the reason written down.
  **Verdict: dead (O7, 2 of 2, control passed).** The owner chooses what replaces it.

---

## The fix

_Not started. Per C-7 the first production commit after this dossier is the A1 instrument._

---

## Acceptance bar

- A task-notification arriving in a live session does not advance the arm counter; a typed
  prompt does. Shown by a live run and by `tests/test_interrogative_witness.py`.
- A temp-repo test on `main` asserts `git status --porcelain` is empty after
  `record_compaction` and the plan-gate archive; the same test on a branch asserts the row
  lands in the tracked shard.
- `scripts/wiki_cites.py` fails on a seeded bare line cite, a removed cite and a missing
  symbol; the shipped pages pass at the base ratchet.
- A synthetic source with `xfail(strict=True)` and no `raises=` fails
  `tests/test_xfail_controls_gate.py`.
- CI `ci_wait` exit 0, with no absorbed retry (C-7 rule 3).
