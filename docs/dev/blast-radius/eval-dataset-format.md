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
- `analyzer.py`: `log_judge_call` gains an optional `prompt_version=` (default `None` = today's behaviour). No `THINKING_POLICY` row (finding 1).
  "Opus is intentionally not used" comment above `SONNET_MODEL`.
- `hardening.py`: `MODEL_PRICING` (a `claude-opus-5-5` row, rates read from the pricing page 2026-10-22).
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
| 16 | `tests/test_egress_allowlist.py:121-145` `SANCTIONED_EGRESS_FILES` | no change (revised) | `evals/golden_author.py` takes the client as an argument and imports no network library; the CLI reaches `evals.runner._get_client` (already listed) with a function-local import. No new host: the destination is still the configured LLM provider (C-2 class a). The egress test passes both ways. |
| 17 | `tests/test_data_root.py:267-282` `_CODE_ANCHORS` | update (revised) | only `evals/golden_set.py` anchors a path with `Path(__file__)`; `golden_author.py` does not, so it is not listed. |
| 18 | `scripts/wiki_relevance.py:41-73` `IRRELEVANT_PREFIXES`; `tests/test_wiki_relevance_classification.py:53,96,108` | update | add the golden data directory with a reason line. The classification test reads the set, so it passes only if every prefix is a real directory; the directory is committed in the same change. |
| 19 | `tests/test_model_overrides.py:204` | update, comment only (revised) | uses `claude-opus-5-5` as the "no policy, no price" refusal case. Still true for the policy: the author pin has a price but no `THINKING_POLICY` row (finding 1), so Opus 5.5 stays an illegal override target and this case keeps its meaning. Its comment said an Opus 5.5 call has neither a price nor a policy; the price exists now, so the comment is corrected and the assertion is untouched (the refusal asserted is the policy one). |
| 20 | `tests/test_eval_runner.py:1670` | update, comment only (revised) | the same case in `test_bad_override_is_refused_before_any_client_or_record`; still refused for the missing policy; its trailing comment is corrected the same way. |
| 21 | `hardening.py:452` `MODEL_PRICING`; `tests/test_hardening.py:795-821` | update, done | `claude-opus-5-5` added with $4 in, $20 out, $5 for a 5-minute write, $0.20 for a hit, **read from the pricing page on 2026-10-22** (it matches the claude-api skill's cached table). `test_hardening` requires every `THINKING_POLICY` model to be priced, not the reverse, so a priced model without a policy passes. |
| 22 | `analyzer.py:1357` `THINKING_POLICY` | no change (revised) | **no row**, finding 1. `_author_create` sends `thinking: {"type": "adaptive"}` and an effort itself, the only settings Opus 5.5 accepts, and records them in the row's `request_settings`. |
| 23 | `analyzer.py:1002` `log_judge_call` and its 6 callers (`evals/runner.py:508,518`, `tests/test_call_record_identity.py:104,174`, `tests/test_eval_run_identity.py:51`, `tests/test_judge_call_provenance.py`) | update | an optional `prompt_version=` keyword, default `None` = today's `PROMPT_VERSION`, so every existing row is byte-identical. |
| 24 | `analyzer.py:1344-1346` comment "Opus is intentionally not used" | no change (revised) | it describes the product's models and is still true: the author pin is not a product model. |
| 25 | `analyzer.model_overrides` (`analyzer.py:803-825`) | no change (revised) | with no `THINKING_POLICY` row, `--model-override SONNET_MODEL=claude-opus-5-5` is still refused before any paid call, so this branch opens no new product path on Opus 5.5. |
| 26 | `evals/README.md:40, 172, 211, 213, 958` | update | `--suite` list, the `--fixture` lookup, the record's `suite` values, per-cell seeds. |
| 27 | `commands/eval.md:3`, `commands/tune-from-annotations.md:47-63`, `.github/PULL_REQUEST_TEMPLATE.md:38-39`, `.github/workflows/ci.yml:113`, `AGENTS.md:273-274`, `CONTRIBUTING.md:181` | no change | they name `synthetic`, `real` or `anchor`; none enumerates the suite choices as a closed set. |
| 28 | `evals/fixtures/synthetic/` consumers: `evals/runner.py:12,878`, `evals/corpus_drafting_probe.py`, `evals/anchors/anchor-v1/manifest.json`, `evals/catalog/{clarify,generate,generate_cover_letter,iterate_clarify}.toml`, `evals/results/baseline_v1.json`, `promptfooconfig.yaml`, `demo_fixtures.py`, `dashboard/templates/dashboard.html:824,1367`, `tests/test_eval_runner.py:1460-1477`, `tests/test_zero_pii_clone.py:102`, `tests/test_hardening.py:147-164`, and this branch's own `tests/test_golden_set.py` (`TestConverter`, `TestWaivers`, `TestParser` read `evals/fixtures/synthetic/` to convert the pilots; they go with the converter) | deferred | 3b retires `synthetic/`, so these are 3b's to retarget. This branch leaves the directory byte-identical. |
| 29 | `evals/catalog/dataset_author.toml` (new), `tests/test_eval_catalog.py:189-197` (file name = call kind) | update | an `exempt` entry whose `exempt` reason is over 40 characters and whose `exempt_approved` names the owner's 2026-10-22 decision. |

---

## Findings that changed the plan

Recorded while building the generator (step 7), after the first version of this dossier.

1. **Opus 5.5 takes no `THINKING_POLICY` row.** The claude-api skill (loaded 2026-10-22) states that
   `{"type": "disabled"}` and a thinking budget are 400s on Opus 5.5 at every effort level, so the only
   valid values are adaptive thinking and an effort. A policy row would also make Opus 5.5 a legal
   `--model-override` target for product calls nobody has validated against it (forced `tool_choice`,
   sampling parameters and prefill are 400s there). So the generator sends its own settings and the
   product's policy table, the override path and the two refusal tests are untouched. Rows 19, 20, 22,
   24 and 25 are revised from "update" to "no change" for this reason. Stated limit: the request shape
   is as documented, not observed; no real call has been made.
2. **The generator imports no network library**, so it needs no egress allowlist entry (row 16).
3. **The price was read, not recalled.** Pricing page, 2026-10-22: Opus 5.5 $4 / $20 / $5 / $0.20.
   It also settles a question earlier handoffs carried: Sonnet 5.5's cache-hit price is **$0.10** on the
   page (0.05x), which is what `hardening.py` has. The skill's cached table says $0.20, so the skill's
   table is the stale one.
4. **No fallback model.** The skill advises `fallbacks` by default for `claude-opus-5-5` code. Declined
   on purpose: a fallback would answer with another model, so the `model` recorded for the prose would
   be wrong. A refusal on résumé prose raises and the cell is not written.

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

Measured, not estimated (`pytest --durations`, 2026-10-22): the reachability test runs the three pilots through
the real pipeline against the stub in about 0.3 s per mode, so about 0.1 s a fixture. A 96-fixture `golden-v1`
costs about 10 s a mode, cheap enough to stay in the default test run (3b re-measures at full size).

Run at close-out: the enumeration greps above, once more, against the final tree, and `python -m scripts.gate`.
