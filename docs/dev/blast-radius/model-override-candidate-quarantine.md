# Blast radius — model-override-candidate-quarantine

> **Branch:** `feat/model-override-candidate-quarantine`
> **Status:** enumeration complete before the first code edit (greps run 2026-10-19 at `a4ee842`, `main` @ `70a118f`).
> **Provenance (C-12):** the first-pass enumeration was produced by an Explore subagent; the sites marked **(re-read)** I
> re-read myself in this session before writing a decision. Rows without that mark rest on the subagent's report and are
> re-checked by the tests listed under Verification, not by my own reading.

**Registry note:** `analyzer.py` and `hardening.py` are `ACKNOWLEDGED_NOT_GATED` in `scripts/enforcement/blast_radius.py:198-209`, so
`require-consumer-enumeration` does not fire on them. `evals/runner.py` and `dashboard/routes.py` are not in the registry either. This
dossier is written anyway: the eval record shape and the `model` field of the call log are shared contracts (charter C-10).

---

## Surface

- `analyzer.py`: new `model_overrides()` context manager + `_model_overrides` ContextVar (next to `prompt_overrides`, `:693-718`);
  `_resolve_model()` applied at `_call_llm`'s `effective_model = model or SONNET_MODEL` line (`:1699`); `pinned_model` on the telemetry
  row of an overridden call only; `active_model_overrides()` for the eval runner.
- `evals/candidates.py` (new, stdlib only): `is_candidate_record(rec)` and `CANDIDATE_VERSION_PREFIX`.
- `evals/runner.py`: `run_suite(model_overrides_map=...)`, `--model-override NAME=ID`, effective `model_snapshots` + `model_overrides`
  on every record, `_load_baseline_scores` skips candidate records.
- `dashboard/routes.py`: baseline aggregations skip candidate records; Pareto scatter labels them.
- Docs that state the quarantine (corrected in the same branch).

---

## Enumeration

