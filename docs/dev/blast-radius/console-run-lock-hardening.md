# Blast radius — console-run-lock-hardening

> **Branch:** `fix/console-run-lock-hardening`
> **Status:** enumeration complete (2026-10-06, before the first production edit)

None of the files below is on the gated list in `scripts/enforcement/blast_radius.py`, and
`analyzer.py` is `ACKNOWLEDGED_NOT_GATED`. This dossier exists because three of the six fixes
change a contract that several sites consume, and C-10 binds those regardless of the guard.

---

## Surface

- `dashboard/templates/dashboard.html`: `window.sartorRunLock` (`acquireRunLock` /
  `releaseRunLock`). `acquire()` changes from returning a boolean to returning a numeric token
  or `null`. `release()` changes from taking nothing to `release(token)`, which is a no-op
  unless that token owns the lock (item 119). `window.sartorEval.run` changes so it acquires
  before `setBtnPending` (item 120).
- `blueprints/diagnostics.py`: the four SSE run routes gain a process-wide single-flight slot
  and a new **409** response (item 117).
- `dashboard/routes.py`:
  - `_read_jsonl` becomes "object lines only", and a new `_iter_jsonl(path, contains=...)`
    generator backs it (item 121);
  - `_parse_date` returns aware UTC (item 112).
- `analyzer.py`: `_HEADER_VALUE_PATTERN` and its substitution in `_redact_error_message`
  (item 118).

---

## Enumeration

Grep over the whole tree (Grep tool, `*.{py,html,js}`), run on `fix/console-run-lock-hardening`
@ 496cc9f:

- `sartorRunLock\.(acquire|release)|_read_jsonl|_iter_jsonl|_parse_date\b|_HEADER_VALUE_PATTERN|_redact_error_message`:
  - `dashboard.html`: 4 acquire and 10 release call sites, plus 1 comment.
  - `dashboard/routes.py`: 3 `_read_jsonl` callers and 2 `_parse_date` callers.
  - `analyzer.py`: 1 pattern use and 3 `_redact_error_message` callers.
  - `tests/`: the new UX test (token-passing) and the redaction and `_read_jsonl` unit tests.
  - **0 hits in `static/`**: the console never loads `app.js`.
- `sartorRunLock` in `tests/`: 2 docstring mentions (`test_20260709…`, `test_20260720…`).
  **No existing test calls `acquire()` or `release()` directly**, so the signature change
  breaks no test.
- Run URLs in `tests/` (`/api/eval/run|/api/tune/run|/api/annotation/bootstrap|/score`):
  - `test_annotation_routes.py`: 42 occurrences.
  - The UX tests: every run POST is intercepted with `page.route(...)` and fulfilled in the
    browser, so **none reaches the server's slot**. `test_20260923_dashboard_polish_ux.py:256`
    continues only non-POST requests.
  - `test_eval_runner.py`: comments only.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `dashboard/templates/dashboard.html:2194-2221` (lock IIFE) | update | Token + owner-checked release (119). |
