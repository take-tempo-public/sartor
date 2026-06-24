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

import json
import types

import pytest


@pytest.fixture
def fetch_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh sqlite DB + temp tree (Sprint 8.3g).

    The profile-fetch route moved to blueprints/users.py and reads
    current_app.config[...], so create_app(Config(base_dir=tmp_path)) replaces the
    old reload + monkeypatch-the-globals fixture; the DB-path monkeypatch stays.
    The corpus_import CONFIGS_DIR monkeypatch is GONE: _get_or_provision_candidate
    threads configs_dir from the injected Config all the way through
    import_candidate_from_config to _safe_load_config, so the onboarding layer no
    longer needs its own path-constant front patched (design §7 zero-debt).
    Returns a namespace exposing .app + .CONFIGS_DIR so the existing test bodies
    (fetch_app.app / _write_config) keep working.
    """
    db_file = tmp_path / "fetch.sqlite"

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output

    from db.session import init_db

    init_db(db_file)

    return types.SimpleNamespace(app=app, CONFIGS_DIR=cfg.configs_dir)


def _write_config(app_module, username: str, **fields) -> None:
    base = {
        "name": username.title(),
        "email": "",
        "phone": "",
        "linkedin_url": "",
        "website_url": "",
        "portfolio_urls": [],
        "skills": [],
        "certifications": [],
        "education_summary": "",
        "notes": "",
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
            fetch_app,
            "casey",
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
        monkeypatch.setattr("scraper.fetch_url_content", lambda url: called.append(url) or "x")
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
            fetch_app,
            "casey",
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
            fetch_app,
            "casey",
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
            fetch_app,
            "casey",
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
