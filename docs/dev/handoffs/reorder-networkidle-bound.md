<!-- provenance: schema=1 session=f202e00d-9a81-4ebf-8944-ff521fd01ca5 branch=fix/reorder-networkidle-bound commit=d6f7fee actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-15 -->

# Agent handoff — item 30, Phase A: the reorder test's `networkidle` wait is bounded, stalls are visible (`fix/reorder-networkidle-bound`) → owner's next drawdown pick

**Branch to create:** none chosen. The owner picks the next item from `docs/dev/work/BOARD.md`
`## Open`; do not start one unprompted.
**Base branch:** `main`

> **This session took item 30 (owner pick, 2026-10-15) and stopped at Phase A by owner decision.
> Item 30 stays `watching`. It is not closed.**
> - **The change:** `ui_pages/wizard_compose.py` gains `predrain_networkidle(page)`, the one
>   definition of the bounded (5 s), swallowed `networkidle` pre-drain. `_wait_settled` and the
>   keyboard-reorder test's timed override both call it. Every traceback recorded on item 30 since
>   2026-10-07 was raised by the override's *unbounded* `wait_for_load_state("networkidle")`.
>   Dossier, with both scratchpad plugins verbatim: `docs/dev/diagnosis/reorder-networkidle-bound.md`.
> - **Observed (C-7):** with the P5 fetch-then-commit order injected before reach 9 of the real
>   test, the unmodified instrument hung **30.047 s** with `still_pending_requests: []` and the
>   main frame `NOT_REACHED` (the recorded CI shape); the bounded one passed, that reach timed out
>   at **5.012 s**. One run per arm, arms in separate processes. **That is capability and
>   mitigation. It is not a finding that this order happened on any CI run.**
> - **Declared, not hidden (C-11):** a stall no longer fails an attempt, so `ci_wait` (exit 3) and
>   `flake_rates` stop seeing it. The new `[ux] networkidle pre-drain: N stall(s) in M reach(es)`
>   line is the only place it shows, and **neither tool reads it**.
> - **Measured:** one local pass, 25 UX test files, probes and the guard deselected: **0 stalls in
>   106 reaches**, 8.4 s waiting, 66 passed. The gate's full UX tier: `2 stall(s) in 115
>   reach(es)`, both the deliberate ones (the P1 probe and the new guard), so **0 unintended in
>   115**. A datum, not evidence the stall does not occur.
> - **Not obtained:** the 4-pass loop was reaped by the harness's memory-pressure reaper before it
>   printed a tally, and the CPU-loaded arm never ran. The reaper killed only the wrapper; the
>   pytest, driver and browser processes were left running and were terminated by hand.
> - **Decided by the owner:** stop at Phase A; the pre-drain is **not** replaced (Phase C). Reopen
>   only on a stall rate from real runs.
> - **Open, and nothing here decides it:** whether item 30 can close. It needs a falsifiable
>   `verified_by` and `ci_wait` exit 0 with 0 `RERUN` on the reorder test across enough CI runs to
>   mean something at about 3.3% per attempt. None of that exists yet.

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

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157) · ~~`fix/console-run-lock-hardening`~~ ✓ (#158) ·
  ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159) · ~~`fix/python-direct-hooks-plan-gate`~~ ✓
  (#160) · ~~`fix/heredoc-escape-guard`~~ ✓ (#161) · ~~`fix/bash-tool-transport`~~ ✓ (#162) ·
  ~~`fix/test-reliability`~~ ✓ (#163) · ~~`test/assertion-strength`~~ ✓ (#164) ·
  ~~`fix/frozen-composition-staleness`~~ ✓ (#165) · ~~`fix/regenerate-persistence`~~ ✓ (#166) ·
  ~~`fix/regenerate-keeps-cover-letter`~~ ✓ (#167) · ~~`fix/recurrence-guardrails`~~ ✓ (#168) ·
  ~~`fix/run-row-letter-edit-shadow`~~ ✓ (#169): item 163 closed.
- ~~`feat/confirm-before-overwriting-typed-edits`~~ ✓ (#170): item 170 closed.
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (#171): item 30's C-7 probe branch.
- ~~`fix/compose-single-context-parse`~~ ✓ (#172): item 161 closed.
- **`fix/reorder-networkidle-bound`** ← this branch (see the pointer's commit on `main`): item 30,
  Phase A. **Item 30 stays `watching`.**
- **Next: the owner's pick.** Open items, none started: item 7 memory-consolidation apply
  (Deferred); launcher items 145–147; the owner-decision items (50, 128, 129, 133, 135, 138).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/reorder-networkidle-bound`:

