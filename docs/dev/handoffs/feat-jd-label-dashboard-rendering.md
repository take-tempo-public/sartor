<!-- provenance: schema=1 session=79329036-7f48-4757-9f7d-9f9d4a4cb1d6 branch=feat/jd-label-dashboard-rendering commit=91ed83e actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-01 -->

# Agent handoff: after `feat/jd-label-dashboard-rendering` (item 32 closed, no next branch pre-scripted)

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

- `docs/dev/work/items/0032-jd-label-dashboard-rendering.md` (closed) — the full
  closure narrative, including the correction to this item's own stale filing.
- `[[reference-eval-results-dir-heterogeneous-files]]` (memory) — the crash this
  branch found and fixed: `evals/results/*.jsonl` can hold non-eval reports from
  other tools (a `vector_before_after_*.jsonl` comparison run) that lack
  `fixture`/`score` entirely. Every aggregation in `dashboard/routes.py` already
  filters on a truthy `fixture`; any NEW code touching individual records
  directly (not through an existing `.get()`-filtered aggregation) must do the
  same or it will 500 on Jinja's `Undefined` against this checkout's real data —
  synthetic test fixtures will not catch this, since you control their shape.
- `[[feedback-trace-stated-mechanism-to-original-citation]]` (memory) — updated
  this branch with a fourth recurrence: a filed item's claim about **where**
  something lives (not just why it's broken) can be as stale as a mechanism
  claim. Verify a work item's own file/line citations against the current repo
  before planning around them.
- `dashboard/routes.py`'s `_jd_label_display` and `_fixture_jd_labels` docstrings
  — the display-join rule and the shared most-recent-non-blank-wins map, reused
  identically by the heatmap and baseline-health surfaces so they can never
  disagree on one fixture's label.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice (item 32,
offered alongside items 15/21/22 as candidates), not from a pre-scripted sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 32
was independent of item 9's dependency chain).

