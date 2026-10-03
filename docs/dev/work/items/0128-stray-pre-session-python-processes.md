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

### 2026-10-02 — inventory (read-only, `chore/release-v1.1.0`)

`Get-CimInstance Win32_Process -Filter "Name like 'python%'"` found 13 stale processes, dated
2026-09-18 to 2026-10-01. Every one shows a 0 MB working set.
- 2× `security_reminder_hook.py`, the `security-guidance` plugin's hook.
- 11× one-line `python3 -c` stdin-JSON readers:
  - 9 print `tool_input.command`;
  - 1 prints `tool_input.file_path`;
  - 1 counts `is_wiki_relevant()` paths.

All of them read stdin, which fits a process blocked on a stdin that never reached EOF. **That
mechanism has not been verified:** parent liveness and pipe state weren't checked. Nothing was
killed.