| Name searched | Result |
|---|---|
| `model_overrides`, `_model_overrides`, `model_override`, `MODEL_OVERRIDE`, `--model-override`, `pinned_model`, `is_candidate_record`, `active_model_overrides`, `_resolve_model` (all `*.py`, `*.md`, `*.html`) | **0 hits**: new names. |
| `os.environ`, `getenv`, `ANTHROPIC_MODEL`, `SARTOR_*MODEL`, `setattr(analyzer` over non-test `*.py` | **No existing way to change the analyzer's model** (negative result). `--model` appears only in `scripts/build_vector_index.py:189` (an embedding model). |
| `messages.stream(` / `messages.create(` | `analyzer.py:1765` (the one product send) and `evals/runner.py:442` (the one judge send). Unchanged from the previous dossier's count. |
| `from analyzer import ... HAIKU_MODEL` | `onboarding/extract_experiences.py:29` and `evals/runner.py:47-48`: **import-time copies of the pin**, so a reassignment of `analyzer.HAIKU_MODEL` would miss them. The override therefore resolves by *value* at the one send site. **(re-read)** |
| `candidate:` prefix checks in non-test code | **0 outside `analyzer.effective_prompt_version`**: no reader filters on it today. **(re-read: `_load_baseline_scores` `:592-613`, `dashboard/routes.py` `:259-356,413-631,655-760,929-997`.)** |
| `MODEL_SNAPSHOTS` / `model_snapshots` | defined `runner.py:120`; written at `:1470,1682,1742,1842,1939`. Read by no non-test code. **(re-read: the five write sites.)** |
| `eval_mode` | written on every record; used only inside `run_suite` to keep assemble runs out of the regression gate. Not read by the dashboard. |

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `analyzer.py:1699` `effective_model` in `_call_llm` | **update** | `_resolve_model(model or SONNET_MODEL)`. No override active → the identical string, so the default path is byte-identical. |
| 2 | `analyzer.py:1745` `thinking_setting(effective_model)` | no change | Runs on the *resolved* model, so the candidate gets its own `THINKING_POLICY` value (a `disabled` sent to Sonnet 5.5 would 400). `model_overrides()` refuses a target with no entry up front. |
| 3 | `analyzer.py:1801-1822` telemetry row | **update** | `model` is the model requested, which is now the candidate, so `compute_call_cost` prices it. `pinned_model` is added **only when an override changed the model**, following the `error_*` precedent, so every other row keeps its bytes. |
| 4 | `analyzer.py` `log_judge_call` (`:813`) | no change | Judge rows name `JUDGE_MODEL` and never pass through `_resolve_model`. They still carry `prompt_version=candidate:<hash>` under a prompt override, as today. |
| 5 | 14 `model=HAIKU_MODEL` + 4 `model=SONNET_MODEL` call sites in `analyzer.py`, `onboarding/extract_experiences.py:174` | no change | All reach `_call_llm`, so all get the swap. |
| 6 | `evals/runner.py:47-48` imports, `:116-124` `JUDGE_MODEL`, `MODEL_SNAPSHOTS` | no change to the constants | `MODEL_SNAPSHOTS` stays (tests pin it, `test_judge_call_provenance.py:241-244`, `test_hardening.py:792,816`). A new `_effective_model_snapshots()` returns it unchanged with no override and substitutes the candidate ids when one is active. |
| 7 | `evals/runner.py:1451,1658,1749,1848,1922` writers + `:1742` merge | **update** | `model_snapshots` takes the effective value; `model_overrides` is added only when active. No test pins an exact key set (subagent report; confirmed by the full-suite run). |
| 8 | `evals/runner.py:557-616` `_load_baseline_scores` | **update** | Skips `is_candidate_record`, so a candidate never becomes the next run's "prior run" and a candidate cannot seed a regression alert for a baseline run. A candidate run is still compared against the non-candidate baseline. |
| 9 | `evals/runner.py:1240-1256` override banner, `run_suite` signature | **update** | Adds `model_overrides_map`; validated once before the fixture loop (a `ValueError` before any paid call), like `prompt_overrides_map`. |
| 10 | `evals/runner.py:~2073-2170` CLI | **update** | `--model-override NAME=ID` (repeatable); a malformed value exits 1 before any paid call. |
| 11 | `dashboard/routes.py:227` `_per_rubric_pass_rate` | **update** | Skips candidate records in its existing loop (no extra pass). A losing candidate would otherwise lower the headline pass rate. |
| 12 | `dashboard/routes.py:259` `_score_over_time` | **update** | Adds the predicate to the existing filter. Today a candidate point lands on the same rubric line as baseline points; `tests/test_dashboard_routes.py:72-99` pins that and is tightened. |
| 13 | `dashboard/routes.py:309` `_rubric_fixture_heatmap` | **update** | Skips candidates in the existing loop; newest-wins would otherwise show a candidate's score as the cell. |
| 14 | `dashboard/routes.py:392` `_failure_mode_frequency` | **update** | Skips candidates in the existing loop (a candidate's failed rules are not the baseline's failure modes). Not in the original plan's list; included because it is the same class (a baseline aggregate). |
| 15 | `dashboard/routes.py:413` `_pareto_data` | **update** | Scatter keeps candidates as **their own labelled series** (key = `prompt_version`, plus ` · SONNET_MODEL→<id>` for a model candidate, so a model candidate under the real `PROMPT_VERSION` does not merge with the baseline series). The "baseline trajectory" polyline, the most-recent-change summary and the latency/cost trend lines use baseline versions only. **Refinement of the plan:** the plan said the trends keep candidates; a trend over time with a candidate on its x-axis reads as a chronological change, which is the mislabel this branch removes. |
| 16 | `dashboard/routes.py:655-760` groundedness points / trend / latest detail | **update** | `_groundedness_points` skips candidates, so the trend and the latest-detail panel (which derives from the same points) agree. |
| 17 | `dashboard/routes.py:929` `_baseline_health` | **update** | Skips candidates in its loop; a candidate run must not flip the badge to "regressed". |
| 18 | `dashboard/routes.py:1074-1077` eval-results table (last 200 records) | no change | A record listing, not an aggregate: shows candidates, which is correct (they are real records). |
| 19 | `dashboard/routes.py:373` `_fixture_jd_labels` | no change | JD labels are fixture properties, identical across candidate and baseline records. |
| 20 | `dashboard/routes.py` call-log readers (`_filter_calls`, `_summarize_calls`, `_cost_by_call_kind`) | no change | Group by `call` / filter by `model`; an overridden row carries the candidate id in `model` and is priced by `compute_call_cost`. The `model` dropdown will list it, which is accurate. |
| 21 | `compute_call_cost` users: `evals/runner.py:521-551` `_eval_cost_since`, `scripts/smoke_phase_b1.py:203-217`, `scripts/probe_call_provenance.py:129`, `evals/corpus_drafting_probe.py:110-128` | no change | Key on `record["model"]`. Priced because `model_overrides()` refuses a target with no `MODEL_PRICING` entry. |
| 22 | `commands/bench.md:14` | no change | Aggregates by `(call, model, prompt_version)`; a candidate model is its own group. Reads the cost from the pricing page, not `compute_call_cost`. |
| 23 | `blueprints/diagnostics.py:1205-1411` `/api/tune/run` | no change (see Deferred) | Runs `run_suite` twice by file path; it never passes a model override, so its behaviour is unchanged. |
| 24 | `evals/tune.py` `load_scores` (`:58-86`) | no change | Compares two files by path; separation is by file. |
| 25 | `evals/bootstrap.py:294`, `evals/annotation.py:520,603,725`, `db/build_context.py:181` (`ApplicationRun.prompt_version`) | no change | Stamp `effective_prompt_version()`, which a model override does not alter (the model is a separate field). |
| 26 | Tests that pin shapes: `tests/test_eval_runner.py:258-282,390-409,438-468`, `tests/test_dashboard_routes.py:72-115,457-550,783`, `tests/test_prompt_overrides.py`, `tests/test_call_provenance.py:171,341` | **update** the ones that pin the old behaviour (`test_dashboard_routes.py:72-99`) | The rest must pass unchanged: they prove the default path is byte-identical. |
| 27 | Docs that state or imply the quarantine: `AGENTS.md:235-240`, `evals/README.md` (override section, console A/B, field table, `model_snapshots` example), `dashboard/README.md`, `commands/prompt-tune.md`, `commands/tune-from-annotations.md`, `dashboard/templates/dashboard.html` help strings, `docs/dev/keep-ledger.md` | **update** | Today they say candidate runs are "quarantined from score-over-time". The code did not do that. After this branch it does; the wording is rewritten to say exactly what is excluded. |
| 28 | Wiki: `prompt-version-discipline.md`, `eval-harness.md`, `diagnostics-console.md`, `llm-call-catalog.md`, `deterministic-llm-boundary.md` | handled by the close-out's scoped `/wiki-self-update` | Not hand-edited here; the wiki obligation is a separate close-out step. |
| 29 | `CHANGELOG.md` | **update** | New CLI flag, new record fields, behaviour change of the dashboard and the regression baseline. No dependency. |

