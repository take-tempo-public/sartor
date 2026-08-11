"""Pins the credential gate at the analyzer's single `client.messages` call site.

**The defect this pins.** With no `ANTHROPIC_API_KEY` and no `.api_key`,
`web_infra.clients._get_client()` returns `anthropic.Anthropic(api_key="")`. The
SDK accepts that at construction and only refuses at *request-build* time, with
a bare `TypeError` from `anthropic/_client.py::_validate_headers` — before any
network I/O, so `anthropic.APIConnectionError` never fires. Every LLM route in
`blueprints/` pairs exactly two handlers (`APIConnectionError` +
`LLMResponseError`), neither of which matches a `TypeError`, so it escaped to
Flask as an unhandled **500**. Observed on PR #117's required check, 3/3 in CI,
from `POST /api/applications/<id>/draft-summary`.

**What is deliberately NOT done, and is pinned as such.** A blanket
`except TypeError` around the SDK call would have closed the hole and swallowed
genuine programming errors along with it — a wrong argument or a `None` where a
dict belongs would become a polite 502 instead of a traceback.
`test_an_ordinary_typeerror_is_not_relabeled` is the assertion that keeps that
trade from being made later by accident.

Enumeration + the options weighed: `docs/dev/blast-radius/prior-apps-pipeline.md`,
second surface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import anthropic
import pytest

from analyzer import (
    LLMConfigurationError,
    LLMResponseError,
    _call_llm,
    _call_llm_streaming,
)

# Reuse the route fixture + seeder rather than cloning them (`draft_app` builds a
# migrated DB, a `Config(base_dir=tmp)` app, and a `casey` user + application).
from tests.test_draft_summary import _seed, draft_app  # noqa: F401


class _ExplodingMessages:
    """Any attribute access is a failed assertion — proves the SDK was never reached."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(
            f"the credential gate let the call through: client.messages.{name} was touched"
        )


def _keyless_client() -> anthropic.Anthropic:
    """Byte-for-byte what `_get_client()` builds on a box with no key configured."""
    client = anthropic.Anthropic(api_key="")
    client.messages = _ExplodingMessages()  # type: ignore[misc,assignment]  # cached_property: instance dict wins
    return client


def _drain(gen: Any) -> list[Any]:
    return list(gen)


# ---------------------------------------------------------------------------
# Analyzer boundary
# ---------------------------------------------------------------------------


