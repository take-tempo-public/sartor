"""Deterministic identity helpers for call-log rows and eval records (item 181).

No LLM call and no dependency (the P1 hardening boundary, charter C-6): a prompt's content
hash, the producer id that names "what produced this output", and the W3C-sized ids that tie a
run together. `analyzer.py` and `evals/runner.py` import this; the prompt-lock script and its
gate test import it so a row and the lock hash text the same way.

Forms follow the sibling projects so the three records converge instead of drifting:
``sha256:<64 hex>`` (spolia P-0001, the isidium `journal@2` pattern) and W3C trace and span ids
(32 and 16 lowercase hex, never all zero).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

# Bump when the producer-id recipe changes, so a recipe change re-keys loudly, never silently.
PRODUCER_RECIPE_VERSION = 1

_TRACE_ID_HEX = 32
_SPAN_ID_HEX = 16


def text_sha256(text: str) -> str:
    """``sha256:<hex>`` of ``text`` encoded as UTF-8 — the text exactly as sent."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reject_floats(value: object, path: str) -> None:
    if isinstance(value, float):
        raise TypeError(f"float at {path or '<root>'}: nothing hashed may contain a float")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")


def canonical_json(value: object) -> str:
    """Compact, key-sorted JSON; raises ``TypeError`` on a float anywhere inside.

    Floats are refused rather than formatted: a float's text differs between languages, and an
    identity two projects must reproduce cannot depend on it (factory C-6, "no floats in
    anything hashed or stored").
    """
    _reject_floats(value, "")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def producer_id(
    *,
    call_kind: str,
    prompt_sha256: str,
    model: str,
    settings: dict[str, Any] | None,
) -> str:
    """``sha256:<hex>`` naming what produced an output: kind, prompt text, model, settings.

    ``call_kind`` loses a ``_retry`` suffix, so a retry is the same producer as its first
    attempt. ``model`` is the answering model when known, else the one requested.
    ``settings`` is the request settings actually sent (``None`` when unknown).
    """
    return text_sha256(
        canonical_json(
            {
                "v": PRODUCER_RECIPE_VERSION,
                "kind": call_kind.removesuffix("_retry"),
                "prompt_sha256": prompt_sha256,
                "model": model,
                "settings": settings,
            }
        )
    )


def _nonzero_hex(nbytes: int) -> str:
    # An all-zero id is invalid in W3C Trace Context; the chance is nil, the check is one line.
    while True:
        value = secrets.token_hex(nbytes)
        if int(value, 16) != 0:
            return value


def new_trace_id() -> str:
    """A fresh 32-hex W3C trace id."""
    return _nonzero_hex(_TRACE_ID_HEX // 2)


def new_span_id() -> str:
    """A fresh 16-hex W3C span id."""
    return _nonzero_hex(_SPAN_ID_HEX // 2)


def is_trace_id(value: object) -> bool:
    """True for a 32-char lowercase hex string that is not all zero."""
    return _is_hex_id(value, _TRACE_ID_HEX)


def is_span_id(value: object) -> bool:
    """True for a 16-char lowercase hex string that is not all zero."""
    return _is_hex_id(value, _SPAN_ID_HEX)


def _is_hex_id(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    if any(c not in "0123456789abcdef" for c in value):
        return False
    return int(value, 16) != 0
