"""Tests for the annotation + bootstrap write surface (app.py).

The console's first READ-WRITE routes (feat/annotation-tab). All routes are
localhost-only and write ONLY under the (monkeypatched-to-temp) ANNOTATION_ROOT,
reusing the deterministic, fail-closed evals.annotation contract. The bootstrap
SSE route's LLM pipeline is stubbed — no paid calls in the suite.
"""

from __future__ import annotations

import importlib
import json

import pytest


@pytest.fixture
def ann_app(tmp_path, monkeypatch):
    """Reload app.py with temp DB + temp config/output + temp ANNOTATION_ROOT."""
    db_file = tmp_path / "ann.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    import app as app_module

    importlib.reload(app_module)
    ann_root = tmp_path / "fixtures_real"
    monkeypatch.setattr(app_module, "CONFIGS_DIR", tmp_path / "configs")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "ANNOTATION_ROOT", ann_root)
    (tmp_path / "configs").mkdir()
    (tmp_path / "output").mkdir()
    ann_root.mkdir()
    (tmp_path / "configs" / "alice.config").write_text("{}", encoding="utf-8")

    from db.session import init_db

    init_db(db_file)
    return app_module


def _seed_bootstrap(root, slug="alice-bootstrap", candidate="alice"):
    """Write a minimal valid bootstrap.json under root/<slug>/. Returns (dir, doc)."""
    fixture_dir = root / slug
    fixture_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "bootstrap_schema_version": 1,
        "generator": "test",
        "candidate_username": candidate,
        "prompt_version": "2026-06-06.1",
        "jaccard_threshold": 0.75,
        "jd_count": 1,
        "per_jd": [{
            "jd_file": "jd1.txt", "run_id": "r1",
            "clarification_questions": [
                {"id": "q1", "text": "What was your scope?", "kind": "scope_probe"},
            ],
        }],
        "dedup": {
            "bullets": {"cluster_count": 2, "clusters": [
                {"representative": "Led a $5M migration", "members": ["Led a $5M migration"],
                 "jd_files": ["jd1.txt"], "size": 1},
                {"representative": "Built CI pipelines", "members": ["Built CI pipelines"],
                 "jd_files": ["jd1.txt"], "size": 1},
            ]},
            "skills": {"cluster_count": 1, "clusters": [
                {"representative": "Python", "members": ["Python"], "jd_files": ["jd1.txt"], "size": 1},
            ]},
        },
        "grounding_signals": None,
    }
    (fixture_dir / "bootstrap.json").write_text(json.dumps(doc), encoding="utf-8")
    return fixture_dir, doc


def _complete_doc(ann_app, slug="alice-bootstrap"):
    """Build a fully-annotated (validate-passing) doc from the seeded bootstrap."""
    from evals.annotation import build_annotation_template

    bootstrap = json.loads(
        (ann_app.ANNOTATION_ROOT / slug / "bootstrap.json").read_text(encoding="utf-8"),
    )
    doc = build_annotation_template(bootstrap)
    for item in doc["bullets"]:
        item["verdict"] = "keep"
    for item in doc["skills"]:
        item["verdict"] = "keep"
    return doc


# --- list ------------------------------------------------------------------

