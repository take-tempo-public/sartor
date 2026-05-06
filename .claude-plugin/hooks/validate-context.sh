#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: validate proposed content for
# output/**/context_*.json files. Currently checks JSON syntax;
# Step 7 (eval harness) will add a schema check against
# evals/schemas/context_set.schema.json once that file exists.
#
# These files are normally written by the running app via
# hardening.save_context_set(); a Claude Edit/Write usually means
# debugging or replay — guard against malformed JSON either way.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Normalize separators and match the canonical context-set path shape
NORM=$(echo "$FILE_PATH" | tr '\\' '/')
if ! echo "$NORM" | grep -qE '(^|/)output/[^/]+/context_[^/]*\.json$'; then
  exit 0
fi

# Get the proposed content
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
  exit 0  # No content to validate (e.g., partial Edit input)
fi

# JSON syntax check
if ! echo "$CONTENT" | python3 -c "import sys, json; json.loads(sys.stdin.read())" 2>/dev/null; then
  echo "BLOCKED (validate-context): Proposed content for $NORM is not valid JSON." >&2
  exit 2
fi

# Schema check: only if the schema exists (Step 7 introduces it)
SCHEMA="$CLAUDE_PROJECT_DIR/evals/schemas/context_set.schema.json"
if [ -f "$SCHEMA" ]; then
  if ! python3 -c "
import sys, json
try:
    import jsonschema
except ImportError:
    sys.exit(0)  # jsonschema not installed; skip silently
schema = json.load(open(r'$SCHEMA', encoding='utf-8'))
data = json.loads(sys.stdin.read())
try:
    jsonschema.validate(data, schema)
except jsonschema.ValidationError as e:
    print(f'BLOCKED (validate-context): schema violation — {e.message}', file=sys.stderr)
    sys.exit(2)
" <<< "$CONTENT"; then
    exit 2
  fi
fi

exit 0
