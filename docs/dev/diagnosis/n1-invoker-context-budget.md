# Diagnosis — invoker context degradation + three run-5 method frictions (item 84, method review)

> **Status:** root cause PROVEN for the CRLF ledger class (reproduced live this session);
> the other three clusters are observed run-5 facts whose fixes are report-shape / prompt /
> prose corrections, not causal claims.
> **Branch:** `fix/n1-invoker-context-budget`

---

## Symptom

Run 5 (session `b0769daa`, 2026-08-13) completed sprint B1b through both gates but
stopped at the sprint boundary: the invoking session's own ledger shard gained two
hook-written `compacted` receipts mid-run — the runbook step-9 external degradation
signal, doubly confirmed — one sprint into an intended three-sprint continuous window.
Alongside it, three smaller method frictions recorded in the run-5 evidence: hook-written
CRLF in ledger shards (a recurrence), a closer that skipped judge-ordered work-item
filings, and a runbook prediction about the plan-approval marker that live behavior
contradicts.

---

## Observed

**O1 — CRLF ledger class, 4th+ instance, reproduced live in THIS session (2026-08-14).**
`docs/dev/ledger/c931e519-38cc-4315-a98d-d01af66853b6.jsonl` — written minutes earlier by
this session's own `python scripts/verify_doc_template.py … --event consumed` — carries
exactly **1 CR byte on its single line**:

```
$ python -c "data = open('docs/dev/ledger/c931e519-….jsonl','rb').read(); print(data.count(b'\r'), data.count(b'\n'), len(data))"
CR bytes: 1 | lines: 1 | size: 289
```

Writer code, both sites: text-mode append with `encoding="utf-8"` and **no `newline=`
argument** — `scripts/enforcement/adapters/claude_context_hook.py:218`
(`with shard.open("a", encoding="utf-8") as handle:`) and
`scripts/verify_doc_template.py:245` (`with shard.open("a", encoding="utf-8") as f:`).
Prior instances: the run-5 handoff's Recurrences #1 records the shard "came back CRLF
after the `consumed` event and after each `compacted` append" on 2026-08-13 (twice), and
the S3 dossier (`n1-scope-dedup.md`) records the class live in a ledger shard the same
day. S3's committed test (`tests/test_n1_pipeline.py::TestWorkflowWorkingTreeBytes`,
lines 713–751) sweeps `.claude/workflows/*.mjs` only — no check covers
`docs/dev/ledger/*.jsonl` working-tree bytes.

**O2 — invoker context accumulation (run 5).** Two `compacted` receipts in
`docs/dev/ledger/b0769daa-4696-48ed-90e8-76f1659c3244.jsonl`, timestamped 22:51:12Z
(during gate #1) and 23:08:27Z (during gate #2). Measured loads recorded in
`docs/dev/handoffs/fix-b1-education-render.md`: ~12.3k lines of mandatory kickoff reading
(the 11-doc list) and a sprint-stage run report of ~24k chars landing in the invoker's
chat surface — while the Workflow harness's own `journal.jsonl` already records every
agent's full structured return (`epic-a-chain-design-corrections.md` §16.5.2.3, verified
live on run 3). The §16.1.B accumulation signature (single-sprint sessions: 3, 3
compactions; multi-sprint continuous windows: 11, 14) has now reproduced at the invoker
level. What internal capability was lost is NOT measurable from inside (C-0/C-8) — the
receipts are the whole of the evidence.

**O3 — closer filing divergence (run 5, first instance of this class).** Item 84's run-5
entry #3: the judge's F1 verdict ordered a residual work item filed and the implementer
handed two more findings over; the closer returned `itemsFiled: []` and wrote a false
"deferred-findings list was empty" claim into the b2 brief (amended same day). The
invoker filed items 90/91/92 at the sprint gate. The closer prompt
(`.claude/workflows/n1-baseline.mjs`, Close phase, step 2) names only the judge's
`defer` verdicts as filing obligations; `CLOSER_SCHEMA` has no field reconciling
`itemsFiled` against obligations.

