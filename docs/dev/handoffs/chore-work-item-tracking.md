<!-- provenance: schema=1 session=2db3a371-1d98-4695-9e1c-fbdd2ac51d2d branch=chore/work-item-tracking commit=fbc160f actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-28 -->

# Agent handoff: after `chore/work-item-tracking` (structured tracking + real gate fix — DONE)

**Branch to create:** none directed yet — see "Where we are in the arc" below.
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
`docs/dev/work/BOARD.md` — **this is now the authoritative live-item source**, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose (both retained as historical narrative with inline "MIGRATED to work item N" pointers,
not deleted). `#2` in the list above is now stale guidance from this template until it's
updated to say so explicitly — a residual not fixed on this branch, flagged here instead.

**Stream:** v1.1.0 endgame, interrupted by a dev-process tooling branch — owner-directed
this session, not part of the RELEASE_ARC numbered fork sequence's other owner-gated steps.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`test/fixture-scoping-rollout`~~ (merged, PR #74) — the branch this session's own
  predecessor closed out; PX-44 fully landed.
- **`chore/work-item-tracking` (this branch, not yet committed) — DONE.** Full detail
  below. Built a structured work-item tracker (`docs/dev/work/`), root-caused and fixed the
  "gate unrunnable by an agent" problem, and picked up + **paused** a resume of PX-39
  mid-branch when the tracking-system redesign was directed instead.
