```toml
schema = 1
id = 149
kind = "item"
title = "block-merge-to-main lets `git -C <dir> merge main` and `git -c k=v merge main` through"
status = "open"
decision_owner = "agent"
branches = ["fix/hook-guard-false-blocks"]
refs = [
  "scripts/enforcement/guards/block_merge_to_main.py:90",
  "docs/dev/diagnosis/hook-guard-false-blocks.md",
]
summary = "The merge regex needs `merge` right after `git`, so any git global option hides a real merge to main."
```

**Observed (2026-10-03, `fix/hook-guard-false-blocks` worktree at `main` d270506).**
`tests/test_enforcement_core.py::TestBlockMergeToMainUnit::test_real_merges_still_block` fails on
2 of its 14 cases: `git -C . merge main` and `git -c core.editor=true merge main` are allowed.
`_MERGE_MAIN_RE = \bgit\s+merge(?!-)\b.*\b(?:main|master)\b` (`block_merge_to_main.py:90`)
requires `merge` to follow `git` directly; `_MERGE_RE` and `_PUSH_MAIN_RE` have the same shape.

**Why it's its own item:** item 136 is the opposite direction (over-blocking on merge *text*).
This one is an under-block, which is the unsafe direction.

**Fix (on `fix/hook-guard-false-blocks`, with 136):** parse each top-level segment's git
invocation past global options to its subcommand. Anything not parsed with certainty, plus
interpreters (`bash -c`, `eval`, `xargs`) and heredoc bodies, still gets the raw-text check,
widened to allow global options.

**Other layers, not this item:**
- The git-native `pre-merge-commit`/`pre-push` hooks see the real operation, but they are
  opt-in and off on the owner's clone (item 150).
- `enforce_admins` on `main` is the remote backstop (item 3, owner toggle).

## Updates

### 2026-10-03 — filed on `chore/agent-doc-drift`
