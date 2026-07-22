<!-- provenance: schema=1 session=649e51e5-7576-45b0-872b-03713c3bda8f branch=chore/dependabot-group-a commit=d41520a actor=amodal1 agent=claude-sonnet-5 generated_at=2026-07-22 -->

# Agent handoff: `chore/dependabot-group-a`

**Branch to create:** none directed by this session — the Dependabot backlog (ledger
item 20) is now fully closed. The next branch is whatever the user directs next; there
is no standing recommendation the way `chore/dependabot-group-a` itself was.
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

**Stream:** v1.1.0 endgame. This branch was the last of the Dependabot dependency-bump
branches (ledger item 20), following `chore/dependabot-docs-site` and
`chore/dependabot-ci-infra`.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`docs/compose-rewrite-dial`~~ ✓ (merged, PR #41) — filed the Dependabot backlog
- ~~`chore/dependabot-docs-site`~~ ✓ (merged, PR #42) — group (d), 5 of 14 PRs
- ~~`chore/dependabot-ci-infra`~~ ✓ (merged, PR #44) — groups (b)/(c), 4 more PRs
- **`chore/dependabot-group-a`** ← **this branch** — group (a), the last 4 PRs
  (#26/#5/#6/#14). **Ledger item 20 now CLOSED, all 14 original PRs accounted for.**
- `#10` (download-artifact) — **not a branch**; still deferred to the v1.1.0 release-tag
  step (RELEASE_ARC step 17), to be handled in lockstep with an `upload-artifact` bump

**Do not pick any fork item (RELEASE_ARC steps 11b-17, other than the #10/step-17 note
above) on your own initiative.**

---

## What just landed on `main`

`main` is at `19081d2` (merge of `chore/dependabot-ci-infra`, PR #44). **This branch has
not merged yet** — pending the PR flow below.

**What this branch did.** Bumped the 4 remaining Dependabot-backlog PRs — the ones that
touch the quality gate itself — with the full local gate this time (not a probe).

1. **#26** `ruff` `0.15.12 → 0.15.22` (`pyproject.toml` line 105) — ruff is
   **deliberately exact-pinned** (see the in-file comment above the pin); `ruff format
   --check .` under the new version: 318 files, **0 reformats**.
2. **#5** `mypy` `<2.0 → <3.0`, resolving to **2.3.0** (itself a MAJOR) — `mypy .`: **0
   errors**, 94 pre-existing `annotation-unchecked` informational notes, identical count
   to the pre-bump baseline (confirms they're pre-existing, not new noise).
3. **#6** `pytest` `<9.0 → <10.0`, resolving to **9.1.1**; **#14**
   `pytest-rerunfailures` `<16 → <17`, resolving to **16.4** — landed together since both
   touch the same `pytest` invocation.

**Re-verification done before touching code (this handoff's own predecessor required
it):** live PyPI queried for all 4 packages — every resolved version matched the prior
session's throwaway-venv probe exactly, no newer patch had shipped. Confirmed Chromium
was installed locally (`%LOCALAPPDATA%\ms-playwright\chromium-1223`) before claiming the
`ux` tier would be validated — it was the probe's one real gap (no Chromium in that
throwaway venv).

**Gate — full run, not a probe:** `ruff check .` ✓ · `ruff format --check .` ✓ (318
files, 0 reformats) · `mypy .` ✓ (0 errors, 94 pre-existing notes) · `pytest` **2180
passed, 1 skipped, 0 failed** in 1317s (22 min) — **including the full `ux`/Playwright
tier**, which the prior probe could not exercise. Run via `python -m scripts.gate >
<scratch>/gate.log 2>&1` (background, no `| tee` — that masks the real exit code); `GATE
EXIT: 0` confirmed from the log, not just the notification summary. No dev server or
long-lived process was started this session.

**Also done this session (doc consistency, not a code change):** the docs-site `npm
audit` finding (7-8 high-severity, pre-existing, unrelated to any Dependabot bump) had
been folded into the Dependabot backlog item's own entry rather than given its own row
("ceiling already breached" at the time). Since that parent item just closed, the
finding was promoted to its own carry-forward ledger row — moving it, not fixing it. Net
open-count effect: **zero** (one item closed, one item opened).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **19 open** (net unchanged this branch — see
above: item 20 closed, the npm-audit sub-finding promoted to its own row).

1. The quality gate is unrunnable by an agent in one shot (~14-22 min) — plus the `| tee`
   exit-code-masking trap.
2. `test_corpus_reload_preserves_scroll_position` + siblings — mode C (~17% under
   saturation) unfixed.
3. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
4. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix.
5. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
6. In-app rendered citation viewer — deliberately deferred.
7. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
8. Agent-coding-practices kit-adoption — external kit source path remains open.
9. 2026-07 efficiency review PX-37..56 — 10 of 13 landed; 3 remain: PX-39 (unblocked, not
   yet run), PX-44 (46-file rollout, step 11b), PX-46 (owner-gated).
10. `enforcement.md` + memories cite "charter W-1" as an existing clause; it does not exist.
11. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
12. `.cb-panel` collapse animation likely snaps rather than eases — owner decision.
13. A mobile `.panel-body` padding override is already shadowed/dead — verify, then decide.
14. `block-merge-to-main`'s pre-merge-worktree bug — dissolved; entry retained for the lesson.
15. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately unchanged.
16. Claude Code CLI sessions/processes don't terminate when closed — `[HUMAN/OWNER]`.
17. `compliance-witness` doesn't verify code-level claims or re-sweep for defect-class
    recurrence — **[OWNER DECISION]**.
18. Compose-time rewrite latitude — the "generate but don't invent" dial. Points at
    `COMPOSE_REWRITE_DIAL.md`. Evidence-gated on PX-39.
19. **`npm audit` on `docs-site/` reports 7-8 high-severity findings** (`sharp`/`next`,
    `fast-uri`/`ajv`) — pre-existing, confirmed unrelated to any Dependabot bump; needs
    its own dedicated `next`/`sharp` upgrade branch. Newly split into its own row this
    branch (was folded into the now-closed Dependabot backlog item).

**RESOLVED this branch, dropped from the count:** ledger item 20, "Dependabot backlog —
14 open PRs" — all 14 now accounted for (9 prior + 4 here + #10 deferred to release).
Its own `#### Resolved` entry retains the full group (a)/(b)/(c)/(d) history.

**Reduction sprint is badly overdue** — ceiling ~8-10, this is 19, unchanged from the
prior handoff (closing one item and opening another nets to zero — see above; this was
NOT a missed opportunity to reduce, the npm-audit finding is a real, still-unresolved
issue that would have been silently lost otherwise).

---

## What this branch should build

Nothing is directed for a next branch by this session. The Dependabot backlog (the
multi-branch effort this handoff's lineage — `docs/compose-rewrite-dial` →
`chore/dependabot-docs-site` → `chore/dependabot-ci-infra` → `chore/dependabot-group-a`
— has been tracking) is now fully closed. Candidates for the next branch, in rough
priority order per the open ledger above, but **none of these is a standing
authorization** — pick with the normal plan-mode ceremony:

1. **The overdue reduction sprint itself** (19 open items, ceiling ~8-10) — several of
   the 19 are owner-gated or owner-decision items that may simply need the owner's
   attention rather than more engineering (items 7, 9's PX-46, 11, 12, 13, 15, 16, 17).
2. **The newly-split npm audit finding** (item 19 above) — its own dedicated
   `next`/`sharp` upgrade branch, out of scope for anything Dependabot-shaped.
3. **PX-39** (item 9) — unblocked per a prior session's note, not yet run.

Scope for whichever is picked: bounded to that item alone. **Do not expand into the
fork items** (RELEASE_ARC steps 11b-17, except #10's own step-17 handling at release
time).

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
   observations` section above**; branches to prune identified; **any dev server or
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