| 2 | `dashboard/templates/dashboard.html:2339-2372` (`sartorEval.run`, acquire :2344, releases :2353/:2354/:2364) | update | Acquire before `setBtnPending` (120). Keep the token; release it at all 3 sites. |
| 3 | `dashboard/templates/dashboard.html:2479-2507` (tune click, acquire :2480, releases :2489/:2490/:2505) | update | Bail on a `null` token before pending/POST; release with the token. |
| 4 | `dashboard/templates/dashboard.html:2883-2924` (`runBootstrap`, acquire :2884, releases :2899/:2923) | update | The same as 3. Pinned by `test_bootstrap_click_while_locked_issues_no_post`. |
| 5 | `dashboard/templates/dashboard.html:2956-2991` (`scoreGrounding`, acquire :2957, releases :2967/:2990) | update | The same as 3. |
| 6 | `dashboard/templates/dashboard.html` `clearBtnPending` / `renderCollateResult` (`isLocked`, `governs`) | no change | They read lock state only; `isLocked()` keeps its meaning. |
| 7 | `blueprints/diagnostics.py:476` `annotation_score_grounding` | update | Take the slot after validation; 409 when held. The worker `finally` frees it before the sentinel. |
| 8 | `blueprints/diagnostics.py:746` `annotation_bootstrap_stream` | update | The same as 7. |
| 9 | `blueprints/diagnostics.py:990` `eval_run_stream` | update | The same as 7. Pinned by `test_second_concurrent_run_is_refused_409_and_never_starts`. |
| 10 | `blueprints/diagnostics.py:1160` `tune_run_stream` | update | The same as 7. The worker spans the baseline and candidate passes, so the slot covers both. |
| 11 | `blueprints/diagnostics.py:373` `annotation_collate` | no change | Not one of the four run routes: it is synchronous JSON, not a paid SSE run. The client lock still governs its buttons (`LOCK_BTN_IDS`). |
| 12 | The client 409 path: `sartorEval.stream` `!resp.ok` → `onEvent('error', …)` (`dashboard.html:2265-2268`) | no change | Every run caller's `error` branch already clears pending and releases its own lock. A 409 shows as `Error: A diagnostics run is already in progress.` |
| 13 | `tests/test_annotation_routes.py::TestRunCancelDisconnect` (4 tests, :1513-1668) | update the shared fixture, **not** these tests | Each test returns while its worker is still unwinding. With a process-wide slot, the next test could race that worker's `finally` and get a 409: a **new flake by construction**. Add an autouse teardown in `tests/conftest.py` that waits, with a bound, for the slot to be free and **fails loudly** if it stays held. It drains real work and never resets the slot. |
| 14 | `dashboard/routes.py:57` `_read_jsonl` | update | Becomes `list(_iter_jsonl(path))`; non-object lines are dropped. |
| 15 | `dashboard/routes.py:108` (`_read_eval_results`) | no change | It gains the dict-only guarantee for free, since `_normalize_eval_record` does `dict(r)`. |
| 16 | `dashboard/routes.py:1014` (`index`) | no change | Dict-only for free. It still needs every line (summaries, filter dropdowns). |
| 17 | `dashboard/routes.py:1105` (`run_detail`) | update | `_iter_jsonl(LLM_LOG, contains=run_id)`. The prefilter token is `json.dumps(run_id)` (with quotes), because a bare `"r1" in line` also matches `other1`/`other10`… The writer is `analyzer.py:577` `json.dumps(record)` (`ensure_ascii=True`). The `ensure_ascii=False` form is accepted too. The exact `run_id ==` filter still runs after parsing. |
| 18 | `dashboard/routes.py:112` `_parse_date`, callers :127, :131 | update | Aware UTC out (naive input read as UTC). Both callers compare its outputs only. |
| 19 | `analyzer.py:601/619` `_HEADER_VALUE_PATTERN` | update | Optional quote after the key and before the value; `Bearer`/`Basic` consumed with the credential. **Deviation from the dossier's "scheme kept before the mask":** `tests/test_llm_call_error_capture.py:236-238` pins `"Authorization: ***"` for `Authorization=Bearer …`, so the scheme is masked with the credential. Every old and new assertion holds unchanged. |
| 20 | `analyzer.py:1428/1431/1436` (`_redact_error_message` callers) | no change | Signature and return type are unchanged. |
| 21 | `dashboard/routes.py:1100` docstring, `dashboard.html:2066` comment | no change | They describe redaction generically and stay true. |

---

## Deferred

- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html:2371-2372`).
  Only the declined path returns `{abort}`. It is out of items 112/117–121, and no caller reads
  the return. Noted, not filed.

---

## Verification

- The 119/120 UX tests drive every changed client site: `sartorEval.run`, the bootstrap
  click, and a token-less release.
- The existing run-lock UX tests (`test_20260709…`, `test_20260720…`, `test_20260923…`)
  exercise the normal acquire→release path at the eval, bootstrap and score sites. A missed
  site that kept a token-less `release()` would leave the lock held, and those tests'
  re-enable assertions would fail.
- `TestRunCancelDisconnect` together with the conftest drain catches a route whose worker
  never frees the slot. The test right after it would 409, and the drain fails first, with
  the test named.
- `test_only_this_runs_lines_are_parsed` pins the prefilter token choice.
