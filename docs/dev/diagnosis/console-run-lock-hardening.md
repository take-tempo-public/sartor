# Diagnosis — diagnostics console: run lock, Since filter, redaction, run detail (items 112, 117–121)

> **Status:** each defect reproduced by a test that fails on `main` (d270506); fixes follow.
> **Branch:** `fix/console-run-lock-hardening`

---

## Symptom

Six defects filed against the diagnostics console (`/_dashboard`) by the Epic C review and
UX audit: a Since date crashes the console (112); two paid runs can start at once (117); the
error-message redaction misses some header shapes (118); the client run lock has no owner and
three handlers ignore a declined acquire (119); a declined `run()` leaves its button pulsing
(120); the run-detail modal reads the whole log and 500s on a non-object line (121).

---

## Observed

All runs below are on this branch's worktree at `main` d270506 with only the new tests added,
Windows 11, Python 3.13.14, pytest 9.1.1, Playwright Chromium.

- **112.** `python -m pytest tests/test_dashboard_routes.py -k test_date_only_floor_against_aware_timestamps`
  fails with
  ```
  E   TypeError: can't compare offset-naive and offset-aware datetimes
  ```
  from `dashboard/routes.py:132` (`if ts and ts < floor`), where `floor` is
  `datetime.fromisoformat("2026-09-01")` (naive) and `ts` parses `…+00:00` (aware).
  `TestFilterCallsSinceDate::test_index_route_with_since_renders` (`GET /dashboard/?since=2026-09-01`)
  fails the same way.
- **117.** `tests/test_annotation_routes.py::TestEvalRunRoute::test_second_concurrent_run_is_refused_409_and_never_starts`:
  with a first `POST /api/eval/run` held open inside a blocked `run_suite` stub, a second
  `POST /api/eval/run` returned
  ```
  E   assert 200 == 409
  E    +  where 200 = <WrapperTestResponse streamed [200 OK]>.status_code
  ```
  and its body streamed `event: start` … `event: done`, i.e. its own worker ran a second suite
  while the first was live. `blueprints/diagnostics.py:41-51` holds no run state at module
  level; each route's `cancel_event` is request-local.
- **118.** `tests/test_llm_call_error_capture.py::TestRedactErrorMessage::test_masks_quoted_key_and_basic_auth_forms`
  fails on all 5 cases. The redacted output still carries the secret, e.g.
  ```
  E   AssertionError: headers={'x-api-key': 'sk-live-abc123', 'a': 'b'}
  E   AssertionError: Authorization: *** dXNlcjpwYXNzd29yZA==
  ```
  (pattern at `analyzer.py:601`: `\b(x-api-key|authorization)\s*[:=]`, so a closing quote
  between key and colon defeats it; `(?:bearer\s+)?` lets `Basic` be the masked `\S+`.)
