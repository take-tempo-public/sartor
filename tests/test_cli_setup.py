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
from pathlib import Path

import pytest

import app as app_module
import instance


@pytest.fixture(autouse=True)
def _isolated_instance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Keep `main()` off the real machine (items 146/147).

    Without this, the callers that reach `app.run` would probe the developer's real
    `:5000` — a dev server running there would turn them into "already running, exit 0" —
    and would write `sartor-instance.json` into the real checkout. Probe → free, data root →
    `tmp_path`, `WERKZEUG_RUN_MAIN` cleared, and the keys `main()` leaves on the
    module-level app removed afterwards.
    """
    monkeypatch.setitem(app_module.app.config, "BASE_DIR", tmp_path)
    monkeypatch.setenv(instance.ENV_INSTANCE_ID, "pre-existing")  # restored at teardown
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    monkeypatch.setattr(instance, "probe", lambda port, timeout=1.0: instance.Probe("free"))
    yield
    for key in ("INSTANCE_ID", "SHUTDOWN_FN", "IDLE_TRACKER"):
        app_module.app.config.pop(key, None)


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


# ---------------------------------------------------------------- items 146/147: single instance


def _never_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module.app, "run", lambda **k: pytest.fail("a server was started"))


def test_a_running_sartor_is_reused_not_duplicated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        instance, "probe", lambda port, timeout=1.0: instance.Probe("sartor", {"app": "sartor"})
    )
    _never_serve(monkeypatch)
    opened: list[str] = []
    monkeypatch.setattr(app_module.webbrowser, "open", lambda url, *a, **k: opened.append(url))
    monkeypatch.delenv("SARTOR_NO_BROWSER", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(app_module, "_is_ci_or_container", lambda: False)

    with pytest.raises(SystemExit) as exc:
        app_module.main(["--port", "5123"])

    assert exc.value.code == 0
    assert opened == ["http://localhost:5123"]  # the browser lands on the copy that is up
    assert "already running" in capsys.readouterr().out
    assert not (tmp_path / instance.INSTANCE_FILE).exists()  # it must not claim the file


def test_a_running_sartor_with_no_browser_flag_exits_zero_without_opening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        instance, "probe", lambda port, timeout=1.0: instance.Probe("sartor", {"app": "sartor"})
    )
    _never_serve(monkeypatch)
    opened: list[str] = []
    monkeypatch.setattr(app_module.webbrowser, "open", lambda url, *a, **k: opened.append(url))

    with pytest.raises(SystemExit) as exc:
        app_module.main(["--no-browser"])

    assert exc.value.code == 0
    assert opened == []


def test_a_foreign_owner_exits_one_naming_the_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(instance, "probe", lambda port, timeout=1.0: instance.Probe("foreign"))
    _never_serve(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        app_module.main(["--port", "5123"])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Port 5123 is in use by another program" in err
    assert "--port 5124" in err  # a suggestion, not a silent fallback
    assert not (tmp_path / instance.INSTANCE_FILE).exists()


def test_a_free_port_writes_the_instance_file_and_registers_its_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    served: dict = {}
    monkeypatch.setattr(app_module.app, "run", lambda **k: served.update(k))
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)
    registered: list[tuple] = []
    monkeypatch.setattr(app_module.atexit, "register", lambda fn, *a: registered.append((fn, a)))

    app_module.main(["--port", "5123"])

    info = instance.read_instance_file(tmp_path)
    assert info is not None
    assert (info["app"], info["port"]) == ("sartor", 5123)
    new_id = app_module.app.config["INSTANCE_ID"]
    assert info["instance_id"] == new_id != "pre-existing"
    # exported for the reloader's serving child, which re-runs main() with this env
    assert app_module.os.environ[instance.ENV_INSTANCE_ID] == new_id
    assert registered == [(instance.release_instance_file, (tmp_path, new_id))]
    assert served["port"] == 5123


def test_the_reload_child_neither_probes_nor_claims_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Under the reloader main() re-runs in the serving child; the supervisor's listening
    socket is already on the port, so a probe there would call it foreign (dossier)."""

    def _boom(port: int, timeout: float = 1.0) -> instance.Probe:
        raise AssertionError("the reload child probed the port")

    monkeypatch.setattr(instance, "probe", _boom)
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    monkeypatch.setenv(instance.ENV_INSTANCE_ID, "from-supervisor")
    monkeypatch.setattr(app_module.app, "run", lambda **k: None)
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)

    app_module.main([])

    assert app_module.app.config["INSTANCE_ID"] == "from-supervisor"
    assert not (tmp_path / instance.INSTANCE_FILE).exists()


def test_shutdown_fn_is_installed_and_bound_to_this_instance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called: list[tuple] = []
    monkeypatch.setattr(instance, "request_shutdown", lambda *a, **k: called.append(a))
    monkeypatch.setattr(app_module.app, "run", lambda **k: None)
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)

    app_module.main([])
    app_module.app.config["SHUTDOWN_FN"]()

    assert called == [(tmp_path, app_module.app.config["INSTANCE_ID"])]


@pytest.mark.parametrize("flag", ["--setup", "--doctor"])
def test_setup_and_doctor_never_probe_or_claim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, flag: str
) -> None:
    def _boom(port: int, timeout: float = 1.0) -> instance.Probe:
        raise AssertionError(f"{flag} probed the port")

    monkeypatch.setattr(instance, "probe", _boom)
    monkeypatch.setattr(app_module, "_run_setup", lambda *a, **k: 0)
    monkeypatch.setattr(app_module.preflight, "run_doctor", lambda *a, **k: 0)

    with pytest.raises(SystemExit) as exc:
        app_module.main([flag])

    assert exc.value.code == 0
    assert not (tmp_path / instance.INSTANCE_FILE).exists()


def test_idle_timeout_below_the_floor_is_rejected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _never_serve(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        app_module.main(["--idle-timeout", str(instance.MIN_IDLE_MINUTES - 1)])
    assert exc.value.code == 2  # argparse usage error
    assert "at least 5 minutes" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("flask_debug", "reload_child", "monitor_started"),
    [
        ("0", False, True),  # single process serves -> it hosts the monitor
        ("1", False, False),  # reloader supervisor does not serve
        ("1", True, True),  # the serving child does
    ],
)
def test_idle_monitor_runs_only_in_the_serving_process(
    monkeypatch: pytest.MonkeyPatch, flask_debug: str, reload_child: bool, monitor_started: bool
) -> None:
    monkeypatch.setenv("FLASK_DEBUG", flask_debug)
    if reload_child:
        monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    started: list[tuple] = []
    monkeypatch.setattr(instance, "start_idle_monitor", lambda *a, **k: started.append(a))
    monkeypatch.setattr(app_module.app, "run", lambda **k: None)
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)

    app_module.main(["--idle-timeout", "5"])

    tracker = app_module.app.config["IDLE_TRACKER"]
    assert tracker.timeout_s == 300.0
    assert bool(started) is monitor_started
    if monitor_started:
        assert started[0][0] is tracker
        assert started[0][1] is app_module.app.config["SHUTDOWN_FN"]


def test_no_idle_timeout_means_no_tracker_and_no_monitor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        instance, "start_idle_monitor", lambda *a, **k: pytest.fail("monitor started by default")
    )
    monkeypatch.setattr(app_module.app, "run", lambda **k: None)
    monkeypatch.setattr(app_module, "_should_open_browser", lambda *a: False)

    app_module.main([])

    assert "IDLE_TRACKER" not in app_module.app.config
