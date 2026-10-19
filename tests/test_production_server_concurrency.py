"""Is the production server threaded? Pins the answer by observing the real entry point.

Item 177 point 1. The repo asserted both answers: `hardening.py`'s `context_transaction`
docstring and item 25 said `app.run()` is single-threaded, while `tests/ux/conftest.py` said the
UX server matches production's threaded one. Both were read from source, never observed.

The probe is route-independent. Connection A sends a *partial* request (no terminating blank
line), so whichever thread serves it blocks reading headers. Connection B then sends a complete
`GET /healthz`. A single-threaded server is stuck on A and B times out; a threaded one answers B.
The two in-process controls prove the probe can tell the cases apart before it is trusted on the
production entry point, which runs as a subprocess with a temp `SARTOR_HOME` so it never touches
real user data, the real instance file or the API key.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Generator
from pathlib import Path

import pytest
from flask import Flask
from werkzeug.serving import make_server

REPO_ROOT = Path(__file__).resolve().parent.parent
PARTIAL_REQUEST = b"GET /healthz HTTP/1.1\r\nHost: probe\r\n"
FULL_REQUEST = b"GET /healthz HTTP/1.1\r\nHost: probe\r\nConnection: close\r\n\r\n"
# A threaded server answers B in milliseconds; a serialized one never does while A is open.
PROBE_TIMEOUT_S = 1.5
BOOT_TIMEOUT_S = 90.0


def _free_port() -> int:
    """Return a port that was free a moment ago (bind to 0, read it back, release)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
    return port


def second_request_answered(port: int) -> bool:
    """Return True if a full request is answered while another connection sits half-sent."""
    with socket.create_connection(("127.0.0.1", port), timeout=PROBE_TIMEOUT_S) as stalled:
        stalled.sendall(PARTIAL_REQUEST)
        time.sleep(0.2)  # let the server accept A and start reading its headers
        with socket.create_connection(("127.0.0.1", port), timeout=PROBE_TIMEOUT_S) as second:
            second.settimeout(PROBE_TIMEOUT_S)
            second.sendall(FULL_REQUEST)
            try:
                return second.recv(64).startswith(b"HTTP/1.")
            except TimeoutError:
                return False


@contextlib.contextmanager
def _werkzeug_server(*, threaded: bool) -> Generator[int]:
    """Serve a one-route app on an ephemeral port with the given `threaded` setting."""
    app = Flask(__name__)
    app.add_url_rule("/healthz", "healthz", lambda: "ok")
    server = make_server("127.0.0.1", 0, app, threaded=threaded)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield int(server.server_port)
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_probe_negative_control_single_threaded_server_is_detected() -> None:
    """The probe must report `False` for a server built with `threaded=False`."""
    with _werkzeug_server(threaded=False) as port:
        assert second_request_answered(port) is False


def test_probe_positive_control_threaded_server_is_detected() -> None:
    """The probe must report `True` for a server built with `threaded=True`."""
    with _werkzeug_server(threaded=True) as port:
        assert second_request_answered(port) is True


def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
    """Kill the process and every descendant (the debug reloader serves from a child)."""
    if sys.platform == "win32":
        subprocess.run(  # noqa: S603 - fixed argv, our own pid
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10)


def _wait_for_healthz(port: int, proc: subprocess.Popen[bytes], log: Path) -> None:
    """Poll `/healthz` until it answers, or fail with the process log if it never does."""
    deadline = time.monotonic() + BOOT_TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"server exited early ({proc.returncode}):\n{log.read_text('utf-8')}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):
                return
        except OSError:
            time.sleep(0.25)
    pytest.fail(f"server never answered /healthz:\n{log.read_text('utf-8')}")


# The reloader case boots two processes (~8 s of an ~16 s file), and `app.run()` is the same call in
# both modes, so it is opt-in: `SARTOR_PROBE_RELOADER=1 pytest tests/test_production_server_concurrency.py`.
_RELOADER = pytest.param(
    "1",
    id="debug-on-reloader",
    marks=pytest.mark.skipif(
        os.environ.get("SARTOR_PROBE_RELOADER") != "1", reason="opt-in: set SARTOR_PROBE_RELOADER=1"
    ),
)


@pytest.mark.parametrize("flask_debug", [pytest.param("0", id="debug-off"), _RELOADER])
def test_production_entry_point_serves_concurrent_requests(
    tmp_path: Path, flask_debug: str
) -> None:
    """`python app.py` (what `sartor` and the container run) answers B while A is stalled."""
    port = _free_port()
    env = {
        **os.environ,
        "SARTOR_HOME": str(tmp_path / "home"),
        "SARTOR_DEMO": "1",
        "SARTOR_NO_BROWSER": "1",
        "FLASK_DEBUG": flask_debug,
        "PYTHONUNBUFFERED": "1",
    }
    env.pop("WERKZEUG_RUN_MAIN", None)
    log = tmp_path / "server.log"
    with log.open("wb") as out:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv
            [sys.executable, "app.py", "--port", str(port), "--no-browser"],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=sys.platform != "win32",
        )
        try:
            _wait_for_healthz(port, proc, log)
            answered = second_request_answered(port)
        finally:
            _kill_tree(proc)
    assert answered is True, (
        "a full request got no answer while another connection was half-sent: "
        f"the production server serializes requests\n{log.read_text('utf-8')}"
    )
