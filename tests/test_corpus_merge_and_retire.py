"""Routes for role-merge suggestions, experience merge, and title/bullet retire visibility.

Covers the corpus-import & curation UX fixes: the post-import "possible duplicate
roles" detection + merge, and the soft-retire-hidden-unless-shown behavior.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def corpus_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh DB + temp config dir (Sprint 8.3d pattern)."""
    db_file = tmp_path / "corpus.sqlite"
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


def _seed_candidate(username="alice"):
    from db.models import Candidate
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username=username, name=username.title())
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def _seed_experience(
    candidate_id,
    *,
    company="Acme",
    start_date="2020-01",
    end_date="2023-06",
    official_title="Product Manager",
    alt_titles=(),
    bullets=(),
    display_order=0,
):
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id,
            company=company,
            start_date=start_date,
            end_date=end_date,
            display_order=display_order,
        )
        s.add(e)
        s.flush()
        s.add(
            ExperienceTitle(
                experience_id=e.id,
                title=official_title,
                is_official=1,
                truthful_enough_to_use=1,
                is_pending_review=0,
                is_active=1,
                source="user_added",
            )
        )
        for t in alt_titles:
            s.add(
                ExperienceTitle(
                    experience_id=e.id,
                    title=t,
                    is_official=0,
                    truthful_enough_to_use=1,
                    is_pending_review=0,
                    is_active=1,
                    source="user_added",
                )
            )
        for i, btext in enumerate(bullets):
            s.add(
                Bullet(
                    experience_id=e.id,
                    text=btext,
                    display_order=i,
                    is_active=1,
                    is_pending_review=0,
                    source="manual",
                    has_outcome=0,
                )
            )
        s.commit()
        return e.id
    finally:
        s.close()


def _title_id(exp_id, title_text):
    from db.models import ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        return s.query(ExperienceTitle).filter_by(experience_id=exp_id, title=title_text).first().id
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Retire / restore visibility (P3 / P4)
# --------------------------------------------------------------------------- #
class TestRetireVisibility:
    def test_retired_title_hidden_by_default_shown_with_flag(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid, alt_titles=("Senior PM",))
        tid = _title_id(eid, "Senior PM")
        client = corpus_app.test_client()

        # Retire the alt title.
        r = client.delete(f"/api/experience-titles/{tid}")
        assert r.status_code == 200
        assert r.get_json()["is_active"] is False

        # Hidden by default.
        default = client.get(f"/api/experiences/{eid}").get_json()
        assert [t["title"] for t in default["titles"]] == ["Product Manager"]

        # Visible with include_retired.
        shown = client.get(f"/api/experiences/{eid}?include_retired=1").get_json()
        titles = {t["title"]: t for t in shown["titles"]}
        assert "Senior PM" in titles
        assert titles["Senior PM"]["is_active"] is False

    def test_restore_title_via_put(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid, alt_titles=("Senior PM",))
        tid = _title_id(eid, "Senior PM")
        client = corpus_app.test_client()
        client.delete(f"/api/experience-titles/{tid}")

        r = client.put(f"/api/experience-titles/{tid}", json={"is_active": True})
        assert r.status_code == 200
        body = r.get_json()
        assert body["is_active"] is True
        assert body["truthful_enough_to_use"] is True

        default = client.get(f"/api/experiences/{eid}").get_json()
        assert "Senior PM" in [t["title"] for t in default["titles"]]

    def test_retired_bullet_hidden_by_default(self, corpus_app):
        from db.models import Bullet
        from db.session import get_session

        cid = _seed_candidate()
        eid = _seed_experience(cid, bullets=("Shipped V1.", "Shipped V2."))
        s = get_session()
        try:
            bid = s.query(Bullet).filter_by(experience_id=eid, text="Shipped V1.").first().id
        finally:
            s.close()
        client = corpus_app.test_client()
        client.delete(f"/api/bullets/{bid}")

        default = client.get(f"/api/experiences/{eid}").get_json()
        assert [b["text"] for b in default["bullets"]] == ["Shipped V2."]
        shown = client.get(f"/api/experiences/{eid}?include_retired=1").get_json()
        assert "Shipped V1." in [b["text"] for b in shown["bullets"]]

    def test_summary_title_count_excludes_retired(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid, alt_titles=("Senior PM",))
        tid = _title_id(eid, "Senior PM")
        client = corpus_app.test_client()
        client.delete(f"/api/experience-titles/{tid}")

        rows = client.get("/api/users/alice/experiences").get_json()
        row = next(r for r in rows if r["id"] == eid)
        assert row["title_count"] == 1  # official only; retired alt excluded


