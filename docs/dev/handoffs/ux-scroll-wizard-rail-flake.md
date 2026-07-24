<!-- provenance: schema=1 session=7c81c254-8e29-4965-b77f-815ce9ae8f83 branch=fix/ux-scroll-wizard-rail-flake commit=73c8505 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-24 -->

# Agent handoff: `fix/ux-scroll-wizard-rail-flake` (mid-branch continuation)

**Branch to create:** none — **continue on the existing
`fix/ux-scroll-wizard-rail-flake` branch** (already exists, 2 commits ahead
of `main`; check it out, do **not** create a new branch or start a new
`fix/*` dossier).
**Base branch:** N/A — this is a mid-investigation handoff on an unmerged
branch, not a fresh branch off `main`. The user is deliberately starting a
new session (different model) to continue the SAME open investigation.

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

**For THIS branch specifically, read before anything else in this
section:** `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md` (this
branch's own dossier — the `restore-evidence` hook should already have
replayed its `## Observed` + `## Falsified` sections into your fresh
context automatically; read the full file anyway, since `## Inferred` and
`## Falsification` are deliberately NOT auto-replayed and contain the
actual next step).

**Stream:** v1.1.0 endgame — this branch is a solo-closeable carry-forward
ledger item (mode C of the scroll-position flake), **not** part of the
RELEASE_ARC numbered fork sequence (steps 11b-17).
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`feat/context-structure-review-skill`~~ ✓ (merged, PR #66, `main` @
  `889650a`) — imported the `context-structure-review` skill, closed the
  entire kit-adoption arc; ledger 9 → 8, then +1 for a self-filed follow-on
  (docs-site badge-fetch flake) → 9
- **`fix/ux-scroll-wizard-rail-flake`** ← **this branch, IN PROGRESS, NOT
  ready to close.** Investigating scroll-flake "mode C" (the last of four
  failure modes of `test_corpus_reload_preserves_scroll_position`; modes
  A/B/D were fixed on the prior `fix/ux-scroll-position-flake` branch).
  Picked from the prior handoff's candidate list ("Item #2, scroll-flake
  mode C") after the owner selected it via AskUserQuestion.
- next branch ← not directed; do not start anything else until this one
  either lands a real fix or the owner explicitly redirects.

**Do not pick any fork item (RELEASE_ARC steps 11b-17) on your own
initiative. Do not start a different ledger item either — this branch is
not done.**

---

## What just landed on `main`

