<!-- provenance: schema=1 session=58d32e9b-1980-4d63-87af-555f5fc2160e branch=docs/eval-redesign commit=3db3580 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-20 -->

# Agent handoff — eval redesign designed: gap map, scheme, dataset and OpenTelemetry research; item 137's A/B held; branch `docs/eval-redesign` → owner decisions, push (needs the owner's OK), PR, merge, prune

**Branch to create:** none chosen. When the owner has answered the eight decisions in `docs/dev/eval-redesign-design.md` section 8 and this
branch has landed, step 1 of that doc's build order (`feat/eval-record-identity`) is the first branch; it gets its own branch off `main`.
Do not start it before this branch is landed or the owner says otherwise.
**Base branch:** `main`

> **This session (`58d32e9b`) took item 137's A/B after the owner picked it** from the previous handoff
> (`docs-item-137-free-review.md`, pointer `@ main (96e870a)`, checked OK; `--event consumed` recorded, fingerprint `25644331cd19`; the ledger
> file `docs/dev/ledger/58d32e9b-1980-4d63-87af-555f5fc2160e.jsonl` is this branch's first commit, `d18e890`). The date is 2026-10-20 throughout.
> - **Owner decisions this session (chat):** next item = item 137's A/B; its four answers: pin `HAIKU_MODEL=claude-haiku-5-5`, suite full
>   synthetic (generate mode), N = 3, spend ceiling $12. Planning found the harness cannot answer the Haiku question, and the owner redirected:
>   map every gap (the agent leads); propose the one redesign worth doing before the public release, aligned with the principles and a model of
>   eval design for the owner's other projects; single, group and full runs; every model call evaluated and dashboarded with drill-downs; a
>   standard comparable dataset, ideally public and varied by profession and level, **never the owner's personal data**; consider OpenTelemetry;
>   take prompt-versioning and model-tracking designs from the owner's other work. The plan was approved through `ExitPlanMode`. At
>   close-out the owner chose to remove every mention of that other work from the committed files, and to push and open the PR. **Not
>   authorised this session: any merge, any paid call (none was made), any pin move, filing the build order as items or an epic.**
> - **Built (commits `d18e890` ledger; `3db3580` the design doc, item 137 update, changelog, wiki log, and one line in
>   `scripts/wiki_relevance.py` with its consumer dossier `docs/dev/blast-radius/eval-redesign.md`; the first full gate run had failed on
>   `test_every_top_level_entry_is_classified` with `assert not ['docs/dev/eval-redesign-design.md']`, and the line fixes it without changing
>   any classification):**
>   - `docs/dev/eval-redesign-design.md`, ten sections: what exists, the gap map, the principles, the scheme (a per-call eval catalog with
>     a gate that fails closed; single / group / full runs; a standard dataset; prompt content hashes and a producer id; a pre-registered
>     comparison with a noise floor and an arithmetic rule; a pinned, calibrated judge; telemetry and a Catalog dashboard tab with
>     drill-downs), the dataset research, the OpenTelemetry research, eight owner decisions, an eleven-step build
>     order, and what the doc does not verify. **Status: proposed; nothing in it is built.** Not registered in `scripts/doc_registry.py`, so
>     not published to the docs site, until the owner decides (decision 8).
>   - Item 137 `## Updates`: one new block recording the four answers, why the A/B is held, and the coverage finding. **Item 137 stays open.**
>   - `CHANGELOG.md` entry under Unreleased; `docs/wiki/log.md` entry recording `eval-harness` read for contradiction (verified no-edit) and
>     `llm-call-catalog` not re-read.
> - **What the gap map says (verified at source this session; the doc carries the cites):** of 21 product call kinds, 2 are scored on their own
>   output, 5 only through the finished document, 1 by an off-runner probe, **12 by no eval at all** (260 of 524 product rows);
>   `recommend_summary` cannot fire under the committed data (no LLM call below two summary variants, `analyzer.py:3978-3989`; the committed
>   seed has one). Judge rows are absent from the call log because judge logging merged after the last paid run (`2ae0dd7`), not because of a
>   fault. The avatar prompt is outside the eval path by an explicit comment (`analyzer.py:1192-1193`).
> - **Research findings, all *reported* by passes that used a summarizing fetch tool:** no public résumé dataset found is both redistributable
>   and broad; O*NET (CC BY 4.0) is the usable base for a synthetic matrix. The OpenTelemetry GenAI conventions moved to their own repository,
>   are "Status: Development", and have no release to pin.
> - **Gate:** `python -X utf8 -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished 2026-10-20T08:10:22-0700, HEAD 3db3580` (non-UX 3688 passed, 9 skipped; ux 189 passed, 1 xfailed, 1 xpassed, the nondeterministic xfail of watching item 62, where an earlier pass of the same code showed 2 xpassed; the log has 0 `RERUN` markers; run in Git Bash). **The first full run failed** at `pytest -m "not ux" -n auto` (1 failed, 3687 passed) on the wiki-relevance audit test; the fix is in `3db3580`. Three full runs in all: that failure, a pass on the pre-rebuild history, and this pass on the rebuilt `3db3580`. This handoff's commit moves HEAD, so `--result` reads **STALE** afterwards; that commit is documentation only and I did not re-run the full gate for it. CI (`ci_wait`) is the authority at PR time.
> - **Not verified:** (1) Everything marked *(reported)* in the design doc. (2) The dashboard's full view list and drill-downs (only `reasons`,
>   cache and per-kind figures were grepped). (3) Which Anthropic id `api_request_id` holds. (4) Dataset licences and the OpenTelemetry names
>   (re-read the primary pages before any decision relies on them). (5) The $0.30 one-call-per-kind figure is arithmetic on logged rows, with
>   two kinds unmeasured and judge calls excluded. (6) `--suite real` exiting 1 on the personal seeds (from code, not run). (7) Whether the
>   docs-site build accepts the new doc: it is unregistered, so the site does not include it; CI is the authority.
> - **Process notes:** the model changed after planning (planning ran as Opus 5.5; the build ran as Sonnet 5.5, which the stamp names). Seven
>   subagents ran (five Explore passes: the runner, the call inventory, the eval surfaces, the dashboard and earlier designs in the
>   owner's other work; two web research passes); all finished, none left running. The interrogative witness paused writes three times, twice re-armed by subagent
>   hand-backs (item 169). Scratch files (`make_handoff.py`, a witness-clear file) are in the session scratchpad, not committed. Three new
>   memory files and a `MEMORY.md` update were written (`feedback-evals-use-standard-dataset-never-personal`, `project-eval-redesign-direction`,
>   and a reference note on the other work's designs; the index lists them).
> - **Branch state at writing:** this branch is 3 commits ahead of `main` (`96e870a`): the ledger file (`d18e890`), the design
>   commit (`3db3580`), and the commit that adds this file. **The history was rebuilt before any push**, at the owner's direction to keep
>   removed material out of public history: the branch had held six commits, two of them carrying a section the owner then asked to remove.
>   A local backup branch, `docs/eval-redesign-pre-scrub`, still holds those six commits (never pushed); its tree differs from commit `3db3580`
>   only by the older version of this file, checked with `git diff --stat`. Delete it when the owner agrees. The gate result above is for `3db3580`. **Push:**
>   the owner confirmed the push and PR; they follow this commit, so check `gh pr list`. The added lines were scanned for machine paths
>   and the owner's personal seed name: none beyond one carried board line.

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

- Everything through `docs/item-137-free-review` ✓ (#193, merge `96e870a`, MERGED): item 137's free review.
- **`docs/eval-redesign`** ← this branch: the eval redesign, designed and written down; no code or pin changed.
- **Next, after the owner answers section 8 of the design doc: build step 1, `feat/eval-record-identity`** (prompt hashes and a version gate,
  producer id, trace / span / case ids, parse outcome, judge cost into run totals). Item 137's A/B is step 11 of that order, not the next branch.
  Other candidates: the rest of item 177; item 25's status; item 176; the six item 7 decisions; items 175, 140, 179's closure; item 178's
  mechanism; item 145's branch 2 and 3 (not started); item 171 (waits on four owner answers).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the owner's alpha approval.
**Do not run the candidate A/B, or any paid eval or capture, without the owner's spend approval** (the four A/B answers are recorded in item
137, but the run is held until the scheme exists; the $12 ceiling was stated for that run only).
**Do not move a pin** (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`). **Do not close items 175, 178, 179 or 137 on your own:** closing needs a
falsifiable `verified_by` or an owner-named `closure_exception`. **Do not build item 171's workflow before the owner answers its four questions.**
**Do not start item 145's branch 2 or 3.** **Do not delete any further memory file** without the owner's approval of the specific rows (item 7).
**Do not change the server's threading** (`app.py`) or item 25's status on your own. **Do not delete `evals/results/_test_stubs_quarantine/`**
without the owner saying so. **Do not change the `analyze_*` cache breakpoint** (Finding 2 in item 137): it is a behaviour change to
`analyzer.py` that needs its own branch and eval. **Do not build any step of the eval redesign, file its items, or register the design doc
for publication before the owner has answered section 8.**

---

## What just landed on `main`

**Nothing from this branch is on `main` as of writing.** `main` is at `96e870a` (PR #193, item 137's free review). Before it: #192
(`26e4f56`), #191 (`18dbc26`), #190 (`70a118f`), #189 (`74140b3`). If the PR below merged, `git log --oneline -3` on `main` shows it.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. Header, read from the board at `3db3580`: **Open 24 / 10 ceiling -- OVER** | Blocked 4 | Deferred 9 | Watching 45 | Epics 6 | Closed 92

**Changes from the previous handoff:** none to the board: this session filed **no new item** (it would have raised an OVER count) and closed
none. Item 137's `## Updates` gained one block. The owner's drawdown direction stands: down to 0 if possible, before alpha staging. Still more
than twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked *(owner)*. **The lists below are the previous handoff's,
copied by script** (`make_handoff.py` in the session scratchpad, not committed); the board header above was read from `BOARD.md`, the entries
were carried, not re-derived.

`## Open` (22):
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
- **179**: A test writes stub eval runs into the real evals/results/: 337 of 425 files. Fixed on this branch; owner closes.

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

- **The eval redesign, `docs/dev/eval-redesign-design.md` section 8 (new, eight decisions; the doc has the context for each):** (1) the
  dataset: an O*NET-based synthetic matrix, a public set fetched on demand, or both; (2) whether v1.1.0 waits for build steps 1 to 3 (my
  recommendation: yes, plus a deterministic-check eval on every kind); (3) the judge model; (4) OpenTelemetry: no dependency or
  `opentelemetry-api` as an optional extra, and whether to pin to a commit; (5) one-time human labels for judge calibration; (6) the avatar
  prompt: keep it out of the eval path or bring it in; (7) epic or items for the build order (the board is OVER); (8) publication: register the
  doc in `scripts/doc_registry.py` for the docs site, or keep it repo-only.
- **Item 137, what is left (updated):** the A/B itself (step 11 of the build order, pre-registered on the full run with the four answers
  already recorded); the subagent pins (`agents/*.md`, after the product decision); Opus 5.5 price and policy (only if a product call is ever
  added); how soon to move off Haiku 4.5 (past its earliest retirement date, still Active, no notice listed; it is also the eval judge and two
  subagent pins); the stale "no Haiku 5" sentence in `CHANGELOG.md`'s 2026-07-05 entry (a dated record, not edited).
- **The `analyze_*` user-prefix breakpoint (new, Finding 2):** cents over five months, written for a `generate` that rarely follows in
  product. Drop it on product synthesis, keep it, or leave it? A behaviour change in `analyzer.py` with its own branch and eval.
- **`commands/bench.md:20` (new):** it describes six call-log fields no row carries yet (they start appearing with the next logged call).
  Edit the line, or leave it until rows exist?
- **Sonnet 5.5 cache-read price (new):** `hardening.py:471-477` $0.10 per million (pricing page footnote, re-read 2026-10-19 by the earlier
  session) against $0.20 in the `claude-api` skill's cached table. Re-fetch the pricing page to settle it before the A/B compares dollars?
- **The 89 top-level result files (new, replaces "the 88"; owner's call):** none was verified to be a real paid run. Worth checking before they seed the A/B baseline?
- **Item 179, close or keep open (new):** needs a `verified_by`: the regression test
  `tests/test_eval_runner.py::TestRunSuite::test_run_suite_default_out_dir_follows_patched_results_dir` and the `pytest_sessionfinish` check in
  `tests/conftest.py`. Keep open if you want the check shown to fire under `-n auto` first.
- **The 337 quarantined files (new):** delete `evals/results/_test_stubs_quarantine/` whenever you do not want them; nothing reads it.
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

### Declared, not filed — carried unchanged from the previous handoff; this session re-verified none of it (any 'this session' wording in the bullets below refers to the previous session)

The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it, `docs/dev/handoffs/dependabot-triage-item.md` and `docs/dev/handoffs/data-root.md` "Carried from earlier handoffs" (about 40 bullets). Not re-copied.

- **`maintainer-lane.md` §"Starting a session from a handoff" step 2 gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.** Re-observed this session: the bare name returned `template not found: AGENT_HANDOFF_TEMPLATE.md under the repo root`, exit 2. The previous handoff warned about it and the maintainer-lane text is unchanged. See the recurrences section. Not fixed (outside item 137's scope).
- **(Resolved, observed this session: `git branch -a` no longer lists them.) Two merged remote branches were reported:** `origin/chore/wiki-checkpoint-pass` (PR #189) and `origin/fix/llm-call-provenance` (PR #188), though the close-out text says the remote copy is auto-deleted on merge. Seen in `git branch -a` at session start; cause not examined (a stale remote-tracking ref without `fetch --prune`, or the repo's delete-on-merge setting being off, are both untested).
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01); cause not examined. `release.yml` and `docker.yml` have no workflow runs at all (item 171).
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (not a registered worktree), and a git stash `stash@{0}` that belongs to another session. Neither touched. Not re-checked this session.
- `origin/fix/eval-results-test-leak` still appeared in `git branch -a` after PR #192 merged (observed this session); cause not examined (a stale remote-tracking ref without `fetch --prune`, or delete-on-merge off).
- `scripts/check_docs_site_mermaid.py` reads a prebuilt `docs-site/out/` and does not check that it is current (see the recurrences section). The `docs-site/out/` on this machine is dated 2026-10-01.

---

## Recurrences observed this session → guardrail authored

1. **A figure carried from a subagent's summary became a premise in my own plan** (I wrote "22 product call kinds"; the pass's summary said
   23, its own table had 21, and the 23 counted two judge kinds): a known class (C-12, an unverified report becoming a premise). Caught by
   counting `call_kind` literals at the send sites and reading `EXPECTED_CALL_KINDS` (`tests/test_call_kind_telemetry.py:74`). **No mechanism
   authored on this branch; unenforced.** The design's catalog gate (build step 2) would make the count mechanical; until then the design doc
   labels every unread figure *(reported)*. Stated so the gap is not counted as protection (C-11).
2. **A requirement not checked before I offered a choice** (I listed the owner's personal seed as an eval seed option; the owner said it is
   not a standard dataset and not a good idea): a known class (an option offered without checking it meets the stated requirement). A
   feedback memory records it (`feedback-evals-use-standard-dataset-never-personal`). **A memory is not a mechanism, and no mechanism is
   possible for a conversational choice; unenforced.** Said to the owner when it happened.
3. **A log entry that claimed more than I had read** (the wiki log said a second page was "checked"; I had only read the first, and I wrote
   "two days earlier" for a same-day correction): the scope-word class the previous handoff recorded. Caught on re-read before commit and
   corrected. No mechanism; a re-read is not one. **Unenforced.**
4. **The interrogative witness re-armed by subagent hand-backs** (known: item 169): three pauses, each cleared by re-running or by a write
   to the scratchpad. Nothing new authored.
5. **The `maintainer-lane.md` template-path trap** (bare `AGENT_HANDOFF_TEMPLATE.md`): avoided by using `docs/dev/AGENT_HANDOFF_TEMPLATE.md`
   from the previous handoff's warning; the doc line is still not fixed. **Unenforced.**
6. **A new loose `docs/dev/*.md` must be classified in `scripts/wiki_relevance.py`** (a gated surface, so also a dossier): a known trap,
   already written down in item 7 (`:177-178`) and `docs/dev/epic-a-chain-design-corrections.md:262`, and it hit this branch anyway. The
   mechanism is the audit test, and it **did fail closed** (`tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`),
   but only 5 minutes 35 seconds into the first full gate run, because the `doc-writing` skill's lint step does not run it. The residual
   cost is that late detection. **A cheaper mechanism is possible and not built:** add the test to the skill's step 6 command list, or a check
   to `scripts/doc_lints.py`. It is outside this branch's scope; surfaced to the owner here. Also a slip of mine, corrected: I named the
   dossier `docs-eval-redesign.md` (the handoff-slug form), the guard looks for the branch name minus its `<type>/` prefix
   (`eval-redesign.md`), and it blocked the edit until I renamed it.
7. **Material about the owner's other work written into public-bound docs before asking** (I wrote a section on a sibling project into the
   design doc and commits, listed "may it name this" as an owner decision, and only then asked; the owner chose removal, which also meant
   rebuilding the unpushed history): a known class, recorded in the memory `feedback-external-ventures-out-of-scope` ("sweep before
   committing"), which I had read earlier in the session. **No mechanism authored; unenforced.** A mechanism is possible and I did not
   build it: a gate over tracked files against a denylist of private project names. It would conflict with mentions already public on
   `main`, so it needs the owner's decision on which names are private. Surfaced to the owner here.

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses; this list is the closing agent's **recommendation for order, not a decision.**

1. **Land this branch first if it is not already landed.** Check `gh pr list` and `git branch -a`. The owner confirmed the push and PR
   this session; **a merge is not authorised**: wait for the required checks with `python -m scripts.ci_wait <n>` (exit 0 only; 3 means
   green-after-retries, stop and look), get the owner's explicit confirmation, then `gh pr merge <n> --merge`, `git checkout main && git pull
   --ff-only`, regenerate and check the pointer, `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **The owner answers section 8 of the design doc**, then chooses epic or items for the build order. Do not file either before that.
3. **Build step 1, `feat/eval-record-identity`**, when the owner approves: prompt content hashes and a gate that fails when a hash changes
   and `PROMPT_VERSION` does not (turns `docs/governance/enforcement.md:127` from convention into a mechanism); producer id; trace, span and
   case ids; parse outcome; judge cost into run totals. `analyzer.py` and `hardening.py` are not on the C-10 gated list, but the call-log
   row and the eval record have consumers (the dashboard, `commands/bench.md`, `evals/tune.py`): enumerate them first and write a dossier.
4. **Item 177 points 12 and 13, then 2 to 11**; **item 25's status**; the remaining item 7 decisions; items 175, 140, 178, 179's closure.
5. **Item 176**, when the owner wants the 44 fold-ins done (re-verify each fact before writing it).
6. **The `maintainer-lane.md` template-path line**, if the owner wants it fixed; a few lines.
7. **Carried, in the previous order:** the wiki-obligation gate (C-11); the handoff-ledger-vs-board check; the app-side race; item 171 after Q1
   to Q4; `capture-smoke.yml`'s three failed scheduled runs; item 145's branch 2; the open product bugs 130, 105, 131, 107, 134, 139, 98, 99;
   the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (**the template path is `docs/dev/AGENT_HANDOFF_TEMPLATE.md`**, not the bare name
`maintainer-lane.md` gives), then check `gh pr list` and `git branch -a` for this branch's PR and merge state (this file may predate it). Then ask which
item to take. Create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do not code first.**

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