**O4 — plan-stamp late-bind (runs 4–5).** The run-5 handoff records the plan-approval
marker transferring `fix/n1-scope-dedup` → `fix/b1-education-render` →
`epic/b-render-ats` without ever retiring (merged-to-epic ≠ merged-to-main). Runbook
step 9 (`docs/dev/n1-baseline-pipeline.md`) predicts "the plan-approval marker retires
when a branch merges, so expect one marker re-approval per sprint boundary" — the
prediction did not match the observed behavior; the behavior itself was benign.

---

## Falsified

- **"The sprint-internal agents are the compaction load."** No — subagent context dies
  with each agent and never enters the invoker's window; the ~849k subagent tokens of
  run 5 are invisible to it. The invoker's own window load is kickoff reading + tool
  results + reports + waits (O2's measurements). (Arithmetic on measured artifacts, not
  a new experiment.)
- **"Checkout normalization covers the ledger CRLF class."** Falsified by S3's own
  record and O1: `.gitattributes` (`*.jsonl` pinned since `fix/n1-args-guard-hardening`)
  governs checkout; the CR bytes here are written by tools AFTER checkout. Committed
  blobs are clean; the working tree is not.

---

## Inferred

- The Windows text-mode `\n` → `\r\n` translation (`open(..., newline=None)` default)
  is the mechanism behind O1 — held as near-certain (it is documented CPython behavior
  and the only line-ending transform on the write path), but the falsification test
  below is what proves it rather than this paragraph.
- That trimming the run report and the kickoff list will reduce invoker compactions is a
  **hypothesis** — plausible arithmetic on O2's measured loads, verifiable only by a
  future run's receipt count. Stated as such; the changes are justified as removing
  measured dead weight (data already durable elsewhere), not by a promised receipt
  count.

---

## Falsification

**O1 mechanism test (run BEFORE the writer fix):** byte-regression tests that call
`record_compaction` (hook writer) and `append_ledger_event` (verify_doc_template writer)
against a `tmp_path` ledger dir and assert `b"\r" not in shard.read_bytes()`.

- **If they fail on HEAD (Windows):** the text-mode translation is the mechanism; apply
  the `newline="\n"` fix.
- **If they pass on HEAD:** the mechanism is elsewhere (an upstream writer, an editor,
  a git filter); STOP, widen the instrument.

Red run recorded here once executed (see "Acceptance bar").

O3/O4 need no falsification experiment: the fixes are a prompt/schema widening and a
prose correction to match observed behavior — no causal mechanism is being claimed
beyond what O3/O4 directly show.

---

## The fix

1. **O1:** `newline="\n"` on both append sites; renormalize this session's working-tree
   shard (content unchanged, 1 line); extend the CR-byte working-tree sweep to
   `docs/dev/ledger/*.jsonl` (fail-closed: a future hook-written CR fails the gate's
   pytest step). This is the C-11 mechanism the run-5 handoff's Recurrences #1 declared
   owed.
2. **O2:** digest the sprint report at the return boundary (full agent returns stay in
   `journal.jsonl`; `escalations` verbatim text, `accounting`, `status`, `commitSha`
   kept in full) + an invoker-scoped kickoff reading list in runbook step 0a (curation,
   **unenforced** — C-11 declared; the never-delegate-reading line guards the D5a
   paraphrase channel). The deterministic *fix* — fresh invoker per sprint — is a scope-
   sentence decision reserved to the owner at Epic C planning; recorded below, not
   implemented.
