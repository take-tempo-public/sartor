"""Tests for cover-letter detachment (Phase β.5).

Two test surfaces:

  - TestGenerateOptOutDefault: /api/generate without the
    generate_cover_letter flag (the new default behavior) skips
    cover-letter production. No file written, cover_letter_path = "".

  - TestGenerateCoverLetterRoute: the new POST /api/generate-cover-letter
    route. Loads finalized résumé from the context, runs the focused
    LLM call, writes the .docx, updates the context's
    last_generated_cover_letter.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def app_with_stubs(tmp_path, monkeypatch):
    """Reload app.py against a tmp_path-isolated DB + filesystem; stub
    LLM calls + document writers. Seeds an iteration-0 context for
    user 'alice' that mirrors what /api/analyze + /api/generate would
    produce (résumé available, cover letter not yet)."""
    db_file = tmp_path / "cl.sqlite"

    import db.session as db_session_mod
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import importlib

    import app as _app
    importlib.reload(_app)

    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    output_dir.mkdir()
    configs_dir.mkdir()
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    monkeypatch.setattr(_app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(_app, "CONFIGS_DIR", configs_dir)

    # Stub generate() — returns empty cover_letter_content when
    # with_cover_letter is False (mirrors production behavior).
    def _stub_generate(client, context_set, analysis, refinement_notes="",
                       username="", run_id="", with_cover_letter=True):
        return {
            "resume_content": "# Stub résumé\n\n## Summary\nText.",
            "cover_letter_content":
                "Stub cover letter body." if with_cover_letter else "",
            "changes_made": ["x"],
            "proofread_notes": [],
        }

    def _stub_resume_writer(content, fmt, user, base_dir, template_path=None):
        out = Path(base_dir) / user / f"resume_stub{fmt}"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return str(out)

    written: list[str] = []

    def _stub_letter_writer(content, user, base_dir):
        out = Path(base_dir) / user / "cover_stub.docx"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        written.append(str(out))
        return str(out)

    # The dedicated cover-letter LLM call (β.5).
    def _stub_cl_against(client, context_set, analysis, resume_content,
                         refinement_notes="", username="", run_id=""):
        return {
            "cover_letter_content": "Focused cover letter for " + resume_content[:20],
            "proofread_notes": [],
        }

    monkeypatch.setattr(_app, "generate", _stub_generate)
    monkeypatch.setattr(_app, "generate_resume", _stub_resume_writer)
    monkeypatch.setattr(_app, "generate_cover_letter", _stub_letter_writer)

    # generate_cover_letter_against_resume is imported lazily inside
    # the route, so patch it at the module from which the route imports.
    import analyzer as _analyzer
    monkeypatch.setattr(_analyzer, "generate_cover_letter_against_resume",
                        _stub_cl_against)

    # Stub the Anthropic client + iteration context machinery.
    monkeypatch.setattr(_app, "_get_client", lambda: object())
    monkeypatch.setattr(_app, "save_iteration_context",
                        lambda *a, **k: str(output_dir / "alice" / "context_iter1.json"))

    # Seed an iteration-0 context with a finalized résumé already written
    # so the cover-letter route has something to work against.
    initial_ctx = {
        "iteration": 0,
        "resume": {"format": "md", "text": "# Original résumé", "filename": ""},
        "llm_analysis": {
            "essential_skills": ["python"],
            "overall_strategy": "Lean into platform work.",
            "professional_vocabulary": ["scalable"],
        },
        "last_generated_resume": "# Generated résumé v1\n- Bullet.",
        "supplemental_resumes": [],
    }
    ctx_path = output_dir / "alice" / "context_iter0.json"
    ctx_path.write_text(json.dumps(initial_ctx), encoding="utf-8")

    # Make the iteration-stub return a usable new path. Signature mirrors
    # hardening.save_iteration_context: parent_context, parent_path, ...
    def _stub_save_iter(parent_context, parent_path, *args, **kwargs):
        n = (parent_context.get("iteration", 0) or 0) + 1
        new = output_dir / "alice" / f"context_iter{n}.json"
        new.write_text(json.dumps(parent_context), encoding="utf-8")
        return str(new)

    monkeypatch.setattr(_app, "save_iteration_context", _stub_save_iter)

    _app._cover_letter_writes = written
    return _app, ctx_path


# ---------------------------------------------------------------------
# /api/generate with the new opt-out default
# ---------------------------------------------------------------------


class TestGenerateOptOutDefault:
    def test_default_omits_cover_letter_file(self, app_with_stubs):
        _app, ctx_path = app_with_stubs
        client = _app.app.test_client()

        # No generate_cover_letter flag in the body → default is False
        r = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(ctx_path),
            "output_format": ".md",
        })
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        # cover_letter_path is empty when no cover letter was produced
        assert body["cover_letter_path"] == ""
        # The stub recorded zero cover-letter writes
        assert _app._cover_letter_writes == []
        # Preview echo is empty (stub returned "" for cover_letter_content)
        assert body["cover_letter_preview"] == ""

    def test_explicit_true_still_produces_cover_letter(self, app_with_stubs):
        _app, ctx_path = app_with_stubs
        client = _app.app.test_client()

        r = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(ctx_path),
            "output_format": ".md",
            "generate_cover_letter": True,
        })
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["cover_letter_path"]  # non-empty
        assert "Stub cover letter body." in body["cover_letter_preview"]
        assert len(_app._cover_letter_writes) == 1


# ---------------------------------------------------------------------
# /api/generate-cover-letter (the new dedicated route)
# ---------------------------------------------------------------------


class TestGenerateCoverLetterRoute:
    def test_happy_path_writes_letter_and_updates_context(self, app_with_stubs):
        _app, ctx_path = app_with_stubs
        client = _app.app.test_client()

        r = client.post("/api/generate-cover-letter", json={
            "username": "alice",
            "context_path": str(ctx_path),
        })
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        assert body["cover_letter_path"].endswith(".docx")
        assert body["cover_letter_preview"].startswith("Focused cover letter for ")
        # The cover letter writer fired exactly once
        assert len(_app._cover_letter_writes) == 1
        # The context was updated with the new cover-letter content
        updated = json.loads(ctx_path.read_text(encoding="utf-8"))
        assert updated["last_generated_cover_letter"].startswith("Focused cover letter for ")

    def test_returns_409_when_no_resume_in_context(self, app_with_stubs):
        _app, ctx_path = app_with_stubs
        # Strip the résumé content from the seeded context
        ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        ctx["last_generated_resume"] = ""
        ctx["resume"]["text"] = ""
        ctx_path.write_text(json.dumps(ctx), encoding="utf-8")

        client = _app.app.test_client()
        r = client.post("/api/generate-cover-letter", json={
            "username": "alice",
            "context_path": str(ctx_path),
        })
        assert r.status_code == 409
        body = r.get_json()
        assert body.get("needs_resume") is True

    def test_returns_400_for_missing_context_path(self, app_with_stubs):
        _app, _ctx_path = app_with_stubs
        client = _app.app.test_client()
        r = client.post("/api/generate-cover-letter", json={"username": "alice"})
        assert r.status_code == 400

    def test_path_traversal_blocked(self, app_with_stubs):
        _app, _ctx_path = app_with_stubs
        client = _app.app.test_client()
        r = client.post("/api/generate-cover-letter", json={
            "username": "alice",
            "context_path": "/etc/passwd",
        })
        assert r.status_code in (403, 404)
