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

Both are committed red (`xfail(strict=True)`) as the first instrument (charter C-7): they record
what the code does today. Drive steps use `control`; only the invariant is a plain `assert`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="item 145 branch 1: writers resolve from the install dir, not SARTOR_HOME",
)
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


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="H1: a seeded bundled row is joined onto BASE_DIR, which has no personas/bundled",
)
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
