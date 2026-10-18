<!-- provenance: schema=1 session=8603d643-9c25-422e-bcbf-78e4bf0a1ae4 branch=fix/model-pricing-rates commit=3bf3476 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-17 -->

# Agent handoff — item 174 fixed (MODEL_PRICING now matches the pricing page), item 175 filed (trace every call to its model version and settings), memory consolidation (item 7) directed for the next session; branch `fix/model-pricing-rates` → owner's next pick

**Branch to create:** none chosen. The owner picks the next item. The two the owner has already directed are under "What this
branch should build" (items 7 and 175); the order there is a recommendation, not a decision. Do not start one unprompted.
**Base branch:** `main`

> **This session (`8603d643`) took item 174 after the owner picked it from the previous handoff.** It fixed the price table,
> filed item 175 at the owner's instruction, recorded the owner's memory-consolidation direction on item 7, and changed no
> prompt text. It made **no paid API call** (the pricing page was read with `WebFetch`; the two telemetry rows were costed
> from the existing local log). Everything is on `fix/model-pricing-rates`.
> - **Item 174 (closed, with `verified_by`):** `hardening.py:446-` priced `claude-sonnet-5` at `$3/$15` and
>   `claude-haiku-4-5-20251001` at `$0.80/$4` per million tokens. The pricing page (read 2026-10-17, rows quoted in the
>   dossier) lists `$2/$10` and `$1/$5`. **Fixed:** Sonnet 5 `2.00 / 10.00 / 2.50 / 0.20`, Haiku 4.5 `1.00 / 5.00 / 1.25 / 0.10`
>   (in, out, 5-minute cache write, cache read); every key kept. Evidence and the failing-on-HEAD run:
>   `docs/dev/diagnosis/model-pricing-rates.md`. Two real telemetry rows now cost `0.0336` (was `0.0504`) and `0.008` (was
>   `0.0064`). New test `tests/test_hardening.py::TestCallCost::test_every_model_pin_has_complete_pricing` (presence of all four
>   fields for `SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL` and every `MODEL_SNAPSHOTS` value). Comment-only edits in
>   `analyzer.py` (the stale `$3/$15` sentence and "no Haiku 5"): **no `PROMPT_VERSION` bump.** `CHANGELOG.md` `[Unreleased]` entry added.
> - **Two statements in item 174 as filed were wrong** and are corrected in its `refs` and `## Updates`: `hardening.py` is **not**
>   a C-10 gated surface (it is in `ACKNOWLEDGED_NOT_GATED`, `scripts/enforcement/blast_radius.py:199-208`), and the Sonnet 5
>   pricing entry is `CHANGELOG.md:5487-5491`, not `:5468`. Item 173 repeats the gated claim in its own record; **not edited.**
> - **Item 175 (open, new):** the owner said "be sure that we are tracking the model, the model version, and the settings such as
>   effort level, thinking etc. so we can trace every decision to the model that made it and the settings for that model."
>   Scope the owner chose: product calls and eval-judge calls; not dev-agent stamps, no database column. The item lists the gaps
>   with `path:line` (read from the code by an exploration pass, **not confirmed by running a call**): the call log keeps the model
>   id asked for, not `final.model`; no `max_tokens`, `thinking`, effort, request id or thinking tokens; `_parse_or_retry`'s retry
>   drops `max_tokens`; judge calls write no telemetry; `MODEL_SNAPSHOTS` is hand-copied; avatar rows and `ApplicationRun`
>   carry the wrong `prompt_version`. **Nothing built.** Item 137 is cross-linked: land 175 before any 137 candidate A/B.
> - **Item 7 (memory consolidation), directed, not started:** the owner said "capture whatever is in memory that is still useful
>   into durable locations before doing the compaction and do so so that you can compact the memory more significantly", then
>   chose **the next session** (not this branch) and **"fold the index, delete only approved rows"**. Measured here: 266 files,
>   1.66 MB, `MEMORY.md` 20,458 bytes. **No memory file was deleted and no row of item 7's draft list is approved.**
> - **Gate:** `python -m scripts.gate --result` read `PASSED on this tree -- exit 0, failed step None, finished
>   2026-10-17T22:54:16-0700, HEAD c5a5560` (non-UX 3580 passed, 8 skipped; ux 189 passed, 2 xpassed; a search of the log for
>   retry lines (`RERUN`) found none). Two commits came after it and are docs only: the item 7 note (`3bf3476`) and this file.
> - **Branch state:** commits `a07119f` (dossier + this session's consumed-event ledger file), `8af432d` (fix), `99c38a3`
>   (records), `c5a5560` (wiki log), `3bf3476` (item 7), then this file. **The owner instructed "push it and open the PR when
>   gate is green".** This file is committed before the push, so it **does not record the PR number or whether it merged**:
>   check `gh pr list` and `git branch -a` first. No merge was authorized.
> - **Model note:** the session began on Opus 5.5 (the plan was written there) and continued on Sonnet 5.5. The consumed event and
>   this file's stamp name `claude-sonnet-5-5`.
> - **Earlier text is not re-copied.** `docs/dev/handoffs/model-55-eval-item.md` (on `main`) holds the item 173/137 first-step
>   results and carries `docs/dev/handoffs/ds-junior-score-drop.md` (item 140b) intact; read them only to check a carried
>   statement. The "Decisions the owner owes" and "Declared, not filed" lists below are the current, merged versions.
> - **Not verified:** the rates are the pricing page's text, **not checked against an invoice or the Console usage page**; the
>   page's Haiku 4.5 row is what the table now carries, and *why* the old numbers equalled the Haiku 3.5 row is not established.
>   Cost figures already published at the old rates were **not** recomputed (owner: leave as dated records;
>   `evals/TUNING_LOG.md` has a dated note). The probe script (`cost_probe.py`) lives in the session scratchpad and is not committed.

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

- Everything through `docs/model-55-eval-item` ✓ (#184, merge `dbc6f02`, MERGED, branch pruned): the record is
  `docs/dev/handoffs/model-55-eval-item.md`, which carries `ds-junior-score-drop.md` (#183) intact.
- **`fix/model-pricing-rates`** ← this branch: item 174 fixed, item 175 filed, item 7 noted. Pushed on the owner's instruction;
  the PR number and merge state are **not recorded here** (this file is committed before the push).
- **Next: the owner's pick.** The owner has already directed two things, in this order of recommendation (not a decision):
  item 175 (call provenance) before any model swap, and item 7 (memory consolidation) in "the next session". Item 145's branch 2
  (`feat/launcher`) and 3 (`feat/pushbuttons`) are not started; item 171 waits on four owner answers.

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7 and 19, and on the owner's alpha
approval. **Do not build item 171's workflow before the owner answers its four questions.** **Do not start item 145's branch 2
or 3.** **Do not run a further paid eval or capture without the owner's spend approval.** That includes item 137's candidate
A/B; its free first step is done and **no later step is approved.** **Do not delete any memory file** until the owner has
approved the specific rows after every DELETE row is re-grepped (item 7).

---

## What just landed on `main`

**PR #184 (`docs/model-55-eval-item`) merged as `dbc6f02`**: items 173 (closed, absorbed) and 174, item 137's absorption of the 5.5
evaluation, and the previous handoff. `main` is at that commit, clean, equal to `origin/main` when this session began (checked).
Before it, PR #183 (`fix/ds-junior-score-drop`, `e490683`) and PR #182 (`fix/capture-generate-stall`, `7807c81`). **Nothing from this
branch is on `main`.** The 15 open Dependabot PRs (item 171) were open when checked at the start of this session.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 21 / 10 ceiling -- OVER"** (19 items and the 2 open epics,
19 and 36). **Changes from the previous handoff's 19 items:** item 174 closed (closed total 91 → 92); item 175 is new and open;
item 7 and item 137 gained `## Updates` blocks (their summaries are unchanged). The owner's drawdown direction stands: down to 0
if possible, before alpha staging. Still twice the ~8 to 10 reduction-sprint threshold. Owner-decision items are marked
*(owner)*. The lists below are **generated from the item files at this commit** (`structural_errors()` in
`scripts/work_items.py`, run with `python -X utf8`; not retyped), grouping every non-epic item by status and listing the epics
separately; the board prints an epic's children under the epic, so its header counts differ by design. Generator output:
`open_all=21 counts={'open': 19, 'blocked': 5, 'deferred': 9, 'watching': 47} epics_not_closed=3 closed_items_and_epics=92` (previous handoff: `open_all=21`, `open: 19`, `closed_items_and_epics=91`).

`## Open` (19):
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
- **175**: The call log keeps the model id asked for, not the answering version, settings or request id; judge calls log none.

`## Blocked` (5):
- **3** *(owner)*: Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5**: First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** *(owner)*: Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [depends on: 6] [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run]
- **10** *(owner)*: Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go. [depends on: 3, 6, 7, 9, 19] [blocked on: everything else landing first, plus the owner's explicit go]
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

- **Item 7, the keep/consolidate/delete list (directed 2026-10-17, for the next session):** the owner chose to fold the index
  and delete only approved rows. What is still owed is the owner's approval of specific rows, after the next session re-derives
  the counts and re-greps every DELETE row. See item 7's `## Updates`.
- **Item 175, the design choices:** how judge calls are recorded (in the eval record, or as `llm_calls.jsonl` rows with their own
  `call` kind, which changes what eval `cost_usd` means) and whether to fix or only record the `max_tokens` retry drift. Both are
  for that branch's plan. No code is written.
- **Item 137 (now carrying the 5.5 evaluation), spend approval for the candidate A/B.** Sonnet 5.5 for the heavy calls and
  Haiku 5.5 for the structured calls are the candidates, one swap per branch, judge held fixed, N per arm chosen in advance (the
  `data-scientist-junior` fixture is bimodal). **The price table is now correct for the two live pins (item 174)**, so a cost
  estimate can be made once the 5.5 keys exist; **no spend is approved.**
- **Item 137, the `thinking` policy per model (before any swap):** Sonnet 5.5 must use `between_tools` (`disabled` is a `400`,
  item 173's Updates). For Haiku 5.5, hold today's behavior with an explicit `disabled`, or adopt `adaptive` as its own
  eval-gated change.
- **Item 137, how soon to move off Haiku 4.5:** it is Active but past its earliest retirement date and is the eval judge too; no
  notice is listed. Schedule, or wait for a notice (60 days' lead): the owner's call.
- **Item 137, keys for the 5.5 models and Haiku 5.5's prompt-length tiers:** a `compute_call_cost` change, not only new keys;
  deliberately not in item 174.
- **Item 140, close or keep open (carried):** every build and measurement part is done. What is left is the original `b180`
  carrier (hypothesis B), which has not reproduced in 31 letters, and which the guard covers regardless (a handle in
  `cover_letter_content` is a hard error). The closure bar needs a falsifiable `verified_by` or an owner-named
  `closure_exception` (`scripts/work_items.py`); I did not close the item. Suggested wording for the owner to adopt or change:
  *"Hypothesis B (the `b180` letter carrier) never reproduced in 31 letters; the runtime guard hard-errors a handle in
  `cover_letter_content`; the score drop is not specific to the change (`docs/dev/diagnosis/ds-junior-score-drop.md`)."*
- **Whether to run stage 2 or another fixture for item 140b (optional, carried):** not needed by the rule; about `$0.0835` per
  run at the OLD rates (item 174 changes that figure), so N = 8 per arm was about `$0.7` then.
- **Whether to file a gate for the per-branch wiki obligation (carried, C-11):** a mechanism is possible and was not built; it
  changes `scripts/gate.py`, a C-10 gated surface, so it is its own item.
- **The app-side race (carried, not fixed):** if a real user clicks Save and continue while an arrival draft is in flight, the
  same sequence can lock Generate behind "You changed your composition after approving it". Confirmed at route level; that a
  user hits it at realistic timing is **not observed**. Options: leave it, make Save and continue wait for in-flight background
  work, or make a draft that lands after the freeze not stale the approval. `TestDraftLandingAfterTheFreeze` pins today's
  behavior; `static/app.js`'s Compose handlers and `hardening.composition_is_stale` are C-10 territory (enumerate consumers first).
- **Item 171, Q1:** may a bot enable auto-merge into `main` for the auto classes? **Q2:** does the 2026-08-07 carve-out (the owner
  handles the docs-site Dependabot alerts personally) still stand, and does it cover version updates? **Q3:** must the four
  Actions majors (PRs #10, #109, #51, #54) be resolved, or consciously pinned with a recorded reason, before the 1.1.0 tag?
  **Q4:** a merge queue (a branch-protection change, the owner's) or accept the squared CI cost under `strict: true`.
- **The `EnterWorktree` question (from item 172):** may agents use the harness worktree location inside the repo?
- **Item 145, branch 2's start:** the C-2 wording, the PEP 668 fallback for `pip install --user`, whether bare `sartor` with no
  runtime runs `up`, whether `sartor` is free on PyPI, separate native and container data. Its end-to-end waits on item 3.
- **Item 10 and the alpha:** item 3 (GitHub toggles), item 7 (the memory list, above), and the owner's alpha approval.
- **The Opus pin on `n1-judge`** is dev tooling only (the product has no Opus call); moving the subagent pins is separate
  (proposal 15 in item 173).
- **Whether figures already published at the old rates get restated:** decided — leave as dated records (owner, 2026-10-17).
- **The *(owner)* items in `## Open`:** 50, 128, 129, 133, 135, 138, 171. The *(owner)* items in Blocked, Deferred and Watching
  are flagged in the generated lists above.
- **Declared by the data-root agent as the owner's call (carried):** whether `sartor --doctor` should print the key path;
  whether the simultaneous-launch race earns an item; whether to reopen item 164 (instrument first); whether the frozen
  `carry_edits=True` generate should keep a typed letter edit over a new letter
  (`docs/dev/diagnosis/run-row-letter-edit-shadow.md` O5); whether a cover letter should be regenerable from the shipped screens
  (item 170's open question).

### Declared, not filed — carried, **not re-verified this session**

The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it,
`docs/dev/handoffs/dependabot-triage-item.md` and `docs/dev/handoffs/data-root.md` "Carried from earlier handoffs" (about 40
bullets). They are **not re-copied here**, to avoid a second hand-maintained copy that rots. The ones most likely to matter next:

- The simultaneous-launch race: the one open limit of the single-instance guard (item 146).
- `maintainer-lane.md` step 2 still gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs
  `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01; latest run `36858103525`); cause not
  examined, no item mentions it. `release.yml` and `docker.yml` have no workflow runs at all (item 171). The stall found on
  `fix/capture-generate-stall` is not that cause by mechanism (`--smoke` stops after Step 1, `scripts/capture_screenshots.py:512`).
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (dated May 6, no files, not a registered worktree). Not touched.
- A checkpoint-advancing wiki pass is owed **before the next wiki-relevant branch**: `wiki_freshness` read 65 files changed since
  the last ingest (under the 75 block threshold) at this close-out, before this branch's own files. This branch's wiki-relevance
  result is in `docs/wiki/log.md` (verified no-edit, `c5a5560`).
- A git stash `stash@{0}` ("On feat/run-detail-modal: epic-c C2 staged implementation … parked for C1c") belongs to another
  session. Not touched.

### New this session, declared (observed unless marked)

- **Item 174's claim that `hardening.py` is C-10 gated was wrong, and the memory already said so** (`reference-consumer-enumeration-gate-c10`:
  `analyzer.py` and `hardening.py` are deliberately ungated). Read `GATED` / `ACKNOWLEDGED_NOT_GATED` in
  `scripts/enforcement/blast_radius.py` before repeating "X is gated". A consumer list was written anyway, in the dossier.
- **The cache-write rate is the 5-minute one** (the product only sends `cache_control: ephemeral`, and telemetry keeps one creation
  count at `analyzer.py:1634-1655`); a 1-hour write cannot be expressed in the table. Stated in the table's comment.
- **Past figures at the old rates:** Sonnet 5 cost was 1.5 times too high and Haiku 4.5 cost 20 percent too low, so a mixed run
  such as item 140b's `$0.6678` is off by an amount that depends on its mix. Re-cost from the telemetry window with
  `compute_call_cost` on a tree at or after this change. Not done.
- **`evals/README.md:977-986` cost estimates** (`~$0.35-0.40` smoke) were computed at the old rates and are not edited; item 134
  owns the contradicting estimates.
- **Item 175's findings are code reading, not runs.** The first commit on its branch should be the observation: make one real call
  and read the row (C-7).
- **Memory written now, before the push (outside the repo, not committed):** `reference-consumer-enumeration-gate-c10` (the
  second mis-statement of what is gated), `reference-kit-phase1-ruff-format-built` (commit-time hook gotchas: `python -m ruff`,
  and the `ruff-changed` hook reads the index before the command runs), and a new `project-llm-call-provenance-requirement`
  with its `MEMORY.md` index line. **`MEMORY.md` is 20,458 bytes and a hook asked for compaction to 17.1 KB; not done by design (item 7).**
- **Process.** The ledger lists came from `structural_errors()` run with `python -X utf8`. The gate was run once, in the
  background from Git Bash, and read from its own `GATE_DONE` marker and `gate --result`, not from the task notification. The only
  python processes on the machine at close-out were two not started by this session. No dev server was started.

---

## Recurrences observed this session → guardrail authored

**Rows 1 to 6 are this session's (`8603d643`).** No row has a mechanism authored on this branch except where it says so.

1. **The interrogative witness paused the first `Write` after a directive prompt, twice** (the plan file, and the first scratch
   file in the handoff step). Same class as item 164's. Each cleared on the identical re-run; no hook was bypassed. **Mechanism
   exists and held**; **no new mechanism authored** (the witness is by design a fail-open one-shot; reopening item 164 is the
   owner's pick). **Unenforced** as a cost.
2. **`block-doubled-backslash` fired once on my own command** (a grep for `$3` escaped with backslashes). **Mechanism exists and held**:
   it named the way through (the Grep tool) and I took it.
3. **`ruff-changed` blocked my commit twice: the new test was not ruff-formatted, and then I formatted, staged and committed in one
   call, which the hook rejects because it reads the index before the command runs.** I did not check for an earlier instance of
   this exact miss, so I am **not** claiming a recurrence. **Mechanism exists and held.** Recorded in memory
   (`reference-kit-phase1-ruff-format-built`). **Unenforced** beyond the hook itself.
4. **`verify-binary-on-path` blocked bare `ruff`** (not on PATH on this machine). **Mechanism exists and held**; the way through was
   `python -m ruff`. Recorded in the same memory note.
5. **A wrong claim about enforcement coverage in a work item** (item 174 said `hardening.py` is C-10 gated). A recurrence of the
   class "an unverified assertion becomes a premise" (charter C-12), and of the memory's own warning that `analyzer.py` and
   `hardening.py` are deliberately ungated. **No mechanism authored, and none is plausible by construction:** a hook cannot judge a
   prose claim in a work item. What is possible and **not built**: a check that a `refs` entry of the form
   `scripts/enforcement/blast_radius.py:N` points at a line containing the file the item names. **Surfaced to the owner here.
   Unenforced.** Corrected in the item and in memory.
6. **A hand-maintained external number went stale (item 174, and row 10 of the previous handoff).** **Mechanism authored on this
   branch, partial:** `tests/test_hardening.py::TestCallCost::test_every_model_pin_has_complete_pricing` fails if a model the code
   can call (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`, any `MODEL_SNAPSHOTS` value) has no `MODEL_PRICING` entry with all four
   rates. It checks **presence, not truth**: the source is an external web page, so no offline test can fail when the page
   changes. A stale-but-present rate is still undetected. **Surfaced to the owner here.**
7. **`MEMORY.md` kept growing until a hook flagged it** (item 7's own text says the count "grows session to session"; 244 files on
   2026-10-02, 266 now). A recurrence. **No mechanism authored:** the index is outside the repo and the owner directed the
   consolidation for the next session with approval of specific rows. **Item 7 holds it. Unenforced.**

---

## What this branch should build

**Nothing is queued on this branch.** The owner chooses the next item; this handoff does not pick one. The list below is the
closing agent's **recommendation for order, not a decision**. Do not expand beyond what the owner names.

1. **Land this branch first (if the owner agrees).** Check first: `gh pr list` and `git branch -a`. The owner authorized the
   push and PR; **a merge needs a fresh instruction.** Then, in order: `python -m scripts.ci_wait <n>` (exit 0 only; 3 means
   green-after-retries, stop and look), `gh pr merge <n> --merge`, `git checkout main && git pull --ff-only`, regenerate the
   pointer with `print_handoff_pointer.py` and verify it with `check_handoff_pointer.py`, then `git branch -d`. Authority:
   `docs/dev/maintainer-lane.md` close-out.
2. **Item 175, call provenance (the owner's stated requirement).** A `feat/*` or `fix/*` branch, your choice with the owner.
   First commit is the observation: one real call, read the logged row, and show which fields are missing. Then the design in
   the item: log the request kwargs derived from the real `stream_kwargs`, plus `response_model`, `request_id`,
   `thinking_tokens`, `attempt`; keep `model` meaning the id requested (pricing and the dashboard key on it); decide how judge
   calls are recorded; a test that fails when a new request setting is not recorded (C-11). `analyzer.py` and `llm_calls.jsonl`
   are not gated; write the consumer list anyway. It makes any later 137 A/B interpretable.
3. **Item 7, memory consolidation (the owner chose "the next session").** Its own branch (`chore/memory-consolidation` or the
   owner's name). Read item 7's `## Updates` first. Steps: re-derive the counts; for each durable recipe worth keeping, put it
   in a repo doc (a docs-IA home, with `doc-writing` for any new doc) **before** touching the memory file; compact `MEMORY.md`
   one line per theme; re-grep every DELETE row of the 2026-10-02 draft list and **show the owner the rows**; delete only
   approved files. Memory edits are outside the repo; the repo docs are what the branch commits.
4. **Item 137 after 175:** the `thinking` policy, the 5.5 keys and Haiku 5.5's tiers in `compute_call_cost`, then the candidate
   A/B (**needs a new, explicit spend approval; none is given**), one swap per branch, judge held fixed, `PROMPT_VERSION`
   unchanged for a model-only change, pricing keys in the same commit as any constant change, subagent pins last. Read item
   173's `## Updates` of 2026-10-17 and 137's block of the same date first.
5. **Item 140, the owner's closure decision** (see "Decisions the owner owes"). No work is left on it.
6. **Carried, in the previous order:** the wiki-obligation gate (C-11) if the owner wants it; the app-side race; item 171 after
   Q1 to Q4 (instruments first: the failing log of PR #127, whether `release.yml`'s `publish` can run on `workflow_dispatch`,
   the changelogs for the four Actions majors; the ruff bump on its own branch); look at `capture-smoke.yml`'s three failed
   scheduled runs; a checkpoint-advancing wiki pass (65 of 75); item 145's branch 2 (read item 0145's `## Updates`; first commit
   is an instrument); open product bugs 130, 105, 131, 107, 134, 139, 98, 99; remaining container checks and H2
   (`docs/dev/blast-radius/data-root.md` O10 to O13); reopening item 164 (instrument first); the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check, then `--event consumed` on this handoff (note the template path: `docs/dev/AGENT_HANDOFF_TEMPLATE.md`),
then check `gh pr list` and `git branch -a` for this branch's PR and merge state (this file does not say). Then ask which item to
take. Create that branch off `main`, write a plan at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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
