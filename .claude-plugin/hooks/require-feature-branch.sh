#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: block code changes while on the default
# branch (main/master). The deterministic enforcement point for "create a
# feature branch before executing a plan" — there is no ExitPlanMode block
# event, so the first Edit/Write after plan→execute is where we gate (same
# philosophy as check-plan-approved.sh).
#
# Exemptions:
#   - the plans dir (~/.claude/plans) — plan files must stay writable
#   - not a git repo / detached HEAD — never wedge the user on edge cases
#   - env CLAUDE_ALLOW_MAIN_EDITS=1 — explicit opt-in (mirrors the
#     CLAUDE_CONFIRM_MERGE=1 escape hatch in block-merge-to-main.sh)

INPUT=$(cat)

# Exempt the plans directory (same parse + normalize as check-plan-approved.sh)
FILE_PATH=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" <<< "$INPUT" 2>/dev/null || echo "")
NORM_PATH=$(echo "$FILE_PATH" | tr '\\' '/')
if echo "$NORM_PATH" | grep -qF ".claude/plans"; then
  exit 0
fi

# Explicit opt-in escape hatch
if [ "${CLAUDE_ALLOW_MAIN_EDITS:-}" = "1" ]; then
  exit 0
fi

# Current branch; pass on any git edge case
BR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -z "$BR" ] || [ "$BR" = "HEAD" ]; then
  exit 0
fi

if [ "$BR" = "main" ] || [ "$BR" = "master" ]; then
  echo "BLOCKED (require-feature-branch): on '$BR'." >&2
  echo "Create a feature branch before code changes:" >&2
  echo "  git checkout -b <type>/<short-desc>   (e.g. feat/foo, fix/bar)" >&2
  echo "Escape hatch (intentional main edit): export CLAUDE_ALLOW_MAIN_EDITS=1" >&2
  exit 2
fi

exit 0