3. **O3:** closer prompt widened to enumerate all three filing-obligation sources;
   `CLOSER_SCHEMA` gains required `filingsOrdered`; in-script reconciliation pushes a
   structured warning into the report when `filingsOrdered` outnumbers `itemsFiled` (or
   deferred verdicts exist with `itemsFiled` empty). **Stated limit (C-0):** this catches
   the machine-readable subset and makes the closer's understanding inspectable; the
   run-5 shape (an obligation inside a fix-verdict's prose rationale) remains prompt-
   discipline — a second recurrence demands a real mechanism (C-11).
4. **O4:** runbook step 9's prediction corrected to the observed late-bind behavior.

**Owner decision recorded, NOT implemented (the run-5 handoff's candidate (c), third
option):** whether future epics run per-sprint sessions with a mandatory boundary
handoff, or keep the continuous window with the step-9 tripwire plus these reducers.
Epic B's ratified sentence is untouched (B2 is terminal — the question is moot for this
epic). Recommendation: Epic C's authorization record adopts the choice deliberately at
Epic C planning, weighing O2 (accumulation is unbounded and invisible; handoff loss is
bounded and inspectable) against the per-sprint relaunch cost.

---

## Acceptance bar

- The two byte-regression tests fail on HEAD (red output recorded below) and pass after
  the one-argument writer fixes — 0 reruns.
- The ledger working-tree sweep passes with the renormalized shard and fails on a
  synthetic CR shard (checker self-test, per the `TestWorkflowWorkingTreeBytes`
  discipline).
- `python -m scripts.gate` green with **0 RERUN lines** (a retried pass is not green —
  charter C-7 rule 3).
- This branch's own close-out (`verify_doc_template.py --event generated`) appends to
  the live shard through the fixed writer; a byte-check afterwards shows 0 CR.
- The `.mjs` digest and reconciliation changes pass the structural gate
  (`tests/test_n1_pipeline.py`); their first live exercise is the B2 run — recorded
  plainly, not claimed as run-tested (C-0).

### Red-run record (2026-08-14, on HEAD before the writer fix)

All three new tests failed on HEAD exactly as predicted; the writer-mechanism reds:

```
FAILED tests/test_c12_disclosure_gate.py::TestM3CompactionDisclosure::test_receipt_bytes_are_lf_only
  AssertionError: hook-written receipt carries CR bytes: b'{"event": "compacted", ... }\r\n'
FAILED tests/test_verify_doc_template.py::TestLedger::test_appended_shard_bytes_are_lf_only
  AssertionError: appended ledger row carries CR bytes: b'{"event": "generated", "doc": "x.md", "ts": "t"}\r\n'
```

**Wider-than-expected sweep finding (O5).** The working-tree sweep flagged **81
shards**, not 1. `git ls-files --eol docs/dev/ledger/` explains it: all 87 tracked
shards are `i/lf` (committed blobs clean, consistent with item 84's "0 committed blobs
carry CR" verification), but 79 are `w/crlf` and 1 is `w/mixed` — stale working-tree
materializations from BEFORE the 2026-08-12 `.gitattributes` `*.jsonl` pin (attributes
govern checkout-time only; git does not rewrite existing working-tree files when
attributes change), the mixed one being run 5's shard (LF checkout + CRLF hook
appends). Plus this session's untracked shard = 81. Renormalizing working-tree bytes
`\r\n → \n` is therefore diff-free for every tracked shard.

**Green run (same day, after the two `newline="\n"` fixes + renormalize):** all three
tests plus the checker self-test pass — `4 passed`, 0 reruns. The 81-shard renormalize
staged **zero content delta** for tracked shards (`git diff --cached --stat`: only the
new session shard, 1 insertion) — `git add` after the byte rewrite additionally clears
git's stale normalization state, which `git status` had reported as `M` with an empty
`git diff` (stat-cache recorded against the pre-pin CRLF materialization).

**Live-writer confirmation, arrived early (same day, 00:49:01Z):** during this branch's
own gate run the PreCompact hook appended a REAL `compacted` receipt to this session's
shard through the fixed writer — **0 CR bytes** on the appended line (byte-checked).
The acceptance bar's live check is thereby met by an organic event rather than a
staged one. (The receipt also means this review session itself compacted mid-gate —
announced per C-12, reconciled against the repo; and it is the benign mid-gate drift
class runbook step 4 already documents.)
