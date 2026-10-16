"""blueprints/lifecycle.py — /healthz, /api/shutdown, /api/heartbeat (items 146/147).

Built on the `app` / `client` fixtures (a fresh `create_app(Config(base_dir=tmp_path))`).
`SHUTDOWN_FN` is always a stub here: the real one calls `os._exit`.
"""

from __future__ import annotations

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

import instance
from blueprints.lifecycle import ACTION_HEADER, SHUTDOWN_ACTION

_SHUTDOWN_HEADERS = {ACTION_HEADER: SHUTDOWN_ACTION}


class _Clock:
    """A settable clock for `IdleTracker`."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture()
def stub_shutdown(app: Flask) -> list[int]:
    """Install a recording stand-in for the real shutdown; returns its call log."""
    calls: list[int] = []
    app.config["SHUTDOWN_FN"] = lambda: calls.append(1)
    return calls


# ------------------------------------------------------------------ /healthz


def test_healthz_identifies_this_server(app: Flask, client: FlaskClient) -> None:
    app.config["INSTANCE_ID"] = "abc123"
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body: dict[str, Any] = resp.get_json()
    assert body["app"] == "sartor"
    assert body["instance_id"] == "abc123"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["pid"], int)
    assert body["idle_timeout_s"] is None  # idle shutdown is off by default
    assert resp.headers["Cache-Control"] == "no-store"


def test_healthz_reports_the_idle_timeout_when_configured(app: Flask, client: FlaskClient) -> None:
    app.config["IDLE_TIMEOUT_S"] = 300  # not read: the tracker is the source of truth
    app.config["IDLE_TRACKER"] = instance.IdleTracker(900.0)
    assert client.get("/healthz").get_json()["idle_timeout_s"] == 900.0


def test_healthz_is_what_the_probe_recognises(app: Flask) -> None:
    """The contract between the two halves: a body `instance.probe` classifies as sartor."""
    app.config["INSTANCE_ID"] = "id"
    body = app.test_client().get("/healthz").get_json()
    assert body["app"] == instance.APP_NAME


@pytest.mark.parametrize("path", ["/healthz"])
def test_healthz_refuses_a_non_loopback_host(client: FlaskClient, path: str) -> None:
    resp = client.get(path, headers={"Host": "evil.example"})
    assert resp.status_code == 403


# ------------------------------------------------------------------ /api/shutdown


def test_shutdown_accepts_a_same_origin_request_with_the_action_header(
    client: FlaskClient, stub_shutdown: list[int]
) -> None:
    resp = client.post(
        "/api/shutdown",
        headers={
            **_SHUTDOWN_HEADERS,
            "Origin": "http://localhost",
            "Sec-Fetch-Site": "same-origin",
        },
    )
    assert resp.status_code == 202
    assert resp.get_json() == {"status": "stopping"}
    assert stub_shutdown == [1]


def test_shutdown_accepts_a_non_browser_client_that_sends_neither_origin_header(
    client: FlaskClient, stub_shutdown: list[int]
) -> None:
    """curl / the item-145 launcher send no Origin and no Sec-Fetch-Site."""
    assert client.post("/api/shutdown", headers=_SHUTDOWN_HEADERS).status_code == 202
    assert stub_shutdown == [1]


@pytest.mark.parametrize(
    ("label", "headers"),
    [
        ("missing action header", {}),
        ("wrong action value", {ACTION_HEADER: "restart"}),
        ("foreign host", {**_SHUTDOWN_HEADERS, "Host": "evil.example"}),
        ("cross-site Sec-Fetch-Site", {**_SHUTDOWN_HEADERS, "Sec-Fetch-Site": "cross-site"}),
        ("same-site (not same-origin)", {**_SHUTDOWN_HEADERS, "Sec-Fetch-Site": "same-site"}),
        ("foreign Origin", {**_SHUTDOWN_HEADERS, "Origin": "https://evil.example"}),
        ("Origin on another port", {**_SHUTDOWN_HEADERS, "Origin": "http://localhost:9999"}),
    ],
)
def test_shutdown_is_refused_and_does_nothing(
    client: FlaskClient, stub_shutdown: list[int], label: str, headers: dict[str, str]
) -> None:
    resp = client.post("/api/shutdown", headers=headers)
    assert resp.status_code == 403, label
    assert stub_shutdown == [], label


def test_shutdown_is_501_when_the_server_was_not_started_by_sartor(client: FlaskClient) -> None:
    """No SHUTDOWN_FN (a WSGI host, a test app): the button must never kill the host."""
    resp = client.post("/api/shutdown", headers=_SHUTDOWN_HEADERS)
    assert resp.status_code == 501


def test_shutdown_rejects_get(client: FlaskClient, stub_shutdown: list[int]) -> None:
    assert client.get("/api/shutdown", headers=_SHUTDOWN_HEADERS).status_code == 405
    assert stub_shutdown == []


# ------------------------------------------------------------------ /api/heartbeat and activity


def test_heartbeat_is_204_and_refuses_a_foreign_host(client: FlaskClient) -> None:
    assert client.post("/api/heartbeat").status_code == 204
    assert client.post("/api/heartbeat", headers={"Host": "evil.example"}).status_code == 403


def test_heartbeat_counts_as_activity_but_healthz_does_not(app: Flask, client: FlaskClient) -> None:
    """Polling /healthz (the launcher's `status`) must not keep an idle server alive."""
    clock = _Clock()
    tracker = instance.IdleTracker(300.0, clock=clock)
    app.config["IDLE_TRACKER"] = tracker

    clock.t = 400.0
    assert tracker.expired()
    assert client.get("/healthz").status_code == 200
    assert tracker.expired(), "/healthz refreshed the idle clock"

    assert client.post("/api/heartbeat").status_code == 204
    assert not tracker.expired()


def test_a_request_in_flight_blocks_expiry_and_is_released_after(
    app: Flask, client: FlaskClient
) -> None:
    clock = _Clock()
    tracker = instance.IdleTracker(60.0, clock=clock)
    app.config["IDLE_TRACKER"] = tracker
    seen: list[tuple[int, bool]] = []

    @app.route("/__probe_inflight")
    def _probe() -> str:
        clock.t += 10_000.0  # a very long request
        seen.append((tracker.in_flight, tracker.expired()))
        return "ok"

    assert client.get("/__probe_inflight").status_code == 200
    assert seen == [(1, False)]
    assert tracker.in_flight == 0


def test_a_failing_request_still_releases_its_in_flight_count(app: Flask) -> None:
    tracker = instance.IdleTracker(60.0)
    app.config["IDLE_TRACKER"] = tracker

    @app.route("/__boom")
    def _boom() -> str:
        raise RuntimeError("boom")

    client = app.test_client()
    # Flask turns an unhandled exception into a streamed 500 (`force_type` wraps the WSGI
    # app iterable), so the count is released when the response is CLOSED — which a WSGI
    # server always does; the context manager is the test client's equivalent.
    with client.get("/__boom") as resp:
        assert resp.status_code == 500
    assert tracker.in_flight == 0


def _add_stream_route(app: Flask, tracker: instance.IdleTracker, seen: list[int]) -> None:
    """A route shaped like the app's SSE routes: `Response(generator)`, no stream_with_context.

    The app's four SSE routes (`blueprints/analysis.py`, `generation.py`, `assistant.py`,
    `diagnostics.py`) return the generator this way, so Flask tears the request down when the
    view returns — before the generator does its (paid, slow) work.
    """
    from flask import Response

    @app.route("/__stream")
    def _stream() -> Response:
        def gen() -> Any:
            seen.append(tracker.in_flight)
            yield "data: a\n\n"
            seen.append(tracker.in_flight)
            yield "data: b\n\n"

        return Response(gen(), mimetype="text/event-stream")


def test_a_streamed_response_holds_the_in_flight_count_until_it_closes(
    app: Flask, client: FlaskClient
) -> None:
    """Regression for a hole found while writing the docs: teardown runs before an SSE
    generator starts, so counting only the request would read 0 for the whole generation
    and let `--idle-timeout` stop the server mid-run once the tab was closed."""
    tracker = instance.IdleTracker(60.0)
    app.config["IDLE_TRACKER"] = tracker
    seen: list[int] = []
    _add_stream_route(app, tracker, seen)

    with client.get("/__stream") as resp:  # closed on exit, as a WSGI server closes it
        body = resp.get_data(as_text=True)
        assert tracker.in_flight == 1, "the count must be held until the response is closed"

    assert "data: a" in body and "data: b" in body
    assert seen == [1, 1], "the stream ran with nothing counted in flight"
    assert tracker.in_flight == 0, "the count leaked after the stream closed"


def test_an_abandoned_stream_releases_the_count_when_closed(
    app: Flask, client: FlaskClient
) -> None:
    """A client that disconnects after the first chunk (or before any) must not leak the
    count — a leaked +1 would mean idle shutdown never fires again."""
    tracker = instance.IdleTracker(60.0)
    app.config["IDLE_TRACKER"] = tracker
    _add_stream_route(app, tracker, [])

    resp = client.get("/__stream", buffered=False)
    next(iter(resp.response))  # first chunk only
    assert tracker.in_flight == 1
    resp.close()
    assert tracker.in_flight == 0

    never_read = client.get("/__stream", buffered=False)
    assert tracker.in_flight == 1
    never_read.close()
    assert tracker.in_flight == 0


def test_no_tracker_means_no_bookkeeping(client: FlaskClient) -> None:
    """Default run (idle shutdown off): the hooks are a no-op and nothing is required."""
    assert client.post("/api/heartbeat").status_code == 204
    assert client.get("/healthz").status_code == 200
