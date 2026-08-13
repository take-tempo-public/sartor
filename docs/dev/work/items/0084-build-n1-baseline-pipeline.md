```toml
schema = 1
id = 84
kind = "item"
title = "Build the N=1 baseline of the proposed chain-orchestration pipeline, pending owner authorization"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "implementer->refuter->judge->closer as a Workflow script, N=1; provably >= robust as today's process per the design."
```

**What this is.** The smallest buildable version of the architecture proposed
in `docs/dev/epic-a-chain-design-corrections.md` §16: a fresh implementer,
Sonnet refuter, judge, and closer, run for exactly one ordinary sprint (N=1)
as a Workflow script. At N=1 this pipeline **is** the current normal
handoff process, plus the refuter step (proven valuable — caught the item-20
defect — but currently absent from `AGENT_HANDOFF_TEMPLATE.md`) and a real,
correlated audit trail. §16.5.1 argues this is provably at least as robust as
today's process, since the boundary reviewer is still the owner, exactly as
today.

**Explicitly blocked, not merely deferred.** §16.7 names three decision
points for the owner: whether to pursue the design at all; whether, if
pursued, to authorize N=1 as the first step; and — not decided by this item
or implied by its filing — whether to ever widen N past 1, retire or merge
`AGENT_HANDOFF_TEMPLATE.md`, or resume any Epic B chain under the old §11
envelope. This item exists to make the next concrete build step legible and
trackable once authorized, not to authorize it.

## Updates

### 2026-08-13 (Epic B run 5, sprint B1b COMPLETE — first live escalation firing; boundary stop on doubled compaction signal)

Session `b0769daa` (invoker Fable) ran B1b end-to-end through the pipeline:
implementer → refuter → judge → closer → recheck (6 agents, ~849k subagent
tokens, 76 min), status `ready_for_gate` → gate #1 green (0 RERUN) →
finalize `f47b1ed` → gate #2 green (0 RERUN) → ff-merge to epic tip.

**Run evidence, the four firsts/divergences:**

1. **The escalation primitive fired live for the FIRST time** (previously
   `escalations: []` on every run). Refuter flag_stop (§11.6.3, F1
   scope-change candidate) → one independent Opus reviewer → `targeted_fix`,
   verbatim rationale carried end-to-end. The reviewer reproduced,
   reattributed (pre-existing emitter ambiguity, NOT a regression), and the
   run correctly did not stop. Routing behaved exactly as designed.
