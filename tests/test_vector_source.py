"""Unit tests for `recall.sources.VectorSource` — the S3 static-embedding tier.

A deterministic FAKE embedder (token-hash bag-of-words → L2-normalized) stands in for
model2vec, so the suite needs no model download and runs in the default `pytest`. The
fake keeps the one property ranking depends on: texts with overlapping tokens are
cosine-similar.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
import pytest

from recall import Audience, Scope, Tier
from recall.sources import Document, VectorSource

_DIM = 64
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _bucket(token: str) -> int:
    return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % _DIM


def _fake_embedder(texts):
    """Deterministic bag-of-token-hash embedder → (n, _DIM) L2-normalized float32."""
    rows = []
    for text in texts:
        vec = np.zeros(_DIM, dtype=np.float32)
        for tok in _TOKEN_RE.findall(text.lower()):
            vec[_bucket(tok)] += 1.0
        norm = float(np.linalg.norm(vec))
        rows.append(vec / norm if norm else vec)
    return np.asarray(rows, dtype=np.float32) if rows else np.empty((0, _DIM), dtype=np.float32)


class _CountingEmbedder:
    """The fake embedder, recording how many texts it embedded (for the
    incremental-reuse assertion)."""

    def __init__(self):
        self.embedded = 0

    def __call__(self, texts):
        batch = list(texts)
        self.embedded += len(batch)
        return _fake_embedder(batch)


def _all_dev(_path: str) -> Audience:
    return Audience.DEV


def _make_source(index_dir, provider=None, **kw):
    return VectorSource(index_dir, _fake_embedder, _all_dev, document_provider=provider, **kw)


def test_refresh_builds_sidecar(tmp_path):
    docs = [Document("a.py", "alpha beta gamma", "sha1"), Document("b.py", "delta epsilon", "sha1")]
    _make_source(tmp_path, provider=lambda: list(docs)).refresh(None)
    assert (tmp_path / "embeddings.npy").exists()
    assert (tmp_path / "chunks.json").exists()
    assert VectorSource.index_exists(tmp_path)


def test_search_returns_vector_units(tmp_path):
    docs = [Document("a.py", "alpha beta gamma", "shaA"), Document("b.py", "delta epsilon zeta", "shaB")]
    src = _make_source(tmp_path, provider=lambda: list(docs))
    src.refresh(None)
    results = list(src.search("alpha beta", Scope()))
    assert results
    top = results[0]
    assert top.tier is Tier.VECTOR
    assert top.source_id == "vector"
    assert top.citation == "a.py:1"
    assert top.audience is Audience.DEV
    assert top.sha == "shaA"
    assert top.score > 0


def test_search_ranks_more_similar_first(tmp_path):
    docs = [
        Document("match.py", "kubernetes deployment scaling replicas", "s"),
        Document("other.py", "banana smoothie recipe", "s"),
    ]
    src = _make_source(tmp_path, provider=lambda: list(docs))
    src.refresh(None)
    results = list(src.search("kubernetes scaling", Scope()))
    assert results[0].citation == "match.py:1"


def test_audience_resolver_applied(tmp_path):
    docs = [Document("readme.md", "alpha beta", "s")]
    src = VectorSource(tmp_path, _fake_embedder, lambda _p: Audience.USER, document_provider=lambda: list(docs))
    src.refresh(None)
    results = list(src.search("alpha", Scope()))
    assert results and all(u.audience is Audience.USER for u in results)


def test_missing_index_returns_empty(tmp_path):
    assert list(_make_source(tmp_path).search("anything", Scope())) == []


def test_refresh_without_provider_is_noop(tmp_path):
    _make_source(tmp_path).refresh(None)
    assert not VectorSource.index_exists(tmp_path)


def test_empty_query_returns_empty(tmp_path):
    src = _make_source(tmp_path, provider=lambda: [Document("a.py", "alpha beta", "s")])
    src.refresh(None)
    assert list(src.search("   ", Scope())) == []


def test_top_k_caps_results(tmp_path):
    docs = [Document(f"f{i}.py", f"alpha token{i}", "s") for i in range(10)]
    src = _make_source(tmp_path, provider=lambda: list(docs), top_k=3)
    src.refresh(None)
    assert len(list(src.search("alpha", Scope()))) == 3


def test_min_score_floor_filters(tmp_path):
    # min_score above the max possible cosine (1.0 for normalized vectors) → drop all.
    src = _make_source(tmp_path, provider=lambda: [Document("a.py", "alpha beta gamma", "s")], min_score=2.0)
    src.refresh(None)
    assert list(src.search("alpha beta gamma", Scope())) == []


def test_incremental_reuse_only_reembeds_changed(tmp_path):
    counter = _CountingEmbedder()
    docs = [Document("a.py", "alpha beta", "s1"), Document("b.py", "gamma delta", "s1")]
    src = VectorSource(tmp_path, counter, _all_dev, document_provider=lambda: list(docs))
    src.refresh(None)
    first = counter.embedded
    assert first == 2  # two single-chunk docs, both new

    docs[1] = Document("b.py", "gamma delta epsilon changed", "s2")  # only b.py changes
    src.refresh(None)
    assert counter.embedded - first == 1  # a.py reused; only the changed chunk re-embedded


def test_removed_document_drops_from_index(tmp_path):
    docs = [Document("a.py", "alpha beta", "s"), Document("b.py", "gamma delta", "s")]
    holder = {"docs": list(docs)}
    src = VectorSource(tmp_path, _fake_embedder, _all_dev, document_provider=lambda: list(holder["docs"]))
    src.refresh(None)
    holder["docs"] = [docs[0]]  # b.py removed
    src.refresh(None)
    results = list(src.search("gamma delta", Scope()))
    assert all(u.citation != "b.py:1" for u in results)


def test_multi_chunk_document_has_distinct_citations(tmp_path):
    body = "\n".join(f"line {i} alpha" for i in range(100))  # > chunk_lines → multiple windows
    src = _make_source(tmp_path, provider=lambda: [Document("big.py", body, "s")], chunk_lines=40, chunk_overlap=10)
    src.refresh(None)
    results = list(src.search("alpha", Scope()))
    cites = [u.citation for u in results]
    assert len(cites) == len(set(cites)) >= 2  # distinct path:line citations per window


def test_chunk_param_validation(tmp_path):
    with pytest.raises(ValueError):
        VectorSource(tmp_path, _fake_embedder, _all_dev, chunk_lines=10, chunk_overlap=10)
    with pytest.raises(ValueError):
        VectorSource(tmp_path, _fake_embedder, _all_dev, chunk_lines=0)
