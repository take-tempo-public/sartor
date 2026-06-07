"""One-shot importer: file-based PII → SQLite corpus.

Scope:
- `configs/{user}.config` → candidate + skill + certification + education rows
- `output/{user}/context_*.json` → clarification rows (deduped)
- `resumes/{user}/{primary}` → experience + bullet rows (when --with-llm)

Idempotent: re-running picks up only new content. Candidate is matched by
`username`. Skills/certifications match by `(candidate_id, name)`.
Clarifications dedupe on (normalized_question, normalized_answer).
Experiences match on `(company, start_date)`.

CLI:
    python -m onboarding.corpus_import --user robert
    python -m onboarding.corpus_import --user robert --dry-run
    python -m onboarding.corpus_import --user robert --with-llm     # Haiku call, ~$0.02
    python -m onboarding.corpus_import --user robert --db /tmp/test.sqlite
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from db.models import (
    Bullet,
    Candidate,
    Certification,
    Clarification,
    Education,
    Experience,
    ExperienceTitle,
    Skill,
)
from db.session import get_session, init_db

logger = logging.getLogger(__name__)

# Repo-relative paths to existing file-based PII.
_REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = _REPO_ROOT / "configs"
OUTPUT_DIR = _REPO_ROOT / "output"
RESUMES_DIR = _REPO_ROOT / "resumes"


# ---------------------------------------------------------------------------
# Dry-run result reporting
# ---------------------------------------------------------------------------


@dataclass
class ImportReport:
    """Summary returned by every importer entry point.

    `created` counts are number of NEW rows. `skipped` counts are duplicates
    that already existed (idempotency working). `errors` is any exception
    message we caught and continued past.
    """

    candidate_created: bool = False
    candidate_id: int | None = None
    skills_created: int = 0
    skills_skipped: int = 0
    certifications_created: int = 0
    certifications_skipped: int = 0
    education_created: int = 0
    education_skipped: int = 0
    clarifications_created: int = 0
    clarifications_skipped: int = 0
    context_files_scanned: int = 0
    experiences_created: int = 0
    experiences_merged: int = 0
    bullets_created: int = 0
    alternate_titles_created: int = 0
    resume_files_processed: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: ImportReport) -> None:
        self.skills_created += other.skills_created
        self.skills_skipped += other.skills_skipped
        self.certifications_created += other.certifications_created
        self.certifications_skipped += other.certifications_skipped
        self.education_created += other.education_created
        self.education_skipped += other.education_skipped
        self.clarifications_created += other.clarifications_created
        self.clarifications_skipped += other.clarifications_skipped
        self.context_files_scanned += other.context_files_scanned
        self.experiences_created += other.experiences_created
        self.experiences_merged += other.experiences_merged
        self.bullets_created += other.bullets_created
        self.alternate_titles_created += other.alternate_titles_created
        self.resume_files_processed += other.resume_files_processed
        self.errors.extend(other.errors)


# ---------------------------------------------------------------------------
# Config → candidate + assets
# ---------------------------------------------------------------------------


def _safe_load_config(username: str) -> dict[str, Any]:
    """Read configs/{user}.config; return {} if absent."""
    path = CONFIGS_DIR / f"{username}.config"
    if not path.exists():
        raise FileNotFoundError(f"No config found at {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def import_candidate_from_config(
    username: str,
    session: Session,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Read configs/{user}.config and seed candidate + skills + certs + education.

    Idempotent: existing candidate (matched on `username`) gets non-destructive
    updates only for empty fields. Skills/certs/education match by name and
    are skipped if already present.
    """
    report = ImportReport()
    cfg = _safe_load_config(username)

    candidate = session.query(Candidate).filter_by(username=username).first()
    if candidate is None:
        candidate = Candidate(
            username=username,
            name=cfg.get("name") or None,
            email=cfg.get("email") or None,
            phone=cfg.get("phone") or None,
            linkedin_url=cfg.get("linkedin_url") or None,
            website_url=cfg.get("website_url") or None,
            notes=cfg.get("notes") or None,
        )
        report.candidate_created = True
        if not dry_run:
            session.add(candidate)
            session.flush()  # populate id without commit
        else:
            # Use a placeholder id for the dry-run report
            candidate.id = -1
    else:
        # Fill empty fields only — never overwrite real data on re-import.
        for fld in ("name", "email", "phone", "linkedin_url", "website_url", "notes"):
            if not getattr(candidate, fld) and cfg.get(fld):
                setattr(candidate, fld, cfg[fld])

    report.candidate_id = candidate.id

    # Skills: list of strings
    for raw in cfg.get("skills") or []:
        name = raw.strip() if isinstance(raw, str) else ""
        if not name:
            continue
        if not dry_run and session.query(Skill).filter_by(
            candidate_id=candidate.id, name=name
        ).first() is not None:
            report.skills_skipped += 1
            continue
        if not dry_run:
            session.add(Skill(candidate_id=candidate.id, name=name))
        report.skills_created += 1

    # Certifications: list of strings (legacy schema is flat)
    for raw in cfg.get("certifications") or []:
        name = raw.strip() if isinstance(raw, str) else ""
        if not name:
            continue
        if not dry_run and session.query(Certification).filter_by(
            candidate_id=candidate.id, name=name
        ).first() is not None:
            report.certifications_skipped += 1
            continue
        if not dry_run:
            session.add(Certification(candidate_id=candidate.id, name=name))
        report.certifications_created += 1

    # Education: single free-text "education_summary" field in legacy schema.
    # Store it as one Education row with the entire summary as `institution`.
    # User can split it in the Career Corpus tab during Phase D.
    edu_summary = (cfg.get("education_summary") or "").strip()
    if edu_summary:
        if not dry_run and session.query(Education).filter_by(
            candidate_id=candidate.id, institution=edu_summary
        ).first() is not None:
            report.education_skipped += 1
        else:
            if not dry_run:
                session.add(Education(
                    candidate_id=candidate.id,
                    institution=edu_summary,
                    notes="Imported from legacy education_summary; split into structured rows when ready.",
                ))
            report.education_created += 1

    # Flush so the report's counters match what subsequent SELECTs will see.
    # (We use autoflush=False to keep transactional control with the caller.)
    if not dry_run:
        session.flush()
    return report


