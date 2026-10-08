"""block-long-bash-command guard (item 158; owner-directed 2026-10-08).

On Windows, refuses a Bash-tool command too long to reach bash whole.

**Why (C-11: a recurrence gets a gate, not a note).** Claude Code starts the Bash tool's bash
as a native Windows program and puts the command on bash's command line, wrapped as
`eval '<cmd>'` with each `'` rewritten as `'"'"'`, after about 400 characters of setup
(`docs/dev/diagnosis/bash-tool-transport.md` O1, O6). Git Bash rebuilds its argv from that
command line and silently cuts any argument longer than 8,186 characters (O4), counting
characters, not bytes (O5). The cut lands inside the `eval '…'` quote, so bash refuses the
whole command with `unexpected EOF while looking for matching '` and runs none of it. That
happened six times in the recorded transcripts, to heredoc'd scripts of 7.8K-14.8K characters
that parse fine as written (O7), and once more on purpose inside the harness (O6).

**The budget.** The wrapped length is `len(command)` plus 4 for every `'`, since each `'`
becomes five characters. It must not exceed `CUT - RESERVE`. `RESERVE` stands for the
harness's own setup text. That measured 408 characters on this machine (O6); it holds the home
and temp paths four times, so the reserve leaves room for longer ones.

**No parsing, so nothing to fail open on.** `len` and `str.count` over the raw command, O(n),
with no regex and no subprocess. Quoting and heredocs do not matter: the cut happens before
bash interprets any of them.

**Windows only (owner decision, as for `block-doubled-backslash`).** Linux and macOS start bash
through `execve`, with no command line to rebuild. Elsewhere the guard allows everything.

**Known limits (C-0).**
- `RESERVE` estimates a wrapper this guard cannot see. A home or temp path much longer than
  this machine's, or a harness release that adds setup text, could let through a command that
  bash still receives cut. Shrinking the reserve needs a fresh O6 measurement.
- The count is in Python characters (code points). The runtime may count a character outside
  the Basic Multilingual Plane as two (not measured), so a command full of them could pass and
  still be cut.
- `tests/test_bash_backslash_collapse.py::test_the_command_line_cuts_at_8186` pins `CUT` to the
  runtime on this machine. If it fails, re-measure before trusting this guard.
- It sees only the Bash tool's command string. A script file run by path has no such limit,
  which is the way through.
"""

from __future__ import annotations

import sys
from typing import Any

from scripts.enforcement.guards.result import GuardResult

#: Git Bash's cut on a command-line argument, in characters (dossier O4, O5).
CUT = 8186
#: Room for the harness's wrapper around the command: 408 measured here (dossier O6).
RESERVE = 1024
#: The longest wrapped command this guard lets through.
BUDGET = CUT - RESERVE

_QUOTE = "'"
_QUOTE_COST = 4  # each ' is rewritten as '"'"', four characters more


def wrapped_length(command: str) -> int:
    """The command's length once the harness wraps it, less the harness's own setup text."""
    return len(command) + _QUOTE_COST * command.count(_QUOTE)


def decide(command: str, platform: str | None = None) -> GuardResult:
    """Pure decision: on win32, block a command whose wrapped length exceeds `BUDGET`."""
    if (sys.platform if platform is None else platform) != "win32":
        return GuardResult.allow()
    size = wrapped_length(command or "")
    if size <= BUDGET:
        return GuardResult.allow()
    return GuardResult.block(
        f"BLOCKED (block-long-bash-command): this command is {size:,} characters once the Bash "
        f"tool wraps it (every ' counts as 5), over the {BUDGET:,} budget. On this machine Git "
        f"Bash silently cuts its command line at {CUT:,} characters, so bash would receive a "
        "truncated command and refuse all of it with `unexpected EOF while looking for "
        "matching`.",
        "Ways through: write the script with the Write tool and run it by path "
        "(`python <file>`, `bash <file>`), or split the work into shorter commands.",
        "Evidence: docs/dev/diagnosis/bash-tool-transport.md (item 158). There is no escape "
        "hatch, and none is needed.",
    )


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: `tool_input.command`. Subagents are checked too."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    return decide(command)
