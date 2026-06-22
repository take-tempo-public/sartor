"""Anthropic client factory shared by `app.py` and the assistant blueprint.

`_get_client` reads the API key from the environment, falling back to a local
`.api_key` file at the repo root. It moved here (Sprint 8.3a) from `app.py`;
`blueprints/assistant.py` carried a duplicate copy that is now deleted.

This is the only `web_infra/` module that imports `anthropic`, so it is the one
listed in `tests/test_egress_allowlist.py:SANCTIONED_EGRESS_FILES` — the network
egress falsifiability gate (PX-08 / charter C-2).
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic

# Repo root for the local `.api_key` fallback (web_infra/ -> repo root). Mirrors
# the retired `app.py:BASE_DIR / ".api_key"` lookup behavior-for-behavior.
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _get_client() -> anthropic.Anthropic:
    """Get Anthropic client. API key from env or config."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try reading from a local key file
        key_file = _REPO_ROOT / ".api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    return anthropic.Anthropic(api_key=api_key)
