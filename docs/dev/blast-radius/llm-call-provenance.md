# Blast radius — llm-call-provenance

> **Branch:** `fix/llm-call-provenance`
> **Status:** enumeration complete for the telemetry row, the judge calls and `MODEL_SNAPSHOTS`; derived from a
> grep-complete exploration pass on 2026-10-19 and spot-checked by hand (judge-call ordering at `evals/runner.py:1457-1462`
> and `:1714`, the `SECURITY.md` field count, `_StreamDone.__slots__`). Counts below are the pass's, not re-run in full.

None of `analyzer.py`, `evals/runner.py`, `dashboard/routes.py`, `db/build_context.py` or `logs/llm_calls.jsonl` is a gated
surface (`scripts/enforcement/blast_radius.py:199-209` lists `analyzer.py` and `hardening.py` under
`ACKNOWLEDGED_NOT_GATED`; `evals/runner.py` and the dashboard are not listed). This dossier is written first anyway: the row
is a shared contract in fact, even though the registry does not gate it. Precedent: `docs/dev/blast-radius/llm-call-error-capture.md`.

---

## Surface

- `analyzer.py` `_call_llm_streaming` (the row at the `_call_log_record` dict) gains fields; `_call_llm`,
  `_parse_or_retry`, `_parse_or_retry_streaming` gain an `attempt` pass-through; `_parse_or_retry`'s retry passes
  `max_tokens`; `avatar_answer` stamps its own prompt version.
- `evals/runner.py` `_grade`, `_score_distinctiveness` emit telemetry rows; `_eval_cost_since` skips `judge_*` rows;
  `MODEL_SNAPSHOTS` is derived; the eval records carry the judge's API request id.
- `db/build_context.py:181` stamps the effective prompt version.
- **Unchanged on purpose:** the meaning of every existing row field. `model` stays "the id requested".

---

## Enumeration

Names searched across the whole tree (py, js, md, templates, yaml/toml/sh): `llm_calls`, `LOG_PATH`, `LLM_LOG_PATH`,
`_emit_call_log`, `compute_call_cost`, `cache_read_input_tokens`, `rec["model"]`, `record["model"]`, `"stop_reason"`,
`MODEL_SNAPSHOTS`, `model_snapshots`, `haiku_judge`, `JUDGE_MODEL`, `AVATAR_PROMPT_VERSION`, `effective_prompt_version`,
`messages.create(`, `messages.stream(`, `max_tokens=`.

Negative results (findings):
- No test asserts a telemetry row's exact key set (`len(rec)`, `set(rec)`, `.keys() ==`, `sorted(rec)`: 0 hits on rows).
- `dashboard/` has 0 hits for `request_id|response_model|"attempt"|"settings"`.
- 0 hits for `llm_calls` in `*.{mjs,cjs,ts,ps1,sh,bat,toml,yaml,yml,txt}`.
- `tests/` has 0 hits for `model_snapshots|haiku_judge`: nothing pins `MODEL_SNAPSHOTS`' contents.
- The only `messages.create(` calls are `evals/runner.py:440` and `:625`; the only `messages.stream(` is `analyzer.py:1601`.

Name clashes to avoid: `response_model` is `_parse_or_retry*`'s pydantic parameter (`analyzer.py:1735`, `:1830`);
`request_id` is the app's error id (`web_infra/http.py:46-70`). New fields are `answered_model`, `api_request_id`,
`request_settings`, `served_as`, `thinking_tokens`, `attempt`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `hardening.py:1715-1745` `compute_call_cost` | no change | Reads `model` + 4 token fields. `model` keeps meaning "requested"; a dated id there would price at 0.0. |
| 2 | `dashboard/routes.py:141-157` `_filter_calls`, `:1063` model dropdown | no change | Reads `timestamp`, `username`, `model`; extra keys ignored. |
| 3 | `dashboard/routes.py:177-224` `_summarize_calls` | no change | Token and latency fields only. Judge rows add to spend totals: **disclosed meaning change**, see `## Deferred` D-1. |
| 4 | `dashboard/routes.py:763-791` `_cost_by_call_kind` | no change | Groups by `call`; `judge_*` kinds appear as their own groups (wanted). |
| 5 | `dashboard/routes.py:794-837` `_reliability` | no change in code | Counts `stop_reason == "max_tokens"` per kind. **The retry fix can change `check_refinement_scope_retry`'s truncation rate** (cap 128 now honoured): expected, disclosed. |
| 6 | `dashboard/routes.py:840-908` `_run_trace`, `:1100-1160` `run_detail` | no change | Named keys only. Judge rows carry `run_id=""` so they do not join a run trace. |
| 7 | `dashboard/routes.py:1067` → `dashboard.html:2019` `var CALLS = {{ calls \| tojson }}` | no change | Embeds the last 200 FULL rows. New keys add page weight (about 250-450 bytes per row, 50-90 KB at 200 rows); values must be JSON-serializable (type-guarded). |
| 8 | `evals/runner.py:461-487` `_eval_cost_since` | **update** | Skip `call.startswith("judge_")`. Without it `cost_usd` would include the distinctiveness judge (written before the rollup at `:1462`) but not the rubric judges (after it, `:1714`). |
| 9 | `evals/runner.py:112` `MODEL_SNAPSHOTS` and its 5 writers `:1393,1604,1664,1763,1860` | **update** | Derive from `analyzer.SONNET_MODEL`/`HAIKU_MODEL` + `JUDGE_MODEL`; keys `sonnet`, `haiku_judge` kept, `haiku` added. Only `evals/results/baseline_v1.json:5-8` stores it; nothing reads it. |
| 10 | `tests/test_hardening.py:778-801` | no change | Requires each snapshot value and `JUDGE_MODEL` to be a `MODEL_PRICING` key; holds. |
| 11 | `evals/corpus_drafting_probe.py:110-129` | no change | Last 200 lines; `run_id` + cost. |
| 12 | `scripts/perf_baseline.py:53-86` | no change | `call`, `latency_ms`, `output_tokens`. Judge kinds appear as new groups. |
| 13 | `scripts/smoke_phase_b1.py:203-218` | no change | `run_id`, cost, `cache_read_input_tokens`. |
| 14 | `commands/bench.md:14-19`, `commands/replay.md:18` | update (doc) | Describe the grouping/fields; add the new fields and the `judge_*` kinds. |
| 15 | `tests/test_analyzer_model_selection.py:17-40,55,66`, `tests/test_demo_mode.py:306-325`, `tests/test_extract_experiences.py:271-292` | no change in the tests; **drives a code requirement** | Their stream/final/usage are plain `MagicMock`: auto-attributes are MagicMocks and `json.dumps` of one raises inside `_emit_call_log`, leaving an EMPTY log (the file is opened `"a"` first). Every SDK-derived value is therefore type-guarded (`isinstance`) before it enters the row. |
| 16 | `tests/test_call_kind_telemetry.py:171-216,231-239` (reused by `test_call_kind_route_telemetry.py:35`), `test_llm_call_error_capture.py:52-101,117-219`, `test_llm_credential_gate.py:160-188`, `test_prompt_overrides.py:160-201`, `test_refinement_scope.py:37-86` | no change | Plain-class fakes with no `request_id` and no `final.model`: reads use `getattr(..., None)`. `test_llm_call_error_capture.py:120-121` asserts `error_type`/`error_message` are ABSENT on ok rows, so new fields must not reuse those names. |
| 17 | Fakes that replace `_call_llm`/`_call_llm_streaming`: `tests/test_analyzer.py:52,271,316,449,500,532,600,647`, `test_analyzer_iteration.py:212,357,396,464,508`, `test_analyze_split.py:76,134,198`, `test_handle_guard.py:58-68,244,397`, `test_avatar_streaming.py:47` | no change | All accept `**kwargs`, so a new `attempt=` / `prompt_version=` kwarg is safe. |
| 18 | `analyzer.py:1489` `_StreamDone.__slots__`; `tests/test_avatar_streaming.py:51` builds it positionally | no change | No field is added to `_StreamDone`. |
| 19 | `tests/test_eval_runner.py:105-183` drives `_grade` with a MagicMock `msg` | no change in the test; same type-guard requirement as #15 | `msg._request_id`, `msg.model`, `msg.usage` are MagicMocks. |
| 19a | **Found after the first edit, not by the sweep:** `tests/test_eval_runner.py` monkeypatches `runner._grade` at `:429,527,591,627,684,934,1018,1076,1224,1428,1530` and `_score_distinctiveness` at `:434,532,586,689,940,1086,1433`; `tests/test_annotation_routes.py:1183-1187` does the same | update one fake; the rest no change | Adding a positional `fixture_name` made `spying_grade(..., **k)` and `_capture_grade(client, rubric_path, payload)` fail (2 tests red). Resolved by passing `fixture_name=` as a **keyword** at the three runner call sites and giving `_capture_grade` `**k`; every `lambda *a, **k` fake is unaffected. |
| 19b | **Also found late:** `scripts/vector_before_after_eval.py:39,108` calls `_grade(client, rubric_path, payload)` positionally | no change | `fixture_name` defaults to `""`; its judge rows are tagged `username="eval"` and kind `judge_grade`, so a run of that script now appears in the telemetry window. Disclosed. |
| 20 | `analyzer.py:3345` `check_refinement_scope` (`max_tokens=128`); all other `_parse_or_retry` callers (`:1959,1979,2429,2573,3080,3287,3476,3576,3740,3972,4195,4421,4523,4617,4728,4861,5075,5248`, `onboarding/extract_experiences.py:165`) | update (one behaviour) / no change | Only `check_refinement_scope` passes a non-default cap, so only its retry changes (128 instead of 8192). Every other caller uses the default, which the retry already used. |
| 21 | `_parse_or_retry_streaming` callers `analyzer.py:2125,2151,3131` | no change | The function has no `max_tokens` parameter and all three want 8192; recorded in `request_settings`, not changed. |
| 22 | `AVATAR_PROMPT_VERSION` (`analyzer.py:672`), read only by `tests/test_avatar_streaming.py:144,299` | update | `avatar_answer` (`:2303`) passes it as the row's `prompt_version`; the pinned `== "2026-09-29.1"` assertion stays valid. |
| 23 | `effective_prompt_version()` callers: `evals/runner.py:823,908,945,1173,1388,1594,1753,1854`, `evals/bootstrap.py:294`, `tests/test_prompt_overrides.py:35-131` | no change | Already the effective version. `evals/corpus_drafting_probe.py:221` uses plain `PROMPT_VERSION`: see `## Deferred` D-2. |
| 24 | `db/build_context.py:181` `ApplicationRun(prompt_version=PROMPT_VERSION)` | update | Stamp `effective_prompt_version()` so a `candidate:<hash>` run is not recorded as the shipped version. |
| 25 | Docs describing the row: `SECURITY.md:174-183` ("13 fields"), `docs/wiki/pages/llm-call-catalog.md:84-103`, `prompt-version-discipline.md:31-33`, `deterministic-llm-boundary.md:64-69`, `diagnostics-console.md:68,338-339`, `eval-harness.md:19,90,119-121`, `evals/README.md:202,868,878,888,892,898,914,922,1053`, `dashboard/README.md:115-116`, `docs/dev/perf/PERFORMANCE_HISTORY.md:53-55`, `docs/user/install.md:654-655`, `docs/dev/RELEASE_ARC.md:120,150` | update (doc) | `SECURITY.md` must keep the "no request or response content" claim true: `request_settings` excludes `system` and `messages` by construction. |

