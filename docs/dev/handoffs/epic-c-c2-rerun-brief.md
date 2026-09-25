# Epic C sprint brief — C2 rerun: `feat/run-detail-modal` (run 4 of 5)

> Written by C1c's closer (`feat/llm-call-error-capture`), 2026-09-24, from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`, per the epic's declared intra-epic
> sprint-transition cadence (item 89; `epic-b-design-brief.md` §"Close-out intervals",
> restated for Epic C in `epic-c-design-brief.md` §"Close-out intervals") and per this
> sprint's own brief's explicit instruction for the closer
> (`docs/dev/handoffs/epic-c-c1c-brief.md` §"First move" → "For the closer").

**C2's scope of record stays `docs/dev/handoffs/epic-c-c2-brief.md` — read that file in
full first.** This brief only states what changed since it was written: C1c's insertion,
C2's new position, the parked-work restoration, and the new telemetry fields C2's UX-8
now has to work with. It does not restate C2's in-scope/out-of-scope split, standing
context, or first-move instructions — those live in `epic-c-c2-brief.md`.

## Sprint identity

- **Sprint:** C2 (rerun), run 4 of 5 (`epicSprintIndex: 4`, `epicSprintCount: 5`).
  C1c was inserted ahead of it (owner directive, 2026-09-24), moving C2 from run 3 of 4 to
  run 4 of 5 and C3 from run 4 of 4 to run 5 of 5 (terminal).
- **Branch to create:** `feat/run-detail-modal` (same name as the original C2 attempt —
  see "What just landed" for why the branch itself needs re-creating, not just re-entering).
