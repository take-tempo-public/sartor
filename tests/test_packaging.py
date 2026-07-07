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

from pathlib import Path

import tomllib

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
        # `Config.bundled_personas_dir` deliberately stays `base_dir`-relative (NOT
        # routed through `_package_dir`) — many existing tests fabricate an
        # isolated fake-bundled fixture under `Config(base_dir=tmp_path)` for test
        # isolation, and redirecting that through the packaged-data resolver would
        # send their writes onto the REAL, tracked `personas/bundled/` files
        # instead (found the hard way while building this fix). The wheel-install
        # case needs no code change here: the DEFAULT `base_dir` (`_PROJECT_ROOT`,
        # `config.py`'s own directory) is `site-packages/` in an installed wheel,
        # and `personas.bundled`'s package-data ships to `site-packages/personas/
        # bundled/` — the same place `base_dir`-relative arithmetic already looks.
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
