# Diagnosis — judge JSON-parse failure plots/colors as a real 0/5 quality score

> **Status:** root cause PROVEN — directly reproduced with two failing unit tests against the real aggregation helpers.
> **Branch:** `fix/eval-judge-parse-failure`

---

## Symptom

Item 12 (`docs/dev/work/items/0012-judge-parse-failure-scores-zero.md`):
`evals/results/20260728_164119Z.jsonl`'s `callback_likelihood` record showed
`score: 0` with `reasons: ["judge response was not valid JSON"]` — a crashed
Haiku judge call, not a real graded 0/5. The cited result file is not present
in this clone (`evals/results/` is gitignored, real-run data; this session
did not find it on disk), so — same pattern as item 11's now-rotated
fixture — the mechanism was reproduced fresh against the live code rather
than trusted from the stale citation.

---

## Observed

Reproduced directly, on demand, against the current (unfixed) code:

- **`evals/runner.py:556-570` (`_grade`)** — when Haiku responds but the
  response text fails `json.loads`, `_grade` returns
  `{"score": 0, "reasons": [...], "status": "judge_error"}`. This is
  confirmed by the existing, passing test
  `tests/test_eval_runner.py::TestGrade::test_unparseable_json_marks_status_judge_error`
  (pins `grade["score"] == 0` in the sibling test
  `test_unparseable_json_returns_zero`, line 153-164). **`score` is `0`, an
  `int`, not `None`, for this path** — this is the common case (Haiku
  responded, the text just wasn't parseable JSON), distinct from the rarer
  caller-level `except Exception` path at `evals/runner.py:1605-1612` (and
  `:844-848`), which sets `score: None` for the same `status: "judge_error"`
  tag.
- **`tests/test_dashboard_routes.py::TestPerRubricPassRate::test_pipeline_error_rows_count_as_fail`**
  (existing, line 52-59) exercises only the `score: None` shape. There was
  no existing coverage of the far more common `score: 0` shape reaching
  `dashboard/routes.py`'s chart/heatmap helpers.
- Added two new tests against the real (unmodified) helpers, run on HEAD
  (`f26687f`, unfixed):
  - `tests/test_dashboard_routes.py::TestScoreOverTime::test_judge_error_record_excluded_from_trend`
    — feeds `_score_over_time` a `{"score": 0, "status": "judge_error", ...}`
    record alongside a real `4.5` record for the same rubric.
    **FAILS on HEAD:**
    ```
    assert 0 not in scores
    E   assert 0 not in [0, 4.5]
    ```
    `_score_over_time` (`dashboard/routes.py:246-250`) filters only on
    `isinstance(r.get("score"), (int, float))` — never reads `status` — so
    the judge_error's `0` is plotted on the quality-trend chart as a real
    data point, on the same line as genuine graded scores.
  - `tests/test_dashboard_routes.py::TestRubricFixtureHeatmap::test_judge_error_record_rendered_as_empty_not_red`
    — feeds `_rubric_fixture_heatmap` a single `{"score": 0, "status":
    "judge_error", ...}` record as the only entry for a (rubric, fixture)
    pair. **FAILS on HEAD:**
    ```
    assert cell["score"] is None
    E   assert 0 is None
    ```
    `_rubric_fixture_heatmap` (`dashboard/routes.py:282-324`) has the exact
    same `isinstance(score, (int, float))` gate at line 308, with no
    `status` check — the cell renders `score: 0` and, per the hue formula
    at line 313 (`hue = max(0.0, min(120.0, 120.0 * score / 5.0))`), colors
    hard red (`hsl(0 ...)`) — pixel-identical to a fixture that was
    actually graded 0/5.
- Both failures are direct assertion failures with tracebacks from a single
  clean run (no `pytest-rerunfailures` involved) — not inferred from reading
  the helpers.

---

## Falsified

- **Hypothesis considered: the exit-code/gate contract (`n_pass`/`n_fail`
  counting in `evals/runner.py`, feeding `exit_code = 0 if (n_fail == 0 and
  not regressions) else 2` at `:1827`) is also broken by this defect.**
  Checked: `n_fail` is incremented for a judge_error record the same way
  (`isinstance(score, (int, float)) and score >= PASS_THRESHOLD` else
  `n_fail += 1`, `:1658-1664` and the iteration-mode twin at `:1561-1566`),
  with no `status` check there either. **Not treating this as part of the
  same defect** — `_per_rubric_pass_rate`'s own docstring
  (`dashboard/routes.py:206-211`) states judge_error/pipeline_error rows are
  *deliberately* counted as failures "so the dashboard surfaces them clearly
  rather than hiding behind None," and its existing test
  (`test_pipeline_error_rows_count_as_fail`) pins that as intentional. A
  binary gate ("was this fixture fully, successfully graded — yes/no") is
  correctly "no" either way, whether the judge crashed or genuinely scored
  0/5; there is no confusion for a gate to be misled by. The defect is
  specifically that a **quality-value visualization** (a line on a trend
  chart, a color on a heatmap) represents "we don't know the quality" and
  "the quality is the worst possible" identically. Left untouched; noted
  here so a future reader doesn't need to re-derive this distinction.
- **Hypothesis considered: `_grade` itself should return `None` instead of
  `0` on JSON-decode failure**, unifying both judge_error shapes. Rejected —
  `evals/runner.py:571-573`'s own comment states downstream aggregations
  "rely on a uniform numeric type," and changing `_grade`'s return shape
  would touch the `iter_record`/`record` construction call sites and their
  existing passing tests (`test_unparseable_json_returns_zero` pins
  `score == 0`) for no benefit — the `status` field already carries the
  distinguishing information; the bug is that two consumers don't read it.

---

## Inferred

None beyond what `## Observed` already demonstrates directly — the two
failing tests ARE the mechanism, not a guess about it.

---

## Falsification

**Experiment:**
```
python -m pytest tests/test_dashboard_routes.py -k "test_judge_error_record_excluded_from_trend or test_judge_error_record_rendered_as_empty_not_red" -v
```

- **Fails on HEAD (confirmed above, both tests):** hypothesis confirmed —
  build the fix.
- **Passes on HEAD:** would mean the helpers already exclude judge_error
  records; not the case here, so this branch proceeds to the fix.

---

## The fix

Scope: `dashboard/routes.py`'s `_score_over_time` and
`_rubric_fixture_heatmap` only. Add a `status != "judge_error"` guard to
each, matching the pattern already established elsewhere in this codebase
for the identical distinction (`evals/runner.py:1615`'s `fixture_scores`
guard, `evals/runner.py:1686`'s regression-detection guard, and
`evals/tune.py`'s score-loading guard) — this fix brings these two
dashboard visualizations into line with the guard convention the rest of
the codebase already uses for this exact `status` field, rather than
inventing a new convention.

`_score_over_time`: exclude judge_error records from the filtered set (they
contribute no point to the trend line — same treatment as records missing
`prompt_version`).

`_rubric_fixture_heatmap`: treat a judge_error record as if no record
existed for that (rubric, fixture) pair when it is the latest — render the
empty-cell shape (`{"score": None, "color": "#1a1a20"}`) instead of a red
cell, so a transient Haiku parse failure doesn't visually read as "this
fixture's grade cratered."

`_per_rubric_pass_rate` is explicitly NOT touched (see `## Falsified`) —
its "count judge_error as fail" behavior is a deliberate, already-tested
design choice for a pass/fail gate view, not part of this defect.
`evals/runner.py`'s `n_pass`/`n_fail`/`exit_code` gate is likewise NOT
touched for the same reason.

---

## Acceptance bar

- `test_judge_error_record_excluded_from_trend` and
  `test_judge_error_record_rendered_as_empty_not_red` pass (a single clean
  run, not via a rerun).
- Full existing `tests/test_dashboard_routes.py` suite still passes
  unchanged, including `test_pipeline_error_rows_count_as_fail` (must keep
  passing exactly as-is — that behavior is deliberately untouched).
- `python -m scripts.gate` green.
