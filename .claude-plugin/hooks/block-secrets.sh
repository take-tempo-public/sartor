#!/usr/bin/env bash
# PreToolUse hook on Bash|Edit|Write: block tool inputs that contain
# Anthropic API keys, env-var assignments with key values, or writes
# to known secret-file paths (.api_key, .env*, *.key, *.pem, *.p12).
#
# Reading these files is allowed; only writing/embedding is blocked.

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# Compose a haystack of strings to scan, based on which tool fired
HAYSTACK=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    inp = d.get('tool_input', {}) or {}
    parts = [
        inp.get('command', ''),
        inp.get('file_path', ''),
        inp.get('new_string', ''),
        inp.get('content', ''),
    ]
    print('\n'.join(p for p in parts if isinstance(p, str) and p))
except Exception:
    pass
" 2>/dev/null)

# Pattern 1: Anthropic API key shape (sk-ant-... with reasonable length)
if echo "$HAYSTACK" | grep -Eq 'sk-ant-[A-Za-z0-9_-]{20,}'; then
  echo "BLOCKED (block-secrets): Anthropic API key detected in tool input." >&2
  echo "Never embed API keys in code, commands, or commits." >&2
  exit 2
fi

# Pattern 2: Edit/Write targeting a known secret-file path
if [ "$TOOL" = "Edit" ] || [ "$TOOL" = "Write" ]; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
  NORM=$(echo "$FILE_PATH" | tr '\\' '/')
  if echo "$NORM" | grep -Eq '(^|/)(\.api_key|\.env|\.env\.[A-Za-z0-9_-]+|[^/]+\.pem|[^/]+\.p12|[^/]+\.key|[^/]+\.crt)$'; then
    echo "BLOCKED (block-secrets): Edit/Write to a secret file ($NORM)." >&2
    echo "Modify these outside Claude Code so the contents don't appear in transcripts." >&2
    exit 2
  fi
fi

# Pattern 3: env-var assignment with literal API key value
if echo "$HAYSTACK" | grep -Eq '(ANTHROPIC_API_KEY|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN)=[A-Za-z0-9_-]{16,}'; then
  echo "BLOCKED (block-secrets): Hard-coded API-key env-var assignment detected." >&2
  echo "Set credentials in your shell before launching Claude, not in tool input." >&2
  exit 2
fi

exit 0
