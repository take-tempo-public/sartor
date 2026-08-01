<!-- provenance: schema=1 session=43dd38dd-29ff-44e1-afd8-44df501173c2 branch=feat/jd-provenance-metadata commit=e2330e6 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-01 -->

# Agent handoff: after `feat/jd-provenance-metadata` (item 14 closed, item 32 filed forward)

**Branch to create:** none pre-authorized. No epic or standing stream currently has an
agent-startable next branch scripted. Read the Carried-forward ledger below and
`docs/dev/work/BOARD.md` directly, then confirm with the owner which item to pick up.
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

- `docs/dev/work/items/0014-no-jd-provenance-metadata.md` (closed) and
  `docs/dev/work/items/0032-jd-label-dashboard-rendering.md` (open) — item 14's
  full closure narrative, and the concrete UI-rendering follow-on filed forward
  from it.
- `hardening.py`'s `extract_jd_label` docstring (right after `extract_company_terms`)
  — the deterministic (title, company) extractor this branch added: its phase order,
  known limits, and the explicit non-goal (never a substitute for `jd_file` identity
  checks anywhere fail-closed).
- `evals/README.md` — three schema blocks updated this branch (bootstrap doc,
  annotations.json, eval-result records); the eval-result block also had pre-existing
  drift corrected (`schema_version: 2` → `3`, several undocumented fields added).
- `[[reference-eval-runner-judge-payload-trap]]` (memory) — the highest-risk mistake
  this branch's own design had to avoid: 2 of the 11 `"fixture":`-keyed dicts in
  `evals/runner.py` are judge INPUTS, not result records; a field added there changes
  graded prompts and silently invalidates `baseline_v1.json`.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice
(item 14, offered alongside items 9/15/21+22 as candidates), not from a pre-scripted
sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 14
was independent of item 9's dependency chain).

