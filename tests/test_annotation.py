"""Tests for the eval annotation contract (evals/annotation).

LLM-free. The schema validator (fail-closed on version/shape/verdict drift), the
bootstrap.json → blank-template emitter, the deterministic collation
(annotations.json → expected.json fixture + improvement brief), and the
write-path guard are all tested directly against hand-built bootstrap/annotation
dicts. No paid LLM calls, no model downloads. Mirrors tests/test_seed_import.py
and tests/test_bootstrap.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from werkzeug.utils import secure_filename

from evals import annotation

# ---------------------------------------------------------------------------
# Fixtures — a realistic bootstrap.json and a completed annotations.json.
# ---------------------------------------------------------------------------


def _bootstrap_doc() -> dict:
    """A bootstrap document with 4 bullet clusters, 3 skill clusters, grounding
    pre-scores aligned by index, and 2 clarification questions across 2 JDs.

    Cluster jd_files spans: a.txt in bullet clusters 0/2/3 (count 3); b.txt in
    0/1 (count 2). So pick_anchor_jd → "a.txt" by count (not just tie-break).
    """
    bullet_clusters = [
        {
            "representative": "Led migration of billing platform to Kubernetes",
            "members": ["..."],
            "jd_files": ["a.txt", "b.txt"],
            "size": 2,
        },
        {
            "representative": "Built HIPAA-compliant claims pipeline",
            "members": ["..."],
            "jd_files": ["b.txt"],
            "size": 1,
        },
        {
            "representative": "Cut p99 latency by improving caching",
            "members": ["..."],
            "jd_files": ["a.txt"],
            "size": 1,
        },
        {
            "representative": "Mentored two engineers",
            "members": ["..."],
            "jd_files": ["a.txt"],
            "size": 1,
        },
    ]
    skill_clusters = [
        {
            "representative": "Python",
            "members": ["Python"],
            "jd_files": ["a.txt", "b.txt"],
            "size": 2,
        },
        {
            "representative": "Kubernetes",
            "members": ["Kubernetes"],
            "jd_files": ["a.txt"],
            "size": 1,
        },
        {"representative": "FHIR", "members": ["FHIR"], "jd_files": ["b.txt"], "size": 1},
    ]
    grounding = {
        "bullet_count": 4,
        "nli": [
            {
                "bullet": "Led migration of billing platform to Kubernetes",
                "nli_entailment_score": 0.88,
                "nli_contradiction_flag": False,
            },
            {
                "bullet": "Built HIPAA-compliant claims pipeline",
                "nli_entailment_score": 0.12,
                "nli_contradiction_flag": True,
            },
            {
                "bullet": "Cut p99 latency by improving caching",
                "nli_entailment_score": 0.75,
                "nli_contradiction_flag": False,
            },
            {
                "bullet": "Mentored two engineers",
                "nli_entailment_score": 0.66,
                "nli_contradiction_flag": False,
            },
        ],
        "nli_summary": {"mean_entailment": 0.60, "contradiction_count": 1},
        "minicheck": [
            {
                "bullet": "Led migration of billing platform to Kubernetes",
                "minicheck_grounding_score": 0.95,
            },
            {"bullet": "Built HIPAA-compliant claims pipeline", "minicheck_grounding_score": 0.80},
            {"bullet": "Cut p99 latency by improving caching", "minicheck_grounding_score": 0.70},
            {"bullet": "Mentored two engineers", "minicheck_grounding_score": 0.85},
        ],
        "minicheck_summary": {"mean_score": 0.825, "low_score_count": 0},
    }
    return {
        "bootstrap_schema_version": 1,
        "generator": "evals/bootstrap.py",
        "generated_at": "2026-06-02T00:00:00+00:00",
        "candidate_username": "alex",
        "seed_path": "evals/fixtures/real/alex/seed.json",
        "prompt_version": "2026-06-01.4",
        "jaccard_threshold": 0.75,
        "jd_count": 2,
        "per_jd": [
            {
                "jd_file": "a.txt",
                "run_id": "r1",
                "analysis": {},
                "clarification_questions": [
                    {"id": "q1", "text": "Tell me about X", "kind": "experience_probe"}
                ],
                "clarification_reasoning": "",
                "generated_resume": "",
                "generated_cover_letter": "",
                "bullets": [],
                "skills": [],
            },
            {
                "jd_file": "b.txt",
                "run_id": "r2",
                "analysis": {},
                "clarification_questions": [
                    {"id": "q2", "text": "What are your strengths?", "kind": "scope_probe"}
                ],
                "clarification_reasoning": "",
                "generated_resume": "",
                "generated_cover_letter": "",
                "bullets": [],
                "skills": [],
            },
        ],
        "dedup": {
            "bullets": {"cluster_count": len(bullet_clusters), "clusters": bullet_clusters},
            "skills": {"cluster_count": len(skill_clusters), "clusters": skill_clusters},
        },
        "grounding_signals": grounding,
    }


def _annotations_doc() -> dict:
    """A completed, valid annotations.json keyed to _bootstrap_doc()'s clusters."""
    return {
        "annotation_schema_version": 1,
        "bootstrap_source": "evals/fixtures/real/alex/bootstrap.json",
        "candidate_username": "alex",
        "prompt_version": "2026-06-01.4",
        "bullets": [
            {
                "cluster_index": 0,
                "representative": "Led migration of billing platform to Kubernetes",
                "jd_files": ["a.txt", "b.txt"],
                "size": 2,
                "nli_entailment_score": 0.88,
                "nli_contradiction_flag": False,
                "minicheck_grounding_score": 0.95,
                "verdict": "keep",
                "failed_rules": [],
                "note": "",
                "should_omit": False,
                "honest_rewrite": None,
                "forbidden_pattern": None,
            },
            {
                "cluster_index": 1,
                "representative": "Built HIPAA-compliant claims pipeline",
                "jd_files": ["b.txt"],
                "size": 1,
                "nli_entailment_score": 0.12,
                "nli_contradiction_flag": True,
                "minicheck_grounding_score": 0.80,
                "verdict": "fabricated",
                "failed_rules": ["jd_pandering"],
                "note": "Source has no healthcare work; re-skinned for the b.txt JD.",
                "should_omit": True,
                "honest_rewrite": None,
                "forbidden_pattern": "HIPAA",
            },
            {
                "cluster_index": 2,
                "representative": "Cut p99 latency by improving caching",
                "jd_files": ["a.txt"],
                "size": 1,
                "nli_entailment_score": 0.75,
                "nli_contradiction_flag": False,
                "minicheck_grounding_score": 0.70,
                "verdict": "fix",
                "failed_rules": ["scope_inflation"],
                "note": "Quantify honestly.",
                "should_omit": False,
                "honest_rewrite": "Reduced p99 latency by adding a read-through cache",
                "forbidden_pattern": None,
            },
            {
                "cluster_index": 3,
                "representative": "Mentored two engineers",
                "jd_files": ["a.txt"],
                "size": 1,
                "nli_entailment_score": 0.66,
                "nli_contradiction_flag": False,
                "minicheck_grounding_score": 0.85,
                "verdict": "omit",
                "failed_rules": [],
                "note": "Redundant with the summary.",
                "should_omit": True,
                "honest_rewrite": None,
                "forbidden_pattern": None,
            },
        ],
        "skills": [
            {
                "cluster_index": 0,
                "representative": "Python",
                "jd_files": ["a.txt", "b.txt"],
                "size": 2,
                "nli_entailment_score": None,
                "nli_contradiction_flag": None,
                "minicheck_grounding_score": None,
                "verdict": "keep",
                "failed_rules": [],
                "note": "",
                "should_omit": False,
                "honest_rewrite": None,
                "forbidden_pattern": None,
            },
            {
                "cluster_index": 1,
                "representative": "Kubernetes",
                "jd_files": ["a.txt"],
                "size": 1,
                "nli_entailment_score": None,
                "nli_contradiction_flag": None,
                "minicheck_grounding_score": None,
                "verdict": "keep",
                "failed_rules": [],
                "note": "",
                "should_omit": False,
                "honest_rewrite": None,
                "forbidden_pattern": None,
            },
            {
                "cluster_index": 2,
                "representative": "FHIR",
                "jd_files": ["b.txt"],
                "size": 1,
                "nli_entailment_score": None,
                "nli_contradiction_flag": None,
                "minicheck_grounding_score": None,
                "verdict": "fabricated",
                "failed_rules": ["jd_pandering"],
                "note": "No FHIR exposure in source.",
                "should_omit": True,
                "honest_rewrite": None,
                "forbidden_pattern": "FHIR",
            },
        ],
        "clarification_ratings": [
            {
                "jd_file": "a.txt",
                "question_id": "q1",
                "question_text": "Tell me about X",
                "kind": "experience_probe",
                "rating": 4,
                "failed_rules": [],
                "note": "",
            },
            {
                "jd_file": "b.txt",
                "question_id": "q2",
                "question_text": "What are your strengths?",
                "kind": "scope_probe",
                "rating": 2,
                "failed_rules": ["generic_question"],
                "note": "Generic interview prompt.",
            },
        ],
        "min_scores": dict(annotation.DEFAULT_MIN_SCORES),
        "notes": "Annotator pass 1.",
    }