| Commit | What |
|---|---|
| `f18f454` | **Dossier first** (C-7). `docs/dev/diagnosis/reorder-networkidle-bound.md` with `## Observed`, the derived consumer list (28 files), the pre-registered falsification, and this session's consumed-ledger file. No production edit. |
| `7a67c54` | **The change.** `predrain_networkidle` and the `PREDRAIN` tally in `ui_pages/wizard_compose.py`; the override in `tests/ux/regression/test_20260604_bullet_drag_reorder.py` calls it and captures the wide dump on a stall; `tests/ux/conftest.py` prints the `[ux] networkidle pre-drain:` line; the fail-closed guard `tests/ux/regression/test_20261015_compose_predrain_bounded.py`. |
| `b9613bc` | Phase B record: one pass, 0 stalls in 106 reaches; the loop reaped, no data. |
| `d6f7fee` | Item 30 `## Updates` (Phase B result, owner stops at Phase A) and the dossier appendix: the A/B plugin and the mutation plugin, verbatim. |
| (this commit) | This handoff, and dossier O-19 / item 30's whole-tier datum. Docs only. |

**Verified, with the evidence:**
- **Before:** the override's `wait_for_load_state("networkidle")` had no timeout
  (`test_20260604_bullet_drag_reorder.py:303` at `18c5ce1`; the earlier `:163` cite is stale).
  Production's was capped at `_NETWORKIDLE_PREDRAIN_MS` (`ui_pages/wizard_compose.py:25,93-94`).
  Three CI failures went through the override (runs `37669157358`, `38310545397`, `38676437085`),
  **read from item 30's entries, not re-read from the raw job logs this session**.
- **A/B, real test, injected before reach 9** (dossier O-10..O-13): control (no injection)
  `1 passed`; HEAD arm `TimeoutError` at 30.047 s; FIXED arm `1 passed`, reach 9
  `networkidle_timed_out: True` at 5.012 s. **Not pre-registered:** reach 10 also stalled (5.02 s)
  and reach 11 recovered (0.486 s). Not explained; consistent with the prior dossier's O-16 and not
  a test of it.
- **Guard** (O-14): passes on the branch (stall recorded, 5.0 s); under a scratchpad mutation of
  the bound to 20 s it fails (`_wait_settled took 20.1s`). Red under the mutation it exists for.
- **Corrections to this session's own approved plan** (dossier F-1, F-2): the consumer count is 28
  tracked files, not 29; and `ui_pages/base.py` is on the *considered-and-not-gated* list
  (`scripts/enforcement/blast_radius.py:207`), not a gated surface. Both were found by reading
  before the dossier was committed.
- **Wiki:** no path in this branch's diff is wiki-relevant (`scripts.wiki_relevance.
  is_wiki_relevant` over `git diff --name-only 18c5ce1..HEAD`: all `not`), so **no page edit was
  needed** and no `/wiki-self-update` was run.

**Gate:**
- `python -m scripts.gate --result`, run on `d6f7fee` (the tip before this handoff commit):
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-15T13:44:00-0700, HEAD d6f7fee`
- **That result is stale for the tip**, because the result binds to HEAD. One docs-only commit
  (this handoff) sits on top of it and changes no code or tests. `work_items check` and the
  handoff validation are re-run by hand on the tip; the full gate was not.
- **What it ran:** hooksPath and memory preflights, `ruff check`, `ruff format --check` and `mypy`
  clean; `pytest -m "not ux" -n auto` **3401 passed, 8 skipped** (5 m 46 s, unchanged from last
  session); `pytest -m ux` **180 passed, 2 xpassed** (9 m 10 s; one more than last session: the
  guard); `work_items check` OK (170 files). 0 `RERUN`, 0 `FAILED` lines. The 2 xpassed are the two
  deliberately non-strict xfails in `tests/ux/regression/test_20260708_busy_states_and_chip.py`,
  not touched here.
- **Wall-clock, measured this time** (`GATE_START 13:28:42`, `GATE_DONE exit=0 13:44:00`, the
  wrapper's own markers): **15 min 18 s** for the whole gate. This replaces the earlier handoffs'
  untimed ">25 minutes" figure for this machine at about 3 GB free.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look. This
  branch's own PR is the first CI run that prints the `[ux] networkidle pre-drain:` line: read it
  from the raw job log (`gh run view <run> --job <job> --log`) and record it in item 30, whatever
  it says.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 21 / 10 ceiling -- OVER"**
(19 items below plus 2 open epics; this branch closed no item: item 30 is `## Watching`). The
owner's drawdown direction stands: down to 0 if possible, before alpha staging. That is well past
the ~8–10 reduction-sprint threshold. Owner-decision items are marked *(owner)*.

`## Open`:
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

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44, including **30**) and `## Epics` (6) in `BOARD.md`.

