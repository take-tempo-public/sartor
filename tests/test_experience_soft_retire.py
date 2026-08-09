"""Reproduction instrument — retiring a 0-bullet role silently no-ops.

`DELETE /api/experiences/<id>` implements "retire" as
``UPDATE bullet SET is_active=0 WHERE experience_id=?``
(`blueprints/corpus/experiences.py:236-263`). A role with **zero bullets**
affects zero rows, still returns 200, and the `experience` row itself carries no
retire flag at all (`db/models.py:88-124`) — so nothing downstream can tell it
apart from a live role.

C-7 rule 4 — **scope the instrument wider than the hypothesis.** These assertions
deliberately span four independent layers rather than the handler's return code:

1. the corpus list route (`GET /api/users/<u>/experiences`),
2. the generation context builder (`db.build_context.build_context_set_from_db`
   → `career_corpus` + the synthesized `resume.text`),
3. the deterministic renderer (`corpus_to_json_resume.build_json_resume_from_corpus`
   → `work[]` and its order-aligned `meta.sartor.work_provenance`),
4. the restore path (a retired role must be un-retirable).

A control arm rides along in every case: a *bulleted* role retired through the
same handler, which today DOES disappear from generation. If the control also
fails, the mechanism is not "0 bullets" and the hypothesis is dead.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def corpus_app(tmp_path, monkeypatch, _migrated_template_db):
    """Factory-built app on a fresh migrated DB (mirrors test_corpus_merge_and_retire)."""
    from tests.conftest import _fresh_migrated_db

    db_file = _fresh_migrated_db(
        tmp_path, monkeypatch, _migrated_template_db, filename="corpus.sqlite"
    )

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    from db.session import init_db

    assert init_db(db_file) is False, "expected the pre-registered copy to skip alembic"
    return app


def _seed(candidate_username="alice"):
    """Seed one candidate with a bulleted role (control) and a 0-bullet role (subject)."""
    from db.models import Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username=candidate_username, name="Alice")
        s.add(c)
        s.flush()

        bulleted = Experience(
            candidate_id=c.id,
            company="Globex",
            start_date="2022-01",
            end_date="2024-01",
            display_order=0,
        )
        empty = Experience(
            candidate_id=c.id,
            company="Acme",
            start_date="2020-01",
            end_date="2021-12",
            display_order=1,
        )
        s.add_all([bulleted, empty])
        s.flush()
        for exp, title in ((bulleted, "Staff Engineer"), (empty, "Advisor")):
            s.add(
                ExperienceTitle(
                    experience_id=exp.id,
                    title=title,
                    is_official=1,
                    truthful_enough_to_use=1,
                    is_pending_review=0,
                    is_active=1,
                    source="user_added",
                )
            )
        s.add(
            Bullet(
                experience_id=bulleted.id,
                text="Shipped the ingest pipeline.",
                display_order=0,
                is_active=1,
                is_pending_review=0,
                source="manual",
                has_outcome=0,
            )
        )
        s.commit()
        return c.id, bulleted.id, empty.id
    finally:
        s.close()


def _companies_in_context(candidate_username="alice"):
    """Return (career_corpus companies, synthesized resume text) from the DB context builder."""
    from db.build_context import build_context_set_from_db
    from db.session import get_session

    s = get_session()
    try:
        cs, _app_row, _run = build_context_set_from_db(
            s,
            candidate_username=candidate_username,
            jd_text="Senior Engineer wanted.",
            run_id="run000000001",
        )
        s.rollback()  # anchor rows are a side effect we do not want to persist here
        return [e["company"] for e in cs["career_corpus"]], cs["resume"]["text"]
    finally:
        s.close()


def _rendered_work(candidate_id):
    """Return (work[] entries, order-aligned work_provenance) from the deterministic renderer."""
    from corpus_to_json_resume import build_json_resume_from_corpus
    from db.session import get_session

    s = get_session()
    try:
        doc = build_json_resume_from_corpus(s, candidate_id)
        return doc["work"], doc["meta"]["sartor"].get("work_provenance", [])
    finally:
        s.close()


class TestZeroBulletRoleRetire:
    def test_retire_zero_bullet_role_hides_it_everywhere(self, corpus_app):
        cid, bulleted_id, empty_id = _seed()
        client = corpus_app.test_client()

        # --- Retire the 0-bullet role through the real handler. --------------
        r = client.delete(f"/api/experiences/{empty_id}")
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json()["retired_bullets"] == 0  # nothing to cascade to

        # Every layer is measured before anything is asserted, so one failing
        # layer cannot hide the others (C-7 rule 4).
        rows = client.get("/api/users/alice/experiences").get_json()
        corpus_companies, resume_text = _companies_in_context()
        work, provenance = _rendered_work(cid)

        observed = {
            "1_corpus_list": [row["company"] for row in rows],
            "2_career_corpus": corpus_companies,
            "2_resume_text_mentions_acme": "Acme" in resume_text,
            "3_work_names": [w.get("name") for w in work],
            "3_provenance_exp_ids": [p["experience_id"] for p in provenance],
        }
        expected = {
            "1_corpus_list": ["Globex"],
            "2_career_corpus": ["Globex"],
            "2_resume_text_mentions_acme": False,
            "3_work_names": ["Globex"],
            "3_provenance_exp_ids": [bulleted_id],
        }
        assert observed == expected, (
            f"retired 0-bullet role (id={empty_id}) survives downstream:\n"
            f"  observed={observed}\n  expected={expected}"
        )

    def test_control_bulleted_role_retire_already_leaves_generation(self, corpus_app):
        """Control arm: the bulleted role's retire already clears generation today.

        If this fails alongside the subject test, the mechanism is NOT "zero
        bullets" and the hypothesis in the diagnosis dossier is dead.
        """
        cid, bulleted_id, _empty_id = _seed()
        client = corpus_app.test_client()

        r = client.delete(f"/api/experiences/{bulleted_id}")
        assert r.status_code == 200
        assert r.get_json()["retired_bullets"] == 1

        _corpus_companies, resume_text = _companies_in_context()
        assert "Shipped the ingest pipeline." not in resume_text

        work, _prov = _rendered_work(cid)
        assert all(not w.get("highlights") for w in work if w.get("name") == "Globex")

    def test_retired_role_can_be_restored(self, corpus_app):
        """Acceptance requires un-retire; a filter in the loader would 404 this."""
        _cid, _bulleted_id, empty_id = _seed()
        client = corpus_app.test_client()

        assert client.delete(f"/api/experiences/{empty_id}").status_code == 200
        rows = client.get("/api/users/alice/experiences").get_json()
        assert [row["company"] for row in rows] == ["Globex"]

        restore = client.put(f"/api/experiences/{empty_id}", json={"is_active": True})
        assert restore.status_code == 200, restore.get_data(as_text=True)
        assert restore.get_json()["is_active"] is True

        rows = client.get("/api/users/alice/experiences").get_json()
        assert sorted(row["company"] for row in rows) == ["Acme", "Globex"]

    def test_retired_role_visible_with_include_retired(self, corpus_app):
        """The owner's hard rule: retired rows stay hidden until Show retired is ticked."""
        _cid, _bulleted_id, empty_id = _seed()
        client = corpus_app.test_client()
        assert client.delete(f"/api/experiences/{empty_id}").status_code == 200

        shown = client.get("/api/users/alice/experiences?include_retired=1").get_json()
        by_company = {row["company"]: row for row in shown}
        assert set(by_company) == {"Acme", "Globex"}
        assert by_company["Acme"]["is_active"] is False
        assert by_company["Globex"]["is_active"] is True
