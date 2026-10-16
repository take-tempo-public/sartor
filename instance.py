"""Single-instance support: is Sartor already running here, and how do we stop it.

Items 146 and 147. A leaf module: stdlib only, no Sartor imports, so `app.py`, the
`lifecycle` blueprint and the tests can all use it without a cycle.

**Why a pre-bind probe, not Werkzeug's own error.** Observed on Windows (the dossier
`docs/dev/blast-radius/single-instance-and-quit.md`): a second launch, and a launch next to
a foreign server, bind the port *silently*. Werkzeug builds its listener with
`SO_REUSEADDR`, which on Windows lets two sockets share one port, so its `EADDRINUSE`
message never fires. This module asks the port who owns it *before* `app.run`.

**Cost, measured on that machine.** A refused loopback connect takes about 2 s on Windows,
and the common case is a free port. So `probe` binds exclusively first (0.3 ms, and a
success means `free` with no connection at all). Only when that bind fails does it connect,
to classify the owner (about 25 ms).

**The one network touch (charter C-2, amended 2026-10-15).** The only host this module ever
names is `LOOPBACK`. `tests/test_egress_allowlist.py` pins that by AST, so a caller cannot
supply a host and a second constant cannot appear unnoticed.

Liveness is decided by asking `/healthz` and comparing `instance_id`, never by a pid check:
`os.kill(pid, 0)` terminates the process on Windows, pids are reused, and under the Flask
reloader the serving pid is the child's, not the supervisor's.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

APP_NAME: Final = "sartor"
INSTANCE_FILE: Final = "sartor-instance.json"
#: The only host this module connects to or binds. Never parameterised (see module docstring).
LOOPBACK: Final = "127.0.0.1"
#: Exported by the supervisor so the reloader's serving child shares the instance id.
ENV_INSTANCE_ID: Final = "SARTOR_INSTANCE_ID"
PROBE_TIMEOUT_S: Final = 1.0
#: `--idle-timeout` floor, in minutes. Below this a browser's own timer throttling (one
#: tick a minute in a background tab) could look like an abandoned page.
MIN_IDLE_MINUTES: Final = 5
#: The page's heartbeat period. 60 s is the floor browsers impose on background timers.
HEARTBEAT_S: Final = 60

PortState = Literal["free", "sartor", "foreign"]


@dataclass(frozen=True)
class Probe:
    """What owns a port: `free`, a running `sartor` (with its `/healthz` body), or `foreign`."""

    state: PortState
    info: dict[str, object] | None = None


def new_instance_id() -> str:
    """Return a fresh opaque id for one launch of Sartor."""
    return uuid.uuid4().hex


def _bind_exclusive_ok(port: int) -> bool:
    """True when nothing at all holds `LOOPBACK:port`; never raises.

    `SO_EXCLUSIVEADDRUSE` on Windows, because there `SO_REUSEADDR` lets a second socket
    bind a port a listener already holds (the observed defect). On POSIX a plain bind
    already refuses a listening port; `SO_REUSEADDR` is set only so a TIME_WAIT leftover
    is not mistaken for an owner.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((LOOPBACK, port))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def _ask(
    port: int, timeout: float
) -> tuple[Literal["refused", "answered", "silent"], dict[str, object] | None]:
    """GET `/healthz` on `LOOPBACK:port`. Imports `http.client` lazily: only a taken port gets here."""
    import http.client  # lazy by design, see the docstring

    conn = http.client.HTTPConnection(LOOPBACK, port, timeout=timeout)
    try:
        conn.request("GET", "/healthz")
        resp = conn.getresponse()
        body = resp.read(4096)
    except ConnectionRefusedError:
        return "refused", None
    except (OSError, http.client.HTTPException):
        return "silent", None
    finally:
        conn.close()
    if resp.status != 200:
        return "answered", None
    try:
        data = json.loads(body)
    except ValueError:
        return "answered", None
    return "answered", data if isinstance(data, dict) else None


def probe(port: int, timeout: float = PROBE_TIMEOUT_S) -> Probe:
    """Classify `LOOPBACK:port` as `free`, a running `sartor`, or `foreign`.

    A failed exclusive bind that is then *refused* on connect means nothing listens (the
    bind failed for another reason, e.g. a privileged port): reported `free` so the caller
    lets the server report its own error rather than blaming a phantom owner.
    """
    if _bind_exclusive_ok(port):
        return Probe("free")
    outcome, info = _ask(port, timeout)
    if outcome == "refused":
        return Probe("free")
    if outcome == "answered" and info is not None and info.get("app") == APP_NAME:
        return Probe("sartor", info)
    return Probe("foreign")


