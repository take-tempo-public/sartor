"""Item 142's premise as a test: Git Bash halves every doubled backslash on its command line.

When a native Windows program starts Git Bash with ``bash -c <text>``, each run of doubled
backslashes in ``<text>`` arrives with half its backslashes. A single backslash survives,
and so does the same text on stdin or with ``MSYS=noglob`` set. Claude Code's Bash tool
starts bash this way, which is how heredoc'd scripts kept writing ``0x08`` where ``\\b``
was meant (``docs/dev/diagnosis/heredoc-escape-guard.md`` O4).

The ``block-doubled-backslash`` guard exists only because of this. **If this test fails, the
collapse is gone and the guard has lost its premise; revisit it rather than "fixing" the
test.** Windows-only, and skipped when Git Bash cannot be found.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the collapse is Windows-only")

BS = chr(92)
# printf %s 'X\\b|Y\b|Z\\\\b' -- built from chr(92) so no layer can touch it before Python.
PAYLOAD = "X" + BS * 2 + "b|Y" + BS + "b|Z" + BS * 4 + "b"
SCRIPT = "printf %s '" + PAYLOAD + "'"
HALVED = "X" + BS + "b|Y" + BS + "b|Z" + BS * 2 + "b"


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


def _run(bash: Path, *, env_msys: str | None, via_stdin: bool) -> str:
    env = {k: v for k, v in os.environ.items() if k != "MSYS"}
    if env_msys is not None:
        env["MSYS"] = env_msys
    args = [str(bash), "-s"] if via_stdin else [str(bash), "-c", SCRIPT]
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        args,
        input=SCRIPT if via_stdin else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return result.stdout


@pytest.fixture(scope="module")
def bash() -> Path:
    found = _git_bash()
    if found is None:
        pytest.skip("Git Bash not found")
    return found


def test_the_command_line_halves_doubled_backslashes(bash: Path) -> None:
    assert _run(bash, env_msys=None, via_stdin=False) == HALVED


def test_stdin_keeps_every_backslash(bash: Path) -> None:
    assert _run(bash, env_msys=None, via_stdin=True) == PAYLOAD


def test_msys_noglob_keeps_every_backslash(bash: Path) -> None:
    assert _run(bash, env_msys="noglob", via_stdin=False) == PAYLOAD
