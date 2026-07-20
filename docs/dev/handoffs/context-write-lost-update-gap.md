<!-- provenance: schema=1 session=5583fb3a-6c2c-41a9-bf69-eb8b28c6aa07 branch=fix/context-write-lost-update-gap commit=0116cc2 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-20 -->

# Agent handoff: `fix/context-write-lost-update-gap`

**Branch to create:** `feat/diagnostics-run-cancel` (branch off `main`)
**Base branch:** `main`

---

## Documents to read before any tool call (in this order)
<!-- verbatim -->

1. `docs/dev/RELEASE_ARC.md` — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. `docs/dev/RELEASE_CHECKLIST.md` — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. `docs/dev/AGENT_FAILURE_PATTERNS.md` —
   failure patterns to avoid. Read in full before writing any code.
   **§5f ("Guessing the mechanism") is the expensive one — it is why the
   Binding-rules block below exists.**
4. `docs/governance/charter.md` — the binding
   constitution. **C-7 (evidence before mechanism) and C-8 (durable before
   deep) are enforced by hooks, not by your judgment.**
5. `docs/architecture.md` — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
6. `evals/TUNING_LOG.md` — baseline floors and
   prompt change history.
7. **If this branch is a `fix/*`:** its diagnosis dossier at
   `docs/dev/diagnosis/<branch-slug>.md`, if one exists. It is the durable
   evidence record — what was **observed**, what was **falsified** (do not
   re-chase those; each one cost real money to kill), and what is still only
   **inferred**. The `restore-evidence` SessionStart hook replays it into your
   context automatically, including after a compaction.

---

## Where we are in the arc

**Stream:** step 9 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step specifically.

