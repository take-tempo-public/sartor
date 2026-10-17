<!-- provenance: schema=1 session=c2815a66-d724-4285-b394-fd1942227c5b branch=fix/capture-generate-stall commit=8c72edd actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-17 -->

# Agent handoff — item 140 part (a): the capture stall found, fixed, and the cover-letter screenshot recaptured; branch `fix/capture-generate-stall` → owner's next pick (item 140 stays open)

**Branch to create:** none chosen. The owner picks the next item. The candidates, with an agent
recommendation (not a decision), are under "What this branch should build". Do not start one unprompted.
**Base branch:** `main`

> **This session took item 140's part (a) after the owner picked it from the previous handoff's list.**
> The branch holds 6 commits ahead of `main` plus the commit that adds this file. **Nothing is pushed and no PR exists yet;
> the push needs the owner's confirmation** (the closing agent asks). **This file does not record the PR number or whether it
> merged.** Check `gh pr list` and `git branch -a` before assuming either.
> - **Reproduced first (C-7):** the instrument (`scripts/capture_stall_probe.py`) went in before any fix. It wraps
>   `capture_screenshots` unchanged and records console/pageerror/dialog events, `/api/` traffic, toast changes and the wizard
>   state around the click. Run 1 reproduced the stall at the same step. Record:
>   `docs/dev/diagnosis/capture-generate-stall.md`.
> - **Cause (observed, then confirmed at route level):** the click landed and `wizardGoTo(5)` refused it with the app's own
>   toast "You changed your composition after approving it" (`compositionFrozen true`, `compositionStale true`,
>   `reachable5 false`; no pageerror, no dialog, no overlay). `WizardComposePage.wait_cards()` returned at the first
>   experience card, so the script clicked Save-and-continue while Compose's arrival `draft_summary` call was still in
>   flight (it began about 1.7 s before the freeze response and ended about 0.6 s after it, from `logs/llm_calls.jsonl`
>   `latency_ms`). The draft then wrote `composition_overrides.summary_text`, which is in the freeze digest. The month-gate
>   guess from the last session stays falsified. **Not observed:** the digest itself inside run 1.
> - **The change:** `wait_cards()` also waits for `Compose.SETTLED` (`ui_pages/wizard_compose.py`; its only caller is the
>   capture script, and all twelve other `continue_to_template()` callers already settle via `open()`).
>   `tests/test_wizard_compose_wait_cards.py` fails without the line and passes with it. A route-level **characterization**
>   test (`tests/test_composition_staleness.py::TestDraftLandingAfterTheFreeze`) pins that a draft persisted after the freeze
>   stales the approval. **No app code changed.**
> - **Verified, n = 1:** run 2 completed end to end (`✓ capture complete in 125.2s`); at the click `compositionStale false`,
>   `reachable5 true`. `walkthrough_coverletter_first-generation.png` was **read**: it shows "October 17, 2026" and no
>   `b`/`e`/`t` id (the committed image it replaces showed `b180` and `March 2025`). `walkthrough_step6_download-with-refine.png`
>   was read and also shows no id. The other nine PNGs the script overwrote were restored with `git checkout`.
> - **Not met, stated plainly:** item 140's other two parts. (1) The `data-scientist-junior` grounding score drop is still
>   unexplained. (2) The original `b180` letter's carrier hypothesis is untested. The item stays **open**.
> - **Gate:** `python -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished 2026-10-17T15:37:11-0700, HEAD 8c72edd` (non-UX 3579 passed, 8 skipped; ux 189 passed, 2 xpassed). Two earlier runs did not pass; see "New this session" for run A (stopped, stale `BOARD.md`) and run B (failed, shared-toast gate). The handoff commit after the gate is docs only.
> - **Spend (telemetry, `compute_call_cost` over each run's window):** run 1 `$0.114` (5 calls), run 2 `$0.192` (7 calls):
>   **`$0.306`**, inside the ~$0.45 cap in the plan.
> - **Wiki:** none of this branch's files is wiki-relevant (`scripts/wiki_relevance.py::is_wiki_relevant` was False for
>   `scripts/capture_stall_probe.py`, `ui_pages/wizard_compose.py`, both test files and the dossier), so no scoped pass ran:
>   a verified no-edit. `.last_ingest_sha` is not advanced; the checkpoint-advancing pass owed from the last handoff is
>   still owed.

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

