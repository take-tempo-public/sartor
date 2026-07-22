<!-- provenance: schema=1 session=3818aee6-cd80-490a-83c7-698fd5637c24 branch=docs/compose-rewrite-dial commit=1d6d723 actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-21 -->

# Agent handoff: `docs/compose-rewrite-dial`

**Branch to create:** `chore/dependabot-sweep` — **owner-directed at close-out** ("land the fixes next session"). See "What this branch should build" for the risk-grouped order. This is the one prescribed item; everything else in the fork remains owner-gated.
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

**Stream:** v1.1.0 endgame. This branch was **docs-only** — it executed no fork item.
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing is gated on this branch.

- ~~`test/fixture-scoping`~~ ✓ (merged, PR #39, `96aec1d`) — PX-44 pilot, 2/46 files
- ~~`docs/v110-endgame-scope`~~ ✓ (merged, PR #40, `2240b09`) — refreshed the step 11-17
  requirements catalog in place; added a **Recommended endgame order**; PX-39 reclassified
  **UNBLOCKED**
- **`docs/compose-rewrite-dial`** ← **this branch** (docs-only, two commits)
- **`chore/dependabot-sweep`** ← **next, owner-directed**

**The fork is unchanged in shape and current in substance** — read `RELEASE_ARC.md` steps
11b-17 for the full requirements, which the previous branch made executable-without-rediscovery:

- Step 12 **UNBLOCKED**: `perf/real-corpus-baseline` (PX-39) — `.api_key` present; targets the
  owner's real E2E corpus via `scripts/export_corpus_seed.py`, not the thin `testuser` fixture.
- Step 13 **[OWNER-GATED]**: `chore/memory-consolidation` (PX-46) — present the
  keep/consolidate/delete list first.
- Step 15: `release/visual-assets` + fresh-clone re-verify (screenshots ~7.5 wks stale; README
  hero captured-but-unwired).
- Step 16 **[HUMAN]-only**: repo public flip, PyPI Trusted Publisher, GHCR visibility, CodeQL
  required check, `enforce_admins`.
- Step 17: `chore/release-v1.1.0` — version bump + CHANGELOG `[1.1.0]` cut + tag.
- Step 11b: the PX-44 46-file fixture-scoping rollout.

**Do not pick any of these on your own initiative.** The only owner-directed item is the
Dependabot sweep below.

---

## What just landed on `main`

`main` is at `2240b09` (merge of `docs/v110-endgame-scope`, PR #40). **This branch has not
merged yet** — pending the PR flow below.

**What this branch did.** Docs-only; no code, prompt, test, or dependency change.

1. **Captured the compose-time rewrite-latitude findings** in a new
   **[`COMPOSE_REWRITE_DIAL.md`](../COMPOSE_REWRITE_DIAL.md)** — design input for a future
   tuning pass, nothing built or scheduled. It came out of an owner-led analysis of a real,
   externally-graded application artifact (owner-local files; **no company or personal data is
   in git — verified across every tracked file and both commits**). Headlines:
   - The canonical corpus **reproduces that artifact with zero fact gaps**, making it a
     **reproducible test case with a real-world grade** — the only one this project has.
   - Bullet re-wording **existed and was documented** (`RELEASE_CHECKLIST.md`'s v1.0.2 WYSIWYG
     section: the LLM was *"free to reword each bullet for sharpness / JD relevance"*), and was
     lost as **WYSIWYG-divergence collateral — not a grounding decision**. The trade-off
     dissolves if re-wording moves to **compose** time, pre-freeze: preview==download and the
     deterministic-assembly boundary (**C-6**) both still hold.
   - The middle-dial machinery is **largely already built** — `draft_surgical_refinement`,
     `supersedes_bullet_id`, `pattern_kind`, and an accept-time exclusion that already enforces
     "never a rewrite and its source bullet in one compose." Missing only a **JD-driven,
     compose-wide trigger**. Jaccard dedup lives in corpus curation, not compose, so it cannot
     suppress a rewrite.
   - Any contract must permit **categorization** (naming the discipline stated facts already
     belong to) as distinct from **invention** — and `grounding_overlap`'s lexical matching
     scores category-2 language as `missing`, so a tuning pass **fights its own metric** unless
     that is handled deliberately.
   - **Evidence-gated:** the PX-39 run can produce the validating comparison at no extra cost.
     n=1, no content-level attribution — **evidence first, then the dial.**
2. **Revised the carry-forward ledger item in place** — its original "non-JD-paired exemplar
   résumé" framing was **superseded** by the analysis (the artifact is JD-paired, and the corpus
   reproduces it). One item, better understood; no count change from that edit.
3. **Gitignored `scratchpad/`** — it was untracked but *not* ignored, so a `git add -A` would
   have swept it in. That is an exposure route, not just noise: it is where analysis of real
   corpus/application data lands. Nothing was tracked there, so nothing was hidden.
4. **Filed the Dependabot backlog** as a new ledger item (see below).

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ · `pytest` **2180 passed,
1 skipped** (`gate: all steps passed.`, exit 0) at commit `3b9ce85`. The `.gitignore` commit
(`1d6d723`) was verified against the five `.gitignore`-coupled test files (`test_zero_pii_clone`,
`test_doc_links`, `test_testuser_fixture`, `test_build_vector_index`, `test_openapi_spec` — 34
passed) plus a final full-gate run before merge. No dev server or long-lived process was started
this session; `tasklist` checked clean.

> **Trap worth inheriting:** an earlier gate run this session was invoked as
> `python -m scripts.gate 2>&1 | tee <log>`. The completion notification reported **exit 0
> while the gate had actually FAILED** — in a pipeline the status is `tee`'s, not the gate's.
> Use `python -m scripts.gate > <log> 2>&1; echo "GATE EXIT: $?"` and confirm from the log's own
> `gate: all steps passed.` line. Recorded in the `reference-background-bash-kill-ceiling` memory.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger (`#### Open`);
this is the required one-line-each mirror. **20 open, +1 this branch** (the Dependabot backlog;
the exemplar-résumé item was rewritten in place, not added).

1. The quality gate is unrunnable by an agent in one shot (~15-18 min) — plus the `| tee`
   exit-code-masking trap described above.
2. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only. **Note:**
   Dependabot #23 (codeql-action `3→4`) is currently red, and is load-bearing for this.
3. `test_corpus_reload_preserves_scroll_position` + siblings — mode C (~17% under saturation)
   unfixed. One instance flaked in this session's first gate run and passed deterministically in
   isolation (16.58s); not a regression, this branch touched no code.
4. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` — opportunistic only.
5. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix.
6. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; blocked on a `[HUMAN]` prerequisite.
7. In-app rendered citation viewer — deliberately deferred.
8. Grounding/hallucination calibrated layers (L1/L2) — owner-gated calibration. **Related:** the
   new `COMPOSE_REWRITE_DIAL.md` metric-conflict section bears directly on this.
9. Agent-coding-practices kit-adoption — the `context-structure-review` skill import's external
   kit source path remains open.
10. 2026-07 efficiency review PX-37..56 — 10 of 13 landed; 3 remain: PX-39 (**unblocked**, not
    yet run), PX-44 (refactor half — pilot landed; 46-file rollout is step 11b), PX-46
    (owner-gated).
11. `enforcement.md` + memories cite "charter W-1" as an existing clause; it does not exist.
12. `scripts/capture_screenshots.py` has zero periodic coverage — owner decision on cadence.
13. `.cb-panel` collapse animation likely snaps rather than eases — owner decision.
14. A mobile `.panel-body` padding override is already shadowed/dead — verify, then decide.
15. `block-merge-to-main`'s pre-merge-worktree bug — dissolved; entry retained for the lesson.
16. `enforce_admins: false` on `main` — **[OWNER DECISION]**, deliberately unchanged.
17. Claude Code CLI sessions/processes don't terminate when closed — `[HUMAN/OWNER]`.
18. `compliance-witness` doesn't verify code-level claims or re-sweep for defect-class
    recurrence — **[OWNER DECISION]**.
19. **Compose-time rewrite latitude — the "generate but don't invent" dial.** Rewritten in place
    this branch; points at `COMPOSE_REWRITE_DIAL.md`. Evidence-gated on PX-39. Owner has further
    material for the normal annotate workflow when the tuning phase opens.
20. **NEW — Dependabot backlog (14 open PRs).** Owner-deferred to the next session at filing
    time, not an oversight. See the next section.

**Reduction sprint is badly overdue** — ceiling ~8-10, this is 20.

---

## What this branch should build

**`chore/dependabot-sweep`** — owner-directed at close-out ("land the fixes next session").
Authorized by the Carry-forward ledger item 20 in `RELEASE_CHECKLIST.md`, which carries the
full risk grouping. **Do NOT bulk-merge all 14.** Key facts:

1. **All 14 are based on `main` from 2026-07-13/16** and branch protection is `strict: true` —
   every one needs updating against current `main` before it can merge at all.
2. **Suggested order** (from the ledger item):
   - **(d) docs-site, lower risk — can batch:** #28 `@tailwindcss/postcss` (patch), #24
     fumadocs-openapi, #25 fumadocs-core, #27 fumadocs-mdx, then #17 typescript `6→7` (major,
     take separately).
   - **(b) CI infrastructure majors — individually:** #10 `actions/download-artifact 4→8` (four
     majors), #12 `actions/setup-python` (**branch says `6.3.0`, title says `7.0.0` — resolve
     the mismatch before merging**), #11 `docker/setup-buildx-action 3→4`, #18
     `docker/build-push-action 6→7`. Breakage here blocks every future PR.
   - **(a) Touches the quality gate — one at a time, FULL GATE after each:** #26 ruff
     `0.15.12→0.15.22` (**ruff is deliberately exact-pinned** — a bump can reformat or re-flag
     the whole tree), #5 mypy `<2.0→<3.0`, #6 pytest `<9.0→<10.0` (both widen bounds to admit
     the next major), #14 pytest-rerunfailures `<16→<17`.
   - **(c) Already red — diagnose first:** #23 `github/codeql-action/init 3.37.0→4.37.1` has
     **2 failing checks**, and CodeQL is exactly what step 16 wants to promote to a required
     check (ledger item 2).
3. **Any dependency change needs a `CHANGELOG.md` entry** (Hard constraints, below).

Scope is bounded to ledger item 20. **Do not expand into the fork items** (steps 11b-17) — those
remain owner-gated and are not authorized by this handoff.

---

## First move

Create branch `chore/dependabot-sweep` off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.** The plan should state
which PRs are in the first batch and confirm the gate cadence for group (a).

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
