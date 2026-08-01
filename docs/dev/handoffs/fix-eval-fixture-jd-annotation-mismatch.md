<!-- provenance: schema=1 session=5a021a87-16d7-4b56-952b-563a5f0538f8 branch=fix/eval-fixture-jd-annotation-mismatch commit=ff3e34f actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-01 -->

# Agent handoff: after `fix/eval-fixture-jd-annotation-mismatch` (item 13 closed, mechanism corrected)

**Branch to create:** none pre-authorized. No epic or standing stream currently has an
agent-startable next branch scripted. Read the Carried-forward ledger below and
`docs/dev/work/BOARD.md` directly, then confirm with the owner which item to pick up.
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

- `docs/dev/diagnosis/eval-fixture-jd-annotation-mismatch.md` — item 13's dossier.
  Read this before touching `evals/annotation.py` or `blueprints/diagnostics.py`'s
  bootstrap-pin resolution again: it is the third recurrence of a filed item's
  mechanism drifting more specific than its evidence (same shape items 30 and 31
  each independently found) — a strong signal to check ANY item's original citation
  before trusting a downstream summary, not just this one.
- `docs/dev/work/items/0013-fixture-jd-mismatches-annotations.md` (closed) and
  `docs/dev/work/items/0014-no-jd-provenance-metadata.md` (still open) — item 13's
  full corrected narrative, and the concrete motivating case now on file for item 14.
- `tests/test_annotation.py::TestEnsureAnchorCoveredByAnnotations`,
  `TestTemplate::test_bootstrap_fingerprint_*` and
  `tests/test_annotation_routes.py::TestCollate::test_rejects_anchor_not_represented_in_annotations`,
  `TestBootstrapPinIntegrity::test_stale_pin_content_is_not_silently_reused` — the
  new regression coverage, reusable if a similar mismatch symptom recurs.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice
(item 13, not the leading-candidate item 9), not from a pre-scripted sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 13
was independent of item 9's dependency chain).

