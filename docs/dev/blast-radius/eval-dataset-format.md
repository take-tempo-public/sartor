# Blast radius — eval-dataset-format

> **Branch:** `feat/eval-dataset-format` (item 183, eval redesign step 3a)
> **Status:** enumeration complete at `4185eb9` (the ledger commit on top of `186a064`), written before the first code
> edit. Step 3 was split by the owner on 2026-10-22: this branch is the format, the generator (stub-tested only), the
> per-cell seeds and the reachability check, with no paid call. Generating the 48 cells is step 3b.

---

## Surface

New:
- `evals/golden_set.py` — stdlib-only: the cell format, the profile builder, the deterministic renderer, the prose
  validator, the `REACHABILITY` table.
- `evals/golden_author.py` — the dataset generator (judge pattern: it calls `client.messages.create` and logs through
  `analyzer.log_judge_call`). Owns `AUTHOR_MODEL`, `AUTHOR_PROMPT_VERSION`, `AUTHOR_SYSTEM_PROMPT`.
- `evals/golden/golden-v1/` — `manifest.json`, `facts/`, `cells/`, `fixtures/` (3 pilot cells).
- `evals/catalog/dataset_author.toml` — an `exempt` catalog entry.
- `tests/test_golden_set.py`, `tests/test_golden_author.py`, `tests/test_golden_reachability.py`.

Changed:
- `evals/runner.py`: `--suite` choices, `_select_fixtures`, `_check_mode` and its two callers, `_load_fixture` (a
  `seed_path` argument), `run_suite` (per-fixture seeded session), `main`, `estimate_spend`, `_pin_models`.
- `evals/eval_catalog.py`: `PINS`, `GROUPS`, `_pin_models`.
- `analyzer.py`: `log_judge_call` (an optional `prompt_version=`), `THINKING_POLICY` (a `claude-opus-5-5` row), and the
  "Opus is intentionally not used" comment above `SONNET_MODEL`.
- `hardening.py`: `MODEL_PRICING` (a `claude-opus-5-5` row).
- `scripts/wiki_relevance.py`: `IRRELEVANT_PREFIXES` gains the golden data directory. **This is a registered gated
  surface** (`scripts/enforcement/blast_radius.py`, the `helper` entry): the classifier behind a merge-blocking gate.
- Tests: `tests/test_eval_catalog.py`, `tests/test_call_kind_telemetry.py`, `tests/test_egress_allowlist.py`,
  `tests/test_data_root.py`, `tests/test_model_overrides.py`, `tests/test_eval_runner.py`, `tests/test_eval_spend.py`.
- Docs: `docs/dev/eval-redesign-design.md`, `evals/README.md`, `CHANGELOG.md`, work items 183 / a new 3b item / epic 180.

Not touched: `evals/fixtures/synthetic/` (3b replaces it), `evals/anchors/`, `PROMPT_VERSION`, `evals/prompt_hashes.json`
(the author prompt is not in `_BASE_SYSTEM_PROMPTS`), any pin, `docs/governance/charter.md`.

---

## Enumeration

Commands run on `feat/eval-dataset-format` at `4185eb9` with the Grep tool. Counts are from the tool output.

