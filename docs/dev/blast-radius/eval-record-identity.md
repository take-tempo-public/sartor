# Blast radius — eval-record-identity

> **Branch:** `feat/eval-record-identity` (item 181, epic 180 step 1)
> **Status:** enumeration complete at `c64d784` + the ledger commit; written before the first code edit. Sites are decided below; anything found later is appended under `## Deferred` or a new row, not silently handled.

---

## Surface

None of these files is on the C-10 gated list (`scripts/enforcement/blast_radius.py`: `analyzer.py` and `hardening.py` are acknowledged-not-gated; `evals/runner.py`, `dashboard/routes.py` and `scripts/gate.py` appear in no bucket), so no hook forces this dossier. It is written because the call-log row and the eval record are shared contracts with many readers (charter C-10).

- `analyzer.py`: `_provenance_fields` (both row builders pass through it), the `finally` row builder in `_call_llm_streaming`, `log_judge_call`, `_call_llm`, `_parse_or_retry`, `_parse_or_retry_streaming`; new `trace_context` ContextVar beside `prompt_overrides`.
- `evals/runner.py`: `run_suite` (trace and case ids), the 7 record literals (via the five `_model_provenance_fields()` spread points), `_eval_cost_since` (replaced), `EvalRunResult` (new defaulted fields), `LLM_LOG_PATH`.
- New: `call_identity.py`, `scripts/prompt_lock.py`, `evals/prompt_hashes.json`, `tests/test_prompt_hash_gate.py`.
- `tests/conftest.py` (redirect `runner.LLM_LOG_PATH`).

New row keys: `prompt_sha256`, `producer_id`, `parse_outcome` (parse loops only); and only inside a trace context `trace_id`, `span_id`, `parent_span_id`, `case_id`. New record keys: `trace_id`, `case_id`, `span_id`, `judge_cost_usd`. `SCHEMA_VERSION` stays 3.

---

## Enumeration

Run in Git Bash at the repo root, `git grep -l -E '<pattern>' -- <scope>`; counts are files (docs, handoffs and archives included).

| Pattern | Files | Code/test/command files among them |
|---|---|---|
| `llm_calls\.jsonl\|LLM_LOG_PATH\|LLM_LOG\b\|analyzer\.LOG_PATH` | 136 | `analyzer.py`, `blueprints/analysis.py` (comment only), `commands/bench.md`, `commands/replay.md`, `dashboard/__init__.py` (docstring), `dashboard/routes.py`, `dashboard/templates/dashboard.html`, `evals/corpus_drafting_probe.py`, `evals/runner.py`, `hardening.py`, `scripts/perf_baseline.py`, `scripts/probe_call_provenance.py`, `scripts/smoke_phase_b1.py`, 20 test files (`tests/conftest.py`, `test_call_provenance.py`, `test_judge_call_provenance.py`, `test_dashboard_routes.py`, `test_data_root.py`, `test_llm_call_error_capture.py`, `test_refinement_scope.py`, `test_call_kind_*`, ux suites, …) |
| `_emit_call_log\|log_judge_call\|_provenance_fields` | 44 | `analyzer.py`, `dashboard/routes.py`, `evals/runner.py`, `scripts/probe_call_provenance.py`, `tests/conftest.py` and 10 test files |
| `_eval_cost_since\|compute_call_cost` | 41 | `analyzer.py`, `dashboard/routes.py`, `evals/corpus_drafting_probe.py`, `evals/runner.py`, `hardening.py`, `scripts/probe_call_provenance.py`, `scripts/smoke_phase_b1.py`, `tests/test_hardening.py`, `test_judge_call_provenance.py`, `test_model_overrides.py` |
| `EvalRunResult` | 8 | `blueprints/diagnostics.py:1290,1304`, `evals/runner.py`, `tests/test_annotation_routes.py` (constructs it by keyword at :1051,:1094,:1307,:1613), `tests/test_eval_runner.py` |
| `model_snapshots\|judge_request_id\|_model_provenance_fields` | 21 | `evals/runner.py`, `evals/results/baseline_v1.json`, `tests/test_eval_runner.py`, `tests/test_judge_call_provenance.py` |
| `is_candidate_record\|_load_baseline_scores` | 32 | `analyzer.py`, `dashboard/routes.py`, `evals/runner.py`, `hardening.py`, `tests/test_candidate_records.py`, `tests/test_eval_runner.py` |
| `EXTRACT_EXPERIENCES_SYSTEM_PROMPT\|AVATAR_SYSTEM_PROMPT` | 23 | `analyzer.py`, `onboarding/extract_experiences.py`, `tests/test_avatar_streaming.py`, `tests/test_prompt_overrides.py` |
| `row_sink\|trace_context\|prompt_sha256\|producer_id\|call_identity` over `*.py` | **0** | negative result: no name collision |
| `13 fields\|six provenance\|provenance fields` over `*.md` | 1 | `SECURITY.md` (the count claim) |