# ---------------------------------------------------------------------------
# Validation — fail-closed on version / shape / verdict / slug drift.
# ---------------------------------------------------------------------------


class TestValidation:
    def test_supported_versions_is_v1(self) -> None:
        assert 1 in annotation.SUPPORTED_ANNOTATION_SCHEMA_VERSIONS

    def test_accepts_valid_doc(self) -> None:
        annotation.validate_annotations(_annotations_doc())  # no raise

    def test_rejects_unsupported_version(self) -> None:
        doc = _annotations_doc()
        doc["annotation_schema_version"] = 2
        with pytest.raises(ValueError, match="annotation_schema_version"):
            annotation.validate_annotations(doc)

    def test_rejects_missing_keys(self) -> None:
        with pytest.raises(ValueError, match="missing required keys"):
            annotation.validate_annotations({"annotation_schema_version": 1})

    def test_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            annotation.validate_annotations([1, 2, 3])

    def test_rejects_unknown_verdict(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][0]["verdict"] = "maybe"
        with pytest.raises(ValueError, match="verdict must be one of"):
            annotation.validate_annotations(doc)

    def test_rejects_blank_template_verdict(self) -> None:
        # A freshly emitted template has verdict=None and is expected to fail until annotated.
        template = annotation.build_annotation_template(_bootstrap_doc())
        with pytest.raises(ValueError, match="verdict must be one of"):
            annotation.validate_annotations(template)

    def test_rejects_unknown_failed_rules_slug(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][0]["failed_rules"] = ["not_a_real_slug"]
        with pytest.raises(ValueError, match="not in the rubric vocabulary"):
            annotation.validate_annotations(doc)

    def test_accepts_parameterized_slug(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][0]["failed_rules"] = ["missing_must_keyword:python"]
        annotation.validate_annotations(doc)  # no raise — base slug is in the vocabulary

    def test_fix_without_honest_rewrite_rejected(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][2]["honest_rewrite"] = ""  # cluster 2 is the fix item
        with pytest.raises(ValueError, match="requires a non-empty honest_rewrite"):
            annotation.validate_annotations(doc)

    def test_fabricated_without_forbidden_pattern_rejected(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][1]["forbidden_pattern"] = None  # cluster 1 is fabricated
        with pytest.raises(ValueError, match="requires a non-empty forbidden_pattern"):
            annotation.validate_annotations(doc)

    def test_fabricated_with_uncompilable_regex_rejected(self) -> None:
        doc = _annotations_doc()
        doc["bullets"][1]["forbidden_pattern"] = "("  # invalid regex
        with pytest.raises(ValueError, match="not a compilable regex"):
            annotation.validate_annotations(doc)

    def test_rating_out_of_range_rejected(self) -> None:
        doc = _annotations_doc()
        doc["clarification_ratings"][0]["rating"] = 9
        with pytest.raises(ValueError, match="out of range"):
            annotation.validate_annotations(doc)

    def test_load_annotations_rejects_drift(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"annotation_schema_version": 99}), encoding="utf-8")
        with pytest.raises(ValueError, match="annotation_schema_version"):
            annotation.load_annotations(p)

    def test_load_annotations_round_trips(self, tmp_path: Path) -> None:
        p = tmp_path / "annotations.json"
        p.write_text(json.dumps(_annotations_doc()), encoding="utf-8")
        loaded = annotation.load_annotations(p)
        assert loaded["candidate_username"] == "alex"


# ---------------------------------------------------------------------------
# Template emitter — blank skeleton with grounding pre-scores joined by index.
# ---------------------------------------------------------------------------


class TestTemplate:
    def test_fills_every_cluster_and_question(self) -> None:
        t = annotation.build_annotation_template(_bootstrap_doc(), bootstrap_source="bs.json")
        assert t["annotation_schema_version"] == annotation.ANNOTATION_SCHEMA_VERSION
        assert t["bootstrap_source"] == "bs.json"
        assert t["candidate_username"] == "alex"
        assert len(t["bullets"]) == 4
        assert len(t["skills"]) == 3
        assert len(t["clarification_ratings"]) == 2
        # verdicts blank — fill-me signal
        assert all(b["verdict"] is None for b in t["bullets"])
        assert all(s["verdict"] is None for s in t["skills"])
        assert all(r["rating"] is None for r in t["clarification_ratings"])

    def test_joins_grounding_pre_scores_by_index(self) -> None:
        t = annotation.build_annotation_template(_bootstrap_doc())
        hipaa = t["bullets"][1]
        assert hipaa["representative"] == "Built HIPAA-compliant claims pipeline"
        assert hipaa["nli_entailment_score"] == 0.12
        assert hipaa["nli_contradiction_flag"] is True
        assert hipaa["minicheck_grounding_score"] == 0.80

    def test_skills_have_null_pre_scores(self) -> None:
        t = annotation.build_annotation_template(_bootstrap_doc())
        assert all(s["minicheck_grounding_score"] is None for s in t["skills"])
        assert all(s["nli_entailment_score"] is None for s in t["skills"])

    def test_null_pre_scores_when_bootstrap_had_no_grounding(self) -> None:
        bs = _bootstrap_doc()
        bs["grounding_signals"] = None
        t = annotation.build_annotation_template(bs)
        assert all(b["nli_entailment_score"] is None for b in t["bullets"])
        assert all(b["minicheck_grounding_score"] is None for b in t["bullets"])

    def test_carries_clarification_question_text(self) -> None:
        t = annotation.build_annotation_template(_bootstrap_doc())
        q = t["clarification_ratings"][0]
        assert q["jd_file"] == "a.txt"
        assert q["question_id"] == "q1"
        assert q["question_text"] == "Tell me about X"


