<!-- provenance: schema=1 session=88ee0376-1e46-4f1f-b1a3-d7cca4290ceb branch=chore/merge-channel-alignment commit=6b03591 actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-19 -->

# Agent handoff: `chore/merge-channel-alignment`

**Branch to create:** `chore/scrub-local-eval-paths` — it already exists as a parked branch;
**rebase it onto current `main`**, gate it, land it. This is step 6 of the numbered sequence.
Confirm with the owner before starting, per one-branch-per-session.
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

**Stream:** step 5 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream was gated on this step, but every
future branch's close-out now follows the flow this one documents.

- ~~`docs/v110-plan-reconciliation`~~ ✓ step 1
- ~~`fix/plan-approval-hook-scope`~~ ✓ step 2
- ~~`fix/compose-unawaited-reloads`~~ ✓ step 3
- ~~`refactor/css-cascade-collapse`~~ ✓ step 4 (PX-51; merged `6b03591`)
- **`chore/merge-channel-alignment`** ← this branch, step 5
- `chore/scrub-local-eval-paths` ← step 6, **next** (rebase the parked branch, gate, land)
- `chore/config-drift-batch` (PX-47) ← step 7
- `chore/hook-dispatcher` (PX-37) ← step 8; **coordinate** — it also touches the
  enforcement core this branch just edited

Steps 5 and 6 were **inserted** on 2026-07-19 (owner-directed); old steps 5-15 renumbered to
7-17. Do not start anything past step 6 on this branch.

---

## What just landed on `main`

`main` is at `6b03591` (merge of `refactor/css-cascade-collapse`). **This branch has not
merged** — that is pending the owner's confirmation and the PR flow described below.

**What this branch did.** Two merge channels were running at once and **the documented one
does not work.** `main` carries branch protection requiring a PR plus six passing status
checks (`strict: true`), so the local `git merge --no-ff` + `git push origin main` close-out
that `AGENTS.md` step 4 and the handoff template both prescribed is **rejected by the
platform** for a non-admin, and silently bypasses those six checks for an admin. Every
close-out had been improvising around it.

Already paid for, three ways: `origin/main` sat **14 commits behind** local `main` across five
branches; the wiki checkpoint `9f3c800` was left **orphaned** (in no branch, content-identical
twin `0e5b9c8` on `main` under a different author name — a GitHub-side re-author); and step 4
could not close through the documented flow at all.

Changes:
- **`AGENTS.md` close-out steps 4-5 + the handoff template's verbatim copy** rewritten to the
  real flow: push → PR → required checks green → **merge commit** → `git pull --ff-only` →
  regenerate + verify pointer → prune. Fixes two ordering bugs: the pointer must be
  regenerated **before** pruning (it has to cite `main`), and `--ff-only` is now mandated so a
  divergence fails loudly instead of silently creating a merge commit.
- **`block_merge_to_main`'s wiki arm re-scoped to push-only.** A local merge publishes
  nothing, so it no longer carries a freshness gate; a direct push does, so it keeps one; the
  PR merge is gated in CI, where `tests/test_wiki_freshness_gate.py` runs inside the required
  `Lint, type-check, test` check and evaluates the PR's **merge ref** — the post-merge state
  the local hook could not see. Two regression tests pin both halves.
- **Ledger item 18 dissolved, not patched.** The union-drift fix designed the previous day
  (measured ALLOW 6 / BLOCK 80 on real refs) is deliberately **not** implemented: its premise —
  that a local merge to `main` is a legitimate channel — was false.
- **Scheduling:** steps 5 and 6 added to `RELEASE_ARC.md`; ledger item 5 moved **parked →
  scheduled**; a new item filed for the `enforce_admins` owner decision.

