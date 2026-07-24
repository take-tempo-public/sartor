<!-- provenance: schema=1 session=fd53a64f-645a-461e-b38b-6571fee4845b branch=feat/context-structure-review-skill commit=7064a8c624f7ab47e5b7e3c49bd12a6364a964e1 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-24 -->

# Agent handoff: `feat/context-structure-review-skill`

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
sequence (steps 11b-17) — it was the final bite of the Agent-coding-practices
kit-adoption arc (a tooling-only side project, running alongside the numbered
sequence since `docs/kit-adoption-arc`, 2026-06-23).
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`docs/compliance-witness-code-claims`~~ ✓ (merged, PR #64) — widened
  `compliance-witness` to code-level docstring/comment claim checking; ledger 11 → 10
- ~~`feat/capture-screenshots-smoke-check`~~ ✓ (merged, PR #65) — implemented the
  periodic drift smoke check for `scripts/capture_screenshots.py`; ledger 10 → 9
- **`feat/context-structure-review-skill`** ← **this branch** — imported the
  `context-structure-review` skill into root `skills/` (kit-adoption Phase 5,
  Decision 5) and, with owner sign-off, **CLOSED the entire kit-adoption ledger
  row** (all three staged commitments now done); ledger 9 → 8
- next branch ← **not directed**; see "What this branch should build" below

**Do not pick any fork item (RELEASE_ARC steps 11b-17) on your own initiative.**

---

## What just landed on `main`

`main` is at `9d78379` (merge of `feat/capture-screenshots-smoke-check`, PR #65).
**This branch has not merged yet** — pending the PR flow below.

**What this branch did (three commits: `c79b916`, `ac4c533`, `7064a8c`):**

1. **Consumed the incoming handoff pointer** (`docs/dev/handoffs/capture-screenshots-smoke-check.md`
   @ `9d78379`) via `check_handoff_pointer.py` then `verify_doc_template.py --event
   consumed` — both passed clean, no C-9 block.
2. **User picked the branch** from the prior handoff's candidate list: the
   `context-structure-review` skill import (kit-adoption Phase 5, Decision 5), over
   the scroll-flake mode-C fix or PX-39.
3. **Imported `skills/context-structure-review/`** — `SKILL.md` +
   `references/criteria.md`, copied from the external agent-coding-practices kit
   (path recorded in `CLAUDE.local.md`). Per an explicit owner choice (over a
   verbatim import or a Callback-only fix), localized both repo-specific refs: the
   old product name (Callback → Sartor) and a cross-reference to a kit file that
   stays external rather than being imported. No plugin-manifest edit needed —
   `skills/` auto-discovers the same way `commands/`/`agents/` already do.
4. **Reconciled four tracking docs** in the same commit: `skills/README.md` (scaffold
   → landed), `kit-adoption-design.md`'s DOC-STATUS comment, `RELEASE_CHECKLIST.md`'s
   kit-adoption ledger row, `CHANGELOG.md` `[Unreleased]`. Phase 5's second
   deliverable (§7 promotable shortlist) was already authored — confirmed present,
   nothing new to add.
5. **Folded in this session's own
   `docs/dev/ledger/fd53a64f-645a-461e-b38b-6571fee4845b.jsonl`** (the `--event
   consumed` record for the incoming handoff pointer) into the first commit, per
   `docs/dev/prov/SPEC.md` §5.
6. **Hit and cleared the wiki-freshness gate** — this branch's own commit tipped the
   file-changed count to 78, crossing the 75-file block threshold (`main` itself was
   at 73, under threshold). Initially asked to run a full cold pass; flagged the
   cost/scope tradeoff (38 existing wiki pages already cover most of the codebase) and
   the user rescoped to a diff pass. Of 78 changed files, only `docs/governance/charter.md`'s
   new W-1/W-2 working-model + amendment-ceremony section was a real content gap —
   updated `docs/wiki/pages/governance-extraction.md` to reflect it. `/wiki-lint`
   gate: **PASS**, 0 errors (38/38 pages indexed, 0 dangling backlinks, 0 orphans, 324
   cites checked / 0 broken). `.last_ingest_sha` advanced `b87ab19` → `c79b916`.
7. **Closed the kit-adoption ledger row entirely** — asked the owner explicitly
   whether commitment (3) needed anything further from the 8.7
   `feat/portable-enforcement-core` window now that the structural four-parallel
   `commands/agents/skills/hooks` end-state was reached; owner confirmed close now.
   `RELEASE_CHECKLIST.md`'s Open count re-counted from actual bullets: 9 → 8.
8. **Updated persistent memory**: `reference-plugin-activation` (skills/ auto-discovery
   confirmed), `project-v110-fork-owner-gated` (ledger 9→8, arc closed, wiki-ingest +
   SQLite-flake notes), and `feedback-schedulewakeup-not-for-background-bash` (a 9th
   recurrence of calling `ScheduleWakeup` near an outstanding background Bash task —
   caught after the fact, self-corrected, did not call it again).

**Gate:** `python -m scripts.gate` (`ruff check .` + `ruff format --check .` + `mypy .`
+ `pytest`) — **all steps passed** on the second of three full runs this session
(`2181 passed, 1 skipped`, no reruns, genuine green — not retry-masked). The first
full run failed at the wiki-freshness test (fixed per item 6 above); a later
standalone full run hit a transient SQLite "database is locked" flake in an unrelated
UX regression test (`test_20260612_corpus_first_landing.py`) — confirmed not caused by
this branch's markdown-only changes by re-running the single test in isolation (passed
cleanly, 41.85s) and by a subsequent clean full run (`2181 passed, 1 skipped`, `gate:
all steps passed.`). **Caution when reading this branch's own background-gate task
notifications:** the shell commands used `cmd; echo "EXIT_CODE=$?"` — the harness's
reported exit code reflects the trailing `echo`, always 0, not the gate's real result;
verify from the log's own `gate: all steps passed.` / `FAILED` line instead, same trap
`reference-background-bash-kill-ceiling` already documents for `| tee`.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward
ledger (`#### Open`). **Rendered open count: 9** (net unchanged this branch — closed
the entire kit-adoption arc row (9 → 8), then filed one new item discovered on this
branch's own PR (8 → 9); verified by counting the actual `- [ ] **` bullets).
One line each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot — makes it unenforceable as
   a single command in some environments. (This session ran it three times
   in the background, ~16-17 min each; no kill this time, but one run hit an
   unrelated transient DB-lock flake — see item 2's sibling note above.)
2. `test_corpus_reload_preserves_scroll_position` is a real ~10-20% flake under CPU
   saturation — measured, not yet fixed. Did not reproduce this session (a
   *different* transient flake — a SQLite lock error in an unrelated test —
   surfaced instead; treated as its own isolated incident, not folded into this item).
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
7. 2026-07 efficiency review — PX-37..PX-56 aggregate; 3 of 20 rows remain (PX-39
   needs the owner's E2E corpus access; PX-44's 44-file rollout is an owner scope
   call; PX-46 is explicitly **owner-gated**, irreversible if botched).
8. Compose-time rewrite latitude — the "generate but don't invent" dial —
   **[OWNER DECISION], evidence-gated**; needs the PX-39 real-corpus run first (see
   item 7); see `COMPOSE_REWRITE_DIAL.md` for full context, not the ledger summary.
9. `docs-site/`'s static-export build flakes on a live `shields.io` badge-image fetch
   timing out at build time (this branch's own PR #66) — not merge-blocking (not one
   of `main`'s required six checks) but will recur on every future PR until fixed;
   solo-closeable (self-host the badge, or make the fetch retry/skip on failure).

**The ceiling is ~8-10 open items; this ledger is at 9** — closed the kit-adoption arc
row entirely this branch, then filed one new solo-closeable item discovered on this
branch's own PR. Of the 9, only item 9 above is freely solo-closeable; the rest are
owner-gated (PyPI/GHCR console access, E2E corpus access, calibration passes,
opportunistic-only sweeps).

---

## What this branch should build

Nothing is formally directed for a next branch by this session. Candidates, in rough
priority order — **none of these is a standing authorization to START**; confirm
with the user which one before picking:

1. **Item #2 (scroll-flake mode C)** — solo-closeable, no owner gate, but large
   (multi-day, mirrors the just-finished mode A/B/D fix's methodology).
2. **PX-39** — unblocked per a prior session's note, not yet run; needs the owner's
   E2E corpus access to actually execute, so it's really owner-gated in practice
   despite being "unblocked" on paper.
3. **Wordmark sweep** (ledger item 3) — explicitly opportunistic-only, not a
   standalone branch; fold into whatever else touches `docs/wiki/` or
   `docs/dev/reviews/` next, don't pick it as the branch itself.

Scope for whichever is picked: bounded to that item alone. **Do not expand into the
fork items** (RELEASE_ARC steps 11b-17).

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
