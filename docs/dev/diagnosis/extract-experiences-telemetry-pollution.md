# Diagnosis — `tests/test_extract_experiences.py` writes fake rows into the real telemetry log

> **Status:** root cause PROVEN (mechanism identical to, and already documented by,
> item 33's filing and `docs/dev/diagnosis/refinement-scope-check-telemetry.md`'s
> item 21 fix; this dossier re-confirms it live on this branch before building the fix).
> **Branch:** `fix/extract-experiences-telemetry-pollution`

---

## Symptom

Running the non-UX pytest suite appends synthetic rows to the developer's real
`logs/llm_calls.jsonl` — a file `/bench` and every `/_dashboard` view treat as ground
truth. Item 33 measured this as 71.1% (3132/4403) of the entire real log as of
2026-08-03.

---

## Observed

Fresh reproduction on this branch, before any fix:

- `logs/llm_calls.jsonl` had exactly 4405 lines before running any test this session
  (`wc -l logs/llm_calls.jsonl` → 4405; last two rows were the prior branch's real
  Tier-3 verification rows, `draft_surgical_refinement` / `recommend_experience_summary`,
  timestamped `2026-08-03T14:00:*`).
- Ran `python -m pytest tests/test_extract_experiences.py -q` in isolation: 32 passed.
- `logs/llm_calls.jsonl` grew to 4414 lines (+9) immediately after, with zero other
  test files run in between. The 9 new rows are byte-identical in shape:
  `{"call": "extract_experiences", "model": "claude-haiku-4-5-20251001",
  "input_tokens": 100, "output_tokens": 50, "latency_ms": 0, "stop_reason": "end_turn",
  "status": "ok", "username": "", "run_id": ""}`, timestamped
  `2026-08-03T19:18:30.{869403..930857}` (9 rows in a 61ms span — consistent with 9
  in-process fake-client calls, not real network round-trips).
- `tests/test_extract_experiences.py`'s `_mock_anthropic_client()` helper
  (`tests/test_extract_experiences.py:240-261`) builds a `MagicMock(spec=anthropic.Anthropic)`
  whose `final.usage.input_tokens = 100` / `output_tokens = 50` are hardcoded literals —
  an exact match to the 9 rows' shape. Read in full: no call site in this file
  monkeypatches `analyzer.LOG_PATH` or `analyzer._emit_call_log`, unlike every other
  fake-client test file in `tests/` (`test_refinement_scope.py`, `test_call_kind_telemetry.py`,
  `test_call_kind_route_telemetry.py`, `test_prompt_overrides.py`,
  `test_analyzer_model_selection.py`, `test_demo_mode.py` — confirmed by
  `grep -n "LOG_PATH\|_emit_call_log" tests/*.py`).
- Traced the call path: `onboarding/extract_experiences.py:29` imports
  `_parse_or_retry` from `analyzer`, which internally reaches
  `analyzer._call_llm_streaming` → `analyzer._emit_call_log(record)`
  (`analyzer.py:468-475`) — a bare module-level call, so it reads `analyzer.LOG_PATH`
  fresh from the module's `__dict__` at call time (confirmed by reading
  `_emit_call_log`'s body: `LOG_PATH.open("a", ...)`, no parameter, no closure capture).
  This is the same mechanism `test_call_kind_telemetry.py`'s own docstring documents
  ("`_emit_call_log` reads the module global at call time, so either [patching
  `_emit_call_log` or `LOG_PATH`] suffices").
- Removed the 9 reproduction rows from the real log by exact match
  (`call == "extract_experiences" and input_tokens == 100 and output_tokens == 50
  and latency_ms == 0 and timestamp.startswith("2026-08-03T19:18:30.")`) — confirmed
  back to 4405 lines after removal, same remediation shape used twice on the prior
  branch (`fix/never-logged-call-kinds`) for this identical bug class.
- Checked every other test file that touches `LOG_PATH` for a conflicting
  requirement: `tests/test_analyzer_model_selection.py` (3 tests) and
  `tests/test_demo_mode.py` (2 sites) each monkeypatch `analyzer.LOG_PATH` to a
  `tmp_path` file and then **read that file's contents back** to assert on
  `_emit_call_log`'s real write behavior — a repo-wide fixture that instead no-ops
  `_emit_call_log` itself (rather than redirecting `LOG_PATH`) would break these 3
  tests (the tmp file would never be written). This directly shaped the fix design
  below.

