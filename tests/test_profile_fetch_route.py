"""Tests for POST /api/users/<u>/profile/fetch (PX-02 scrape re-wire).

This route is the whole point of PX-02: the profile/website scrape regressed to
dead code because NOTHING asserted that the runtime path actually called it.
These tests pin the wiring so it can't silently die again — plus the
no-pollution guard (the scrape must never touch profile_text, the β.6
positioning summary that backs the résumé basics.summary).

LLM-free and network-free: scraper.fetch_url_content is monkeypatched, so no
socket opens (the real egress lives in scraper.py, already exercised by
tests/test_egress_allowlist.py + tests/test_scraper.py).
"""

from __future__ import annotations

import importlib
import json

import pytest


@pytest.fixture
def fetch_app(tmp_path, monkeypatch):
    """Fresh DB + tmp configs/ + output/ so each test starts clean.

    Mirrors the summary-route fixture: reload app so module-level CONFIGS_DIR /
    OUTPUT_DIR / BASE_DIR + the corpus_import CONFIGS_DIR all point at tmp dirs.
    """
    db_file = tmp_path / "fetch.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()

    import onboarding.corpus_import as corpus_import_mod
    monkeypatch.setattr(corpus_import_mod, "CONFIGS_DIR", tmp_path / "configs")

    from db.session import init_db
    init_db(db_file)
    return app_module


def _write_config(app_module, username: str, **fields) -> None:
    base = {
        "name": username.title(), "email": "", "phone": "",
        "linkedin_url": "", "website_url": "", "portfolio_urls": [],
        "skills": [], "certifications": [], "education_summary": "", "notes": "",
    }
    base.update(fields)
    path = app_module.CONFIGS_DIR / f"{username}.config"
    path.write_text(json.dumps(base, indent=2), encoding="utf-8")


def _seed_candidate(username="casey", **fields):
    from db.models import Candidate
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username=username, name=username.title(), **fields)
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


def _get_candidate(username="casey"):
    from db.models import Candidate
    from db.session import get_session
    session = get_session()
    try:
        return session.query(Candidate).filter_by(username=username).first()
    finally:
        session.close()


class TestProfileFetchWiring:
    def test_runtime_path_actually_calls_the_scraper_and_persists(self, fetch_app, monkeypatch):
        """THE regression-prevention test: the route invokes
        scraper.fetch_profile_content (→ fetch_url_content per URL) for every
        configured URL and caches the combined text in online_profile_text."""
        _write_config(
            fetch_app, "casey",
            linkedin_url="https://linkedin.com/in/casey",
            website_url="https://casey.dev",
            portfolio_urls=["https://github.com/casey", "https://casey.art"],
        )

        called = []

        def fake_fetch_url_content(url: str) -> str:
            called.append(url)
            return f"TEXT::{url}"

        monkeypatch.setattr("scraper.fetch_url_content", fake_fetch_url_content)

        client = fetch_app.app.test_client()
        r = client.post("/api/users/casey/profile/fetch")
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["ok"] is True
        assert body["urls"] == 4
        assert body["chars"] > 0

        # The scraper was genuinely invoked for every configured URL.
        assert called == [
            "https://linkedin.com/in/casey",
            "https://casey.dev",
            "https://github.com/casey",
            "https://casey.art",
        ]

        # Combined, labelled text persisted to the DISTINCT column.
        cand = _get_candidate("casey")
        assert cand is not None
        stored = cand.online_profile_text or ""
        assert "--- Linkedin ---" in stored
        assert "--- Website ---" in stored
        assert "--- Portfolio ---" in stored
        assert "TEXT::https://casey.dev" in stored

    def test_unknown_user_returns_400(self, fetch_app, monkeypatch):
        monkeypatch.setattr("scraper.fetch_url_content", lambda url: "x")
        client = fetch_app.app.test_client()
        r = client.post("/api/users/ghost/profile/fetch")
        assert r.status_code == 400

    def test_no_urls_stores_none(self, fetch_app, monkeypatch):
        """A config with no URLs is a valid opt-out: nothing fetched, column
        cleared to None, graceful status."""
        _write_config(fetch_app, "casey")  # all URL fields empty
        called = []
        monkeypatch.setattr("scraper.fetch_url_content",
                            lambda url: called.append(url) or "x")
        client = fetch_app.app.test_client()
        r = client.post("/api/users/casey/profile/fetch")
        assert r.status_code == 200
        body = r.get_json()
        assert body["urls"] == 0
        assert body["chars"] == 0
        assert called == []  # nothing to fetch
        assert _get_candidate("casey").online_profile_text is None

    def test_failed_fetches_store_none_gracefully(self, fetch_app, monkeypatch):
        """URLs present but all unreachable (scraper swallows → "") → chars 0,
        column None. The scrape 'fails gracefully' contract."""
        _write_config(
            fetch_app, "casey",
            linkedin_url="https://linkedin.com/in/casey",
            website_url="https://casey.dev",
        )
        monkeypatch.setattr("scraper.fetch_url_content", lambda url: "")
        client = fetch_app.app.test_client()
        r = client.post("/api/users/casey/profile/fetch")
        assert r.status_code == 200
        body = r.get_json()
        assert body["urls"] == 2
        assert body["chars"] == 0
        assert _get_candidate("casey").online_profile_text is None

    def test_does_not_touch_profile_text(self, fetch_app, monkeypatch):
        """No-pollution guard: the scrape writes online_profile_text ONLY —
        profile_text (the β.6 positioning summary / résumé basics.summary
        fallback) is left untouched."""
        _write_config(
            fetch_app, "casey",
            linkedin_url="https://linkedin.com/in/casey",
        )
        _seed_candidate("casey", profile_text="Senior PM positioning summary.")
        monkeypatch.setattr("scraper.fetch_url_content", lambda url: "scraped bio")
        client = fetch_app.app.test_client()
        r = client.post("/api/users/casey/profile/fetch")
        assert r.status_code == 200
        cand = _get_candidate("casey")
        assert cand.profile_text == "Senior PM positioning summary."  # untouched
        assert "scraped bio" in (cand.online_profile_text or "")

    def test_provisions_candidate_when_absent(self, fetch_app, monkeypatch):
        """A config-only user (no Candidate row yet) gets provisioned on fetch,
        same lazy-provisioning posture as the analyze path."""
        _write_config(
            fetch_app, "casey",
            website_url="https://casey.dev",
        )
        assert _get_candidate("casey") is None  # config-only, no row
        monkeypatch.setattr("scraper.fetch_url_content", lambda url: "bio text")
        client = fetch_app.app.test_client()
        r = client.post("/api/users/casey/profile/fetch")
        assert r.status_code == 200
        cand = _get_candidate("casey")
        assert cand is not None
        assert "bio text" in (cand.online_profile_text or "")
