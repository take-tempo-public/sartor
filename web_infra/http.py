"""HTTP / SSE helpers shared by `app.py` and the blueprints.

`_sse` is the pure Server-Sent-Event frame formatter. `_error_detail_payload`
builds the per-route 5xx body and is gated on `current_app.debug` — the same Flask
flag SECURITY.md names as "the gate's mechanism." It moved here (Sprint 8.3a) from
`app.py`, where it read the module-global `app.debug`; `current_app.debug` is
behavior-identical (it resolves to the same flag inside a request) but breaks the
`app.py` import dependency so this stays a leaf module.

P1 Hardening boundary: deterministic, no LLM calls (charter C-6).
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


def _sse(event: str, payload: dict[str, Any]) -> str:
    r"""Format a Server-Sent Event line block.

    SSE protocol requires:
    `event: <name>\\ndata: <line>\\n\\n` with the trailing blank line.
    Multi-line data values aren't used here so a single data line suffices.
    """
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _error_detail_payload(exc: Exception) -> dict[str, Any]:
    """Return the per-route 5xx error payload extras.

    In debug mode (Flask's default for `python app.py`): includes the
    exception class + message + the last 3 traceback frames. This is
    load-bearing for the dev-console / smoke-debugging workflow — the
    user opens dev tools, sees the response body, copies the traceback
    into a bug report without needing terminal access.

    In production-mode (FLASK_DEBUG=0): returns only a short
    `request_id` (8 hex chars) so the user / support can correlate
    with the server log (`logger.exception` emits the full traceback
    server-side regardless). Suppresses class names, file paths, and
    function names that an attacker could fingerprint to scope
    follow-up attacks. Per the security review (2026-05-27):
    "Information Disclosure via Error Details".

    The request_id is logged alongside the exception so support can
    look it up via `grep <request_id> logs/` to retrieve the full
    traceback.
    """
    request_id = uuid.uuid4().hex[:8]
    # logger.exception is called by the route wrapper one level up;
    # this just adds the correlation id to the response.
    logger.error("error request_id=%s class=%s", request_id, type(exc).__name__)
    if current_app.debug:
        return {
            "detail": "{cls}: {msg}\n\n{tb}".format(
                cls=type(exc).__name__,
                msg=str(exc),
                tb="".join(traceback.format_tb(exc.__traceback__)[-3:]),
            ),
            "request_id": request_id,
        }
    return {"request_id": request_id}
