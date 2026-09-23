```toml
schema = 1
id = 112
kind = "item"
title = "The diagnostics console's Since filter raises TypeError on any date: naive date floor compared against offset-aware telemetry timestamps"
status = "open"
decision_owner = "agent"
branches = ["docs/epic-c-kickoff"]
refs = [
  "dashboard/routes.py:112-133",
  "docs/dev/reviews/epic-c-console-ux-audit.md",
]
summary = "Any Since date crashes the console: _filter_calls compares a naive floor to offset-aware (+00:00) timestamps."
```

**Observed (2026-09-22, session `0ea1b8bf`, HEAD `a078ca1`).** The pre-Epic-C UX audit
(UX-22) found this. I re-ran it independently, not on the subagent's word:

```
$ python -c "from datetime import datetime, timezone; from dashboard import routes; routes._filter_calls([{'timestamp': datetime.now(timezone.utc).isoformat()}], '2026-09-01', '', '')"
TypeError can't compare offset-naive and offset-aware datetimes
```

`dashboard/routes.py:127-133`: `floor = _parse_date(since)` is naive, and
`ts = _parse_date(r.get("timestamp", "").rstrip("Z"))` is aware for `isoformat()`
timestamps (`+00:00`, not `Z`). Then `if ts and ts < floor:` raises.

**Out of Epic C scope.** RELEASE_ARC §Epic C (C1/C2/C3) does not name the filters' behavior,
only "filter-scoping explainers" copy (C3). Fixing it is its own `fix/*` branch. C-7:
the reproduction above is the Observed; the first commit is a failing test with an aware
timestamp. The invoker may raise it with the owner as a candidate addition to C1. It is
not folded in silently.
