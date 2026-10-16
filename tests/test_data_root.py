"""One data root: every user-data writer honours `SARTOR_HOME` (item 145, branch 1).

Item 145's container contract is `-v sartor-data:/data -e SARTOR_HOME=/data`. Only
`config._default_base_dir()` read the variable; the SQLite DB, the LLM log, `.api_key` and the
onboarding CLI's paths resolved from the install directory, so that one mount lost them
(`docs/dev/blast-radius/data-root.md`).

**Two instruments, because the question has two shapes.**

* The module-level constants (`analyzer.LOG_PATH`, `db.session.DEFAULT_DB_PATH`, ...) are
  computed at import, and this suite's autouse fixtures already redirect two of them per test,
  so an in-process check would read the redirect, not the code. A fresh interpreter with
  `SARTOR_HOME` set *before* import is the only honest drive.
* The persona resolver reads `Config()` at call time, so it runs in-process on a copy of the
  migrated template DB (never the real `db/resume.sqlite`).

Both were committed red (`xfail(strict=True)`) as the first instrument (charter C-7), recording what
the code did before the fix; the dossier's `## Observed` holds that output. The path probe is now an
ordinary test. The persona arm stays red until the resolver is fixed. Drive steps use `control`;
only the invariant is a plain `assert`.

**The ratchet** (`TestNoUnclassifiedFileAnchoredPath`) is the mechanism for the recurrence: a
writer that anchors a path on its own file silently resolves from the install directory, which is
the site of the next lost-data bug. Charter C-11 asks for a gate, not a note.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests._controls import control

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Deliberately NOT key-shaped (same convention as `test_preflight.py`): it only tells us
#: *where* a key was read from, and is never compared by value outside the child.
_FAKE_KEY = "placeholder-credential-value"

#: Runs in a fresh interpreter. Prints one JSON object: a path string per site, or a bool for a
#: behavioural check. Nothing here writes a file or opens the real DB.
_PROBE = r"""
import json
from pathlib import Path

FAKE = {fake!r}
out = {{}}

import analyzer
out["analyzer.LOG_PATH"] = str(analyzer.LOG_PATH)

import db.session as session_mod
out["db.session.DEFAULT_DB_PATH"] = str(session_mod.DEFAULT_DB_PATH)

import preflight
out["preflight.api_key_path()"] = str(preflight.api_key_path())

from web_infra import clients
out["web_infra.clients reads the key from SARTOR_HOME"] = clients._get_client().api_key == FAKE

from onboarding import corpus_import
out["onboarding.corpus_import.CONFIGS_DIR"] = str(corpus_import.CONFIGS_DIR)
out["onboarding.corpus_import.OUTPUT_DIR"] = str(corpus_import.OUTPUT_DIR)
out["onboarding.corpus_import.RESUMES_DIR"] = str(corpus_import.RESUMES_DIR)
out["onboarding.corpus_import reads the key from SARTOR_HOME"] = (
    corpus_import._resolve_api_key(None) == FAKE
)

from evals import annotation, bootstrap
out["evals.annotation.ALLOWED_ROOT"] = str(annotation.ALLOWED_ROOT)
out["evals.bootstrap.ALLOWED_ROOT"] = str(bootstrap.ALLOWED_ROOT)

from evals import runner
out["evals.runner.LLM_LOG_PATH"] = str(runner.LLM_LOG_PATH)

from config import Config
out["Config().annotation_root"] = str(Config().annotation_root)

from dashboard import routes
out["dashboard reads the log analyzer writes"] = Path(routes.LLM_LOG) == Path(analyzer.LOG_PATH)