Unchanged since the last merge: `main` is at `889650a` (merge of PR #66).
**Nothing has merged since** — this handoff is entirely about THIS branch's
own in-progress state, not a base-branch update.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s
Carry-forward ledger (`#### Open`). **Rendered open count: 9** (unchanged
this session — this branch is investigating ledger item 2's mode-C
follow-on but has not yet closed it). One line each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot (~15-25min,
   background-Bash kill risk around 5-10min) — makes it unenforceable as a
   single command in some environments.
2. `test_corpus_reload_preserves_scroll_position` mode-C follow-on — **this
   branch's own subject.** Not yet fixed; see "## The fix" status below.
3. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic
   fold-in only, not a standalone branch.
4. PyPI wheel not installable — **RESOLVED-PENDING-PUBLISH**, owner-gated
   (PyPI/GHCR console access, blocked on the GitHub repo rename).
5. In-app rendered citation viewer — deferred, no friction signal yet.
6. Grounding / hallucination metric (calibrated layers B) — owner-gated
   (manual annotation + threshold-setting pass).
7. 2026-07 efficiency review (PX-37..56) — 3 of 20 rows remain, all
   owner-gated (E2E corpus access / scope calls / irreversible-if-botched).
8. Compose-time rewrite latitude dial — [OWNER DECISION], evidence-gated on
   item 7's PX-39 run.
9. `docs-site/`'s shields.io badge-fetch build flake — solo-closeable, not
   merge-blocking, will recur on every future PR until fixed.

**The ceiling is ~8-10 open items; this ledger is at 9.** Only items 2
(this branch) and 9 are freely solo-closeable right now.

---

## What this branch should build

**Continue the mode-C investigation — do not start over, do not pick a
different item.** Concretely, in order:

1. **Read `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md` in full**,
   especially `## Inferred` and `## Falsification` (the sections NOT
   auto-replayed by the SessionStart hook). The short version: the
   approved fix from the prior session (route the wizard rail's
   `scrollIntoView` through `prefers-reduced-motion`) was **falsified by a
   direct A/B against the real target test** (control ~33% n=6 vs.
   with-fix ~62% n=8 failure rate — the fix made it WORSE). A
   frame-by-frame trace showed the true mechanism is `scrollIntoView`
   being clamped by the document's own max-scroll bound
   (`scrollHeight − viewportHeight`), not an animation-duration race as
   first assumed.
2. **Next falsification round (owner-selected, not yet run):** hold page
   height / viewport height fixed and directly test the clamp hypothesis —
   force `scrollHeight − viewportHeight` to land exactly at vs. away from
   the test's own baseline value, and confirm corruption only occurs in
   the "away from" case. The dossier's own `## Falsification` section has
   the fuller writeup of this and an alternative fix-shape hint (extending
   the existing `_scrollInterruptGen` generation-counter guard, which
   already wraps `scrollIntoView` at `app.js:5551-5554`, to also protect a
   plain baseline read the same way it protects a `refreshCorpus` capture
   — rather than changing the wizard's own scroll call at all).
3. **Whatever fix candidate you reach, A/B it against the REAL target
   test** (`test_corpus_reload_preserves_scroll_position`, ≥6-8 runs each
   side, both conditions) **before trusting it** — not just the isolated
   forced-ordering instrument
   (`test_wizard_render_firing_after_baseline_creeps_it`). The isolated
   instrument passing is necessary but was NOT sufficient last time; it
   missed the regression the real test caught immediately. This is the
   single most important lesson from this session — see the feedback
   memory `feedback-ab-fix-against-real-test-not-just-instrument` if your
   memory system carries it forward.
4. Once a fix survives that A/B cleanly (materially lower failure rate,
   ideally near-zero, on both the isolated instrument AND the real test),
   flip the falsifying test(s) into regression tests (the O-10/O-11
   "flip" pattern the prior `fix/ux-scroll-position-flake` branch used),
   update the dossier's `## The fix` / `## Acceptance bar` sections, run
   the full quality gate, and proceed through the normal close-out
   checklist below.

**Reference: 2 tests already exist in
`tests/ux/regression/test_20260708_busy_states_and_chip.py`** from this
session's own instrument work (both still present, committed, and
correctly reflect the CURRENT understanding — no revert needed):
- `test_wizard_render_smooth_scroll_creeps_explicit_baseline` — falsified
  ordering (O-1), stays green, useful negative-space coverage.
- `test_wizard_render_firing_after_baseline_creeps_it` — the confirmed
  forced-ordering instrument (O-2), currently asserts the BUG (expected to
  fail on `HEAD` until a real fix lands — this is intentional, matching
  the dossier's own falsification-test convention, not a broken test to
  "fix" by weakening its assertion).

Scope is bounded to mode C of `test_corpus_reload_preserves_scroll_position`
(ledger item 2). Do not expand into other carry-forward items or RELEASE_ARC
fork items.

---

## First move

Do **not** create a new branch — `git checkout fix/ux-scroll-wizard-rail-flake`
(it already exists locally with 2 commits: `2284e0a` instrument, `73c8505`
falsification docs). Read the dossier in full, then either continue
directly (this is a research/instrument continuation, not a fresh
feature — the existing plan-mode approval already covers "investigate and
fix mode C") or write an updated plan at `~/.claude/plans/<slug>.md` if the
new falsification round changes the shape of the work enough to warrant
re-confirming with the user. **Do not silently implement a new fix without
A/B-testing it against the real target test first** — see item 3 above.

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
