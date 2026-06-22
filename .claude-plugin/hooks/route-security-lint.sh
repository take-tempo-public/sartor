#!/usr/bin/env bash
# PreToolUse hook on Edit|Write of app.py OR a route-bearing blueprint module
# under blueprints/: when proposed content adds or modifies a Flask route
# (@app.route or @<bp>.route/.get/.post/...) that touches the filesystem,
# require both _safe_username() and _within() to appear in the same content.
# Encodes the security pattern documented in CLAUDE.md "Key Patterns — Security".
#
# Scope (PX-21, v1.0.8 blueprint split): app.py + blueprints/**.py. The
# read-only dashboard/ surface is deliberately NOT covered — its routes are
# localhost-gated, take no <username>, and read fixed diagnostic dirs, so the
# _safe_username/_within user-path guards do not apply there.
#
# Heuristic, not perfect: catches obvious omissions; review still required
# for routes that do filesystem access through indirection.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Only act on app.py or a module under blueprints/ (any depth, so a corpus
# sub-package like blueprints/corpus/experiences.py is covered too). The file
# matcher intentionally over-selects (a route-free helper under blueprints/
# also matches here) — the route + filesystem content checks below are the
# real gate, so such a file still exits 0.
NORM=$(echo "$FILE_PATH" | tr '\\' '/')
if ! echo "$NORM" | grep -qE '(^|/)app\.py$|(^|/)blueprints/.*\.py$'; then
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
#
# Route detection covers @app.route AND blueprint decorators
# (@<bp>.route/.get/.post/.put/.delete/.patch). The leading @ is load-bearing:
# it keeps the bare method names (.get/.post/...) from false-matching ordinary
# dict/object access like data.get( or request.json.get(.
if ! echo "$CONTENT" | grep -qE '@[A-Za-z_][A-Za-z0-9_]*\.(route|get|post|put|delete|patch)\('; then
  exit 0
fi

# CONFIGS_DIR is intentionally NOT a filesystem indicator (Sprint 8.3d): post-8.3a
# a route body only ever reaches it as `_safe_username(configs_dir=...)`, and
# _safe_username IS the containment guard (secure_filename + existence check). The
# raw `CONFIGS_DIR / f"{username}.config"` path construction that _within protected
# was removed in PX-21. OUTPUT_DIR/RESUMES_DIR/open(/Path(/send_file( remain
# indicators, so upload/ingest/download routes still require _within.
if ! echo "$CONTENT" | grep -qE '\b(open\(|send_file\(|send_from_directory\(|Path\(|read_text\(|write_text\(|\.exists\(\)|os\.path\.|RESUMES_DIR|OUTPUT_DIR)\b'; then
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
  echo "BLOCKED (route-security-lint): proposed route-module edit defines a route" >&2
  echo "that touches the filesystem without calling:$MISSING" >&2
  echo "" >&2
  echo "See CLAUDE.md 'Key Patterns — Security' for the required call sequence." >&2
  echo "If this is a false positive (e.g., a partial Edit that doesn't show the" >&2
  echo "guards), include the full route block in the new_string." >&2
  exit 2
fi

exit 0
