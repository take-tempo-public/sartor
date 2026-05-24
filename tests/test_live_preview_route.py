"""Tests for `/api/applications/<id>/preview` (Phase β.4).

The route renders the application's latest JSON Resume sidecar through
the selected persona's HTML+CSS template and returns a fully self-
contained HTML page (CSS inlined) for embedding in an iframe.

Test surface:
  - Returns 200 + text/html with expected content when sidecar + template exist
  - Returns 409 when no sidecar (user hasn't generated yet)
  - Returns 400 on malformed template_id
  - Returns 404 when application doesn't belong to the user
  - Falls back to bundled Classic when the selected persona lacks
    an HTML companion
  - CSS is inlined into a <style> block (no remote <link>)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def preview_app(tmp_path, monkeypatch):
    """Fresh in-memory DB + temp directories so we can seed candidates,
    applications, sidecars, and HTML templates without colliding with
    real user data."""
    db_file = tmp_path / "preview.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import importlib

    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "PERSONAS_DIR", tmp_path / "personas")
    monkeypatch.setattr(app_module, "BUNDLED_PERSONAS_DIR", tmp_path / "personas" / "bundled")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "personas").mkdir()
    (tmp_path / "personas" / "bundled").mkdir()
    (tmp_path / "output").mkdir()

    from db.session import init_db
    init_db(db_file)

    # Materialize the bundled Classic HTML + CSS in the temp dir so the
    # fallback path works. Mirror the real classic.html + classic.css
    # so the inlining test catches the real shape.
    repo_root = Path(__file__).resolve().parents[1]
    src_html = repo_root / "personas" / "bundled" / "classic.html"
    src_css = repo_root / "personas" / "bundled" / "classic.css"
    (tmp_path / "personas" / "bundled" / "classic.html").write_text(
        src_html.read_text(encoding="utf-8"), encoding="utf-8",
    )
    (tmp_path / "personas" / "bundled" / "classic.css").write_text(
        src_css.read_text(encoding="utf-8"), encoding="utf-8",
    )
    # Also drop a stub .docx so the bundled-template DB rows resolve.
    from docx import Document
    for filename in ("classic.docx", "modern.docx"):
        doc = Document()
        doc.add_paragraph(f"stub for {filename}")
        doc.save(str(tmp_path / "personas" / "bundled" / filename))

    (tmp_path / "configs" / "casey.config").write_text("{}", encoding="utf-8")
    return app_module


def _seed_candidate_app(app_module, username="casey", title="Senior PM"):
    """Insert a candidate + application row, return (candidate_id, application_id)."""
    from db.models import Application, Candidate
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(username=username, name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id, title=title,
            jd_text="placeholder JD", jd_fingerprint="x" * 16,
        )
        session.add(a)
        session.commit()
        return c.id, a.id
    finally:
        session.close()


def _seed_sidecar(app_module, username, doc):
    """Write a JSON Resume sidecar into the user's output dir."""
    user_dir = app_module.OUTPUT_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    sidecar = user_dir / "resume_20260524_120000.jsonresume.json"
    sidecar.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return sidecar


# -------------------------------------------------------------------
# Happy path
# -------------------------------------------------------------------


class TestPreviewHappyPath:
    def test_returns_html_with_expected_content(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_sidecar(preview_app, "casey", {
            "basics": {"name": "Casey Rivera", "label": "PM",
                       "summary": "Senior PM with a decade of leadership."},
            "work": [{"name": "Polaris", "position": "Lead PM",
                      "startDate": "2022", "endDate": "present",
                      "highlights": ["Shipped the unified corpus."]}],
        })

        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview")
        assert r.status_code == 200
        assert r.content_type.startswith("text/html")
        body = r.get_data(as_text=True)
        assert "Casey Rivera" in body
        assert "Senior PM with a decade of leadership." in body
        assert "Polaris" in body
        assert "Shipped the unified corpus." in body

    def test_css_is_inlined(self, preview_app):
        """The response must be fully self-contained — no remote
        <link rel="stylesheet"> tags. CSS lives inside a <style> block
        so the iframe sandbox works without cross-origin gymnastics."""
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_sidecar(preview_app, "casey", {
            "basics": {"name": "Casey Rivera"},
        })

        client = preview_app.app.test_client()
        body = client.get(f"/api/applications/{aid}/preview").get_data(as_text=True)
        assert "<link rel=\"stylesheet\"" not in body
        assert "<style>" in body
        # A signature rule from classic.css proves the inline succeeded
        assert "Helvetica" in body or "page-break" in body


# -------------------------------------------------------------------
# Failure paths
# -------------------------------------------------------------------


class TestPreviewFailureModes:
    def test_returns_409_when_no_sidecar(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        # No sidecar seeded
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview")
        assert r.status_code == 409
        body = r.get_json()
        assert body.get("needs_generate") is True

    def test_returns_404_for_unknown_application(self, preview_app):
        client = preview_app.app.test_client()
        r = client.get("/api/applications/9999/preview")
        assert r.status_code == 404

    def test_returns_400_for_malformed_template_id(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id=not-a-number")
        assert r.status_code == 400


# -------------------------------------------------------------------
# Explicit template_id
# -------------------------------------------------------------------


class TestPreviewWithExplicitTemplate:
    def test_uses_specified_template(self, preview_app):
        """When template_id is passed, the route resolves through that
        persona's HTML companion (or falls back to bundled Classic if
        no companion exists)."""
        from db.models import PersonaTemplate
        from db.session import get_session

        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_sidecar(preview_app, "casey", {"basics": {"name": "Casey"}})

        # Find the bundled Classic row from the seed migration
        session = get_session()
        try:
            classic = session.query(PersonaTemplate).filter_by(
                source="bundled", name="Classic Single-Column",
            ).first()
            assert classic is not None
            classic_id = classic.id
        finally:
            session.close()

        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id={classic_id}")
        assert r.status_code == 200
        assert "Casey" in r.get_data(as_text=True)

    def test_returns_404_for_unknown_template_id(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_sidecar(preview_app, "casey", {"basics": {"name": "Casey"}})
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id=99999")
        assert r.status_code == 404
