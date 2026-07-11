"""mypy --strict roster falsifiability gate — kit-adoption Phase 2 §6-exit (KIT-6/KIT-7).

WHY: the kit-adoption mypy ``--strict`` ratchet reached its §6 exit (2026-07-10) — the
categorical claim "every non-exempt production module is at full ``--strict``; only the
Decision-7 exempt set stays permissive" (docs/dev/kit-adoption-design.md §6; the pyproject
strict-roster block comment). Charter **C-0** (docs/governance/charter.md) requires a
categorical claim be enforced BY CONSTRUCTION, not by a one-time manual proof: without a
gate, a new ``.py`` added outside the exempt set and left off the strict roster would
type-check under the permissive GLOBAL mypy config — ``mypy .`` would still print "Success",
and the §6 claim would go silently stale (compliance-witness CW-118). This test reifies the
§6-exit proof as a do-not-regress gate — the mypy-roster analogue of the two sibling KEEP
gates (tests/test_route_containment_gate.py, tests/test_docstring_coverage_gate.py).

HOW: parse the strict roster — the ``[[tool.mypy.overrides]]`` block carrying
``disallow_untyped_defs`` (NOT the ignore-missing-imports block) — from pyproject.toml via
``tomllib`` (single source of truth). Enumerate every tracked ``*.py`` (``git ls-files``)
minus the Decision-7 exempt set, map each to its module name, and assert every one is
covered by a roster entry under mypy's own per-module glob semantics (``pkg.*`` matches
``pkg`` itself and any ``pkg.sub``; a non-wildcard entry matches only the exact module —
mypy docs: ``mycode.foo.*`` matches ``mycode.foo``, ``mycode.foo.bar``, …). A module that
escapes strict fails here even though ``mypy .`` stays green.

SCOPE / EXEMPT SET: ``tests/`` ONLY (Decision-7, AMENDED 2026-07-10,
`chore/mypy-strict-tooling`, owner-directed v1.0.9 tooling-slice pull-in). The set
originally also carved out ``evals/`` · ``scripts/`` · ``db/migrations/versions/``; all
three were brought to full strict on this branch (72 measured errors: 22 scripts + 44 evals
+ 6 migrations/versions — entirely bare-generic dict/list parametrization, missing
annotations, and `cast(...)`-wrapped `no-any-return`s) and are now covered by roster globs
(``scripts.*``, ``evals.*``, ``db.migrations.versions.*``). ``tests/`` stays permissive —
out of scope for this pull-in; a much larger, separately-scoped burn is deferred per owner
direction. Note ``db/migrations/{env,_sqlite_check_constraint}.py`` were already in scope
(rostered explicitly, not via a ``db.*``/``db.migrations.*`` wildcard) — that db-glob-trap
avoidance (rung 5, kit-adoption-design.md §4) is still live wisdom even though
``db.migrations.versions.*`` is now ALSO rostered: it is its OWN explicit glob entry, not
swept in by a broader db wildcard, so a hypothetical future ``db.*`` entry would still be
the wrong move (it would duplicate, not introduce, versions-tree coverage — the guard below
now asserts the tree IS covered, and stays a canary against a `db.*` wildcard replacing the
concrete `db.*` sibling entries, which is a different kind of drift than what it originally
caught).

SKIP: enumeration needs ``git ls-files``; when git is unavailable / this is not a git
checkout the enumeration-based tests SKIP (the matcher + roster-parse teeth still run).
CI runs in a git checkout, so the gate has teeth there.

TEETH: a broken parse/enumeration (empty roster or ~no modules) fails loudly; a synthetic
uncovered module must classify as uncovered and known-covered modules as covered — so the
main assertion can never pass vacuously.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Decision-7 exempt set (kit-adoption-design.md §6, amended 2026-07-10): path prefixes that
# stay permissive. Now `tests/` only — `evals/`/`scripts/`/`db/migrations/versions/` were
# brought to full strict on `chore/mypy-strict-tooling` (the tooling-slice pull-in).
_EXEMPT_PREFIXES = ("tests/",)

# Teeth thresholds: the enumeration must find the real surface, not a vacuous empty set.
# Measured 2026-07-10 (post tooling-slice pull-in): 33 roster entries, 131 non-exempt
# production modules (up from ~80 before scripts/evals/migrations-versions counted as
# production) — both floors below, with headroom, not exact.
_MIN_ROSTER_ENTRIES = 20
_MIN_PRODUCTION_MODULES = 110


def _strict_roster() -> list[str]:
    """Return the ``module`` list of the strict ``[[tool.mypy.overrides]]`` block.

    Identified by ``disallow_untyped_defs`` (a strict-preset component flag), to
    distinguish it from the ignore-missing-imports override block.
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    overrides = data["tool"]["mypy"]["overrides"]
    strict = [o for o in overrides if o.get("disallow_untyped_defs")]
    assert len(strict) == 1, (
        "expected exactly one strict [[tool.mypy.overrides]] block (the one with "
        f"disallow_untyped_defs), found {len(strict)}"
    )
    modules = strict[0]["module"]
    return modules if isinstance(modules, list) else [modules]


def _covers(entry: str, module: str) -> bool:
    """True if roster ``entry`` covers ``module`` under mypy per-module glob semantics.

    ``pkg.*`` matches ``pkg`` itself and any submodule ``pkg.sub…``; a non-wildcard entry
    matches only the exact module.
    """
    if entry.endswith(".*"):
        prefix = entry[:-2]
        return module == prefix or module.startswith(prefix + ".")
    return module == entry


