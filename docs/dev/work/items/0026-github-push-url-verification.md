```toml
schema = 1
id = 26
kind = "item"
title = "Push to GitHub + verify public URLs resolve"
status = "closed"
decision_owner = "agent"
resolution = "Found already satisfied in practice, never reconciled in the old doc. git remote -v confirms origin = https://github.com/take-tempo-public/sartor.git (both fetch and push), and PRs are actively merging through it (e.g. PR #75, #76). pyproject.toml:139-142 Homepage/Repository/Issues/Changelog all point at the same real, public take-tempo-public/sartor repo. The v1.0.1-era checklist row (RELEASE_CHECKLIST.md:3593-3602) was simply never checked off after the push actually happened."
refs = [
  "docs/dev/RELEASE_CHECKLIST.md:3593-3602",
  "pyproject.toml:139-142",
]
summary = "Old v1.0.1 checklist row never checked off; verified 2026-07-29 the push + URLs already happened in reality."
```

Found during the 2026-07-29 old-system-vs-board migration-gap sweep
(`fix/bootstrap-annotation-overwrite`). `RELEASE_CHECKLIST.md:3593-3602`
(pre-ledger, v1.0.1-era "Must do before tag" section) has an unchecked box:
"Push to GitHub + verify the `https://github.com/take-tempo-public/sartor`
URL resolves" — planned for the v1.1.0 cut, with the repo staying
local-only ("no `origin` remote configured") until then.

Verified 2026-07-29: that's stale. `git remote -v` shows `origin` already
set to `https://github.com/take-tempo-public/sartor.git`, and this session's
own git log shows PRs #75/#76 merged through it. `pyproject.toml`'s
Homepage/Repository/Issues/Changelog URLs all resolve to the same repo.
Filed closed rather than open, since the substance is already done — only
the doc reconciliation was missing.

## Updates

### 2026-07-29 — filed closed during fix/bootstrap-annotation-overwrite, migration-gap sweep
