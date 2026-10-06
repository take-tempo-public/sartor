```toml
schema = 1
id = 119
kind = "item"
title = "Run lock has no owner; tune, bootstrap and annScore ignore acquire()'s return value"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "fix/console-run-lock-hardening"]
refs = [
  "dashboard/templates/dashboard.html",
  "docs/dev/diagnosis/dashboard-run-lock-gaps.md",
]
resolution = "2026-10-06, fix/console-run-lock-hardening: dashboard.html window.sartorRunLock: acquire() returns a numeric owner token or null; release(token) is a no-op unless that token owns the lock. All 4 acquire sites (run(), tune, bootstrap, score-grounding) keep the token and bail on null before any pending state or POST; all 10 release sites pass it."
verified_by = [
  "tests/ux/regression/test_20261003_run_lock_ownership.py::test_stale_release_does_not_free_a_live_run",
  "tests/ux/regression/test_20261003_run_lock_ownership.py::test_bootstrap_click_while_locked_issues_no_post",
]
summary = "Any release() frees the lock, and three inline acquire() sites start a run even when acquire() returned false."
```

**Observed by reading the code (epic refuter R1-4; re-checked at epic close).**
`acquireRunLock()` returns `false` when a run is live, but the tuning, bootstrap and
Score-grounding handlers call `window.sartorRunLock.acquire()` and carry on regardless
(only the shared `run()` streamer checks the return). `releaseRunLock()` takes no token,
so any completion path (including one that never acquired) frees the lock while another
run is still live, re-enabling every lock-governed button.

C1a deferred the three inline sites on the premise that they had "no reachable path to a
second click while locked". Epic review R2-2 falsified that premise for `#annCollate`
(fixed at epic close); the general ownership gap remains.

**Suggested shape:** `acquire()` returns a token (or `null`), `release(token)` is a no-op
for a stale token, and every caller bails when it gets `null`. A UX test that forces a
second handler's click while locked and asserts no second POST is issued.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)

### 2026-10-06 — closed on `fix/console-run-lock-hardening`

dashboard.html window.sartorRunLock: acquire() returns a numeric owner token or null; release(token) is a no-op unless that token owns the lock. All 4 acquire sites (run(), tune, bootstrap, score-grounding) keep the token and bail on null before any pending state or POST; all 10 release sites pass it.
