```toml
schema = 1
id = 121
kind = "item"
title = "run_detail reads all of llm_calls.jsonl per modal open; a non-object JSON line raises 500"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "fix/console-run-lock-hardening"]
refs = [
  "dashboard/routes.py:57-71",
  "dashboard/routes.py:1082-1110",
]
resolution = "2026-10-06, fix/console-run-lock-hardening: dashboard/routes.py: new _iter_jsonl streams object lines only (non-object JSON lines dropped; _read_jsonl wraps it). run_detail prefilters on the JSON-quoted run id (json.dumps(run_id), plus the ensure_ascii=False form), so other runs' lines are never json.loads-ed and a bare 'r1' can't match 'other1'."
verified_by = [
  "tests/test_dashboard_routes.py::TestReadJsonlSkipsNonObjects",
  "tests/test_dashboard_routes.py::TestRunDetailRoute::test_non_object_line_in_log_is_not_a_500",
  "tests/test_dashboard_routes.py::TestRunDetailRoute::test_only_this_runs_lines_are_parsed",
]
summary = "GET /api/run/<id> materializes the whole log to find one run; _read_jsonl keeps non-dict lines -> AttributeError."
```

**Observed by reading the code (epic refuters R1-7 / R2-6; re-checked at epic close).**
`run_detail()` calls `_read_jsonl(LLM_LOG)`, which builds a list of every record in the
log, then filters to one `run_id`. The log grows without bound, so every modal open costs
a full parse, with no note at the site explaining the eager load (global efficiency rule:
an eager load needs a stated reason). Separately, `_read_jsonl` skips only
`JSONDecodeError`: a line that parses to a non-object (`[]`, `3`, `"x"`) is appended, and
the first `r.get(...)` raises `AttributeError` (500). That second defect is shared with
the pre-existing readers of `_read_jsonl`.

**Suggested shape:** stream the file and keep only matching rows (a generator filter),
and have `_read_jsonl` skip non-dict values; a route test with a `[]` line asserting 200.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)

### 2026-10-06 — closed on `fix/console-run-lock-hardening`

dashboard/routes.py: new _iter_jsonl streams object lines only (non-object JSON lines dropped; _read_jsonl wraps it). run_detail prefilters on the JSON-quoted run id (json.dumps(run_id), plus the ensure_ascii=False form), so other runs' lines are never json.loads-ed and a bare 'r1' can't match 'other1'.