- Everything through `fix/llm-handle-leak-and-letter-date` ✓ (#181, merge `3bb2674`, MERGED 2026-10-17T16:04:17Z per
  `gh pr list`): the record is `docs/dev/handoffs/llm-handle-leak-and-letter-date.md`.
- **`fix/capture-generate-stall`** ← this branch: item 140 part (a). The push and merge state are not recorded here.
- **Next: the owner's pick.** Item 145's branch 2 (`feat/launcher`) and 3 (`feat/pushbuttons`) are not started; item 171
  waits on four owner answers.

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the
owner's alpha approval. **Do not build item 171's workflow before the owner answers its four questions.** **Do not
start item 145's branch 2 or 3 on this branch.** **Do not re-run the screenshot capture or the score experiment
without the owner's spend approval.**

---

## What just landed on `main`

PR #181 (`fix/llm-handle-leak-and-letter-date`) merged as `3bb2674`: item 140's prompt rule, `<letter_date>`, schema
rewording (`PROMPT_VERSION 2026-10-17.2`), the handle guard and the `leaked_handles` eval metric. This session re-ran
nothing of it beyond the gate. Before it, PR #180 (`fix/gate-skips-linked-worktrees`) merged as `cb3799a`.

**On this branch (not on `main`), oldest first:** `3d7d12a` the dossier, the probe and this session's `consumed` ledger
file; `4eccf51` the probe's toast-observer fix (found by an offline run, no LLM calls); `91e6cf2` the `wait_cards` fix and
both tests; `0d1c083` the recaptured image, item 140's record and the CHANGELOG; `c242909` `BOARD.md` regenerated for item
140's new summary; `8c72edd` the probe no longer reads the shared toast (the first full gate run failed on that, see
below); then the commit that adds this file.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 20 / 10 ceiling -- OVER"** (18 items and the 2 open
epics, 19 and 36; this branch **closed 0**: item 140 stays open). The owner's drawdown direction stands: down to 0 if
possible, before alpha staging. Still twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked
*(owner)*. The lists below are **generated from the item files at this commit** (`structural_errors()` in
`scripts/work_items.py`; not retyped), grouping every non-epic item by status and listing the epics separately (to
reproduce: load the items with `structural_errors(_ITEMS_DIR)` and group `kind == "item"` by `status`); the board prints an epic's children under the epic (item 82), so its header counts differ by design.
Generator output: `META open_all=20 counts={'open': 18, 'blocked': 5, 'deferred': 9, 'watching': 47} epics_not_closed=3 closed_items_and_epics=90`.

`## Open` (18):
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
- **140**: Fix built and measured; screenshots recaptured; open: one fixture score drop unexplained, hypothesis B untested.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **171** *(owner)*: 16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy.

`## Blocked` (5):
- **3** *(owner)*: Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5**: First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** *(owner)*: Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run] [depends on: 6]
- **10** *(owner)*: Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go. [blocked on: everything else landing first, plus the owner's explicit go] [depends on: 3, 6, 7, 9, 19]
- **97** *(owner)*: Orchestration may belong outside the project; sartor's job becomes keeping ARC/CHECKLIST/ledger/BOARD in sync. [blocked on: owner design decision — this is a strategic redirect the owner raised; the tool choice and the scope of any sync layer are the owner's]

