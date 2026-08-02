<!-- provenance: schema=1 session=3e1192f5-470c-402d-b03c-c32ad02c2e99 branch=fix/refinement-scope-check-telemetry commit=c143ae0 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-02 -->

# Agent handoff: after `fix/refinement-scope-check-telemetry` (item 21 closed, no next branch pre-scripted)

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

- `docs/dev/diagnosis/refinement-scope-check-telemetry.md` — the full evidence
  chain: item 21's own filed mechanism (`check_refinement_scope` bypassing
  `_call_llm` via a direct `client.messages.create`) confirmed correct by
  direct code read plus an empirical check of the local `logs/llm_calls.jsonl`
  (4393 records, 22 distinct call kinds, zero `check_refinement_scope`); the
  O-3 sub-finding (the UX test harness's `install_llm_stubs` never stubbed
  this call, so every UX refinement flow silently exercised only the
  fail-open path) confirmed by execution, not just code-reading; and a
  **second defect found and fixed during this same branch's own
  test-writing** — the first draft of `tests/test_refinement_scope.py` only
  redirected telemetry in 3 of 9 tests, so running the file wrote real rows
  into the developer's live `logs/llm_calls.jsonl`, caught by line-count
  diffing before/after a run.
- `docs/dev/work/items/0021-refinement-scope-check-untelemetered.md` (closed) —
  the full closure narrative.
- `docs/dev/work/items/0033-extract-experiences-test-pollutes-real-telemetry-log.md`
  (new, `watching`) — a **pre-existing, unrelated** version of this same
  test-isolation shape found in `tests/test_extract_experiences.py` while
  diagnosing this branch's own instance. Deliberately left unfixed (out of
  scope for this branch) — the fix is mechanical and cheap whenever that file
  is next opened for its own reason.
