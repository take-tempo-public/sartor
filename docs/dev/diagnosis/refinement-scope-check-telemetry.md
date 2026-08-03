# Diagnosis — `check_refinement_scope` produces zero telemetry rows

> **Status:** root cause PROVEN (static, by direct code read + empirical log check —
> not a runtime/flaky defect, so no reproduction campaign is needed).
> **Branch:** `fix/refinement-scope-check-telemetry`

---

## Symptom

Work item 21 (`docs/dev/work/items/0021-refinement-scope-check-untelemetered.md`):
`check_refinement_scope`'s cost, latency, and error rate are invisible to
`logs/llm_calls.jsonl`, `/bench`, and the `/_dashboard` cost/reliability views, unlike
every other LLM call in `analyzer.py`.

---

## Observed

- **O-1 — empirical, local telemetry log.** `logs/llm_calls.jsonl` (this machine) holds
  4393 records spanning 22 distinct `call` values (tallied 2026-08-02 via
  `json.loads` over every line and collecting `rec["call"]` into a set). The string
  `"check_refinement_scope"` is **not** among them — confirmed by
  `"check_refinement_scope" in kinds == False`. The app has been exercised
  extensively (4393 rows across `extract_experiences`, `generate`, `clarify`,
  `analyze`, `analyze_extraction`, `analyze_synthesis`, `avatar_answer`, `recommend`,
  `recommend_summary`, `draft_summary`, `iterate_clarify`, `generate_cover_letter`,
  `draft_gap_fill`, `recommend_skill`, and 6 more, per-kind counts recorded in this
  branch's planning transcript) — the absence is not an artifact of low usage.
- **O-2 — direct source read, `analyzer.py:2826-2871` (full function body read, not
  excerpted).** `check_refinement_scope` calls `client.messages.create(...)` directly
  at `analyzer.py:2856-2861`. It does not call `_call_llm`, `_call_llm_streaming`, or
  `_parse_or_retry` — the three functions that reach `_emit_call_log`
  (`analyzer.py:457-464`, invoked only from `_call_llm_streaming`'s `finally` at
  `:1235`). No other code path in `analyzer.py` writes to `LOG_PATH`
  (`analyzer.py:453-454`). Therefore this function structurally cannot produce a
  telemetry row, on any input, by any code path that exists today. This is the
  mechanism, not a hypothesis about it — the absence of any `_emit_call_log` call on
  this function's only path is directly visible in the 46-line function body.
- **O-3 — direct source read, cross-referenced, CONFIRMED by execution.**
  `tests/ux/stubs.py:387-428` (`install_llm_stubs`, the UX tier's LLM-stubbing entry
  point) patches `blueprints.generation._get_client` to `lambda: None` (`:406`) but
  does not patch `analyzer.check_refinement_scope` or
  `blueprints.generation.check_refinement_scope`. `blueprints/generation.py:1485-1486`
  (`validate_refinement` route) calls `client = _get_client()` then
  `check_refinement_scope(client, note)` unconditionally — so under
  `install_llm_stubs`, `client` is `None` and `check_refinement_scope` receives it.
  Executed the falsification experiment below directly (2026-08-02):
  `analyzer.check_refinement_scope(None, "test note")` logged
  `scope check failed, failing open: 'NoneType' object has no attribute 'messages'`
  and returned `{"valid": True}` — confirmed, not raised. Every UX flow exercising a
  refinement note under `install_llm_stubs` has been silently taking the fail-open
  path on every run, with zero signal it was ever exercised as anything other than
  "outage."

---

## Falsified

Nothing chased and killed on this branch — this is a first-pass, code-read-driven
diagnosis for a structural instrumentation gap, not a flaky/intermittent defect, so
there was no prior wrong theory to falsify. O-3 was stated as a hypothesis in advance
and survived execution (see `## Falsification` below — confirmed, not killed).

---

## Inferred

**Why O-3 matters for the fix (forward-looking — the fix itself hasn't landed yet):**
once `check_refinement_scope` is routed through
`_call_llm`/`_parse_or_retry` (this branch's actual fix, for the Symptom above), a
`None` client under `install_llm_stubs` will still raise inside `_call_llm_streaming`
before reaching the network, still be caught by the same outer
`except Exception` fail-open — but now `_call_llm_streaming`'s own `finally` block
(`analyzer.py:1231-1251`) will emit a `status="error"` telemetry row on
**every** UX run that exercises this path, appending to whatever `LOG_PATH` resolves
to at test time. In an unstubbed UX run (not redirecting `analyzer.LOG_PATH` to a
tmp path), that is the developer's real `logs/llm_calls.jsonl` — the same file this
whole fix exists to make trustworthy for cost/reliability aggregation. That is the
concrete reason the fix and the stub gap are coupled, not two independent chores.

---

## Falsification

**The experiment that settled O-3.** Run before writing any fix:

```python
import analyzer
result = analyzer.check_refinement_scope(None, "test note")
assert result == {"valid": True}
```

- **If it returns `{"valid": True}` without raising:** O-3 confirmed — the UX harness
  gap is real, `tests/ux/stubs.py` must gain a `check_refinement_scope` stub as part
  of this fix (plan step 5).
- **If it raises instead:** O-3 is dead — the current fail-open `except Exception` is
  narrower than it looks. Stop, do not add the `stubs.py` change from the plan, and
  re-diagnose the actual UX-harness behavior before proceeding to any fix.

**Ran 2026-08-02, result: returned `{"valid": True}`, logged
`scope check failed, failing open: 'NoneType' object has no attribute 'messages'`.
O-3 CONFIRMED.** `tests/ux/stubs.py` will gain a `check_refinement_scope` stub as
part of this fix (plan step 5), tracked in `## Observed` above.

---

## The fix

Landed on `fix/refinement-scope-check-telemetry`, matching the approved plan
(`~/.claude/plans/generic-seeking-feigenbaum.md`): threaded an optional `max_tokens`
kwarg through `_call_llm`/`_call_llm_streaming`/`_parse_or_retry` (default
`MAX_TOKENS`, byte-identical for every pre-existing call site); extracted the inline
`system=` literal into a named, registered `SCOPE_CHECK_SYSTEM_PROMPT`; added a
`RefinementScopeResponse` Pydantic model; rewrote `check_refinement_scope`'s body to
call `_parse_or_retry(..., call_kind="check_refinement_scope", model=HAIKU_MODEL,
max_tokens=128, ...)` in place of the direct `client.messages.create`. The outer
`except Exception` fail-open wrapper is untouched. Also stubbed
`check_refinement_scope` in `tests/ux/stubs.py:install_llm_stubs` (O-3's fix).

**A second defect was found and fixed during this same branch's own test-writing,
not filed separately:** the first version of `tests/test_refinement_scope.py` only
redirected `analyzer._emit_call_log` in the 3 tests that asserted on it directly;
the other 6 (including a test that calls `analyzer._parse_or_retry` twice on
purpose) drove the real `_call_llm_streaming` with a fake client but left the real
`_emit_call_log` — and therefore the real `logs/llm_calls.jsonl` — unprotected.
Caught by re-inspecting the live file's tail after the end-to-end verification run
below and noticing 10 unexplained rows with an unmistakably synthetic shape
(`input_tokens=10, output_tokens=5, latency_ms=0`, timestamped to this session's two
earlier test runs). Fixed by making the telemetry redirect an **autouse** fixture
(`_telemetry`) so no test in the file can omit it; verified by running the suite
before/after and confirming `wc -l logs/llm_calls.jsonl` is unchanged (4413 → 4413).
The 10 already-written polluting rows were removed from the real file by exact
`(timestamp, call)` match, keeping every other pre-existing row and the one
legitimate end-to-end row untouched.

---

## Acceptance bar

- A new test asserting a `check_refinement_scope` telemetry row is written **fails on
  HEAD** (this branch's parent commit) and **passes after the fix** — not a retried
  pass; the log must show a clean first-attempt PASS. **Met** — 8/9 new tests failed
  on HEAD (`assert 0 == 1` on the telemetry-row test), all 9 pass post-fix, zero
  reruns, confirmed via `python -m scripts.gate`.
- `logs/llm_calls.jsonl` gains a `check_refinement_scope` row on a real end-to-end run
  against `python app.py`, priced (non-zero `model` matching a `MODEL_PRICING` key),
  and visible in `/_dashboard`'s cost-by-call-kind and reliability tables without any
  aggregator code change (they are data-driven, per the exploration behind this
  branch's plan). **Met** — a real `POST /api/validate-refinement` against a live
  `python app.py` produced `{"call": "check_refinement_scope", "model":
  "claude-haiku-4-5-20251001", "status": "ok", "input_tokens": 195, "output_tokens":
  13, "latency_ms": 1308}`, and `check_refinement_scope` appears 4× in the rendered
  `/_dashboard` HTML with no code change to any aggregator.
- The fail-open contract is unchanged: an outage or unparseable response still
  returns `{"valid": True}` to the caller, now WITH a `status="error"`/parse-failure
  telemetry row instead of silently vanishing. **Met** — `test_outage_fails_open_...`
  and `test_unparseable_response_fails_open_after_retry` both assert this exact pair.
- `python -m scripts.gate` green, zero reruns. **Met** — ruff, ruff format, mypy,
  2188 non-UX + 137 UX tests (1 pre-existing xfailed/1 pre-existing xpassed,
  unrelated to this branch), `work_items check`, all green, zero reruns.
- No test in this branch's own new suite writes to the real `logs/llm_calls.jsonl`.
  **Met** — verified by line-count before/after (`wc -l` unchanged across a full
  `tests/test_refinement_scope.py` run) after fixing the autouse-fixture gap found
  above; the 10 rows written before that fix was in place were identified by exact
  `(timestamp, call)` match and removed from the real file.