```
Grep "_check_mode|_load_fixture\(|_select_fixtures\(|_fixture_iterates|_call_plan\(|estimate_spend\(|
      _suite_of\(|seeded_session\(|load_seed\("   (*.py, whole tree)                              -> 80+ lines, 14 files
Grep "same names, count mode"                                                                      -> 117 occurrences, 14 files
Grep "PINS|GROUPS|_pin_models|_pin_model|_ROUTED|_SUITE_DIRS|EXPECTED_CALL_KINDS|
      SANCTIONED_EGRESS_FILES|_CODE_ANCHORS|IRRELEVANT_PREFIXES"   (*.py)                          -> 4 definition sites + 9 test/doc readers
Grep "log_judge_call|MODEL_PRICING|THINKING_POLICY"   (*.py)                                       -> 1 definition + 4 runtime callers + 12 test files
Grep "opus-5|opus-4|claude-opus"   (*.py,toml,json,yml,yaml)                                       -> 4 hits (see Consumers 19-20)
Grep "--suite|requires --seed|\"synthetic\""   (whole tree minus wiki, handoffs, results, TUNING_LOG)-> ~210 lines; live consumers listed below
Grep "run_suite\(|seed_data|has_seed"   (blueprints, evals, scripts, app, dashboard)               -> 2 console callers, 1 CLI caller
Grep "\[\"suite\"\]|\.get\(\"suite\"|rec\[.suite.\]|\"suite\":"   (dashboard, evals, blueprints)     -> 0 readers of the value
```

Negative results (also findings):
- **0** consumers in `dashboard/` read a record's `suite` value. Records carry it through (`runner.py:1882,2095,2156,2257,2356`)
  and nothing branches on it, so a new suite name needs no dashboard edit.
- `claude-opus-5-5` appears in **no** pricing or policy table today. It appears only as the "unlisted model" in two
  refusal tests (Consumers 19 and 20).
- `analyzer._call_llm_streaming` and the product call routes get **no** new call: the generator is a judge-pattern
  caller, so the 26 product call sites stay 26 and the site count becomes 27 only through `_author_create`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `evals/runner.py:2499-2502` `--suite` choices | update | add `golden-v1`; `all` deliberately excludes it (a 96-case set must not ride into `--suite all`). |
