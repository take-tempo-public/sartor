#!/usr/bin/env bash
# PreToolUse hook on Bash: block `git merge` and `git push origin` targeting
# main/master unless the command itself opts in with CLAUDE_CONFIRM_MERGE=1
# as an env-var prefix. Encodes the project's "always confirm before merge"
# rule deterministically.
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation
# (scripts/enforcement/guards/block_merge_to_main.py). That module also fixes
# the two defects filed against this hook (RELEASE_CHECKLIST.md
# "Portable-enforcement-core migration" ledger row, Train-1 note,
# 2026-07-07): the `merge-base`/`merge-tree` false positive, and resolving
# HEAD against the invocation's own cwd (from the PreToolUse `cwd` field)
# instead of the hook process's ambient cwd. See that module's docstring for
# the full write-up, and tests/test_enforcement_core.py for the regression
# cases. The same escape hatch (CLAUDE_CONFIRM_MERGE=1) and message text are
# preserved byte-for-byte for the cases this hook already caught correctly.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" block-merge-to-main
