<!-- provenance: schema=1 session=520b7b1b-abe0-4c81-acf4-4088fa632303 branch=fix/extract-experiences-telemetry-pollution commit=c8eb74d actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-03 -->

# Agent handoff: after `fix/extract-experiences-telemetry-pollution` (item 33 closed)

**Branch to create:** none pre-authorized. Item 34 is the natural next pick per
this session's own ranking (33 → 34 → 20, all agent-owned/mechanical except 20),
but per one-item-per-branch discipline it is not started here — confirm with the
owner before creating it.
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

- `docs/dev/diagnosis/extract-experiences-telemetry-pollution.md` — the full
  evidence chain: a fresh reproduction (9 rows, `4405 -> 4414`), the traced call
  path (`onboarding/extract_experiences.py` → `analyzer._parse_or_retry` →
  `_call_llm_streaming` → `_emit_call_log`), the constraint that shaped the fix
  design (`test_analyzer_model_selection.py` / `test_demo_mode.py` need
  `_emit_call_log`'s REAL write behavior, so the fix redirects `LOG_PATH`, never
  `_emit_call_log` itself), and a disclosed cleanup-script incident (below).
- `docs/dev/work/items/0033-extract-experiences-test-pollutes-real-telemetry-log.md`
  (closed) — the resolution.
- `[[reference-fake-client-tests-must-redirect-telemetry]]` (memory, updated this
  session) — now carries a third confirmed instance of this failure shape, AND a
  new, sharper warning: **cleanup of this log file must match on timestamp AND
  shape together, never shape alone.**
- **Read before touching `logs/llm_calls.jsonl` in any way:** this session
  disclosed a mistake — a cleanup command meant to remove 9 rows this session's
  own RED-check reproduced instead matched on shape alone, silently deleting
  3,132 unrelated historical pollution rows alongside them (already-documented
  test noise per item 33's own prior measurement, not real telemetry, but
  deleted by mistake, not by authorized intent). `logs/` is gitignored with no
  git history and no other backup — irreversible. Disclosed to the user
  immediately; their direction was to leave the file as-is and record the risk.
  Full account in the diagnosis dossier's own "Incident during this branch's own
  work" section and the memory above.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice, after
being asked to rank items 20/33/34 by logical progression (33 → 34 → 20) and confirming
33 first — not from a pre-scripted sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch).

- **`fix/extract-experiences-telemetry-pollution` (this branch)** — closed item 33
  (9 fake-client tests in `test_extract_experiences.py` polluting the real telemetry
  log). Fixed with a repo-wide `tests/conftest.py` autouse fixture redirecting
  `analyzer.LOG_PATH` to `tmp_path` by default for every test; `test_extract_experiences.py`
  itself needed no code change, only a new module-scoped regression guard (same
  pattern as `test_call_kind_telemetry.py`). Disclosed and recorded a cleanup-script
  mistake made during verification (see above) — user-directed to leave the log file
  as-is and capture the risk in memory.
- **Item 34 is the natural next pick** per this session's own ranking (agent-owned,
  mechanical, same failure-shape family as 33 but a different mechanism — a real
  billed-API risk in the UX test harness, not a log-pollution one) — **not
  pre-authorized**; confirm with the owner first.
- **Item 20 remains last in that ranking** — not agent-startable without an owner
  decision on Step 5's gating behavior first.
- Do not start items 3, 5, 8, 10 without their own listed unblock (all `Blocked`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `c8eb74d` (PR #95, item 22 close-out). This branch's own work adds:

- `tests/conftest.py`: new `_default_llm_log_path` autouse fixture, redirecting
  `analyzer.LOG_PATH` to a per-test `tmp_path` for every test in the suite by default.
- `tests/test_extract_experiences.py`: new module-scoped `_real_log_line_count_unchanged`
  autouse guard (no other code changes needed — the file now inherits the conftest
  default). Confirmed the guard actually catches the regression via a deliberate RED
  check (temporarily disabling the conftest fixture reproduced `4405 -> 4414` before
  restoring it).
- `docs/dev/diagnosis/extract-experiences-telemetry-pollution.md` (new): the full
  evidence chain, including the disclosed cleanup-script incident.
- `docs/dev/work/items/0033-*.md` closed (resolution + refs); `docs/dev/work/BOARD.md`
  regenerated (open 2→2, unchanged; watching 6→5; closed 18→19). `CHANGELOG.md` entry
  added.
- `docs/dev/ledger/520b7b1b-abe0-4c81-acf4-4088fa632303.jsonl` (new): this session's own
  `consumed`-event provenance record for the incoming handoff pointer, folded in per
  `docs/dev/prov/SPEC.md` §5 step 3.
- Memory updated (not a repo file): `[[reference-fake-client-tests-must-redirect-telemetry]]`
  gained a third confirmed instance and explicit timestamp+shape cleanup guidance.

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ (342 source files) ·
non-ux pytest (`-n auto`, 2197 passed, 1 skipped, zero reruns) ✓ · ux pytest (serial, 137
passed, 1 xfailed, 1 xpassed, zero reruns) ✓ · `work_items check` ✓ (34 files). The 1
xfailed/1 xpassed pair is the same pre-existing, previously-documented nondeterministic
pair noted in the prior handoff (`test_20260708_busy_states_and_chip.py`'s two
wizard-render-scroll tests) — not new, unrelated to this branch. Real telemetry log
confirmed stable at 1,273 lines across the full gate run (non-UX suite, UX suite, and
this handoff's own authoring) — no further growth after the fix landed.

**Local data note (disclosed, not a code change):** `logs/llm_calls.jsonl` went from
4,405 lines (pre-session) to 1,273 lines, due to the cleanup-script mistake described
above — 3,141 rows removed (9 legitimate RED-check reproduction rows, plus 3,132
unrelated historical pollution rows caught by an overly broad match). Irreversible
(`logs/` is gitignored, no backup). User-directed: leave as-is.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 2 / 10 ceiling — net 0 open, net 0 total this session** (item 33 closed;
nothing newly filed).

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

**Watching (5):**
11. Item 2 — wordmark sweep, opportunistic only.
12. Item 16 — `evals/runner.py --suite real` non-functional.
13. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
14. Item 23 — PX-52 analyzer.py split, WATCH disposition.
15. Item 34 — corpus blueprints' `_get_client` unpatched in the UX harness — a real
    billed-API risk, latent today. Ranked as this session's own natural next pick.

16 total open+blocked+deferred+watching (was 17 at last handoff; item 33 closed,
nothing newly filed — net −1). This is the first handoff in three where the cumulative
count dropped rather than holding flat or growing (17 → 16) — still worth watching, not
yet at the reduction-sprint threshold.

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 33; it does
not open a new authorized branch. The next session's first move is to read the
Carried-forward ledger above and `docs/dev/work/BOARD.md` directly, then confirm with the
owner which item to pick up (item 34 is the natural next pick per this session's ranking,
but is not pre-authorized).

---

## First move

Do NOT create a branch yet. Read the ledger above and `docs/dev/work/BOARD.md`, propose
item 34 (or another item) to the owner, and only once confirmed: create the branch, write
a plan at `~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.**

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
