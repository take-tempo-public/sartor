```toml
schema = 1
id = 124
kind = "item"
title = "Recurrence: agents invoke bare `ruff` (not on PATH here) and get hook-blocked mid-run"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "scripts/enforcement/guards/verify_binary_on_path.py",
  "AGENTS.md",
]
summary = "Pipeline run wf_fd312963-54d's implementer stopped on a bare-ruff block; the guard should steer to python -m."
```

**Observed.** C3's pipeline run `wf_fd312963-54d` stopped after the implementer on a
`verify-binary-on-path` hook block for a bare `ruff` command (commit `dbbd1b0`'s message),
forcing a manual dispatch of the remaining stages. Reproduced at epic close:

```
decide('ruff check .')             -> blocked: "'ruff' not found on PATH."
decide('python -m ruff check .')   -> not blocked
```

This is a recurrence (earlier sessions hit the same missing-binary case, which is why the
guard exists), so charter C-11 asks for a mechanism, not a note. The guard already fails
closed; what it lacks is steering, so each agent rediscovers the workaround.

**Suggested shape:** when the blocked name is a Python tool importable as a module
(`ruff`, `mypy`, `pytest`), the block message names the exact replacement
(`python -m ruff …`). A `decide()` test pins the suggestion. Optionally, the pipeline's
implementer prompt names `python -m` for these tools.

## Updates

### 2026-09-26 — filed at Epic C close (epic-close fixer, `feat/dashboard-copy-discovery`, from the three-refuter epic review)
