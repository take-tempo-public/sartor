#!/usr/bin/env bash
# PreToolUse hook: blocks Edit/Write unless an approval marker exists.
# Exempts writes to the plans directory (plan file must always be writable).
# Marker is created by ExitPlanMode; deleted after merge → next task starts blocked.
# Scoped per-project via CLAUDE_PROJECT_DIR (F-gov-02/F-gov-03): the marker and the
# "which plan file is this" pointer both live under a per-project key, so a
# concurrent session in a different project/worktree can never trip or satisfy
# this project's gate.

PLANS_DIR="$HOME/.claude/plans"
PROJECT_KEY=$(echo -n "${CLAUDE_PROJECT_DIR:-unknown}" | tr -c 'A-Za-z0-9' '-')
MARKER="$PLANS_DIR/.approved-$PROJECT_KEY"
CURRENT="$PLANS_DIR/.current-$PROJECT_KEY"

# Read stdin once
INPUT=$(cat)

# Exempt the plans directory — plan file must always be writable in plan mode
FILE_PATH=$(python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" <<< "$INPUT" 2>/dev/null || echo "")

# Normalize path separators (Windows uses backslashes) then check
NORM_PATH=$(echo "$FILE_PATH" | tr '\\' '/')
if echo "$NORM_PATH" | grep -qF ".claude/plans"; then
  # Track which plan file THIS project is actively writing, so
  # mark-plan-approved.sh can record exactly the right file at approval time
  # without ever scanning the whole shared ~/.claude/plans directory.
  case "$NORM_PATH" in
    *.md) echo "$NORM_PATH" > "$CURRENT" ;;
  esac
  exit 0
fi

# No marker → not approved for this project
if [ ! -f "$MARKER" ]; then
  echo "NO EDIT APPROVAL: No approved plan found for this project." >&2
  echo "Write a plan and call ExitPlanMode." >&2
  exit 2
fi

# Marker exists — check only the specific plan file it was approved for (never
# the newest *.md across the whole shared directory, which is what let a
# different project's plan file trip this project's gate).
APPROVED_PLAN=$(cat "$MARKER" 2>/dev/null)
if [ -n "$APPROVED_PLAN" ] && [ -f "$APPROVED_PLAN" ] && [ "$APPROVED_PLAN" -nt "$MARKER" ]; then
  echo "PLAN NOT APPROVED: '$(basename "$APPROVED_PLAN")' is newer than approval marker." >&2
  echo "Call ExitPlanMode and get user approval before editing files." >&2
  exit 2
fi

exit 0