`## Deferred` (9):
- **4** *(owner)*: Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet. [blocked on: no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants]
- **7** *(owner)*: Selective, not wholesale, memory consolidation - present the list, act only after explicit approval. [blocked on: owner sign-off on the keep/consolidate/delete list required first - judged irreversible if botched]
- **24** *(owner)*: In-app preview is single-column (python-docx limit); multi-column/paging fidelity needs a spike, never scheduled. [blocked on: not yet scheduled; needs a product-priority decision on investing in the spike before any code work starts]
- **25** *(owner)*: Single-threaded app.run() freezes the app during a diagnostics run; making it threaded is an owner-gated C-1 call. [blocked on: owner governance call not yet made; touches the C-1-sensitive loopback-bind area, deliberately kept out of the diagnostics epic and every branch since]
- **41** *(owner)*: Local lexicons (design, SWE, business, startup) so Compose drafting uses the JD domain's language and conventions. [blocked on: post-1.1.0 - owner scheduled this for 1.1.x investigation, not the Final March]
- **42** *(owner)*: Investigate dotx/mht as import formats and lock a small set of bullet-proof ATS templates with exact-preview fidelity. [blocked on: post-1.1.0 - owner scheduled a template epic for a 1.1.x sprint]
- **43** *(owner)*: v1.1.0 ships an approved-fonts list of Arial, Calibri, Georgia (sprint B2); verified additions considered later. [blocked on: post-1.1.0 - additions only after per-font ATS verification, owner-gated]
- **113** *(owner)*: 18 console UX findings outside Epic C (6 major, 12 minor) await triage; UX-22 is item 112; UX-24 joined C1b. [blocked on: owner triage after Epic C lands: which findings become items, which fold into a later epic, which are dropped]
- **114**: bench.md already summarizes error rows generically; naming error_message/error_type explicitly is a nice-to-have. [blocked on: low value until logs/llm_calls.jsonl accumulates real status="error" rows with the new fields; revisit once there is real data to summarize]