**Owner-applied the same day (do not redo):** squash merging disabled
(`squashMergeAllowed: false`; rebase already `false`) → merge commit is the only method, making
the commit-orphaning class structurally impossible.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ (313 files) · `mypy .` ✓ (328 files) ·
`pytest -m "not ux"` **2029 passed, 1 skipped** · `pytest -m ux` **121 passed**. Run in chunks
(see the note under ledger item 2 below); **no reruns anywhere**, so no masked failures.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`); this
is the required one-line-each mirror. **19 open** (verified by direct `grep -c '^- \[ \]'`).
This branch added one (19) and reclassified two without closing them (5 → scheduled, 18 →
dissolving).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a 64%-broken test for 11 runs.
   Bug fixed; the retry-policy decision is deliberately open pending a real post-fix CI sample.
2. The quality gate is unrunnable by an agent in one shot — worked around by chunking again
   here. **Read this before running the gate** (see the note after this list).
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings — modes B/D fixed; mode C (~17%
   under saturation) unfixed. A controlled baseline A/B on step 4 cleared the CSS refactor of a
   related failure and found a `before == 0` signature outside the A/B/C/D taxonomy.
5. `chore/scrub-local-eval-paths` — **no longer parked; SCHEDULED as step 6 (your next
   branch).** Private-clone + personal paths still live on the public repo.
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
7. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
9. In-app rendered citation viewer — deliberately deferred.
10. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
11. Agent-coding-practices kit-adoption staged commitments.
12. 2026-07 efficiency review PX-37..PX-56 — 8 of 13 land; 5 remain (PX-37/39/44/46/47).
13. UX round-2 remediation — design-heavy remainder is the unscheduled UX Cohesion Epic.
14. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
15. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
16. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
17. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
18. `block-merge-to-main`'s pre-merge-worktree bug — **being dissolved by this branch**; the
    entry is retained for the lesson (the first fix design measured drift along the source
    branch alone and wrongly ALLOWED a stale merge).
19. **NEW — [OWNER DECISION]** `enforce_admins: false` on `main`, so the six required checks
    stay bypassable. Deliberately not changed: it closes the bypass but removes the ability to
    push a hotfix when CI itself is broken.

**Reduction sprint is badly overdue** — the ceiling is ~8-10 and this is 19. Items 6, 9, and
possibly 3 look cheap. Landing step 6 clears item 5.

**Gate-running note (ledger item 2), read before you run it.** Background commands get killed at
inconsistent points — 58% through pytest once, then instantly on an identical retry, then at 9%;
a long-stable dev server died at the same moment as a fresh gate run, which points at an
environment-wide event rather than a per-command ceiling. **Foreground calls survived reliably
where identical backgrounded ones were killed.** Chunk from the start: `split -n l/6` over
`tests/test_*.py` for the non-UX tier, and `tests/ux/` by subdirectory (plus splitting the
largest regression chunk) for the UX tier. Do not retry the full gate hoping it survives.

---

## What this branch should build

This handoff records `chore/merge-channel-alignment`'s close-out. Your branch is **step 6**:

**`chore/scrub-local-eval-paths`** — the parked branch already exists (2 commits, `71ef57f` +
`5e84d3b`, branched 2026-07-14 off `98da67a`). Rebase it onto current `main`, gate it, land it.

1. **Verify the exposure is still live first** (it was at `6b03591`) — and note the **grep
   trap**: the `db/models.py` path is double-escaped inside a raw docstring
   (`C:\\Users\\iam\\...`), so a natural pattern like `grep "Users.iam"` returns nothing and
   reads as "already fixed." That cost a false all-clear once. Use a distinctive literal
   (`grep -n "rosy-chasing-pinwheel" db/models.py`) and check against `main`, never the branch.
2. **Rebase onto `main`.** The ledger's old claim that it is "current with `main`, no rebase
   needed" is **stale** — `main` has moved a long way, and the branch touches `CHANGELOG.md`,
   which later branches (including this one) also edited. **Expect a conflict there.**
3. **Gate it properly.** The original stall was "gate re-verification incomplete — *not
   failed*": a full-suite run was interrupted at 95-96% when the session froze. Finish that run.
4. **Do not attempt a git-history rewrite.** Merging cleans the working tree only; the strings
   remain in public history, including inside `71ef57f` (the scrub commit itself). That is a
   separate, sign-off-gated owner decision — surface it, do not act on it.
5. Clears carry-forward ledger item 5. Prior analysis: `[[project-scrub-local-eval-paths-parked]]`.

Scope is bounded to step 6 in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Create branch `chore/scrub-local-eval-paths` off `main`, write a plan
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
