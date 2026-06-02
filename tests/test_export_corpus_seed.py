"""Tests for the deterministic corpus seed exporter (scripts/export_corpus_seed).

LLM-free. DB cases use the in-memory `db_session` fixture from conftest.py; the
write-path guard cases need no DB at all. The exporter is a faithful snapshot:
ALL rows (active + inactive) are captured — the active-only / JD-aware filtering
lives in build_context_set_from_db, not here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.export_corpus_seed import (
    ALLOWED_ROOT,
    _resolve_output_path,
    _within,
    export_seed,
)


def _seed_full_candidate(session) -> None:
    """Insert a candidate exercising every entity the seed captures, including
    an inactive bullet and tag links across bullet / title / summary item."""
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


class TestExportSeed:
    def test_happy_path_captures_all_entities(self, db_session) -> None:
        _seed_full_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")

        # Envelope
        assert seed["seed_schema_version"] == 1
        assert seed["generator"] == "scripts/export_corpus_seed.py"
        assert seed["candidate_username"] == "alex"
        assert seed["candidate"]["profile_text"] == "Platform SRE."

        # Every top-level collection present
        for key in ("tags", "experiences", "summary_items", "skills",
                    "educations", "certifications"):
            assert key in seed

        # Faithful snapshot: BOTH the active and the inactive bullet are present
        exp = seed["experiences"][0]
        assert len(exp["bullets"]) == 2
        active_flags = {b["text"]: b["is_active"] for b in exp["bullets"]}
        assert active_flags == {"Cut p99 latency 40%.": True, "Retired bullet.": False}

        # FK round-trip: every tag_link references a tag in the registry
        tag_ids = {t["id"] for t in seed["tags"]}
        assert tag_ids
        assert exp["titles"][0]["tag_links"][0]["tag_id"] in tag_ids
        active_bullet = next(b for b in exp["bullets"] if b["is_active"])
        assert active_bullet["tag_links"][0]["tag_id"] in tag_ids
        assert seed["summary_items"][0]["tag_links"][0]["tag_id"] in tag_ids

        # int columns are surfaced as JSON bools
        assert exp["titles"][0]["is_official"] is True
        assert seed["skills"][0]["years"] == 6.0
        assert len(seed["educations"]) == 1 and len(seed["certifications"]) == 1

    def test_unknown_user_raises(self, db_session) -> None:
        with pytest.raises(ValueError, match="No candidate with username"):
            export_seed(db_session, candidate_username="ghost")

    def test_minimal_candidate_yields_empty_lists_not_none(self, db_session) -> None:
        from db.models import Candidate

        db_session.add(Candidate(username="solo", name="Solo"))
        db_session.commit()

        seed = export_seed(db_session, candidate_username="solo")
        assert seed["experiences"] == []
        assert seed["skills"] == []
        assert seed["tags"] == []
        assert seed["summary_items"] == []
        assert seed["candidate"]["username"] == "solo"


class TestWritePathGuard:
    def test_default_path_under_real_fixtures(self) -> None:
        out = _resolve_output_path("alex", None)
        assert out.parent.name == "alex"
        assert out.name == "seed.json"
        assert _within(out, ALLOWED_ROOT)

    def test_username_is_sanitized(self) -> None:
        # secure_filename strips traversal; the dir component can't escape.
        out = _resolve_output_path("../../etc", None)
        assert _within(out, ALLOWED_ROOT)
        assert ".." not in out.parts

    def test_empty_sanitized_username_rejected(self) -> None:
        with pytest.raises(ValueError, match="sanitizes to empty"):
            _resolve_output_path("..", None)

    def test_out_outside_allowed_root_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="refusing to write outside"):
            _resolve_output_path("alex", str(tmp_path / "seed.json"))

    def test_out_inside_allowed_root_accepted(self) -> None:
        target = ALLOWED_ROOT / "alex" / "custom.json"
        out = _resolve_output_path("alex", str(target))
        assert _within(out, ALLOWED_ROOT)
        assert out.name == "custom.json"

    def test_within_helper(self, tmp_path: Path) -> None:
        assert _within(tmp_path / "a" / "b", tmp_path)
        assert not _within(tmp_path.parent / "outside", tmp_path)
