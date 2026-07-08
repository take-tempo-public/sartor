"""Anthropic client factory shared by `app.py` and the assistant blueprint.

`_get_client` reads the API key from the environment, falling back to a local
`.api_key` file at the repo root. It moved here (Sprint 8.3a) from `app.py`;
`blueprints/assistant.py` carried a duplicate copy that is now deleted.

This is the only `web_infra/` module that imports `anthropic`, so it is the one
listed in `tests/test_egress_allowlist.py:SANCTIONED_EGRESS_FILES` — the network
egress falsifiability gate (PX-08 / charter C-2).

F-19 offline/demo mode: when `SARTOR_DEMO=1` (`demo_fixtures.is_demo_mode()`),
`_get_client()` returns a `_DemoClient` sentinel instead of constructing a real
`anthropic.Anthropic` — no key is read, no network call is possible. Checked
BEFORE the key lookup, so a real key present alongside the flag still yields
the sentinel (demo wins; never an accidental spend). Every analyzer call kind
independently short-circuits to a canned response before it would touch this
object (`analyzer.py`'s own `_demo_mode_active()` check), so the sentinel is
never dereferenced — it exists only so this function's return type stays
`anthropic.Anthropic` for every caller, with no signature churn.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import anthropic

from demo_fixtures import is_demo_mode

# Repo root for the local `.api_key` fallback (web_infra/ -> repo root). Mirrors
# the retired `app.py:BASE_DIR / ".api_key"` lookup behavior-for-behavior.
_REPO_ROOT = Path(__file__).resolve().parent.parent


class _DemoClient:
    """Sentinel `_get_client()` returns in demo mode instead of a real client.

    Never touched: every analyzer call kind short-circuits to a canned
    response before it would call `.messages...` on this object. Its only
    job is to let `_get_client()` keep returning something typed as
    `anthropic.Anthropic` without constructing one.
    """


def _get_client() -> anthropic.Anthropic:
    """Get Anthropic client. API key from env or config.

    Returns the `_DemoClient` sentinel (cast to the real type) when
    `SARTOR_DEMO=1` — no key is read and no `anthropic.Anthropic` is ever
    constructed. A missing/blank key WITHOUT the demo flag is unchanged: it
    still returns a real (keyless) client whose first API call fails loudly,
    exactly as before this module gained demo-mode awareness.
    """
    if is_demo_mode():
        return cast("anthropic.Anthropic", _DemoClient())
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try reading from a local key file
        key_file = _REPO_ROOT / ".api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    return anthropic.Anthropic(api_key=api_key)
