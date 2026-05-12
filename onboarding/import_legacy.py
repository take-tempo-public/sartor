"""One-shot importer: file-based PII → SQLite corpus.

Phase A scope:
- `configs/{user}.config` → candidate + skill + certification + education rows
- `output/{user}/context_*.json` → clarification rows (deduped)
- Resume parsing (experience + bullet extraction) is deferred to a separate
  `extract_experiences.py` module so this importer stays LLM-free and
  cheaply testable.

Idempotent: re-running picks up only new content. Candidate is matched by
`username`. Skills/certifications match by `(candidate_id, name)`.
Clarifications dedupe on (normalized_question, normalized_answer).

CLI:
    python -m onboarding.import_legacy --user robert
    python -m onboarding.import_legacy --user robert --dry-run
    python -m onboarding.import_legacy --user robert --db /tmp/test.sqlite
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from db.models import (
    Candidate,
    Certification,
    Clarification,
    Education,
    Skill,
)
from db.session import get_session, init_db

logger = logging.getLogger(__name__)

# Repo-relative paths to existing file-based PII.
_REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = _REPO_ROOT / "configs"
OUTPUT_DIR = _REPO_ROOT / "output"


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
# Top-level entry points
# ---------------------------------------------------------------------------


def run_import(
    username: str,
    *,
    dry_run: bool = False,
    db_path: Path | str | None = None,
) -> ImportReport:
    """Run the full Phase A import for one candidate.

    Materializes the DB schema if needed, then runs the config and
    clarification importers in sequence. On dry_run, no rows are committed.
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
    parser.add_argument("--db", default=None, help="Override DB path (defaults to db/resume.sqlite)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        report = run_import(args.user, dry_run=args.dry_run, db_path=args.db)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(_format_report(report, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