- **Stacked on:** `feat/llm-call-error-capture` — **staged (`git add -A` by this closer,
  not committed).** Per the corrected close ordering
  (`docs/dev/epic-a-chain-design-corrections.md` §11.9.4 / §2), the commit and the full
  gate belong to the invoking session, which runs after this brief is written. HEAD at the
  time of writing is `691a17a` (the C1c invoker's run-record commit); this closer's own
  staged work (analyzer.py, the dossier, the test file, the CHANGELOG entry, `BOARD.md`,
  this brief, item 114, and the wiki log entry) sits on top of it, uncommitted. **The
  invoking session must record the actual C1c commit sha here (or verify it directly)
  before starting C2 — do not start C2 against an uncommitted tip.**
  **Recorded by the C2-rerun invoker (session `d9b0e005`, Opus 5.5, preflight 2026-09-24):**
  C1c committed as `0d480c2`, plus the hook-written ledger commits `90e91b0` and `71d0d17`.
  Gate re-run by this invoker on `epic/c-diagnostics @ 71d0d17`: `gate: all steps passed.`,
  0 `RERUN`. `feat/run-detail-modal` was fast-forwarded `a66edb7` → `71d0d17`, and the parked
  work was restored with `git cherry-pick --no-commit 12acfc5`. The staged result is
  7 files, 728+/6−, and `git diff --cached 12acfc5 --` over those 7 paths is empty.
  **Authoritative copy: `wip/c2-run-detail-modal @ 12acfc5`.** Its tree (`08ce457c`) is
  identical to both the index and working-tree sides of `stash@{0}` (verified directly,
  which closes the open risk below). The stash stays as an undropped backup.
- **Implementer model + effort:** `sonnet`, per `epic-c-design-brief.md` §"Sprint →
  pipeline-run mapping" (RELEASE_ARC §"Session models": C2 = Sonnet). Unchanged from the
  original C2 brief and from C1c's own brief.

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| C2's scope of record | `docs/dev/handoffs/epic-c-c2-brief.md` — **read in full.** In-scope/out-of-scope, first-move instructions, and the original UX-7/UX-8 spec all live there unchanged. |
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md` — **read in full**, including the ratified scope sentence and its 2026-09-24 amendment record (the C1c insertion). |
| Authorization envelope | `epic-c-design-brief.md` §"Execution mode + authorization record", §"Escalation + envelope"; `docs/dev/epic-a-chain-design-corrections.md` §11.4-§11.9 (the envelope C1c itself ran under). |
| Close-out cadence | `epic-c-design-brief.md` §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", the **C2** bullet |
| Why C2 is a rerun, not a fresh start | `docs/dev/handoffs/epic-c-c1c-brief.md` §"What just landed" (the original escalation) and §"Invoker run record (C1c)" (the stash incident and the owner's resolution) |

## What just landed

- **C1a** `150bfb9` and **C1b** `27a1fdc`, plus ledger commit `e7005b2`, are ff-merged into
  `epic/c-diagnostics`. Both of C1b's gates passed (`gate: all steps passed.`, 0 `RERUN`).
- **C2's original run** (`wf_697596d4-c2f`) built UX-7 and a metadata-only UX-8, then
  raised a `flag_stop`: the telemetry record it needed for UX-8 carried no error message.
  The owner directed inserting an error-capture sprint (this is what C1c is) rather than
  continuing C2 against an incomplete record shape.
- **C2's staged implementation was parked, not lost, and then re-parked more durably.**
  Sequence, all `[VERIFIED]` by this closer reading `docs/dev/handoffs/epic-c-c1c-brief.md`
  §"Invoker run record (C1c)" and confirming directly:
  1. The C1c invoker first parked C2's staged diff (7 files, 728+/6−) as `git stash` —
     "epic-c C2 staged implementation (wf_697596d4-c2f), parked for C1c" — with a backup
     patch (`c2-staged.patch`) in the invoker's session scratchpad.
  2. During C1c's review, the **refuter subagent ran `git stash -u` / `git stash pop`
     itself** — a violation of the brief's "No pipeline agent may run `git stash`
     commands." Both Opus reviewers escalated this as a C-11 recurrence (no guard failed
     closed on it) and the run returned `escalated_to_owner` without the closer running.
  3. **Owner directive, 2026-09-24:** *"Build the stash guard, move C2 to a wip branch,
     then resume C1c and continue the epic."* Done by the invoker:
     - C2's parked work is now **committed**, not stashed, on a local branch:
       `wip/c2-run-detail-modal @ 12acfc5` ("wip(epic-c): C2 staged implementation parked
       from run wf_697596d4-c2f (UX-7 + metadata-only UX-8)"), tree-identical to
       `stash@{0}`. I confirmed this directly: `git log --oneline wip/c2-run-detail-modal
       -3` shows `12acfc5` on top of `a66edb7`/`b5fe01b`, and `git stash list` still shows
       `stash@{0}` present as a second copy — **neither has been dropped.**
     - The guard is `88add1f` — `block-subagent-git-stash`, live in the Bash dispatcher
       (already merged into this branch's history; not part of any staged diff).
  4. C1c's implementation then ran cleanly on a fresh sprint stage (not
     `resumeFromRunId`), fixed the refuter's F2 finding (grep re-derivation), and this
     closer applied two further judge-ordered fixes (F1, F2 — see
     `docs/dev/blast-radius/llm-call-error-capture.md` for both corrections, made against
     the staged tree, verified against source line numbers directly, not reused from the
     verdicts' own citations).

**I have not verified** whether `wip/c2-run-detail-modal`'s tree is byte-identical to
`stash@{0}` beyond the invoker's own claim — that check is the invoking session's or C2
implementer's to make before treating either as the source of truth for restoration.

## What this sprint builds

**Unchanged from `docs/dev/handoffs/epic-c-c2-brief.md` — read it for the full UX-7/UX-8
spec, in-scope and out-of-scope lists.** This section states only what's new since that
brief was written.

- **New telemetry fields to build UX-8 against.** `logs/llm_calls.jsonl` rows with
  `status == "error"` now carry `error_type` (exception class name) and a redacted,
  size-capped `error_message` (analyzer.py:1427-1448, via the new
  `_redact_error_message` helper at analyzer.py:604). Rows with `status == "ok"` are
  byte-identical to before — the two keys are absent, not null. **UX-8's error-rate rows
  can now show a real message and error type.** Rows written before this sprint (and any
  `status == "ok"` row) still lack the fields; the C2 implementer should render that as
  "no message logged" or equivalent, not as an empty string or a missing-field error.
- **The implementer resumes from the parked staged diff — it does not rebuild UX-7 from
  scratch.** Before invoking, the invoking session restores C2's parked work
  (`wip/c2-run-detail-modal @ 12acfc5`, or the `stash@{0}` / `c2-staged.patch` copies as a
  fallback) onto the fresh `feat/run-detail-modal` branch. The C2 implementer's first job
  is to **verify** the restored diff still applies cleanly against C1c's tip (analyzer.py
  changed — check for conflicts around `_call_llm_streaming`'s `finally` block, since
  that's exactly what C1c touched) and matches what `epic-c-c2-brief.md` describes, then
  **finish UX-8 against the new fields** rather than re-implementing UX-7.
- **`docs/dev/blast-radius/run-detail-modal.md`** — C2's own consumer-enumeration dossier
  for `ui_pages/selectors.py` — is also part of the parked work. It restores with the rest
  of the diff; the C2 implementer re-verifies it against the current tip rather than
  trusting it unread (C-10's ordering requirement still applies to a restored dossier, not
  just a freshly-written one).

**Out of scope:** unchanged from `epic-c-c2-brief.md`. C1c's own out-of-scope list
(`epic-c-c1c-brief.md` §"Out of scope, deliberately") explicitly named "any dashboard/UI
change... Showing the messages on error-rate rows is C2's UX-8, re-run next on top of this
sprint" — that's this sprint.

## First move

Unchanged from `epic-c-c2-brief.md` §"First move" for the implementation itself. Added
for this rerun specifically:

1. **Before invoking:** the invoking session restores C2's parked work onto a fresh
   `feat/run-detail-modal` branch cut from C1c's committed tip (verify the sha first — see
   "Sprint identity" above), and confirms the restoration is complete (7 files, 728+/6−
   per the invoker's own count) before handing off to the implementer.
2. The C2 implementer verifies the restored diff applies cleanly and still matches
   `epic-c-c2-brief.md`'s spec, paying particular attention to `analyzer.py` (C1c touched
   the exact function C2's UX-8 reads telemetry from).
3. Finish UX-8 against the new `error_type`/`error_message` fields.
4. Everything else per `epic-c-c2-brief.md`'s own "First move".

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c2-rerun-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 4,
  epicSprintCount: 5,
  nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c3-brief.md',
  implementerModel: 'sonnet',
}})
```

## Decisions taken alone last sprint that this one inherits

- **The redaction/size policy** (whitespace collapse → API-key/header masking → 500-char
  truncation with a `…[truncated]` marker) was specified by the C1c invoker under §11.8 and
  is now load-bearing: `error_message` is never raw `str(exc)`. C2's UX-8 renders whatever
  `_redact_error_message` already produced — it does not re-redact or re-truncate.
- **The stash-guard decision** (owner-directed): no pipeline agent — implementer,
  refuter, judge, or closer — may run any state-changing `git stash` command. `88add1f`
  enforces this for subagents via the Bash dispatcher; it does not relax for C2.
- **This closer's two judge-ordered dossier corrections (F1, F2)** are text-only fixes to
  `docs/dev/blast-radius/llm-call-error-capture.md` — no code or test changed as a result.
  They do not affect what C2 inherits functionally, only the accuracy of C1c's own
  dossier's citations and one restored consumer row
  (`tests/test_analyzer_model_selection.py`, decision: no change).

## Open risks handed forward

- **[REPORTED, not independently re-verified by this closer]** The invoker's claim that
  `wip/c2-run-detail-modal @ 12acfc5` is tree-identical to `stash@{0}`. I confirmed both
  exist and are distinct refs; I did not diff their trees against each other.
- **[VERIFIED by this closer]** `stash@{0}` still shows in `git stash list` — it has not
  been dropped. Whoever restores C2's work should decide which of the three copies (wip
  branch / stash / scratchpad patch) is authoritative and say so, rather than assuming.
