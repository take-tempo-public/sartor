"""SessionStart probe: which of this machine's shells can run ``python3``, ``sleep`` and
``grep`` (item 152). A witness: it warns, it never gates, and it always returns 0.

Why it exists: on 2026-10-03 the Bash tool resolved a ``/usr/bin/bash`` with no coreutils.
``python``, ``grep`` and ``sleep`` were all "command not found", and a Monitor armed with
``until grep -q …; do sleep 15; done`` busy-looped at full CPU until stopped. The hooks no
longer need any shell (``scripts/enforcement/adapters/hook.py``), but the agent's own Bash
calls still do. So the probe says, at session start, which shell lacks what.

Silent when every probed shell has every tool: a hook that greets every session with
boilerplate gets skimmed. SessionStart stdout is added to the session's context.

**Known limits (C-0):**
- The probe cannot see which bash the Bash *tool* will resolve. It reports the bash on PATH
  and, on Windows, Git for Windows' own bash, which are the two observed.
- It cannot report a missing ``python3``, because it runs on ``python3``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = ("python3", "python", "sleep", "grep")
_BUDGET_S = 3.0
_SCRIPT = "for c in " + " ".join(TOOLS) + "; do command -v $c >/dev/null 2>&1 || echo $c; done"


def _candidate_shells() -> list[str]:
    shells: list[str] = []
    on_path = shutil.which("bash")
    if on_path:
        shells.append(on_path)
    if os.name == "nt":
        git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git" / "bin"
        git_bash = git_bash / "bash.exe"
        if git_bash.is_file() and all(Path(s).resolve() != git_bash.resolve() for s in shells):
            shells.append(str(git_bash))
    return shells


def probe() -> dict[str, list[str] | None]:
    """Shell path -> the tools it cannot find (None: the shell did not answer in time).

    Every shell is started at once and waited on together, so the probe costs one budget,
    not one per shell.
    """
    procs: dict[str, subprocess.Popen[str] | None] = {}
    for shell in _candidate_shells():
        try:
            procs[shell] = subprocess.Popen(  # noqa: S603 - fixed argv, constant script
                [shell, "-c", _SCRIPT],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            procs[shell] = None
    result: dict[str, list[str] | None] = {}
    for shell, proc in procs.items():
        if proc is None:
            result[shell] = None
            continue
        try:
            out, _ = proc.communicate(timeout=_BUDGET_S)
            result[shell] = out.split()
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            result[shell] = None
    return result


def report(results: dict[str, list[str] | None]) -> str:
    """The context note, or "" when every shell has every tool (``python`` alone missing is
    fine wherever ``python3`` is present)."""
    problems: list[str] = []
    for shell, missing in results.items():
        if missing is None:
            problems.append(f"- `{shell}` did not answer within {_BUDGET_S:.0f} s.")
            continue
        real = [t for t in missing if not (t == "python" and "python3" not in missing)]
        if real:
            problems.append(f"- `{shell}` cannot find: {', '.join(real)}.")
    if not problems:
        return ""
    return "\n".join(
        [
            "shell-probe (item 152): some of this machine's shells lack basic tools.",
            *problems,
            "If the Bash tool reports `command not found` for any of these, do not arm a "
            "Monitor or a `sleep` loop in it: it will spin at full CPU. Use PowerShell or a "
            "`python3 -c` loop instead. Hooks do not depend on any shell.",
        ]
    )


def main(argv: list[str]) -> int:
    del argv
    try:
        sys.stdin.read()
        text = report(probe())
    except Exception:
        return 0
    if text:
        print(text)
    return 0
