"""LLM-free DB + config seeding for the UX suite.

Mirrors the helpers in `tests/test_application_routes.py` (`_seed_candidate`,
`_seed_exp_with_bullets`, `_seed_run`) so the browser tests seed state the
same proven way the route tests do — reused across flows + regression.
All writes go through `db.session.get_session`, which the `ux_app` fixture
has already pointed at the temp DB.
"""

from __future__ import annotations

import hashlib
import json
from types import ModuleType


def write_user_config(ux_app: ModuleType, username: str,
                      name: str | None = None, email: str | None = None) -> None:
    """Write a non-empty config — `_load_config` treats an empty dict as
    'user not found' (404), so a realistic config keeps GET /config a 200,
    matching an onboarded user."""
    config = {"name": name or username.title(),
              "email": email or f"{username}@example.com"}
    (ux_app.CONFIGS_DIR / f"{username}.config").write_text(
        json.dumps(config), encoding="utf-8")


def seed_candidate(username: str = "alice", name: str | None = None) -> int:
    from db.models import Candidate
    from db.session import get_session

    s = get_session()
    try:
        c = Candidate(username=username, name=name or username.title())
        s.add(c)
        s.commit()
        return c.id
    finally:
        s.close()


def seed_user(ux_app: ModuleType, username: str = "alice") -> int:
    """Config file + Candidate row — the minimum to select a user in the UI."""
    write_user_config(ux_app, username)
    return seed_candidate(username)


def seed_exp_with_bullets(candidate_id: int, company: str = "Acme") -> int:
    """One experience with a JD-relevant bullet + a weak one (k8s first)."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        e = Experience(
            candidate_id=candidate_id, company=company,
            start_date="2021-01", display_order=0,
        )
        s.add(e)
        s.flush()
        s.add(ExperienceTitle(
            experience_id=e.id, title="Staff Engineer",
            is_official=1, is_pending_review=0, source="official",
        ))
        s.add(Bullet(
            experience_id=e.id,
            text="Reduced Kubernetes latency 40% across 12 services",
            display_order=0, is_active=1, is_pending_review=0,
            source="manual", has_outcome=1,
        ))
        s.add(Bullet(
            experience_id=e.id, text="Attended weekly syncs",
            display_order=1, is_active=1, is_pending_review=0,
            source="manual", has_outcome=0,
        ))
        s.commit()
        return e.id
    finally:
        s.close()


def seed_application(candidate_id: int, title: str = "Senior PM @ Foo",
                     company: str = "Foo Inc", jd_text: str = "Long JD text.",
                     status: str = "draft") -> int:
    from db.models import Application
    from db.session import get_session

    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id, title=title, company=company,
            jd_text=jd_text, status=status,
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        s.add(a)
        s.commit()
        return a.id
    finally:
        s.close()


def seed_run(application_id: int, iteration: int = 0, run_id: str = "uxrun0000001",
             generated_resume_md: str | None = None,
             generated_cover_letter_md: str | None = None,
             persona_template_id: int | None = None) -> int:
    from db.models import ApplicationRun
    from db.session import get_session

    s = get_session()
    try:
        r = ApplicationRun(
            application_id=application_id, iteration=iteration, run_id=run_id,
            prompt_version="2026-05-12.1", corpus_snapshot_json="{}",
            generated_resume_md=generated_resume_md,
            generated_cover_letter_md=generated_cover_letter_md,
            persona_template_id=persona_template_id,
        )
        s.add(r)
        s.commit()
        return r.id
    finally:
        s.close()


def bundled_persona_id() -> int:
    """Id of a DB-seeded bundled persona (resolvable to a real on-disk
    template, so the Step-6 preview renders)."""
    from db.models import PersonaTemplate
    from db.session import get_session

    s = get_session()
    try:
        p = (s.query(PersonaTemplate)
             .filter(PersonaTemplate.candidate_id.is_(None))
             .order_by(PersonaTemplate.id).first())
        assert p is not None, "no bundled personas seeded by migration"
        return p.id
    finally:
        s.close()


def bundled_persona_id_by_path(path: str) -> int:
    """Id of a specific bundled persona, addressed by its `path` column
    (e.g. ``personas/bundled/modern.docx``). Lets a test render each bundled
    template by name rather than only the first one `bundled_persona_id`
    returns. Asserts the row exists so a renamed/removed template fails loud."""
    from db.models import PersonaTemplate
    from db.session import get_session

    s = get_session()
    try:
        p = (s.query(PersonaTemplate)
             .filter(PersonaTemplate.candidate_id.is_(None),
                     PersonaTemplate.path == path).first())
        assert p is not None, f"no bundled persona seeded for path={path!r}"
        return p.id
    finally:
        s.close()


def write_context_file(ux_app: ModuleType, username: str, filename: str,
                       payload: dict) -> str:
    """Write a context_*.json under OUTPUT_DIR/<user>/; return the abs path."""
    user_dir = ux_app.OUTPUT_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    p = user_dir / filename
    p.write_text(json.dumps(payload), encoding="utf-8")
    return str(p)
