#!/usr/bin/env bash
# PreToolUse hook on Bash: when a `git commit` is about to run, run ruff
# (lint + format check) on the staged Python files. Block the commit if ruff
# reports lint issues OR any staged file is not ruff-formatted.
# Skips if no Python files are staged.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# Fast exit: only act on git commit invocations
if ! echo "$CMD" | grep -qE '\bgit[[:space:]]+commit\b'; then
  exit 0
fi

# Find staged .py files (cwd-relative), excluding deletions. If none, nothing to do.
STAGED=$(git diff --cached --name-only --diff-filter=ACM -- '*.py' 2>/dev/null)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Run ruff lint against the staged files. Stream output to stderr so the user sees it.
if ! python -m ruff check $STAGED 1>&2; then
  echo "" >&2
  echo "BLOCKED (ruff-changed): ruff reported issues on staged Python files." >&2
  echo "Fix them (or auto-fix many: python -m ruff check --fix), re-stage, then re-commit." >&2
  exit 2
fi

# Kit-adoption Phase 1 (KIT-6 — hard-block unambiguous gates day one): also require
# staged Python to be ruff-formatted. `ruff format --check` is non-mutating; it exits
# non-zero when a file would be reformatted.
if ! python -m ruff format --check $STAGED 1>&2; then
  echo "" >&2
  echo "BLOCKED (ruff-changed): staged Python files are not ruff-formatted." >&2
  echo "Run: python -m ruff format <files>  (or: python -m ruff format .), re-stage, then re-commit." >&2
  exit 2
fi

exit 0
