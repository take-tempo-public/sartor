<!-- provenance: schema=1 session=da53af22-06c4-4bb0-b929-2b203f31741e branch=fix/ux-keyboard-reorder-timeout commit=3eb711c actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-31 -->

# Agent handoff: after `fix/ux-keyboard-reorder-timeout` (item 30 closed, capability-proven mechanism fixed)

**Branch to create:** `fix/ux-surgical-refinement-network-retry-flake` (branch off `main`) — item
31, the last epic-19 child. Start a NEW dossier at
`docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md` (the
`require-evidence-before-fix` hook expects that filename — branch name minus the `fix/`
prefix); item 31's own file (`docs/dev/work/items/0031-refinement-network-retry-error-flake.md`)
carries its two samples (one under `-n 2`, one clean-isolated rerun) and has no diagnosis yet.
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

- `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md` — item 30's now-complete dossier. Two
  things worth carrying forward: (1) **an item's stated mechanism can be an unsourced narrowing
  introduced downstream of the original record** — this item's own filing said
  `wait_for_load_state` with no cited source; the original observation
  (`docs/dev/work/items/0001-gate-unrunnable-by-agent.md`) said only "a plain Playwright 30s
  timeout." Trace item 31's own stated symptom (`'error' not in status_text`, an assertion
  flake, NOT a timeout) back to its original record before instrumenting narrow — it may hold up
  fine, but check rather than assume. (2) **Deterministic `page.route()` capability probes**
  (stall a specific resource indefinitely via `held.append(route)`, or force a specific failure
  via `route.fulfill(status=...)`) disambiguated between three rival hypotheses in two test runs,
  far cheaper than a blind rate campaign — reach for this FIRST if item 31 turns out to have
  multiple candidate mechanisms once its call path is mapped, not after a campaign comes back
  inconclusive.
- `docs/dev/work/items/0031-refinement-network-retry-error-flake.md` — item 31's own file: an
  assertion flake (`'error' not in status_text`), not a timeout — a different symptom shape than
  item 30's, so do not assume the same instrument or mechanism class applies without checking.
- `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md` `## Item 30 / item 31 sanity check` —
  already confirmed item 31 shares no call site or primitive with the scroll-position family.

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
`depends_on = [3, 6, 7, 9, 19]` — epic 19 cannot close until item 31 closes (27/28/29/30 all
closed; **31 is the last child**).

