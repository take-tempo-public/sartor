<!-- provenance: schema=1 session=c6221f23-8b99-4759-9ce5-08ab8e9ed9a6 branch=fix/run-row-letter-edit-shadow commit=840c87b actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-14 -->

# Agent handoff — a new cover letter now clears the run row's typed letter edit (`fix/run-row-letter-edit-shadow`, item 163) → owner's next drawdown pick

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session closed item 163 on one branch (owner pick, 2026-10-14).**
> - **The defect:** after a generate or a detached `/api/generate-cover-letter` replaced a letter,
>   the context dropped the typed letter edit but `ApplicationRun.edited_cover_letter_text` kept
>   it, so a Pipeline resume showed the typed text over the new letter and `has_edits` stayed true.
> - **Observed on all three routes before the fix**, including the detached route the item had only
>   inferred (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O1-O3).
> - **The fix** is `blueprints/generation.py` only: the run row's letter edit is nulled exactly
>   when the context consumes it, derived from `resolve_cover_letter_after_generate`'s result.
> - **One adjacent path was observed and left alone:** the frozen `carry_edits=True` generate keeps
>   the typed letter edit over a newly produced letter on the context, the run row and the response
>   alike (O5). That is consistent, so it is not this defect; whether it is the right product
>   behaviour is the owner's call, and nothing here decides it.

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

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157): items 123/124/136/148–151 closed, 153 filed.
- ~~`fix/console-run-lock-hardening`~~ ✓ (#158): items 112/117–121 closed, 154 filed.
- ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159): item 153 closed, 155 filed.
- ~~`fix/python-direct-hooks-plan-gate`~~ ✓ (#160): items 152/111/154/143 closed, 156 filed.
- ~~`fix/heredoc-escape-guard`~~ ✓ (#161): item 142 closed, items 157 and 158 filed.
- ~~`fix/bash-tool-transport`~~ ✓ (#162): items 157 (falsified) and 158 closed.
- ~~`fix/test-reliability`~~ ✓ (#163): items 155 and 156 closed.
- ~~`test/assertion-strength`~~ ✓ (#164): items 115, 116, 122 and 159 closed.
- ~~`fix/frozen-composition-staleness`~~ ✓ (#165): items 106, 132 and 66 closed; 160 and 161 filed.
- ~~`fix/regenerate-persistence`~~ ✓ (#166): item 160 closed; 162 filed.
- ~~`fix/regenerate-keeps-cover-letter`~~ ✓ (#167): item 162 closed; 163 filed.
- ~~`fix/recurrence-guardrails`~~ ✓ (#168): items 164-167 filed and closed, item 55 closed;
  168 and 169 filed (watching).
- ~~`fix/run-row-letter-edit-shadow`~~ ✓ (PR pending): item 163 closed.
- **Next: the owner's pick.** Not started:
  - item 161 (`GET /composition` parses the context about eleven times per request; counted from
    the code, not measured, so the first step is a measurement);
  - item 7 memory-consolidation apply (Deferred);
  - item 30's C-7 probe branch;
  - launcher items 145–147;
  - the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/run-row-letter-edit-shadow`:

| Commit | What |
|---|---|
| `b2bafb1` | **The dossiers and the reproduction first** (C-7, C-10). `docs/dev/diagnosis/run-row-letter-edit-shadow.md` (`## Observed` O1-O5), `docs/dev/blast-radius/run-row-letter-edit-shadow.md`, `tests/test_run_row_letter_edit.py` with the three defect arms as `xfail(strict=True, raises=AssertionError)`, and this session's consumed-ledger file. Run on `main` @ `562a3a0` with `--runxfail`, all three failed at the invariant line after their controls held. |
| `09f2771` | **The fix.** `_clear_run_edits(run_id, *, resume, letter)`; new `_clear_consumed_run_edits`, called by both generate routes; `_persist_cover_letter_to_db` nulls the column in its existing session. Only the three xfail markers were deleted from the instrument. CHANGELOG entry. |
| `840c87b` | Item 163 closed (`verified_by`, board regenerated); the wiki's "writes **only** `generated_cover_letter_md`" sentence corrected in `application-audit-chain.md`; `docs/wiki/log.md` entry; consumer grep re-derived. |
| (this commit) | This handoff and its `generated` ledger file. |

**Tests run locally** (`-p no:rerunfailures`):
- `tests/test_run_row_letter_edit.py`: 8 passed (3 controls x2 arms of `C2`, `C1`, `C3`, `A1`/`A2` json and stream, `A3`, `A5`);
- that file with `test_regenerate_cover_letter`, `test_regenerate_persistence`, `test_app_iteration`, `test_application_routes`, `test_xfail_controls_gate`: **145 passed, 31 s**;
- **mutation check**, file restored and its sha256 verified after each: forcing `clear_letter = False` fails exactly `A1`/`A2` (2 failed, 6 passed); removing the `= None` line in `_persist_cover_letter_to_db` fails exactly `A3` (1 failed, 7 passed);
- `ruff check` and `ruff format --check` clean on the changed Python; `mypy blueprints/generation.py` clean; `work_items check` OK (169); `wiki_cites` OK; `wiki_freshness` OK (38 < 75); `tests/test_wiki_cites.py` 34 passed.

**Gate:**
- `python -m scripts.gate --result`, run on `840c87b` (the commit before this handoff):
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-14T14:17:58-0700, HEAD 840c87b`
- **That result goes stale the moment this handoff is committed**, because the result binds to
  HEAD and this commit moves it. The gate ran on the tree one docs commit short of this one
  (the handoff, its ledger file and the item 169 note).
- **What it ran:** `ruff check` and `ruff format --check` clean; `mypy` clean;
  `pytest -m "not ux" -n auto` **3373 passed, 8 skipped** (6 m 32 s; 3365 before this branch, the
  8 new are `tests/test_run_row_letter_edit.py`); `pytest -m ux` **171 passed, 2 xpassed**
  (9 m 02 s); `work_items check` OK (169). The log holds no `FAILED`, `ERROR` or `RERUN` status
  line (a `grep -aE` count of 0). The 2 xpassed are the two deliberately non-strict xfails in
  `tests/ux/regression/test_20260708_busy_states_and_chip.py`, which this branch does not touch.
- **The run was not killed**, and it passed the 52% UX mark where the previous session's first
  run was reaped. I kept the turn active with a blocking wait on the gate's process, as the
  previous handoff advised; whether that mattered is unproven (one run).
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
- **CI on the PR:** not yet run; the PR is not open. Push needs the owner's confirmation.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 22 / 10 ceiling -- OVER"**
(this branch closed 163; nothing was filed as Open). The owner's drawdown direction stands: down
to 0 if possible, before alpha staging. That is well past the ~8–10 reduction-sprint threshold.

`## Open` (20 items listed; the header's 22 also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **128** *(owner)*: D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **133** *(owner)*: No route, UI or script removes a user. Product decision: wanted, and when?
- **134**: Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right.
- **135** *(owner)*: Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule.
- **137**: Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **161**: Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (44) and `## Epics` (6) in `BOARD.md`. Item **169** gained one observation this
session (see below); **168** is unchanged.

Declared, not filed. Carried from the previous handoff and **not re-verified this session**
unless marked:
- **New: the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced
  letter, and the run row agrees with the context** (observed, `docs/dev/diagnosis/run-row-letter-edit-shadow.md`
  O5). Consistent across context, run row, response and `resume_state`, so not a 163-class defect.
  Whether that is the right behaviour is an owner question. Recorded in that dossier and the
  blast-radius dossier's `## Deferred`, not filed as an item.
- **New: the interrogative witness paused the first `Edit` after a subagent hand-back message**
  (item 169's class: a prompt shape not yet seen arms the pause). Observed once; the payload was
  not captured, so *which* shape armed it is unverified. The hand-back arrived as "Another Claude
  session sent a message"; the pause cleared on re-running the identical call, as designed.
- **New: `ruff` is not on the Git Bash PATH here**; `python -m ruff` works. The IDE's Pyright
  also reports `int(None-able)` at `blueprints/generation.py` near lines 567 and 573; those lines
  are outside this diff and `mypy` is clean. Not investigated.
- **New: the auditor in the wiki pass was scoped to the changed paragraph**, 15 claims, not the
  whole of `application-audit-chain.md`. The other four pages that describe the letter edit were
  checked by reading, not by an auditor.
- **the sibling window's gap is one sample.** 1.133 s between a pause and the batch-mate's
  hook (diagnosis O8). The 3 s default is a judgment, not a measurement of a distribution.
- **a trunk-time `compacted` row is no longer in `git log`.** Branch-time rows are
  (item 165). Items 84, 93, 94 and 110 cite branch-time rows, which are unchanged.
- **`plan_gate` reports a detached HEAD as `""`**, so its `plan-archived` receipt stays in
  the tracked shard there. Recorded in item 169.
- **E1 sees a `lines N-M` reference only when a path is on the same or the preceding
  line**, and E3 is word-presence in the file, weaker than "defined here" (`scripts/wiki_cites.py`
  docstring).
- **`ALLOWED_LINE_CITES` holds 25 line cites on 8 pages.** `education-degree-field-rendering.md`
  has 12. Converting one to a symbol forces the entry down; that is the intent.
- **edits made outside the Edit|Write gates this session:** `tests/test_interrogative_witness.py`
  (removing the instrument), `tests/test_ledger_spool.py` and the work-item files, through
  Python scripts run from Bash; `docs/wiki/log.md` through a shell heredoc. None is a gated
  surface (`tests/**` and `docs/**` are exempt); declared because the carried item below says the
  gates cannot see such writes. The `block-doubled-backslash` guard also stopped three of my own
  heredocs, which is that guard working.
- **The two UX tests `fix/frozen-composition-staleness` added ran on CI #165 only** (carried).
- **Bash-run scripts edit files without the Edit|Write gates seeing them** (carried).
- **A gap-fill retire, or a drag back to the same position, marks an approval stale without
  changing the résumé** (carried).
- **Approvals frozen before `fix/frozen-composition-staleness` carry no digest** (carried).
- **The post-generate announcement still says "Resume and cover letter generated"** when no
  cover letter was produced (`static/app.js`, `runGeneration`'s `_announce`) (carried).
- **`lastCoverLetterPath` is assigned in seven places and read by none** (`static/app.js`)
  (carried).
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN), as counted by an earlier `/wiki-lint`.
- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html`); no caller reads
  it (carried).
- **`docs/dev/diagnostics.md` cites code by line number**, which rots on every edit (carried).
- **The derived-set test's `git ls-files` costs 1.8–5.2 s on this machine** under 0.5–0.8 GB
  free (carried).
- **Transitive wiki relevance is not modelled** (`PERFORMANCE_HISTORY.md` →
  `scripts/perf_baseline.py`) (carried).
- **`python3` resolution on hypha and the homelab is unchecked.** On a machine without `python3`
  on PATH no hook starts and the gates fail open (`docs/governance/enforcement.md`) (carried).
- **`tests/test_plan_approval_scoping.py` takes about 6 minutes locally.** Split it by `-k`
  class. This session's `-k` run took 35 s (carried).
- **Pre-existing count drift**, each deferred in `docs/dev/blast-radius/bash-tool-transport.md`:
  `docs/governance/enforcement.md:29-31` says "8 exist" (14 rules now); `TestBashDispatcher`'s
  docstring names four guards (there are seven); `blast_radius.py`'s `result.py` entry says "10
  non-test importers" (carried).
- **Item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry** (carried).
- **The threaded UX `live_server` may expose route reads on Windows** (inferred, not observed;
  `docs/dev/diagnosis/test-reliability.md` §Inferred) (carried).
- **`tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt** (run 30940947527). Not investigated (carried).
- **The full local gate takes more than 25 minutes on this machine.** Run it in the background
  with a 35–40 minute budget, never a shorter `timeout` (carried).
- **A fresh pytest start costs 9–47 s here, depending on free RAM** (carried).
- **Free memory read 3.6–4.4 GB at this session's close-out and never fell below 2.74 GB during
  the 14.5-minute gate run** (131 samples, 5 s apart; `mem_sampler.py` in the session
  scratchpad, a Windows `GlobalMemoryStatusEx` sampler), against 0.5–1.1 GB earlier in the
  month. **A harness kill for "low memory" still happened once at 4.36 GB free at start, and
  is unexplained** (see Gate above). Treat a background job's survival as unproven; keep the
  turn active while the gate runs.

---

## Recurrences observed this session → guardrail authored

1. **A drive stubbed one of two routes, and a strict-xfail arm could have read it as the defect**
   (item 167's class; recognized as a recurrence of that class, in its first live use).
   - **The instance:** `[stream]` arm `A1A2-stream`, first run. `tests/test_regenerate_cover_letter.py`'s
     `_generate_stub` replaces `bgen.generate` only; `/api/generate/stream` calls
     `generate_streaming`, which the rig stubs separately and never with a letter.
   - **The existing mechanism held:** the arm's drive step raised `ControlFailed` through
     `tests/_controls.py`, so it failed loudly instead of xfailing. `tests/test_xfail_controls_gate.py`
     enforces the marker shape; nothing enforces that a *step* uses `control` (declared limit,
     C-0), and I used it because I was following the convention.
   - **Authored here:** a local `_generate_stub` in `tests/test_run_row_letter_edit.py` that stubs
     both routes. The older helper is untouched, so its stream arms still drive the rig's stub.
     Its resume-only stream arms stay valid because no letter is expected either way, which is a
     reading of the code and not a re-run.
2. **The wiki scribe wrote a bare line cite** (member of item 166's class: a scribe outside its
   brief).
   - **The instance:** `blueprints/generation.py:194`, mid-sentence, with the paragraph's wrapping
     joined into one line.
   - **The existing mechanism held:** `scripts/wiki_cites.py` E1 failed the page
     (`wiki_cites: FAILED (1 violation(s)...)`); re-anchored to a symbol; re-run OK.
   - **Plainly:** the join of wrapped lines is a style regression no check sees. I caught it in
     review (step 6, unenforced).
3. **A first Edit after a subagent hand-back paused again** (item 169's class; second recorded
   shape). **No mechanism authored and none is possible from here:** the payload was not
   captured, so there is nothing to classify. Said plainly and surfaced here; item 169 is the
   home, and it needs a witness trace, not a branch.
4. **A report carried across a context boundary was verified before use** (C-12 class, held, not
   a failure): the scribe's one-line hand-back was checked against `git diff` and the cite check
   before anything depended on it. Recorded as held, not as new guardrail work.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list above,
under item 40's drawdown direction. Item 161 is the nearest follow-on in the same files and
needs a measurement before a fix. Items 168 and 169 are Watching: they need a live
`/wiki-self-update` pass and a witness trace respectively, not a branch.

Scope is whatever the owner names, as filed in `docs/dev/work/items/`. Do not expand beyond it.

---

## First move

Run the pointer check and `--event consumed`, then ask the owner which Open item comes next.
Then create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to
the user before touching any code. **Do not code first.**

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
