```toml
schema = 1
id = 21
kind = "item"
title = "check_refinement_scope LLM call invisible to telemetry"
status = "closed"
resolution = "Fixed on fix/refinement-scope-check-telemetry. Confirmed the mechanical fix this item itself proposed: check_refinement_scope now routes through _parse_or_retry (new RefinementScopeResponse model, named+registered SCOPE_CHECK_SYSTEM_PROMPT) instead of calling client.messages.create directly, so it gets a call_kind, a telemetry row, and an error row on outage, like every other analyzer.py LLM call. Threaded an optional max_tokens kwarg through _call_llm/_call_llm_streaming/_parse_or_retry (default MAX_TOKENS, byte-identical for all pre-existing call sites) to preserve this call's original 128-token cap. Fail-open contract unchanged -- an outage or unparseable response still returns {valid: true}. Diagnosis also surfaced and fixed a related gap: tests/ux/stubs.py's install_llm_stubs never stubbed this call, so every UX refinement flow was silently exercising only the fail-open path (confirmed by execution, not just code-reading -- analyzer.check_refinement_scope(None, note) returns {valid: true} via the outer except). Full evidence chain: docs/dev/diagnosis/refinement-scope-check-telemetry.md."
decision_owner = "agent"
refs = [
  "analyzer.py:_call_llm",
  "analyzer.py:_parse_or_retry",
  "analyzer.py:check_refinement_scope",
  "analyzer.py:RefinementScopeResponse",
  "tests/ux/stubs.py:fake_check_refinement_scope",
  "docs/dev/diagnosis/refinement-scope-check-telemetry.md",
]
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

### 2026-08-02 — fixed and closed (`fix/refinement-scope-check-telemetry`)

Confirmed this item's own filed mechanism (`client.messages.create` bypassing
`_call_llm`) and its suggested fix (route through `_call_llm` with a `call_kind`)
were both correct. Routed the call through `_parse_or_retry`, added a threaded
`max_tokens` kwarg on the shared funnel so the call keeps its original 128-token
cap, and closed a related silent gap in the UX test harness found during
diagnosis. Full evidence chain, falsification experiment, and acceptance bar:
`docs/dev/diagnosis/refinement-scope-check-telemetry.md`.
