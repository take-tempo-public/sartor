r"""ORM models for the career corpus + candidate memory.

See `C:\\Users\\iam\\.claude\\plans\\rosy-chasing-pinwheel.md` for the design.
Stable enums use CHECK constraints; free-text fields (tag values, bullet
phrasing, source provenance suffixes) carry no DB-level validation and rely
on the application layer.

Timestamps are TEXT ISO-8601 UTC strings (matches the legacy file-based
context schema; lets sqlite-cli inspection stay greppable).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> str:
    """ISO-8601 UTC timestamp with Z suffix — same shape used in JSONL telemetry."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Base(DeclarativeBase):
    """Declarative base for all corpus and candidate-memory ORM models."""


# ---------------------------------------------------------------------------
# Core entities: candidate, experience, experience_title, bullet, tag
# ---------------------------------------------------------------------------


class Candidate(Base):
    """The account root — one row per username; parent of every corpus, application, and memory entity."""

    __tablename__ = "candidate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    linkedin_url: Mapped[str | None] = mapped_column(String)
    website_url: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    # The candidate's go-to positioning summary (résumé basics.summary fallback;
    # β.6 backfilled it into SummaryItem rows). NOT a scraped online profile.
    profile_text: Mapped[str | None] = mapped_column(Text)
    # PX-02: cached text from the opt-in LinkedIn/website/portfolio scrape
    # (scraper.fetch_profile_content). A distinct channel from profile_text so
    # the scrape can never clobber the positioning summary / basics.summary.
    online_profile_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    experiences: Mapped[list[Experience]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list[Skill]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    tags: Mapped[list[Tag]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    applications: Mapped[list[Application]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    clarifications: Mapped[list[Clarification]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    # β.6 — SummaryItem variants. Candidate has 1..N; recommend_summaries
    # picks one per JD; composition_overrides can pin/exclude per app.
    summary_items: Mapped[list[SummaryItem]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class Experience(Base):
    """One job or role in the candidate's history; parent of its titles, bullets, and per-role intro variants."""

    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    company: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM or YYYY
    end_date: Mapped[str | None] = mapped_column(String)  # YYYY-MM / YYYY; NULL = current
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    candidate: Mapped[Candidate] = relationship(back_populates="experiences")
    titles: Mapped[list[ExperienceTitle]] = relationship(
        back_populates="experience", cascade="all, delete-orphan"
    )
    bullets: Mapped[list[Bullet]] = relationship(
        back_populates="experience", cascade="all, delete-orphan"
    )
    # B.4 (Sprint 6.6) — per-role intro variants. An Experience has 0..N;
    # recommend_experience_summaries picks one per JD; composition_overrides
    # opts a role in (use_experience_summaries) + pins a variant per app.
    # The single `summary` column above is now the legacy denormalized
    # cache — alembic 0008 backfills it into one ExperienceSummaryItem row.
    summary_items: Mapped[list[ExperienceSummaryItem]] = relationship(
        back_populates="experience", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_experience_candidate_order", "candidate_id", "display_order"),)


class ExperienceTitle(Base):
    """A title variant for an Experience — official, user-added, or LLM-proposed (at most one is_official per role)."""

    __tablename__ = "experience_title"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_official: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    truthful_enough_to_use: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Soft-retire flag (parity with Bullet.is_active): 1 = live, 0 = retired.
    # Retired titles are hidden from the corpus unless include_retired is set,
    # and never reach generation. Kept (not hard-deleted) because
    # application_run_title / proposal_review FKs reference titles for audit.
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'official' | 'user_added' | 'llm_proposed:<run_id>'
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    experience: Mapped[Experience] = relationship(back_populates="titles")
    tag_links: Mapped[list[ExperienceTitleTag]] = relationship(
        back_populates="title", cascade="all, delete-orphan"
    )

    # At most one is_official per experience (partial unique index for SQLite).
    __table_args__ = (
        Index(
            "ix_experience_title_official",
            "experience_id",
            unique=True,
            sqlite_where=text("is_official = 1"),
        ),
    )


class Bullet(Base):
    """One achievement bullet under an Experience — the core tailorable corpus item (active/pending, tagged, with metrics)."""

    __tablename__ = "bullet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String, nullable=False)  # see plan §bullet
    pattern_kind: Mapped[str | None] = mapped_column(
        String
    )  # 'xyz' | 'star' | 'car' | 'manual' | NULL
    has_outcome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    experience: Mapped[Experience] = relationship(back_populates="bullets")
    tag_links: Mapped[list[BulletTag]] = relationship(
        back_populates="bullet", cascade="all, delete-orphan"
    )
    metrics: Mapped[list[BulletMetric]] = relationship(
        back_populates="bullet", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "pattern_kind IS NULL OR pattern_kind IN ('xyz', 'star', 'car', 'manual')",
            name="ck_bullet_pattern_kind",
        ),
        Index(
            "ix_bullet_experience_active_pending_order",
            "experience_id",
            "is_active",
            "is_pending_review",
            "display_order",
        ),
    )


class Tag(Base):
    """Canonical registry shared across bullets, titles, templates, and clarifications."""

    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)  # role|domain|skill|tech
    value: Mapped[str] = mapped_column(
        String, nullable=False
    )  # normalized: lowercase, hyphen-separated
    display_value: Mapped[str] = mapped_column(String, nullable=False)  # user's original casing
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    merged_into_id: Mapped[int | None] = mapped_column(
        ForeignKey("tag.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    candidate: Mapped[Candidate] = relationship(back_populates="tags")
    merged_into: Mapped[Tag | None] = relationship(remote_side="Tag.id")

    __table_args__ = (
        UniqueConstraint("candidate_id", "kind", "value", name="uq_tag_candidate_kind_value"),
        CheckConstraint("kind IN ('role', 'domain', 'skill', 'tech')", name="ck_tag_kind"),
    )


class BulletTag(Base):
    """Tag join table linking a Bullet to a Tag, with a match-confidence weight."""

    __tablename__ = "bullet_tag"

    bullet_id: Mapped[int] = mapped_column(
        ForeignKey("bullet.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    bullet: Mapped[Bullet] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_bullet_tag_tag", "tag_id"),)


class ExperienceTitleTag(Base):
    """Tag join table linking an ExperienceTitle to a Tag, with a match-confidence weight."""

    __tablename__ = "experience_title_tag"

    experience_title_id: Mapped[int] = mapped_column(
        ForeignKey("experience_title.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    title: Mapped[ExperienceTitle] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_experience_title_tag_tag", "tag_id"),)


class BulletMetric(Base):
    """A structured metric (count, currency, percent, duration, or scope) extracted verbatim from a Bullet."""

    __tablename__ = "bullet_metric"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bullet_id: Mapped[int] = mapped_column(
        ForeignKey("bullet.id", ondelete="CASCADE"), nullable=False
    )
    metric_kind: Mapped[str] = mapped_column(
        String, nullable=False
    )  # count|currency|percent|duration|scope
    value: Mapped[str] = mapped_column(String, nullable=False)  # verbatim from source
    unit: Mapped[str | None] = mapped_column(String)

    bullet: Mapped[Bullet] = relationship(back_populates="metrics")

    __table_args__ = (
        CheckConstraint(
            "metric_kind IN ('count', 'currency', 'percent', 'duration', 'scope')",
            name="ck_bullet_metric_kind",
        ),
    )


class MergeDismissal(Base):
    """A candidate's 'keep separate' decision for a pair of similar experiences.

    Records that the user reviewed two experiences the merge-suggestion scan
    flagged as possible duplicate roles and chose to keep them distinct, so the
    scan stops re-surfacing the pair. The pair is stored order-normalized
    (exp_a_id < exp_b_id) and uniqued, so a dismissal is idempotent regardless of
    which side the UI sends first. Cascades away if either experience is deleted.
    """

    __tablename__ = "merge_dismissal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    exp_a_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    exp_b_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("candidate_id", "exp_a_id", "exp_b_id", name="uq_merge_dismissal_pair"),
        Index("ix_merge_dismissal_candidate", "candidate_id"),
    )


# ---------------------------------------------------------------------------
# β.6 — Summary items (Corpus Item pattern for the candidate's
# positioning summary). Parallel to Bullet for experience-bound content.
# Per docs/PRODUCT_SHAPE.md §3 + §6, every curatable résumé element gets
# the same lifecycle: variants, tags, scoring, has_outcome, soft-retire,
# pin/exclude per application. SummaryItem is the first new CorpusItem
# specialization landing in v1.0.
#
# Parent: Candidate (the candidate has multiple positioning variants —
# "AI platform PM", "enterprise PM", "early-stage builder PM" — and the
# Compose step picks one per application).
# ---------------------------------------------------------------------------


class SummaryItem(Base):
    """One variant of the candidate's overall positioning summary.

    Mirrors Bullet's shape (text + has_outcome + is_active +
    is_pending_review + tags) but parented by Candidate instead of
    Experience. A single candidate has 1..N variants; recommend_summaries
    picks one per JD (β.6b); composition_overrides can pin/exclude
    variants per application (β.6c).

    Backfill semantics (alembic 0004): every Candidate.profile_text
    that's non-empty becomes a SummaryItem row at migration time.
    Candidate.profile_text stays on the schema as a denormalized cache
    of "the candidate's go-to summary" for back-compat with code that
    reads it directly; new code should query SummaryItem rows.
    """

    __tablename__ = "summary_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(
        String
    )  # optional human-readable name like "AI platform PM"
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )  # 'manual' | 'imported' | 'llm_proposed'
    has_outcome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    candidate: Mapped[Candidate] = relationship(back_populates="summary_items")
    tag_links: Mapped[list[SummaryItemTag]] = relationship(
        back_populates="summary_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('manual', 'imported', 'llm_proposed')",
            name="ck_summary_item_source",
        ),
        Index(
            "ix_summary_item_candidate_active_pending_order",
            "candidate_id",
            "is_active",
            "is_pending_review",
            "display_order",
        ),
    )


class SummaryItemTag(Base):
    """Tag join table for SummaryItem, mirroring BulletTag exactly so the tag-composer UI and corpus-tag operations can treat both kinds identically."""

    __tablename__ = "summary_item_tag"

    summary_item_id: Mapped[int] = mapped_column(
        ForeignKey("summary_item.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    summary_item: Mapped[SummaryItem] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_summary_item_tag_tag", "tag_id"),)


# ---------------------------------------------------------------------------
# B.4 (Sprint 6.6) — Experience summary items (Corpus Item pattern for the
# per-role intro paragraph). Parallel to SummaryItem but parented by
# Experience instead of Candidate: the line a recruiter reads first under a
# single job. Maps to JSON Resume work[].summary.
#
# Unlike SummaryItem (which auto-applies the recommendation), per-role intros
# are OPT-IN: a role shows an intro only when the user turns on the Tailor-time
# "Add role intros" toggle (composition_overrides.use_experience_summaries) and
# a variant is chosen (composition_overrides.chosen_experience_summary_ids).
# ---------------------------------------------------------------------------


class ExperienceSummaryItem(Base):
    """One variant of a single role's intro paragraph.

    Mirrors SummaryItem's shape (text + has_outcome + is_active +
    is_pending_review + tags) but parented by Experience instead of
    Candidate. An Experience has 0..N variants;
    recommend_experience_summaries picks one per JD (batch, keyed by
    experience_id); composition_overrides opts the role in + pins a
    variant per application.

    Backfill semantics (alembic 0008): every Experience.summary that's
    non-empty becomes one ExperienceSummaryItem row (source='imported')
    at migration time. Experience.summary stays on the schema as a
    denormalized cache for back-compat; new code queries these rows.
    """

    __tablename__ = "experience_summary_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String)  # optional name like "platform-scale framing"
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )  # 'manual' | 'imported' | 'llm_proposed'
    has_outcome: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    experience: Mapped[Experience] = relationship(back_populates="summary_items")
    tag_links: Mapped[list[ExperienceSummaryItemTag]] = relationship(
        back_populates="summary_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('manual', 'imported', 'llm_proposed')",
            name="ck_experience_summary_item_source",
        ),
        Index(
            "ix_experience_summary_item_active_pending_order",
            "experience_id",
            "is_active",
            "is_pending_review",
            "display_order",
        ),
    )