**Correction after the first full-suite run (the enumeration above missed three kinds of consumer):** a new root-level module is a consumer of `pyproject.toml`'s two rosters and of `scripts/wiki_relevance.py` (`git grep -l -E 'sartor_home' -- pyproject.toml scripts/wiki_relevance.py` shows the precedent); and a removed private symbol (`_eval_cost_since`) is a consumer in the wiki pages' line-cite checks (`git grep -n '_eval_cost_since' -- docs/wiki` shows `eval-harness.md:131-132`). Rows 31 to 35 below were added when the suite found them; the grep table did not search for "what must a new module be registered in" or for the wiki's cite form.

Also found by reading, not grep: `evals/tune.py` and `blueprints/diagnostics.py` do **not** read the call log (diagnostics reads eval results through `evals.tune`); no `schemas/` folder or validator describes a row or record; no test asserts an exact key set of a row or record (the exact-set assertions at `tests/test_call_provenance.py:107-120` and `tests/test_judge_call_provenance.py:104-114` are on `request_settings`, not the row).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `analyzer.py:826-834` `_emit_call_log` | no change | Single writer; keeps its never-raises contract. A new field that cannot serialise would lose the row, so every new field is a str. |
| 2 | `analyzer.py:865-895` `_provenance_fields` | update | One place both product and judge rows pass through: gains `prompt_sha256`, `producer_id`. |
| 3 | `analyzer.py:1889-1921` row builder + write in `_call_llm_streaming` | update | Adds ids; hands the row to a `row_sink` when one is supplied, otherwise writes exactly as today (error rows included). |
| 4 | `analyzer.py:898-948` `log_judge_call` | update | Same hash/producer fields and ids; `run_id` stays `""` (see Deferred). |
| 5 | `analyzer.py:1945-1978` `_call_llm`; `:2093-2189` `_parse_or_retry`; `:1997-2090` `_parse_or_retry_streaming` | update | Parse outcome known only here; one row per attempt, written in a `finally`. |
| 6 | `analyzer.py` `avatar_answer_streaming` (:2574-2584) and `check_refinement_scope` | no change | Do not parse JSON through the loops (avatar) or fail open (scope check); no `parse_outcome`, immediate write. |
| 7 | `evals/runner.py:545-575` `_eval_cost_since` | update (replace) | Time-window selection is the leak; replaced by `(trace_id, case_id)` selection read from the run's byte offset. `cost_usd` keeps its generation-only meaning. |
| 8 | `evals/runner.py` 7 record literals via spreads at :1522,:1734,:1794,:1894,:1991 | update | Add `trace_id`, `case_id`, `span_id`; the iteration records recompute cost later (Deferred). |
| 9 | `evals/runner.py:172-190` `EvalRunResult` | update | New fields all have defaults; `tests/test_annotation_routes.py` and `blueprints/diagnostics.py` build/read it by keyword. |
| 10 | `evals/runner.py:110` `LLM_LOG_PATH`; `tests/conftest.py` | update | conftest redirects only `analyzer.LOG_PATH`; add the runner's copy so `run_suite` tests stop reading the developer's real log. `tests/test_data_root.py:80-86` still holds. |
| 11 | `dashboard/routes.py` row readers (`_filter_calls`, `_summarize_calls`, `_cost_by_call_kind`, `_reliability`, `_run_trace`, `/api/run/<id>`) | no change | All `.get` on named keys; none enumerates keys. |
| 12 | `dashboard/templates/dashboard.html:1029-1036,2019` | no change | Fixed columns. `CALLS` embeds whole raw rows (last 200): about +28 KB with the two new 71-byte hashes. Accepted; trimming deferred. |
| 13 | `dashboard/routes.py` eval-record readers (`_normalize_eval_record`, `_pareto_data`, groundedness, baseline health) | no change | `.get` readers; new keys are ignored. |
| 14 | `hardening.py:1743-1780` `compute_call_cost`; `:1792-1797` `is_candidate_record` | no change | Read token fields / `prompt_version` / `model_overrides` only. No new key is named `model_overrides`. |
| 15 | `evals/runner.py:581-702` `_load_baseline_scores`, regression detection; `evals/tune.py:58-86` `load_scores` | no change | Read `fixture`, `rubric`, `score`, `status`, `timestamp`, `prompt_version`. |
| 16 | `evals/corpus_drafting_probe.py:102-129`, `scripts/perf_baseline.py`, `scripts/smoke_phase_b1.py`, `scripts/probe_call_provenance.py` | no change | Select by `run_id` or `call`; `probe_call_provenance` prints whole rows, so new keys appear on their own. |
| 17 | `scripts/vector_before_after_eval.py` | no change | Calls `runner._grade` with no `fixture_name`: its judge rows land under `username "eval"` with no trace context, so they carry no ids (correct under the absence rule). |
| 18 | `commands/bench.md:20` | update | Names the extra row fields; add the new ones. `commands/replay.md:18` no change. |
| 19 | `SECURITY.md:174-185` | update | "13 fields on every row" and "six provenance fields" become false. |
| 20 | `evals/README.md:902-940`, `docs/wiki/pages/{eval-harness,llm-call-catalog,deterministic-llm-boundary,prompt-version-discipline,diagnostics-console}.md`, `dashboard/README.md`, `CHANGELOG.md` | update | Row/record field lists and the PROMPT_VERSION rule; wiki relevance check and scoped self-update at close-out. |
| 21 | `docs/governance/enforcement.md:127` | update | System-prompt half of the bump rule moves from "convention + witness" to a shipped gate; user-template half stays and is labelled unenforced. |
| 22 | `tests/test_call_provenance.py:157-162`, `tests/test_judge_call_provenance.py:149-154` | no change | "No prompt text in a row": a hash is not text. Kept as the guard. |
| 23 | `tests/test_call_provenance.py:210-241`, `tests/test_judge_call_provenance.py:191-206` | no change | MagicMock clients: new fields are computed from our own strings, not the SDK response, so they are always plain `str`. |
| 24 | `tests/test_llm_call_error_capture.py:120-121`, `tests/test_model_overrides.py:92-162` | no change | ok rows carry no `error_type`; default rows carry no `pinned_model`. New fields use neither name. |
| 25 | `tests/test_eval_runner.py:191-194` | no change | `SCHEMA_VERSION == 3` stays. |
| 26 | `tests/test_eval_runner.py:1537-1556` | no change | `jd_label` stays out of the judge payload; the new fields are added to records after grading and are not put in `runner.py:1830-1842`. |
| 27 | `tests/test_call_kind_telemetry.py` | no change | New call kinds are not added. |
| 28 | ~56 test files patching `_call_llm` / `_call_llm_streaming` / `_emit_call_log` | update only the strict fakes | Most fakes take `**kwargs`; the three with fixed signatures (`fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, **kwargs)`) already accept extras. Run the suite after the keyword lands; list any failure here. |
| 29 | `tests/test_avatar_streaming.py:303-307`, `tests/test_prompt_overrides.py:95,136-152,228` | no change | Pin `AVATAR_PROMPT_VERSION` and the base-path identity (`effective_system is` the constant); the hash is computed from the same object. The new gate test extends the drift guard rather than editing it. |
| 30 | `db/build_context.py:181` → `db/models.py:818` → `blueprints/applications.py:280` | no change | Carry the `prompt_version` string, not the row. |
| 31 | `pyproject.toml` `py-modules` (:156-181) and the mypy-strict roster (:437-475) | update | Found by the full suite, not by the first grep: a new root-level module (`call_identity.py`) must be registered in both. `tests/test_packaging.py::TestPyModulesRosterMatchesRepo` pins the first. |
| 32 | `scripts/wiki_relevance.py` (the root-module list at :160-175) | update | `scripts/wiki_relevance.py` is a gated helper (`scripts/enforcement/blast_radius.py`), so this row names it. `call_identity.py` is production code and is added beside `sartor_home.py`, so a branch that touches it triggers the wiki obligation. Consumers of the list: `scripts/wiki_freshness.py` and the close-out wiki check; both only read it. |
| 33 | `docs/wiki/pages/eval-harness.md:131-132` | update | Two cites of `evals/runner.py:_eval_cost_since`, which this branch removes; `tests/test_wiki_cites.py::TestTheRealTree` fails on them (E3). Re-point to `_trace_cost` / `_case_cost` and rewrite the sentence (the wiki is a doc consumer of a symbol the first grep did not look for). |
| 34 | `tests/test_call_provenance.py:245` | update | Calls `_provenance_fields` directly; `call_kind` is now a required keyword. |
| 35 | `tests/test_judge_call_provenance.py` `test_eval_cost_ignores_judge_rows_whatever_their_order` | update | Called the removed `_eval_cost_since`; rewritten onto `_case_cost` with trace and case ids on the rows. Same assertion (judge rows excluded), plus the judge total. |

