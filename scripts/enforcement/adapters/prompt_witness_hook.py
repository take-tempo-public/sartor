#!/usr/bin/env python3
"""Claude Code UserPromptSubmit adapter for the interrogative-prompt witness (item 87).

Reads the standard hook-input JSON from stdin (``session_id`` + ``prompt``),
records the per-session pause state via
`scripts.enforcement.guards.interrogative_witness.record_prompt`, and — when
the heuristic classifies the prompt as a question — prints the reminder to
stdout, which UserPromptSubmit adds to Claude's context verbatim (the same
plain-stdout channel `restore-evidence` uses on SessionStart).

Always exits 0, on every path including internal failure: this is the
fail-open half of the witness pair, and a prompt hook that can wedge prompt
submission would be a worse defect than the momentum failure it mitigates.
The classification limits are stated in the guard module's docstring
(charter C-0/C-11) — this adapter only translates stdin/stdout.

Invoked by `hooks/interrogative-prompt-witness.sh`:

    exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/prompt_witness_hook.py"
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.adapters import claude_hook  # noqa: E402
from scripts.enforcement.guards import interrogative_witness  # noqa: E402


def main(argv: list[str]) -> int:
    """CLI entry point: no arguments — stdin is the UserPromptSubmit payload."""
    del argv
    try:
        payload = claude_hook.load_payload()
        session_id = str(payload.get("session_id") or "")
        prompt = str(payload.get("prompt") or "")
        if interrogative_witness.record_prompt(session_id, prompt):
            for line in interrogative_witness.REMINDER_LINES:
                print(line)
    except Exception:  # fail-open witness: never disturb prompt submission
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
