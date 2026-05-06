#!/usr/bin/env bash
# PreToolUse hook on Bash: when a `git commit` is about to run, run ruff
# on the staged Python files. Block the commit if ruff reports issues.
# Skips if no Python files are staged.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# Fast exit: only act on git commit invocations
if ! echo "$CMD" | grep -qE '\bgit[[:space:]]+commit\b'; then
  exit 0
fi

# Find staged .py files (cwd-relative). If none, nothing to do.
STAGED=$(git diff --cached --name-only -- '*.py' 2>/dev/null)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Run ruff against the staged files. Stream output to stderr so the user sees it.
if ! python -m ruff check $STAGED 1>&2; then
  echo "" >&2
  echo "BLOCKED (ruff-changed): ruff reported issues on staged Python files." >&2
  echo "Fix them (or auto-fix many: python -m ruff check --fix), re-stage, then re-commit." >&2
  exit 2
fi

exit 0
