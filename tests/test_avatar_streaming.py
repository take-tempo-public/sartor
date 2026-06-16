"""Unit tests for `analyzer.avatar_answer_streaming` — the doc-grounded avatar.

LLM-free: `_call_llm_streaming` is monkeypatched to yield canned deltas then the
`_StreamDone` sentinel, so these exercise prompt construction + the chunk/done
contract without an API call.
"""

from __future__ import annotations

import analyzer
from recall.models import Audience, Context, Tier, Unit


def _ctx(units: tuple[Unit, ...] = (), *, truncated: bool = False) -> Context:
    return Context(query="q", units=units, token_estimate=0, truncated=truncated)


def _two_units() -> tuple[Unit, ...]:
    return (
        Unit("The grounding check rejects invented facts.", Tier.WIKI, "wiki",
             "[[generation-and-grounding]]", Audience.USER, "a" * 40, score=2.0),
        Unit("SYSTEM_PROMPT = ...", Tier.GIT, "git", "analyzer.py:353", Audience.DEV, "a" * 40, score=1.0),
    )


def _install_stub(monkeypatch, captured: dict, deltas=("Hello ", "world.")):
    def _fake_stream(client, user_prompt, **kwargs):
        captured["user_prompt"] = user_prompt
        captured["kwargs"] = kwargs
        yield from deltas
        yield analyzer._StreamDone("".join(deltas), "end_turn")

    monkeypatch.setattr(analyzer, "_call_llm_streaming", _fake_stream)


def test_yields_chunks_then_done(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(analyzer.avatar_answer_streaming(None, "how does grounding work?", _ctx(_two_units())))
    assert events[0] == ("chunk", "Hello ")
    assert events[1] == ("chunk", "world.")
    name, payload = events[-1]
    assert name == "done"
    assert payload["answer"] == "Hello world."


def test_done_payload_carries_citations_and_flags(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(
        analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units(), truncated=True), allow_dev=True)
    )
    _, payload = events[-1]
    assert payload["citations"] == ["[[generation-and-grounding]]", "analyzer.py:353"]
    assert payload["truncated"] is True
    assert payload["allow_dev"] is True


def test_prompt_includes_each_citation_and_question(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "explain the grounding check", _ctx(_two_units())))
    prompt = captured["user_prompt"]
    assert "[[generation-and-grounding]]" in prompt
    assert "analyzer.py:353" in prompt
    assert "explain the grounding check" in prompt


def test_dev_mode_marked_in_prompt(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units()), allow_dev=True))
    assert "<mode>dev</mode>" in captured["user_prompt"]


def test_user_mode_marked_in_prompt(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units()), allow_dev=False))
    assert "<mode>user</mode>" in captured["user_prompt"]


def test_avatar_uses_haiku_and_own_call_kind(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units())))
    assert captured["kwargs"]["model"] == analyzer.HAIKU_MODEL
    assert captured["kwargs"]["call_kind"] == "avatar_answer"
    assert captured["kwargs"]["system_prompt"] == analyzer.AVATAR_SYSTEM_PROMPT


def test_empty_context_renders_fallback(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(analyzer.avatar_answer_streaming(None, "q", _ctx(())))
    assert "no relevant context" in captured["user_prompt"]
    _, payload = events[-1]
    assert payload["citations"] == []


def test_avatar_prompt_version_is_distinct_from_prompt_version():
    # The avatar carries its own version so persona tweaks don't bump PROMPT_VERSION.
    assert analyzer.AVATAR_PROMPT_VERSION != analyzer.PROMPT_VERSION
    assert "AVATAR_SYSTEM_PROMPT" not in analyzer._BASE_SYSTEM_PROMPTS
