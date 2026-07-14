#!/usr/bin/env bash
# PreCompact hook (auto|manual): charter C-8, "durable before deep".
#
# Warns the USER when a context window is about to be discarded while the
# checked-out fix branch has no captured evidence. PreCompact cannot inject
# context into Claude (verified against the hooks reference — it supports only
# `decision: block` and `systemMessage`, and plain stdout goes to the debug log),
# so this speaks to the one party who can intervene: the human.
#
# It deliberately does NOT block compaction — a blocked auto-compact can wedge a
# session, and that cure is worse than the disease. The structural control is
# `require-evidence-before-fix`: no production code gets written without a
# dossier, so by the time a compaction lands there is always something for
# `restore-evidence` to replay.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_context_hook.py" capture-before-compact
