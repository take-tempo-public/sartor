# Diagnosis — the N=1 pipeline's args guard is untested prose and its regression test can pass while the pipeline is broken

> **Status:** root cause PROVEN — every defect below reproduced first-hand in this session, not inherited from the refuter reports
> **Branch:** `fix/n1-args-guard-hardening`

---

## Symptom

Epic B run 1 never ran: the N=1 pipeline failed to invoke twice before any agent
spawned (CRLF checkout, then `args` arriving as a JSON string). The previous
session's fixes made the pipeline invocable, but three adversarial refuters
(reports reproduced in `docs/dev/handoffs/epic-b-render-ats.md` appendix) found
the fix's validation half untested and incomplete, and the regression test
spoofable. This branch hardens both, per that handoff's deliverables 1–6.

---

## Observed

All reproduced **in this session** (2026-08-12) by direct experiment against the
committed tree at `fbc2c2b`, before any fix was written:

- **Guard has zero test teeth (R1-1).** Deleting the entire
  `typeof rawArgs !== 'object'` throw (`.claude/workflows/n1-baseline.mjs:276-278`)
  from a copy of the script: the committed test's regex still matches
  (`TEST REGEX STILL MATCHES MUTANT: True`) and the extracted mutant block runs
  green under node with the test's own string-arg arm
  (`mutant block runs green: True`). Every assertion in
  `test_args_normalization_tolerates_a_json_string` passes with the guard deleted.
- **Arrays and null slip the guard (R1-4).** Real committed block, unmutated,
  under node v24: `args='[1,2,3]'` → rc=0, no error at the guard (the array
  spreads index-keyed, exactly the defect class the fix claims to close);
  `args='null'` → rc=0, falls through to defaults.
- **Non-JSON string bypasses the authored error (R1-3).** `args='not json'` →
  `SyntaxError: Unexpected token 'o', "not json" is not valid JSON` — a raw parse
  error that never names `args`, while the block comment at
  `n1-baseline.mjs:267-274` claims a non-JSON string "is surfaced as [a caller
  error]".
- **Empty string produces the wrong diagnostic (R1-2).** `args=''` → throws
  ``args must be an object (or a JSON object string); got string`` — the
  `args.trim() !== ''` carve-out cannot reach its apparent intent (fall through
  to defaults); `''` skips `JSON.parse` and then fails `typeof '' !== 'object'`.
- **The test regexes raw source, bypassing `blank_non_code()` (R2-2).** Read
  directly: `tests/test_n1_pipeline.py:412-415` searches `script_src`, not
  `blank_non_code(script_src)`, though the module ships and RED-tests that
  scanner (`tests/test_n1_pipeline.py:66`) for exactly this spoofing class.
- **The test hand-supplies `defaults` and never executes the real required-arg
  guards (R2-3).** Read directly: the extraction spans only the normalization
  block; `const defaults = { stage: 'sprint' }` is supplied by the test
  (`tests/test_n1_pipeline.py:426`), so the real `defaults` (`n1-baseline.mjs:258-266`)
  and the real guards (`:281-286`) — the code that actually fired during the
  incident — have zero coverage.
- **CRLF class is wider than `.mjs` and has no mechanism (R3-2 / C-11).**
  `git grep -Il $'\r' HEAD` → **0 committed blobs** contain CR; the same command
  against the working tree → **112 files**, because `.gitattributes` leaves
  `.jsonl` (80 tracked), `.tsx` (12), `.ts` (9), `.ini`, `.mako`,
  `.editorconfig`, `.dockerignore`, `Dockerfile`, `LICENSE`,
  `.git-blame-ignore-revs`, and `docs/wiki/.last_ingest_sha` on `* text=auto`,
  which checks out CRLF under `core.autocrlf=true`. Any of these fed to a
  `\r`-rejecting consumer reproduces the Epic B blocker exactly. Nothing in
  `tests/`, `scripts/`, or `.github/` asserts `.gitattributes` coverage.
- **`scripts/work_items.py:22-24` states a false C-0 claim.** It asserts "no
  `*.md` rule in `.gitattributes`"; `.gitattributes:6` has `*.md text eol=lf`
  and `git log -S` dates it to the initial commit `ce150e0` (2026-04-10).

Inherited from the previous session's probes, independently consistent with all
of the above (run ids preserved in work item 84): `wf_733613af-2c5` (harness
delivers `typeof args === 'string'`), `wf_af5e441a-faa` (post-fix invocability),
`wf_e47f2d49-7f0` (LF arm of the CRLF two-arm probe).

---

## Falsified

