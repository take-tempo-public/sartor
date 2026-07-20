#!/usr/bin/env bash
# PostToolUse hook on Bash: after a `git commit`, if the wiki has a real ingest
# baseline AND tracked files have changed since it, emit a NON-BLOCKING reminder
# that docs/wiki/ may be stale. This is a nudge, never a gate — it ALWAYS exits 0.
#
# Why a reminder and not auto-ingest: a /wiki-ingest run costs LLM tokens, so
# running it on every commit is wrong. The hook only surfaces the drift; a human
# decides when to pay for an ingest. (See docs/wiki/SCHEMA.md "Ops".)
#
# Message tiers (witness only — the hook NEVER invokes either op): below the drift
# threshold it nudges toward a manual /wiki-ingest; at/above it the accumulated diff
# is large enough to be worth the bounded self-documenting loop, so it escalates the
# wording to /wiki-self-update. Only the WORDS change; the hook still always exits 0.
#
# Silent by design when:
#   - the tool call was not a `git commit`;
#   - docs/wiki/.last_ingest_sha is the sentinel (no 40-char SHA yet) — "not yet
#     ingested" is a known, tracked state (RELEASE_ARC WS-4a), so nagging through
#     the rest of the epic adds no information. The hook speaks only once a real
#     ingest baseline exists to measure drift against;
#   - nothing tracked changed since the baseline (the wiki itself is excluded).

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

# Only act after a git commit
if ! echo "$CMD" | grep -qE '\bgit[[:space:]]+commit\b'; then
  exit 0
fi

ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$ROOT" ]; then
  exit 0
fi

SHA_FILE="$ROOT/docs/wiki/.last_ingest_sha"
if [ ! -f "$SHA_FILE" ]; then
  exit 0
fi

# A real checkpoint is a 40-char hex SHA; the sentinel line has none.
SHA=$(grep -oE '[0-9a-f]{40}' "$SHA_FILE" | head -n1)
if [ -z "$SHA" ]; then
  exit 0  # sentinel — silent until the first ingest establishes a baseline
fi

# Count tracked files changed since the baseline, excluding the wiki itself.
CHANGED=$(git -C "$ROOT" diff --name-only "$SHA" HEAD 2>/dev/null | grep -vE '^docs/wiki/' | grep -c .)
if [ "${CHANGED:-0}" -eq 0 ]; then
  exit 0
fi

SHORT=$(echo "$SHA" | cut -c1-8)

# Drift threshold: at/above it, escalate the nudge to the bounded self-documenting
# loop (/wiki-self-update); below it, the lighter manual /wiki-ingest nudge. Tunable.
THRESHOLD=10

# Surface a non-blocking, user-facing reminder via the hook systemMessage channel.
python3 - "$CHANGED" "$SHORT" "$THRESHOLD" <<'PY' 2>/dev/null
import json, sys
changed, short, threshold = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
if changed >= threshold:
    msg = (f"wiki may be stale: {changed} file(s) changed since the last ingest "
           f"({short}) — the diff is large enough to run the loop. Consider "
           f"/wiki-self-update (bounded Haiku diff-pass); /wiki-lint for the drift report.")
else:
    msg = (f"wiki may be stale: {changed} file(s) changed since the last ingest "
           f"({short}). Consider /wiki-ingest; /wiki-lint for the drift report.")
print(json.dumps({"systemMessage": msg}))
PY

exit 0
