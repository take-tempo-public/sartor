"""Shared AST import-root walker for the boundary-gate tests (PX-53).

`test_construction_boundary.py`, `test_recall_boundary.py`, and
`test_web_infra_is_leaf.py` each statically walk a module's *whole* AST (not
just module scope, so lazy / `TYPE_CHECKING` / in-function imports are caught
too) to collect the top-level root of every import, then diff that set
against a forbidden-roots set to enforce an architectural boundary by
construction, not by convention. The walk itself was duplicated near-verbatim
three times
(`docs/dev/reviews/2026-07-efficiency/findings/d-tests-ci.md` F-tci-02); this
module is the one shared implementation the three gates import.

The three call sites are byte-identical in behavior EXCEPT for how they
treat a relative import (``from . import x`` / ``from .foo import y``, i.e.
``node.level > 0``):

- `test_construction_boundary.py` and `test_web_infra_is_leaf.py` (verified
  byte-identical bodies) SKIP relative imports outright — a relative import
  can never resolve to an absolute forbidden root like ``analyzer`` or
  ``blueprints``, so there is nothing for those two gates to catch.
- `test_recall_boundary.py` needs to recognize `recall/`'s OWN
  self-referential relative imports (e.g. ``from .models import X`` inside
  `recall/foo.py`) as in-package rather than third-party, so
  `test_recall_imports_only_stdlib` can filter them back out. It resolves a
  relative import to a root instead of skipping it, falling back to the
  literal string ``"recall"`` when a bare ``from . import x`` leaves
  ``node.module`` as `None`.

Pass ``resolve_relative=True`` to reproduce that recall-only behavior
exactly; the default (`False`) reproduces the other two gates' skip
behavior. Do not change either behavior here — this module was extracted to
remove the duplication, not to change what any of the three gates enforce.
"""

from __future__ import annotations

import ast


def imported_roots(tree: ast.AST, *, resolve_relative: bool = False) -> set[str]:
    """Top-level module name for every import in `tree` (the whole tree, not
    just module scope), e.g. ``from collections.abc import X`` -> ``collections``,
    ``from recall.models import Y`` -> ``recall``, ``import re`` -> ``re``.

    Relative imports (``node.level > 0``) are skipped by default — they can
    never reach an absolute root outside the current package. Pass
    ``resolve_relative=True`` to instead resolve them to a local root
    (falling back to ``"recall"`` when a bare ``from . import x`` leaves the
    module name empty) — the behavior `test_recall_boundary.py` needs to
    recognize its own package's relative imports as in-package, not
    third-party.
    """
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if resolve_relative:
                    roots.add((node.module or "recall").split(".")[0] or "recall")
                continue
            roots.add((node.module or "").split(".")[0])
    return roots
