```toml
schema = 1
id = 120
kind = "item"
title = "run() leaves its button pulsing (btn-pending) when it declines to start a second run"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "fix/console-run-lock-hardening"]
refs = [
  "dashboard/templates/dashboard.html",
]
resolution = "2026-10-06, fix/console-run-lock-hardening: dashboard.html sartorEval.run() acquires the run lock before setBtnPending, so a declined start returns with no pulsing button."
verified_by = [
  "tests/ux/regression/test_20261003_run_lock_ownership.py::test_declined_run_does_not_leave_its_button_pulsing",
]
summary = "run() calls setBtnPending before the acquire() check; the early return never clears it."
```

**Observed by reading the code (epic refuter R1-6; re-checked at epic close).**
The shared `window.sartorEval.run()` calls `setBtnPending(btnEl)` first, then checks
`sartorRunLock.acquire()`; on `false` it writes "A diagnostics run is already in
progress." and returns without `clearBtnPending(btnEl)`. The button keeps the
`.btn-pending` pulse after the live run ends (the lock's release re-enables it, but does
not remove the class). Only reachable through a stray enabled button, which C1a closed
for the known paths.

**Suggested shape:** move `setBtnPending` after a successful acquire, or clear it on the
early return; assert the class is absent in the C1a regression test's declined path.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)

### 2026-10-06 — closed on `fix/console-run-lock-hardening`

dashboard.html sartorEval.run() acquires the run lock before setBtnPending, so a declined start returns with no pulsing button.
