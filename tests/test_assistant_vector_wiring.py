"""Wiring tests for the S3 vector tier's activation logic in `blueprints/assistant.py`.

The tier is 'on when available': it joins the source list (and `Tier.VECTOR` joins the
scope) only when BOTH the embedder loads (model present) AND a built index exists. These
drive that gate without a model download.
"""

from __future__ import annotations

from blueprints import assistant
from recall import Tier, VectorSource


def _dummy_embedder():
    """Stands in for `_make_embedder()` → returns a (never-called here) embedder."""
    return lambda texts: None


def test_vector_tier_absent_without_model(monkeypatch):
    monkeypatch.setattr(assistant, "_make_embedder", lambda: None)
    sources = assistant._build_sources([])
    assert not any(isinstance(s, VectorSource) for s in sources)
    assert Tier.VECTOR not in assistant._enabled_tiers(sources)


def test_vector_tier_present_with_model_and_index(monkeypatch, tmp_path):
    (tmp_path / "embeddings.npy").write_bytes(b"\x00")  # index_exists() only checks presence
    monkeypatch.setattr(assistant, "_VECTOR_INDEX_DIR", tmp_path)
    monkeypatch.setattr(assistant, "_make_embedder", _dummy_embedder)
    sources = assistant._build_sources([])
    assert any(isinstance(s, VectorSource) for s in sources)
    assert Tier.VECTOR in assistant._enabled_tiers(sources)


def test_vector_tier_absent_when_index_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant, "_VECTOR_INDEX_DIR", tmp_path)  # empty dir: no sidecar
    monkeypatch.setattr(assistant, "_make_embedder", _dummy_embedder)
    sources = assistant._build_sources([])
    assert not any(isinstance(s, VectorSource) for s in sources)
    assert Tier.VECTOR not in assistant._enabled_tiers(sources)