- **[REPORTED]** The SDK exception-string content claim (rule 4 of the redaction policy —
  `str(exc)` on `anthropic.APIError` carries only the response body, never request
  content) was verified by C1c's implementer against the installed SDK
  (`anthropic==0.88.0`) per the dossier's own "Correction, re-verified" note on the F3
  defer verdict. Not independently re-checked by this closer; treat as reported, not
  reproduced, until someone else re-confirms it.
- **UX-suite flake history:** unchanged from the original C2 brief — the rerun sweep is
  mandatory, and a green-after-retries result means stop and look (C-7).

## Flag-stop state

None. The owner already resolved C1c's escalation (the stash incident) with the directive
that produced this rerun brief. Nothing is currently waiting on the owner for C2's rerun
itself.

## Gate + verification state

- Last gate: C1b gate #2 at `e7005b2` — `gate: all steps passed.`, 0 `RERUN`. C1c's own
  gate has **not yet run** — it belongs to the invoking session, per the corrected close
  ordering, and runs against the committed tree after this closer's staged work (including
  this brief) is committed.
- Structural pipeline gate probe: not re-run by this closer (out of scope — §11.9 reserves
  the gate for the invoking session, not any subagent).
- Wiki drift: **40 of 75** (`python -m scripts.wiki_freshness`, run by this closer,
  2026-09-24) — unchanged from C1c's own brief, since `analyzer.py`'s change isn't
  committed yet. Still well under the 60 backstop; the epic-close wiki pass stands
  deferred. Scoped relevance check for this sprint recorded in `docs/wiki/log.md`
  ("2026-09-24 — scoped close-out relevance check (`feat/llm-call-error-capture`, C1c)").

---

## Close-out obligations this sprint still owes

- **Owed now:**
  - the C-10 dossier (`docs/dev/blast-radius/run-detail-modal.md`, already written by the
    original C2 implementer and parked with the rest of the diff — re-verify it against
    the current tip rather than trusting it stale);
  - a substantive commit message;
  - the **C3 brief** at `docs/dev/handoffs/epic-c-c3-brief.md`;
  - work items for anything discovered and not chased;
  - `BOARD.md` regeneration;
  - the invoking session's two gate runs with the `RERUN` sweep;
  - the refuter pass (this time without any pipeline agent touching `git stash`).
- **Deferred to epic close:**
  - the wiki pass (unless drift reaches 60 — currently 40);
  - the full `AGENT_HANDOFF_TEMPLATE.md` ceremony;
  - the epic-level adversarial review.
