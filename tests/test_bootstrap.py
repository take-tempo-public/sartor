"""Tests for the corpus bootstrap engine (evals/bootstrap).

LLM-free. The deterministic collation (token normalization, Jaccard dedup, skills
extraction, document assembly, write-path guard) is tested directly. The pipeline
orchestrator is exercised against a REAL `seeded_session` (the seed produced by
the genuine `scripts.export_corpus_seed.export_seed`, as the seed-import tests do)
with `analyze`/`clarify`/`generate` monkeypatched to canned dicts — so the wiring
is covered with zero paid LLM calls.
"""

from __future__ import annotations

import anthropic
import pytest
from werkzeug.utils import secure_filename

from evals import bootstrap
from evals.seed_import import seeded_session
from scripts.export_corpus_seed import export_seed

# A generated résumé with the section shapes the extractors walk: `- ` bullets
# under Experience and a comma-list Skills section bounded by `##` headings.
RESUME_MD = """# Jordan Park

## Experience

### Acme Corp, Senior Engineer 2020 — Present
- Led migration of the billing platform to Kubernetes.
- Cut p99 latency by improving caching.

## Skills

Python, Kubernetes, Go

## Education

- State University
"""


def _seed_candidate(session) -> None:
    """Insert a minimal candidate sufficient for build_context_set_from_db to
    synthesize a non-empty corpus résumé (one experience + official title + active
    bullets + a skill)."""
    from db.models import Bullet, Candidate, Experience, ExperienceTitle, Skill

    c = Candidate(
        username="alex", name="Alex Chen", email="alex@example.com",
        phone="555-0100", linkedin_url=None, website_url=None,
        notes=None, profile_text="Platform SRE.",
    )
    session.add(c)
    session.flush()

    e = Experience(
        candidate_id=c.id, company="Polaris", location="Remote",
        start_date="2022-09", end_date=None, display_order=0, summary="Backend.",
    )
    session.add(e)
    session.flush()

    session.add(ExperienceTitle(
        experience_id=e.id, title="Senior SRE", is_official=1,
        truthful_enough_to_use=1, is_pending_review=0, source="official",
    ))
    session.add_all([
        Bullet(
            experience_id=e.id, text="Cut p99 latency 40%.", display_order=0,
            is_active=1, is_pending_review=0, source="primary:r.md",
            pattern_kind=None, has_outcome=1,
        ),
        Bullet(
            experience_id=e.id, text="Ran incident response for Kafka pipelines.",
            display_order=1, is_active=1, is_pending_review=0, source="primary:r.md",
            pattern_kind=None, has_outcome=0,
        ),
    ])
    session.add(Skill(
        candidate_id=c.id, name="Python", category="language",
        proficiency="expert", years=6.0,
    ))
    session.commit()


class TestJaccard:
    def test_identical_sets_are_one(self) -> None:
        a = frozenset({"led", "migration", "kubernetes"})
        assert bootstrap._jaccard(a, a) == 1.0

    def test_disjoint_sets_are_zero(self) -> None:
        a = frozenset({"led", "migration"})
        b = frozenset({"mentored", "engineers"})
        assert bootstrap._jaccard(a, b) == 0.0

    def test_both_empty_is_zero(self) -> None:
        assert bootstrap._jaccard(frozenset(), frozenset()) == 0.0

    def test_partial_overlap(self) -> None:
        a = frozenset({"a", "b", "c"})
        b = frozenset({"b", "c", "d"})
        # |∩| = 2, |∪| = 4
        assert bootstrap._jaccard(a, b) == pytest.approx(0.5)

    def test_normalize_drops_short_tokens_and_lowercases(self) -> None:
        toks = bootstrap._normalize_tokens("Led TO the KubernetesX of")
        # "to"/"of" (len 2) dropped; rest lowercased
        assert toks == frozenset({"led", "the", "kubernetesx"})


