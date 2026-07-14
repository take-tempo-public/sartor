#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: charter C-7, "evidence before mechanism".
#
# On a `fix/*` branch, blocks edits to production code until
# docs/dev/diagnosis/<branch-slug>.md carries a filled-in `## Observed` section.
# docs/**, tests/** and *.md stay writable, so the way through is always open:
# instrument, reproduce, write down what you SAW — then fix.
#
# Thin wrapper forwarding the Claude PreToolUse JSON contract on stdin to the
# shared guard (scripts/enforcement/guards/require_evidence_before_fix.py), the
# same adapter pattern every other guard here uses.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" require-evidence-before-fix
