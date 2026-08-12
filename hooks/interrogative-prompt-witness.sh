#!/usr/bin/env bash
# UserPromptSubmit hook: the prompt-receipt half of the interrogative-prompt
# witness (work item 87). A cheap heuristic — trailing "?" or an
# interrogative lead word — records per-session state and, on a match,
# injects a non-blocking "the deliverable is the ANSWER" reminder into
# context via plain stdout (the same channel restore-evidence.sh uses).
#
# Always exit 0 — fail-open witness, never a gate. The Edit|Write pause half
# runs inside edit-write-dispatcher.sh (the `interrogative-witness` guard).
exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/prompt_witness_hook.py"
