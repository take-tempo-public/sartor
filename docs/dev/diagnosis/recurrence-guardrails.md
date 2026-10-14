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

**O9 — an `AskUserQuestion` answer produced no `UserPromptSubmit` record** (n = 1, this
session, between the second probe and the fix): the trace held exactly the two notification
`prompt` records before and after the answer.

**O10 — after the fix (`28812dd`), the drive that paused twice no longer pauses.** Same drive:
a background task completes, its notification arrives, then one Write. State before and after:

```
before: {"prompt_seq": 8, "interrogative": false, "witnessed": true}
after:  {"prompt_seq": 9, "interrogative": false, "witnessed": true}     # notification moved the counter only
Write -> File created (no PAUSE)
```

**O11 — the whole path, through the real entry points** (`hook.py interrogative-prompt-witness`
and `hook.py edit-write-dispatcher`, one process per call, throwaway session and state dir,
default 3 s window; script kept in the session scratchpad):

```
human prompt arms                  exit=0
call 1 (pause)                     exit=2  PAUSE (interrogative-witness): first Edit/Write since the last user prompt.
call 2 (sibling, immediately)      exit=2  PAUSE (interrogative-witness): sibling of a paused call.
call 3 (sibling, immediately)      exit=2  PAUSE (interrogative-witness): sibling of a paused call.
call 4 (re-run after window)       exit=0
notification (must not arm)        exit=0
call 5 (after notification)        exit=0
state: {"prompt_seq": 2, "armed_seq": 1, "interrogative": false, "witnessed": true, "paused_at": 1791988213.82}
```

Each hook process took 0.13-0.35 s in that run.

**O12 — the ledger defect, reproduced on the unfixed writers** (`tests/test_ledger_spool.py`,
10 tests against throwaway git repos with the real `.claude/*` ignore rule, before
`scripts/enforcement/ledger_spool.py` existed):

```
FAILED TestCompactionReceipt::test_a_compaction_on_main_leaves_the_tree_clean
       AssertionError: assert '?? docs/\n' == ''
FAILED TestCompactionReceipt::test_master_is_trunk_too[master]
FAILED TestCompactionReceipt::test_a_detached_head_is_trunk_too
FAILED TestCompactionReceipt::test_the_count_spans_both_locations
FAILED TestCompactionReceipt::test_the_spool_is_lf_only
FAILED TestPlanArchivedReceipt::test_a_retirement_on_main_leaves_the_tree_clean
6 failed, 4 passed
```

The 4 that passed are controls (a feature branch, a directory with no git, the real
`.gitignore`), so the 6 failures are the defect and not a broken drive.

**O13 — after the fix, through the real entry points** (`hook.py capture-before-compact` and
`hook.py restore-evidence`, throwaway repo, session `e2e-ledger-165`):

```
PreCompact on main          exit=0   git status --porcelain = ''   tracked shard exists = False   spool exists = True
  spool row = {"event": "compacted", "session": "e2e-ledger-165", "branch": "main", "trigger": "auto", ...}
SessionStart(compact)       "Compactions on record this session: 1."
PreCompact on fix/e2e       exit=0   git status --porcelain = '?? docs/\n'   (a branch row is tracked, as before)
SessionStart(compact)       "Compactions on record this session: 2."
```

**O14 — the xfail gate bites on the real tree, not only on synthetic source**
(`tests/test_xfail_controls_gate.py`, session scratchpad `mutate_xfail_gate.py`):

```
baseline problems: []
with violating file: 2
   tests/_probe_xfail_violation.py:4: strict xfail without raises=AssertionError; a broken drive would read as the expected defect
   tests/_probe_xfail_violation.py: holds a strict xfail but does not import control/ControlFailed from tests._controls, so its controls are bare asserts
after removal: [] | probe exists: False
```

At HEAD the repo holds no strict xfail (`grep -rn "xfail(" tests | grep -i "strict=True"` finds
only docstrings), so the gate passes on the shipped tree by construction; the probe is what shows
it is not vacuous.

**O15 — what the wiki's cites look like, measured with `scripts/wiki_cites.py` (item 166).**
`python -m scripts.wiki_cites --summary`, 44 pages (`pages/*.md`, `overview.md`, `index.md`):

