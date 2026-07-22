<!-- provenance: schema=1 session=78adabd4-4557-4859-8303-f50a87166001 branch=chore/docs-site-npm-audit commit=0ce56b6 actor=amodal1 agent=claude-sonnet-5 generated_at=2026-07-22 -->

# Agent handoff: `chore/docs-site-npm-audit`

**Branch to create:** none directed by this session — see "What this branch should build"
below for candidates, chief among them the new `[URGENT]` item this branch itself filed.
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
sequence (steps 11b-17) — it is a one-off item picked from the RELEASE_CHECKLIST
carry-forward ledger (item 19, the docs-site `npm audit` finding), per the same pattern
as its two immediate predecessor branches.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`docs/record-orphaned-ledger-event`~~ ✓ (merged, PR #46)
- ~~`docs/record-handoff-consumed-event`~~ ✓ (merged, PR #47) — also landed the
  fold-the-ledger-commit-into-the-next-branch process fix this branch is the first to
  actually exercise (see below)
- **`chore/docs-site-npm-audit`** ← **this branch** — closed the docs-site `npm audit`
  carry-forward item (`sharp`/`fast-uri` overrides + a `next` patch bump), AND discovered
  (did not fix) a separate, currently-live production outage: `docs-site/`'s build has
  failed on every push to `main` for 5 consecutive merges
- next branch ← **not directed**; the new `[URGENT]` item this branch filed is the
  strongest candidate — see "What this branch should build" below

**Do not pick any fork item (RELEASE_ARC steps 11b-17, other than the #10/step-17 note in
`chore/dependabot-group-a`'s own handoff) on your own initiative.**

---

## What just landed on `main`

`main` is at `0ce56b6` (merge of `docs/record-handoff-consumed-event`, PR #47). **This
branch has not merged yet** — pending the PR flow below.

**What this branch did:**

1. **Closed the docs-site `npm audit` carry-forward item.** A live `npm audit` found
   **3** high-severity findings (the original filing's "7-8" was an estimate at filing
   time, corrected here) across two real vectors: `fast-uri` `3.0.0–3.1.3`
   (GHSA-v2hh-gcrm-f6hx) and `sharp` `<0.35.0` (GHSA-f88m-g3jw-g9cj, inherited libvips
   CVEs). Fixed by extending `docs-site/package.json`'s existing `overrides` block
   (already used for the `postcss` case) with `sharp: ^0.35.0` and `fast-uri: ^3.1.4`,
   plus bumping `next` `16.2.10 → 16.2.11` as hygiene (note: the `next` bump alone does
   **not** clear the advisory — `next@16.2.11` still declares `sharp ^0.34.5`; only the
   override does). Verified via `npm audit` → **0 vulnerabilities** and `npm ls next
   sharp fast-uri postcss` showing the resolved patched versions.
2. **Discovered, and explicitly did NOT fix, a separate production outage.** While
   trying to verify the audit fix end-to-end (`npm run build`), found that `docs-site/`'s
   static-export build has failed on every push to `main` for the last 5 merges (PRs
   #42, #44, #45, #46, #47) — confirmed via an isolated worktree that this reproduces
   identically on unmodified `main` HEAD, unrelated to this branch's own change. No PR
   check builds `docs-site/` (`docs-deploy.yml` triggers on push-to-main only), so this
   went unnoticed at merge time, 5 times running. Full evidence trail (including one
   self-caught correction — an early `git diff` command silently produced a false
   "no diff" result due to a shell-quoting issue, later corrected in place) at
   `docs/dev/diagnosis/docs-site-typescript-detection-broken.md`. Filed as a new
   `[URGENT]` carry-forward ledger item — **user explicitly decided to keep this branch
   scoped to the audit fix alone** and file the outage urgently rather than expand scope.
3. **Found and corrected a pre-existing, unrelated drift in the ledger's own header:**
   the "Rendered open count" line claimed 19 before this branch touched anything: a
   direct recount of the actual `- [ ] **` bullets under `#### Open` at `main` HEAD
   (`0ce56b6`) found **20**, not 19 — a stale-by-one header, not something this branch
   introduced. Corrected in place rather than silently propagated.

**Could not verify:** the full static-export build (`npm run build` → `out/index.html`)
end-to-end, per item 2 above — blocked by the separate, pre-existing outage, not by
anything in this branch's own change.

**Gate:** ran the full `python -m scripts.gate` (no Python changed, but the rule has no
docs/JS-only carve-out) — `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓
(0 errors, pre-existing `annotation-unchecked` notes only) · `pytest` **2180 passed, 1
skipped, 0 failed** in 3606s (1:00:06), no reruns needed — `gate: all steps passed.`,
exit 0.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward
ledger (`#### Open`). **Rendered open count: 20** (corrected this branch from a
previously-stated, already-stale 19 — see above). One line each, in ledger order:

1. The quality gate is unrunnable by an agent in one shot — makes it unenforceable as a
   single command in some environments.
2. **[HUMAN/OWNER]** Wire CodeQL as a *required* status check on `main`.
3. `test_corpus_reload_preserves_scroll_position` is a real ~10-20% flake under CPU
   saturation — measured, not yet fixed.
4. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/`.
5. 3 `loadComposition()` call sites excluded from the `compose-unawaited-reloads` fix.
6. PyPI wheel not installable — data files not packaged (**RESOLVED-PENDING-PUBLISH**;
   needs a real publish to confirm).
7. In-app rendered citation viewer (deferred UX item).
8. Grounding / hallucination metric — calibrated layers (B), not yet built.
9. Agent-coding-practices kit-adoption — staged commitments (2026-06-23), not all landed.
10. 2026-07 efficiency review — PX-37..PX-56 aggregate, witness-only follow-through
    still open.
11. `docs/governance/enforcement.md` (and several memory files) cite "charter W-1" —
    a naming/reference consistency item.
12. `scripts/capture_screenshots.py` has zero automated coverage.
13. `.cb-panel`'s collapse animation likely already snaps instead of easing (UI polish,
    unverified).
14. A mobile `.panel-body` padding override is already shadowed/dead CSS.
15. `block-merge-to-main`'s wiki arm makes a wiki-refreshing branch unmergeable.
16. **[OWNER DECISION]** `enforce_admins` is `false` on `main`'s branch protection.
17. **[OWNER-REPORTED]** Claude Code CLI sessions/processes don't terminate cleanly when
    the owner closes a window.
18. `compliance-witness` doesn't verify code-level claims (docstrings/comments) or catch
    a previously-fixed defect class recurring elsewhere.
19. Compose-time rewrite latitude — the "generate but don't invent" dial — **[OWNER
    DECISION], evidence-gated**; see `COMPOSE_REWRITE_DIAL.md` for full context, not the
    ledger summary.
20. **[URGENT — active production outage, filed THIS branch]** `docs-site/`'s
    static-export build has failed on every push to `main` for 5 consecutive merges.
    Evidence trail: `docs/dev/diagnosis/docs-site-typescript-detection-broken.md`.

**The ceiling is ~8-10 open items; this ledger is now at 20 — more than double.** The
reduction sprint flagged as overdue by several prior handoffs remains overdue, and item
20's urgency (a live break, not backlog) is itself an argument for picking either the
sprint or that one item next, immediately.

---

## What this branch should build

Nothing is formally directed for a next branch by this session, but item 20 above (the
production outage) is the strongest candidate by far — it is not routine backlog, it is
an active break discovered this session. Candidates, in rough priority order; **none of
these is a standing authorization** — pick with the normal plan-mode ceremony:

1. **Item 20 — fix the `docs-site/` build outage.** Start from
   `docs/dev/diagnosis/docs-site-typescript-detection-broken.md`, which already has an
   `## Observed` section, falsified hypotheses, an evidenced-but-unproven `## Inferred`
   hypothesis, and a concrete `## Falsification` experiment specified (pin
   `typescript` back to `^6.0.3` and see if the build succeeds). This should be a
   `fix/*` branch — rename the diagnosis file to match its slug once created, since
   `require-evidence-before-fix` looks for that exact path. **Run the falsification
   experiment before writing any fix** — the hypothesis is well-evidenced but not yet
   proven by reading Next's actual detector source.
2. **The overdue reduction sprint** (20 open items now, ceiling ~8-10) — several are
   owner-gated or owner-decision items that may need the owner's attention rather than
   more engineering.
3. **PX-39** — unblocked per a prior session's note, not yet run.

Scope for whichever is picked: bounded to that item alone. **Do not expand into the
fork items** (RELEASE_ARC steps 11b-17, except #10's own step-17 handling at release
time).

**Process note for whoever picks next:** per the rule landed on `docs/record-handoff-consumed-event`,
when you consume this handoff you will write your own `docs/dev/ledger/<session>.jsonl`
on `main` before creating any branch. Do not open a dedicated branch for it — fold its
commit into the first commit of whichever candidate branch above (or other directed
work) you create next. (This branch itself did exactly that — see its own first commit.)

---

## First move

Whatever branch is picked next: write a plan at `~/.claude/plans/<slug>.md` and show it
to the user before touching any code. **Do not code first.** If picking item 1 (the
build outage), run the falsification experiment in the diagnosis dossier as part of
plan-mode exploration, before finalizing the plan — the plan should already reflect
whichever outcome the experiment produced.

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
