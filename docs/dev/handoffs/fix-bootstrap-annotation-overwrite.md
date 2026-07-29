<!-- provenance: schema=1 session=a4adba21-8c91-4677-bf02-cca4456c90e3 branch=fix/bootstrap-annotation-overwrite commit=48b6099 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-29 -->

# Agent handoff: after `fix/bootstrap-annotation-overwrite` (item 11 fix + 4 filed work items — DONE)

**Branch to create:** `fix/eval-judge-parse-failure` (branch off `main`)
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

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s
endgame-steps prose (both retained as historical narrative with inline
"MIGRATED to work item N" / "RESOLVED" pointers, not deleted).

**Stream:** v1.1.0 endgame.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** nothing was gated on this branch.

- ~~`docs/pipeline-truth-and-era4-baseline`~~ (merged, `f7b6562`) — pipeline
  docs truth pass + Era 4 real-corpus baseline; closed item 6 (PX-39) and
  item 17.
- **`fix/bootstrap-annotation-overwrite` (this branch, not yet merged) —
  DONE.** Full detail below. Filed 4 work items covering old-system→board
  migration gaps (items 23-26), then fixed item 11 (bootstrap overwrite)
  with a live reproduction + regression test, then assessed items 13/14 as
  NOT resolved by that fix (left open, notes added) and ranked the
  remaining board opens by priority.
