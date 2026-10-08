"""block-doubled-backslash guard (item 142; owner-directed 2026-10-07).

On Windows, refuses a Bash-tool command that contains two consecutive backslashes.

**Why (C-11: a recurrence gets a gate, not a note).** Claude Code starts the Bash tool's
bash as a native Windows program, and Git Bash rebuilds its argv from the Windows command
line. That rebuild halves every run of doubled backslashes, before bash parses anything.
A single backslash survives, so does the same text on stdin, and so does the same text with
`MSYS=noglob` set (`docs/dev/diagnosis/heredoc-escape-guard.md` O1-O4). The command bash
runs is therefore not the command that was written. Heredoc'd Python wrote `0x08` where
`\\b` was meant and a real newline where `\\n` was meant, and `grep` patterns silently
matched the wrong thing. That is at least nine incidents from 2026-08-05 to 2026-10-07
(O5). A prose rule ("write scripts with the Write tool") was recorded and did not hold.

**Hooks see the intended text.** The PreToolUse payload reaches this guard as JSON on stdin,
not through a command line, so the doubled backslashes are still there to find.

**No parsing, so nothing to fail open on.** The test is a substring search over the raw
command, O(n), with no regex, no `shell_split` and no subprocess. Quoting, heredocs and
`$(...)` do not matter, because the collapse happens before any of them is interpreted.
Every doubled backslash changes the bytes bash receives, even where the output happens to
come out the same (`"\\\\b"` in double quotes), so there is no false positive in the sense
of "this command would have run as written".

**Windows only (owner decision, 2026-10-07).** Linux and macOS start bash through `execve`,
with no command line to rebuild. Elsewhere the guard allows everything.

**Known limits (C-0).**
- It assumes every win32 Bash tool collapses. `tests/test_bash_backslash_collapse.py` pins
  the collapse on this machine. If that test starts failing, this guard has lost its premise.
- `MSYS=noglob` is not a way round it. It keeps backslashes, but on the harness's real
  command line (every `"` escaped as `\\"`) it breaks every quoted command
  (`docs/dev/diagnosis/bash-tool-transport.md` O3, item 157).
- It sees only the Bash tool's command string. A script file run by path is not inspected,
  and does not need to be: the Write tool writes its bytes exactly.
"""

from __future__ import annotations

import sys
from typing import Any

from scripts.enforcement.guards.result import GuardResult

_BACKSLASH = "\\"
_DOUBLED = _BACKSLASH * 2
_CONTEXT = 24

_MESSAGE_LINES = (
    f"BLOCKED (block-doubled-backslash): this command contains `{_DOUBLED}`. On this machine "
    f"the Bash tool halves every doubled backslash before bash parses the command, so "
    f"`{_DOUBLED}` would arrive as `{_BACKSLASH}`. The command that would run is not the one "
    "you wrote: heredoc'd Python writes 0x08 for a backslash-b and a real newline for a "
    "backslash-n, and grep or sed patterns match the wrong thing.",
    "Ways through: write the script with the Write tool and run it by path; make the file "
    "change with the Edit tool; run the command with the PowerShell tool, which keeps every "
    "backslash; or build the character in code (`chr(92)`).",
    "Evidence: docs/dev/diagnosis/heredoc-escape-guard.md (item 142). There is no escape "
    "hatch, and none is needed.",
)


def first_doubled(command: str) -> str | None:
    """An excerpt around the first doubled backslash in `command`, or None if there is none."""
    index = command.find(_DOUBLED)
    if index < 0:
        return None
    return command[max(0, index - _CONTEXT) : index + len(_DOUBLED) + _CONTEXT]


def decide(command: str, platform: str | None = None) -> GuardResult:
    """Pure decision: on win32, block any command containing a doubled backslash."""
    if (sys.platform if platform is None else platform) != "win32":
        return GuardResult.allow()
    excerpt = first_doubled(command or "")
    if excerpt is None:
        return GuardResult.allow()
    return GuardResult.block(*_MESSAGE_LINES, f"First match: {excerpt!r}")


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: `tool_input.command`. Subagents are checked too."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    return decide(command)
