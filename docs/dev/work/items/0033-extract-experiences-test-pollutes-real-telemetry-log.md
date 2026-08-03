```toml
schema = 1
id = 33
kind = "item"
title = "tests/test_extract_experiences.py writes fake rows into the real logs/llm_calls.jsonl"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/test_extract_experiences.py",
  "tests/test_refinement_scope.py",
  "docs/dev/diagnosis/refinement-scope-check-telemetry.md",
]
summary = "9 tests drive extract_experiences without redirecting LOG_PATH - appends fake rows to the real telemetry log."
```

Found 2026-08-02 on `fix/refinement-scope-check-telemetry` while diagnosing and
fixing the identical shape in this branch's own new
`tests/test_refinement_scope.py` (caught via the branch's own end-to-end
verification step: 9 unexplained rows with a synthetic shape —
`input_tokens=100, output_tokens=50, latency_ms≈0` — appeared in
`logs/llm_calls.jsonl` after a full `python -m scripts.gate` run, timestamped
to `pytest -m "not ux"`). Traced to `tests/test_extract_experiences.py`'s
`_mock_anthropic_client(response_text)` helper (9 call sites): it builds a
fake `client.messages.stream(...)` and drives the real
`onboarding.extract_experiences.extract_experiences`, which reaches the real
`analyzer._emit_call_log` — the file never redirects `analyzer.LOG_PATH` or
monkeypatches `_emit_call_log`, so every one of those 9 tests appends a real
row to whatever `logs/llm_calls.jsonl` the test process resolves. In a normal
dev checkout (not CI, no `LOG_PATH` override), that is the developer's live
telemetry file — the exact file `/bench` and every `/_dashboard` view treat
as ground truth.

Data-only cleanup was done in-session (removed the 9 rows this branch's own
gate run produced, by exact timestamp match, from the real log) — but the
underlying test file itself is untouched. Left `watching`, not `open`,
because: (1) it is pre-existing and unrelated to item 21's own scope — folding
it in would have violated this branch's own scope discipline; (2) impact is
low-severity dev-experience noise (skews per-kind counts/costs by a small,
easily-identifiable synthetic shape — `input_tokens=100, output_tokens=50`
constant across all 9 calls — not a correctness or security issue); (3) the
fix is mechanical and identical in shape to what this branch just did for
`tests/test_refinement_scope.py` (add an autouse fixture redirecting
`_emit_call_log`, or `monkeypatch.setattr(analyzer, "LOG_PATH", tmp_path)`)
and can be picked up cheaply whenever `test_extract_experiences.py` is next
opened for an unrelated reason.

## Updates

### 2026-08-02 — filed during fix/refinement-scope-check-telemetry