---

**Process note (C-10).** The sweep's search for `_grade` found the MagicMock-driven tests and missed the monkeypatched fakes
with a fixed signature, because it searched for callers of the function rather than for replacements of it. Two tests went red
on the first run. The class to search is "anything that substitutes the symbol", not only "anything that calls it".

---

## Deferred

- **D-1 — judge spend now reaches the dashboard's totals.** Rows with `judge_*` kinds are summed by `_summarize_calls`
  (#3), so the dashboard's spend rises by the judge spend while eval `cost_usd` stays generation-only. Chosen by the owner
  (2026-10-19) over eval-record-only. Not split into a separate dashboard series here.
- **D-2 — `evals/corpus_drafting_probe.py:221` records plain `PROMPT_VERSION`** and no model. Not touched: it is an
  eval-side record outside the gaps 1-7 the owner scoped, and it has no override path. Carry-forward ledger.
- **D-3 — gap 8** (saved context files and the database carry no model): out of scope by the owner's 2026-10-17 decision;
  the `run_id` join against the telemetry log is the trace. `db/models.py` and `evals/schemas/context_set.schema.json` (both
  gated) are not touched.
- **D-4 — `_parse_or_retry_streaming` has no `max_tokens` parameter** (#21): recorded, not changed.
- **D-5 — `thinking_tokens` live population** is unverified (no probed call thinks); the field is built defensively.

---

## Verification

A missed consumer would surface as: (a) `tests/test_call_provenance.py` failing closed when a kwarg passed to
`messages.stream` is missing from `request_settings`; (b) an empty log file under the MagicMock fakes (#15), caught by
`test_analyzer_model_selection.py` / `test_demo_mode.py` which `json.loads` the log; (c) the `_eval_cost_since` test with
interleaved judge rows; (d) the live probe re-run showing the new fields on a real row. The consumer sweep itself is a
curation, not a computed audit: JS and Jinja readers are covered by the greps above, not by an import graph.
