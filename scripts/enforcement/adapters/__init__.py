"""Adapters translating one external hook contract into guard calls each.

`claude_hook.py` speaks the Claude Code PreToolUse JSON-stdin/exit-code
contract; `git_hook.py` speaks the native git `pre-commit`/`pre-merge-commit`/
`pre-push` contract. Both dispatch to the same `scripts/enforcement/guards/*`
decision functions.
"""

from __future__ import annotations
