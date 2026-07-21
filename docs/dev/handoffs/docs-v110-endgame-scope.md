<!-- provenance: schema=1 session=3818aee6-cd80-490a-83c7-698fd5637c24 branch=docs/v110-endgame-scope commit=96aec1d actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-21 -->

# Agent handoff: `docs/v110-endgame-scope`

**Branch to create:** none prescribed — this is another owner-decision fork, same pattern as the branch this one succeeds. The recommended order below is a recommendation, not a schedule.
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

**Stream:** the same owner-decision fork the prior two handoffs described — this branch is a
**pure requirements/scoping refresh**, not a build. No fork item was executed here.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this branch specifically —
this branch only refreshed the documentation the fork already pointed at.

- ~~`feat/rerun-rate-alarm`~~ ✓ (merged, PR #38, `39a6c46`) — rerun-rate alarm
- ~~`test/fixture-scoping`~~ ✓ (merged, PR #39, `96aec1d`) — PX-44 pilot on 2/46 files
- **`docs/v110-endgame-scope`** ← **this branch**. Sourced current verified state (not a prior
  handoff summary) for every remaining fork item and refreshed `RELEASE_ARC.md`'s step 11-17
  sequence + `RELEASE_CHECKLIST.md`'s carry-forward ledger in place. No sequence or decision
  was changed — annotations only, plus a new **Recommended endgame order** subsection and one
  new carry-forward ledger item (below).
- **The fork is otherwise unchanged in shape — every remaining item is still owner-gated or
  condition-gated — but the state under each item is now current:**
  - Step 12 **UNBLOCKED** (was `[NEEDS .api_key PRESENT]`): `perf/real-corpus-baseline` (PX-39)
    — the `.api_key` blocker is cleared, and the data source is updated: the owner has a
    separate E2E clone with genuinely real user data, richer than the current `testuser`
    fixture. Export it via `scripts/export_corpus_seed.py` before running.
  - Step 13 **[OWNER-GATED, no unsolicited scheduling]**: `chore/memory-consolidation` (PX-46)
    — present the keep/consolidate/delete list first; concrete prescription now recorded in
    `RELEASE_ARC.md` step 13.
  - Step 15: `release/visual-assets` + fresh-clone re-verify — screenshots confirmed ~7.5 weeks
    stale; README hero image captured but never wired in; zero periodic coverage stays open.
  - Step 16 **[HUMAN]-only, gates the tag itself**: enumerated concretely (repo public flip,
    PyPI Trusted Publisher, GHCR visibility, CodeQL required check, `enforce_admins`).
  - Step 17: `chore/release-v1.1.0` — exact cut mechanics now recorded (version bump, CHANGELOG
    `[Unreleased]`→`[1.1.0]` rename which activates the D-7.4 disclosure gate, tag).
  - Step 11b **(new, PX-44 follow-on)**: the 46-file fixture-scoping rollout, evidence-backed by
    the `test/fixture-scoping` pilot — owner decides pre-tag vs. post-public.

RELEASE_ARC.md's own text is explicit: "Steps 11/11b/12/13/16 are explicitly owner-gated or
condition-gated, not agent-schedulable in sequence." **Do not pick one of 12/13/16/11b on your
own initiative.** RELEASE_ARC.md now also carries a **"Recommended endgame order"** subsection
(step 12 → step 15 → step 13 → step 11b → step 16 → step 17) — the owner's call to accept or
reorder, not a schedule to execute blind.

**New, not yet scoped — needs its own dedicated design session, do not attempt inline:** the
owner surfaced a non-JD-paired "exemplar resume" that generated real interest outside this
app's own pipeline, and wants to use it (plus the E2E real corpus above) to inform tuning.
Every existing mechanism here is JD-paired (`context_set` assembled per job description); a
real-world success case with no JD to pair against does not fit any existing fixture or
prompt-tuning contract as a drop-in. Filed as a new carry-forward ledger item (below) — the
mechanism (reference exemplar for `callback_likelihood` calibration? a new non-JD-paired tuning
axis? something else?) is genuinely undesigned. **Do not design or implement this blind** —
it needs a conversation with the owner first.

---

## What just landed on `main`

`main` is at `96aec1d` (merge of `test/fixture-scoping`, PR #39). **This branch has not merged
yet** — pending your confirmation and the PR flow below.

**What this branch did.** Pure documentation refresh — no code, no prompt, no test changed.

- Sourced current state directly from `RELEASE_ARC.md`, `RELEASE_CHECKLIST.md`, and the
  working tree (not the incoming handoff's summary), via three parallel read-only Explore
  agents covering release mechanics, PX-39, and visual-assets/PX-46.
- Refreshed `RELEASE_ARC.md` steps 12/13/15/16/17 with concrete, verified current-state detail
  (see "Where we are in the arc" above) and added a new step 11b (PX-44 follow-on) and a
  **Recommended endgame order** subsection.
- Reconciled `RELEASE_CHECKLIST.md`'s PX-39 sub-note (no longer "needs `.api_key` present") and
  filed one new carry-forward ledger item — the non-JD-paired exemplar-resume tuning question
  (open count 18 → 19).
- `CHANGELOG.md` `[Unreleased]` gained a `### Changed` entry summarizing the refresh.
- **Mid-session, the owner surfaced new information not previously in any doc**: a separate E2E
  clone with real user data, and a real resume that generated outside-pipeline interest. Both
  were folded into the refresh (PX-39's data source; the new ledger item) rather than acted on
  directly — see the two notes above.

**Gate:** `ruff check .` ✓ (all checks passed) · `ruff format --check .` ✓ (318 files) ·
`mypy .` ✓ (333 source files, only pre-existing `annotation-unchecked` notes on test bodies,
not errors) · `pytest` — **2179 passed, 1 skipped, 1 failed**
(`tests/ux/regression/test_20260708_review_surface_and_flows.py::
test_editing_experience_dates_refreshes_card_header_rail`, a Playwright `wait_for_selector`
timeout). **Verified NOT a regression from this branch:** this branch touched zero `.py`/`.js`
files (docs-only diff); re-ran the single failing test in isolation
(`pytest <nodeid> -p no:rerunfailures -v`) and it **passed deterministically in 16.58s**; no
stray dev server or background process was found (`tasklist` clean, port 5000 clear) before the
rerun. Matches the class of CPU/load-contention flake already tracked in the carry-forward
ledger (item 1, the unrunnable-gate item) — not a new, distinct flake pattern, so no new ledger
row was filed for it beyond that existing tracking.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **19 open, +1 this branch** (one new item filed —
the exemplar-resume tuning question; nothing else added or resolved).

1. The quality gate is unrunnable by an agent in one shot (~13-18 min, hard-capped shell
   commands) — worked around this session by running it backgrounded via `tee` to a log file,
   then reading/grepping the log (the pipe masked `scripts.gate`'s real exit code — `tee`'s
   exit code, not the gate's, was what the background-task notification reported; worth noting
   for future sessions using this same pattern — check the log's actual `gate: ... (exit N)`
   line, not just the notification).
2. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
3. `test_corpus_reload_preserves_scroll_position` + siblings (settle/restore family) — modes
   B/D fixed; mode C (~17% under saturation) unfixed. CI leg confirmed real (step 14). Not
   touched this branch (out of scope, docs-only).
4. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
5. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
6. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
7. In-app rendered citation viewer — deliberately deferred.
8. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
9. Agent-coding-practices kit-adoption staged commitments — the `context-structure-review`
   skill import's external kit source path is the remaining open sub-item.
10. 2026-07 efficiency review PX-37..PX-56 — 10 of 13 landed; 3 remain: PX-39 (**now
    unblocked**, data source updated to the owner's E2E corpus — not yet run), PX-44 (refactor
    half — piloted on 2/46 files; 46-file rollout filed as step 11b, evidence-backed), PX-46
    (owner-gated memory consolidation — step 13).
11. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
12. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
13. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
14. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
15. `block-merge-to-main`'s pre-merge-worktree bug — dissolved by `chore/merge-channel-alignment`;
    entry retained for the lesson.
16. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately not changed.
17. Claude Code CLI sessions/processes don't terminate when closed, forcing manual cleanup
    across projects (owner-reported); same class corroborated one layer down by the Werkzeug
    reloader orphan finding. `[HUMAN/OWNER]` on the CLI-level behavior itself.
18. `compliance-witness` doesn't verify code-level claims (docstrings/comments) or re-sweep
    for recurrence of a previously-fixed defect class. **[OWNER DECISION]** on whether to
    widen the witness's scope. Not hit or touched this session.
19. **NEW.** A non-JD-paired "exemplar resume" (real callback interest, generated outside this
    app's pipeline) the owner wants to use for tuning, alongside a richer real E2E corpus.
    Every existing mechanism here is JD-paired — this doesn't fit as a drop-in fixture.
    **[OWNER DECISION]**: needs its own dedicated design session to work out the mechanism.

**Reduction sprint is still overdue** — ceiling is ~8-10, this is 19, up one this branch (a
genuinely new item, not scope creep — filing new trailing observations durably is itself a
mandatory pre-close-sweep obligation, distinct from triaging the existing pile, which stays
out of scope until the owner schedules it).

---

## What this branch should build

**Nothing is prescribed.** This handoff is another owner-decision fork, not a "create branch
X" handoff. Every item in the fork (steps 12/13/15/16/11b) needs an explicit owner call before
any branch starts, and the new exemplar-resume item needs a design conversation before any item
is even filed as a candidate branch. `RELEASE_ARC.md`'s "Recommended endgame order" subsection
is the closing agent's recommendation for sequencing IF the owner wants one followed — it is
not authorization to start any of them unprompted.

Scope is bounded to what is listed here. Do not expand beyond it.

---

## First move

**Do not create a branch on your own initiative.** Present the user with the fork above and
the recommended order in `RELEASE_ARC.md`: step 12 (PX-39, now unblocked, data source =
owner's E2E corpus), step 15 (visual-assets refresh), step 13 (PX-46 memory consolidation),
step 11b (46-file fixture-scoping rollout), step 16 ([HUMAN]-only tag gates), step 17 (release
cut) — plus the new, undesigned exemplar-resume tuning question, which needs a conversation
before it becomes a candidate branch at all. If the user directs a specific step, THEN write a
plan at `~/.claude/plans/<slug>.md` and show it before touching any code, per the standard
workflow.

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
