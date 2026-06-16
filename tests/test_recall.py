"""Unit tests for the `recall/` Memory substrate (Stage 0 skeleton, Sprint 7.4).

These prove the seams are right — the Stage 0 deliverable. They cover the
provenance stamp, the access/disclosure plane, RRF fusion, budget packing, and
`assemble()` end to end over the in-memory reference source. All deterministic
and LLM-free.
"""

import pytest

from recall import Audience, Context, Scope, Source, Tier, Unit, assemble
from recall.assemble import _estimate_tokens, _pack_to_budget, _rrf_fuse
from recall.memory_source import InMemorySource
from recall.planes import allowed_audiences, filter_units, within_scope


def _unit(
    text: str = "alpha beta",
    *,
    tier: Tier = Tier.WIKI,
    source_id: str = "s1",
    citation: str = "[[p]]",
    audience: Audience = Audience.USER,
    sha: str = "abc123",
    score: float = 0.0,
) -> Unit:
    return Unit(
        text=text,
        tier=tier,
        source_id=source_id,
        citation=citation,
        audience=audience,
        sha=sha,
        score=score,
    )


class TestUnitStamp:
    """The provenance plane — a Unit cannot exist without its stamp."""

    def test_rejects_empty_text(self):
        with pytest.raises(ValueError):
            _unit(text="   ")

    def test_rejects_empty_citation(self):
        with pytest.raises(ValueError):
            _unit(citation="")

    def test_is_frozen(self):
        from dataclasses import FrozenInstanceError

        unit = _unit()
        # Deliberate illegal mutation: the frozen stamp must reject it. setattr
        # (not direct assignment) keeps this clean for both ruff and mypy.
        with pytest.raises(FrozenInstanceError):
            setattr(unit, "score", 9.9)  # noqa: B010


class TestAccessPlane:
    """The access/disclosure plane — audience + tier gating."""

    def test_user_scope_excludes_dev(self):
        assert allowed_audiences(Scope()) == frozenset({Audience.USER})
        assert within_scope(_unit(audience=Audience.USER), Scope()) is True
        assert within_scope(_unit(audience=Audience.DEV), Scope()) is False

    def test_dev_toggle_admits_dev(self):
        scope = Scope(allow_dev=True)
        assert allowed_audiences(scope) == frozenset({Audience.USER, Audience.DEV})
        assert within_scope(_unit(audience=Audience.DEV), scope) is True

    def test_tier_gate(self):
        # VECTOR is not in the default enabled tiers ({WIKI, GIT}).
        assert within_scope(_unit(tier=Tier.VECTOR), Scope()) is False
        admit_vector = Scope(enabled_tiers=frozenset({Tier.VECTOR}))
        assert within_scope(_unit(tier=Tier.VECTOR), admit_vector) is True

    def test_filter_preserves_order(self):
        units = [
            _unit(citation="[[a]]", audience=Audience.USER),
            _unit(citation="g.py:1", audience=Audience.DEV),
            _unit(citation="[[b]]", audience=Audience.USER),
        ]
        kept = filter_units(units, Scope())
        assert [u.citation for u in kept] == ["[[a]]", "[[b]]"]


class TestRrfFusion:
    """Reciprocal Rank Fusion — dedup by stamp, deterministic order."""

    def test_dedup_accumulates_score(self):
        unit = _unit(source_id="s", citation="[[a]]", text="alpha")
        fused = _rrf_fuse([[unit], [unit]])
        assert len(fused) == 1
        assert fused[0].score == pytest.approx(2.0 / 61)

    def test_orders_by_fused_score(self):
        pool = [
            _unit(source_id="s", citation="[[a]]", text="alpha"),
            _unit(source_id="s", citation="[[b]]", text="beta"),
        ]
        fused = _rrf_fuse([pool])
        assert [u.citation for u in fused] == ["[[a]]", "[[b]]"]

    def test_stamp_preserved(self):
        unit = _unit(text="alpha beta", citation="[[a]]", sha="deadbeef")
        (fused,) = _rrf_fuse([[unit]])
        assert fused.text == "alpha beta"
        assert fused.citation == "[[a]]"
        assert fused.sha == "deadbeef"
        assert fused.score != unit.score  # only the score is rewritten

    def test_empty(self):
        assert _rrf_fuse([]) == []


class TestBudgetPacking:
    """Token-budget packing — highest-scoring prefix that fits."""

    def test_truncates_when_over_budget(self):
        units = [
            _unit(text="abcdefghijklmnop", citation="[[1]]"),  # 16 chars → 4 tokens
            _unit(text="abcdefgh", citation="[[2]]"),  # 8 → 2
            _unit(text="ijklmnop", citation="[[3]]"),  # 8 → 2
        ]
        packed, total, truncated = _pack_to_budget(units, budget=5)
        assert [u.citation for u in packed] == ["[[1]]"]
        assert total == 4
        assert truncated is True

    def test_fits_within_budget(self):
        units = [
            _unit(text="abcdefghijklmnop", citation="[[1]]"),
            _unit(text="abcdefgh", citation="[[2]]"),
        ]
        packed, total, truncated = _pack_to_budget(units, budget=100)
        assert len(packed) == 2
        assert total == 6
        assert truncated is False

    def test_estimate_tokens(self):
        assert _estimate_tokens("") == 1  # floor of 1
        assert _estimate_tokens("abcdefgh") == 2


class TestAssembleEndToEnd:
    """`assemble()` over the in-memory reference source — the whole seam."""

    def _source(self) -> InMemorySource:
        return InMemorySource(
            "mix",
            [
                _unit(text="alpha beta gamma", source_id="wiki", citation="[[a]]",
                      audience=Audience.USER, tier=Tier.WIKI),
                _unit(text="alpha delta", source_id="wiki", citation="[[b]]",
                      audience=Audience.USER, tier=Tier.WIKI),
                _unit(text="alpha epsilon", source_id="git", citation="g.py:1",
                      audience=Audience.DEV, tier=Tier.GIT),
            ],
        )

    def test_reference_source_satisfies_protocol(self):
        assert isinstance(self._source(), Source)

    def test_user_scope_drops_dev_units(self):
        ctx = assemble("alpha", Scope(), [self._source()])
        assert isinstance(ctx, Context)
        assert [u.citation for u in ctx.units] == ["[[a]]", "[[b]]"]
        assert all(u.audience is Audience.USER for u in ctx.units)
        assert ctx.truncated is False
        # Stamp preserved — assemble never rewrites text.
        assert ctx.units[0].text == "alpha beta gamma"

    def test_dev_toggle_admits_dev_units(self):
        ctx = assemble("alpha", Scope(allow_dev=True), [self._source()])
        assert "g.py:1" in [u.citation for u in ctx.units]
        assert len(ctx.units) == 3

    def test_budget_truncates(self):
        ctx = assemble("alpha", Scope(allow_dev=True, token_budget=5), [self._source()])
        assert [u.citation for u in ctx.units] == ["[[a]]"]
        assert ctx.truncated is True

    def test_no_sources_is_empty(self):
        ctx = assemble("alpha", Scope())
        assert ctx.units == ()
        assert ctx.token_estimate == 0
        assert ctx.truncated is False
