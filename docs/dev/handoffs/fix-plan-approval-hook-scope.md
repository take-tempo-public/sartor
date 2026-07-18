<!-- provenance: schema=1 session=ccd0dad5-59f7-4a2c-bddf-c08af55e3beb branch=docs/fix-plan-approval-hook-scope-handoff commit=1b75915 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-17 -->

# fix/plan-approval-hook-scope handoff — 2026-07-17

This handoff covers two merged branches from the same session: `fix/plan-approval-hook-scope`
(the per-project hook-scoping fix) and the small `docs/fix-handoff-before-merge-ordering`
follow-up it triggered. It was written on a third, tiny branch
(`docs/fix-plan-approval-hook-scope-handoff`) because the first branch was merged and pruned
before its handoff got written — a close-out-checklist ordering bug (now fixed) let that happen.
See "What just landed on `main`" below for the full story.

---

**Branch to create:** `<!-- pick per whatever the owner wants next -->` (branch off `main`)
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

**Stream:** `RELEASE_ARC.md` "v1.1.0 close-out — reconciliation" individual-branch sequence.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this specific step; the
whole reduction-sprint sequence gates the `v1.1.0` tag.

- ~~`docs/v110-plan-reconciliation`~~ ✓ — step 1, audited state + this ordered sequence itself
- ~~**`fix/plan-approval-hook-scope`**~~ ✓ — step 2, this handoff's subject, DONE
- `fix/compose-unawaited-reloads` ← next per the sequence — await the remaining un-awaited
  Compose user-action `loadComposition()` calls (ledger item 7)
- `refactor/css-cascade-collapse` (PX-51), `chore/config-drift-batch` (PX-47),
  `chore/hook-dispatcher` (PX-37), and the rest of the ordered list ← do not start these on
  this branch; each is its own session per `RELEASE_ARC.md`'s explicit one-branch-at-a-time rule

Do not start `chore/hook-dispatcher` believing it also covers these 3 plan-lifecycle scripts —
they were deliberately kept standalone (not migrated to the portable enforcement core) and stay
that way; see "What just landed" below.

---

## What just landed on `main`

**`fix/plan-approval-hook-scope`** (merge `b2bf2f8`, work commit `981630b`): resolves
`RELEASE_CHECKLIST.md` Carry-forward item 14 (F-gov-02/F-gov-03). `check-plan-approved.sh` /
`mark-plan-approved.sh` / `cleanup-plan-on-merge.sh` now key their approval marker and a new
"current plan file" pointer off `CLAUDE_PROJECT_DIR` (confirmed a real env var inside hook
bodies — 9 of the other 12 hooks already use it) instead of one global
`$HOME/.claude/plans/.approved` + a whole-directory `*.md` scan. A concurrent session in a
different project/worktree can no longer false-block or wipe this project's approval.

**A second, related defect was found LIVE during this branch's own investigation, not
hypothesized:** `cleanup-plan-on-merge.sh`'s merge-detection was a bare text `grep` over the
whole raw stdin JSON with no check that a merge actually happened — a diagnostic Bash command
whose text merely *mentioned* the trigger phrases (as embedded test data) tripped it for real
and deleted a just-approved plan. Fixed by gating the actual deletion on a structural check
(`git -C "$CLAUDE_PROJECT_DIR" log -1 --pretty=%P` has ≥2 parents — HEAD is genuinely a merge
commit), keeping the text `grep` only as a cheap pre-filter. Full evidence, both defects:
[`diagnosis/plan-approval-hook-scope.md`](../diagnosis/plan-approval-hook-scope.md). New
regression suite `tests/test_plan_approval_scoping.py` (7 tests, subprocess-level against the
real scripts). `tests/test_governance_hooks_gate.py` needed zero changes.

