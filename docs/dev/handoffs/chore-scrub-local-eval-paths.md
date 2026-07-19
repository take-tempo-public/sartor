<!-- provenance: schema=1 session=0ea5832d-e464-47fd-acf4-1d8d32a6343b branch=chore/scrub-local-eval-paths commit=7e0bd67 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-19 -->

# Agent handoff: `chore/scrub-local-eval-paths`

**Branch to create:** `chore/config-drift-batch` (branch off `main`)
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

**Stream:** step 7 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step specifically,
but step 8 (`chore/hook-dispatcher`) touches the same enforcement core and is explicitly
sequenced to land after it.

- ~~`docs/v110-plan-reconciliation`~~ ✓ step 1
- ~~`fix/plan-approval-hook-scope`~~ ✓ step 2
- ~~`fix/compose-unawaited-reloads`~~ ✓ step 3
- ~~`refactor/css-cascade-collapse`~~ ✓ step 4 (PX-51; merged `6b03591`)
- ~~`chore/merge-channel-alignment`~~ ✓ step 5 (merged `cce2dc1`, PR #30)
- ~~`chore/scrub-local-eval-paths`~~ ✓ step 6 — this branch (merge pending your confirmation)
- **`chore/config-drift-batch`** (PX-47) ← this branch, step 7
- `chore/hook-dispatcher` (PX-37) ← step 8, next — **coordinate**: it also touches the
  enforcement core this and step 5 both edited

Do not start anything past step 7 on this branch.

---

## What just landed on `main`

`main` is at `cce2dc1` (merge of `chore/merge-channel-alignment`, PR #30). **This branch has
not merged yet** — pending your confirmation and the PR flow below; once it does, `main`
will additionally contain this branch's two rebased commits plus one doc-only commit.

**What this branch did.** Rebased the parked `chore/scrub-local-eval-paths` branch (2
commits, cut 2026-07-14, stalled on an interrupted gate re-verification — not a failure)
onto current `main`. The rebase applied **cleanly, with no conflict** — a `git merge-tree`
3-way simulation run beforehand predicted this correctly, contradicting `RELEASE_ARC.md`
step 6's own prior expectation of a `CHANGELOG.md` conflict (the branch's one hunk there sat
far enough from 45 intervening commits' insertions for git's context matching to resolve it
automatically).

- **`db/models.py:3`** — dropped a dead docstring reference to the owner's personal plans
  file (`C:\Users\iam\.claude\plans\rosy-chasing-pinwheel.md`, double-escaped inside a raw
  docstring). Re-verified live against `main` immediately before landing, via a
  distinctive-literal grep (`rosy-chasing-pinwheel`), not the trap-prone `Users.iam` pattern
  that the prior session's notes warned about (that pattern did NOT actually trap this
  session's `git grep` — worth knowing it isn't universal, but the distinctive literal is
  still the reliable check).
- **`CHANGELOG.md`, `docs/dev/ORCHESTRATION_PLAYBOOK.md`,
  `docs/dev/generation-experience-rearchitecture.md` (×3), `evals/TUNING_LOG.md`** —
  genericized references to the owner's private local testing clone
  (`../sartor-e2e/output/robert/...`) to neutral descriptors.
- **Working-tree-only, as designed.** The leaked strings remain permanently in git history,
  including inside the scrub commits themselves. A history rewrite on an already-public repo
  is a separate, sign-off-gated owner decision — surfaced in the PR description, not
  attempted.
- **Durable docs updated same branch:** `RELEASE_CHECKLIST.md` moves ledger item 5 to
  Resolved; `RELEASE_ARC.md` marks steps 5 and 6 done (step 5's own DONE marker had gone
  stale despite being merged — corrected here since it was noticed in the same list); a new
  `CHANGELOG.md` entry documents the land.
- **New ledger item 20 filed** (see below) — an owner-reported Claude Code session/process
  lifecycle gap, corroborated by concrete evidence gathered while gating this branch.
  `AGENTS.md` and `AGENT_HANDOFF_TEMPLATE.md`'s pre-close sweep (step 0) now require the
  closing agent to check for and terminate any dev server / long-lived background process it
  started, before ending the session.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ (313 files) · `mypy .` ✓ (328 files) ·
`pytest -m "not ux"` **2029 passed, 1 skipped** (chunked in 6 batches, all foreground — matches
the prior gate's cited total exactly) · `pytest -m ux` **121 passed** (a11y+flows: 11;
regression split into 3 chunks: 24, 42, 44). No reruns anywhere, so no masked failures.
Doc-structure gates re-verified after editing governance docs: `test_doc_frontmatter_gate`,
`test_doc_links`, `test_doc_single_home_gate`, `test_doc_status_gate`,
`test_governance_hooks_gate`, `test_docstring_coverage_gate` — all green.