# ---------------------------------------------------------------------------
# Output context files → clarifications
# ---------------------------------------------------------------------------


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(s: str) -> str:
    """Lowercase + collapse whitespace for dedup. Not for display."""
    return _WHITESPACE_RE.sub(" ", s.strip().lower())


def _iter_context_files(username: str) -> list[Path]:
    user_dir = OUTPUT_DIR / username
    if not user_dir.exists():
        return []
    return sorted(user_dir.glob("context_*.json"))


def _extract_qa_pairs(context: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """Return [(question_id, question_text, answer_text, kind), ...] from one context.

    Pairs `clarification_questions` (carry the text + kind) with `clarifications`
    (the dict of id → answer). Skips questions the user didn't answer.
    """
    questions = context.get("clarification_questions") or []
    answers = context.get("clarifications") or {}
    out: list[tuple[str, str, str, str]] = []
    for q in questions:
        qid = q.get("id")
        qtext = q.get("text", "").strip()
        kind = q.get("kind", "manual")
        if not qid or not qtext:
            continue
        atext = (answers.get(qid) or "").strip()
        if not atext:
            continue
        out.append((qid, qtext, atext, kind))
    return out


_VALID_KINDS = {"experience_probe", "scope_probe", "iteration_probe", "outcome_probe", "manual"}


def import_clarifications_from_output(
    username: str,
    candidate_id: int,
    session: Session,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Bulk-import every Q&A pair found in `output/{user}/context_*.json`.

    Dedupes on `(normalized_question, normalized_answer)` across all context
    files for this candidate. Both intra-file dupes (same Q&A repeated in
    iter chain) and re-runs are caught.

    `origin_application_id` / `origin_run_id` are left NULL — Phase A doesn't
    yet have application rows. Phase B's pipeline migration will backfill them
    by matching context-file timestamps to newly-created application rows.
    """
    report = ImportReport()

    # Build the existing-keys set once so we dedupe against already-imported rows.
    existing_keys: set[tuple[str, str]] = set()
    if not dry_run:
        for row in session.query(Clarification.question, Clarification.answer).filter_by(
            candidate_id=candidate_id
        ):
            existing_keys.add((_normalize(row[0]), _normalize(row[1])))

    seen_this_run: set[tuple[str, str]] = set()

    for ctx_path in _iter_context_files(username):
        report.context_files_scanned += 1
        try:
            with ctx_path.open(encoding="utf-8") as fh:
                ctx = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            report.errors.append(f"{ctx_path.name}: {exc}")
            continue

        for _qid, qtext, atext, kind in _extract_qa_pairs(ctx):
            dedup_key = (_normalize(qtext), _normalize(atext))
            if dedup_key in existing_keys or dedup_key in seen_this_run:
                report.clarifications_skipped += 1
                continue
            seen_this_run.add(dedup_key)
            safe_kind = kind if kind in _VALID_KINDS else "manual"
            if not dry_run:
                session.add(Clarification(
                    candidate_id=candidate_id,
                    question=qtext,
                    answer=atext,
                    kind=safe_kind,
                    target_gap=None,
                ))
            report.clarifications_created += 1

    if not dry_run:
        session.flush()
    return report


# ---------------------------------------------------------------------------
# Resumes → experiences + bullets (LLM-assisted)
# ---------------------------------------------------------------------------


_RESUME_EXTS = (".docx", ".pdf", ".md")


def _iter_resume_files(username: str) -> list[Path]:
    """Return resume files for `username` in deliberate processing order.

    Order: primary first (from `config.latest_resume`), then any other files
    listed in `config.included_resumes`, then any remaining files alphabetical.
    The primary-first ordering matters: the first file's `candidate_inferred_title`
    becomes the experience's `is_official=1` title; subsequent files contribute
    alternates (see `_merge_into_existing_experience`).

    If config is missing or has no resume hints, falls back to alphabetical.
    """
    user_dir = RESUMES_DIR / username
    if not user_dir.exists():
        return []
    available = sorted(
        p for p in user_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _RESUME_EXTS
    )

    cfg_path = CONFIGS_DIR / f"{username}.config"
    if not cfg_path.exists():
        return available

    try:
        with cfg_path.open(encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return available

    primary = (cfg.get("latest_resume") or "").strip()
    included = cfg.get("included_resumes")
    # Filter to included files if the whitelist is present. None / [] / missing
    # all mean "include everything" for compat with configs that never set it.
    if isinstance(included, list) and included:
        included_set = {str(name).strip() for name in included if name}
        available = [p for p in available if p.name in included_set]

    # Sort: primary first, then everything else alphabetical (the original order).
    if primary:
        primary_paths = [p for p in available if p.name == primary]
        rest = [p for p in available if p.name != primary]
        return primary_paths + rest
    return available


def import_experiences_from_resumes(
    username: str,
    candidate_id: int,
    session: Session,
    *,
    dry_run: bool = False,
    api_key: str | None = None,
) -> ImportReport:
    """Parse each resume file in `resumes/{user}/` and extract experiences via Haiku.

    One LLM call per resume file (~$0.01-0.03 each). All extracted experiences
    are inserted as `is_pending_review=1` so the user reviews them in the
    Career Corpus tab (Phase D) before they become canonical corpus content.

    Idempotent at the experience level: re-runs skip experiences whose
    `(company, start_date)` already exists. Bullets are NOT deduped (different
    resume files often have different phrasings of the same achievement; the
    user prunes duplicates in review).

    Requires `api_key` (or `.api_key` file at repo root, or `ANTHROPIC_API_KEY`
    env var). Returns an ImportReport with experience/bullet counters.
    """
    report = ImportReport()

    # Lazy import — pulls in anthropic SDK; defer until --with-llm is engaged.
    # (parse_resume / extract_experiences are imported inside ingest_one_resume.)
    import anthropic

    resolved_key = _resolve_api_key(api_key)
    if not resolved_key:
        report.errors.append(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY, pass --api-key, "
            "or place key in .api_key at repo root."
        )
        return report
    client = anthropic.Anthropic(api_key=resolved_key)

    files = _iter_resume_files(username)
    for index, resume_path in enumerate(files):
        is_primary = (index == 0)  # _iter_resume_files puts primary first
        ingest_one_resume(
            resume_path, candidate_id, session,
            client=client, username=username, is_primary=is_primary,
            dry_run=dry_run, report=report,
        )

    if not dry_run:
        session.flush()
    return report


def ingest_one_resume(
    resume_path: Path,
    candidate_id: int,
    session: Session,
    *,
    client: Any,
    username: str,
    is_primary: bool = False,
    dry_run: bool = False,
    report: ImportReport | None = None,
) -> ImportReport:
    """Parse + Haiku-extract a single resume file and insert/merge its
    experiences as `is_pending_review=1`. Shared by the CLI importer's
    per-file loop AND the live `/api/users/<u>/corpus/ingest-resume`
    route so the merge-as-alternate-title behavior never forks.

    The caller owns session lifecycle + commit; this only flushes (when
    not dry_run) so it composes inside both call sites.
    """
    from onboarding.extract_experiences import extract_experiences
    from parser import parse_resume

    report = report if report is not None else ImportReport()
    report.resume_files_processed += 1
    try:
        parsed = parse_resume(str(resume_path))
    except Exception as exc:
        report.errors.append(f"parse {resume_path.name}: {exc}")
        return report

    resume_text = parsed.get("text", "")
    if not resume_text.strip():
        report.errors.append(f"parse {resume_path.name}: empty text after parsing")
        return report

    try:
        extracted = extract_experiences(client, resume_text, username=username)
    except Exception as exc:
        report.errors.append(f"extract {resume_path.name}: {exc}")
        return report

    for exp in extracted:
        _insert_or_merge_experience(
            exp, candidate_id,
            source_filename=resume_path.name,
            is_primary_file=is_primary,
            session=session, dry_run=dry_run, report=report,
        )
    if not dry_run:
        session.flush()
    return report


def _resolve_api_key(explicit: str | None) -> str | None:
    """Search explicit arg → env var → `.api_key` file at repo root."""
    if explicit:
        return explicit.strip()
    env = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env:
        return env
    key_file = _REPO_ROOT / ".api_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip() or None
    return None


def _insert_or_merge_experience(
    exp: Mapping[str, Any],
    candidate_id: int,
    *,
    source_filename: str,
    is_primary_file: bool,
    session: Session,
    dry_run: bool,
    report: ImportReport,
) -> None:
    """Insert an extracted experience or MERGE into an existing match.

    Dedup key: (candidate_id, company, start_date). On match, the new file's
    `candidate_inferred_title` becomes an alternate `experience_title` row
    (is_official=0, is_pending_review=1) — preserving the multi-framing
    intent of the redesign. New bullets append unless (source, text) already
    exists on the experience.

    `is_primary_file` controls bullet provenance: True → `primary:<file>`,
    False → `supplemental:<file>`. Only meaningful for new experiences; merge
    path uses the supplemental prefix because the experience itself was
    created by an earlier file.
    """
    company = exp.get("company", "")
    start_date = exp.get("start_date", "")
    title_text = exp.get("candidate_inferred_title", "")
    if not company or not start_date:
        return  # _normalize_experience emitted a sentinel; nothing to do

    if dry_run:
        # Same-shape counting for visibility; can't know existing matches
        # without LLM extraction, so report all as creates.
        report.experiences_created += 1
        for b in exp.get("bullets", []):
            if b.get("text"):
                report.bullets_created += 1
        return

    existing = session.query(Experience).filter_by(
        candidate_id=candidate_id, company=company, start_date=start_date,
    ).first()

    if existing is not None:
        _merge_into_existing_experience(
            existing, exp, source_filename=source_filename,
            session=session, report=report,
        )
        return

    # Net-new experience: create + official title + bullets.
    experience_row = Experience(
        candidate_id=candidate_id,
        company=company,
        location=exp.get("location") or None,
        start_date=start_date,
        end_date=exp.get("end_date"),
        summary=None,
    )
    session.add(experience_row)
    session.flush()  # need experience_row.id for FKs

    if title_text:
        session.add(ExperienceTitle(
            experience_id=experience_row.id,
            title=title_text,
            is_official=1,
            truthful_enough_to_use=1,
            is_pending_review=1,
            source="user_added",
            notes=f"Imported from {source_filename}; review before promoting to canonical.",
        ))

    source_prefix = "primary" if is_primary_file else "supplemental"
    for b in exp.get("bullets", []):
        btext = b.get("text", "")
        if not btext:
            continue
        session.add(Bullet(
            experience_id=experience_row.id,
            text=btext,
            display_order=report.bullets_created,
            is_active=1,
            is_pending_review=1,
            source=f"{source_prefix}:{source_filename}",
            has_outcome=1 if b.get("has_outcome") else 0,
        ))
        report.bullets_created += 1

    report.experiences_created += 1


def _merge_into_existing_experience(
    existing: Experience,
    exp: Mapping[str, Any],
    *,
    source_filename: str,
    session: Session,
    report: ImportReport,
) -> None:
    """A subsequent file produced the same (company, start_date). Treat its
    extraction as alternate framing material:

    - If the new title text doesn't already exist on this experience, add it
      as an alternate (is_official=0, truthful_enough_to_use=1, is_pending_review=1).
    - Append every new bullet whose *normalized text* isn't already attached.
      Different files often phrase the same achievement differently — those
      different phrasings get kept and the user prunes them in review.
      Identical phrasings dedupe at the (experience_id, normalized_text)
      boundary regardless of source. (The previous (source, text) key
      missed same-file re-imports because the source flips from
      `primary:<file>` to `supplemental:<file>` on the merge path, so the
      same text under two different sources looked like two distinct
      bullets.)

    Implementation note: we query titles/bullets directly rather than going
    through `existing.titles` / `existing.bullets` because the relationship
    cache on the in-session Experience object doesn't reflect FK-only inserts
    until refresh — and we add via FK above for performance. Direct query is
    cheap (single small index lookup per merge) and unambiguous.
    """
    report.experiences_merged += 1
    title_text = exp.get("candidate_inferred_title", "")

    # Flush any pending inserts from earlier calls so our SELECT queries below
    # see them. (session.autoflush=False means we have to do this explicitly.)
    session.flush()

    if title_text:
        existing_title_set = {
            row[0] for row in session.query(ExperienceTitle.title).filter(
                ExperienceTitle.experience_id == existing.id
            )
        }
        if title_text not in existing_title_set:
            session.add(ExperienceTitle(
                experience_id=existing.id,
                title=title_text,
                is_official=0,
                truthful_enough_to_use=1,
                is_pending_review=1,
                source="user_added",
                notes=f"Alternate framing from {source_filename}; review and promote if accurate.",
            ))
            report.alternate_titles_created += 1

    source_value = f"supplemental:{source_filename}"
    # Dedup on normalized text only (lowercased + whitespace-collapsed).
    # The old (source, text) key let same-file re-imports through because
    # the source flips primary→supplemental between runs; normalizing
    # the text and ignoring the source catches that case AND continues
    # to keep genuinely different phrasings from different files.
    existing_bullet_keys = {
        _normalize(row[0]) for row in session.query(Bullet.text).filter(
            Bullet.experience_id == existing.id
        )
    }
    existing_bullet_count = session.query(Bullet).filter(
        Bullet.experience_id == existing.id
    ).count()
    for b in exp.get("bullets", []):
        btext = b.get("text", "")
        if not btext:
            continue
        norm_btext = _normalize(btext)
        if norm_btext in existing_bullet_keys:
            continue
        session.add(Bullet(
            experience_id=existing.id,
            text=btext,
            display_order=existing_bullet_count + report.bullets_created,
            is_active=1,
            is_pending_review=1,
            source=source_value,
            has_outcome=1 if b.get("has_outcome") else 0,
        ))
        # Track within this loop so two identical bullets in the same
        # extraction don't both insert.
        existing_bullet_keys.add(norm_btext)
        report.bullets_created += 1


# ---------------------------------------------------------------------------
# Top-level entry points
# ---------------------------------------------------------------------------


def run_import(
    username: str,
    *,
    dry_run: bool = False,
    with_llm: bool = False,
    api_key: str | None = None,
    db_path: Path | str | None = None,
) -> ImportReport:
    """Run the full importer for one candidate.

    Always imports candidate + skills + certifications + education from config
    and clarifications from output context files. When with_llm=True, ALSO
    parses resumes from `resumes/{user}/` via Haiku and inserts experiences
    + bullets as is_pending_review=1.

    On dry_run, no rows are committed and no LLM calls are made (counts in
    the report are computed but not persisted).
    """
    init_db(db_path)
    session = get_session() if db_path is None else _make_isolated_session(db_path)
    try:
        candidate_report = import_candidate_from_config(username, session, dry_run=dry_run)
        if candidate_report.candidate_id is None:
            return candidate_report
        clarif_report = import_clarifications_from_output(
            username, candidate_report.candidate_id, session, dry_run=dry_run
        )
        candidate_report.merge(clarif_report)

        if with_llm and not dry_run:
            exp_report = import_experiences_from_resumes(
                username, candidate_report.candidate_id, session,
                dry_run=dry_run, api_key=api_key,
            )
            candidate_report.merge(exp_report)
        elif with_llm and dry_run:
            # In dry-run, just count resume files so the user sees what WOULD run.
            files = _iter_resume_files(username)
            candidate_report.resume_files_processed = len(files)

        if dry_run:
            session.rollback()
        else:
            session.commit()
        return candidate_report
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _make_isolated_session(db_path: Path | str) -> Session:
    """Build a session against an explicit DB path (not the process-wide default)."""
    from db.session import make_engine, make_session_factory
    eng = make_engine(db_path)
    return make_session_factory(eng)()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(report: ImportReport, *, dry_run: bool) -> str:
    prefix = "[DRY-RUN] " if dry_run else ""
    lines = [
        f"{prefix}Candidate id={report.candidate_id} "
        f"({'created' if report.candidate_created else 'updated'})",
        f"{prefix}Skills:         created={report.skills_created:3d}, skipped={report.skills_skipped:3d}",
        f"{prefix}Certifications: created={report.certifications_created:3d}, skipped={report.certifications_skipped:3d}",
        f"{prefix}Education:      created={report.education_created:3d}, skipped={report.education_skipped:3d}",
        f"{prefix}Clarifications: created={report.clarifications_created:3d}, "
        f"skipped={report.clarifications_skipped:3d} "
        f"(scanned {report.context_files_scanned} context files)",
    ]
    if report.resume_files_processed or report.experiences_created or report.experiences_merged:
        lines.append(
            f"{prefix}Experiences:    created={report.experiences_created:3d}, "
            f"merged={report.experiences_merged:3d} "
            f"(processed {report.resume_files_processed} resume files)"
        )
        lines.append(
            f"{prefix}Bullets:        created={report.bullets_created:3d}, "
            f"alternate-titles={report.alternate_titles_created:3d}"
        )
    if report.errors:
        lines.append(f"{prefix}Errors ({len(report.errors)}):")
        for err in report.errors[:10]:
            lines.append(f"{prefix}  - {err}")
        if len(report.errors) > 10:
            lines.append(f"{prefix}  ... ({len(report.errors) - 10} more)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import legacy file-based PII into the SQLite corpus.",
    )
    parser.add_argument("--user", required=True, help="Username (matches configs/{user}.config)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted, no DB writes")
    parser.add_argument("--with-llm", action="store_true",
                        help="Also parse resumes via Haiku and import experiences + bullets (~$0.02/run)")
    parser.add_argument("--api-key", default=None,
                        help="Anthropic API key override (else uses ANTHROPIC_API_KEY env or .api_key file)")
    parser.add_argument("--db", default=None, help="Override DB path (defaults to db/resume.sqlite)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        report = run_import(
            args.user,
            dry_run=args.dry_run,
            with_llm=args.with_llm,
            api_key=args.api_key,
            db_path=args.db,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(_format_report(report, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
