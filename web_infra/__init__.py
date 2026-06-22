"""Shared web-infra package — cross-cutting HTTP-layer helpers.

The small, cohesive home for the helpers `app.py` and every blueprint share
(Sprint 8.3a, the `app.py` -> blueprints decomposition foundation). Six fixed
groups (per the 8.1 design): security, http/sse, clients, config-io, provisioning,
request-gates.

Hard rule (enforced by `tests/test_web_infra_is_leaf.py`): this package NEVER
imports `app.py`, any blueprint, or `config.py`. It is leaf infrastructure — that
is what keeps the import graph acyclic and lets every blueprint import it freely.
The helpers that need a path take it as an explicit `configs_dir` arg (so a test
can call them with a `tmp_path`, no app context); blueprints pass
`current_app.config["CONFIGS_DIR"]`.

`no_implicit_reexport` is set (pyproject [tool.mypy]), so the re-exported names
must be declared in `__all__` for importers to see them.
"""

from __future__ import annotations

from web_infra.clients import _get_client
from web_infra.config_io import _load_config, _save_config
from web_infra.http import _error_detail_payload, _sse
from web_infra.provisioning import _get_or_provision_candidate
from web_infra.request_gates import _is_localhost_request
from web_infra.security import _safe_username, _within

__all__ = [
    "_error_detail_payload",
    "_get_client",
    "_get_or_provision_candidate",
    "_is_localhost_request",
    "_load_config",
    "_safe_username",
    "_save_config",
    "_sse",
    "_within",
]
