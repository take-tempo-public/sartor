```toml
schema = 1
id = 7
kind = "item"
title = "PX-46 selective memory consolidation"
status = "deferred"
decision_owner = "user"
blocked_on = "owner sign-off on the keep/consolidate/delete list required first - judged irreversible if botched"
refs = ["RELEASE_ARC.md step 13", "docs/dev/reviews/2026-07-efficiency/prescriptions.md:53"]
summary = "Selective, not wholesale, memory consolidation - present the list, act only after explicit approval."
```

Prescription: fold the ≥3 unique-recipe memories into a durable `docs/dev/`
reference, delete only genuinely redundant completion logs, shrink the freed
`MEMORY.md` index lines. Never actioned — owner sign-off on the specific
keep/consolidate/delete list was never sought. Memory file count grows
session to session; re-verify the count fresh before acting.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, not new)