class TestFixturesList:
    def test_lists_seeded_bootstrap(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixtures")
        assert resp.status_code == 200
        fixtures = resp.get_json()["fixtures"]
        assert len(fixtures) == 1
        f = fixtures[0]
        assert f["slug"] == "alice-bootstrap"
        assert f["candidate_username"] == "alice"
        assert f["bullet_clusters"] == 2
        assert f["skill_clusters"] == 1
        assert f["has_annotations"] is False

    def test_empty_when_no_fixtures(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixtures")
        assert resp.status_code == 200
        assert resp.get_json()["fixtures"] == []

    def test_localhost_guard_blocks_remote_host(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixtures", headers={"Host": "evil.example"})
        assert resp.status_code == 403


# --- load ------------------------------------------------------------------

class TestLoad:
    def test_returns_template_when_no_annotations(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixture/alice/alice-bootstrap")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["has_annotations"] is False
        assert len(body["annotations"]["bullets"]) == 2
        assert len(body["annotations"]["skills"]) == 1
        assert body["annotations"]["bullets"][0]["verdict"] is None
        assert "keep" in body["vocab"]["verdicts"]
        assert "invented_metric" in body["vocab"]["failed_rules"]

    def test_returns_existing_annotations(self, ann_app):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        doc = _complete_doc(ann_app)
        (fixture_dir / "annotations.json").write_text(json.dumps(doc), encoding="utf-8")
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixture/alice/alice-bootstrap")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["has_annotations"] is True
        assert body["annotations"]["bullets"][0]["verdict"] == "keep"

    def test_unknown_user_rejected(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixture/nobody/alice-bootstrap")
        assert resp.status_code == 400

    def test_missing_bootstrap_404(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.get("/api/annotation/fixture/alice/does-not-exist")
        assert resp.status_code == 404


# --- save (fail-closed) ----------------------------------------------------

class TestSave:
    def test_rejects_incomplete_template(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        from evals.annotation import build_annotation_template
        bootstrap = json.loads(
            (ann_app.ANNOTATION_ROOT / "alice-bootstrap" / "bootstrap.json").read_text(encoding="utf-8"),
        )
        template = build_annotation_template(bootstrap)  # verdicts all None
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap", json=template)
        assert resp.status_code == 400
        body = resp.get_json()
        assert "validation" in body["error"].lower()
        assert "verdict" in body["detail"]
        # Nothing was written.
        assert not (ann_app.ANNOTATION_ROOT / "alice-bootstrap" / "annotations.json").exists()

    def test_accepts_complete_and_writes(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        doc = _complete_doc(ann_app)
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap", json=doc)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        out = ann_app.ANNOTATION_ROOT / "alice-bootstrap" / "annotations.json"
        assert out.exists()
        # Round-trips through the canonical validator.
        from evals.annotation import load_annotations
        load_annotations(out)

    def test_rejects_fabricated_without_pattern(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        doc = _complete_doc(ann_app)
        doc["bullets"][0]["verdict"] = "fabricated"  # no forbidden_pattern
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap", json=doc)
        assert resp.status_code == 400
        assert "forbidden_pattern" in resp.get_json()["detail"]

    def test_unknown_user_rejected(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        doc = _complete_doc(ann_app)
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/nobody/alice-bootstrap", json=doc)
        assert resp.status_code == 400


# --- collate ---------------------------------------------------------------

class TestCollate:
    def test_requires_saved_annotations(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/collate")
        assert resp.status_code == 400
        assert "Save annotations" in resp.get_json()["error"]

    def test_produces_expected_and_brief(self, ann_app):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        # One fabricated bullet → a forbidden_invention; skills kept → must_keywords.
        doc = _complete_doc(ann_app)
        doc["bullets"][0]["verdict"] = "fabricated"
        doc["bullets"][0]["forbidden_pattern"] = r"\$5M\b"
        doc["bullets"][0]["failed_rules"] = ["invented_metric"]
        (fixture_dir / "annotations.json").write_text(json.dumps(doc), encoding="utf-8")
        # The anchor JD the wrapper would have saved.
        (fixture_dir / "jds").mkdir()
        (fixture_dir / "jds" / "jd1.txt").write_text("Senior PM JD body.", encoding="utf-8")

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/collate")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["must_keywords"] == 1          # "Python"
        assert body["forbidden_inventions"] == 1   # \$5M\b
        assert body["jd_written"] is True
        assert (fixture_dir / "expected.json").exists()
        assert (fixture_dir / "improvement_brief.md").exists()
        assert (fixture_dir / "jd.txt").read_text(encoding="utf-8") == "Senior PM JD body."
        expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))
        # collate_expected lowercases skill keywords (case-insensitive coverage).
        assert "python" in expected["must_keywords"]
        assert r"\$5M\b" in expected["forbidden_inventions"]


# --- path containment helpers ----------------------------------------------

class TestContainment:
    def test_fixture_path_sanitizes_traversal(self, ann_app):
        # secure_filename neutralizes traversal; the result stays under ANNOTATION_ROOT.
        path = ann_app._annotation_fixture_path("../../etc")
        assert path is not None
        assert ann_app._within(path, ann_app.ANNOTATION_ROOT)

    def test_fixture_path_empty_slug_is_none(self, ann_app):
        assert ann_app._annotation_fixture_path("") is None
        assert ann_app._annotation_fixture_path("///") is None

    def test_within_rejects_escape(self, ann_app):
        outside = ann_app.ANNOTATION_ROOT.parent / "elsewhere"
        assert ann_app._within(outside, ann_app.ANNOTATION_ROOT) is False


# --- bootstrap SSE (LLM stubbed) -------------------------------------------

class TestBootstrapStream:
    def test_writes_bootstrap_from_stubbed_pipeline(self, ann_app, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # client construct only; never called

        def _fake_pipeline(client, session, username, jds, *, progress=None):
            per_jd = []
            for i, (name, _text) in enumerate(jds):
                if progress:
                    progress("jd_start", {"jd_file": name, "index": i, "total": len(jds)})
                    progress("jd_done", {"jd_file": name, "index": i, "total": len(jds),
                                         "bullets": 1, "skills": 1, "questions": 0})
                per_jd.append({
                    "jd_file": name, "run_id": f"run{i}", "analysis": {},
                    "clarification_questions": [], "clarification_reasoning": "",
                    "generated_resume": "", "generated_cover_letter": "",
                    "bullets": [f"Did {name} work"], "skills": ["Python"],
                })
            return per_jd, "corpus source text"

        import evals.bootstrap as bootstrap_mod
        monkeypatch.setattr(bootstrap_mod, "run_pipeline_over_jd_texts", _fake_pipeline)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/bootstrap", json={
            "username": "alice",
            "jds": [{"name": "kafka backend", "text": "JD one"},
                    {"name": "frontend", "text": "JD two"}],
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "event: start" in body
        assert "event: done" in body
        assert "event: error" not in body

        fixture_dir = ann_app.ANNOTATION_ROOT / "alice-bootstrap"
        bootstrap_doc = json.loads((fixture_dir / "bootstrap.json").read_text(encoding="utf-8"))
        assert bootstrap_doc["jd_count"] == 2
        assert bootstrap_doc["candidate_username"] == "alice"
        # Pasted JDs persisted for later collate → jd.txt.
        assert (fixture_dir / "jds" / "kafka_backend.txt").exists()

    def test_rejects_empty_jds(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/bootstrap", json={"username": "alice", "jds": []})
        assert resp.status_code == 400

    def test_rejects_unknown_user(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/bootstrap", json={
            "username": "nobody", "jds": [{"name": "x", "text": "y"}],
        })
        assert resp.status_code == 400


# --- grounding scorers (models stubbed; no transformers/minicheck download) --

# A minimal but valid seed_schema_version-1 corpus snapshot for `alice`. The score
# route imports this into a throwaway in-memory SQLite and synthesizes the résumé
# text it scores against, so a fixture only needs a bootstrap.json + this seed.json.
_SEED = {
    "seed_schema_version": 1,
    "generator": "test",
    "candidate_username": "alice",
    "candidate": {
        "username": "alice", "name": "Alice Lee", "email": None, "phone": None,
        "linkedin_url": None, "website_url": None, "notes": None, "profile_text": None,
    },
    "tags": [],
    "experiences": [{
        "id": 1, "company": "Acme", "location": None, "start_date": "2020",
        "end_date": "2023", "display_order": 0, "summary": None,
        "titles": [{
            "id": 1, "title": "Engineer", "is_official": True,
            "truthful_enough_to_use": True, "is_pending_review": False,
            "source": "user", "tag_links": [],
        }],
        "bullets": [
            {"id": 1, "text": "Led a $5M migration", "display_order": 0,
             "is_active": True, "is_pending_review": False, "source": "user",
             "pattern_kind": None, "has_outcome": True, "tag_links": []},
            {"id": 2, "text": "Built CI pipelines", "display_order": 1,
             "is_active": True, "is_pending_review": False, "source": "user",
             "pattern_kind": None, "has_outcome": False, "tag_links": []},
        ],
    }],
    "summary_items": [],
    "skills": [{"id": 1, "name": "Python", "category": None, "proficiency": None, "years": None}],
    "educations": [],
    "certifications": [],
}


def _write_seed(fixture_dir):
    (fixture_dir / "seed.json").write_text(json.dumps(_SEED), encoding="utf-8")


def _fake_scorer(resume_md, source_texts):
    """Stand-in for evals.grounding_signals.run_grounding_signals — same output
    shape, no model download. Bullets are the `- ` lines of the rendered reps."""
    bullets = [ln[2:].strip() for ln in resume_md.splitlines() if ln.strip().startswith("- ")]
    return {
        "bullet_count": len(bullets),
        "nli": [{"bullet": b, "nli_entailment_score": 0.9, "nli_contradiction_flag": False}
                for b in bullets],
        "nli_summary": {"mean_entailment": 0.9, "contradiction_count": 0},
        "minicheck": [{"bullet": b, "minicheck_grounding_score": 0.8} for b in bullets],
        "minicheck_summary": {"mean_score": 0.8, "low_score_count": 0},
    }


class TestScoreGrounding:
    def test_scores_and_writes_grounding_signals(self, ann_app, monkeypatch):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        _write_seed(fixture_dir)
        monkeypatch.setattr("evals.grounding_signals.run_grounding_signals", _fake_scorer)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/score")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "event: start" in body
        assert "event: done" in body
        assert "event: error" not in body

        doc = json.loads((fixture_dir / "bootstrap.json").read_text(encoding="utf-8"))
        gs = doc["grounding_signals"]
        assert gs is not None
        assert gs["bullet_count"] == 2
        assert len(gs["nli"]) == 2                       # index-aligned to the 2 clusters
        assert gs["nli"][0]["nli_entailment_score"] == 0.9

    def test_patches_existing_annotations_without_clobbering_verdicts(self, ann_app, monkeypatch):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        _write_seed(fixture_dir)
        doc = _complete_doc(ann_app)               # null pre-scores + verdict=keep
        doc["bullets"][0]["note"] = "human note"
        (fixture_dir / "annotations.json").write_text(json.dumps(doc), encoding="utf-8")
        monkeypatch.setattr("evals.grounding_signals.run_grounding_signals", _fake_scorer)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/score")
        assert resp.status_code == 200
        # Consume the SSE stream so the generator runs to completion (the file
        # writes happen inside it; the Flask test client is lazy otherwise).
        assert "event: done" in resp.get_data(as_text=True)

        patched = json.loads((fixture_dir / "annotations.json").read_text(encoding="utf-8"))
        # Scores patched in by cluster_index…
        assert patched["bullets"][0]["minicheck_grounding_score"] == 0.8
        assert patched["bullets"][0]["nli_entailment_score"] == 0.9
        # …without touching the human's verdict / note.
        assert patched["bullets"][0]["verdict"] == "keep"
        assert patched["bullets"][0]["note"] == "human note"

    def test_no_seed_returns_409(self, ann_app):
        _seed_bootstrap(ann_app.ANNOTATION_ROOT)   # no seed.json written
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/score")
        assert resp.status_code == 409
        assert "seed.json" in resp.get_json()["error"]

    def test_missing_extras_streams_install_message(self, ann_app, monkeypatch):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        _write_seed(fixture_dir)

        def _raise_import(*_a, **_k):
            raise ImportError("transformers is required for NLI scoring.")
        monkeypatch.setattr("evals.grounding_signals.run_grounding_signals", _raise_import)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/alice-bootstrap/score")
        assert resp.status_code == 200            # SSE; the error rides in the stream
        body = resp.get_data(as_text=True)
        assert "event: error" in body
        assert "not installed" in body
        # bootstrap.json left un-scored.
        doc = json.loads((fixture_dir / "bootstrap.json").read_text(encoding="utf-8"))
        assert doc["grounding_signals"] is None

    def test_missing_bootstrap_404(self, ann_app):
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/alice/does-not-exist/score")
        assert resp.status_code == 404

    def test_unknown_user_rejected(self, ann_app):
        fixture_dir, _ = _seed_bootstrap(ann_app.ANNOTATION_ROOT)
        _write_seed(fixture_dir)
        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/fixture/nobody/alice-bootstrap/score")
        assert resp.status_code == 400


class TestBootstrapGrounding:
    """The bootstrap route's opt-in grounding pass (scorer stubbed)."""

    @staticmethod
    def _stub_pipeline(monkeypatch):
        def _fake_pipeline(client, session, username, jds, *, progress=None):
            return ([{
                "jd_file": n, "run_id": f"r{i}", "analysis": {},
                "clarification_questions": [], "clarification_reasoning": "",
                "generated_resume": "", "generated_cover_letter": "",
                "bullets": [f"Did {n} work"], "skills": ["Python"],
            } for i, (n, _t) in enumerate(jds)], "corpus source text")
        import evals.bootstrap as bootstrap_mod
        monkeypatch.setattr(bootstrap_mod, "run_pipeline_over_jd_texts", _fake_pipeline)

    def test_optin_scores_bootstrap(self, ann_app, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        self._stub_pipeline(monkeypatch)
        monkeypatch.setattr("evals.grounding_signals.run_grounding_signals", _fake_scorer)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/bootstrap", json={
            "username": "alice",
            "jds": [{"name": "kafka", "text": "JD one"}],
            "grounding_signals": True,
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "event: done" in body
        assert "event: error" not in body
        doc = json.loads(
            (ann_app.ANNOTATION_ROOT / "alice-bootstrap" / "bootstrap.json").read_text(encoding="utf-8"),
        )
        assert doc["grounding_signals"] is not None

    def test_optin_degrades_when_extras_missing(self, ann_app, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        self._stub_pipeline(monkeypatch)

        def _raise_import(*_a, **_k):
            raise ImportError("transformers is required.")
        monkeypatch.setattr("evals.grounding_signals.run_grounding_signals", _raise_import)

        client = ann_app.app.test_client()
        resp = client.post("/api/annotation/bootstrap", json={
            "username": "alice",
            "jds": [{"name": "kafka", "text": "JD one"}],
            "grounding_signals": True,
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Degrades: non-fatal warning, the bootstrap still completes.
        assert "event: warning" in body
        assert "not installed" in body
        assert "event: done" in body
        doc = json.loads(
            (ann_app.ANNOTATION_ROOT / "alice-bootstrap" / "bootstrap.json").read_text(encoding="utf-8"),
        )
        assert doc["grounding_signals"] is None