Declared, not filed. New this session, observed unless marked:
- **`ci_wait` and `flake_rates` are now blind to a pre-drain stall, by the owner's choice.** The
  `[ux] networkidle pre-drain:` line carries it and neither tool parses it. Teaching either to read
  it is the owner's call; until then a rising stall count is visible only to a human reading a job
  log. Unenforced, declared.
- **The summary line counts the deliberate stalls** (`test_diagnostic_p1_*`, the guard). A reader
  must subtract them (dossier O-16); on the gate's full tier that left 0 of 2.
- **The harness's memory-pressure reaper kills a background task's wrapper but not its children**
  (this session: the pytest process, Playwright driver and three browser processes survived,
  about 550 MB). Found by listing processes, not from the notification. Memory
  `reference-shared-machine-oom-kills-bg-runs` is updated. Not a repo defect; no repo mechanism is
  possible for it.
- **The stalls a loop would measure were never obtained locally.** One pass is 106 reaches in
  4 m 10 s and about 550 MB resident. A real rate needs CI job logs or a re-run when memory is free.
- **The IDE's Pyright again reported stale "not defined / not accessed" hints** between consecutive
  edits (`contextlib`, `predrain_networkidle`, `_report_predrain_stalls`); `ruff` and `mypy` were
  clean each time.
