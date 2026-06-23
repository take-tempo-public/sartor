"""Unit tests for the S3 vector-index freshness check (window-8.5-findings S3-1).

`index_freshness` is pure — no git, no model, no embeddings — so it tests against a
tmp dir with hand-written manifests. The check is what stops the assistant from
silently citing moved lines after a refactor staled the (gitignored, local) index.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_vector_index import MANIFEST_NAME, index_freshness


def _write_manifest(index_dir: Path, sha: str) -> None:
    (index_dir / MANIFEST_NAME).write_text(
        json.dumps({"built_at_sha": sha, "chunk_count": 3, "dim": 256}),
        encoding="utf-8",
    )


def test_missing_manifest_reports_missing(tmp_path: Path) -> None:
    # Never built, or a pre-S3-1 index with no manifest.
    status = index_freshness("abc1230000", index_dir=tmp_path)
    assert status["state"] == "missing"
    assert status["built_at_sha"] is None


def test_matching_sha_is_fresh(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "abc1230000")
    status = index_freshness("abc1230000", index_dir=tmp_path)
    assert status["state"] == "fresh"
    assert status["built_at_sha"] == "abc1230000"


def test_different_sha_is_stale(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "old0000000")
    status = index_freshness("new9999999", index_dir=tmp_path)
    assert status["state"] == "stale"
    assert status["built_at_sha"] == "old0000000"
    assert status["current_sha"] == "new9999999"


def test_malformed_manifest_reports_missing(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("{ not valid json", encoding="utf-8")
    assert index_freshness("abc1230000", index_dir=tmp_path)["state"] == "missing"
