<!-- provenance: schema=1 session=fee63c3e-d300-4c7f-bbb8-3412f5b4ca15 branch=fix/ux-restore-scroll-y-resource-contention commit=63f1a1e actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-07-30 -->

# Agent handoff: after `fix/ux-restore-scroll-y-resource-contention` round 3 (item 29 FIXED and closed)

**Branch to create:** `fix/ux-compose-reload-scroll-restore` (branch off `main`) — item 28,
the next epic-19 child in the standing priority order. Start a NEW dossier at
`docs/dev/diagnosis/ux-compose-reload-scroll-restore.md` (the `require-evidence-before-fix`
hook expects that filename — branch name minus the `fix/` prefix); item 28's single sample
(O-13) lives in `docs/dev/diagnosis/ux-scroll-position-flake.md` and its item file carries an
inherited first check from this session (see "What this branch should build").
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

## Documents to read next, specific to this handoff

- `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` — item 29's dossier,
  now carrying the full Round 3 record (R3-0 … R3-8): the height-at-read instrument, the
  captured `-n2` failure whose spy timeline named the writer, the two-phase fix, both
  deterministic FAIL→PASS flips, and the 16/16 clean fixed-arm A/B. **The one-paragraph
  version: every mystery value in this flake family was geometry** — `59 = 959-900` (the
  small-page clamp), `306 = 1206-900` (the wizard smooth-scroll's clamped landing),
  `273/291/31` (mid-flight samples of that animation), `0` (the animation retargeted after
  its element was hidden) — written by the user-select tail's stale smart-landing
  (`_activateTab` tab flip + `wizardInit`'s smooth `scrollIntoView`) and, phase 2, by that
  animation *surviving* an explicit tab switch. The scroll capture/restore mechanism was
  confirmed correct in every captured failure.
- `docs/dev/work/items/0028-compose-reload-scroll-restore-untested-site.md` — item 28's file,
  including the 2026-07-30 inherited-check Update this session added.
- `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` — the cross-item review whose
  falsification experiment this session ran; background for how the hypothesis was formed.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** v1.1.0 endgame — epic 19 (UX-suite flakiness solution sprint).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — epic 19 cannot close until items 28/30/31 close
(27 closed 2026-07-30 no-code; **29 closed this branch, WITH a two-phase fix**).

- ~~`fix/ux-mode-c-scroll-residual`~~ ✓ (merged, PR #80) — item 27 closed as already-fixed.
- ~~`fix/ux-restore-scroll-y-resource-contention`~~ ✓ (merged, PR #81) — item 29's contention
  campaign; found the `-n2` vector, no mechanism yet.
- ~~`fix/ux-scroll-flake-cross-item-review`~~ ✓ (merged, PR #85) — falsified the
  anchoring-bleed-in inference, proposed the height-clamp hypothesis + the falsification
  experiment.
- **`fix/ux-restore-scroll-y-resource-contention` (this branch, round 3, reused name) — ran
  the experiment, captured the writer, fixed it in two owner-approved phases, closed item 29.**
- `fix/ux-compose-reload-scroll-restore` ← next after this (item 28)
- items 30, 31 ← after that, in order; do not start them on item 28's branch

Do not begin items 9/13/14/15/20/21/22 on the next branch — each is its own branch per the
board; the epic-19 children go strictly in order 28 → 30 → 31.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit. `main`
is at `eb655af` (PR #85). This branch's commits, in order:

1. `60aeee5` — height-at-read instrument (C-7 first commit): both scroll reads in
   `test_restore_scroll_y_stale_invocation_overwrites_later_scroll` return
   `{y, sh, ih, cards}` from one evaluate; session ledger jsonl folded in.
2. `9a796dc` — `SCROLL_READ_LOG` env-gated durable read log (xdist swallows passing stdout).
3. `5d28fad` — dossier R3-2: the captured `-n2` failure (`59→273`, `sh=1206` at read) whose
   spy timeline shows `_wizardRender`'s smooth `scrollIntoView(#panelJD)` as the writer and
   the stale restore abandoning correctly.
4. `e9d9586` — deterministic repro `test_smart_landing_tail_defers_to_user_navigation`
   (3/3, xfail at that point), dossier R3-3, item 0028/0029 updates.
5. `fc3e437` — **phase-1 fix** (owner-approved): `_navGen` navigation-generation guard on
   `onUserSelect`'s tail; `wizardInit(opts)`/`_wizardRender(opts)` with `{scroll:false}`;
   repro flipped to plain PASS; CHANGELOG.
6. `65b0f88` — **phase-2 fix** (owner-approved): `switchTopTab` cancels in-flight smooth
   scrolls via raw `_scrollRestoreNative.scrollTo` (no gen bump); same-task bench
   `test_tab_switch_cancels_inflight_smooth_scroll` (3/3 FAIL→3/3 PASS); item 29 closed,
   board regenerated (open 12 → 11).
7. `b50abec` — owner-authorized `/wiki-self-update` diff pass (cap 18): 3 pages updated +
   audited, 12 verified no-edit, checkpoint advanced — clears the 75-file freshness gate that
   was blocking this merge.
8. `63f1a1e` — epic-19 update, CHANGELOG phase-2 addendum.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) · non-ux pytest (2 chunks,
`-n auto`): 1161 + 945 passed / 1 skipped — plus the wiki-freshness test which failed
pre-wiki-pass and re-ran green (10/10) after it · ux tier (4 chunks): 130 passed /
1 xfailed / 1 xpassed (= the 131 historical baseline + this branch's 2 new tests) · ONE
disclosed load-flake: `test_compose_skills_card_drop_persists`, a `#panelTemplate`
visibility timeout of the documented O-8 class, 2/2 clean isolated, logged in epic 19's
Updates — no reruns anywhere else · `work_items check` ✓ (31 files) · `check_doc_links` ✓
(317 files).**

**Process notes for whoever runs long commands next (two updates to the standing note):**
(1) the full non-ux tier no longer fits reliably in one background call this session —
background Bash calls were killed twice at unpredictable points; foreground file-list chunks
(2 × ~65 files, `-n auto`, ~5-10 min each) worked first try. (2) **A killed background Bash
call does NOT kill its process tree**: the bash loop survives and keeps spawning pytest runs
(this session briefly had two concurrent ux runs that way — the exact forbidden condition).
After ANY killed background call, sweep `Win32_Process` for surviving `bash.exe` +
`pytest`/execnet workers, `taskkill /T /F`, and re-query until empty. Full detail in the
`reference-background-bash-kill-ceiling` memory. Never run two Playwright/pytest-ux
processes concurrently, including across your own chunks.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 11 / 10 ceiling — still OVER, net −1 this session** (item 29 closed; nothing new
filed — this session's two trailing observations were folded into existing homes: the O-8
flake occurrence into epic 19's Updates, the background-bash tree-kill trap into memory).
A reduction sprint remains flagged, per charter W-1.

**Open (11 / 10 ceiling — OVER):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its fixture's annotations.
3. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts.
4. Item 15 — suggested-skills comma-split rendering bug.
5. Item 19 (epic) — UX-suite flakiness sprint umbrella; cannot close until 28/30/31 close
   (27 closed no-code; 29 closed this branch with the two-phase fix).
6. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
8. Item 22 — 4 call kinds never logged despite real call sites.
9. **Item 28** (epic 19 child) — O-13, one sample, `loadComposition` call site
   (`before=400 after=796`). Now has an inherited first check from item 29's resolution —
   see "What this branch should build".
10. **Item 30** (epic 19 child) — keyboard-reorder timeout, one sample, no diagnosis.
11. **Item 31** (epic 19 child) — network-retry assertion flake, one sample + one clean
    isolated rerun.

**Blocked (4):**
12. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
13. Item 5 — grounding-score persistence gap.
14. Item 8 — compose-time rewrite dial, blocked pending owner direction.
15. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]`.

**Deferred (4):**
16. Item 4 — in-app citation viewer, no friction signal yet.
17. Item 7 — PX-46 memory consolidation, owner sign-off required first.
18. Item 24 — template-preview fidelity spike (T2), never scheduled.
19. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
20. Item 2 — wordmark sweep, opportunistic only.
21. Item 16 — `evals/runner.py --suite real` non-functional.
22. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
23. Item 23 — PX-52 analyzer.py split, WATCH disposition.

23 total open+blocked+deferred+watching (was 24; item 29 closed).

---

## What this branch should build

1. **Post-fix re-check FIRST (cheapest possible outcome):** item 28's single sample (O-13,
   `test_compose_reload_preserves_scroll_position`, `before=400 after=796`) predates this
   branch's two fixes — and that test ran clean in all 16 fixed-arm `-n2` iterations this
   session (it is one of the campaign's 4 nodeids). Before instrumenting anything new, run
   the documented `-n2` vector (recreate `scratchpad/capture_contention_n2.sh` from item
   29's dossier `## Observed` — the scratchpad copy is session-local and will not survive)
   for ~16-24 iterations watching item 28's test specifically. If it never fails, item 28's
   likely resolution is "same writer, fixed by item 29's fix" — but per the cross-item
   review's own scope rule, claim that only with its own evidence (the 16 clean runs this
   session are already evidence; extend the sample and close on it with owner concurrence).
2. **If it still fails:** apply the inherited first check (item 0028's 2026-07-30 Update):
   was a select/landing-tail write or surviving animation in flight at the read, on the
   Tailor/Compose tab's own geometry? Add the same single-evaluate height-at-read
   instrument item 29 used (`_READ_SCROLL_STATE_JS` pattern,
   `tests/ux/regression/test_20260708_busy_states_and_chip.py:~324`) to
   `test_compose_reload_preserves_scroll_position`'s reads, plus `SCROLL_READ_LOG` logging
   — as the FIRST commit, with a new dossier at
   `docs/dev/diagnosis/ux-compose-reload-scroll-restore.md` (fill `## Observed` from O-13's
   record before any production edit; the hook requires it).
3. Authorization: epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`), child
   item 28 (`0028-compose-reload-scroll-restore-untested-site.md`).

Scope is bounded to item 28's own falsification/closure and whatever new, evidence-backed
next step it produces — not to items 9, 13, 14, 15, 20, 21, 22, 30, or 31, and not to any
further app-side scroll work without its own captured evidence (both of item 29's fixes
required owner approval; assume the same bar).

---

## First move

Create branch `fix/ux-compose-reload-scroll-restore` off `main`, write a plan
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
