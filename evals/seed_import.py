"""Import a corpus seed.json into an in-memory SQLite for corpus-backed eval.

Deterministic, LLM-free (P1 hardening boundary — an ``evals/`` helper, no model
calls). The faithful inverse of ``scripts/export_corpus_seed.py::export_seed``:
reads a single-candidate ``seed.json`` (``seed_schema_version: 1``) and
reconstructs the Candidate / Tag / Experience / ExperienceTitle / Bullet /
SummaryItem / Skill / Education / Certification rows (plus the bullet / title /
summary tag links) into a fresh DB, **preserving the original primary keys** so
foreign-key joins round-trip unambiguously without a remap table.

The imported session feeds ``db.build_context.build_context_set_from_db``, so the
corpus-backed eval runner exercises the REAL product pipeline. The active-only /
JD-aware filtering stays inside ``build_context_set_from_db`` — the importer does
NOT pre-filter; it reconstructs the faithful snapshot (inactive rows included),
exactly as the exporter captured it.

Usage (the runner's ergonomic entry):

    from evals.seed_import import seeded_session
    with seeded_session("evals/fixtures/real/alex/seed.json") as (session, username):
        ctx, _app, _run = build_context_set_from_db(
            session, candidate_username=username, jd_text=jd, run_id=run_id,
        )
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

# The schema versions THIS importer knows how to read. Declared independently of
# the exporter's SEED_SCHEMA_VERSION on purpose: a future seed v2 with a changed
# shape must be REJECTED here until the importer is taught to read it, not
# silently half-imported because the exporter bumped its own constant.
SUPPORTED_SEED_SCHEMA_VERSIONS = frozenset({1})

# Top-level keys every v1 seed must carry (produced by export_seed).
_REQUIRED_TOP_LEVEL_KEYS = (
    "seed_schema_version",
    "candidate_username",
    "candidate",
    "tags",
    "experiences",
    "summary_items",
    "skills",
    "educations",
    "certifications",
)


def validate_seed(seed: Any) -> None:
    """Raise ValueError unless ``seed`` is an importable seed_schema_version-1 doc.

    Checks the schema version against ``SUPPORTED_SEED_SCHEMA_VERSIONS`` and that
    the required top-level collections are present. Fail-closed: shape drift is
    rejected rather than half-imported. The message names ``seed_schema_version``
    so callers/tests can match on it.
    """
    if not isinstance(seed, dict):
        raise ValueError(f"seed must be a JSON object, got {type(seed).__name__}")
    version = seed.get("seed_schema_version")
    if version not in SUPPORTED_SEED_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported seed_schema_version={version!r}; this importer reads "
            f"{sorted(SUPPORTED_SEED_SCHEMA_VERSIONS)}"
        )
    missing = [k for k in _REQUIRED_TOP_LEVEL_KEYS if k not in seed]
    if missing:
        raise ValueError(f"seed is missing required keys: {missing}")


def load_seed(path: str | Path) -> dict[str, Any]:
    """Read + validate a seed.json from disk. Raises on bad JSON or shape drift."""
    seed = cast("dict[str, Any]", json.loads(Path(path).read_text(encoding="utf-8")))
    validate_seed(seed)
    return seed


def _flag(value: Any) -> int:
    """Coerce a JSON bool (the exporter's shape) back to the source int column,
    so the imported row round-trips identically to the DB row it snapshotted."""
    return int(bool(value))


def import_seed(session: Session, seed: dict[str, Any]) -> str:
    """Insert one seed's rows into ``session`` in FK order; return the username.

    Validates the schema version first. The session is committed before
    returning; the caller owns the engine/session lifecycle (see
    ``seeded_session``).

    PK preservation: every entity carrying an ``id`` in the seed is inserted with
    that explicit id (the target DB is assumed empty, so no collision), which
    keeps the seed's tag_links FK-correct with no remap table. The Candidate
    carries no id (single-candidate by construction), so it is inserted and
    flushed to obtain a fresh id that all children reference. FK enforcement is
    ON (db/session.py sets ``PRAGMA foreign_keys=ON``), so each tier is flushed
    before the rows that reference it.
    """
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

    validate_seed(seed)

    c = seed["candidate"]
    candidate = Candidate(
        username=c["username"],
        name=c.get("name"),
        email=c.get("email"),
        phone=c.get("phone"),
        linkedin_url=c.get("linkedin_url"),
        website_url=c.get("website_url"),
        notes=c.get("notes"),
        profile_text=c.get("profile_text"),
    )
    session.add(candidate)
    session.flush()  # assign candidate.id for the child FKs below

    for t in seed["tags"]:
        session.add(
            Tag(
                id=t["id"],
                candidate_id=candidate.id,
                kind=t["kind"],
                value=t["value"],
                display_value=t["display_value"],
            )
        )
    session.flush()

    for exp in seed["experiences"]:
        session.add(
            Experience(
                id=exp["id"],
                candidate_id=candidate.id,
                company=exp["company"],
                location=exp.get("location"),
                start_date=exp["start_date"],
                end_date=exp.get("end_date"),
                display_order=exp.get("display_order", 0),
                summary=exp.get("summary"),
            )
        )
        session.flush()

        for title in exp["titles"]:
            session.add(
                ExperienceTitle(
                    id=title["id"],
                    experience_id=exp["id"],
                    title=title["title"],
                    is_official=_flag(title["is_official"]),
                    truthful_enough_to_use=_flag(title["truthful_enough_to_use"]),
                    is_pending_review=_flag(title["is_pending_review"]),
                    source=title["source"],
                )
            )
            session.flush()
            for link in title["tag_links"]:
                session.add(
                    ExperienceTitleTag(
                        experience_title_id=title["id"],
                        tag_id=link["tag_id"],
                        confidence=link["confidence"],
                    )
                )

        for bullet in exp["bullets"]:
            session.add(
                Bullet(
                    id=bullet["id"],
                    experience_id=exp["id"],
                    text=bullet["text"],
                    display_order=bullet.get("display_order", 0),
                    is_active=_flag(bullet["is_active"]),
                    is_pending_review=_flag(bullet["is_pending_review"]),
                    source=bullet["source"],
                    pattern_kind=bullet.get("pattern_kind"),
                    has_outcome=_flag(bullet["has_outcome"]),
                )
            )
            session.flush()
            for link in bullet["tag_links"]:
                session.add(
                    BulletTag(
                        bullet_id=bullet["id"],
                        tag_id=link["tag_id"],
                        confidence=link["confidence"],
                    )
                )

    for item in seed["summary_items"]:
        session.add(
            SummaryItem(
                id=item["id"],
                candidate_id=candidate.id,
                text=item["text"],
                label=item.get("label"),
                display_order=item.get("display_order", 0),
                is_active=_flag(item["is_active"]),
                is_pending_review=_flag(item["is_pending_review"]),
                source=item["source"],
                has_outcome=_flag(item["has_outcome"]),
            )
        )
        session.flush()
        for link in item["tag_links"]:
            session.add(
                SummaryItemTag(
                    summary_item_id=item["id"],
                    tag_id=link["tag_id"],
                    confidence=link["confidence"],
                )
            )

    for s in seed["skills"]:
        session.add(
            Skill(
                id=s["id"],
                candidate_id=candidate.id,
                name=s["name"],
                category=s.get("category"),
                proficiency=s.get("proficiency"),
                years=s.get("years"),
            )
        )

    for ed in seed["educations"]:
        session.add(
            Education(
                id=ed["id"],
                candidate_id=candidate.id,
                institution=ed["institution"],
                degree=ed.get("degree"),
                field=ed.get("field"),
                start_date=ed.get("start_date"),
                end_date=ed.get("end_date"),
                display_order=ed.get("display_order", 0),
                is_active=_flag(ed["is_active"]),
                notes=ed.get("notes"),
            )
        )

    for cert in seed["certifications"]:
        session.add(
            Certification(
                id=cert["id"],
                candidate_id=candidate.id,
                name=cert["name"],
                issuer=cert.get("issuer"),
                issued=cert.get("issued"),
                expires=cert.get("expires"),
                display_order=cert.get("display_order", 0),
                is_active=_flag(cert["is_active"]),
            )
        )

    session.commit()
    return candidate.username


@contextmanager
def seeded_session(seed: dict[str, Any] | str | Path) -> Iterator[tuple[Session, str]]:
    """Yield ``(session, candidate_username)`` over a fresh in-memory SQLite with
    the seed imported. Disposes the engine + closes the session on exit.

    Accepts an already-loaded seed dict or a path to a seed.json (loaded +
    validated via ``load_seed``). Mirrors the in-memory engine pattern in
    ``tests/conftest.py::db_session`` (engine disposed at teardown for Windows
    file-handle hygiene).
    """
    from db.models import Base
    from db.session import make_engine, make_session_factory

    seed_dict = seed if isinstance(seed, dict) else load_seed(seed)

    engine = make_engine(":memory:")
    Base.metadata.create_all(engine)
    session = make_session_factory(engine)()
    try:
        username = import_seed(session, seed_dict)
        yield session, username
    finally:
        session.close()
        engine.dispose()


__all__ = [
    "SUPPORTED_SEED_SCHEMA_VERSIONS",
    "import_seed",
    "load_seed",
    "seeded_session",
    "validate_seed",
]
