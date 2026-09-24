# Epic C sprint brief — C1c: `feat/llm-call-error-capture` (run 3 of 5, inserted)

> Written by the Epic C invoker (session `93ed5108`, Opus 5.5), 2026-09-24, from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`. The owner directed this sprint
> mid-epic, so the invoker wrote the brief. There was no previous closer to write it, and
> C1a's kickoff brief is the precedent for invoker-written briefs.

## Sprint identity

- **Sprint:** C1c, run 3 of 5 (`epicSprintIndex: 3`, `epicSprintCount: 5`). It is inserted
  ahead of C2, so C2 becomes run 4 and C3 becomes run 5 (terminal).
- **Branch:** `feat/llm-call-error-capture`. It has already been created by the invoker.
- **Stacked on:** `feat/run-detail-modal @ a66edb7`. That tip holds two docs-only commits on
  top of the epic tip `e7005b2`: `b5fe01b` (C1b sha record) and `a66edb7` (C2 run record +
  owner decision). **The branch carries no C2 code.** C2's staged implementation is parked in
  the invoker's stash (see "Open risks").
- **Implementer model:** `sonnet`. The invoker chose it under §11.8 because RELEASE_ARC
  §"Session models" sets C1/C2 = Sonnet and this sprint sits between them. The owner has not
  set a model for C1c. **Reported in the boundary report, not asked mid-window.**

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md` — **read in full**, including the ratified scope sentence and its 2026-09-24 amendment record (this sprint) |
| Authorization envelope | `epic-c-design-brief.md` §"Execution mode + authorization record", §"Escalation + envelope"; `docs/dev/epic-a-chain-design-corrections.md` §11.4-§11.9 |
| Close-out cadence | `epic-c-design-brief.md` §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", the **C1c** bullet (added 2026-09-24) |
| Why this sprint exists | `docs/dev/handoffs/epic-c-c2-brief.md` §"Invoker run record (C2)": the escalation from run `wf_697596d4-c2f` and the owner's decision |

## What just landed

- C1a `150bfb9` and C1b `27a1fdc`, plus ledger commit `e7005b2`, are ff-merged into
  `epic/c-diagnostics`. Both of C1b's gates passed (`gate: all steps passed.`, 0 `RERUN`). The
  C2 invoker verified this from `gate1.log`/`gate2.log`.
- C2 run `wf_697596d4-c2f`: the implementer built UX-7 and a metadata-only UX-8, then raised
  a `flag_stop`. Both Opus reviewers escalated it to the owner.
  - **The finding, verified by both reviewers:** `analyzer.py`'s `_call_llm_streaming`
    `except` branches set `status = "error"` and re-raise.
  - The `finally` block's `_emit_call_log(...)` record carries no exception text, so
    `logs/llm_calls.jsonl` holds no error message anywhere.
  - Owner decision: option (a). Then the owner's typed directive: **"Insert an error-capture
    sprint before C2, then continue the epic."** That is this sprint.
- **The refuter, judge and closer never ran on C2.** C2's code is unreviewed and ungated.

## What this sprint builds

**In scope:**
- **Error capture in the call telemetry record.** In `analyzer.py`'s `_call_llm_streaming`,
  every row written with `status == "error"` gains two fields:
  - `error_type`: the exception's class name, e.g. `"APIStatusError"` or
    `"LLMConfigurationError"`. When the `TypeError` branch re-labels the error, record the
    type that is actually raised.
  - `error_message`: `str(exc)` after the redaction/size policy below.
  - Rows with `status == "ok"` are **unchanged**. Do not add null-valued keys to them;
    readers already tolerate absence, because every existing row lacks the fields.
- **Redaction/size policy.** The owner asked for "a redaction/size policy". The invoker
  specifies it here, under §11.8, and reports it at the boundary:
  1. Collapse whitespace runs to single spaces.
  2. Mask any API-key-shaped substring: `sk-ant-` followed by key characters becomes
     `sk-ant-***`. Mask any `x-api-key`/`Authorization` header value echoed into the message.
  3. Truncate to **500 characters**, with a trailing `…[truncated]` marker when cut.
  4. Never serialize request content: not `messages`, not the system prompt, not user text.
     `str(exc)` from the SDK carries the response's error body, not the request. The
     implementer verifies that claim against the installed `anthropic` SDK rather than
     trusting this sentence (C-0). If it does not hold, that is a flag.
  5. Put the policy in one small pure helper, `_redact_error_message`, with unit tests for
     each rule. The log stays local-only (charter C-1).
