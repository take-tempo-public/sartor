#!/usr/bin/env bash
# PreToolUse hook on Bash|Edit|Write: block tool inputs that contain
# Anthropic API keys, env-var assignments with key values, or writes
# to known secret-file paths (.api_key, .env*, *.key, *.pem, *.p12).
#
# Reading these files is allowed; only writing/embedding is blocked.
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation — all three detection patterns and
# the exact block messages live once in
# scripts/enforcement/guards/block_secrets.py, byte-identical to this
# script's pre-migration behavior (see tests/test_enforcement_core.py). The
# same guard also runs as a native git pre-commit hook (.githooks/, opt-in)
# scanning staged content instead of one proposed tool_input.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" block-secrets
