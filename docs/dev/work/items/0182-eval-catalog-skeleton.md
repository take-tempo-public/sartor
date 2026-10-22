```toml
schema = 1
id = 182
kind = "item"
title = "Eval redesign step 2: catalog skeleton and the all-kinds gate"
status = "open"
depends_on = [181]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-catalog-skeleton"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Catalog format, lazy loader, all-kinds gate, --list/--estimate/--max-spend; entries for the kinds already covered."
```

Step 2 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 2. Scope lives there.


## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions

### 2026-10-22 -- unblocked; started on feat/eval-catalog-skeleton

Item 181 landed (PR #198, `dcbe24d`) and is closed. The owner chose this item and decided: `case_id` is `<suite>/<name>`; a call kind's measured cost lives in a machine-written `evals/catalog/costs.json` (integer token means, refreshed by `python -m evals.eval_catalog measure --write`), not in a field each run rewrites. Consumers: `docs/dev/blast-radius/eval-catalog-skeleton.md`.
