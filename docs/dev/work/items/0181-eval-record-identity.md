```toml
schema = 1
id = 181
kind = "item"
title = "Eval redesign step 1: record identity and the prompt-version gate"
status = "open"
decision_owner = "agent"
epic = 180
branches = ["feat/eval-record-identity"]
refs = ["docs/dev/eval-redesign-design.md"]
summary = "Prompt content hashes + version gate, producer id, trace/span/case ids, parse outcome, judge cost in run totals."
```

Step 1 of the eval redesign build order: docs/dev/eval-redesign-design.md section 9, row 1. Scope lives there.
Enumerate the consumers of the call-log row and the eval record first (dashboard, `commands/bench.md`, `evals/tune.py`) and write the dossier.

## Updates

### 2026-10-20 -- filed during docs/eval-redesign-decisions
