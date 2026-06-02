"""Tests for the corpus seed importer (evals/seed_import).

LLM-free. The DB cases use the in-memory `db_session` fixture from conftest.py as
the SOURCE corpus; the importer reconstructs it into a fresh in-memory DB. The
seed is produced by the real `scripts.export_corpus_seed.export_seed`, so these
tests exercise the genuine export→import round-trip — the importer must be a
faithful inverse of the exporter, preserving primary keys so the imported session
drives `build_context_set_from_db` exactly like the live corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.seed_import import (
    SUPPORTED_SEED_SCHEMA_VERSIONS,
    import_seed,
    load_seed,
    seeded_session,
    validate_seed,
)
from scripts.export_corpus_seed import export_seed

# A JD with enough signal that extract_keywords + the snapshot scorer have
# something to chew on. Content is irrelevant to the import — only the corpus is.
SAMPLE_JD = (
    "Senior Site Reliability Engineer. You will own Kafka pipelines, cut p99 "
    "latency, run incident response, and improve observability across services. "
    "Python and Kubernetes experience required."
)


def _seed_candidate(session) -> None:
    """Insert a candidate exercising every entity the seed captures, including an
    inactive bullet and tag links across bullet / title / summary item. Mirrors
    the export-test fixture so the round-trip covers the full shape."""
    from db.models import (
        Bullet,
        BulletTag,
        Candidate,
        Certification,
        Education,
        Experience,
        ExperienceTitle,
        ExperienceTitleTag,
        Skill,
        SummaryItem,
        SummaryItemTag,
        Tag,
    )

    c = Candidate(
        username="alex", name="Alex Chen", email="alex@example.com",
        phone="555-0100", linkedin_url="https://lnkd.in/alex",
        website_url="https://alex.dev", notes="n", profile_text="Platform SRE.",
    )
    session.add(c)
    session.flush()

    tag = Tag(candidate_id=c.id, kind="skill", value="kafka", display_value="Kafka")
    session.add(tag)
    session.flush()

    e = Experience(
        candidate_id=c.id, company="Polaris", location="Remote",
        start_date="2022-09", end_date=None, display_order=0, summary="Backend.",
    )
    session.add(e)
    session.flush()

    title = ExperienceTitle(
        experience_id=e.id, title="Senior SRE", is_official=1,
        truthful_enough_to_use=1, is_pending_review=0, source="official",
    )
    session.add(title)
    session.flush()
    session.add(ExperienceTitleTag(experience_title_id=title.id, tag_id=tag.id, confidence=1.0))

    active = Bullet(
        experience_id=e.id, text="Cut p99 latency 40%.", display_order=0,
        is_active=1, is_pending_review=0, source="primary:r.md",
        pattern_kind="xyz", has_outcome=1,
    )
    inactive = Bullet(
        experience_id=e.id, text="Retired bullet.", display_order=1,
        is_active=0, is_pending_review=0, source="primary:r.md",
        pattern_kind=None, has_outcome=0,
    )
    session.add_all([active, inactive])
    session.flush()
    session.add(BulletTag(bullet_id=active.id, tag_id=tag.id, confidence=0.9))

    summary = SummaryItem(
        candidate_id=c.id, text="SRE who ships reliability.", label="SRE",
        display_order=0, is_active=1, is_pending_review=0, source="manual",
        has_outcome=0,
    )
    session.add(summary)
    session.flush()
    session.add(SummaryItemTag(summary_item_id=summary.id, tag_id=tag.id, confidence=1.0))

    session.add(Skill(candidate_id=c.id, name="Python", category="language",
                       proficiency="expert", years=6.0))
    session.add(Education(candidate_id=c.id, institution="State U", degree="BS",
                          field="CS", start_date="2014", end_date="2018",
                          display_order=0, is_active=1, notes=None))
    session.add(Certification(candidate_id=c.id, name="CKA", issuer="CNCF",
                              issued="2021", expires="2024", display_order=0,
                              is_active=1))
    session.commit()


def _fresh_session():
    """A second, independent in-memory DB (separate from the db_session fixture)
    with the full schema created. Caller closes the session + disposes engine."""
    from db.models import Base
    from db.session import make_engine, make_session_factory

    engine = make_engine(":memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)(), engine


class TestRoundTrip:
    def test_export_import_export_is_faithful(self, db_session) -> None:
        """import_seed is the exact inverse of export_seed: re-exporting an
        imported seed reproduces every collection (ids and all), modulo the
        volatile exported_at timestamp."""
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")

        with seeded_session(seed) as (fresh, username):
            assert username == "alex"
            seed2 = export_seed(fresh, candidate_username="alex")

        seed_no_ts = {k: v for k, v in seed.items() if k != "exported_at"}
        seed2_no_ts = {k: v for k, v in seed2.items() if k != "exported_at"}
        assert seed2_no_ts == seed_no_ts

    def test_primary_keys_preserved(self, db_session) -> None:
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        src_tag_ids = [t["id"] for t in seed["tags"]]
        src_exp_ids = [e["id"] for e in seed["experiences"]]
        src_bullet_ids = [b["id"] for e in seed["experiences"] for b in e["bullets"]]

        with seeded_session(seed) as (fresh, _username):
            from db.models import Bullet, Experience, Tag
            assert [t.id for t in fresh.query(Tag).order_by(Tag.id).all()] == src_tag_ids
            assert [e.id for e in fresh.query(Experience).order_by(Experience.id).all()] == src_exp_ids
            assert sorted(b.id for b in fresh.query(Bullet).all()) == sorted(src_bullet_ids)

    def test_inactive_rows_imported(self, db_session) -> None:
        """Faithful snapshot: the inactive bullet is imported (the active-only
        filtering lives in build_context_set_from_db, NOT the importer), and the
        int flag round-trips as 1/0."""
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        with seeded_session(seed) as (fresh, _username):
            from db.models import Bullet
            flags = {b.text: b.is_active for b in fresh.query(Bullet).all()}
        assert flags == {"Cut p99 latency 40%.": 1, "Retired bullet.": 0}

    def test_tag_links_round_trip(self, db_session) -> None:
        """The bullet/title/summary tag links resolve to the imported tags with
        confidences preserved — the FK fidelity build_context_set_from_db relies
        on in _bullet_tag_values."""
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        with seeded_session(seed) as (fresh, _username):
            from db.models import BulletTag, Tag
            tag_ids = {t.id for t in fresh.query(Tag).all()}
            links = fresh.query(BulletTag).all()
            assert links, "expected at least one bullet tag link"
            for link in links:
                assert link.tag_id in tag_ids
                assert link.tag is not None and link.tag.value == "kafka"
                assert link.confidence == 0.9


class TestBuildsContextSet:
    def test_imported_session_builds_context_set(self, db_session) -> None:
        """The handoff's core acceptance: round-trip a seed through the importer →
        build_context_set_from_db, and the ContextSet matches the file-based
        contract."""
        from db.build_context import build_context_set_from_db

        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")

        with seeded_session(seed) as (fresh, username):
            context, _app, _run = build_context_set_from_db(
                fresh, candidate_username=username,
                jd_text=SAMPLE_JD, run_id="abc123def456",
            )

            required = {
                "candidate", "resume", "supplemental_resumes", "job_description",
                "deterministic_analysis", "run_id", "career_corpus",
            }
            assert required.issubset(context.keys())
            assert context["resume"]["format"] == "md"
            assert context["supplemental_resumes"] == []
            assert context["run_id"] == "abc123def456"
            assert context["candidate"]["name"] == "Alex Chen"

            career = context["career_corpus"]
            assert career, "career_corpus should be non-empty"
            assert {e["id"] for e in career}  # preserved experience ids present
            texts = {b["text"] for e in career for b in e["bullets"]}
            # active bullet surfaces; inactive is filtered DOWNSTREAM, not by the importer
            assert "Cut p99 latency 40%." in texts
            assert "Retired bullet." not in texts

    def test_career_corpus_matches_source_db(self, db_session) -> None:
        """Strongest equivalence: the corpus built off the imported session is
        identical to the corpus built off the source DB."""
        from db.build_context import build_context_set_from_db

        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")

        src_ctx, _a, _r = build_context_set_from_db(
            db_session, candidate_username="alex",
            jd_text=SAMPLE_JD, run_id="run000000001",
        )
        with seeded_session(seed) as (fresh, username):
            imp_ctx, _a2, _r2 = build_context_set_from_db(
                fresh, candidate_username=username,
                jd_text=SAMPLE_JD, run_id="run000000002",
            )
            assert imp_ctx["career_corpus"] == src_ctx["career_corpus"]
            assert imp_ctx["resume"]["text"] == src_ctx["resume"]["text"]


class TestValidation:
    def test_supported_versions_is_v1(self) -> None:
        assert 1 in SUPPORTED_SEED_SCHEMA_VERSIONS

    def test_validate_rejects_unsupported_version(self) -> None:
        with pytest.raises(ValueError, match="seed_schema_version"):
            validate_seed({
                "seed_schema_version": 2, "candidate_username": "x", "candidate": {},
                "tags": [], "experiences": [], "summary_items": [], "skills": [],
                "educations": [], "certifications": [],
            })

    def test_validate_rejects_missing_keys(self) -> None:
        with pytest.raises(ValueError, match="missing required keys"):
            validate_seed({"seed_schema_version": 1})

    def test_validate_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            validate_seed([1, 2, 3])

    def test_import_rejects_drifted_schema_version(self, db_session) -> None:
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        seed["seed_schema_version"] = 2
        fresh, engine = _fresh_session()
        try:
            with pytest.raises(ValueError, match="seed_schema_version"):
                import_seed(fresh, seed)
        finally:
            fresh.close()
            engine.dispose()


class TestLoadSeed:
    def test_load_seed_reads_and_validates(self, tmp_path: Path, db_session) -> None:
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        p = tmp_path / "seed.json"
        p.write_text(json.dumps(seed), encoding="utf-8")
        loaded = load_seed(p)
        assert loaded["candidate_username"] == "alex"

    def test_load_seed_rejects_drift(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"seed_schema_version": 99}), encoding="utf-8")
        with pytest.raises(ValueError, match="seed_schema_version"):
            load_seed(p)

    def test_seeded_session_accepts_path(self, tmp_path: Path, db_session) -> None:
        from db.models import Candidate

        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        p = tmp_path / "seed.json"
        p.write_text(json.dumps(seed), encoding="utf-8")
        with seeded_session(p) as (session, username):
            assert username == "alex"
            assert session.query(Candidate).count() == 1
