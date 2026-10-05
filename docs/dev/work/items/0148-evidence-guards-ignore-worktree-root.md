```toml
schema = 1
id = 148
kind = "item"
title = "C-7/C-10 guards and restore-evidence read the dossier from CLAUDE_PROJECT_DIR, not the edited file's worktree"
status = "closed"
decision_owner = "agent"
branches = ["chore/agent-doc-drift", "fix/hook-guard-false-blocks"]
refs = [
  "scripts/enforcement/guards/require_evidence_before_fix.py:57",
  "scripts/enforcement/guards/require_consumer_enumeration.py:107",
  "scripts/enforcement/adapters/claude_context_hook.py:82",
  "scripts/enforcement/adapters/claude_hook.py:106",
]
resolution = "2026-10-05, fix/hook-guard-false-blocks: gitutil.repo_root resolves the checkout holding the edited file (or the payload cwd for the context hooks); CLAUDE_PROJECT_DIR is only the no-repo fallback. Used by require-evidence-before-fix, require-consumer-enumeration and claude_context_hook. A static test pins the only CLAUDE_PROJECT_DIR readers."
verified_by = [
  "tests/test_evidence_gate.py::TestRequireEvidenceBeforeFixGuard::test_reads_the_dossier_from_the_edited_files_worktree",
  "tests/test_evidence_gate.py::TestRequireEvidenceBeforeFixGuard::test_a_main_checkout_dossier_does_not_cover_a_worktree_edit",
  "tests/test_consumer_enumeration_gate.py::TestRequireConsumerEnumerationGuard::test_reads_the_dossier_from_the_edited_files_worktree",
  "tests/test_evidence_gate.py::TestRepoRootFollowsTheWorktree",
]
summary = "In a worktree, the guard reads the branch from the worktree but the dossier from the main checkout, and blocks."
```

**Observed (2026-10-03, session 3abb1df0).**
- Setup: the main checkout (the session's `CLAUDE_PROJECT_DIR`) on `chore/flake-shard-slim`;
  a sibling worktree (`git worktree add`) on `fix/console-run-lock-hardening`, holding
  `docs/dev/diagnosis/console-run-lock-hardening.md` with a filled `## Observed` section.
- An `Edit` to `<worktree>/dashboard/routes.py` was refused:
  ```
  BLOCKED (require-evidence-before-fix): on 'fix/console-run-lock-hardening', but
  docs/dev/diagnosis/console-run-lock-hardening.md does not exist.
  ```
- The mechanism is in the code, not inferred: `decide()` reads the branch with
  `git_branch(<edited file's directory>)` (`require_evidence_before_fix.py:141-144`), but builds the
  dossier path from `_repo_root_for()`, which returns `CLAUDE_PROJECT_DIR` whenever it is set
  (`:57-61`). The session's project dir is the main checkout, which has no such dossier.

**Same shape, not exercised this session:**
- `require_consumer_enumeration.py:107-110` has an identical `_repo_root_for`.
- `claude_context_hook.py:82-83` (the `restore-evidence` SessionStart hook) prefers
  `CLAUDE_PROJECT_DIR` over the payload's `cwd`, so a worktree session's evidence would not
  be replayed after a compaction. **I have not verified this one.**

**Why it matters:** charter W-1 sanctions parallel worktree sessions, and the owner's memory
says separate worktrees for concurrent agents. The guard fails in the safe direction here
(over-blocks). The opposite case is possible too, though not observed: a main checkout that
happens to hold a dossier for the same slug would let a worktree edit through on the main
checkout's evidence.

**Workaround used:** move the branch's work into the main checkout.

**Fix direction:** resolve the repo root from the edited file first (walk up to the
directory holding `.git`, file or folder), and fall back to `CLAUDE_PROJECT_DIR` only when
the file is outside any repo. For the context hook, prefer the payload `cwd`'s repo.

## Updates

### 2026-10-03 — filed on `chore/agent-doc-drift`

### 2026-10-05 — closed on `fix/hook-guard-false-blocks`

gitutil.repo_root resolves the checkout holding the edited file (or the payload cwd for the context hooks); CLAUDE_PROJECT_DIR is only the no-repo fallback. Used by require-evidence-before-fix, require-consumer-enumeration and claude_context_hook. A static test pins the only CLAUDE_PROJECT_DIR readers.
