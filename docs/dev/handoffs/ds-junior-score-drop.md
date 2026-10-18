<!-- provenance: schema=1 session=c2815a66-d724-4285-b394-fd1942227c5b branch=fix/ds-junior-score-drop commit=5fcc546 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-18 -->

# Agent handoff — item 140 part (b): the `data-scientist-junior` score drop measured (low scores under the OLD code too); branch `fix/ds-junior-score-drop` → owner's next pick (item 140 stays open)

**Branch to create:** none chosen. The owner picks the next item. The candidates, with an agent
recommendation (not a decision), are under "What this branch should build". Do not start one unprompted.
**Base branch:** `main`

> **This session took item 140's part (b) after the owner approved the experiment on 2026-10-17.**
> The branch holds 5 commits ahead of `main` plus the commit that adds this file. **Nothing is pushed and no PR exists yet;
> the push needs the owner's confirmation** (the closing agent asks, and asks again before any merge: "merge and prune when
> CI is green" covered PR #182 only). **This file does not record the PR number or whether it merged.** Check `gh pr list`
> and `git branch -a` before assuming either.
> - **Registered before any paid run (commit `f3f51bd`):** an interleaved A/B of the OLD code (`a970033`, `PROMPT_VERSION
>   2026-08-14.1`, no guard, no letter date) against `main` (`2026-10-17.2`), `data-scientist-junior`, assemble mode,
>   grounding rubric only; "low" fixed as score `< 3.0`; stage 1 N = 4 per arm; a written decision rule; a $2.50 telemetry
>   cap; the limits stated in advance. `--prompt-overrides` could not do it: three of the four changes (schemas,
>   `<letter_date>`, guard) are not persona constants. Record: `docs/dev/diagnosis/ds-junior-score-drop.md`.
> - **Method, verified free before any spend:** arm A ran from a detached worktree OUTSIDE the repo
>   (`git worktree add --detach C:/Dev/sartor-eval-old a970033`) with `SARTOR_HOME` pointing at this repo's data root, so no
>   key file was copied. The repo has an editable install that could have shadowed the old code; each arm's
>   `analyzer.__file__` and `PROMPT_VERSION` were printed first (arm A imported its own `analyzer.py` at `2026-08-14.1`), and
>   every record's `prompt_version` matched its arm. The worktree is removed.
> - **Result (stage 1, 8 of 8 runs scored):** old arm `1.2`, `0.0`, `4.8`, `5.0`; new arm `0.0`, `4.9`, `0.0`, `5.0`. **Low in
>   2 of 4 under BOTH.** By the registered rule (`a >= 1`): the `1.2` is **not evidence of a regression at this n;
>   consistent with variance**, not proven. Exact 95% interval for 2 of 4 is `[0.068, 0.932]` per arm (Fisher p = 1.000), so
>   this does **not** show the rates are equal. The outcome is **bimodal** (`0.0`/`1.2` vs `4.8` to `5.0`); the earlier
>   "`4.8` x4" was four high draws.
> - **Re-replicated on this fixture:** `b` handles in the analysis in 4 of 4 old-arm runs (6 to 11 each) and 0 of 4 new-arm
>   runs (its 5 findings per run are the clarify response's own `q1..q5`); letter date correct 0 of 4 vs 4 of 4; **no letter
>   carried a handle in any of the 8**.
> - **Not met, stated plainly:** (1) nothing says the new prompts leave the low-score rate unchanged; (2) generator and judge
>   variance are not separated (no generated text is kept); (3) one fixture, assemble mode only; (4) item 140's hypothesis B
>   (the original `b180` carrier) is still untested, now 31 letters without a handle, 15 of them under the old prompts. The item stays **open**.
> - **Gate:** `python -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished 2026-10-17T17:45:22-0700, HEAD 5fcc546` (non-UX 3579 passed, 8 skipped; ux 189 passed, 2 xpassed). Two earlier runs on this branch did not finish: one stopped by me to run the wiki-relevance check first, one stopped to correct item 140's letter count (see "New this session" and "Recurrences"). The handoff commit after the gate is docs only.
> - **Spend (telemetry, `compute_call_cost` over each run's window):** `$0.6678` for 8 runs (mean `$0.0835`, against the
>   `$0.15` the dossier guessed), inside the `$2.50` cap. Stage 2 was not run; the rule did not call for it.
> - **Wiki:** `evals/TUNING_LOG.md` is wiki-relevant (the other three changed files are not); a **verified no-edit** entry is
>   in `docs/wiki/log.md` (`15112eb`): the one page citing the file does so by path, no page cites it by line or states the
>   fixture's scores; `wiki_cites` 0 violations; `wiki_freshness` **65 of 75** (it was 64). A checkpoint-advancing pass is
>   still owed and is now 10 files away from blocking.

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

- Everything through `fix/capture-generate-stall` ✓ (#182, merge `7807c81`, MERGED, branch pruned): the record is
  `docs/dev/handoffs/capture-generate-stall.md`.
- **`fix/ds-junior-score-drop`** ← this branch: item 140 part (b), a measurement with no product change. The push and merge
  state are not recorded here.
- **Next: the owner's pick.** Item 145's branch 2 (`feat/launcher`) and 3 (`feat/pushbuttons`) are not started; item 171
  waits on four owner answers.

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the
owner's alpha approval. **Do not build item 171's workflow before the owner answers its four questions.** **Do not
start item 145's branch 2 or 3 on this branch.** **Do not run a further paid eval or capture without the owner's spend
approval.**

---

## What just landed on `main`

PR #182 (`fix/capture-generate-stall`) merged as `7807c81`: the capture script now waits for Compose to settle before
Save-and-continue (`WizardComposePage.wait_cards`), the recaptured cover-letter image, `scripts/capture_stall_probe.py`, and
two tests. Before it, PR #181 (`fix/llm-handle-leak-and-letter-date`) merged as `3bb2674`.

**On this branch (not on `main`), oldest first:** `f3f51bd` the dossier with the A/B registered before any paid run;
`eb7953d` the preflight record; `746020c` the result, item 140's record, `BOARD.md` and the `TUNING_LOG.md` entry;
`15112eb` the wiki log's verified-no-edit entry; `5fcc546` a correction to item 140's letter count (15 of the 31 letters
were under the old prompts); then the commit that adds this file. **No production code changed.**

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 20 / 10 ceiling -- OVER"** (18 items and the 2 open
epics, 19 and 36; this branch **closed 0**: item 140 stays open). The owner's drawdown direction stands: down to 0 if
possible, before alpha staging. Still twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked
*(owner)*. The lists below are **generated from the item files at this commit** (`structural_errors()` in
`scripts/work_items.py`; not retyped), grouping every non-epic item by status and listing the epics separately (to
reproduce: load the items with `structural_errors(_ITEMS_DIR)` and group `kind == "item"` by `status`); the board prints an
epic's children under the epic (item 82), so its header counts differ by design. Generator output: `META open_all=20 counts={'open': 18, 'blocked': 5, 'deferred': 9, 'watching': 47} epics_not_closed=3 closed_items_and_epics=90`.

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
- **140**: Fix built, measured, screenshots recaptured; score drop not specific to the change; carrier hypothesis never reproduced.
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

- **Item 140, close or keep open (new):** every build and measurement part is done. What is left is the original `b180`
  carrier (hypothesis B), which has not reproduced in 31 letters (23 in the first item-140 session, 11 old-prompt and 12 new-prompt, plus 8 here, 4 and 4) and which the
  guard covers regardless (a handle in `cover_letter_content` is a hard error). The closure bar needs a falsifiable
  `verified_by` or an owner-named `closure_exception` (`scripts/work_items.py`); I did not close the item and will not.
  Suggested wording for you to adopt or change: *"Hypothesis B (the `b180` letter carrier) never reproduced in 31 letters;
  the runtime guard hard-errors a handle in `cover_letter_content`; the score drop is not specific to the change
  (`docs/dev/diagnosis/ds-junior-score-drop.md`)."* Closing also means moving `status` and regenerating the board.
- **Whether to run stage 2 or another fixture (optional):** not needed by the rule. A larger sample would narrow the
  `[0.068, 0.932]` interval; about `$0.0835` per run, so N = 8 per arm is about `$0.7`.
- **Whether to file a gate for the per-branch wiki obligation (new, C-11):** see "Recurrences" item 3. A mechanism is
  possible and was **not** built here; it changes `scripts/gate.py`, a C-10 gated surface, so it is its own item.
- **The app-side race (carried, not fixed):** if a real user clicks Save and continue while an arrival draft is in flight, the
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

- **The A/B method works and is in memory** (`reference-eval-harness-auth-and-cost`): detached worktree outside the repo,
  `SARTOR_HOME`, a per-arm `analyzer.__file__` check, `prompt_version` asserted per record, cost from a telemetry window.
  **The driver and preflight scripts live in the session scratchpad and are not committed**; their logic is described in the
  dossier. If you want it reusable, a small committed `scripts/` tool is an option, not done.
- **A second kind of low score** appeared in the new arm: `0.0` with `fundamental_domain_mismatch` and
  `candidate_self_disqualifies_in_cover_letter` (the letter itself says the candidate does not fit), not an invented
  claim. Not interpreted. It raises a rubric question (should a letter that honestly says the corpus does not fit score
  `0.0` on grounding?) that is the tuner's or the owner's, not settled here.
- **This fixture is a weak single-run regression signal:** its assemble score is bimodal and the corpus seed does not match
  it. I did **not** check whether any committed baseline or gate reads it as a single run; unverified.
- The runner exits `2` for a low-scoring run (the smoke gate), which is not a pipeline failure; every `rc 2` row in the
  dossier is a low score.
- **`block-doubled-backslash` stopped two of my commands** (a regex and a Python string that needed a literal `\.`). The
  PowerShell tool and the Edit tool were the way through, as the guard says; no hook was bypassed.
- **Two of my gate runs on this branch were stopped, not failed:** the first because I had started the gate before the
  wiki-relevance check (see "Recurrences" item 3), the second to correct a wrong letter count in item 140's record that I
  found while drafting this file (`5fcc546`: 15 of the 31 letters were under the old prompts, not "23 under the new"). The
  result cited above is the run that finished on the final tree.
- Carried and still true: everything under "New this session, declared" in `docs/dev/handoffs/capture-generate-stall.md`
  (the probe, the `demo` DB rows, the stale-`BOARD.md` note, the background-job note). Not re-copied.

---

## Recurrences observed this session → guardrail authored

1. **The interrogative witness paused the first `Write` after the plan-mode prompt** (item 164's class; every handoff's last
   item). It cleared on the identical re-run; no hook was bypassed. **No mechanism authored on this branch**: reopening
   item 164 (instrument first) is the owner's pick. **Unenforced.**
2. **`block-doubled-backslash` fired twice on my own commands.** **Mechanism exists and held** (it blocked, named the way
   through, and I took it). Nothing to add.
3. **Recurrence of "a close-out obligation done after the gate was launched"** (last session: a stale `BOARD.md`; this
   session: the wiki-relevance check for `evals/TUNING_LOG.md`). The lane puts the pre-close sweep BEFORE the gate; I
   launched the gate first, caught it by running `is_wiki_relevant()` over the diff, stopped the run (about 4 minutes lost)
   and re-ran. **A mechanism IS possible and I did not build it** (C-11, stated): a gate step that fails when a branch's
   diff contains a wiki-relevant path and neither a `docs/wiki/pages/` edit nor a `docs/wiki/log.md` change is in the same
   diff. I did not build it because it changes `scripts/gate.py`, a gated surface (C-10), on a branch whose scope is a
   measurement. **Today this stays prose, unenforced**, backed only by the freshness count (`wiki_freshness`, 65 of 75),
   which counts files and cannot see a missing log entry. **Proposed as its own item; the owner decides.**
4. **Estimate versus measurement:** the dossier guessed `$0.15` a run and the telemetry said `$0.0835`. This time the
   estimate was high, the opposite direction to last session's. **Mechanism in this run only:** the driver aborted above the
   cap, but it lived in the scratchpad and is not committed. **Unenforced** as a standing rule.

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The list below is
the closing agent's **recommendation for order, not a decision**. Do not expand beyond what the owner names.

1. **Land this branch first (if the owner agrees).** Check first: `gh pr list` and `git branch -a`. Then, in order:
   `python -m scripts.ci_wait <n>` (exit 0 only; 3 means green-after-retries, stop and look), `gh pr merge <n> --merge`,
   `git checkout main && git pull --ff-only`, regenerate the pointer with `print_handoff_pointer.py` and verify it with
   `check_handoff_pointer.py`, then `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 140, the owner's closure decision** (see "Decisions the owner owes"). No work is left on it.
3. **The wiki-obligation gate (C-11), if the owner wants it:** its own item, consumers of `scripts/gate.py` enumerated
   first (C-10).
4. **The app-side race**, if the owner wants it handled: a small branch, instrument first (record the digest before and
   after the draft in the real page), consumers enumerated first (C-10).
5. **Item 171, after the owner answers Q1 to Q4.** Instruments first: read the failing log of PR #127; trace whether
   `release.yml`'s `publish` job can run on `workflow_dispatch`; read the changelogs for the four Actions majors. Then the
   policy and the small `pull_request` workflow. Do the ruff bump on its own branch (`pyproject.toml:113`).
6. **File and look at `capture-smoke.yml`'s three failed scheduled runs** (cause not examined; by mechanism not the capture
   stall, because `--smoke` stops after Step 1).
7. **A checkpoint-advancing wiki pass** (65 of 75; due before the next wiki-relevant branch).
8. **Item 145's branch 2** (`feat/launcher`). Read item 0145's `## Updates` first. The first commit is an instrument (does a
   built wheel ship `alembic.ini` and `personas/cover_letter.html`? does the image's recall index build?). Ask the owner the
   questions listed above before any code.
9. **Open product bugs, agent-workable:** 130 (profile edits do not reach the AI), 105 (no education from corpus import),
   131 (a retired application cannot be found again), 107 (no account-naming step at first run), 134 (contradicting
   smoke-cost estimates), 139 (`capture_screenshots` leaves its demo user), 98 (wiki freshness measures
   checkpoint-staleness), 99 (`install.md` documents unpublished paths; depends on 3), 137 (a models and call-settings
   review).
10. **Remaining container checks and H2** if the owner picks them; the method is in
    `docs/dev/blast-radius/data-root.md` O10 to O13.
11. **Reopening item 164** if the owner picks it: instrument first.
12. **The *(owner)* items**, which need a decision before any branch.

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
