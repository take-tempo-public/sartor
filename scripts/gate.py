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
    pytest -m "not ux" -n auto
    pytest -m ux
    work_items check   (docs/dev/work/ backlog validation and board freshness)

Each step is print-labelled and the wrapper stops at the first failing step
(matching CI's step-by-step short-circuit), returning that step's exit code.
All output is passed through untouched (no output capture) so failures read
identically to running the command directly.

The pytest step is split and only the non-UX half is parallelized
(docs/dev/work/items/0001-gate-unrunnable-by-agent.md): the full suite's real
runtime is ~30min as of 2026-07-28, long enough that a foreground/short-timeout
agent call always got cut off — which every prior session read as a mysterious
kill, when it was really just an unmeasured runtime. `-n auto` (pytest-xdist)
cuts the non-UX tier from ~700s+ call-time to ~437s with zero new failures,
verified against PX-44's migrated-template-DB isolation work
(test/fixture-scoping-rollout) which already made the DB-touching fixtures
concurrency-safe. **The UX/Playwright tier is deliberately kept serial** —
tested with `-n 2` and it reproduced 5 real, already-diagnosed CPU-saturation
timing flakes (docs/dev/diagnosis/ux-scroll-position-flake.md's exact
mechanism) that do not occur running alone. Running two heavy pytest/Playwright
processes concurrently on this machine reliably induces that same flake class —
confirmed directly, not inherited folklore — so nothing in this repo's tooling
should ever run UX tests concurrently with another heavy process.

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
    (
        'pytest -m "not ux" -n auto',
        [sys.executable, "-m", "pytest", "-m", "not ux", "-n", "auto"],
    ),
    ("pytest -m ux", [sys.executable, "-m", "pytest", "-m", "ux"]),
    ("work_items check", [sys.executable, "-m", "scripts.work_items", "check"]),
]


def _run_step(name: str, cmd: list[str]) -> int:
    print(f"\n=== gate: {name} ===", flush=True)
    result = subprocess.run(cmd, check=False)  # noqa: S603 - fixed argv, no shell, no untrusted input
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """Run the quality-gate steps in CI order; stop at the first failure."""
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
