"""Request-scoped gates shared by `app.py` and the blueprints.

`_is_localhost_request` is the loopback gate for the dev/eval write surface (the
annotation + bootstrap routes that touch PII-bearing artifacts under
evals/fixtures/real/) and the read-only `/_dashboard` diagnostics. It moved here
(Sprint 8.3a) so `app.py` and `dashboard/routes.py` share one definition rather
than each carrying a loopback host-check.

P1 Hardening boundary: deterministic, no LLM calls (charter C-6).
"""

from __future__ import annotations

from flask import request


def _is_localhost_request() -> bool:
    """True only for loopback hosts.

    Gates the dev/eval-only annotation + bootstrap write surface so it is
    unreachable except from the local machine (it touches PII-bearing artifacts
    under evals/fixtures/real/).
    """
    host = (request.host or "").split(":")[0]
    return host in {"localhost", "127.0.0.1", "::1", "[::1]"}


def _is_same_origin_request() -> bool:
    """True unless a browser says this request came from another site (items 146/147).

    The CSRF-style companion to `_is_localhost_request`, for a state-changing route a
    page on another origin could otherwise POST to the user's own machine (`/api/shutdown`).
    Rejects a request whose `Sec-Fetch-Site` is anything but `same-origin` / `none`, or
    whose `Origin` is not this server's own origin. A client that sends neither header
    (curl, the item-145 launcher) passes: browsers always send one of the two on a
    cross-site request, so absence means "not a browser acting for another site" — and the
    route still requires its own custom action header, which a cross-site page can only
    send after a CORS preflight this server never answers.
    """
    site = request.headers.get("Sec-Fetch-Site")
    if site is not None and site not in {"same-origin", "none"}:
        return False
    origin = request.headers.get("Origin")
    return origin is None or origin == request.host_url.rstrip("/")
