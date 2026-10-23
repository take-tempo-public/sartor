```toml
schema = 1
id = 191
kind = "item"
title = "Eval redesign step 3b: generate the golden cells, calibration run, retire synthetic"
status = "blocked"
blocked_on = "step 3a (item 183) has not landed"
depends_on = [183]
decision_owner = "agent"
epic = 180
branches = ["feat/eval-dataset-v1"]
refs = ["docs/dev/eval-redesign-design.md", "docs/dev/blast-radius/eval-dataset-format.md"]
summary = "Step 3b: other professions' facts, paid generation of the 48 cells, capped calibration run, retire synthetic/."
```

Step 3b of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 3 (split by the owner on 2026-10-22; 3a is item 183). Per owner decision 2 this half blocks the v1.1.0 cut with 3a, so item 10 depends on it.

## Scope

- The O*NET facts and the level ladder for the other professions (12 professions by 4 levels, 48 cells; the three pilots from 3a are the first three). Re-read the O*NET licence text ("Except as noted below") and the DDaT ladders at the primary source before relying on them.
- The paid generation run through `evals/golden_author.py`, with `--max-spend` and `--confirm-paid`. **It needs the owner's spend approval, estimated first.**
- The capped calibration run on the finished set. Afterwards `python -m evals.eval_catalog measure --write`, so the estimate prices the judge kinds.
- Retire `evals/fixtures/synthetic/` and retarget its consumers (listed under "Deferred" in `docs/dev/blast-radius/eval-dataset-format.md`).
- Final tier sizes, from measured cost, for up to 96 cases (one fixture per JD).
- Freeze `golden-v1`: the manifest goes to `frozen` and `pilot_waivers` must be empty. A check against git history so a frozen cell cannot be rewritten in place.

## Updates

### 2026-10-22 -- filed during feat/eval-dataset-format

Filed when the owner split step 3 into 3a and 3b. Item 184 (step 4) and item 10 (the v1.1.0 cut) now depend on this item as well as on 183.
