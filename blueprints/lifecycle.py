"""Lifecycle blueprint — `/healthz`, `/api/shutdown`, `/api/heartbeat` (items 146/147).

The server's answer to "who are you?" and "stop". Localhost-only, behind the same
host-header guard as `/_dashboard` (`web_infra._is_localhost_request`).

* `GET /healthz` — app identity, version, pid, instance id and the idle timeout.
  What the launch-time probe (`instance.probe`) reads, what the item-145 launcher's
  `status` will read, and what the container `HEALTHCHECK` will call. It is *not*
  counted as activity, so polling it can never keep an idle server alive.
* `POST /api/shutdown` — the in-app Quit. Same-origin only (`_is_same_origin_request`)
  **and** a custom `X-Sartor-Action: shutdown` header, which a cross-site page cannot
  send without a CORS preflight this server never answers. It answers 202 and the
  process exits shortly after, so the response is delivered first. 501 when the process
  was not started by `sartor` (no `SHUTDOWN_FN`): a WSGI host such as gunicorn must never
  be killed by a page button.
* `POST /api/heartbeat` — the page's keep-alive when idle shutdown is on (`--idle-timeout`).

No filesystem path is read or written by any route here (the instance file is handled in
`instance.py`, by `main()` and the shutdown callable), so the `_safe_username` /
`_within` containment pattern does not apply — there is no user-supplied path to contain.

The request hooks feed `instance.IdleTracker` when one is configured: a request in flight
blocks idle expiry, so a long generation whose tab was closed is not cut off.
"""

from __future__ import annotations

import os

from flask import Blueprint, current_app, g, jsonify, request
from flask.typing import ResponseReturnValue

import instance
from web_infra import _is_localhost_request, _is_same_origin_request
from web_infra.openapi import app_version

lifecycle_bp = Blueprint("lifecycle", __name__)

#: The header `POST /api/shutdown` requires; a cross-site page cannot set it without a preflight.
ACTION_HEADER = "X-Sartor-Action"
SHUTDOWN_ACTION = "shutdown"

_COUNTED = "_sartor_idle_counted"


def _localhost_only() -> ResponseReturnValue:
    """The 403 every route here answers to a non-loopback Host header."""
    return jsonify({"error": "localhost only"}), 403


def _tracker() -> instance.IdleTracker | None:
    """The configured idle tracker, or None when idle shutdown is off (the default)."""
    tracker: instance.IdleTracker | None = current_app.config.get("IDLE_TRACKER")
    return tracker


@lifecycle_bp.before_app_request
def _begin_activity() -> None:
    """Count this request as activity and in flight (idle shutdown only; `/healthz` exempt)."""
    tracker = _tracker()
    if tracker is not None and request.endpoint != "lifecycle.healthz":
        tracker.begin()
        setattr(g, _COUNTED, True)


@lifecycle_bp.teardown_app_request
def _end_activity(_exc: BaseException | None) -> None:
    """Release the in-flight count taken by `_begin_activity`, exactly once per request."""
    if getattr(g, _COUNTED, False):
        setattr(g, _COUNTED, False)
        tracker = _tracker()
        if tracker is not None:
            tracker.end()


@lifecycle_bp.route("/healthz", methods=["GET"])
def healthz() -> ResponseReturnValue:
    """Identify this server: app name, version, pid, instance id, idle timeout (or null)."""
    if not _is_localhost_request():
        return _localhost_only()
    tracker = _tracker()
    resp = jsonify(
        {
            "app": instance.APP_NAME,
            "version": app_version(),
            "pid": os.getpid(),
            "instance_id": current_app.config.get("INSTANCE_ID"),
            "idle_timeout_s": tracker.timeout_s if tracker is not None else None,
        }
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@lifecycle_bp.route("/api/shutdown", methods=["POST"])
def shutdown() -> ResponseReturnValue:
    """Stop the server (in-app Quit). 202 now; the process exits a moment after the reply."""
    if not _is_localhost_request():
        return _localhost_only()
    if not _is_same_origin_request() or request.headers.get(ACTION_HEADER) != SHUTDOWN_ACTION:
        return jsonify({"error": "same-origin request required"}), 403
    shutdown_fn = current_app.config.get("SHUTDOWN_FN")
    if shutdown_fn is None:
        return jsonify(
            {"error": "this server was not started by sartor, so it cannot stop itself"}
        ), 501
    shutdown_fn()
    return jsonify({"status": "stopping"}), 202


@lifecycle_bp.route("/api/heartbeat", methods=["POST"])
def heartbeat() -> ResponseReturnValue:
    """Keep-alive from an open page. The activity itself is recorded by `_begin_activity`."""
    if not _is_localhost_request():
        return _localhost_only()
    return "", 204
