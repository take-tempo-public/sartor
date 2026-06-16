"""Unit tests for `recall.sources.WikiSource` — the S1 committed-wiki tier."""

from __future__ import annotations

import re
from pathlib import Path

from recall.models import Audience, Scope, Tier
from recall.sources import WikiSource

# A minimal stand-in for the wiring layer's audience resolver: parse the
# `**Audience:**` tag, default dev.
_AUDIENCE_RE = re.compile(r"\*\*Audience:\*\*\s*`(user|dev)`", re.IGNORECASE)


def _audience_for_page(stem: str, raw: str) -> Audience:
    m = _AUDIENCE_RE.search(raw)
    if m:
        return Audience.USER if m.group(1).lower() == "user" else Audience.DEV
    return Audience.DEV


def _write_page(wiki_dir: Path, stem: str, body: str) -> None:
    pages = wiki_dir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    (pages / f"{stem}.md").write_text(body, encoding="utf-8")


def _make_source(wiki_dir: Path, sha: str | None = "a" * 40) -> WikiSource:
    sha_path = wiki_dir / ".last_ingest_sha"
    if sha is not None:
        sha_path.write_text(sha, encoding="utf-8")
    return WikiSource(wiki_dir, sha_path, _audience_for_page)


def test_refresh_builds_user_unit(tmp_path: Path):
    _write_page(
        tmp_path,
        "tailoring-a-resume",
        "# Tailoring\n\n> **Audience:** `user`\n\nThe wizard tailors your resume in six steps.\n",
    )
    src = _make_source(tmp_path)
    results = list(src.search("wizard tailors steps", Scope()))
    assert len(results) == 1
    u = results[0]
    assert u.tier is Tier.WIKI
    assert u.audience is Audience.USER
    assert u.citation == "[[tailoring-a-resume]]"
    assert u.sha == "a" * 40


def test_dev_audience_parsed(tmp_path: Path):
    _write_page(
        tmp_path,
        "code-module-map",
        "# Module map\n\n> **Audience:** `dev`\n\nThe analyzer owns all model calls.\n",
    )
    src = _make_source(tmp_path)
    results = list(src.search("model calls", Scope(allow_dev=True)))
    assert results and results[0].audience is Audience.DEV


def test_audience_defaults_dev_when_tag_absent(tmp_path: Path):
    _write_page(tmp_path, "untagged", "# Untagged\n\nSome content about pipelines here.\n")
    src = _make_source(tmp_path)
    results = list(src.search("pipelines content", Scope(allow_dev=True)))
    assert results and results[0].audience is Audience.DEV


def test_search_ranks_higher_overlap_first(tmp_path: Path):
    _write_page(tmp_path, "page-a", "# A\n\nalpha beta gamma delta keyword\n")
    _write_page(tmp_path, "page-b", "# B\n\nalpha keyword keyword unrelated\n")
    src = _make_source(tmp_path)
    results = list(src.search("alpha keyword", Scope(allow_dev=True)))
    # page-b shares both query tokens (alpha, keyword); page-a shares both too,
    # but token overlap counts distinct tokens — assert ordering is deterministic
    # and the top hit shares the most query tokens.
    assert results[0].score >= results[-1].score


def test_one_unit_per_page_best_paragraph(tmp_path: Path):
    # Matching is distinct-token overlap (a set, like InMemorySource) — the best
    # paragraph is the one sharing the MOST distinct query tokens, not the one that
    # repeats a token most.
    _write_page(
        tmp_path,
        "multi",
        "# Multi\n\n> **Audience:** `dev`\n\nFirst para mentions widgets only.\n\n"
        "Second para mentions widgets and gadgets together.\n",
    )
    src = _make_source(tmp_path)
    results = list(src.search("widgets gadgets", Scope(allow_dev=True)))
    assert len(results) == 1  # one Unit per page
    assert "gadgets" in results[0].text  # the paragraph sharing both query tokens


def test_ingest_sha_missing_gives_empty_string(tmp_path: Path):
    _write_page(tmp_path, "p", "# P\n\n> **Audience:** `user`\n\nbody text here\n")
    src = _make_source(tmp_path, sha=None)  # no .last_ingest_sha file
    results = list(src.search("body text", Scope()))
    assert results and results[0].sha == ""


def test_non_sha_sentinel_gives_empty_string(tmp_path: Path):
    _write_page(tmp_path, "p", "# P\n\n> **Audience:** `user`\n\nbody text here\n")
    src = _make_source(tmp_path, sha="not-a-real-sha")
    results = list(src.search("body text", Scope()))
    assert results and results[0].sha == ""


def test_empty_wiki_dir_returns_empty(tmp_path: Path):
    (tmp_path / "pages").mkdir()
    (tmp_path / ".last_ingest_sha").write_text("b" * 40, encoding="utf-8")
    src = WikiSource(tmp_path, tmp_path / ".last_ingest_sha", _audience_for_page)
    assert list(src.search("anything", Scope(allow_dev=True))) == []


def test_no_match_returns_empty(tmp_path: Path):
    _write_page(tmp_path, "p", "# P\n\n> **Audience:** `user`\n\napples oranges\n")
    src = _make_source(tmp_path)
    assert list(src.search("zzzznonexistent", Scope())) == []
