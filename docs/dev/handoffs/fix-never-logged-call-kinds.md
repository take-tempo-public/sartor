<!-- provenance: schema=1 session=dbfc3d98-79dc-4694-ac23-81259a489c22 branch=fix/never-logged-call-kinds commit=9d875cc actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-03 -->

# Agent handoff: after `fix/never-logged-call-kinds` (item 22 closed, no next branch pre-scripted)

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

- `docs/dev/diagnosis/never-logged-call-kinds.md` — the full evidence chain: an
  append-order analysis proving `recommend_skill`/`suggest_skill`'s log rows were
  imported from the owner's separate E2E clone after item 22 was filed (not produced
  by this checkout); three falsification tiers (an inventory-complete capability
  probe, route-level reachability tests, a live click-through against a real running
  app) proving `recommend_experience_summary`/`draft_surgical_refinement` were
  genuinely never logged simply because their own preconditions had never existed on
  this machine; and the pre-registered rival-hypothesis table (b1–b6) each tier
  closed.
- `docs/dev/work/items/0022-never-logged-call-kinds.md` (closed) — the corrected
  filing and resolution.
- `docs/dev/work/items/0033-extract-experiences-test-pollutes-real-telemetry-log.md`
  (updated, still `watching`) — this branch's own gate runs re-triggered this exact
  pollution **twice** (9 rows, then 9 more), confirming the item's magnitude claim was
  understated (71.1% of the real log is synthetic, not "low-severity"); cleaned both
  times by exact-match removal, same remediation as item 21. A repo-wide
  `tests/conftest.py` fix is proposed, not implemented.
- `docs/dev/work/items/0034-corpus-blueprints-get-client-unpatched-in-ux-harness.md`
  (new, `watching`) — `blueprints/corpus/skills.py`/`proposals.py`'s `_get_client` is
  unpatched in `install_llm_stubs`; worse than the `draft_surgical_refinement` gap
  this branch fixed (a real billed API call risk on a machine with `.api_key`
  present, not just an uncaught exception). Latent — no current UX test reaches it.
- `[[reference-append-order-vs-timestamp-detects-backdated-log-import]]` (memory,
  new this session) — the generalized technique: in an append-only log, a
  `timestamp[n+1] < timestamp[n]` violation proves the block at that point was
  bulk-imported, regardless of what timestamps it carries. This is what distinguished
  "the item's claim was wrong" from "the item's claim was correct when written, then
  overtaken by an unrelated data import."
- Both `tests/test_call_kind_telemetry.py` and `tests/test_call_kind_route_telemetry.py`
  drive the REAL `_call_llm_streaming` funnel with a fake client (not `_parse_or_retry`
  patched out, unlike every pre-existing test for these six call kinds) — read their
  module docstrings before adding a 7th near-identical fake-client copy elsewhere;
  extracting a shared `tests/llm_fakes.py` is filed as a chore, not done here.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice (item
22, offered alongside items 9/34, item 20 excluded as owner-gated), not from a
pre-scripted sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 22
was independent of item 9's dependency chain).

