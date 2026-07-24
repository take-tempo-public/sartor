<!-- provenance: schema=1 session=98c376df-abd1-45a8-b218-3f9ebe5ecd55 branch=feat/capture-screenshots-smoke-check commit=830aa31 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-23 -->

# Agent handoff: `feat/capture-screenshots-smoke-check`

**Branch to create:** none directed by this session — see "What this branch should
build" below for candidates.
**Base branch:** `main` (once this branch has merged)

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

**Stream:** v1.1.0 endgame. This branch is NOT part of the RELEASE_ARC numbered branch
sequence (steps 11b-17) — it is a tooling-only bite of the overdue reduction sprint,
continuing directly from the immediately-prior branch.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`chore/reduction-sprint-ledger-compose-notes`~~ ✓ (merged, PR #58) — first bite of
  the reduction sprint: triaged all 19 open items, resolved 3, ledger 19 → 16
- ~~`fix/panel-css-cascade-residuals`~~ ✓ (merged, PR #59) — owner walk-through of every
  remaining owner-gated ledger item; resolved 4 (#11, #12, `enforce_admins`,
  Claude Code CLI orphaned-process); recorded owner decisions on 6 more; ledger 16 → 12
- ~~`docs/charter-w1-amendment`~~ ✓ (merged, PR #60) — authored the real charter W-1,
  W-2, and Amendment-ceremony sections (ledger item #9 / F-gov-03); ledger 12 → 11
- ~~`docs/compliance-witness-code-claims`~~ ✓ (merged, PR #64) — widened
  `compliance-witness` to code-level docstring/comment claim checking; ledger 11 → 10
- **`feat/capture-screenshots-smoke-check`** ← **this branch** — implemented the
  periodic drift smoke check for `scripts/capture_screenshots.py` (ledger item #9 /
  RELEASE_CHECKLIST bullet); ledger 10 → 9
- next branch ← **not directed**; see "What this branch should build" below

**Do not pick any fork item (RELEASE_ARC steps 11b-17) on your own initiative.**

---

## What just landed on `main`

`main` is at `19d37e2` (merge of `docs/compliance-witness-code-claims`, PR #64). **This
branch has not merged yet** — pending the PR flow below.

**What this branch did (single commit `830aa31`):**

1. **Consumed the incoming handoff pointer** (`docs/dev/handoffs/compliance-witness-code-claims.md`
   @ `19d37e2`) via `check_handoff_pointer.py` then `verify_doc_template.py --event
   consumed` — both passed clean, no C-9 block.
2. **User picked the branch** from the prior handoff's candidate list (via
   `AskUserQuestion`): the `capture_screenshots.py` periodic smoke check, not the
   `context-structure-review` skill import or the scroll-flake mode-C fix.
3. **User picked the cadence** (via `AskUserQuestion`, since the owner decision on
   record only said "pre-tag or monthly"): monthly cron + manual `workflow_dispatch`,
   decoupled from `release.yml`.
4. **Added `--smoke` to `scripts/capture_screenshots.py`** — runs the setup phases +
   `run_step1` (paths where all three historical staleness bugs lived, plus the
   single most representative LLM round-trip, the Analyze Sonnet call) then stops,
   skipping Steps 2-6 and the cover letter. Cleanup still runs. Module docstring
   updated with the new usage line and the rationale.
5. **Added `.github/workflows/capture-smoke.yml`** — standalone scheduled workflow
   (mirrors `codeql.yml`/`scorecard.yml` being separate for the same reason: it's
   schedule/dispatch-only, never runs on push/PR). Reuses
   `./.github/actions/setup-python-env`, copies the `ux` job's Chromium-cache block
   verbatim, backgrounds `python app.py` (which auto-disables its reloader/browser-open
   under CI via `_is_ci_or_container()`), waits for `:5000`, runs
   `capture_screenshots --headless --smoke`, uploads the Step-1 PNGs as an artifact.
   `ANTHROPIC_API_KEY` from the existing repo secret (same one `eval-smoke` uses).
6. **Verified locally, end-to-end, with the owner's explicit go-ahead for the real
   spend**: started `python app.py`, ran `python -m scripts.capture_screenshots
   --headless --smoke` against it. Exited 0, printed "--smoke: stopping after Step 1",
   captured the 3 Step-1 PNGs, cleaned up the demo user. **Caught and reverted an
   unintended side effect of its own**: the verification run regenerated 5 tracked
   `docs/screenshots/*.png` files in place (the script's normal behavior) — those were
   `git checkout --`'d back to their committed state before commit, since this branch's
   scope is the tooling, not a screenshot refresh.
7. **Added a `CHANGELOG.md` `[Unreleased]` entry** documenting the new flag + workflow
   and their cadence/cost.
8. **Closed the ledger item** in `RELEASE_CHECKLIST.md` (`[x]` + a dated RESOLVED note
   citing the owner's cadence choice) and decremented the rendered open count (10 → 9,
   re-counted the actual `- [ ] **` bullets between `#### Open` and `#### Resolved` per
   the ledger's own anti-drift rule — confirmed 9, not trusted arithmetic).
9. **Updated persistent memory** (`project-v110-fork-owner-gated.md`): reconciled the
   memory's own stale ledger-count history (last updated at 16, four resolutions
   behind reality) up through this session's 10 → 9, and flagged explicitly that the
   new CI job's real LLM spend is intentional design, not a mistake to "fix" later.
10. **Folded in this session's own
    `docs/dev/ledger/98c376df-abd1-45a8-b218-3f9ebe5ecd55.jsonl`** (the `--event
    consumed` record for the incoming handoff pointer) into this branch's only commit,
    per `docs/dev/prov/SPEC.md` §5.

**Gate:** `python -m scripts.gate` (`ruff check .` + `ruff format --check .` + `mypy .`
+ `pytest`) — **all steps passed**, 0 failures. `pytest`: **2181 passed, 1 skipped**
(1231.82s / ~20:32). No `--reruns` in play for this invocation (`pyproject.toml`
`addopts` carries none; reruns are CI-`ux`-tier-only), so this is a genuine,
unmasked green result, not a retry-hidden one. The CPU-saturation scroll-flake family
(`[[project-ux-scroll-flake-chip0]]`, ledger item #2) did **not** reproduce this run.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward
ledger (`#### Open`). **Rendered open count: 9** (down from 10 — this branch resolved
the `capture_screenshots.py` item; verified by counting the actual `- [ ] **` bullets).
One line each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot — makes it unenforceable as
   a single command in some environments. (This session's own gate run took ~1232s
   (20:32) in the background and needed the same output-file-read handling — see
   `[[reference-background-bash-kill-ceiling]]`. Completed clean this time.)
2. `test_corpus_reload_preserves_scroll_position` is a real ~10-20% flake under CPU
   saturation — measured, not yet fixed. (This session's own gate run did NOT hit the
   sibling flake this time — 0 failures, 2181 passed.)
3. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — the ledger's own
   remedy explicitly vetoes a standalone bulk-rewrite branch; fold in
   opportunistically only.
4. PyPI wheel not installable — data files not packaged (**RESOLVED-PENDING-PUBLISH**;
   needs a real publish to confirm; **owner-gated**, PyPI/GHCR console access, blocked
   on the GitHub repo rename).
5. In-app rendered citation viewer — reaffirmed deferred; owner confirms no friction
   signal yet.
6. Grounding / hallucination metric — calibrated layers (B), not yet built
   (**owner-gated**, manual annotation + threshold-setting pass).
7. Agent-coding-practices kit-adoption — kit source path found + confirmed
   (`/c/Dev/lichen/projects/agent-coding-practices-kit/`, recorded in
   `CLAUDE.local.md`) — unblocks but does not complete the `context-structure-review`
   skill import (Phase 5, Decision 5); that import is still its own future branch.
8. 2026-07 efficiency review — PX-37..PX-56 aggregate; 3 of 20 rows remain (PX-39
   needs the owner's E2E corpus access; PX-44's 44-file rollout is an owner scope
   call; PX-46 is explicitly **owner-gated**, irreversible if botched).
9. Compose-time rewrite latitude — the "generate but don't invent" dial —
   **[OWNER DECISION], evidence-gated**; needs the PX-39 real-corpus run first (see
   item 8); see `COMPOSE_REWRITE_DIAL.md` for full context, not the ledger summary.

**The ceiling is ~8-10 open items; this ledger is now at 9** — under the ceiling for
the first time in this reduction sprint. All remaining items are owner-gated (PyPI/GHCR
console access, E2E corpus access, calibration passes, opportunistic-only sweeps) —
none is solo-closeable without an owner decision or access this session doesn't have.

---

## What this branch should build

Nothing is formally directed for a next branch by this session. Candidates, in rough
priority order — **none of these is a standing authorization to START**; confirm
with the user which one before picking:

1. **`context-structure-review` skill import** (ledger item 7, kit-adoption Phase 5,
   Decision 5) — unblocked (kit path in `CLAUDE.local.md`). Read
   `docs/dev/kit-adoption-design.md` §7 Phase 5 and `skills/README.md` first.
2. **Item #2 (scroll-flake mode C)** — solo-closeable, no owner gate, but large
   (multi-day, mirrors the just-finished mode A/B/D fix's methodology).
3. **PX-39** — unblocked per a prior session's note, not yet run; needs the owner's
   E2E corpus access to actually execute, so it's really owner-gated in practice
   despite being "unblocked" on paper.
4. **Wordmark sweep** (ledger item 3) — explicitly opportunistic-only, not a
   standalone branch; fold into whatever else touches `docs/wiki/` or
   `docs/dev/reviews/` next, don't pick it as the branch itself.

Scope for whichever is picked: bounded to that item alone. **Do not expand into the
fork items** (RELEASE_ARC steps 11b-17).

**Process note for whoever picks next:** per the rule at
`docs/dev/prov/SPEC.md` §5 step 3, when you consume this handoff you will write
your own `docs/dev/ledger/<session>.jsonl` on `main` before creating any branch. Do
not open a dedicated branch for it — fold its commit into the first commit of
whichever candidate branch above (or other directed work) you create next.

---

## First move

Whatever branch is picked next: write a plan at `~/.claude/plans/<slug>.md` and show it
to the user before touching any code. **Do not code first.**

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
