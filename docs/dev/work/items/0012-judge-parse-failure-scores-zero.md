```toml
schema = 1
id = 12
kind = "item"
title = "Judge JSON-parse failure silently scores as 0, indistinguishable from a real failing grade"
status = "open"
decision_owner = "agent"
refs = ["evals/runner.py", "evals/results/20260728_164119Z.jsonl"]
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
