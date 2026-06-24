"""Tests for the /api/iterate-clarify route (the iteration interview).

The route lives on `blueprints/analysis.py` (Sprint 8.3b — relocated here out of
test_app_iteration.py, which keeps the generation-seam tests until 8.3c). Tests
build the app via the `create_app(Config(base_dir=tmp_path))` factory and stub
`analyzer.clarify_iteration` on the blueprint module (the imported binding the
route resolves). The iteration≥1 precondition is seeded directly onto the context
file (the shape `/api/generate` would have written) so these tests exercise
iterate-clarify in isolation, with no dependency on the generation routes.
"""

import json
from pathlib import Path

import pytest

import blueprints.analysis as ban

_BASE_ANALYSIS = {
    "essential_skills": [],
    "preferred_skills": [],
    "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
    "keyword_placement": [],
    "overall_strategy": "",
    "ideal_resume_profile": "",
    "industry_keywords": [],
    "hidden_qualities": [],
    "professional_vocabulary": [],
    "suggestions": [],
    "ats_improvements": [],
}


def _seed_context(output_dir: Path, name: str, *, iteration: int, **extra) -> Path:
    """Write a context_*.json under output_dir/alice/ with the given iteration.

    Mirrors what /api/analyze (+ /api/generate at iteration>=1) would have
    written. `extra` overlays fields like last_generated_resume,
    edited_resume_text, clarification_questions, clarifications.
    """
    ctx: dict = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice", "skills": []},
        "resume": {
            "text": "original resume",
            "filename": "alice.docx",
            "format": ".docx",
            "sections": [],
            "path": "",
        },
        "supplemental_resumes": [],
        "job_description": "JD body.",
        "deterministic_analysis": {
            "jd_keywords": {},
            "resume_keywords": {},
            "keyword_overlap": {},
            "ats_warnings": [],
        },
        "llm_analysis": dict(_BASE_ANALYSIS),
        "iteration": iteration,
        "run_id": "rid_iteration_test",
    }
    ctx.update(extra)
    path = output_dir / "alice" / name
    path.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def iterate_client(tmp_path, monkeypatch):
    """Factory-built test client with `clarify_iteration` stubbed on the blueprint.

    Returns (client, output_dir, captured): `captured` is filled by the stub with
    the inputs clarify_iteration received, so tests can assert the route threaded
    the four signal sources through.
    """
    from app import create_app
    from config import Config

    captured: dict = {}

    # Stub the iteration clarifier — return a fixed 3-question payload and record
    # the inputs so tests can verify route plumbing (signals passed, questions
    # persisted with iteration-prefixed ids) rather than the LLM's question quality.
    def _stub_iterate_clarify(
        client,
        context_set,
        analysis,
        current_resume_text,
        current_cover_letter_text,
        recent_edits_summary,
        deterministic_signals,
        prior_clarifications,
        username="",
        run_id="",
    ):
        captured.update(
            {
                "current_resume_text": current_resume_text,
                "current_cover_letter_text": current_cover_letter_text,
                "recent_edits_summary": recent_edits_summary,
                "deterministic_signals": deterministic_signals,
                "prior_clarifications": prior_clarifications,
            }
        )
        return {
            "questions": [
                {"id": "q1", "text": "Q1?", "target_gap": "g1", "kind": "iteration_probe"},
                {"id": "q2", "text": "Q2?", "target_gap": "g2", "kind": "experience_probe"},
                {"id": "q3", "text": "Q3?", "target_gap": "g3", "kind": "scope_probe"},
            ],
            "reasoning": "Three probes.",
        }

    monkeypatch.setattr(ban, "clarify_iteration", _stub_iterate_clarify)
    monkeypatch.setattr(ban, "_get_client", lambda: object())

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    # ensure_dirs() (in the factory) already created configs/output under tmp_path.
    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    return app.test_client(), output_dir, captured


