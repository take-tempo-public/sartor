<!-- provenance: schema=1 session=d2af43a0-e500-4a5a-a955-a89d28702c68 branch=fix/console-run-lock-hardening commit=0cdb544 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-06 -->

# Agent handoff — console run lock (`fix/console-run-lock-hardening`) → wiki relevance (item 153)

**Branch to create:** `fix/wiki-relevance-cited-scripts` (branch off `main`)
**Base branch:** `main`

> **This session fixed the diagnostics console.** Items 112, 117, 118, 119, 120 and 121 are
> fixed and closed, each with `verified_by` test ids. Item 154 is filed. The branch is
> `fix/console-run-lock-hardening`, on `main` 4f6f34a. It merges through its PR once the owner
> confirms.
>
> **CI is the gate, owner-directed (2026-10-05), and still is.** Free RAM was 0.71–1.05 GB all
> session, so the full local gate was not run. The targeted tests below were. After any local
> gate run, cite `python -m scripts.gate --result`, not a notification.
>
> **The owner chose the next branch (2026-10-06): item 153.** Of the open drawdown candidates
> (items 7, 30, 145–147, 153), the owner picked 153.

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
- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157): items 123/124/136/148–151 closed, 153 filed.
- ~~`fix/console-run-lock-hardening`~~ ✓ (PR pending): items 112/117–121 closed, 154 filed.
- **`fix/wiki-relevance-cited-scripts`** ← next (owner's pick, 2026-10-06): item 153.
- Item 7 memory-consolidation apply (Deferred); item 30 C-7 probe branch; launcher items
  145–147; item 154 (plan-approval recurrence): not started.

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold item 154, the launcher items or any other
item into the item-153 branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/console-run-lock-hardening`:
- `b6afece`: the C-7 instrument. The dossier, 11 Python and 3 UX tests that failed on `main`,
  and this session's consumed-ledger file.
- `496cc9f`: the instrument re-run on the rebased tip, recorded under `## Observed`.
  - 12 Python node ids failed, not the dossier's "11".
  - `test_stale_release…` first failed on a `Page.goto` timeout, then reproduced its quoted
    assertion alone in 301 s.
- `5799106`: the fix.
  - 112: `dashboard/routes.py:_parse_date` returns aware UTC.
  - 117: `blueprints/diagnostics.py:_single_flight_sse` and `_RUN_SLOT`, a process-wide slot
    over the four SSE run routes. A second run gets 409; the worker frees the slot in its
    `finally`.
  - 118: `analyzer._HEADER_VALUE_PATTERN` handles quoted keys and Basic auth.
  - 119: `sartorRunLock` hands out an owner token and only that token's `release` frees it.
  - 120: `run()` acquires before marking its button pending.
  - 121: `_iter_jsonl` reads object lines only and prefilters on the JSON-quoted run id.
  - `tests/conftest.py:_drain_diagnostics_run_slot`: a bounded teardown drain that fails
    closed.
  - The C-10 dossier, `docs/dev/blast-radius/console-run-lock-hardening.md`, was written
    before the first edit. The dossier records two deviations: 118 masks the scheme word with
    the credential, and 121 uses the quoted-token prefilter.
- `0cdb544` and this handoff's commit:
  - items closed, item 154 filed, item 143 updated (sixth instance);
  - `docs/dev/diagnostics.md` rewritten for the lock and every cite re-anchored;
  - the `dashFilters` help copy fixed;
  - wiki `diagnostics-console` and `index.md` updated, plus a `log.md` entry.
- **Tests:** both runs used `-p no:rerunfailures`, so no test was retried.
  - Python: 162 passed (`test_dashboard_routes`, `test_annotation_routes`,
    `test_llm_call_error_capture`).
  - UX: 9 passed (the new ownership test plus the three existing run-lock files).
  - Ruff, format and mypy are clean on the touched files.
- **Gate:** the full local gate was not run (memory). CI on the PR is the gate. Check it with
  `python -m scripts.ci_wait <n>`; a result of 3 means stop, not merge.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 32 / 10 ceiling -- OVER"**
(this branch's tip). It was 37 at this branch's start: six items closed, one filed. The owner's
drawdown direction stands: down to 0 if possible, before alpha staging. This is well past the
~8–10 reduction-sprint threshold.

`## Open` (30 items; the header's 32 also counts the two open epics, 19 and 36). Generated from
the board; owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **111**: Plan-approval hook: ~2 s per edit, 8-21 s per retire, from MSYS fork count. Item 110 fixed correctness, not speed.
- **115**: Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring.
- **116**: Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified.
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
- **154**: Approved on main, then checkout+rebase; next Edit hit NO EDIT APPROVAL. Item 110's class; cause unverified.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` and `## Epics` in `BOARD.md`. Open epics 19 (UX flake) and 36 (epic A) are unchanged.

Declared, not filed (still true):
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN).
- **Item 128 (owner):** stray stdin-reader hook helpers, left running (owner's call).
  - At this close-out (`Win32_Process`, 2026-10-06), pids 22820 and 2264 from earlier
    sessions were still alive.
  - Two are new during this session: pid 45296 (`adapters/claude_dispatcher.py`, 11:18) and
    pid 45104 (`python3.exe -c "import sys,json; print(json.load(sys.stdin)…"`, 11:57).
  - In all, 19 such `python3*` stdin-readers date from 2026-09-18 to today.
  - None was started by this session's own commands. The link to hooks is inferred from their
    command lines and not verified.
- **New: `sartorEval.run()` returns no handle on its success path** (`dashboard.html`, the end
  of `run()`). Only its declined path returns `{abort}`. No caller reads the return value.
  Recorded under `## Deferred` in `docs/dev/blast-radius/console-run-lock-hardening.md`.
- **New: one UX test took 301 s alone** (`test_stale_release_does_not_free_a_live_run`, before
  the fix, at about 1 GB free RAM). After the fix, the same file took 4–7 s per call. The cause
  was not investigated; the timing is noted only.
- **New: `docs/dev/diagnostics.md` cites code by line number.** Its cites were already off
  before this branch (the lock was cited at `:2142`, but sat at `:2184` on `main`). They are
  re-anchored now, but line cites in a hand-maintained dev doc rot on every edit. The wiki
  cites by symbol and does not have this problem.

---

## Recurrences observed this session → guardrail authored

1. **A process-wide lock leaks between tests.** This is the shared-state test-leak class
   (item 33's temp-state leak is the earlier instance). I recognized it before writing the
   slot: `TestRunCancelDisconnect` returns while its worker is still unwinding.
   - **Mechanism, fails closed:** `tests/conftest.py:_drain_diagnostics_run_slot`, autouse.
     After every test it waits up to 15 s for the slot. If the slot is still held, it calls
     `pytest.fail` naming the test that leaked it. It never resets the slot. The owner's memory
     `reference-process-wide-run-slot-test-drain` has the details.
2. **The witness paused a Write while the reader of its file ran in the same batch** (item 143,
   now six instances). A scratchpad lint script's Write paused; the `python` call that ran it
   failed with `Errno 2`.
   - **No mechanism authored:** a hook-ordering change is outside this branch's items. The rule
     followed is prose and **unenforced**: never batch a reader with the Write that creates its
     input. **Surfaced to the owner.** Recorded on item 143.
3. **The plan-approval stamp retired mid-branch** (item 110's class). It was reported by the
   previous handoff and filed here as item 154.
   - **No mechanism:** the cause is undiagnosed, and item 154 names the instrument to build
     first. This session avoided it with an **unenforced** workaround: setup-only work under a
     `main` approval, then re-entering plan mode and re-approving on the branch before any
     production edit. **Surfaced to the owner.**
4. **A hand-maintained count was stale** (C-10's "rots in both directions" class). The dossier's
   acceptance bar said 11 Python tests; 12 node ids failed.
   - **No mechanism:** the bar is now stated as "every failing node id here passes", recorded
     in the dossier. Prose; **unenforced**.
5. **Docs carried a defect forward after its fix.** The in-app `dashFilters` help and
   `docs/dev/diagnostics.md` both described item 112 as a live bug. The wiki said there was no
   server lock.
   - **No mechanism:** they were found by grepping for the item numbers and changed symbols at
     close-out. Nothing ties a "known issue" sentence to its item's status. **Surfaced to the
     owner.**
6. **Subagent reports carried facts.** The scribe's summary was checked against `git diff`.
   The auditor's UNSUPPORTED finding was checked against the `annotation_score_grounding`
   docstring before it went to the owner. No mechanism is possible (C-12, as declared in
   earlier handoffs).

---

## What this branch should build

`fix/wiki-relevance-cited-scripts`, item 153 only. The authority is the owner's 2026-10-06 pick,
item 40's drawdown direction, and `docs/dev/work/items/0153-wiki-relevance-misses-cited-scripts.md`.

1. **C-7 instrument first.** Add a failing test in `tests/test_wiki_relevance_classification.py`.
   For every `scripts/*.py` path cited anywhere under `docs/wiki/pages/`, assert that
   `scripts.wiki_relevance.is_wiki_relevant(path)` is `True`. On `main` it fails on
   `scripts/gate.py`, `scripts/ci_wait.py`, `scripts/work_items.py`, `scripts/doc_lints.py` and
   the other files the item counts. **Re-derive that list with grep;** never copy it from the
   item text. Write `docs/dev/diagnosis/wiki-relevance-cited-scripts.md` with `## Observed`
   before any production edit.
2. **The fix:** derive the overrides from what the wiki cites, rather than hand-listing them in
   `scripts/wiki_relevance.py` (`RELEVANT_OVERRIDES`, `:109`; `is_wiki_relevant`, `:214`).
   - Keep the module's dual-check pattern (memory
     `reference-maintained-classification-list-pattern`).
   - Weigh the efficiency of each design. The function runs inside the freshness gate and the
     commit-time reminder, so it should not rescan the whole wiki on every call without a
     reason written at the site.
3. **C-10, and the guard will enforce it.** `scripts/wiki_relevance.py` is a **gated
   surface** in `scripts/enforcement/blast_radius.py`, registered as a "helper": "the
   classifier behind a merge-blocking freshness gate". `require-consumer-enumeration` blocks
   every edit to it until `docs/dev/blast-radius/wiki-relevance-cited-scripts.md` has a
   `## Consumers` section naming it.
   - Consumers seen by grep this session: `scripts/wiki_freshness.py`,
     `hooks/wiki-freshness-reminder.sh`, and the maintainer-lane close-out relevance check.
     The tests are `tests/test_wiki_relevance_classification.py`,
     `tests/test_blast_radius_classification.py` and `tests/test_consumer_enumeration_gate.py`.
   - **Re-derive the list yourself;** this one is a snapshot.

Scope is bounded to item 153 as filed in `docs/dev/work/items/`. Do not expand beyond it.

---

## First move

Create branch `fix/wiki-relevance-cited-scripts` off `main`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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