# --------------------------------------------------------------------------- #
# Merge suggestions (P1) + dismiss
# --------------------------------------------------------------------------- #
class TestMergeSuggestions:
    def test_similar_roles_surface_as_suggestion(self, corpus_app):
        cid = _seed_candidate()
        _seed_experience(
            cid,
            company="Acme Corp",
            start_date="2020-01",
            end_date="2023-06",
            official_title="Product Manager",
            bullets=("Led roadmap for 3 products.", "Grew ARR 40%."),
        )
        _seed_experience(
            cid,
            company="Acme, Inc.",
            start_date="2021-03",
            end_date="2024-01",
            official_title="Senior Product Manager",
            bullets=("Led roadmap for 3 products.", "Hired 6 PMs."),
            display_order=1,
        )
        client = corpus_app.test_client()
        body = client.get("/api/users/alice/corpus/merge-suggestions").get_json()
        assert body["count"] == 1
        sug = body["suggestions"][0]
        assert "company" in sug["matched_signals"]
        assert sug["shared_bullet_count"] == 1
        # in_corpus = lower id (older); other = newer import.
        assert sug["exp_in_corpus"]["id"] < sug["exp_other"]["id"]

    def test_distinct_companies_no_suggestion(self, corpus_app):
        cid = _seed_candidate()
        _seed_experience(cid, company="Acme", official_title="Engineer")
        _seed_experience(cid, company="Globex", official_title="Engineer", display_order=1)
        client = corpus_app.test_client()
        body = client.get("/api/users/alice/corpus/merge-suggestions").get_json()
        assert body["count"] == 0

    def test_dismiss_removes_suggestion(self, corpus_app):
        cid = _seed_candidate()
        e1 = _seed_experience(
            cid,
            company="Acme Corp",
            start_date="2020-01",
            official_title="Product Manager",
            bullets=("Led roadmap.", "Grew ARR."),
        )
        e2 = _seed_experience(
            cid,
            company="Acme Inc",
            start_date="2021-03",
            official_title="Senior Product Manager",
            bullets=("Led roadmap.", "Hired PMs."),
            display_order=1,
        )
        client = corpus_app.test_client()
        assert client.get("/api/users/alice/corpus/merge-suggestions").get_json()["count"] == 1

        r = client.post(
            "/api/users/alice/corpus/merge-suggestions/dismiss",
            json={"exp_a_id": e1, "exp_b_id": e2},
        )
        assert r.status_code == 200
        assert client.get("/api/users/alice/corpus/merge-suggestions").get_json()["count"] == 0


# --------------------------------------------------------------------------- #
# Merge endpoint (P1)
# --------------------------------------------------------------------------- #
class TestMergeExperience:
    def test_merge_folds_source_into_target(self, corpus_app):
        from db.models import Experience
        from db.session import get_session

        cid = _seed_candidate()
        target = _seed_experience(
            cid,
            company="Acme Corp",
            start_date="2020-01",
            end_date="2023-06",
            official_title="Product Manager",
            bullets=("Led roadmap.", "Grew ARR 40%."),
        )
        source = _seed_experience(
            cid,
            company="Acme, Inc.",
            start_date="2021-03",
            end_date="2024-01",
            official_title="Senior Product Manager",
            bullets=("Led roadmap.", "Hired 6 PMs."),  # 1 dup, 1 new
            display_order=1,
        )
        client = corpus_app.test_client()
        r = client.post(f"/api/experiences/{target}/merge", json={"source_id": source})
        assert r.status_code == 200
        merged = r.get_json()

        # Target keeps its own dates.
        assert merged["start_date"] == "2020-01"
        assert merged["end_date"] == "2023-06"
        # Both titles present; exactly one official.
        title_texts = {t["title"] for t in merged["titles"]}
        assert {"Product Manager", "Senior Product Manager"} <= title_texts
        officials = [t for t in merged["titles"] if t["is_official"]]
        assert len(officials) == 1 and officials[0]["title"] == "Product Manager"
        # Bullets unified + deduped (3 distinct, not 4).
        bullet_texts = sorted(b["text"] for b in merged["bullets"])
        assert bullet_texts == ["Grew ARR 40%.", "Hired 6 PMs.", "Led roadmap."]
        # Source experience is gone.
        s = get_session()
        try:
            assert s.query(Experience).filter_by(id=source).first() is None
        finally:
            s.close()

    def test_merge_rejects_self_and_missing_source(self, corpus_app):
        cid = _seed_candidate()
        eid = _seed_experience(cid)
        client = corpus_app.test_client()
        assert (
            client.post(f"/api/experiences/{eid}/merge", json={"source_id": eid}).status_code == 400
        )
        assert client.post(f"/api/experiences/{eid}/merge", json={}).status_code == 400
        assert (
            client.post(f"/api/experiences/{eid}/merge", json={"source_id": 99999}).status_code
            == 404
        )

    def test_merge_refused_when_source_used_in_application(self, corpus_app):
        from db.models import (
            Application,
            ApplicationBullet,
            ApplicationRun,
            Bullet,
        )
        from db.session import get_session

        cid = _seed_candidate()
        target = _seed_experience(cid, company="Acme Corp", start_date="2020-01")
        source = _seed_experience(
            cid,
            company="Acme Inc",
            start_date="2021-03",
            bullets=("Used in a real application.",),
            display_order=1,
        )
        s = get_session()
        try:
            bid = s.query(Bullet).filter_by(experience_id=source).first().id
            app_row = Application(
                candidate_id=cid,
                title="Some role",
                jd_text="jd",
                jd_fingerprint="abc123",
            )
            s.add(app_row)
            s.flush()
            run = ApplicationRun(
                application_id=app_row.id,
                iteration=0,
                run_id="run000000001",
                prompt_version="2026-01-01.1",
                corpus_snapshot_json="{}",
            )
            s.add(run)
            s.flush()
            s.add(ApplicationBullet(application_run_id=run.id, bullet_id=bid, position=0))
            s.commit()
        finally:
            s.close()

        client = corpus_app.test_client()
        r = client.post(f"/api/experiences/{target}/merge", json={"source_id": source})
        assert r.status_code == 409
