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
