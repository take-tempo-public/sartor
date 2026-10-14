"""A strict xfail must be able to fail only at its invariant (item 167).

**The failure class** (`docs/dev/diagnosis/recurrence-guardrails.md` O5,
`docs/dev/handoffs/regenerate-keeps-cover-letter.md` Recurrence 4). An
`xfail(strict=True)` arm with bare-`assert` controls reads a broken drive as the expected
defect, because the setup's `AssertionError` is what pytest was told to expect. The arm then
"confirms" a defect it never reached. `strict` catches only the opposite mistake.

**The convention** (`tests/_controls.py`): drive steps and controls raise `ControlFailed`; the
marker carries `raises=AssertionError`, so a `ControlFailed` is a real failure.

**What this gate enforces** (all three are deterministic, AST-level):

1. every `xfail(...)` that is strict, by keyword or by the project's `xfail_strict`, carries
   `raises=` naming `AssertionError`, and never `Exception`, `BaseException` or
   `ControlFailed` (any of those would match the very step failures the convention separates);
2. a module holding such a marker imports `control`/`ControlFailed` from `tests._controls`;
3. `ControlFailed` is defined exactly once, in `tests/_controls.py`.

**Declared limits (C-0)**, stated rather than papered over:

* It cannot see whether a given step uses `control` or a bare `assert`: that needs a call graph
  through each arm's drive helpers. Rule 2 is a proxy (the module *has* the tool).
* Non-strict `xfail` is out of scope. Two exist, deliberately, with the reason in each
  marker (`tests/ux/regression/test_20260708_busy_states_and_chip.py`); they are negative-space
  evidence that must be allowed to xpass, not a defect pin.
* The imperative `pytest.xfail(...)` call and `xfail` set from a variable are not parsed.
"""

from __future__ import annotations

import ast
import os
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_SELF = Path(__file__).resolve()
_CONTROLS_REL = "tests/_controls.py"

_PRUNE_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "docs-site",
        "__pycache__",
        "build",
        "dist",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

#: Exception names that, as `raises=`, would also match a failed drive step or control.
_TOO_BROAD = frozenset({"Exception", "BaseException", "ControlFailed"})


def _iter_py_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield Path(dirpath) / name


def _is_mark_xfail(call: ast.Call) -> bool:
    """`pytest.mark.xfail(...)`, `mark.xfail(...)`; not the imperative `pytest.xfail(...)`."""
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "xfail":
        return False
    owner = func.value
    if isinstance(owner, ast.Attribute):
        return owner.attr == "mark"
    return isinstance(owner, ast.Name) and owner.id == "mark"


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _names(node: ast.expr) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple | ast.List):
        out: set[str] = set()
        for element in node.elts:
            out |= _names(element)
        return out
    return set()


def _imports_controls(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests._controls"
            and {alias.name for alias in node.names} & {"control", "ControlFailed"}
        ):
            return True
    return False


def scan_source(rel: str, source: str, *, strict_default: bool = False) -> list[str]:
    """Violations in one module's source; each is a human-readable line naming the site."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    problems: list[str] = []
    has_strict = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ControlFailed":
            if rel != _CONTROLS_REL:
                problems.append(
                    f"{rel}:{node.lineno}: defines its own ControlFailed; "
                    "import it from tests._controls"
                )
            continue
        if not isinstance(node, ast.Call) or not _is_mark_xfail(node):
            continue
        strict_node = _kw(node, "strict")
        if isinstance(strict_node, ast.Constant):
            strict = bool(strict_node.value)
        elif strict_node is None:
            strict = strict_default
        else:
            strict = True  # not statically known: assume the stricter reading
        if not strict:
            continue
        has_strict = True
        raises = _kw(node, "raises")
        if raises is None:
            problems.append(
                f"{rel}:{node.lineno}: strict xfail without raises=AssertionError; a broken "
                "drive would read as the expected defect"
            )
            continue
        names = _names(raises)
        if "AssertionError" not in names or names & _TOO_BROAD:
            problems.append(
                f"{rel}:{node.lineno}: strict xfail raises={sorted(names) or '<dynamic>'}; "
                "it must name AssertionError and not Exception/BaseException/ControlFailed"
            )
    if has_strict and rel != _CONTROLS_REL and not _imports_controls(tree):
        problems.append(
            f"{rel}: holds a strict xfail but does not import control/ControlFailed from "
            "tests._controls, so its controls are bare asserts"
        )
    return problems


def _strict_default() -> bool:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    return str(options.get("xfail_strict", "false")).lower() == "true"


def _scan_repo() -> list[str]:
    strict_default = _strict_default()
    problems: list[str] = []
    for path in _iter_py_files(REPO_ROOT / "tests"):
        if path.resolve() == _SELF:
            continue
        raw = path.read_bytes()
        if b"xfail" not in raw and b"ControlFailed" not in raw:
            continue  # cheap prefilter: parse only the files that can matter
        rel = path.relative_to(REPO_ROOT).as_posix()
        problems.extend(
            scan_source(rel, raw.decode("utf-8", errors="replace"), strict_default=strict_default)
        )
    return problems


class TestScannerCatchesEachShape:
    """A gate never shown to reject a bad input is not evidence (the repo's own standard)."""

    def test_strict_without_raises_is_flagged(self) -> None:
        src = "import pytest\n@pytest.mark.xfail(strict=True, reason='x')\ndef test_a(): ...\n"
        assert len(scan_source("tests/test_x.py", src)) == 2  # no raises + no controls import

    def test_strict_with_assertion_error_and_controls_is_clean(self) -> None:
        src = (
            "import pytest\n"
            "from tests._controls import control\n"
            "@pytest.mark.xfail(strict=True, raises=AssertionError, reason='x')\n"
            "def test_a(): ...\n"
        )
        assert scan_source("tests/test_x.py", src) == []

    @pytest.mark.parametrize(
        "raises",
        [
            "Exception",
            "BaseException",
            "ControlFailed",
            "(AssertionError, Exception)",
            "ValueError",
        ],
    )
    def test_a_raises_that_would_match_a_failed_step_is_flagged(self, raises: str) -> None:
        src = (
            "import pytest\n"
            "from tests._controls import control\n"
            f"@pytest.mark.xfail(strict=True, raises={raises}, reason='x')\n"
            "def test_a(): ...\n"
        )
        assert scan_source("tests/test_x.py", src), f"raises={raises} was not flagged"

    def test_non_strict_is_out_of_scope(self) -> None:
        src = "import pytest\n@pytest.mark.xfail(reason='x', strict=False)\ndef test_a(): ...\n"
        assert scan_source("tests/test_x.py", src) == []

    def test_a_param_mark_is_scanned(self) -> None:
        src = (
            "import pytest\nP = pytest.param(1, marks=pytest.mark.xfail(strict=True, reason='x'))\n"
        )
        assert scan_source("tests/test_x.py", src)

    def test_the_project_default_strict_makes_a_bare_xfail_strict(self) -> None:
        src = "import pytest\n@pytest.mark.xfail(reason='x')\ndef test_a(): ...\n"
        assert scan_source("tests/test_x.py", src) == []
        assert scan_source("tests/test_x.py", src, strict_default=True)

    def test_the_imperative_pytest_xfail_is_not_a_marker(self) -> None:
        src = "import pytest\ndef test_a():\n    pytest.xfail('known')\n"
        assert scan_source("tests/test_x.py", src, strict_default=True) == []

    def test_a_second_controlfailed_definition_is_flagged(self) -> None:
        src = "class ControlFailed(Exception): ...\n"
        assert scan_source("tests/test_other.py", src)
        assert scan_source("tests/_controls.py", src) == []


class TestTheRepo:
    def test_no_strict_xfail_can_mask_a_broken_drive(self) -> None:
        problems = _scan_repo()
        assert problems == [], "\n".join(problems)

    def test_controlfailed_is_defined_in_the_shared_module(self) -> None:
        source = (REPO_ROOT / _CONTROLS_REL).read_text(encoding="utf-8")
        assert "class ControlFailed(Exception)" in source