- `[[reference-fake-client-tests-must-redirect-telemetry]]` (memory) — the
  generalized lesson: any test driving a fake anthropic client through the
  real `_call_llm_streaming` must redirect `_emit_call_log`/`LOG_PATH` via an
  **autouse** fixture, not an opt-in helper some tests skip, or it silently
  pollutes the real telemetry file. Two independent confirmed instances now
  (this branch's own new test file, and item 33).
- `analyzer.py`'s `_call_llm`/`_call_llm_streaming`/`_parse_or_retry` now take
  an optional `max_tokens: int = MAX_TOKENS` kwarg (byte-identical for every
  pre-existing call site) — read this before adding a new LLM call site that
  needs a tighter output cap than the shared default.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice (item
21, offered alongside items 9/22, item 20 excluded as owner-gated), not from a
pre-scripted sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 21
was independent of item 9's dependency chain).

- **`fix/refinement-scope-check-telemetry` (this branch)** — closed item 21
  (`check_refinement_scope` invisible to telemetry): routed the call through
  `_parse_or_retry` like every other Haiku call site (new `RefinementScopeResponse`
  model, named+registered `SCOPE_CHECK_SYSTEM_PROMPT`), threaded an optional
  `max_tokens` kwarg through the shared funnel to preserve the call's original
  128-token cap, fixed the UX-harness fail-open gap (O-3), and — found during this
  branch's own test-writing, not filed separately — fixed a test-isolation bug in
  its own new test file that was writing fake rows into the real telemetry log
  (and filed the pre-existing sibling instance in `test_extract_experiences.py` as
  item 33, `watching`, deliberately not fixed here).
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 8, 10 without their own listed unblock (all `Blocked`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `c143ae0` (PR #93, item 15 close-out). This branch's own work adds:

- `analyzer.py`: `check_refinement_scope` now calls `_parse_or_retry` (new
  `RefinementScopeResponse` Pydantic model, `call_kind="check_refinement_scope"`,
  `model=HAIKU_MODEL`, `max_tokens=128`, a named `SCOPE_CHECK_SYSTEM_PROMPT`
  registered in `_BASE_SYSTEM_PROMPTS`) instead of a direct
  `client.messages.create`. `_call_llm`/`_call_llm_streaming`/`_parse_or_retry`
  gained an optional `max_tokens: int = MAX_TOKENS` kwarg, byte-identical for
  every pre-existing call site. The outer `except Exception` fail-open wrapper
  (`{"valid": true}` on any failure) is unchanged; an outage now also produces a
  `status="error"` telemetry row instead of vanishing. `SCOPE_CHECK_MODEL` (a
  duplicate literal of `HAIKU_MODEL`) is deleted.
- `tests/ux/stubs.py`: `install_llm_stubs` now stubs `check_refinement_scope`
  (`fake_check_refinement_scope`, deterministic `{"valid": true}`) on
  `blueprints.generation` — closes the O-3 gap where every UX refinement flow was
  silently exercising only the real function's fail-open path against a `None`
  client.
- `tests/test_refinement_scope.py` (new): 9 tests, all fail on HEAD before the fix
  (the falsification experiment for the diagnosis dossier) and pass after. Every
  test is protected by an **autouse** `_telemetry` fixture — the file's own first
  draft omitted this on 3+1 tests and polluted the real `logs/llm_calls.jsonl`;
  fixed and verified via before/after line-count diffing.
- Docs: `docs/wiki/pages/llm-call-catalog.md`, `deterministic-llm-boundary.md`,
  `code-module-map.md`, and `docs/architecture.md` (sequence diagram + routing
  diagram + prose) all updated — they previously documented this call as the one
  deliberate exception to the telemetry funnel; that claim is now false and all
  four are corrected. `blueprints/diagnostics.py`'s docstring corrected (said
  "eight" `_BASE_SYSTEM_PROMPTS` keys; already stale at 15, now 16 — reworded to
  not restate a volatile count). `CHANGELOG.md` entry added.
- Item 21 closed with a dated `## Updates` entry; item 33 filed (`watching`) for
  the pre-existing sibling gap in `test_extract_experiences.py`; board regenerated
  (open 4→3, watching 4→5, item 21 closed, item 33 filed).
- **Real telemetry log hygiene:** the developer's actual `logs/llm_calls.jsonl`
  had 19 test-artifact rows written into it during this session (10 from this
  branch's own pre-fix test file, 9 from the pre-existing `test_extract_experiences.py`
  gap surfaced by an unrelated full-gate run) — all removed by exact
  `(timestamp, call)` match, keeping every real row including the one legitimate
  end-to-end verification row this branch produced.

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ (one fix needed on
`tests/ux/stubs.py` after the initial stub edit) · mypy ✓ (340 source files) ·
non-ux pytest (`-n auto`, 2188 passed, 1 skipped, zero reruns) ✓ · ux pytest
(serial, 137 passed, 1 xfailed, 1 xpassed, zero reruns) ✓ · `work_items check` ✓
(33 files). The 1 xfailed/1 xpassed pair
(`test_20260708_busy_states_and_chip.py`'s two wizard-render-scroll tests) is
**not new** — recorded as this pair's known nondeterministic behavior in prior
handoffs; unrelated to this branch's scope. Ran the gate twice: once before
discovering the telemetry test-isolation bug, once after fixing it — both fully
green, confirming the fix didn't regress anything. **End-to-end verified against
a live `python app.py`:** a real `POST /api/validate-refinement` produced a
priced `check_refinement_scope` row (`model=claude-haiku-4-5-20251001`,
`input_tokens=195`, `output_tokens=13`, `latency_ms=1308`, `status=ok`), visible
4× in the rendered `/_dashboard` HTML with zero aggregator code changes (every
consumer derives call kinds from the data). Dev server processes killed after
verification — the actual listening PID was the Werkzeug reloader's worker
child, not the launching shell PID (per
`[[reference-werkzeug-reloader-orphan-child]]`), found via
`Get-CimInstance Win32_Process` after `taskkill` on the wrong PID left the port
still bound.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 3 / 10 ceiling — net −1 open, net 0 total this session** (item 21 closed;
item 33 filed as `watching`, not `open`).

**Open (3 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
3. Item 22 — 4 call kinds never logged despite real call sites.

**Blocked (4):**
4. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
5. Item 5 — grounding-score persistence gap.
6. Item 8 — compose-time rewrite dial, blocked pending owner direction.
7. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
   gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
8. Item 4 — in-app citation viewer, no friction signal yet.
9. Item 7 — PX-46 memory consolidation, owner sign-off required first.
10. Item 24 — template-preview fidelity spike (T2), never scheduled.
11. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (5):**
12. Item 2 — wordmark sweep, opportunistic only.
13. Item 16 — `evals/runner.py --suite real` non-functional.
14. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
15. Item 23 — PX-52 analyzer.py split, WATCH disposition.
16. Item 33 — `tests/test_extract_experiences.py` writes fake rows into the real
    telemetry log (new this session — see above).

16 total open+blocked+deferred+watching (was 16 at last handoff; item 21 closed,
item 33 filed — net 0). At the ~8–10 open-only reduction-sprint threshold's
neighboring band; the **open-only** count (3) is well under it, but the full
cumulative count (16) has now held flat for two handoffs in a row — worth a look
next time it grows rather than holds.

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 21; it does
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
