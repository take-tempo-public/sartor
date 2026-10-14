<!-- provenance: schema=1 session=8463b4af-b6eb-492e-9744-c3e4acdadb39 branch=fix/recurrence-guardrails commit=5040ce1 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-14 -->

# Agent handoff — four recurrences from the last handoff now have mechanisms (`fix/recurrence-guardrails`, items 164-167 and 55) → owner's next drawdown pick

**Branch to create:** none directed by this session. The owner picks the next drawdown item;
see "What this branch should build".
**Base branch:** `main`

> **This session answered the previous handoff's four "no mechanism" recurrences, on one
> bundled branch (owner decision, 2026-10-14).**
> - **Witness (item 164):** a task-notification no longer re-arms the pause, and a paused call's
>   batch-mates are refused with it for a short window. The second half is a timing heuristic.
> - **Ledger rows on trunk (items 165, 55):** hook-written `compacted` and `plan-archived` rows go
>   to an untracked spool while HEAD is on `main`; `SPEC.md` now names both events.
> - **Wiki loop (item 166):** `scripts/wiki_cites.py`, the auditor on Sonnet 5, an explicit review
>   step (prose, unenforced).
> - **xfail controls (item 167):** `tests/test_xfail_controls_gate.py` and the shared
>   `tests/_controls.py`.
> - **Two plan steps changed on evidence.** The transcript cannot show a paused call's batch at
>   hook time (A3 as designed is falsified, 2 of 2), and the cite check is a pytest test, so no
>   separate `scripts/gate.py` step. Both are in `docs/dev/diagnosis/recurrence-guardrails.md`.

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
- ~~`fix/recurrence-guardrails`~~ ✓ (PR pending): items 164-167 filed and closed, item 55 closed;
  168 and 169 filed (watching).
- **Next: the owner's pick.** Not started:
  - item 163 (the run row's typed letter edit shadows a newly generated letter in
    `resume_state`; observed for a with-letter generate, inferred for the cover-letter route);
  - item 161 (`GET /composition` parses the context about eleven times per request);
  - item 7 memory-consolidation apply (Deferred);
  - item 30's C-7 probe branch;
  - launcher items 145–147;
  - the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase), `fix/recurrence-guardrails`:

| Commit | What |
|---|---|
| `4f409d4` | **The dossiers first** (C-7, C-10). Items 164-167, `docs/dev/diagnosis/recurrence-guardrails.md` (`## Observed` O1-O5), `docs/dev/blast-radius/recurrence-guardrails.md`, and this session's consumed-ledger file. |
| `d3e5296`, `a2bdc9c` | **The instrument.** A fail-open trace of what a `UserPromptSubmit` payload and a pause look like, in the OS temp dir. One of its own tests caught a leak in the first cut (a 32-character head carried part of a task id). |
| `28812dd` | **The witness fix.** `record_prompt` skips arming on a `<task-notification>` prompt; `decide` stamps `paused_at` and refuses main-agent Edit/Write calls inside `SARTOR_WITNESS_BATCH_WINDOW_S` (default 3 s). 22 tests, mutation-checked in-process. |
| `960dcd9` | The instrument removed (`git show d3e5296 a2bdc9c` keeps it); `docs/governance/enforcement.md`; item 164 closed. |
| `9dbf581` | **The ledger fix.** `scripts/enforcement/ledger_spool.py`; both writers go through `hook_shard`; `compaction_count` reads both places; `SPEC.md` §3 names the two hook events; items 165 and 55 closed. 6 of the 10 reproduction tests failed on the unfixed code first; the other 4 were controls that held (O12). |
| `da82f71` | **The xfail gate.** `tests/_controls.py`, `tests/test_xfail_controls_gate.py`; the two files that defined `ControlFailed` import it; item 167 closed. |
| `b7ad1c7` | **The wiki loop.** `scripts/wiki_cites.py`, the auditor on `claude-sonnet-5` with four explicit checks, `/wiki-self-update` steps 4 and 6, the `RELEVANT_OVERRIDES` entry the derived-set test required, `CLAUDE.md` / `tooling.md` / `decisions.md` PX-47b; item 166 closed. |
| `c040d10`, `490f021` | Dossier O12-O17 and the declared limits; `CHANGELOG.md`; the verified no-edit wiki log entry; items 168 and 169 filed. |
| `5040ce1` | Dossier O18: the first local gate run was killed at 52% of the UX tier; ruff, format, mypy and all 3365 non-UX tests had passed. |
| (this commit) | This handoff. |

