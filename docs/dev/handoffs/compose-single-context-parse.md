<!-- provenance: schema=1 session=ba12a563-980f-4723-bb20-263fadc78f95 branch=fix/compose-single-context-parse commit=2ca703e actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-15 -->

# Agent handoff — item 161: `GET /composition` reads its context file once (`fix/compose-single-context-parse`) → owner's next drawdown pick

**Branch to create:** none chosen. The owner picks the next item from `docs/dev/work/BOARD.md`
`## Open`; do not start one unprompted.
**Base branch:** `main`

> **This session closed item 161 (owner pick, 2026-10-15): measured first, then fixed.**
> - **The change:** `blueprints/applications.py` gains `_load_compose_context`, which reads and
>   parses the context file once per request; the eleven `_read_*` helpers (names and return
>   values unchanged) now take the loaded dict. Guard test
>   `tests/test_composition_single_context_read.py`. Dossier, with the instrument's full source:
>   `docs/dev/diagnosis/compose-single-context-parse.md`.
> - **Observed before the fix (C-7):** `reads_per_get = 11` at the p50, p90 and max local context
>   sizes (67 / 131 / 205 KB). The 11-helper block cost 12.5 / 19.9 / 23.2 ms median, which is
>   **1.4–2.3×** eleven bare read+parse units: parsing is part of the block, not all of it.
> - **Observed after, same instrument file:** reads **1**; block 2.0 / 1.7 / 1.9 ms median; whole
>   GET on an empty-corpus fixture 21.5 / 29.9 / 29.0 → 6.3 / 7.8 / 7.2 ms. The pre-registered
>   predictions (reads == 1; block drop ≥ 10 × one read+parse) were met at all three sizes.
>   **One run each, not interleaved**, on one laptop.
> - **A deliberate behaviour change:** a context that is valid JSON but not an object (`null`, a
>   list, a string) is now treated as absent (200, default Compose state). It was an
>   `AttributeError` 500 on `main` (dossier O-7).
> - **Not established:** that the response is now a consistent snapshot under a concurrent POST
>   (dossier I-1, inferred only); which part of the block's non-parsing cost was
>   `_within`/`exists()` repeated eleven times (I-2, consistent with the after-run, not isolated).
> - **Open, and nothing here decides it:** the owner asked (2026-10-15) whether item 30's repair
>   is next. No decision is recorded. The question from the previous handoff stands: which fix, if
>   any — bound the instrument's wait as production does, or replace the `networkidle` pre-drain in
>   `ui_pages/wizard_compose.py::_wait_settled`. Bounding it also removes the failure from the
>   counters `ci_wait` and `flake_rates` use; that trade is the owner's to make.

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
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (#171): item 30's C-7 probe branch. **Item 30 stays
  `watching`** (probe only, by owner direction).
- ~~`fix/compose-single-context-parse`~~ ✓ (see the pointer's commit on `main`): item 161 closed.
- **Next: the owner's pick.** Open items, none started: a `fix/*` branch for item 30 if the owner
  chooses a fix; item 7 memory-consolidation apply (Deferred); launcher items 145–147; the
  owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/compose-single-context-parse`:

| Commit | What |
|---|---|
| `74b2f76` | **Instrument and dossier first** (C-7). `docs/dev/diagnosis/compose-single-context-parse.md` with `## Observed` (count, timings, environment), the consumers table, the pre-registered guard test and predicted after-run, and the instrument's full source; this session's consumed-ledger file. No production edit. |
| `ad31f7d` | **The fix.** `_load_compose_context` plus the eleven helpers on the loaded dict; the guard test (red on `main`, recorded in the dossier as O-7, green here); item 161 closed with `verified_by`; `BOARD.md` regenerated (Open 22 → 21). |
| `2ca703e` | Scoped `/wiki-self-update`: `route-surface.md`'s `get_application_composition` bullet, and the `log.md` entry. |
| (this commit) | This handoff. Docs only. |

**Verified, with the evidence:**
- **Count, before:** `reads_per_get = 11` at all three sizes (dossier O-2); a second, independent
  method (a `pytest` monkeypatch on `Path.read_text`) gave 11 on `main` (O-7).
- **Guard test on `main`:** 4 failed, 1 passed — `11 times`, then three `assert 500 == 200`
  (`AttributeError` on `null`, a list, a string); the malformed-JSON case passes and is the
  control (O-7).
- **After:** reads 1; block and whole-GET figures in the summary above (O-8). The suites over the
  change: 272 passed across the guard plus the 11 other files that call
  `/composition?context_path=`, and the two UX tests that monkeypatch
  `_read_composition_overrides` by name passed (2 passed) (O-9).
- **Wiki:** the scribe's one sentence, then the auditor (Sonnet 5): 1 UNSUPPORTED of 6 claims,
  **pre-existing on `main`** (titles said to be fit-ranked via `score_corpus_bullet`; they use an
  inline token-overlap count), corrected on the owner's decision. `wiki_cites --strict-removed`
  0 violations; `wiki_freshness` OK (38 files). `.last_ingest_sha` unchanged (scoped pass).

**Gate:**
- `python -m scripts.gate --result`, run on `2ca703e` (the tip before this handoff commit):
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-15T06:25:01-0700, HEAD 2ca703e`
- **That result is stale for the tip**, because the result binds to HEAD. One docs-only commit
  (this handoff) sits on top of it and changes no code or tests. `work_items check` and the
  handoff validation are re-run by hand on the tip; the full gate was not.
- **What it ran:** `ruff` and `mypy` clean; `pytest -m "not ux" -n auto` **3401 passed, 8
  skipped** (5 m 48 s; the 3396 of last session plus the five guard tests); `pytest -m ux` **179
  passed, 2 xpassed** (8 m 53 s; unchanged, this branch adds no UX test); `work_items check` OK
  (170). 0 `RERUN`, 0 `FAILED`/`ERROR` lines. The 2 xpassed are the two deliberately non-strict
  xfails in `tests/ux/regression/test_20260708_busy_states_and_chip.py`, which this branch does
  not touch.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.
  Item 30's flake can produce exit 3 on this very PR: if it does, read `awaiting_body`,
  `frame_timeline` and `frames` from the failing attempt's raw job log (`gh run view <run> --job
  <job> --log`) before anything else, and record them in item 30 and its dossier. That log would
  be the first natural capture.

**Wiki:** the scoped pass ran and is committed in `2ca703e` (above).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 21 / 10 ceiling -- OVER"**
(19 items below plus 2 open epics; this branch closed item 161). The owner's drawdown direction
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

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44, including **30**) and `## Epics` (6) in `BOARD.md`.

Declared, not filed. New this session, observed unless marked:
- **`docs/dev/maintainer-lane.md` step 2 gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`;
  `scripts/verify_doc_template.py` resolves it from the repo root, so that exact command exits 2
  (`template not found`).** The working argument is `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, which
  this handoff's First move uses. Not fixed here (out of scope). First instance; the fix is one
  line in the lane doc, or a fallback in the script.
- **The block's non-parsing cost (about half of it at p50) is unattributed.** Dossier I-2 is a
  guess, consistent with the after-run and not isolated. Anyone citing "the parses were the
  cost" is overstating; the absolute block figures are the ones to carry.
- **The measurement fixture's database is empty**, so the whole-GET figures carry almost no ORM or
  scoring work and the block's share of a real GET is overstated (dossier O-5).
- **The other routes in `blueprints/applications.py` were not audited for repeated reads.** About
  twenty more `json.loads(cp.read_text(...))` sites exist (e.g. `:1700`, `:2013` before this
  change); each presumably reads once. Not verified; item 161's scope was the GET.
- **The wiki auditor found a fact-level error the cite check cannot see**, already on `main`. It
  was found because the audit covered the whole bullet, not only the changed clause. Brief a
  scribe's page edit and its audit to the **same** region, and widen the audit to the whole
  bullet or paragraph (`docs/wiki/log.md`, the 2026-10-15 entry).
- **The first Bash call of the session returned "auto mode classifier gave no verdict"** and was
  re-issued as instructed. One occurrence; no pattern drawn.
- **The interrogative witness paused the first `Write`/`Edit` after each real prompt turn**
  (the plan file; the wiki sentence; this handoff's body) and the re-run proceeded, as designed.

Carried from earlier handoffs, **not re-verified this session**:
- the three probe tests (P3, P4, P5) stay in the UX tier until the owner decides: keep P5 as a
  guard against a Playwright upgrade, or remove (item 30);
- the instrument's own `networkidle` wait is still unbounded, deliberately, so `ci_wait` keeps
  counting it: each recurrence costs a re-push and about 7 minutes of CI;
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- whether a cover letter should be regenerable from the shipped screens (item 170's open
  question: cases 2 and 3 have no shipped client trigger);
- `python -I` drops the user site-packages on this machine (Playwright lives there), so an
  isolated run of a scratch script that imports it fails with `No module named 'playwright'`;
- the `isidium` MCP server (two `python.exe -m isidium.store.client.cli mcp`) is not this
  session's to stop;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works); the IDE's Pyright reports
  stale "not accessed / not defined" hints between consecutive edits to one file, which `ruff`
  and `mypy` do not (this session also saw it report `str`-to-`dict` errors that had already
  been fixed);
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
- `python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree three sessions
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
- the full local gate: this run's two pytest steps took 5 m 48 s and 8 m 53 s; the total
  wall-clock was not timed, so the earlier "more than 25 minutes" figure is neither confirmed nor
  refuted here. Run it in the background with a 35–40 minute budget.

---

## Recurrences observed this session → guardrail authored

1. **A deferred consolidation that grows by one each time** (item 161's own history: the tenth
   helper, then `fix/frozen-composition-staleness` added the eleventh and deferred the fix,
   citing it as "filed separately"). Recognized as a class: a count that only moves one way
   while a note says "later".
   - **Mechanism authored:** `tests/test_composition_single_context_read.py` fails closed when
     the GET reads its context file more than once; it ran red on `main` (`11 times`) and green
     here. It runs in `pytest -m "not ux"`, so it is inside `python -m scripts.gate` and CI.
     **Unenforced limit:** it counts reads of one file through `Path.read_text`; a helper that
     opened it by another API (`open()`, `json.load`) would not be counted.
2. **The `consumed` command's template path** in `maintainer-lane.md` (above). A first instance,
   not a recurrence of a known class. **No mechanism authored**, stated plainly: the cheap ones
   (correct the doc line, or let `verify_doc_template.py` fall back to `docs/dev/`) are not in
   this branch's scope and were left to the owner's pick.
3. **A fact-level wiki error that the deterministic cite check cannot detect** (the
   `score_corpus_bullet`/titles clause). The known limit of `scripts/wiki_cites.py` (it checks
   that a cited symbol exists, not that a sentence is true). **No new mechanism possible by
   construction** (C-0): the Sonnet auditor and the step-6 review are the only checks of truth,
   and step 6 is prose and unenforced. Surfaced here, not papered over.
4. **A background task's "exit code 0"** (the known class,
   `reference-background-task-exit-code-unreliable`). This time the notification was right, and
   it was still not the evidence: the result was read from the script's own `GATE_DONE exit=`
   marker and `python -m scripts.gate --result`. No new mechanism; the scratch wrapper writes a
   marker and ends with `exit $ec`.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next drawdown item; this handoff does not pick one.
Scope for whatever is chosen is whatever the owner names, as filed in `docs/dev/work/items/`.
Do not expand beyond it.

If the owner picks **item 30's fix**: it is a `fix/*` branch with its own diagnosis dossier whose
`## Observed` cites `docs/dev/diagnosis/reorder-networkidle-empty-census.md`. The bound-versus-
replace choice is the owner's to make before the branch starts (see the summary). A/B it against
the real test in an in-process loop (memory `reference-pytest-in-process-loop-and-mutation-plugins`),
and do not close item 30 without a falsifiable `verified_by` (C-11).

If the owner asks what is cheapest to unblock: the launcher items 145–147 are the launch
requirements, and the *(owner)* items need a decision before any branch. The lane doc's template
path (above) is a one-line fix that no one has been asked to take.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner that the PR for
`fix/compose-single-context-parse` has merged (this handoff's pointer names that branch's commit
on `main`). Then ask which item to take. Create that branch off `main`, write a plan at
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
