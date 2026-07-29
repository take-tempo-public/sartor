```toml
schema = 1
id = 4
kind = "item"
title = "In-app rendered citation viewer"
status = "deferred"
decision_owner = "user"
blocked_on = "no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants"
refs = ["docs/dev/RELEASE_CHECKLIST.md:1442-1456"]
summary = "Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet."
```

Migrated from `RELEASE_CHECKLIST.md`'s Carry-forward ledger. Known
trade-off of the current GitHub-link approach: a code citation on an
unpushed local sha can 404 until pushed.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, not new)
