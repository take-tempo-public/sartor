"""Tests for the live HTML preview routes (Phase β.4 + β.6).

Two routes share the same render pipeline:
  - GET /api/applications/<id>/preview  → corpus + application overrides
  - GET /api/users/<username>/preview   → corpus only (pre-application)

Both build a JSON Resume v1.0 doc directly from Candidate + Experience
+ Bullet + SummaryItem rows via `corpus_to_json_resume`, render it
through the chosen persona's HTML+CSS template, inline CSS into a
<style> block, and return text/html for iframe consumption.

The corpus-direct shape replaces the earlier sidecar-only behavior so
the preview works BEFORE any /api/generate has run — fixing the
"can't preview a template without paying for a generate" gap surfaced
in the hands-on review.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def preview_app(tmp_path, monkeypatch):
    """Fresh in-memory DB + temp directories so we can seed candidates,
    applications, and corpus rows without colliding with real user data."""
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


def _seed_candidate_app(app_module, username="casey",
                        name="Casey Rivera",
                        profile_text="Senior PM with a decade of leadership.",
                        title="Senior PM"):
    """Insert a candidate (with profile_text) + application row.
    Returns (candidate_id, application_id)."""
    from db.models import Application, Candidate
    from db.session import get_session
    session = get_session()
    try:
        c = Candidate(
            username=username, name=name, profile_text=profile_text,
            email="casey@example.com",
        )
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


def _seed_experience_with_bullets(candidate_id: int, *,
                                  company="Polaris", position="Lead PM",
                                  bullet_texts=("Shipped the unified corpus.",)):
    """Seed one experience + bullets + an official title for the candidate."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session
    session = get_session()
    try:
        exp = Experience(
            candidate_id=candidate_id, company=company,
            start_date="2022", end_date="present",
        )
        session.add(exp)
        session.flush()
        t = ExperienceTitle(
            experience_id=exp.id, title=position,
            is_official=1, source="official",
        )
        session.add(t)
        for i, text in enumerate(bullet_texts):
            b = Bullet(
                experience_id=exp.id, text=text,
                display_order=i, is_active=1, source="resume_import",
            )
            session.add(b)
        session.commit()
        return exp.id
    finally:
        session.close()


# -------------------------------------------------------------------
# Per-application preview — happy path
# -------------------------------------------------------------------


class TestApplicationPreviewHappyPath:
    def test_returns_html_from_corpus(self, preview_app):
        """The preview reads from corpus rows directly — no sidecar
        required. Generates BEFORE any /api/generate has run."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

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
        _seed_candidate_app(preview_app, username="casey")

        client = preview_app.app.test_client()
        body = client.get(
            "/api/users/casey/preview",
        ).get_data(as_text=True)
        assert "<link rel=\"stylesheet\"" not in body
        assert "<style>" in body
        # A signature rule from classic.css proves the inline succeeded
        assert "Helvetica" in body or "page-break" in body

    def test_pinned_summary_wins_over_profile_text(self, preview_app):
        """A pinned SummaryItem must override Candidate.profile_text in
        the rendered preview — proves corpus_to_json_resume honors
        composition_overrides.pinned_summary_id passed via context_path."""
        from db.models import SummaryItem
        from db.session import get_session

        cid, aid = _seed_candidate_app(preview_app, username="casey")
        session = get_session()
        try:
            si = SummaryItem(
                candidate_id=cid, text="Pinned variant text.",
                display_order=0, is_active=1,
            )
            session.add(si)
            session.flush()
            si_id = si.id
            session.commit()
        finally:
            session.close()

        # Persist a context file under OUTPUT_DIR with the pin so the
        # preview route's _within(cp, OUTPUT_DIR) gate passes.
        import json as _json
        out_dir = (preview_app.OUTPUT_DIR / "casey").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        ctx_file = out_dir / "context_pin.json"
        ctx_file.write_text(_json.dumps({
            "application_id": aid,
            "composition_overrides": {
                "pinned": [], "excluded": [], "added": [],
                "pinned_summary_id": si_id,
            },
        }), encoding="utf-8")

        client = preview_app.app.test_client()
        body = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        ).get_data(as_text=True)
        assert "Pinned variant text." in body
        assert "Senior PM with a decade of leadership." not in body


# -------------------------------------------------------------------
# Per-application preview — failure paths
# -------------------------------------------------------------------


class TestApplicationPreviewFailureModes:
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
# Per-application preview — explicit template_id
# -------------------------------------------------------------------


class TestPreviewWithExplicitTemplate:
    def test_uses_specified_template(self, preview_app):
        """When template_id is passed, the route resolves through that
        persona's HTML companion (or falls back to bundled Classic if
        no companion exists)."""
        from db.models import PersonaTemplate
        from db.session import get_session

        _cid, aid = _seed_candidate_app(preview_app, username="casey")

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
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id=99999")
        assert r.status_code == 404


# -------------------------------------------------------------------
# Pre-application preview (/api/users/<u>/preview)
# -------------------------------------------------------------------


class TestUserPreview:
    def test_renders_corpus_without_application(self, preview_app):
        """A candidate with corpus rows but no application_id still
        gets a renderable preview — answers the user's "let me see what
        my résumé looks like through Classic" before any application."""
        cid, _aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

        client = preview_app.app.test_client()
        r = client.get("/api/users/casey/preview")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "Casey Rivera" in body
        assert "Polaris" in body

    def test_rejects_unknown_user(self, preview_app):
        """A username with no `.config` is rejected at `_safe_username`
        (returns None → 400). Practical: the surface is closed before
        the candidate row is consulted, so we never leak which users
        exist in the corpus tables vs which don't."""
        client = preview_app.app.test_client()
        r = client.get("/api/users/ghost/preview")
        assert r.status_code == 400

    def test_returns_409_when_config_exists_but_no_candidate(self, preview_app):
        """When a config exists but the candidate row is missing, the
        UI needs the `needs_onboarding` flag so it routes the user
        through onboarding rather than showing a blank preview."""
        # Materialize a config file (no candidate row)
        (preview_app.CONFIGS_DIR / "newbie.config").write_text(
            "{}", encoding="utf-8",
        )
        client = preview_app.app.test_client()
        r = client.get("/api/users/newbie/preview")
        assert r.status_code == 409
        assert r.get_json().get("needs_onboarding") is True

    def test_returns_400_for_invalid_username(self, preview_app):
        """Path-traversal-style usernames are rejected by
        _safe_username before any DB hit."""
        client = preview_app.app.test_client()
        r = client.get("/api/users/..%2Fadmin/preview")
        # Werkzeug routing strips the slash; the validator catches it.
        assert r.status_code in (400, 404)