`## Watching` (47):
- **2**: ~107-file wiki + reviews-archive wordmark cleanup deliberately deferred to opportunistic fold-in, not a branch.
- **16** *(owner)*: No jd.txt/expected.json under evals/fixtures/real/ anywhere in this project - --suite real exits 1, zero LLM spend.
- **18**: Same fixture, 68s apart: tone 3.2->2.1, clarification_quality 3.2->3.8, composite 4.06->3.89 - n=2, uncharacterized.
- **23** *(owner)*: PX-52, WATCH: extract prompts.py/client.py when prompt work next opens the file, not a standalone refactor.
- **30**: test_keyboard_reorder_persists_and_reset_reverts: one Playwright 30s timeout; single sample.
- **34**: install_llm_stubs patches _get_client on 4 blueprints but not the corpus ones - real API risk if ever hit.
- **46**: Control assertion (`assert naive`) is itself a timing race; a quiet runner completes write_text between reader polls.
- **47**: Item 44's fix landed in one shared helper; other tests reasoning about spy events after a clear were not audited.
- **48**: ux job took 14m49s on PR #102 vs ~5m1s on PR #100 — zero reruns, so not a flake; the runtime is the anomaly.
- **49**: A suite run leaves personas/bundled/tmp*.html behind; `git add -A` swept one into a commit before it was caught.
- **51**: flake_rates.py is an instrument, not a gate; report --check against a committed budget is a named, unbuilt successor.
- **52** *(owner)*: The tree that lands is never the tree the gate examined; class study documents 6 instances + candidate mechanisms.
- **53**: Quote-parity tracker ignores heredoc semantics; prose quotes in a commit-message heredoc caused a live false-BLOCK.
- **56** *(owner)*: On main the reconciler dies mid-function: empty archive dir, all three pointers survive, stale approval stays live.
- **57**: 400 on a context file that exists: JSONDecodeError/OSError on read. Settle-hole dossier's O-3 had zero non-2xx.
- **58** *(owner)*: Handoff amended after its generated row; fingerprint and stamp both drift, and the next session hits a C-9 block.
- **59** *(owner)*: A role card offers two summary editors: the legacy Experience.summary cache and the canonical variants section.
- **60**: Count reports live roles; the empty hint branches on total rows, so they disagree when every role is retired.
- **61**: Stopping the chain at N-1 yields today's full schema, so the guard skips and the ADD path goes unexercised.
- **62**: Two gate runs over the same code gave `1 xfailed, 1 xpassed` then `2 xfailed` — the xfail is nondeterministic.
- **63** *(owner)*: `_setBusy` adds `body.cb-busy`, but no rule matches it — the busy banner is cosmetic, not blocking.
- **64**: A2 guarded a confirmed mechanism whose reachability was never established — the question, not a bug claim.
- **65** *(owner)*: Drift = files-since-checkpoint assumes periodic catch-up passes; under a per-branch workflow it self-perpetuates.
- **67** *(owner)*: The rail is the gate; the server fallback is the floor. Filed so the surface is tracked, not assumed closed.
- **68** *(owner)*: One lock message covers two refusal causes; telling them apart needs the server to say WHY, a payload change.
- **69**: Prompt-context bias only (no rendered-resume leak) -- lower severity than what A3 fixed, but the same root class.
- **70**: Every current blueprint uses the matched ImportFrom form; an attribute-access blueprint would escape the gate.
- **71** *(owner)*: Pointer + aggregated data for a future orchestrated-epic-execution design pass -- not a proposal.
- **72** *(owner)*: At-a-glance pending-review discoverability regressed -- count is still reachable in the detail modal, not on the row.
- **73** *(owner)*: open_detail() moved from DOM click to page.evaluate; four files still pass but now cover a direct-JS path, not a click.
- **74**: refreshApplications() (1 candidate) replaced by refreshPipeline() (whole roster) at 7 sites -- disclosed trade, no N+1.
- **76** *(owner)*: declared is checked for presence only, never as a date -- the staleness exemption never expires on its own.
- **77**: pytest -m ux is documented LLM-free; nothing gates that each LLM-reachable UX test calls install_llm_stubs.
- **78** *(owner)*: One alice/draft_summary billed row predates the fixed test and doesn't match its token shape -- source unresolved.
- **79**: ci_wait's verdict was right twice but delivery crashed on encoding + TLS faults, both requiring a manual re-run.
- **80**: Dependabot merges staled Epic A's open PR under strict:true, costing an update-branch cycle plus ~6 min CI.
- **81** *(owner)*: drift_count() has no change-status filter -- a deletion inflates drift exactly like new content needing ingestion.
- **82** *(owner)*: open_count sums ALL items; the other three counts sum top-level only -- one header line, two populations, undisclosed.
- **83** *(owner)*: F1/F2/F3/F5/F11/F13 each independently got a different piece of backgrounding wrong; codify the pattern once.
- **84** *(owner)*: implementer->refuter->judge->closer as a Workflow script, N=1; provably >= robust as today's process per the design.
- **85**: trigger is 'unknown' in all 52 ledger rows; the code round-trips it correctly when present -- the payload may lack it.
- **88**: The 3 preview routes + _render_pdf_from_json pass the refreshed companion; today only a manual grep verifies it.
- **90**: A first-field-less entry emits ambiguous markdown that misroutes on re-parse; the fix spans three entry kinds.
- **91** *(owner)*: Inconsistent GPA rendering between two bundled personas; no record of whether Spacious omits it deliberately.
- **92**: Bullets bypass the run-proto path, so no captured template typography (size/bold/font) applies to them.
- **168**: The auditor moved to Sonnet 5 on a measured miss rate, but its own catch rate and cost per pass are unmeasured.
- **169**: Only a <task-notification> prompt is exempt from arming; other injected turns, not yet observed, still arm it.