- **119.** `tests/ux/regression/test_20261003_run_lock_ownership.py::test_stale_release_does_not_free_a_live_run`:
  after `acquire()`, a second `acquire()`, then a token-less `release()`, page script reported
  ```
  E     {'second': False} != {'second': None}
  E     {'stillLocked': False} != {'stillLocked': True}
  ```
  — the stale release freed the live run's lock. `test_bootstrap_click_while_locked_issues_no_post`
  failed with `a click while another run is live started a second bootstrap`: with the lock held,
  a click on `#bsRun` (forced enabled) issued `POST /api/annotation/bootstrap`
  (`dashboard.html:2883-2884` ignores `acquire()`'s return).
- **120.** `test_declined_run_does_not_leave_its_button_pulsing`: with the lock held,
  `window.sartorEval.run({...}, null, evalRunBtn)` returned early and left
  ```
  E     {'pending': True} != {'pending': False}
  ```
  (`dashboard.html:2340` calls `setBtnPending` before the `acquire()` check at :2344).
- **121.** `tests/test_dashboard_routes.py::TestRunDetailRoute::test_non_object_line_in_log_is_not_a_500`:
  a log holding `["r1"]` and `"r1"` lines returned 500 with
  ```
  AttributeError: 'list' object has no attribute 'get'
  ```
  and `test_only_this_runs_lines_are_parsed` counted `assert 50 == 0` — all 50 other-run lines
  were `json.loads`-ed to answer one run (`dashboard/routes.py:1105`, `_read_jsonl(LLM_LOG)`).
  `TestReadJsonlSkipsNonObjects` showed `_read_jsonl` returns `[1, 2]`, `'str'`, `42`, `None`.

### Re-run on rebased tip (`main` 4f6f34a + instrument commit), 2026-10-06

Free RAM was 1.05 GB at the start of the run (`Win32_OperatingSystem.FreePhysicalMemory`).
- `python -m pytest tests/test_dashboard_routes.py tests/test_annotation_routes.py tests/test_llm_call_error_capture.py -p no:rerunfailures -q`
  gave `12 failed, 150 passed in 247.26s`. The 12 node ids are 8 test functions: 112 ×3, 121 ×3,
  117 ×1, and 118 ×1 parametrized 5 ways. **This differs from the "11 Python tests" in the
  acceptance bar below.**
  - `TestFilterCallsSinceDate::test_aware_floor_against_naive_and_aware_timestamps` is in that
    set but is not quoted above.
  - The source of the 11 is not verified. The bar now reads as "every failing node id here
    passes".
- `python -m pytest -m ux tests/ux/regression/test_20261003_run_lock_ownership.py -p no:rerunfailures -q`
  gave `3 failed in 122.24s`.
  - `test_declined_run_does_not_leave_its_button_pulsing` and
    `test_bootstrap_click_while_locked_issues_no_post` failed as quoted above.
  - **`test_stale_release_does_not_free_a_live_run` failed differently.** It raised
    `playwright._impl._errors.TimeoutError: Page.goto: Timeout 30000ms exceeded` navigating to
    `/_dashboard/`. It never reached its assertion. The cause is not verified (low free RAM is a
    candidate, not a finding).
  - Re-run alone (`...::test_stale_release_does_not_free_a_live_run`, same flags), it
    **reproduced the quoted assertion**: `{'second': False} != {'second': None}` and
    `{'stillLocked': False} != {'stillLocked': True}`. The result was `1 failed in 301.49s`.
    One UX test taking ~5 min is itself abnormal. The cause is not investigated: it is outside
    items 112/117–121, and the timing is noted only.

### After the fix (same tip + fix, 2026-10-06)

Both runs used `-p no:rerunfailures`, so no test was retried.
- **Python:** `python -m pytest tests/test_dashboard_routes.py tests/test_annotation_routes.py tests/test_llm_call_error_capture.py -p no:rerunfailures -q`
  gave `162 passed in 152.94s`. That covers all 12 previously failing node ids, the existing
  `TestRunCancelDisconnect` and `test_undrained_response_does_not_hold_the_slot`, with the new
  conftest drain active. Free RAM was 0.71 GB.
- **UX:** `python -m pytest -m ux` over `test_20261003_run_lock_ownership.py`,
  `test_20260709_diagnostics_run_lock.py`, `test_20260720_diagnostics_run_cancel.py` and
  `test_20260923_annotate_collate_run_lock.py` gave `9 passed in 114.37s` (`pytest_exit=0`,
  `--durations=0`). The slowest phase was the first test's setup, at 38.67s (browser start); no
  call took more than 7.65s.

---

## Falsified

- **The 120 item text cites "the C1a regression test's declined path".** No such test exists:
  `grep -rn "already in progress" tests/` has no hit before this branch. The declined path was
  untested, not tested-and-passing.

---

## Inferred

- None needed: every mechanism above is the line a failing test points at.
- **Not verified:** whether a real second *browser tab* reaches the server concurrently on the
  dev server. Flask's `app.run` defaults `threaded=True`, so it should, but this branch's
  evidence is the test client from two threads, not two tabs.

---

## Falsification

The tests named under `## Observed` are the experiment. Each failed on `main` as quoted. A fix
is accepted only when the same tests pass unchanged.

---

## The fix

- **112:** `_parse_date` returns aware UTC datetimes (naive input is read as UTC, which is what
  the telemetry writer emits), so floor and timestamp always compare.
- **117:** a process-wide single-flight slot in `blueprints/diagnostics.py`. All four console
  run routes take it after eager validation and answer 409 when it is held. The worker frees it
  in its `finally`, before it signals the stream, so the slot lives as long as the work; a
  response closed before its stream ever started frees it via `call_on_close`.
- **118:** the header pattern allows a quote around the key and the value, and treats
  `Bearer`/`Basic` as a scheme word kept before the masked credential.
  - **As built (2026-10-06), the scheme word is masked WITH the credential, not kept.**
    `tests/test_llm_call_error_capture.py:236-238` pins `"Authorization: ***"` for
    `Authorization=Bearer deadbeef123`, and keeping `Bearer` would break that pinned contract.
    Every old and new assertion holds unchanged (blast-radius dossier, row 19).
- **119:** `acquire()` returns a numeric owner token or `null`; `release(token)` is a no-op
  unless the token owns the lock. Every caller keeps its token and bails on `null`.
- **120:** `run()` acquires first, then sets its button pending.
- **121:** `_iter_jsonl` yields object lines only; `run_detail` passes the run id as a substring
  pre-filter so lines of other runs are never parsed.
  - **As built:** the pre-filter token is the JSON-quoted id (`json.dumps(run_id)`), not the
    bare id. A bare `"r1"` also matches `other1` and `other10`–`other19`, which
    `test_only_this_runs_lines_are_parsed` would catch.
- **117, as built:** a process-wide slot like this is a flake by construction for any test that
  returns while its worker is still unwinding (`TestRunCancelDisconnect`). The autouse
  `_drain_diagnostics_run_slot` in `tests/conftest.py` waits, with a bound, for the real worker
  after every test. It fails naming the leaking test, and never resets the slot.

---

## Acceptance bar

The 11 Python and 3 UX tests above pass, the full gate is green with no reruns, and the existing
run-lock UX tests (`test_20260709_diagnostics_run_lock.py`, `test_20260720_diagnostics_run_cancel.py`,
`test_20260923_annotate_collate_run_lock.py`) still pass.