# ---------------------------------------------------------------------------
# Collation → expected.json fixture (matches _load_fixture's field set).
# ---------------------------------------------------------------------------


class TestCollateExpected:
    def test_keep_skills_become_must_keywords(self) -> None:
        exp = annotation.collate_expected(_annotations_doc(), _bootstrap_doc())
        # keep-verdict skills: Python, Kubernetes (lowercased); FHIR is fabricated.
        assert exp["must_keywords"] == ["python", "kubernetes"]

    def test_fabricated_become_forbidden_inventions(self) -> None:
        exp = annotation.collate_expected(_annotations_doc(), _bootstrap_doc())
        # bullets first (HIPAA), then skills (FHIR); regex case preserved.
        assert exp["must_keywords"]  # sanity
        assert exp["forbidden_inventions"] == ["HIPAA", "FHIR"]

    def test_min_scores_default_to_readme_values(self) -> None:
        doc = _annotations_doc()
        del doc["min_scores"]
        exp = annotation.collate_expected(doc, _bootstrap_doc())
        assert exp["min_grounding_score"] == 4.0
        assert exp["min_tone_score"] == 3.0
        assert exp["min_clarification_quality_score"] == 4.0

    def test_min_scores_override(self) -> None:
        doc = _annotations_doc()
        doc["min_scores"]["grounding"] = 4.5
        exp = annotation.collate_expected(doc, _bootstrap_doc())
        assert exp["min_grounding_score"] == 4.5

    def test_candidate_name_and_field_set(self) -> None:
        exp = annotation.collate_expected(_annotations_doc(), _bootstrap_doc())
        assert exp["candidate_name"] == "alex"
        # Exactly the field set evals/runner.py:_load_fixture + the rubrics read.
        assert set(exp.keys()) == {
            "candidate_name",
            "must_keywords",
            "forbidden_inventions",
            "min_grounding_score",
            "min_keyword_coverage_score",
            "min_ats_format_score",
            "min_tone_score",
            "min_clarification_quality_score",
            "notes",
        }

    def test_forbidden_inventions_compile(self) -> None:
        import re

        exp = annotation.collate_expected(_annotations_doc(), _bootstrap_doc())
        for pat in exp["forbidden_inventions"]:
            re.compile(pat)  # no raise

    def test_notes_carry_annotator_text_and_provenance(self) -> None:
        exp = annotation.collate_expected(_annotations_doc(), _bootstrap_doc())
        assert "Annotator pass 1." in exp["notes"]
        assert "2026-06-01.4" in exp["notes"]  # prompt_version provenance stamp