---

## Deferred

- **Judge rows keep `run_id ""`.** Giving them the fixture's `run_id` would change `_run_trace` (it drops rows with an empty `run_id`, `dashboard/routes.py:899-901`) and `/api/run/<id>`. The trace and case ids carry the join instead. A dashboard decision, not this step.
- **Iteration records recompute `cost_usd` at a later time** (`runner.py:929,1014,1052`) so they include the `iterate_clarify` row while the other rubric records (one value taken at :1592) do not. Pre-existing inconsistency, found here, not changed (selection by trace keeps each site's current semantics).
- **Dashboard embed of whole raw rows** (`dashboard.html:2019`): +28 KB from two full-length hashes. Trimming it is a dashboard change.
- **User-prompt templates** (~25 inline f-strings with dynamic content) are not hashed; the bump rule for them stays convention + witness, labelled unenforced.
- **Judge system prompts** (inline strings in `runner.py:526,729`) get a row hash but are not in the lock; rubrics ride `rubric_version`.
- **Product-flow tracing** (ids on non-eval rows) and the OpenTelemetry projection: step 10 (item 190). **Catalog `case_id` semantics:** step 2 (item 182). `case_id` is the fixture name until then.
- **`parse_outcome` for rows written before this change** cannot be derived.

---

## Verification

- A missed row consumer would surface as a `KeyError` or a changed total in the dashboard and runner tests; every reader above uses `.get`, and the regression set (`test_call_provenance`, `test_judge_call_provenance`, `test_call_kind_telemetry`, `test_eval_runner`, `test_prompt_overrides`, `test_dashboard_routes`, `test_annotation_routes`, `test_data_root`, `test_candidate_records`, `test_hardening`, plus the ~56 stub-patching files) is run after each build step, then `python -m scripts.gate` and `--result`.
- The leak fix is shown by a test that fails on the old `_eval_cost_since`: two interleaved fake runs on the same fixture must get separate costs.
- "Exactly one row per attempt" is asserted for the deferred write when the parse loop raises.
- The gate test is shown failing (prompt changed, version unchanged; stale lock) before it is shown passing.
- Re-run the grep table above at close-out; a count that grew means a new consumer appeared mid-branch.
