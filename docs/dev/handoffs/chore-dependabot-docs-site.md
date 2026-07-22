<!-- provenance: schema=1 session=209d9d55-9c58-438d-8d06-c3cbb5fce020 branch=chore/dependabot-docs-site commit=72ae5ba actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-22 -->

# Agent handoff: `chore/dependabot-docs-site`

**Branch to create:** `chore/dependabot-ci-infra` — **directed, same session** (this is
the second of two branches the owner authorized this session for ledger item 20, the
Dependabot backlog). See "What this branch should build" below for the exact scope.
**Base branch:** `main` (once this branch, `chore/dependabot-docs-site`, has merged)

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

**Stream:** v1.1.0 endgame. This branch was a **Dependabot dependency-bump branch**, one
of two authorized this session for ledger item 20 (`docs/compose-rewrite-dial`'s handoff
directed "land the fixes next session").
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`test/fixture-scoping`~~ ✓ (merged, PR #39) — PX-44 pilot
- ~~`docs/v110-endgame-scope`~~ ✓ (merged, PR #40) — endgame requirements catalog refresh
- ~~`docs/compose-rewrite-dial`~~ ✓ (merged, PR #41) — filed the Dependabot backlog +
  compose-rewrite-latitude design input
- **`chore/dependabot-docs-site`** ← **this branch** (5 of 14 Dependabot PRs, group (d))
- **`chore/dependabot-ci-infra`** ← **next, same-session-directed** (groups (b)/(c),
  the remaining 9 minus group (a)'s 4)
- Group (a) — #26 ruff, #5 mypy, #6 pytest, #14 pytest-rerunfailures — **deferred to a
  LATER session**, after a throwaway-venv probe (see "Carried-forward observations")

**Do not pick any fork item (RELEASE_ARC steps 11b-17) on your own initiative.** Only the
Dependabot-backlog work is authorized.

---

## What just landed on `main`

`main` is at `e935ee7` (merge of `docs/compose-rewrite-dial`, PR #41). **This branch has
not merged yet** — pending the PR flow below.

**What this branch did.** 5 of the 14 open Dependabot PRs (group (d), docs-site,
lower-risk), cherry-picked/hand-applied onto one branch rather than merged individually —
forced by two facts Dependabot's own PRs can't satisfy: a grouped CHANGELOG entry has to
live on a contributing branch (not a bot PR), and PR #25 needs a fix Dependabot's diff
doesn't offer.

1. **#28** `@tailwindcss/postcss` 4.3.2→4.3.3 (patch) — clean cherry-pick.
2. **#24** `fumadocs-openapi` 11.1.1→11.2.2 — clean cherry-pick (auto-merged lockfile).
3. **#25** `fumadocs-core` 16.11.2→16.11.5 — clean cherry-pick, but see the found-and-fixed
   defect below.
4. **#27** `fumadocs-mdx` 15.1.0→15.2.0 — **conflicted on cherry-pick** (package.json/
   package-lock.json touched the same fumadocs fields as #24/#25 already on the branch);
   resolved by hand-editing `package.json` + `npm install --package-lock-only`, not by
   text-merging the conflicted lockfile.
5. **#17** `typescript` 6.0.3→7.0.2 (major) — clean cherry-pick.

**Found and fixed within this branch, not a new open item** (matching the
`fix/context-write-lost-update-gap` precedent): #25 (`fumadocs-core` alone) breaks
`npm ci` **on its own** — `fumadocs-ui` is aliased to `npm:@fumadocs/base-ui@16.11.2`,
whose peer dependency locks `fumadocs-core` to an EXACT version. Verified this is a
defect in #25 itself (not an artifact of this branch's cherry-pick order) by running
`npm ci` against #25's own commit in an isolated `git worktree` — it fails there too. No
PR check builds `docs-site/` (`docs-deploy.yml` triggers on push-to-`main` only), so
Dependabot's own CI never caught it. **Fix:** bumped the `fumadocs-ui` pin to
`npm:@fumadocs/base-ui@16.11.5` in lockstep (verified via `npm view` that 16.11.5's own
peer dependency matches). Full detail: `CHANGELOG.md` `[Unreleased]` "docs-site
dependency bumps."

**Validated with a real `npm run build`** (not just lockfile resolution, since no PR
check exercises this) — compiled, typechecked clean under TypeScript 7, generated all
126 static pages.

**`npm audit` shows 7-8 high-severity findings** (`sharp` inherited libvips CVEs via
`next@16.2.10`; `fast-uri` via `ajv`) — confirmed identical on unmodified `main` via an
isolated worktree audit, so **pre-existing, not introduced by any bump here**. No open
Dependabot PR touches `next` or `sharp`. This contradicts `CHANGELOG.md`'s own 2026-07-14
"`npm audit` now reports 0 vulnerabilities" claim (`chore/scorecard-and-docs-voice`) —
drifted upward since. **Not fixed on this branch** (a `next`/`sharp` upgrade is its own
risk-bearing change, out of scope for a Dependabot-bump branch) — filed as a sub-note on
ledger item 20, not a new top-level item (ceiling already breached).

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ · `pytest` **2180
passed, 1 skipped** (`gate: all steps passed.`, exit 0) at commit `87980ba`, run via
`python -m scripts.gate > <log> 2>&1; echo "GATE EXIT: $?"` (never `| tee` — masks the
exit code, per the prior branch's trap note). Confirmed from the log's own `gate: all
steps passed.` line, not the background-task notification summary alone. No dev server
or long-lived process was started this session; two throwaway `git worktree`s (peer-dep
isolation check, main-audit comparison) were created and removed with
`git worktree remove --force` before close-out — `git worktree list` checked clean.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **Still 20 open** (net unchanged this branch —
partial progress on item 20, not a resolve; see its updated text for the group (b)/(c)/(d)
breakdown).

1. The quality gate is unrunnable by an agent in one shot (~15-18 min) — plus the `| tee`
   exit-code-masking trap.
2. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — **STATUS
   CORRECTED this branch:** `Analyze (python)` + `Analyze (javascript-typescript)` are
   **already** required (confirmed via the branch-protection API) — this item's own prior
   framing and `codeql.yml`'s in-file comment ("NOT a required check") both drifted from
   that. `chore/dependabot-ci-infra` will reconcile the comment; this ledger item's text
   should be corrected too once that lands (or fold this note into item 20, since it
   surfaced there — owner's call). Dependabot #23 (codeql-action `3→4`) is diagnosed
   (config error, not code) and planned for that branch.
3. `test_corpus_reload_preserves_scroll_position` + siblings — mode C (~17% under
   saturation) unfixed.
4. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
5. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix.
6. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
7. In-app rendered citation viewer — deliberately deferred.
8. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
9. Agent-coding-practices kit-adoption — external kit source path remains open.
10. 2026-07 efficiency review PX-37..56 — 10 of 13 landed; 3 remain: PX-39 (unblocked, not
    yet run), PX-44 (46-file rollout, step 11b), PX-46 (owner-gated).
11. `enforcement.md` + memories cite "charter W-1" as an existing clause; it does not exist.
12. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
13. `.cb-panel` collapse animation likely snaps rather than eases — owner decision.
14. A mobile `.panel-body` padding override is already shadowed/dead — verify, then decide.
15. `block-merge-to-main`'s pre-merge-worktree bug — dissolved; entry retained for the lesson.
16. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately unchanged.
17. Claude Code CLI sessions/processes don't terminate when closed — `[HUMAN/OWNER]`.
18. `compliance-witness` doesn't verify code-level claims or re-sweep for defect-class
    recurrence — **[OWNER DECISION]**.
19. Compose-time rewrite latitude — the "generate but don't invent" dial. Points at
    `COMPOSE_REWRITE_DIAL.md`. Evidence-gated on PX-39.
20. **Dependabot backlog (14 open PRs) — IN PROGRESS.** Group (d) (5 PRs: #17/#24/#25/#27/#28)
    **landed this branch**. Groups (b) (#11/#18, plus #12 setup-python) and (c) (#23
    codeql) **diagnosed this branch, planned for `chore/dependabot-ci-infra`** — not yet
    executed. #10 (download-artifact) **recommend deferring to release time** — pairs with
    an `upload-artifact` bump `release.yml` needs but Dependabot doesn't offer; a
    v4-upload/v8-download split risks breaking the release and can't be live-tested
    pre-tag. Group (a) (#26/#5/#6/#14, the 4 gate-touching bumps) **untouched, probe only**
    — see next branch's scope. Full risk detail + exact SHA pins in
    `RELEASE_CHECKLIST.md`'s item 20.

**Reduction sprint is badly overdue** — ceiling ~8-10, this is 20 (net unchanged; will
drop once item 20 fully resolves across the remaining branches/session).

---

## What this branch should build

**`chore/dependabot-ci-infra`** — same-session-directed, continuing ledger item 20.

1. **Hand-apply 3 action-SHA bumps** (not cherry-pick — these touch call sites Dependabot's
   own diffs miss):
   - **#12** `actions/setup-python` 5.6.0→7.0.0, pin
     `5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0`, at **5 sites**: `ci.yml:85,185`,
     `docs-deploy.yml:32`, `release.yml:37`, **and** the composite action
     `.github/actions/setup-python-env/action.yml:17` (Dependabot doesn't scan composite
     actions — this site would otherwise stay stale forever).
   - **#23** `github/codeql-action` init/analyze/upload-sarif 3→4, pin
     `7188fc363630916deb702c7fdcf4e481b751f97a # v4.37.1`, at **3 sites**:
     `codeql.yml:44` (init), `codeql.yml:63` (analyze), `scorecard.yml:49`
     (upload-sarif). Dependabot's #23 bumped `init` only, which is why its 2 required
     checks are failing with "CodeQL job status was configuration error" — verified in
     the run log, not inferred. Close #23 as superseded once this commit lands.
   - **#11** `docker/setup-buildx-action` 3→4, pin
     `bb05f3f5519dd87d3ba754cc423b652a5edd6d2c # v4.2.0`, `docker.yml:40`.
   - **#18** `docker/build-push-action` 6→7, pin
     `53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0`, `docker.yml:60`.
2. **Reconcile the governance-drift comment** in `codeql.yml` (currently states "this
   workflow is NOT a required check" — false; `Analyze (python)` and
   `Analyze (javascript-typescript)` are both in `main`'s required-checks list per the
   branch-protection API) and correct `RELEASE_CHECKLIST.md` ledger item 2 to match.
3. **CHANGELOG `[Unreleased]` entry** — grouped "CI-infra action bumps", noting: #10
   deferred (with the upload/download version-split reasoning), and that #11/#18 have no
   PR-time live check (`docker.yml` triggers on tag-push/`workflow_dispatch` only — first
   real exercise is the v1.1.0 tag).
4. **Quality gate.** `#12` (setup-python) is exercised live by this PR's required `quality`
   checks; `#23` (codeql) is exercised live by this PR's required `Analyze` checks — both
   should flip from the failing state visible on `main`/their own Dependabot PRs today to
   passing. Confirm from the actual PR checks, not an assumption.
5. **Do NOT dispatch `docker.yml` manually** to pre-validate #11/#18 without explicit owner
   sign-off — a dispatch may push to GHCR. Default is merge-on-review + the tag-time
   validation TODO from ledger item 20.
6. **Probe group (a) in a throwaway venv, no repo change** (per this session's plan): ruff
   0.15.22, mypy 2.3.0 (a MAJOR — verify current PyPI state doesn't drift further),
   pytest 9.1.1, pytest-rerunfailures 16.4. Capture the measured delta (new lint findings /
   reformats, new mypy error count+categories, pytest collection/deprecation/failures) into
   this branch's own handoff so the eventual group-(a) session starts from evidence, not a
   re-guess. Local Python is 3.13 only — note the probe doesn't cover the 3.11/3.12 CI
   matrix.

Scope is bounded to ledger item 20's groups (b) and (c), plus the group-(a) probe. **Do
not expand into the fork items** (RELEASE_ARC steps 11b-17) — those remain owner-gated.
Do not attempt #10 (download-artifact) — deferred to release time per the reasoning above.

---

## First move

Create branch `chore/dependabot-ci-infra` off `main` (after this branch merges), write a
plan at `~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.** The plan should confirm the 4 SHA pins above (re-verify against the
live GitHub API rather than trusting this handoff's transcription) and the probe scope.

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