- **"The committed blobs need renormalizing before pinning."** Dead: `git grep
  -Il $'\r' HEAD` returns zero files — every CR in the tree is a working-tree
  checkout artifact of `* text=auto`. Pinning `eol=lf` for the missing
  extensions rewrites no blob and produces no phantom diff. (This also kills any
  need for a `git add --renormalize` commit.)
- **"The regression test at least pins the parse half against deletion of the
  whole block."** Survives — reverting the whole block does fail the test
  (`match is None`), confirmed by R2's replay. The falsified part is only the
  claim that the test pins the *guard*.

---

## Inferred

- **The harness stringifies `args` unconditionally in this environment.** Two
  probes agree, but only object and absent args were probed; whether a
  future harness version honors the documented verbatim contract is unknown.
  The fix therefore normalizes defensively in both directions (string parsed,
  object passed through) rather than assuming either contract.
- **Whether `args` is the binding name the harness injects is not pinnable by a
  unit test** (R2-3's sharp point). The probes prove it is `args` *today*; a
  harness rename would break the pipeline with no committed test able to catch
  it. Stated as a known limit, not papered over.

---

## Falsification

**Run BEFORE writing the fix — and it was.** The experiment: delete the
validation guard from a copy of the script; if the committed test's regex still
matches and the extracted block still satisfies the test's assertions, the
guard is unprotected prose (C-11) and the test must be rewritten. Executed
2026-08-12 on `fbc2c2b`: **regex matched, block ran green — hypothesis
confirmed.** (Had the test failed on the mutant, the refuter reports would have
been wrong and the rewrite unjustified.)

---

## The fix

1. **`n1-baseline.mjs` args guard rewritten:** empty/whitespace string → treated
   as absent args (accurate downstream "required" error); `JSON.parse` wrapped
   in try/catch re-throwing with `args` named; `Array.isArray` rejected
   explicitly; null still falls through to defaults (the required-arg guard's
   message is accurate for it).
2. **Regression test rewritten:** extraction anchored semantically and routed
   through `blank_non_code()` (offsets are preserved 1:1, so the span found in
   blanked source slices the original); the executed snippet now includes the
   REAL `defaults` block and REAL required-arg guards; behavioral arms for
   string/object/empty/non-JSON/array/null inputs, asserting the *messages*
   so deleting the guard fails the array arm; tautological red arm deleted.
3. **C-11 mechanism for the CRLF class:** `.gitattributes` pins every remaining
   tracked text extension; new `tests/test_gitattributes_coverage.py` asks git
   itself (`git ls-files` × `git check-attr`) and fails closed on any tracked
   file whose `text`/`eol` resolution would fall to `core.autocrlf`.
4. `gate*.log` gitignored; `scripts/work_items.py` false claim corrected.

## C-7 branch-placement decision (handoff deliverable 6)

The previous session made two non-exempt edits (`.gitattributes`,
`n1-baseline.mjs`) on `epic/b-render-ats`, where `require-evidence-before-fix`
does not fire; on a `fix/*` branch both would have been blocked pending this
dossier, which did not then exist. **Decision, recorded rather than left
unnamed:** the *evidence standard* was met (three run ids, a two-arm probe, a
RED arm) but the *gate* that proves it was bypassed by branch topology. This
branch re-places the work correctly: it is a `fix/*` branch, this dossier exists
before any production edit, and every claim above is either reproduced
first-hand or cited to a preserved run id. Epic-branch placement for tooling
fixes is NOT endorsed as precedent — the pipeline's own design brief warned it
silently downgrades C-7 to advisory, and it did.

---

## Acceptance bar

- New test fails on each of these mutants (verified by in-session mutant runs,
  not by assumption): validation guard deleted; `Array.isArray` check deleted;
  try/catch around `JSON.parse` deleted; whole block reverted to the pre-fix
  spread; block copied into a template literal while the real code is reverted.
  **Run 2026-08-12 against the rewritten test — all five killed:**

  ```
  guard-deleted                          -> FAILED (good)
  isarray-deleted                        -> FAILED (good)
  trycatch-deleted                       -> FAILED (good)
  reverted-to-prefix-spread              -> FAILED (good)
  revert-plus-template-literal-spoof     -> FAILED (good)
  original restored: True
  ```
- `tests/test_gitattributes_coverage.py` fails when any pin is removed and
  passes on the pinned tree; zero phantom diffs after pinning (`git status`
  clean).
- Full gate green with zero retries: `python -m scripts.gate`, watched to its
  own terminal line (`gate: all steps passed.`), never inferred from a
  mid-run log.