- **C-10 consumer enumeration BEFORE the first edit.** The dossier goes in
  `docs/dev/blast-radius/llm-call-error-capture.md`.
  - The `llm_calls.jsonl` record shape is a shared contract. The invoker's grep of the name
    `llm_calls` hit 48 files, among them `dashboard/routes.py`, `dashboard/__init__.py`,
    `hardening.py`, `blueprints/analysis.py`, `commands/bench.md`, `commands/replay.md`,
    `docs/architecture.md`, `docs/install.md`, `docs/governance/metrics.md` and
    `docs/wiki/pages/diagnostics-console.md`.
  - Re-derive that list grep-complete across every name the record goes by (`LOG_PATH`,
    `_emit_call_log`, `llm_calls`, the field names). Decide each site.
  - The `require-consumer-enumeration` guard is expected to fire on `analyzer.py`, because it
    is on the registry (`scripts/enforcement/blast_radius.py:191`). That is the guard
    working, not a stop.
- **Tests:**
  - an error-path unit test proving the two fields land on an error row and are absent on an
    ok row;
  - the redaction helper's unit tests;
  - a check that existing telemetry tests still pass. Test telemetry must redirect `LOG_PATH`
    (memory `fake-client-tests-must-redirect-telemetry`).
- **CHANGELOG** entry, Unreleased, one line.

**Out of scope, deliberately:**
- **Any dashboard/UI change.** Showing the messages on error-rate rows is C2's UX-8, re-run
  next on top of this sprint. Do not touch `dashboard/routes.py`,
  `dashboard/templates/dashboard.html`, `ui_pages/*`, or the C2 stash.
- Any prompt change. There is no `PROMPT_VERSION` bump, because the telemetry shape is not a
  prompt.
- Error capture for any log other than `logs/llm_calls.jsonl`.
- The non-`Exception` exit paths (`GeneratorExit`/`KeyboardInterrupt`, i.e. a consumer
  closing the stream). If the implementer finds these write misleading rows, **file a work
  item**. Do not fold them in.
- UX-22..UX-41 (items 112, 113), and C1a/C1b's lock and wait-state surfaces.

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** The C2 reviewers
> cited `analyzer.py:1352-1387` at `a66edb7`. Re-derive before relying on it.

## First move

1. Read the epic design brief in full.
2. Re-derive the `_call_llm_streaming` except/finally structure at the tip.
3. Write the C-10 dossier's `## Consumers` section, grep-complete, **before** the first edit
   to `analyzer.py`.
4. Then implement the helper, the two fields, and the tests.

For the **invoking session** (after runbook step 0 preconditions):

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c1c-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 3,
  epicSprintCount: 5,
  nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c2-rerun-brief.md',
  implementerModel: 'sonnet',
}})
```

**For the closer:** the next-sprint brief goes to `epic-c-c2-rerun-brief.md`, a **new
file**. Never overwrite `epic-c-c2-brief.md`, which holds C2's run record. The rerun brief
must:
- point at `epic-c-c2-brief.md` as C2's scope of record;
- state C2's new position: `epicSprintIndex: 4`, `epicSprintCount: 5`,
  `nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c3-brief.md'`, `implementerModel: 'sonnet'`;
- state that UX-8's error-rate rows now **show `error_message`/`error_type`** from the new
  fields. Older rows lack the fields and render as "no message logged".
- state that the invoker restores C2's parked staged work (stash / patch) onto the C2
  branch before invoking. The C2 implementer resumes from that staged diff: it verifies it,
  finishes UX-8 against the new fields, and does not rebuild UX-7 from scratch.

## Decisions taken alone last sprint that this one inherits

- The invoker parked C2's staged diff (7 files, 728+/6−) as `git stash`
  "epic-c C2 staged implementation (wf_697596d4-c2f), parked for C1c". Its backup patch is
  `c2-staged.patch` in the invoker's session scratchpad. Nothing from it is on this branch.
