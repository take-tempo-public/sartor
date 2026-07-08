#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: validate proposed content for
# output/**/context_*.json files. Currently checks JSON syntax;
# Step 7 (eval harness) will add a schema check against
# evals/schemas/context_set.schema.json once that file exists.
#
# These files are normally written by the running app via
# hardening.save_context_set(); a Claude Edit/Write usually means
# debugging or replay — guard against malformed JSON either way.
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation
# (scripts/enforcement/guards/validate_context.py), byte-identical to this
# script's pre-migration behavior (see tests/test_enforcement_core.py). The
# same guard also runs as a native git pre-commit hook (.githooks/, opt-in)
# scanning any staged context-set files.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" validate-context
