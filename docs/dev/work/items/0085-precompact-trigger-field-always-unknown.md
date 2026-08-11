```toml
schema = 1
id = 85
kind = "item"
title = "PreCompact payload's trigger field reads 'unknown' in 100% of historical ledger rows despite correct code handling"
status = "watching"
decision_owner = "agent"
refs = [
  "scripts/enforcement/adapters/claude_context_hook.py:213",
  "tests/test_c12_disclosure_gate.py:156-168",
]
summary = "trigger is 'unknown' in all 52 ledger rows; the code round-trips it correctly when present -- the payload may lack it."
```

**The observation.** Every `compacted` receipt ever written to
`docs/dev/ledger/*.jsonl` (52 rows, all history, checked this session) carries
`"trigger": "unknown"`. This looked, at first read, like the same class of
bug as D1 (the `session` field's missing environment fallback, fixed this
session in `claude_context_hook.py`) — but it is not the same bug, and was
**not** fixed alongside D1.

**Why this is a distinct, unverified finding rather than a guessed fix.**
`record_compaction()`'s handling of `trigger` is already correct and already
tested: `tests/test_c12_disclosure_gate.py:156-168` constructs a literal
payload `{"session_id": "sess-1", "cwd": ..., "trigger": "auto"}`, calls
`record_compaction()`, and asserts `record["trigger"] == "auto"` — which
passes. The code round-trips whatever value it's given correctly. Unlike
`session_id`, there is no adjacent function with a working environment-variable
fallback to copy (`_ledger_shard()` falls back to `CLAUDE_CODE_SESSION_ID`;
there is no known equivalent env var for `trigger`).

**The honest conclusion, stated rather than guessed past (C-12):** if the
code's own handling is correct and every real row is still "unknown," the
defect — if real — is upstream of this file: either real PreCompact
invocations in this harness never carry a `trigger` key in their payload at
all, or it arrives under a different name than the one `.claude/settings.json`'s
`auto|manual` matcher configuration implies. Verifying which requires
inspecting a live PreCompact payload's actual stdin content, not reasoning
from the settings.json matcher string or guessing a fallback with nothing
established to fall back to.

**No mechanism authored here.** `decision_owner = "agent"` — this is an
engineering investigation (does the payload carry the field or not, and
under what name), not a product or governance call.

## Updates

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed alongside the D1 fix (`session` field) in the same file, after
confirming this is a distinct, not-yet-diagnosed finding rather than the
same bug.
