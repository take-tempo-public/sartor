"""Tests for POST /api/users/<u>/corpus/ingest-resume (Workstream D).

The route saves the upload, then runs the shared ingest_one_resume which
calls extract_experiences (Haiku). We patch extract_experiences + the
Anthropic client so no API credit is spent; parse_resume on .md is
deterministic and runs for real.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest


@pytest.fixture
def ingest_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp dirs (Sprint 8.3d).

    The ingest route moved to blueprints/corpus/curation and reads
    current_app.config at request time, so create_app(Config(base_dir=tmp_path))
    replaces the old reload + monkeypatch-the-globals pattern. Config.ensure_dirs
    makes configs/output/resumes. Provisioning threads configs_dir through
    web_infra, so the corpus_import.CONFIGS_DIR monkeypatch is gone. The DB-path
    monkeypatch stays.
    """
    db_file = tmp_path / "ingest.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db

    init_db(db_file)
    return app


def _seed_candidate():
    from db.models import Candidate
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username="alice", name="Alice")
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


_FAKE_EXTRACT = [
    {
        "company": "Polaris",
        "location": "Remote",
        "start_date": "2022-01",
        "end_date": None,
        "candidate_inferred_official_title": "Staff Engineer",
        "bullets": [
            {"text": "Shipped the thing", "suggested_tags": ["infra"]},
        ],
    }
]


class TestIngestResume:
    def test_ingests_md_into_corpus_as_pending(self, ingest_app):
        _seed_candidate()
        client = ingest_app.test_client()
        with (
            patch("onboarding.extract_experiences.extract_experiences", return_value=_FAKE_EXTRACT),
            patch("blueprints.corpus.curation._get_client", return_value=object()),
        ):
            r = client.post(
                "/api/users/alice/corpus/ingest-resume",
                data={
                    "file": (
                        io.BytesIO(b"# Resume\n\n## Experience\n\n- Did things at Polaris"),
                        "r.md",
                    )
                },
                content_type="multipart/form-data",
            )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["experiences_created"] >= 1

        from db.models import Bullet, Experience
        from db.session import get_session

        s = get_session()
        try:
            exps = s.query(Experience).all()
            assert any(e.company == "Polaris" for e in exps)
            # Imported content lands pending-review
            bullets = s.query(Bullet).all()
            assert bullets and all(b.is_pending_review == 1 for b in bullets)
        finally:
            s.close()

    def test_unreadable_resume_does_not_masquerade_as_success(self, ingest_app):
        # A file that parses to empty text records an error and creates nothing.
        # The route must surface that as a 4xx — not a 201 the client reads as a
        # successful import (the "status says ready over an empty corpus" bug).
        _seed_candidate()
        client = ingest_app.test_client()
        with patch("blueprints.corpus.curation._get_client", return_value=object()):
            r = client.post(
                "/api/users/alice/corpus/ingest-resume",
                data={"file": (io.BytesIO(b"   \n   "), "blank.md")},
                content_type="multipart/form-data",
            )
        assert r.status_code == 422, r.get_json()
        body = r.get_json()
        assert body["experiences_created"] == 0
        assert body["errors"]

    def test_no_dated_roles_stays_201_without_error(self, ingest_app):
        # A readable résumé that simply has no extractable dated roles is a
        # warning, not a failure — 201 with a zero count (the client warns,
        # doesn't error). Guards the 422-only-on-error carve-out.
        _seed_candidate()
        client = ingest_app.test_client()
        with (
            patch("onboarding.extract_experiences.extract_experiences", return_value=[]),
            patch("blueprints.corpus.curation._get_client", return_value=object()),
        ):
            r = client.post(
                "/api/users/alice/corpus/ingest-resume",
                data={"file": (io.BytesIO(b"# Resume\n\nSummary only, no roles"), "r.md")},
                content_type="multipart/form-data",
            )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["experiences_created"] == 0
        assert not body["errors"]

    def test_rejects_unsupported_extension(self, ingest_app):
        _seed_candidate()
        client = ingest_app.test_client()
        r = client.post(
            "/api/users/alice/corpus/ingest-resume",
            data={"file": (io.BytesIO(b"x"), "evil.exe")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400

    def test_missing_candidate_is_auto_provisioned(self, ingest_app):
        # A config-only user (no Candidate row) is provisioned on ingest —
        # importing a résumé IS the onboarding step, no separate import.
        client = ingest_app.test_client()
        with (
            patch("onboarding.extract_experiences.extract_experiences", return_value=_FAKE_EXTRACT),
            patch("blueprints.corpus.curation._get_client", return_value=object()),
        ):
            r = client.post(
                "/api/users/alice/corpus/ingest-resume",
                data={
                    "file": (
                        io.BytesIO(b"# Resume\n\n## Experience\n\n- Did things at Polaris"),
                        "r.md",
                    )
                },
                content_type="multipart/form-data",
            )
        assert r.status_code == 201, r.get_json()
        from db.models import Candidate
        from db.session import get_session

        s = get_session()
        try:
            assert s.query(Candidate).filter_by(username="alice").first() is not None
        finally:
            s.close()

    def test_unknown_user_400(self, ingest_app):
        client = ingest_app.test_client()
        r = client.post(
            "/api/users/ghost/corpus/ingest-resume",
            data={"file": (io.BytesIO(b"# x"), "r.md")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400
