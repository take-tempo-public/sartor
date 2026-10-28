# Blast radius — eval-dataset-v1

> **Branch:** `feat/eval-dataset-v1` (item 191, eval redesign step 3b-ii)
> **Status:** enumeration complete at `77decd4` (`main`), written before the first code edit. This branch changes the
> generator's guards and CLI, adds the facts for about 24 professions and three authored families, replaces the three
> converted pilots with generated cells, and runs the paid generation in stages. The calibration run, tier sizes,
> retiring `evals/fixtures/synthetic/` and the freeze move to a follow-on item (owner's staging direction, 2026-10-28:
> no run that has to be repeated, no stall that is paid twice, stepwise learning).

---

## Surface

Changed (none is on the `scripts/enforcement/blast_radius.py` registry, which has no golden path, so no hook fires and
this dossier is the prose-binding C-10 step):

- `evals/golden_set.py` — `validate_facts` (an optional `level` on an industry; one per tier when any has it), a small
  `industries_for(facts, level)` helper next to `build_profile`. `build_profile`'s signature is unchanged.
- `evals/golden_author.py` — `main` (new flags, a total-spend cap read from the call log, resume, a rejects directory, a
  consecutive-failure stop), `author_cell` (a render dry-run before a reply is accepted), the request's client options.
  `AUTHOR_SYSTEM_PROMPT` and `build_user_prompt` are **not** touched, so `AUTHOR_PROMPT_VERSION` stays `golden-author-1`.
- `evals/golden/golden-v1/manifest.json` — three new families, about 21 new `professions` rows, `pilot_waivers` emptied,
  the pilot `pairs` replaced; later `files` re-stamped by `python -m evals.golden_set manifest`.
- `evals/golden/golden-v1/facts/*.json` — new directory, about 24 files. Already hashed by `tracked_files`.
- `evals/golden/golden-v1/cells/`, `fixtures/` — the three converted pilot cells and their fixtures and both pilot pairs
  are deleted; generated cells and derived pairs are added.
- Tests: `tests/test_golden_set.py`, `tests/test_golden_author.py`, `tests/test_eval_golden_runner.py`,
  `tests/test_golden_reachability.py`.
- Docs: `evals/README.md`, `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` (6.4), work items 191 and a new follow-on.

Not touched: `evals/runner.py`, `evals/eval_catalog.py`, `evals/fixtures/synthetic/`, `blueprints/diagnostics.py`,
`analyzer.py` (reads `LOG_DIR` only), `hardening.py`, any pin, `PROMPT_VERSION`, `docs/governance/`.

---

## Enumeration

Greps with the Grep tool on 2026-10-28 at `77decd4`. Counts are from the tool output.

```
Grep "validate_facts|ladder_for|\bbuild_profile\(|industries="  (*.py,md,toml,json, whole tree)      -> 5 definitions/uses in evals/, 40 test lines, 6 doc lines
        golden_set.py: validate_facts :1382, ladder_for :762, build_profile :1504
        golden_author.py: ladder_for :355, build_profile :356 (the only non-test caller)
        tests: test_golden_set.py (~38 lines), test_golden_reachability.py :308, test_golden_author.py :166
Grep "golden_author|AUTHOR_PROMPT_VERSION|AUTHOR_MODEL|EXIT_OVER_BUDGET|max-spend|confirm-paid"
        (whole tree minus handoffs, ledger, results, .git, count)                                      -> 182 hits, 30 files
        code/tests that read it: analyzer.py 1, hardening.py 1, evals/eval_catalog.py 4, evals/runner.py 15,
        evals/golden_set.py 1, evals/catalog/dataset_author.toml 2, tests/test_call_kind_telemetry.py 2,
        tests/test_golden_reachability.py 4, tests/test_eval_spend.py 8, tests/test_golden_author.py 32,
        tests/test_eval_catalog.py 3, tests/test_model_overrides.py 1
Grep "pilot_waivers|\"pairs\"|\[\"families\"\]|\[\"professions\"\]|get\(\"professions\""  (*.py,toml,yml)    -> golden_set.py 8 sites, tests 4 files
Grep "borealis-labs|lattice-cloud|atrium-health|data-ml-entry|sre-ops-mid|product-mgmt-senior"
        (whole tree minus handoffs, ledger, results, evals/golden, .git, count)                        -> 6 hits, 5 files
        CHANGELOG.md 1, eval-golden-breadth.md 1 (historical), test_eval_golden_runner.py 1,
        test_golden_reachability.py 1, test_golden_set.py 2
Grep "golden" in scripts/                                                                              -> scripts/wiki_relevance.py :58-60 only
Grep "golden_set|golden_author|golden-v1" in tests/test_data_root.py                                   -> :282 (a reason string)
Grep "golden" in tests/test_eval_catalog.py                                                            -> :34, :67 (`_SUITE_DIRS`), :238 (the author pin)
Grep "golden|logs/" in .gitignore                                                                      -> `logs/` (:48); no golden entry
```

Call log, measured 2026-10-28: `logs/llm_calls.jsonl` is 576,562 bytes, 1,564 rows, **0 rows with `call="dataset_author"`**
(so no real author call has ever been made on this machine). `analyzer.LOG_PATH` and `evals.runner.LLM_LOG_PATH` are both
`sartor_home.data_path("logs", "llm_calls.jsonl")`: one file under two names. A full scan at start costs milliseconds at
this size; a byte-offset scan between cells (the pattern of `runner._log_offset` / `_trace_cost`) costs only the new rows.

Negative results (also findings):
- **0** consumers of `facts/` outside `golden_author.main` and `golden_set` (the directory does not exist yet). No wiki
  page cites a `facts/` path.
- **0** readers of `manifest["pilot_waivers"]` outside `golden_set.check_suite` and two tests; `evals/runner.py` and
  `evals/eval_catalog.py` never read the manifest.
- **0** hits for `golden` in `.github/`, `pyproject.toml` and `.githooks/`: CI does not run `python -m evals.golden_set
  check`; it is covered only by `TestCommittedSuite` inside the gate's pytest run.
- `golden_author` is imported by `evals/runner.py:88` and `evals/eval_catalog.py:339`, so **an import error in
  `golden_author` breaks the whole eval runner**: every edit is followed by `python -c "import evals.runner"`.

Found while enumerating (each changes the plan):
1. **A paid reply can be lost after payment.** `render_fixtures` calls `pick_edit_target` (`golden_set.py:463-476`) on the
   iteration target slot (`r1.b2`, a no-number bullet of 8 to 40 words). It raises `ValueError` when the text has no
   stretch of five words between commas, semicolons, colons or brackets. `author_cell` checks each slot with
   `check_slot_text` only, `check_prose` is the same rule set (read, `golden_set.py:385-404`), so the text passes, the
   cell is returned and paid for, and then `gs.write_cell` (`golden_author.py:399`, outside the `try`) raises an
   uncaught `ValueError`: a traceback, no cell written, the prose gone, and the cost never added to `spent`.
   Decision (as built): `pick_edit_target` is the only text-driven raise in the render path (read: the other is an unknown
   section kind), so `author_cell` runs it on the iteration target slot in the same pass as `check_slot_text` and counts a
   `ValueError` as a failure of that slot; the rewrite request repairs it inside the same attempt budget. A
   `render_fixtures` call after acceptance is a backstop, and `main` also catches `ValueError`/`OSError` from `write_cell`
   and keeps the prose. Observed: with the unmodified code, a comma-split reply is accepted after one request
   (`tests/test_golden_author.py::TestRenderBeforeAccepting::test_such_a_target_is_rewritten_alone_in_the_same_cell`
   failed first, `assert 1 == 2`).
2. **A failed attempt is invisible to the cap.** `spent` (`golden_author.py:386`) is per invocation and adds a cell's
   cost only on success. A cell rejected after two requests is paid for and uncounted. And `log_judge_call` with
   `response=None` records zero tokens, so a request that errors client side (a timeout after the server began
   generating) is **unpriced in the log** and cannot be counted at all. Stated limit; the mitigation is fail-fast.
3. **The client has SDK defaults.** `runner._get_client` (`evals/runner.py:237-245`) builds `anthropic.Anthropic(api_key)`:
   a 600 s timeout and 2 automatic retries, none of which writes a row. A hang can be re-sent and billed twice, and
   only the last attempt is logged.
4. **Every generated profile carries an `iteration`** (`build_profile`, `iteration.mode = "derived"`), so every fixture's
   `expected.json` gets `iteration_scenarios` and `iterate_clarify` fires for every fixture in generate mode. That
   raises the per-fixture price of an eval run and is the follow-on item's cost input; it is not an authoring cost.
