<!-- provenance: schema=1 session=e003a99b-d8a3-4b6d-866b-3f29e9f8837d branch=fix/ux-surgical-refinement-network-retry-flake commit=040b665 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-01 -->

# Agent handoff: after `fix/ux-surgical-refinement-network-retry-flake` (item 31 closed, epic 19 closed — all 5 UX-flake candidates resolved)

**Branch to create:** none pre-authorized. Epic 19 (the sole active, owner-directed sequential
stream) is now fully closed — there is no epic-scripted next branch. The most defensible
candidate, by inference only (not an existing owner directive), is **item 9**
(release/visual-assets refresh — stale screenshots) since it is the only currently-`open`,
agent-owned item inside item 10's (`chore/release-v1.1.0`) own `depends_on` chain. **Confirm
with the owner before starting it or anything else** — see "Where we are in the arc" below.
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

- `docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md` — item 31's now-complete
  dossier. Same lesson item 30's dossier taught, confirmed recurring: an item's own filing can
  drift from its original evidence with no new data added (here, the "-n 2 contention"
  attribution — both surviving artifacts are provably serial runs). Trace a filed claim to its
  ORIGINAL source before instrumenting narrow around it.
- `docs/dev/work/items/0031-refinement-network-retry-error-flake.md` and
  `docs/dev/work/items/0019-ux-flake-solution-sprint.md` — the closed item and epic, both with
  a full Updates narrative of the investigation and fix.
- `tests/ux/regression/test_20260708_review_surface_and_flows.py` — the target regression test
  plus three new diagnostic probes (baseline, P1, P2), reusable if this exact mechanism ever
  needs re-verification.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** v1.1.0 endgame — epic 19 (UX-suite flakiness solution sprint) is now **CLOSED**.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are now closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned.**

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
- ~~`fix/ux-keyboard-reorder-timeout`~~ ✓ (merged, PR #88) — corrected item 30's own unsourced
  provenance, wide-instrumented the target test, ran two deterministic capability probes,
  fixed the confirmed vulnerability, closed item 30.
- **`fix/ux-surgical-refinement-network-retry-flake` (this branch) — corrected item 31's own
  unsourced "-n 2" provenance, capability-proved the mechanism (a stale `onUserSelect` tail
  clobbering a more meaningful status write) on the first deterministic probe, landed a
  two-phase owner-approved fix (app-side generation guard + harness settle contract), fixed one
  collateral regression the harness change surfaced, closed item 31 — the LAST child of epic 19
  — and epic 19 itself.**
- **Epic 19 is closed. No successor epic or branch is pre-scripted.** Read the board's Open
  list and confirm with the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 7, 8, 10 without their own listed unblock (all `Blocked`/`Deferred`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `a938683` (PR #88). This branch's commits, in order:

1. `c630b66` — instrument (C-7 first commit): new dossier
   `docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md` with `## Observed` filled
   from a direct provenance audit (item 31's "-n 2" specificity traced back to an unsourced
   narrowing — both surviving artifacts are provably serial runs, no xdist plugin, no `gw`
   worker markers) plus a direct-code-read structural finding (`onUserSelect`'s async tail
   writes `setStatus('READY')` ungated by item 29's own `_navGen` guard). Wide instrument added
   to `tests/ux/regression/test_20260708_review_surface_and_flows.py`: a `window.setStatus`
   interceptor plus three diagnostic probes (baseline, P1, P2). Also folds in
   `docs/dev/ledger/e003a99b-d8a3-4b6d-866b-3f29e9f8837d.jsonl`, this session's `consumed`
   event.
2. `040b665` — fix + close-out: two-phase owner-approved fix (app-side `_statusGen` guard in
   `static/app.js`, mirroring item 29's `_navGen`; harness settle contract
   `UserPicker.SELECT_READY` in `ui_pages/`, mirroring `data-compose-ready`). One collateral
   regression fixed: `test_smart_landing_tail_defers_to_user_navigation`
   (`tests/ux/regression/test_20260708_busy_states_and_chip.py`, item 29's own deterministic
   reproduction) relied on `UserPickerPage.select()`'s old narrow contract to hold part of the
   same cascade open on purpose — updated to drive the raw pre-fix primitive directly. Item 31
   and epic 19 both closed in the item files; board regenerated (open 9→7, closed 10→12).

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
non-ux pytest (`-n auto`): 2107 passed, 1 skipped in 387.57s · ux pytest (serial): 136 passed,
2 xfailed in 454.69s, **zero reruns** · `work_items check` ✓ (31 files).

**Process notes for whoever runs long commands next (carried forward, updated this session):**
(1) the full non-ux tier does not reliably fit in one background call — foreground
file-list chunks (~2 × 65 files, `-n auto`, ~5-10 min each) is the fallback if a single
`scripts.gate` background call gets killed. (2) **A killed background Bash call does NOT
kill its process tree**: the loop survives and keeps spawning pytest runs. After ANY
killed background call, sweep `Win32_Process` for surviving `bash.exe` +
`pytest`/execnet workers, `taskkill /T /F`, and re-query until empty — but **check whose
processes they are first**: never touch another session's process. (3) Never run two
Playwright/pytest-ux processes concurrently, including across your own chunks. (4) **New this
session:** this machine can run genuinely low on free memory (observed 0.88-1.82GB free of
15.73GB) from OTHER concurrent processes (other Claude Code sessions, VS Code, browsers) —
this OS-kills background pytest/gate runs (both `-n auto` AND plain serial; both the UX/Chromium
tier AND the plain non-ux tier) with no useful error, sometimes an xdist `[gw0] node down`. This
is NOT fixed by chunking or retrying the same command — check `Get-CimInstance
Win32_OperatingSystem` free memory and sweep your own orphans (should be empty) before
concluding it's your own change; if memory is genuinely tight, surface it to the user and wait
rather than burning cycles on retries (see `[[reference-shared-machine-oom-kills-bg-runs]]`).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 7 / 10 ceiling — net −2 this session** (item 31 closed; epic 19 itself closed;
nothing new filed).

**Open (7 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its fixture's annotations.
3. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts.
4. Item 15 — suggested-skills comma-split rendering bug.
5. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
6. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
7. Item 22 — 4 call kinds never logged despite real call sites.

**Blocked (4):**
8. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
9. Item 5 — grounding-score persistence gap.
10. Item 8 — compose-time rewrite dial, blocked pending owner direction.
11. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 now closed; still
    gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
12. Item 4 — in-app citation viewer, no friction signal yet.
13. Item 7 — PX-46 memory consolidation, owner sign-off required first.
14. Item 24 — template-preview fidelity spike (T2), never scheduled.
15. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
16. Item 2 — wordmark sweep, opportunistic only.
17. Item 16 — `evals/runner.py --suite real` non-functional.
18. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
19. Item 23 — PX-52 analyzer.py split, WATCH disposition.

19 total open+blocked+deferred+watching (was 21; item 31 and epic 19 both closed net −2).
**Epic 19 (5 children) is fully resolved and no longer on this ledger at all.**

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes epic 19; it does not
open a new authorized branch. The next session's first move is to read the Carried-forward
ledger above and `docs/dev/work/BOARD.md` directly, then confirm with the owner which item to
pick up (item 9 is the most defensible inference — see the top of this handoff — but is NOT a
standing authorization).

---

## First move

Do NOT create a branch yet. Read the ledger above and `docs/dev/work/BOARD.md`, propose a
next item to the owner (item 9 is the leading candidate, not a mandate), and only once
confirmed: create the branch, write a plan at `~/.claude/plans/<slug>.md`, and show it to the
user before touching any code. **Do not code first.**

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