- **`feat/jd-label-dashboard-rendering` (this branch)** — closed item 32 (`jd_label` not
  rendered anywhere in the dashboard UI): rendered the F-14 JD label on 5 dashboard/annotate
  surfaces and restored a table deleted by a prior redesign. No new item filed forward — this
  branch's own fix closed its scope cleanly, with one incidental defect (the
  `vector_before_after_*.jsonl` crash) found and fixed inline, not filed separately, since it
  was directly caused by and scoped to the surface this branch added.
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 7, 8, 10 without their own listed unblock (all `Blocked`/`Deferred`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `80bb43d` (PR #91, item 14 close-out). This branch's own commit (`91ed83e`)
adds:

- `dashboard/routes.py`: new `_jd_label_display(label) -> str` (isinstance-guarded join of
  the F-14 `{title, company}` dict — a malformed `jd_label` surviving
  `_normalize_eval_record`'s `setdefault` would otherwise resolve `.title` to Python's
  `str.title` method inside Jinja) and `_fixture_jd_labels(records) -> dict[str, str]` (one
  shared most-recent-non-blank-wins map per fixture, called once in `index()`, so the heatmap
  and baseline-health table — which apply different record filters — can never disagree on
  the same fixture's label). `index()`'s `eval_results` template variable now also filters on
  a truthy `fixture` and stamps a per-record `jd_label_display` (see the crash below).
- `dashboard/templates/dashboard.html`: a `.jd-label` CSS rule (muted second line, ellipsis-
  clamped — the heatmap table is `width:auto` with no `overflow-x` wrapper, so an unclamped
  label would inflate every column); the label rendered on the heatmap `<th>` and the
  baseline-health fixture cell; a **restored** "recent evals" tile + detail block (deleted in
  the v1.0.5 tabbed-console redesign, commit `edde81d` — this item's own filing named the
  table by stale line numbers that no longer matched the file; corrected during this branch,
  not carried forward); `loadFixtures()`'s dropdown option text now names the JD (or a count
  summary for a multi-JD bootstrap, since there's no single anchor identity until collate
  time); `renderCollateResult()` now renders `anchor_jd_label` (a field item 14 already
  computed and shipped but nothing displayed).
- `blueprints/diagnostics.py`: `annotation_fixtures()` (the `/api/annotation/fixtures` list
  route) now echoes each bootstrap's `jd_labels` verbatim — zero extra IO, the doc is already
  loaded.
- **Found and fixed a real crash**, not a hypothetical: this checkout's own
  `evals/results/` directory holds a `vector_before_after_*.jsonl` report from an unrelated
  tool that shares the directory but carries no `fixture`/`score` at all. Every existing
  aggregation in `dashboard/routes.py` already tolerates this via `.get()`-based filtering;
  the restored table is the first surface to render individual records directly via Jinja
  dot-access, and it 500'd (`UndefinedError` on `r.score >= 4.0`) the moment it ran against
  real data instead of synthetic test fixtures. Fixed at the same filter point
  (`index()`'s `eval_results` build now requires a truthy `fixture`), with a regression test
  reproducing the exact record shape (`tests/test_dashboard_routes.py::
  TestIndexRoutePopulated::test_non_eval_record_sharing_the_results_dir_does_not_crash`).
  Full detail: `[[reference-eval-results-dir-heterogeneous-files]]`.
- Tests: new `TestJdLabelDisplay` + `TestFixtureJdLabels` unit classes; a new
  `TestIndexRoutePopulated` class (the dashboard's **first** test to render the template with
  populated eval data — every prior route test only exercised the empty-state path), built on
  an extracted `dash_client` fixture; `TestFixturesList` gained a verbatim-echo test;
  `tests/ux/a11y/test_axe_smoke.py::test_axe_dashboard_console` widened to open the heatmap +
  health tiles (probed clean against **current** markup before any new markup was written, so
  a later failure could be attributed cleanly); `tests/ux/flows/test_dashboard_console.py` and
  `test_annotation_tab.py` each gained a `jd_label` seed field and matching assertions.
- Docs: `evals/README.md` corrected in the same pass — two claims describing the deleted
  recent-eval table as if it still existed (one is now literally true again, since this
  branch restored the table). `CHANGELOG.md` entry; item 32 closed with a dated `## Updates`
  entry; board regenerated (open 6→5, item 32 closed, no new item filed).

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ · non-ux pytest
(`-n auto`, 2161 passed, 1 skipped) ✓ · ux pytest (serial, 136 passed, 2 xfailed, zero
reruns) ✓ · `work_items check` ✓ (32 files). Two backgrounded re-runs were needed along the
way: one ANN401 fix (`label: Any` → `label: object` — the correct type for an
isinstance-narrowed, untrusted value; ruff's `ANN401` rule flags `Any` specifically, not
`object`) and one `ruff format` auto-fix on two files. Ran in the background each time per
this project's own precedent for gate runs exceeding the Bash tool's timeout.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 5 / 10 ceiling — net −1 this session** (item 32 closed; nothing filed forward).

**Open (5 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 15 — suggested-skills comma-split rendering bug.
3. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
4. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
5. Item 22 — 4 call kinds never logged despite real call sites.

**Blocked (4):**
6. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
7. Item 5 — grounding-score persistence gap.
8. Item 8 — compose-time rewrite dial, blocked pending owner direction.
9. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
   gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
10. Item 4 — in-app citation viewer, no friction signal yet.
11. Item 7 — PX-46 memory consolidation, owner sign-off required first.
12. Item 24 — template-preview fidelity spike (T2), never scheduled.
13. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
14. Item 2 — wordmark sweep, opportunistic only.
15. Item 16 — `evals/runner.py --suite real` non-functional.
16. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
17. Item 23 — PX-52 analyzer.py split, WATCH disposition.

17 total open+blocked+deferred+watching (was 18 at last handoff; item 32 closed, nothing
filed — net −1). Below the ~8–10 open-only reduction-sprint threshold.

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 32; it does
not open a new authorized branch. The next session's first move is to read the
Carried-forward ledger above and `docs/dev/work/BOARD.md` directly, then confirm with the
owner which item to pick up.

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
