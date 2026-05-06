---
description: Aggregate logs/llm_calls.jsonl to summarize cache hit rate, latency, and rough token cost.
argument-hint: [--since YYYY-MM-DD] [--user USERNAME]
allowed-tools:
  - Bash
  - Read
---

Read the LLM telemetry log and print a summary table.

1. Run a Python one-liner that reads `logs/llm_calls.jsonl`, applying optional filters from `$ARGUMENTS`:
   - `--since YYYY-MM-DD` — UTC date floor
   - `--user USERNAME` — exact match on the `username` field
2. Aggregate by `(call, model, prompt_version)`:
   - count of calls
   - mean `latency_ms`
   - sum of `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
   - cache hit ratio = `sum(cache_read) / (sum(cache_read) + sum(cache_creation))` — undefined when both are zero
   - rough cost estimate using current Anthropic pricing (state the assumed rates in the output so the user can verify)
3. Print the table sorted by `count` descending.
4. After the table, surface any anomalies:
   - Cache hit ratio < 30% on `generate` calls (caching may not be working — likely the system block isn't structured correctly)
   - p95 `latency_ms` > 60_000 (calls timing out)
   - Any `status: "error"` rows
5. Do not modify the log file. Read-only operation.

If `logs/llm_calls.jsonl` doesn't exist, report that the LLM pipeline hasn't been run since instrumentation landed and exit.
