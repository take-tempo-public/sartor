```toml
schema = 1
id = 117
kind = "item"
title = "Paid diagnostics runs have no server-side single-flight lock; the run lock is per browser tab"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "dashboard/templates/dashboard.html",
  "blueprints/diagnostics.py:989",
  "blueprints/diagnostics.py:1159",
  "blueprints/diagnostics.py:745",
  "docs/dev/diagnosis/dashboard-run-lock-gaps.md",
]
summary = "Two tabs (or curl) can start two paid runs at once: LOCK_BTN_IDS/acquire() are client-only, no server lock."
```

**Observed by reading the code (epic refuter R1-1, re-checked at epic close).**
`window.sartorRunLock` (`dashboard/templates/dashboard.html`, `acquireRunLock` /
`LOCK_BTN_IDS`) is a JavaScript variable in one page. Nothing in
`blueprints/diagnostics.py`'s paid routes (`POST /api/eval/run`, `/api/tune/run`,
`/api/annotation/bootstrap`, `/api/annotation/fixture/<u>/<slug>/score`) refuses a
second concurrent run. A second tab, a reload during a run (the `beforeunload` warning is
dismissable), or a direct POST starts a second paid run.

The Epic C design brief's C1a acceptance criterion ("no second eval can start while one
is live") holds per tab only. The brief's own text admits there is no server-side lock;
the qualification is recorded in `docs/dev/diagnosis/dashboard-run-lock-gaps.md`
(epic-close note). The brief's ratified criteria text is not edited.

**Suggested shape:** a process-wide single-flight guard (a module-level lock or
`threading.Event` held for the life of the worker) that the four paid SSE routes check
eagerly and answer with 409 plus a clear message; a route test that fires two requests
and asserts the second gets 409 and no second worker starts.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)
