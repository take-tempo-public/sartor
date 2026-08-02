<!-- provenance: schema=1 session=75b4d002-fc92-45fe-b03c-e6cc2eac5bb4 branch=fix/skill-line-parenthetical-split commit=d2a7701 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-02 -->

# Agent handoff: after `fix/skill-line-parenthetical-split` (item 15 closed, no next branch pre-scripted)

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

- `docs/dev/diagnosis/skill-line-parenthetical-split.md` — the full evidence
  chain: item 15's own filed mechanism (a comma-split in `suggest_skills`'
  LLM-output parsing) read in full and falsified, the real bracket-blind
  mechanism reproduced byte-for-byte at three independent sites, and the
  acceptance bar.
- `docs/dev/work/items/0015-skill-suggestion-rendering-split.md` (closed) —
  the full closure narrative.
- `[[feedback-trace-stated-mechanism-to-original-citation]]` (memory) —
  updated this branch with a **fifth** recurrence, and a new variant: this
  time correcting a false filed mechanism **widened** scope rather than just
  relocating it — the same bracket-blind split pattern independently
  reproduced at two more, unrelated sites once the wrong attribution was
  cleared. When a falsified mechanism turns out to be a generic/reusable
  code shape, grep for other call sites of that shape before scoping the fix
  to only the one site that was filed.
- `json_resume.py`'s `split_outside_brackets` docstring — the shared
  depth-aware split primitive now used by `evals/bootstrap.py` and
  `json_resume.py` itself; `static/app.js`'s `_splitOutsideBrackets` mirrors
  it for the JS side (no code-sharing possible across that boundary). Both
  must not go negative-depth on a stray closing bracket, and both leave an
  unbalanced opening bracket's tail as one token — read the docstring before
  changing either.

---

## Where we are in the arc

**Read before #1-7 above, this handoff specifically:** `docs/dev/work/SCHEMA.md` and
`docs/dev/work/BOARD.md` — still the authoritative live-item source, superseding
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and most of `RELEASE_ARC.md`'s endgame-steps
prose.

