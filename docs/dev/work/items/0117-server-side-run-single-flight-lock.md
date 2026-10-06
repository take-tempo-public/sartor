```toml
schema = 1
id = 117
kind = "item"
title = "Paid diagnostics runs have no server-side single-flight lock; the run lock is per browser tab"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "fix/console-run-lock-hardening"]
refs = [
  "dashboard/templates/dashboard.html",
  "blueprints/diagnostics.py:989",
  "blueprints/diagnostics.py:1159",
  "blueprints/diagnostics.py:745",
  "docs/dev/diagnosis/dashboard-run-lock-gaps.md",
]
resolution = "2026-10-06, fix/console-run-lock-hardening: blueprints/diagnostics.py: a process-wide single-flight slot (_RUN_SLOT, _single_flight_sse) wraps the 4 SSE run routes (score, bootstrap, eval, tune); taken after eager validation, 409 'A diagnostics run is already in progress.' while held. The worker frees it in its finally before the sentinel; call_on_close frees it only when the stream never started. tests/conftest.py's autouse _drain_diagnostics_run_slot waits (bounded) for the slot after every test and fails naming the leaker -- never resets it."
verified_by = [
  "tests/test_annotation_routes.py::TestEvalRunRoute::test_second_concurrent_run_is_refused_409_and_never_starts",
  "tests/test_annotation_routes.py::TestEvalRunRoute::test_undrained_response_does_not_hold_the_slot",
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

### 2026-10-06 — closed on `fix/console-run-lock-hardening`

blueprints/diagnostics.py: a process-wide single-flight slot (_RUN_SLOT, _single_flight_sse) wraps the 4 SSE run routes (score, bootstrap, eval, tune); taken after eager validation, 409 'A diagnostics run is already in progress.' while held. The worker frees it in its finally before the sentinel; call_on_close frees it only when the stream never started. tests/conftest.py's autouse _drain_diagnostics_run_slot waits (bounded) for the slot after every test and fails naming the leaker -- never resets it.
