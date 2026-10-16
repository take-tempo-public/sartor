<!-- provenance: schema=1 session=7e849060-2775-4e0f-b4bf-a8be8c434c41 branch=feat/single-instance-and-quit commit=349ace5 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-15 -->

# Agent handoff — items 146 + 147: one launch, one server, an off switch (`feat/single-instance-and-quit`) → owner's next drawdown pick

**Branch to create:** none chosen. The owner picks the next item from `docs/dev/work/BOARD.md`
`## Open`; the launcher (item 145) is the natural follow-on. Do not start one unprompted.
**Base branch:** `main`

> **This session took items 146 and 147 (owner pick, 2026-10-15; item 145 deliberately left) and
> closed both. The branch is committed and the full gate is green on its code. It is NOT pushed
> or merged: the PR, the C-2 sign-off and the merge are the owner's.**
> - **The change:** `instance.py` (new stdlib leaf module: the pre-bind port probe, the instance
>   file, `request_shutdown`, `IdleTracker`); `blueprints/lifecycle.py` (new: `GET /healthz`,
>   `POST /api/shutdown`, `POST /api/heartbeat`); `app.py:main` (`_claim_port_or_exit`,
>   `--idle-timeout`); `web_infra` (`_is_same_origin_request`, public cached `app_version`); and the
>   page (Settings → Quit Sartor, an opt-in heartbeat, `beforeunload` for unsaved text only).
>   Dossier, with the consumer enumeration, every observation, and the four measurement scripts
>   verbatim: `docs/dev/blast-radius/single-instance-and-quit.md`.
> - **Observed (C-7), one run each unless stated:**
>   - On Windows a second `python app.py`, and one next to a foreign `http.server`, **bind the port
>     silently**; Werkzeug's own address-in-use error never fires. So the guard is a pre-bind probe.
>   - A refused loopback connect costs **2.04 s** here (5 runs, 2.037–2.058 s); an exclusive bind is
>     **0.3 ms**; classifying a live owner by `GET /healthz` is **24.5 ms**. The probe binds first.
>   - Real app, reloader and `FLASK_DEBUG=0`: second launch exit 0 "already running"; shutdown
>     refused (403) with no action header and with a cross-site `Sec-Fetch-Site`; same-origin 202
>     then **exit 0 in 0.49 s / 0.33 s** with the instance file removed; a foreign owner exits 1
>     naming the port and writes no file.
>   - `--idle-timeout 5` exited 0 at **300.1 s** (`FLASK_DEBUG=0`) and **300.3 s** (reloader, 0
>     restarts) with `/healthz` polled every 20 s throughout (exempt from activity).
> - **Defects found and fixed on the way** (each written down when found):
>   - **Idle expiry did not cover streamed (SSE) responses.** All four SSE routes return
>     `Response(generator)` without `stream_with_context`, so teardown ran before the generator did
>     its paid work. Found by checking a user-doc sentence against the code; red-before test, then
>     fixed (`8116be1`).
>   - **A confirm/error dialog opened from the Settings drawer was unclickable** (drawer z-index
>     1500 over `.cb-modal` 1000). Found by the new UX test's own call log.
>   - **The scribe's wiki counts were wrong** (123 / 24; "the only module that opens a loopback
>     socket"; a stale "392-line"). Re-derived and corrected before commit.
> - **Not counted:** the first reloader-mode idle run. This session's own `.py` edits made the
>   reloader restart the child three times (the log's `Detected change` lines), resetting the clock.
>   Recorded as invalid in the dossier; the two clean runs above replace it.
> - **Declared, not hidden (C-11):**
>   - **Two launches racing inside the probe window can both bind.** Windows permits it (observed)
>     and the instance file is written after the probe, so it cannot arbitrate. Closing it needs an
>     exclusive listening socket, i.e. replacing `app.run`. Not done; stated, not counted as
>     protection.
>   - The probe checks `127.0.0.1` only, never `--host`.
>   - The idle path was proved on a route *shaped like* the SSE routes, not run against
>     `/api/generate/stream`. The unload guard's editor and Compose-autosave arms set the state the
>     predicates read directly rather than walking the wizard to it.
>   - Launch time (1.9–2.5 s) was not split into import time and probe time; macOS and Linux timings
>     were not measured.
> - **Charter C-2 was amended on this branch, owner-directed (chat, 2026-10-15), and needs the
>   owner's sign-off at the PR** (ceremony step 3). Clarification only: a connection Sartor makes
>   to its own loopback address is not outbound traffic and not a third class; the two off-box
>   classes are unchanged. Pinned by `tests/test_egress_allowlist.py::test_instance_module_names_only_loopback`
>   (red under four scratchpad mutations) and the AST allowlist entry for `instance.py`.
> - **Gate:** green, `python -m scripts.gate --result`, on the committed tree — see "What just
>   landed". Two earlier attempts did not complete: the first failed at `mypy .` on five errors in
>   *my* `tests/test_cli_setup.py` (fixed, `349ace5`); the second was killed by the harness's
>   memory-pressure reaper as `pytest` started. The owner then asked for a rerun, which passed.

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
- ~~`fix/reorder-networkidle-empty-census`~~ ✓ (#171) · ~~`fix/compose-single-context-parse`~~ ✓
  (#172): item 161 closed · ~~`fix/reorder-networkidle-bound`~~ ✓ (#173): item 30's Phase A;
  **item 30 stays `watching`**.
- **`feat/single-instance-and-quit`** ← this branch (see the pointer's commit on `main`, once
  merged): items **146 and 147 closed**.
- **Next: the owner's pick.** Open items, none started: the launcher item **145** (now unblocked
  on its two server-side dependencies; its end-to-end still needs item 3); item 7 memory-
  consolidation apply (Deferred); the owner-decision items (50, 128, 129, 133, 135, 138).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`feat/single-instance-and-quit`:

| Commit | What |
|---|---|
| `f1e64e4` | **Dossier first** (C-7, C-10). Observed on the real app before any production edit; the consumer enumeration for the one gated surface (`ui_pages/selectors.py`: 14 non-test importers, 0 member enumerators) and every other site; item 146's observation; this session's consumed-ledger file. No production edit. |
| `6c30d81` | **Server side.** `instance.py`, `blueprints/lifecycle.py`, `app.py:main`, `web_infra` gate and `app_version`, the C-2 amendment, the egress allowlist entry and its AST pin, `pyproject` / `wiki_relevance` registrations; tests `test_instance.py`, `test_lifecycle_routes.py`, `test_cli_setup.py`. |
| `b9d4f6c` | **Page side.** Quit control, stopped dialog, opt-in heartbeat, `beforeunload` guard, the drawer-over-dialog z-index fix, additive `ui_pages/selectors.py` keys; 8 UX arms and an axe check. |
| `8116be1` | **Fix:** a streamed response holds the idle in-flight count until it closes (red-before test). |
| `6e04f31` | **Docs.** `install.md`, `SECURITY.md`, `CHANGELOG.md`, items 146/147 closed with `verified_by`, board regenerated (open 21 → 19), dossier updates, the scoped wiki update. |
| `349ace5` | `tests/test_cli_setup.py` imports `webbrowser`/`atexit`/`os`/`preflight` directly (the gate's `mypy .` rejected the `app_module.` reach-through). |
| (this commit) | The dossier's instruments appendix, this handoff and its ledger event. Docs only. |

**Verified, with the evidence:**
- **Before:** `python app.py` twice on a port bound silently on Windows (dossier A1/A2); next to a
  foreign server likewise (B). Nothing identified a running Sartor; only `Ctrl+C` stopped it.
- **After, on the real app** (dossier "Observed after the build"): see the callout above.
- **Probe design** is measured, not assumed: connect-first would have cost ~2 s on every normal
  launch (`measure_probe.py`, in the dossier appendix).
- **The unload guard is red under mutation:** with `_composeSaveTimer`, the stopped flag, and the
  form-field comparison each broken in turn, exactly the three tests for those predicates failed
  and the other five stayed green; then restored (`git diff` showed 103 insertions, 0 deletions in
  `static/app.js`, 0 markers left).
- **Wiki:** scoped `/wiki-self-update` on four pages (`code-module-map`, `route-surface`,
  `diagnostics-console`, `engineering-workstreams`). Cite check 0 violations (three runs); the
  Sonnet auditor made 2 catches (one a scribe regression: "each seam registers with no
  `url_prefix`" was false for `assistant_bp`); my review made 4 more, including a wrong count.
  The checkpoint was **not** advanced. `docs/wiki/log.md` has the entry, the three signals apart.

**Gate:**
- `python -m scripts.gate --result`, run on `349ace5`:
  `gate --result: PASSED on this tree -- exit 0, failed step None, finished 2026-10-15T18:53:14-0700, HEAD 349ace5`
- **That result is stale for the tip**, because the result binds to HEAD. This handoff's own
  commit (docs plus one ledger line) sits on top of it and changes no code or tests. The handoff
  validation, `work_items check`, `doc_lints` and `wiki_cites` were re-run on the tip; the full
  gate was not. CI re-runs on the tip.
- **What it ran** (`GATE_START 18:31:19`, `GATE_DONE exit=0 18:53:14`, the wrapper's own markers):
  **21 min 55 s** for the whole gate. Preflights, `ruff check`, `ruff format --check` (418 files) and
  `mypy .` (434 files) clean; `pytest -m "not ux" -n auto` **3463 passed, 8 skipped** (5 m 43 s);
  `pytest -m ux` **189 passed, 2 xpassed** (15 m 55 s; the two xpassed are the deliberate non-strict
  xfails in `test_20260708_busy_states_and_chip.py`, untouched); `work_items check` OK (170 files).
  **0 `RERUN`, 0 `FAILED`, no rerun-rate alarm.** The new stall line read
  `[ux] networkidle pre-drain: 2 stall(s) in 115 reach(es), 21.6 s waiting`: the two deliberate
  probes, 115 reaches as last session, so 0 unintended (item 30: unchanged, still `watching`).
- **Wall-clock note:** 22 minutes here against 15 m 18 s last session. The UX tier alone took
  15 m 55 s against 9 m 10 s; this branch adds 9 UX tests, which does not account for it. Not
  investigated (machine load was not captured). Do not read "22 minutes" as this branch's cost.
- **The merge rule:** `python -m scripts.ci_wait <n>` must exit 0. Exit 3 means stop and look.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 19 / 10 ceiling -- OVER"**
(17 items below plus 2 open epics; this branch **closed items 146 and 147**, taking the board from
21). The owner's drawdown direction stands: down to 0 if possible, before alpha staging. Still well
past the ~8–10 reduction-sprint threshold. Owner-decision items are marked *(owner)*.

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
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link. (This branch added a Quit section to that drawer and no help bubble.)
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **145**: Owner pre-launch requirement (2026-08-16): stdlib launcher, two backends, per-OS one-click wrappers. Now has `/healthz`, the instance file and `POST /api/shutdown` to build on.

`## Blocked` (4): **3**, **5**, **8**, **97**.
`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.
Plus `## Watching` (44, including **30**) and `## Epics` (6) in `BOARD.md`.

Declared, not filed. New this session; **observed unless marked**:
- **The simultaneous-launch race** (above, and item 146's resolution): the one open limit of the
  guard this branch built. Owner's call whether it earns an item.
- **Wiki route and blueprint counts are prose, derived by whoever last edited the page.** The
  scribe's counts were wrong twice this pass; the auditor caught one scope word, not the counts.
  Unenforced. A deterministic check (anchored decorator count vs the number in the page) is
  possible and was not built.
- **Reported by subagents, not verified by me** (treat as leads):
  - `blueprints/corpus/__init__.py`'s own docstring sums its routes to 50 where the files hold 54
    (I verified the 54 by an anchored grep; I did not read the docstring).
  - `hardening.py:1780-1785` says the dev server "defaults to `threaded=False`", but Flask's
    `app.run` defaults `threaded=True` (an Explore agent read Flask 3.1.3; I did not re-check).
  - `docs/dev/releasing.md:36-39` still describes a `GATE` step in the publish job that
    `release.yml` no longer has.
  - **For item 145:** `SARTOR_HOME` is not honoured by `analyzer.py:568` `LOG_DIR`,
    `db/session.py:24-25`, `preflight.py:415` or `web_infra/clients.py:34` (`CHANGELOG.md` already
    lists `LOG_DIR`); the `Dockerfile` sets no `SARTOR_HOME`, `VOLUME` or `HEALTHCHECK`;
    `/data` must be writable by uid 10001; `sartor` is already the app wheel's project name and
    console script (`app:main`), so the launcher needs another name or `main` needs verbs
    (inference); in an installed wheel `--setup`'s index build likely writes under
    `site-packages` (inference).
- **A background-run reaper kill left no orphans this time** (listed: only the isidium MCP server
  and the editor's Pyright, neither mine). Known class; memory
  `reference-shared-machine-oom-kills-bg-runs`.
- **The IDE's Pyright again reported stale "not defined / not accessed" hints** between
  consecutive edits; `ruff` and `mypy` were clean each time.
- **`maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`**
  (this handoff's validation used `docs/dev/AGENT_HANDOFF_TEMPLATE.md`); carried from earlier.

Carried from earlier handoffs, **not re-verified this session**:
- the three probe tests (P3, P4, P5) stay in the UX tier until the owner decides (item 30);
- the frozen `carry_edits=True` generate keeps a typed letter edit over a newly produced letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5): an owner question;
- whether a cover letter should be regenerable from the shipped screens (item 170's open question);
- `python -I` drops the user site-packages on this machine (Playwright lives there);
- the `isidium` MCP server (two `python.exe -m isidium.store.client.cli mcp`) is not a session's to stop;
- `ruff` is not on the Git Bash PATH here (`python -m ruff` works);
- the sibling window's gap is one sample (1.133 s; diagnosis O8), the 3 s default is a judgment;
- a trunk-time `compacted` row is no longer in `git log`; branch-time rows are (item 165);
- `plan_gate` reports a detached HEAD as `""`, so its `plan-archived` receipt stays in the tracked
  shard there (item 169);
- E1 sees a `lines N-M` reference only when a path is on the same or the preceding line, and E3 is
  word-presence in the file (`scripts/wiki_cites.py` docstring);
- `ALLOWED_LINE_CITES` holds 25 line cites on 8 pages; converting one to a symbol forces the entry down;
- bash-run scripts edit files without the Edit|Write gates seeing them;
- a gap-fill retire, or a drag back to the same position, marks an approval stale without changing
  the résumé; approvals frozen before `fix/frozen-composition-staleness` carry no digest;
- the post-generate announcement still says "Resume and cover letter generated" when no cover
  letter was produced (`static/app.js`, `runGeneration`'s `_announce`);
- `lastCoverLetterPath` is assigned in seven places and read by none (`static/app.js`);
- a stale comment at `db/build_context.py:92`: fold it into any branch that touches that file;
- `scripts/enforcement/blast_radius.py` says `ui_pages/selectors.py` has "14 non-test importers";
  re-derived this session as 14 by the dossier's anchored grep (an earlier session said 15);
- two UX tests hard-code the `#cbConfirm*` ids instead of the `ConfirmModal` selectors
  (`test_20260612_corpus_affordance_polish.py`, `test_20260707_ux_w4_aesthetic.py`);
- the doc-writing skill's evaluation plan has not been run (the owner's call when);
- 32 one-way wiki backlinks (WARN), as counted by an earlier `/wiki-lint`;
- `python scripts/check_docs_projection_fresh.py` reported STALE on a clean tree four sessions ago;
  not re-checked since;
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
  (item 161's scope was the GET);
- the wiki auditor found a fact-level error the cite check cannot see (item 161's close-out).
  Brief a scribe's page edit and its audit to the **same** region, and widen the audit to the whole
  bullet or paragraph (`docs/wiki/log.md`, the 2026-10-15 entries).

---

## Recurrences observed this session → guardrail authored

1. **A claim written into the user docs before it was checked against the code** ("a generation
   that is still running is never cut off", written while the in-flight count did not cover SSE).
   Recognized as the C-0 / C-12 class (a filled gap becomes a premise).
   - **Mechanism authored, for the instance:** `tests/test_lifecycle_routes.py::test_a_streamed_response_holds_the_in_flight_count_until_it_closes`
     (and the abandoned-stream arm) was red before the fix and fails closed if the hand-off to
     the response is removed.
   - **For the class: none.** A sentence in a doc is not checkable by a gate; the only defence was
     the habit of checking each behavioural claim against code before writing it. **Unenforced.**
2. **A subagent's self-reported count and an unsearched scope word taken as verified** (scribe:
   "123 … actually counted via grep", "the only module that opens a loopback socket"). A
   recurrence of memory `feedback-verify-rollup-claims-against-source`.
   - **No mechanism authored**, stated plainly. A deterministic count-vs-decorator check for wiki
     pages is possible (see the carried-forward list) and was not built. The orchestrator's review
     step caught all four defects; it is prose and **unenforced** (charter C-11 says so in the
     `/wiki-self-update` command itself). The memory entry was extended; a memory is not a
     mechanism.
3. **A measurement invalidated by the session's own edits** (new class). The Werkzeug reloader
   watches every `.py` under the repo root; editing during a timed `--idle-timeout` run restarted
   the child and reset the clock. Detected by reading the run's own log, not the exit notification.
   - **No repo mechanism is possible** (it is a property of the dev server and of what the session
     was doing). The defence is the habit of grepping the log for `Detected change` before
     trusting a timed run, now in memory `reference-flask-stream-teardown-and-reloader-watch`
     (**unenforced**). The dossier records the invalid run so it cannot be cited as evidence.
4. **A full-gate step failed on something a targeted check had not covered** (`mypy .` rejected
   five reach-throughs in my own test; I had type-checked single files). The gate **failed
   closed as designed** and named the file; the lapse was running a subset in place of the
   definition ("`gate.py` is the single definition"). No new mechanism needed or authored.
5. **The interrogative witness paused the first `Edit`/`Write` after turns the owner did not
   type** (about four to six times: wiki page edits, the memory edits, a route-surface edit, a
   scratch script). Each pause cleared on a re-run, as designed, with no bypass.
   - **Observed.** Item 164 (closed 2026-10-14) added a prefix test, `_NON_HUMAN_PROMPT_RE =
     \s*<task-notification>` (`scripts/enforcement/guards/interrogative_witness.py:77`), and the
     batch window; anything else still arms, which the code's own comment says. This session's
     state file reads `prompt_seq 18, armed_seq 10` against **4 prompts the owner typed**. The
     transcript has exactly **6 other user-role turns** that do not begin `<task-notification>`:
     2 `origin=peer` hand-backs (text begins `Another Claude session sent a message:`), 3
     harness-injected skill bodies (`isMeta`), and one `[Request interrupted by user]`. 4 + 6 = 10.
     `<task-notification>` turns were not seen to arm, and the batch window refused siblings as
     designed, so 164's *verified* scope is not refuted.
   - **Not established.** Which of the six armed which pause: the hook writes no per-pause
     receipt and stores no prompt text, and the payload's `prompt` for a peer turn was never
     observed (164's O6 found no `origin` field in the payload). **An earlier version of this
     handoff said the pauses followed hand-backs. Skill bodies are at least as likely (3 against
     2) and have no stable prefix, so a peer-prefix patch alone would miss them.** Five of the 18
     events are also unaccounted for.
   - **Evaluation (owner-requested): reopen 164, instrument first.** Its title names
     "hand-backs" but its `verified_by` covers only `<task-notification>`, and its resolution
     names unseen shapes as a residual that this session has now seen. The first commit on that
     branch should be the instrument (C-7): per `UserPromptSubmit`, log the payload's keys, the
     first ~60 characters of `prompt`, and whether the transcript's last entry exposes `origin`
     at hook time (164's O7 tested that only at `PreToolUse`). Choose the discriminator after
     that, not before (arming only on non-`meta` turns is one candidate). Reopening needs
     `guardrail_deferred` or a `guardrail` under C-11.
   - **No mechanism authored on this branch**, stated plainly. The reopen is **not done here**: it
     needs its own branch, and it is the owner's pick.
6. **The harness reaper killed a background gate run** (known class). Listed processes
   afterwards; no orphans. No repo mechanism possible; the owner asked for the rerun explicitly
   and it was not restarted on my initiative.

---

## What this branch should build

**Nothing is queued.** The owner chooses the next drawdown item; this handoff does not pick one.
Scope for whatever is chosen is whatever the owner names, as filed in `docs/dev/work/items/`.
Do not expand beyond it.

If the owner picks **item 145** (the launcher): the server-side contract it needs now exists —
`GET /healthz` (`app`, `version`, `pid`, `instance_id`, `idle_timeout_s`), the instance file
`sartor-instance.json` under `SARTOR_HOME` (written by the launching process, `pid` is the
supervisor under the reloader — decide liveness with `/healthz` and `instance_id`, never by pid),
`POST /api/shutdown` (loopback, same-origin or no `Origin` at all, header `X-Sartor-Action:
shutdown`; 501 unless started by `sartor`), and `--idle-timeout`. Start from the carried-forward
"For item 145" list above, and re-verify each line before depending on it. The probe module is
`instance.py`; a launcher that talks to a running server needs the same C-2 loopback clarification
that is now in the charter. The end-to-end still depends on item 3 (publish).

If the owner picks **reopening item 164** (the interrogative witness arming on turns the owner did
not type): the evaluation is in "Recurrences" #5. Start with the instrument, not a fix; do not
patch a peer prefix before the payload's `prompt` for those turns has been observed.

If the owner asks what is cheapest to unblock: the *(owner)* items need a decision before any
branch. The lane doc's template path (above) is a one-line fix that no one has been asked to take.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner that the PR for
`feat/single-instance-and-quit` has merged and that the **C-2 amendment was signed off** at it
(this handoff's pointer names that branch's commit on `main`). Then ask which item to take.
Create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to the
user before touching any code. **Do not code first.**

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
