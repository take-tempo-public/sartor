<!-- provenance: schema=1 session=2b79cef7-1384-4089-b860-bd4864c0e9aa branch=fix/hook-guard-false-blocks commit=62ab275 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-05 -->

# Agent handoff — enforcement fixes (`fix/hook-guard-false-blocks`) → console run lock

**Branch to create:** `fix/console-run-lock-hardening` (it exists already as a local worktree; bring it onto the new `main`)
**Base branch:** `main`

> **This session landed the hook branch.** Items 123, 124, 136, 148, 149, 150 and 151 are fixed
> and closed, each with `verified_by` test ids. Item 153 is filed. The branch is
> `fix/hook-guard-false-blocks`, three commits on `main` c384fad. It merges through its PR once
> the owner confirms.
>
> **CI is the gate, owner-directed (2026-10-05).** The laptop had 0.5–1.1 GB free RAM all
> session. Owner: "set it and let ci be the gate". `core.hooksPath` is now `.githooks` on the
> owner's clone, set on the owner's direction, so the native `pre-commit` / `pre-merge-commit` /
> `pre-push` hooks are live from here on. A local `python -m scripts.gate` now refuses without
> that setting (item 150). After any local run, cite `python -m scripts.gate --result`, not a
> background notification (item 151).
>
> **`fix/console-run-lock-hardening` exists only as an uncommitted local worktree**
> (`C:/Dev/sartor-wt-console`). It holds a dossier and tests that fail on `main`, and no
> production fix yet. It is the only copy.

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
5. `docs/dev/architecture.md` — module map and LLM routing
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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging
(owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- ~~`chore/flake-shard-slim`~~ ✓ (#155): item 144, the held flake shard slimmed and committed.
- ~~`chore/agent-doc-drift`~~ ✓ (#156): items 54/141 closed, 148–152 filed.
- ~~`fix/hook-guard-false-blocks`~~ ✓ (PR pending): items 123/124/136/148/149/150/151 closed, 153 filed.
- **`fix/console-run-lock-hardening`** ← next: items 112, 117, 118, 119, 120, 121.
- Item 7 memory-consolidation apply; item 30 C-7 probe branch; launcher items 145–147;
  item 153 (wiki relevance): not started.

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold item 153 or any other item into the
console branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/hook-guard-false-blocks`:
- `783f922`: the C-7 instrument. The diagnosis dossier, 13 tests that fail on `main`, and
  this session's consumed-ledger file. The commit subject says "14"; the 14th was a
  PowerShell-launch artifact, recorded in the dossier's `## Observed`.
- `541e06b`: the fix.
  - New `scripts/enforcement/shell_split.py`, the shared splitter and tokenizer.
  - `verify_binary_on_path` handles brace groups and gives a `python -m` hint (123, 124).
  - `block_merge_to_main.targets_main` judges each segment by its command word, and reads
    git past its global options (136, 149).
  - `gitutil.repo_root` resolves the edited file's own checkout (148).
  - `scripts/gate.py` adds a hooksPath preflight and `gate-result.json` / `--result` (150, 151).
  - `tests/conftest.py` autouse-redirects the result file.
  - Tests: 229 passed across the evidence, consumer, C-12 and enforcement-core files, with no
    reruns; the gate tests had 40 passed and 3 skipped.
- `62ab275` + this handoff commit (`62ab275` at writing): items closed, item 153 filed, item 143
  updated, `CONTRIBUTING.md` / `maintainer-lane.md` gate text, wiki `code-module-map` gate row
  (audited 7/7 SUPPORTED) and a log entry.
- **Gate:** the full local gate was not run (memory). Ruff, format and mypy were clean on the
  touched files. CI on the PR is the gate. Check it with `python -m scripts.ci_wait <n>`; a
  result of 3 means stop, not merge.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 37 / 10 ceiling -- OVER"** (this branch's tip). The owner's drawdown direction stands: down to 0 if possible, before alpha staging. This is well past the ~8–10 reduction-sprint threshold.

`## Open` (35 items; the header's 37 also counts the two open epics, 19 and 36). Generated from
the board; owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **111**: Plan-approval hook: ~2 s per edit, 8-21 s per retire, from MSYS fork count. Item 110 fixed correctness, not speed.
- **112**: Any Since date crashes the console: _filter_calls compares a naive floor to offset-aware (+00:00) timestamps.
- **115**: Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring.
- **116**: Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified.
- **117**: Two tabs (or curl) can start two paid runs at once: LOCK_BTN_IDS/acquire() are client-only, no server lock.
- **118**: _HEADER_VALUE_PATTERN skips {'x-api-key': ...} / {"authorization": ...} and masks only the word 'Basic'.
- **119**: Any release() frees the lock, and three inline acquire() sites start a run even when acquire() returned false.
- **120**: run() calls setBtnPending before the acquire() check; the early return never clears it.
- **121**: GET /api/run/<id> materializes the whole log to find one run; _read_jsonl keeps non-dict lines -> AttributeError.
- **122**: Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names.
- **128** *(owner)*: D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **132**: Follow-up answers save, but regenerate re-assembles the frozen composition with no AI call. UNVERIFIED.
- **133** *(owner)*: No route, UI or script removes a user. Product decision: wanted, and when?
- **134**: Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right.
- **135** *(owner)*: Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule.
- **137**: Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **142**: Heredoc python scripts with backslash escapes wrote a backspace char and a broken file; a Bash guard could refuse them.
- **143**: Witness paused the plan Write; ExitPlanMode in the same batch still ran, so the owner approved the old plan text.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **152**: A Bash with no grep/sleep made a Monitor spin. Owner chose Python-direct hooks (no .sh wrappers) + a shell probe.
- **153**: RELEVANT_OVERRIDES lists 4 scripts; wiki pages cite 13. gate.py (26 cites) changed and the relevance check missed it.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` and `## Epics` in `BOARD.md`. Open epics 19 (UX flake) and 36 (epic A) are unchanged.

Declared, not filed (still true):
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN).
- **Item 128 (owner):** stray stdin-reader hook helpers seen at close-out, left running (owner's call):
  - pid 22820, `prompt_witness_hook.py`, started 2026-10-04 10:40;
  - **new:** pid 2264, `claude_dispatcher.py`, started 2026-10-05 12:53:24. That is one minute
    before this session's plan approval was retired (12:54). The timing is noted only; no link
    is verified.
- **The console worktree** `C:/Dev/sartor-wt-console` is uncommitted and exists nowhere else.
  Don't remove it until its branch is committed.
- **New, unfiled: the plan-approval stamp retired mid-branch.** The plan was approved while on
  `main`. The session then checked out and rebased `fix/hook-guard-false-blocks`, and the next
  `Edit` hit `NO EDIT APPROVAL` (archive dir mtime 12:54). Re-entering plan mode and
  re-approving cleared it. **Cause not verified.** It matches the class in memory
  `reference-flush-stale-plan-stamp-on-branch-not-main`. Capture it in your branch's sweep:
  file it, or fold it into an existing plan-approval item.

---

## Recurrences observed this session → guardrail authored

1. **Item 136's merge guard blocked text, again.** A `python - <<'PYEOF'` heredoc holding this
   fix's own source was refused, a known recurrence of 136.
   - **Mechanism:** the segment parser in `scripts/enforcement/guards/block_merge_to_main.py`
     (`_judge`, `_judge_segment`), pinned by
     `tests/test_enforcement_core.py::TestBlockMergeToMainUnit::test_merge_text_in_arguments_is_not_a_merge`
     and `::test_real_merges_still_block`.
   - **Stated limit:** a heredoc BODY that mentions a merge to main still blocks, by design
     (fail closed). The way round is to put the script in a file with the Write tool.
2. **A background notification is not a result** (item 151's class). This session read logs
   instead of trusting notifications.
   - **Mechanism:** `scripts/gate.py` writes `gate-result.json` on every terminal path, and
     `python -m scripts.gate --result` checks it, pinned by
     `tests/test_gate_result_and_hooks_path.py::TestResultFile`.
3. **A guard read the main checkout instead of the edited worktree** (item 148's class, the
   recurrence of `defect ii` in the merge guard's history).
   - **Mechanism:** `scripts/enforcement/gitutil.py:repo_root`, plus a static test that pins the
     only `CLAUDE_PROJECT_DIR` readers
     (`tests/test_evidence_gate.py::TestRepoRootFollowsTheWorktree`).
4. **A witness PAUSE on one call of a parallel batch while its dependent call ran** (item 143,
   now five instances). A subagent hand-back re-armed the witness; the Write of item 153 paused
   while `work_items board --write` ran without it. It was harmless.
   - **No mechanism authored:** it is a hook-ordering change, outside this branch's items. The
     rule followed is prose and **unenforced**: never batch a reader with the Write that
     creates its input. **Surfaced to the owner.** Recorded on item 143.
5. **The plan-approval stamp retired mid-branch** after an approval on `main` (memory
   `reference-flush-stale-plan-stamp-on-branch-not-main` is this class).
   - **No mechanism:** the cause was not diagnosed this session. It is listed above as
     declared-not-filed, and **surfaced to the owner.**
6. **The wiki-relevance classifier missed a cited file** (`scripts/gate.py`). This is the
   false-negative mirror of the false positives in `docs/wiki/log.md`.
   - **No mechanism yet:** filed as item 153, with a test design named in it. **Surfaced to
     the owner.**
7. **A subagent's report carried facts.** The grounding auditor's line citations were
   spot-checked against `scripts/gate.py` before use. No mechanism is possible (C-12, as declared
   in earlier handoffs).

---

## What this branch should build

`fix/console-run-lock-hardening`, items 112, 117, 118, 119, 120, 121. The authority is item 40's
2026-10-02 drawdown sequence and the items themselves (`docs/dev/work/items/`).

1. **Bring the work in.** Check `git worktree list`: `C:/Dev/sartor-wt-console` should be on
   `fix/console-run-lock-hardening` @ d270506. Uncommitted, it should hold
   `docs/dev/diagnosis/console-run-lock-hardening.md`, the new
   `tests/ux/regression/test_20261003_run_lock_ownership.py`, and edits to
   `tests/test_annotation_routes.py`, `tests/test_dashboard_routes.py` and
   `tests/test_llm_call_error_capture.py` (+166 lines). Never reconstruct a missing file from
   this text.
   - Commit those in the worktree, `git worktree remove` it, then check out and `git rebase main`
     in the main checkout. That is the order this session used for the hook branch. Item 148
     has landed, so working in a worktree is also possible now.
   - Fold this session's consumed-ledger file into that first commit. Re-run the dossier's
     tests on the new `main` and record any difference under `## Observed` before going on.
2. **The fixes are the dossier's `## The fix`**, one line per item. Read it in full:
   - 112: `_parse_date` returns aware UTC;
   - 117: a single-flight slot in `blueprints/diagnostics.py`, 409 when held;
   - 118: the header-redaction pattern;
   - 119: `acquire()` returns a token, and `release(token)` checks the owner;
   - 120: `run()` acquires before it marks its button pending;
   - 121: `_iter_jsonl` yields only object lines, with a run-id prefilter.

   Routes touched under `blueprints/` keep the `_safe_username` / `_within` pattern
   (`route-security-lint`).
3. **Acceptance bar (dossier):** the 11 Python and 3 UX tests pass. The existing run-lock UX
   tests (`test_20260709_diagnostics_run_lock.py`, `test_20260720_diagnostics_run_cancel.py`
   and `test_20260923_annotate_collate_run_lock.py`) still pass. The gate is green with no
   reruns.

Scope is bounded to those items as filed in `docs/dev/work/items/`. Do not expand beyond them.

---

## First move

Create branch `fix/console-run-lock-hardening` off `main`. It already exists as the worktree
named above: commit, remove and rebase as step 1 describes. Then write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code
first.** Approve the plan **after** the branch is checked out, not while on `main`: an
approval stamped on `main` was retired mid-branch this session (see Carried-forward).

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

**6. Enumerate consumers before changing a contract (charter C-10).** Before
implementing any change to a **schema, a shared contract, or a widely-consumed
helper**, enumerate its consumers **grep-complete** — the whole tree, and every
name the thing goes by (symbol, string form, re-export, raw-SQL column, template
selector) — and **decide-and-document each site before the first edit.**
- **The ordering is the mechanism.** An enumeration written afterwards is a
  description of what you did. Written first, it is the thing that tells you the
  change is bigger than you thought.
- **A site you skip deliberately gets a written reason** under `## Deferred`. The
  same site skipped silently is a defect the next person finds.
- **Treat any hand-maintained consumer list as stale until you re-derive it** — it
  rots in *both* directions, naming sites already fixed and omitting sites that
  are not.
- The `require-consumer-enumeration` hook blocks edits to a gated surface (registry:
  `scripts/enforcement/blast_radius.py`) until
  `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section naming that
  surface. There is no escape hatch. That dossier's directory and `tests/**` stay
  writable, so the way through is always open: **write down who consumes it.**

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
   the user the URL) → **wait for the required checks with
   `python -m scripts.ci_wait <n>`** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **`scripts/ci_wait.py` is the single definition of "the PR is green" — never
   hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner.** It
   exits **0** only when every required check passed *and* no test needed a
   retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do
   not merge on it reflexively), **1** a failing required check plus its log
   tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled
   30-minute watches once ran to completion emitting *nothing* while a required
   check was already red — that silence is the failure this replaces.
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
