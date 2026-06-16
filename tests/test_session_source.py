"""Unit tests for `recall.sources.SessionSource` — the S5-P1 session buffer."""

from __future__ import annotations

from recall.models import Audience, Scope, Tier
from recall.sources import SessionSource


def _scope() -> Scope:
    return Scope()


def test_empty_search_returns_empty():
    src = SessionSource()
    assert list(src.search("anything", _scope())) == []


def test_observe_adds_searchable_unit():
    src = SessionSource()
    src.observe("I asked about the grounding check yesterday.")
    results = list(src.search("grounding check", _scope()))
    assert len(results) == 1
    assert "grounding" in results[0].text


def test_all_units_have_session_tier_and_user_audience():
    src = SessionSource()
    src.observe("first turn about templates")
    src.observe("second turn about templates")
    results = list(src.search("templates", _scope()))
    assert len(results) == 2
    assert all(u.tier is Tier.SESSION for u in results)
    assert all(u.audience is Audience.USER for u in results)


def test_citation_default_is_turn_numbered():
    src = SessionSource()
    src.observe("alpha bravo")
    src.observe("charlie alpha")
    cites = {u.citation for u in src.search("alpha", _scope())}
    assert cites == {"session:turn-1", "session:turn-2"}


def test_explicit_citation_is_kept():
    src = SessionSource()
    src.observe("delta echo", citation="session:custom")
    results = list(src.search("delta", _scope()))
    assert results[0].citation == "session:custom"


def test_blank_turn_is_ignored():
    src = SessionSource()
    src.observe("   ")
    assert list(src.search("whatever", _scope())) == []


def test_refresh_is_noop():
    src = SessionSource()
    src.observe("foxtrot golf")
    src.refresh(None)
    src.refresh("deadbeef")
    assert len(list(src.search("foxtrot", _scope()))) == 1