```
cites by kind:          {'symbol': 727, 'line': 11, 'prose-line': 14}
with a resolved path:   {'symbol': 727, 'line': 11}
line cites per page:    diagnostics-console 2, document-rendering 3, education-degree-field-rendering 12,
                        governance-extraction 2, llm-call-catalog 1, non-dependency-downloads 2,
                        openapi-api-reference 1, route-surface 2        (total 25)
E2 (past end of file):  0        E3 (symbol absent from file):  0
```

The first run reported 6 E3 hits, all `` [`parser.py`](../../../parser.py) `` / `scraper.py`: a
file-name label read as a symbol. They were false positives, fixed by treating a label that ends
in a file extension as a path, and pinned by `test_a_filename_label_is_a_path_not_a_symbol`.
Widening prose-line detection to the preceding wrapped line moved the count from 20 to 25
(`education-degree-field-rendering.md` 7 → 12).

**O16 — the three rules fire on a real page, not only on synthetic source.** A violation seeded
into `docs/wiki/pages/llm-call-catalog.md` in memory (the file on disk untouched):

```
docs/wiki/pages/llm-call-catalog.md:164: E2: analyzer.py:99999 is past the end of the file (5027 lines)
docs/wiki/pages/llm-call-catalog.md:164: E3: analyzer.py does not contain 'no_such_symbol_zzz' (cited as 'no_such_symbol_zzz')
docs/wiki/pages/llm-call-catalog.md:0: E1: 3 bare line cite(s), 1 allowed: cite a symbol (or a heading) instead of a line number
clean tree: True
```

**O17 — a corrected test sweep was needed to see anything.** The first "wider sweep" passed with
`22 passed, 364 deselected`: a `-k` expression meant for one slow file filtered every file in the
invocation. Re-run as two invocations (`-k` on `test_plan_approval_scoping.py` only):
`11 passed, 26 deselected` and `408 passed, 2 skipped in 128.08s` over `test_enforcement_core`,
`test_n1_pipeline`, `test_enforcement_coverage`, `test_governance_hooks_gate`,
`test_evidence_gate`, `test_c12_disclosure_gate`, `test_ledger_spool`,
`test_verify_doc_template` and `test_interrogative_witness` (session scratchpad `wider2.log`).

**O18 — the full local gate on `490f021` did not finish: the harness killed it for low system
memory while the UX tier was at 52%.** Session scratchpad `gate.log`, read after the kill:

```
=== gate: ruff check . ===            passed
=== gate: ruff format --check . ===   passed
=== gate: mypy . ===                  Success: no issues found in 423 source files
=== gate: pytest -m "not ux" -n auto ===   3365 passed, 8 skipped in 345.26s (0:05:45)
=== gate: pytest -m ux ===            91 PASSED, 0 FAILED, killed at [ 52%]
background task status: killed -- "the system is running low on memory"
```

- **Not a pass.** `python -m scripts.gate --result` reads `FAILED -- last run: exit 1, failed step
  'memory preflight', finished 2026-10-11T09:09:54, HEAD 6dc58c3`: the killed run was terminated
  hard and wrote no result, so the file still holds an earlier run's. There is **no local gate
  pass for this tree**.
- **No failure and no retry in what ran.** `grep -c -E "\] (FAILED|ERROR|RERUN|XPASS)"` over the
  log returns 0; the 32 looser matches are test names containing "rerun" and the plugin banner
  (`rerunfailures-16.4` was active, so an absorbed rerun would have printed).
- **Free memory read 4.36 GB when it started** against the gate's 1.0 GB floor, so the preflight
  did not refuse. The harness's own reaper stopped it. `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`
  turns that off, but only at Claude Code startup.
- The UX tier's remaining 48% is unrun here. CI's `ux` job is where it runs.

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

Item 164 (`28812dd`, after the instrument commits `d3e5296` and `a2bdc9c`):

- **A2.** `record_prompt` does not arm on a prompt that begins `<task-notification>` (O6). It
  advances `prompt_seq` only, so an arm the owner's real prompt left unconsumed survives, and
  `armed_seq` counts real arms. Shapes not seen still arm.
