"""One-off backfill: retitle Application rows still on the raw first-line inference.

Deterministic, LLM-free (P1 hardening boundary — a `scripts/` tool, no model
calls). `db.build_context.build_context_set_from_db` used to title every new
application `_infer_application_title(jd_text)` — the raw first non-empty JD
line, truncated to 80 chars. That call site now uses `_infer_role_title`
(role-title ONLY — owner spec, fix/review-surface-and-flows; company already
renders separately via `Application.company`/F-15, so the title never
prefixes it), but existing rows created before this fix keep their old
raw-first-line title until this script is run against them.

SAFETY RULE (owner-approved): a row is only eligible for backfill when its
CURRENT title still equals `_infer_application_title(row.jd_text)` exactly —
i.e. nothing has touched it since creation. The instant a user renames an
application (Applications tab, `PUT /api/applications/<id>/meta`), its title
diverges from that raw form and this script leaves it alone forever, even on
repeat runs. This is intentionally conservative: a coincidental hand-edit
that happens to reproduce the exact raw first line is the one (accepted)
false negative — safety over completeness.

Manual only — never wired to a route, a migration, or app startup. Defaults
to dry-run (prints before -> after, writes nothing); pass --apply to commit.

Usage:
    python -m scripts.backfill_application_titles                # dry run, default DB
    python -m scripts.backfill_application_titles --apply         # writes changes
    python -m scripts.backfill_application_titles --db path/to.sqlite --apply
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# scripts/backfill_application_titles.py -> repo root is one parent up.
REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Pure core — read-only compute + a separate UPDATE-only apply step. Both
# filesystem-free, so they unit-test against an in-memory session with no I/O.
# ---------------------------------------------------------------------------


def compute_title_backfill(session: Session) -> list[dict[str, Any]]:
    """Read-only: find eligible Application rows + the title the new extractor would give them.

    Eligible = `application.title == _infer_application_title(application.jd_text)`
    (see module docstring "SAFETY RULE"). Returns one entry per eligible row
    whose computed new title actually differs from the current one — a
    would-be no-op (new extractor agrees with the old one) is silently
    skipped. Shape: `[{"id", "company", "before", "after"}, ...]`, ordered by
    application id for stable, readable dry-run output.
    """
    from db.build_context import _infer_application_title, _infer_role_title
    from db.models import Application

    changes: list[dict[str, Any]] = []
    for app_row in session.query(Application).order_by(Application.id).all():
        jd_text = app_row.jd_text or ""
        raw_first_line = _infer_application_title(jd_text)
        if (app_row.title or "") != raw_first_line:
            continue  # hand-edited (or already backfilled) — never touched
        new_title = _infer_role_title(jd_text) or raw_first_line
        if new_title == app_row.title:
            continue  # new extractor agrees with the old one — nothing to change
        changes.append(
            {
                "id": app_row.id,
                "company": app_row.company,
                "before": app_row.title,
                "after": new_title,
            }
        )
    return changes


def apply_title_backfill(session: Session, changes: list[dict[str, Any]]) -> int:
    """UPDATE-only: write the computed `changes` (from `compute_title_backfill`).

    No schema operation — a plain UPDATE per row via the ORM. Caller commits.
    Returns the number of rows written.
    """
    from db.models import Application

    by_id = {c["id"]: c["after"] for c in changes}
    if not by_id:
        return 0
    rows = session.query(Application).filter(Application.id.in_(by_id.keys())).all()
    for row in rows:
        row.title = by_id[row.id]
    return len(rows)


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
    # Windows cp1252 consoles can't encode the em-dash this script prints in
    # "before -> after" lines; force UTF-8 on our streams before anything prints.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--db",
        default=None,
        help="SQLite DB file to read/write (default: the app's db/resume.sqlite).",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write the computed changes. Default is dry-run (prints only, writes nothing).",
    )
    args = ap.parse_args()

    session, engine = None, None
    try:
        session, engine = _open_session(args.db)
        changes = compute_title_backfill(session)
        for c in changes:
            print(f"[{c['id']}] {c['before']!r} -> {c['after']!r}")
        print(f"{len(changes)} application(s) eligible for retitle")
        if not args.apply:
            print("Dry run only — pass --apply to write changes.")
            return 0
        n = apply_title_backfill(session, changes)
        session.commit()
        print(f"Applied: {n} row(s) updated.")
        return 0
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}")
        return 1
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
