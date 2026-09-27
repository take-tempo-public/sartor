```toml
schema = 1
id = 121
kind = "item"
title = "run_detail reads all of llm_calls.jsonl per modal open; a non-object JSON line raises 500"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "dashboard/routes.py:57-71",
  "dashboard/routes.py:1082-1110",
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
