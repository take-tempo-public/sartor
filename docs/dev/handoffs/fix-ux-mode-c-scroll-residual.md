<!-- provenance: schema=1 session=ef6f6172-123c-4a19-a63a-0bac5b4e875e branch=fix/ux-mode-c-scroll-residual commit=f95d097 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-30 -->

# Agent handoff: after `fix/ux-mode-c-scroll-residual` (item 27 closed as already-resolved — no code fix)

**Branch to create:** `fix/ux-restore-scroll-y-resource-contention` (branch off `main`) — item 29, owner-confirmed as the next branch in sequence
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
endgame-steps prose.

**Stream:** v1.1.0 endgame — epic 19 (UX-suite flakiness solution sprint).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — item 19 is an epic that cannot close until
items 28-31 all close (27 is now closed, no code change).

- ~~`chore/ux-flake-epic-split`~~ ✓ (merged, PR #79) — promoted item 19 to an
  epic, filed items 27-31, one per original flake candidate.
- **`fix/ux-mode-c-scroll-residual` (this branch, not yet merged) — DONE.**
  Found item 27 (mode C's own residual) had already been root-caused and
  fixed on a SEPARATE branch three days before item 27 was ever filed.
  Closed item 27 with a resolution; wrote no code fix. Full detail below.
- **`fix/ux-restore-scroll-y-resource-contention` (recommended next,
  owner-confirmed)** — item 29
  (`docs/dev/work/items/0029-o10-regression-test-resource-contention.md`):
  strongest evidence of the remaining four candidates (4 occurrences —
  O-12 twice, O-14 once, plus the original deliberate `-n 2` capture), and
  the diagnosis doc already names the next step (a dedicated busy-loop-style
  campaign using the resource-contention vector, distinct from every prior
  pure-CPU-busy-loop campaign in this arc). Confirmed with the owner
  before this handoff was written, same as every branch in this arc.
- **After item 29, in priority order (evidence strength): item 28, then
  item 30, then item 31** — each gets its own branch. Do not start any of
  28, 30, or 31 on the `fix/ux-restore-scroll-y-resource-contention` branch.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is
currently at `ba570fe` (the `chore/ux-flake-epic-split` merge, PR #79).
This branch's own work, once merged, will be the next thing to land:

Commit `f95d097`: item 27 closed (`status = "closed"`, `resolution` field
added, `refs` widened to include `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md`);
epic 19 updated with a dated `## Updates` note on the child's closure;
`BOARD.md` regenerated; this session's own `consumed`-event provenance-ledger
file (for the incoming `chore-ux-flake-epic-split` handoff pointer) committed.

**Why no code change.** Item 27 described `_wizardRender`'s smooth-scroll
racing `refreshCorpus`'s baseline read (~17%/attempt), citing only
`docs/dev/diagnosis/ux-scroll-position-flake.md` (2026-07-16), which itself
scoped that mode out as unfixed. Before starting the C-7 campaign this item
called for, checked whether a newer dossier already covered the same
symptom — it did: `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md`, a
SEPARATE branch (`fix/ux-scroll-wizard-rail-flake`, seven rounds,
2026-07-16 through 2026-07-26) that **falsified the wizard-rail attribution
entirely (F-7)** and root-caused the same test/signature
(`test_corpus_reload_preserves_scroll_position`, `dy≈dh` family) to Chromium
scroll-anchoring on `refreshMergeSuggestions()`'s async growth — fixed via
`overflow-anchor: none` at the document/`body` scope (`static/style.css`),
merged to `main` (`27d349b`/`90e495d`) **2026-07-26, three days before item
27 was filed (2026-07-28) and four before the epic split (2026-07-29)**.
Neither filing cross-referenced that dossier or its RESOLVED carry-forward
ledger entry.

Verified live rather than closing on the paper trail alone:
`static/style.css:122` still carries the fix on current `main`; the two
wizard-render instrument tests are still `xfail(strict=False)` citing
F-7/O-15 by name; a fresh 20-run campaign at the identical 6-loader/8-core
calibration that produced 6/20 (30%) failures on the unfixed control in
round 7's own A/B produced **20/20 passed, 0 failed, 0 reruns**
(`scratchpad/capture_scroll_verify_20260730.log` — gitignored, not
committed, but its tally is quoted in item 27's own `## Updates`).

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
`pytest -m "not ux" -n auto` — 2107 passed / 1 skipped ·
`pytest -m ux` — 129 passed / 1 xfailed / 1 xpassed · `work_items check` ✓
(31 files).** Genuinely clean, no reruns anywhere in the log.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessor):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded.

**Open is now 12 / 10 ceiling — OVER, net −1 this session** (item 27 moved
from open to closed; no new items filed). Still over ceiling — a reduction
sprint remains flagged, per charter W-1.

**Open (12 / 10 ceiling — OVER):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item
   10 (the v1.1.0 cut). Needs the dev server + visual review, not just code.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its own
   fixture's annotations. Needs a real heuristic decision in `pick_anchor_jd`.
3. Item 14 — no JD-identifying (name/company) metadata in bootstrap/eval
   artifacts.
4. Item 15 — suggested-skills rendering bug (comma-split inside
   parentheticals).
5. Item 19 (epic) — UX-suite flakiness solution sprint umbrella. Cannot
   close until items 28-31 (below) all close. Item 27 closed this session
   with no code change — do not re-pick it.
6. Item 20 — legacy `generate()` reachable via wizard rail without
   freezing Compose (`decision_owner=user`).
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
8. Item 22 — 4 call kinds never logged despite real call sites.
9. **Item 28** (epic 19 child) — O-13, one sample, untested
   `loadComposition` call site of the `_captureScrollY`/`_restoreScrollY`
   primitive.
10. **Item 29** (epic 19 child) — O-12/O-14, the O-10 regression test
    itself fails under resource contention; 4 occurrences, most evidence
    of the 4 remaining candidates. **Recommended next branch, owner-confirmed.**
11. **Item 30** (epic 19 child) — keyboard-reorder timeout, one sample, no
    diagnosis yet, unrelated to scroll.
12. **Item 31** (epic 19 child) — network-retry assertion flake, one
    sample plus one clean isolated rerun, unrelated to scroll, no
    diagnosis yet.

**Blocked (4):**
13. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR,
    `enforce_admins`).
14. Item 5 — grounding-score persistence gap.
15. Item 8 — compose-time rewrite dial, blocked pending owner direction.
16. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]`.

**Deferred (4):**
17. Item 4 — in-app citation viewer, no friction signal yet.
18. Item 7 — PX-46 memory consolidation, owner sign-off required first.
19. Item 24 — template-preview fidelity spike (T2), never scheduled.
20. Item 25 — `app.run(threaded=True)` governance decision, deliberately
    deferred.

**Watching (4):**
21. Item 2 — wordmark sweep, opportunistic only.
22. Item 16 — `evals/runner.py --suite real` non-functional.
23. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
24. Item 23 — PX-52 analyzer.py split, WATCH disposition.

24 total open+blocked+deferred+watching items (down from 25 at the
predecessor handoff — the delta is item 27 closing, net of nothing new
filed). **New process observation, not itself a ledger item:** epic/item
filings that cite a diagnosis doc should check for a newer, superseding
dossier on the same symptom before treating it as open — see
`docs/dev/work/items/0027-mode-c-scroll-residual.md`'s own `## Updates`
and item 19's dated note for the specifics.

---

## What this branch should build

Nothing further — this branch is closed out, and its deliverable was a
reconciliation, not a code fix. The recommended next branch,
`fix/ux-restore-scroll-y-resource-contention`, should tackle item 29
(`docs/dev/work/items/0029-o10-regression-test-resource-contention.md`) —
already owner-confirmed. Scope is bounded to item 29 only. Do not expand
into items 9, 13, 14, 15, 20, 21, 22, 28, 30, or 31 on the same branch —
each gets its own branch per the sequencing rule above.

---

## First move

Create `fix/ux-restore-scroll-y-resource-contention` off `main`, then
follow C-7. `test_restore_scroll_y_stale_invocation_overwrites_later_scroll`
(the O-10 deterministic reproduction from the ORIGINAL Chip-2/3 fix, not
round-7's CSS fix) has failed 4 times under confirmed resource contention
(O-12 ×2, O-14) and passed 5/5 in isolation every time — see
`docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-12/O-14 entries. No
dedicated diagnosis dossier exists yet for this candidate specifically.
The `require-evidence-before-fix` hook will block production edits on this
branch until `docs/dev/diagnosis/fix-ux-restore-scroll-y-resource-contention.md`'s
`## Observed` section is filled in with fresh evidence for THIS candidate —
per the diagnosis doc's own suggested next step, a dedicated busy-loop-style
campaign using the resource-contention vector (not another pure-CPU-busy-loop
campaign like every prior one in this arc — the widened vector now includes
an orphaned same-project server and genuine cross-project load, per O-12/O-14).
**Do not code the fix first.**

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
