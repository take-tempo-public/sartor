<!-- provenance: schema=1 session=f272a785-6dd6-49cb-a77e-4d17980d3626 branch=docs/diagnostics-content-cluster commit=981a639 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-20 -->

# Agent handoff: `docs/diagnostics-content-cluster`

**Branch to create:** none prescribed — see "First move" below, this is an owner-decision handoff
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

**Stream:** step 10 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" sequence — **the last agent-startable step in that sequence.**
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream is gated on this step specifically —
but see the owner-gated fork below.

- ~~`chore/hook-dispatcher`~~ ✓ step 8 (merged, PR #33)
- ~~`fix/context-write-lost-update-gap`~~ ✓ step 8b (unplanned insertion; merged, PR #34)
- ~~`feat/diagnostics-run-cancel`~~ ✓ step 9 (merged, PR #35, `981a639`)
- ~~`docs/diagnostics-content-cluster`~~ ✓ step 10 — **this branch**, merge pending your confirmation
- **The sequence forks here — every remaining item is owner-gated or condition-gated:**
  - Step 11 **[OWNER DECISION POINT]**: `test/fixture-scoping` (PX-44) — decide pre-tag vs. post-public defer.
  - Step 12 **[NEEDS `.api_key` PRESENT]**: `perf/real-corpus-baseline` (PX-39) — real Sonnet-5 measurement, cannot run in an isolated worktree.
  - Step 13 **[OWNER-GATED, no unsolicited scheduling]**: `chore/memory-consolidation` (PX-46) — present the keep/consolidate/delete list first.
  - Step 14: check accumulated CI runs on `main` post-scroll-fix-merge → resolve the `--reruns 2` retry-policy decision (ledger item 1 below) + confirm the scroll-flake CI leg. **Read-only investigation; may not need its own branch.** The one item in this fork that is NOT owner-gated — the only candidate for unprompted forward progress.
  - Step 15: `release/visual-assets` + a fresh-clone re-verify (tag criteria: screenshots current, fresh-clone < 5 min, doc links resolve).
  - Step 16 **[HUMAN]-only, gates the tag itself**: GitHub repo public flip, PyPI Trusted Publisher config, GHCR visibility, CodeQL required-check wiring, branch protection update.
  - Step 17: `chore/release-v1.1.0` — CHANGELOG cut, version bump, tag — executed on the owner's go.

RELEASE_ARC.md's own text is explicit: "Steps 11/12/13/16 are explicitly owner-gated or
condition-gated, not agent-schedulable in sequence — the closing agent on each preceding
branch should surface them rather than attempt them blind." **Do not pick one of 11/12/13
on your own initiative.** Do not start step 15 unprompted either — it's mechanical but
should wait for explicit ordering from the user relative to 11-13.

---

## What just landed on `main`

`main` is at `981a639` (merge of `feat/diagnostics-run-cancel`, PR #35). **This branch has
not merged yet** — pending your confirmation and the PR flow below; once it does, `main`
will additionally contain this branch's commits.

**What this branch did.** The remaining #2/#4/#5/#6/#16 field-level `_DASH_HELP` authoring
pass for the diagnostics console (`/_dashboard`) — content-only, per `RELEASE_ARC.md` step
10's own scope line:

- **9 new `_DASH_HELP` entries** in `dashboard/templates/dashboard.html`: `dashSuiteField`,
  `dashSubsetField`, `dashGroundingSignals` (each shared verbatim across the 2-3 tabs where
  that control repeats — Suite/Subset on Quality + Tuning, grounding-signals additionally
  on Annotate), plus `dashTuneConstant`, `dashTuneCandidate`, `dashTuneSeed`,
  `dashBootstrapRun`, `dashVerdicts`, `dashAnnScore`. Voice matches the main app's
  `_HELP_REGISTRY` (2nd person, 2-5 sentences, plain-text bodies — the shared
  `help-modal.js` opener sets `.textContent`, so no HTML/links ever render; deep-doc
  references stay literal paths, e.g. "see CONTRIBUTING.md, section...").
- **13 new static `.help-info` icon instances** across Quality/Tuning/Annotate (Pipeline
  and Groundedness stayed tab-level only — read-only tiles, nothing granular to explain).
  **Design decision worth knowing if you touch this area again:** every icon is a SIBLING
  of its `<label>`/control, never nested inside one. A `<button>` nested inside a `<label>`
  risks the label's default click-forwarding double-firing the wrapped
  checkbox/select — so icons sit in the field's existing flex row (`.filters`,
  `.tune-editor-head`, `.annotate-actions`) instead, each with a unique `id` (some
  registry keys are shared across tabs, e.g. `dashSuiteField`, so the DOM `id` gets a
  `-quality`/`-tuning` suffix while `data-help` stays the shared registry key).
- **Broadened the one click-handler selector** in the dashboard's wiring IIFE from
  `.dash-pane-intro .help-info` to `.help-info[data-help]` — the field-level icons live
  outside the tab intro paragraph, so the narrower selector would never have wired them up.
  Field icons carry no auto-open (`_maybeFireDashHelp` untouched) — click-only, matching
  the main app's field-level entries.
- **Rewrote `dashTuning`'s prompt-tuning-loop explainer** in plainer language (finding #6):
  shorter sentences, dropped the ALL-CAPS emphasis (WITHOUT/TWO).
- **One incidental doc fix**: `AGENTS.md:193`'s eval-cost line quoted a stale pre-Sonnet-5
  `~$1.50` figure for the full synthetic suite (superseded by `TUNING_LOG.md:1529`'s
  measured `$0.4068`); corrected to `~$0.30-0.40` in the same commit rather than filed as a
  new ledger row, given the ledger's own reduction-sprint pressure.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ (331 files) ·
`pytest -m "not ux"` **2049 passed, 1 skipped** (pre-existing skip; chunked into 6
foreground batches — one chunk needed a further split when the heavy
`test_grounding_signals.py` combined with 18 sibling files timed out at 9 min in one
attempt; split alone it ran in 41s, so the timeout was transient, not the test itself) ·
`pytest -m ux` **123 passed** (a11y+flows together: 11; regression split into 3 chunks:
24/42/46 — matches the prior session's exact UX count, no regressions from the template
changes) · a real Chromium/Playwright click-through (not part of the committed suite,
throwaway script) confirming all 9 new entries open with correct title/body and zero
console/page errors, including the 5 that needed a collapsed `<details>` expanded or a
hidden section force-shown first (`dashTuneSeed`, `dashBootstrapRun`, `dashVerdicts`,
`dashAnnScore`) — all real UI states, not bugs. Two Werkzeug reloader child processes
orphaned during manual verification (parent `taskkill` doesn't kill the reloader's actual
listening-socket child — see `reference-werkzeug-reloader-orphan-child` memory, written
this session) were found via `netstat` + `Get-CimInstance` cross-reference and killed
before close.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **19 open** (**−1** this branch — item 12, UX
round-2 remediation, is now RESOLVED: this branch's field-level authoring pass was its
last open sub-scope; full multi-branch history in the ledger's `#### Resolved` entry).
Re-verified via `grep -c '^- \[ \]'` over the ledger's Open subsection at close-out.

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a 64%-broken test for 11 runs.
2. The quality gate is unrunnable by an agent in one shot (~13 min, hard-capped shell commands) —
   worked around by chunking. This session's chunking hit the SAME background-kill pattern as
   last session (foreground + explicit long timeout is what works; background gets silently
   killed ~5-7 min in) — see `reference-background-bash-kill-ceiling` memory. One chunk
   additionally needed a mid-run split (see Gate note above) — the heavy grounding-signals test
   is fine alone, just don't bundle it with 18 other files in one already-long batch.
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only toggle.
4. `test_corpus_reload_preserves_scroll_position` + siblings — modes B/D fixed; mode C (~17%
   under saturation) unfixed. Not hit this session.
5. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
6. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix — needs its
   own scoped design pass.
7. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
8. In-app rendered citation viewer — deliberately deferred.
9. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration.
10. Agent-coding-practices kit-adoption staged commitments — the `context-structure-review`
    skill import's external kit source path is the remaining open sub-item.
11. 2026-07 efficiency review PX-37..PX-56 — 10 of 13 landed; 3 remain: PX-39 (needs a session
    with `.api_key` present — this is step 12 above), PX-44 (refactor half — step 11 above),
    PX-46 (owner-gated memory consolidation — step 13 above).
12. `enforcement.md` + memories cite "charter W-1" as an existing clause; it still does not
    exist. Needs an owner-directed amendment ceremony.
13. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
14. `.cb-panel`'s collapse animation likely already snaps rather than eases — owner decision.
15. A mobile `.panel-body` padding override is already shadowed/dead — verify on a narrow
    viewport, then decide.
16. `block-merge-to-main`'s pre-merge-worktree bug — dissolved by `chore/merge-channel-alignment`;
    entry retained for the lesson.
17. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately not changed.
18. Claude Code CLI sessions/processes don't terminate when closed, forcing manual cleanup
    across projects (owner-reported). This session independently corroborated the SAME
    process-lifecycle class one level down: Werkzeug's own reloader leaves an orphaned child
    behind a killed parent (see the new memory cited in the Gate note above) — same failure
    shape, different layer. `[HUMAN/OWNER]` on the CLI-level behavior itself.
19. `compliance-witness` doesn't verify code-level claims (docstrings/comments) or re-sweep
    for recurrence of a previously-fixed defect class. **[OWNER DECISION]** on whether to
    widen the witness's scope. Not hit or touched this session.

**Reduction sprint is still overdue** — ceiling is ~8-10, this is 19 (down from 20). No
new items were added this session (the incidental `AGENTS.md` staleness was fixed directly
rather than filed, and the Werkzeug orphan finding folded into existing item 18 rather than
becoming a new item 20). Next closing agent: the fork above (steps 11-17) is where real
reduction can happen — items 11 (PX-39/44/46 all map onto ledger item 11) and 3/17 (both
CodeQL/branch-protection, both owner-gated) would clear multiple ledger rows at once if the
owner greenlights that fork.

---

## What this branch should build

**Nothing is prescribed.** This handoff is an owner-decision fork, not a "create branch X"
handoff — see "Where we are in the arc" above. RELEASE_ARC.md's own sequence puts four
owner/condition-gated items (11/12/13/16) and two ungated-but-sequenced items (14 read-only
investigation, 15 release-prep) next, with the actual `v1.1.0` tag cut (17) waiting behind
all of them. There is no more agent-startable, non-owner-gated diagnostics or content work
left in this sequence — step 10 (this branch) was the last one.

---

## First move

**Do not create a branch on your own initiative.** Present the user with the fork above:
steps 11 (`test/fixture-scoping` pre-tag-vs-defer decision), 12 (needs `.api_key` present),
13 (`chore/memory-consolidation` keep/consolidate/delete list), and 16 ([HUMAN]-only tag
gates) all need an explicit owner call before any branch starts. The one candidate for
unprompted forward progress is step 14 — a read-only CI-log investigation that "may not
need its own branch" per RELEASE_ARC.md's own text — but confirm with the user before even
that, since it's the one item where reasonable agents could disagree on whether "read-only
investigation" still counts as work requiring sign-off given how close this sequence is to
the actual tag. If the user directs a specific step, THEN write a plan at
`~/.claude/plans/<slug>.md` and show it before touching any code, per the standard workflow.

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
