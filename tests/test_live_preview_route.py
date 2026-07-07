"""Tests for the live HTML preview routes (Phase β.4 + β.6).

Two routes share the same render pipeline:
  - GET /api/applications/<id>/preview  → corpus + application overrides
  - GET /api/users/<username>/preview   → corpus only (pre-application)

Both build a JSON Resume v1.0 doc directly from Candidate + Experience
+ Bullet + SummaryItem rows via `corpus_to_json_resume`, render it
through the chosen persona's HTML+CSS template, inline CSS into a
<style> block, and return text/html for iframe consumption.

The corpus-direct shape replaces the earlier sidecar-only behavior so
the preview works BEFORE any /api/generate has run — fixing the
"can't preview a template without paying for a generate" gap surfaced
in the hands-on review.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def preview_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh sqlite DB + temp tree (Sprint 8.3e).

    The preview routes moved to blueprints/templates.py and read
    current_app.config[...], so create_app(Config(base_dir=tmp_path)) replaces
    the old reload + monkeypatch-the-globals fixture; the DB-path monkeypatch
    stays. Returns a namespace exposing the factory app + Config-derived paths so
    the existing test bodies keep referencing `preview_app.app` / `.OUTPUT_DIR` /
    `.CONFIGS_DIR` unchanged.
    """
    import types

    db_file = tmp_path / "preview.sqlite"

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output
    cfg.bundled_personas_dir.mkdir(parents=True, exist_ok=True)

    from db.session import init_db

    init_db(db_file)

    # Materialize the bundled Classic HTML + CSS in the temp dir so the
    # fallback path works. Mirror the real classic.html + classic.css
    # so the inlining test catches the real shape.
    repo_root = Path(__file__).resolve().parents[1]
    src_html = repo_root / "personas" / "bundled" / "classic.html"
    src_css = repo_root / "personas" / "bundled" / "classic.css"
    (cfg.bundled_personas_dir / "classic.html").write_text(
        src_html.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (cfg.bundled_personas_dir / "classic.css").write_text(
        src_css.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Materialize the shared cover-letter shell so the cover-letter preview
    # route (PERSONAS_DIR / cover_letter.html) resolves in-temp.
    (cfg.personas_dir / "cover_letter.html").write_text(
        (repo_root / "personas" / "cover_letter.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # Also drop a stub .docx so the bundled-template DB rows resolve.
    from docx import Document

    for filename in ("classic.docx", "modern.docx"):
        doc = Document()
        doc.add_paragraph(f"stub for {filename}")
        doc.save(str(cfg.bundled_personas_dir / filename))

    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    return types.SimpleNamespace(
        app=app,
        BASE_DIR=cfg.base_dir,
        CONFIGS_DIR=cfg.configs_dir,
        OUTPUT_DIR=cfg.output_dir,
        PERSONAS_DIR=cfg.personas_dir,
        BUNDLED_PERSONAS_DIR=cfg.bundled_personas_dir,
    )


def _seed_candidate_app(
    app_module,
    username="casey",
    name="Casey Rivera",
    profile_text="Senior PM with a decade of leadership.",
    title="Senior PM",
):
    """Insert a candidate (with profile_text) + application row.
    Returns (candidate_id, application_id)."""
    from db.models import Application, Candidate
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(
            username=username,
            name=name,
            profile_text=profile_text,
            email="casey@example.com",
        )
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title=title,
            jd_text="placeholder JD",
            jd_fingerprint="x" * 16,
        )
        session.add(a)
        session.commit()
        return c.id, a.id
    finally:
        session.close()


def _seed_experience_with_bullets(
    candidate_id: int,
    *,
    company="Polaris",
    position="Lead PM",
    bullet_texts=("Shipped the unified corpus.",),
):
    """Seed one experience + bullets + an official title for the candidate."""
    from db.models import Bullet, Experience, ExperienceTitle
    from db.session import get_session

    session = get_session()
    try:
        exp = Experience(
            candidate_id=candidate_id,
            company=company,
            start_date="2022",
            end_date="present",
        )
        session.add(exp)
        session.flush()
        t = ExperienceTitle(
            experience_id=exp.id,
            title=position,
            is_official=1,
            source="official",
        )
        session.add(t)
        for i, text in enumerate(bullet_texts):
            b = Bullet(
                experience_id=exp.id,
                text=text,
                display_order=i,
                is_active=1,
                source="resume_import",
            )
            session.add(b)
        session.commit()
        return exp.id
    finally:
        session.close()


# -------------------------------------------------------------------
# Per-application preview — happy path
# -------------------------------------------------------------------


def _write_context_with_recommendations(
    out_dir: Path,
    application_id: int,
    experience_id: int,
    bullet_ids: list[int],
    *,
    extra_overrides: dict | None = None,
    pinned_summary_id: int | None = None,
    filename: str = "context_test.json",
) -> Path:
    """Persist a context_*.json under out_dir with the curation fields
    the preview route now requires (per the 2026-05-26 architectural
    decision: preview reflects curation, never falls back to all
    bullets).

    Returns the resolved path so callers can pass it as context_path=.
    """
    import json as _json
    from typing import Any

    out_dir.mkdir(parents=True, exist_ok=True)
    composition_overrides: dict[str, Any] = {
        "pinned": [],
        "excluded": [],
        "added": [],
    }
    if pinned_summary_id is not None:
        composition_overrides["pinned_summary_id"] = pinned_summary_id
    if extra_overrides:
        composition_overrides.update(extra_overrides)
    ctx_path = out_dir / filename
    ctx_path.write_text(
        _json.dumps(
            {
                "application_id": application_id,
                "composition_overrides": composition_overrides,
                "llm_recommendations": {
                    str(experience_id): {
                        "bullet_ids": [int(b) for b in bullet_ids],
                        "rationale": "test fixture",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return ctx_path


class TestApplicationPreviewHappyPath:
    def test_returns_html_when_recommendations_present(self, preview_app):
        """Per the 2026-05-26 architectural decision: the preview only
        renders the curated set when `llm_recommendations` is populated
        in the context_path's JSON. This test sets up the recommendations
        explicitly and confirms the full render happens."""
        from db.models import Bullet
        from db.session import get_session

        cid, aid = _seed_candidate_app(preview_app, username="casey")
        exp_id = _seed_experience_with_bullets(cid)
        # Resolve the bullet ids we just seeded so we can put them in
        # llm_recommendations.
        session = get_session()
        try:
            bullet_ids = [b.id for b in session.query(Bullet).filter_by(experience_id=exp_id).all()]
        finally:
            session.close()
        ctx_file = _write_context_with_recommendations(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            exp_id,
            bullet_ids,
        )

        client = preview_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        )
        assert r.status_code == 200
        assert r.content_type.startswith("text/html")
        body = r.get_data(as_text=True)
        assert "Casey Rivera" in body
        assert "Senior PM with a decade of leadership." in body
        assert "Polaris" in body
        assert "Shipped the unified corpus." in body

    def test_returns_placeholder_when_no_recommendations(self, preview_app):
        """The preview returns a placeholder HTML — NOT a full render
        of all active bullets — when llm_recommendations is missing.
        Pre-2026-05-26 behavior was to fall back to all active bullets;
        the user explicitly rejected that as "no changes that aren't
        seen or approved" — un-curated bullets surfaced silently would
        bloat the preview and mislead the user about the download
        shape. The placeholder explains the empty-state honestly."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

        client = preview_app.app.test_client()
        # No context_path at all.
        r = client.get(f"/api/applications/{aid}/preview")
        assert r.status_code == 200
        assert r.content_type.startswith("text/html")
        body = r.get_data(as_text=True)
        assert "Preview is waiting on curation" in body
        # The actual corpus content must NOT be rendered.
        assert "Shipped the unified corpus." not in body

    def test_css_is_inlined(self, preview_app):
        """The response must be fully self-contained — no remote
        <link rel="stylesheet"> tags. CSS lives inside a <style> block
        so the iframe sandbox works without cross-origin gymnastics."""
        _seed_candidate_app(preview_app, username="casey")

        client = preview_app.app.test_client()
        body = client.get(
            "/api/users/casey/preview",
        ).get_data(as_text=True)
        assert '<link rel="stylesheet"' not in body
        assert "<style>" in body
        # A signature rule from classic.css proves the inline succeeded
        assert "Helvetica" in body or "page-break" in body

    def test_pinned_summary_wins_over_profile_text(self, preview_app):
        """A pinned SummaryItem must override Candidate.profile_text in
        the rendered preview — proves corpus_to_json_resume honors
        composition_overrides.pinned_summary_id passed via context_path.

        Context file also carries llm_recommendations so the post-
        2026-05-26 preview-requires-curation check passes; the
        recommendations cover the seeded experience's only bullet."""
        from db.models import Bullet, SummaryItem
        from db.session import get_session

        cid, aid = _seed_candidate_app(preview_app, username="casey")
        exp_id = _seed_experience_with_bullets(cid)
        session = get_session()
        try:
            si = SummaryItem(
                candidate_id=cid,
                text="Pinned variant text.",
                display_order=0,
                is_active=1,
            )
            session.add(si)
            session.flush()
            si_id = si.id
            session.commit()
            bullet_ids = [b.id for b in session.query(Bullet).filter_by(experience_id=exp_id).all()]
        finally:
            session.close()

        ctx_file = _write_context_with_recommendations(
            (preview_app.OUTPUT_DIR / "casey").resolve(),
            aid,
            exp_id,
            bullet_ids,
            pinned_summary_id=si_id,
            filename="context_pin.json",
        )

        client = preview_app.app.test_client()
        body = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        ).get_data(as_text=True)
        assert "Pinned variant text." in body
        assert "Senior PM with a decade of leadership." not in body


# -------------------------------------------------------------------
# Per-application preview — WYSIWYG Option 1 (v1.0.5)
# -------------------------------------------------------------------


_WYSIWYG_MARKDOWN = """# Casey Rivera
Senior Product Manager
casey@example.com

## Summary

LLM-rewritten positioning for this exact job.

## Experience

### Orbital Dynamics, Principal PM\t2020 – Present

- Drove a 3x revenue lift by repositioning the platform.

## Skills

- Roadmapping, Stakeholder alignment
"""


def _write_context_with_cached_json_resume(
    out_dir: Path,
    application_id: int,
    markdown: str,
    *,
    include_recommendations: bool = False,
    experience_id: int | None = None,
    bullet_ids: list[int] | None = None,
    filename: str = "context_gen.json",
) -> Path:
    """Persist a post-generate context carrying last_generated_json_resume —
    the deterministic md_to_json_resume() of `markdown`, exactly as
    save_iteration_context() would write it.

    By default no llm_recommendations are included, so a render proves the
    WYSIWYG path bypasses the pre-generate curation gate.
    """
    import json as _json

    from json_resume import md_to_json_resume

    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "application_id": application_id,
        "last_generated_resume": markdown,
        "last_generated_json_resume": md_to_json_resume(markdown),
    }
    if include_recommendations and experience_id is not None and bullet_ids is not None:
        payload["llm_recommendations"] = {
            str(experience_id): {
                "bullet_ids": [int(b) for b in bullet_ids],
                "rationale": "test fixture",
            },
        }
    ctx_path = out_dir / filename
    ctx_path.write_text(_json.dumps(payload), encoding="utf-8")
    return ctx_path


class TestApplicationPreviewWysiwyg:
    def test_serves_cached_json_resume_over_corpus(self, preview_app):
        """Once /api/generate has run, the context carries the cached
        md_to_json_resume() of the LLM markdown. The preview must serve THAT
        (preview == download), NOT a fresh corpus render — even though the
        candidate's corpus has different, un-rewritten content."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        # Corpus content that must NOT leak into the WYSIWYG render.
        _seed_experience_with_bullets(cid)

        ctx_file = _write_context_with_cached_json_resume(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            _WYSIWYG_MARKDOWN,
        )

        client = preview_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        )
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        # The cached generate output renders.
        assert "Orbital Dynamics" in body
        assert "Drove a 3x revenue lift by repositioning the platform." in body
        # The corpus-direct content does NOT — proves we served the cache.
        assert "Polaris" not in body
        assert "Shipped the unified corpus." not in body

    def test_cached_path_bypasses_recommendations_gate(self, preview_app):
        """The cached JSON Resume serves even with NO llm_recommendations in
        the context — a generate having run means curation already happened,
        so the pre-generate placeholder gate must not fire on this path."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

        # No recommendations on this context (include_recommendations=False).
        ctx_file = _write_context_with_cached_json_resume(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            _WYSIWYG_MARKDOWN,
            filename="context_no_recs.json",
        )

        client = preview_app.app.test_client()
        body = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        ).get_data(as_text=True)
        assert "Preview is waiting on curation" not in body
        assert "Orbital Dynamics" in body

    def test_empty_cached_skeleton_falls_back_to_gate(self, preview_app):
        """A degenerate cached skeleton (blank generate) has no renderable
        content, so the route ignores it and falls back to the pre-generate
        path — which, with no recommendations, returns the placeholder rather
        than rendering an empty document."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

        # Empty markdown → md_to_json_resume() emits an empty skeleton.
        ctx_file = _write_context_with_cached_json_resume(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            "",
            filename="context_empty.json",
        )

        client = preview_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/preview?context_path={ctx_file}",
        )
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "Preview is waiting on curation" in body


_APPROVED_DOC = {
    "$schema": "x",
    "basics": {"name": "Casey Rivera", "summary": "Frozen positioning line for this JD."},
    "work": [
        {
            "name": "Frozen Corp",
            "position": "Staff Engineer",
            "startDate": "2021-01",
            "endDate": "present",
            "highlights": ["Delivered the frozen approved bullet."],
        }
    ],
    "skills": [{"name": "FrozenSkill"}],
    "education": [],
    "certificates": [],
    "projects": [],
    "meta": {"sartor": {"frozen": True}},
}


def _write_context_with_approved_composition(
    out_dir: Path,
    application_id: int,
    doc: dict,
    *,
    edited_markdown: str | None = None,
    filename: str = "context_frozen.json",
) -> Path:
    """Persist a context carrying a frozen approved_composition (Phase 4).

    When ``edited_markdown`` is given, also stamps ``edited_resume_text`` +
    ``last_generated_json_resume`` (as /api/save-edits would) so the D6(a) hand-edit
    precedence over the frozen composition can be exercised.
    """
    import json as _json

    from json_resume import md_to_json_resume

    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict = {"application_id": application_id, "approved_composition": doc}
    if edited_markdown is not None:
        payload["edited_resume_text"] = edited_markdown
        payload["last_generated_resume"] = edited_markdown
        payload["last_generated_json_resume"] = md_to_json_resume(edited_markdown)
    ctx_path = out_dir / filename
    ctx_path.write_text(_json.dumps(payload), encoding="utf-8")
    return ctx_path


class TestApplicationPreviewApprovedComposition:
    def test_serves_approved_composition_over_corpus(self, preview_app):
        """Phase 4 — once Compose has frozen an approved_composition, the preview
        serves THAT (preview == deterministic assemble == download), NOT a fresh
        corpus render (even though the corpus has different content)."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)  # corpus content that must NOT leak
        ctx_file = _write_context_with_approved_composition(
            preview_app.OUTPUT_DIR / "casey", aid, _APPROVED_DOC
        )
        client = preview_app.app.test_client()
        body = client.get(f"/api/applications/{aid}/preview?context_path={ctx_file}").get_data(
            as_text=True
        )
        assert "Frozen positioning line for this JD." in body
        assert "Delivered the frozen approved bullet." in body
        # Corpus-direct content does NOT leak — proves the frozen composition served.
        assert "Polaris" not in body
        assert "Shipped the unified corpus." not in body

    def test_hand_edit_wins_over_approved_composition(self, preview_app):
        """D6(a) — a user hand-edit (edited_resume_text) takes precedence over the
        frozen composition, so the preview reflects the edit (WYSIWYG)."""
        cid, aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)
        edited = (
            "# Casey Rivera\n\n## Experience\n\n"
            "### Frozen Corp, Staff Engineer\t2021-01 – present\n"
            "- Hand-edited bullet wins.\n"
        )
        ctx_file = _write_context_with_approved_composition(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            _APPROVED_DOC,
            edited_markdown=edited,
            filename="context_edited.json",
        )
        client = preview_app.app.test_client()
        body = client.get(f"/api/applications/{aid}/preview?context_path={ctx_file}").get_data(
            as_text=True
        )
        assert "Hand-edited bullet wins." in body
        assert "Delivered the frozen approved bullet." not in body


# -------------------------------------------------------------------
# Cover-letter preview — styled business-letter render (v1.0.5)
# -------------------------------------------------------------------


def _write_context_with_cover_letter(
    out_dir: Path,
    application_id: int,
    cover_letter_md: str,
    *,
    filename: str = "context_cl.json",
) -> Path:
    """Persist a context carrying last_generated_cover_letter — as
    run_generate_cover_letter writes it in place after a CL generation."""
    import json as _json

    out_dir.mkdir(parents=True, exist_ok=True)
    ctx_path = out_dir / filename
    ctx_path.write_text(
        _json.dumps(
            {
                "application_id": application_id,
                "last_generated_cover_letter": cover_letter_md,
            }
        ),
        encoding="utf-8",
    )
    return ctx_path


class TestCoverLetterPreview:
    _CL = (
        "June 4, 2026\n"
        "Hiring Manager, Orbital Dynamics\n\n"
        "Dear Hiring Manager,\n\n"
        "I rebuilt three distributed systems after scaling to 4M users.\n\n"
        "Sincerely,\nCasey Rivera"
    )

    def test_serves_styled_cover_letter(self, preview_app):
        """A context carrying last_generated_cover_letter renders through the
        business-letter shell as self-contained HTML."""
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        ctx = _write_context_with_cover_letter(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            self._CL,
        )
        client = preview_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/cover-letter-preview?context_path={ctx}",
        )
        assert r.status_code == 200
        assert r.content_type.startswith("text/html")
        body = r.get_data(as_text=True)
        assert "Hiring Manager, Orbital Dynamics" in body
        assert "distributed systems" in body
        # The shared business-letter shell wraps the body.
        assert 'class="cover-letter"' in body
        # Self-contained — paged.js injected, no remote stylesheet link.
        assert "paged.polyfill.js" in body

    def test_placeholder_when_no_cover_letter_yet(self, preview_app):
        """No context (pre-generate) → honest empty-state placeholder."""
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/cover-letter-preview")
        assert r.status_code == 200
        assert "No cover letter yet" in r.get_data(as_text=True)

    def test_placeholder_when_context_has_empty_cover_letter(self, preview_app):
        """A context that exists but carries no cover letter → placeholder,
        not a blank styled page."""
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        ctx = _write_context_with_cover_letter(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            "",
            filename="context_cl_empty.json",
        )
        client = preview_app.app.test_client()
        body = client.get(
            f"/api/applications/{aid}/cover-letter-preview?context_path={ctx}",
        ).get_data(as_text=True)
        assert "No cover letter yet" in body

    def test_returns_404_for_unknown_application(self, preview_app):
        client = preview_app.app.test_client()
        r = client.get("/api/applications/9999/cover-letter-preview")
        assert r.status_code == 404

    def test_rejects_out_of_tree_context_path(self, preview_app, tmp_path):
        """A context file OUTSIDE OUTPUT_DIR must not be read — the _within
        guard refuses it, so its cover letter never renders (placeholder
        shown). Proves path-traversal containment on the new route."""
        import json as _json

        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        outside = tmp_path / "evil_context.json"
        outside.write_text(
            _json.dumps(
                {
                    "application_id": aid,
                    "last_generated_cover_letter": "SENTINEL_LEAK_TEXT",
                }
            ),
            encoding="utf-8",
        )
        client = preview_app.app.test_client()
        body = client.get(
            f"/api/applications/{aid}/cover-letter-preview?context_path={outside}",
        ).get_data(as_text=True)
        assert "SENTINEL_LEAK_TEXT" not in body
        assert "No cover letter yet" in body


# -------------------------------------------------------------------
# Per-application preview — failure paths
# -------------------------------------------------------------------


class TestApplicationPreviewFailureModes:
    def test_returns_404_for_unknown_application(self, preview_app):
        client = preview_app.app.test_client()
        r = client.get("/api/applications/9999/preview")
        assert r.status_code == 404

    def test_returns_400_for_malformed_template_id(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id=not-a-number")
        assert r.status_code == 400


# -------------------------------------------------------------------
# Per-application preview — explicit template_id
# -------------------------------------------------------------------


class TestPreviewWithExplicitTemplate:
    def test_uses_specified_template(self, preview_app):
        """When template_id is passed, the route resolves through that
        persona's HTML companion (or falls back to bundled Classic if
        no companion exists). Per the 2026-05-26 architectural decision
        the preview also requires llm_recommendations in the
        context_path — without those it returns a placeholder."""
        from db.models import Bullet, PersonaTemplate
        from db.session import get_session

        cid, aid = _seed_candidate_app(preview_app, username="casey")
        exp_id = _seed_experience_with_bullets(cid)

        # Find the bundled Classic row from the seed migration; resolve
        # the seeded bullet ids so llm_recommendations covers them.
        session = get_session()
        try:
            classic = (
                session.query(PersonaTemplate)
                .filter_by(
                    source="bundled",
                    name="Classic Single-Column",
                )
                .first()
            )
            assert classic is not None
            classic_id = classic.id
            bullet_ids = [b.id for b in session.query(Bullet).filter_by(experience_id=exp_id).all()]
        finally:
            session.close()

        ctx_file = _write_context_with_recommendations(
            preview_app.OUTPUT_DIR / "casey",
            aid,
            exp_id,
            bullet_ids,
            filename="context_tpl.json",
        )

        client = preview_app.app.test_client()
        r = client.get(
            f"/api/applications/{aid}/preview?template_id={classic_id}&context_path={ctx_file}",
        )
        assert r.status_code == 200
        assert "Casey" in r.get_data(as_text=True)

    def test_returns_404_for_unknown_template_id(self, preview_app):
        _cid, aid = _seed_candidate_app(preview_app, username="casey")
        client = preview_app.app.test_client()
        r = client.get(f"/api/applications/{aid}/preview?template_id=99999")
        assert r.status_code == 404


# -------------------------------------------------------------------
# Pre-application preview (/api/users/<u>/preview)
# -------------------------------------------------------------------


class TestUserPreview:
    def test_renders_corpus_without_application(self, preview_app):
        """A candidate with corpus rows but no application_id still
        gets a renderable preview — answers the user's "let me see what
        my résumé looks like through Classic" before any application."""
        cid, _aid = _seed_candidate_app(preview_app, username="casey")
        _seed_experience_with_bullets(cid)

        client = preview_app.app.test_client()
        r = client.get("/api/users/casey/preview")
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert "Casey Rivera" in body
        assert "Polaris" in body

    def test_rejects_unknown_user(self, preview_app):
        """A username with no `.config` is rejected at `_safe_username`
        (returns None → 400). Practical: the surface is closed before
        the candidate row is consulted, so we never leak which users
        exist in the corpus tables vs which don't."""
        client = preview_app.app.test_client()
        r = client.get("/api/users/ghost/preview")
        assert r.status_code == 400

    def test_returns_409_when_config_exists_but_no_candidate(self, preview_app):
        """When a config exists but the candidate row is missing, the
        UI needs the `needs_onboarding` flag so it routes the user
        through onboarding rather than showing a blank preview."""
        # Materialize a config file (no candidate row)
        (preview_app.CONFIGS_DIR / "newbie.config").write_text(
            "{}",
            encoding="utf-8",
        )
        client = preview_app.app.test_client()
        r = client.get("/api/users/newbie/preview")
        assert r.status_code == 409
        assert r.get_json().get("needs_onboarding") is True

    def test_returns_400_for_invalid_username(self, preview_app):
        """Path-traversal-style usernames are rejected by
        _safe_username before any DB hit."""
        client = preview_app.app.test_client()
        r = client.get("/api/users/..%2Fadmin/preview")
        # Werkzeug routing strips the slash; the validator catches it.
        assert r.status_code in (400, 404)
