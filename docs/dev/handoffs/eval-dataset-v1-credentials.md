<!-- provenance: schema=1 session=6943dcdd-2597-4232-9998-b7af21c064c2 branch=feat/eval-dataset-v1-credentials commit=f0f4461 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-29 -->

# Agent handoff — item 194 findings 1 and 2 built: entry-tier credentials bound to the career start, a fail-closed check for a posting that prefers a credential the facts do not name, 26 cells regenerated for $1.88 (branch `feat/eval-dataset-v1-credentials`); the push was authorized in chat ("push when green"), a PR and the merge need the owner's go; then the owner chooses item 194's remaining scopes

**Branch to create:** none queued. The next branch is chosen by the owner after this one lands; the candidate is item 194's scopes 3 to 6 (the calibration run, tier sizes, retiring `evals/fixtures/synthetic/`, the freeze), off `main`, after this branch has merged. Do not start it before then.
**Base branch:** `main`

> **This session (`6943dcdd-2597-4232-9998-b7af21c064c2`) took the previous handoff, `eval-dataset-v1-finish`, pruned what it left, and built item 194's findings 1 and 2 on `feat/eval-dataset-v1-credentials`.** Planning ran on Opus 5.5 (plan mode, `~/.claude/plans/handoff-docs-dev-handoffs-eval-dataset-v-shimmying-feigenbaum.md`, approved before any code) and the build on Opus 5.5 and Sonnet 5.5. The handoff pointer was checked and consumed on `main` (`check_handoff_pointer: OK`, then `--event consumed`).
> - **Prune, at the start (owner's approvals in chat):** `feat/eval-dataset-v1-finish` (merged in PR #205) deleted with its stale remote ref; the local-only backup branch `docs/eval-redesign-pre-scrub` deleted; `stash@{0}` (an older draft of the Epic C C2 run-detail modal, superseded by `8bf95a6`) dropped; the empty `.claude/worktrees/interesting-engelbart-27c56d` removed. The 15 `origin/dependabot/*` branches each have an open PR and were left.
> - **Owner decisions this session (chat, 2026-10-29):** finding 1, bind entry-tier credentials to the career start (option 1); finding 2, a fail-closed check plus regenerating only the cells it flags (option 2); finding 3, the employer pool, **accepted for v1** (invented names in a backend eval dataset, no effect on any score); a **total author-spend cap of $14.00 for this work** (the call log read $11.2104 on entry); and "push when green".
> - **The push:** at writing the branch is **not pushed**; the push follows this commit, so check `git ls-remote --heads origin feat/eval-dataset-v1-credentials` and `gh pr list`. It makes this branch's commits public (code, tests, docs, and 26 regenerated cells with their fixtures and 36 re-derived pair fixtures, all invented text). **No PR is open; opening it and merging need the owner's confirmation.**
> - **Built:** (1) `build_profile` (`evals/golden_set.py`): an entry-tier credential's cap is the year of the earliest role, replacing the old rule that left it uncapped (23 credentials in 22 cells were dated after the career began; in 11 the posting required it). Tests first; they failed on the old builder (10 of 24 professions on the real matrix; 18 of 40 synthetic entry cells). (2) New `check_jd_credential_status` in `evals/golden_set.py`, called by `check_prose` (so `golden_set check` and CI fail on a stale cell) and by `author_cell` in `evals/golden_author.py` (inside the one-rewrite budget): a JD sentence naming a credential and saying "prefer" is refused when the facts name none above the cell's tier. It named exactly 4 cells (`accounting-senior`, `carpenter-foreman-lead`, `construction-pm-senior`, `logistics-driving-lead`). The builder's required and preferred phrases became shared constants (`CERT_REQUIRED_PHRASE`, `CERT_PREFERRED_PHRASE`); the briefs are byte-identical. 11 new tests (`TestJdCredentialStatus`) plus an entry-tier test and the two credential tests tightened. The consumer dossier is `docs/dev/blast-radius/eval-dataset-v1-credentials.md` (written before the first code edit; it holds every measurement). The README, CHANGELOG, design doc §6.4, item 194 and a wiki log "verified no-edit" entry are updated.
> - **Regenerated:** 26 cells (the 23 whose profile changed plus the 4; `accounting-senior` is in both), none rejected; 36 pair fixtures re-derived; one pair's authored `transferable` term re-picked (see the ledger below). `golden_set check` prints `OK (96 cells)`. Both audits over the 96 cells read 0 (credentials dated after their role: 22 cells before; unbacked "preferred" credential sentences: 4 before). The `prompt_version` of every committed cell is still `golden-author-2`, effort `medium`.
> - **Spend:** one pilot cell ($0.0973) and a 25-cell sweep ($1.7790) = **$1.8763 over 29 requests** (three cells needed one rewrite); the call log reads **$13.0866 of the owner's $14.00**, leaving $0.91. The recorded-cost projection was $1.8469. The one `sales-senior` request of item 191 that a laptop standby cut off may have billed; the call log cannot say, so true spend may be a little above the log.
> - **Hand-read:** the whole of `accounting-senior`, `teacher-entry` and `logistics-driving-lead`, plus every credential year against its role start and every posting sentence naming a credential in all 26 regenerated cells. No contradiction left. The earlier sample stands: 23 of the 96 cells were read whole before this branch; 3 more now, so **26 of 96 have been read whole by someone**, and 70 have not.
> - **Gate:** `python -m scripts.gate` ran on the clean tree at `f0f4461` (everything committed). The log's own marker is `gate: all steps passed.` then `GATE_EXIT=0`, and `python -m scripts.gate --result` printed `PASSED on this tree -- exit 0, failed step None, finished 2026-10-29T17:06:52-0700, HEAD f0f4461`. Steps run: hooksPath preflight, memory preflight, ruff check, ruff format, mypy, `pytest -m "not ux" -n auto` (4310 passed, 9 skipped in 669.77s), `pytest -m ux` (189 passed, 4319 deselected, 2 xpassed in 651.19s), `work_items check`; **0 `RERUN` marker lines**. The first attempt was killed by the low-memory reaper at the pytest step and is not counted. **Commits after the gate:** this handoff and its ledger event only; `--result` goes `STALE` after them and CI is the final authority.
> - **Not verified:** (1) 70 of the 96 cells have not been read whole by anyone. (2) The status check is a word list (see the ledger). (3) The three rewrites' reasons were not read. (4) No calibration run has scored the set, so the rate of `scenario_misaligned` runs and everything about the judge are unmeasured. (5) The lower effort levels were not tried. (6) The DDaT ladders and the OGL text were not read. (7) The wiki entry is a read for contradiction, not a grounding audit.
> - **Branch state at writing:** 4 commits ahead of `main` (`6b93e7c`) before the one commit that adds this handoff and its ledger event (5 after it): `f690e8f` the dossier and the consumed-event ledger file, `5189fa4` the builder, the check and the tests, `e2684b2` the regenerated data, `f0f4461` the docs.

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

- Everything through item 194's scopes 1 and 2 ✓ (PR #205, merge `6b93e7c`, MERGED): the facts for 24 professions, the guarded generator, 96 cells and 36 pairs, and the first round of credential fixes.
- **`feat/eval-dataset-v1-credentials`** ← this branch (item 194, findings 1 and 2): built, gate green (see the preamble), handoff written. Landing it needs the owner's go to open the PR; then `python -m scripts.ci_wait <n>`, `gh pr merge <n> --merge`, `git checkout main && git pull --ff-only`, the pointer, the prune. Item 194 stays `open` for scopes 3 to 6.
- **Next, once this branch has landed:** item 194's remaining scopes, in the item's order: (3) the calibration run (its own spend ask: judge calls and a full-pipeline run; the $14.00 covers none of it), (4) tier sizes from the measured cost, (5) retire `evals/fixtures/synthetic/` (**re-derive the consumer list first**, it was never re-derived), (6) freeze `golden-v1` plus a history check. Items 184 (step 4) and 10 depend on it. **No cell may change after the calibration run**: it scores this set.
  Other candidates: the rest of item 177; item 25's status; item 176; the six item 7 decisions; items 175, 140, 179's closure; item 178's mechanism; item 145's branch 2 and 3 (not started); item 171 (waits on four owner answers).

**Do not start the cut, the version bump or the CHANGELOG cut.** Item 10 depends on 3, 6, 7, 9, 19, items 181 to 186, 191 and 194, and on the owner's alpha approval.
**Do not spend on the author model, run the calibration run, the candidate A/B (item 137), or any paid eval or capture, without the owner's spend approval.** The approval on record is **$14.00 total on `golden_author` for findings 1 and 2** (2026-10-29), of which **$13.0866 is logged**; it covers no calibration run, eval or capture, and a further regeneration needs a new cap.
**Do not build a USAJOBS fetch, register a key, or commit any third-party posting or résumé text** (decided 2026-10-27, design doc 6.5). **Do not edit `evals/fixtures/synthetic/`** until item 194 retires it. **Do not hand-edit a golden cell, a facts file or the manifest hashes:** `python -m evals.golden_set check` rebuilds every generated cell from its facts and refuses a mismatch; change the facts or the builder, delete the stale cells and regenerate them under the caps. The `transferable` terms of a pair are authored manifest fields (write them with `load_manifest` / `write_manifest`, then run `pairs`, `manifest`, `check`).
**Do not move a pin** (`SONNET_MODEL`, `HAIKU_MODEL`, `JUDGE_MODEL`, `AUTHOR_MODEL`); the judge is chosen at step 9 (item 189). **Do not add a `THINKING_POLICY` row for `claude-opus-5-5`.** **Do not close items 175, 178, 179 or 137 on your own.** **Do not build item 171's workflow before the owner answers its four questions.**
**Do not edit `evals/catalog/costs.json` or `evals/prompt_hashes.json` by hand** (re-measure with `python -m evals.eval_catalog measure --write`). **Do not change `AUTHOR_SYSTEM_PROMPT` or `build_user_prompt` without bumping `AUTHOR_PROMPT_VERSION`** (the test pins both hashes), and a bump means regenerating every cell so the set stays single-version.
**Do not register the design doc in `scripts/doc_registry.py`** (decision 8). **Do not start item 145's branch 2 or 3.** **Do not delete any further memory file** without the owner's approval of the specific rows (item 7). **Do not change the server's threading** or item 25's status on your own. **Do not delete `evals/results/_test_stubs_quarantine/`** without the owner saying so. **Do not change the `analyze_*` cache breakpoint** (Finding 2 in item 137).
**Do not write into spolia, the-factory or isidium from a sartor session.** Anything for them goes as a proposal the owner carries.

---

## What just landed on `main`

**Nothing from this branch is on `main` as of writing.** `main` is at `6b93e7c` (PR #205, item 194 scopes 1 and 2: three credential faults fixed, 40 cells regenerated, the first hand-read). Before it: #204 (`b62c704`, item 191 built), #202 (`77decd4`, items 182, 183 and 193 closed), #201, #200, #199. If this branch's PR merged, `git log --oneline -3` on `main` shows it; the merge is a merge commit (squash and rebase are disabled on the repo).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. Header, read from the board on this branch: **Open 27 / 10 ceiling -- OVER** | Blocked 4 | Deferred 9 | Watching 46 | Epics 7 | Closed 96

**Changes from the previous handoff:** no item was opened or closed on this branch (`python -m scripts.work_items check` printed `work_items: OK (194 files)`, and the board header above is unchanged); item **194** is updated (findings 1 and 2 built, finding 3 accepted for v1, scopes 3 to 6 still open) and item **191** stays `open` for the owner to close after the merge it already had. The still-open items other than 191 and 194 are unchanged from the previous handoff and are listed there (`docs/dev/handoffs/docs-close-eval-items-182-183-193.md`, section "Carried-forward observations": `## Open` 21, `## Blocked` 4, `## Deferred` 9, `## Watching` 46); they are not re-copied here because none changed, and the board is the authority. The board is over its ceiling and the owner's direction stands: drawdown to 0 if possible before alpha staging.

### Decisions the owner owes, new from this session

- **Whether to try `AUTHOR_EFFORT = "low"` (carried, owner's call):** the owner kept `medium`; a different effort would mix recorded settings across cells unless all are regenerated.
- **Did the cut-off `sales-senior` request bill? (carried, unknown):** the call log cannot say; the provider's usage page can. If it did, true spend is a little above the logged $11.2104.
- **How a pair is graded, and whether results pool across pairs and cells (steps 8 and 9, carried):** the 36 pairs exist; their `expected.json` says the gate is grounding and no invention, not callback, and sets no keyword-coverage minimum, but no code enforces `min_*` keys and the judge sees the whole dict.
- **Per-field results are directional only (carried, a stated limit of the design):** the binomial rule (5 discordant cases in one direction for a one-sided p below 0.05) cannot be met inside one profession (4 cases) and is marginal inside a group (about 24). Written in design doc 6.4.
- **Re-read before relying (carried):** the DDaT ladders for roles other than software developer and the OGL v3.0 text are still unread. The licence forbids the possessive form of the O\*NET name; other prose in the repo may still use it.
- **Pair `transferable` terms are authored, and I re-picked one (new, declared):** `electrician-senior-to-hvac-technician-mid`, `customer` to `installation`, because the regenerated electrician-senior résumé no longer contained `customer` and no skill name was in both documents. `installation` is in the résumé's "Lighting installation" skill and the posting's "thermostat installation". A different reasonable pick exists; the choice is a judgment, not a derivation. (The three re-picked on the previous branch stand.)

### Decisions the owner owes, carried from earlier sessions (this session re-verified none of them)

- **The level ladder and the non-tech levels are authored, not sourced (new, accepted 2026-10-21):** every rule in `manifest.json` has `rule_source = "authored"`; the DDaT ladders for these professions were not read. Revise if a source is found.
- **Opus 5.5 as the author, and no fallback model (new, declared):** chosen by the owner outside both arms of item 137's comparison; a fallback would make the recorded model wrong for the text, so a refusal raises and writes nothing.
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
- **The eval redesign: all eight section 8 decisions and the four follow-on questions (9 to 12) are ANSWERED (recorded in `docs/dev/eval-redesign-design.md` section 8).** Open follow-ons: (a) **USAJOBS: decided 2026-10-27, no fetch** (design doc 6.5). (b) **NYC Jobs:** not targeted (Q12); its open-data statute ruling is parked. (c) With no gold labels (decision 5), step 9's calibration is judge-to-judge agreement only, which shows consistency, not correctness. (d) Haiku 4.5's status was not re-checked; re-check before step 9 picks the judge. (e) Tier sizes (21 / 12 / 96 fixtures plus the pairs) and the per-arm cost are still proposals; step 3b's calibration run measures them.
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


### Declared, not filed — from this session

- **The employer pool is accepted for v1 (owner, 2026-10-29).** 216 roles use 59 invented employer names, 32 of them in two or more professions ("Riverbend Health Network" and "Ironbridge Co" in 8 each); only 5 of the 24 facts files name their own employers. The owner's reason: invented names in a backend eval dataset, no effect on any score. I know of no eval check that reads employer names except the grounding source union; I did not audit every check. A fix (an `employers` list of at least three names in the 19 facts files that lack one, which `_employers_for` already honours) would redraw the employers of 76 of the 96 cells, about $6, and belongs in a `golden-v2`. **The calibration run (item 194 scope 3) scores this set, so any cell change has to land before it.**
- **The status check is a word list** (`check_jd_credential_status`, `evals/golden_set.py`): a JD sentence with `certif|licen[cs]|credential|endorsement|accredit` and "prefer" is refused when no `needs` brief asks for a preferred credential. It misses a paraphrase ("ideally", "a plus"), cannot tell which credential a sentence means, and does not catch a credential called required twice or a second credential required. **Unenforced** for those. Three hits of the facts-based rule were read and are not contradictions (a "Licensure and qualifications" heading in `product-mgmt-senior` and `web-backend-senior`; a negation in `ux-design-senior`).
- **The entry cap is checked by the gate's tests, not before a paid request:** a profile carries names, issuers and years, not which credential is entry-tier, so `_certification_problems` cannot check it. **Unenforced at the point of spend.**
- **Observed, not changed:** `logistics-driving-lead` dates all four credentials 2011 (the year of the first role), including a Dispatch Coordinator Certificate for a supervisor role that starts in 2018. The profile is unchanged by this branch and the cap rules allow it. It reads oddly; whether to tighten the cap for the top tier is the owner's call.
- **I quoted a cost from a regex before running the rule over the whole matrix.** About $0.6 for finding 2 came from a 9-hit scan for "preferred" near a credential word; the broad "credential word in about/duties" rule flagged 35 cells (most consistent; some false positives such as "licensed electricians"), and the facts-based rule flagged 4. The union cost $1.85. Recorded in the memory `paid-generation-ladder`.
- **The builder diff found 23 stale profiles, not the 22 I predicted** (`electrician-senior`: the entry draw moved, and the sorted hand-out shifted a mid-tier year). Every difference in all 23 was a certification year (31 changes), which also shows the hoisted phrase constants left the briefs byte-identical.
- **Three cells needed one rewrite** (`accounting-senior`, `carpenter-foreman-lead`, `logistics-driving-lead`; 29 requests for 26 cells). All three are finding-2 cells, which is consistent with the new check firing on a first reply, but the cell records keep attempts and not the failed text, so that is an inference.
- **The first gate attempt was killed by Claude Code's low-memory reaper** at the `pytest -m "not ux" -n auto` step (free RAM 1.70 GB; the log's `GATE_EXIT=1` was the wrapper's exit). It was not restarted until the owner asked; the second ran clean (see the preamble). Memory notes `shared-machine-oom-kills-bg-runs` and `background-bash-kill-ceiling` apply.
- **A shell loop reported success from its own counter** ("removed 26") while every `git rm` had failed: the cell list was written by Python on Windows with CRLF line endings, so each path ended in `\r`. `ls` showed all 96 cells still present; the loop was rerun with the `\r` stripped and with the counter incrementing only on success. Recorded in the memory `paid-generation-ladder`.
- **The working directory drifted** to `evals/golden/golden-v1` and then `fixtures` after a `cd` in a command that ran there; later commands used absolute paths or an explicit `cd /c/Dev/sartor`.
- **Two processes I did not start are still running:** an orphaned `sh.exe` under `pytest-7339` and its `isidium.signer.page` children (since 2026-10-28). Nothing this session started is left running.
- **Plan-gate friction, no bypass:** the interrogative witness paused the first `Write` after a prompt (twice, on the plan file), each cleared by re-running the identical call; `ExitPlanMode` was refused once by `plan-write-landed` because the paused Write had not landed, and the Write and the `ExitPlanMode` were then run in separate messages. `control()` in `tests/_controls.py` takes a second argument (`what`); Pyright caught the one-argument calls I first wrote.
- **Scratch only, not in the repo:** `regen_cells.txt`, the commit message files, the red/green and sweep logs, and `build_handoff.py` in the session scratchpad. Every audit script was an inline `python -` run.

### Declared, not filed — carried from the item 194 scopes 1 and 2 session (this session re-verified none of it; any 'this session' wording in the bullets below refers to that session)

- **The gate's memory preflight refused three times** (0.45, 0.60 and about 1.1 GB free against a 1.00 GB floor), with WSL (about 1.5 GB), Chrome, VS Code, Spotify and NordVPN the largest users; none was started by this session. The owner chose to run at the margin; the gate was retried only on a preflight refusal. Memory notes `shared-machine-oom-kills-bg-runs` and `never-suggest-wsl-shutdown` apply.
- **A detached `( ... ) &` job inside a background Bash command makes the harness notification fire at once** (the wrapper exited). The job's own log marker (`SWEEP_EXIT=`) was read instead, and a PowerShell waiter on that marker was used for a time-bounded wait. This is the known class in memory `background-bash-kill-ceiling`; run the real process as the foreground of the background command next time.
- **The first paid cell was paid for three times** ($0.0877, $0.0956, $0.0870) because three builder faults were found one at a time by hand-reading it. The free whole-set audit would have shown them together. Recorded in memory `paid-generation-ladder`; the point-of-spend guard covers two of the three (see the recurrences section).
- **Pyright reported `_certification_problems` undefined** between the two edits that added it and its call site; mypy and the tests are the authority.
- **Scratch only, not in the repo:** `consumers.py`, `compare.py`, `predict.py`, `diff3.py`, `cert_years.py`, `audit_titles.py`, `audit_titles_narrow.py`, `entry_residue.py`, `patterns.py`, `pair_terms.py`, `fix_terms.py`, `missing_cells.py`, `sample_plan.py`, `pick_sample.py`, `rm_stale.py`, `gate_retry.sh` and `build_handoff.py` in the session scratchpad, and the two discarded `electrician-lead` outputs.

### Declared, not filed — carried unchanged from earlier sessions (this session re-verified none of it)

- **A pipe hid a failing check and a commit shipped it.** `python -m mypy . | tail -1 && git commit` committed with one mypy-strict error (`__exit__ -> bool`); the next commit fixed it. See the recurrences section. The gate would have caught it at close-out.
- **`python -X utf8` does not reach child processes.** `tests/test_doc_links.py`, `test_doc_frontmatter_gate.py` and `test_doc_single_home_gate.py` failed with `TypeError: ... 'NoneType' and 'str'` under `-X utf8`; they pass with `PYTHONUTF8=1`. In the memory notes.
- **`verify-binary-on-path` false-BLOCKed a commit message with an apostrophe** (item 53's class). Worked around with `git commit -F <file>`, a message written with the Write tool.
- **The interrogative witness paused edits four times** on directive work (the plan stub, a wiki edit pair, a log entry), each cleared by re-running the identical call; a subagent hand-back re-arms it (item 169).
- **A background command's notification reported exit 0 within seconds** while the gate it had launched ran for many minutes (the wrapper's exit, not the gate's). The log's own `GATE_EXIT=` marker was the evidence. A later watcher was reaped under memory pressure and not restarted.
- **The sibling-repo conventions were not re-read this session.** The catalog entry format still follows the earlier subagent report (see the carried section). The `exempt` entry for `dataset_author` uses the format as built.
- **The mypy 'annotation-unchecked' notes** in `tests/test_composition_staleness.py:145` and `tests/test_regenerate_cover_letter.py:278` are pre-existing and not errors.
- **Scratch only, not in the repo:** `make_pilots.py`, `mutate_runner_seeds.py`, `mutate_author.py`, `mutate_reach.py`, `show_fired.py` and `build_handoff.py` in the session scratchpad; the `claude-api` skill was loaded for the Opus 5.5 request rules.

### Declared, not filed — carried from item 182's session (no session since has re-verified it)

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
- (Resolved this session, owner's approvals in chat 2026-10-29.) The empty directory `.claude/worktrees/interesting-engelbart-27c56d` was removed; `stash@{0}` (an older draft of the Epic C C2 run-detail modal, superseded by `8bf95a6` / PR #148) was dropped; the local-only backup branch `docs/eval-redesign-pre-scrub` (tip `27bac3f`, the pre-rewrite history of PR #194) was deleted and is recoverable from the reflog for about 90 days.
- `origin/fix/eval-results-test-leak` still appeared in `git branch -a` after PR #192 merged (observed this session); cause not examined (a stale remote-tracking ref without `fetch --prune`, or delete-on-merge off).
- `scripts/check_docs_site_mermaid.py` reads a prebuilt `docs-site/out/` and does not check that it is current (see the recurrences section). The `docs-site/out/` on this machine is dated 2026-10-01.

---

## Recurrences observed this session → guardrail authored

1. **A deterministic check passed data that a person could see was wrong** (the known class: the previous handoff's recurrence 1, now a second branch). The two faults of this branch were an entry-tier credential dated after the career began and a posting that calls a credential preferred when the facts name none. **Mechanisms authored, each failing on the old code or the old data first:** `check_jd_credential_status` in `evals/golden_set.py`, called by `check_prose` (so `golden_set check` and CI refuse a stale cell) and by `author_cell` in `evals/golden_author.py`; `TestJdCredentialStatus` (11 cases) and `TestCertifications::test_an_entry_tier_credential_is_dated_no_later_than_the_first_role` in `tests/test_golden_set.py`; and the exemption removed from `tests/test_golden_facts.py::test_a_cells_credentials_are_asked_dated_and_ordered_like_a_real_career` (10 of 24 professions failed on the old builder). **Not covered, and said plainly:** a paraphrase of "preferred", a credential called required twice, the entry cap at the point of spend, and whether prose reads as real at all. **Unenforced** for those; surfaced above.
2. **The whole-matrix audit before the first paid cell** (the previous handoff's recurrence 2). This session ran it by hand: both measurements over all 96 cells before any paid request, which is what showed the broad rule would have flagged 35 cells and the regeneration set was 26. **No mechanism was authored** that makes a session do it; the candidate remains a `golden_author` preflight that runs the matrix invariants of `tests/test_golden_facts.py` over every cell it is about to write. Surfaced to the owner here; **unenforced.**
3. **A cost was quoted before the candidate rule was run over the whole matrix** (about $0.6 from a 9-hit regex; the broad rule flagged 35 cells, the facts-based rule 4). A known class (an estimate not grounded in the full data). **No mechanism:** a prose estimate cannot be gated. Recorded in the memory `paid-generation-ladder`; **unenforced.**
4. **A prediction in prose differed from the instrument by one** (22 predicted, 23 measured by `golden_set check`; the previous handoff's recurrence 4 was the same class). The instrument held: it names the real set before any spend. **Unenforced** for the prediction itself.
5. **A shell loop reported success from its own counter while every command inside had failed** (the CRLF cell list; "removed 26", 96 cells still present). The known class of reading success from a wrapper or counter instead of the result (memory `background-task-exit-code-unreliable`). Caught by an `ls` count. **No mechanism authored**; the rerun counted successes only. **Unenforced.**

---

## What this branch should build

**Nothing is queued on this branch beyond landing it.** The owner chooses what follows; this list is the closing agent's **recommendation for order, not a decision.**

1. **Land this branch.** The push was authorized in chat ("push when green"); check `git ls-remote --heads origin feat/eval-dataset-v1-credentials`. Then, with the owner's confirmation: `gh pr create` → `python -m scripts.ci_wait <n>` and read its own `CI_WAIT_EXIT=` marker (exit 0 only; 3 means green-after-retries, stop and look; never trust the task notification's exit field) → `gh pr merge <n> --merge` → `git checkout main && git pull --ff-only` → regenerate and check the pointer → `git branch -d`. Authority: `docs/dev/maintainer-lane.md` close-out.
2. **Item 194, scopes 3 to 6** (`feat/...` named when chosen), in the item's order, after this branch has merged. **Enumerate consumers first** (a dossier under `docs/dev/blast-radius/`), because the `synthetic/` retirement touches the runner, eight gate tests, a CI job, four catalog TOMLs and a hash-locked prompt line, and that list was never re-derived. The calibration run is its own spend ask. **No golden cell changes after it.**
3. **The `golden_author` whole-matrix preflight** (recurrence 2), if the owner wants the audit made a gate rather than a habit.
4. **Item 177 points 12 and 13, then 2 to 11**; **item 25's status**; the remaining item 7 decisions; items 175, 140, 178 and 179's closure.
5. **Item 176**, when the owner wants the 44 fold-ins done (re-verify each fact before writing it).
6. **Carried, in the previous order:** the wiki-obligation gate (C-11); the handoff-ledger-vs-board check; the untracked-files preflight in `scripts/gate.py` (item 52); an in-repo mutation harness for the golden-set rules; the app-side race; item 171 after Q1 to Q4; `capture-smoke.yml`'s three failed scheduled runs; item 145's branch 2; the open product bugs 130, 105, 131, 107, 134, 139, 98, 99; the *(owner)* items.

Scope is bounded to what the owner names from this list. Do not expand beyond it.

---

## First move

Run the pointer check (**the whole line, with its `Handoff:` prefix**), then `--event consumed` on this handoff (**the template path is `docs/dev/AGENT_HANDOFF_TEMPLATE.md`**), then check `gh pr list` and `git log --oneline -3` on `main` for this branch's merge state (this file predates it). If a Bash call is refused with "The server-side auto mode classifier gave no verdict", issue it again once, unchanged: nothing ran. **Run every check by its own exit code, never through a pipe,** and run pytest with `PYTHONUTF8=1`. If a Bash command contains two consecutive backslashes the guard will block it: write the script with the Write tool and run it by path. **A list file written by Python on Windows has CRLF line endings: strip the `\r` before using it in a shell loop.** Then ask which item to take; the recommendation is to land this branch (with the owner's go to open the PR), then item 194's remaining scopes. Create that branch off `main`, write a plan at the path the harness names (**check the path the harness gives you before writing**), and show it to the user before touching any code. **Do not code first.**

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