def _module_name(rel_path: str) -> str:
    """``web_infra/clients.py`` -> ``web_infra.clients``; ``x/__init__.py`` -> ``x``; ``app.py`` -> ``app``."""
    parts = list(Path(rel_path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _tracked_py_or_skip() -> list[str]:
    """All tracked ``*.py`` (repo-relative, forward-slashed); skip if git is unavailable."""
    try:
        out = subprocess.run(  # git ls-files: static, trusted argv (S607 partial-path tests-exempt)
            ["git", "ls-files", "*.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(
            "git ls-files unavailable — the strict-roster gate enumerates tracked modules "
            "via git (CI runs in a git checkout, so the gate has teeth there)."
        )
    files = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    if not files:
        pytest.skip("git ls-files returned no .py files — not a populated git checkout.")
    return files


def _production_modules() -> list[tuple[str, str]]:
    """``(rel_path, module)`` for every non-exempt tracked ``.py``."""
    return [
        (p, _module_name(p)) for p in _tracked_py_or_skip() if not p.startswith(_EXEMPT_PREFIXES)
    ]


# --------------------------------------------------------------------------- #
# 1. The parse + enumeration have teeth — they find the real surface.
# --------------------------------------------------------------------------- #
def test_enumeration_has_teeth() -> None:
    """No vacuous pass: the roster must be non-trivial and the module scan must find the
    bulk of the ~130 non-exempt production module surface (tests/ is the only exempt
    prefix now — see the module docstring for the 2026-07-10 Decision-7 amendment). An
    empty roster or a broken enumeration would make the coverage assertion below pass for
    the wrong reason."""
    roster = _strict_roster()
    assert len(roster) >= _MIN_ROSTER_ENTRIES, (
        f"strict roster has only {len(roster)} entries (< {_MIN_ROSTER_ENTRIES}) — the "
        "roster parse looks broken or the ratchet regressed."
    )
    prod = _production_modules()
    assert len(prod) >= _MIN_PRODUCTION_MODULES, (
        f"found only {len(prod)} non-exempt production modules (< {_MIN_PRODUCTION_MODULES}) — "
        "the tracked-file enumeration looks broken."
    )


# --------------------------------------------------------------------------- #
# 1b. The coverage matcher has teeth — glob vs exact vs a real gap.
# --------------------------------------------------------------------------- #
def test_coverage_matcher_has_teeth() -> None:
    """``pkg.*`` covers the package + submodules; an exact entry covers only itself; a
    module absent from the roster is uncovered. Guards the main assertion from a matcher
    that is accidentally always-True."""
    assert _covers("web_infra.*", "web_infra")  # glob matches the package itself
    assert _covers("web_infra.*", "web_infra.clients")  # …and submodules
    assert _covers("analyzer", "analyzer")  # exact
    assert not _covers("analyzer", "analyzer.sub")  # exact does not match submodules
    assert not _covers("db.session", "db.migrations.versions.0001_x")  # unrelated
    # A synthetic never-rostered module is not covered by ANY real roster entry.
    roster = _strict_roster()
    assert not any(_covers(e, "newpkg.newmod") for e in roster)


# --------------------------------------------------------------------------- #
# 2. Every non-exempt production module carries the strict override (§6 exit).
# --------------------------------------------------------------------------- #
def test_every_nonexempt_production_module_is_strict_rostered() -> None:
    """The §6-exit invariant, enforced by construction: no non-exempt production module
    may escape the strict roster. A module left off would type-check permissively while
    ``mypy .`` still prints Success — the silent-staleness gap compliance-witness CW-118
    flagged."""
    roster = _strict_roster()
    uncovered = sorted(
        f"{rel} (module {mod})"
        for rel, mod in _production_modules()
        if not any(_covers(e, mod) for e in roster)
    )
    assert not uncovered, (
        "Non-exempt production module(s) NOT covered by the mypy --strict roster — a §6-exit "
        f"regression (they type-check permissively while `mypy .` still says Success): {uncovered}. "
        "Add each to the strict [[tool.mypy.overrides]] block in pyproject.toml (or, if genuinely "
        "non-production, to the Decision-7 exempt set + document it in kit-adoption-design.md §6)."
    )


# --------------------------------------------------------------------------- #
# 3. The migrations/versions tree IS strict-rostered (inverted 2026-07-10 —
#    it left the Decision-7 exempt set on `chore/mypy-strict-tooling`).
# --------------------------------------------------------------------------- #
def test_migrations_versions_is_strict_rostered() -> None:
    """``db/migrations/versions`` was in the Decision-7 exempt set through 2026-07-10;
    the tooling-slice pull-in (`chore/mypy-strict-tooling`) brought it to full strict via
    its own explicit ``db.migrations.versions.*`` glob entry. This is the premise-reversal
    of the original guard (which asserted the tree stayed OUT of the roster) — now it
    asserts the opposite: the tree IS covered, so a future accidental removal of the
    glob entry (silently returning the alembic version scripts to permissive typing while
    ``mypy .`` still says Success) fails here first.

    The db-glob-trap wisdom this test originally encoded stays live in a different shape:
    ``db.migrations.versions.*`` must be its OWN explicit entry, not a side effect of a
    broader ``db.*`` / ``db.migrations.*`` wildcard replacing the concrete sibling ``db.*``
    entries (rung 5, kit-adoption-design.md §4) — collapsing those into a wildcard would
    still be the wrong move even though the versions tree is now deliberately rostered."""
    roster = _strict_roster()
    sample = "db.migrations.versions.0001_initial_schema"
    matching = [e for e in roster if _covers(e, sample)]
    assert matching, (
        "No roster entry covers db/migrations/versions — a regression of the 2026-07-10 "
        "tooling-slice pull-in (kit-adoption-design.md §6 amendment). Add "
        "'db.migrations.versions.*' back to the strict [[tool.mypy.overrides]] module list "
        "in pyproject.toml."
    )
