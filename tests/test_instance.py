"""instance.py — the single-instance probe, the instance file, shutdown and idle rule.

Items 146/147. Everything here talks only to 127.0.0.1 on ephemeral ports, against real
listeners (`http.server`, which sets ``allow_reuse_address=1`` exactly as Werkzeug's
listener does — the property that makes a plain bind succeed on a taken port on Windows).
The egress side (the module names no other host) is pinned in
``tests/test_egress_allowlist.py::test_instance_module_names_only_loopback``.
"""

from __future__ import annotations

import http.server
import json
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import instance


def _free_port() -> int:
    with socket.socket() as s:
        s.bind((instance.LOOPBACK, 0))
        return int(s.getsockname()[1])


@contextmanager
def _serving(status: int, body: bytes, content_type: str = "application/json") -> Iterator[int]:
    """A real loopback HTTP server answering every GET with a fixed response."""

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # http.server's naming
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer((instance.LOOPBACK, 0), _Handler)
    # poll_interval: shutdown() otherwise waits out the default 0.5 s poll, per listener.
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    ).start()
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- probe


class TestProbe:
    def test_free_port_is_free_without_connecting(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A free port is decided by the bind alone: the (slow, on Windows) connect never runs."""

        def _boom(*_a: object, **_k: object) -> None:
            raise AssertionError("probe connected although the exclusive bind succeeded")

        monkeypatch.setattr(instance, "_ask", _boom)
        assert instance.probe(_free_port()).state == "free"

    def test_running_sartor_is_recognised_with_its_healthz_body(self) -> None:
        body = json.dumps({"app": "sartor", "instance_id": "abc", "version": "9.9.9", "pid": 7})
        with _serving(200, body.encode()) as port:
            result = instance.probe(port)
        assert result.state == "sartor"
        assert result.info is not None
        assert result.info["instance_id"] == "abc"

    def test_bind_refuses_a_listener_built_like_werkzeugs(self) -> None:
        """Regression for the observed Windows defect: a plain SO_REUSEADDR bind succeeds on a
        taken port there; the exclusive bind must not."""
        with _serving(200, b"{}") as port:
            assert instance._bind_exclusive_ok(port) is False
        assert instance._bind_exclusive_ok(_free_port()) is True

    @pytest.mark.parametrize(
        ("status", "body", "ctype"),
        [
            (200, b"not sartor", "text/plain"),  # a foreign web server
            (200, json.dumps({"app": "somebody-else"}).encode(), "application/json"),
            (200, b"[1, 2, 3]", "application/json"),  # JSON but not an object
            (404, b"nope", "text/plain"),  # a server with no /healthz
            (
                500,
                json.dumps({"app": "sartor"}).encode(),
                "application/json",
            ),  # sick, not ours to claim
        ],
    )
    def test_anything_else_that_answers_is_foreign(
        self, status: int, body: bytes, ctype: str
    ) -> None:
        with _serving(status, body, ctype) as port:
            assert instance.probe(port).state == "foreign"

    def test_an_owner_that_accepts_but_never_answers_is_foreign(self) -> None:
        """Listens (the kernel backlog accepts the connect) and never replies: bounded by the
        timeout, classified foreign rather than hanging the launch."""
        listener = socket.socket()
        try:
            listener.bind((instance.LOOPBACK, 0))
            listener.listen(1)
            port = int(listener.getsockname()[1])
            assert instance.probe(port, timeout=0.3).state == "foreign"
        finally:
            listener.close()

    def test_a_failed_bind_with_nothing_listening_is_free_not_foreign(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bind that fails for another reason (a privileged port) and is then *refused*
        on connect has no owner to blame; the server will report its own error."""
        monkeypatch.setattr(instance, "_bind_exclusive_ok", lambda _port: False)
        monkeypatch.setattr(instance, "_ask", lambda _port, _timeout: ("refused", None))
        assert instance.probe(1).state == "free"


# --------------------------------------------------------------------------- instance file


class TestInstanceFile:
    def _write(self, base: Path, instance_id: str = "id-1") -> Path:
        return instance.write_instance_file(
            base, instance_id=instance_id, port=5000, host="127.0.0.1", version="1.2.3"
        )

    def test_round_trip_and_no_temp_file_left(self, tmp_path: Path) -> None:
        path = self._write(tmp_path)
        info = instance.read_instance_file(tmp_path)
        assert path == tmp_path / instance.INSTANCE_FILE
        assert info is not None
        assert info["app"] == "sartor"
        assert (info["instance_id"], info["port"], info["version"]) == ("id-1", 5000, "1.2.3")
        assert [p.name for p in tmp_path.iterdir()] == [instance.INSTANCE_FILE]

    def test_write_replaces_a_stale_file(self, tmp_path: Path) -> None:
        self._write(tmp_path, "old")
        self._write(tmp_path, "new")
        info = instance.read_instance_file(tmp_path)
        assert info is not None and info["instance_id"] == "new"

    def test_release_removes_only_our_own_file(self, tmp_path: Path) -> None:
        self._write(tmp_path, "someone-else")
        assert instance.release_instance_file(tmp_path, "mine") is False
        assert (tmp_path / instance.INSTANCE_FILE).exists()
        assert instance.release_instance_file(tmp_path, "someone-else") is True
        assert not (tmp_path / instance.INSTANCE_FILE).exists()

    def test_absent_and_corrupt_files_read_as_none_and_release_never_raises(
        self, tmp_path: Path
    ) -> None:
        assert instance.read_instance_file(tmp_path) is None
        assert instance.release_instance_file(tmp_path, "x") is False
        (tmp_path / instance.INSTANCE_FILE).write_text("{not json", encoding="utf-8")
        assert instance.read_instance_file(tmp_path) is None
        (tmp_path / instance.INSTANCE_FILE).write_text("[1]", encoding="utf-8")
        assert instance.read_instance_file(tmp_path) is None
        assert instance.release_instance_file(tmp_path, "x") is False


# --------------------------------------------------------------------------- shutdown


def test_request_shutdown_releases_the_file_then_exits_zero(tmp_path: Path) -> None:
    instance.write_instance_file(tmp_path, instance_id="me", port=1, host="127.0.0.1", version="v")
    seen: list[tuple[int, bool]] = []
    done = threading.Event()

    def _exit(code: int) -> None:
        seen.append((code, (tmp_path / instance.INSTANCE_FILE).exists()))
        done.set()

    instance.request_shutdown(tmp_path, "me", delay=0.0, exit_fn=_exit)
    assert done.wait(5.0), "shutdown never fired"
    # exit code 0, and the file was already gone when exit_fn ran (atexit does not run
    # under os._exit, so the order is the whole point).
    assert seen == [(0, False)]


def test_request_shutdown_returns_before_it_fires(tmp_path: Path) -> None:
    """The route must be able to send its 202 first: the call itself never exits."""
    fired = threading.Event()
    instance.request_shutdown(tmp_path, "x", delay=0.5, exit_fn=lambda _c: fired.set())
    assert not fired.is_set()
    assert fired.wait(5.0)


# --------------------------------------------------------------------------- idle rule


@pytest.mark.parametrize(
    ("now", "last", "timeout", "in_flight", "expected"),
    [
        (100.0, 0.0, 300.0, 0, False),  # quiet for 100 s of 300
        (300.0, 0.0, 300.0, 0, True),  # exactly the timeout
        (301.0, 0.0, 300.0, 0, True),
        (10_000.0, 0.0, 300.0, 1, False),  # a request in flight is never idle
        (10_000.0, 0.0, 300.0, 3, False),
    ],
)
def test_idle_expired_rule(
    now: float, last: float, timeout: float, in_flight: int, expected: bool
) -> None:
    assert instance.idle_expired(now, last, timeout, in_flight) is expected


class TestIdleTracker:
    def test_touch_and_in_flight_restart_the_quiet_period(self) -> None:
        clock = {"t": 0.0}
        tracker = instance.IdleTracker(300.0, clock=lambda: clock["t"])
        clock["t"] = 299.0
        assert not tracker.expired()
        tracker.touch()
        clock["t"] = 598.0
        assert not tracker.expired()  # 299 s since the touch
        clock["t"] = 599.0
        assert tracker.expired()

    def test_a_request_in_flight_blocks_expiry_and_end_restarts_the_clock(self) -> None:
        clock = {"t": 0.0}
        tracker = instance.IdleTracker(60.0, clock=lambda: clock["t"])
        tracker.begin()
        clock["t"] = 10_000.0
        assert tracker.in_flight == 1
        assert not tracker.expired()
        tracker.end()
        assert tracker.in_flight == 0
        assert not tracker.expired()  # end() counted as activity at t=10_000
        clock["t"] = 10_060.0
        assert tracker.expired()

    def test_end_never_goes_below_zero(self) -> None:
        tracker = instance.IdleTracker(60.0)
        tracker.end()
        tracker.end()
        assert tracker.in_flight == 0


def test_idle_monitor_fires_once_after_the_timeout() -> None:
    tracker = instance.IdleTracker(0.05)
    fired = threading.Event()
    calls: list[int] = []

    def _on_expire() -> None:
        calls.append(1)
        fired.set()

    thread = instance.start_idle_monitor(tracker, _on_expire, poll_s=0.01)
    assert fired.wait(5.0), "idle monitor never fired"
    thread.join(timeout=2.0)
    assert calls == [1]
    assert not thread.is_alive()


def test_idle_monitor_does_not_fire_while_activity_continues() -> None:
    tracker = instance.IdleTracker(0.3)
    fired = threading.Event()
    instance.start_idle_monitor(tracker, fired.set, poll_s=0.01)
    for _ in range(15):  # 0.6 s, twice the timeout, but never quiet for 0.3 s
        tracker.touch()
        assert not fired.wait(0.04)
    assert not fired.is_set()
