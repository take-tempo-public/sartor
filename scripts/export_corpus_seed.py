"""Export one candidate's corpus from the SQLite DB to a portable seed.json.

Deterministic, LLM-free snapshot tool (P1 hardening boundary — a `scripts/`
exporter, no model calls). Reads Candidate / Experience / ExperienceTitle /
Bullet / SummaryItem / Skill / Education / Certification (+ the candidate-scoped
Tag registry and the bullet/title/summary tag links) and writes a single-
candidate JSON document under the gitignored `evals/fixtures/real/`.

The `seed.json` shape is the contract consumed by the next branch
(`eval/corpus-backed-runner`), which imports it into an in-memory SQLite and
feeds `db.build_context.build_context_set_from_db`. Original DB primary keys are
preserved so foreign-key relationships (tag links → tags) round-trip
unambiguously.

A `_within`-style resolved-path guard (mirroring `app.py:_within`) refuses to
write anywhere except `evals/fixtures/real/`, so a stray `--out` can't leak the
snapshot — which contains real PII — outside the gitignored tree.

Usage:
    python -m scripts.export_corpus_seed --user alex
    python -m scripts.export_corpus_seed --user alex --stdout
    python -m scripts.export_corpus_seed --user alex --out evals/fixtures/real/alex/seed.json
    python -m scripts.export_corpus_seed --user alex --db path/to/copy.sqlite
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

SEED_SCHEMA_VERSION = 1
GENERATOR = "scripts/export_corpus_seed.py"

# scripts/export_corpus_seed.py → repo root is two parents up.
REPO_ROOT = Path(__file__).resolve().parent.parent
# The only directory this tool is ever allowed to write into. Already gitignored
# (evals/fixtures/real/* in .gitignore), so the snapshot's PII stays untracked.
ALLOWED_ROOT = REPO_ROOT / "evals" / "fixtures" / "real"


# ---------------------------------------------------------------------------
# Pure core — read-only DB → seed dict. Filesystem-free, so it unit-tests
# against an in-memory session with no I/O.
# ---------------------------------------------------------------------------


def export_seed(session: Session, *, candidate_username: str) -> dict[str, Any]:
    """Build the seed document for one candidate from DB rows.

    Read-only. Raises ValueError (same message style as
    `build_context_set_from_db`) when the candidate does not exist. The export
    is a faithful snapshot — ALL rows are captured (active and inactive); the
    active-only / JD-aware filtering lives in `build_context_set_from_db`, so
    the importer reproduces real pipeline behavior rather than the exporter
    pre-deciding it.
    """
    from db.models import (
        Candidate,
        Certification,
        Education,
        Experience,
        Skill,
        SummaryItem,
        Tag,
        utc_now,
    )

    candidate = session.query(Candidate).filter_by(username=candidate_username).first()
    if candidate is None:
        raise ValueError(f"No candidate with username={candidate_username!r}")

    tags = session.query(Tag).filter_by(candidate_id=candidate.id).order_by(Tag.id).all()
    experiences = (
        session.query(Experience)
        .filter_by(candidate_id=candidate.id)
        .order_by(Experience.display_order, Experience.id)
        .all()
    )
    summary_items = (
        session.query(SummaryItem)
        .filter_by(candidate_id=candidate.id)
        .order_by(SummaryItem.display_order, SummaryItem.id)
        .all()
    )
    skills = (
        session.query(Skill)
        .filter_by(candidate_id=candidate.id)
        .order_by(Skill.name, Skill.id)
        .all()
    )
    educations = (
        session.query(Education)
        .filter_by(candidate_id=candidate.id)
        .order_by(Education.display_order, Education.id)
        .all()
    )
    certifications = (
        session.query(Certification)
        .filter_by(candidate_id=candidate.id)
        .order_by(Certification.display_order, Certification.id)
        .all()
    )

    return {
        "seed_schema_version": SEED_SCHEMA_VERSION,
        "generator": GENERATOR,
        "exported_at": utc_now(),
        "candidate_username": candidate.username,
        "candidate": {
            "username": candidate.username,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "linkedin_url": candidate.linkedin_url,
            "website_url": candidate.website_url,
            "notes": candidate.notes,
            "profile_text": candidate.profile_text,
        },
        "tags": [_tag_row(t) for t in tags],
        "experiences": [_experience_row(e) for e in experiences],
        "summary_items": [_summary_item_row(s) for s in summary_items],
        "skills": [_skill_row(s) for s in skills],
        "educations": [_education_row(e) for e in educations],
        "certifications": [_certification_row(c) for c in certifications],
    }


def _tag_links(links: Any) -> list[dict[str, Any]]:
    """Serialize a list of *Tag join rows (BulletTag / ExperienceTitleTag /
    SummaryItemTag) to {tag_id, confidence}, ordered by tag_id for stable diffs."""
    rows = [{"tag_id": link.tag_id, "confidence": link.confidence} for link in links]
    rows.sort(key=lambda r: r["tag_id"])
    return rows


def _tag_row(tag: Any) -> dict[str, Any]:
    return {
        "id": tag.id,
        "kind": tag.kind,
        "value": tag.value,
        "display_value": tag.display_value,
    }


def _experience_row(exp: Any) -> dict[str, Any]:
    titles = sorted(exp.titles, key=lambda t: t.id)
    bullets = sorted(exp.bullets, key=lambda b: (b.display_order, b.id))
    return {
        "id": exp.id,
        "company": exp.company,
        "location": exp.location,
        "start_date": exp.start_date,
        "end_date": exp.end_date,
        "display_order": exp.display_order,
        "summary": exp.summary,
        "titles": [_title_row(t) for t in titles],
        "bullets": [_bullet_row(b) for b in bullets],
    }


def _title_row(title: Any) -> dict[str, Any]:
    return {
        "id": title.id,
        "title": title.title,
        "is_official": bool(title.is_official),
        "truthful_enough_to_use": bool(title.truthful_enough_to_use),
        "is_pending_review": bool(title.is_pending_review),
        "source": title.source,
        "tag_links": _tag_links(title.tag_links),
    }


def _bullet_row(bullet: Any) -> dict[str, Any]:
    return {
        "id": bullet.id,
        "text": bullet.text,
        "display_order": bullet.display_order,
        "is_active": bool(bullet.is_active),
        "is_pending_review": bool(bullet.is_pending_review),
        "source": bullet.source,
        "pattern_kind": bullet.pattern_kind,
        "has_outcome": bool(bullet.has_outcome),
        "tag_links": _tag_links(bullet.tag_links),
    }


def _summary_item_row(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "text": item.text,
        "label": item.label,
        "display_order": item.display_order,
        "is_active": bool(item.is_active),
        "is_pending_review": bool(item.is_pending_review),
        "source": item.source,
        "has_outcome": bool(item.has_outcome),
        "tag_links": _tag_links(item.tag_links),
    }


def _skill_row(skill: Any) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category,
        "proficiency": skill.proficiency,
        "years": skill.years,
    }


def _education_row(ed: Any) -> dict[str, Any]:
    return {
        "id": ed.id,
        "institution": ed.institution,
        "degree": ed.degree,
        "field": ed.field,
        "start_date": ed.start_date,
        "end_date": ed.end_date,
        "display_order": ed.display_order,
        "is_active": bool(ed.is_active),
        "notes": ed.notes,
    }


def _certification_row(cert: Any) -> dict[str, Any]:
    return {
        "id": cert.id,
        "name": cert.name,
        "issuer": cert.issuer,
        "issued": cert.issued,
        "expires": cert.expires,
        "display_order": cert.display_order,
        "is_active": bool(cert.is_active),
    }


# ---------------------------------------------------------------------------
# Write-path guard — defense against emitting the (PII-bearing) snapshot
# anywhere except evals/fixtures/real/.
# ---------------------------------------------------------------------------


def _within(path: Path, parent: Path) -> bool:
    """Return True only if path resolves to within parent. Mirrors app.py:_within."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_output_path(username: str, out_arg: str | None) -> Path:
    """Compute the seed.json path and enforce containment under ALLOWED_ROOT.

    Default: `<ALLOWED_ROOT>/<secure_filename(username)>/seed.json`. With
    `--out`, the given path is resolved and must still live under ALLOWED_ROOT.
    Raises ValueError on a sanitized-empty username or an out-of-bounds target —
    the guard fails closed (no write).
    """
    if out_arg:
        target = Path(out_arg).expanduser()
    else:
        safe = secure_filename(username)
        if not safe:
            raise ValueError(f"username {username!r} sanitizes to empty; cannot place seed")
        target = ALLOWED_ROOT / safe / "seed.json"

    if not _within(target, ALLOWED_ROOT):
        raise ValueError(
            f"refusing to write outside {ALLOWED_ROOT.as_posix()} "
            f"(resolved target: {target.resolve().as_posix()})"
        )
    return target.resolve()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _open_session(db_arg: str | None) -> tuple[Session, Any]:
    """Open a session, running migrations idempotently. Returns (session, engine)
    where engine is non-None only for a `--db`-supplied path (so main can dispose
    the dedicated engine; the process-wide default engine is left alone)."""
    from db.session import get_session, init_db, make_engine, make_session_factory

    if db_arg:
        db_path = Path(db_arg).expanduser()
        if not db_path.exists():
            raise FileNotFoundError(f"no SQLite DB at {db_path}")
        init_db(db_path)
        engine = make_engine(db_path)
        return make_session_factory(engine)(), engine

    init_db()
    return get_session(), None