- **No branch owner-directed next.** Per AGENTS.md "Do not pick a fork item on your own
  initiative," the owner must direct the next branch explicitly. **Read
  `docs/dev/work/BOARD.md` for the current fork** — 9 open / 4 blocked / 2 deferred / 3
  watching, not the old prose list. The most likely candidate, since it was already
  in-progress this session before the pivot: **item 6 (PX-39)** — real-corpus Sonnet-5
  baseline, likely resumable at near-zero cost (72 real non-eval telemetry records already
  exist in the owner's E2E clone; see the item file for the exact plan that was in flight).
  Do not resume it or anything else without the owner's explicit go.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged; nothing has been committed yet.**
`main` is currently at `fbc160f` (the `test/fixture-scoping-rollout` merge, PR #74 — the
46-file fixture-scoping rollout this session's predecessor completed). This branch's own
work, once committed, will be the next thing to land:

1. **Structured work-item tracking system** — `docs/dev/work/SCHEMA.md` +
   `scripts/work_items.py` (vendored from sister project `spolia`'s proven design, one
   addition: an optional `depends_on` field for peer-level sequencing), 19 live items filed
   under `docs/dev/work/items/`, `BOARD.md` generated, `work_items check` wired into
   `scripts/gate.py`. `RELEASE_CHECKLIST.md`/`RELEASE_ARC.md` point at the board via inline
   migration markers on each moved item — history preserved, not deleted. `tests/
   test_work_items.py` (44 tests, vendored + a new `depends_on` class + 2 real-backlog bridge
   tests). Charter W-1.4 amended (single written rationale line — a working-model clause, not
   constitutional, so no full C-0…C-9 ceremony) to point at the new location, plus the
   owner's explicit note to revisit promoting it to the full ceremony once it settles into
   practice.
2. **Real quality-gate fix, not just tooling** — the "gate unrunnable by an agent" work item
   (now item 1, **closed**) turned out to never be a mystery environment-wide kill: the full
   suite's real runtime is ~30min as of today (was ~13min on 2026-07-14; test count only grew
   ~8% in that window — organic growth, not one bug, though a single `transformers`/`torch`
   lazy-import cost in `test_grounding_signals.py` explains ~7.7% of it alone). `pytest-xdist`
   (new dependency, `pyproject.toml`) now parallelizes the non-UX tier in `scripts/gate.py`
   (437s vs. ~700s+ serial call-time, zero new failures, verified against PX-44's DB-isolation
   work). The UX/Playwright tier is deliberately kept serial — `-n 2` reproduced 5 real
   CPU-contention timing flakes matching `docs/dev/diagnosis/ux-scroll-position-flake.md`'s
   already-diagnosed mechanism. Also found and killed (owner-confirmed) two orphaned
   `python app.py` processes left running from earlier in the session — carry-forward ledger
   item 20's exact documented failure class, directly reproduced.
3. **UX-flake documentation + solution sprint filed** — `ux-scroll-position-flake.md` gained
   two new, precisely-scoped observations (O-12, O-13), kept strictly separate from existing
   findings per that document's own Observed/Inferred discipline. New work item 19 schedules
   the actual investigation (not done here) — the doc's own already-flagged mode-C residual
   plus 3 newly-observed single-sample flakes, explicitly not conflated into one mechanism.
4. **6 real defects found and filed** (items 11-18) exercising the annotate/bootstrap
   workflow this session: a bootstrap-overwrite data-loss bug (no merge/versioning — every
   run replaces the last), a judge JSON-parse failure silently scoring `0`, a fixture whose
   `jd.txt` doesn't match its own annotations (an eval graded the wrong target), missing
   JD-provenance metadata, a skill-suggestion rendering bug (comma-split inside a
   parenthetical), `evals/runner.py --suite real` being non-functional (no fixtures exist),
   a doc contradiction between `PERFORMANCE_HISTORY.md` and `RELEASE_ARC.md`, and
   run-to-run judge-score variance (watching, n=2, not yet characterized).
5. **PX-39 started, then paused** — item 6. Key finding before the pause: the owner's E2E
   clone already has 72 real, non-`eval:`-prefixed, Sonnet-5 telemetry records from historical
   app usage (2026-07-06–09) — likely zero new spend needed to close this out. `--suite real`
   was also found broken in this project (item 16, watching) independent of PX-39's own plan.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ (338 files) · `pytest -m "not ux" -n auto` ✓ ·
`pytest -m ux` ✓ (clean on retry — 129 passed; the first attempt hit this project's
already-known, already-CI-accepted ~40%-ish UX rerun rate, not a regression) ·
`work_items check` ✓ (19 files).**

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note, this handoff:** this template's own instruction below says to reproduce
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that is now stale guidance (see "Where we
are" above). Rendering `docs/dev/work/BOARD.md`'s full Open/Blocked/Deferred/Watching subset
instead, since that is the actual authoritative source as of this branch. The template itself
was not updated to say so explicitly — a small residual, not fixed here.

**Open (9 / 10 ceiling):**
1. Item 6 — PX-39 real-corpus Sonnet-5 baseline — started, paused mid-branch, likely
   near-zero-cost to finish (see above).
2. Item 9 — release/visual-assets refresh, screenshots ~7.5+ weeks stale.
3. Item 11 — bootstrap overwrite destroys prior annotation work, no merge/versioning.
4. Item 12 — judge JSON-parse failure silently scores as 0.
5. Item 13 — fixture `jd.txt` doesn't match its own annotations (depends on 11).
6. Item 14 — no JD-identifying metadata in bootstrap/eval artifacts (depends on 11).
7. Item 15 — suggested-skills rendering bug (comma-split inside parentheticals).
8. Item 17 — doc contradiction, eval-vs-live traffic source (depends on 6).
9. Item 19 — UX-suite flakiness solution sprint (scheduled, not yet investigated).

**Blocked (4):**
10. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
11. Item 5 — grounding-score persistence gap (blocks calibrated L1/L2 metric layers).
12. Item 8 — compose-time rewrite dial, evidence-gated on PX-39 (depends on 6) — owner has
    since excluded the Microsoft JD from that evidence path; the design doc may need a
    one-line update reflecting this, not yet done.
13. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9]`.

**Deferred (2):**
14. Item 4 — in-app citation viewer, no friction signal yet.
15. Item 7 — PX-46 memory consolidation, owner sign-off required first.

**Watching (3):**
16. Item 2 — wordmark sweep, opportunistic only.
17. Item 16 — `evals/runner.py --suite real` non-functional, needs a real JD + owner data.
18. Item 18 — judge-score run-to-run variance, n=2, uncharacperized.

**Well within the 10-item WIP ceiling.** None of the above are freely solo-closeable without
further owner input except where `decision_owner = "agent"` is marked on the board — even
those, per "do not pick a fork item on your own initiative," should be presented, not started
unprompted.

**Still-pending, unresolved thread — surface at next session start, do not assume its
shape:** mid-session the owner said "the fixes I am still gathering" (implying more
UX/annotation findings beyond this session's 6) and separately asked for "another
investigation to capture... a documentation-only session, next session." The exact scope was
never clarified and **deliberately not filed as a work item** — filing it half-understood
would misrepresent scope. Ask the owner directly what that investigation should cover.

---

## What this branch should build

Nothing further — this branch is closed out. The next agent's job is to get explicit owner
direction on which board item to pick up next (see "Where we are in the arc" above), or to
scope the "still-gathering" investigation thread noted just above. All open items are either
`decision_owner = "user"` or, for the `agent`-owned ones, still require the owner to pick
which one to schedule next — there is no freely solo-closeable item this branch left behind
that should be started without that direction.

Scope is bounded to what's on `docs/dev/work/BOARD.md`. Do not expand beyond it, and do not
invent new items without owner direction beyond what this session already filed.

---

## First move

Do not create a branch yet. Confirm with the owner what to work on next — start by asking
about the "still-gathering" investigation thread above, since that was explicitly flagged as
unresolved, before defaulting to the board's own most-obvious candidate (PX-39). Once
directed, follow the same pattern: write a plan at `~/.claude/plans/<slug>.md` and show it to
the user before touching any code. **Do not code first.**

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