- C2's implementer added `docs/dev/blast-radius/run-detail-modal.md` (for
  `ui_pages/selectors.py`). It is parked with the stash. It is not this sprint's dossier.
- The redaction policy and the implementer model above: both are invoker §11.8 decisions,
  reported at the boundary.

## Open risks handed forward

- **The C2 stash is local-only state** (verified: `stash@{0}`). No pipeline agent may run
  `git stash` commands. A `git stash drop`/`clear` would lose C2's implementation, although
  the scratchpad patch is a second copy.
- **The SDK exception-string content** is inferred, not verified (policy rule 4). The
  implementer verifies it.
- UX-suite flake history: the rerun sweep is mandatory, and a green-after-retries result
  means stop and look (C-7).

## Flag-stop state

The owner resolved C2's escalation by directing this sprint. Nothing else is waiting.

## Gate + verification state

- Last gate: C1b gate #2 at `e7005b2`: `gate: all steps passed.`, 0 `RERUN`.
- Structural pipeline gate this session: 46 passed. Dispatch probe `wf_7f6d3065-0c7`:
  `ok_to_run`.
- Wiki drift: **40 of 75** (2026-09-24). `analyzer.py` is wiki-relevant, so re-check at the
  gate. The backstop is 60.

---

## Close-out obligations this sprint still owes

- **Owed now:**
  - the C-10 dossier;
  - a substantive commit message;
  - the **C2 rerun brief** at `docs/dev/handoffs/epic-c-c2-rerun-brief.md`;
  - work items for anything discovered and not chased;
  - `BOARD.md` regeneration;
  - the invoker's two gate runs with the `RERUN` sweep;
  - the refuter pass.
- **Deferred to epic close:**
  - the wiki pass (unless drift reaches 60);
  - the full `AGENT_HANDOFF_TEMPLATE.md` ceremony;
  - the epic-level adversarial review.

## Invoker run record (C1c)

- Run `wf_9f0c8afe-bf9` (2026-09-24) returned **`escalated_to_owner`**. The **refuter** raised
  a `flag_stop` against itself. It had run `git stash -u` and then `git stash pop` during
  review, which violated this brief's "No pipeline agent may run `git stash` commands". Both
  Opus reviewers returned `escalate` on the C-11 reading: this is a recurrence of the
  agent-stash class (memory `reference-background-bash-kill-ceiling`), and no guard fails
  closed on it.
- The invoker verified the state read-only: `analyzer.py` and `CHANGELOG.md` are now unstaged
  (87+/20−, content intact). The dossier and test are still staged (319+). `stash@{0}` (C2)
  is intact at 7 files, 728+/6−. The closer did not run.
- The refuter's F2 finding: the C-10 dossier's grep counts don't reproduce. It says 19 files
  but lists 21, it omits `tests/test_hardening.py:747`, and it lists
  `tests/test_analyzer_model_selection.py`, which has no match. F3: the code change itself is
  correct.
- Awaiting the owner: (1) the fail-closed guard for agent `git stash`; (2) how C2's parked
  work is protected.
- **Owner directive, 2026-09-24:** "Build the stash guard, move C2 to a wip branch, then resume
  C1c and continue the epic." Done by the invoker:
  - C2 is committed on the local branch `wip/c2-run-detail-modal` @ `12acfc5`, a tree-identical
    copy of `stash@{0}`, which is kept.
  - The guard is `88add1f`: `block-subagent-git-stash`, live in the Bash dispatcher. A
    subagent's state-changing `git stash` now exits 2.
  - `88add1f` is committed, so it is **not** part of C1c's staged diff for review.
  - C1c's CHANGELOG entry also carries the guard's line. That is the one invoker write inside
    the staged diff.
- **Re-run instructions (fresh sprint stage, not `resumeFromRunId`):** C1c's implementation
  is already staged. The implementer verifies it, completes it, and **fixes F2**: re-derive
  the dossier's grep commands and counts without any `git stash`, add
  `tests/test_hardening.py:747`, and drop `tests/test_analyzer_model_selection.py` if it has
  no match. It does not rebuild from scratch.
- **Compaction receipt** in this session's ledger shard at 19:46Z. That is runbook step 9's
  external signal. The invoker finishes C1c, then stops cleanly at the C1c boundary.