print(json.dumps(out))
"""


def _probe(home: Path) -> dict[str, object]:
    env = {k: v for k, v in os.environ.items() if k not in {"ANTHROPIC_API_KEY", "SARTOR_DEMO"}}
    env["SARTOR_HOME"] = str(home)
    proc = subprocess.run(  # noqa: S603 - sys.executable + a constant script, no shell
        [sys.executable, "-c", _PROBE.format(fake=_FAKE_KEY)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    control(proc.returncode == 0, f"probe exited {proc.returncode}: {proc.stderr[-1500:]}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("{")]
    control(len(lines) == 1, f"expected one JSON line, got {proc.stdout[-500:]!r}")
    parsed: dict[str, object] = json.loads(lines[0])
    return parsed


class TestSartorHome:
    """The helper itself: precedence, the platform directory, and the stdlib-only boundary."""

    def test_sartor_home_wins_and_is_expanded_and_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sartor_home

        monkeypatch.setenv("SARTOR_HOME", str(tmp_path / "a" / ".." / "data"))
        assert sartor_home.base_dir() == (tmp_path / "data").resolve()

    def test_a_dev_checkout_defaults_to_the_repo_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sartor_home

        monkeypatch.delenv("SARTOR_HOME", raising=False)
        assert sartor_home.is_dev_checkout() is True
        assert sartor_home.base_dir() == sartor_home.code_root() == REPO_ROOT

    def test_an_installed_wheel_defaults_to_the_platform_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sartor_home

        monkeypatch.delenv("SARTOR_HOME", raising=False)
        monkeypatch.setattr(sartor_home, "is_dev_checkout", lambda: False)
        assert sartor_home.base_dir() == sartor_home.platform_data_dir()

    def test_an_empty_sartor_home_is_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`-e SARTOR_HOME=` (set but empty) must not resolve to the current directory."""
        import sartor_home

        monkeypatch.setenv("SARTOR_HOME", "")
        assert sartor_home.base_dir() == REPO_ROOT

    def test_data_path_joins_under_the_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sartor_home

        monkeypatch.setenv("SARTOR_HOME", str(tmp_path))
        assert sartor_home.data_path() == tmp_path.resolve()
        assert (
            sartor_home.data_path("db", "resume.sqlite")
            == tmp_path.resolve() / "db" / "resume.sqlite"
        )

    def test_platform_data_dir_matches_platformdirs_on_this_os(self) -> None:
        import platformdirs

        import sartor_home

        expected = Path(platformdirs.user_data_dir("sartor", appauthor=False))
        assert sartor_home.platform_data_dir() == expected
        assert sartor_home.platform_data_dir("other") == Path(
            platformdirs.user_data_dir("other", appauthor=False)
        )

    @pytest.mark.parametrize(
        ("platform", "env", "expected_tail"),
        [
            ("win32", {"LOCALAPPDATA": "L:/Local"}, Path("L:/Local") / "sartor"),
            ("linux", {"XDG_DATA_HOME": "/x/share"}, Path("/x/share") / "sartor"),
            ("linux", {"XDG_DATA_HOME": "  "}, Path.home() / ".local" / "share" / "sartor"),
            ("darwin", {}, Path.home() / "Library" / "Application Support" / "sartor"),
        ],
    )
    def test_platform_data_dir_branches(
        self,
        monkeypatch: pytest.MonkeyPatch,
        platform: str,
        env: dict[str, str],
        expected_tail: Path,
    ) -> None:
        """The branches the host OS never takes, driven by patching the platform."""
        import sartor_home

        for name in ("LOCALAPPDATA", "XDG_DATA_HOME"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setattr(sys, "platform", platform)
        assert sartor_home.platform_data_dir() == expected_tail

    def test_it_imports_only_the_standard_library(self) -> None:
        """The launcher's core imports this module and must stay stdlib-only (item 145)."""
        import ast

        tree = ast.parse((REPO_ROOT / "sartor_home.py").read_text(encoding="utf-8"))
        roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level == 0
        }
        assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)