def instance_path(base_dir: Path) -> Path:
    """Where the instance file lives for a given data root (`SARTOR_HOME` / repo root / user dir)."""
    return Path(base_dir) / INSTANCE_FILE


def write_instance_file(
    base_dir: Path, *, instance_id: str, port: int, host: str, version: str
) -> Path:
    """Write the instance file atomically (tmp + `os.replace`) and return its path.

    `pid` is the launching process. Under the reloader that is the supervisor; the serving
    child's pid is in `/healthz`. Do not use it for liveness (module docstring).
    """
    path = instance_path(base_dir)
    payload = {
        "app": APP_NAME,
        "instance_id": instance_id,
        "pid": os.getpid(),
        "port": port,
        "host": host,
        "version": version,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    tmp = path.with_name(f"{INSTANCE_FILE}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_instance_file(base_dir: Path) -> dict[str, object] | None:
    """Return the parsed instance file, or None when absent, unreadable or not an object."""
    try:
        data = json.loads(instance_path(base_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def release_instance_file(base_dir: Path, instance_id: str) -> bool:
    """Remove the instance file iff it is ours (matching `instance_id`). Never raises."""
    info = read_instance_file(base_dir)
    if info is None or info.get("instance_id") != instance_id:
        return False
    try:
        instance_path(base_dir).unlink()
    except OSError:
        return False
    return True


def request_shutdown(
    base_dir: Path,
    instance_id: str,
    *,
    delay: float = 0.3,
    exit_fn: Callable[[int], object] = os._exit,
) -> None:
    """Stop this process shortly, after the HTTP response has been sent. Returns at once.

    `os._exit`, because Werkzeug's development server has no clean-stop API and `atexit`
    handlers do not run under it, so the instance file is released explicitly first and the
    standard streams are flushed by hand. State on disk is safe to cut: SQLite commits per
    transaction and context files are written by atomic replace. Under the reloader the
    serving child exits 0 and the supervisor then exits 0 (observed, dossier §Observed).
    """

    def _go() -> None:
        release_instance_file(base_dir, instance_id)
        with contextlib.suppress(Exception):
            sys.stdout.flush()
            sys.stderr.flush()
        exit_fn(0)

    timer = threading.Timer(delay, _go)
    timer.daemon = True
    timer.start()


def idle_expired(now: float, last_activity: float, timeout_s: float, in_flight: int) -> bool:
    """Pure rule: idle shutdown is due only with no request in flight and `timeout_s` of quiet."""
    return in_flight == 0 and (now - last_activity) >= timeout_s


class IdleTracker:
    """Last-activity clock plus an in-flight counter, shared by the request hooks and the monitor.

    `touch` is a single float store (atomic under the GIL, so lockless on the hot path that
    every request takes); the counter needs a lock because `+= 1` is not atomic.
    In-flight counting is what stops a long generation whose tab was closed from being
    cut off by the idle timer.
    """

    def __init__(self, timeout_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        """Start the clock now; `timeout_s` of quiet with nothing in flight means expired."""
        self.timeout_s = timeout_s
        self._clock = clock
        self._last = clock()
        self._in_flight = 0
        self._lock = threading.Lock()

    def touch(self) -> None:
        """Record activity now."""
        self._last = self._clock()

    def begin(self) -> None:
        """A request started: count it and treat it as activity."""
        with self._lock:
            self._in_flight += 1
        self._last = self._clock()

    def end(self) -> None:
        """A request finished (never below zero): the quiet period restarts now."""
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
        self._last = self._clock()

    @property
    def in_flight(self) -> int:
        """Requests currently being served."""
        return self._in_flight

    def expired(self) -> bool:
        """True when the idle rule (`idle_expired`) holds at the current clock."""
        return idle_expired(self._clock(), self._last, self.timeout_s, self._in_flight)


def start_idle_monitor(
    tracker: IdleTracker, on_expire: Callable[[], None], poll_s: float | None = None
) -> threading.Thread:
    """Start a daemon thread that calls `on_expire` once when `tracker` expires, then exits.

    Polls every `min(60, timeout/5)` seconds (at least 1), so a 5-minute timeout fires within
    a minute of becoming due. Daemon, so it never holds the interpreter open.
    """
    interval = poll_s if poll_s is not None else max(1.0, min(60.0, tracker.timeout_s / 5.0))

    def _watch() -> None:
        while True:
            time.sleep(interval)
            if tracker.expired():
                on_expire()
                return

    thread = threading.Thread(target=_watch, name="sartor-idle-monitor", daemon=True)
    thread.start()
    return thread