class ExperienceSummaryItemTag(Base):
    """Tag join table for ExperienceSummaryItem, mirroring SummaryItemTag exactly so corpus-tag operations treat all corpus items identically."""

    __tablename__ = "experience_summary_item_tag"

    experience_summary_item_id: Mapped[int] = mapped_column(
        ForeignKey("experience_summary_item.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    summary_item: Mapped[ExperienceSummaryItem] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_experience_summary_item_tag_tag", "tag_id"),)


# ---------------------------------------------------------------------------
# Career assets: skill, education, certification, project, publication
# ---------------------------------------------------------------------------


class Skill(Base):
    """A single skill — promoted to a full Corpus Item (Sprint 6.6 B.5).

    Mirrors Bullet's lifecycle (is_active + is_pending_review + source +
    display_order + tags) so a skill participates in the same recommend /
    pin / drop / curate / tag machinery as every other corpus item.
    recommend_skills selects + orders the active, approved skills per JD;
    suggest_skills proposes corpus-grounded new skills as pending
    (is_pending_review=1, source='llm_proposed') for the user to approve or
    deny. Résumé import (F-02, `onboarding.corpus_import._insert_pending_skills`)
    extracts a flat skills list from the same Haiku call that extracts
    experiences and lands them the same way (is_pending_review=1,
    source='imported' — `source` has no per-file slot; it's DB-CHECK-limited
    to 'manual'|'imported'|'llm_proposed'), deduped case-insensitively
    against every existing Skill row for the candidate. Pending/inactive
    skills never reach the recommend set, the preview skills[], or the
    generate prompt — the approve/deny gate is the grounding backstop.

    Backfill semantics (alembic 0009): every pre-existing Skill row becomes
    source='imported', is_active=1, is_pending_review=0, with display_order
    set to preserve the prior name-sorted order.
    """

    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(
        String
    )  # language|framework|platform|methodology|domain
    proficiency: Mapped[str | None] = mapped_column(String)  # expert|proficient|familiar
    years: Mapped[float | None] = mapped_column(nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )  # 'manual' | 'imported' | 'llm_proposed'
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
    tag_links: Mapped[list[SkillTag]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "name", name="uq_skill_candidate_name"),
        CheckConstraint(
            "source IN ('manual', 'imported', 'llm_proposed')",
            name="ck_skill_source",
        ),
        Index(
            "ix_skill_candidate_active_pending_order",
            "candidate_id",
            "is_active",
            "is_pending_review",
            "display_order",
        ),
    )