def test_every_user_data_writer_honours_sartor_home(tmp_path: Path) -> None:
    home = (tmp_path / "sartor-home").resolve()
    home.mkdir()
    (home / ".api_key").write_text(_FAKE_KEY + "\n", encoding="utf-8")
    observed = _probe(home)
    control(len(observed) >= 12, f"the probe reported too few sites: {sorted(observed)}")

    offenders: list[str] = []
    for site, value in observed.items():
        if isinstance(value, bool):
            if not value:
                offenders.append(f"{site}: False")
        elif not Path(str(value)).resolve().is_relative_to(home):
            offenders.append(f"{site}: {value}  (not under {home})")

    assert not offenders, "sites that ignore SARTOR_HOME:\n  " + "\n  ".join(offenders)


def test_a_bundled_template_resolves_when_sartor_home_redirects_the_base_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _migrated_template_db: Path
) -> None:
    from tests.conftest import _fresh_migrated_db

    home = (tmp_path / "home").resolve()
    home.mkdir()
    monkeypatch.setenv("SARTOR_HOME", str(home))
    db_file = _fresh_migrated_db(tmp_path, monkeypatch, _migrated_template_db, filename="h1.sqlite")

    import blueprints.templates as templates_mod
    from app import create_app
    from config import Config, _package_dir
    from db.session import init_db

    cfg = Config()
    control(cfg.base_dir == home, f"Config() base_dir {cfg.base_dir} is not SARTOR_HOME {home}")
    packaged = _package_dir("personas.bundled")
    control(cfg.bundled_personas_dir == packaged, "the default base dir must use the packaged dir")
    control((packaged / "classic.docx").is_file(), "the shipped classic.docx must exist")
    control(not (home / "personas" / "bundled").exists(), "the data root must start empty")
    app = create_app(cfg)
    control(init_db(db_file) is False, "the pre-registered copy must skip the alembic chain")

    with app.app_context():
        resolved = templates_mod._resolve_default_persona_template_path()

    assert resolved is not None, "the bundled default template did not resolve under SARTOR_HOME"
    assert Path(resolved).resolve().is_relative_to(packaged)


#: Every runtime module that anchors a path on its own file (`Path(__file__)`), and why that path is
#: CODE (shipped, read-only) and not user data. A new entry is a decision: if the path holds anything
#: the user owns, it belongs under `sartor_home.data_path(...)` instead. `scripts/**` is dev and CI
#: tooling that locates the checkout, and is out of scope (`docs/dev/blast-radius/data-root.md`).
_CODE_ANCHORS: dict[str, str] = {
    "sartor_home.py": "defines code_root()",
    "docx_to_persona_html.py": "reads the shipped personas/bundled/classic.html skeleton",
    "generator.py": "reads shipped personas/bundled/classic.html and personas/cover_letter.html",
    "preflight.py": "the recall-index probe default: the index is built from shipped source",
    "db/session.py": "alembic.ini is code; the DB path itself follows the data root",
    "blueprints/assistant.py": "the checkout-only git-grep tier and the index built from shipped source",
    "evals/runner.py": "sys.path bootstrap, and EVALS_DIR for the shipped fixtures and rubrics",
    "evals/annotation.py": "sys.path bootstrap so `python -m evals.annotation` resolves imports",
    "evals/bootstrap.py": "sys.path bootstrap so `python -m evals.bootstrap` resolves imports",
    "evals/corpus_drafting_probe.py": "sys.path bootstrap, and the shipped synthetic fixtures",
}

_RUNTIME_PACKAGES = (
    "blueprints",
    "dashboard",
    "db",
    "evals",
    "onboarding",
    "recall",
    "ui_pages",
    "web_infra",
)


def _file_anchored(root: Path) -> set[str]:
    """Repo-relative posix paths of runtime `.py` files that call `Path(__file__)`."""
    import ast

    candidates = list(root.glob("*.py"))
    for package in _RUNTIME_PACKAGES:
        candidates.extend((root / package).rglob("*.py"))
    found: set[str] = set()
    for path in candidates:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Path"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "__file__"
            ):
                found.add(path.relative_to(root).as_posix())
                break
    return found