class TestDedupTexts:
    def test_near_identical_bullets_cluster_across_jds(self) -> None:
        items = [
            ("a.txt", "Led migration of the billing platform to Kubernetes"),
            ("b.txt", "Led migration of the billing platform to Kubernetes clusters"),
            ("b.txt", "Mentored five junior engineers on incident response"),
        ]
        clusters = bootstrap.dedup_texts(items, 0.75)
        assert len(clusters) == 2

        big = clusters[0]
        assert big["representative"] == items[0][1]
        assert big["size"] == 2
        assert big["jd_files"] == ["a.txt", "b.txt"]

        lone = clusters[1]
        assert lone["size"] == 1
        assert lone["jd_files"] == ["b.txt"]

    def test_threshold_keeps_below_cutoff_apart(self) -> None:
        items = [
            ("a.txt", "Led migration of the billing platform to Kubernetes"),
            ("b.txt", "Led migration of the billing platform to Kubernetes clusters"),
        ]
        # Jaccard ≈ 0.857; a 0.9 threshold must NOT merge them.
        clusters = bootstrap.dedup_texts(items, 0.9)
        assert len(clusters) == 2

    def test_same_jd_contributes_once_to_jd_files(self) -> None:
        items = [
            ("a.txt", "Led migration of the billing platform to Kubernetes"),
            ("a.txt", "Led migration of the billing platform to Kubernetes now"),
        ]
        clusters = bootstrap.dedup_texts(items, 0.75)
        assert len(clusters) == 1
        assert clusters[0]["size"] == 2
        assert clusters[0]["jd_files"] == ["a.txt"]

    def test_empty_input(self) -> None:
        assert bootstrap.dedup_texts([], 0.75) == []


class TestExtractSkills:
    def test_comma_list(self) -> None:
        assert bootstrap._extract_skills(RESUME_MD) == ["Python", "Kubernetes", "Go"]

    def test_bullet_list_and_dedup(self) -> None:
        md = "## Skills\n- Python\n- Go, Rust\n- python\n## Next\n- ignored"
        assert bootstrap._extract_skills(md) == ["Python", "Go", "Rust"]

    def test_bold_heading(self) -> None:
        md = "**Skills**\nGo, Rust\n**Experience**\n- not a skill"
        assert bootstrap._extract_skills(md) == ["Go", "Rust"]

    def test_no_skills_section(self) -> None:
        assert bootstrap._extract_skills("## Experience\n- did a thing") == []


class TestBuildBootstrapDocument:
    def _per_jd(self) -> list[dict]:
        return [
            {
                "jd_file": "a.txt", "run_id": "r1", "analysis": {"x": 1},
                "clarification_questions": [], "clarification_reasoning": "",
                "generated_resume": "", "generated_cover_letter": "",
                "bullets": ["Led migration to Kubernetes", "Cut latency by improving caching"],
                "skills": ["Python", "Go"],
            },
            {
                "jd_file": "b.txt", "run_id": "r2", "analysis": {"x": 2},
                "clarification_questions": [], "clarification_reasoning": "",
                "generated_resume": "", "generated_cover_letter": "",
                "bullets": ["Led migration to Kubernetes clusters", "Built HIPAA-compliant pipeline"],
                "skills": ["Python", "Rust"],
            },
        ]

    def test_schema_and_dedup_counts(self) -> None:
        doc = bootstrap.build_bootstrap_document(
            self._per_jd(), username="alex", seed_path="seed.json",
            threshold=0.75, corpus_source="CORPUS", grounding_fn=None,
        )
        assert doc["bootstrap_schema_version"] == bootstrap.BOOTSTRAP_SCHEMA_VERSION
        assert doc["generator"] == "evals/bootstrap.py"
        assert {
            "bootstrap_schema_version", "generator", "generated_at",
            "candidate_username", "seed_path", "prompt_version",
            "jaccard_threshold", "jd_count", "per_jd", "dedup", "grounding_signals",
        }.issubset(doc.keys())
        assert doc["jd_count"] == 2
        assert doc["candidate_username"] == "alex"
        # "Led migration…" pair clusters (size 2); the two others are size 1 each.
        assert doc["dedup"]["bullets"]["cluster_count"] == 3
        # "Python" appears in both JDs (exact dup → one cluster); Go + Rust separate.
        assert doc["dedup"]["skills"]["cluster_count"] == 3
        assert doc["grounding_signals"] is None

    def test_grounding_fn_runs_over_dedup_representatives(self) -> None:
        calls: list[tuple[str, list[str]]] = []

        def fake_grounding(resume_md: str, sources: list[str]) -> dict:
            calls.append((resume_md, sources))
            return {"bullet_count": 3, "sentinel": True}

        doc = bootstrap.build_bootstrap_document(
            self._per_jd(), username="alex", seed_path="seed.json",
            threshold=0.75, corpus_source="CORPUS", grounding_fn=fake_grounding,
        )
        assert doc["grounding_signals"] == {"bullet_count": 3, "sentinel": True}
        assert len(calls) == 1
        md, sources = calls[0]
        assert sources == ["CORPUS"]
        # representatives rendered as a `- ` markdown list, one per bullet cluster
        assert "- Led migration to Kubernetes" in md
        assert len([ln for ln in md.splitlines() if ln.startswith("- ")]) == 3