**Stream:** none — epic 19 (the last active, owner-directed sequential stream) closed
2026-07-31. This branch was picked from the open backlog by explicit owner choice (item 15,
offered alongside items 9/21/22, item 20 excluded as owner-gated), not from a pre-scripted
sequence.
**Sequencing rule:** strictly sequential — one branch at a time (no
conductor/waves until further notice, per charter W-1 posture).
**Blocked until this stream tags:** item 10 (`chore/release-v1.1.0`)
`depends_on = [3, 6, 7, 9, 19]` — 6 and 19 are closed; **3 and 7 are human/owner-gated
(not agent-startable); 9 is open and agent-owned** (unchanged by this branch — item 15
was independent of item 9's dependency chain).

- **`fix/skill-line-parenthetical-split` (this branch)** — closed item 15 (skill names
  with an internal comma split mid-parenthetical): corrected the item's own false filed
  mechanism, fixed the real bracket-blind delimiter split at all three sites it
  independently reproduced (`evals/bootstrap.py`, `json_resume.py`, `static/app.js`). No
  new item filed forward — this branch's own fix closed its scope cleanly, including the
  two extra sites found during diagnosis (fixed inline, not filed separately, since they
  were the identical mechanism as the filed item, just at different call sites).
- **No successor branch is pre-scripted.** Read the board's Open list and confirm with
  the owner before picking a next branch — see the top of this handoff.
- Do not start items 3, 5, 7, 8, 10 without their own listed unblock (all `Blocked`/`Deferred`
  per the board) — each is its own branch and none is authorized by this handoff.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `8a3a481` (PR #92, item 32 close-out). This branch's own commit (`d2a7701`)
adds:

- `evals/bootstrap.py`: `_split_skill_line` now splits via the new
  `json_resume.split_outside_brackets` instead of a bare `re.split` — delimiters nested
  inside `()`/`[]` are no longer treated as separators. Docstring updated; all 10
  pre-existing `TestExtractSkills` cases pass unmodified, plus 3 new cases and a new
  direct `TestSplitSkillLine` class (6 cases) covering nesting, stray/unbalanced brackets.
- `json_resume.py`: new public `split_outside_brackets(text, delim_re)` — a depth-aware
  split primitive, reused by `evals/bootstrap.py` (a stdlib-only leaf module, so no import
  cycle). Wired into both `_parse_skills` shapes (single-paragraph and grouped-bullet). New
  `TestSplitOutsideBrackets` class (7 cases) plus 2 new `TestSkills` cases.
- `static/app.js`: new `_splitOutsideBrackets(value)` mirroring the Python primitive (JS
  can't share the code); used at `saveConfig()`'s `skills`/`certifications` fields
  (previously a bare `.split(',')` that silently corrupted persisted corpus data on every
  Settings save whenever an existing entry had an internal comma).
- **Found and fixed real bugs beyond item 15's own filed scope**, not hypothetical: the
  identical bracket-blind split pattern independently reproduced (verified by execution,
  not inference) at `json_resume.py`'s skills parser — the user-facing preview/PDF/DOCX
  rendering path — and at the Settings save round trip above. Both fixed in this branch
  after explicit scope confirmation with the owner (all three sites vs. bootstrap-only vs.
  the two Python sites).
- Tests: RED-then-GREEN at all three sites. The first attempt at the Settings UX test
  asserted against the re-rendered textarea text and **passed even against the unfixed
  code** — `join(', ')` on the corrupted 3-entry array reconstructs the identical display
  string, hiding the corruption. Corrected to read the real persisted array via the config
  `GET` route instead, which does fail pre-fix; caught by actually stashing the JS fix and
  re-running before trusting the test. New file:
  `tests/ux/regression/test_20260802_settings_skill_parenthetical_split.py`.
- Docs: item 15 closed with a dated `## Updates` entry correcting its own filed mechanism;
  board regenerated (open 5→4, item 15 closed, no new item filed); `CHANGELOG.md` entry.

**Gate (`python -m scripts.gate`):** ruff ✓ (one import-sort fix needed: `json_resume`
import in `evals/bootstrap.py` was alphabetically after `hardening`, not before — fixed) ·
ruff format ✓ (one auto-format needed on `tests/test_bootstrap.py`) · mypy ✓ · non-ux
pytest (`-n auto`, 2179 passed, 1 skipped, zero reruns) ✓ · ux pytest (serial, 137 passed,
2 xpassed, zero reruns) ✓ · `work_items check` ✓ (32 files). The 2 xpassed
(`test_20260708_busy_states_and_chip.py`'s two wizard-render-scroll tests) are **not new**
— item 30's own closure note (2026-07-31) already recorded "1 xfailed/1 xpassed unchanged"
as this pair's known nondeterministic behavior; unrelated to this branch's scope (skills
parsing / config save, not scroll timing). No `xfail_strict` is set, so this does not fail
the gate. Ran the gate in the background per this project's own precedent for runs
exceeding the Bash tool's timeout; verified the actual log content each time rather than
trusting the background-task exit-code summary (per
`[[reference-background-bash-kill-ceiling]]` — a stale-cache issue in this same session
independently confirmed the exit-code claim can be wrong: the first gate re-run's
notification said "completed (exit code 0)" while the real log showed a ruff-format
failure).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full
Open/Blocked/Deferred/Watching subset is rendered below instead of `RELEASE_CHECKLIST.md`'s
Carry-forward ledger — that ledger is superseded.

**Open is 4 / 10 ceiling — net −1 this session** (item 15 closed; nothing filed forward).

**Open (4 / 10 ceiling):**
1. Item 9 — release/visual-assets refresh, screenshots stale. Blocks item 10.
2. Item 20 — legacy `generate()` reachable via wizard rail without freezing Compose
   (`decision_owner=user`).
3. Item 21 — `check_refinement_scope` LLM call invisible to telemetry.
4. Item 22 — 4 call kinds never logged despite real call sites.

**Blocked (4):**
5. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI, GHCR, `enforce_admins`).
6. Item 5 — grounding-score persistence gap.
7. Item 8 — compose-time rewrite dial, blocked pending owner direction.
8. Item 10 — release cut v1.1.0, `depends_on = [3, 6, 7, 9, 19]` — 6 and 19 closed; still
   gated on 3, 7 (human/owner) and 9 (open, agent-doable).

**Deferred (4):**
9. Item 4 — in-app citation viewer, no friction signal yet.
10. Item 7 — PX-46 memory consolidation, owner sign-off required first.
11. Item 24 — template-preview fidelity spike (T2), never scheduled.
12. Item 25 — `app.run(threaded=True)` governance decision, deliberately deferred.

**Watching (4):**
13. Item 2 — wordmark sweep, opportunistic only.
14. Item 16 — `evals/runner.py --suite real` non-functional.
15. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
16. Item 23 — PX-52 analyzer.py split, WATCH disposition.

16 total open+blocked+deferred+watching (was 17 at last handoff; item 15 closed, nothing
filed — net −1). Below the ~8–10 open-only reduction-sprint threshold.

---

## What this branch should build

**Nothing — this section is intentionally empty.** This handoff closes item 15; it does
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