`## Epics` not closed (3):
- **19** (open): UX-suite flakiness solution sprint - mode-C residual + newly observed instances
- **36** (open): Final March epic A - main-app function + UX
- **40** (blocked) *(owner)*: Final March epic E - the public v1.1.0 cut

### Decisions the owner owes (collected; each is also in the item it belongs to)

- **Item 140, close or continue:** part (a) is done. What remains is the `data-scientist-junior` score drop (repeat that
  fixture N times on the old and new prompts with `--prompt-overrides`, about $0.15 per run per arm, needs spend approval)
  and the untested carrier hypothesis. Close the item over them with a `closure_exception` you name, or run the experiment.
- **The app-side race (new, not fixed):** if a real user clicks Save and continue while an arrival draft is in flight, the
  same sequence locks Generate behind "You changed your composition after approving it" although they changed nothing.
  The mechanism is confirmed at route level; that a user hits it at realistic timing is **not observed**. Options for the
  owner: leave it (a draft takes about 2 to 3 s), make Save and continue wait for in-flight background work, or make a
  draft that lands after the freeze not stale the approval. `TestDraftLandingAfterTheFreeze` pins today's behavior; change
  it with the decision. Touching `static/app.js`'s Compose handlers or `hardening.composition_is_stale` is a gated-surface
  change (C-10): enumerate consumers first.
- **Item 171, Q1:** may a bot enable auto-merge into `main` for the auto classes? (`maintainer-lane.md` step 4 says ask
  before a merge; it was written for agent branches.)
- **Item 171, Q2:** does the 2026-08-07 carve-out (the owner handles the docs-site Dependabot alerts personally) still
  stand, and does it cover version updates or only security alerts?
