#!/usr/bin/env bash
# SessionStart hook (startup|resume|compact): charter C-8, "durable before deep".
#
# Replays the current fix branch's diagnosis dossier — its `## Observed` and
# `## Falsified` sections — into the fresh context. SessionStart's plain stdout
# is added to Claude's context verbatim, and it fires on `compact` too, so the
# evidence re-enters the window every time the window is rebuilt. That is what
# makes context rot survivable rather than merely regrettable.
#
# Silent on non-fix branches and when there is no dossier — a hook that greets
# every session with boilerplate gets skimmed, and is then worthless on the day
# it matters.
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_context_hook.py" restore-evidence
