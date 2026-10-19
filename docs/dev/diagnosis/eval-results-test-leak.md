# Diagnosis — a test writes stub eval runs into the real `evals/results/`

> **Status:** writer **hypothesis only** until the reproduction in `## Falsification` has run; the symptom itself is observed.
> **Branch:** `fix/eval-results-test-leak` (work item 179)

---

## Symptom

`evals/results/` (gitignored; read by the runner's regression check and by the dashboard) is mostly test output. Found while
scoping item 137's candidate A/B: any baseline built from this directory would be built from stubs.

---

## Observed

All on `main` at `18dbc26`, 2026-10-19, read-only.

- `python -` over `glob('evals/results/2026*.jsonl')`: **425 files, 337 contain the string `led a project`** (printed
  `425 files; 337 contain stub text "led a project"`). By month prefix, the same script: `('202607', 137), ('202608', 118),
  ('202609', 35), ('202610', 47)` for the 337, against `202605 43, 202606 27, 202607 145, 202608 118, 202609 35, 202610 57`
  for all 425. 88 files do not contain it.
- The same script grouped the 337 by a record signature and printed ONE group:
  `337 (6, ('4.5',), '{"score": 4.0, "summary": "ok"}', ('data-scientist-junior', 'pm-senior', 'sre-mid-level'))`, example
  `20260709_181839Z.jsonl`: 6 rows, grounding score `4.5` everywhere, `distinctiveness` `{"score": 4.0, "summary": "ok"}`, the
  three smoke fixtures.
- Newest four, `evals/results/20261019_030028Z.jsonl`, `_051655Z`, `_173853Z`, `_190655Z`: 6 rows each, `cost_usd` 0,
  `judge_request_id` null, `prompt_version` `2026-10-17.2` (`head -c 1500 evals/results/20261019_190655Z.jsonl`).
- `tests/test_annotation_routes.py:1150-1196` (`test_grounding_scorer_failure_streams_warning_not_error`): stubs `runner._grade`
  to `{"score": 4.5, ...}`, `runner._score_distinctiveness` to `{"score": 4.0, "summary": "ok"}` and `runner.generate` to
  `"- Led a project\n- Built a system"`, patches `runner.RESULTS_DIR` to `ann_app.OUTPUT_DIR / "eval_results"`, then POSTs
  `/api/eval/run`. That test was added in `9b2d3d6` (2026-07-08, `git log -S`).
- `blueprints/diagnostics.py:1118` and `:1306` call `run_suite(...)` with no `out_dir` argument.
- `evals/runner.py:1204`: `out_dir: str | Path = RESULTS_DIR` (a default, bound when the function is defined), and
  `evals/runner.py:1340-1353` writes `out_dir / f"{timestamp}.jsonl"`.
- `evals/runner.py:581-619` (`_load_baseline_scores`): every non-candidate `*.jsonl` in `RESULTS_DIR` is layered over
  `baseline_v1.json`, newest timestamp wins. `dashboard/routes.py:116-119` globs the same directory.
- `tests/conftest.py:16-136`: autouse redirects exist for `analyzer.LOG_PATH`, the gate result, the witness state, the session
  id and the plan-gate state; none for the eval results dir.
- Prior sighting: `docs/dev/diagnosis/llm-handle-leak-and-letter-date.md:161` records ONE stray file,
  `evals/results/20261017_093904Z.jsonl`, "from a pytest run (`test_eval_runner`, stubbed)", as a one-off.

- **Reproduction (2026-10-19).** `git worktree add --detach /c/Dev/sartor-leak-repro main`, then there
  `PYTHONPATH=/c/Dev/sartor-leak-repro python -m pytest tests/test_annotation_routes.py -k
  test_grounding_scorer_failure_streams_warning_not_error -p no:cacheprovider -q` → `1 passed`. The worktree's
  `evals/results/` went from 1 entry (`baseline_v1.json`) to 2: new file `20261019_204936Z.jsonl`, 6 rows, contains
  `led a project`, fixtures `data-scientist-junior`/`pm-senior`/`sre-mid-level`, grounding `[4.5]`, `cost_usd` 0.0,
  `distinctiveness` `{"score": 4.0, "summary": "ok"}`: the 337-file signature. The real `evals/results/` listing was
  identical before and after (`diff` of `ls`, printed `REAL_DIR_UNCHANGED`), so the lone test writes to the checkout it runs from.
- **Regression test fails on unchanged code.** `tests/test_eval_runner.py::TestRunSuite::test_run_suite_default_out_dir_follows_patched_results_dir`
  copied into the same worktree: `1 failed`, `AssertionError: assert WindowsPath('C:/Dev/sartor-leak-repro/evals/results')
  == WindowsPath('C:/Users/iam/AppData/Local/Temp/pytest-of-iam/pytest-7129/test_run_suite_default_out_dir0/patched_results')`
  (`result.out_path` was `.../evals/results/20261019_205006Z.jsonl`). Real dir again unchanged. (The log also shows
  `Fixture load failed: corpus ... jd.txt` in the worktree: a gitignored fixture absent from a fresh checkout, unrelated.)

## Falsified

_(Nothing yet.)_

---

## Inferred

**Partly confirmed (see the Reproduction bullet): that test alone writes a file with the signature.** Still only inferred:
that it wrote all 337 (every one has the signature, but a second test with the same stubs would too) and that no other
writer exists. The session sentinel in the fix is the instrument for the second. Original hypothesis, kept: that test is the writer of all 337 files: its
`RESULTS_DIR` patch rebinds the module global, but `run_suite`'s default was bound at definition time, and the route passes no
`out_dir`, so the run writes to the real directory. The stub signature matches this test. What is not seen: a file produced by
running that test alone, and the absence of any second writer (the 20261017 file is attributed to `test_eval_runner` by a
prior session, a different test file). Other tests that call `run_suite` without `out_dir` have not been enumerated yet.

---

## Falsification

1. In a detached worktree of `main` outside the repo (its own `evals/results/`), run only the suspect test. **If a new file with
   the signature appears there**, the writer is confirmed. **If none appears**, the hypothesis is dead: do not fix; widen the
   instrument (the session sentinel runs over the whole suite) and report.
2. Regression test (`tests/test_eval_runner.py`): with `runner.RESULTS_DIR` patched to `tmp_path` and the LLM calls stubbed,
   `run_suite(...)` with no `out_dir` must write under `tmp_path`. It must fail on `main`.

## The fix

_(Only after step 1 and 2 above have run; recorded here as they happen.)_

## Acceptance bar

The regression test passes and fails on the old code; the session sentinel fails the session when the old runner is used with
the new conftest; `python -m scripts.gate --result` reads PASSED on the final tree with no `RERUN` markers; the file list of the
real `evals/results/` is identical before and after the gate run.
