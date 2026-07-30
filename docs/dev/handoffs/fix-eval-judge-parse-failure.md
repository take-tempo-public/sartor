<!-- provenance: schema=1 session=7fa21445-6fb4-46f5-aff4-c32a021d6de5 branch=fix/eval-judge-parse-failure commit=23b916e012cf45f7862d02e173dcc42d697384c1 actor=amodal1 agent=claude-code generated_at=2026-07-29 -->

# Agent handoff: after `fix/eval-judge-parse-failure` (item 12 fix + UX-flake sprint escalation — DONE)

**Branch to create:** `fix/ux-flake-solution-sprint` (branch off `main`) — pending the owner's explicit go, same as every branch below
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

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s
endgame-steps prose (both retained as historical narrative with inline
"MIGRATED to work item N" / "RESOLVED" pointers, not deleted).

**Stream:** v1.1.0 endgame.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`) now
`depends_on = [3, 6, 7, 9, 19]` — item 19 was added this branch, per explicit
owner direction that the UX-flake sprint must land before the v1.1.0 cut.

- ~~`fix/bootstrap-annotation-overwrite`~~ (merged, `aa338d6`) — item 11 fixed
  (bootstrap runs no longer overwrite prior annotation work); filed items
  23-26; closed item 26 as already-satisfied.
- **`fix/eval-judge-parse-failure` (this branch, not yet merged) — DONE.**
  Full detail below. Fixed item 12 (dashboard judge_error handling), then —
  per explicit owner direction after this branch's own gate run surfaced a
  fourth occurrence of an already-tracked UX flake — added a new observation
  to `docs/dev/diagnosis/ux-scroll-position-flake.md` (O-14), updated item 19
  with that evidence, and made item 10 explicitly depend on item 19.
- **`fix/ux-flake-solution-sprint` (recommended next, NOT yet owner-confirmed)**
  — item 19: the UX-suite flakiness solution sprint. This is now the
  strongest candidate given the owner's explicit "must solve before 1.1.0"
  direction this session, but — same as every branch in this arc — present
  the ranked board to the owner and let them confirm before creating the
  branch. Read `docs/dev/work/items/0019-ux-flake-solution-sprint.md` in
  full first: it lists 5 separate candidates (mode-C's own residual, O-13,
  O-12/O-14, and two newly-observed unrelated flakes) that are **explicitly
  not one mechanism** — the item's own body warns against picking a shape
  before reading `docs/dev/diagnosis/ux-scroll-position-flake.md` in full
  and deciding with the owner whether to split it into an epic.
- **Everything else on the board** ← do not start on either of these two
  branches; each board item gets its own branch per the sequencing rule
  above.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is
currently at `aa338d6` (the `fix/bootstrap-annotation-overwrite` merge,
PR #77). This branch's own work, once committed and merged, will be the
next thing to land:

1. **Item 12 fixed.** `dashboard/routes.py`'s `_score_over_time` and
   `_rubric_fixture_heatmap` only checked `isinstance(score, (int, float))`
   — true for the common in-`_grade` `json.JSONDecodeError` path's `score:
   0` — so a Haiku judge call that returned unparseable JSON plotted/colored
   identically to a genuine 0/5 rubric failure on the quality trend chart
   and rubric × fixture heatmap. Both helpers now also check `status !=
   "judge_error"`. Reproduced first (C-7): the cited evidence
   (`evals/results/20260728_164119Z.jsonl`) doesn't exist in this clone
   (`evals/results/` is gitignored), so this session traced the mechanism
   fresh via code reading + two new tests
   (`tests/test_dashboard_routes.py::TestScoreOverTime::test_judge_error_record_excluded_from_trend`,
   `::TestRubricFixtureHeatmap::test_judge_error_record_rendered_as_empty_not_red`),
   confirmed both **fail on unfixed HEAD**, then fixed. Full trace in
   `docs/dev/diagnosis/eval-judge-parse-failure.md`, including a `##
   Falsified` section explaining why `_per_rubric_pass_rate` and
   `evals/runner.py`'s `n_pass`/`n_fail` exit-code gate are deliberately
   **untouched** (already-correct, already-tested pass/fail-only semantics
   — a binary gate has no "why did it fail" distinction to be misled by).
2. **UX-flake sprint (item 19) escalated with new evidence, per explicit
   owner direction.** This branch's own gate run hit
   `test_restore_scroll_y_stale_invocation_overwrites_later_scroll` (item
   19's candidate #3) failing a fourth time. Investigated rather than
   assumed: a `git stash`-based A/B confirmed the failure rate is
   materially unchanged with this branch's entire diff completely removed
   from the tree (1 pass / 3 fail across 4 serial reruns on the clean base
   commit) — ruling out any interaction with the item-12 fix. A process
   check found no orphaned sartor `app.py` process (the specific vector a
   prior occurrence implicated) but did find two unrelated, concurrently
   running `python.exe` processes from a different project (`spolia`) —
   widening the "resource contention" finding to a cross-project load
   vector. Logged as O-14 in
   `docs/dev/diagnosis/ux-scroll-position-flake.md` (plus a header-note
   update); item 19 and item 10 updated accordingly (see below). **Not
   root-caused or fixed this branch** — deliberately deferred to item 19's
   own dedicated branch, per this branch's own scope (item 12 only) and the
   diagnosis doc's established "log, don't re-chase here" discipline.
3. **Item 10 now `depends_on` item 19.** Owner direction, captured this
   session: the UX-flake sprint must be *solved*, not just scheduled
   alongside, before the v1.1.0 cut.
4. **Work item 12 closed** with a resolution citing the fix + evidence.
   Board regenerated (`python -m scripts.work_items board --write`);
   `python -m scripts.work_items check` passes (26 files).

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ · `pytest -m "not ux" -n auto` ✓ ·
`pytest -m ux`** — **2 failures in the full gate run, both pre-existing and
already tracked, confirmed unrelated to this branch's diff:**
`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` (item 19
candidate #3; see point 2 above) and
`test_surgical_refinement_network_failure_surfaces_error_with_retry` (item
19 candidate #5 — passed cleanly on an immediate isolated rerun this
session, the first isolation data point for that candidate). Owner
explicitly directed proceeding to commit/merge given both are
already-documented, already-tracked, evidence-backed pre-existing flakes,
after the O-14 documentation + item 19/10 escalation above landed. **Do not
read this as "the gate was green"** — it was not, on this specific tier,
for reasons fully traced and orthogonal to this branch's own change.
`work_items check` ✓ (26 files, after item 12 closed).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note, this handoff (same as predecessor):** `docs/dev/work/BOARD.md`'s
full Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded, per
"Where we are" above.

**Open (8 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item
   10 (the v1.1.0 cut, alongside item 19 now). Needs the dev server + visual
   review, not just code.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its own
   fixture's annotations. Needs a real heuristic decision in `pick_anchor_jd`.
3. Item 14 — no JD-identifying (name/company) metadata in bootstrap/eval
   artifacts. Only partially touched by item 11 (run provenance added, JD-
   name provenance still missing).
4. Item 15 — suggested-skills rendering bug (comma-split inside
   parentheticals). Reproducible, but the exact call site in
   `suggest_skills`'s output parsing isn't traced yet — some tracing needed
   before it's a pure mechanical fix.
5. Item 19 — **UX-suite flakiness solution sprint — now explicitly blocks
   v1.1.0 (item 10's `depends_on`), per owner direction this branch.** 5
   candidate flakes, not one mechanism — read the item file and
   `docs/dev/diagnosis/ux-scroll-position-flake.md` (through O-14) in full
   before picking a shape.
6. Item 20 — legacy `generate()` reachable via wizard rail without freezing
   Compose (`decision_owner=user`) — needs the owner's product-flow call
   (hard-gate Step 5, or warn/redirect?) before any code.
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry. Its
   own filing calls the fix "mechanical, likely" (route through `_call_llm`
   with a `call_kind`), but touches `analyzer.py`'s LLM-call boundary —
   confirm there's no deliberate reason it skips `_call_llm` before
   rerouting it.
8. Item 22 — 4 call kinds never logged despite real call sites. Needs a
   live click-through per route to distinguish "dead path" from
   "instrumentation gap" before there's anything to fix — investigation,
   not yet a fix.

**Blocked (4):**
9. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR,
   `enforce_admins`).
10. Item 5 — grounding-score persistence gap (blocks calibrated L1/L2
    metric layers).
11. Item 8 — compose-time rewrite dial, still blocked pending owner
    direction on the real evidence channel (likely `/tune-from-annotations`,
    not decided).
12. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` (6
    satisfied; 19 newly added this branch).