2. **The derived intra-epic ceremony worked** (S2's first live exercise):
   the closer wrote `epic-b-b2-brief.md` from position args 2-of-3; no
   `closeoutKind` was passed anywhere.
3. **Closer divergence:** the judge's F1 verdict ordered a residual work
   item filed and the implementer handed two more findings for filing; the
   closer's `itemsFiled` was `[]`. The invoker filed items 90/91/92 at the
   sprint gate and regenerated the board. The closer also wrote a false
   "deferred-findings list was empty" claim into the b2 brief (amended,
   dated, same commit as this entry).
4. **Item-87 witness re-armed on a mid-run task notification** (known
   residual) and landed on the INVOKER's main-loop write, not a subagent's —
   consumed with one re-run, no escalation. The step-0a deliberate
   consumption worked for the sprint stage itself.

**Boundary stop (runbook step 9, the one permitted self-judged early stop):**
the session's ledger shard carries TWO hook-written `compacted` receipts
(22:51:12Z during gate #1, 23:08:27Z during gate #2) — the external
context-degradation signal, doubly confirmed. B1b closed cleanly; the
session stops at the boundary rather than continuing degraded into B2.
Resume state: epic tip (this commit's parent `f74c94d` + this docs commit),
`docs/dev/handoffs/epic-b-b2-brief.md`, `docs/dev/n1-baseline-pipeline.md`
step 0. Epic remainder: B2 (`feat/ats-conformance`, 3 of 3, terminal) + the
epic close-out to PR-ready.

### 2026-08-13 (Epic B run 5 — executor session kickoff, invocation record)

Session `b0769daa` — **invoker model: Fable** (the owner's launch choice per
RELEASE_ARC §"Session models", 2026-08-12 amendment; recorded here per that
amendment's per-run requirement). Scope: the ENTIRE Epic B remainder — B1b,
B2, epic close-out to PR-ready — per the owner-ratified scope sentence,
single-sourced in `epic-b-design-brief.md` §"Execution mode + authorization
record" (cited, not restated). Run opt-in: the owner's pointer-delivery
message consuming `docs/dev/handoffs/fix-n1-scope-dedup.md` (its First move
names that message as the opt-in for the entire remainder). Base: epic tip
`9d3bec5` (ff-merge of `fix/n1-scope-dedup` verified); sprint branch
`fix/b1-education-render` cut per the brief. Preflight structural gate:
46 passed, 0 reruns. S5 measurement recording owed this kickoff (first
sprint after the hardening round).

### 2026-08-13 (`fix/n1-scope-dedup`, owner-directed hardening review — NOT a run) — 0-for-4 investigated from source; adversarial review killed the hook-gate proposals; the scope sentence is now owner-ratified and single-sourced

Session `7225a213` (Fable — review/hardening role, no pipeline invocation).
Mandate: independent investigation of all four failed runs from source
(transcripts + git + committed docs, never prior agents' accounts);
deterministic-fix proposals scoped to this pipeline; adversarial review by
three separately invoked Opus agents; owner approval; implement survivors
only. Full record with citations:
`docs/dev/diagnosis/n1-pipeline-hardening-review.md` (now also the durable
citation for the prompt-rewrite corruption instance — "entire epic" silently
became "one sprint" in a task prompt, owner-caught).

**Review verdicts:** the Workflow-matcher invocation-gate hook, the blocking
Stop-hook session-end guard, a new epic-plan JSON, in-pipeline dispatch
probes, and gate receipts were ALL killed (unmeasured harness contracts — the
exact class that cost runs 1–3; a live derivation deadlock against step 9's
own prune; a per-boundary plan-re-approval deadlock; laundering risk on the
scope sentence; scope leaks into shared surfaces). **Implemented survivors
(owner-approved plan, 2026-08-13):** S1 the "(default: one sprint per
session)" sentence — the planted contradiction behind run 4's guess — is
DELETED and replaced by the owner-RATIFIED scope sentence (typed selection at
the checkpoint), single-sourced in `epic-b-design-brief.md` §"Execution mode
+ authorization record"; S2 `closeoutKind` is no longer a caller arg —
`n1-baseline.mjs` derives it from required `epicSprintIndex`/`epicSprintCount`
(red-first: the derivation arm failed on the pre-fix script exactly as
predicted, then 43/43 structural green); S3 a CR-byte working-tree assertion
over `.claude/workflows/*.mjs` (the class was live in a ledger shard this very
day); S4 the SessionStart epic-state banner (context, not a gate) — every
fresh session sees Epic B's remainder derived from committed briefs at the
epic tip, so a stopped epic can never again hide behind a session boundary;
S5 log-only measurement hooks staged in machine-local settings so harness
facts exist before any hook-based control is reconsidered. Stated residue,
unenforced: a sincerely-wrong stop; prompt fidelity outside the repo;
paraphrase of the ratified sentence; escalation routing still never fired
live. Prior cleanup on this branch's base: the run-4 false record corrected
(`43dd351` — "the false claim plus its correction is the honest record") and
the renamed `docs/n1-0for4-analysis` branch folded + pruned. **Item stays
`watching`** — nothing here is run evidence; the next authorized invoker runs
the ENTIRE remaining epic per the ratified sentence.

### 2026-08-12 (Epic B run 2 invoker, sprint B1b) — invocation record: invoker model FABLE (first Fable-invoked run)

Per the 2026-08-12 §"Session models" amendment, recording this run's actual
invoker model: **Fable** (the owner's launch choice for this session; sprint-
internal casting unchanged — implementer Opus, refuter Sonnet, judge Opus per
the epic model table). Preflight batch results: handoff pointer verified and
consumed (fingerprint `c3a4b05c638e`); structural gate 42 passed in 15s; live
dispatch probe `wf_4f4c50e3-102` → `verdict: "ok_to_run"`, both
`sartor:n1-refuter` and `sartor:n1-judge` resolved (4.1s, 67,115 subagent
tokens — at the recorded floor). **The scope reconciliation was reported
"clean" — falsely (the ELEVENTH failure, the scoping class's FOURTH):** the
author resolved a real conflict by guess — the design brief's "(default: one
sprint per session)" against the same record's epic-remainder continue
license and runbook step 9's continue default — planned a boundary stop
after B1b, and was caught by the owner at the first commit attempt, before
kickoff. **The run was aborted: no sprint stage was ever invoked.** The
session's remaining output at owner direction is
`docs/dev/diagnosis/n1-pipeline-0for4-analysis.md` (the 0-for-4 record, the
violated rules enumerated, session-state inventory for the next agent).
Branch base: `epic/b-render-ats` @ `dc2f0cf`; `fix/b1-education-render` cut
from it, zero commits. Run opt-in had been granted via the approved session
plan — that plan's one-sprint scope is superseded by the owner on screen: the
test is the ENTIRE remaining epic in one continuous managed flow.

### 2026-08-12 (`fix/n1-invoker-loop`, the owner-directed polish round) — the TENTH failure named; the invoker loop built; invoker model now the owner's per-run choice

**The tenth failure (the run-3 retrospective recorded nine; this one surfaced
only after the handoff was committed):** the invoking session's job was to
manage the flow across the whole epic — consume each closer-written brief and
continue to the next run — and no committed document said so. The runbook ran
steps 0–8, one sprint, and stopped; the closer prompt hardcoded the
session-terminating full ceremony every sprint (item 89); and the epic-level
authorization ("run the epic as a test") was never reconciled against the
sprint-scoped handoff. Run 3's invoker followed the committed instructions,
performed a single-branch close-out after one sprint of a three-sprint epic,
reported no boundary, and the owner lost a day to a stopped epic that read as
running. **Epic-level score after three attempts: 0/3 — the owner's count, and
the fair one.** All four failure boundaries to date (CRLF, stringified `args`,
bare-name dispatch, invoker scope) are process/harness boundaries; none is the
sprint's subject matter.

**Fixes landed on this branch** (evidence trail:
`docs/dev/diagnosis/n1-invoker-loop.md`, red-first): the runbook's **epic loop
(step 9)** — merge, verify the next brief, **report the boundary immediately**,
context check on external signals, continue or stop cleanly; **step 0a scope
reconciliation** (epic authorization vs sprint brief — surface, never guess;
never re-ask what the record grants); **item 89 fixed** — the closer branches
on `closeoutKind` (intra-epic → `EPIC_SPRINT_BRIEF_TEMPLATE.md`, terminal →
full ceremony); **harness throws → `kind: 'harness_throw'` escalations**
(retro #1 — the boundary class that cost three runs now surfaces verbatim
instead of dying with `escalations: []`); closer self-verifies with the gate's
static steps (retro #2); repo-relative accounting paths (retro #4); the
brief-as-hypothesis rule in the implementer prompt and the sprint-brief
template (retro #5). The owed `epic-b-b1b-brief.md` was authored in the
declared format. Retro #6 (item 58's fingerprint gate) deliberately NOT built
here — a new enforcement surface, deferred with this written reason; item 58
stays watching.

**Owner decisions recorded (2026-08-12, on screen):** the remainder of Epic B
(B1b, B2, epic close + PR) is authorized one sprint per run with the invoker
managing the flow — recorded in `epic-b-design-brief.md` §"Execution mode +
authorization record"; the **invoking-session model is the owner's choice of
Fable or Opus, stated at invocation** — recorded as a dated amendment in
`RELEASE_ARC.md` §"Session models". Record each run's actual invoker model
here when the run happens.

**Item stays `watching`:** escalation routing (reviewers, halt points, and now
the harness_throw boundary) has still never fired live — `escalations: []` on
every run to date. The close condition is unchanged, and the call is the
owner's (`decision_owner = "user"`).

### 2026-08-12 (run 3 resumed, `fix/b1-stale-template-companions`) — THE PIPELINE COMPLETED END TO END; four of five experiment measures now have data

After the namespace fix (`2807979`), `resumeFromRunId: wf_9bb80d14-c94` ran the
pipeline to `status: "ready_for_gate"`. **Every stage executed for the first
time.** 5 agents, 0 errors, 548,436 subagent tokens, 210 tool calls, 2,239,687 ms
(~37 min).

**Resume behaved exactly as designed** — the decisive practical finding. The
implementer replayed from cache (`cached: true`, 0 new tokens) because its
`(prompt, opts)` were untouched; only the refuter call's `opts` changed, so it
and everything downstream ran live. The 22 minutes and 169k tokens of the first
attempt were **not** re-spent. C-0 limit 4 was honored before trusting it: the
cached return was eyeballed in `journal.jsonl` and is a substantive result with
`flags: []`, not a block-description.

| Stage | Dispatch | Model | Tokens | Tools | Duration |
|---|---|---|---|---|---|
| implementer | default | opus | cached | — | — |
| refuter | `sartor:n1-refuter` | claude-sonnet-5 | 131,065 | 67 | 10m30s |
| judge | `sartor:n1-judge` | claude-opus-5[1m] | 70,934 | 15 | 3m13s |
| closer | default | claude-sonnet-5 | 287,935 | 115 | 21m32s |
| refuter-recheck | `sartor:n1-refuter` | claude-sonnet-5 | 58,502 | 13 | 2m04s |

**The adversarial layer did real work — this is the first evidence it functions
inside the pipeline rather than in principle.** The refuter raised two
evidence-cited findings; the judge dispositioned both with reasoning that
engaged the code rather than the summaries:

- **F1 (MED → judged `fix`)** — `companion_stamp_is_current`'s docstring said
  "the sidecar's PRESENCE is the ownership test" while the implementation tested
  *readability*: `_read_sidecar` returned `None` for absent AND corrupt, and both
  mapped to "current". A corrupt sidecar would freeze a companion forever — the
  very class the sprint exists to close, reachable through a trigger the fix
  itself introduced. The judge **narrowed the refuter's severity honestly**
  (degrades to today's behavior, not a new harm) while still landing it
  pre-commit, because leaving it ships a false docstring claim (C-0). It gave
  the closer an exact four-line prescription including the ordering that keeps
  the hot path free of an extra `stat()`.
- **F2 (LOW → judged `defer`)** — no integration test covers the four
  companion-resolution call sites. The judge **reproduced the gap but rejected
  the refuter's "unverified rewrite" characterization**, showing the swap
  provably behavior-preserving by inspection, and deferred because closing it is
  a test-architecture decision (the PDF tests are Playwright-gated and skip in
  the default `pytest`). Filed as item 88.

The closer applied F1 with a parametrized regression test, filed items 88 and
89, regenerated the board, and wrote + validated the handoff. The recheck
cleared F1 and reconfirmed nothing.

**Experiment measures, updated:**

1. **Harness compatibility — discharged.** Every documented mechanism worked
   once the namespace was right: `agentType` dispatch, `phase()` grouping,
   schema-forced returns, `journal.jsonl`, and `resumeFromRunId`'s
   longest-unchanged-prefix caching.
2. **Escalation behavior — STILL UNTESTED after three runs.** `escalations: []`;
   no agent raised a flag of any kind, and the one real failure (the dispatch
   throw) bypassed the primitive entirely because a harness error is not a flag.
   **Do not record this as working.** Nothing has ever traversed
   `routeFlags`/`escalate` in a live run.
3. **Inter-sprint brief sufficiency — partially tested, and it surfaced a
   design defect.** The closer wrote the full `AGENT_HANDOFF_TEMPLATE.md`
   ceremony rather than the lighter `EPIC_SPRINT_BRIEF_TEMPLATE.md` the epic
   declared, because `n1-baseline.mjs`'s closer prompt hardcodes the former
   unconditionally. It followed the machine-sourced instruction, noticed the
   contradiction, and **filed it (item 89) instead of silently resolving it** —
   the behavior the design wants. B1b's fresh cast is the real test of whether
   the artifact suffices.
4. **Run-report/accounting fidelity — PASSES again, 14/14 exact cover.** Second
   consecutive pass, now across four agents' combined writes. Note for whoever
   maintains the check: the implementer reports repo-relative paths and the
   closer absolute ones, so the comparison must normalize before diffing.
5. **Owner interruption count — 2.** The step-0a preflight batch, and the
   dispatch-failure decision. Both were at genuine decision boundaries; neither
   was a question answerable from the repo.

**Two honesty events worth keeping, both from the agents themselves:**

- The **refuter self-disclosed** running `pytest` on four test files, outside
  its sanctioned read-only-Bash allowance, rather than let it pass silently.
  That is C-0 limit 3 of this contract ("the read-only-Bash boundary is
  instruction, not construction") demonstrated live — the boundary held only
  because the agent chose to surface crossing it, exactly as the limit says.
- The provenance ledger records a **`failed` validation at 01:04:21 followed by
  `generated` at 01:04:52** on the same handoff: `verify_doc_template.py`
  rejected the closer's first attempt, it fixed the file and revalidated. The
  failed row survives in the ledger rather than being overwritten.

**Full run-3 retrospective — owner-directed, and the actionable home for the
polish round:** `docs/dev/handoffs/fix-b1-stale-template-companions.md`
§"Run-3 retrospective". It carries the run's cost table (10 agents, 845,591
subagent tokens, ~3.5 h for a 139-line production diff), the nine things that
went wrong, what held, and eight ranked suggestions. **The highest-value one:
a thrown `agent()` kills the workflow OUTSIDE `routeFlags`/`escalate`, which is
why escalation routing is still untested after three runs and why each failure
reached the owner as a bare task notification rather than as verbatim
escalation text.**

**The step-6 assertion has a structural false-positive source: the session's own
provenance ledger.** Gate #1 went green, then the assertion failed on
`docs/dev/ledger/<session>.jsonl` carrying one working-tree-column change. Looked
rather than re-staged: the delta was a single `compacted` receipt appended at
`01:31:20Z` by the `capture-before-compact` PreCompact hook *while the gate ran*.
No content changed. Any gate run long enough to span a compaction can trip this,
and gate runs here are 15-20 minutes. Recorded rather than papered over, with the
handling written into the runbook's step 4 — the honest disposition is that
gate #2 on the committed tree is what actually closes the window, which is the
argument for the two-gate shape that Epic A's one-gate amendment traded away.

**Three compactions occurred in this session** (`01:17:25Z`, `01:31:20Z`,
`02:03:06Z`), each disclosed to the owner when found and each reconciled against
git rather than against recollection (C-8/C-12). None cost a fact: branch,
commit chain, epic tip and `main` all verified unchanged from the repo after
each.

**And the third one exposed a regress the runbook fix does not escape.** It
landed *after* gate #2 went green, dirtying the tree again with one more
`compacted` receipt. Re-gating to cover a hook-written audit row simply gives
the next compaction ~17 minutes to append another — the loop does not converge
on a machine that compacts this often under a long run. The disposition taken
here, stated rather than hidden: the post-gate delta was **one hook receipt plus
one work-item paragraph** (this one), and instead of a fourth full gate the
specific gate steps that could fail on that delta were run directly
(`work_items check`, `check_doc_links`) — every other step is a pure function of
code that did not change. This is a **deliberate, disclosed narrowing of "gate
green," not a claim of one.** It also raises suggestion 7 in the retrospective
from nice-to-have to load-bearing: the assertion needs to exclude the session's
own ledger, or no long run can ever honestly converge.

**The invoking session's gate caught what the closer's self-verification
missed** — an argument for the two-gate shape, not against it. The closer
reported "`ruff check` / `ruff format --check` clean, 24/24 pytest" and
explicitly noted it did not run the full gate; gate #1 then failed at
`mypy .` on `tests/test_docx_to_persona_html.py:488`
(`Item "None" of "Path | None" has no attribute "exists"`) in a test the closer
itself added. Fixed in the invoking session with `assert resolved is not None`.
**A subagent's targeted verification is not a gate**, and the role boundary that
keeps the gate in the main loop is what made this visible.

### 2026-08-12 (run 3, `fix/b1-stale-template-companions`) — FIRST AGENT EVER SPAWNED; C-0 limit 2 FALSIFIED at the refuter

Run `wf_9bb80d14-c94`. **The pipeline spawned a real agent for the first time
in its existence**, the implementer completed a full sprint of work, and the run
then died at the refuter spawn. 2 agents attempted, 1 done, 1 error, 169,429
subagent tokens, 89 tool uses, 1,319,095 ms (~22 min).

**C-0 limit 2 is no longer unverified — it is falsified.** Verbatim:

```
Error: agent({agentType}): agent type 'n1-refuter' not found. Available agents:
claude, claude-code-guide, Explore, feature-dev:code-architect,
feature-dev:code-explorer, feature-dev:code-reviewer, general-purpose, Plan,
sartor:compliance-witness, sartor:eval-judge, sartor:git-flow, sartor:headhunter,
sartor:n1-judge, sartor:n1-refuter, sartor:prompt-archaeologist,
sartor:tune-drafter, sartor:ux-onboarding-designer, sartor:wiki-grounding-auditor,
sartor:wiki-scribe, statusline-setup
```

Bare-name `agentType` dispatch does **not** resolve. The agents exist and are
registered — as `sartor:n1-refuter` / `sartor:n1-judge`, carrying the plugin
namespace `CLAUDE.md` already documents for commands and subagents
(`/sartor:…`, `sartor:…`). The build followed "the repo's subagent-dispatch
convention" as the limit itself said; the convention it needed was the
namespaced one. Sites: `n1-baseline.mjs:384,403,476` (refute, judge,
refuter-recheck) and the structural pin at `tests/test_n1_pipeline.py:323-324`,
which asserts the bare-name counts and so currently pins the defect.

**This is the third invocation-boundary failure in a row, and the pattern is
now the finding.** CRLF at the permission layer, `args` arriving stringified,
and now namespace-qualified agent dispatch — three separate harness-contract
assumptions, each verified only against documentation or repo convention, each
costing a run. None was detectable by `tests/test_n1_pipeline.py`, whose own
stated scope is self-consistency with the design docs, not harness
compatibility. That limit has now been paid for three times.

**What the run nonetheless discharged — experiment measures 1 and 4:**

- **Harness compatibility (measure 1):** `phase()` grouping, `agent()` dispatch
  for the *default* agent type with an explicit `model`, structured-schema
  return, `journal.jsonl`, and the transcript tree all work. What is broken is
  narrower than "the API": bare-name custom `agentType` resolution.
- **Run-report/accounting fidelity (measure 4) — PASSES, first measurement
  ever.** The implementer's `filesWritten` (7 entries) covers
  `git status --porcelain` **exactly**: `CHANGELOG.md`,
  `blueprints/templates.py`, the two dossiers, `docx_to_persona_html.py`,
  `generator.py`, `tests/test_docx_to_persona_html.py`. No unreported tracked
  file; no claimed file absent. The §11.9 check is real, not theoretical.
- **Escalation behavior (measure 2) is still untested** — `flags: []`; the run
  died on a harness throw, which is not routed through the escalation
  primitive at all. A dispatch error is not a flag, so nothing surfaced
  verbatim; the invoking session learned of it only from the task
  notification. Worth noting as a gap in the primitive's coverage.

**Independently verified, not taken on the subagent's word (C-12).** The
implementer reported ruff/mypy clean and 267 passing tests. Re-run in the
invoking session against its staged tree: `ruff check .` all passed;
`ruff format --check .` 354 files formatted; `mypy` clean on all three changed
production files; `pytest tests/test_docx_to_persona_html.py tests/test_pdf_render.py
tests/test_bundled_templates.py -q` → **61 passed**, zero reruns. A batch of
Pyright diagnostics delivered alongside the failure notification reported
`resolve_companion_html` and `html_template_path_for` as undefined in
`blueprints/templates.py` — **a stale mid-edit snapshot**, falsified by the
above and by the definition at `docx_to_persona_html.py:543` with
function-local imports at each call site. Pyright is not in
`scripts/gate.py`; ruff and mypy are.

**Unadjudicated, and the reason this run cannot simply be resumed to
completion without a decision:** the implementer reports that the sprint
brief's specified fix *would not have fixed the bug* — the guard at
`docx_to_persona_html.py:438-444` is never reached on the preview path,
because all four resolution sites call `generate_companion` only when the
companion is **absent**, and a stale companion is present. It widened scope to
add `resolve_companion_html()` and rewire those four sites, citing §11.8
(in-scope-and-small is the implementer's to decide and record). That may well
be correct — it cites a pristine-worktree reproduction at HEAD `acdb737` — but
**the refuter and judge that exist precisely to adjudicate a scope widening
never ran.** The claim is recorded here as the implementer's, unadjudicated.

**Live item-87 sighting, second observed instance.** Writing *this* entry drew
the PAUSE: the task notification announcing the run's failure re-armed the
witness, exactly as the preflight entry below predicted, and the next `Edit`
was refused once and proceeded on the identical retry. The hazard that entry
describes is therefore real and not hypothetical — had the notification landed
while a subagent held the next `Edit`, the pipeline would have converted a
self-clearing witness into `kind: "hook_block"` and stopped the run.

### 2026-08-12 (run 3 preflight, `fix/b1-stale-template-companions`) — the item-87 pause can silently consume itself, and that is what keeps it from killing a run

Preflight for Epic B run 1 attempt 3 surfaced an interaction between the item-87
interrogative witness and this pipeline's escalation routing that **no document
records**, and two observations that bound it. Filed before the run, not after.

**The hazard.** The item-87 pause refuses the first `Edit`/`Write` after each
recorded prompt with exit 2. The implementer is instructed
(`.claude/workflows/n1-baseline.mjs:51-55`) that a hook block is "an immediate
structured return, not a problem to solve" → it returns `kind: "hook_block"` →
`escalate()` (`n1-baseline.mjs:189-191`) short-circuits to `stop` with **no
reviewer spawned**. The implementer's first act is writing the diagnosis
dossier. So a self-clearing, benign witness would have stopped run 1 dead —
the hook built to protect this session killing it.

**Observed (C-7), not inferred.** Both facts come from reading the guard's own
per-session state file at
`%TEMP%/sartor-interrogative-witness/<session_id>.json`:

1. **The pause is consumed *silently* by a call blocked for a different
   reason.** A throwaway `Edit` on this branch surfaced only
   `check-plan-approved.sh`'s `PLAN RETIRED` message — no PAUSE text anywhere —
   yet the state file read
   `{"prompt_seq": 1, "interrogative": false, "witnessed": true}` immediately
   after. Both PreToolUse entries ran; `interrogative_witness.decide()` marked
   `witnessed` before returning its refusal (`guards/interrogative_witness.py:187`),
   and the aggregated message the agent sees can carry another guard's text
   instead. **A consumed pause is therefore not always a visible one.**
2. **Tool-answer turns do not re-arm it.** `prompt_seq` stayed at **1** across an
   `AskUserQuestion` round trip *and* an `ExitPlanMode` approval — a subsequent
   `Edit` was not paused. Only a real `UserPromptSubmit` calls `record_prompt`.
3. **Not every task notification re-arms it either — refining item 87's
   closing claim.** That entry records "task notifications count as
   prompt-receipt events, so long autonomous runs get one pause per
   notification turn." Observed across this session's four background
   notifications, read from the state file each time:

   | # | Notification | Armed? |
   |---|---|---|
   | 1 | run `wf_9bb80d14-c94` FAILED (dispatch throw) | **yes** (`prompt_seq` 1→2) |
   | 2 | probe `wf_d5ab3682-071` completed (6.2s) | **no** (stayed at 2) |
   | 3 | run `wf_9bb80d14-c94` completed (37 min) | **yes** |
   | 4 | gate-waiter background command killed | **yes** |

   So **3 of 4** — the per-notification pause is real but *not* uniform, and
   long-autonomous-run friction is lower than item 87 predicted. Success vs.
   failure is **not** the discriminator (rows 2 and 3 are both successes and
   differ); neither is short-vs-long alone, without more data. Recorded as an
   open question rather than guessed at (C-12). `AskUserQuestion` answers and
   `ExitPlanMode` approvals never arm it — only a real `UserPromptSubmit`
   calls `record_prompt`.

**Consequence, and the mitigation actually used.** The risk is far narrower than
it first looks: the state arms once per user prompt, and the invoking session
can consume it deliberately before the `Workflow` call — which is what happened
here (the base-sha edit to the B1a brief drew the block; the state was already
`witnessed: true` by the time the pipeline was invoked). Residual exposure is a
mid-run **task-notification** turn, which item 87's own closing update records
as a prompt-receipt event. The owner pre-authorized, for that specific case
only, verifying the flag's `verbatim` is exactly the interrogative-witness PAUSE
and resuming via `resumeFromRunId`; any other hook name still stops for the
owner.

**Stated limit (C-0).** Whether subagents share the parent `session_id` — the
premise that makes a subagent able to consume the main agent's pause at all — is
**inherited, not re-derived**: it is asserted as a known limit in
`guards/interrogative_witness.py`'s module docstring (lines 35-37) and was not
verified in this preflight. No agent has been spawned yet, so it remains
untested here too.

### 2026-08-12 (later, `fix/n1-args-guard-hardening`) — both refuter-broken halves hardened; C-11 mechanisms now real

The next session (per the epic handoff's 7-item specification) re-placed the
work on a proper `fix/*` branch with a diagnosis dossier
(`docs/dev/diagnosis/n1-args-guard-hardening.md`) and closed every defect the
three refuters found:

- **args guard rewritten** (`n1-baseline.mjs`): `JSON.parse` in try/catch
  naming `args` (R1-3); empty/whitespace string treated as absent args so the
  required-arg guard names what is actually missing (R1-2); arrays rejected by
  name via `Array.isArray` (R1-4).
- **Regression test rewritten** (`test_args_normalization_tolerates_a_json_string`):
  anchored through `blank_non_code()` so a copy of the block in a comment or
  template literal cannot satisfy it (R2-2); executes the REAL region —
  defaults, normalization, both required-arg guards, nothing hand-supplied
  (R2-3); asserts discriminating error messages per arm, including the
  committed form of the `wf_af5e441a-faa` finalize signal; tautological red arm
  deleted (R2-5). **Mutant-verified in-session: all five acceptance-bar mutants
  fail the test** (guard deleted, Array.isArray deleted, try/catch deleted,
  full revert, revert + template-literal spoof) — the artifact is in the
  dossier. The validation half is now a mechanism, not prose.
- **CRLF half got its mechanism** (the C-11 gap declared in the previous
  entry): `tests/test_gitattributes_coverage.py` asks `git check-attr` for
  every tracked file and fails on any whose text/eol resolution would fall to
  `core.autocrlf` — the pre-pin run enumerated 116 offenders (its own red arm);
  `.gitattributes` now pins them all. Verified: 0 committed blobs carry CR, so
  the pins changed no content and produced no phantom diffs.
- `gate*.log` gitignored (accounting-check noise); `scripts/work_items.py`'s
  false `*.md` claim corrected in place.

Still true and unchanged: **no agent has ever been spawned by this pipeline**
— agentType dispatch, `phase()` grouping, escalation routing, `journal.jsonl`,
and the §11.9 accounting check remain unverified until run 3. Item stays
`watching`.

### 2026-08-12 — FIRST RUN ATTEMPTED (Epic B run 1): blocked at invocation by CRLF line endings

The owner authorized Epic B run 1 (sprint B1a) this session and the pipeline was
invoked for the first time. **It never started** — the `Workflow` tool call was
rejected before any agent spawned:

```
The permission handler returned updatedInput for Workflow that failed schema
validation: path ["script"], message "script contains control characters that
would be hidden in the approval dialog"
```

**Observed (C-7), not inferred.** The permission layer inlines the file named by
`scriptPath` into a `script` field and validates it; a `\r` (0x0D) trips the
control-character check. Established by a deterministic two-arm probe with dummy
scripts that spawn no agents (scratchpad, not committed):

| Arm | Bytes | Only difference | Result |
|---|---|---|---|
| `probe_crlf.mjs` | 143 | CRLF | rejected — **identical** error, `path: ["script"]` |
| `probe_lf.mjs` | 137 | LF | `{"probe":"ok"}`, 0 agents, 60 ms (run `wf_e47f2d49-7f0`) |

A byte scan of `.claude/workflows/n1-baseline.mjs` found **no control characters
other than its 507 CRLF pairs** — CRLF is the whole of the trigger.

**Root cause is a `.gitattributes` gap, not a defect in the pipeline script.**
The committed blob is correct (0 CRLF). `.gitattributes` pins `*.js text eol=lf`
but has **no `*.mjs` rule**, so `.mjs` falls through to `* text=auto`; with this
clone's `core.autocrlf=true`, the file checks out CRLF in the Windows working
tree. `.claude/workflows/n1-baseline.mjs` is the repo's only `.mjs` outside
`docs-site/`, so nothing else surfaced this.

**Experiment results banked (the §"What this experiment measures" list):**

1. **Harness compatibility — partially discharged.** C-0 limit 1 said script
   loading and the Workflow API were unverified. The LF probe proves the harness
   loads a script, honors `meta`, and returns its value. What is *newly* known to
   be broken is narrower and environmental: `scriptPath` + CRLF on a Windows
   checkout.
2. **`agentType` bare-name dispatch (C-0 limit 2) is STILL unverified** — the
   probe spawned 0 agents. Do not record it as tested.

**Scope note:** the fix is a one-line `.gitattributes` addition plus a working-tree
renormalize. That is outside sprint B1a's scope (the companion regen guard), and
it blocks **all three** Epic B runs, not just this one — surfaced to the owner as
a scope decision rather than folded in silently. Owner approved; landed on the
epic branch as `34ad528`.

### 2026-08-12 — SECOND invocation blocker: `args` arrives as a JSON string, not an object

With CRLF fixed, the pipeline was invoked again and failed a second time — still
before any agent spawned (0 agents, 20 ms):

```
Error: args.sprintBriefPath and args.epicBriefPath are required — the pipeline
never invents its own brief
```

**The script is behaving correctly; the harness boundary is not.** `cfg` is built
as `{ ...defaults, ...(args || {}) }` (`n1-baseline.mjs:267`). Spreading a *string*
yields index-keyed characters, so `cfg.sprintBriefPath` is `undefined` and the
guard fires exactly as designed — it refused to invent a brief, which is the
behavior we want.

**Observed (C-7), not inferred.** A dummy probe returning `typeof args` (no agents,
`wf_733613af-2c5`, 14 ms), invoked with a normal object arg:

```json
{"typeofArgs":"string","isString":true,"keys":null,"sprintBriefPath":null,
 "raw":"{\"stage\": \"sprint\", \"sprintBriefPath\": \"docs/dev/handoffs/epic-b-b1a-brief.md\"}"}
```

`args` arrives as a **JSON string** in this environment regardless of how it is
passed. This **contradicts the documented Workflow contract**, which states args
are exposed to the script "verbatim" and warns specifically against passing a
JSON-encoded string because "a stringified list reaches the script as one string."
Here the harness does the stringifying itself.

**Consequence for C-0 limit 1:** the limit said the Workflow API was unverified.
It is now verified in part and *falsified* in part — script loading, `meta`,
`phase`, and return values work; **object-arg marshalling does not match its
documented contract.** Any future script written to that contract has the same
defect. This is a finding about the harness, not about this pipeline.

**Cost of the fix:** one defensive line (`typeof args === 'string' ? JSON.parse(args)
: args`). `tests/test_n1_pipeline.py` contains **no** reference to args handling
(grep-checked: zero matches for `args`, `defaults`, `sprintBriefPath`), so nothing
in the structural gate is coupled to it.

**Still unverified after two attempts: bare-name `agentType` dispatch (C-0 limit 2).**
Both failures occurred before any agent spawned. No sprint work has happened yet.

### 2026-08-12 — both blockers fixed; pipeline PROVEN INVOCABLE; B1a handed to a fresh session

Owner decision this session: apply the fix **and** a regression test, then hand
off rather than continuing into the sprint. Done on `epic/b-render-ats`:

- `.gitattributes`: `*.mjs text eol=lf` + a comment recording why (`34ad528`).
- `n1-baseline.mjs`: `args` is normalized before the spread — a JSON string is
  parsed, a real object still passes through, and a non-object is a loud caller
  error rather than a silent empty config.
- `tests/test_n1_pipeline.py`: a **behavioral** regression test. It lifts the real
  normalization block out of the script and executes it under node with a string
  arg, an object arg, and a RED arm. Shown to fail: with the fix reverted it errors
  with "the args-normalization block is missing from n1-baseline.mjs".

  **CORRECTION (same day, after adversarial review — this entry originally called
  the test "the C-11 fail-closed mechanism this recurrence required"; that claim
  was an overstatement and is withdrawn).** Three independent refuters were run
  against these fixes and all three found real defects. On this test specifically:
  deleting the *validation guard* leaves every assertion green (so the guard half
  does **not** fail closed), and a template literal containing a copy of the block
  makes the test pass while the real script is reverted — because it regexes raw
  source and never routes through this file's own `blank_non_code()` scanner. The
  regex also breaks on 8 of 9 behavior-preserving edits, each emitting a
  confidently-worded and false "block is missing" message. **The parse half is a
  mechanism; the validation half is prose.** Full reports, with the remedies, are
  the appendix of `docs/dev/handoffs/epic-b-render-ats.md`.

  **The CRLF half got no mechanism at all**, and that gap is declared rather than
  left silent (C-11): nothing asserts `.gitattributes` covers the repo's text
  extensions, and **80 `.jsonl`, 12 `.tsx`, and 9 `.ts` files remain unpinned**, so
  a future workflow script authored as `.ts` recreates the identical blocker. This
  is the **third** instance of the class — `scripts/work_items.py:22-26` records a
  prior CRLF/LF bug noting `verify_doc_template.py`'s `fingerprint` "already fixed
  once."

**Invocability verified end-to-end, with zero agents spawned** (`wf_af5e441a-faa`,
13 ms). Invoking `stage: 'finalize'` with both brief paths and no `commitMessage`
now fails on the **`commitMessage`** guard — which sits *after* the args parse —
instead of the `sprintBriefPath` guard. The string arg parsed and both paths
resolved; the script advances past the blocker that stopped it twice.

**What remains unverified (C-0, stated not papered over):** bare-name `agentType`
dispatch for `n1-refuter` / `n1-judge` (limit 2), `phase()` grouping, the
escalation routing, `journal.jsonl` contents, and the §11.9 accounting check.
**No agent has ever been spawned by this pipeline.** The next run is still the
first real test of everything downstream of invocation — do not read "invocable"
as "working".

Item stays `watching`: the closure bar wants first-run evidence, and a run that
never reached its first agent is not that.

### 2026-08-11 — BUILT on `feat/n1-baseline-pipeline`; watching until the first authorized run

The authorized build landed: `.claude/workflows/n1-baseline.mjs` (the pipeline
script — two stages bracketing the invoking session's gate runs, escalation
primitive with a no-reviewer short-circuit for §11.5 halt points and hook
blocks, drift layer inert at N=1 by construction), `agents/n1-refuter.md` +
`agents/n1-judge.md` (read-only role definitions), the contract/runbook at
`docs/dev/n1-baseline-pipeline.md`, and the structural gate
`tests/test_n1_pipeline.py` (29 tests, RED-fixture scanner teeth first).

**Status `watching`, not `closed` — owner decision this session, taken on an
adversarial reviewer's finding:** the structural tests certify
self-consistency with the design docs, not harness compatibility — the
Workflow API the script targets has zero committed instances in this repo and
the script has never been executed (running is its own owner opt-in,
§16.5.2.3). Closing on `verified_by = ["tests/test_n1_pipeline.py"]` would be
exactly the "closure resting on weaker evidence than it claims" pattern the
closure bar exists for. Close when the first authorized run supplies real run
evidence.

### 2026-08-11 — owner resolved §16.7: pursue the design; N=1 baseline authorized

The owner answered §16.7's decision points in-session (branch
`fix/retired-roles-a3-prompt`, asked directly per the pre-Epic-B handoff's
"First move" step 3): **(1) pursue the C+drift design** rather than shelving
it as reference material, and **(2) the N=1 baseline build is authorized** as
the next concrete step. Status flips `blocked` → `open` accordingly. Decision
point (3) is unchanged — nothing here widens N past 1, retires or merges
`AGENT_HANDOFF_TEMPLATE.md`, builds the ledger extension (§16.5.2.2), or
resumes any Epic B chain under the old §11 envelope; each stays its own
later, owner-gated decision. Building the pipeline is a full-session piece of
work and was NOT taken on this branch (this session's one branch is item 75's
fix, per the one-branch-per-session rule) — it is the natural next-session
candidate.

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed as the concrete next-step pointer for the design pass's own
recommendation, `status = "blocked"` from the moment of filing since the
owner's decision has not yet been made.
