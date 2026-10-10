```toml
schema = 1
id = 122
kind = "item"
title = "Weak C3 test assertions: raw-name denylist, unbounded registry-title regex, bare 'error' in body"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "test/assertion-strength"]
refs = [
  "tests/test_dashboard_copy.py",
  "tests/test_annotation_routes.py:893",
]
summary = "Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names."
resolution = "2026-10-10, test/assertion-strength: raw names are matched by shape (snake_case, *.json(l)) over space-joined tile text with a used allowlist (invented_metric); the registry title search is bounded to the entry's own block; the Score-grounding help test asserts the specific claim 'a missing one stops it with an error'. The three mutants named in the filing each passed the HEAD test and fail the new one."
verified_by = [
  "tests/test_dashboard_copy.py::TestCopyContent::test_quality_tiles_have_no_unglossed_raw_names",
  "tests/test_dashboard_copy.py::TestEveryTileHasLayLineAndBubble::test_help_icon_labels_match_registry_titles",
  "tests/test_annotation_routes.py::TestScoreGrounding::test_score_grounding_help_matches_server_behaviour",
  "docs/dev/diagnosis/assertion-strength.md (A1 before, A3 after: raw-names, title-hole, error-claim)",
]
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

### 2026-10-10 — closed on `test/assertion-strength`

All three, as suggested (`docs/dev/diagnosis/assertion-strength.md` A0, A1, A3):

1. Raw names are matched by shape (snake_case, `*.json(l)`) over tile text joined with spaces.
   A probe showed `_Node.all_text()` glues neighbours (`modeinvented_metricnamed`). The
   allowlist is `invented_metric`, the rule id the failure-modes tile reports, and an entry
   no longer rendered fails too. `≥2` stays as a literal check: it is notation, not a name.
2. The title search is bounded to the entry's own block (`_registry_entry()`, which
   `_registry_body()` now shares).
3. `test_annotation_routes.py` asserts the help's specific claim, "a missing one stops it with
   an error".

Each mutant (the refuter's raw-name string; an entry with no title whose bubble names the next
entry's; help wording that keeps the word "error" but drops the claim) passed the HEAD test and
fails the new one.
