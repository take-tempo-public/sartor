#!/usr/bin/env bash
# PostToolUse hook on ExitPlanMode: stamps the approval marker so the
# PreToolUse hook allows Edit and Write for the current plan.
# Scoped per-project via CLAUDE_PROJECT_DIR: records the exact plan file this
# project's session was writing (tracked by check-plan-approved.sh's plans-dir
# exemption branch) rather than "the newest .md in the shared ~/.claude/plans
# dir" — so a concurrent session in a different project can never be mistaken
# for this project's approval.

PLANS_DIR="$HOME/.claude/plans"
PROJECT_KEY=$(echo -n "${CLAUDE_PROJECT_DIR:-unknown}" | tr -c 'A-Za-z0-9' '-')
MARKER="$PLANS_DIR/.approved-$PROJECT_KEY"
CURRENT="$PLANS_DIR/.current-$PROJECT_KEY"

if [ -f "$CURRENT" ]; then
  cp "$CURRENT" "$MARKER"
else
  : > "$MARKER"
fi
