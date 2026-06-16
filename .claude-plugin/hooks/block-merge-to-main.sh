#!/usr/bin/env bash
# PreToolUse hook on Bash: block `git merge` and `git push origin` targeting
# main/master unless the command itself opts in with CLAUDE_CONFIRM_MERGE=1
# as an env-var prefix. Encodes the project's "always confirm before merge"
# rule deterministically.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# Detect: merge into main/master, or push to origin main/master
TARGETING_MAIN=0
if echo "$CMD" | grep -qE '\bgit[[:space:]]+merge\b.*\b(main|master)\b'; then
  TARGETING_MAIN=1
fi
if echo "$CMD" | grep -qE '\bgit[[:space:]]+push\b.*\borigin[[:space:]]+(main|master)\b'; then
  TARGETING_MAIN=1
fi

# PX-24 (F-gov-01): the dominant direction is `git checkout main` then
# `git merge feature --no-ff`, which names the branch (not "main") and slipped past
# the greps above. Catch a `git merge` issued while HEAD is main/master. Scoped to
# merge commands so ordinary read commands on main (status/log/checkout) are unaffected.
# `git rev-parse --abbrev-ref HEAD` is worktree-local — safe under W-1.
if echo "$CMD" | grep -qE '\bgit[[:space:]]+merge\b'; then
  CUR_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ "$CUR_BRANCH" = "main" ] || [ "$CUR_BRANCH" = "master" ]; then
    TARGETING_MAIN=1
  fi
fi

if [ "$TARGETING_MAIN" -eq 0 ]; then
  exit 0
fi

# Allow if the command itself opts in
if echo "$CMD" | grep -q 'CLAUDE_CONFIRM_MERGE=1'; then
  exit 0
fi

echo "BLOCKED (block-merge-to-main): git merge/push targeting main or master." >&2
echo "If you really intend this, prefix the command with: CLAUDE_CONFIRM_MERGE=1" >&2
echo "Example: CLAUDE_CONFIRM_MERGE=1 git merge feature-branch --no-ff -m '...'" >&2
exit 2
