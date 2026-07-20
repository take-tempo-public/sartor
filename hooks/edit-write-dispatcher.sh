#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: runs the five Edit/Write guards in one
# process (require-feature-branch, require-evidence-before-fix, block-secrets,
# validate-context, route-security-lint) instead of five separate hook
# entries, aggregating every blocked guard's messages before exiting — the
# settings.json PreToolUse/Edit|Write consolidation (PX-37).
#
# check-plan-approved.sh is NOT one of the five (different mechanism, not a
# scripts/enforcement/guards/ guard) — it stays wired as its own separate
# entry alongside this one.
#
# See scripts/enforcement/adapters/claude_dispatcher.py for the aggregation
# logic (no short-circuit).
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_dispatcher.py"
