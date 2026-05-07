#!/usr/bin/env bash
# PostToolUse hook on ExitPlanMode: stamps the approval marker so the
# PreToolUse hook allows Edit and Write for the current plan.

touch "$HOME/.claude/plans/.approved"
