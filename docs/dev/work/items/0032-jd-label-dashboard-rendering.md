```toml
schema = 1
id = 32
kind = "item"
title = "jd_label not rendered anywhere in the dashboard UI"
status = "open"
decision_owner = "agent"
depends_on = [14]
refs = [
  "dashboard/routes.py:_normalize_eval_record",
  "dashboard/templates/dashboard.html",
  "evals/README.md",
]
summary = "Item 14 stamped jd_label onto every eval record + bootstrap/annotation artifact; no UI surface renders it yet."
```

Filed forward from item 14 (`feat/jd-provenance-metadata`, closed 2026-08-01):
that branch's own scope boundary was the artifacts themselves (bootstrap.json,
annotations.json, expected.json, `evals/results/*.jsonl`) plus the SSE
`done` event and collate route response/log — a human reading raw files or
server logs now sees which JD a run covered. `dashboard/routes.py`'s
`_normalize_eval_record` defaults the field so nothing breaks, but no
dashboard template (the recent-eval table, the score-heatmap, the annotation
tab's fixture list) renders `jd_label` anywhere yet — a person using only the
`/_dashboard` UI still can't see a JD's identity without opening a file. Kept
deliberately out of item 14's own branch per AGENTS.md "minimal targeted
edits" — this is a UI change with its own copy/layout decisions
(`dashboard/templates/dashboard.html`'s heatmap around line 890-925, the
recent-eval table around 407/623), not a one-line fold-in.

## Updates

### 2026-08-01 — filed during feat/jd-provenance-metadata close-out