- ~~`chore/scrub-local-eval-paths`~~ ✓ step 6 (merged; PR #31, `cb68182`)
- ~~`chore/config-drift-batch`~~ ✓ step 7 (PX-47; merged, PR #32, `ad04d27`)
- ~~`chore/hook-dispatcher`~~ ✓ step 8 (PX-37 + kit-adoption commitment 3's hooks half; merged, PR #33, `702d96a`)
- ~~`fix/context-write-lost-update-gap`~~ ✓ step 8b — **unplanned insertion, not in the
  original sequence** (found while researching this branch's own `threaded=True`
  question for step 9). This branch, merge pending your confirmation.
- **`feat/diagnostics-run-cancel`** ← this branch, step 9 — the real abort endpoint
- `docs/diagnostics-content-cluster` ← step 10, next — the remaining `_DASH_HELP` content pass

Do not start anything past step 9 on this branch. In particular, do not fold in the
remaining efficiency-review rows (PX-39, PX-44 refactor half, PX-46) even on overlap —
they are their own owner-gated/scheduled items (see the ledger below).

---

## What just landed on `main`

`main` is at `702d96a` (merge of `chore/hook-dispatcher`, PR #33). **This branch has
not merged yet** — pending your confirmation and the PR flow below; once it does, `main`
will additionally contain this branch's 5 commits (`bd08ac8`, `7206c54`, `82ac505`,
`d1080cf`, `0116cc2`).

**What this branch did.** Started as planning for `feat/diagnostics-run-cancel`
(step 9) — checking whether `app.run(threaded=True)` was safe to consider led to
re-deriving the scope of the earlier `fix/compose-frozen-composition` lost-update fix
and finding it was narrower than its own docstring claimed:

- **Found 5 more context-write sites** sharing the identical unprotected
  read-modify-write shape the 12-site `blueprints/applications.py` fix already closed:
  `blueprints/analysis.py`'s `/api/clarify`, `/api/answer-clarifications`,
  `/api/iterate-clarify`; `blueprints/generation.py`'s `/api/save-edits`,
  `/api/generate-cover-letter`. An adversarial review agent (independently prompted to
  try to refute the finding) confirmed it and found it slightly understated — these 5
  share the same `OUTPUT_DIR/<username>/context_*.json` namespace as the 12
  already-fixed routes, so the real race surface includes cross-contamination with
  those, not just among the 5.
- **Dynamically reproduced before fixing** — the falsification test
  (`tests/test_app_clarify.py::TestConcurrentContextWriters`) failed on HEAD for the
  `/api/clarify` ↔ `/api/answer-clarifications` pairing, promoting the hypothesis to an
  observation per C-7.
- **Fixed all 5** via `hardening.context_transaction`, matching the established
  `applications.py` pattern — delta applied to a freshly-read dict inside the lock,
  never a stale pre-call copy. Two sites needed their merge/append/id-collision logic
  moved inside the lock too, not just the final write.
- **Corrected a related, dated documentation error**: `hardening.py`'s
  `context_transaction` docstring and the original diagnosis dossier both claimed the
  production server runs threaded (`app.run(threaded=True)`) — it never has;
  `threaded=True` appears nowhere in the repo outside a test-only fixture
  (`tests/ux/conftest.py`). `hardening.py` corrected in place; the historical dossier
  got an appended erratum note, not a rewrite.
- **Filed a new carry-forward ledger item** (user-directed): `compliance-witness` has
  no mechanism to catch a docstring making a false code-level claim, or a
  previously-fixed defect class recurring elsewhere — both gaps this session's own
  investigation exposed. Whether to widen the witness's scope is an explicit
  **[OWNER DECISION]**, not decided or implemented here.
- **Full evidence record**: `docs/dev/diagnosis/context-write-lost-update-gap.md`.

**Gate:** `ruff check .` ✓ (315 files) · `ruff format --check .` ✓ · `mypy .` ✓
(330 files) · `pytest -m "not ux"` **2038 passed, 1 skipped** (chunked in 6 batches, all
foreground) · `pytest -m ux` **78 passed** (a11y+flows: 11; regression split into 3
chunks: 24, 42, 43+1). One UX regression test unrelated to this change
(`test_20260708_busy_states_and_chip.py::test_restore_scroll_y_loses_to_post_restore_growth`
— scroll-position-restore mechanics, zero relation to this branch's routes) failed once
inside a large batched chunk and passed cleanly in an isolated re-run — matches the
already-tracked "mode C ~17% under CPU saturation" flake (ledger item, see below), not a
regression; noted rather than silently re-run into a green summary. No stray processes
from this session's own runs (`tasklist` checked before and after).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`); this
is the required one-line-each mirror. **20 open** (re-verified directly via
`grep -c '^- \[ \]'` over the ledger's Open subsection, per the ledger's own stated
source-of-truth convention — **+1 this branch**, the compliance-witness item filed
below; this branch's own lost-update fix does not itself add an open item, found and
fixed within the branch, matching the `fix/handoff-pointer-verification` precedent).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a 64%-broken test for 11 runs.
   Bug fixed; the retry-policy decision is deliberately open pending a real post-fix CI sample.
2. The quality gate is unrunnable by an agent in one shot (~13 min, hard-capped shell commands) —
   worked around by chunking again this session (6 non-UX batches, a11y+flows together, 3 UX
   regression batches). **Read this before running the gate.** No stray-process repro needed —
   `tasklist` came back clean before and after.
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings — modes B/D fixed; mode C (~17%
   under saturation) unfixed. This session's own gate run hit this exact flake class once
   (different test in the same family), confirmed via isolated re-run, not a regression.
5. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
6. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
7. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
8. In-app rendered citation viewer — deliberately deferred.
9. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
10. Agent-coding-practices kit-adoption staged commitments — root `skills/` scaffold landed
    step 8; the `context-structure-review` skill import's external kit source path is the
    remaining open sub-item.
11. 2026-07 efficiency review PX-37..PX-56 — 10 of 13 landed as of step 8; 3 remain: PX-39
    (needs a session with `.api_key` present), PX-44 (refactor half, owner decision point),
    PX-46 (owner-gated memory consolidation).
12. UX round-2 remediation — design-heavy remainder is the unscheduled UX Cohesion Epic.
13. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
14. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
15. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
16. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
17. `block-merge-to-main`'s pre-merge-worktree bug — dissolved by `chore/merge-channel-alignment`;
    entry retained for the lesson.
18. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately not changed.
19. Claude Code CLI sessions/processes don't terminate when closed, forcing manual cleanup
    across projects (owner-reported). Practical mitigation shipped (pre-close sweep checks for
    this); the underlying harness behavior is `[HUMAN/OWNER]`.
20. **NEW this branch**: `compliance-witness` doesn't verify code-level claims
    (docstrings/comments) or re-sweep for recurrence of a previously-fixed defect class —
    both gaps this branch's own investigation exposed (the false "threaded server" docstring
    claim stood uncaught through at least one witness pass; the 5-site recurrence itself is a
    pattern the witness has no mechanism to catch). **[OWNER DECISION]** on whether to widen
    the witness's scope.

**Reduction sprint is badly overdue** — the ceiling is ~8-10 and this is 20.

**Gate-running note (item 2), read before you run it.** Foreground calls survived
reliably where identical backgrounded ones were killed in prior sessions. Chunk from the
start: split `tests/test_*.py` into ~6 batches of ~20 files for the non-UX tier, and
`tests/ux/` by subdirectory (a11y+flows together, then split
`tests/ux/regression/` into ~3 chunks of ~15-16) for the UX tier — this session's
chunking held up cleanly again, though one UX chunk needed a longer-than-default timeout
(real per-test duration under load, not a hang — verified by letting it run to
completion). **Also check for stray long-lived processes first** (`tasklist` or
equivalent) — see item 19 above. Unrelated processes from other projects/the owner's
own browser may appear in `tasklist`; do not touch processes you did not start and do
not recognize.

---

## What this branch should build

This handoff records `fix/context-write-lost-update-gap`'s close-out. Your branch is
**step 9**:

**`feat/diagnostics-run-cancel`** — per `RELEASE_ARC.md` step 9: the real abort
endpoint for a running diagnostics job (owner opted in). Touches run-lifecycle /
threading — **read `docs/dev/reviews/2026-07-diagnostics-round2-findings.md`'s
RUN-LIFECYCLE note first**, before writing any code, since that note is the
authoritative context for what "cancel" needs to mean given how runs are currently
tracked.

**Design direction already settled this session** (researched in depth, presented to
and approved by the user before this branch's scope pivoted to the lost-update fix
instead — re-confirm it still holds, don't re-derive from scratch):

1. **"Disconnect-as-cancel" — no new Flask route, no run registry, no `threaded=True`
   change.** `app.py`'s `app.run()` has no `threaded=True` in any real deployment
   (confirmed exhaustively this session — see this branch's own diagnosis dossier); a
   literal second `POST /cancel` request genuinely cannot be serviced while an SSE
   stream connection is open under that constraint. The cancel signal must travel over
   the SAME already-open SSE connection.
2. A real "Cancel" button (not just tab-close) closes the `EventSource`/aborts the
   `fetch` for the in-flight run. Server-side, each of the 4 SSE routes in
   `blueprints/diagnostics.py` (`annotation_score_grounding`,
   `annotation_bootstrap_stream`, `eval_run_stream`, `tune_run_stream`) switches its
   blocking `events.get()` to a timed poll that periodically attempts a heartbeat SSE
   write; a failed write is the disconnect signal.
3. On disconnect, set a `threading.Event` shared via closure with the worker thread
   (same request — no cross-request state needed). Thread a `cancel_check` into
   `evals/runner.py:run_suite`, `evals/bootstrap.py:run_pipeline_over_jd_texts`,
   `evals/grounding_signals.py:run_grounding_signals`, and the single-fixture path
   backing `annotation_score_grounding` — checked before each paid call
   (analyze/clarify/generate/assemble), stopping early with a distinguishable
   "cancelled" (not "error") outcome. Fully opt-in/backward-compatible for callers that
   don't pass it (the CLI `main()` / eval harness).
4. `tune_run_stream`'s baseline/candidate double-pass needs the same check between and
   within each pass.
5. Known accepted UX limitation: once the connection drops, no confirmation can reach
   the client that cancellation actually took effect — UI goes optimistic
   ("cancelling…"), server logs the cancellation for audit.
6. Re-verify the current diagnostics run-tracking code against `main` before assuming
   the above is still accurate — this handoff's own branch found real drift between
   what an earlier document claimed and current code twice; the lesson generalizes.

Scope is bounded to step 9 in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Create branch `feat/diagnostics-run-cancel` off `main`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

---

## Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)
<!-- verbatim -->

**These are not heuristics, and your judgment does not decide whether they apply
today.** Each one exists because an agent decided it did not apply, and was
expensively wrong. Read them as prohibitions, not as advice.

**1. Evidence before mechanism (charter C-7). If you did not SEE it, you did not
find it.**
- For a defect you cannot reproduce on demand, **the first commit on this branch
  is the instrument or the reproduction — never the fix.** The
  `require-evidence-before-fix` hook blocks production edits on a `fix/*` branch
  until `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section. There is no escape hatch. `docs/**`, `tests/**` and `*.md` stay
  writable, so the way through is always open: **write down what you saw.**
- **Reading code and finding a plausible mechanism is a HYPOTHESIS.** Put it under
  `## Inferred` and label it as unproven. A fix for a real defect that isn't
  **the** defect still leaves the bug — and plausibility is exactly what makes you
  skip the check.
- **Never scope an instrument to the theory you are testing.** It will confirm
  your theory by hiding its rivals. Capture wider than you think you need.
- **Green CI is not evidence if the test needed a retry.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the
  log**.
- If you are not certain **from evidence**, say **"I have not verified this"** and
  **stop**. That sentence is always cheaper than the alternative.

**2. Durable before deep (charter C-8). The context window is not a store.**
- Write a hard-won fact — a measurement, a falsified hypothesis, an observed
  artifact — to its durable home **in the turn you learn it.** Not at close-out.
  The pre-close sweep *reconciles*; it must not *discover*.
- **Compaction is an unannounced data-loss event.** After one, reconcile against
  the repo and git — never continue from a summary as though it were the evidence.
- **A thin context is a handoff trigger, not a push-harder trigger.**

**3. Hooks are not obstacles (see `feedback_hook_discipline`).**
- **NEVER** bypass a hook on your own initiative. Never hand-create the file a hook
  checks for. Never skip a step that has no escape hatch. Escape hatches
  (`CLAUDE_ALLOW_MAIN_EDITS=1`, `CLAUDE_CONFIRM_MERGE=1`) are legitimate **only when
  the user explicitly directs their use** — never on your own judgment.
- If a hook blocks you: **surface the hook name and its message, and STOP.**

**4. Do not declare done. Verify done.** "Done" is the *output* of the pre-close
sweep, not an announcement. See the close-out checklist below.

**5. Corrupted input is a blocked gate (charter C-9).** Damaged, truncated, or
fingerprint-mismatched input is a blocked gate — surface it as your **first
output** and **STOP**; never silently reconstruct, however confident the
reconstruction feels. A `blocked` result from
`scripts/verify_doc_template.py --event consumed` on a handoff you're
consuming is exactly this case — three of the four confirmed silent
handoff-corruption events this rule exists for were an agent reconstructing
damaged text instead of saying so (see
`docs/dev/handoff-integrity-design.md` §2).

---

## Hard constraints (copy verbatim — do not shorten)
<!-- verbatim -->

- Branch before any code edit (`require-feature-branch` hook enforces this)
- Quality gate before every commit: `ruff check .` + `mypy .` + `pytest`
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`
  — `route-security-lint` hook enforces this on `app.py` edits
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, or `pdf_render.py`
- `PROMPT_VERSION` must bump in the same commit as any prompt change
- New dependency = `pyproject.toml` entry + `CHANGELOG.md` entry
- If a hook blocks you: surface the hook name + error, do not bypass,
  wait for authorization
- Do not merge to `main` without explicit user confirmation
- One branch per session — close, merge, hand off before starting the next
- Capture-before-merge: land ALL of this branch's docs / memory / CHANGELOG /
  RELEASE_ARC-CHECKLIST / tracked-deferred / flaky-test captures **before** the merge.
  Never merge then open a follow-up branch for a one-file doc/memory edit — it
  re-triggers the `--no-ff` `.approved` marker-wipe ceremony. If a small item surfaces
  after you'd otherwise merge, the sweep isn't finished: fold it in and re-gate.

---

## Branch close-out checklist (do in this order before closing the window)
<!-- verbatim -->

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified; **any dev server or
   long-lived background process started this session terminated** before closing the
   window (check with `tasklist`/equivalent — an agent's own orphaned processes are
   exactly the failure mode carry-forward ledger item 20 documents). "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Write the next-agent handoff at `docs/dev/handoffs/<branch-slug>.md` from
   this template (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), stamped per
   `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. **Do this ON THIS BRANCH, BEFORE the
   merge** — this is exactly what the Capture-before-merge hard constraint
   above already requires (the handoff is one of this branch's own docs),
   and `require-feature-branch` blocks writing it on `main` once this
   branch is gone, so there is no compliant way to do this step after
   merging.
3. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean); the handoff file from step 2
   must be committed by this point too (its own commit or folded into this
   one — either way, both must exist before step 4)
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER
   the flow.** `main` carries branch protection requiring a pull request plus
   six passing status checks (`strict: true`), so a local merge is rejected
   outright for a non-admin and, for an admin, silently bypasses those six
   checks. Squash and rebase merges are both disabled on the repo, leaving
   **merge commit** as the only method — deliberately: a squash rewrites SHAs
   and orphans the local commits it replaces (it already produced one zombie
   commit, `9f3c800`, before this was understood). Ask the user to confirm,
   then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand
   the user the URL) → **wait for all required checks to go green** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **Pushing is outward-facing on a public repo:** state what will become
   public — including any commits already on your local `main` that the remote
   does not have, since they ride along — and get explicit confirmation before
   the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the
   pointer FIRST**, because it must cite `main`, and pruning a branch a
   pointer still names leaves the next session with an unresolvable
   reference (a correct C-9 halt, but a wasted first move). After the
   `pull --ff-only` in step 4: generate the one-line pointer with
   `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`). Then prune
   (`git branch -d <branch>`; the remote copy is auto-deleted on merge).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