**`docs/fix-handoff-before-merge-ordering`** (merge `1b75915`, work commit `2c42389`): a direct
consequence of closing the branch above. `AGENTS.md`'s close-out checklist and its canonical
source (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`) both ordered "write the next-agent handoff" AFTER
"execute merge" — directly contradicting the template's own "Capture-before-merge" hard
constraint two paragraphs above it (the handoff **is** one of the branch's own docs, and that
constraint says all such docs must land before the merge). Following the literal step order on
`fix/plan-approval-hook-scope` reproduced exactly that mistake: merged and pruned, then got
blocked writing the handoff (`require-feature-branch` has no docs/handoffs exemption). Fixed by
moving "write/validate/commit the handoff" before "ask to merge" in both files; pruning is now
the last substantive step. **You are reading the result of that fix working correctly** — this
handoff itself was written on its own branch, before its own merge, per the corrected order.

`python -m scripts.gate` equivalent run in batches (documented workaround for the still-open
"gate unrunnable in one shot" ledger item, below): ruff check ✓, ruff format --check ✓
(1 file auto-reformatted), mypy ✓ (324 files, 0 issues), pytest — 2018 passed + 1 skipped
across 6 file-batches (non-`ux` tier), plus the `ux` tier: 119 passed + 1 failure
(`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`, the already-characterized
pre-existing scroll-flake — see ledger item 4 below — confirmed clean on isolated re-run,
unrelated to either branch's changes).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger
(`#### Open`); this is the required one-line-each mirror. **14 open, still over the ~8–10
ceiling** — this branch resolved item 14 (below, the old `check-plan-approved` global-scope
gap) and added one new item (the charter-W-1 citation gap), net unchanged.

1. `--reruns 2` on the `ux` CI tier is a masking policy that hid a real 64%-broken test for 11
   runs — fix landed; the reruns-policy question itself is deliberately left open until a real
   post-fix CI sample exists.
2. The quality gate is unrunnable by an agent in one shot (~13 min vs. a 10-command shell cap)
   — a governance hole: an agent will rationalize a partial-green as "probably fine." (This
   session's own gate run needed 6 file-batches + a separate `ux`-tier run — direct, repeated
   confirmation this item is still real.)
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only 30-second
   Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` — a real ~10–20% flake, measured not fixed;
   deterministic-looking values point at an async scroll race, not random jitter. (Hit again
   this session, isolated re-run confirmed clean — consistent with the existing characterization,
   not a new data point worth its own item.)
5. `chore/scrub-local-eval-paths` parked branch — 2 commits, unmerged, gate re-verification
   incomplete (not failed).
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` (~107 files, agent-regenerated) —
   user-facing surface already swept; this remainder deliberately deferred.
7. Compose user-action reloads still fire `loadComposition()` un-awaited — only the five
   auto-arrival cascade fires were awaited by `fix/ci-first-linux-run`.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; left open only for the still-blocked
   `[HUMAN]` Trusted Publisher prerequisite.
9. In-app rendered citation viewer — deliberately deferred; build only if real friction shows
   up (GitHub links suffice for now).
10. Grounding/hallucination metric calibrated layers (L1/L2) — no labeled real data yet;
    scheduled as v1.0.7 Sprint PV-2.
11. Agent-coding-practices kit-adoption staged commitments — cross-cutting deferrals
    (mypy-strict ratchet exit, gate-hardness ratchet-then-block, etc.) kept in one tracked home.
12. 2026-07 efficiency review PX-37..PX-56 aggregate — drains via per-PX-coordinated individual
    branches per `RELEASE_ARC.md` "v1.1.0 close-out — reconciliation."
13. UX round-2 remediation — Wave A (six decision-free findings) landed on
    `fix/round2-quick-wins`; the design-heavy remainder (state-communication unification, etc.)
    is still open.
14. `docs/governance/enforcement.md` (and several memory files) cite "charter W-1" (the
    parallel-session working model) as an existing clause — it does not exist in
    `docs/governance/charter.md` (only C-0…C-9, D-1…D-7). Needs an owner-directed amendment
    ceremony (the same shape as how C-9 was added on `feat/handoff-integrity-kit`) to write the
    actual clause and reconcile the dangling citations.

**Reduction sprint is overdue, not merely due** — the ~8–10 ceiling has been exceeded since
before this session started, and this session (correctly, per its own scope) resolved one item
while discovering another. Strongly consider the reduction sprint as the very next branch.

---

## What this branch should build

This handoff exists solely to record two already-merged branches and hand off cleanly — it
does not mandate a deliverable itself. Per `RELEASE_ARC.md`'s ordered sequence, the next
candidate is **step 3, `fix/compose-unawaited-reloads`** (ledger item 7 above), unless the
owner prefers to run the overdue reduction sprint first (see the note above) or names something
else entirely.

Scope is bounded to whatever the owner confirms next — do not treat this handoff as
authorizing any specific branch by default.

---

## First move

Create branch `<!-- branch-name -->` off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.**

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
   observations` section above**; branches to prune identified. "Done" is the output
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
4. Ask user to confirm merge to `main`; execute merge after confirmation
5. Prune merged branch(es) with the user's OK. Give the user the one-line
   pointer to the handoff file — path + branch + short commit hash — **as
   copyable chat text**, as the **last act** before closing the window.
   Never paste the handoff file's content into chat;
   that reintroduces the corruption channel this pipeline exists to remove.
