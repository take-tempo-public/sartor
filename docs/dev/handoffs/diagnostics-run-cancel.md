<!-- provenance: schema=1 session=508504be-b937-4db1-9ac1-4e2461b4515b branch=feat/diagnostics-run-cancel commit=60fcad4 actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-20 -->

# Agent handoff: `feat/diagnostics-run-cancel`

**Branch to create:** `docs/diagnostics-content-cluster` (branch off `main`)
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

**Stream:** step 10 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step specifically.

- ~~`chore/scrub-local-eval-paths`~~ ✓ step 6 (merged; PR #31, `cb68182`)
- ~~`chore/config-drift-batch`~~ ✓ step 7 (PX-47; merged, PR #32, `ad04d27`)
- ~~`chore/hook-dispatcher`~~ ✓ step 8 (PX-37 + kit-adoption commitment 3's hooks half; merged, PR #33, `702d96a`)
- ~~`fix/context-write-lost-update-gap`~~ ✓ step 8b (unplanned insertion; merged, PR #34, `ec6128a`)
- ~~`feat/diagnostics-run-cancel`~~ ✓ step 9 — **this branch**, merge pending your confirmation
- **`docs/diagnostics-content-cluster`** ← this branch, step 10 — the remaining #2/4/5/6/16
  field-level `_DASH_HELP` authoring pass. **Content-only** — see RELEASE_ARC.md's own
  one-line scope for this step; do not fold in code changes.

Do not start anything past step 10 on this branch. In particular, do not fold in the
remaining efficiency-review rows (PX-39, PX-44, PX-46) even on overlap — they are their
own owner-gated/scheduled items (see the ledger below), and step 11 (`test/fixture-scoping`)
is explicitly an owner decision point, not a branch to start unprompted.

---

## What just landed on `main`

`main` is at `ec6128a` (merge of `fix/context-write-lost-update-gap`, PR #34). **This
branch has not merged yet** — pending your confirmation and the PR flow below; once it
does, `main` will additionally contain this branch's 6 commits (`3ff6b7f`, `43ca8b6`,
`70e9388`, `06d9d15`, `207af60`, `60fcad4`).

**What this branch did.** The owner-opted-in real run-cancel mechanism for diagnostics
(eval/tune/bootstrap/grounding-score) — not just the client-side button-lock that already
shipped:

- **Disconnect-as-cancel, not a literal second route.** `app.run()` has never been
  `threaded=True` (confirmed again this session, `app.py:292` — that flag stays its own
  deliberately-deferred governance decision, unchanged by this branch), so with a
  single-threaded dev server a real second `POST /cancel` couldn't be serviced while the
  original run's SSE connection is open. The cancel signal travels over that SAME
  connection instead. This is a real translation of the findings doc's literal "add a real
  abort endpoint" wording (worked out and approved in the immediately-prior session) — both
  docs now cross-reference this, not a scope deviation.
- **All 4 SSE routes** in `blueprints/diagnostics.py` (`annotation_score_grounding`,
  `annotation_bootstrap_stream`, `eval_run_stream`, `tune_run_stream`) switched their
  blocking `events.get()` to a 5s-timeout poll (yields a heartbeat SSE comment on
  `queue.Empty`), and wrapped the whole generator body in `try/except GeneratorExit` — a
  real disconnect (or the new frontend Cancel button's `AbortController.abort()`) causes
  the next write to fail, Werkzeug tears the generator down, and the handler sets a
  per-request `threading.Event` before re-raising.
- **`run_suite`** (`evals/runner.py`), **`run_pipeline_over_jd_texts`**
  (`evals/bootstrap.py`), and **`run_grounding_signals`** (`evals/grounding_signals.py`,
  zero paid calls — checkpoint only shortens wall-clock) each gained an optional
  `cancel_check: Callable[[], bool] | None = None` param mirroring the existing `progress`
  pattern — additive, every existing caller (production and ~40 test call sites)
  unaffected by default. `run_suite` checkpoints at 6 points per fixture — broader than
  the handoff's literal analyze/clarify/generate list, since the findings doc's own
  wording is "before its next paid Anthropic call," not "before its next fixture."
  `tune_run_stream`'s baseline→candidate double-pass skips the candidate run entirely if
  cancellation lands during baseline.
- **Frontend:** `window.sartorEval.stream()` gained `AbortController` support + a shared
  `wireCancel`/`hideCancel` helper; a Cancel button was added to all 4 run surfaces
  (Quality, Tuning, Bootstrap, Annotate). The bootstrap and grounding-score routes' own
  hand-rolled `fetch`+`getReader` SSE pumps (pre-existing duplication, ~70 lines) were
  folded into `window.sartorEval.stream()` as part of this branch — Cancel needed
  identical wiring in all 4 places anyway. This invalidated a claim in
  `test_20260709_diagnostics_run_lock.py`'s docstring ("NOT window.sartorEval.stream") —
  corrected in the same branch.
- **Known, deliberately out-of-scope gap:** `run_suite`'s `mode="assemble"` branch
  (`_run_assemble_pipeline`, 3 internal paid calls) has NO cancel checkpoints — neither
  diagnostics route ever passes `mode="assemble"`, so this has zero current effect. Would
  need its own `cancel_check` threading if a future route starts using assemble mode.
  Documented in `run_suite`'s own comments; not filed as a carry-forward ledger item
  (zero current reachability, and the ledger is already over-ceiling — see below).
- **Testing technique** for the route-level falsification tests: Flask's test client
  fully drains the SSE generator on `.get_data()`, so a real disconnect is simulated by
  grabbing `resp.response` (the undrained WSGI iterator) BEFORE draining, `next()`-ing
  once (starts the background worker — nothing in a generator runs before the first
  `next()`), then `.close()`-ing it directly — delivers a genuine `GeneratorExit` at the
  generator's suspended point, the same thing Werkzeug does on a real socket disconnect.
  See memory `reference-sse-disconnect-simulation-technique` if you need this pattern
  again for a different SSE route.
- **Full evidence/design record**: `docs/dev/reviews/2026-07-diagnostics-round2-findings.md`'s
  RUN-LIFECYCLE note (updated this branch) + `CHANGELOG.md`'s "Added" entry for this branch.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ (331 files) ·
`pytest -m "not ux"` **2050 passed, 1 skipped** (pre-existing skip; chunked into 6
foreground batches — see the gate-running note below) · `pytest -m ux` **123 passed**
(a11y+flows together: 11; regression split into 3 chunks: 24, 42, 46 — including 2 new
Playwright Cancel-button tests and the 4 new server-side falsification tests, all green).
No stray processes from this session's own runs (`tasklist` checked; the only `node.exe`
processes present were pre-existing Pyright language-server helpers, not mine).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`); this
is the required one-line-each mirror. **20 open**, unchanged by this branch (re-verified via
`grep -c '^- \[ \]'` over the ledger's Open subsection at close-out — this branch's own
run-cancel work advanced the "UX round-2 remediation" checklist row's sub-scope but did not
add or resolve a numbered ledger item, matching the `fix/handoff-pointer-verification`
precedent).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a 64%-broken test for 11 runs.
   Bug fixed; the retry-policy decision is deliberately open pending a real post-fix CI sample.
2. The quality gate is unrunnable by an agent in one shot (~13 min, hard-capped shell commands) —
   worked around by chunking again this session. **This session's chunking hit a NEW wrinkle:
   see the gate-running note below — background bash calls got silently killed ~5-7 min in,
   even after being re-launched; switching to foreground calls with an explicit long timeout
   is what actually worked.**
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings — modes B/D fixed; mode C (~17%
   under saturation) unfixed. Not hit this session.
5. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
6. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
7. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
8. In-app rendered citation viewer — deliberately deferred.
9. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
10. Agent-coding-practices kit-adoption staged commitments — the `context-structure-review`
    skill import's external kit source path is the remaining open sub-item.
11. 2026-07 efficiency review PX-37..PX-56 — 10 of 13 landed; 3 remain: PX-39 (needs a session
    with `.api_key` present), PX-44 (refactor half, owner decision point), PX-46
    (owner-gated memory consolidation).
12. UX round-2 remediation — **this branch closed the run-cancel sub-scope.** The only
    remaining scope is the #2/4/5/6/16 instructional content-cluster full pass —
    **exactly what `docs/diagnostics-content-cluster` (this handoff's target branch) is
    for.** Landing that branch should let this whole ledger item finally move to Resolved.
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
20. `compliance-witness` doesn't verify code-level claims (docstrings/comments) or re-sweep
    for recurrence of a previously-fixed defect class. **[OWNER DECISION]** on whether to
    widen the witness's scope. Not hit or touched this session.

**Reduction sprint is badly overdue** — the ceiling is ~8-10 and this is 20. Item 12
(UX round-2 remediation) is now down to ONE remaining sub-scope (the content cluster) —
landing this handoff's target branch should let it fully resolve, which would be the
single highest-leverage item to clear next.

**Gate-running note (item 2), read before you run it.** This session hit a NEW wrinkle on
top of the already-known chunking need: **background Bash calls (`run_in_background: true`)
got silently killed ~5-7 minutes in, even after being re-launched a second time** — matches
the documented background-kill-ceiling pattern (`reference-background-bash-kill-ceiling`),
but tighter than the previously-observed 5-10 min range. **Foreground calls with an explicit
long `timeout` (e.g. 540000ms) survived reliably** — this is what actually completed the
gate this session; don't trust `run_in_background` for anything gate-sized. Chunk from the
start: split `tests/test_*.py` into ~6 batches of ~20-21 files for the non-UX tier (this
session: 390/375/392/398/275/221 tests per batch, ~2-5 min each), and `tests/ux/` by
subdirectory (a11y+flows together — 11 tests, ~2 min — then split `tests/ux/regression/`
into 3 chunks of ~16 files, ~3-4.5 min each) for the UX tier. **Also check for stray
long-lived processes first** (`tasklist` or equivalent) — see item 19 above.

---

## What this branch should build

This handoff records `feat/diagnostics-run-cancel`'s close-out. Your branch is
**step 10**:

**`docs/diagnostics-content-cluster`** — per `RELEASE_ARC.md` step 10: "the remaining
#2/4/5/6/16 field-level `_DASH_HELP` authoring pass. Content-only." This is the SAME
instructional cluster the round-2 findings doc's "The instructional cluster
(#2/#4/#5/#6/#16), grounded once" section describes
(`docs/dev/reviews/2026-07-diagnostics-round2-findings.md`) — the plumbing already exists
(`_DASH_HELP` in `dashboard.html`, mirrors `_HELP_REGISTRY` via `static/help-modal.js`),
the gap is granularity/content: only 5 per-tab info-circles vs the main app's 18
field-level entries. A small draft down-payment already landed (a handful of tooltips,
per `RELEASE_CHECKLIST.md`'s "UX round-2 remediation" row) — this branch does the FULL
field-level authoring pass, not another partial one.

**Content, not code.** Author `_DASH_HELP` entries per field, following the SAME
established pattern the main app's `_HELP_REGISTRY` already uses (seen-once localStorage,
shared `static/help-modal.js` modal). Read the findings doc's instructional-cluster
section first for the exact granularity gap being closed. Landing this branch should let
`RELEASE_CHECKLIST.md`'s "UX round-2 remediation" ledger item (still open — see item 12
above) finally move to Resolved, since this is its one remaining sub-scope.

Scope is bounded to step 10 in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Create branch `docs/diagnostics-content-cluster` off `main`, write a plan
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
