#!/usr/bin/env bash
# PostToolUse hook on Bash: after a successful git merge --no-ff, delete plan
# files and the approval marker so the next task starts from a clean blocked state.

INPUT=$(cat)

# Fast exit: only care about commands containing git merge --no-ff
if ! echo "$INPUT" | grep -q 'git merge'; then
  exit 0
fi
if ! echo "$INPUT" | grep -q -- '--no-ff'; then
  exit 0
fi

# Only clean up on a confirmed successful merge (git's success string)
if ! echo "$INPUT" | grep -q 'Merge made by'; then
  exit 0
fi

PLANS_DIR="$HOME/.claude/plans"

# Delete plan files
for f in "$PLANS_DIR"/*.md; do
  [ -f "$f" ] && rm "$f"
done

# Delete marker — next task must earn fresh approval
rm -f "$PLANS_DIR/.approved"
