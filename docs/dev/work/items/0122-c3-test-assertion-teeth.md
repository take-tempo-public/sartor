```toml
schema = 1
id = 122
kind = "item"
title = "Weak C3 test assertions: raw-name denylist, unbounded registry-title regex, bare 'error' in body"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "tests/test_dashboard_copy.py",
  "tests/test_annotation_routes.py:893",
]
summary = "Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names."
```

**Observed (epic refuter R2-4 / R2-7; re-read at epic close).**

1. `test_quality_tiles_have_no_unglossed_raw_names` checks five literal strings. A mutant
   adding "fabricated_specifics_rate from llm_calls.jsonl cost_usd" to a Quality tile
   survived. The rendered failure-modes tile also shows a raw rule slug
   (`invented_metric`) from the fixture data, which the test does not consider.
2. `test_help_icon_labels_match_registry_titles` searches `title: '…'` from the entry's
   start to the end of the page, so an entry missing its own title matches the next
   entry's title.
3. `tests/test_annotation_routes.py:893` asserts `"error" in body`, which almost any
   response body satisfies.

**Suggested shape:** (1) a pattern for snake_case / `*.json(l)` tokens in tile text with
an explicit allowlist; (2) bound the search to the entry's own `{…}`; (3) assert the
specific server message or status.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)
