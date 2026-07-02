"""Tests for the `sartor` CLI dispatch (`app.main` / `app._run_setup`).

Covers the argparse behavior added for packaging (feat/packaging-publish):
`--setup` runs the two bootstrap subprocesses and exits WITHOUT starting the
server; the default + `--host`/`--port` paths bind the right address; and
`--no-browser` opts out of the auto-open. The subprocesses + `app.run` are
monkeypatched — no Chromium download, no server, no browser.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

import app as app_module


def test_setup_runs_bootstrap_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(
        app_module.app, "run", lambda *a, **k: pytest.fail("server started on --setup")
    )

    with pytest.raises(SystemExit) as exc:
        app_module.main(["--setup"])
    assert exc.value.code == 0

    # Two steps, both run via THIS interpreter: playwright chromium, then the index.
    assert len(calls) == 2
    assert calls[0][:4] == [sys.executable, "-m", "playwright", "install"]
    assert calls[0][-1] == "chromium"
    assert calls[1] == [sys.executable, "-m", "scripts.build_vector_index"]


def test_setup_reports_failure_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", _boom)
    with pytest.raises(SystemExit) as exc:
        app_module.main(["--setup"])
    assert exc.value.code == 1  # non-zero when a step fails


def test_default_binds_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}
    monkeypatch.setattr(app_module.app, "run", lambda **k: seen.update(k))
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)
    app_module.main([])
    assert seen["host"] == "127.0.0.1"  # PX-19 loopback-only default preserved
    assert seen["port"] == 5000


def test_host_port_override(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}
    monkeypatch.setattr(app_module.app, "run", lambda **k: seen.update(k))
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)
    app_module.main(["--host", "0.0.0.0", "--port", "8080"])  # the container path
    assert seen["host"] == "0.0.0.0"
    assert seen["port"] == 8080


def test_no_browser_flag_passes_optout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(app_module.app, "run", lambda **k: None)

    def _spy(run_main, no_browser):
        captured["no_browser"] = no_browser
        return False

    monkeypatch.setattr(app_module, "_should_open_browser", _spy)
    app_module.main(["--no-browser"])
    assert captured["no_browser"] == "1"  # flag maps to the SARTOR_NO_BROWSER opt-out
