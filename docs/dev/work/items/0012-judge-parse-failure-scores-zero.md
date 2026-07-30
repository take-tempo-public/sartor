```toml
schema = 1
id = 12
kind = "item"
title = "Judge JSON-parse failure silently scores as 0, indistinguishable from a real failing grade"
status = "closed"
decision_owner = "agent"
resolution = "Fixed on fix/eval-judge-parse-failure: dashboard/routes.py's _score_over_time and _rubric_fixture_heatmap now exclude status==judge_error records instead of only checking isinstance(score, (int, float)) (true for the common in-_grade JSON-decode-failure path's score=0)."
refs = ["evals/runner.py", "evals/results/20260728_164119Z.jsonl", "dashboard/routes.py", "docs/dev/diagnosis/eval-judge-parse-failure.md"]
summary = "_grade coerces a judge parse failure into score=0 instead of null/error - a crash reads as 'worst possible quality'."
```

Found 2026-07-28. `evals/results/20260728_164119Z.jsonl`'s
`callback_likelihood` record: `score: 0`, full `reasons` field is literally
`["judge response was not valid JSON"]`. The Haiku judge call failed to
parse and `_grade` silently converted that into the worst possible numeric
score rather than a null/skip/error state. A crashed grader and a résumé
that completely fails a rubric are currently indistinguishable in the
output — anyone reading the eval result (or a heatmap built from it) sees
"0" either way.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

### 2026-07-29 — fixed on fix/eval-judge-parse-failure

Reproduced first (C-7): `docs/dev/diagnosis/eval-judge-parse-failure.md`'s `## Observed`
traces the mechanism to two dashboard consumers, not `_grade` itself (`_grade` already tagged
`status: "judge_error"` correctly; the gap was that `_score_over_time` and
`_rubric_fixture_heatmap` never read that field). Two new tests
(`tests/test_dashboard_routes.py::TestScoreOverTime::test_judge_error_record_excluded_from_trend`,
`::TestRubricFixtureHeatmap::test_judge_error_record_rendered_as_empty_not_red`) fail on
unfixed HEAD, pass after. `_per_rubric_pass_rate` and `evals/runner.py`'s `n_pass`/`n_fail`
exit-code gate deliberately left untouched — see the diagnosis doc's `## Falsified` for why
those are already-correct, already-tested, deliberate design (a pass/fail gate has no
"why did it fail" distinction to be misled by; only a quality-value visualization does).