# ---------------------------------------------------------------------------
# Collation → improvement brief (markdown).
# ---------------------------------------------------------------------------


class TestImprovementBrief:
    def test_brief_has_all_sections(self) -> None:
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        for section in (
            "## Fabrication patterns",
            "## Rewrites",
            "## Omissions",
            "## Clarification-question ratings",
            "## Scorer agreement",
        ):
            assert section in brief

    def test_fabrication_section_lists_pattern_and_slug(self) -> None:
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        assert "jd_pandering" in brief
        assert "HIPAA" in brief

    def test_rewrites_section_has_honest_rewrite(self) -> None:
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        assert "Reduced p99 latency by adding a read-through cache" in brief

    def test_omissions_section_lists_omit_items(self) -> None:
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        assert "Mentored two engineers" in brief

    def test_clarification_ratings_weakest_first(self) -> None:
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        assert "generic_question" in brief
        # the 2/5 question sorts before the 4/5 question
        assert brief.index("[2/5]") < brief.index("[4/5]")

    def test_scorer_disagreement_surfaced(self) -> None:
        # HIPAA bullet: human=fabricated but MiniCheck=0.80 (≥0.5) → flagged.
        brief = annotation.build_improvement_brief(_annotations_doc(), _bootstrap_doc())
        assert "human=`fabricated` but MiniCheck" in brief


# ---------------------------------------------------------------------------
# Anchor JD selection.
# ---------------------------------------------------------------------------


class TestPickAnchorJd:
    def test_widest_span_jd_wins(self) -> None:
        # a.txt appears in 3 bullet clusters, b.txt in 2.
        assert annotation.pick_anchor_jd(_bootstrap_doc()) == "a.txt"

    def test_override_wins(self) -> None:
        assert annotation.pick_anchor_jd(_bootstrap_doc(), override="b.txt") == "b.txt"

    def test_tie_breaks_lexicographically(self) -> None:
        bs = _bootstrap_doc()
        # a.txt in clusters {0,1}, b.txt in clusters {2,3}: both span 2 → tie → "a.txt".
        bs["dedup"]["bullets"]["clusters"] = [
            {"representative": "x", "members": ["x"], "jd_files": ["a.txt"], "size": 1},
            {"representative": "y", "members": ["y"], "jd_files": ["a.txt"], "size": 1},
            {"representative": "z", "members": ["z"], "jd_files": ["b.txt"], "size": 1},
            {"representative": "w", "members": ["w"], "jd_files": ["b.txt"], "size": 1},
        ]
        assert annotation.pick_anchor_jd(bs) == "a.txt"

    def test_falls_back_to_first_per_jd_when_no_clusters(self) -> None:
        bs = _bootstrap_doc()
        bs["dedup"]["bullets"]["clusters"] = []
        assert annotation.pick_anchor_jd(bs) == "a.txt"


# ---------------------------------------------------------------------------
# Write-path guard — refuses to emit outside evals/fixtures/real/.
# ---------------------------------------------------------------------------


class TestWritePathGuard:
    def test_template_default_beside_bootstrap(self) -> None:
        bootstrap_path = annotation.ALLOWED_ROOT / "alex" / "bootstrap.json"
        p = annotation._resolve_template_path("alex", bootstrap_path, None)
        assert p == (annotation.ALLOWED_ROOT / "alex" / "annotations.json").resolve()

    def test_guard_allows_within_root(self) -> None:
        target = annotation.ALLOWED_ROOT / "alex" / "annotations.json"
        assert annotation._guard(target) == target.resolve()

    def test_guard_rejects_outside_root(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="refusing to write outside"):
            annotation._guard(tmp_path / "leak.json")

    def test_fixture_slug_default(self) -> None:
        assert annotation._resolve_fixture_slug("alex", None) == "alex-bootstrap"

    def test_fixture_slug_explicit(self) -> None:
        assert annotation._resolve_fixture_slug("alex", "my-fixture") == "my-fixture"

    def test_fixture_slug_empty_sanitized_raises(self) -> None:
        assert secure_filename("..") == ""  # precondition
        with pytest.raises(ValueError, match="sanitizes to empty"):
            annotation._resolve_fixture_slug("..", "..")


