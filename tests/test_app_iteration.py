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


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client with OUTPUT_DIR/CONFIGS_DIR/RESUMES_DIR redirected
    and the LLM/document-generation calls stubbed.

    Seeds an iteration-0 context for /alice/ that mirrors what /api/analyze
    would have written. Tests exercise routes without any real LLM call.
    """
    import app as _app

    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    resumes_dir = tmp_path / "resumes"
    output_dir.mkdir()
    configs_dir.mkdir()
    resumes_dir.mkdir()
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()
    (resumes_dir / "alice").mkdir()

    monkeypatch.setattr(_app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(_app, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(_app, "RESUMES_DIR", resumes_dir)

    # Stub the generate() LLM call — return deterministic content.
    def _stub_generate(client, context_set, analysis, refinement_notes="",
                      username="", run_id=""):
        return {
            "resume_content": f"# Generated resume (iter input={context_set.get('iteration', 0)})",
            "cover_letter_content": "Generated cover letter body.",
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

    # Stub the iteration clarifier — return a fixed 3-question payload.
    # Tests verify route plumbing (signals passed, questions persisted with
    # iteration-prefixed ids) rather than the LLM's question quality.
    def _stub_iterate_clarify(client, context_set, analysis, current_resume_text,
                               current_cover_letter_text, recent_edits_summary,
                               deterministic_signals, prior_clarifications,
                               username="", run_id=""):
        # Record the inputs on a module-level slot so tests can introspect them
        _app._last_iterate_clarify_inputs = {
            "current_resume_text": current_resume_text,
            "current_cover_letter_text": current_cover_letter_text,
            "recent_edits_summary": recent_edits_summary,
            "deterministic_signals": deterministic_signals,
            "prior_clarifications": prior_clarifications,
        }
        return {
            "questions": [
                {"id": "q1", "text": "Q1?", "target_gap": "g1", "kind": "iteration_probe"},
                {"id": "q2", "text": "Q2?", "target_gap": "g2", "kind": "experience_probe"},
                {"id": "q3", "text": "Q3?", "target_gap": "g3", "kind": "scope_probe"},
            ],
            "reasoning": "Three probes.",
        }

    monkeypatch.setattr(_app, "generate", _stub_generate)
    monkeypatch.setattr(_app, "generate_resume", _stub_resume_writer)
    monkeypatch.setattr(_app, "generate_cover_letter", _stub_letter_writer)
    monkeypatch.setattr(_app, "clarify_iteration", _stub_iterate_clarify)
    monkeypatch.setattr(_app, "_get_client", lambda: object())

    _app.app.config["TESTING"] = True
    client = _app.app.test_client()

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


# ---------- /api/iterate-clarify -------------------------------------------

class TestIterateClarifyRoute:
    def _advance_to_iteration_one(self, client, parent_context_path) -> str:
        """Run /api/generate once so we have an iteration-1 context to probe."""
        resp = client.post("/api/generate", json={
            "username": "alice", "context_path": str(parent_context_path),
        })
        return resp.get_json()["context_path"]

    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/iterate-clarify", json={})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, _ = app_client
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/iterate-clarify", json={"context_path": str(outside)})
        assert resp.status_code == 403

    def test_iteration_zero_context_rejected_with_400(self, app_client):
        """The iteration interview requires a generated draft to probe — calling
        on iteration 0 (analyze-only) should bounce the user back to /api/clarify."""
        client, parent_path, _ = app_client
        resp = client.post("/api/iterate-clarify", json={
            "context_path": str(parent_path),
        })
        assert resp.status_code == 400
        body = resp.get_json()
        assert "at least one generated draft" in body["error"].lower()

    def test_happy_path_persists_questions_with_iteration_prefixed_ids(self, app_client):
        client, parent_path, _ = app_client
        iter1_path = self._advance_to_iteration_one(client, parent_path)

        resp = client.post("/api/iterate-clarify", json={
            "context_path": iter1_path, "username": "alice",
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["questions"]) == 3
        assert body["iteration"] == 1

        # Question ids must be re-keyed to avoid colliding with prior /api/clarify ids
        ids = [q["id"] for q in body["questions"]]
        assert all(qid.startswith("iter1_") for qid in ids)

        # Persisted on the same context file
        saved = json.loads(Path(iter1_path).read_text(encoding="utf-8"))
        assert len(saved["clarification_questions"]) == 3
        # Audit note appended
        assert any(n["action"] == "iterate_clarify" for n in saved.get("iteration_notes", []))

    def test_appends_to_prior_clarification_questions(self, app_client):
        """Iteration questions must be APPENDED to clarification_questions, not
        overwriting. Otherwise the audit chain breaks and prior answers can't
        be paired by id."""
        client, parent_path, _ = app_client
        # Seed a prior clarify-style question on parent (iteration 0)
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
        parent["clarification_questions"] = [
            {"id": "q1", "text": "Prior Q?", "target_gap": "g", "kind": "experience_probe"},
        ]
        parent["clarifications"] = {"q1": "Prior answer."}
        parent_path.write_text(json.dumps(parent), encoding="utf-8")

        iter1_path = self._advance_to_iteration_one(client, parent_path)

        # Iter1 context should have inherited the prior question + answer
        iter1_ctx = json.loads(Path(iter1_path).read_text(encoding="utf-8"))
        assert len(iter1_ctx["clarification_questions"]) == 1
        assert iter1_ctx["clarifications"] == {"q1": "Prior answer."}

        client.post("/api/iterate-clarify", json={
            "context_path": iter1_path, "username": "alice",
        })

        saved = json.loads(Path(iter1_path).read_text(encoding="utf-8"))
        ids = [q["id"] for q in saved["clarification_questions"]]
        # Original q1 preserved AND iter1_ ids appended
        assert "q1" in ids
        assert sum(qid.startswith("iter1_") for qid in ids) == 3
        # Prior answer still paired
        assert saved["clarifications"]["q1"] == "Prior answer."

    def test_passes_signals_and_prior_clarifications_to_clarifier(self, app_client):
        """Route must thread the four signal sources (current draft, edits,
        deterministic metrics, prior clarifications) through to clarify_iteration."""
        client, parent_path, _ = app_client
        # Seed prior clarification w/ answer so it propagates
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
        parent["clarification_questions"] = [
            {"id": "q1", "text": "K8s?", "kind": "experience_probe", "target_gap": "k8s"},
            {"id": "q_skipped", "text": "Skipped?", "kind": "scope_probe", "target_gap": "scope"},
        ]
        parent["clarifications"] = {"q1": "Yes prod 2023."}  # q_skipped intentionally omitted
        parent_path.write_text(json.dumps(parent), encoding="utf-8")

        iter1_path = self._advance_to_iteration_one(client, parent_path)
        # Apply some edits so the recent_edits_summary has content
        client.post("/api/save-edits", json={
            "context_path": iter1_path,
            "edited_resume": "# Edited\n- Shipped V2 to enterprise customers in Q3.",
        })

        client.post("/api/iterate-clarify", json={
            "context_path": iter1_path, "username": "alice",
        })

        import app as _app
        inputs = _app._last_iterate_clarify_inputs
        # Current draft reflects the edit (precedence: edited > last_generated)
        assert "Shipped V2 to enterprise" in inputs["current_resume_text"]
        # Recent edits summary has the diff
        assert inputs["recent_edits_summary"]  # non-empty
        # Deterministic signals computed (keys present)
        sig = inputs["deterministic_signals"]
        assert "verb_diversity" in sig
        assert "specificity_density" in sig
        assert "grounding_overlap" in sig
        assert "keyword_coverage" in sig
        # Prior clarification with answer made it through; skipped one did not
        priors = inputs["prior_clarifications"]
        assert len(priors) == 1
        assert priors[0]["answer"] == "Yes prod 2023."
        assert priors[0]["question"] == "K8s?"