**Tests run locally** (`-p no:rerunfailures`):
- witness 61, ledger spool 13, xfail gate 14, wiki cites 34, regenerate cover letter 10;
- a sweep of `test_enforcement_core`, `test_n1_pipeline`, `test_enforcement_coverage`,
  `test_governance_hooks_gate`, `test_evidence_gate`, `test_c12_disclosure_gate`,
  `test_ledger_spool`, `test_verify_doc_template`, `test_interrogative_witness`:
  **408 passed, 2 skipped, 128 s**, plus `test_plan_approval_scoping.py -k "Archive or Retire or
  Killed or Receipt"`: 11 passed. **The first version of this sweep was wrong:** one `-k` filtered
  every file in the invocation (`22 passed, 364 deselected`) and the background task still said
  `exit 0`. It was caught by reading the summary line (diagnosis O17).
- end to end through the real `hook.py` entry points on throwaway repos (O11, O13);
- `ruff check .` clean, `ruff format --check .` 407 files, `mypy` clean on the changed modules,
  `work_items check` OK, `check_doc_links` OK (648), `doc_lints` 0 blocks, `wiki_cites` OK,
  `wiki_freshness` OK (38 < 75).

**Gate:**
- `python -m scripts.gate --result`, run before this file was written, on `5040ce1`:
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-14T11:12:40-0700, HEAD 5040ce1`
- **That result goes stale the moment this handoff is committed**, because the result binds to
  HEAD and this commit moves it. The gate ran on the tree one docs file short of this one.
- **What it ran** (second run, 14.5 minutes): `ruff check` and `ruff format --check` (407 files)
  clean; `mypy` 423 files clean; `pytest -m "not ux" -n auto` **3365 passed, 8 skipped**;
  `pytest -m ux` **171 passed, 2 xpassed**; `work_items check` OK (169). No `FAILED`, `ERROR` or
  `RERUN` status line in the log. The 2 xpassed are the two deliberately non-strict xfails in
  `tests/ux/regression/test_20260708_busy_states_and_chip.py`, documented as allowed to xpass;
  this branch does not touch them.
- **The first run was killed** by the harness for low system memory at 52% of the UX tier
  (diagnosis O18). It was not reproduced: with a sampler logging free RAM every 5 s, the second
  run's **minimum was 2.74 GB** against the gate's 1.0 GB floor, 131 samples. **The cause of the
  first kill is not established.** The one difference I can name: in the first run my turn had
  ended (the harness reaps background jobs only "while the session was idle"), in the second it
  stayed active. One sample each, so that is a lead and not a finding.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
- **CI on the PR:** not run yet; the PR is opened only after the owner confirms the push.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 23 / 10 ceiling -- OVER"**
(this branch filed and closed 164-167, closed 55 from Watching, and filed 168 and 169 as
Watching, so Open is unchanged). The owner's drawdown direction stands: down to 0 if possible,
before alpha staging. That is well past the ~8–10 reduction-sprint threshold.

`## Open` (23 items; the header also counts open epics). Generated from the board;
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
- **163**: A with-letter generate consumes the letter edit in the context but not on the run row; resume shows the typed text.

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (44) and `## Epics` (6) in `BOARD.md`. New this session:
**168** (measure the Sonnet auditor against Haiku) and **169** (non-human prompt shapes the
witness has not seen still arm the pause), both Watching.

Declared, not filed. Carried from the previous handoff and **not re-verified this session**
unless marked:
- **New: the sibling window's gap is one sample.** 1.133 s between a pause and the batch-mate's
  hook (diagnosis O8). The 3 s default is a judgment, not a measurement of a distribution.
- **New: a trunk-time `compacted` row is no longer in `git log`.** Branch-time rows are
  (item 165). Items 84, 93, 94 and 110 cite branch-time rows, which are unchanged.
- **New: `plan_gate` reports a detached HEAD as `""`**, so its `plan-archived` receipt stays in
  the tracked shard there. Recorded in item 169.
- **New: E1 sees a `lines N-M` reference only when a path is on the same or the preceding
  line**, and E3 is word-presence in the file, weaker than "defined here" (`scripts/wiki_cites.py`
  docstring).
- **New: `ALLOWED_LINE_CITES` holds 25 line cites on 8 pages.** `education-degree-field-rendering.md`
  has 12. Converting one to a symbol forces the entry down; that is the intent.
- **New: edits made outside the Edit|Write gates this session:** `tests/test_interrogative_witness.py`
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
- **`carry_edits=True` with a letter produced keeps the typed letter edit** (existing,
  unobserved; the blast-radius dossier of `fix/regenerate-keeps-cover-letter`) (carried).
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

