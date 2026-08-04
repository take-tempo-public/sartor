<!-- provenance: schema=1 session=520b7b1b-abe0-4c81-acf4-4088fa632303 branch=fix/wiki-freshness-relevance-classification commit=c8eb74d actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-03 -->

# Agent handoff: after `fix/wiki-freshness-relevance-classification` (item 35 closed)

**Branch to create:** none pre-authorized. The immediate next action is NOT a new
branch — it's returning to `fix/extract-experiences-telemetry-pollution`'s already-open
PR #96 once this branch merges (see "What just landed" below).
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

## Documents to read next, specific to this handoff

- `docs/dev/diagnosis/wiki-freshness-relevance-classification.md` — the full evidence
  chain: the raw drift-count mechanism read in full, the 79-file categorization that
  found 60+ files were process/provenance churn never wiki-cited, the two prior
  incidents in `docs/wiki/log.md` (2026-07-24, 2026-07-30) that patched the same
  false-positive shape with one-off manual triage instead of fixing it, and the
  end-to-end verification that the fix drops that exact 79-file window to 12
  genuinely relevant files.
- `docs/dev/work/items/0035-wiki-freshness-gate-counts-non-wiki-churn-as-drift.md`
  (closed) — the resolution.
- `scripts/wiki_relevance.py` — the new single source of truth for wiki-relevance
  classification, consumed by both `scripts/wiki_freshness.py` (the merge-blocking
  gate) and `hooks/wiki-freshness-reminder.sh` (the post-commit nudge). Read its
  module docstring before adding a new top-level directory/file anywhere in the
  repo — `tests/test_wiki_relevance_classification.py` will fail loudly if it's
  unclassified, and that failure IS the prompt to classify it, not a bug to route
  around.
- `[[reference-maintained-classification-list-pattern]]` (memory, new this session)
  — the reusable design shape this fix is built on
  (`tests/test_egress_allowlist.py`'s `SANCTIONED_EGRESS_FILES` + offenders/stale
  dual-check), worth reusing for any future "classify every X against category Y"
  gate in this repo.
- `[[reference-wiki-freshness-single-branch-threshold]]` (memory, updated this
  session) — the original note is now superseded in part; read the update at the
  top before the historical PX-44 example below it.
- **AGENTS.md's branch close-out checklist gained a new step** (also mirrored
  verbatim into `docs/dev/AGENT_HANDOFF_TEMPLATE.md`): if a branch's own diff
  touches a `scripts.wiki_relevance.is_wiki_relevant()`-classified path, run a
  scoped `/wiki-self-update` and commit the wiki edit **before** opening the PR —
  small incremental per-branch updates are the new expected norm; the CI gate is
  the backstop for anything missed, not the primary mechanism. This branch's own
  diff touched two such paths (`AGENTS.md`, `docs/dev/AGENT_HANDOFF_TEMPLATE.md`) —
  checked `docs/wiki/pages/llm-wiki-design.md` (the only page mentioning
  close-out/lint-gate ownership) and confirmed its `[synthesis]` claim ("ownership
  is the branch close-out + the pre-release lint gate") is still accurate after
  this change (a step was added, not the ownership model changed) — **verified
  no-edit**, not skipped.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was NOT picked from the open backlog — it's an infrastructure
fix discovered and authorized mid-session while closing out
`fix/extract-experiences-telemetry-pollution` (item 33), whose own PR #96 was blocked
by the exact gate defect this branch fixes.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch).

- **`fix/wiki-freshness-relevance-classification` (this branch)** — closed item 35
  (the wiki-freshness gate counting non-wiki-tracked churn as drift). New
  `scripts/wiki_relevance.py` classification module + audit test; both the gate and
  the post-commit nudge now filter through it; `AGENTS.md` close-out checklist gained
  a step making incremental per-branch wiki updates the norm. Does NOT advance
  `docs/wiki/.last_ingest_sha` and does NOT run an actual `/wiki-self-update` pass —
  the 12 genuinely wiki-relevant files still accumulated since the last real ingest
  (`analyzer.py`, `blueprints/diagnostics.py`, `dashboard/routes.py`,
  `dashboard/templates/dashboard.html`, `docs/architecture.md`, `evals/{README,
  annotation,bootstrap,runner}.py`, `hardening.py`, `json_resume.py`,
  `static/app.js`) remain a known, real, moderate backlog for whenever those files
  are next touched by a future branch's own close-out check — deliberately not
  cleared here, since this branch's scope is the measurement fix, not a content
  catch-up pass.
- **Immediately next: `fix/extract-experiences-telemetry-pollution`'s PR #96.** Once
  this branch merges to `main`, that PR's wiki-freshness CI check will re-evaluate
  against the fixed gate. Verified locally: recomputing drift on that PR's actual
  diff window with the new classifier gives 12 (see above), far under the 75-file
  threshold — it should go green without any wiki content changes on that branch.
  **Do not merge #96 without confirming its CI has actually gone green post-merge** —
  the local recomputation is strong evidence, not a substitute for watching the real
  check.
- Items 34 (corpus blueprints' `_get_client` unpatched in UX harness) and 20 (legacy
  `generate()` reachable without freezing Compose) remain the standing next-pick
  candidates per the session's earlier ranking, unaffected by this branch.
