```toml
schema = 1
id = 123
kind = "item"
title = "verify-binary-on-path blocks shell brace groups: \"'{', '}' not found on PATH\""
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "scripts/enforcement/guards/verify_binary_on_path.py",
  "tests/test_enforcement_core.py",
]
summary = "A `{ cmd; cmd; } | head` brace group is parsed as binaries named { and }; blocked an epic refuter."
```

**Observed.** Epic refuter R2 was blocked mid-review by `verify-binary-on-path` (via
`hooks/bash-dispatcher.sh`) with `'{', '}' not found on PATH`, so its skip/xfail sweep
was not done. Reproduced at epic close against the guard's pure `decide()`:

```
decide('{ grep -n foo a.txt; grep -n bar b.txt; } | head')
-> GuardResult(blocked=True, messages=("BLOCKED (verify-binary-on-path): '{', '}' not found on PATH.", ...))
```

The guard's stated contract is to fail open on anything it cannot parse with certainty;
`{` and `}` are reserved words, not binaries.

**Suggested shape:** add `{` and `}` to `_BUILTINS_AND_KEYWORDS` (or fail open on a
segment starting with a reserved word), with a `decide()` test for the command above.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)
