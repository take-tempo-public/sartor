<!-- provenance: schema=1 session=4c067cbd-ff45-45e1-a303-988700830907 branch=fix/reorder-networkidle-empty-census commit=a8489dc actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-14 -->

# Agent handoff — item 30's C-7 probe branch: `networkidle` is order-dependent (`fix/reorder-networkidle-empty-census`) → owner's next drawdown pick

**Branch to create:** none chosen. The owner picks the next item from `docs/dev/work/BOARD.md`
`## Open`; do not start one unprompted.
**Base branch:** `main`

> **This session ran item 30's C-7 probe branch (owner pick, 2026-10-14), probe only: no fix.**
> - **The change:** tests and docs only. `tests/ux/regression/test_20260604_bullet_drag_reorder.py`
>   gains a widened settle instrument (request bodies via `requestfinished`, a frame timeline, a
>   per-frame `networkidle` check taken only after a failure) and three capability probes. The
>   instrument's unbounded `networkidle` wait is still the trigger, so a natural failure still
>   fails and `ci_wait` / `flake_rates` still count it.
> - **Capability shown, from first principles (P5, one run, a fresh page per arm, no app JS,
>   Playwright 1.60.0):** a main-frame fetch finishing and *then* a child-frame commit times out
>   `wait_for_load_state("networkidle")` (8.03 s bound) with nothing pending, nothing awaiting a
>   body, every child frame reached and `readyState: complete`. The opposite order returns in
>   0.505 s. That is the recorded CI shape. The mechanism was read from the installed driver's
>   `coreBundle.js` and then probed; it is a Playwright-internal bookkeeping gap.
> - **Not established:** that this happened on any CI run. The natural-capture attempt found
>   nothing (30 of 30 passed locally under 6 CPU loaders, which is about a 0.37 chance at the
>   measured 3.3% per attempt, on a laptop and not the CI runners).
> - **Inferred, not observed (dossier I-9):** production `_wait_settled` caps this wait at 5 s and
>   swallows the timeout, so there it costs 5 s and does not fail. Every recorded traceback goes
>   through the *instrument's* unbounded wait, which arrived 2026-07-31; recurrences are recorded
>   from 2026-08-03.
> - **One owner question is open and nothing here decides it:** which fix, if any, for item 30
>   (bound the instrument as production does, or replace the `networkidle` pre-drain in
>   `ui_pages/wizard_compose.py::_wait_settled`). Both are written out in item 30's `## Updates`.

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
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (see the pointer's commit on `main`): item 30's
  C-7 probe branch. **Item 30 stays `watching`** (probe only, by owner direction).
- **Next: the owner's pick.** Open items, none started: 161 (`GET /composition` parses the
  context about eleven times per request; counted from the code, not measured, so the first
  step is a measurement); item 7 memory-consolidation apply (Deferred); a `fix/*` branch for
  item 30 if the owner chooses a fix; launcher items 145–147; the owner-decision items (50,
  128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/reorder-networkidle-empty-census`:

| Commit | What |
|---|---|
| `c59e7a1` | **Instrument and dossier first** (C-7). The widened census and settle instrument; `docs/dev/diagnosis/reorder-networkidle-empty-census.md`; this session's consumed-ledger file. Ordinary local run: 12 reaches, `awaiting_body` empty at rest. |
| `d3dbd35` | **Capability probes P3, P4, P5** in the same test file, pre-registered in the dossier before they ran (two were amended, openly, before any run). Mutation check on the instrument. |
| `a8489dc` | Item 30's `## Updates` entry and dossier O-20 (the empty natural-capture attempt). |
| (this commit) | This handoff and its ledger row. Docs only. |

**Verified, with the evidence:**
- **P5 (the finding):** `fetch+commit` timed out at 8.032 s with main `NOT_REACHED` and the child
  `reached`; `commit` 0.501 s, `commit+fetch` 0.505 s, `fetch+commit+fetch` 0.505 s (dossier
  O-17). One run each, on a fresh page.
- **P3, isolated:** a held body returns `networkidle` at once on its own (0.033 s), withholds it
  once a frame commit forces the recalculation (8.033 s), and recovers 0.519 s after release.
  The original census (`still_pending`) was empty throughout; the widened one listed it (O-18).
- **P4:** the app's own single preview navigation, after the page was idle, also timed out
  (8.041 s) in the same state (O-14).
- **Mutation check:** removing the `requestfinished` listener fails P3's control
  (`probe void: not at rest`); the file was restored and its sha256 prefix verified equal (O-19).
- **Natural capture:** 30 of 30 passed under 6 loaders, 0 exception records, largest
  `networkidle_s` 0.679 s (O-20). Not evidence of a fix.

**Gate:**
- `python -m scripts.gate --result`, run on `a8489dc` (the tip before this handoff commit):
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-14T21:50:14-0700, HEAD a8489dc`
- **That result is stale for the tip**, because the result binds to HEAD. One docs-only commit
  (this handoff and its ledger row) sits on top of it and changes no code or tests.
  `work_items check` and the doc checks are re-run by hand on the tip; the full gate was not.
- **What it ran:** `ruff check` and `ruff format --check` clean; `mypy` clean;
  `pytest -m "not ux" -n auto` **3396 passed, 8 skipped** (7 m 14 s; unchanged, since this
  branch adds only UX-tier tests); `pytest -m ux` **179 passed, 2 xpassed** (16 m 48 s; the
  173 of last session plus the six probe tests); `work_items check` OK (170). 0 `RERUN`, 0
  `FAILED`/`ERROR` status lines. The 2 xpassed are the two deliberately non-strict xfails in
  `tests/ux/regression/test_20260708_busy_states_and_chip.py`, which this branch does not touch.
- **UX-tier time, stated with its limits:** 16 m 48 s here against 11 m 02 s in the previous
  session's gate. The six probe tests, timed alone with `--durations=0`, cost about 47 s of call
  time (P4 22.3 s, P3 9.8 s, P5 four arms 13.0 s) and about 5 s of extra setup, 68.55 s wall for
  the six including a one-time 14.8 s fixture setup. **That does not account for the +5 m 46 s;
  the remainder is not attributed** and was not measured (no per-test timings were taken for the
  other 173 on either run).
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
  Item 30's flake can produce exit 3 on this very PR: if it does, read `awaiting_body`,
  `frame_timeline` and `frames` from the failing attempt's raw job log (`gh run view <run> --job
  <job> --log`) before anything else, and record them in item 30 and the dossier.

**Wiki:** no `/wiki-self-update` pass was needed. `scripts/wiki_relevance.py::is_wiki_relevant()`
returned `False` for all three paths in this branch's diff (the test file, the dossier, the
ledger file), so there is no page edit to make and `.last_ingest_sha` is unchanged.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 22 / 10 ceiling -- OVER"**
(20 items below plus 2 open epics; this branch closed none). The owner's drawdown direction
stands: down to 0 if possible, before alpha staging. That is well past the ~8–10
reduction-sprint threshold. Owner-decision items are marked *(owner)*.

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
- **161**: Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all.

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44, including **30**, which gained its largest entry yet this session) and
`## Epics` (6) in `BOARD.md`.

Declared, not filed. New this session, observed unless marked:
- **The three probe tests stay in the UX tier until someone decides.** P3, P4 and P5 are one-shot
  capability experiments in the P1/P2 precedent; P4 and P5's hanging arms each spend an 8 s bound.
  Their added cost to the full UX tier is in the gate's own timing above, not estimated here. The
  disposition (keep P5 as a guard against a Playwright upgrade, or remove) is the owner's.
- **P4 reaches into two app globals by name** (`_composeApplicationId`, `lastContextPath`, in
  `_NAVIGATE_PREVIEW_FRAME_JS`). A rename in `static/app.js` would fail its controls loudly
  (`probe void`), not silently.
- **The instrument's own wait is still unbounded**, deliberately, so `ci_wait` keeps counting it.
  While that holds, each recurrence costs a re-push and about 7 minutes of CI, and the next
  `ci_wait` exit-3 log is the first one that can say which mechanism fired: read
  `awaiting_body`, `frame_timeline` and `frames` from it.
- **`python -I` drops the user site-packages** on this machine (Playwright lives there), so an
  isolated run of a scratch script that imports it fails with `No module named 'playwright'`.
  Not a defect; noted because the untrusted-input guidance says to use `-I`.
- **Two processes I did not start were left alone**: the `isidium` MCP server (two
  `python.exe -m isidium.store.client.cli mcp`, started 8:48 PM). They are not this session's.
- **`ruff` format on the test file ran twice** and changed layout only; behaviour was re-verified
  by the probe runs that followed each change.

Carried from earlier handoffs, **not re-verified this session**:
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- whether a cover letter should be regenerable from the shipped screens (item 170's open
  question: cases 2 and 3 have no shipped client trigger);
- the interrogative witness can pause the first `Edit`/`Write` after a prompt or a subagent
  hand-back (item 169's class); this session it paused the first `Write` once, which is the
  designed one-shot, and a re-run of the same call proceeded;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works); the IDE's Pyright reports
  stale "not accessed / not defined" hints between consecutive edits to one file, which `ruff`
  and `mypy` do not;
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
  re-derived 2026-10-14 by the previous session it was 15;
- two UX tests hard-code the `#cbConfirm*` ids instead of the `ConfirmModal` selectors
  (`test_20260612_corpus_affordance_polish.py`, `test_20260707_ux_w4_aesthetic.py`);
- the doc-writing skill's evaluation plan has not been run (the owner's call when);
- 32 one-way wiki backlinks (WARN), as counted by an earlier `/wiki-lint`;
- `python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree two sessions
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
- the full local gate takes more than 25 minutes on this machine; run it in the background with a
  35–40 minute budget.

---

## Recurrences observed this session → guardrail authored

1. **A probe built on a plausible reading of the mechanism, nearly run before the mechanism was
   read** (C-7 5f's class: the narrowed instrument that confirms or hides its rival).
   - **The instance:** the first P3 was "fire a held fetch, then wait for `networkidle`". Reading
     the installed driver first showed a late request alone does not remove an already-fired
     `networkidle`, so that draft would have returned at once and been misread as "a held body
     does not block". It was amended in the dossier before it ran. The *second* failure was real:
     three arms in one page, arm A left the page stuck, and arms B and C were void. Caught from
     the result (arm A timed out when the code read predicted 1 s), recorded as F-3.
   - **Mechanism authored:** the probes fail closed on their own controls (`probe void`
     assertions: idle before arming, the held request listed, each frame commit seen before the
     wait), and P5 isolates arms by construction (`parametrize`, a fresh page each). The mutation
     check shows the `requestfinished` control is load-bearing. **Unenforced:** the "one arm per
     page" rule itself is in a memory note (`reference-playwright-networkidle-order-dependence`),
     not a gate.
2. **A background task's "exit code 0"** (the known class, `reference-background-task-exit-code-unreliable`,
   now n=5). The tool reported exit 0 for a wrapper whose last command was an `echo`. Recognized
   from the note; the result was read from the script's own `LOOP_DONE pytest_exit=` marker and
   the pytest summary line, not from the notification.
   - **Mechanism authored: none, plainly.** The scratch script writes its own marker and exits
     with pytest's code, but it lives in the scratchpad and the invoking one-liner added a
     trailing `echo`. A general re-raise wrapper is possible and was not built (same stance as
     the previous handoff).
3. **`block-doubled-backslash` fired on this session's own command** (a heredoc'd Python script
   containing a doubled backslash). The guard did its job: the way through it offers (write the
   script with the Write tool, run it by path) was taken. A recurrence of the class item 142
   built the guard for, caught by that guard; **no new mechanism needed**.
4. **Item 30 itself** recurred a third time since the 2026-10-02 re-measurement (PR #170, in the
   previous session); this branch is the C-7 probe the earlier entries asked for. **Mechanism
   authored: the widened instrument**, which records and does not gate. The flake still trips
   `ci_wait` at about 7 minutes a time until a fix lands; surfaced here and in item 30 (C-11),
   not papered over.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next drawdown item; this handoff does not pick one.
Scope for whatever is chosen is whatever the owner names, as filed in `docs/dev/work/items/`.
Do not expand beyond it.

If the owner picks **item 30's fix**: it is a `fix/*` branch with its own diagnosis dossier whose
`## Observed` cites `docs/dev/diagnosis/reorder-networkidle-empty-census.md`. A/B it against the
real test in an in-process loop (memory `reference-pytest-in-process-loop-and-mutation-plugins`),
and do not close item 30 without a falsifiable `verified_by` (C-11).

If the owner asks what is cheapest to unblock: item 161 begins with a *measurement* (the
eleven-parse count is from the code, not measured), items 145–147 are the launch requirements,
and the *(owner)* items need a decision before any branch.

---

## First move

Run the pointer check, then `--event consumed` on this handoff, then confirm with the owner
that the PR for `fix/reorder-networkidle-empty-census` has merged (this handoff's pointer names
that branch's commit on `main`). Then ask which item to take. Create that
branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to the user before
touching any code. **Do not code first.**

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
