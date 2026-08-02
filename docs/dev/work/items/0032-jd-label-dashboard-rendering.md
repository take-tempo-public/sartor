```toml
schema = 1
id = 32
kind = "item"
title = "jd_label not rendered anywhere in the dashboard UI"
status = "closed"
resolution = "Fixed on feat/jd-label-dashboard-rendering: added dashboard/routes.py._jd_label_display (isinstance-guarded join of the F-14 {title, company} dict -- a malformed jd_label surviving _normalize_eval_record's setdefault would otherwise resolve .title to Python's str.title method in Jinja) and _fixture_jd_labels (one shared most-recent-non-blank-wins map per fixture, so the heatmap and baseline-health table can never disagree on the same fixture's label -- they apply different record filters). Rendered on 5 surfaces: the rubric x fixture heatmap header, the baseline-health fixture cell, a RESTORED recent-eval table (deleted in the v1.0.5 tabbed-console redesign, commit edde81d -- item 32's own filing named this table's location by stale line numbers; corrected during the branch), the collate result (blueprints/diagnostics.py's anchor_jd_label, already computed by item 14 but never displayed), and the Annotate tab's fixture picker (widened GET /api/annotation/fixtures to echo jd_labels verbatim). Found and fixed a real crash surfaced by this project's own evals/results/*.jsonl: a vector_before_after_*.jsonl report from an unrelated tool shares that directory and lacks fixture/score entirely -- every other aggregation already gated on a truthy fixture, the restored table's raw per-record rendering didn't, and Jinja's Undefined raised on the score comparison. Filtered at the same point (index()'s eval_results build), with a regression test using the exact record shape. evals/README.md corrected in the same pass (2 stale claims tied to the deleted table's non-existence)."
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

### 2026-08-01 — fixed and closed (`feat/jd-label-dashboard-rendering`)

Rendered `jd_label` on all 5 dashboard/annotate surfaces named in this
item's own summary, plus the collate result. Corrected this item's own
filing: the "recent-eval table around 407/623" it named did not exist —
deleted in the v1.0.5 redesign (`edde81d`) — so this branch restored it as
a new Quality-tab tile + detail block rather than a one-line fold-in, per
owner direction. Also found and fixed a real crash: an unrelated tool's
`vector_before_after_*.jsonl` report shares `evals/results/` and lacks
`fixture`/`score` entirely; the restored table's raw per-record rendering
is the first dashboard surface to touch individual records directly
without the fixture-truthy gate every aggregation already applies, so it
raised on Jinja's Undefined instead of silently skipping the record like
every other consumer of `_read_eval_results()` does. Full gate green
(`python -m scripts.gate`): ruff, ruff format, mypy, 2161 non-UX + 136 UX
tests, `work_items check`.