**Deferred (4):**
13. Item 4 — in-app citation viewer, no friction signal yet.
14. Item 7 — PX-46 memory consolidation, owner sign-off required first.
15. Item 24 — template-preview fidelity spike (T2), never scheduled; needs
    a product-priority decision before any code.
16. Item 25 — `app.run(threaded=True)` governance decision, deliberately
    deferred across many branches; owner-gated, touches the C-1-sensitive
    loopback-bind area.

**Watching (4):**
17. Item 2 — wordmark sweep, opportunistic only.
18. Item 16 — `evals/runner.py --suite real` non-functional, needs a real
    JD + owner data.
19. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
20. Item 23 — PX-52 analyzer.py split, WATCH disposition, deferred
    post-v1.1.0 (trigger: next major prompt-surface work).

**At 8/10 open — below the W-1.4 reduction-sprint ceiling** (down from the
predecessor handoff's 9, since item 12 closed this branch). 20 total
open+blocked+deferred+watching items (down from 21) — the reduction-pass
flag from the predecessor handoff is now slightly less urgent but still
worth revisiting once item 19 (the next likely branch) resolves, since a
sprint on item 19 may itself close or split several of the items above it.

**No unresolved "still-pending thread" carried from further back** — the
predecessor handoff's note about two possibly-still-open threads (an
owner's "still gathering" UX fixes, and a documentation-only investigation)
was not re-raised this session either. Worth asking the owner directly if
they're not simply resolved by now — this is now the second handoff in a
row carrying this same unresolved question forward unanswered.

---

## What this branch should build

Nothing further — this branch is closed out. The recommended next branch,
`fix/ux-flake-solution-sprint`, should tackle item 19
(`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) — **but confirm
with the owner first**, including whether to split it into an epic (the
item's own body flags this as an open structural question, not a decision
this handoff makes). Read `docs/dev/diagnosis/ux-scroll-position-flake.md`
in full (through O-14) before proposing any approach — its own established
discipline (Observed/Inferred kept strictly separate, F-3's falsification
of "all four modes are one race") applies to every one of item 19's 5
candidates.

Scope is bounded to item 19 only, once confirmed. Do not expand into items
9, 13, 14, 15, 20, 21, or 22 on the same branch — each gets its own branch
per the sequencing rule above.

---

## First move

If the owner confirms item 19 as the next branch: create
`fix/ux-flake-solution-sprint` off `main`, then follow C-7 — do not assume
any of the 5 candidates share a mechanism (the diagnosis doc's own F-3
falsification is exactly this trap for the scroll-family candidates). Pick
ONE candidate to instrument first (item 19's own text suggests it may
already need to become an epic — decide this with the owner before writing
any code) and fill in that candidate's own diagnosis dossier's `##
Observed` section before touching any fix. **Do not code the fix first.**

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
   observations` section above**; branches to prune identified; **this session's
   own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`,
   written on `main` at session start when the incoming handoff pointer was
   consumed) **committed on this branch** — folded into an early commit, never
   left untracked and never given its own dedicated branch/PR (see
   `docs/dev/prov/SPEC.md` §5 step 3); **any dev server or
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