class SkillTag(Base):
    """Tag join table for Skill, mirroring BulletTag exactly so corpus-tag operations treat skills like every other taggable corpus item.

    Distinct from a Tag of kind='skill' (which tags bullets/titles with a
    skill keyword): this links a Skill ROW to any-kind tags so the matcher
    can reason about the skill itself.
    """

    __tablename__ = "skill_tag"

    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    skill: Mapped[Skill] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_skill_tag_tag", "tag_id"),)


class Education(Base):
    """One education entry — institution, degree, field, and dates."""

    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(String, nullable=False)
    degree: Mapped[str | None] = mapped_column(String)
    field: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[str | None] = mapped_column(String)
    end_date: Mapped[str | None] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text)


class Certification(Base):
    """One professional certification — name, issuer, and issued/expiry dates."""

    __tablename__ = "certification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    issuer: Mapped[str | None] = mapped_column(String)
    issued: Mapped[str | None] = mapped_column(String)
    expires: Mapped[str | None] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Project(Base):
    """One project entry — name, description, optional URL, and dates."""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String)
    start_date: Mapped[str | None] = mapped_column(String)
    end_date: Mapped[str | None] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Publication(Base):
    """One publication entry — title, venue, optional URL, and publish date."""

    __tablename__ = "publication"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    venue: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    published_date: Mapped[str | None] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ---------------------------------------------------------------------------
