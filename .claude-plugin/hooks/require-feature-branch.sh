#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: block code changes while on the default
# branch (main/master). The deterministic enforcement point for "create a
# feature branch before executing a plan" — there is no ExitPlanMode block
# event, so the first Edit/Write after plan→execute is where we gate (same
# philosophy as check-plan-approved.sh).
#
# Portable-enforcement-core adapter (feat/portable-enforcement-core,
# 2026-07-08): thin wrapper forwarding the Claude PreToolUse JSON contract on
# stdin to the shared guard implementation — decision logic, the plans-dir
# exemption, and the CLAUDE_ALLOW_MAIN_EDITS=1 escape hatch all live once in
# scripts/enforcement/guards/require_feature_branch.py, byte-identical to this
# script's pre-migration behavior (see tests/test_enforcement_core.py). The
# same guard also runs as a native git pre-commit hook (.githooks/, opt-in)
# and is reused by the Claude adapter here.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_hook.py" require-feature-branch
