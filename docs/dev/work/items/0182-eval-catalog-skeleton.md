```toml
schema = 1
id = 182
kind = "item"
title = "Eval redesign step 2: catalog skeleton and the all-kinds gate"
status = "closed"
depends_on = [181]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-catalog-skeleton"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Catalog format, lazy loader, all-kinds gate, --list/--estimate/--max-spend; entries for the kinds already covered."
resolution = "Built and merged as PR #199 (186a064, 2026-10-22); the owner asked for it to be closed on 2026-10-27 (docs/close-eval-items-182-183-193). The four findings recorded against the build order on epic 180 stay with the epic, and costs.json still holds one machine's token means until the step 3 calibration run."
verified_by = [
  "tests/test_eval_catalog.py",
  "tests/test_eval_spend.py",
  "PR #199 merge 186a064: python -m scripts.ci_wait 199 exit 0 (read 2026-10-27, after the merge), no absorbed reruns, required checks green (CI run 39724575282)",
]
```

Step 2 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 2. Scope lives there.


## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

### 2026-10-21 -- unblocked; started on feat/eval-catalog-skeleton

Item 181 landed (PR #198, `dcbe24d`) and is closed. The owner chose this item and decided: `case_id` is `<suite>/<name>`; a call kind's measured cost lives in a machine-written `evals/catalog/costs.json` (integer token means, refreshed by `python -m evals.eval_catalog measure --write`), not in a field each run rewrites. Consumers: `docs/dev/blast-radius/eval-catalog-skeleton.md`.

### 2026-10-27 -- closed on docs/close-eval-items-182-183-193

PR #199 merged as `186a064` on 2026-10-22T04:58Z. The owner asked for the closure in chat on 2026-10-27. `python -m scripts.ci_wait 199` was run after the merge and printed `GREEN (exit 0)` and `no absorbed reruns found in any required run log` (CI run 39724575282). The closure rests on the two test files and that run. It was merged and left `open` for five days; nothing was found wrong with it in that time, which is not a test.