class TestIterateClarifyRoute:
    def test_missing_context_path_returns_400(self, iterate_client):
        client, _, _ = iterate_client
        resp = client.post("/api/iterate-clarify", json={})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, iterate_client, tmp_path):
        client, _, _ = iterate_client
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/iterate-clarify", json={"context_path": str(outside)})
        assert resp.status_code == 403

    def test_iteration_zero_context_rejected_with_400(self, iterate_client):
        """The iteration interview requires a generated draft to probe — calling
        on iteration 0 (analyze-only) should bounce the user back to /api/clarify."""
        client, output_dir, _ = iterate_client
        parent_path = _seed_context(output_dir, "context_iter0.json", iteration=0)
        resp = client.post(
            "/api/iterate-clarify",
            json={
                "context_path": str(parent_path),
            },
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "at least one generated draft" in body["error"].lower()

    def test_happy_path_persists_questions_with_iteration_prefixed_ids(self, iterate_client):
        client, output_dir, _ = iterate_client
        iter1_path = _seed_context(
            output_dir,
            "context_iter1.json",
            iteration=1,
            last_generated_resume="# Draft\n- Did things.",
        )

        resp = client.post(
            "/api/iterate-clarify",
            json={
                "context_path": str(iter1_path),
                "username": "alice",
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["questions"]) == 3
        assert body["iteration"] == 1

        # Question ids must be re-keyed to avoid colliding with prior /api/clarify ids
        ids = [q["id"] for q in body["questions"]]
        assert all(qid.startswith("iter1_") for qid in ids)

        # Persisted on the same context file
        saved = json.loads(iter1_path.read_text(encoding="utf-8"))
        assert len(saved["clarification_questions"]) == 3
        # Audit note appended
        assert any(n["action"] == "iterate_clarify" for n in saved.get("iteration_notes", []))

    def test_appends_to_prior_clarification_questions(self, iterate_client):
        """Iteration questions must be APPENDED to clarification_questions, not
        overwriting. Otherwise the audit chain breaks and prior answers can't
        be paired by id."""
        client, output_dir, _ = iterate_client
        # Seed an iteration-1 context that already carries a prior clarify-round
        # question + answer (the state /api/generate would have inherited forward).
        iter1_path = _seed_context(
            output_dir,
            "context_iter1.json",
            iteration=1,
            last_generated_resume="# Draft\n- Did things.",
            clarification_questions=[
                {"id": "q1", "text": "Prior Q?", "target_gap": "g", "kind": "experience_probe"},
            ],
            clarifications={"q1": "Prior answer."},
        )

        client.post(
            "/api/iterate-clarify",
            json={
                "context_path": str(iter1_path),
                "username": "alice",
            },
        )

        saved = json.loads(iter1_path.read_text(encoding="utf-8"))
        ids = [q["id"] for q in saved["clarification_questions"]]
        # Original q1 preserved AND iter1_ ids appended
        assert "q1" in ids
        assert sum(qid.startswith("iter1_") for qid in ids) == 3
        # Prior answer still paired
        assert saved["clarifications"]["q1"] == "Prior answer."

    def test_passes_signals_and_prior_clarifications_to_clarifier(self, iterate_client):
        """Route must thread the four signal sources (current draft, edits,
        deterministic metrics, prior clarifications) through to clarify_iteration."""
        client, output_dir, captured = iterate_client
        # Seed an iteration-1 context with a prior answered clarification (and a
        # skipped one) plus a user edit on top of the last generated draft — the
        # state save-edits + generate would have produced.
        iter1_path = _seed_context(
            output_dir,
            "context_iter1.json",
            iteration=1,
            last_generated_resume="# Draft\n- Did things.",
            edited_resume_text="# Edited\n- Shipped V2 to enterprise customers in Q3.",
            clarification_questions=[
                {"id": "q1", "text": "K8s?", "kind": "experience_probe", "target_gap": "k8s"},
                {
                    "id": "q_skipped",
                    "text": "Skipped?",
                    "kind": "scope_probe",
                    "target_gap": "scope",
                },
            ],
            clarifications={"q1": "Yes prod 2023."},  # q_skipped intentionally omitted
        )

        client.post(
            "/api/iterate-clarify",
            json={
                "context_path": str(iter1_path),
                "username": "alice",
            },
        )

        inputs = captured
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
