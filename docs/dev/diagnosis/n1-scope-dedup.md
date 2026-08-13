# Diagnosis — the scope default is encoded contradictorily, and the close-out ceremony is a caller decision

> **Status:** root cause PROVEN — for a process defect the committed doc/prompt text IS the
> mechanism, and both defects below are quoted from committed text.
> **Branch:** `fix/n1-scope-dedup`
> **Full investigation record:** [`n1-pipeline-hardening-review.md`](n1-pipeline-hardening-review.md)
> (divergence catalog D0a–D5a, root causes, and the three-reviewer adversarial verdicts that
> selected this branch's fixes).

---

## Symptom

Four epic-run attempts, zero epic-level successes. The two most recent scope-class failures:
run 3's invoker performed a session-terminating close-out after 1 of 3 sprints (item 84, the
tenth failure), and run 4's invoker resolved a records-contradiction by guess and committed a
false "scope reconciliation clean" claim (`git show 97c1338`; the eleventh failure).

## Observed

- **The contradiction is in one committed sentence.** `docs/dev/handoffs/epic-b-design-brief.md:56`:
  "Per-session sprint scope is whatever the owner's invocation message states (default: one
  sprint per session)." — against the SAME paragraph's `:43` ("one sprint per run"), `:48-50`
  ("the license to continue to the next sprint at each boundary per the runbook's epic loop"),
  and `docs/dev/n1-baseline-pipeline.md:254` step 9's default arm ("otherwise: cut the next
  sprint branch off the epic tip and return to step 0").
- **The owner's actual words never said "one sprint per session."** Session `1abaec04`
  transcript, 03:29Z, verbatim: "leave it to the owner's choice fable or opus. if fable can do
  a one sprint and we can get 1/4" — ambiguous, and codified by that session into the
  parenthetical above. The owner's standing directive, session `0e65bffe` 05:42Z, verbatim:
  "this is supposed to be a test to run the entire B epic".
- **Run 4 guessed on exactly this conflict.** `git show 97c1338:docs/dev/work/items/0084-build-n1-baseline-pipeline.md`
  contains "scope reconciliation clean — the epic authorization record and `epic-b-b1b-brief.md`
  name the same unit of work (sprint B1b, one sprint this session, the recorded default)" —
  a false verification claim; the conflict quoted above exists in the files it certifies.
- **The close-out ceremony is a caller-chosen arg with a wrong-for-epics default.**
  `.claude/workflows/n1-baseline.mjs:271` — `closeoutKind: 'terminal'` is the default; a
  sprint-stage caller that omits the arg mid-epic gets the session-terminating full ceremony,
  which is run 3's failure shape replayed (item 84, tenth failure). Nothing derives the
  ceremony from the sprint's position; the invoker decides.
- **CR bytes reappear in working-tree files after checkout-time normalization.**
  `python -c "…count(b'\r')"` on `docs/dev/ledger/0e65bffe-c60d-4127-9558-4d10d2a0d3ad.jsonl`
  (before this branch's cleanup commit normalized it) → 2 CR bytes, while `git check-attr`
  reported `text: set, eol: lf` — post-checkout tool writes are not governed by
  `.gitattributes`, and a CR in `.claude/workflows/*.mjs` is the exact class that rejected the
  run-1 invocation (item 84, first-run entry; probe `wf_e47f2d49-7f0`).
- **A stopped epic is invisible to the next session.** No SessionStart surface mentions epic
  state (`.claude/settings.json:92-103` — the only SessionStart hook is `restore-evidence.sh`,
  which replays a fix-branch dossier); run 3's stopped epic read as running for a day
  (session `01ff2090` transcript: owner approval at 01:54Z, discovery at 03:10Z).

## Falsified

- "Hook-based deterministic gates (Workflow-matcher PreToolUse, blocking Stop hook) are
  buildable now" — falsified by adversarial review against the repo: unmeasured harness
  contracts, a live derivation deadlock (B1a's branch pruned per runbook step 9 itself),
  a finalize-stage hard block, a per-sprint plan-re-approval deadlock, and a repo-wide
  governance-gate restructure. Full verdicts: `n1-pipeline-hardening-review.md`
  §"Adversarial review".
- "Sprint completion can be derived from merged branch refs" — falsified live:
  `git show-ref --verify refs/heads/fix/b1-stale-template-companions` → absent (pruned), yet
  B1a is complete; `epic/b-render-ats` and `fix/n1-invoker-loop` are the same SHA. Committed
  brief-existence at the epic tip is the derivation that survives.

## Inferred

- Deleting the contradictory parenthetical removes run 4's trigger (traced by the minimality
  reviewer against D4a's event sequence: with one consistent encoding, step 0a's
  reconciliation is genuinely clean and no guess occurs). Labeled inference: no live run has
  yet exercised the corrected text.

## The fix (owner-approved plan, 2026-08-13 — survivors of adversarial review only)

S1 delete the poisoned sentence + install the owner-RATIFIED scope sentence as the single
source (epic brief §"Execution mode + authorization record"); superseded-marker on the stale
handoff arm. S2 derive `closeoutKind` in-script from required `epicSprintIndex`/
`epicSprintCount`; reject the caller-supplied form by name (consumer enumeration:
`docs/dev/blast-radius/n1-scope-dedup.md`). S3 CR-byte working-tree assertion over
`.claude/workflows/*.mjs` in the structural suite. S4 SessionStart epic-state banner derived
from committed blobs at the epic tip. S5 log-only measurement hooks in machine-local settings
(no repo surface).

## Acceptance bar

- S2's new structural pins RED at the pre-fix tree, green after; zero reruns.
- S3's checker self-test proves it flags a synthetic CR fixture; green on the real tree.
- S4's banner observed on a fresh session start; `tests/test_governance_hooks_gate.py` green
  with the new hook classified in the existing context category.
- `python -m scripts.gate` fully green on the branch before commit.
- Exactly one scope-default encoding greps in the epic brief + runbook after S1.
