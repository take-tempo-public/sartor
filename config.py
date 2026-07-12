"""Typed application configuration — the injected paths/flags for the factory.

Sprint 8.3a (the `app.py` -> blueprints decomposition foundation). This replaces
the eight module-global path constants + `ALLOWED_EXTENSIONS` + the bind host that
`app.py` carried at import time, and that ~29 test files reached into via
`monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp)`. A single typed `Config`,
constructed once and injected into `create_app(config)`, ends that
monkeypatch-the-global smell: tests build `Config(base_dir=tmp_path)` and every
derived directory re-points off the one `base_dir`.

`Config` lives top-level (not inside `web_infra/`) so it stays importable by the
composition root (`app.py`), the test fixtures (`tests/conftest.py`), and the
`onboarding.corpus_import` call sites without dragging in `web_infra/`'s
Flask-context helpers — `web_infra/` is a pure leaf and never imports this module
(it reads `current_app.config[...]` dicts or takes explicit args instead).

P1 Hardening boundary: this module is deterministic — no LLM calls (charter C-6).
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

from demo_fixtures import is_demo_mode

# The repo root. `config.py` is a top-level module (like `app.py`), so this is the
# same directory `app.py:BASE_DIR` resolves to. This is the production default
# ONLY in a dev/editable checkout — see `_default_base_dir()` below for the
# installed (non-editable wheel) case, where this resolves to `site-packages/`
# instead and is deliberately NOT used as the user-data root. Still overridable
# directly via `Config(base_dir=...)`.
_PROJECT_ROOT = Path(__file__).resolve().parent


def _package_dir(dotted_name: str) -> Path:
    """Resolve a shipped, READ-ONLY data package's directory.

    `templates/`, `static/`, and `personas/bundled/` ship as tiny data-only
    Python packages (an `__init__.py` marker + `[tool.setuptools.package-data]`
    globs in `pyproject.toml`) purely so this import-based lookup resolves
    correctly under BOTH `pip install -e .` (import machinery points at THIS
    source tree — byte-identical to the historical `_PROJECT_ROOT`-relative
    computation) AND a real non-editable wheel install (`site-packages/<name>/`),
    where the old `Path(__file__)`-relative computation 404'd (PyPI-wheel ledger
    item, `docs/dev/RELEASE_CHECKLIST.md`). Deliberately independent of
    `base_dir` — these directories are read-only shipped content, not the
    user-writable runtime data root.
    """
    module_file = importlib.import_module(dotted_name).__file__
    if module_file is None:
        # Only happens for namespace packages / frozen / built-in modules — never
        # true for these real, `__init__.py`-backed, filesystem data packages.
        raise RuntimeError(f"package {dotted_name!r} has no __file__ (not a filesystem package)")
    return Path(module_file).resolve().parent


# Absolute, install-mode-independent locations for the Flask app shell's own
# template/static folders (passed explicitly to `Flask(__name__, ...)` in
# `app.py` instead of relying on the implicit `Flask(__name__)` default, which
# only worked when `app.py` and `templates/`/`static/` were co-located on disk —
# true for a source checkout / editable install, false for a real wheel install).
TEMPLATES_DIR = _package_dir("templates")
STATIC_DIR = _package_dir("static")


def _is_dev_checkout() -> bool:
    """True when this is a source checkout (a plain git clone or `pip install -e .`).

    `pyproject.toml` ships in the repo/sdist but is deliberately NOT part of the
    wheel's `[tool.setuptools.package-data]` (it describes the build, it isn't
    runtime data) — so a real non-editable `pip install` drops `config.py` into
    `site-packages/` with no `pyproject.toml` alongside it, while an editable
    install or a plain clone resolves `config.py`'s `__file__` back to the real
    repo root, where `pyproject.toml` always sits next to it. Cheap, dependency-free
    heuristic — no need to shell out to `importlib.metadata` to distinguish
    editable vs. wheel installs.
    """
    return (_PROJECT_ROOT / "pyproject.toml").is_file()


def _default_base_dir() -> Path:
    r"""Resolve the default user-writable data root (configs/resumes/output/db).

    Packaging-floor fix (owner decision 8; Carry-forward ledger #2 residual
    (ii)): on a bare `pip install sartor && sartor` (non-editable wheel),
    `_PROJECT_ROOT` resolves to `site-packages/`, so user data would land there
    instead of a proper per-user data directory. Precedence:

    1. `SARTOR_HOME` env var, if set — always wins, dev checkout or not (an
       explicit escape hatch for anyone who wants a non-default data root).
    2. Dev/editable checkout (`_is_dev_checkout()`) — keep today's behavior,
       the repo root (`_PROJECT_ROOT`), unchanged.
    3. Otherwise (a real installed wheel) — the platform user-data directory
       via `platformdirs` (`%LOCALAPPDATA%\\sartor` on Windows, `~/.local/share/sartor`
       on Linux, `~/Library/Application Support/sartor` on macOS).

    Read via `field(default_factory=...)` on `Config.base_dir` (like
    `demo_mode` below) so each `Config()` construction re-reads the env var —
    not frozen at module-import time.
    """
    override = os.environ.get("SARTOR_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if _is_dev_checkout():
        return _PROJECT_ROOT
    return Path(platformdirs.user_data_dir("sartor", appauthor=False))


@dataclass(frozen=True)
class Config:
    """Injected paths + flags for `create_app(config)`.

    The default instance mirrors today's production module globals byte-for-byte
    (`app.py:70-82`, `:2322-2323`). The derived directories are `@property`
    computations off `base_dir`, so a single `Config(base_dir=tmp_path)` re-points
    all seven roots — the isolation seam the test suite migrates onto (including
    `bundled_personas_dir`: many existing tests fabricate an isolated fake-bundled
    fixture under `tmp_path` and wire it in via `BUNDLED_PERSONAS_DIR`, so an
    EXPLICITLY overridden `base_dir` keeps this `base_dir`-relative — see
    `bundled_personas_dir`'s own docstring for how the DEFAULT `base_dir` instead
    routes through the packaged-data resolver, which is what keeps the PyPI-wheel
    fix (`docs/dev/RELEASE_CHECKLIST.md`) correct now that the packaging-floor fix
    (`SARTOR_HOME` / `platformdirs`) redirects an installed wheel's default
    `base_dir` away from `site-packages/`).
    """

    base_dir: Path = field(default_factory=_default_base_dir)
    # PX-19: pin the bind to loopback by construction (mirror at `app.run(...)`).
    host: str = "127.0.0.1"
    allowed_extensions: frozenset[str] = frozenset({".docx", ".pdf", ".md"})
    # F-19 offline/demo mode. Defaults from the `SARTOR_DEMO=1` env var (the
    # single source of truth `demo_fixtures.is_demo_mode()` also reads directly
    # for analyzer.py, which must work outside a Flask request context) so a
    # bare `Config()` — including the module-level `app = create_app()` in
    # `app.py` — picks it up with no extra wiring. A test that wants demo mode
    # OFF regardless of the environment can still pass `Config(demo_mode=False)`
    # explicitly; the default only reads the env var.
    demo_mode: bool = field(default_factory=is_demo_mode)

    # --- Derived roots (mirror the app.py module globals exactly) ---
    @property
    def configs_dir(self) -> Path:
        """The per-user config directory (`<base>/configs`)."""
        return self.base_dir / "configs"

    @property
    def resumes_dir(self) -> Path:
        """The uploaded-résumé directory (`<base>/resumes`)."""
        return self.base_dir / "resumes"

    @property
    def output_dir(self) -> Path:
        """The generated-artifact directory (`<base>/output`)."""
        return self.base_dir / "output"

    @property
    def annotation_root(self) -> Path:
        """The annotation/bootstrap write surface (`<base>/evals/fixtures/real`)."""
        # The only directory the annotation/bootstrap write surface touches; equal
        # to evals.annotation.ALLOWED_ROOT / evals.bootstrap.ALLOWED_ROOT. Created
        # lazily by its writers today (NOT by ensure_dirs) — see app.py:75-80.
        return self.base_dir / "evals" / "fixtures" / "real"

    @property
    def personas_dir(self) -> Path:
        """The persona/template directory (`<base>/personas`)."""
        return self.base_dir / "personas"

    @property
    def bundled_personas_dir(self) -> Path:
        """The shipped default-persona directory (`<personas>/bundled`).

        An EXPLICITLY overridden `base_dir` (`self.base_dir != _default_base_dir()`)
        stays `self.personas_dir / "bundled"`, unchanged: many existing tests
        fabricate an isolated fake-bundled fixture under `Config(base_dir=tmp_path)`
        and rely on writing into this exact path (e.g. `tests/test_persona_routes.py`,
        `tests/test_default_template_resolver.py`) — routing that through the
        packaged-data resolver would redirect those writes onto the REAL, tracked
        `personas/bundled/` files (found the hard way: it corrupted
        `classic.docx`/`classic.html`/etc. under test).

        The DEFAULT (unoverridden) `base_dir` instead resolves via
        `_package_dir("personas.bundled")` — the import-based packaged-data
        resolver, correct under both a dev/editable checkout (byte-identical to
        the old `base_dir`-relative computation, since `_PROJECT_ROOT` there IS
        the repo root `personas.bundled` also resolves from) and a real
        installed wheel. Needed because the packaging-floor fix
        (`_default_base_dir()`: `SARTOR_HOME` / `platformdirs`) now points a
        real installed wheel's default `base_dir` at the platform user-data
        root, which does NOT contain the shipped bundled templates — those
        ship only under `site-packages/personas/bundled/`
        (`[tool.setuptools.package-data]`), never copied into user data. Before
        that fix, `base_dir` defaulted to `_PROJECT_ROOT`, which in an
        installed wheel WAS `site-packages/` itself, so the plain
        `base_dir`-relative computation coincidentally landed on the shipped
        content — this branch keeps that outcome true now that the
        coincidence no longer holds. See `pyproject.toml`
        `[tool.setuptools.package-data]` and `personas/bundled/__init__.py`
        (PyPI-wheel ledger item, `docs/dev/RELEASE_CHECKLIST.md`).
        """
        if self.base_dir == _default_base_dir():
            return _package_dir("personas.bundled")
        return self.personas_dir / "bundled"

    def ensure_dirs(self) -> None:
        """Create the directories the import-time loop made (app.py:85-86).

        Creates ONLY configs/resumes/output (with `exist_ok=True`).
        annotation_root / personas / bundled are deliberately NOT created here
        — they are made lazily by their writers, and creating them eagerly
        would be a behavior change the pure-refactor rule forbids.
        `parents=True` (new alongside the packaging-floor fix): a fresh
        installed-wheel run's platform user-data directory (`_default_base_dir()`)
        may not exist yet at all, unlike the dev-checkout repo root, which
        always does — a plain `exist_ok=True` mkdir of `<base>/configs` would
        raise `FileNotFoundError` if `<base>` itself is missing.
        """
        for d in (self.configs_dir, self.resumes_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

    def as_flask_config(self) -> dict[str, object]:
        """UPPERCASE keys for `app.config.update(...)`.

        Key names match the legacy `app.py` module-global names so each seam
        branch (8.3b-h) can migrate a route from `CONFIGS_DIR` (the import-bound
        global) to `current_app.config["CONFIGS_DIR"]` as a mechanical swap.
        """
        return {
            "BASE_DIR": self.base_dir,
            "CONFIGS_DIR": self.configs_dir,
            "RESUMES_DIR": self.resumes_dir,
            "OUTPUT_DIR": self.output_dir,
            "ANNOTATION_ROOT": self.annotation_root,
            "PERSONAS_DIR": self.personas_dir,
            "BUNDLED_PERSONAS_DIR": self.bundled_personas_dir,
            "ALLOWED_EXTENSIONS": self.allowed_extensions,
            "HOST": self.host,
            "DEMO_MODE": self.demo_mode,
        }