class TestNoUnclassifiedFileAnchoredPath:
    def test_the_scan_sees_a_file_anchored_path(self, tmp_path: Path) -> None:
        """Control arm: the scan must be able to fail, or the test below proves nothing."""
        (tmp_path / "onboarding").mkdir()
        (tmp_path / "onboarding" / "new_writer.py").write_text(
            "from pathlib import Path\nLOG = Path(__file__).parent / 'logs'\n", encoding="utf-8"
        )
        (tmp_path / "clean.py").write_text("X = 1\n", encoding="utf-8")
        assert _file_anchored(tmp_path) == {"onboarding/new_writer.py"}

    def test_every_file_anchored_path_is_classified_as_code(self) -> None:
        found = _file_anchored(REPO_ROOT)
        unclassified = sorted(found - set(_CODE_ANCHORS))
        stale = sorted(set(_CODE_ANCHORS) - found)
        assert not unclassified, (
            f"a runtime file anchors a path on itself: {unclassified}. If it holds user data it must "
            f"use sartor_home.data_path(...) so SARTOR_HOME is honoured; if it is shipped code, "
            f"add it to _CODE_ANCHORS with the reason."
        )
        assert not stale, f"_CODE_ANCHORS names files that no longer anchor a path: {stale}"


class TestBundledPersonaUnderSartorHome:
    """H1's fix, beyond the resolver: the download route and the row-location helper.

    `SARTOR_HOME` makes `Config.base_dir` the default data root, so `bundled_personas_dir` is
    the packaged directory while the seeded rows still say `personas/bundled/<name>`.
    """

    @pytest.fixture
    def home_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _migrated_template_db: Path
    ) -> tuple[object, Path, Path]:
        from tests.conftest import _fresh_migrated_db

        home = (tmp_path / "home").resolve()
        home.mkdir()
        monkeypatch.setenv("SARTOR_HOME", str(home))
        db_file = _fresh_migrated_db(
            tmp_path, monkeypatch, _migrated_template_db, filename="bundled.sqlite"
        )

        from app import create_app
        from config import Config, _package_dir
        from db.session import init_db

        cfg = Config()
        control(cfg.base_dir == home, "Config() must follow SARTOR_HOME")
        app = create_app(cfg)
        control(init_db(db_file) is False, "the pre-registered copy must skip the alembic chain")
        return app, home, _package_dir("personas.bundled")

    def test_the_download_route_serves_a_bundled_persona(
        self, home_app: tuple[Any, Path, Path]
    ) -> None:
        from db.models import PersonaTemplate
        from db.session import get_session

        app, _home, packaged = home_app
        session = get_session()
        try:
            row = session.query(PersonaTemplate).filter_by(source="bundled").first()
            control(row is not None, "the migrated template must carry bundled rows")
            assert row is not None
            persona_id, stored = row.id, row.path
        finally:
            session.close()
        control(stored.startswith("personas/bundled/"), f"unexpected seeded path {stored!r}")

        response = app.test_client().get(f"/api/personas/{persona_id}/download")

        assert response.status_code == 200, response.get_data(as_text=True)
        assert response.data == (packaged / stored.removeprefix("personas/bundled/")).read_bytes()
        response.close()

    def test_a_user_named_bundled_keeps_their_upload_in_the_data_root(
        self, home_app: tuple[Any, Path, Path]
    ) -> None:
        """A candidate called "bundled" writes to `personas/bundled/`: the source decides, not the prefix."""
        from blueprints.templates import _persona_row_location

        app, home, _packaged = home_app
        with app.app_context():
            located, root = _persona_row_location("user_upload", "personas/bundled/mine.docx")
        assert located == home / "personas" / "bundled" / "mine.docx"
        assert root == home / "personas"

    def test_a_bundled_row_cannot_point_outside_the_shipped_directory(
        self, home_app: tuple[Any, Path, Path]
    ) -> None:
        from blueprints.templates import _persona_row_location
        from web_infra import _within

        app, _home, packaged = home_app
        with app.app_context():
            located, root = _persona_row_location("bundled", "personas/bundled/../../config.py")
        assert root == packaged
        assert not _within(located, root)

    def test_the_cover_letter_preview_finds_its_shipped_shell(
        self, home_app: tuple[Any, Path, Path]
    ) -> None:
        """`personas/cover_letter.html` is shipped, like the bundled personas.

        The preview route read it as `PERSONAS_DIR / "cover_letter.html"`, which is only the shipped
        file in a checkout. Under `SARTOR_HOME` (the container's `/data`) that directory is empty, and
        `render_cover_letter_html` raises `FileNotFoundError`.
        """
        from tests.test_live_preview_route import (
            _seed_candidate_app,
            _write_context_with_cover_letter,
        )

        app, home, _packaged = home_app
        (home / "configs" / "casey.config").write_text("{}", encoding="utf-8")
        _cid, application_id = _seed_candidate_app(app, username="casey")
        ctx = _write_context_with_cover_letter(
            home / "output" / "casey",
            application_id,
            "June 4, 2026\nHiring Manager\n\nDear Hiring Manager,\n\nI rebuilt three systems.\n\nSincerely,\nCasey",
        )
        control(
            not (home / "personas" / "cover_letter.html").exists(),
            "the data root must not contain a copy of the shell",
        )

        response = app.test_client().get(
            f"/api/applications/{application_id}/cover-letter-preview?context_path={ctx}"
        )

        assert response.status_code == 200, response.get_data(as_text=True)[:300]
        assert 'class="cover-letter"' in response.get_data(as_text=True)

    @pytest.mark.parametrize("doc_type", ["resume", "cover_letter"])
    def test_preview_edited_accepts_a_bundled_template_under_sartor_home(
        self, home_app: tuple[Any, Path, Path], doc_type: str
    ) -> None:
        """The route re-checks the resolver's path is inside `PERSONAS_DIR`; a bundled template is not.

        Under `SARTOR_HOME` the resolver (correctly, after H1) returns the packaged directory, which is
        outside `PERSONAS_DIR`, so the belt-and-suspenders containment check answered 404 for both
        document types. The cover-letter branch also reads the shipped shell (the second site).
        """
        from tests.test_live_preview_route import _seed_candidate_app

        app, home, _packaged = home_app
        (home / "configs" / "casey.config").write_text("{}", encoding="utf-8")
        _cid, application_id = _seed_candidate_app(app, username="casey")

        response = app.test_client().post(
            f"/api/applications/{application_id}/preview-edited",
            json={"content": "Dear Hiring Manager,\n\nI rebuilt three systems.", "type": doc_type},
        )

        assert response.status_code == 200, response.get_data(as_text=True)[:300]
        assert "html" in response.get_json()


class TestImageShipsItsFiles:
    """`.dockerignore` must not silently drop a shipped file (item 145 dossier O11).

    `personas/*/` is read as `personas/*` (a trailing slash is stripped from ignore patterns), so it
    also excluded `personas/cover_letter.html`, a FILE; the image shipped without it and the
    cover-letter preview returned 500. Observed by building the image, not by any test.
    """

    @staticmethod
    def _rules() -> list[str]:
        text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]

    def test_every_tracked_file_directly_under_personas_is_re_included(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "personas"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        direct_files = sorted(p for p in tracked if p.count("/") == 1)
        control(direct_files != [], "git ls-files found no file directly under personas/")
        rules = self._rules()
        broad = rules.index("personas/*/")
        for path in direct_files:
            assert f"!{path}" in rules[broad:], (
                f"{path} is shipped code but .dockerignore's `personas/*/` also excludes it. "
                f"Add `!{path}` after that line, or the image will lack it."
            )

    def test_the_bundled_folder_is_still_re_included_after_the_broad_rule(self) -> None:
        rules = self._rules()
        assert "!personas/bundled/" in rules[rules.index("personas/*/") :]
