#!/usr/bin/env bash
# PreToolUse hook on Bash: when a `git commit` is about to run, run ruff
# (lint + format check) on the staged Python files. Block the commit if ruff
# reports lint issues OR any staged file is not ruff-formatted.
# Skips if no Python files are staged.
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation
# (scripts/enforcement/guards/ruff_changed.py) — the block/allow decision and
# fix-it guidance are byte-identical to this script's pre-migration behavior
# (see tests/test_enforcement_core.py; exact ruff diagnostic text is
# naturally environment-dependent, so the equivalence tests compare
# block-message substance, not a byte-exact ruff transcript). The same guard
# also runs as a native git pre-commit hook (.githooks/, opt-in), where it is
# simpler still: no `git commit` substring detection needed, since the hook
# only fires when a commit is actually happening.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" ruff-changed