def main() -> int:
    # Windows cp1252 consoles can't encode the unicode in this script's output
    # (the `→` success line, the em-dashes in `--help`/`__doc__`), which crashed
    # the run AFTER the seed had already been written (window-8.5-findings EV-3).
    # Force UTF-8 on our streams before argparse or any print runs.
    for _stream in (sys.stdout, sys.stderr):
        # suppress on a non-reconfigurable stream (e.g. piped)
        with contextlib.suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--user",
        "--username",
        dest="user",
        required=True,
        help="Candidate username to export.",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Output path (must resolve under evals/fixtures/real/). "
        "Default: evals/fixtures/real/<user>/seed.json",
    )
    ap.add_argument(
        "--db",
        default=None,
        help="SQLite DB file to read from (default: the app's db/resume.sqlite).",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Print the seed JSON to stdout instead of writing a file.",
    )
    args = ap.parse_args()

    session, engine = None, None
    try:
        session, engine = _open_session(args.db)
        seed = export_seed(session, candidate_username=args.user)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 1
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()

    payload = json.dumps(seed, indent=2, ensure_ascii=False)

    if args.stdout:
        print(payload)
        return 0

    try:
        out_path = _resolve_output_path(args.user, args.out)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload + "\n", encoding="utf-8")

    n_bullets = sum(len(e["bullets"]) for e in seed["experiences"])
    print(
        f"{len(seed['experiences'])} experiences, {n_bullets} bullets, "
        f"{len(seed['summary_items'])} summary items, {len(seed['skills'])} skills "
        f"→ {out_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
