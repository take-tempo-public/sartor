<!-- provenance: schema=1 session=bfdd068a-3db7-4030-ac55-0536edc35492 branch=chore/ux-flake-epic-split commit=56d250e actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-29 -->

# Agent handoff: after `chore/ux-flake-epic-split` (item 19 promoted to an epic, 5 children filed — DONE)

**Branch to create:** `fix/ux-mode-c-scroll-residual` (branch off `main`) — pending the owner's explicit go, same as every branch below
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
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` (unchanged this branch) — item 19 is now an
epic that cannot close until ALL of items 27-31 close, so item 10 is
transitively gated on all five new children, not just the umbrella.

- ~~`fix/eval-judge-parse-failure`~~ (merged, `94d7e26`) — item 12 fixed
  (dashboard judge_error handling); escalated item 19 with O-14 evidence;
  made item 10 explicitly depend on item 19.
- **`chore/ux-flake-epic-split` (this branch, not yet merged) — DONE.**
  Full detail below. Per explicit owner direction, promoted item 19 from a
  single item bundling 5 flake candidates into `kind = "epic"`, and filed
  items 27-31 — one per candidate — so each gets its own independent C-7
  evidence trail instead of being chased as one sprint.
- **`fix/ux-mode-c-scroll-residual` (recommended next, NOT yet
  owner-confirmed)** — item 27
  (`docs/dev/work/items/0027-mode-c-scroll-residual.md`): the mode-C
  smooth-scroll residual (`_wizardRender`'s smooth-scroll racing
  `refreshCorpus`'s scroll baseline read, ~17%/attempt). Recommended because
  its mechanism is already the best-understood of the 5 candidates — see
  `docs/dev/diagnosis/ux-scroll-position-flake.md`'s Inferred §3 and
  Acceptance-bar section — but it was explicitly scoped OUT of the O-10/O-11
  fix and has never itself been fixed. **That existing mechanism write-up is
  still a hypothesis from a shared, multi-mode document — not a dedicated
  capture for this specific candidate.** Confirm with the owner before
  creating the branch, same as every branch in this arc.
- **Everything else on the board** ← do not start on either of these two
  branches, and do not start on any of items 28, 29, 30, or 31 either; each
  board item (including each of the epic's other 4 children) gets its own
  branch per the sequencing rule above.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is
currently at `94d7e26` (the `fix/eval-judge-parse-failure` merge, PR #78).
This branch's own work, once committed and merged, will be the next thing
to land:

1. **Item 19 promoted to `kind = "epic"`.** `refs` trimmed to the shared
   diagnosis doc only (per-test-file refs moved to the relevant child);
   `summary` rewritten to describe the umbrella role; a dated `## Updates`
   entry documents the split and why (owner direction, this branch).
2. **Items 27-31 filed**, one per original candidate: 27 = mode C's own
   residual, 28 = O-13 (`loadComposition` scroll-restore call site, one
   sample), 29 = O-12/O-14 (the O-10 regression test itself failing under
   resource contention — 4 occurrences, the most evidence of any candidate,
   still not root-caused), 30 = keyboard-reorder timeout (one sample, no
   diagnosis yet), 31 = network-retry assertion flake (one sample plus one
   clean isolated rerun, no diagnosis yet). Each: `epic = 19`,
   `decision_owner = "agent"`, `status = "open"`, refs to the diagnosis doc
   and/or its own specific test file(s).
3. **Board regenerated** (`python -m scripts.work_items board --write`);
   `python -m scripts.work_items check` passes (31 files).
4. **This session's own `consumed`-event provenance-ledger file**
   (`docs/dev/ledger/bfdd068a-3db7-4030-ac55-0536edc35492.jsonl`, for the
   incoming `fix/eval-judge-parse-failure` handoff pointer) committed on
   this branch.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
`pytest -m "not ux" -n auto` — 2107 passed / 1 skipped ·
`pytest -m ux` — 129 passed / 1 xfailed / 1 xpassed · `work_items check` ✓
(31 files).** Genuinely clean this run, no reruns needed — notably, both
flakes that hit the *previous* branch's gate run (item 29's candidate,
`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`, and item
31's candidate, `test_surgical_refinement_network_failure_surfaces_error_with_retry`)
passed clean here. That is one more isolated-clean data point for each, not
a resolution — do not read it as "the flake is gone," per this document's
own C-7 discipline; log it on the relevant child item if picking either one
up next.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note, this handoff (same as predecessor):** `docs/dev/work/BOARD.md`'s
full Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded, per
"Where we are" above.

**⚠ Open is now 13 / 10 ceiling — OVER**, entirely a mechanical consequence
of this branch's own split (item 19 stayed open as an epic AND gained 5 open
children where it was 1 open item before). This is advisory only — it fails
no gate, `work_items check` passes clean — but per the schema §5 / charter
W-1.4 convention, it is exactly the signal a reduction sprint exists for.
Closing even 2-3 of items 27-31 brings this back under ceiling; this is the
predictable near-term shape of the epic split the owner directed, not a new
problem to solve on its own.

