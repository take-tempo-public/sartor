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
from dataclasses import dataclass
from pathlib import Path

# The repo root. `config.py` is a top-level module (like `app.py`), so this is the
# same directory `app.py:BASE_DIR` resolves to — the production default. This
# remains the USER-WRITABLE data root (configs/resumes/output/db) — unchanged by
# the packaging fix below, and still overridable via `Config(base_dir=...)`.
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


@dataclass(frozen=True)
class Config:
    """Injected paths + flags for `create_app(config)`.

    The default instance mirrors today's production module globals byte-for-byte
    (`app.py:70-82`, `:2322-2323`). The derived directories are `@property`
    computations off `base_dir`, so a single `Config(base_dir=tmp_path)` re-points
    all seven roots — the isolation seam the test suite migrates onto (including
    `bundled_personas_dir`: many existing tests fabricate an isolated fake-bundled
    fixture under `tmp_path` and wire it in via `BUNDLED_PERSONAS_DIR`, so this
    stays `base_dir`-relative — see `bundled_personas_dir`'s own docstring for how
    the PyPI-wheel fix (`docs/dev/RELEASE_CHECKLIST.md`) still resolves correctly
    for the PRODUCTION default without touching this property at all).
    """

    base_dir: Path = _PROJECT_ROOT
    # PX-19: pin the bind to loopback by construction (mirror at `app.run(...)`).
    host: str = "127.0.0.1"
    allowed_extensions: frozenset[str] = frozenset({".docx", ".pdf", ".md"})

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

        Byte-identical to before the PyPI-wheel fix — DELIBERATELY still
        `self.personas_dir / "bundled"`, not `_package_dir("personas.bundled")`:
        many existing tests fabricate an isolated fake-bundled fixture under
        `Config(base_dir=tmp_path)` and rely on writing into this exact path (e.g.
        `tests/test_persona_routes.py`, `tests/test_default_template_resolver.py`)
        — routing this through the packaged-data resolver instead would have
        redirected those writes onto the REAL, tracked `personas/bundled/` files
        (found the hard way: it corrupted `classic.docx`/`classic.html`/etc. under
        test). The wheel-install fix needs NO code change here: `base_dir` defaults
        to `_PROJECT_ROOT` (`config.py`'s own directory), which in an installed
        wheel IS `site-packages/`, and `[tool.setuptools.package-data]` now ships
        `personas/bundled/*` as real files at `site-packages/personas/bundled/` —
        so the plain `base_dir`-relative computation already lands on the shipped
        content in production. See `pyproject.toml` `[tool.setuptools.package-data]`
        and `personas/bundled/__init__.py` (PyPI-wheel ledger item,
        `docs/dev/RELEASE_CHECKLIST.md`).
        """
        return self.personas_dir / "bundled"

    def ensure_dirs(self) -> None:
        """Create the directories the import-time loop made (app.py:85-86).

        Byte-identical to today: creates ONLY configs/resumes/output (with
        `exist_ok=True`). annotation_root / personas / bundled are deliberately
        NOT created here — they are made lazily by their writers, and creating
        them eagerly would be a behavior change the pure-refactor rule forbids.
        """
        for d in (self.configs_dir, self.resumes_dir, self.output_dir):
            d.mkdir(exist_ok=True)

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
        }