# Persona templates (bundled + user-uploaded)
# ---------------------------------------------------------------------------


class PersonaTemplate(Base):
    """A résumé .docx style template — bundled with the app (NULL candidate_id) or user-uploaded."""

    __tablename__ = "persona_template"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # NULL candidate_id = bundled with the app; non-NULL = user-uploaded.
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    primary_role_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("tag.id", ondelete="SET NULL"), nullable=True
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, nullable=False)  # 'bundled' | 'user_upload'
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    tag_links: Mapped[list[PersonaTemplateTag]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("source IN ('bundled', 'user_upload')", name="ck_persona_template_source"),
        Index(
            "ix_persona_template_default",
            "candidate_id",
            "primary_role_tag_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )


class PersonaTemplateTag(Base):
    """Tag join table linking a PersonaTemplate to a role/domain Tag."""

    __tablename__ = "persona_template_tag"

    persona_template_id: Mapped[int] = mapped_column(
        ForeignKey("persona_template.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)

    template: Mapped[PersonaTemplate] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_persona_template_tag_tag", "tag_id"),)


# ---------------------------------------------------------------------------
# Applications (Job Items) and their iteration runs
# ---------------------------------------------------------------------------


class Application(Base):
    """One job application (Job Item) — the target JD, its fingerprint, status, and iteration runs."""

    __tablename__ = "application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str | None] = mapped_column(String)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    jd_url: Mapped[str | None] = mapped_column(String)
    jd_fingerprint: Mapped[str] = mapped_column(String, nullable=False)  # sha256[:16] of jd_text
    target_role_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("tag.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        String, nullable=False, default=utc_now, onupdate=utc_now
    )
    sent_at: Mapped[str | None] = mapped_column(String)
    outcome_at: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String)
    # Soft-retire flag (walkthrough J1): 1 = live, 0 = retired. Retired
    # applications are hidden from the Prior Applications list unless
    # include_retired is set. Kept (not hard-deleted) so their runs + audit
    # trail survive — same rationale as ExperienceTitle.is_active (migration 0011).
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    candidate: Mapped[Candidate] = relationship(back_populates="applications")
    runs: Mapped[list[ApplicationRun]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'interview', 'rejected', 'withdrawn')",
            name="ck_application_status",
        ),
        Index("ix_application_candidate_status_updated", "candidate_id", "status", "updated_at"),
    )


class ApplicationRun(Base):
    """One generate/iterate run of an Application — the frozen corpus snapshot plus every generated and edited artifact."""

    __tablename__ = "application_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_run.id", ondelete="SET NULL"), nullable=True
    )
    run_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )  # 12-hex correlation primitive
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    persona_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("persona_template.id", ondelete="SET NULL"), nullable=True
    )
    # Frozen-at-iteration-0 set of bullet/title IDs used for cache stability.
    # See plan §application_run for the rationale.
    corpus_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_json: Mapped[str | None] = mapped_column(Text)
    clarification_questions_json: Mapped[str | None] = mapped_column(Text)
    clarifications_json: Mapped[str | None] = mapped_column(Text)
    generated_resume_md: Mapped[str | None] = mapped_column(Text)
    generated_cover_letter_md: Mapped[str | None] = mapped_column(Text)
    edited_resume_text: Mapped[str | None] = mapped_column(Text)
    edited_cover_letter_text: Mapped[str | None] = mapped_column(Text)
    deterministic_signals_json: Mapped[str | None] = mapped_column(Text)
    # Phase C.3: JSON result of the ATS round-trip self-check run after
    # _write_docx emits the generated .docx. Top-level keys: status
    # ('pass'|'warning'|'fail'|'not_run'), bullet_count_emitted,
    # bullet_count_recovered, sections_emitted, sections_recovered,
    # notes (list of human-readable findings).
    ats_roundtrip_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    application: Mapped[Application] = relationship(back_populates="runs")
    parent_run: Mapped[ApplicationRun | None] = relationship(remote_side="ApplicationRun.id")
    bullets: Mapped[list[ApplicationBullet]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    title_overrides: Mapped[list[ApplicationRunTitle]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    proposal_reviews: Mapped[list[ProposalReview]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    log_entries: Mapped[list[IterationLog]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_application_run_app_iter", "application_id", "iteration"),)


class ApplicationRunTitle(Base):
    """Per-application title override: chooses which experience_title to use for this run."""

    __tablename__ = "application_run_title"

    application_run_id: Mapped[int] = mapped_column(
        ForeignKey("application_run.id", ondelete="CASCADE"), primary_key=True
    )
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), primary_key=True
    )
    experience_title_id: Mapped[int] = mapped_column(
        ForeignKey("experience_title.id", ondelete="CASCADE"), nullable=False
    )

    run: Mapped[ApplicationRun] = relationship(back_populates="title_overrides")


class ApplicationBullet(Base):
    """Audit + composition record: which bullets ended up in which run's output."""

    __tablename__ = "application_bullet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_run_id: Mapped[int] = mapped_column(
        ForeignKey("application_run.id", ondelete="CASCADE"), nullable=False
    )
    # No CASCADE on bullet — deleting a referenced bullet must fail.
    # Retire instead via Bullet.is_active = 0.
    bullet_id: Mapped[int] = mapped_column(ForeignKey("bullet.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    run: Mapped[ApplicationRun] = relationship(back_populates="bullets")
    bullet: Mapped[Bullet] = relationship()

    __table_args__ = (
        UniqueConstraint("application_run_id", "bullet_id", name="uq_application_bullet"),
        Index("ix_application_bullet_bullet", "bullet_id"),
    )


# ---------------------------------------------------------------------------
# Proposal review (LLM-proposed bullet/title editing audit + feedback)
# ---------------------------------------------------------------------------


class ProposalReview(Base):
    """Audit + feedback record for one LLM-proposed bullet or title edit and the user's accept/reject decision."""

    __tablename__ = "proposal_review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_run_id: Mapped[int] = mapped_column(
        ForeignKey("application_run.id", ondelete="CASCADE"), nullable=False
    )
    bullet_id: Mapped[int | None] = mapped_column(
        ForeignKey("bullet.id", ondelete="SET NULL"), nullable=True
    )
    experience_title_id: Mapped[int | None] = mapped_column(
        ForeignKey("experience_title.id", ondelete="SET NULL"), nullable=True
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    user_edited_text: Mapped[str | None] = mapped_column(Text)  # NULL = user accepted as-is
    llm_critique_json: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)
    decided_at: Mapped[str | None] = mapped_column(String)

    run: Mapped[ApplicationRun] = relationship(back_populates="proposal_reviews")

    __table_args__ = (
        # Exactly one of bullet_id / experience_title_id must be set.
        CheckConstraint(
            "(bullet_id IS NOT NULL AND experience_title_id IS NULL) "
            "OR (bullet_id IS NULL AND experience_title_id IS NOT NULL)",
            name="ck_proposal_review_subject_xor",
        ),
        CheckConstraint(
            "decision IN ('pending', 'accept_original', 'accept_edit', 'reject')",
            name="ck_proposal_review_decision",
        ),
        Index("ix_proposal_review_run", "application_run_id"),
        Index("ix_proposal_review_bullet", "bullet_id"),
        Index("ix_proposal_review_title", "experience_title_id"),
    )


# ---------------------------------------------------------------------------
# Candidate memory: clarification, iteration log, engagement
# ---------------------------------------------------------------------------


class Clarification(Base):
    """Cross-application candidate memory: every Q&A pair the candidate has ever answered."""

    __tablename__ = "clarification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    origin_application_id: Mapped[int | None] = mapped_column(
        ForeignKey("application.id", ondelete="SET NULL"), nullable=True
    )
    origin_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_run.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    target_gap: Mapped[str | None] = mapped_column(Text)
    is_promoted_to_bullet: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    candidate: Mapped[Candidate] = relationship(back_populates="clarifications")
    tag_links: Mapped[list[ClarificationTag]] = relationship(
        back_populates="clarification", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('experience_probe', 'scope_probe', 'iteration_probe', 'outcome_probe', 'manual')",
            name="ck_clarification_kind",
        ),
        Index("ix_clarification_candidate_created", "candidate_id", "created_at"),
    )