**Open (13 / 10 ceiling — OVER):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item
   10 (the v1.1.0 cut). Needs the dev server + visual review, not just code.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its own
   fixture's annotations. Needs a real heuristic decision in `pick_anchor_jd`.
3. Item 14 — no JD-identifying (name/company) metadata in bootstrap/eval
   artifacts. Only partially touched by item 11 (run provenance added, JD-
   name provenance still missing).
4. Item 15 — suggested-skills rendering bug (comma-split inside
   parentheticals). Reproducible, but the exact call site in
   `suggest_skills`'s output parsing isn't traced yet.
5. Item 19 (epic) — UX-suite flakiness solution sprint umbrella. Cannot
   close until items 27-31 (below) all close. No standalone work happens
   against item 19 itself anymore — pick one of its children instead.
6. Item 20 — legacy `generate()` reachable via wizard rail without freezing
   Compose (`decision_owner=user`) — needs the owner's product-flow call
   before any code.
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
   Filing calls the fix "mechanical, likely" but touches `analyzer.py`'s
   LLM-call boundary — confirm no deliberate reason it skips `_call_llm`
   before rerouting it.
8. Item 22 — 4 call kinds never logged despite real call sites. Needs a
   live click-through per route to distinguish "dead path" from
   "instrumentation gap" before there's anything to fix.
9. **Item 27** (epic 19 child) — mode C's own residual (~17%/attempt),
   mechanism already described in the shared diagnosis doc. **Recommended
   next branch, not yet owner-confirmed** — see "Where we are" above.
10. **Item 28** (epic 19 child) — O-13, one sample, untested call site.
11. **Item 29** (epic 19 child) — O-12/O-14, the O-10 regression test
    itself under resource contention; 4 occurrences, most evidence of the 5.
12. **Item 30** (epic 19 child) — keyboard-reorder timeout, one sample, no
    diagnosis yet, unrelated to scroll.
13. **Item 31** (epic 19 child) — network-retry assertion flake, one sample
    plus one clean isolated rerun, unrelated to scroll, no diagnosis yet.

**Blocked (4):**
14. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR,
    `enforce_admins`).
15. Item 5 — grounding-score persistence gap (blocks calibrated L1/L2
    metric layers).
16. Item 8 — compose-time rewrite dial, still blocked pending owner
    direction on the real evidence channel (likely `/tune-from-annotations`,
    not decided).
17. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` (6
    satisfied; 19 now transitively gated on 27-31 all closing).

**Deferred (4):**
18. Item 4 — in-app citation viewer, no friction signal yet.
19. Item 7 — PX-46 memory consolidation, owner sign-off required first.
20. Item 24 — template-preview fidelity spike (T2), never scheduled; needs
    a product-priority decision before any code.
21. Item 25 — `app.run(threaded=True)` governance decision, deliberately
    deferred across many branches; owner-gated, touches the C-1-sensitive
    loopback-bind area.

**Watching (4):**
22. Item 2 — wordmark sweep, opportunistic only.
23. Item 16 — `evals/runner.py --suite real` non-functional, needs a real
    JD + owner data.
24. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
25. Item 23 — PX-52 analyzer.py split, WATCH disposition, deferred
    post-v1.1.0 (trigger: next major prompt-surface work).

25 total open+blocked+deferred+watching items (up from 20 at the predecessor
handoff — the delta is entirely the epic split's +5 children, net of item 19
itself not being double-counted). The Open-over-ceiling flag above is the
live signal to act on; this total-count line is context, not itself
actionable.

**No unresolved "still-pending thread" carried from further back** — the
two threads noted as unresolved across the last two handoffs (an owner's
"still gathering" UX fixes, and a documentation-only investigation) were not
re-raised this session either, and this session did not touch anything that
would resolve them either way. Still worth asking the owner directly.

---

## What this branch should build

Nothing further — this branch is closed out. The recommended next branch,
`fix/ux-mode-c-scroll-residual`, should tackle item 27
(`docs/dev/work/items/0027-mode-c-scroll-residual.md`) — **but confirm with
the owner first**, same as every branch in this arc. Scope is bounded to
item 27 only, once confirmed. Do not expand into items 9, 13, 14, 15, 20,
21, 22, 28, 29, 30, or 31 on the same branch — each gets its own branch per
the sequencing rule above.

---

## First move

If the owner confirms item 27 as the next branch: create
`fix/ux-mode-c-scroll-residual` off `main`, then follow C-7. The mechanism
already written up in `docs/dev/diagnosis/ux-scroll-position-flake.md`'s
Inferred §3 (`_wizardRender`'s smooth-scroll racing `refreshCorpus`'s
baseline read) is a **hypothesis from a shared, multi-mode document** — item
27 has no dedicated diagnosis dossier of its own yet. The
`require-evidence-before-fix` hook will block production edits on this
branch until a `docs/dev/diagnosis/fix-ux-mode-c-scroll-residual.md`
`## Observed` section is filled in with fresh evidence for THIS candidate
specifically — reading the existing shared document is orientation, not a
substitute for that. **Do not code the fix first.**

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
