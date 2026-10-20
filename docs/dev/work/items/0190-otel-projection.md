```toml
schema = 1
id = 190
kind = "item"
title = "Eval redesign step 10: OpenTelemetry projection"
status = "blocked"
blocked_on = "step 9 (item 189) has not landed"
depends_on = [189]
decision_owner = "agent"
epic = 180
branches = ["feat/otel-projection"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Pure row-to-span projection and its mapping module, pinned to one semantic-conventions-genai commit; no dependency."
```

Step 10 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 10. Scope lives there.
Owner decision 4: option 1, no dependency. Re-read the primary pages and record the commit before writing the mapping (the names in the design doc are reported). Check which Anthropic id `api_request_id` holds.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions
