```toml
schema = 1
id = 31
kind = "item"
title = "Surgical-refinement network-retry test: assertion flake, one isolated-clean rerun so far"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "tests/ux/regression/test_20260708_review_surface_and_flows.py",
]
summary = "test_surgical_refinement_network_failure_surfaces_error_with_retry: assertion flake under -n2 and once serial."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 5 of that epic's original 5, and unrelated to the scroll-
position mechanism items 27-29 track.

`test_surgical_refinement_network_failure_surfaces_error_with_retry`
(`tests/ux/regression/test_20260708_review_surface_and_flows.py`) failed once
(`'error' not in status_text`) under deliberate `-n 2` contention, then recurred once more during
`fix/eval-judge-parse-failure`'s gate run — that time in a plain serial `pytest -m ux` run, not
under `-n 2` — but passed cleanly on an immediate isolated rerun, the first isolation data point
for this candidate (previously "not yet reproduced in isolation" per the epic's original filing).
Still one clean-isolation sample, not a diagnosis. No diagnosis dossier exists yet — this item is
the scheduled follow-on to investigate, not a diagnosis in itself. Per C-7, the first commit on
any branch against this item must be the instrument or reproduction, never a fix.

## Updates

### 2026-07-29 — filed, split from epic 19