class TestPipelineOrchestration:
    def _patch_pipeline(self, monkeypatch, *, clarify_raises: bool = False) -> None:
        def fake_analyze(client, context, **kw) -> dict:
            return {"essential_skills": ["python"], "overall_strategy": "lead with reliability"}

        def fake_clarify(client, context, analysis, **kw) -> dict:
            if clarify_raises:
                raise RuntimeError("boom")
            return {
                "questions": [{"id": "q1", "text": "Tell me about X", "kind": "experience_probe"}],
                "reasoning": "r",
            }

        def fake_generate(client, context, analysis, **kw) -> dict:
            return {"resume_content": RESUME_MD, "cover_letter_content": "Dear team,"}

        monkeypatch.setattr(bootstrap, "analyze", fake_analyze)
        monkeypatch.setattr(bootstrap, "clarify", fake_clarify)
        monkeypatch.setattr(bootstrap, "generate", fake_generate)

    def test_orchestrator_wiring(self, db_session, monkeypatch, tmp_path) -> None:
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        self._patch_pipeline(monkeypatch)

        jd_a = tmp_path / "kafka.txt"
        jd_a.write_text("Kafka backend role", encoding="utf-8")
        jd_b = tmp_path / "frontend.jd"
        jd_b.write_text("Frontend role", encoding="utf-8")

        client = anthropic.Anthropic(api_key="test-key")
        with seeded_session(seed) as (session, username):
            per_jd, corpus_source = bootstrap.run_pipeline_over_jds(
                client, session, username, [jd_a, jd_b],
            )

        assert len(per_jd) == 2
        assert [r["jd_file"] for r in per_jd] == ["kafka.txt", "frontend.jd"]
        assert all(r["run_id"] for r in per_jd)
        assert "Led migration of the billing platform to Kubernetes." in per_jd[0]["bullets"]
        assert per_jd[0]["skills"] == ["Python", "Kubernetes", "Go"]
        assert per_jd[0]["clarification_questions"][0]["kind"] == "experience_probe"
        assert per_jd[0]["analysis"]["essential_skills"] == ["python"]
        # corpus source captured once from the synthesized résumé (one seed)
        assert "Polaris" in corpus_source

    def test_clarify_failure_is_non_fatal(self, db_session, monkeypatch, tmp_path) -> None:
        _seed_candidate(db_session)
        seed = export_seed(db_session, candidate_username="alex")
        self._patch_pipeline(monkeypatch, clarify_raises=True)

        jd = tmp_path / "role.txt"
        jd.write_text("Some role", encoding="utf-8")

        client = anthropic.Anthropic(api_key="test-key")
        with seeded_session(seed) as (session, username):
            per_jd, _src = bootstrap.run_pipeline_over_jds(client, session, username, [jd])

        assert len(per_jd) == 1
        assert per_jd[0]["clarification_questions"] == []
        # generate still ran despite the clarify failure
        assert per_jd[0]["bullets"]


class TestWritePathGuard:
    def test_default_path_under_allowed_root(self) -> None:
        p = bootstrap._resolve_output_path("alex", None)
        assert p == (bootstrap.ALLOWED_ROOT / "alex" / "bootstrap.json").resolve()

    def test_out_within_allowed_root_ok(self) -> None:
        target = bootstrap.ALLOWED_ROOT / "alex" / "custom.json"
        assert bootstrap._resolve_output_path("alex", str(target)) == target.resolve()

    def test_out_outside_allowed_root_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="refusing to write outside"):
            bootstrap._resolve_output_path("alex", str(tmp_path / "leak.json"))

    def test_empty_sanitized_username_raises(self) -> None:
        assert secure_filename("..") == ""  # precondition for the guard below
        with pytest.raises(ValueError, match="sanitizes to empty"):
            bootstrap._resolve_output_path("..", None)