- Do not start items 3, 5, 8, 10 without their own listed unblock (all `Blocked`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `c8eb74d` (PR #95, item 22 close-out; PR #96 for item 33 is open but not
yet merged, blocked on this branch's own fix). This branch's own work adds:

- `scripts/wiki_relevance.py` (new): the wiki-relevance classification single source
  of truth — `IRRELEVANT_PREFIXES`, `IRRELEVANT_FILES`, `MIXED_PREFIXES` +
  `RELEVANT_OVERRIDES`, `KNOWN_RELEVANT_TOP_LEVEL`, `is_wiki_relevant()`,
  `filter_relevant()`.
- `tests/test_wiki_relevance_classification.py` (new): the audit — enumerates git-
  tracked root / `docs/` / `docs/dev/` entries via `git ls-tree HEAD:<dir>` and fails
  if any is unclassified (offenders) or a classified entry no longer exists (stale),
  mirroring `tests/test_egress_allowlist.py`'s shape.
- `scripts/wiki_freshness.py`: `drift_count()` now filters through
  `is_wiki_relevant()` instead of a bare `docs/wiki/`/`docs-site/` exclusion.
- `hooks/wiki-freshness-reminder.sh`: the post-commit nudge now shells out to the
  same `scripts.wiki_relevance.is_wiki_relevant` instead of an independently
  bash-reimplemented (and slightly inconsistent — it never excluded `docs-site/`)
  count.
- `AGENTS.md` + `docs/dev/AGENT_HANDOFF_TEMPLATE.md`: new close-out checklist step
  (identical text in both, per this repo's verbatim-sync convention for the
  handoff-template's fixed sections).
- `docs/dev/diagnosis/wiki-freshness-relevance-classification.md` (new): the full
  evidence chain.
- `docs/dev/work/items/0035-*.md` closed (resolution + refs);
  `docs/dev/work/BOARD.md` regenerated (35 files, closed 18→19).

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ (344 source files) ·
non-ux pytest (`-n auto`, 2202 passed, 1 skipped, zero reruns) ✓ · ux pytest (serial, 137
passed, 1 xfailed, 1 xpassed, zero reruns) ✓ · `work_items check` ✓ (35 files). The 1
xfailed/1 xpassed pair is the same pre-existing, previously-documented nondeterministic
pair noted in prior handoffs (`test_20260708_busy_states_and_chip.py`'s two
wizard-render-scroll tests) — not new, unrelated to this branch.

**No local data note this time** — this branch made no changes to `logs/`, the DB, or
any other local runtime state.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 2 / 10 ceiling — net 0 open, net 0 total this session** (item 35 filed and
closed same-branch; item 33 still pending merge via PR #96, not yet reflected in this
branch's own BOARD.md since that branch hasn't merged to `main` yet).

**Open (2 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).

**Blocked (4):**
3. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
4. Item 5 — grounding-score persistence gap.
5. Item 8 — compose-time rewrite dial, blocked pending owner direction.
6. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
   gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
7. Item 4 — in-app citation viewer, no friction signal yet.
8. Item 7 — PX-46 memory consolidation, owner sign-off required first.
9. Item 24 — template-preview fidelity spike (T2), never scheduled.
10. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (6, once item 33 also merges — 5 on THIS branch's own BOARD.md since item
33 hasn't merged yet):**
11. Item 2 — wordmark sweep, opportunistic only.
12. Item 16 — `evals/runner.py --suite real` non-functional.
13. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
14. Item 23 — PX-52 analyzer.py split, WATCH disposition.
15. Item 33 — extract_experiences telemetry pollution (this branch's OWN BOARD.md
    still shows this as `watching`/open since it's on the not-yet-merged PR #96's
    branch, not this one — will show `closed` once #96 merges).
16. Item 34 — corpus blueprints' `_get_client` unpatched in the UX harness — a real
    billed-API risk, latent today. Standing next-pick candidate.

Additionally, a NEW, deliberately-not-cleared backlog item worth tracking: the 12
genuinely wiki-relevant files that have accumulated drift since the last real
`/wiki-self-update`/`/wiki-ingest` (listed under "What just landed" above) — not
filed as its own numbered work item since it isn't a defect, just known pending
content work that the new close-out-checklist discipline will pick up piecemeal as
those specific files are next touched, or all at once if a future session decides to
run `/wiki-self-update` deliberately against them.

17 total open+blocked+deferred+watching on THIS branch's own board (item 33 not yet
merged so its board reflects pre-merge state) — flat vs. the last handoff's 16 (item
35 opened+closed net zero; item 33 remains pending its own separate merge). Still
below the ~8-10 open-only reduction-sprint threshold (open-only count is 2).

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 35; it
does not open a new authorized branch. The next session's first move is to confirm
`fix/extract-experiences-telemetry-pollution`'s PR #96 actually goes green in CI once
this branch merges (not just trust the local recomputation), merge it, then read the
Carried-forward ledger above and `docs/dev/work/BOARD.md` directly before picking a
next item.

---

## First move

Do NOT create a branch yet. First: get this branch's own PR merged (user-confirmed
push/PR/merge, same as every branch). Then: watch PR #96's CI re-run and confirm it
passes; merge #96 once confirmed green. Only after both are merged: read the ledger
above and `docs/dev/work/BOARD.md`, propose a next item (item 34 is the standing
candidate) to the owner, and only once confirmed: create the branch, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do
not code first.**

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
   `docs/dev/prov/SPEC.md` §5 step 3); **wiki-relevance check** — if this branch's
   own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`)
   classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this
   branch's own diff and commit the wiki edit now, before opening the PR (same
   "committed before merge" discipline as memory/CHANGELOG, never a follow-up PR);
   if the touched file needed no page edit, say so explicitly rather than silently
   skipping the check; **any dev server or
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