1. **A notification re-arms the interrogative witness; a paused call's batch-mates land without
   it** (carried from three handoffs; item 164).
   - **Recognized as a recurrence:** the previous handoff's Recurrence 3, and 9 instances in item
     143.
   - **Mechanism authored:** `scripts/enforcement/guards/interrogative_witness.py`
     (`is_non_human_prompt`, `record_prompt`, `decide`'s window), `tests/test_interrogative_witness.py`
     (`TestNonHumanTurnsDoNotArm`, `TestBatchWindow`; mutation-checked), and an end-to-end drive
     (O11).
   - **Plainly:** the notification half is a deterministic exemption on an observed prefix. The
     batch half is a **timing heuristic** and not a gate: it fails open past 3 s. The transcript
     cannot see the batch at hook time (O7), so no per-call hook can close that gap. Prompt
     shapes not yet seen still arm (item 169). Surfaced to the owner, who chose the window.
2. **A hook-written ledger row left a tracked file modified on `main`** (second instance, and the
   first one's recorded; item 165).
   - **Mechanism authored:** `scripts/enforcement/ledger_spool.py` and
     `tests/test_ledger_spool.py`, which drives real throwaway repos and fails on a dirty
     `git status`; `TestWritersRouteThroughTheHelper` fails a third writer that builds the tracked
     path by hand; `TestTheSpoolStaysUntracked` fails if `.gitignore` stops covering the spool.
   - **Plainly:** `""` as a branch name keeps the tracked shard, and `plan_gate` cannot tell a
     detached HEAD from an unreadable one.
3. **The wiki scribe/auditor pair passed defects that review then caught** (fourth pass in a row
   counting the heredoc one; item 166).
   - **Mechanism authored for the mechanical part:** `scripts/wiki_cites.py`,
     `tests/test_wiki_cites.py::TestTheRealTree` (E1-E3 in the `pytest` gate).
   - **Authored for the rest, UNENFORCED:** the auditor on Sonnet 5 with four explicit checks,
     and `commands/wiki-self-update.md` step 6 (review every added sentence). Whether a
     sentence is TRUE is not mechanically checkable. Whether Sonnet catches more than Haiku is
     **not measured** (item 168). Surfaced to the owner, who chose all three parts.
4. **A strict-xfail arm with bare-assert controls reads a broken drive as the defect** (first
   instance, last handoff; item 167).
   - **Mechanism authored:** `tests/test_xfail_controls_gate.py` (decorator shape, shared helper,
     one `ControlFailed`), probed on the real tree (O14).
   - **Plainly:** a bare `assert` inside a drive helper is not checkable without a call graph; that
     half stays prose and is labeled unenforced in `tests/_controls.py` and the memory note.
5. **A background task reported a status that was not the result** (new this session, twice; a
   member of the known class "background-task status is unreliable", memory
   `reference-background-bash-kill-ceiling`). Instance (b): the first gate run's notification
   said `killed`, which is a status about the harness, not about the tests; I read the log and
   `--result` instead, and cited neither the notification nor the first run.
   - **The instance:** `-k "Archive or Retire or Killed or Receipt"` applied to every file in one
     `pytest` invocation: `22 passed, 364 deselected`, task notification `exit 0`.
   - **No mechanism authored, and none is possible for an ad-hoc command.** The gate runs the
     whole suite; this was my own sweep. Caught only by reading the summary line. Written to
     memory (`reference-hook-receipts-spool-on-trunk`). That is a note, not a mechanism: said
     plainly, and surfaced here.
6. **A figure carried from a subagent report into a durable record without re-measuring** (new;
   the C-12 class).
   - **The instances:** "575 resolved cites" (a raw `grep` count of `path:token` strings) and
     "23 existing line cites" (the true total was 25), both written into item 166 before I ran
     the measurement. Caught by re-measuring before the commit; the real figures are 44 pages,
     727 symbol cites, 25 line cites (O15).
   - **No mechanism authored.** The ratchet's per-page counts are pinned by a test; prose figures
     are not. Surfaced here.
7. **A consumer enumeration found sites only while building** (charter C-10, working as designed).
   - **The instances:** PX-47b, `CLAUDE.md` and `tooling.md` for the model pin (found by grep
     during the enumeration), and the `RELEVANT_OVERRIDES` entry (found after, because
     `test_relevant_overrides_equal_wiki_cited_mixed_files` reads `git ls-files` and passes while a
     new file is untracked).
   - **Mechanism:** the existing one held. The dossier was committed first (`4f409d4`) and the
     late site is row 34. The untracked-file blind spot is recorded in memory.

---

## What this branch should build

**None directed by this session.** The next branch is the owner's pick from the Open list above,
under item 40's drawdown direction. Item 163 is the closest follow-on from the previous branch
and needs an instrument before a fix. Items 168 and 169 are Watching: they need a live
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
