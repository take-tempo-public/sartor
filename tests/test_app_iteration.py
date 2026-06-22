"""Tests for the iteration routes added in Phase 1.

Covers:
  - /api/save-edits: security guards, input validation, persistence
  - /api/generate: writes a NEW iteration context file (not in-place mutation),
                   sets parent_context_path, increments iteration, returns
                   the new path so the frontend can target subsequent calls.
"""

import json
from pathlib import Path

import pytest

import blueprints.generation as bgen


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Factory-built Flask test client with config paths under tmp_path and the
    LLM/document-generation calls stubbed on the generation blueprint.

    The generate/save-edits routes live on `blueprints/generation.py` (Sprint
    8.3c), so paths come from `Config(base_dir=tmp_path)` (no app-global
    monkeypatch) and the generate/document-writer/_get_client stubs target the
    blueprint module. The DB-path monkeypatch (db.session.DEFAULT_DB_PATH) keeps
    `_resolve_default_persona_template_path` hermetic — a distinct, legitimate
    seam. Seeds an iteration-0 context for /alice/ that mirrors what /api/analyze
    would have written. Tests exercise routes without any real LLM call.
    """
    import db.session as db_session
    monkeypatch.setattr(db_session, "DEFAULT_DB_PATH", tmp_path / "test.sqlite")
    db_session._engine = None
    db_session._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True

    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    resumes_dir = tmp_path / "resumes"
    # ensure_dirs() (in the factory) already created configs/resumes/output.
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()
    (resumes_dir / "alice").mkdir()

    # Stub the generate() LLM call — return deterministic content.
    def _stub_generate(client, context_set, analysis, refinement_notes="",
                      username="", run_id="", with_cover_letter=True):
        # β.5 — accept the new kwarg. When False, mimic the production
        # behavior of an empty cover_letter_content so the route's
        # "skip cover-letter write" branch is exercised.
        return {
            "resume_content": f"# Generated resume (iter input={context_set.get('iteration', 0)})",
            "cover_letter_content":
                "Generated cover letter body." if with_cover_letter else "",
            "changes_made": ["a"],
            "proofread_notes": [],
        }

    # Stub document writers — return a fake on-disk path. The Phase 1 test
    # surface is the route shape and context lineage, not docx rendering.
    def _stub_resume_writer(content, fmt, user, base_dir, template_path=None):
        out = Path(base_dir) / user / f"resume_stub{fmt}"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return str(out)

    def _stub_letter_writer(content, user, base_dir):
        out = Path(base_dir) / user / "cover_stub.docx"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return str(out)

    monkeypatch.setattr(bgen, "generate", _stub_generate)
    monkeypatch.setattr(bgen, "generate_resume", _stub_resume_writer)
    monkeypatch.setattr(bgen, "generate_cover_letter", _stub_letter_writer)
    monkeypatch.setattr(bgen, "_get_client", lambda: object())

    client = app.test_client()

    context_path = output_dir / "alice" / "context_20260511_120000.json"
    initial = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice", "skills": []},
        "resume": {"text": "original resume", "filename": "alice.docx",
                   "format": ".docx", "sections": [], "path": ""},
        "supplemental_resumes": [],
        "job_description": "JD body.",
        "deterministic_analysis": {
            "jd_keywords": {}, "resume_keywords": {},
            "keyword_overlap": {}, "ats_warnings": [],
        },
        "llm_analysis": {
            "essential_skills": [], "preferred_skills": [],
            "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
            "keyword_placement": [], "overall_strategy": "",
            "ideal_resume_profile": "", "industry_keywords": [],
            "hidden_qualities": [], "professional_vocabulary": [],
            "suggestions": [], "ats_improvements": [],
        },
        "iteration": 0,
        "run_id": "rid_iteration_test",
    }
    context_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    return client, context_path, output_dir


# ---------- /api/save-edits ------------------------------------------------

class TestSaveEditsRoute:
    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/save-edits", json={"edited_resume": "x"})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, _ = app_client
        outside = tmp_path / "elsewhere.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/save-edits", json={
            "context_path": str(outside),
            "edited_resume": "x",
        })
        assert resp.status_code == 403

    def test_nonexistent_context_returns_404(self, app_client, tmp_path):
        client, _, output_dir = app_client
        ghost = output_dir / "alice" / "ghost.json"
        resp = client.post("/api/save-edits", json={
            "context_path": str(ghost),
            "edited_resume": "x",
        })
        assert resp.status_code == 404

    def test_both_edits_empty_returns_400(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": "   ",
            "edited_cover_letter": "",
        })
        assert resp.status_code == 400

    def test_non_string_edits_return_400(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": ["not", "a", "string"],
        })
        assert resp.status_code == 400

    def test_persists_resume_edit_only(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": "USER EDITED RESUME",
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["saved_resume"] is True
        assert body["saved_cover_letter"] is False

        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["edited_resume_text"] == "USER EDITED RESUME"
        assert "edited_cover_letter_text" not in saved
        # save-edits must NOT advance the iteration counter
        assert saved["iteration"] == 0
        # An iteration_note must be appended for audit
        assert any(n["action"] == "save_edits" for n in saved.get("iteration_notes", []))

    def test_persists_both_edits(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": "RESUME EDIT",
            "edited_cover_letter": "LETTER EDIT",
        })
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["edited_resume_text"] == "RESUME EDIT"
        assert saved["edited_cover_letter_text"] == "LETTER EDIT"

    def test_returns_context_path_for_frontend(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": "x",
        })
        body = resp.get_json()
        assert body["context_path"] == str(context_path)


# ---------- /api/generate iteration semantics ------------------------------

class TestGenerateRouteIteration:
    def test_first_generate_writes_new_iteration_file(self, app_client):
        """Iteration-0 input must produce an iteration-1 child file at a NEW
        path; the parent file stays untouched (no in-place mutation)."""
        client, context_path, output_dir = app_client
        parent_size_before = context_path.stat().st_size

        resp = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(context_path),
        })
        assert resp.status_code == 200
        body = resp.get_json()

        assert body["iteration"] == 1
        assert body["parent_context_path"] == str(context_path)
        new_path = Path(body["context_path"])
        assert new_path != context_path
        assert new_path.exists()
        # Parent file is untouched
        assert context_path.stat().st_size == parent_size_before
        # Filename format: context_<ts>_iter1.json
        assert "_iter1.json" in new_path.name

    def test_new_context_records_lineage(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(context_path),
        })
        body = resp.get_json()
        new_ctx = json.loads(Path(body["context_path"]).read_text(encoding="utf-8"))

        assert new_ctx["iteration"] == 1
        assert new_ctx["parent_context_path"] == str(context_path)
        assert "last_generated_resume" in new_ctx
        assert "last_generated_cover_letter" in new_ctx
        # Run id propagates so telemetry stays correlated across iterations
        assert new_ctx["run_id"] == "rid_iteration_test"

    def test_second_generate_increments_iteration(self, app_client):
        """Calling generate against an iteration-1 context produces iter-2."""
        client, context_path, _ = app_client
        first = client.post("/api/generate", json={
            "username": "alice", "context_path": str(context_path),
        }).get_json()

        second = client.post("/api/generate", json={
            "username": "alice",
            "context_path": first["context_path"],
        })
        assert second.status_code == 200
        body = second.get_json()
        assert body["iteration"] == 2
        assert body["parent_context_path"] == first["context_path"]
        # The lineage chain: child2 → child1 → parent (analyze)
        child2 = json.loads(Path(body["context_path"]).read_text(encoding="utf-8"))
        assert child2["parent_context_path"] == first["context_path"]
        child1 = json.loads(Path(first["context_path"]).read_text(encoding="utf-8"))
        assert child1["parent_context_path"] == str(context_path)

    def test_generate_consumes_edits_from_context(self, app_client):
        """When save-edits stored edits on the parent context, generate must
        consume them — the new iteration must NOT carry edited_* forward."""
        client, context_path, _ = app_client
        # Save edits onto iteration 0
        client.post("/api/save-edits", json={
            "context_path": str(context_path),
            "edited_resume": "USER EDITED",
            "edited_cover_letter": "USER LETTER",
        })
        # Confirm edits landed on parent
        parent_after_edits = json.loads(context_path.read_text(encoding="utf-8"))
        assert parent_after_edits["edited_resume_text"] == "USER EDITED"

        # Now generate — child must not carry edited_* fields
        body = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(context_path),
        }).get_json()
        child = json.loads(Path(body["context_path"]).read_text(encoding="utf-8"))
        assert "edited_resume_text" not in child
        assert "edited_cover_letter_text" not in child

    def test_path_outside_output_dir_rejected(self, app_client, tmp_path):
        client, _, _ = app_client
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/generate", json={
            "username": "alice",
            "context_path": str(outside),
        })
        assert resp.status_code == 403


# ---------- /api/generate date-grounding guard (KW6) ------------------------

class TestGenerateDateGrounding:
    """KW6: corpus-mode generates run the deterministic date check; flagged
    headings surface as proofread_notes warnings + a date_grounding field.
    Warn-only — the route still returns 200 and the resume is untouched."""

    CORPUS = [
        {"id": 1, "company": "Acme", "start_date": "2016-01", "end_date": "2018-12",
         "eligible_titles": [{"id": 1, "title": "Product Lead", "is_official": True}],
         "bullets": [{"id": 1, "text": "Did a thing.", "tags": [], "has_outcome": False}]},
        {"id": 2, "company": "Acme", "start_date": "2012-01", "end_date": "2016-12",
         "eligible_titles": [{"id": 2, "title": "Design Lead", "is_official": True}],
         "bullets": [{"id": 2, "text": "Did another thing.", "tags": [], "has_outcome": False}]},
    ]

    def _make_corpus_context(self, context_path):
        ctx = json.loads(context_path.read_text(encoding="utf-8"))
        ctx["career_corpus"] = self.CORPUS
        context_path.write_text(json.dumps(ctx), encoding="utf-8")

    def _stub_generate_returning(self, monkeypatch, resume_content):
        def _stub(client, context_set, analysis, refinement_notes="",
                  username="", run_id="", with_cover_letter=True):
            return {
                "resume_content": resume_content,
                "cover_letter_content": "Letter.",
                "changes_made": [],
                "proofread_notes": ["model note"],
            }
        monkeypatch.setattr(bgen, "generate", _stub)

    def test_corrupted_date_flags_and_warns(self, app_client, monkeypatch):
        client, context_path, _ = app_client
        self._make_corpus_context(context_path)
        # The KW6 shape: 2012-2016 role re-stamped with the adjacent 2016-2018.
        self._stub_generate_returning(monkeypatch, (
            "# Alice\n\n## Experience\n\n"
            "### Acme, Product Lead\t2016 – 2018\n- Did a thing.\n\n"
            "### Acme, Design Lead\t2016 – 2018\n- Did another thing.\n"
        ))
        resp = client.post("/api/generate", json={
            "username": "alice", "context_path": str(context_path),
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["date_grounding"]["status"] == "flag"
        assert len(body["date_grounding"]["flagged"]) == 1
        # Warning rides the already-rendered proofread_notes list, after the
        # model's own notes; the resume preview itself is never mutated.
        assert body["proofread_notes"][0] == "model note"
        assert any("Date check:" in n for n in body["proofread_notes"])
        assert "2016 – 2018" in body["resume_preview"]

    def test_correct_dates_pass_without_warning(self, app_client, monkeypatch):
        client, context_path, _ = app_client
        self._make_corpus_context(context_path)
        self._stub_generate_returning(monkeypatch, (
            "# Alice\n\n## Experience\n\n"
            "### Acme, Product Lead\t2016 – 2018\n- Did a thing.\n\n"
            "### Acme, Design Lead\t2012 – 2016\n- Did another thing.\n"
        ))
        body = client.post("/api/generate", json={
            "username": "alice", "context_path": str(context_path),
        }).get_json()
        assert body["date_grounding"]["status"] == "pass"
        assert body["proofread_notes"] == ["model note"]

    def test_legacy_mode_skips_check(self, app_client):
        # Seeded context has no career_corpus -> no date ground truth.
        client, context_path, _ = app_client
        body = client.post("/api/generate", json={
            "username": "alice", "context_path": str(context_path),
        }).get_json()
        assert body["date_grounding"] is None