---

## Deferred

- **A model-override input on the console route `/api/tune/run`** (`blueprints/diagnostics.py`). UI and request-schema work; the CLI is
  enough for the candidate A/B, and the route's behaviour is unchanged. Own item if the owner wants it.
- **`_load_baseline_scores` ignores `eval_mode`**, so an assemble-mode run still seeds a generate-mode run's baseline. A different
  population problem from candidates; noted, not touched.
- **Candidate runs stay in the eval-results table and the call log.** They are real records; only the baseline *aggregates* exclude them.
- **Opus 5.5** has no price or policy entry, so `model_overrides()` refuses it (stated in the error). Add both when a call exists.
- **Any pin move and the paid A/B itself.** Unchanged: needs the owner's spend approval.

---

## Verification

- `tests/test_model_overrides.py` (new): the default request and row are unchanged; an override swaps `model` and `thinking`; each refusal raises before `messages.stream`; the ContextVar resets; the judge send is unaffected.
- The existing default-path tests (`test_eval_runner.py:390-409,438-468`, `test_prompt_overrides.py`, `test_call_provenance.py`) pass unchanged.
- A prefix-agreement test pins `evals/candidates.CANDIDATE_VERSION_PREFIX` to the string `analyzer.effective_prompt_version()` produces.
- Re-run at close-out: the `messages.stream(` / `messages.create(` counts above (still exactly one product and one judge send).