- **`fix/eval-judge-parse-failure` (next, owner-directed this session)** —
  item 12: `evals/runner.py`'s `_grade` coerces a judge JSON-parse failure
  into `score: 0`, indistinguishable from a real failing grade. Owner
  picked this explicitly over the other ranked candidates (see "Carried-
  forward observations" below for the full ranking and why).
- **Everything else on the board** ← do not start on either of these two
  branches; each board item gets its own branch per the sequencing rule
  above.

---

## What just landed on `main`

**Not yet on `main` — this branch has not been merged.** `main` is
currently at `f7b6562` (the `docs/pipeline-truth-and-era4-baseline` merge,
PR #76). This branch's own work, once committed and merged, will be the
next thing to land:

1. **4 work items filed (23-26)** — a migration-gap sweep found these
   still open/deferred in the old `RELEASE_ARC.md`/`RELEASE_CHECKLIST.md`
   prose but never migrated onto `docs/dev/work/BOARD.md` (they lived in
   review-register and epic prose, outside the `chore/work-item-tracking`
   migration's scope, not dropped by it): item 23 (PX-52 analyzer.py split,
   watching), item 24 (T2 template-preview fidelity spike, deferred), item
   25 (`app.run(threaded=True)` governance decision, deferred), item 26
   (GitHub push + URL verification — filed **closed**, found already
   satisfied in practice via `git remote -v` + `pyproject.toml` check, just
   never reconciled in the old doc).
2. **Item 11 closed — fixed, not just filed.** `blueprints/diagnostics.py`'s
   bootstrap-run route wrote a fixed `bootstrap.json` unconditionally on
   every run, with no read-merge step — a second run for the same fixture
   slug silently destroyed the first run's clusters, orphaning any
   `cluster_index` an already-saved `annotations.json` (real, expensive
   human-verdicted work) still pointed at. The original cited evidence
   (`robert-bootstrap` fixture) no longer exists in this clone
   (`evals/fixtures/real/` is gitignored real user data, since rotated), so
   this session reproduced the defect fresh instead of trusting the stale
   citation: added
   `tests/test_annotation_routes.py::TestBootstrapStream::test_second_run_does_not_destroy_first_runs_bootstrap`,
   confirmed it **fails on unfixed HEAD**, then fixed. Fix: every bootstrap
   run now writes a never-colliding `bootstrap-<UTC-timestamp>.json`
   (`_new_bootstrap_path`); `bootstrap.json` is kept only as a disposable
   "latest" mirror for backward compatibility with tooling/tests reading
   the legacy fixed name. All read routes (`annotation_load`,
   `annotation_save`, `annotation_collate`, `annotation_score_grounding`)
   now resolve via `_resolve_bootstrap_path`, which pins to whichever file
   `annotations.json`'s own `bootstrap_source` field names (when it still
   exists) — so a later run can no longer even semantically hijack an
   in-progress annotation's `cluster_index` meanings, not just avoid
   deleting the old bytes. Full evidence chain in
   `docs/dev/diagnosis/bootstrap-annotation-overwrite.md`.
3. **Items 13 and 14 assessed, left open — item 11 did NOT resolve them,
   despite item 11's own body speculating it might.** Item 13 (anchor-JD
   selection can pick a JD the annotation data doesn't represent) needs its
   own fix to `pick_anchor_jd` (`evals/annotation.py:587-606`) — unchanged
   by this branch. Item 14 (no JD-name/company metadata) is answered only
   partially: this branch added RUN provenance (the timestamped filename,
   surfaced as `bootstrap_file` in the bootstrap SSE `done` event) but not
   JD-NAME provenance, which is what item 14 actually asks for. Notes
   added to both item files explaining the gap precisely so the next
   session doesn't have to re-derive it.
4. **Remaining board opens ranked by priority** (see "Carried-forward
   observations" below) and presented to the owner, who picked item 12 as
   the next branch.

**Gate: ruff ✓ · ruff format ✓ · mypy ✓ · `pytest -m "not ux" -n auto` ✓ ·
`pytest -m ux` ✓ (129 passed / 1 known xfail / 1 known xpass, matching
prior sessions — not a regression) · `work_items check` ✓ (26 files).**

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note, this handoff (same as predecessor):** `docs/dev/work/BOARD.md`'s
full Open/Blocked/Deferred/Watching subset is rendered below instead of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger — that ledger is superseded, per
"Where we are" above.

**Open (9 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item
   10 (the v1.1.0 cut). Needs the dev server + visual review, not just code.
2. Item 12 — **picked as this handoff's next branch** — judge JSON-parse
   failure silently scores as 0. Bounded, single-function fix in
   `evals/runner.py`'s `_grade`; no open design question.
3. Item 13 — Collate picks an anchor `jd.txt` that doesn't match its own
   fixture's annotations. NOT resolved by item 11 (see above) — needs a
   real heuristic decision in `pick_anchor_jd`.
4. Item 14 — no JD-identifying (name/company) metadata in bootstrap/eval
   artifacts. Only partially touched by item 11 (run provenance added, JD-
   name provenance still missing).
5. Item 15 — suggested-skills rendering bug (comma-split inside
   parentheticals). Reproducible, but the exact call site in
   `suggest_skills`'s output parsing isn't traced yet — some tracing needed
   before it's a pure mechanical fix.
6. Item 19 — UX-suite flakiness solution sprint (scheduled, not yet
   investigated) — larger scope, not a quick win.
7. Item 20 — legacy `generate()` reachable via wizard rail without freezing
   Compose (`decision_owner=user`) — needs the owner's product-flow call
   (hard-gate Step 5, or warn/redirect?) before any code.
8. Item 21 — `check_refinement_scope` LLM call invisible to telemetry. Its
   own filing calls the fix "mechanical, likely" (route through `_call_llm`
   with a `call_kind`), but touches `analyzer.py`'s LLM-call boundary —
   confirm there's no deliberate reason it skips `_call_llm` before
   rerouting it.
9. Item 22 — 4 call kinds never logged despite real call sites. Needs a
   live click-through per route to distinguish "dead path" from
   "instrumentation gap" before there's anything to fix — investigation,
   not yet a fix.

**Blocked (4):**
10. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR,
    `enforce_admins`).
11. Item 5 — grounding-score persistence gap (blocks calibrated L1/L2
    metric layers).
12. Item 8 — compose-time rewrite dial, still blocked pending owner
    direction on the real evidence channel (likely `/tune-from-annotations`,
    not decided).
13. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9]` (6 satisfied
    since the last handoff).

**Deferred (4):**
14. Item 4 — in-app citation viewer, no friction signal yet.
15. Item 7 — PX-46 memory consolidation, owner sign-off required first.
16. Item 24 — **new this branch** — template-preview fidelity spike (T2),
    never scheduled; needs a product-priority decision before any code.
17. Item 25 — **new this branch** — `app.run(threaded=True)` governance
    decision, deliberately deferred across many branches; owner-gated,
    touches the C-1-sensitive loopback-bind area.

**Watching (4):**
18. Item 2 — wordmark sweep, opportunistic only.
19. Item 16 — `evals/runner.py --suite real` non-functional, needs a real
    JD + owner data.
20. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
21. Item 23 — **new this branch** — PX-52 analyzer.py split, WATCH
    disposition, deferred post-v1.1.0 (trigger: next major prompt-surface
    work).

**At 9/10 open — one below the W-1.4 reduction-sprint ceiling.** 21 total
open+blocked+deferred+watching items (up from the predecessor handoff's 19)
— worth a reduction pass soon, though not yet over the ceiling on the
`status = "open"` count specifically (schema §5: only `open` counts against
the 10 ceiling).

**No unresolved "still-pending thread" carried from further back** — the
predecessor handoff's two open threads (the owner's "still gathering" UX
fixes, and a documentation-only investigation) were asked about at this
session's start; the owner redirected straight to a concrete question ("are
there any opens from the old system that were deferred and not on this
list?") which became this branch's item-23-26 filing work. If those two
original threads are still live, they were not re-raised this session —
worth asking the owner directly again if they're not simply resolved by now.

---

## What this branch should build

Nothing further — this branch is closed out. The next branch,
`fix/eval-judge-parse-failure`, should fix item 12
(`docs/dev/work/items/0012-judge-parse-failure-scores-zero.md`): a Haiku
judge JSON-parse failure in `evals/runner.py`'s `_grade` currently
produces `score: 0`, identical in shape to a real failing grade — a crashed
grader and a résumé that completely fails a rubric are indistinguishable in
every downstream consumer (the JSONL result, `/bench`, the `/_dashboard`
heatmap). This is a `fix/*` branch — reproduce first (a parse-failure judge
response, real or synthesized, driving `_grade` to the buggy branch) and
fill in `docs/dev/diagnosis/eval-judge-parse-failure.md`'s `## Observed`
before touching `evals/runner.py`.

Scope is bounded to item 12 only. Do not expand into items 13, 14, 15, 19,
21, or 22 on this same branch — each gets its own branch per the
sequencing rule above.

---

## First move

Create branch `fix/eval-judge-parse-failure` off `main`, then follow C-7:
reproduce the parse-failure-scores-as-zero behavior on demand (a fresh
regression test is the cleanest instrument, same pattern this branch used
for item 11) and fill in the diagnosis doc's `## Observed` section before
touching `evals/runner.py`. **Do not code the fix first.**

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