- **The interrogative witness paused the first `Write`/`Edit` after each real prompt turn** (the
  plan file; the dossier append at close-out; this handoff's draft) and the re-run proceeded, as
  designed.
- **`maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`**,
  which `scripts/verify_doc_template.py` does not resolve. Not re-run this session (this handoff's
  validation used `docs/dev/AGENT_HANDOFF_TEMPLATE.md`); carried from the previous handoff.

Carried from earlier handoffs, **not re-verified this session**:
- the three probe tests (P3, P4, P5) stay in the UX tier until the owner decides: keep P5 as a
  guard against a Playwright upgrade, or remove (item 30);
- **changed by this branch:** the instrument's own `networkidle` wait is **no longer** unbounded,
  and `ci_wait` no longer counts it (above). The earlier handoff's "deliberately unbounded" line is
  superseded;
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- whether a cover letter should be regenerable from the shipped screens (item 170's open
  question: cases 2 and 3 have no shipped client trigger);
- `python -I` drops the user site-packages on this machine (Playwright lives there), so an
  isolated run of a scratch script that imports it fails with `No module named 'playwright'`;
- the `isidium` MCP server (two `python.exe -m isidium.store.client.cli mcp`) is not this
  session's to stop;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works);
- the sibling window's gap is one sample (1.133 s; diagnosis O8), the 3 s default is a judgment;
- a trunk-time `compacted` row is no longer in `git log`; branch-time rows are (item 165);
- `plan_gate` reports a detached HEAD as `""`, so its `plan-archived` receipt stays in the
  tracked shard there (item 169);
- E1 sees a `lines N-M` reference only when a path is on the same or the preceding line, and E3
  is word-presence in the file (`scripts/wiki_cites.py` docstring);
- `ALLOWED_LINE_CITES` holds 25 line cites on 8 pages; converting one to a symbol forces the
  entry down;
- bash-run scripts edit files without the Edit|Write gates seeing them;
- a gap-fill retire, or a drag back to the same position, marks an approval stale without
  changing the résumé; approvals frozen before `fix/frozen-composition-staleness` carry no digest;
- the post-generate announcement still says "Resume and cover letter generated" when no cover
  letter was produced (`static/app.js`, `runGeneration`'s `_announce`);
- `lastCoverLetterPath` is assigned in seven places and read by none (`static/app.js`);
- a stale comment at `db/build_context.py:92`: fold it into any branch that touches that file;
- `scripts/enforcement/blast_radius.py` says `ui_pages/selectors.py` has "14 non-test importers";
  re-derived 2026-10-14 by an earlier session it was 15;
- two UX tests hard-code the `#cbConfirm*` ids instead of the `ConfirmModal` selectors
  (`test_20260612_corpus_affordance_polish.py`, `test_20260707_ux_w4_aesthetic.py`);
- the doc-writing skill's evaluation plan has not been run (the owner's call when);
- 32 one-way wiki backlinks (WARN), as counted by an earlier `/wiki-lint`;
- `python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree four sessions
  ago; not re-checked since;
- `sartorEval.run()` returns no handle on its success path (`dashboard.html`);
- `docs/dev/diagnostics.md` cites code by line number, which rots on every edit;
- the derived-set test's `git ls-files` costs 1.8–5.2 s on this machine under 0.5–0.8 GB free;
- transitive wiki relevance is not modelled (`PERFORMANCE_HISTORY.md` → `scripts/perf_baseline.py`);
- `python3` resolution on hypha and the homelab is unchecked; without `python3` on PATH no hook
  starts and the gates fail open (`docs/governance/enforcement.md`);
- `tests/test_plan_approval_scoping.py` takes about 6 minutes locally: split it by `-k` class;
- pre-existing count drift, each deferred in `docs/dev/blast-radius/bash-tool-transport.md`:
  `docs/governance/enforcement.md:29-31` says "8 exist" (14 rules now); `TestBashDispatcher`'s
  docstring names four guards (there are seven); `blast_radius.py`'s `result.py` entry says "10
  non-test importers";
- item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry;
- the threaded UX `live_server` may expose route reads on Windows (inferred, not observed;
  `docs/dev/diagnosis/test-reliability.md` §Inferred);
- `tests/test_hardening.py::TestWriteContextAtomic::test_reader_never_observes_a_partial_file`
  failed one CI attempt (run 30940947527), not investigated;
- the other routes in `blueprints/applications.py` were not audited for repeated context reads
  (item 161's scope was the GET): about twenty more `json.loads(cp.read_text(...))` sites, each
  presumably one read, unverified;
- the wiki auditor found a fact-level error the cite check cannot see (item 161's close-out).
  Brief a scribe's page edit and its audit to the **same** region, and widen the audit to the whole
  bullet or paragraph (`docs/wiki/log.md`, the 2026-10-15 entry).

---

## Recurrences observed this session → guardrail authored

1. **A diagnostic aid re-introducing the defect it was added to diagnose** (item 30's own
   history: the 2026-07-31 branch bounded production's `networkidle`; the same branch's
   instrument then waited on it unbounded, and that unbounded wait raised every traceback
   recorded since 2026-10-07). Recognized as a member of a known class (prior dossier I-9, the
   2026-10-07 item entry).
   - **Mechanism authored:** `predrain_networkidle` is now the one definition, called by both the
     page object and the override, so the override cannot carry its own unbounded wait; and
     `tests/ux/regression/test_20261015_compose_predrain_bounded.py` fails closed if production's
     pre-drain becomes unbounded again (red under a 20 s mutation of the bound). It runs in
     `pytest -m ux`, so it is inside `python -m scripts.gate` and CI.
     **Unenforced limit:** the guard covers production's `_wait_settled`. A *future* instrument
     that adds its own raw `wait_for_load_state("networkidle")` is not caught by anything.
2. **A figure or registry claim carried into a plan without being re-derived** ("29 test files";
   "`ui_pages/base.py` is a gated surface"). The class is the one C-10 names ("any
   hand-maintained consumer list is stale until re-derived"). Recognized because both were
   contradicted by the grep and the registry read before the dossier was committed.
   - **No new mechanism authored**, stated plainly: the gate enforces a consumer list for *gated*
     surfaces only, and a claim about a surface's gating status is a sentence in a plan; nothing
     can fail closed on an agent's recall. Surfaced to the owner in chat when found, and recorded
     as dossier F-1 and F-2.
3. **A background task's "exit code 0" notification** (the known class,
   `reference-background-task-exit-code-unreliable`). Twice this session (Phase B pass 1, the
   gate). The result was read from the script's own `PHASEB_DONE` / `GATE_DONE` marker and from
   `python -m scripts.gate --result`. No new mechanism; the scratch wrapper writes a marker and
   ends with `exit $ec`.
4. **A killed background run that was not actually dead** (new class this session; see the
   reaper entry above). **No mechanism possible from this repo:** the reaper is the harness's, the
   orphaning is its behaviour, and the only defence is the habit of listing processes after any
   `killed` notification, which is **prose in a memory file and unenforced**. Surfaced to the
   owner in chat.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next drawdown item; this handoff does not pick one.
Scope for whatever is chosen is whatever the owner names, as filed in `docs/dev/work/items/`.
Do not expand beyond it.

If the owner returns to **item 30**: the open work is *evidence*, not a fix. Read the
`[ux] networkidle pre-drain:` line from real CI UX job logs (this branch's own PR is the first),
and record the stall count and node ids in item 30 whatever they are. Phase C (replace the
pre-drain) needs a stall rate that shows a cost, and an A/B against the real test and the three
Compose settle files; the marker cannot see an in-flight POST not yet issued, which is why the
pre-drain exists (`reference-ux-compose-ready-wait`). Do not close item 30 without a falsifiable
`verified_by` (C-11).

If the owner asks what is cheapest to unblock: the launcher items 145–147 are the launch
requirements, and the *(owner)* items need a decision before any branch. The lane doc's template
path (above) is a one-line fix that no one has been asked to take.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner that the PR for
`fix/reorder-networkidle-bound` has merged (this handoff's pointer names that branch's commit on
`main`). Then ask which item to take. Create that branch off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code
first.**

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
