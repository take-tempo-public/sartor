<!-- provenance: schema=1 session=94bf82f3-beaf-46f8-951c-1cc7836041ed branch=feat/eval-dataset-format commit=653c6f0 actor=amodal1 agent=anthropic/claude-sonnet-5-5 generated_at=2026-10-23 -->

# Agent handoff — item 183 (eval redesign step 3a) built: the golden-set format, a stub-tested prose generator, per-cell seeds in the runner and a reachability check; branch `feat/eval-dataset-format` → needs the owner's go to push, then PR, merge on green CI, prune; then 3b (item 191)

**Branch to create:** `feat/eval-dataset-v1` (item 191, step 3b: the paid generation of the 48 cells), off `main`, when the owner approves it and this branch has landed. Do not start it before then.
**Base branch:** `main`

> **This session (`94bf82f3`) built step 3a and nothing else** (pointer `@ main (186a064)` from `feat-eval-catalog-skeleton.md`; the pointer check passed with the `Handoff:` prefix and exit 0; `--event consumed` recorded, fingerprint `c3b32592ab74`; the ledger file `docs/dev/ledger/94bf82f3-beaf-46f8-951c-1cc7836041ed.jsonl` is this branch's first commit). The work was done on 2026-10-22, the owner's local day (UTC had already rolled to 10-23), so every dated entry on this branch says 2026-10-22; this handoff was written on 2026-10-23, after the gate finished. The plan was written and approved in plan mode (`~/.claude/plans/handoff-docs-dev-handoffs-feat-eval-cata-precious-feather.md`).
> - **No standing instruction to push or merge was given this session.** Pushing is outward-facing on a public repo, so **the first thing to do is ask the owner to confirm the push**, then `git push -u origin feat/eval-dataset-format`. At writing the branch is **not pushed**, no PR is open, and `git log origin/main..main` is empty (local `main` had nothing the remote lacks).
> - **Owner decisions this session (chat, plan mode, 2026-10-22):** (1) take step 3, item 183; (2) the run-size flags `--eval` / `--group` / `--affected-by` / `--full` are built in **step 4**; (3) single-call evals of `generate` and `generate_cover_letter` are in **step 4**; (4) **split step 3 into 3a (this branch, no paid call) and 3b (item 191)**; (5) the dataset's prose is written by a **generator script**; (6) the **USAJOBS fetch is deferred**, 3a writes an amendment proposal only; (7) the golden data directory is classified wiki-irrelevant; (8) the author model is **`claude-opus-5-5`**; (9) **one fixture per JD**, so `case_id` is `golden-v1/<cell>--<industry>` and the full tier is up to **96 fixtures**. One decision was mine, shown in the plan: the three converted pilots carry a **waiver list** the checker requires to be exact and a `frozen` suite must leave empty.
> - **Built (commits on this branch, oldest first):**
>   - `4185eb9` docs(ledger): consumed handoff feat-eval-catalog-skeleton (item 183, eval redesign step 3a)
>   - `794979d` docs(blast-radius): consumer enumeration for the eval dataset format, before any code edit (item 183)
>   - `44f2e69` chore(work): split eval step 3 into 3a (item 183) and 3b (item 191); record the owner's build-order answers
>   - `6e177c5` feat(eval): golden-set cell format, deterministic renderer and checks (item 183, step 3a)
>   - `a964369` feat(eval): three pilot cells of golden-v1 and the draft manifest (item 183, step 3a)
>   - `2eec0e1` feat(eval): per-cell seeds in the runner and the golden-v1 suite (item 183, step 3a)
>   - `24797c4` feat(eval): golden-set prose generator, tested against a stub client only (item 183, step 3a)
>   - `c0c1d75` test(eval): reachability of every golden cell through the real pipeline, free (item 183, step 3a)
>   - `b86f957` fix(test): __exit__ of the reachability stub stream returns None, not bool (mypy strict)
>   - `9397310` docs(eval): golden-set docs, the 3a/3b split, and a C-2 proposal for the USAJOBS fetch (item 183, step 3a)
>   - `a142451` docs(wiki): scoped self-update for the golden-set format and generator (item 183, step 3a)
>   - `653c6f0` docs(work): file item 192, record the apostrophe false-BLOCK recurrence on item 53, correct a count (item 183, step 3a)
>   - **The format** (`evals/golden_set.py`, `evals/golden/golden-v1/`): a cell is a profession at a level; `profile.json` (code-written) and `prose.json` (model-written or converted) are the source, and `resume.md`, `jd.txt`, `expected.json`, `seed.json` are derived and compared byte for byte; `manifest.json` carries the ladder (every rule `authored`), the O*NET attribution and a sha256 per file; `python -m evals.golden_set check` runs it all. **Three pilot cells** are the existing personas converted without changing a word (checked with `cmp`, independent of the converter).
>   - **The runner:** `--suite golden-v1`; in assemble mode with no `--seed` each fixture's own `seed.json` is its own corpus, opened and closed one at a time; the `--seed` path and `--suite real` are unchanged; `--estimate` works for the suite with no seed.
>   - **The generator** (`evals/golden_author.py`, call kind `dataset_author`, an `exempt` catalog entry, pin `AUTHOR_MODEL`): **built and tested against a stub only; it has never made a real call.** `claude-opus-5-5` has a `MODEL_PRICING` row (read from the pricing page 2026-10-22) and **no `THINKING_POLICY` row on purpose**; no fallback model; `--confirm-paid` and `--max-spend` are required.
>   - **The reachability check** (`tests/test_golden_reachability.py`): the real pipeline against a stub client; its control arm is the old `recommend_summary` gap.
> - **Gate:** `python -X utf8 -m scripts.gate` ran on the tree at `a142451` (everything then committed, working tree clean, no untracked file): **PASSED**; the log's own marker is `GATE_EXIT=0` and it printed "gate: all steps passed" (4019 passed, 9 skipped in 383.84s (0:06:23); 189 passed, 4028 deselected, 2 xpassed in 826.04s (0:13:46)). The log has 0 `RERUN` markers. Two commits came after it and are docs and work items only: `653c6f0` (items 192, 53 and 183, one dossier line, two corrected counts in the design doc and the CHANGELOG) and this handoff. `--result` therefore reads STALE (HEAD moved); after `653c6f0` I re-ran the work-item check, 120 doc, wiki and work-item tests and `check_doc_links` (all green by exit code). CI is the authority.
> - **Mutation checks (scratch, not committed):** 4 of the runner's per-cell-seed change, 8 of the generator, 5 of the reachability test and its inputs (including making `recommend_summaries` short-circuit at two variants, the original gap). Each turned a test red; every file was restored byte for byte.
> - **Primary sources read this session, not recalled:** the O*NET 31.0 licence text (its "Except as noted below" is the *License Exceptions*: CC BY 4.0 covers the downloadable database files only); O*NET OnLine for the occupation codes (no site-reliability and no product-manager occupation exists, so those two mappings are `nearest`, with the evidence in the manifest); the pricing page for Opus 5.5 ($4 / $20 / $5 / $0.20); the USAJOBS terms (design doc 6.5).
> - **Not verified:** (1) **the generator has never made a real call**; the live request shape (explicit adaptive thinking plus an effort, no sampling parameters) is as the claude-api skill documents it. (2) The **API host, headers and rate limits of USAJOBS** were not read, only the terms. (3) The prose validator cannot tell an invented employer from a real one, and **freezing is not enforced against git history**. (4) `evals/README.md`, `CHANGELOG.md`, the design doc and the dossier were edited by hand and not audited. (5) The wiki audit covered changed hunks only. (6) No paid call of any kind was made, so `costs.json` still prices neither judge kind. (7) CI's result and the merge are not known at writing.
> - **Process notes:** the harness reported the model as Opus 5.5 on the planning turns and Sonnet 5.5 on the execution turns; the stamp names Sonnet 5.5. Subagents: 3 `Explore` and 1 `Plan` (planning), 4 `wiki-scribe` (Haiku), 5 `wiki-grounding-auditor` (Sonnet 5; four pages plus one fresh re-audit of two corrected sentences). Browser tabs: opened for O*NET, the pricing page and the USAJOBS terms, all closed. **Processes:** the gate has exited; no dev server was started. **A background watcher was reaped under memory pressure and was not restarted** (the harness said not to); the gate was checked by reading its own log.
> - **Branch state at writing:** ahead of `origin/main` (`186a064`) by the commits above; not pushed. `docs/eval-redesign-pre-scrub`, `stash@{0}` and the Dependabot branches were not touched.
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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging (owner's 2026-10-02 sequence on item 40), plus the eval redesign filed as epic 180.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- Everything through `feat/eval-catalog-skeleton` ✓ (#199, merge `186a064`, MERGED): step 2, the catalog and the spend flags. **Item 182 is still `open` on the board** (merged, never closed): closing it needs a `verified_by` (candidates: `tests/test_eval_catalog.py`, `tests/test_eval_spend.py`, the merge of #199 and its green CI run); I did not close it, it was not in this session's plan.
- **`feat/eval-dataset-format`** ← this branch (item 183, step 3a): built, gate run on `a142451`. Landing it needs the owner's go to push; then `python -m scripts.ci_wait <n>`, `gh pr merge <n> --merge`, `git checkout main && git pull --ff-only`, the pointer, the prune.
- **Next, once this branch has landed:** **step 3b, `feat/eval-dataset-v1` (item 191)** when the owner approves it and **approves the spend**: the other professions' facts (re-read the DDaT ladders and the O*NET database files' terms first), the paid generation through `python -m evals.golden_author ... --confirm-paid --max-spend`, the capped calibration run, `python -m evals.eval_catalog measure --write` afterwards, retiring `evals/fixtures/synthetic/` and retargeting its consumers (listed in `docs/dev/blast-radius/eval-dataset-format.md` under Deferred), tier sizes for up to 96 fixtures, and freezing `golden-v1` (the pilots' waivers must be gone first: the pilots are replaced by generated cells or enriched). Item 184 (step 4) and item 10 depend on 191.
  Other candidates: the rest of item 177; item 25's status; item 176; the six item 7 decisions; items 175, 140, 179's closure; item 178's mechanism; item 145's branch 2 and 3 (not started); item 171 (waits on four owner answers).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 depends on 3, 6, 7, 9, 19 and items 181 to 186 and 191, and on the owner's alpha approval.
**Do not run the golden generator for real, the candidate A/B (item 137), or any paid eval or capture, without the owner's spend approval.** The four A/B answers are recorded in item 137; the $12 ceiling was stated for that run only, and the run waits for step 10.
**Do not move a pin** (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`, `AUTHOR_MODEL`); the judge is chosen at step 9 (item 189). **Do not add a `THINKING_POLICY` row for `claude-opus-5-5`:** it would make Opus 5.5 a legal `--model-override` target for product calls nobody validated on it. **Do not close items 175, 178, 179 or 137 on your own:** closing needs a falsifiable `verified_by` or an owner-named `closure_exception`. **Do not build item 171's workflow before the owner answers its four questions.**
**Do not edit `evals/catalog/costs.json` by hand:** re-measure it with `python -m evals.eval_catalog measure --write`; the gate fails if a measurement is for a model that is no longer the pin. **Do not edit `evals/prompt_hashes.json` by hand:** change a system prompt, bump `PROMPT_VERSION` (`AVATAR_PROMPT_VERSION` for the avatar prompt), then run `python -m scripts.prompt_lock --write`; the gate fails otherwise, and a hand edit defeats the rule (a stated limit).
**Do not edit a frozen cell of `golden-v1` in place:** a later version adds cells and never edits one (design doc 6.4). While the manifest says `draft`, a cell may change, but `python -m evals.golden_set check` must pass and the manifest hashes must be re-stamped (`python -m evals.golden_set manifest`).
**Do not start item 145's branch 2 or 3.** **Do not delete any further memory file** without the owner's approval of the specific rows (item 7).
**Do not change the server's threading** (`app.py`) or item 25's status on your own. **Do not delete `evals/results/_test_stubs_quarantine/`** without the owner saying so. **Do not change the `analyze_*` cache breakpoint** (Finding 2 in item 137): it is a behaviour change to `analyzer.py` that needs its own branch and eval.
**Do not register the design doc in `scripts/doc_registry.py`** (decision 8: repo-only until steps 1 to 3 land). **Do not build the USAJOBS fetch, and do not commit any third-party posting or résumé text, before the owner chooses the C-2 route in design doc 6.5.** **Do not edit `evals/fixtures/synthetic/`**: step 3b replaces it. **Do not register or request a USAJOBS API key:** that is the owner's to do.
**Do not write into spolia, the-factory or isidium from a sartor session.** Anything for them goes as a proposal the owner carries.

---

## What just landed on `main`

**Nothing from this branch is on `main` as of writing.** `main` is at `186a064` (PR #199, step 2: the eval catalog and the spend flags; merged 2026-10-22T04:58Z, which was the evening of 2026-10-21 locally). Before it: #198 (`dcbe24d`), #197 (`c64d784`), #196 (`c7c82ce`). If this branch's PR merged, `git log --oneline -3` on `main` shows it; the merge is a merge commit (squash and rebase are disabled on the repo).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. Header, read from the board after this branch's filings: **Open 27 / 10 ceiling -- OVER** | Blocked 4 | Deferred 9 | Watching 46 | Epics 7 | Closed 93

**Changes from the previous handoff:** item **183** is open (step 3a) and **191** (step 3b) is new and blocked on 183, so Open goes 26 to 27 (items 181 to 191 and 137 render under epic 180, not in the lists below); item **192** is new and Watching (the committed corpus seed's `area` / `study_type` keys are dropped by the importer); items 184 and 10 now depend on 191. `python -m scripts.work_items check` printed `work_items: OK (192 files)`. The lists below are the previous handoff's, plus 192. The board is over its ceiling and the owner's direction stands: drawdown to 0 if possible before alpha staging. Owner-decision items are marked *(owner)*.

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
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Fix built, measured, screenshots recaptured; score drop not specific to the change; carrier hypothesis never reproduced.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **171** *(owner)*: 16 Dependabot PRs open, oldest 2026-07-13; nothing acts on green ones. Design the per-class merge policy.
- **175**: Built (fix/llm-call-provenance): rows record answering model, request id, settings; judge calls logged. Owner closes.
- **177**: Sweep found a threaded-server contradiction, a wrong gate.py item path, README min_* claims and stale counts.
- **179**: run_suite's out_dir default binds RESULTS_DIR at def time, so a test's patch misses it; 337 stub files in the real dir.

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

`## Watching` (46):
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
- **192**: The committed corpus seed (`synthetic/corpus/role-summary-drafting/seed.json`) uses `area` / `study_type`; the importer reads `field`, so the discipline is dropped.

`## Epics` not closed (4):
- **19** (open): UX-suite flakiness solution sprint - mode-C residual + newly observed instances
- **36** (open): Final March epic A - main-app function + UX
- **40** (blocked): Final March epic E - the public v1.1.0 cut
- **180** (open): Eval redesign build order

### Decisions the owner owes (collected; each is also in the item it belongs to)

- **The USAJOBS exploration fetch needs a charter decision (new, owner's call):** design doc 6.5 recommends amending C-2 with an opt-in class (c) and lists seven rules; the alternatives are reading D-6 to cover it (a stretch, explained there) or not fetching at all (the exploration set becomes a seeded draw from the matrix). Nothing blocks 3b. Ceremony: `docs/governance/charter.md:500-510`.
- **Item 182 is merged but still open (new, housekeeping):** it needs a `verified_by` (see "Where we are") or an owner-named `closure_exception`. Item 181 was closed on the next branch last time; I did not repeat that because it was not in this session's plan.
- **The converted pilots are not rich enough, and say so (new, declared):** four richness checks fail for each (summary variants, role intro variants, refinement notes, clarifications); the manifest lists 12 waivers and a `frozen` suite must have none. 3b either replaces the pilots with generated cells or enriches them by hand.
- **The level ladder and the non-tech levels are authored, not sourced (new, accepted 2026-10-21):** every rule in `manifest.json` has `rule_source = "authored"`; the DDaT ladders for these professions were not read. Revise if a source is found.
- **The full tier is up to 96 fixtures, not 48 (new, declared):** one fixture per JD. 3b's cost estimate must count 96 per arm (about double design 6.4's figure for 48).
- **Opus 5.5 as the author, and no fallback model (new, declared):** chosen by the owner outside both arms of item 137's comparison; a fallback would make the recorded model wrong for the text, so a refusal raises and writes nothing.
- **Re-measure `costs.json` after the first paid run (carried, now step 3b):** both judge kinds, `promote_clarification_to_bullet` and `suggest_skill_from_corpus` have no call-log rows, so `--estimate` names them and leaves them out of the total, and `--max-spend`'s pre-flight cannot price the judge (the runtime check bounds it). After 3b's calibration run: `python -m evals.eval_catalog measure --write`. The means are one machine's usage until then.
- **Four `lean` statements and the `flows` group for the judge kinds are authored, not measured (new, owner's call):** `clarify`, `iterate_clarify`, `generate` and `generate_cover_letter` carry `lean = "false_positive"` with a `lean_why` that cites a rubric rule or `AGENTS.md`; both judge kinds sit in `flows` because the end-to-end flows are what call them. Accept or revise.
- **A bad `--max-spend` value exits 2 (new, owner's call):** that is argparse's usage error, the same code as "a grading failed". The README says so. A distinct code would need a custom error path.
- **`--estimate` under `--model-override` is approximate (new, declared):** the token means were measured on the pin and are priced at the candidate model. The README says so.
- **The plan counts `iterate_clarify` even when the scripted edit does not land (new, declared):** a `scenario_misaligned` run skips it. The plan is a plan, not a prediction; the tie test uses a résumé that contains the edit.
- **How the dashboard shows a slash-bearing `case_id` (carried, deferred to step 8):** the form is now `golden-v1/<cell>--<industry>`; no dashboard code reads `case_id` today (grep, `docs/dev/blast-radius/eval-catalog-skeleton.md` and `eval-dataset-format.md`).
- **The wiki scribe wrote overstated prose again (carried class of items 168 and 178):** this session 5 defects on `eval-harness` (fixtures called "generated", `_check_mode` said to select the mode, `PREDICATES` said to define the traps, `REACHABILITY` said to pair cells with routes, an unsourced prediction), caught by my review before the auditors; one more unsupported claim was in a sentence I added myself and the auditor caught it (`docs/wiki/log.md`). The auditors' catch rate is unmeasured again because the review ran first.
- **Carry sartor's producer-id recipe to spolia (carried, owner's call):** `call_identity.producer_id` (recipe version 1: call kind without `_retry`, prompt hash, answering model else requested, request settings; `sha256:` form) is built and tested. Spolia's P-0004 (agent identity and producer id) is reserved and unwritten, and the owner said sartor learns from the siblings and is outside Isidium's scope. Sending it is a proposal the owner carries (spolia `docs/proposals/README.md`); nothing was written into another project's repo.
- **Dashboard embeds whole raw rows (carried, owner's call):** `dashboard/templates/dashboard.html:2019` puts the last 200 rows in the page, so the two 71-byte hashes add roughly 28 KB (arithmetic, not measured). Trimming the embed is a dashboard change; left.
- **Judge rows keep `run_id ""` (carried, owner's call):** giving them the fixture's `run_id` would change `_run_trace` (it drops empty `run_id`) and `/api/run/<id>`. The trace and case ids carry the join today.
- **`cost_usd` on the iteration records (carried, found, not changed):** `_run_iteration_phase` recomputes it later, so those records include the `iterate_clarify` row and the other rubric records of the same fixture do not. Align them, or leave?
- **A hand-edited prompt lock passes (carried, C-11, owner's call):** `scripts/prompt_lock.py --write` refuses a changed hash under an unchanged version, but editing the hash and the version by hand in `evals/prompt_hashes.json` passes. Comparing the lock against `origin/main`'s copy would close it and is fragile on shallow CI clones. Not built.
- **User-prompt templates are unhashed (carried, declared, UNENFORCED):** about 25 inline f-strings with dynamic content; a change there still relies on the convention.
- **The mypy-strict roster is not gated for a new root module (carried, found by experiment, owner's call):** see recurrence 2.
- **Make the gate refuse untracked files (carried, item 52's class, owner's call):** the local gate passed while CI failed because the new files were untracked and several checks read `git ls-files` (recurrence 6). Candidate: `scripts/gate.py` refuses, or loudly warns, when `git ls-files --others --exclude-standard` is non-empty. Item 52 holds the mechanism choice; nothing was changed in `gate.py`.
- **The eval redesign: all eight section 8 decisions and the four follow-on questions (9 to 12) are ANSWERED (recorded in `docs/dev/eval-redesign-design.md` section 8).** Open follow-ons: (a) **USAJOBS:** the terms were re-read in a browser on 2026-10-22 (design doc 6.5); the page still shows no effective date. The fetch is **not built**: 6.5 is a proposal for the owner. The API key is the owner's to register. (b) **NYC Jobs:** not targeted (Q12); its open-data statute ruling is parked. (c) With no gold labels (decision 5), step 9's calibration is judge-to-judge agreement only, which shows consistency, not correctness. (d) Haiku 4.5's status was not re-checked; re-check before step 9 picks the judge. (e) Tier sizes (21 / 12 / 48 cells, up to 96 fixtures) and the per-arm cost are still proposals; step 3b's calibration run measures them.
- **The backup branch `docs/eval-redesign-pre-scrub` (carried, owner's call):** the owner said keep it for now; it was never pushed (tip `27bac3f`). Delete when the owner agrees.
- **Item 137, what is left (updated):** the A/B itself (step 11 of the build order, item 137 under epic 180, depending on item 190; pre-registered on the full run with the four answers already recorded); the subagent pins (`agents/*.md`, after the product decision); how soon to move off Haiku 4.5 (past its earliest retirement date, still Active, no notice listed; it is also the eval judge and two subagent pins); the stale "no Haiku 5" sentence in `CHANGELOG.md`'s 2026-07-05 entry (a dated record, not edited). Opus 5.5 is now priced as the dataset author's model, with no `THINKING_POLICY` row on purpose; an Opus 5.5 *product* call would still need the policy chosen by probing the API.
- **The `analyze_*` user-prefix breakpoint (carried, Finding 2):** cents over five months, written for a `generate` that rarely follows in
  product. Drop it on product synthesis, keep it, or leave it? A behaviour change in `analyzer.py` with its own branch and eval.
- **`commands/bench.md:20` (carried):** it describes six call-log fields no row carries yet (they start appearing with the next logged call).
  Edit the line, or leave it until rows exist?
- **The 89 top-level result files (carried, replaces "the 88"; owner's call):** none was verified to be a real paid run. Worth checking before they seed the A/B baseline?
- **Item 179, close or keep open (carried):** needs a `verified_by`: the regression test
  `tests/test_eval_runner.py::TestRunSuite::test_run_suite_default_out_dir_follows_patched_results_dir` and the `pytest_sessionfinish` check in
  `tests/conftest.py`. Keep open if you want the check shown to fire under `-n auto` first.
- **The 337 quarantined files (carried):** delete `evals/results/_test_stubs_quarantine/` whenever you do not want them; nothing reads it.
- **Model override on the console route (carried, owner's call):** `POST /api/tune/run` (`blueprints/diagnostics.py`) takes no model override; the
  flag is CLI-only. Wanted in the browser, or is the CLI enough for the A/B?
- **`_load_baseline_scores` ignores `eval_mode` (carried, not touched):** an assemble-mode run still seeds a generate-mode run's baseline. A
  different population problem from candidates; file as an item, or leave?
- **A gate for "every baseline view skips candidates" (carried, C-11, owner's call):** nothing enumerates the dashboard's aggregations, so a NEW
  baseline view that forgets `is_candidate_record` would pass every test. A test that walks the aggregation functions is possible; not built.
- **`LLMConfigurationError` for an unlisted model (carried, owner's call):** it fails closed, but the type's name and message read as a credential problem. A dedicated subclass or a plain `ValueError` would be clearer; the cost is the 19 handlers keyed on `LLMResponseError`. Not changed.
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

### Declared, not filed — new this session

- **A pipe hid a failing check and a commit shipped it.** `python -m mypy . | tail -1 && git commit` committed with one mypy-strict error (`__exit__ -> bool`); the next commit fixed it. See the recurrences section. The gate would have caught it at close-out.
- **`python -X utf8` does not reach child processes.** `tests/test_doc_links.py`, `test_doc_frontmatter_gate.py` and `test_doc_single_home_gate.py` failed with `TypeError: ... 'NoneType' and 'str'` under `-X utf8`; they pass with `PYTHONUTF8=1`. In the memory notes.
- **`verify-binary-on-path` false-BLOCKed a commit message with an apostrophe** (item 53's class). Worked around with `git commit -F <file>`, a message written with the Write tool.
- **The interrogative witness paused edits four times** on directive work (the plan stub, a wiki edit pair, a log entry), each cleared by re-running the identical call; a subagent hand-back re-arms it (item 169).
- **A background command's notification reported exit 0 within seconds** while the gate it had launched ran for many minutes (the wrapper's exit, not the gate's). The log's own `GATE_EXIT=` marker was the evidence. A later watcher was reaped under memory pressure and not restarted.
- **The sibling-repo conventions were not re-read this session.** The catalog entry format still follows the earlier subagent report (see the carried section). The `exempt` entry for `dataset_author` uses the format as built.
- **The mypy 'annotation-unchecked' notes** in `tests/test_composition_staleness.py:145` and `tests/test_regenerate_cover_letter.py:278` are pre-existing and not errors.
- **Scratch only, not in the repo:** `make_pilots.py`, `mutate_runner_seeds.py`, `mutate_author.py`, `mutate_reach.py`, `show_fired.py` and `build_handoff.py` in the session scratchpad; the `claude-api` skill was loaded for the Opus 5.5 request rules.

### Declared, not filed — carried from item 182's session (this session re-verified none of it)

- **The sibling conventions came from a subagent.** The entry format's `schema`/`kind` head, the no-floats rule, filename-is-key and the length rule for an exemption reason are as an Explore subagent reported them from spolia, the factory and isidium; the dossier and design doc cite them as reported. Re-read the siblings at source before step 3 extends the format.
- **The tables the dossier rests on were checked, not trusted:** the 26-site table was re-derived by my own AST script (`sites.py`, scratch), and the registration-surface report was confirmed by running the tests it predicted (66, then 314 passed).
- **Two Bash calls were refused with "The server-side auto mode classifier gave no verdict"** (the first `check_handoff_pointer` and the first `--event consumed`); each ran on the identical retry and nothing had run before. The previous handoff recorded the same refusal once. Cause not examined.
- **`verify-binary-on-path` blocked a bare `ruff` / `mypy`.** Use `python -m ruff` and `python -m mypy`.
- **`python -m scripts.check_doc_links` fails** with `ModuleNotFoundError: check_doc_frontmatter`; run it as `python scripts/check_doc_links.py`.
- **Pyright (the IDE) reports unreachable-code hints in `run_suite`** because `stop_reason` is rebound through `nonlocal` in `_cancelled`; mypy and `test_a_run_stops_before_the_next_phase_once_the_cap_is_reached` are the authority.
- **A blanket `sed` over my own entries (UTC date to local day) also changed one correct UTC timestamp** in item 181. I grepped for `Z`-stamps, found it and restored it before committing. No gate would have caught it.
- **`/wiki-lint` was not run as the command.** I ran its structural checks with a throwaway script over all 42 pages: 0 real errors, 0 warnings, and one false positive on the literal text `[[wikilink]]` inside backticks in `docs-information-architecture.md` (untouched by this branch).
- **`run_suite` names its result file to the second and appends** (memory note `reference-run-suite-result-file-same-second`): a test that runs it twice must give each run its own `out_dir`.
- **Scratch only, not in the repo:** `mutate_catalog.py`, `mutate_runner.py`, `sites.py`, `wiki_lint_structural.py` and `build_handoff.py` in the session scratchpad.
- **The wiki audit covered changed hunks only;** `evals/README.md`, `SECURITY.md`, the design doc and `CHANGELOG.md` were edited by hand and not audited.

### Declared, not filed — carried from item 181's session (this session re-verified none of it)

- **The first full-suite run overlapped my own edits** (a detached subshell run, no completion notification, an empty log until it finished). It found two real failures that I fixed (the `py-modules` roster; two wiki cites of a removed function), and is not evidence for the final tree. The gate run in the preamble is.
- **Spolia's files were uncommitted and moving** (branch `design/item-279-weights-and-model-map`, many modified items and new evidence notes) when I read them. Every convention cited from them is dated 2026-10-21 and should be re-read before it is cited again.
- **The wiki audit covered the changed hunks only.** `SECURITY.md`, `evals/README.md`, `docs/governance/enforcement.md`, `commands/bench.md` and the design doc were edited by hand and are not wiki pages, so nothing audited them.
- **`evals/README.md` still says four rubrics ship** (seven do) and gives contradictory cost figures; that is item 177 and was not touched.
- **Scratch only, not in the repo:** `scratchpad/mutate_leak.py` (the mutation check that made the leak test fail on the old selection rule).
- **Pyright shows `@contextmanager` -> `Iterator` deprecation hints and `reportTypedDict*` errors in `analyzer.py`.** Pre-existing; `mypy .` and `ruff` are clean and are the gate.

### Declared, not filed — carried from the session before that (this session re-verified only that `git fetch --prune` deleted `origin/feat/eval-record-identity`, the stale-ref mechanism this section describes)

- **Stale remote-tracking refs, cause now examined:** `git ls-remote --heads origin 'docs/*'` returned nothing while `git branch -a` still listed `origin/docs/eval-dataset-research` and `origin/docs/eval-redesign-decisions`. So the remote copies were deleted on merge (the repo's delete-on-merge works) and the local refs were only stale; `git fetch --prune` clears them. This resolves the previous handoff's "cause not examined" bullets for `origin/chore/wiki-checkpoint-pass`, `origin/fix/llm-call-provenance` and `origin/fix/eval-results-test-leak` as far as the mechanism goes; I did not re-check those three names.
- **One Bash call was refused with "The server-side auto mode classifier gave no verdict"** (the first `--event consumed` attempt, issued right after plan approval). Nothing ran: the tree was clean afterwards and no ledger file existed. The same command ran on the next attempt. Cause not examined.
- **Unread, listed in the design doc's 6.4 "did not settle" list:** NYC Jobs statute; DDaT ladders other than software developer; the OGL text; O\*NET's "Except as noted below" text; ESCO's licence page; ResumeBench; arXiv 2509.09229's dataset link. This session read none of them.

### Declared, not filed — carried unchanged from the previous handoff; this session re-verified none of it (any 'this session' wording in the bullets below refers to an earlier session)


The full set is in `docs/dev/handoffs/gate-skips-linked-worktrees.md` and, behind it, `docs/dev/handoffs/dependabot-triage-item.md` and `docs/dev/handoffs/data-root.md` "Carried from earlier handoffs" (about 40 bullets). Not re-copied.

- **`maintainer-lane.md` §"Starting a session from a handoff" step 2 gives the template as bare `AGENT_HANDOFF_TEMPLATE.md`; the validator needs `docs/dev/AGENT_HANDOFF_TEMPLATE.md`.** Re-observed this session: the bare name returned `template not found: AGENT_HANDOFF_TEMPLATE.md under the repo root`, exit 2. The previous handoff warned about it and the maintainer-lane text is unchanged. See the recurrences section. Not fixed (outside item 137's scope).
- **(Resolved, observed this session: `git branch -a` no longer lists them.) Two merged remote branches were reported:** `origin/chore/wiki-checkpoint-pass` (PR #189) and `origin/fix/llm-call-provenance` (PR #188), though the close-out text says the remote copy is auto-deleted on merge. Seen in `git branch -a` at session start; cause not examined (a stale remote-tracking ref without `fetch --prune`, or the repo's delete-on-merge setting being off, are both untested).
- `capture-smoke.yml` failed its last three monthly schedules (2026-08-01, 09-01, 10-01); cause not examined. `release.yml` and `docker.yml` have no workflow runs at all (item 171).
- A stray empty directory `.claude/worktrees/interesting-engelbart-27c56d` (not a registered worktree), and a git stash `stash@{0}` that belongs to another session. Neither touched. Not re-checked this session.
- `origin/fix/eval-results-test-leak` still appeared in `git branch -a` after PR #192 merged (observed this session); cause not examined (a stale remote-tracking ref without `fetch --prune`, or delete-on-merge off).
- `scripts/check_docs_site_mermaid.py` reads a prebuilt `docs-site/out/` and does not check that it is current (see the recurrences section). The `docs-site/out/` on this machine is dated 2026-10-01.

---
## Recurrences observed this session → guardrail authored

1. **A piped command's exit code hid a failing check and a commit shipped the failure** (`mypy . | tail -1 && git commit`). This is `reference-pytest-exit-through-pipe`'s class, second variant; the first handoff to name it was seven sessions ago. **No new mechanism authored:** the quality gate (`python -m scripts.gate`) already runs `mypy .` and fails closed, so the defect could not have reached `main`, and the `ruff-changed` commit hook runs ruff only. A hook that ran mypy on staged files is possible and was **not built**: it would add about a minute to every commit. The local rule (check each tool by its own exit code, never through a pipe) is prose and **unenforced**. Surfaced here; the memory note is updated.
2. **`verify-binary-on-path` blocked a commit message containing an apostrophe** — item 53's class (quote-parity tracking ignores heredoc semantics). **No mechanism authored:** item 53 is the open home and the workaround (`git commit -F <file>`) works. Surfaced here.
3. **The interrogative witness paused edits on directive work four times**, each after a subagent hand-back or at the first write of a turn — item 169's class. **No mechanism authored:** a stricter classifier cannot be deterministic (charter C-0). Surfaced here.
4. **The wiki scribe wrote overstated prose again, and I added an unsupported claim myself** (items 168 and 178's class). The layers worked in order: the cite check, my review, the auditors; the one claim all three earlier layers missed was caught by the auditor. **No new mechanism authored:** the review step is prose and **unenforced**, and this pass again could not measure the auditor's catch rate because the review ran first.
5. **A Windows encoding trap with a misleading symptom** (`-X utf8` not reaching child processes) cost a re-run. **No mechanism authored, and none is possible by gate:** the failure is in how a developer invokes pytest, not in a file; the memory note carries it (**unenforced**).
6. **The local-gate-versus-untracked-files class (item 52) did not recur:** everything was committed and `git ls-files --others --exclude-standard` was empty before the gate ran. That is a manual step, **unenforced**; `scripts/gate.py` refusing when untracked files exist is still unbuilt and is the owner's call (item 52).

---
## What this branch should build

**Nothing is queued on this branch beyond landing it.** The owner chooses what follows; this list is the closing agent's **recommendation for order, not a decision.**

1. **Ask the owner to confirm the push, then land this branch.** State what becomes public: this branch's commits (`git log --oneline main..HEAD`) and nothing else from local `main`. Then `git push -u origin feat/eval-dataset-format` → `gh pr create` → `python -m scripts.ci_wait <n>` and read its own `CI_WAIT_EXIT=` marker (exit 0 only; 3 means green-after-retries, stop and look; never trust the task notification's exit field) → `gh pr merge <n> --merge` with the owner's confirmation → `git checkout main && git pull --ff-only` → regenerate and check the pointer → `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Put the owner's questions to them:** the USAJOBS route (design doc 6.5, three questions), whether to close item 182 now, and whether to approve 3b's spend. None blocks the others.
3. **Build step 3b, `feat/eval-dataset-v1` (item 191),** when the owner approves it and its spend: read `docs/dev/blast-radius/eval-dataset-format.md` first (its Deferred list is 3b's work list), then design doc 5.4 and 6.4. **Enumerate consumers first.** The first paid command is `python -m evals.golden_author --profession <p> --level <l> ... --max-spend <usd> --confirm-paid`, run after `--help` and a dry run without `--confirm-paid`, and only with the owner's approved cap. Re-read the DDaT ladders and the O*NET database files' terms before relying on them.
4. **Item 177 points 12 and 13, then 2 to 11**; **item 25's status**; the remaining item 7 decisions; items 175, 140, 178 and 179's closure.
5. **Item 176**, when the owner wants the 44 fold-ins done (re-verify each fact before writing it).
6. **Carried, in the previous order:** the wiki-obligation gate (C-11); the handoff-ledger-vs-board check; the untracked-files preflight in `scripts/gate.py` (item 52); the app-side race; item 171 after Q1 to Q4; `capture-smoke.yml`'s three failed scheduled runs; item 145's branch 2; the open product bugs 130, 105, 131, 107, 134, 139, 98, 99; the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---
## First move

Run the pointer check (**the whole line, with its `Handoff:` prefix**), then `--event consumed` on this handoff (**the template path is `docs/dev/AGENT_HANDOFF_TEMPLATE.md`**), then check `gh pr list` and `git log --oneline -3` on `main` for this branch's merge state (this file predates it). If a Bash call is refused with "The server-side auto mode classifier gave no verdict", issue it again once, unchanged: nothing ran. **Run every check by its own exit code, never through a pipe,** and run pytest with `PYTHONUTF8=1`. Then ask which item to take; the recommendation is to land this branch (with the owner's go to push), then the 3b decisions. Create that branch off `main`, write a plan at the path the harness names (**check the path the harness gives you before writing**), and show it to the user before touching any code. **Do not code first.**

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
