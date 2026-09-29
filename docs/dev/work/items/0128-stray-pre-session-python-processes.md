```toml
schema = 1
id = 128
kind = "item"
title = "Stray python3.13 processes from earlier sessions left running"
status = "open"
decision_owner = "user"
branches = ["feat/docs-ia-design"]
refs = ["AGENTS.md"]
summary = "D1 close-out saw several python3.13 processes started 2026-09-18..25 (~0 MB), not that session's own."
```

**Observed.** At D1 close-out, `Get-Process` showed several `python3.13` processes started
between 2026-09-18 and 2026-09-25, each with about 0 MB working set. They weren't that
session's, so they were left for the owner. Ledger item 20 is the precedent for orphaned
processes causing a later test failure.

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2), carried from the D1 handoff