class TestPatchGroundingScoresByText:
    """RH-1 (2026-07 e2e-run-health-review): the text-matched persistence seam
    ``patch_grounding_scores_by_text`` uses — unit-level, LLM-free, no scorer
    models involved. The end-to-end wiring into ``evals.runner.run_suite`` is
    covered by ``tests/test_eval_runner.py::TestGroundingSignalsAnnotationPersistence``.
    """

    def _doc(self, **overrides: object) -> dict:
        base = {
            "annotation_schema_version": 1,
            "bootstrap_source": "",
            "candidate_username": "alex",
            "prompt_version": "v1",
            "bullets": [
                {
                    "cluster_index": 0,
                    "representative": "Led a $5M migration",
                    "jd_files": [],
                    "size": 1,
                    "nli_entailment_score": None,
                    "nli_contradiction_flag": None,
                    "minicheck_grounding_score": None,
                    "verdict": "keep",
                    "failed_rules": [],
                    "note": "keep me",
                    "should_omit": False,
                    "honest_rewrite": None,
                    "forbidden_pattern": None,
                }
            ],
            "skills": [],
            "clarification_ratings": [],
            "min_scores": {},
            "notes": "",
        }
        base.update(overrides)
        return base

    def test_patches_by_normalized_text_match(self, tmp_path: Path) -> None:
        ann_path = tmp_path / "annotations.json"
        ann_path.write_text(json.dumps(self._doc()), encoding="utf-8")
        gs = {
            "nli": [
                {
                    "bullet": "  Led   a $5M migration ",  # extra whitespace, still matches
                    "nli_entailment_score": 0.95,
                    "nli_contradiction_flag": False,
                }
            ],
            "minicheck": [{"bullet": "led a $5m migration", "minicheck_grounding_score": 0.8}],
        }
        patched = annotation.patch_grounding_scores_by_text(ann_path, gs)
        assert patched == 1
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
        item = doc["bullets"][0]
        assert item["nli_entailment_score"] == 0.95
        assert item["minicheck_grounding_score"] == 0.8
        # Human fields untouched.
        assert item["verdict"] == "keep"
        assert item["note"] == "keep me"

    def test_unmatched_bullet_is_left_untouched(self, tmp_path: Path) -> None:
        ann_path = tmp_path / "annotations.json"
        ann_path.write_text(json.dumps(self._doc()), encoding="utf-8")
        gs = {
            "nli": [
                {
                    "bullet": "A completely different bullet",
                    "nli_entailment_score": 0.1,
                    "nli_contradiction_flag": True,
                }
            ],
            "minicheck": [],
        }
        patched = annotation.patch_grounding_scores_by_text(ann_path, gs)
        assert patched == 0
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
        assert doc["bullets"][0]["nli_entailment_score"] is None

    def test_empty_grounding_data_is_a_noop(self, tmp_path: Path) -> None:
        ann_path = tmp_path / "annotations.json"
        ann_path.write_text(json.dumps(self._doc()), encoding="utf-8")
        assert annotation.patch_grounding_scores_by_text(ann_path, None) == 0
        assert annotation.patch_grounding_scores_by_text(ann_path, {}) == 0

    def test_missing_file_is_a_noop(self, tmp_path: Path) -> None:
        assert (
            annotation.patch_grounding_scores_by_text(
                tmp_path / "does-not-exist.json",
                {"nli": [{"bullet": "x", "nli_entailment_score": 1}]},
            )
            == 0
        )

    def test_malformed_json_is_a_noop(self, tmp_path: Path) -> None:
        ann_path = tmp_path / "annotations.json"
        ann_path.write_text("not json", encoding="utf-8")
        assert (
            annotation.patch_grounding_scores_by_text(
                ann_path, {"nli": [{"bullet": "x", "nli_entailment_score": 1}]}
            )
            == 0
        )
