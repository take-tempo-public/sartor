"""Tests for the /api/clarify and /api/answer-clarifications routes.

Mocks analyzer.clarify() at the import boundary in app.py so tests run without
network or Anthropic SDK calls. Verifies the security guards (_safe_username,
_within) and the persistence shape (clarification_questions, clarifications)
written back to the context file.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client with OUTPUT_DIR and CONFIGS_DIR redirected to tmp_path.

    Also creates a saved context_*.json file under OUTPUT_DIR/alice/ so the
    routes have something to load. analyzer.clarify is replaced with a
    deterministic stub so no network or LLM call is made.
    """
    import app as _app

    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    output_dir.mkdir()
    configs_dir.mkdir()
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    monkeypatch.setattr(_app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(_app, "CONFIGS_DIR", configs_dir)

    # Stub clarify to return a deterministic payload; the route should accept it
    # whether or not the LLM was actually called.
    def _stub_clarify(client, context_set, analysis, username="", run_id=""):
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "Used Kubernetes in production?",
                    "target_gap": "Essential skill Kubernetes missing from resume",
                    "kind": "experience_probe",
                },
                {
                    "id": "q2",
                    "text": "Did the migration ship or remain a POC?",
                    "target_gap": "Scope ambiguity flagged in title_alignment",
                    "kind": "scope_probe",
                },
            ],
            "reasoning": "Two probes covering missing tech and shipped status.",
        }

    monkeypatch.setattr(_app, "clarify", _stub_clarify)
    # Avoid real API client construction
    monkeypatch.setattr(_app, "_get_client", lambda: object())

    _app.app.config["TESTING"] = True
    client = _app.app.test_client()
    context_path = output_dir / "alice" / "context_20260511_120000.json"
    initial = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice", "skills": ["docker"]},
        "resume": {"text": "...", "filename": "alice.docx", "format": ".docx",
                   "sections": [], "path": ""},
        "supplemental_resumes": [],
        "job_description": "K8s SRE role.",
        "deterministic_analysis": {
            "jd_keywords": {}, "resume_keywords": {},
            "keyword_overlap": {"missing_from_resume": ["kubernetes"]},
            "ats_warnings": [],
        },
        "llm_analysis": {
            "essential_skills": ["kubernetes"],
            "preferred_skills": [],
            "comparison": {"strengths": [], "gaps": ["No K8s"], "title_alignment": ""},
            "keyword_placement": [],
            "overall_strategy": "",
            "ideal_resume_profile": "",
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "suggestions": [],
            "ats_improvements": [],
        },
        "run_id": "abc123abc123",
    }
    context_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    return client, context_path, output_dir


class TestClarifyRoute:
    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/clarify", json={})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, output_dir = app_client
        # Path that's a sibling of OUTPUT_DIR — must be rejected by _within
        outside = tmp_path / "elsewhere.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/clarify", json={"context_path": str(outside)})
        assert resp.status_code == 403

    def test_nonexistent_context_file_returns_404(self, app_client, tmp_path):
        client, _, output_dir = app_client
        ghost = output_dir / "alice" / "context_ghost.json"
        resp = client.post("/api/clarify", json={"context_path": str(ghost)})
        assert resp.status_code == 404

    def test_context_without_analysis_returns_400(self, app_client, tmp_path):
        client, _, output_dir = app_client
        no_analysis = output_dir / "alice" / "context_blank.json"
        no_analysis.write_text(json.dumps({"timestamp": "x", "candidate": {}}), encoding="utf-8")
        resp = client.post("/api/clarify", json={"context_path": str(no_analysis)})
        assert resp.status_code == 400

    def test_happy_path_persists_questions_and_returns_them(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/clarify", json={"context_path": str(context_path)})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["questions"]) == 2
        assert body["questions"][0]["kind"] == "experience_probe"
        assert "context_path" in body

        # Questions must be persisted on the same context file
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert "clarification_questions" in saved
        assert len(saved["clarification_questions"]) == 2

    def test_preserves_existing_run_id(self, app_client):
        client, context_path, _ = app_client
        client.post("/api/clarify", json={"context_path": str(context_path)})
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["run_id"] == "abc123abc123"


class TestAnswerClarificationsRoute:
    def _seed_questions(self, context_path: Path):
        """Pre-populate clarification_questions on the saved context."""
        ctx = json.loads(context_path.read_text(encoding="utf-8"))
        ctx["clarification_questions"] = [
            {"id": "q1", "text": "Q1?", "kind": "experience_probe", "target_gap": "k8s"},
            {"id": "q2", "text": "Q2?", "kind": "scope_probe", "target_gap": "scope"},
        ]
        context_path.write_text(json.dumps(ctx, indent=2), encoding="utf-8")

    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/answer-clarifications", json={"answers": {}})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, _ = app_client
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/answer-clarifications", json={
            "context_path": str(outside), "answers": {}
        })
        assert resp.status_code == 403

    def test_answers_must_be_dict(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/answer-clarifications", json={
            "context_path": str(context_path), "answers": ["not", "a", "dict"]
        })
        assert resp.status_code == 400

    def test_stores_valid_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post("/api/answer-clarifications", json={
            "context_path": str(context_path),
            "answers": {"q1": "Yes, used K8s briefly.", "q2": "Shipped to prod."},
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body == {"ok": True, "answered": 2, "total": 2}

        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {
            "q1": "Yes, used K8s briefly.",
            "q2": "Shipped to prod.",
        }

    def test_filters_unknown_question_ids(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post("/api/answer-clarifications", json={
            "context_path": str(context_path),
            "answers": {"q1": "real answer", "q_attacker": "injected"},
        })
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert "q_attacker" not in saved["clarifications"]
        assert saved["clarifications"] == {"q1": "real answer"}

    def test_filters_empty_and_whitespace_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post("/api/answer-clarifications", json={
            "context_path": str(context_path),
            "answers": {"q1": "   ", "q2": "real answer"},
        })
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {"q2": "real answer"}

    def test_idempotent_overwrites_prior_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        client.post("/api/answer-clarifications", json={
            "context_path": str(context_path),
            "answers": {"q1": "first try"},
        })
        client.post("/api/answer-clarifications", json={
            "context_path": str(context_path),
            "answers": {"q1": "revised answer", "q2": "added later"},
        })
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {
            "q1": "revised answer", "q2": "added later",
        }
