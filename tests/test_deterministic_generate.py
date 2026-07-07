"""Tests for Phase 4 — deterministic corpus-mode Generate.

Generation-experience re-architecture (fix/compose-frozen-composition): in corpus
mode, /api/generate assembles the frozen ``approved_composition`` deterministically
(ZERO résumé-body LLM calls) instead of calling analyzer.generate(). The COVER
LETTER stays an LLM call. Legacy (no ``career_corpus``) and pre-freeze corpus
contexts keep the generate() LLM path — so --suite synthetic stays byte-identical.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

import blueprints.generation as bgen
from json_resume import json_resume_to_markdown, md_to_json_resume

_APPROVED = {
    "$schema": "x",
    "basics": {
        "name": "Alice Rivera",
        "summary": "A platform PM who ships. Cut churn with a rewrite.",
    },
    "work": [
        {
            "name": "Acme",
            "position": "Senior PM",
            "startDate": "2021-01",
            "endDate": "present",
            "highlights": ["Led the billing rewrite that cut churn."],
        }
    ],
    "skills": [{"name": "Python"}, {"name": "Kubernetes"}],
    "education": [],
    "certificates": [],
    "projects": [],
    "meta": {
        "sartor": {
            "frozen": True,
            "work_provenance": [
                {"experience_id": 3, "title_id": 9, "role_intro_id": None, "highlight_ids": [41]}
            ],
        }
    },
}


# -------------------------------------------------------------------
# json_resume_to_markdown — the deterministic inverse serializer
# -------------------------------------------------------------------


class TestJsonResumeToMarkdown:
    def test_round_trips_core_fields(self):
        md = json_resume_to_markdown(_APPROVED)
        rt = md_to_json_resume(md)
        assert rt["basics"]["name"] == "Alice Rivera"
        assert rt["basics"]["summary"].startswith("A platform PM")
        assert rt["work"][0]["name"] == "Acme"
        assert rt["work"][0]["position"] == "Senior PM"
        assert rt["work"][0]["highlights"] == ["Led the billing rewrite that cut churn."]
        assert [s["name"] for s in rt["skills"]] == ["Python", "Kubernetes"]

    def test_empty_doc_is_deterministic(self):
        md = json_resume_to_markdown({"basics": {}, "work": [], "skills": []})
        assert json_resume_to_markdown({"basics": {}, "work": [], "skills": []}) == md

    def test_no_llm_no_clock(self):
        # Same input → identical output twice (no time/randomness).
        assert json_resume_to_markdown(_APPROVED) == json_resume_to_markdown(_APPROVED)


# -------------------------------------------------------------------
# _frozen_composition — the deterministic-assemble gate
# -------------------------------------------------------------------


class TestFrozenCompositionGate:
    def test_none_without_career_corpus(self):
        assert bgen._frozen_composition({"approved_composition": _APPROVED}) is None

    def test_none_without_approved_composition(self):
        assert bgen._frozen_composition({"career_corpus": [{"id": 1}]}) is None

    def test_none_when_approved_empty(self):
        empty = {"basics": {}, "work": [], "skills": []}
        ctx = {"career_corpus": [{"id": 1}], "approved_composition": empty}
        assert bgen._frozen_composition(ctx) is None

    def test_returns_doc_when_corpus_and_content(self):
        ctx = {"career_corpus": [{"id": 1}], "approved_composition": _APPROVED}
        assert bgen._frozen_composition(ctx) is _APPROVED


# -------------------------------------------------------------------
# _assemble_from_frozen_composition — the deterministic result builder
# -------------------------------------------------------------------


class TestAssembleFromFrozen:
    def test_no_cover_letter_no_llm(self):
        # client=object() would blow up if the cover-letter LLM path ran.
        result = bgen._assemble_from_frozen_composition(
            object(), {}, {}, _APPROVED, with_cover_letter=False, username="u", run_id="r"
        )
        assert result["cover_letter_content"] == ""
        assert result["resume_content"] == json_resume_to_markdown(_APPROVED)
        assert result["proposed_new_bullets"] == []
        assert result["proposed_experience_titles"] == []
        # selected_bullets synthesized from meta.sartor.work_provenance
        assert result["selected_bullets"] == [
            {"experience_id": 3, "chosen_title_id": 9, "bullet_ids_in_order": [41]}
        ]

    def test_cover_letter_calls_llm(self, monkeypatch):
        seen = {}

        def _fake_cl(client, ctx, analysis, resume_content, username="", run_id=""):
            seen["resume_content"] = resume_content
            return {"cover_letter_content": "Dear hiring manager, ..."}

        monkeypatch.setattr(bgen, "generate_cover_letter_against_resume", _fake_cl)
        result = bgen._assemble_from_frozen_composition(
            object(), {}, {}, _APPROVED, with_cover_letter=True, username="u", run_id="r"
        )
        assert result["cover_letter_content"] == "Dear hiring manager, ..."
        # The LLM cover letter is written against the assembled résumé text.
        assert "billing rewrite" in seen["resume_content"]


# -------------------------------------------------------------------
# Route integration — /api/generate + /api/generate/stream
# -------------------------------------------------------------------


@pytest.fixture
def gen_app(tmp_path, monkeypatch):
    import db.session as db_session

    monkeypatch.setattr(db_session, "DEFAULT_DB_PATH", tmp_path / "test.sqlite")
    db_session._engine = None
    db_session._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    output_dir = tmp_path / "output"
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    calls = {"generate": 0, "generate_streaming": 0, "cover_letter_llm": 0}

    def _tracked_generate(*a, **k):
        calls["generate"] += 1
        return {
            "resume_content": "# LLM WROTE THIS",
            "cover_letter_content": "",
            "changes_made": [],
            "proofread_notes": [],
        }

    def _tracked_stream(*a, **k):
        calls["generate_streaming"] += 1
        yield (
            "done",
            {
                "resume_content": "# LLM WROTE THIS (stream)",
                "cover_letter_content": "",
                "changes_made": [],
                "proofread_notes": [],
            },
        )

    def _fake_cl(client, ctx, analysis, resume_content, username="", run_id=""):
        calls["cover_letter_llm"] += 1
        return {"cover_letter_content": "LLM COVER LETTER"}

    def _stub_letter_writer(content, user, base_dir):
        out = Path(base_dir) / user / "cover_stub.docx"
        out.write_text(content, encoding="utf-8")
        return str(out)

    monkeypatch.setattr(bgen, "generate", _tracked_generate)
    monkeypatch.setattr(bgen, "generate_streaming", _tracked_stream)
    monkeypatch.setattr(bgen, "generate_cover_letter_against_resume", _fake_cl)
    monkeypatch.setattr(bgen, "generate_cover_letter", _stub_letter_writer)
    monkeypatch.setattr(bgen, "_get_client", lambda: object())

    return types.SimpleNamespace(client=app.test_client(), output_dir=output_dir, calls=calls)


def _write_ctx(output_dir, *, corpus=True, approved=True):
    ctx: dict = {
        "resume": {
            "text": "orig",
            "filename": "alice.docx",
            "format": ".docx",
            "sections": [],
            "path": "",
        },
        "job_description": "JD body.",
        "llm_analysis": {
            "essential_skills": [],
            "preferred_skills": [],
            "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
            "keyword_placement": [],
            "industry_keywords": [],
        },
        "deterministic_analysis": {"keyword_overlap": {}},
        "iteration": 0,
        "run_id": "rid",
    }
    if corpus:
        ctx["career_corpus"] = [
            {
                "id": 3,
                "company": "Acme",
                "start_date": "2021-01",
                "end_date": "present",
                "eligible_titles": [],
                "bullets": [{"id": 41, "text": "Led the billing rewrite that cut churn."}],
            }
        ]
    if approved:
        ctx["approved_composition"] = _APPROVED
    p = output_dir / "alice" / "context_iter0.json"
    p.write_text(json.dumps(ctx), encoding="utf-8")
    return str(p)


class TestDeterministicGenerateRoute:
    def test_corpus_generate_makes_no_resume_llm_call(self, gen_app):
        ctx_path = _write_ctx(gen_app.output_dir)
        r = gen_app.client.post(
            "/api/generate",
            json={"username": "alice", "context_path": ctx_path, "output_format": ".md"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        # Zero résumé-body LLM calls — the headline invariant.
        assert gen_app.calls["generate"] == 0
        assert gen_app.calls["cover_letter_llm"] == 0
        # download == approved_composition (the .md is the frozen doc serialized).
        body = r.get_json()
        resume_md = Path(body["resume_path"]).read_text(encoding="utf-8")
        assert resume_md == json_resume_to_markdown(_APPROVED)
        assert "Led the billing rewrite" in resume_md
        assert body["resume_preview"] == json_resume_to_markdown(_APPROVED)

    def test_corpus_generate_cover_letter_stays_llm(self, gen_app):
        ctx_path = _write_ctx(gen_app.output_dir)
        r = gen_app.client.post(
            "/api/generate",
            json={
                "username": "alice",
                "context_path": ctx_path,
                "output_format": ".md",
                "generate_cover_letter": True,
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        assert gen_app.calls["generate"] == 0  # résumé body still no LLM
        assert gen_app.calls["cover_letter_llm"] == 1  # cover letter IS an LLM call
        assert r.get_json()["cover_letter_preview"] == "LLM COVER LETTER"

    def test_legacy_context_still_calls_generate(self, gen_app):
        ctx_path = _write_ctx(gen_app.output_dir, corpus=False, approved=False)
        r = gen_app.client.post(
            "/api/generate",
            json={"username": "alice", "context_path": ctx_path, "output_format": ".md"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        assert gen_app.calls["generate"] == 1  # legacy LLM path unchanged

    def test_corpus_without_freeze_falls_back_to_llm(self, gen_app):
        # career_corpus present but NO approved_composition (pre-freeze) → LLM path.
        ctx_path = _write_ctx(gen_app.output_dir, corpus=True, approved=False)
        r = gen_app.client.post(
            "/api/generate",
            json={"username": "alice", "context_path": ctx_path, "output_format": ".md"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        assert gen_app.calls["generate"] == 1

    def test_streaming_corpus_makes_no_resume_llm_call(self, gen_app):
        ctx_path = _write_ctx(gen_app.output_dir)
        r = gen_app.client.post(
            "/api/generate/stream",
            json={"username": "alice", "context_path": ctx_path, "output_format": ".md"},
        )
        assert r.status_code == 200
        text = r.get_data(as_text=True)
        assert gen_app.calls["generate_streaming"] == 0  # deterministic — no streaming LLM
        # The assembled résumé rode the chunk + done events.
        assert "Led the billing rewrite" in text
