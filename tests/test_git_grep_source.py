"""Unit tests for `recall.sources.GitGrepSource` — the S2 `git grep` tier.

Exercised against the real repository working tree (the tests run inside it). They
skip cleanly when git is unavailable (CI quirk / detached snapshot), matching the
`tests/test_testuser_fixture.py` git-call convention.
"""

from __future__ import annotations

import re
import subprocess
import uuid
from pathlib import Path

import pytest

from recall.models import Audience, Scope, Tier
from recall.sources import GitGrepSource

REPO_ROOT = Path(__file__).resolve().parent.parent


def _git_available() -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _git_available(), reason="not in a git working tree")


def _all_dev(_path: str) -> Audience:
    return Audience.DEV


def _make_source(**kw) -> GitGrepSource:
    src = GitGrepSource(REPO_ROOT, _all_dev, **kw)
    src.refresh(None)
    return src


def test_search_returns_path_line_units_from_real_repo():
    src = _make_source()
    results = list(src.search("_safe_username", Scope(allow_dev=True)))
    assert results, "expected git grep to find _safe_username in the tracked tree"
    u = results[0]
    assert u.tier is Tier.GIT
    assert re.match(r"^[\w./-]+:\d+$", u.citation), f"bad citation: {u.citation}"


def test_no_match_returns_empty():
    src = _make_source()
    # The query token must be GENUINELY absent from every TRACKED file. Built at runtime so
    # the literal never appears in this test's own source: `git grep` searches tracked files,
    # so a hardcoded "absent" token self-matches this file once it is committed (that latent
    # bug, dormant while the file was untracked during Sprint 7.5, surfaced in 7.6).
    absent = "zz" + uuid.uuid4().hex
    assert list(src.search(absent, Scope(allow_dev=True))) == []


def test_audience_fn_is_applied():
    src = GitGrepSource(REPO_ROOT, lambda _p: Audience.USER)
    src.refresh(None)
    results = list(src.search("_safe_username", Scope(allow_dev=True)))
    assert results and all(u.audience is Audience.USER for u in results)


def test_refresh_caches_head_sha():
    src = _make_source()
    results = list(src.search("_safe_username", Scope(allow_dev=True)))
    assert results
    assert re.match(r"^[0-9a-f]{40}$", results[0].sha), f"bad sha: {results[0].sha!r}"


def test_max_results_caps_output():
    # "def" appears in many tracked files; cap must bound the result count.
    src = _make_source(max_results=5)
    results = list(src.search("def", Scope(allow_dev=True)))
    assert len(results) <= 5


def test_git_not_found_returns_empty(monkeypatch):
    src = _make_source()

    def _boom(*_a, **_k):
        raise FileNotFoundError("git not on PATH")

    monkeypatch.setattr(subprocess, "run", _boom)
    assert list(src.search("_safe_username", Scope(allow_dev=True))) == []


def test_stopword_only_query_returns_empty():
    src = _make_source()
    assert list(src.search("how do i", Scope(allow_dev=True))) == []
