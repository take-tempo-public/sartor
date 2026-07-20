#!/usr/bin/env bash
# PostToolUse hook on Bash: after a successful git merge --no-ff, delete THIS
# project's plan file and approval state so its next task starts from a clean
# blocked state. Scoped per-project via CLAUDE_PROJECT_DIR (F-gov-02/F-gov-03):
# a merge in one project/worktree must never wipe another concurrent session's
# already-approved plan.
#
# The three grep checks below are a cheap PRE-FILTER only (avoids spawning git
# on every single Bash call) — they are NOT the safety check, because a Bash
# command whose TEXT merely mentions these phrases (e.g. echoed test data) can
# satisfy all three without any real merge happening. Proven live on
# fix/plan-approval-hook-scope, 2026-07-17: a diagnostic command that
# constructed JSON containing "Merge made by" as test data tripped this exact
# check for real and deleted a just-approved plan. The actual deletion is now
# gated on a structural check: HEAD in this project's own repo must currently
# BE a merge commit.

INPUT=$(cat)

# Cheap pre-filter — not the safety check; see comment above.
if ! echo "$INPUT" | grep -q 'git merge'; then
  exit 0
fi
if ! echo "$INPUT" | grep -q -- '--no-ff'; then
  exit 0
fi
if ! echo "$INPUT" | grep -q 'Merge made by'; then
  exit 0
fi

# Structural check: HEAD must actually BE a merge commit right now, in THIS
# project's own repo. A command whose text merely mentions the phrases above
# cannot fake this.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi
PARENT_COUNT=$(git -C "$PROJECT_DIR" log -1 --pretty=%P 2>/dev/null | wc -w)
if [ "${PARENT_COUNT:-0}" -lt 2 ]; then
  exit 0
fi

PLANS_DIR="$HOME/.claude/plans"
PROJECT_KEY=$(echo -n "${CLAUDE_PROJECT_DIR:-unknown}" | tr -c 'A-Za-z0-9' '-')
MARKER="$PLANS_DIR/.approved-$PROJECT_KEY"
CURRENT="$PLANS_DIR/.current-$PROJECT_KEY"

# Delete only THIS project's recorded plan file(s) — read the pointers before
# removing the pointer files themselves. Never touch another project's files.
if [ -f "$MARKER" ]; then
  APPROVED_PLAN=$(cat "$MARKER" 2>/dev/null)
  [ -n "$APPROVED_PLAN" ] && [ -f "$APPROVED_PLAN" ] && rm -f "$APPROVED_PLAN"
fi
if [ -f "$CURRENT" ]; then
  CURRENT_PLAN=$(cat "$CURRENT" 2>/dev/null)
  [ -n "$CURRENT_PLAN" ] && [ -f "$CURRENT_PLAN" ] && rm -f "$CURRENT_PLAN"
fi

# Delete this project's own pointer files — next task must earn fresh approval
rm -f "$MARKER" "$CURRENT"
