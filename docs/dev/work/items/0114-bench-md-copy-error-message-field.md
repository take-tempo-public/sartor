```toml
schema = 1
id = 114
kind = "item"
title = "commands/bench.md doesn't explicitly call out the new error_message/error_type fields"
status = "deferred"
blocked_on = "low value until logs/llm_calls.jsonl accumulates real status=\"error\" rows with the new fields; revisit once there is real data to summarize"
decision_owner = "agent"
branches = ["feat/llm-call-error-capture"]
refs = ["docs/dev/blast-radius/llm-call-error-capture.md", "commands/bench.md:11-27", "analyzer.py:1427-1448"]
summary = "bench.md already summarizes error rows generically; naming error_message/error_type explicitly is a nice-to-have."
```

C1c (`feat/llm-call-error-capture`) added `error_type`/`error_message` to
`logs/llm_calls.jsonl` rows where `status == "error"`. `commands/bench.md:11-27` already
instructs summarizing "Any `status: \"error\"` rows" generically, so it will surface the
new fields once they're populated without any edit — this item is purely about tightening
the slash command's instructions to explicitly ask for `error_message`/`error_type` by
name, which is a nice-to-have and not required for C1c's scope
(`docs/dev/blast-radius/llm-call-error-capture.md` row 14 and "Deferred" section).

Filed per the C1c closer's obligation enumeration (`docs/dev/blast-radius/llm-call-error-capture.md`,
row 14 + "## Deferred" — both say "filed as a work item rather than folded in here").

## Updates

- 2026-09-24: filed by the C1c closer.
