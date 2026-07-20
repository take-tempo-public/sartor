"""Concurrent-writer regression tests for the remaining context-write-lost-update
gap sites (charter C-7 falsification, `docs/dev/diagnosis/context-write-lost-update-gap.md`).

`tests/test_app_clarify.py::TestConcurrentContextWriters` already covers the
`/api/clarify` <-> `/api/answer-clarifications` pairing (the one dynamically
reproduced on HEAD before the fix). This file covers the remaining two
LLM-backed sites — `/api/iterate-clarify` and `/api/generate-cover-letter` —
each raced against `/api/save-edits` (the fast, non-LLM writer), so all 5
sites named in the dossier get direct concurrent-write coverage.

Same shape as `docs/dev/diagnosis/compose-summary-draft-settle-hole.md`'s
original `TestConcurrentContextWriters`: stub the slow route's LLM call, gate
it on a `threading.Event` so the fast route can read/write inside the window,
then assert neither writer's delta was silently erased by the other's
whole-dict write-back.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest


@pytest.fixture
def races_app(tmp_path, monkeypatch):
    """Factory-built app with both analysis_bp and generation_bp routes live.

    Stubs `blueprints.analysis.clarify_iteration` and
    `analyzer.generate_cover_letter_against_resume` (lazily imported inside
    the route, so patched on the `analyzer` module per the established
    pattern in `tests/test_cover_letter_detached.py`) so both slow routes run
    without network calls. `/api/save-edits` needs no LLM stub — it has none.
    """
    import analyzer as _analyzer
    import blueprints.analysis as ban
    import blueprints.generation as bgen
    from app import create_app
    from config import Config

    monkeypatch.setattr(ban, "_get_client", lambda: object())
    monkeypatch.setattr(bgen, "_get_client", lambda: object())

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    output_dir = tmp_path / "output"
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    return app, output_dir, ban, bgen, _analyzer


def _seed(output_dir: Path, *, iteration: int) -> Path:
    ctx = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice", "skills": []},
        "resume": {"text": "original resume", "filename": "alice.docx", "format": ".docx"},
        "supplemental_resumes": [],
        "job_description": "JD body.",
        "deterministic_analysis": {
            "jd_keywords": {},
            "resume_keywords": {},
            "keyword_overlap": {},
            "ats_warnings": [],
        },
        "llm_analysis": {
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
        },
        "last_generated_resume": "# Generated résumé v1\n- Bullet.",
        "iteration": iteration,
        "run_id": "rid_races_test",
    }
    path = output_dir / "alice" / f"context_iter{iteration}.json"
    path.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
    return path


class TestIterateClarifyVsSaveEdits:
    """Does a concurrent `/api/iterate-clarify` erase `/api/save-edits`'s delta?"""

    def test_save_edits_does_not_erase_a_concurrent_iterate_clarify(self, races_app):
        app, output_dir, ban, _bgen, _analyzer = races_app
        ctx_path = _seed(output_dir, iteration=1)

        iterate_has_read = threading.Event()
        save_has_persisted = threading.Event()

        def _slow_iterate_clarify(
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
            iterate_has_read.set()
            assert save_has_persisted.wait(timeout=20), "/api/save-edits never persisted"
            return {
                "questions": [
                    {
                        "id": "iq1",
                        "text": "New iteration Q?",
                        "target_gap": "g",
                        "kind": "iteration_probe",
                    }
                ],
                "reasoning": "One probe.",
            }

        ban.clarify_iteration = _slow_iterate_clarify

        status: dict[str, int] = {}

        def _fire_iterate() -> None:
            c = app.test_client()
            r = c.post("/api/iterate-clarify", json={"context_path": str(ctx_path)})
            status["iterate"] = r.status_code

        t = threading.Thread(target=_fire_iterate)
        t.start()
        assert iterate_has_read.wait(timeout=20), "/api/iterate-clarify never reached its LLM call"

        c2 = app.test_client()
        r2 = c2.post(
            "/api/save-edits",
            json={"context_path": str(ctx_path), "edited_resume": "My hand-edited résumé text."},
        )
        status["save"] = r2.status_code
        save_has_persisted.set()

        t.join(timeout=30)
        assert not t.is_alive(), "/api/iterate-clarify thread hung"

        assert status.get("save") == 200, f"/api/save-edits did not succeed: {status}"
        assert status.get("iterate") == 200, f"/api/iterate-clarify did not succeed: {status}"

        final = json.loads(ctx_path.read_text(encoding="utf-8"))

        # The route always re-keys ids to iter{iteration}_q{i} regardless of
        # what the stub returned (analysis.py's id-collision-avoidance loop).
        assert any(q.get("id") == "iter1_q1" for q in final.get("clarification_questions", [])), (
            "/api/iterate-clarify's delta is missing"
        )
        assert final.get("edited_resume_text") == "My hand-edited résumé text.", (
            "LOST UPDATE: /api/iterate-clarify's whole-dict write-back erased the edit "
            "/api/save-edits had already persisted."
        )


class TestGenerateCoverLetterVsSaveEdits:
    """Does a concurrent `/api/generate-cover-letter` erase `/api/save-edits`'s delta?"""

    def test_save_edits_does_not_erase_a_concurrent_cover_letter_generate(self, races_app):
        app, output_dir, _ban, bgen, _analyzer = races_app
        ctx_path = _seed(output_dir, iteration=0)

        cl_has_read = threading.Event()
        save_has_persisted = threading.Event()

        def _slow_generate_cl(
            client,
            context_set,
            analysis,
            resume_content,
            *,
            refinement_notes="",
            username="",
            run_id="",
        ):
            cl_has_read.set()
            assert save_has_persisted.wait(timeout=20), "/api/save-edits never persisted"
            return {"cover_letter_content": "A focused cover letter.", "proofread_notes": []}

        _analyzer.generate_cover_letter_against_resume = _slow_generate_cl

        def _stub_letter_writer(content, user, base_dir):
            out = Path(base_dir) / user / "cover_stub.docx"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
            return str(out)

        bgen.generate_cover_letter = _stub_letter_writer

        status: dict[str, int] = {}

        def _fire_cl() -> None:
            c = app.test_client()
            r = c.post("/api/generate-cover-letter", json={"context_path": str(ctx_path)})
            status["cl"] = r.status_code

        t = threading.Thread(target=_fire_cl)
        t.start()
        assert cl_has_read.wait(timeout=20), "/api/generate-cover-letter never reached its LLM call"

        c2 = app.test_client()
        r2 = c2.post(
            "/api/save-edits",
            json={"context_path": str(ctx_path), "edited_resume": "My hand-edited résumé text."},
        )
        status["save"] = r2.status_code
        save_has_persisted.set()

        t.join(timeout=30)
        assert not t.is_alive(), "/api/generate-cover-letter thread hung"

        assert status.get("save") == 200, f"/api/save-edits did not succeed: {status}"
        assert status.get("cl") == 200, f"/api/generate-cover-letter did not succeed: {status}"

        final = json.loads(ctx_path.read_text(encoding="utf-8"))

        assert final.get("last_generated_cover_letter") == "A focused cover letter.", (
            "/api/generate-cover-letter's delta is missing"
        )
        assert final.get("edited_resume_text") == "My hand-edited résumé text.", (
            "LOST UPDATE: /api/generate-cover-letter's whole-dict write-back erased the edit "
            "/api/save-edits had already persisted."
        )