- **A3 replacement (owner decision, 2026-10-14).** `decide` stamps `paused_at`; main-agent
  Edit/Write calls within `SARTOR_WITNESS_BATCH_WINDOW_S` (default 3, 0 disables) are refused as
  siblings (O7 killed the transcript design). It is a timing heuristic and says so in the
  refusal, the module docstring and `docs/governance/enforcement.md`.
- **Declared limits.** (1) A sibling slower than the window lands as before. (2) A re-run
  inside the window is refused once more. (3) The 1.13 s sibling gap is n = 1; no distribution
  was measured. (4) Scheduled-wakeup, cron and usage-limit-resume prompts were not observed
  and still arm.
- The instrument was removed in `960dcd9`; `git show d3e5296 a2bdc9c` keeps it.

Item 165 (this commit's successor, same branch):

- `scripts/enforcement/ledger_spool.py` routes a hook-written receipt: `main`, `master` or a
  detached `HEAD` go to the untracked `.claude/state/ledger/<session>.jsonl`, any other branch to
  the tracked shard. `claude_context_hook.record_compaction` and `plan_gate.retire` both write
  through `hook_shard`, and `compaction_count` reads both places.
- Owner decision (2026-10-14): divert only on trunk, so branch-time rows stay committed evidence.
- `docs/dev/prov/SPEC.md` §3 now names `compacted` and `plan-archived` (closes item 55).
- **Declared limits.** A branch name of `""` keeps the tracked shard (no repo, or `git` failed).
  `plan_gate` reads `.git/HEAD` itself and reports a detached HEAD as `""`, so its receipt stays
  tracked there. The spool is machine-local and is not part of the committed record.

Item 166 (owner decision, 2026-10-14: all three parts):

- `scripts/wiki_cites.py`: E1 bare line cites ratcheted per page in `ALLOWED_LINE_CITES` (exact
  counts, both directions), E2 a line cite past the end of its file, E3 a cited symbol the file
  does not contain, E4 (`--base`, listed; `--strict-removed` to fail) a symbol cite removed while
  its target still exists. E1-E3 are a pytest test (`TestTheRealTree`), so they ride the gate's
  `pytest` step like `wiki_freshness` does; **no separate `scripts/gate.py` step** (a deviation
  from the plan, recorded in the blast-radius dossier row 33).
- E4 is deliberately **not** in the merge gate: a deliberate removal has no way through there.
  `commands/wiki-self-update.md` runs it (step 4), where the orchestrator restores the cite or
  logs the removal.
- `agents/wiki-grounding-auditor.md` moves to `claude-sonnet-5` and gains four explicit checks
  (a claim about a branch the code can take, a negative or universal claim, an intent, a
  placement or name). `CLAUDE.md`, `docs/dev/tooling.md` and `docs/dev/decisions.md` (PX-47b,
  amended) carry the new counts.
- `commands/wiki-self-update.md` step 6: the orchestrator reviews every added sentence against
  source. **Prose, labeled unenforced** (C-11).
- Declared limits: whether a sentence is *true* is not checkable by a script; a `lines N-M` with
  no path on its own or the preceding line is not seen; E3 is word-presence, weaker than "defined
  here". Not measured: Sonnet's catch rate against Haiku's, or its per-pass cost.

Item 167:

- `tests/_controls.py` holds `ControlFailed` and `control` once; the two files that each defined
  them import it (`tests/test_regenerate_cover_letter.py`, the B7 browser arm).
- `tests/test_xfail_controls_gate.py` fails on a strict `xfail` without `raises=AssertionError`
  (or with `Exception`/`BaseException`/`ControlFailed`, which would match the step failures it
  exists to separate), on a module holding one that does not import the shared helper, and on a
  second `ControlFailed` definition. The project's `xfail_strict` setting is honored.
- **Declared limits.** Whether a step *uses* `control` rather than a bare `assert` is not
  checked: that needs a call graph through each arm's drive helpers. Non-strict xfails (two
  exist, deliberately, in `test_20260708_busy_states_and_chip.py`) and the imperative
  `pytest.xfail(...)` are out of scope.

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