**Incidental finding during the gate run, real and controlled, not a guess:** a UX regression
test failed with `sqlite3.OperationalError: database is locked`. Investigation found a
day-old orphaned `python app.py` dev server (running since 2026-07-18, from an
already-closed prior session) plus a Werkzeug-reloader child it spawned mid-session
(apparently in response to this session's own doc edits). Killing both processes made the
failure disappear on re-run (24/24 passed, vs. 23 passed/1 error before). **One hypothesis
explicitly checked and falsified:** this was NOT a shared-sqlite-file collision — UX tests
isolate their DB at `tmp_path / "ux.sqlite"` (`tests/ux/conftest.py:51`), distinct from the
stray server's default `db/resume.sqlite`. The likelier mechanism is general resource
contention from the orphaned process, which corroborates (without fully proving) ledger item
2's existing candidate-cause note — but the decisive experiment item 2 asks for (kill
orphans, re-run the full **un-chunked** gate) is still unrun; this session only ran chunked.
Full detail: ledger item 20 in `RELEASE_CHECKLIST.md`.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`); this
is the required one-line-each mirror. **19 open** (net unchanged this branch: item 5
resolved, −1; new item 20 filed, +1).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a 64%-broken test for 11 runs.
   Bug fixed; the retry-policy decision is deliberately open pending a real post-fix CI sample.
2. The quality gate is unrunnable by an agent in one shot — worked around by chunking again
   here. **Read this before running the gate** (see the note after this list). This session
   added corroborating (not decisive) evidence — see item 20 and the note above.
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings — modes B/D fixed; mode C (~17%
   under saturation) unfixed.
5. ~~`chore/scrub-local-eval-paths`~~ — **RESOLVED this branch.** See `#### Resolved` in
   `RELEASE_CHECKLIST.md`.
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
7. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
9. In-app rendered citation viewer — deliberately deferred.
10. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
11. Agent-coding-practices kit-adoption staged commitments.
12. 2026-07 efficiency review PX-37..PX-56 — 8 of 13 land; 5 remain (PX-37/39/44/46/47).
    **PX-47 is this branch's own scope.**
13. UX round-2 remediation — design-heavy remainder is the unscheduled UX Cohesion Epic.
14. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
15. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
16. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
17. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
18. `block-merge-to-main`'s pre-merge-worktree bug — dissolved by `chore/merge-channel-alignment`;
    entry retained for the lesson (the first fix design measured drift along the source
    branch alone and wrongly ALLOWED a stale merge).
19. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately not changed: it
    closes the bypass but removes the ability to push a hotfix when CI itself is broken.
20. **NEW — Claude Code CLI sessions/processes don't terminate when closed**, forcing manual
    cleanup across projects (owner-reported). This session found a concrete instance: a
    day-old orphaned `python app.py` caused a real test failure; killing it fixed the test.
    Practical mitigation shipped this branch (pre-close sweep now checks for this); the
    underlying harness behavior is `[HUMAN/OWNER]` — not fixable via a repo change.

**Reduction sprint is badly overdue** — the ceiling is ~8-10 and this is 19. Items 6, 9, and
possibly 3 look cheap.

**Gate-running note (ledger item 2), read before you run it.** Background commands get killed at
inconsistent points. **Foreground calls survived reliably where identical backgrounded ones
were killed** in prior sessions. Chunk from the start: split `tests/test_*.py` into ~6 batches
of ~20 files for the non-UX tier, and `tests/ux/` by subdirectory (a11y+flows together, then
split the 46-file `tests/ux/regression/` into ~3 chunks of ~16) for the UX tier — this
session's chunking held up cleanly. **Also check for stray long-lived processes first**
(`tasklist` or equivalent) — this session found a day-old orphaned dev server that caused a
real test failure; see item 20 above.

---

## What this branch should build

This handoff records `chore/scrub-local-eval-paths`'s close-out. Your branch is **step 7**:

**`chore/config-drift-batch`** (PX-47) — per `RELEASE_ARC.md` step 7: "`plugin.json` version
bump, model-pin convention, `CLAUDE.local.md` refresh, `settings.local.json` prune. Purely
mechanical." This handoff does not have first-hand detail on PX-47's exact scope beyond that
one line — **read the full PX-47 entry in `docs/dev/RELEASE_CHECKLIST.md`'s efficiency-review
section (ledger item 12's aggregate) before starting**, since the one-line RELEASE_ARC.md
summary is a pointer, not the full spec.

1. Read PX-47's full prescription in `RELEASE_CHECKLIST.md` first — do not start from the
   one-line summary above.
2. Verify each of the four sub-items is still live on current `main` before changing it
   (`plugin.json` version, model-pin convention, `CLAUDE.local.md`, `settings.local.json`) —
   per this session's own lesson, ledger entries can go stale; check against `main`, not the
   ledger's prose.
3. Purely mechanical scope — do not expand into PX-37 (hook-dispatcher, step 8's job) even if
   you notice overlap; coordinate via the ledger instead.

Scope is bounded to step 7 in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Create branch `chore/config-drift-batch` off `main`, write a plan
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
