"""Live probe for item 175: what does one real call record, and what did the API actually return?

Makes TWO tiny paid calls (one Sonnet, one Haiku; one-word prompt, ``max_tokens`` 16;
well under a cent) through ``analyzer._call_llm`` -- the product's own path -- with the
client wrapped so the SAME call yields both:

* the telemetry row exactly as ``_emit_call_log`` would have written it, and
* the raw facts the SDK exposed for that call: the answering model, the API request id,
  the full ``usage`` dump and the kwargs sent (never the prompt text).

Run it before a provenance change and again after: the difference between the row and
the raw facts is the gap. Rows are captured in memory and NOT appended to the live
``logs/llm_calls.jsonl``.

Usage:
    python -m scripts.probe_call_provenance --yes
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from unittest.mock import patch

import analyzer
import hardening
from demo_fixtures import is_demo_mode
from web_infra.clients import _get_client

PROBE_PROMPT = "Reply with the single word: ok"
PROBE_USER = "probe:175"
PROBE_MAX_TOKENS = 16

#: Request kwargs that carry prompt content; never echoed.
_CONTENT_KEYS = ("system", "messages")


class _StreamSpy:
    """Delegate to the SDK stream, keeping what ``get_final_message`` returned."""

    def __init__(self, stream: Any, sink: dict[str, Any]) -> None:
        """Wrap ``stream``; observed facts accumulate in ``sink``."""
        self._stream = stream
        self._sink = sink

    def __getattr__(self, name: str) -> Any:
        """Forward everything else (``text_stream``...) to the real stream."""
        return getattr(self._stream, name)

    def get_final_message(self) -> Any:
        """Return the real final message, recording its raw facts first."""
        final = self._stream.get_final_message()
        usage = getattr(final, "usage", None)
        dump = getattr(usage, "model_dump", None)
        self._sink["answering_model"] = getattr(final, "model", None)
        self._sink["request_id"] = getattr(self._stream, "request_id", None)
        self._sink["usage"] = dump() if callable(dump) else repr(usage)
        self._sink["stop_reason"] = getattr(final, "stop_reason", None)
        return final


class _StreamCM:
    """Context manager that hands the analyzer a ``_StreamSpy``."""

    def __init__(self, cm: Any, sink: dict[str, Any]) -> None:
        """Wrap the SDK's stream context manager ``cm``."""
        self._cm = cm
        self._sink = sink

    def __enter__(self) -> _StreamSpy:
        """Enter the real context manager and return the spy."""
        return _StreamSpy(self._cm.__enter__(), self._sink)

    def __exit__(self, *exc: object) -> Any:
        """Delegate to the real context manager."""
        return self._cm.__exit__(*exc)


class _MessagesSpy:
    """Record the kwargs of every ``stream()`` call (minus prompt content)."""

    def __init__(self, messages: Any, sink: dict[str, Any]) -> None:
        """Wrap the SDK ``client.messages`` namespace."""
        self._messages = messages
        self._sink = sink

    def stream(self, **kwargs: Any) -> _StreamCM:
        """Record the request kwargs, then open the real stream."""
        self._sink["kwargs_sent"] = {k: v for k, v in kwargs.items() if k not in _CONTENT_KEYS}
        return _StreamCM(self._messages.stream(**kwargs), self._sink)


class _ClientSpy:
    """Stand-in for ``anthropic.Anthropic`` exposing only the recorded ``messages``."""

    def __init__(self, client: Any, sink: dict[str, Any]) -> None:
        """Wrap the real ``client``."""
        self.messages = _MessagesSpy(client.messages, sink)
        # `_assert_client_has_credential` inspects the real client's auth fields.
        self.api_key = getattr(client, "api_key", None)
        self.auth_token = getattr(client, "auth_token", None)


def _probe_one(model: str | None, label: str) -> dict[str, Any]:
    """Make one call through ``analyzer._call_llm``; return its row and the raw facts."""
    rows: list[dict[str, Any]] = []
    sink: dict[str, Any] = {}
    with patch.object(analyzer, "_emit_call_log", rows.append):
        client = _ClientSpy(_get_client(), sink)
        text = analyzer._call_llm(
            client,  # type: ignore[arg-type]
            PROBE_PROMPT,
            call_kind="probe_175",
            username=PROBE_USER,
            model=model,
            max_tokens=PROBE_MAX_TOKENS,
        )
    row = rows[0] if rows else {}
    return {
        "label": label,
        "reply": text,
        "row_as_logged": row,
        "raw_from_sdk": sink,
        "cost_usd": hardening.compute_call_cost(row) if row else None,
    }


def main() -> int:
    """Run both probes and print one JSON document."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yes", action="store_true", help="Confirm the (sub-cent) paid calls")
    args = ap.parse_args()
    if not args.yes:
        print("Refusing to spend without --yes (2 calls, well under $0.01).")
        return 2
    if is_demo_mode():
        print("SARTOR_DEMO is set: no real call would be made.")
        return 2
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    results = [
        _probe_one(None, "sonnet (default pin)"),
        _probe_one(analyzer.HAIKU_MODEL, "haiku"),
    ]
    print(json.dumps(results, indent=2, default=str))
    total = sum(r["cost_usd"] or 0.0 for r in results)
    print(f"total cost from rows: ${total:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