- **Item 171, Q3:** must the four Actions majors (PRs #10, #109, #51, #54) be resolved, or consciously pinned with a
  recorded reason, before the 1.1.0 tag? (The tag push is the first run of `release.yml` and `docker.yml`.)
- **Item 171, Q4:** a merge queue (a branch-protection change, owner's) or accept the squared CI cost under
  `strict: true`.
- **The `EnterWorktree` question (from item 172):** the scans are fixed and merged (#180), so may agents use the harness
  worktree location inside the repo? Other tools that walk the tree themselves (`pytest` collection, `ruff`, `mypy`) were
  seen unaffected (O6) with one worktree and one run.
- **Item 145, branch 2's start:** the C-2 wording (`charter.md` names "the single-instance probe"; the launcher adds a
  loopback shutdown POST and a health read), the PEP 668 fallback for `pip install --user`, whether bare `sartor` with no
  runtime runs `up`, whether `sartor` is free on PyPI, separate native and container data. Its end-to-end waits on item 3
  (nothing is published).
- **Item 10 and the alpha:** item 3 (GitHub toggles), item 7 (the memory keep/consolidate/delete list), and the owner's
  alpha approval.
- **The *(owner)* items in `## Open`:** 50, 128, 129, 133, 135, 138, 171. The *(owner)* items in Blocked, Deferred and
  Watching are flagged in the generated lists above.
- **Declared by the data-root agent as the owner's call (carried):** whether `sartor --doctor` should print the key path;
  whether the simultaneous-launch race earns an item; whether to reopen item 164 (instrument first); whether the frozen
  `carry_edits=True` generate should keep a typed letter edit over a new letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5); whether a cover letter should be regenerable from the shipped
  screens (item 170's open question).

### Declared, not filed — carried, **not re-verified this session**

The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it,
`docs/dev/handoffs/dependabot-triage-item.md` and `docs/dev/handoffs/data-root.md` "Carried from earlier handoffs"
(about 40 bullets). They are **not re-copied here**, to avoid a second hand-maintained copy that rots. The ones most likely
to matter next:

- The simultaneous-launch race: the one open limit of the single-instance guard (item 146).
- `maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs
  `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01; latest run `36858103525`); cause
  not examined, no item mentions it. `release.yml` and `docker.yml` have no workflow runs at all (item 171). The stall
  found on `fix/capture-generate-stall` is **not** that cause by mechanism: `--smoke` stops after Step 1
  (`scripts/capture_screenshots.py:512`) and never reaches Compose. The smoke failures themselves are still unexamined.
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (dated May 6, no files, not a registered
  worktree). Not touched.
- A checkpoint-advancing wiki pass is owed **before the next wiki-relevant branch**: the freshness gate reads 64 of the
  75-file block threshold, and this branch's scoped pass does not advance the checkpoint.
- A git stash `stash@{0}` ("On feat/run-detail-modal: epic-c C2 staged implementation … parked for C1c") belongs to
  another session. Not touched.

### New this session, declared (observed unless marked)

- **`scripts/capture_stall_probe.py` is committed and reusable** for any future capture stall: `python -m
  scripts.capture_stall_probe --out <events.jsonl> --headless [--keep-user]`. Not wired into the gate. Its snapshot code
  should be run against the live app with no LLM calls before any paid run (that is how its dead toast observer was found).
- The `demo` candidate in `db/resume.sqlite` gained one application per capture run (ids 80 and the next); no route removes
  a user (item 133) and `cleanup()` never removes DB rows (item 139). Nothing was done about it.
- **Three gate runs on this branch.** Run A was stopped by me, not failed: item 140's `summary` was edited and `BOARD.md`
  was stale (`python -m scripts.work_items check` said so); regenerated as `c242909`. Run B **failed**:
  `tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist` (1 failed, 3578 passed, 8 skipped; result file
  `FAILED -- ... failed step 'pytest -m "not ux" -n auto' ... HEAD c242909`). Cause, observed from the assertion: the probe's
  constants named the shared toast element (item 159 / C-11 forbids that in any Python file), and the probe's `_STATE_JS`
  alias collided **by bare name** with the unrelated `_STATE_JS` in
  `tests/ux/regression/test_20261014_editor_text_hidden_tab.py`, which the scanner then reported as well. `main` was clean
  for this gate (the same scanner over the files at `3bb2674`, minus the gate test's own file which the real scan skips).
  Fixed in `8c72edd` by removing the toast reads from the probe; **no allowlist entry was added**. The only thing lost is
  the fact that the toast was shown to the user; `lockReason5` still records the reason. Run C is the result in the Gate
  line above.
- The Grep tool failed once with `EUNKNOWN: uv_spawn` (harness-side); shell `grep` worked. Not investigated.
- A background `&` job started inside a Bash wrapper died with it; the server only stayed up once it was the background
  task's own foreground command. A second launch exits through the single-instance guard ("already running"). In the
  memory `reference-capture-screenshots-demo-state`.
- Carried and still true from item 140: `_parse_or_retry`'s retry drops `max_tokens`; `pm-senior` generate mode
  intermittently gets an empty response; `evals/fixtures/synthetic/corpus` fails to load as a fixture; analyses saved before
  the fix that already contain ids keep feeding later prompts; the eval does not exercise `suggest_skills`,
  `draft_gap_fill`, `recommend_experience_summaries`, `recommend_skills`, `draft_experience_summaries`,
  `draft_surgical_refinement` or critique. All are in item 140's `## Updates` and its dossier.

---

## Recurrences observed this session → guardrail authored

1. **Recurrence of "an instrument that is wrong and nobody can tell"** (the probe's toast observer threw on every frame and
   logged nothing, in the same family as the last session's "evidence you cannot audit later"). It was caught **before** any
   paid run by running the probe's own page code against the live app with no LLM calls, and its output showed an empty
   `toastLog` beside a visible toast. **Mechanism:** none in code. The method is recorded in the memory
   `reference-capture-screenshots-demo-state`. **Unenforced.**
2. **A new file tripped an existing C-11 gate (the shared-toast scanner) on its first full gate run, and the gate's
   bare-name alias matching reported an untouched UX test as an offender too.** **Mechanism exists and held** (the gate
   failed closed, as built); the known limit is in its own docstring: aliases match by bare identifier across files, so a
   generic name such as `_STATE_JS` can implicate an unrelated file. Nothing changed in the gate. The owner may want the
   scanner's report to say WHICH alias caused an alias-use site; as it stands the offender message names only the file and
   scope.
3. **Recurrence of "a hand-derived file left stale after editing its source"** (`BOARD.md` after an item `summary` edit).
   **Mechanism exists and held:** `python -m scripts.work_items check` (also a gate step) reported it; I found it by running
   that check before the gate result, not by the gate failing. **Known limit:** the check detects it, nothing regenerates it.
4. **The interrogative witness paused the first `Write` after the plan-mode prompt** (item 164's class; every handoff's last
   item). It cleared on the identical re-run; no hook was bypassed. **No mechanism authored on this branch**: reopening
   item 164 (instrument first) is the owner's pick. **Unenforced.**
5. **A causal chain stated from code before it was observed** was avoided on purpose this time: the code reading went under
   `## Inferred`, the observation under `## Observed`, and the one place where the observation stops (the digest inside
   run 1) is declared in the dossier and above. **No mechanism possible** for prose. **Unenforced.**

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The list below is
the closing agent's **recommendation for order, not a decision**. Do not expand beyond what the owner names.

1. **Land this branch first (if the owner agrees).** Check first: `gh pr list` and `git branch -a`. Then, in order:
   `python -m scripts.ci_wait <n>` (exit 0 only; 3 means green-after-retries, stop and look), `gh pr merge <n> --merge`,
   `git checkout main && git pull --ff-only`, regenerate the pointer with `print_handoff_pointer.py` and verify it with
   `check_handoff_pointer.py`, then `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 140's remainder, owner's decision:** close over the score drop with a named `closure_exception`, or approve the
   experiment (about $0.15 per run per arm).
3. **The app-side race**, if the owner wants it handled: a small branch, instrument first (record the digest before and
   after the draft in the real page), consumers enumerated first (C-10).
4. **Item 171, after the owner answers Q1 to Q4.** Instruments first: read the failing log of PR #127; trace whether
   `release.yml`'s `publish` job can run on `workflow_dispatch`; read the changelogs for the four Actions majors. Then the
   policy and the small `pull_request` workflow. Do the ruff bump on its own branch (`pyproject.toml:113`).
5. **File and look at `capture-smoke.yml`'s three failed scheduled runs** (cause not examined; by mechanism not this
   session's stall, because `--smoke` stops after Step 1).
6. **A checkpoint-advancing wiki pass** (see the carried-forward notes).
7. **Item 145's branch 2** (`feat/launcher`). Read item 0145's `## Updates` first. The first commit is an instrument (does a
   built wheel ship `alembic.ini` and `personas/cover_letter.html`? does the image's recall index build?). Ask the owner the
   questions listed above before any code.
8. **Open product bugs, agent-workable:** 130 (profile edits do not reach the AI), 105 (no education from corpus import),
   131 (a retired application cannot be found again), 107 (no account-naming step at first run), 134 (contradicting
   smoke-cost estimates), 139 (`capture_screenshots` leaves its demo user), 98 (wiki freshness measures
   checkpoint-staleness), 99 (`install.md` documents unpublished paths; depends on 3), 137 (a models and call-settings
   review).
9. **Remaining container checks and H2** if the owner picks them; the method is in
   `docs/dev/blast-radius/data-root.md` O10 to O13.
10. **Reopening item 164** if the owner picks it: instrument first.
11. **The *(owner)* items**, which need a decision before any branch.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path:
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), then confirm with the owner whether this branch was pushed and merged (this file
does not say). Then ask which item to take. Create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and
show it to the user before touching any code. **Do not code first.**

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
