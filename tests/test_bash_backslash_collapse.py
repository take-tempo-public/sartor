"""Git Bash's command-line rebuild, as the Bash tool meets it (items 142, 157 and 158).

When a native Windows program starts Git Bash with ``bash -c <text>``, the MSYS2 runtime
rebuilds bash's argv from the Windows command line, and the rebuild changes ``<text>``:

- each run of doubled backslashes arrives with half its backslashes; a single backslash
  survives (item 142, ``docs/dev/diagnosis/heredoc-escape-guard.md`` O4). Claude Code's Bash
  tool starts bash this way, which is how heredoc'd scripts kept writing ``0x08`` where
  ``\\b`` was meant;
- an argument longer than 8,186 characters is silently cut to 8,186 (item 158,
  ``docs/dev/diagnosis/bash-tool-transport.md`` O4-O6). The harness wraps every command as
  ``eval '<cmd>'``, so a cut command fails with ``unexpected EOF while looking for matching``;
- ``MSYS=noglob`` stops both, but on the harness's real command line (every ``"`` escaped as
  ``\\"``) it also breaks quoting, so it is no fix (item 157, same dossier O3).

The same text on stdin arrives intact.

The ``block-doubled-backslash`` and ``block-long-bash-command`` guards exist only because of
this. **If a test here fails, the runtime has changed and a guard has lost or moved its
premise; revisit the guard rather than "fixing" the test.** Windows-only, and skipped when Git
Bash cannot be found. Every bash start runs concurrently in one module fixture, so the file
costs about one Git Bash start of wall time.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the rebuild is Windows-only")

BS, SQ, DQ = chr(92), chr(39), chr(34)
# printf %s 'X\\b|Y\b|Z\\\\b' -- built from chr(92) so no layer can touch it before Python.
PAYLOAD = "X" + BS * 2 + "b|Y" + BS + "b|Z" + BS * 4 + "b"
SCRIPT = "printf %s '" + PAYLOAD + "'"
HALVED = "X" + BS + "b|Y" + BS + "b|Z" + BS * 2 + "b"

# bash-tool-transport.md O3, exactly: printf '%s|' 'SQ' "DQ" 'A\\b' 'B\b'; echo, wrapped in
# the harness's own form (O1: eval '<cmd>', each ' rewritten as '"'"'). list2cmdline then
# escapes every " as \" on the command line, as the harness does (O2).
HARNESS_CMD = (
    "printf "
    + SQ
    + "%s|"
    + SQ
    + " "
    + SQ
    + "SQ"
    + SQ
    + " "
    + DQ
    + "DQ"
    + DQ
    + " "
    + SQ
    + "A"
    + BS * 2
    + "b"
    + SQ
    + " "
    + SQ
    + "B"
    + BS
    + "b"
    + SQ
    + "; echo"
)
HARNESS_SCRIPT = "eval " + SQ + HARNESS_CMD.replace(SQ, SQ + DQ + SQ + DQ + SQ) + SQ

# The cut (bash-tool-transport.md O4). Each script reports the length bash received.
CUT = 8186
_LENGTH_HEAD = "echo ${#BASH_EXECUTION_STRING} #"


def _sized(length: int) -> str:
    return _LENGTH_HEAD + "x" * (length - len(_LENGTH_HEAD))


# name -> (script, MSYS value or None for unset, delivered on stdin?)
_ARMS: dict[str, tuple[str, str | None, bool]] = {
    "default": (SCRIPT, None, False),
    "stdin": (SCRIPT, None, True),
    "noglob": (SCRIPT, "noglob", False),
    "harness_default": (HARNESS_SCRIPT, None, False),
    "harness_noglob": (HARNESS_SCRIPT, "noglob", False),
    "at_cut": (_sized(CUT), None, False),
    "past_cut": (_sized(CUT + 1), None, False),
}


def _git_bash() -> Path | None:
    """Git for Windows' own bash.exe. Never ``which bash``: System32's WSL bash shadows it."""
    override = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if override and Path(override).is_file():
        return Path(override)
    git = shutil.which("git")
    if not git:
        return None
    for root in Path(git).resolve().parents[:3]:
        candidate = root / "usr" / "bin" / "bash.exe"
        if candidate.is_file():
            return candidate
    return None


def _start(bash: Path, script: str, *, msys: str | None, via_stdin: bool) -> subprocess.Popen[str]:
    env = {k: v for k, v in os.environ.items() if k != "MSYS"}
    if msys is not None:
        env["MSYS"] = msys
    args = [str(bash), "-s"] if via_stdin else [str(bash), "-c", script]
    return subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        args,
        stdin=subprocess.PIPE if via_stdin else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def bash() -> Path:
    found = _git_bash()
    if found is None:
        pytest.skip("Git Bash not found")
    return found


@pytest.fixture(scope="module")
def ran(bash: Path) -> dict[str, tuple[int, str, str]]:
    """Every arm's (returncode, stdout, stderr). All arms start before any is waited on."""
    procs = {
        name: (_start(bash, script, msys=msys, via_stdin=via_stdin), script if via_stdin else None)
        for name, (script, msys, via_stdin) in _ARMS.items()
    }
    results: dict[str, tuple[int, str, str]] = {}
    try:
        for name, (proc, stdin) in procs.items():
            out, err = proc.communicate(stdin, timeout=60)
            results[name] = (proc.returncode, out, err)
    finally:
        for proc, _ in procs.values():
            if proc.poll() is None:
                proc.kill()
    return results


def test_the_command_line_halves_doubled_backslashes(ran: dict[str, tuple[int, str, str]]) -> None:
    assert ran["default"][:2] == (0, HALVED)


def test_stdin_keeps_every_backslash(ran: dict[str, tuple[int, str, str]]) -> None:
    assert ran["stdin"][:2] == (0, PAYLOAD)


def test_msys_noglob_keeps_every_backslash(ran: dict[str, tuple[int, str, str]]) -> None:
    """True only for a payload with no ``"``: see the next test for the harness's form."""
    assert ran["noglob"][:2] == (0, PAYLOAD)


def test_msys_noglob_breaks_the_harness_quoting(ran: dict[str, tuple[int, str, str]]) -> None:
    """Item 157: the control arm parses (and halves, as item 142 says); the same command line
    under ``noglob`` does not parse at all."""
    assert ran["harness_default"][:2] == (0, "SQ|DQ|A" + BS + "b|B" + BS + "b|\n")
    rc, out, err = ran["harness_noglob"]
    assert rc == 2
    assert out == ""
    assert "unexpected EOF while looking for matching" in err


def test_the_command_line_cuts_at_8186(ran: dict[str, tuple[int, str, str]]) -> None:
    """Item 158: 8,186 characters arrive whole; one more, and bash still receives 8,186."""
    assert ran["at_cut"][:2] == (0, f"{CUT}\n")
    assert ran["past_cut"][:2] == (0, f"{CUT}\n")