---

## Falsified

Nothing falsified — the mechanism item 33 already named (`_mock_anthropic_client`'s 9
call sites never redirecting telemetry) reproduced exactly as filed, on the first
attempt, with no rival explanation needed.

---

## Inferred

_(Nothing — the mechanism is directly observed above, not inferred.)_

---

## Falsification

Not applicable in the usual sense (this is a reproducible-on-demand bug, not an
intermittent one) — the reproduction above already ran on HEAD-of-branch (pre-fix)
and demonstrably failed (9 real rows appended). The acceptance bar below is the
post-fix falsification: re-run the identical command and confirm zero growth.

---

## The fix

Add one `autouse=True` fixture to `tests/conftest.py` that redirects
`analyzer.LOG_PATH` to a per-test `tmp_path` file **by default, for every test in the
suite** — not `_emit_call_log` itself, per the `test_analyzer_model_selection.py` /
`test_demo_mode.py` constraint observed above. Any test that already does its own
`monkeypatch.setattr(analyzer, "LOG_PATH", ...)` or
`monkeypatch.setattr(analyzer, "_emit_call_log", ...)` continues to work unchanged —
its own patch simply applies after the conftest default and wins (monkeypatch chains
and reverts in LIFO order; this is the same pattern already relied on throughout
`tests/`). `test_extract_experiences.py` itself needs no changes: today it does
neither, so it currently falls through to the real path by omission; after this fix
it inherits the safe default like every other test file, present and future, closing
the class of gap rather than this one file's instance of it (per item 33's own
proposal, and the fact this exact shape has now recurred three times —
`test_refinement_scope.py`'s first draft, this item, and item 34's UX-harness
sibling).

---

## Incident during this branch's own work (disclosed, not silently absorbed)

While verifying the fix actually catches the regression (a deliberate RED check:
temporarily disabling the new conftest fixture and re-running
`tests/test_extract_experiences.py` to confirm the new module-scoped guard fails —
it did, `4405 -> 4414`), the cleanup of that RED check's own 9 reproduction rows was
written without the timestamp scoping the first cleanup had used, matching on shape
alone (`call=extract_experiences, input_tokens=100, output_tokens=50, latency_ms=0`).
That shape is not unique to this session — it is the exact signature of the 3,132
historical rows item 33 had already measured as accumulated pollution from every
prior session. The deletion removed all 3,141 matching rows (3,132 historical + 9
from the RED check), collapsing `logs/llm_calls.jsonl` from 4,414 to 1,273 lines.

`logs/` is gitignored with no git history and no other backup — this was
**unrecoverable**. Disclosed to the user immediately as a mistake, not framed as an
intentional cleanup. The user's direction: leave the file as-is (every removed row
was confirmed test-pollution noise by item 33's own prior measurement, not real
telemetry) and record the risk for future sessions —
`[[reference-fake-client-tests-must-redirect-telemetry]]` (memory) now carries this
as a third confirmed instance, with explicit guidance that any future cleanup of
this file must scope on **timestamp AND shape together, never shape alone**, and
should sanity-check the row count about to be removed before writing back.

---

## Acceptance bar

- A new regression test in `tests/test_extract_experiences.py` (or a new small test
  file) that reads `logs/llm_calls.jsonl`'s real row count before and after running
  one of the existing fake-client tests via `pytest.main`/subprocess is unnecessarily
  heavy; instead the bar is: re-run the exact reproduction command,
  `python -m pytest tests/test_extract_experiences.py -q`, and confirm via
  `wc -l logs/llm_calls.jsonl` that the count is unchanged (still 4405) — this is the
  same falsification experiment as `## Observed`, just post-fix.
- `tests/test_analyzer_model_selection.py` and `tests/test_demo_mode.py` (the tests
  that need `_emit_call_log`'s real write behavior) must still pass unmodified.
- Full quality gate (`python -m scripts.gate`) green, with the non-UX pytest run
  itself not producing any further real-log growth (checked the same way).