| 2 | `evals/runner.py:867` `_select_fixtures`; `:870` the `--fixture` search | update | resolve `golden-v1` to its `fixtures/` directory (the anchor layout); `--fixture` searches it too. |
| 3 | `evals/runner.py:896` `_suite_of` | no change | already returns the grandparent name when the parent is `fixtures`, so `golden-v1` falls out of the anchor layout. A test pins it. |
| 4 | `evals/runner.py:244` `_load_fixture` | update | gains `seed_path=`; the seed bytes join the content hash only when given, so every existing hash is unchanged. |
| 5 | `evals/runner.py:960` `_check_mode` and its callers `:1069` (`estimate_spend`) and `:1591` (`run_suite`) | update | the "assemble requires a seed" check becomes "requires `--seed` or a `seed.json` in every selected fixture"; it keeps the phrase "requires --seed" because `tests/test_eval_runner.py:813` and `tests/test_eval_spend.py:176` match it. |
| 6 | `evals/runner.py:971` `_fixture_iterates`, `:991` `_call_plan` | no change | they read `iteration_scenarios` from `expected.json`, which the renderer writes in the same shape. |
| 7 | `evals/runner.py:1060` `estimate_spend` | update | takes the same seed-source decision so `--estimate` works for golden cells with no `--seed`. |
| 8 | `evals/runner.py:1725-1728, 1739, 1787` `run_suite` seeded session | update | per-fixture session for the per-cell source; the `--seed` path (one shared session) stays byte-identical. |
| 9 | `evals/runner.py:2645-2674` `main` | update | the seed source is decided once and passed to both the estimate and the run. |
| 10 | `evals/runner.py:1022` `_pin_models` | update | `AUTHOR_MODEL` is a pin name the catalog may name, so `--list` must resolve it; never overridable (like the judge). |
| 11 | `blueprints/diagnostics.py:1061-1062, 1231-1232` (suite allowlists), `:1099, 1286` (`load_seed`) | deferred | the console cannot reach `golden-v1` until step 8 (dashboard / catalog tab). Reason: adding a suite to the browser means the console's cost-confirm flow and `seeded` flag need a per-cell notion. |
| 12 | `evals/bootstrap.py:576, 613`, `evals/corpus_drafting_probe.py:92, 149`, `evals/seed_import.py:308` `seeded_session` | no change | the signature is untouched; they pass a seed dict or path as before. |
| 13 | `evals/eval_catalog.py:38` `PINS`, `:39` `GROUPS`, `:333` `_pin_models` | update | add `AUTHOR_MODEL` and a `dataset` group; `_pin_models` imports `evals.golden_author` for the id (still only `measure` imports the product). |
| 14 | `tests/test_eval_catalog.py:47-55` `_ROUTED`, `:60-63` `_SUITE_DIRS`, `:98` `_pin`, `:228` `_pin_model`, `:367` site count | update | add `_author_create` to `_ROUTED` (no defaults: a missing `model=` / `system_prompt=` raises `GateCannotRead`), `golden-v1` to `_SUITE_DIRS`, `AUTHOR_MODEL` to `_pin_model`, and 26 to 27. |
| 15 | `tests/test_call_kind_telemetry.py:74-102` `EXPECTED_CALL_KINDS` | update | add `dataset_author`; row emission is covered in `tests/test_golden_author.py`, as the judge kinds are in `test_judge_call_provenance.py`. |
| 16 | `tests/test_egress_allowlist.py:121-145` `SANCTIONED_EGRESS_FILES` | update | `evals/golden_author.py` imports `anthropic` (it takes the client type), so it is listed on purpose, as `evals/runner.py` is. No new host: the destination is still the configured LLM provider (C-2 class a). |
| 17 | `tests/test_data_root.py:267-282` `_CODE_ANCHORS` | update | `golden_set.py` and `golden_author.py` anchor paths with `Path(__file__)`; each is listed with its reason. |
| 18 | `scripts/wiki_relevance.py:41-73` `IRRELEVANT_PREFIXES`; `tests/test_wiki_relevance_classification.py:53,96,108` | update | add the golden data directory with a reason line. The classification test reads the set, so it passes only if every prefix is a real directory; the directory is committed in the same change. |
| 19 | `tests/test_model_overrides.py:204` | update | uses `claude-opus-5-5` as the "no policy, no price" refusal case. Adding the rows makes it a legal override, so the case moves to a still-unlisted id. |
| 20 | `tests/test_eval_runner.py:1670` | update | the same case in `test_bad_override_is_refused_before_any_client_or_record`; same replacement id. |
| 21 | `hardening.py:452` `MODEL_PRICING`; `tests/test_hardening.py:795-821` | update | add `claude-opus-5-5` with the four rates **read from the primary pricing page on the day**; the test then requires its `THINKING_POLICY` row too. If the page cannot be read, the work stops and goes to the owner: a guessed price is a C-0 violation. |
| 22 | `analyzer.py:1357` `THINKING_POLICY` | update | add the Opus 5.5 row, **observed against the API contract in the pricing / models docs, not assumed** (Sonnet 5.5 rejects `disabled`; Opus's value is not known here). |
| 23 | `analyzer.py:1002` `log_judge_call` and its 6 callers (`evals/runner.py:508,518`, `tests/test_call_record_identity.py:104,174`, `tests/test_eval_run_identity.py:51`, `tests/test_judge_call_provenance.py`) | update | an optional `prompt_version=` keyword, default `None` = today's `PROMPT_VERSION`, so every existing row is byte-identical. |
| 24 | `analyzer.py:1344-1346` comment "Opus is intentionally not used" | update | the comment would be false next to an Opus row; it now says the author pin is not a product pin. |
| 25 | `analyzer.model_overrides` (`analyzer.py:803-825`) | no change, declared | Opus 5.5 becomes an accepted `SONNET_MODEL` override target as a side effect of rows 21-22. Declared in the CHANGELOG; the override still cannot touch the judge or the author pin. |
| 26 | `evals/README.md:40, 172, 211, 213, 958` | update | `--suite` list, the `--fixture` lookup, the record's `suite` values, per-cell seeds. |
| 27 | `commands/eval.md:3`, `commands/tune-from-annotations.md:47-63`, `.github/PULL_REQUEST_TEMPLATE.md:38-39`, `.github/workflows/ci.yml:113`, `AGENTS.md:273-274`, `CONTRIBUTING.md:181` | no change | they name `synthetic`, `real` or `anchor`; none enumerates the suite choices as a closed set. |
| 28 | `evals/fixtures/synthetic/` consumers: `evals/runner.py:12,878`, `evals/corpus_drafting_probe.py`, `evals/anchors/anchor-v1/manifest.json`, `evals/catalog/{clarify,generate,generate_cover_letter,iterate_clarify}.toml`, `evals/results/baseline_v1.json`, `promptfooconfig.yaml`, `demo_fixtures.py`, `dashboard/templates/dashboard.html:824,1367`, `tests/test_eval_runner.py:1460-1477`, `tests/test_zero_pii_clone.py:102`, `tests/test_hardening.py:147-164` | deferred | 3b retires `synthetic/`, so these are 3b's to retarget. This branch leaves the directory byte-identical. |
| 29 | `evals/catalog/dataset_author.toml` (new), `tests/test_eval_catalog.py:189-197` (file name = call kind) | update | an `exempt` entry whose `exempt` reason is over 40 characters and whose `exempt_approved` names the owner's 2026-10-22 decision. |

---

## Deferred

- **The console allowlists (Consumers 11)** — step 8. A browser run of a 96-case set needs the cost-confirm flow to know the set's size.
- **`--suite all`** includes `golden-v1`: no, on purpose. A paid pass over 96 cases must be asked for by name.
- **The `synthetic/` consumers (Consumers 28)** — 3b, with the directory's retirement.
- **Per-cell seeds in generate mode.** The runner reads a fixture's `seed.json` only in assemble mode. Real fixtures
  can already hold a `seed.json` (the console runs them in generate mode, `blueprints/diagnostics.py:1088-1122`), so
  reading it by presence would silently change `--suite real`.
- **The committed corpus seed's `area` / `study_type` keys** (`evals/fixtures/synthetic/corpus/role-summary-drafting/seed.json`)
  are not read by the importer (`evals/seed_import.py:280` reads `field`), so the education discipline is lost. Not
  fixed here: that file is under `synthetic/`. The golden renderer writes `field`, and a test asserts every seed key is
  one the importer reads. To be filed as a carry-forward observation.
- **Seed-borne clarifications.** The seed format (v1) has no clarifications and the importer ignores them; `iterate_clarify`
  gets its answers from `expected.json`. A seed v2 is not designed here.
- **The freeze is prose-enforced.** Nothing stops a later commit rewriting both a cell and the manifest hash. Stated as a limit;
  3b adds a check against git history once there is a frozen version to protect.

---

## Verification

How a missed consumer would surface:
- **A new `call_kind=` site or a new pin:** `tests/test_call_kind_telemetry.py` and `tests/test_eval_catalog.py` fail on any
  literal, site count or pin not in their sets, in both directions.
- **A new network importer:** `tests/test_egress_allowlist.py` fails both ways.
- **A new `Path(__file__)` anchor:** `tests/test_data_root.py` fails both ways.
- **A wiki-classification gap:** `tests/test_wiki_relevance_classification.py`.
- **A priced model without a policy, or the reverse:** `tests/test_hardening.py:795-821`.
- **A seed key the importer drops:** the new `tests/test_golden_set.py` asserts every key of every rendered seed is read by
  `evals/seed_import.py`.
- **A call kind a golden cell cannot reach:** `tests/test_golden_reachability.py`, with the `REACHABILITY` keys tied to
  `eval_catalog.names()` in both directions.
- **The `--seed` path drifting:** the existing `tests/test_eval_runner.py`, `tests/test_eval_spend.py` and
  `tests/test_seed_import.py` run unchanged; any edit to them other than rows 19 and 20 is a finding.

Run at close-out: the enumeration greps above, once more, against the final tree, and `python -m scripts.gate`.
