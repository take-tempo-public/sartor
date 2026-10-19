<!-- provenance: schema=1 session=75747747-7b68-46dd-815a-e00253f2b2a3 branch=feat/model-override-candidate-quarantine commit=3e89b5e actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-19 -->

# Agent handoff — item 137: a model override for candidate runs is built, and candidate runs are now really kept out of the baseline; branch `feat/model-override-candidate-quarantine` → push (needs the owner's OK), PR, merge, prune, then the owner's next pick

**Branch to create:** none chosen. The owner picks the next item. The candidates are under "What this branch should build"; the
order there is a recommendation, not a decision. Do not start one unprompted.
**Base branch:** `main`

> **This session (`75747747`) took item 137's remainder after the owner picked it** from the previous handoff (`thinking-policy-55-pricing.md`,
> pointer `@ main (70a118f)`, checked OK; `--event consumed` recorded, fingerprint `73aa9d90cc85`; the ledger file
> `docs/dev/ledger/75747747-7b68-46dd-815a-e00253f2b2a3.jsonl` is this branch's first commit, `a4ee842`). Dates are the UTC date (2026-10-19).
> - **Owner decisions this session (chat):** item 137's remainder, starting with the model-override question (from a list of four); scope "Build it"
>   over "Design only"; model candidates attributed with "New record field" (not a folded `candidate:` hash); then, after I showed that prompt candidates
>   were never excluded, "One filter, both kinds" (over "model only; file the gap"); the plan was approved through `ExitPlanMode`; the wiki spend was
>   authorised at the step-2 gate ("Authorize", 5 pages); and "Commit it" for the wiki diff. **Not authorised this session: any push, PR or merge**
>   (the previous session's authority does not carry over). **No paid call was made.**
> - **Built (commits `33a8ad0`, `d1c6ce0`, `6c83d13`, `6d1bf77`, `3e89b5e`):**
>   - `analyzer.model_overrides()` (+ `active_model_overrides()`, `_resolve_model`, `_validate_model_override`): sends a candidate model in place of
>     `SONNET_MODEL` / `HAIKU_MODEL` for one run, resolved **by value** at the one product send site (`_call_llm_streaming`). It raises `ValueError` before
>     anything is sent for an unknown pin, a target equal to its pin, or a target with no `THINKING_POLICY` or `MODEL_PRICING` entry (Opus 5.5 today).
>     The judge (`client.messages.create`, `JUDGE_MODEL`) never reaches that site, so it stays fixed. An overridden call-log row carries `pinned_model`;
>     ordinary rows are unchanged.
>   - `evals/runner.py`: `--model-override PIN=ID` (repeatable), `run_suite(model_overrides_map=...)`, every record carries `model_overrides` (only when
>     active) and the models actually sent in `model_snapshots` (`_model_provenance_fields`).
>   - **`hardening.is_candidate_record` / `CANDIDATE_VERSION_PREFIX`**: the one definition of "not a baseline record" (a `candidate:` prompt version OR a
>     non-empty `model_overrides`). `_load_baseline_scores` and the dashboard's pass rate, score-over-time, heatmap, failure modes, baseline health and
>     groundedness views skip such records; the Pareto scatter shows them as their own series (`<version> · SONNET_MODEL→<id>` for a model candidate), and
>     its trajectory, summary and trend lines use baseline versions only. `_score_over_time` reports them in a new `candidate_records` count.
>   - Docs, help text and a CHANGELOG entry corrected to say what the code does; five wiki pages edited (scoped pass).
> - **Finding that changed the scope (read from the code, not reproduced as a user-visible bug):** the documented "candidate runs never pollute
>   score-over-time" was **false**. Nothing excluded a `candidate:<hash>` run: it was the next run's regression "prior run", the heatmap cell, and could
>   flip the baseline-health badge. `AGENTS.md`, `evals/README.md`, the dashboard help text, two slash commands and five wiki pages said otherwise.
> - **Deviations from the approved plan (all disclosed in the dossier):** (1) the predicate lives in **`hardening.py`**, not a new `evals/candidates.py`:
>   `pyproject.toml` packages `dashboard*` but not `evals*`, so a module-level import of an `evals` module in `dashboard/routes.py` would break an
>   installed wheel; `analyzer` now builds the `candidate:` label from the same constant, so the two cannot drift. (2) The latency/cost trend lines are
>   baseline-only (the plan said candidates stay in them); a candidate on a time axis reads as the next chronological change. (3) `_per_rubric_pass_rate`
>   and `_failure_mode_frequency` also skip candidates (the plan listed fewer views). (4) The plan said to tighten `tests/test_dashboard_routes.py:72-99`; the
>   Explore subagent had reported it pinned candidate points, but **I read it and it does not**, so new tests were added instead (the dossier says so).
> - **Evidence (fail-before):** `tests/test_model_overrides.py` run against an unchanged `HEAD` in a detached worktree (removed after): **21 failed, 3 passed**
>   (the 3 are the default-path tests, which must pass on old code). The 17 new dashboard tests failed on the unchanged dashboard (**17 failed, 80 passed**
>   before the fix). **I did not run `tests/test_candidate_records.py` or the new `TestCandidateRuns` cases in `tests/test_eval_runner.py` against the old code.**
> - **$0 live check:** `python evals/runner.py --suite synthetic --subset smoke --model-override SONNET_MODEL=claude-opus-5-5` exited **1** with the
>   `THINKING_POLICY` error; `logs/llm_calls.jsonl` stayed at 1564 lines and `evals/results` at 426 files. `--model-override SONNET_MODEL` (malformed) exited 1.
> - **Gate:** the first run **FAILED at `mypy .`** (`dashboard/routes.py:514`, `min()` over `Any` returned from a function declared `str`; mine: I had run
>   `ruff` and `pytest` but not `mypy` before committing). The harness reported that background run as "exit 0"; `python -m scripts.gate --result` read FAILED.
>   Fixed in `3e89b5e`. Re-run: `python -X utf8 -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished
>   2026-10-19T12:19:29-0700, HEAD 3e89b5e` (non-UX 3687 passed, 9 skipped; ux 189 passed, 2 xpassed; the log has 0 `RERUN` markers). This handoff's commit
>   moves HEAD, so `--result` reads **STALE** afterwards; I did not re-run the full gate for a docs-only commit.
> - **Wiki:** scoped pass over this branch's diff (10 wiki-relevant paths), `.last_ingest_sha` **not advanced** (still `619549a`). 5 pages edited, `index.md`
>   two one-liners, `docs/wiki/log.md` entry. Cite check: first run failed E1 on 3 pages (the scribes added 5 bare line cites against the brief), fixed, then
>   OK. Auditors: changed hunks 33 SUPPORTED / 0 / 0; they also caught a stale quoted warning text, a too-narrow heading and an incomplete validation
>   sentence outside the hunks; the corrected hunks were re-audited by two fresh auditors, 13 SUPPORTED / 0 / 0. My own review caught one more
>   (`eval-harness` still said later-timestamped records always win the baseline). Declared in the log: the other 24 pages were not audited.
> - **Not verified:** (1) **No overridden request has ever reached the real API**: every test uses a duck-typed client. That `between_tools` is accepted by
>   Sonnet 5.5 is item 173's recorded probe, not re-run. (2) The dashboard was **not opened in a browser**; the template edits (help strings and the
>   `candidate_records` note) are covered only by the existing render tests (97 dashboard tests pass), not by a render with candidate data in it.
>   (3) The ContextVar does not cross threads; the eval path has none today (`ThreadPoolExecutor` / `threading.Thread` grep over `analyzer.py` and
>   `evals/*.py`: no hits), so a future parallel `run_suite` would silently lose the override (the same limit `prompt_overrides` has). (4) The wiki pages
>   were audited on the changed hunks, not end to end (except `prompt-version-discipline`).
> - **Process notes:** the interrogative witness paused the first `Edit`/`Write` after **every batch of subagent hand-backs** (three times) and I re-ran each
>   as designed (item 169's class). The long-command guard blocked two Bash calls (over 7,162 characters); I wrote the scripts with the Write tool and ran them
>   by path. `verify-binary-on-path` blocked a bare `ruff`; `python -m ruff` is the way. The model changed mid-session (planning ran as Opus 5.5; the
>   build ran as Sonnet 5.5, which the stamp names). Two python processes (PIDs 27284, 25268, started 11:29, `isidium.store.client.cli mcp`) are this
>   session's `isidium-store` MCP server, not something I started; left running. I started no dev server.
> - **Branch state at writing:** this branch is 7 commits ahead of `main` (`70a118f`): the ledger file, the primitive (with its dossier), the runner,
> the dashboard and docs, the wiki, the mypy fix, and the commit that adds this file. **Not pushed.** `git branch -a` and `gh pr list` show how far it got.

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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging (owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- Everything through `feat/thinking-policy-55-pricing` ✓ (#190, merge `70a118f`, MERGED): item 137's free part. Record: `docs/dev/handoffs/thinking-policy-55-pricing.md`.
- **`feat/model-override-candidate-quarantine`** ← this branch: item 137's model-override mechanism and the candidate-run exclusion, built and gated.
- **Next: the owner's pick.** Item 137's remainder (below); the rest of item 177 (points 2 to 13); item 25's status; item 176; the six remaining item 7 decisions; item 175's and item 140's closure; item 178's mechanism; item 145's branch 2 and 3 (not started); item 171 (waits on four owner answers).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the owner's alpha approval.
**Do not run the candidate A/B, or any paid eval or capture, without the owner's spend approval** (none is approved; the override mechanism does not change that).
**Do not move a pin** (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`): that is the A/B's outcome, one swap per branch. **Do not close items 175, 178 or 137 on your own:**
closing needs a falsifiable `verified_by` or an owner-named `closure_exception`. **Do not build item 171's workflow before the owner answers its four questions.**
**Do not start item 145's branch 2 or 3.** **Do not delete any further memory file** without the owner's approval of the specific rows (item 7). **Do not change the
server's threading** (`app.py`) or item 25's status on your own. **Do not "fix" the 17 remaining bare line cites or build a wiki-cites content check unprompted** (item 178).

---

## What just landed on `main`

**Nothing from this branch is on `main` as of writing.** `main` is at `70a118f` (PR #190, item 137's thinking policy and 5.5 prices). Before it: #189 (`74140b3`,
the checkpoint-advancing wiki pass), #188 (`855b551`, item 175), #187 (`72d2ff9`, item 177 point 1), #186 (`f32475c`, item 7).
If the PR below merged, `git log --oneline -3` on `main` shows it.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. Header, read from the board at `3e89b5e`: **Open 23 / 10 ceiling -- OVER** | Blocked 4 | Deferred 9 | Watching 45 | Epics 6 | Closed 92

**Changes from the previous handoff:** none to the counts; item 137's `## Updates` gained the 2026-10-19 model-override entry (what was built, the
finding that candidate runs were never excluded, what stays open). The owner's drawdown direction stands: down to 0 if possible, before alpha staging.
Still more than twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked *(owner)*.
**The lists below were rendered from `BOARD.md` by script in this session** (`make_handoff.py` in the session scratchpad, not committed), not copied from the
previous handoff.

`## Open` (21):
- **7** *(owner)*: Memory consolidation: 85 deleted, 16 trimmed, 12 merged, index rebuilt; further deletions await owner approval.
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
- **137**: Review pinned models and call settings, now including the Claude 5.5 candidate evaluation (absorbs item 173).
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Fix built, measured, screenshots recaptured; score drop not specific to the change; carrier hypothesis never reproduced.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **171** *(owner)*: 16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy.
- **175**: Built (fix/llm-call-provenance): rows record answering model, request id, settings; judge calls logged. Owner closes.
- **177**: Sweep found a threaded-server contradiction, a wrong gate.py item path, README min_* claims and stale counts.

`## Blocked` (4):
- **3** *(owner)*: Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5**: First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** *(owner)*: Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [depends on: 6] [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run]
- **97** *(owner)*: Orchestration may belong outside the project; sartor's job becomes keeping ARC/CHECKLIST/ledger/BOARD in sync. [blocked on: owner design decision — this is a strategic redirect the owner raised; the tool choice and the scope of any sync layer are the owner's]

`## Deferred` (9):
- **4** *(owner)*: Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet. [blocked on: no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants]
- **24** *(owner)*: In-app preview is single-column (python-docx limit); multi-column/paging fidelity needs a spike, never scheduled. [blocked on: not yet scheduled; needs a product-priority decision on investing in the spike before any code work starts]
- **25** *(owner)*: Single-threaded app.run() freezes the app during a diagnostics run; making it threaded is an owner-gated C-1 call. [blocked on: owner governance call not yet made; touches the C-1-sensitive loopback-bind area, deliberately kept out of the diagnostics epic and every branch since]
- **41** *(owner)*: Local lexicons (design, SWE, business, startup) so Compose drafting uses the JD domain's language and conventions. [blocked on: post-1.1.0 - owner scheduled this for 1.1.x investigation, not the Final March]
- **42** *(owner)*: Investigate dotx/mht as import formats and lock a small set of bullet-proof ATS templates with exact-preview fidelity. [blocked on: post-1.1.0 - owner scheduled a template epic for a 1.1.x sprint]
- **43** *(owner)*: v1.1.0 ships an approved-fonts list of Arial, Calibri, Georgia (sprint B2); verified additions considered later. [blocked on: post-1.1.0 - additions only after per-font ATS verification, owner-gated]
- **113** *(owner)*: 18 console UX findings outside Epic C (6 major, 12 minor) await triage; UX-22 is item 112; UX-24 joined C1b. [blocked on: owner triage after Epic C lands: which findings become items, which fold into a later epic, which are dropped]
- **114**: bench.md already summarizes error rows generically; naming error_message/error_type explicitly is a nice-to-have. [blocked on: low value until logs/llm_calls.jsonl accumulates real status="error" rows with the new fields; revisit once there is real data to summarize]
- **176** *(owner)*: 44 memory files hold facts with no repo home, plus leftovers of 69 deleted ones; fold them into docs. [blocked on: owner chose on 2026-10-18 to defer these 44 fold-ins to a later session; nothing here is started]

`## Watching` (45):
- **2**: ~107-file wiki + reviews-archive wordmark cleanup deliberately deferred to opportunistic fold-in, not a branch.
- **16** *(owner)*: No jd.txt/expected.json under evals/fixtures/real/ anywhere in this project - --suite real exits 1, zero LLM spend.
- **18**: Same fixture, 68s apart: tone 3.2->2.1, clarification_quality 3.2->3.8, composite 4.06->3.89 - n=2, uncharacterized.
- **23** *(owner)*: PX-52, WATCH: extract prompts.py/client.py when prompt work next opens the file, not a standalone refactor.
- **46**: Control assertion (`assert naive`) is itself a timing race; a quiet runner completes write_text between reader polls.
- **47**: Item 44's fix landed in one shared helper; other tests reasoning about spy events after a clear were not audited.
- **48**: ux job took 14m49s on PR #102 vs ~5m1s on PR #100 — zero reruns, so not a flake; the runtime is the anomaly.
- **49**: A suite run leaves personas/bundled/tmp*.html behind; `git add -A` swept one into a commit before it was caught.
- **51**: flake_rates.py is an instrument, not a gate; report --check against a committed budget is a named, unbuilt successor.
- **52** *(owner)*: The tree that lands is never the tree the gate examined; class study documents 6 instances + candidate mechanisms.
- **53**: Quote-parity tracker ignores heredoc semantics; prose quotes in a commit-message heredoc caused a live false-BLOCK.
- **56** *(owner)*: On main the reconciler dies mid-function: empty archive dir, all three pointers survive, stale approval stays live.
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
- **178**: wiki_cites passed 4 line cites that no longer pointed at their claim; 17 bare line cites remain allowed.

`## Epics` not closed (3):
- **19** (open): UX-suite flakiness solution sprint - mode-C residual + newly observed instances
- **36** (open): Final March epic A - main-app function + UX
- **40** (blocked): Final March epic E - the public v1.1.0 cut

### Decisions the owner owes (collected; each is also in the item it belongs to)

- **Item 137, what is left (rewritten this session):** (1) the **candidate A/B**, one swap per branch with the judge held fixed, N chosen in
  advance (the `data-scientist-junior` fixture is bimodal): needs a spend approval, none given. **The mechanism now exists**:
  `python evals/runner.py ... --model-override SONNET_MODEL=claude-sonnet-5-5`; the owner chooses the pin, the suite/subset and N.
  (2) The **routing review** per call kind, the cache hit rate (`/sartor:bench`) and output limits. (3) The **subagent pins** (`agents/*.md`),
  after the product decision. (4) **Opus 5.5** price and policy, only if a product call is ever added (`--model-override` refuses it today).
  (5) **How soon to move off Haiku 4.5** (past its earliest retirement date, still Active, no notice listed; it is also the eval judge and two
  subagent pins). (6) The stale "no Haiku 5" sentence in `CHANGELOG.md`'s 2026-07-05 entry is a dated record: not edited.
- **Model override on the console route (new, owner's call):** `POST /api/tune/run` (`blueprints/diagnostics.py`) takes no model override; the
  flag is CLI-only. Wanted in the browser, or is the CLI enough for the A/B?
- **`_load_baseline_scores` ignores `eval_mode` (new, not touched):** an assemble-mode run still seeds a generate-mode run's baseline. A
  different population problem from candidates; file as an item, or leave?
- **A gate for "every baseline view skips candidates" (new, C-11, owner's call):** nothing enumerates the dashboard's aggregations, so a NEW
  baseline view that forgets `is_candidate_record` would pass every test. A test that walks the aggregation functions is possible; not built.
- **`LLMConfigurationError` for an unlisted model (new, owner's call):** it fails closed, but the type's name and message read as a credential problem. A dedicated subclass or a plain `ValueError` would be clearer; the cost is the 19 handlers keyed on `LLMResponseError`. Not changed.
- **Item 178, which mechanism, if any (carried):** the cite check passes a line cite whose content moved; 17 bare line cites remain allowed. Not built.
- **Item 65, the class (carried):** the counter will re-diverge on the next scoped pass.
- **Item 168 (carried):** one full-window data point for the Sonnet auditor, no Haiku comparison and no per-call cost.
- **Item 175, close or keep open (carried):** needs a `verified_by` (the probe re-run in `docs/dev/diagnosis/llm-call-provenance.md` plus the two new test files) or a `closure_exception`. Follow-ons D-2 and D-4 in its blast-radius dossier are not filed.
- **Item 140, close or keep open (carried):** the original `b180` carrier has not reproduced in 31 letters.
- **The Pipeline tab mixes eval and product spend (carried):** `dashboard/routes.py` filters only by date, user and model. Product question, not filed.
- **Item 25 (carried):** its premise ("single-threaded `app.run()` freezes the app") is false; the server is threaded. Stay deferred, close, or become a new item for the freeze itself (never observed)?
- **Item 177, points 12 and 13 (carried):** 12 is the unaudited production exposure of the optimistic context read to the Windows `PermissionError`; 13 is the false "a real `POST /cancel` couldn't be serviced" rationale. Points 2 to 11 are untouched.
- **Item 7, six remaining decisions (carried):** the 12 merged files; the 15 draft-list FOLD files; the 2 PARTIAL rows; batches C and D (24 files); whether to apply the sweep's STALE flags; closing item 7 and deleting `memory-backup-2026-10-18`.
- **Item 176 (deferred by the owner):** the 44 fold-ins and the 26 unhomed leftover lines. Nothing started.
- **The app-side race (carried, not fixed):** a Save-and-continue during an in-flight arrival draft can lock Generate behind "You changed your composition after approving it". C-10 territory.
- **Item 171, Q1 to Q4 (carried):** auto-merge for the auto classes; the 2026-08-07 docs-site alert carve-out; the four Actions majors before the tag; a merge queue or the squared CI cost under `strict: true`.
- **The `EnterWorktree` question (carried):** may agents use the harness worktree location inside the repo?
- **Item 145, branch 2's start (carried):** the C-2 wording, the PEP 668 fallback, whether bare `sartor` runs `up`, whether `sartor` is free on PyPI, separate native and container data.
- **Item 10 and the alpha (carried):** item 3 (GitHub toggles), item 7, and the owner's alpha approval.
- **Whether to file a gate for the per-branch wiki obligation (carried, C-11):** possible, not built; it changes `scripts/gate.py`, a C-10 gated surface.

### Declared, not filed — carried; this session re-observed the first two and did not re-verify the rest

The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it, `docs/dev/handoffs/dependabot-triage-item.md` and `docs/dev/handoffs/data-root.md` "Carried from earlier handoffs" (about 40 bullets). Not re-copied.

- **`maintainer-lane.md` §"Starting a session from a handoff" step 2 gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.** Re-observed this session: the bare name returned `template not found: C:\Dev\sartor\AGENT_HANDOFF_TEMPLATE.md`, exit 2. The previous handoff warned about it and the maintainer-lane text is unchanged. See the recurrences section. Not fixed (outside item 137's scope).
- **Two merged remote branches still exist:** `origin/chore/wiki-checkpoint-pass` (PR #189) and `origin/fix/llm-call-provenance` (PR #188), though the close-out text says the remote copy is auto-deleted on merge. Seen in `git branch -a` at session start; cause not examined (a stale remote-tracking ref without `fetch --prune`, or the repo's delete-on-merge setting being off, are both untested).
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01); cause not examined. `release.yml` and `docker.yml` have no workflow runs at all (item 171).
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (not a registered worktree), and a git stash `stash@{0}` that belongs to another session. Neither touched. Not re-checked this session.

---

## Recurrences observed this session → guardrail authored

1. **A documented invariant the code did not enforce** ("candidate runs never pollute score-over-time", stated in six places): the class C-10 warns about
   (a hand-maintained claim that rots) and a C-0 violation. **Mechanism authored:** `hardening.is_candidate_record` as the single definition,
   `TestCandidateRecordsAreNotBaseline` (parametrized over both candidate kinds, one test per baseline view) and `TestCandidateRuns`, and
   `tests/test_candidate_records.py` (the `candidate:` label and the filter share one constant). **Known limit (C-0), unenforced:** a NEW baseline view added
   later that forgets the predicate is not caught; nothing enumerates the aggregations (offered above as a decision).
2. **A subagent's unverified report taken at face value** (the Explore report said an existing test pinned candidate points): the class C-12 and
   `reference-conductor-verify-lanes` describe. Caught because I read the test before writing "tighten" into the plan. **No mechanism authored; unenforced.**
3. **A gate failure hidden by the background wrapper** ("exit 0" on a run that failed at `mypy`): the known class in `maintainer-lane.md` step 1. The existing
   guardrail (`python -m scripts.gate --result`) is what caught it. Nothing new.
4. **Committing without running the full gate's steps** (`ruff` and `pytest` ran, `mypy` did not): the gate caught it and failed closed. The pre-commit hook
   (`ruff-changed`) runs ruff only. **No new mechanism: the gate is the closed backstop; a pre-commit mypy would be new and costly.** Unenforced locally.
5. **Scribes ignoring "symbol cites only"** (3 of 5 pages, 5 bare line cites) and leaving one named stale sentence untouched: the existing cite check (E1) and
   the review step caught them. The three layers held; no change.
6. **The interrogative witness re-arming on subagent hand-backs** (item 169, again, three times): re-run as designed; no new data.
7. **The `maintainer-lane.md` template-path trap** (bare `AGENT_HANDOFF_TEMPLATE.md`): avoided by using `docs/dev/AGENT_HANDOFF_TEMPLATE.md`; the doc line is still
   not fixed (outside this branch's scope). **Unenforced.**

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The list is the closing agent's **recommendation for
order, not a decision.** Do not expand beyond what the owner names.

1. **Land this branch first if it is not already landed.** Check `gh pr list` and `git branch -a`. **The owner has not authorised the push this session**:
   state what becomes public (the commits listed under "Branch state", plus anything on local `main` the remote lacks) and get explicit confirmation, then:
   `git push -u origin feat/model-override-candidate-quarantine`, `gh pr create`, `python -m scripts.ci_wait <n>` (exit 0 only; 3 means green-after-retries,
   stop and look), `gh pr merge <n> --merge`, `git checkout main && git pull --ff-only`, regenerate and check the pointer, `git branch -d`.
   Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 137's remainder** (the list under "Decisions the owner owes"). The first A/B needs three owner answers: the pin, the suite/subset and N, and the
   spend. Then it is `--model-override SONNET_MODEL=claude-sonnet-5-5` against a baseline run on the same fixtures with the judge unchanged.
3. **Item 177 points 12 and 13, then 2 to 11** (point 12: audit which routes read a context file outside `context_transaction`; instrument first, since the
   production exposure is unobserved).
4. **Item 25's status**, then the remaining item 7 decisions, then closing item 7. **Items 175, 140 and 178** (above).
5. **Item 176**, when the owner wants the 44 fold-ins done (re-verify each fact before writing it).
6. **The `maintainer-lane.md` template-path line and the stale remote branches** (above), if the owner wants them fixed; each is a few lines.
7. **Carried, in the previous order:** the wiki-obligation gate (C-11); the handoff-ledger-vs-board check; the app-side race; item 171 after Q1 to Q4;
   `capture-smoke.yml`'s three failed scheduled runs; item 145's branch 2; the open product bugs 130, 105, 131, 107, 134, 139, 98, 99; the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (**the template path is `docs/dev/AGENT_HANDOFF_TEMPLATE.md`**, not the bare name `maintainer-lane.md` gives), then check `gh pr list` and
`git branch -a` for this branch's PR and merge state (this file may predate it). Then ask which item to take. Create that branch off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code first.**

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
