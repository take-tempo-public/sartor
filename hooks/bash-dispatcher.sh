#!/usr/bin/env bash
# PreToolUse hook on Bash: runs the four Bash guards in one process
# (block-secrets, block-merge-to-main, ruff-changed, verify-binary-on-path)
# instead of four separate hook entries, aggregating every blocked guard's
# messages before exiting — the settings.json PreToolUse/Bash consolidation
# (feat/verify-dont-assume-guard), mirroring hooks/edit-write-dispatcher.sh's
# established pattern for Edit|Write.
#
# See scripts/enforcement/adapters/bash_dispatcher.py for the aggregation
# logic (no short-circuit).
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/bash_dispatcher.py"