class ClarificationTag(Base):
    """Tag join table linking a Clarification to a Tag, with a match-confidence weight."""

    __tablename__ = "clarification_tag"

    clarification_id: Mapped[int] = mapped_column(
        ForeignKey("clarification.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    clarification: Mapped[Clarification] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()

    __table_args__ = (Index("ix_clarification_tag_tag", "tag_id"),)


class IterationLog(Base):
    """One human-readable audit entry recording an action taken during an ApplicationRun."""

    __tablename__ = "iteration_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_run_id: Mapped[int] = mapped_column(
        ForeignKey("application_run.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    run: Mapped[ApplicationRun] = relationship(back_populates="log_entries")


class Engagement(Base):
    """One funnel-telemetry event for a candidate (and optional application) — opened, edited, abandoned, or submitted."""

    __tablename__ = "engagement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("application.id", ondelete="SET NULL"), nullable=True
    )
    event: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "event IN ('opened', 'edited_jd', 'abandoned', 'submitted_externally')",
            name="ck_engagement_event",
        ),
    )


__all__ = [  # noqa: RUF022 — curated domain grouping (Core / Career assets / …), not alphabetical
    "Base",
    "utc_now",
    # Core
    "Candidate",
    "Experience",
    "ExperienceTitle",
    "Bullet",
    "Tag",
    "BulletTag",
    "ExperienceTitleTag",
    "BulletMetric",
    # Career assets
    "Skill",
    "SkillTag",
    "Education",
    "Certification",
    "Project",
    "Publication",
    # Templates
    "PersonaTemplate",
    "PersonaTemplateTag",
    # Applications
    "Application",
    "ApplicationRun",
    "ApplicationRunTitle",
    "ApplicationBullet",
    # Memory + audit
    "ProposalReview",
    "Clarification",
    "ClarificationTag",
    "IterationLog",
    "Engagement",
]
