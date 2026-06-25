"""Docstring-coverage floor-lock gate — kit-adoption Phase 2 final sub-item (KIT-6/KIT-7).

WHY: Decision KIT-6 "measured-current / warn-start" — lock today's production public-API
docstring coverage as a do-not-regress floor. It forces no new docstrings (green today),
turning red only on a drop below the floor. This is the aggregate-% companion to the ruff-`D`
family, which gates per-symbol docstring *presence*; interrogate catches a module-scale
regression that could slip under D's per-file ratchet, and — empirically — is slightly stricter
on class docstrings than ruff-`D`/google. At adoption it surfaced two undocumented public
classes (`onboarding`'s `Color` and `ExtractResponse`) that google's D101 leaves un-flagged;
both were documented to reach the 100% baseline this floor locks. See
docs/dev/kit-adoption-design.md §4/§6 and docs/dev/decisions.md KIT-6/KIT-7.

HOW: the single source of truth is `[tool.interrogate]` in pyproject.toml (scope, ignore flags,
and `fail-under`). A bare `python -m interrogate -c pyproject.toml .` reproduces this gate
locally; this test re-runs that exact CLI and asserts exit 0 (interrogate exits non-zero when
coverage < `fail-under`). The floor lives once, as `fail-under`; the test reads it via `tomllib`
only for the sanity-teeth check below — no duplicated magic number.

SKIP: interrogate is a dev-extra; when it is not installed the test SKIPS (mirroring the
tests/ux/conftest.py Chromium skip-guard) so the default `pytest` stays green without dev-extras.
CI installs dev-extras, so the gate has teeth there.

SCOPE: production only — the KIT-7 exempt set (tests/ · evals/ · scripts/ · db/migrations) is
excluded in `[tool.interrogate].exclude`; `ui_pages/**` stays IN scope to match the surface
ruff-`D` covers (its ratchet unit 8). Single-underscore helpers are semiprivate and excluded
(`ignore-semiprivate`), keeping the metric coherent with ruff-`D`'s public-only scope (so a
helper-only module like `web_infra/` contributes zero counted symbols, by design).

TO RAISE THE FLOOR ("ratchet up later"): document more of the production tree, re-run
interrogate, and bump `fail-under` in pyproject.toml in a later branch. Never lower it.

For a maintainer who prefers interrogate's Python API over this subprocess: the path is
`from interrogate.coverage import InterrogateCoverage` then `.get_coverage().perc_covered`
(confirm against the installed version). This gate deliberately uses the CLI so it depends only
on interrogate's stable command contract, not its internal module layout.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Sane window for the recorded floor: a real production-API coverage %, never 0 (gate silently
# disabled) and never absurd. The lower bound is the load-bearing guard.
_FLOOR_MIN = 50
_FLOOR_MAX = 100
# Teeth: interrogate must scan a non-trivial public-API surface (currently 417 symbols). A
# misconfigured `exclude` that empties the scope would otherwise pass "100% of nothing"
# vacuously — the route-containment gate's "has teeth" discipline, applied here.
_MIN_SCANNED_SYMBOLS = 250


def _configured_floor() -> int:
    """Return `[tool.interrogate].fail-under` from pyproject.toml (the single source of truth)."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return int(data["tool"]["interrogate"]["fail-under"])


def test_configured_floor_is_sane() -> None:
    """The recorded floor must be a real measured value, not a placeholder.

    Guards against `fail-under` reset to 0 (gate silently off) or an absurd value. Reads
    pyproject only, so it runs even when interrogate is not installed.
    """
    floor = _configured_floor()
    assert _FLOOR_MIN <= floor <= _FLOOR_MAX, (
        f"[tool.interrogate].fail-under = {floor} is outside the sane window "
        f"[{_FLOOR_MIN}, {_FLOOR_MAX}]; it must be the measured production docstring-coverage "
        "% floored with a small headroom (KIT-6 measured-current)."
    )


def test_docstring_coverage_meets_floor() -> None:
    """Re-run the bare interrogate CLI and assert production coverage meets the recorded floor.

    Floor-lock ratchet: green today, red only on a regression below `fail-under`. Skips when
    interrogate is not installed (default pytest stays green; CI has teeth). The teeth checks
    assert interrogate scanned a non-trivial production surface, so an emptied/misconfigured
    scope cannot pass vacuously.
    """
    if importlib.util.find_spec("interrogate") is None:
        pytest.skip(
            "interrogate not installed — `pip install -e .[dev]` to run the docstring-coverage "
            "gate (CI installs dev-extras, so the gate has teeth there)."
        )
    result = subprocess.run(  # noqa: S603 - static, trusted argv (sys.executable + string literals)
        [sys.executable, "-m", "interrogate", "-c", str(PYPROJECT), "-v", "."],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    # Teeth 1: the scan named real production modules (not an empty / misscoped run).
    assert "analyzer.py" in output and "hardening.py" in output, (
        "interrogate -v output names no core production module — the scope is empty or "
        "misconfigured; check [tool.interrogate].exclude.\n" + output
    )
    # Teeth 2: the scan covered a non-trivial number of symbols.
    match = re.search(r"TOTAL\s*\|\s*(\d+)\s*\|", output)
    assert match is not None, "could not parse interrogate's TOTAL summary row:\n" + output
    scanned = int(match.group(1))
    assert scanned >= _MIN_SCANNED_SYMBOLS, (
        f"interrogate scanned only {scanned} symbols (< {_MIN_SCANNED_SYMBOLS}) — the production "
        "scope looks empty/misconfigured; check [tool.interrogate].exclude.\n" + output
    )
    # Floor-lock: interrogate exits non-zero when coverage < fail-under.
    assert result.returncode == 0, (
        f"Production docstring coverage fell below [tool.interrogate].fail-under "
        f"({_configured_floor()}%). Add docstrings to restore the floor; do NOT lower fail-under "
        "(KIT-6: the floor ratchets UP, never down).\n" + output
    )
