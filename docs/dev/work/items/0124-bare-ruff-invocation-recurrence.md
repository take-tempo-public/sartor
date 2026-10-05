```toml
schema = 1
id = 124
kind = "item"
title = "Recurrence: agents invoke bare `ruff` (not on PATH here) and get hook-blocked mid-run"
status = "closed"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery", "fix/hook-guard-false-blocks"]
refs = [
  "scripts/enforcement/guards/verify_binary_on_path.py",
  "AGENTS.md",
]
resolution = "2026-10-05, fix/hook-guard-false-blocks: when a missing name is importable as a module by the interpreter running the hook (importlib.util.find_spec, top-level names only), the block adds 'run `python -m <name>` instead'. A name with no importable module gets no hint."
verified_by = [
  "tests/test_enforcement_core.py::TestVerifyBinaryOnPathUnit::test_missing_python_tool_message_names_python_dash_m",
  "tests/test_enforcement_core.py::TestVerifyBinaryOnPathUnit::test_missing_non_module_tool_gets_no_python_hint",
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

### 2026-10-05 — closed on `fix/hook-guard-false-blocks`

when a missing name is importable as a module by the interpreter running the hook (importlib.util.find_spec, top-level names only), the block adds 'run `python -m <name>` instead'. A name with no importable module gets no hint.
