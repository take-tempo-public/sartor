```toml
schema = 1
id = 21
kind = "item"
title = "check_refinement_scope LLM call invisible to telemetry"
status = "open"
decision_owner = "agent"
refs = ["analyzer.py:2826", "analyzer.py:2856-2871"]
summary = "check_refinement_scope bypasses _call_llm - no call_kind, no telemetry row, cost invisible to logs/llm_calls.jsonl."
```

Found 2026-07-28 during the PX-39 (item 6) pipeline trace. Every other LLM
call in `analyzer.py` goes through `_call_llm` / `_call_llm_streaming`, which
is what writes the per-call telemetry record (`_emit_call_log`,
`analyzer.py:1235-1251`) that `logs/llm_calls.jsonl`, `/bench`, and the
`/_dashboard` cost views all read. `check_refinement_scope`
(`analyzer.py:2826`) is the one exception — it calls
`client.messages.create` directly (`analyzer.py:2856-2861`), so it has no
`call_kind`, produces no telemetry row, and its cost is invisible to every
tool that aggregates `logs/llm_calls.jsonl`. It also fails open on error
(`analyzer.py:2868-2871`), so a silent failure here wouldn't show up in
retry-rate or error-rate views either.

Mechanical fix, likely: route it through `_call_llm` with a `call_kind` like
every other call site, unless there's a reason (e.g. its scope-check role
wanting to stay outside the retry/cache machinery) that this was deliberate —
not established either way yet.

## Updates

### 2026-07-28 — filed during docs/pipeline-truth-and-era4-baseline
