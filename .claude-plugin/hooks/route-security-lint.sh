#!/usr/bin/env bash
# PreToolUse hook on Edit|Write of app.py: when proposed content adds or
# modifies a Flask @app.route that touches the filesystem, require both
# _safe_username() and _within() to appear in the same content. Encodes
# the security pattern documented in CLAUDE.md "Key Patterns — Security".
#
# Heuristic, not perfect: catches obvious omissions; review still required
# for routes that do filesystem access through indirection.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only act on app.py
NORM=$(echo "$FILE_PATH" | tr '\\' '/')
if ! echo "$NORM" | grep -qE '(^|/)app\.py$'; then
  exit 0
fi

# Get proposed content (Edit's new_string OR Write's content)
CONTENT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    inp = d.get('tool_input', {}) or {}
    print(inp.get('new_string', '') or inp.get('content', ''))
except Exception:
    pass
" 2>/dev/null)

if [ -z "$CONTENT" ]; then
  exit 0
fi

# Quick checks — the proposed content must contain a route definition AND
# evidence of filesystem access for the lint to trigger. Otherwise pass.
if ! echo "$CONTENT" | grep -qE '@app\.route\('; then
  exit 0
fi

if ! echo "$CONTENT" | grep -qE '\b(open\(|send_file\(|Path\(|read_text\(|write_text\(|\.exists\(\)|os\.path\.|RESUMES_DIR|OUTPUT_DIR|CONFIGS_DIR)\b'; then
  exit 0
fi

# Both helpers must appear
MISSING=""
if ! echo "$CONTENT" | grep -q '_safe_username'; then
  MISSING="$MISSING _safe_username()"
fi
if ! echo "$CONTENT" | grep -q '_within'; then
  MISSING="$MISSING _within()"
fi

if [ -n "$MISSING" ]; then
  echo "BLOCKED (route-security-lint): proposed app.py edit defines a route that" >&2
  echo "touches the filesystem without calling:$MISSING" >&2
  echo "" >&2
  echo "See CLAUDE.md 'Key Patterns — Security' for the required call sequence." >&2
  echo "If this is a false positive (e.g., a partial Edit that doesn't show the" >&2
  echo "guards), include the full route block in the new_string." >&2
  exit 2
fi

exit 0
