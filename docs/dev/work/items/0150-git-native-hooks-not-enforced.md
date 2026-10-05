```toml
schema = 1
id = 150
kind = "item"
title = "The git-native .githooks guards are opt-in, and off on the owner's own clone; the gate never checks"
status = "open"
decision_owner = "agent"
branches = ["fix/hook-guard-false-blocks"]
refs = [
  ".githooks/pre-merge-commit",
  ".githooks/pre-push",
  "CONTRIBUTING.md:120",
  "scripts/gate.py",
]
summary = "core.hooksPath is unset on the owner's clone, so pre-merge-commit/pre-push never run; nothing fails when they're off."
```

**Observed (2026-10-03).**
- `git config --get core.hooksPath` in the owner's main checkout prints nothing (unset), and so
  does the `fix/hook-guard-false-blocks` worktree.
- `.githooks/` holds `pre-commit`, `pre-merge-commit` and `pre-push`.
- `scripts/gate.py` has no `hooksPath` check; the only mention of turning them on is
  `CONTRIBUTING.md:120` (`git config core.hooksPath .githooks`).

**Why it matters:** these are the guard layer that can't be fooled by command text, because
git itself invokes them on a real merge or push (`block_merge_to_main.git_operation_check` /
`git_push_check`). With them off, item 149's under-block has no second line locally.

**Fix direction:** a gate step that fails when `core.hooksPath` is not `.githooks`, with a
message giving the one command to fix it. It is skipped in CI, where no local merge or push
happens, and CI says so in its log instead of passing silently.

## Updates

### 2026-10-03 — filed on `chore/agent-doc-drift`