class TestCredentialGate:
    def test_keyless_client_raises_a_configuration_error_before_any_sdk_call(self) -> None:
        with pytest.raises(LLMConfigurationError) as excinfo:
            _drain(_call_llm_streaming(_keyless_client(), "hi", call_kind="draft_summary"))

        # The error names the cause AND the remediation — the whole point of the
        # change is that "no key" stops being an anonymous 500.
        detail = excinfo.value.validation_error
        assert "no credential" in detail
        assert "ANTHROPIC_API_KEY" in detail
        assert ".api_key" in detail
        assert "draft_summary" in detail, "the failing call kind must be attributable"
        assert "not configured" in str(excinfo.value)

    def test_it_is_catchable_by_every_route_that_already_handles_llmresponseerror(self) -> None:
        """The design decision, pinned: 19 `except LLMResponseError` sites across
        five blueprint modules inherit this without a single edit. If someone
        later 'cleans up' the inheritance, every one of them starts 500-ing
        again — which is the original defect."""
        assert issubclass(LLMConfigurationError, LLMResponseError)
        with pytest.raises(LLMResponseError):
            _drain(_call_llm_streaming(_keyless_client(), "hi", call_kind="analyze"))

    def test_the_non_streaming_wrapper_inherits_the_gate(self) -> None:
        with pytest.raises(LLMConfigurationError):
            _call_llm(_keyless_client(), "hi", call_kind="clarify")

    def test_the_failure_still_emits_its_telemetry_row(self, tmp_path: Path) -> None:
        """Observability is unchanged: a failed call has always written exactly
        one `status="error"` row, and still does. `tests/conftest.py`'s autouse
        fixture already points `LOG_PATH` at this same `tmp_path`."""
        with pytest.raises(LLMConfigurationError):
            _drain(_call_llm_streaming(_keyless_client(), "hi", call_kind="draft_summary"))

        rows = [
            json.loads(line)
            for line in (tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(rows) == 1, rows
        assert rows[0]["status"] == "error"
        assert rows[0]["call"] == "draft_summary"

    def test_an_ordinary_typeerror_is_not_relabeled(self) -> None:
        """The anti-blanket-catch assertion. A real programming error inside the
        streaming call must still reach the developer as a `TypeError`."""

        class _BoomMessages:
            def stream(self, **_kwargs: Any) -> Any:
                raise TypeError("unsupported operand type(s) for +: 'int' and 'str'")

        client = anthropic.Anthropic(api_key="sk-not-a-real-key")
        client.messages = _BoomMessages()  # type: ignore[misc,assignment]  # cached_property: instance dict wins

        with pytest.raises(TypeError) as excinfo:
            _drain(_call_llm_streaming(client, "hi", call_kind="analyze"))
        assert not isinstance(excinfo.value, LLMConfigurationError)

    def test_the_sdk_credential_typeerror_is_relabeled(self) -> None:
        """Version-drift backstop: if a future SDK reaches its own auth refusal by
        a route the pre-check cannot see, it is still not a 500."""

        class _AuthRefusingMessages:
            def stream(self, **_kwargs: Any) -> Any:
                raise TypeError(
                    '"Could not resolve authentication method. Expected either '
                    'api_key or auth_token to be set."'
                )

        client = anthropic.Anthropic(api_key="sk-not-a-real-key")
        client.messages = _AuthRefusingMessages()  # type: ignore[misc,assignment]  # cached_property: instance dict wins

        with pytest.raises(LLMConfigurationError):
            _drain(_call_llm_streaming(client, "hi", call_kind="analyze"))

    def test_a_client_exposing_neither_slot_is_passed_straight_through(self) -> None:
        """`install_llm_stubs` patches `_get_client` to `lambda: None`, and nine
        tests in `test_extract_experiences.py` pass `MagicMock(spec=
        anthropic.Anthropic)` — which has no `api_key`, since the SDK sets it as
        an instance attribute. Neither may be read as 'no credential': the first
        must keep its loud missing-stub `AttributeError`, the second must keep
        working."""
        with pytest.raises(AttributeError):
            _drain(_call_llm_streaming(None, "hi", call_kind="analyze"))  # type: ignore[arg-type]

    def test_a_keyed_client_reaches_the_sdk_untouched(self) -> None:
        """The happy path must be byte-identical in behavior."""
        seen: dict[str, Any] = {}

        class _RecordingStream:
            text_stream = iter(["hello"])

            def get_final_message(self) -> Any:
                class _Usage:
                    input_tokens = 10
                    output_tokens = 2
                    cache_creation_input_tokens = 0
                    cache_read_input_tokens = 0

                class _Final:
                    usage = _Usage()
                    stop_reason = "end_turn"

                return _Final()

            def __enter__(self) -> Any:
                return self

            def __exit__(self, *_a: Any) -> None:
                return None

        class _Messages:
            def stream(self, **kwargs: Any) -> Any:
                seen.update(kwargs)
                return _RecordingStream()

        client = anthropic.Anthropic(api_key="sk-not-a-real-key")
        client.messages = _Messages()  # type: ignore[misc,assignment]  # cached_property: instance dict wins

        out = _call_llm(client, "hi", call_kind="analyze")
        assert out == "hello"
        assert seen, "the SDK call was never made"


# ---------------------------------------------------------------------------
# Route boundary — the surface the red CI check actually observed
# ---------------------------------------------------------------------------


class TestDraftSummaryRouteWithNoCredential:
    def test_no_key_is_a_deliberate_error_not_an_unhandled_500(
        self,
        draft_app: Any,  # noqa: F811
    ) -> None:
        """Reproduces the CI condition at the route: a real keyless client, the
        REAL `analyzer.draft_positioning_summary`, no stub anywhere. On HEAD
        before this change the SDK's `TypeError` escaped both route handlers and
        Flask returned 500."""
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)

        with patch("blueprints.applications._get_client", _keyless_client):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/draft-summary",
                json={"context_path": ctx_path},
            )

        body = r.get_data(as_text=True)
        assert r.status_code != 500, f"still an unhandled server error: {body}"
        assert r.status_code == 502, body
        detail = r.get_json().get("detail", "")
        assert "ANTHROPIC_API_KEY" in detail, f"the response does not name the cause: {body}"
        assert "no credential" in detail, body

    def test_the_happy_path_is_unchanged(self, draft_app: Any) -> None:  # noqa: F811
        """Guard against the gate leaking into the keyed path: with the analyzer
        stubbed exactly as the existing route tests stub it, the route still
        200s and persists. (`draft_app` patches `_get_client` to `object()`,
        which exposes neither credential slot — the pass-through case.)"""
        _app, output_dir = draft_app
        _cid, aid, ctx_path = _seed(output_dir)

        def _stub(client: Any, context_set: Any, *, username: str = "", run_id: str = "") -> Any:
            return {"summary": "Kept working. Second sentence."}

        with patch("analyzer.draft_positioning_summary", _stub):
            client = _app.app.test_client()
            r = client.post(
                f"/api/applications/{aid}/draft-summary",
                json={"context_path": ctx_path},
            )
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json()["summary_text"] == "Kept working. Second sentence."
