<!-- provenance: schema=1 session=209d9d55-9c58-438d-8d06-c3cbb5fce020 branch=chore/dependabot-ci-infra commit=804096f actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-22 -->

# Agent handoff: `chore/dependabot-ci-infra`

**Branch to create:** `chore/dependabot-group-a` — **recommended, not owner-directed for
this exact session; requires a fresh plan + confirmation like any branch.** This session's
owner direction ("land the fixes next session," scoped via this session's own plan Q&A to
"unblock + low-risk, defer (a)") is now fully executed for groups (b)/(c)/(d); group (a)
is the one deliberately-deferred remainder, and this session's own throwaway-venv probe
found no red flag. It is the natural next step, but pick it up with the normal plan-mode
ceremony, not as a standing authorization to skip straight to code.
**Base branch:** `main` (once this branch, `chore/dependabot-ci-infra`, has merged)

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

**Stream:** v1.1.0 endgame. This branch was the second of two Dependabot dependency-bump
branches directed this session (ledger item 20).
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`docs/compose-rewrite-dial`~~ ✓ (merged, PR #41) — filed the Dependabot backlog
- ~~`chore/dependabot-docs-site`~~ ✓ (merged, PR #42) — group (d), 5 of 14 PRs
- **`chore/dependabot-ci-infra`** ← **this branch** (groups (b)/(c), 4 more PRs; 9 of 14
  total closed after this merges)
- `chore/dependabot-group-a` ← **recommended next** (the 4 remaining PRs: #26/#5/#6/#14) —
  see "Branch to create" above for the authorization nuance
- `#10` (download-artifact) — **not a branch**; deferred to the v1.1.0 release-tag step
  (RELEASE_ARC step 17), to be handled in lockstep with an `upload-artifact` bump

**Do not pick any fork item (RELEASE_ARC steps 11b-17, other than the #10/step-17 note
above) on your own initiative.**

---

## What just landed on `main`

`main` is at `e6eb12e` (merge of `chore/dependabot-docs-site`, PR #42). **This branch has
not merged yet** — pending the PR flow below.

**What this branch did.** Hand-applied 4 Dependabot PRs' worth of action-SHA bumps (not
cherry-picked — Dependabot's own diffs miss call sites for 2 of the 4), plus reconciled a
governance-drift finding surfaced along the way.

1. **#12** `actions/setup-python` 5.6.0→7.0.0 (`5fda3b95a4ea91299a34e894583c3862153e4b97`)
   at **5 sites**: `ci.yml` (×2), `docs-deploy.yml`, `release.yml`, and the composite
   action `.github/actions/setup-python-env/action.yml` — the last of which Dependabot's
   own PR diff never touched (it doesn't scan composite actions). Live-exercised by this
   PR's own required `quality` checks.
2. **#23** `github/codeql-action` (init/analyze/upload-sarif) 3→4.37.1
   (`7188fc363630916deb702c7fdcf4e481b751f97a`) at **3 sites**: `codeql.yml` (init +
   analyze), `scorecard.yml` (upload-sarif). **Root-caused, not guessed:** #23's own 2
   failing checks were a CodeQL configuration error — Dependabot bumped `init` only,
   leaving `analyze`/`upload-sarif` on v3, and CodeQL's own workflow linter refuses to run
   with mismatched action versions ("CodeQL job status was configuration error" — verified
   from the run log). All 3 sites now share the same commit SHA, independently
   re-verified against the GitHub API rather than trusted from Dependabot's diff (whose
   `# v3` comment on the new SHA was itself stale/wrong). #23 closed as superseded.
   Live-exercised by this PR's own required `Analyze` checks.
3. **#11** `docker/setup-buildx-action` 3→4.2.0
   (`bb05f3f5519dd87d3ba754cc423b652a5edd6d2c`), **#18**
   `docker/build-push-action` 6→7.3.0 (`53b7df96c91f9c12dcc8a07bcb9ccacbed38856a`), both
   single-site in `docker.yml`. **Not live-exercised** — `docker.yml` triggers on
   tag-push/`workflow_dispatch` only; first real exercise is the v1.1.0 tag.

**Found and reconciled, not itself a dependency bump:** `codeql.yml`'s in-file comment
AND both `RELEASE_CHECKLIST.md`'s carry-forward ledger AND `RELEASE_ARC.md` step 16 all
stated CodeQL is "NOT a required check" on `main`, pending an `[HUMAN/OWNER]` toggle.
Querying `main`'s branch protection directly
(`gh api repos/:owner/:repo/branches/main/protection`) shows `Analyze (python)` and
`Analyze (javascript-typescript)` are **already required** — the toggle had already
happened at some point, without any of the three docs being updated. All three corrected
on this branch; the `RELEASE_CHECKLIST.md` item is marked RESOLVED.

**Deliberately NOT landed:** #10 `actions/download-artifact` 4.3.0→8.0.1 — `release.yml`
uploads with `actions/upload-artifact@v4` (no matching upload-side bump offered by
Dependabot), and a v4-upload/v8-download pair risks breaking the release; it also can't be
live-tested pre-tag. Deferred to release time (RELEASE_ARC step 17).

**Group (a) probed this session, throwaway venv, no repo change:** #26 ruff, #5 mypy
(resolves 2.3.0, a MAJOR), #6 pytest, #14 pytest-rerunfailures all installed clean at
their widened bounds. `ruff check` + `ruff format --check` under 0.15.22: **0 new
findings, 0 reformats**. `mypy .` under 2.3.0: **0 new errors** (94 pre-existing
`annotation-unchecked` informational notes, identical count to the 1.20.2 baseline run
side-by-side). `pytest` under 9.1.1 + rerunfailures 16.4: **2024 passed, 129 skipped, 0
failed, 0 errors** in 379s. **Caveat, not fully validated:** the probe venv never ran
`playwright install chromium`, so the entire `ux`-marked tier (129 tests) skipped instead
of running — this probe does NOT validate the Playwright/a11y tier under the new pytest.
Also Python-3.13-only, doesn't cover the 3.11/3.12 CI matrix. Net: no red flag, but not a
substitute for a real branch + full gate.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ · `pytest` **2180
passed, 1 skipped** (`gate: all steps passed.`, exit 0) at commit `804096f`, run via
`python -m scripts.gate > <log> 2>&1; echo "GATE EXIT: $?"`. Confirmed from the log's own
`gate: all steps passed.` line. No dev server or long-lived process was started this
session; the throwaway probe venv was removed (`rm -rf`) before close-out —
`git worktree list` and a process check both came back clean.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **19 open** (**−1** this branch — resolved the
CodeQL-required-check item; see below).

1. The quality gate is unrunnable by an agent in one shot (~14-18 min) — plus the `| tee`
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
19. **Dependabot backlog (14 open PRs) — 9 of 14 CLOSED this session.** Groups (b)/(c)/(d)
    landed across `chore/dependabot-docs-site` + `chore/dependabot-ci-infra`
    (#17/#24/#25/#27/#28/#11/#12/#18/#23). #10 deliberately deferred to release time (see
    above). **Only group (a) remains** (#26 ruff, #5 mypy, #6 pytest, #14
    pytest-rerunfailures) — probed clean this session (see above), still needs its own
    branch with a full gate (not a probe) between each bump before landing. Full risk
    detail + probe results in `RELEASE_CHECKLIST.md` item 20.

**RESOLVED this branch, dropped from the count:** "[HUMAN/OWNER] Wire CodeQL as a required
status check on `main`" — found already done (verified via the branch-protection API);
`codeql.yml`, `RELEASE_CHECKLIST.md`, and `RELEASE_ARC.md` step 16 all corrected.

**Reduction sprint is badly overdue** — ceiling ~8-10, this is 19 (down from 20, still
more than double the ceiling). Once group (a) lands, item 19 above resolves too, bringing
it to 18.

---

## What this branch should build

**`chore/dependabot-group-a`** — the last piece of ledger item 20. See "Branch to create"
above for why this is a recommendation, not an unconditional directive: pick it up with
the normal plan-mode ceremony.

1. **#26 ruff** `0.15.12→0.15.22` — this session's probe found 0 new findings, 0
   reformats. Ruff is **deliberately exact-pinned** (`pyproject.toml` — see the comment
   there and the kit-phase2 ratchet notes); bump the exact pin, run `ruff format .` if the
   probe result doesn't hold on a real branch, full gate after.
2. **#5 mypy** `<2.0→<3.0` — resolves to **2.3.0**, itself a MAJOR. Probe found 0 new
   errors (94 pre-existing informational notes, unchanged count). Full gate after.
3. **#6 pytest** `<9.0→<10.0` — resolves to 9.1.1. **#14 pytest-rerunfailures**
   `<16→<17` — resolves to 16.4. Probe found 0 failures on the non-`ux` tier, but **the
   `ux`/Playwright tier was NOT exercised** (no Chromium in the throwaway venv) — this is
   the one real gap in the probe evidence. Land these together (both touch the same
   `pytest` invocation), and pay close attention to the `ux` tier's real result on a real
   branch — `python -m playwright install chromium` first if the local environment needs
   it, per `CONTRIBUTING.md`'s dev-loop setup.
4. **Full local gate after each risky bump, not just after all four** — per this item's
   original ordering guidance, since these touch the gate itself. Re-verify on the live
   PyPI index that mypy 2.3.0/pytest 9.1.1/rerunfailures 16.4 are still current (a newer
   patch may have shipped since this probe).
5. **CHANGELOG entry** grouped for these 4, noting the probe's clean result and the
   ux-tier caveat.
6. **This closes ledger item 20 entirely** (all 14 original PRs accounted for: 9 landed,
   4 landed here, #10 deferred to release). Update the ledger to reflect full closure and
   drop item 19 from the open count once this lands.

Scope is bounded to these 4 PRs. **Do not expand into the fork items** (RELEASE_ARC steps
11b-17, except #10's own step-17 handling at release time).

---

## First move

Create branch `chore/dependabot-group-a` off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not
code first.** The plan should re-verify all 4 target versions against the live PyPI index
(this handoff's probe results are a point-in-time snapshot, not a guarantee) and confirm
whether the local dev environment has Chromium installed before claiming the `ux` tier is
validated.

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