- ~~`fix/ux-mode-c-scroll-residual`~~ ✓ (merged, PR #80) — item 27 closed as already-fixed.
- ~~`fix/ux-restore-scroll-y-resource-contention`~~ ✓ (merged, PR #81) — item 29's contention
  campaign; found the `-n2` vector, no mechanism yet.
- ~~`fix/ux-scroll-flake-cross-item-review`~~ ✓ (merged, PR #85) — falsified the
  anchoring-bleed-in inference, proposed the height-clamp hypothesis + the falsification
  experiment.
- ~~`fix/ux-restore-scroll-y-resource-contention` (round 3, reused name)~~ ✓ (merged, PR #86)
  — ran the experiment, captured the writer, fixed it in two owner-approved phases, closed
  item 29.
- ~~`fix/ux-compose-reload-scroll-restore`~~ ✓ (merged, PR #87) — instrumented item 28's call
  site, confirmed item 29's fix does not reach it, ran a 24-iteration campaign, zero failures,
  closed item 28 as not-reproduced.
- **`fix/ux-keyboard-reorder-timeout` (this branch) — corrected item 30's own unsourced
  provenance, wide-instrumented the target test, ran two deterministic capability probes (one
  killed a candidate mechanism, one confirmed another), fixed the confirmed vulnerability in the
  test harness, verified against the mechanism (not just the repro) and a full clean `pytest -m
  ux` run, closed item 30.**
- `fix/ux-surgical-refinement-network-retry-flake` ← next after this (item 31, LAST epic-19 child)
- Do not start items 9/13/14/15/20/21/22 on the next branch — each is its own branch per
  the board; item 31 closes epic 19.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `b7a804b` (PR #87). This branch's commits, in order:

1. `b0488ed` — instrument (C-7 first commit): new dossier
   `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md` with `## Observed` filled from a direct
   provenance audit (item 30's `wait_for_load_state` specificity traced back to an unsourced
   narrowing — the original record said only "a plain Playwright 30s timeout") plus a
   direct-code-read structural finding (the target test hits `_wait_settled()` 12 times, not 3).
   Wide instrument added to `tests/ux/regression/test_20260604_bullet_drag_reorder.py`: times all
   three of `_wait_settled`'s sub-waits separately per reach, tracks every network
   request/response/failure for the whole test, dumps on any exception. Also folds in
   `docs/dev/ledger/da53af22-06c4-4bb0-b929-2b203f31741e.jsonl`, this session's `consumed` event.
2. `dd72967` — baseline: 7 isolated runs (1 shakedown + 6 more), all PASSED. Found reach 7
   (immediately after `WizardTemplatePage.open()`) consistently ~15-20x every sibling reach's
   `networkidle` cost on every run (~0.57s vs ~0.02-0.04s) — a real, reproducible structural cost,
   not yet a hang.
3. `110455c` — two pre-registered deterministic capability probes. P2 (Compose cascade retry
   hypothesis): forced `draft-summary` to 400 repeatedly, settled in 6.5s regardless — hypothesis
   killed, and a corrected, less alarming read of the cascade's actual recursion logic recorded.
   P1 (live-preview iframe hypothesis): stalled the iframe's script load, reproduced the EXACT
   symptom — a genuine `networkidle` `TimeoutError` at 31.1s — hypothesis capability-proven, not
   confirmed as item 30's specific historical cause (no artifact from that one sample survives to
   check).
4. `06e0b8a` — fix: `ui_pages/wizard_compose.py::_wait_settled` bounds the `networkidle`
   pre-drain to 5s (`contextlib.suppress` on timeout) instead of leaving it open to Playwright's
   30s default; the real settle gate (`Compose.SETTLED`) is unchanged. An app-side alternative
   (cancel the iframe nav on leaving Step 4) was investigated and rejected — no existing
   mechanism reaches wizard-step transitions, and the current behavior plausibly benefits a user
   who briefly navigates away and back. Re-ran P1 against the fix: `timed_out=False` twice.
5. `b78b35b` — full `pytest -m ux` regression check: 133 passed (131 baseline + 2 new probes),
   1 xfailed / 1 xpassed unchanged, zero reruns. (First attempt showed ~2x the historical wall
   time; traced to CPU contention from a concurrently-running, read-only session sharing this
   machine — confirmed benign by re-timing the single target test in isolation, unaffected.)
6. `3eb711c` — closed item 30 (owner-directed scope decision recorded in the dossier): item
   file + epic 19's own Updates + board regenerated (open 10→9, closed 9→10).

**Gate (`python -m scripts.gate`, no reruns anywhere, re-run clean after the contention above
resolved):** ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) · non-ux pytest (`-n auto`) ✓ ·
ux pytest (serial): 133 passed / 1 xfailed / 1 xpassed in 521.39s — 131 historical baseline + the
2 new diagnostic probe tests, fully accounted for · `work_items check` ✓ (31 files).

**Process notes for whoever runs long commands next (carried forward, still true):**
(1) the full non-ux tier does not reliably fit in one background call — foreground
file-list chunks (~2 × 65 files, `-n auto`, ~5-10 min each) is the fallback if a single
`scripts.gate` background call gets killed. (2) **A killed background Bash call does NOT
kill its process tree**: the loop survives and keeps spawning pytest runs. After ANY
killed background call, sweep `Win32_Process` for surviving `bash.exe` +
`pytest`/execnet workers, `taskkill /T /F`, and re-query until empty — but **check whose
processes they are first**: this session hit a killed gate run, swept, and found surviving
`bash.exe` processes that turned out to belong to a DIFFERENT, concurrently-running session
(explicitly read-only, sharing this machine) — not orphans from the kill. Never touch another
session's process; confirm with the user if a survivor's command line doesn't match anything you
launched. (3) Never run two Playwright/pytest-ux processes concurrently, including across your
own chunks — and be aware a concurrent session (even a read-only one) can still contend for CPU
and roughly double UX-suite wall time without causing any actual failures; don't over-attribute a
slow run to your own change without checking (re-time a representative single test in isolation).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 9 / 10 ceiling — net −1 this session** (item 30 closed; nothing new filed).

**Open (9 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its fixture's annotations.
3. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts.
4. Item 15 — suggested-skills comma-split rendering bug.
5. Item 19 (epic) — UX-suite flakiness sprint umbrella; cannot close until 31 closes
   (27 closed no-code; 28 closed not-reproduced; 29 closed with a two-phase fix; **30 closed
   this branch, capability-proven mechanism fixed**).
6. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
7. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
8. Item 22 — 4 call kinds never logged despite real call sites.
9. **Item 31** (epic 19's LAST child) — network-retry assertion flake, one `-n2` sample + one
   clean isolated rerun.

**Blocked (4):**
10. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
11. Item 5 — grounding-score persistence gap.
12. Item 8 — compose-time rewrite dial, blocked pending owner direction.
13. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]`.

**Deferred (4):**
14. Item 4 — in-app citation viewer, no friction signal yet.
15. Item 7 — PX-46 memory consolidation, owner sign-off required first.
16. Item 24 — template-preview fidelity spike (T2), never scheduled.
17. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
18. Item 2 — wordmark sweep, opportunistic only.
19. Item 16 — `evals/runner.py --suite real` non-functional.
20. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
21. Item 23 — PX-52 analyzer.py split, WATCH disposition.

21 total open+blocked+deferred+watching (was 22; item 30 closed).

---

## What this branch should build

1. Read item 31's own work-item file and `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`'s
   own sanity-check of it (that review confirmed item 31 shares no code path, primitive, or call
   site with the scroll-flake family — an assertion failure, `'error' not in status_text`, in
   `test_surgical_refinement_network_failure_surfaces_error_with_retry`,
   `tests/ux/regression/test_20260708_review_surface_and_flows.py`). Do not assume the settle-wait
   instrumentation pattern from item 30 applies here without checking — it is a different symptom
   shape (an assertion on rendered error text, not a timeout).
2. Reproduce first. Two samples on record (one under deliberate `-n 2`, one clean serial-run
   recurrence that passed on immediate isolated rerun) — closer to a diagnosis starting point than
   item 30 had, but still not a diagnosis. Follow the same C-7 discipline this arc has used
   throughout: instrument before guessing, first commit is the instrument/repro, never the fix.
   If the call path maps to more than one candidate mechanism, prefer deterministic
   `page.route()`-based capability probes over a blind rate campaign (item 30's own experience,
   this handoff's "Documents to read next" above).
3. Authorization: epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`), child
   item 31 (`docs/dev/work/items/0031-refinement-network-retry-error-flake.md`). Closing item 31
   closes epic 19 and unblocks item 10's `depends_on` list (still gated on items 3/6/7/9 too).

Scope is bounded to item 31's own falsification/closure and whatever new, evidence-backed
next step it produces — not to items 9/13/14/15/20/21/22, and not to any further app-side or
harness-side scroll/settle work without its own captured evidence.

---

## First move

Create branch `fix/ux-surgical-refinement-network-retry-flake` off `main`, write a plan
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
