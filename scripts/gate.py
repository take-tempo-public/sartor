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

Before any step runs, a **memory preflight** (docs/dev/work/items/0108-gate-
memory-preflight-refusal.md) refuses to start below `_MEMORY_FLOOR_GB` free
physical memory rather than letting `-n auto` die mid-run as an OOM'd xdist
worker (`[gw0] node down: Not properly terminated`) — the exact failure four
consecutive attempts hit on 2026-09-02, misread each time as a mystery kill
until the fourth produced that decisive line. See `_MEMORY_FLOOR_GB` for how
the floor was measured. Stated limit (C-0): this closes the illegibility gap
— it converts a silent, later kill into an immediate, named refusal — but it
is a start-of-run snapshot, not a guarantee. It does not make the gate
runnable on a loaded machine (the operator still has to free memory or
wait), and it cannot detect memory pressure that arrives after the check
passes. On a platform (or in an environment) where free memory cannot be
read at all, the preflight fails OPEN — proceeds without checking — rather
than blocking a run it has no evidence against.

Usage:
    python -m scripts.gate
"""

from __future__ import annotations

import platform
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any, cast

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

# Measured 2026-09-03 on this project's primary Windows dev box (15.7 GB total
# physical memory, 8 logical cores), item 108
# (docs/dev/work/items/0108-gate-preflight-resource-check.md). Method: ran
# `pytest -m "not ux" -n auto` in the background while sampling free physical
# memory (GlobalMemoryStatusEx) every ~3s, under this machine's real ambient
# desktop load at the time (VS Code x3, Chrome x-many, NordVPN, Windows
# Defender, WSL — ordinary use, not a sibling project's gate).
#
# Result: the suite survived a genuine dip to 0.172 GB available without
# crashing, but sustained operation in the 0.4-0.8 GB band produced severe
# thrashing: the run crawled from 97% to 98% complete over roughly 15
# minutes (a normal full run takes about 7-9 minutes total) before this
# measurement was stopped by hand at about 37 minutes elapsed, both to stop
# tying up the machine and because the picture had stopped sharpening.
# Separately, item 108's own diagnosis recorded an earlier session where the
# same suite was OOM-killed (the "node down" failure) after available memory
# fell to 0.7 GB.
#
# The floor is set above both the observed sustained-thrashing band and the
# previously observed crash point, not just above the bare survival minimum
# -- "did not crash" and "ran acceptably" turned out to be different
# thresholds here. Stated limit: available memory alone is an imperfect
# proxy for "the suite will run at normal speed" (today's slow stretch and
# an earlier fast stretch occupied overlapping available-memory ranges) --
# this floor stops a run that is very likely to crash or crawl; it does not
# guarantee either outcome.
_MEMORY_FLOOR_GB = 1.0


def _parse_proc_meminfo(text: str) -> float | None:
    """Extract MemAvailable from `/proc/meminfo` text, in GB. None if absent."""
    match = re.search(r"^MemAvailable:\s+(\d+)\s+kB", text, re.MULTILINE)
    if match is None:
        return None
    return int(match.group(1)) / 1024**2


def _parse_vm_stat(text: str) -> float | None:
    """Extract free memory from macOS `vm_stat` output, in GB. None if unparsable."""
    size_match = re.search(r"page size of (\d+) bytes", text)
    free_match = re.search(r"Pages free:\s+(\d+)", text)
    if size_match is None or free_match is None:
        return None
    page_size = int(size_match.group(1))
    free_pages = int(free_match.group(1))
    return (free_pages * page_size) / 1024**3


def _windows_avail_phys_gb() -> float | None:
    """Read available physical memory via `GlobalMemoryStatusEx`, in GB.

    None on any failure. `os.name` (not `sys.platform`) is the Windows guard
    on purpose: mypy statically narrows `sys.platform` to the --platform
    value, so `sys.platform != "win32"` would mark this whole function body
    unreachable under the Linux CI platform and trip `warn_unreachable` --
    the same reason `onboarding/review_cli.py:_enable_ansi_on_windows` uses
    `os.name`, which is typed `str` and never narrowed. `ctypes.windll`
    exists only on win32; cast `ctypes` to `Any` so mypy (which now type
    checks this reachable block against Linux too) does not flag a missing
    attribute -- runtime-guarded by the `os.name` check, matching the same
    file's precedent exactly.
    """
    import os

    if os.name != "nt":
        return None
    try:
        import ctypes

        class _MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        kernel32 = cast(Any, ctypes).windll.kernel32
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return None
        avail_phys = cast(int, stat.ullAvailPhys)
        return avail_phys / 1024**3
    except OSError:
        return None


def _available_memory_gb() -> float | None:
    """Best-effort free-physical-memory read, in GB.

    None means "could not measure" -- see the module docstring: the
    preflight fails OPEN on that, since it cannot gate a number it cannot
    read. Dispatches on `platform.system()` rather than `sys.platform` on
    purpose: mypy narrows `sys.platform` to the --platform value (the host
    OS mypy itself runs on, absent an explicit override), so a sequence of
    early-return `if sys.platform == ...` checks makes every branch after
    the one matching that assumed platform provably unreachable once the
    matching branch is seen to always return -- exactly what broke CI here
    (Linux) while this same file stayed clean on Windows dev boxes.
    `platform.system()` returns a plain `str` mypy does not specially
    narrow, so all three branches stay reachable regardless of which OS
    mypy itself is running on -- the same reason `_windows_avail_phys_gb`
    uses `os.name` instead of `sys.platform` for its own guard.
    """
    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo", encoding="ascii") as handle:
                text = handle.read()
        except OSError:
            return None
        return _parse_proc_meminfo(text)
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["vm_stat"],  # noqa: S607 - fixed argv, resolved via PATH by design
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        return _parse_vm_stat(result.stdout)
    return _windows_avail_phys_gb()


def _parse_tasklist_csv(text: str) -> list[tuple[str, int]]:
    """Parse `tasklist /fo csv` output into (label, mem_kb) pairs, unsorted."""
    import csv
    import io

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header, *body = rows
    try:
        name_i = header.index("Image Name")
        pid_i = header.index("PID")
        mem_i = header.index("Mem Usage")
    except ValueError:
        return []
    parsed: list[tuple[str, int]] = []
    for row in body:
        if len(row) <= max(name_i, pid_i, mem_i):
            continue
        try:
            mem_kb = int(row[mem_i].replace(",", "").replace(" K", "").strip())
        except ValueError:
            continue
        parsed.append((f"{row[name_i]} (pid {row[pid_i]})", mem_kb))
    return parsed


def _parse_ps_output(text: str) -> list[tuple[str, int]]:
    """Parse `ps -eo pid,rss,comm` output into (label, rss_kb) pairs, unsorted.

    Tolerates a leading header row (first token "PID", non-numeric).
    """
    parsed: list[tuple[str, int]] = []
    for line in text.splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        pid, rss, comm = parts
        try:
            rss_kb = int(rss)
        except ValueError:
            continue
        parsed.append((f"{comm} (pid {pid})", rss_kb))
    return parsed


def _top_memory_consumers(limit: int = 8) -> list[str]:
    """Best-effort top-N memory consumers as "<name> (pid N) - M MB" strings.

    Returns [] if the platform listing command is unavailable or fails to
    parse -- the refusal message degrades gracefully rather than failing on
    this diagnostic-only step. Deliberately reports the raw top consumers
    rather than asserting a specific process is "the" cause: on this
    project's own dev box the top consumers are routinely ordinary desktop
    apps (an IDE, a browser, a VPN client), not another gate run, and
    claiming otherwise without evidence is a C-0 problem.
    """
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/fo", "csv"],  # noqa: S607 - fixed argv, resolved via PATH by design
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            pairs = _parse_tasklist_csv(result.stdout)
        else:
            result = subprocess.run(
                ["ps", "-eo", "pid,rss,comm"],  # noqa: S607 - fixed argv, resolved via PATH by design
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            pairs = _parse_ps_output(result.stdout)
    except (OSError, subprocess.SubprocessError):
        return []
    pairs.sort(key=lambda pair: pair[1], reverse=True)
    return [f"{label} - {kb / 1024:.0f} MB" for label, kb in pairs[:limit]]


def _check_memory_preflight() -> int:
    """Refuse to start the gate below `_MEMORY_FLOOR_GB` free physical memory.

    Returns 0 to proceed (memory OK, or unmeasurable -- fails open) and a
    non-zero code to refuse.
    """
    available = _available_memory_gb()
    if available is None:
        print(
            f"\n=== gate: memory preflight ===\n"
            f"gate: could not measure free memory on this platform ({sys.platform}) "
            f"-- proceeding without the preflight check.",
            flush=True,
        )
        return 0
    if available >= _MEMORY_FLOOR_GB:
        print(
            f"\n=== gate: memory preflight ===\n"
            f"gate: {available:.2f} GB free (floor {_MEMORY_FLOOR_GB:.2f} GB) -- proceeding.",
            flush=True,
        )
        return 0
    lines = [
        "\n=== gate: memory preflight ===",
        f"gate: REFUSED -- {available:.2f} GB free, below the {_MEMORY_FLOOR_GB:.2f} GB floor.",
        "gate: the full suite has previously died mid-run as an OOM'd xdist worker under",
        "gate: conditions like this (docs/dev/work/items/0108-gate-preflight-resource-check.md).",
        "gate: free up memory and re-run rather than waiting for a 10-30 minute mystery kill.",
    ]
    consumers = _top_memory_consumers()
    if consumers:
        lines.append("gate: top memory consumers right now:")
        lines.extend(f"gate:   {consumer}" for consumer in consumers)
    print("\n".join(lines), file=sys.stderr, flush=True)
    return 1


def _run_step(name: str, cmd: list[str]) -> int:
    print(f"\n=== gate: {name} ===", flush=True)
    result = subprocess.run(cmd, check=False)  # noqa: S603 - fixed argv, no shell, no untrusted input
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    """Run the quality-gate steps in CI order; stop at the first failure."""
    del argv  # no flags today — the wrapper takes no arguments, by design (single definition)
    preflight_code = _check_memory_preflight()
    if preflight_code != 0:
        return preflight_code
    for name, cmd in _STEPS:
        code = _run_step(name, cmd)
        if code != 0:
            print(f"\ngate: FAILED at `{name}` (exit {code})", file=sys.stderr)
            return code
    print("\ngate: all steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
