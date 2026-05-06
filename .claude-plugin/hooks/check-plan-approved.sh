#!/usr/bin/env bash
# PreToolUse hook: blocks Edit/Write unless an approval marker exists.
# Exempts writes to the plans directory (plan file must always be writable).
# Marker is created by ExitPlanMode; deleted after merge → next task starts blocked.

PLANS_DIR="$HOME/.claude/plans"
MARKER="$PLANS_DIR/.approved"

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
  exit 0
fi

# No marker → not approved for this session
if [ ! -f "$MARKER" ]; then
  echo "NO EDIT APPROVAL: No approved plan found." >&2
  echo "Write a plan and call ExitPlanMode, or for simple tasks run:" >&2
  echo "  New-Item -Force -ItemType File \"\$env:USERPROFILE\\.claude\\plans\\.approved\"" >&2
  exit 2
fi

# Marker exists — check no plan file is newer (unapproved update)
NEWEST_PLAN=$(ls -t "$PLANS_DIR"/*.md 2>/dev/null | head -1)
if [ -n "$NEWEST_PLAN" ] && [ "$NEWEST_PLAN" -nt "$MARKER" ]; then
  echo "PLAN NOT APPROVED: '$(basename "$NEWEST_PLAN")' is newer than approval marker." >&2
  echo "Call ExitPlanMode and get user approval before editing files." >&2
  exit 2
fi

exit 0
