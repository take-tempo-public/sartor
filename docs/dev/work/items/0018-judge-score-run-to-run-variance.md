```toml
schema = 1
id = 18
kind = "item"
title = "Large judge-score variance between back-to-back runs of the same fixture"
status = "watching"
decision_owner = "agent"
refs = ["evals/results/20260728_164011Z.jsonl", "evals/results/20260728_164119Z.jsonl"]
summary = "Same fixture, 68s apart: tone 3.2->2.1, clarification_quality 3.2->3.8, composite 4.06->3.89 - n=2, uncharacterized."
```

Found 2026-07-28. Two eval runs of `robert-bootstrap`, 68 seconds apart,
same nominal input, real (non-error) reasoning behind both scores — this
isn't the item-12 parse-failure bug, both these rubrics graded successfully
both times. The swing is large enough to be worth tracking, but n=2 is not
enough to characterize it as a real reliability problem vs. expected LLM
judge noise. Needs more samples before concluding anything either way.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking
