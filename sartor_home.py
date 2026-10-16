"""Where Sartor keeps the user's data: one root, one resolution (item 145, branch 1).

A leaf module: stdlib only, no Sartor imports, so `config.py`, `preflight.py`, `analyzer.py`,
`db/session.py` and the item-145 launcher can all use it without a cycle or a heavy import.

**The root.** `base_dir()` is the one directory that holds everything the user owns: the
SQLite DB, the LLM log, `.api_key`, `configs/`, `resumes/`, `output/`, `personas/`, the instance
file. Precedence, highest first:

1. `SARTOR_HOME`, if set (the container sets it to its `/data` volume).
2. A dev or editable checkout (a `pyproject.toml` beside this file): the repo root, unchanged.
3. Otherwise a real installed wheel: the per-user platform data directory.

**Code is not data.** `code_root()` is where this file lives (the repo root in a checkout,
`site-packages/` in a wheel). Shipped, read-only content (templates, static files, bundled
personas, `alembic.ini`, the vector index built from shipped source) resolves from there or
through its own package, never from `base_dir()`.

**Why not `platformdirs` here.** The launcher's core must import only the stdlib, and it needs
this module. `platform_data_dir` reimplements the one call Sartor makes;
`tests/test_data_root.py` pins it against `platformdirs` so the two cannot drift.

Every function reads the environment when called and holds no state, so a test or a parent
process that changes `SARTOR_HOME` is believed. Module-level constants elsewhere that call
`data_path` fix their value at import, which is what a container wants (the variable is set
before the process starts) and what the existing `monkeypatch.setattr(<module>, "LOG_PATH", ...)`
test seams expect.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

#: The environment variable that overrides the data root. Read here and nowhere else.
ENV_HOME: Final = "SARTOR_HOME"

_CODE_ROOT: Final = Path(__file__).resolve().parent


def code_root() -> Path:
    """The directory this install's code lives in: the repo root, or `site-packages/`."""
    return _CODE_ROOT


def is_dev_checkout() -> bool:
    """True for a source checkout (a plain clone or `pip install -e .`).

    `pyproject.toml` ships in the repo and the sdist but deliberately not in the wheel, so a real
    non-editable install drops this module into `site-packages/` with none beside it. A cheap,
    dependency-free test; no need to ask `importlib.metadata` whether the install is editable.
    """
    return (_CODE_ROOT / "pyproject.toml").is_file()


def platform_data_dir(app: str = "sartor") -> Path:
    r"""The per-user data directory for `app`, without `platformdirs`.

    Matches `platformdirs.user_data_dir(app, appauthor=False)`: `%LOCALAPPDATA%\<app>` on
    Windows, `~/Library/Application Support/<app>` on macOS, `$XDG_DATA_HOME/<app>` (else
    `~/.local/share/<app>`) elsewhere. Only computes a path; it creates nothing.
    """
    # A variable, not `sys.platform` in the comparison: mypy narrows a direct comparison to the
    # host OS and would flag the other branches unreachable (CI runs on all three), and the
    # branch tests patch `sys.platform` at call time.
    platform: str = sys.platform
    if platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        return Path(local) / app if local else Path.home() / "AppData" / "Local" / app
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return Path(xdg) / app if xdg else Path.home() / ".local" / "share" / app


def base_dir() -> Path:
    """The user-writable data root. See the module docstring for the precedence."""
    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser().resolve()
    if is_dev_checkout():
        return _CODE_ROOT
    return platform_data_dir()


def data_path(*parts: str) -> Path:
    """`base_dir()` joined with `parts`: the one way to name a file or directory of user data."""
    return base_dir().joinpath(*parts)
