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
    assert client.get("/__boom").status_code == 500
    assert tracker.in_flight == 0


def test_no_tracker_means_no_bookkeeping(client: FlaskClient) -> None:
    """Default run (idle shutdown off): the hooks are a no-op and nothing is required."""
    assert client.post("/api/heartbeat").status_code == 204
    assert client.get("/healthz").status_code == 200