- **`fix/never-logged-call-kinds` (this branch)** — closed item 22 (four `call_kind`s
  claimed never logged): found the filing wrong in two directions
  (`recommend_skill`/`suggest_skill` DO have rows — imported from a separate instance
  after filing, proven by append-order analysis; `recommend_experience_summary`/
  `draft_surgical_refinement` were genuinely never logged, proven via three
  falsification tiers rather than assumed). **No `analyzer.py` change** — the funnel,
  routes, and frontend dispatch all work correctly. Fixed a latent, prophylactic UX-stub
  gap (`draft_surgical_refinement`, same shape item 21 fixed); corrected item 33's
  severity; filed item 34 (a worse, real-API-risk sibling of the stub gap, not fixed
  here per one-item-per-branch discipline).
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 8, 10 without their own listed unblock (all `Blocked`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `172273d` (PR #94, item 21 close-out). This branch's own work adds:

- `docs/dev/diagnosis/never-logged-call-kinds.md` (new): the full evidence chain —
  Tier 0 census (append-order analysis, DB/context census, repo-wide `call_kind`
  inventory), Tier 1 (inventory-complete capability probe, 7/7 passed), Tier 2
  (route-level reachability, 2/2 passed), Tier 3 (live click-through against a real
  `python app.py`, candidate `testuser`, producing two real priced rows for the first
  time on this machine).
- `tests/test_call_kind_telemetry.py` (new): AST-walks every `call_kind=` literal
  repo-wide (20 literals, 23 call sites) asserting an explicit frozenset (closes rival
  b6 — a whole unreviewed class of never-logged calls), plus one runtime probe per
  zero-row call kind (all six, not just item 22's four) driving the real analyzer
  function through the real telemetry funnel.
- `tests/test_call_kind_route_telemetry.py` (new): drives the real Flask routes for
  `recommend_experience_summary`/`draft_surgical_refinement` with the real analyzer
  function (every pre-existing route test for these two patches the function itself,
  never exercising the real funnel) — fake client injected only at the
  `blueprints.applications._get_client` seam.
- `tests/ux/stubs.py`: `install_llm_stubs` now stubs `draft_surgical_refinement`
  (`fake_draft_surgical_refinement`) — prophylactic, no observed leak (no current UX
  test reaches this route in a gate-satisfying state), same shape item 21 fixed for
  `check_refinement_scope`.
- `docs/dev/work/items/0022-*.md` closed (resolution + corrected refs);
  `0033-*.md` updated (real magnitude: 71.1% of the log, not "low-severity"); new
  `0034-*.md` filed (`watching`). `docs/dev/work/BOARD.md` regenerated (open 3→2).
  `CHANGELOG.md` entry added.
- **Real telemetry log hygiene:** this branch's own gate runs re-triggered item 33's
  pre-existing pollution bug **twice** (9 synthetic `extract_experiences` rows each
  time, `input_tokens=100, output_tokens=50, latency_ms≈0`) — both cleaned by exact
  match, keeping the two legitimate Tier-3 rows this branch produced.

**Gate (`python -m scripts.gate`):** ruff ✓ · ruff format ✓ · mypy ✓ (342 source files) ·
non-ux pytest (`-n auto`, 2197 passed, 1 skipped, zero reruns) ✓ · ux pytest (serial, 137
passed, 1 xfailed, 1 xpassed, zero reruns) ✓ · `work_items check` ✓ (34 files). The 1
xfailed/1 xpassed pair (`test_20260708_busy_states_and_chip.py`'s two wizard-render-scroll
tests) is **not new** — recorded as this pair's known nondeterministic behavior in prior
handoffs; unrelated to this branch's scope. A separate, third test in the same file
(`test_scroll_spy_attributes_overlapping_refresh_corpus_calls`) failed once on an earlier
gate attempt under unrelated load, passed cleanly in isolation and on the confirming
clean gate run — a documented pre-existing flake (`docs/dev/diagnosis/ux-scroll-position-flake.md`,
`ux-scroll-wizard-rail-flake.md`), not touched by anything on this branch. **End-to-end
verified against a live `python app.py`:** real `POST /api/applications/7/composition`
(freeze), `/draft-refinement`, and `/recommend-experience-summaries` calls against
candidate `testuser` produced two real priced rows (`draft_surgical_refinement`
`claude-sonnet-5` $0.019683; `recommend_experience_summary` `claude-haiku-4-5-20251001`),
both visible in `/_dashboard` with zero aggregator code changes. Dev server process tree
(nohup → launcher → the actual Werkzeug reloader worker child) killed after verification,
confirmed via `Get-CimInstance Win32_Process` + a follow-up connection-refused check.

**Local DB/data note (not a code change, disclosed for the record):** this branch's Tier
3 live verification inserted two real `ExperienceSummaryItem` rows on candidate
`testuser`'s current experience and froze `application_id=7`'s `approved_composition` —
the first time either state has existed on this machine. Deliberately used `testuser`
(the dev/test persona), never `robert` (the owner's real job-search data). This state is
left in place as ordinary dev-sandbox data, not reverted.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 2 / 10 ceiling — net −1 open, net 0 total this session** (item 22 closed;
item 34 filed as `watching`, not `open`).

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

**Watching (6):**
11. Item 2 — wordmark sweep, opportunistic only.
12. Item 16 — `evals/runner.py --suite real` non-functional.
13. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
14. Item 23 — PX-52 analyzer.py split, WATCH disposition.
15. Item 33 — `tests/test_extract_experiences.py` writes fake rows into the real
    telemetry log — magnitude corrected this session (71.1% of the log, not
    "low-severity"); a repo-wide `conftest.py` fix proposed, not implemented.
16. Item 34 (new) — corpus blueprints' `_get_client` unpatched in the UX harness —
    a real billed-API risk if ever exercised, latent today.

17 total open+blocked+deferred+watching (was 16 at last handoff; item 22 closed,
item 34 filed — net +1). **This is the third handoff in a row where the cumulative
count held flat or grew (16 → 16 → 17)** — worth a reduction sprint the next time an
agent has slack, per the ~8–10 open-only threshold's neighboring-band guidance (the
open-only count, 2, is well under it, but the full cumulative count keeps climbing).

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 22; it does
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