- **`fix/eval-fixture-jd-annotation-mismatch` (this branch)** — corrected item 13's own
  filed mechanism (falsified: `pick_anchor_jd` was never the defect), capability-proved
  two real gaps (a stale bootstrap pin trusted on path-existence alone; no collate-time
  check that the anchor JD is represented in the annotation data), fixed both fail-closed,
  closed item 13, noted the concrete motivating case into item 14 (kept open, separate).
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 7, 8, 10 without their own listed unblock (all `Blocked`/`Deferred`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `e419a75` (PR #89, item 31 / epic 19 close-out). This branch's commits, in order:

1. `f598452` — instrument (C-7 first commit): new dossier
   `docs/dev/diagnosis/eval-fixture-jd-annotation-mismatch.md` with `## Observed` filled
   from a direct measurement against the real `robert-bootstrap` artifacts (kept out of
   this repo, `.gitignore:57`) — falsifying item 13's own filed mechanism and identifying
   the two real gaps. Two new RED regression tests added to
   `tests/test_annotation_routes.py`, run and confirmed failing on pre-fix `HEAD` for the
   documented mechanism, before any production code changed. Also folds in
   `docs/dev/ledger/5a021a87-16d7-4b56-952b-563a5f0538f8.jsonl`, this session's `consumed`
   event.
2. `8536259` — fix: `build_annotation_template` stamps a `bootstrap_fingerprint`;
   `_resolve_bootstrap_path` (split into `_resolve_bootstrap_pin`) verifies it and fails
   closed on a content mismatch instead of substituting the newest `bootstrap-*.json`.
   `evals.annotation.ensure_anchor_covered_by_annotations` refuses to collate an anchor
   JD not represented in the annotation data, wired into both `_cmd_collate` (CLI) and
   `annotation_collate` (route, → 409). `pick_anchor_jd` itself untouched — proven not
   the defect; its own existing tests pass unmodified. Both RED tests from commit 1 now
   pass; new unit tests added for the guard function and the fingerprint stamping.
3. `ff3e34f` — docs: corrected item 13's own filing to the falsified mechanism, closed
   it; filed the concrete motivating case into item 14 (kept open, separate item); board
   regenerated (open 7→6, closed 12→13).

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ (338 source files) ·
non-ux pytest (`-n auto`): 2115 passed, 1 skipped in 332.15s · ux pytest (serial): 136
passed, 1 xfailed, 1 xpassed in 469.00s, **zero reruns** · `work_items check` ✓ (31 files).
Ran in the foreground this session after a low-free-memory reading (1.53GB/15.73GB)
raised the risk of a silent background OOM kill (per the process notes below) — the user
chose foreground over waiting, and it completed cleanly.

**Process notes for whoever runs long commands next (carried forward, unchanged this
session):** (1) the full non-ux tier does not reliably fit in one background call —
foreground file-list chunks (~2 × 65 files, `-n auto`, ~5-10 min each) is the fallback if
a single `scripts.gate` background call gets killed. (2) **A killed background Bash call
does NOT kill its process tree**: the loop survives and keeps spawning pytest runs. After
ANY killed background call, sweep `Win32_Process` for surviving `bash.exe` +
`pytest`/execnet workers, `taskkill /T /F`, and re-query until empty — but **check whose
processes they are first**: never touch another session's process. (3) Never run two
Playwright/pytest-ux processes concurrently, including across your own chunks. (4) This
machine can run genuinely low on free memory (observed as low as 0.88GB free of 15.73GB,
and 1.53GB this session) from OTHER concurrent processes (other Claude Code sessions, VS
Code, browsers) — this OS-kills background pytest/gate runs with no useful error. Check
`Get-CimInstance Win32_OperatingSystem` free memory before a long background run; if
tight, ask the user whether to run foreground, wait, or scope down rather than retrying
blind. (5) **New this session:** 3 stray `python3.13.exe` processes were found running
`claude_hook.py block-secrets` / `block-merge-to-main`, dated the day before this session
(not spawned by this session — this session's own commits ran through hooks normally).
Flagged to the user rather than killed unilaterally; user said leave them. If they're
still present next session and still doing nothing, that's independent confirmation
they're orphaned, not a coincidence — but still ask before touching, per
`[[project-e2e-instance-location]]`'s process-audit-trap precedent (never assume a found
process is safe to kill without checking whose it is first).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 6 / 10 ceiling — net −1 this session** (item 13 closed; nothing new filed).

**Open (6 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts. Now has a concrete
   motivating case on file (item 13's closure) — worth weighing when picked up.
3. Item 15 — suggested-skills comma-split rendering bug.
4. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
5. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
6. Item 22 — 4 call kinds never logged despite real call sites.

**Blocked (4):**
7. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
8. Item 5 — grounding-score persistence gap.
9. Item 8 — compose-time rewrite dial, blocked pending owner direction.
10. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
    gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
11. Item 4 — in-app citation viewer, no friction signal yet.
12. Item 7 — PX-46 memory consolidation, owner sign-off required first.
13. Item 24 — template-preview fidelity spike (T2), never scheduled.
14. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
15. Item 2 — wordmark sweep, opportunistic only.
16. Item 16 — `evals/runner.py --suite real` non-functional.
17. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
18. Item 23 — PX-52 analyzer.py split, WATCH disposition.

18 total open+blocked+deferred+watching (was 19; item 13 closed net −1).

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 13; it does
not open a new authorized branch. The next session's first move is to read the
Carried-forward ledger above and `docs/dev/work/BOARD.md` directly, then confirm with the
owner which item to pick up.

---

## First move

Do NOT create a branch yet. Read the ledger above and `docs/dev/work/BOARD.md`, propose a
next item to the owner, and only once confirmed: create the branch, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not
code first.**

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
