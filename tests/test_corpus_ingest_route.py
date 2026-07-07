"""Tests for POST /api/users/<u>/corpus/ingest-resume (Workstream D).

The route saves the upload, then runs the shared ingest_one_resume which
calls extract_experiences_and_skills (Haiku, F-02: one call returns both
experiences and a flat skills list). We patch extract_experiences_and_skills
+ the Anthropic client so no API credit is spent; parse_resume on .md is
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

_FAKE_SKILLS = ["Python", "Kubernetes"]


def _patch_extract(experiences=None, skills=None):
    """Patch the shared extraction call at its source module (F-02: one Haiku
    call returns both experiences and skills — ingest_one_resume imports it
    lazily, so patching the source attribute is what the existing
    extract_experiences patches also relied on)."""
    return patch(
        "onboarding.extract_experiences.extract_experiences_and_skills",
        return_value=(experiences if experiences is not None else [], skills or []),
    )


class TestIngestResume:
    def test_ingests_md_into_corpus_as_pending(self, ingest_app):
        _seed_candidate()
        client = ingest_app.test_client()
        with (
            _patch_extract(_FAKE_EXTRACT, _FAKE_SKILLS),
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
        assert body["skills_created"] == 2

        from db.models import Bullet, Experience, Skill
        from db.session import get_session

        s = get_session()
        try:
            exps = s.query(Experience).all()
            assert any(e.company == "Polaris" for e in exps)
            # Imported content lands pending-review
            bullets = s.query(Bullet).all()
            assert bullets and all(b.is_pending_review == 1 for b in bullets)
            # F-02: skills extracted during import also land pending-review
            skills = s.query(Skill).order_by(Skill.display_order).all()
            assert {sk.name for sk in skills} == {"Python", "Kubernetes"}
            assert all(sk.is_pending_review == 1 and sk.is_active == 1 for sk in skills)
            # source is DB-CHECK-limited (ck_skill_source) to manual|imported|llm_proposed.
            assert all(sk.source == "imported" for sk in skills)
        finally:
            s.close()

    def test_skills_dedup_case_insensitively_against_existing(self, ingest_app):
        """A skill that already exists (any case, any review state) never gets a duplicate pending row."""
        from db.models import Skill
        from db.session import get_session

        cid = _seed_candidate()
        s = get_session()
        try:
            s.add(Skill(candidate_id=cid, name="python", is_active=1, is_pending_review=0))
            s.commit()
        finally:
            s.close()

        client = ingest_app.test_client()
        with (
            _patch_extract(_FAKE_EXTRACT, ["Python", "Kubernetes"]),
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
        # Only "Kubernetes" is new; "Python" collides case-insensitively with
        # the pre-existing "python" row and is skipped, not duplicated.
        assert body["skills_created"] == 1

        s = get_session()
        try:
            rows = s.query(Skill).filter_by(candidate_id=cid).all()
            names = [sk.name for sk in rows]
            assert names.count("python") + names.count("Python") == 1
            assert "Kubernetes" in names
        finally:
            s.close()

    def test_reimport_is_idempotent_for_skills(self, ingest_app):
        """Uploading the same résumé twice must not create a second pending row per skill."""
        _seed_candidate()
        client = ingest_app.test_client()

        def _upload():
            with (
                _patch_extract(_FAKE_EXTRACT, _FAKE_SKILLS),
                patch("blueprints.corpus.curation._get_client", return_value=object()),
            ):
                return client.post(
                    "/api/users/alice/corpus/ingest-resume",
                    data={
                        "file": (
                            io.BytesIO(b"# Resume\n\n## Experience\n\n- Did things at Polaris"),
                            "r.md",
                        )
                    },
                    content_type="multipart/form-data",
                )

        r1 = _upload()
        assert r1.status_code == 201, r1.get_json()
        assert r1.get_json()["skills_created"] == 2

        r2 = _upload()
        assert r2.status_code == 201, r2.get_json()
        # Second pass: both names already exist (from the first pass), so
        # nothing new is created.
        assert r2.get_json()["skills_created"] == 0

        from db.models import Skill
        from db.session import get_session

        s = get_session()
        try:
            names = [sk.name for sk in s.query(Skill).all()]
            assert sorted(names) == ["Kubernetes", "Python"]
        finally:
            s.close()

    def test_accepted_skill_flows_to_downstream_consumption(self, ingest_app):
        """A pending import-skill, once approved, is picked up by the deterministic
        corpus_to_json_resume._collect_skills consumer (the frozen-composition /
        JSON-Resume skills[] source) — pending skills never are."""
        from db.models import Skill
        from db.session import get_session

        cid = _seed_candidate()
        client = ingest_app.test_client()
        with (
            _patch_extract(_FAKE_EXTRACT, ["Python"]),
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

        s = get_session()
        try:
            sk = s.query(Skill).filter_by(candidate_id=cid, name="Python").one()
            skill_id = sk.id
        finally:
            s.close()

        from corpus_to_json_resume import _collect_skills

        # Still pending: invisible to the deterministic consumer.
        s = get_session()
        try:
            names, _ids = _collect_skills(s, cid)
            assert names == []
        finally:
            s.close()

        # Approve via the existing review route (reuse, not a new surface).
        r_approve = client.put(f"/api/skills/{skill_id}", json={"is_pending_review": False})
        assert r_approve.status_code == 200

        s = get_session()
        try:
            names, ids = _collect_skills(s, cid)
            assert names == [{"name": "Python"}]
            assert ids == [skill_id]
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
            _patch_extract([], []),
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
            _patch_extract(_FAKE_EXTRACT, _FAKE_SKILLS),
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