- **`feat/jd-provenance-metadata` (this branch)** — closed item 14 (no JD-identifying
  metadata in bootstrap/eval artifacts): added a deterministic `(title, company)`
  extractor and threaded it through every artifact surface named in the item's own
  filing. Filed item 32 forward (dashboard UI never renders the new field) as a
  deliberate scope boundary, not an oversight.
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 7, 8, 10 without their own listed unblock (all `Blocked`/`Deferred`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `e2330e6` (PR #90, item 13 close-out). This branch's own commit(s) add:

- `hardening.py`: new `extract_jd_label(jd_text) -> {"title": str, "company": str}`,
  deterministic, header-bound (first ~6 non-blank lines), reusing (not modifying)
  `extract_company_terms`'s constants — that function stays byte-identical, protecting
  its own baselined eval-scoring behavior (`tests/test_hardening.py::TestKeywordScoreFixtureRegression`).
  New `TestExtractJdLabel` class (16 tests), including a snapshot guard on
  `extract_company_terms`'s output for the 3 committed synthetic fixtures.
- `evals/bootstrap.py`: stamps `jd_label` on every `per_jd` record (computed once,
  before the paid pipeline calls, so a mid-run cancel still leaves labels on completed
  JDs) plus a top-level `jd_labels` projection for glanceability.
- `evals/annotation.py`: `build_annotation_template` carries `jd_labels` straight
  through from the bootstrap doc (no re-derivation); `collate_expected` gained an
  `anchor_name` kwarg and resolves the anchor's own label into `expected.json`'s new
  `jd_label` field.
- `evals/runner.py`: `_load_fixture` computes the label once per fixture (preferring
  an already-stamped `expected.json` value, falling back to fresh derivation) and
  stamps it onto **exactly 7** of the module's 11 `"fixture":`-keyed dicts — the
  actual result-record write sites. The other 4 (2 judge-input payloads, 1 baseline
  helper, 1 regression-comparison dict) are deliberately untouched; a dedicated test
  (`test_jd_label_absent_from_judge_payload`) captures the real `_grade` payload and
  asserts the field never reaches it. `fixture_hash` is unaffected (bytes-only).
- `blueprints/diagnostics.py`: SSE `done` event + its paired log line gained
  `jd_labels`; the collate route (and CLI `_cmd_collate`) gained `anchor_jd_label` in
  both the JSON response and the log — the collate log now names the anchor JD's
  identity at exactly the moment item 13's Zoox/Faros mismatch would have been visible
  on sight.
- `dashboard/routes.py`: `_normalize_eval_record` defaults `jd_label` for pre-F-14
  records — rendering it in the dashboard UI is explicitly **not** in this branch
  (filed forward as item 32).
- Docs: `evals/README.md`'s three schema blocks updated (bootstrap, annotations,
  eval-result — the last one's pre-existing `schema_version: 2`→stale drift corrected
  to `3` plus 8 previously-undocumented fields, at the owner's explicit direction to
  fix inline rather than ledger it); `CHANGELOG.md`; item 14 closed with a dated
  `## Updates` entry; item 32 filed; board regenerated (open 6→5→6 net 0: item 14
  closed, item 32 filed).
- No schema-version bumps anywhere (additive field; `evals/runner.py`'s
  `SCHEMA_VERSION` is an equality gate for baseline seeding — bumping it would have
  been actively harmful, not just unnecessary).

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ · non-ux pytest
(`-n auto`) ✓ · ux pytest (serial) 136 passed, 1 xfailed, 1 xpassed, zero reruns ·
`work_items check` ✓ (32 files, re-verified after filing item 32 post-gate). Ran in
the foreground after a low-free-memory reading (1.55GB/15.73GB, the same range that
previously OOM-killed a background gate run) — owner chose foreground over waiting or
chunking, matching the prior session's precedent at an almost identical reading.

**Process note for whoever runs long commands next:** the foreground gate exceeded the
Bash tool's 600s timeout and auto-backgrounded; its captured output FILE came back
truncated to only the last ~150 lines (the UX tier + `work_items check` — no trace of
the earlier ruff/mypy/non-UX-pytest sections, even though the file was read in full).
This is a **log-capture artifact, not evidence of failure** — `scripts/gate.py`'s
`main()` only ever reaches its final `gate: all steps passed.` print after every prior
step returns 0, so a captured tail ending in that line plus the background task's own
exit-code-0 is sufficient evidence for the whole run. Full writeup in
`[[reference-background-bash-kill-ceiling]]`'s newest section — read it before
re-running a truncated-looking gate log from scratch.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 6 / 10 ceiling — net 0 this session** (item 14 closed; item 32 filed forward
from it).

**Open (6 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 15 — suggested-skills comma-split rendering bug.
3. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
4. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
5. Item 22 — 4 call kinds never logged despite real call sites.
6. Item 32 — `jd_label` (item 14's own new field) not rendered anywhere in the
   dashboard UI. Deliberately scoped out of item 14's own branch; depends on 14
   (closed, so agent-startable now).

**Blocked (4):**
7. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
8. Item 5 — grounding-score persistence gap.
9. Item 8 — compose-time rewrite dial, blocked pending owner direction.
10. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
    gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
11. Item 4 — in-app citation viewer, no friction signal yet.
12. Item 7 — PX-46 memory consolidation, owner sign-off required first.
13. Item 24 — template-preview fidelity spike (T2), never scheduled.
14. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
15. Item 2 — wordmark sweep, opportunistic only.
16. Item 16 — `evals/runner.py --suite real` non-functional.
17. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
18. Item 23 — PX-52 analyzer.py split, WATCH disposition.

18 total open+blocked+deferred+watching (was 18 at last handoff; item 14 closed, item
32 filed — net 0).

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 14; it does
not open a new authorized branch. The next session's first move is to read the
Carried-forward ledger above and `docs/dev/work/BOARD.md` directly, then confirm with the
owner which item to pick up. Item 32 (dashboard rendering of `jd_label`, filed this
session) is one candidate among several open items — not a default pick.

---

## First move

Do NOT create a branch yet. Read the ledger above and `docs/dev/work/BOARD.md`, propose a
next item to the owner, and only once confirmed: create the branch, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not
code first.**

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
