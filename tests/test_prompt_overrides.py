"""Tests for the prompt-override primitive (eval tuning loop, v1.0.4).

The primitive lets an eval run inject a candidate system prompt without editing
the persona constants. Two invariants are load-bearing and tested here:

1. **Default path byte-identical.** With no override active, `_resolve_system_prompt`
   returns the *identical* constant object and `effective_prompt_version()` returns
   `PROMPT_VERSION` verbatim — so the bytes sent to the API and the logged version
   are unchanged (production cache + score-over-time attribution untouched).
2. **Candidate runs quarantined.** Inside a `prompt_overrides(...)` context every
   LLM call logs a stable `candidate:<hash>` version and sends the candidate text.

The integration tests exercise the real `_call_llm_streaming` with a fake
Anthropic client, so the SYSTEM_PROMPT fallback resolution and the per-call
version logging are tested end to end (not just the helpers in isolation).
"""

import pytest

import analyzer
from analyzer import (
    _BASE_SYSTEM_PROMPTS,
    PROMPT_VERSION,
    _resolve_system_prompt,
    effective_prompt_version,
    prompt_overrides,
)

# --------------------------------------------------------------------------- #
# effective_prompt_version()
# --------------------------------------------------------------------------- #

def test_effective_version_default_is_prompt_version():
    assert effective_prompt_version() == PROMPT_VERSION


def test_effective_version_candidate_when_overridden():
    with prompt_overrides({"SYSTEM_PROMPT": "candidate persona"}):
        v = effective_prompt_version()
    assert v.startswith("candidate:")
    assert v != PROMPT_VERSION
    # 12 hex chars after the prefix.
    digest = v.split(":", 1)[1]
    assert len(digest) == 12 and all(c in "0123456789abcdef" for c in digest)


def test_effective_version_resets_after_context():
    with prompt_overrides({"SYSTEM_PROMPT": "x"}):
        assert effective_prompt_version().startswith("candidate:")
    assert effective_prompt_version() == PROMPT_VERSION


def test_candidate_hash_is_stable_for_same_overrides():
    with prompt_overrides({"SYSTEM_PROMPT": "abc"}):
        first = effective_prompt_version()
    with prompt_overrides({"SYSTEM_PROMPT": "abc"}):
        second = effective_prompt_version()
    assert first == second


def test_candidate_hash_differs_for_different_overrides():
    with prompt_overrides({"SYSTEM_PROMPT": "abc"}):
        a = effective_prompt_version()
    with prompt_overrides({"SYSTEM_PROMPT": "xyz"}):
        b = effective_prompt_version()
    assert a != b


def test_candidate_hash_is_order_independent():
    # Canonical JSON (sort_keys) → key order in the dict literal must not matter.
    with prompt_overrides({"SYSTEM_PROMPT": "a", "CLARIFY_SYSTEM_PROMPT": "b"}):
        a = effective_prompt_version()
    with prompt_overrides({"CLARIFY_SYSTEM_PROMPT": "b", "SYSTEM_PROMPT": "a"}):
        b = effective_prompt_version()
    assert a == b


# --------------------------------------------------------------------------- #
# _resolve_system_prompt() — the byte-identity guard
# --------------------------------------------------------------------------- #

def test_resolver_returns_identical_constant_outside_context():
    # `is` (identity), not just `==`: the exact same object is sent to the API,
    # which is what guarantees the prompt cache is unaffected on the default path.
    for name, const in _BASE_SYSTEM_PROMPTS.items():
        assert _resolve_system_prompt(name) is const


def test_resolver_returns_override_inside_context():
    with prompt_overrides({"CLARIFY_SYSTEM_PROMPT": "CANDIDATE CLARIFY"}):
        assert _resolve_system_prompt("CLARIFY_SYSTEM_PROMPT") == "CANDIDATE CLARIFY"
        # An un-overridden name still resolves to its identical baseline constant.
        assert _resolve_system_prompt("SYSTEM_PROMPT") is analyzer.SYSTEM_PROMPT


def test_resolver_resets_after_context():
    with prompt_overrides({"SYSTEM_PROMPT": "x"}):
        pass
    assert _resolve_system_prompt("SYSTEM_PROMPT") is analyzer.SYSTEM_PROMPT


# --------------------------------------------------------------------------- #
# prompt_overrides() context manager
# --------------------------------------------------------------------------- #

def test_unknown_key_raises_value_error():
    with pytest.raises(ValueError, match="Unknown prompt override key"):
        with prompt_overrides({"NOT_A_REAL_PROMPT": "x"}):
            pass


def test_empty_and_none_overrides_are_noops():
    with prompt_overrides({}):
        assert effective_prompt_version() == PROMPT_VERSION
        assert _resolve_system_prompt("SYSTEM_PROMPT") is analyzer.SYSTEM_PROMPT
    with prompt_overrides(None):
        assert effective_prompt_version() == PROMPT_VERSION


def test_context_resets_even_on_exception():
    try:
        with prompt_overrides({"SYSTEM_PROMPT": "x"}):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert effective_prompt_version() == PROMPT_VERSION
    assert _resolve_system_prompt("SYSTEM_PROMPT") is analyzer.SYSTEM_PROMPT


def test_registry_covers_every_named_system_prompt_constant():
    # Drift guard: if someone adds a new *_SYSTEM_PROMPT persona constant but
    # forgets to register it, it silently becomes non-overridable. Catch that.
    module_prompts = {
        n for n in dir(analyzer)
        if n.endswith("SYSTEM_PROMPT") and isinstance(getattr(analyzer, n), str)
    }
    assert module_prompts == set(_BASE_SYSTEM_PROMPTS)


# --------------------------------------------------------------------------- #
# Integration — through the real _call_llm_streaming via a fake client
# --------------------------------------------------------------------------- #

class _FakeUsage:
    input_tokens = 10
    output_tokens = 5
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _FakeFinal:
    usage = _FakeUsage()
    stop_reason = "end_turn"


class _FakeStream:
    def __init__(self, text):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield self._text

    def get_final_message(self):
        return _FakeFinal()


class _FakeMessages:
    def __init__(self, captured):
        self._captured = captured

    def stream(self, **kwargs):
        self._captured.append(kwargs)
        return _FakeStream('{"ok": true}')


class _FakeClient:
    def __init__(self, captured):
        self.messages = _FakeMessages(captured)


def _drive_call(monkeypatch, *, call_kind, system_prompt=""):
    """Run a single _call_llm through the real streaming path with a fake client.

    Returns (system_text_sent, logged_prompt_version).
    """
    captured: list[dict] = []
    logs: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", lambda rec: logs.append(rec))
    analyzer._call_llm(
        _FakeClient(captured), "USER PROMPT",
        call_kind=call_kind, username="u", run_id="r",
        system_prompt=system_prompt,
    )
    system_text = captured[-1]["system"][0]["text"]
    return system_text, logs[-1]["prompt_version"]


def test_integration_default_path_sends_base_system_and_base_version(monkeypatch):
    # A SYSTEM_PROMPT-default call (e.g. generate) with no override: the fallback
    # resolves to the SYSTEM_PROMPT constant and the logged version is PROMPT_VERSION.
    system_text, version = _drive_call(monkeypatch, call_kind="generate")
    assert system_text == analyzer.SYSTEM_PROMPT
    assert version == PROMPT_VERSION


def test_integration_candidate_overrides_system_and_version(monkeypatch):
    with prompt_overrides({"SYSTEM_PROMPT": "CANDIDATE SYSTEM"}):
        system_text, version = _drive_call(monkeypatch, call_kind="generate")
    assert system_text == "CANDIDATE SYSTEM"
    assert version.startswith("candidate:")


def test_integration_named_override_flows_through(monkeypatch):
    # Mirrors what the clarify() call site does: pass the resolved named prompt.
    # Outside the context it's the identical baseline; inside, the candidate text.
    _, version_default = _drive_call(
        monkeypatch, call_kind="clarify",
        system_prompt=_resolve_system_prompt("CLARIFY_SYSTEM_PROMPT"),
    )
    assert version_default == PROMPT_VERSION
    with prompt_overrides({"CLARIFY_SYSTEM_PROMPT": "CANDIDATE CLARIFY"}):
        system_text, version = _drive_call(
            monkeypatch, call_kind="clarify",
            system_prompt=_resolve_system_prompt("CLARIFY_SYSTEM_PROMPT"),
        )
    assert system_text == "CANDIDATE CLARIFY"
    assert version.startswith("candidate:")
