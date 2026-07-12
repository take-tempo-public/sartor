"""Wheel-packaging regression pin (PyPI-wheel ledger item, `docs/dev/RELEASE_CHECKLIST.md`).

A full "does a real installed wheel serve a page" check needs a fresh venv + a
real `pip install <wheel>` — that stays a scripted verify (see the branch's
close-out report), not a pytest. What CAN be pinned as a fast, always-on unit
test is the set of *conditions* the fresh-venv verify depends on:

  * `create_app()` points Flask at ABSOLUTE, EXISTING template/static folders
    (not the implicit `Flask(__name__)` default, which only resolves correctly
    when `app.py` and `templates/`/`static/` happen to be co-located on disk —
    true in this dev checkout, false in a real non-editable wheel install).
  * The data-only packages introduced for the fix (`templates`, `static`,
    `personas.bundled`, `docs.wiki`) actually exist, are importable, and hold
    the files `[tool.setuptools.package-data]` in `pyproject.toml` promises to
    ship (F-26's `py-modules` roster gets the same treatment: a live diff
    against the repo's actual root-level `.py` modules).

These tests run from the source checkout (so they can't catch a *build-time*
packaging misconfiguration — only the real `python -m build` + fresh-venv
install can), but they DO pin the code-level contract the fix depends on, so a
future edit that reverts to `Flask(__name__)` or drops a `package-data` glob
fails fast in the normal test lane instead of silently re-breaking the wheel.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import platformdirs
import pytest

import config as config_module
from app import create_app
from config import STATIC_DIR, TEMPLATES_DIR, Config, _package_dir

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestFlaskFoldersAreAbsoluteAndExist:
    def test_template_folder_is_absolute_and_holds_index_html(self, tmp_path: Path) -> None:
        # An empty tmp_path base_dir mirrors the fresh-venv verify's shape (a
        # user-data root with nothing shipped alongside it) — template_folder
        # must resolve regardless.
        app = create_app(Config(base_dir=tmp_path))
        assert app.template_folder is not None
        template_folder = Path(app.template_folder)
        assert template_folder.is_absolute()
        assert (template_folder / "index.html").is_file()

    def test_static_folder_is_absolute_and_holds_app_js(self, tmp_path: Path) -> None:
        app = create_app(Config(base_dir=tmp_path))
        assert app.static_folder is not None
        static_folder = Path(app.static_folder)
        assert static_folder.is_absolute()
        assert (static_folder / "app.js").is_file()

    def test_folders_are_independent_of_base_dir(self, tmp_path: Path) -> None:
        # The packaging fix's whole point: an empty tmp base_dir (the fresh-venv
        # verify's shape) must not change where templates/static resolve.
        app_default = create_app(Config())
        app_tmp = create_app(Config(base_dir=tmp_path))
        assert app_default.template_folder == app_tmp.template_folder
        assert app_default.static_folder == app_tmp.static_folder

    def test_config_constants_match_flask_app_folders(self) -> None:
        app = create_app(Config())
        assert app.template_folder == str(TEMPLATES_DIR)
        assert app.static_folder == str(STATIC_DIR)


class TestPackageDirHelper:
    def test_resolves_templates(self) -> None:
        assert TEMPLATES_DIR.is_dir()
        assert (TEMPLATES_DIR / "index.html").is_file()

    def test_resolves_static(self) -> None:
        assert STATIC_DIR.is_dir()
        assert (STATIC_DIR / "app.js").is_file()
        assert (STATIC_DIR / "vendor" / "chart.umd.min.js").is_file()

    def test_resolves_bundled_personas(self) -> None:
        bundled = _package_dir("personas.bundled")
        assert bundled.is_dir()
        for name in ("classic", "modern", "spacious", "tech"):
            assert (bundled / f"{name}.html").is_file()
            assert (bundled / f"{name}.css").is_file()
            assert (bundled / f"{name}.docx").is_file()

    def test_default_config_bundled_personas_dir_matches_packaged_location(self) -> None:
        # `Config.bundled_personas_dir` routes the DEFAULT (unoverridden) `base_dir`
        # through `_package_dir`, not `base_dir`-relative arithmetic — an explicitly
        # overridden `base_dir` (e.g. `Config(base_dir=tmp_path)`, used by many
        # existing tests to fabricate an isolated fake-bundled fixture) still stays
        # `base_dir`-relative; only the default falls back to the packaged
        # location. Needed since `chore/packaging-floor`: the default `base_dir` no
        # longer always coincides with `_PROJECT_ROOT` (a real installed wheel's
        # default now redirects to the platform user-data dir via
        # `_default_base_dir()`), so the old "base_dir-relative already lands on
        # site-packages/personas/bundled/" coincidence no longer holds.
        assert Config().bundled_personas_dir == _package_dir("personas.bundled")

    def test_resolves_docs_wiki(self) -> None:
        wiki = _package_dir("docs.wiki")
        assert wiki.is_dir()
        assert (wiki / "index.md").is_file()
        assert (wiki / "SCHEMA.md").is_file()
        assert (wiki / "pages").is_dir()


class TestAssistantWikiDirMatchesPackageDir:
    def test_wiki_dir_resolves_via_import_not_relative_path_math(self) -> None:
        # Import lazily — importing blueprints.assistant at collection time would
        # pull in `anthropic` + the recall stack for every test run.
        from blueprints.assistant import _WIKI_DIR

        assert _package_dir("docs.wiki") == _WIKI_DIR
        assert _WIKI_DIR.is_absolute()
        assert (_WIKI_DIR / ".last_ingest_sha").exists()


class TestPyModulesRosterMatchesRepo:
    def test_py_modules_covers_every_root_level_module(self) -> None:
        """F-26 pin: `[tool.setuptools] py-modules` must list every root `.py`
        module the app ships — a future new root module that forgets to add
        itself here silently repeats the F-26 gap in the next wheel build."""
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        declared = set(pyproject["tool"]["setuptools"]["py-modules"])

        actual_root_modules = {p.stem for p in REPO_ROOT.glob("*.py")}
        assert actual_root_modules == declared, (
            f"pyproject.toml [tool.setuptools] py-modules drifted from the repo's actual "
            f"root-level .py files. Missing from py-modules: {actual_root_modules - declared}. "
            f"Stale entries (file no longer exists): {declared - actual_root_modules}."
        )


class TestSartorHomeDataDirRedirect:
    """B1 (`chore/packaging-floor`, Carry-forward ledger #2 residual (ii)):
    `Config.base_dir`'s default must not resolve into `site-packages/` on a
    real installed wheel — it redirects to a platform user-data dir
    (`platformdirs`), overridable by `SARTOR_HOME`. A real fresh-venv wheel
    install is the actual end-to-end proof (a scripted verify, not a pytest —
    see this file's own module docstring); these pin the code-level contract."""

    def test_sartor_home_env_always_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "sartor-data"
        monkeypatch.setenv("SARTOR_HOME", str(target))
        assert Config().base_dir == target.resolve()
        # Not the repo root / this module's own directory.
        assert Config().base_dir != config_module._PROJECT_ROOT

    def test_dev_checkout_default_is_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # This test suite itself runs from a dev checkout (pyproject.toml sits
        # right alongside config.py) — the packaging-floor fix must not move
        # the default for that case.
        monkeypatch.delenv("SARTOR_HOME", raising=False)
        assert config_module._is_dev_checkout() is True
        assert Config().base_dir == config_module._PROJECT_ROOT

    def test_installed_non_dev_checkout_redirects_to_platform_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulate a real non-editable wheel install (no pyproject.toml next to
        # config.py) without needing an actual fresh-venv install.
        monkeypatch.delenv("SARTOR_HOME", raising=False)
        monkeypatch.setattr(config_module, "_is_dev_checkout", lambda: False)
        expected = Path(platformdirs.user_data_dir("sartor", appauthor=False))
        assert config_module._default_base_dir() == expected
        assert Config().base_dir == expected
        # Never lands in this module's own (would-be site-packages) directory.
        assert Config().base_dir != config_module._PROJECT_ROOT

    def test_dashboard_project_root_shares_the_same_resolution(self) -> None:
        # `dashboard/routes.py`'s telemetry/eval-results root must resolve off
        # the same base as `Config.base_dir`, not an independent
        # `Path(__file__)`-relative computation (the other half of residual (ii)).
        from dashboard import routes as dashboard_routes

        assert config_module._default_base_dir() == dashboard_routes.PROJECT_ROOT


class TestPythonFloorClaim:
    def test_requires_python_is_311_plus(self) -> None:
        """PX-42: the declared floor must be >=3.11 (the code/tooling's real
        minimum — e.g. `tests/test_docstring_coverage_gate.py` uses `tomllib`,
        stdlib-only since 3.11 — and CI (`ci.yml`) only tests 3.11-3.13)."""
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        assert pyproject["project"]["requires-python"] == ">=3.11"
        classifiers = pyproject["project"]["classifiers"]
        assert not any("3.10" in c for c in classifiers), (
            f"a 3.10 classifier survives alongside the >=3.11 floor: {classifiers}"
        )
