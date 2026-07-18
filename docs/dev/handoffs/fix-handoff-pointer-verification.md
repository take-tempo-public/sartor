<!-- provenance: schema=1 session=7b8ec7a5-b109-400b-ae10-bedc4041e5f9 branch=fix/handoff-pointer-verification commit=3758d8e actor=amodal1 agent=claude-sonnet-5 generated_at=2026-07-18 -->

# fix/handoff-pointer-verification handoff — 2026-07-18

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

**Stream:** this branch is **outside** `RELEASE_ARC.md`'s "v1.1.0 close-out —
reconciliation" numbered sequence — an ad-hoc fix triggered mid-session by the
user noticing a fabricated commit hash in the handoff pointer they'd just been
handed, not a pre-planned step. Same precedent as `feat/handoff-integrity-kit`
(also unlisted there).
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice) — unaffected by this branch's own
out-of-sequence status.
**Blocked until this stream tags:** nothing downstream is gated on this step.

- ~~`docs/v110-plan-reconciliation`~~ ✓ — step 1 of the numbered sequence
- ~~`fix/plan-approval-hook-scope`~~ ✓ — step 2 of the numbered sequence
- **`fix/handoff-pointer-verification`** ← this branch, NOT numbered-sequence step 3
- `fix/compose-unawaited-reloads` ← still the actual next numbered-sequence
  step (ledger item 7) — do not start it on this branch
- The overdue reduction sprint (ledger stayed at 14 open, over the ~8–10
  ceiling, through this branch too — see below) is still a live candidate for
  "what's next," per the prior handoff's own recommendation

Do not treat this handoff as authorizing `fix/compose-unawaited-reloads` or
the reduction sprint by default — the owner picks the next branch.

---

## What just landed on `main`

**Not yet merged as of this handoff** — `fix/handoff-pointer-verification` is
still open, branched off `main` at `3758d8e` (the tip of
`fix/plan-approval-hook-scope`'s own close-out chain, including its stranded
handoff-commit branch). Full detail: [[project-handoff-pointer-verification]]
memory, [`diagnosis/handoff-pointer-verification.md`](../diagnosis/handoff-pointer-verification.md).

**The defect:** the branch close-out checklist's step 5 pointer line
(`Handoff: <path> @ <branch> (<short-hash>)`) — the ONE thing that reliably
crosses from a closing session into the next one — had its commit hash
hand-typed from memory, with nothing forcing or checking it, unlike the
handoff FILE it points to (already fingerprint/provenance-verified). Proven
fabricated, not theorized: this session received pointer `Handoff:
docs/dev/handoffs/fix-plan-approval-hook-scope.md @ main (0d7fe1a)`;
`0d7fe1a` does not exist anywhere in the repo (confirmed via `git cat-file`,
`git rev-list --all`, `git reflog`, and a fetch-and-diff against
`origin/main`). Reading the prior session's own transcript
(`~/.claude/projects/C--Dev-sartor/ccd0dad5-....jsonl`) found the string
exactly once — in the model's own generated closing text, present in no tool
call or tool result — immediately after a `git merge --no-ff` whose stdout is
a diffstat with no hash in it. `git show --stat 3758d8e` confirmed the real
hash that should have been cited.

**The fix:** new `scripts/print_handoff_pointer.py` generates the pointer
line from `git` directly (branch + short HEAD hash), refusing to print
anything for a handoff doc not yet committed and reachable at HEAD. New
`scripts/check_handoff_pointer.py` independently re-verifies a pointer line
against git state (cited commit exists, doc present in its tree, commit is an
ancestor of the named branch) — run on both ends per the user's own framing
mid-session: *"it's not guaranteed unless we enforce method and then check."*
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`, `AGENTS.md`, and
`docs/dev/handoffs/README.md` now mandate both scripts in place of a
hand-typed line. New regression suite `tests/test_handoff_pointer.py` (11
tests, subprocess-level against both real scripts in a throwaway git repo).
Manually verified against the real bug: `print_handoff_pointer.py` on the
prior handoff now prints the correct `3758d8e`; `check_handoff_pointer.py`
accepts that and rejects the original `0d7fe1a` with `commit not found`.

`python -m scripts.gate` equivalent run in batches (the still-open
"gate unrunnable in one shot" ledger item, unchanged by this branch): ruff
check ✓, ruff format --check ✓ (1 file auto-reformatted), mypy ✓ (327 files,
0 issues), pytest — 2028 passed across 6 non-`ux` batches, plus the `ux`
tier split regression/a11y/flows: 108 + 5 + 6 passed, 1 failure
(`test_restore_scroll_y_loses_to_post_restore_growth`, the
already-characterized pre-existing scroll-flake — see
[[project-ux-scroll-flake-chip0]] — confirmed clean on isolated re-run,
unrelated to this branch's changes).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger
(`#### Open`); this is the required one-line-each mirror. **14 open, still over the ~8–10
ceiling** — this branch found and fixed its own item within itself (never entered `#### Open`),
so the count is unchanged from the prior handoff.

1. `--reruns 2` on the `ux` CI tier is a masking policy — fix landed; the reruns-policy
   question itself is deliberately left open until a real post-fix CI sample exists.
2. The quality gate is unrunnable by an agent in one shot (~13 min vs. a 10-command shell cap)
   — a governance hole. (Hit again this session — 6 batches + a separate 3-way `ux` split —
   direct, repeated confirmation this item is still real.)
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only 30-second
   Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` (and sibling scroll-restore tests) — a real
   ~10–20% flake, measured not fixed. (Hit again this session under a different test name,
   `test_restore_scroll_y_loses_to_post_restore_growth` — isolated re-run confirmed clean,
   consistent with the existing characterization.)
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
    ceremony to write the actual clause and reconcile the dangling citations.

**Reduction sprint is overdue, not merely due** — the ~8–10 ceiling has been exceeded since
before the prior handoff, and this branch (correctly, per its own scope) neither resolved nor
added a tracked item — it fixed a defect found and closed entirely within its own lifetime.
Strongly consider the reduction sprint as the very next branch.

---

## What this branch should build

This handoff exists solely to record `fix/handoff-pointer-verification` and hand off cleanly —
it does not mandate a deliverable itself. Per `RELEASE_ARC.md`'s ordered sequence, the next
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
5. Prune merged branch(es) with the user's OK. Generate the one-line
   pointer with `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   [`diagnosis/handoff-pointer-verification.md`](diagnosis/handoff-pointer-verification.md)).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