5. **Four tests are tied to the three pilots by name** (Consumers 12 to 15 below) and must move with the cells.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/golden_set.py:1382-1441` `validate_facts` | update | accept an optional `level` on each `industries[]` entry; when any entry has one, exactly one entry per tier and no entry without one. Facts without any `level` validate as before, so `FACTS`/`CERT_FACTS` in the tests are unchanged. |
| 2 | `evals/golden_set.py` `build_profile`, the `chosen = ...` line (was `:1647`) | update (default only) | an explicit `industries=` still wins; otherwise `industries_for(facts, level)`; otherwise the first two as before. The signature is unchanged, so no caller changes and facts without tiers build byte-identical profiles (the pinned prompt hash and `cell_seed_for` tests prove it). |
| 3 | `evals/golden_set.py` new `industries_for(facts, level)` | new | returns `[slug]` for a tier's entry, or `None` for facts that name no tiers; the single place the rule lives. |
| 4 | `evals/golden_set.py:762` `ladder_for`, `:775` `_check_ladders` | no change | families are data; three more families pass the same checks (four tiers, `rule_source`, `label`, years, roles fit). |
| 5 | `evals/golden_set.py:1012-1091` `check_suite`, `:1055-1063` waivers | no change | with `pilot_waivers = []` and every cell generated, no predicate fails and no waiver is stale. A draft suite stays valid at every intermediate state (a partial set passes). |
| 6 | `evals/golden_set.py:945-1010` `_pairs_wanted`, `check_pairs`, `write_pairs` | no change | re-derive each pair from its two fixtures; the old pairs are removed from the manifest in the same commit as the pilot cells, new ones added after the cells exist (step 7), so no commit has a pair naming a missing fixture. |
| 7 | `evals/golden_set.py:463-476` `pick_edit_target` and `:479-502` `render_expected` | no change | the defect is handled at the caller (finding 1), not by loosening the rule: the edit target must survive generation. |
| 8 | `evals/golden_author.py` `author_cell`, `AuthorError`, `AuthorRejected` | update | the iteration target is checked with `pick_edit_target` per slot, a `render_fixtures` backstop follows acceptance, and every `AuthorError` carries `usage`, `replies` and `request_ids` (finding 2). Callers of `author_cell` (Grep `author_cell\(`, 26 hits in 3 files): its definition and `main`, 24 in `tests/test_golden_author.py` and `tests/test_golden_reachability.py`. |
| 9 | `evals/golden_author.py` `main` and its argument list | update | adds `--cell P:L` (repeatable), `--skip-existing`, `--max-total-spend` (required with `--confirm-paid`), `--max-consecutive-failures` (default 2); `--profession`/`--level` become optional but go together; `logged_spend`, `cost_of_usage`, `_keep_reject` are new. `--max-spend` stays (this run's cap). Exit codes 0, 1, 3, 4 keep their meanings; a batch now continues past a rejected cell (up to the limit) and exits 1 at the end. A missing or unreadable facts file is now a message and exit 1, not a traceback. |
| 10 | `evals/golden_author.py` the client in `main` | update | `runner._get_client().with_options(timeout=AUTHOR_TIMEOUT_SECONDS, max_retries=0)`. `AUTHOR_TIMEOUT_SECONDS = 420` is **unobserved** (no real call has been timed); the first paid cell's latency revises it. `AUTHOR_MAX_TOKENS`, effort and thinking settings are unchanged and the pinned-prompt test covers the prompt bytes. |
| 11 | `evals/runner.py:237-245` `_get_client` | no change | other callers (judges, the runner) keep the SDK defaults; the author narrows its own client with `with_options` instead of changing a shared helper. |
| 12 | `tests/test_eval_golden_runner.py:30,53-57,142,205-222` `PILOT_CELLS` and the counts | update | replaced by counts derived from the committed manifest; the "pair runs on its résumé's cell" mapping stays. |
| 13 | `tests/test_golden_reachability.py:266-301` `TestCommittedPilots` | update | the waiver assertion goes (no waivers); the "iterating pilot" assertion (`sre-ops-mid--lattice-cloud`, exactly one `iterate_clarify`) is replaced: every generated fixture iterates (finding 4), so it asserts one `iterate_clarify` per fixture that has `iteration_scenarios`. |
| 14 | `tests/test_golden_set.py:1121-1224` `TestWaivers`, `TestConverter`, `TestParser`, and `:1255-1280` `TestCommittedSuite` | update / keep | the converter tests read `evals/fixtures/synthetic/` and stay until that directory is retired (follow-on); they build in `tmp_path`, not the committed suite. The pair assertions at `:1263-1279` name the pilots and are rewritten to the new pairs. |
| 15 | `tests/test_golden_author.py:355-460` `TestCommandLine` | update | `--max-total-spend` becomes required with `--confirm-paid`; the helper `_args` and five tests pass it. New tests: resume, the total cap counting a failed attempt, a render failure, the consecutive-failure stop. |
| 16 | `tests/test_golden_author.py:121-170` `TestRequest` | update | adds an assertion that the request kwargs and `AUTHOR_SYSTEM_PROMPT` bytes are unchanged and that the client is narrowed. |
| 17 | `tests/test_eval_catalog.py:34,67,238` | no change | reads `golden_author.AUTHOR_MODEL` and `GOLDEN_DIR`; re-run to confirm, since every fixture's `expected.json` is read for `covered` cases. |
| 18 | `tests/test_data_root.py:282` `_CODE_ANCHORS["evals/golden_set.py"]` | no change | the rejects directory comes from `analyzer.LOG_DIR` (`sartor_home.data_path`), so no new `Path(__file__)` anchor is added. |
| 19 | `evals/catalog/dataset_author.toml` | no change | the call kind and the exempt reason are unchanged. |
| 20 | `scripts/wiki_relevance.py:58-60` | no change | `evals/golden/` is already irrelevant data; `golden_set.py` and `golden_author.py` stay relevant, so a scoped `/wiki-self-update` runs at close-out. |
| 21 | `docs/wiki/pages/eval-harness.md:264,268`, `code-module-map.md:133` | update (close-out) | the wiki scribe step, committed before the PR. |
| 22 | `evals/README.md` golden-set sections, `CHANGELOG.md`, `docs/dev/eval-redesign-design.md` 6.4 | update | the new flags, facts, families, counts, the measured cost, and the staging. |
| 23 | `.gitignore` | no change | `logs/` is already ignored and the rejects directory is under it. |
| 24 | work items: 191 (updates), a new follow-on item, epic 180 | update | item ids are allocated at commit time. |

---

## Deferred

The **`evals/fixtures/synthetic/` retirement** and every consumer in the list below move to the follow-on item, because a
retirement retargets consumers onto a *complete, calibrated* set, and a calibration run on a set that still changes would
have to be paid for again. The list was derived by an Explore subagent at `77decd4` and **has not been re-derived by me**;
the follow-on item re-derives it before its first edit.

- Readers of the directory: `evals/runner.py` `_select_fixtures` and `--fixture` lookup (about `:882-895`) and the
  `run_suite` default (`:1575`, `:2580-2581`); `evals/corpus_drafting_probe.py:79-80` (the only reader of
  `synthetic/corpus/`); `evals/golden_set.py` `profile_from_persona` and the converter tests; `scripts/smoke_phase_b1.py:34`.
- Tests that read it or count it: `test_eval_runner.py`, `test_eval_spend.py` (including `skipped == ["corpus"]`),
  `test_eval_run_identity.py`, `test_eval_catalog.py:65,248-273`, `test_hardening.py:147-170,246-251,300`,
  `test_eval_golden_runner.py:68,94,167`, `test_golden_set.py` (converter), `test_zero_pii_clone.py:102`,
  `test_data_root.py:277`, `tests/ux/regression/test_20261003_run_lock_ownership.py:68`.
- CI and config: `.github/workflows/ci.yml:97-113` (label-gated `eval-smoke`, `--suite synthetic --subset smoke`),
  `evals/catalog/{clarify,generate,generate_cover_letter,iterate_clarify}.toml` (`cases = ["synthetic/..."]`),
  `evals/anchors/anchor-v1/manifest.json`, `evals/results/baseline_v1.json` (the regression keys are bare fixture names),
  `promptfooconfig.yaml`, the dashboard selects (`dashboard/templates/dashboard.html:424-425,611-612`), and the
  suite allowlists in `blueprints/diagnostics.py:1061-1062,1231-1232`.
- A hash-locked prompt line: `analyzer.py:1319` inside `AVATAR_SYSTEM_PROMPT` names `--suite synthetic`; editing it trips
  the prompt lock.
- The anchor copies of the three personas are byte-identical to `synthetic/`, so retiring the directory does not remove
  the anchor suite.
- **The calibration run, tier sizes and the freeze** (the git-history guard) — the same follow-on item.
- **`--suite all` and the console allowlists** — step 8, as in the previous dossiers.
- **Per-cell manifest re-stamping is kept** (about 2 to 4 s per cell against a call of tens of seconds, measured in
  `eval-golden-breadth.md`): a crash then leaves the manifest consistent. The cost is stated, not hidden.

---

## Verification

How a missed consumer would surface:
- **Anything importing `golden_set` / `golden_author`:** `python -c "import evals.runner"` after every edit, then
  `tests/test_golden_set.py`, `test_golden_author.py`, `test_golden_reachability.py`, `test_eval_golden_runner.py`,
  `test_eval_catalog.py`, `test_data_root.py`, `test_call_kind_telemetry.py`.
- **A committed byte drifting or a pair out of step:** `python -m evals.golden_set check` at every commit that touches
  the suite (a draft suite with fewer cells must pass).
- **The prompt changing by accident:** the existing prompt-hash and bytes tests, plus the new request-kwargs assertion.
- **The render hole:** a test whose stub reply has a comma-split target bullet; committed failing first, then green.
- **The cap missing a failed attempt:** a test with a stub that rejects twice, run twice; the second run must see the first's
  spend in the log.
- **The whole set at full size before any spend:** a free dress rehearsal (plan step 5) builds all 96 profiles from the real
  facts, fills them with stub prose and runs `check_suite`, the reachability check and `--estimate` in both modes.

Run at close-out: the enumeration greps above, once more, against the final tree, and `python -m scripts.gate`.
