"""Unified quality-gate wrapper (PX-55, 2026-07 efficiency review).

Before this script existed, "gate green" was defined independently in three
places — `.github/workflows/ci.yml`'s `quality` job, `AGENTS.md`, and
`CONTRIBUTING.md` — with no mechanism to keep the three in sync. This module
is the single definition; the three docs/workflow now invoke it instead of
restating the step list.

Runs, in order, exactly the steps the CI `quality` job runs:

    ruff check .
    ruff format --check .
    mypy .
    pytest

Each step is print-labelled and the wrapper stops at the first failing step
(matching CI's step-by-step short-circuit), returning that step's exit code.
All output is passed through untouched (no output capture) so failures read
identically to running the command directly.

Usage:
    python -m scripts.gate
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

# Invoked as `sys.executable -m <tool>` rather than the bare console-script name
# (`ruff`, `mypy`, `pytest`) — the same portability reason `ruff_changed.py`'s
# guard already documents: an editable/venv install's console scripts are not
# guaranteed to be on PATH (they aren't on this project's Windows Store Python
# setup), but `python -m <tool>` always resolves once the package is installed.
_STEPS: list[tuple[str, list[str]]] = [
    ("ruff check .", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format --check .", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("mypy .", [sys.executable, "-m", "mypy", "."]),
    ("pytest", [sys.executable, "-m", "pytest"]),
]


def _run_step(name: str, cmd: list[str]) -> int:
    print(f"\n=== gate: {name} ===", flush=True)
    result = subprocess.run(cmd, check=False)  # noqa: S603 - fixed argv, no shell, no untrusted input
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """Run the four quality-gate steps in CI order; stop at the first failure."""
    del argv  # no flags today — the wrapper takes no arguments, by design (single definition)
    for name, cmd in _STEPS:
        code = _run_step(name, cmd)
        if code != 0:
            print(f"\ngate: FAILED at `{name}` (exit {code})", file=sys.stderr)
            return code
    print("\ngate: all steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
