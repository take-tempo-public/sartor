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
