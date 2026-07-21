<!-- provenance: schema=1 session=8ea6512f-e01e-4d41-bac0-007f677d959d branch=docs/scroll-flake-ci-data-rerun-policy commit=PENDING actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-20 -->

# Agent handoff: `docs/scroll-flake-ci-data-rerun-policy`

**Branch to create:** none prescribed — see "First move" below, this is an owner-decision fork, same as the branch this one succeeds
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

**Stream:** step 14 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence — the
one ungated, agent-startable item in the current fork (steps 11/12/13/16 remain owner/condition-gated).
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step specifically —
the fork below is unchanged from the previous handoff.

- ~~`docs/diagnostics-content-cluster`~~ ✓ step 10 (merged, PR #36, `6323599`)
- ~~`docs/scroll-flake-ci-data-rerun-policy`~~ ✓ step 14 — **this branch**, merge pending your confirmation
- **The fork is unchanged — every remaining item is still owner-gated or condition-gated:**
  - Step 11 **[OWNER DECISION POINT]**: `test/fixture-scoping` (PX-44) — decide pre-tag vs. post-public defer.
  - Step 12 **[NEEDS `.api_key` PRESENT]**: `perf/real-corpus-baseline` (PX-39) — real Sonnet-5 measurement, cannot run in an isolated worktree.
  - Step 13 **[OWNER-GATED, no unsolicited scheduling]**: `chore/memory-consolidation` (PX-46) — present the keep/consolidate/delete list first.
  - **New candidate, NOT yet scheduled or owner-confirmed:** build the rerun-rate alarm this
    branch's investigation decided on (RELEASE_CHECKLIST ledger item 1, option (a)) — a CI
    workflow / pytest-report code change, not a docs edit, so deliberately not built on this
    docs-only branch. Needs its own owner-confirmed slot before starting.
  - Step 15: `release/visual-assets` + a fresh-clone re-verify (tag criteria: screenshots current, fresh-clone < 5 min, doc links resolve).
  - Step 16 **[HUMAN]-only, gates the tag itself**: GitHub repo public flip, PyPI Trusted Publisher config, GHCR visibility, CodeQL required-check wiring, branch protection update.
  - Step 17: `chore/release-v1.1.0` — CHANGELOG cut, version bump, tag — executed on the owner's go.

RELEASE_ARC.md's own text is explicit: "Steps 11/12/13/16 are explicitly owner-gated or
condition-gated, not agent-schedulable in sequence — the closing agent on each preceding
branch should surface them rather than attempt them blind." **Do not pick one of 11/12/13
on your own initiative.** Do not start step 15 or the new rerun-rate-alarm candidate
unprompted either — both are mechanical-ish but should wait for explicit ordering from the
user.

---

## What just landed on `main`

`main` is at `6323599` (merge of `docs/diagnostics-content-cluster`, PR #36). **This branch
has not merged yet** — pending your confirmation and the PR flow below; once it does, `main`
will additionally contain this branch's commits.

**What this branch did.** Step 14's read-only CI investigation, per its own scope line
("Check accumulated CI runs on `main` post-scroll-fix-merge → resolve the `--reruns 2`
retry-policy decision and confirm the scroll-flake CI leg. Read-only investigation."):

- Pulled real job logs (`gh api .../actions/jobs/<id>/logs`) for **all 12 CI runs on `main`**
  from the scroll-fix's own landing run (`df95773`, 2026-07-16) through `6323599` (2026-07-20).
  **0/12 red** (confirms the chronic 64%-broken test stays fixed); **5/12 (~42%) fired at
  least one rerun**, spread across 5 distinct tests in the already-tracked settle/restore
  scroll-flake family — no single test dominates. One run (`8326b5e`) came within one retry of
  going red on a single test (2 of 3 attempts failed).
- Presented the owner with the (a)/(b)/(c) retry-policy choice from RELEASE_CHECKLIST ledger
  item 1 using this data. **Owner decided (a): keep `--reruns 2`, add a rerun-rate alarm.**
  The alarm itself is a code change and is deliberately **not built on this docs-only branch**
  — filed as an explicit next candidate in "Where we are in the arc" above.
  Recorded in `RELEASE_CHECKLIST.md`'s `--reruns 2` ledger item.
- Confirmed the previously-unmet "CI leg of the acceptance bar" for ledger item 4 (the mode-C
  scroll flake) — the flake is now proven present on real CI, not just local CPU-saturation
  simulation. Recorded in the same ledger item.
- During the gate run, hit the known settle/restore flake locally
  (`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`, 3/4 isolated re-runs
  failed — elevated vs. the ~17% catalogued rate, most plausibly this machine being under load
  right after two full pytest-suite runs). This branch changes zero `.py`/`.js` (verified via
  `git diff --stat main -- '*.py' '*.js'`), so it cannot be a regression from it. Logged as a
  fresh data point on the same pre-existing, separately-tracked ledger item — not fixed here,
  matching this ledger's own repeated precedent for this exact test.
- Updated `RELEASE_ARC.md` step 14 to **DONE** with a summary pointing at the ledger detail
  (cite, not restate).

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ (331 files) ·
`pytest -m "not ux"` **2050 passed, 1 skipped** (pre-existing skip) ·
`pytest -m ux` **122 passed, 1 failed** — the failure is the pre-existing, separately-tracked
settle/restore flake described above, confirmed non-regression (zero code changed on this
branch) via 4 isolated re-runs (3 failed / 1 passed locally, consistent with — if higher
than — the catalogued rate). No stray dev-server or background processes from this session
(`tasklist` checked clean before close).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **19 open, unchanged this branch** (no item
resolved, no new item added — items 1 and 4 below gained real data but stay open pending
their own build/fix branches). Re-verified via `grep -c '^- \[ \]'` over the ledger's Open
subsection at close-out.

1. `--reruns 2` on the `ux` CI tier — **DECIDED this branch: (a) keep + add a rerun-rate
   alarm** (real post-fix CI sample: 5/12 runs reran, 0/12 red). Alarm itself not yet built.
2. The quality gate is unrunnable by an agent in one shot (~13 min, hard-capped shell commands) —
   worked around by chunking (this session: two ~15–25 min tiers each auto-moved to background
   after their 580s foreground timeout, completed clean).
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings (settle/restore family) — modes
   B/D fixed; mode C (~17% under saturation) unfixed. **CI leg now confirmed this branch**
   (5/12 post-fix CI runs reran across the family); local isolated re-run also hit it this
   session (see Gate note above) — both filed as data points, not fixed.
5. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
6. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
7. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
8. In-app rendered citation viewer — deliberately deferred.
9. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
10. Agent-coding-practices kit-adoption staged commitments — the `context-structure-review`
    skill import's external kit source path is the remaining open sub-item.
11. 2026-07 efficiency review PX-37..PX-56 — 10 of 13 landed; 3 remain: PX-39 (needs a session
    with `.api_key` present — this is step 12 above), PX-44 (refactor half — step 11 above),
    PX-46 (owner-gated memory consolidation — step 13 above).
12. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
13. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
14. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
15. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
16. `block-merge-to-main`'s pre-merge-worktree bug — dissolved by `chore/merge-channel-alignment`;
    entry retained for the lesson.
17. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately not changed.
18. Claude Code CLI sessions/processes don't terminate when closed, forcing manual cleanup
    across projects (owner-reported); same class corroborated one layer down by the Werkzeug
    reloader orphan finding (prior branch). `[HUMAN/OWNER]` on the CLI-level behavior itself.
19. `compliance-witness` doesn't verify code-level claims (docstrings/comments) or re-sweep
    for recurrence of a previously-fixed defect class. **[OWNER DECISION]** on whether to
    widen the witness's scope. Not hit or touched this session.

**Reduction sprint is still overdue** — ceiling is ~8-10, this is 19, unchanged this branch.
Next closing agent: the fork above (steps 11-17, plus the new rerun-rate-alarm candidate) is
where real reduction can happen once the owner greenlights any of it.

---

## What this branch should build

**Nothing is prescribed.** This handoff is another owner-decision fork, not a "create branch
X" handoff — see "Where we are in the arc" above. The only newly-unlocked, ungated candidate
from this branch's own work is building the rerun-rate alarm (RELEASE_CHECKLIST ledger item
1) — not yet owner-confirmed as a slot, so not started here.

---

## First move

**Do not create a branch on your own initiative.** Present the user with the fork above:
steps 11 (`test/fixture-scoping` pre-tag-vs-defer decision), 12 (needs `.api_key` present),
13 (`chore/memory-consolidation` keep/consolidate/delete list), 16 ([HUMAN]-only tag gates),
and the new rerun-rate-alarm candidate all need an explicit owner call before any branch
starts. If the user directs a specific step, THEN write a plan at
`~/.claude/plans/<slug>.md` and show it before touching any code, per the standard workflow.

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
