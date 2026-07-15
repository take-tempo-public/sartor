"""Unit tests for hardening.py — the deterministic layer.

These functions must remain LLM-free and produce stable output for given input.
"""

import contextlib
import json
import threading
import time
from pathlib import Path
from typing import ClassVar

import pytest

from hardening import (
    assemble_source_union,
    check_ats_format,
    compute_call_cost,
    compute_date_grounding,
    compute_fabricated_specifics,
    compute_grounding_overlap,
    compute_keyword_overlap,
    compute_quantification_rate,
    compute_specificity_density,
    compute_top_third_density,
    compute_verb_diversity,
    context_transaction,
    extract_company_terms,
    extract_keywords,
    save_context_set,
    strip_cover_letter_block,
    validate_config,
    write_context_atomic,
)


class TestStripCoverLetterBlock:
    """Walkthrough C3 — cover-letter text that leaked into resume_content is dropped."""

    def test_strips_from_dear_salutation_onward(self):
        md = "# Jane\n## Experience\n- Shipped V2\n\nDear Hiring Manager,\nI am excited…\nSincerely,\nJane"
        assert strip_cover_letter_block(md) == "# Jane\n## Experience\n- Shipped V2\n"

    def test_strips_to_whom_it_may_concern(self):
        md = "# Jane\n- A bullet\n\nTo Whom It May Concern:\nBody text."
        assert strip_cover_letter_block(md) == "# Jane\n- A bullet\n"

    def test_noop_on_clean_resume(self):
        md = "# Jane\n## Experience\n### Acme\n- Led a team\n- Shipped V2\n"
        assert strip_cover_letter_block(md) == md

    def test_does_not_strip_dear_inside_a_bullet(self):
        # "Dear" mid-line (not a salutation line) is left alone.
        md = "# Jane\n- Wrote to Dear Leader Corp about pricing\n"
        assert strip_cover_letter_block(md) == md

    def test_empty_input(self):
        assert strip_cover_letter_block("") == ""


class TestExtractKeywords:
    def test_returns_keywords_and_count(self):
        result = extract_keywords("Python developer building scalable APIs")
        assert "keywords" in result
        assert "total_unique" in result
        assert result["total_unique"] > 0

    def test_filters_stopwords(self):
        result = extract_keywords("the and or but in")
        assert result["keywords"] == {}

    def test_lowercases_input(self):
        result = extract_keywords("Python PYTHON python")
        assert "python" in result["keywords"]
        assert result["keywords"]["python"] == 3

    def test_top_n_caps_results(self):
        text = " ".join(f"word{i}" for i in range(100))
        result = extract_keywords(text, top_n=5)
        assert len(result["keywords"]) <= 5


class TestComputeKeywordOverlap:
    def test_identical_sets_score_one(self):
        kw = {"keywords": {"python": 3, "django": 1}}
        result = compute_keyword_overlap(kw, kw)
        assert result["match_score"] == 1.0
        assert set(result["matched"]) == {"python", "django"}
        assert result["missing_from_resume"] == []

    def test_disjoint_sets_score_zero(self):
        resume = {"keywords": {"python": 1}}
        jd = {"keywords": {"java": 1}}
        result = compute_keyword_overlap(resume, jd)
        assert result["match_score"] == 0.0
        assert result["missing_from_resume"] == ["java"]
        assert result["only_in_resume"] == ["python"]

    def test_empty_jd_does_not_divide_by_zero(self):
        result = compute_keyword_overlap({"keywords": {}}, {"keywords": {}})
        assert result["match_score"] == 0.0


class TestExtractCompanyTerms:
    def test_header_dash_line(self):
        jd = "Senior Site Reliability Engineer\nLattice Cloud — Remote (US)\n\nDuties follow."
        assert "lattice cloud" in extract_company_terms(jd)

    def test_sentence_position_pattern(self):
        jd = "About the role\nLattice Cloud runs a multi-region container platform."
        assert "lattice cloud" in extract_company_terms(jd)

    def test_about_and_at_patterns(self):
        assert "acme" in extract_company_terms("Come thrive at Acme today.")
        assert "initech" in extract_company_terms("About Initech\nWe make software.")

    def test_title_line_never_captured(self):
        jd = "Senior Site Reliability Engineer\n\nKubernetes and Prometheus daily."
        assert extract_company_terms(jd) == frozenset()

    def test_title_noun_rejected_even_with_dash(self):
        jd = "Senior SRE — Remote\n\nBody text."
        assert extract_company_terms(jd) == frozenset()

    def test_duty_proper_nouns_not_captured(self):
        jd = (
            "Platform Role\nAcme — Boston\n\n"
            "- Extend our Prometheus/Grafana stack.\n- Author Terraform modules.\n"
        )
        assert extract_company_terms(jd) == frozenset({"acme"})

    def test_empty_input(self):
        assert extract_company_terms("") == frozenset()


class TestKeywordOverlapCleaning:
    """F-01 — boilerplate + hiring-company cleaning in compute_keyword_overlap."""

    def test_boilerplate_never_counts_matched_or_missing(self):
        resume = {"keywords": {"python": 2, "hiring": 1}}
        jd = {"keywords": {"python": 3, "hiring": 2, "benefits": 1}}
        result = compute_keyword_overlap(resume, jd)
        assert result["matched"] == ["python"]
        assert result["missing_from_resume"] == []
        assert result["match_score"] == 1.0
        assert set(result["excluded_terms"]) == {"hiring", "benefits"}

    def test_company_absence_forgiven(self):
        resume = {"keywords": {"python": 1}}
        jd = {"keywords": {"python": 1, "lattice": 4, "lattice cloud": 2, "terraform": 1}}
        result = compute_keyword_overlap(resume, jd, company_terms=frozenset({"lattice cloud"}))
        assert result["missing_from_resume"] == ["terraform"]
        assert result["match_score"] == 0.5  # 1 matched / (1 matched + 1 missing)
        assert "lattice" in result["excluded_terms"]
        assert "lattice cloud" in result["excluded_terms"]

    def test_company_presence_still_credited(self):
        resume = {"keywords": {"databricks": 2, "python": 1}}
        jd = {"keywords": {"databricks": 5, "python": 1}}
        result = compute_keyword_overlap(resume, jd, company_terms=frozenset({"databricks"}))
        assert "databricks" in result["matched"]
        assert result["match_score"] == 1.0

    def test_no_cleaning_inputs_behave_as_before(self):
        resume = {"keywords": {"python": 1, "go": 2}}
        jd = {"keywords": {"python": 1, "kubernetes": 3}}
        result = compute_keyword_overlap(resume, jd)
        assert result["matched"] == ["python"]
        assert result["missing_from_resume"] == ["kubernetes"]
        assert result["match_score"] == 0.5
        assert result["excluded_terms"] == []


class TestKeywordScoreFixtureRegression:
    """F-01 acceptance — the real SRE fixture must score defensibly.

    Before-state evidence: 18% with "lattice cloud" in the missing list
    (docs/dev/reviews/2026-07-ux-review/40-friction-register.md §F-01).
    """

    FIXTURE = Path(__file__).parent.parent / "evals" / "fixtures" / "synthetic" / "sre-mid-level"

    def test_company_and_boilerplate_not_in_missing(self):
        jd_text = (self.FIXTURE / "jd.txt").read_text(encoding="utf-8")
        resume_text = (self.FIXTURE / "resume.md").read_text(encoding="utf-8")
        company = extract_company_terms(jd_text)
        assert "lattice cloud" in company
        result = compute_keyword_overlap(
            extract_keywords(resume_text),
            extract_keywords(jd_text),
            company_terms=company,
        )
        for term in ("lattice", "lattice cloud", "cloud", "hiring", "serving"):
            assert term not in result["missing_from_resume"]

    def test_score_exceeds_raw_overlap(self):
        jd_text = (self.FIXTURE / "jd.txt").read_text(encoding="utf-8")
        resume_text = (self.FIXTURE / "resume.md").read_text(encoding="utf-8")
        jd_kw = extract_keywords(jd_text)
        resume_kw = extract_keywords(resume_text)
        jd_set = set(jd_kw["keywords"])
        raw_score = len(set(resume_kw["keywords"]) & jd_set) / max(len(jd_set), 1)
        result = compute_keyword_overlap(
            resume_kw, jd_kw, company_terms=extract_company_terms(jd_text)
        )
        assert result["match_score"] > raw_score


class TestCheckAtsFormat:
    def test_flags_missing_email(self):
        parsed = {
            "text": "Some content with no contact info",
            "sections": [{"heading": "Experience", "content": []}],
            "format": ".docx",
        }
        warnings = check_ats_format(parsed)
        assert any("email" in w.lower() for w in warnings)

    def test_flags_missing_phone(self):
        parsed = {
            "text": "test@example.com no phone here",
            "sections": [{"heading": "Experience", "content": []}],
            "format": ".docx",
        }
        warnings = check_ats_format(parsed)
        assert any("phone" in w.lower() for w in warnings)

    def test_flags_pdf_format(self):
        parsed = {
            "text": "test@example.com 555-123-4567",
            "sections": [{"heading": "Experience", "content": []}],
            "format": ".pdf",
        }
        warnings = check_ats_format(parsed)
        assert any("pdf" in w.lower() for w in warnings)

    def test_flags_no_standard_headings(self):
        parsed = {
            "text": "test@example.com 555-123-4567 some body text " * 30,
            "sections": [{"heading": "Random Section", "content": []}],
            "format": ".docx",
        }
        warnings = check_ats_format(parsed)
        assert any("section heading" in w.lower() for w in warnings)


class TestValidateConfig:
    def test_missing_name_is_error(self):
        errors = validate_config({})
        assert any("name" in e.lower() for e in errors)

    def test_valid_config_has_no_errors(self):
        errors = validate_config({"name": "Jane", "linkedin_url": "https://linkedin.com/in/jane"})
        assert errors == []

    def test_malformed_url_is_error(self):
        errors = validate_config({"name": "Jane", "linkedin_url": "not-a-url"})
        assert any("invalid url" in e.lower() for e in errors)

    def test_malformed_portfolio_url_is_error(self):
        errors = validate_config({"name": "Jane", "portfolio_urls": ["not-a-url"]})
        assert any("portfolio" in e.lower() for e in errors)

    def test_scheme_less_dotted_host_is_tolerated(self):
        # A bare host the fetch layer already accepts must not be rejected here.
        errors = validate_config(
            {
                "name": "Jane",
                "linkedin_url": "linkedin.com/in/jane",
                "website_url": "jane.dev",
                "portfolio_urls": ["github.com/jane"],
            }
        )
        assert errors == []


class TestVerbDiversity:
    def test_empty_resume(self):
        out = compute_verb_diversity("")
        assert out["total_bullets"] == 0
        assert out["diversity_ratio"] == 0.0
        assert out["top_repeated"] == []

    def test_no_bullets_in_text(self):
        out = compute_verb_diversity("This is a paragraph without bullets.")
        assert out["total_bullets"] == 0

    def test_perfect_diversity(self):
        text = (
            "- Architected a distributed cache.\n"
            "- Designed the rollout plan.\n"
            "- Mentored two engineers.\n"
        )
        out = compute_verb_diversity(text)
        assert out["unique_verbs"] == 3
        assert out["total_bullets"] == 3
        assert out["diversity_ratio"] == 1.0
        assert out["top_repeated"] == []

    def test_low_diversity_flags_repeated_verb(self):
        text = "- Built dashboards.\n- Built reports.\n- Built ETL.\n- Maintained the warehouse.\n"
        out = compute_verb_diversity(text)
        assert out["unique_verbs"] == 2
        assert out["total_bullets"] == 4
        assert out["diversity_ratio"] == 0.5
        assert out["top_repeated"][0] == ("built", 3)

    def test_handles_asterisk_bullets(self):
        text = "* Led one effort.\n* Owned another.\n"
        out = compute_verb_diversity(text)
        assert out["total_bullets"] == 2
        assert out["unique_verbs"] == 2


class TestSpecificityDensity:
    def test_empty_input(self):
        out = compute_specificity_density("")
        assert out["total_bullets"] == 0
        assert out["density"] == 0.0

    def test_all_bullets_quantified(self):
        text = (
            "- Increased revenue 30% over two quarters.\n"
            "- Shipped 12 launches in 2024.\n"
            "- Saved $2.4M annually.\n"
        )
        out = compute_specificity_density(text)
        assert out["total_bullets"] == 3
        assert out["bullets_with_metric"] == 3
        assert out["density"] == 1.0

    def test_no_bullets_quantified(self):
        text = (
            "- Led cross-functional teams.\n"
            "- Mentored junior engineers.\n"
            "- Owned the architecture review process.\n"
        )
        out = compute_specificity_density(text)
        assert out["bullets_with_metric"] == 0
        assert out["density"] == 0.0

    def test_mixed(self):
        text = (
            "- Drove a 30% reduction in latency.\n"
            "- Mentored junior engineers.\n"
            "- Hired 5 ICs.\n"
            "- Drafted standards.\n"
        )
        out = compute_specificity_density(text)
        assert out["total_bullets"] == 4
        assert out["bullets_with_metric"] == 2
        assert out["density"] == 0.5


class TestGroundingOverlap:
    def test_empty_inputs(self):
        out = compute_grounding_overlap("", [])
        assert out["overlap_ratio"] == 0.0
        assert out["total_ngrams"] == 0
        assert out["missing_samples"] == []

    def test_full_overlap(self):
        source = "I built customer dashboards for the analytics team last year."
        out = compute_grounding_overlap(source, [source], n=3)
        assert out["overlap_ratio"] == 1.0
        assert out["missing_samples"] == []

    def test_data_scientist_junior_failure_mode(self):
        """The exact failure observed in evals/results: source said 'built
        dashboards', generated added 'time-series forecasting'. The 3-gram
        'time series forecasting' must surface in missing_samples."""
        source = "Built customer-facing dashboards for the analytics team."
        generated = "Built time-series forecasting models for executive stakeholders."
        out = compute_grounding_overlap(generated, [source], n=3)
        # 'time series forecasting' (or its punctuation-stripped equivalent)
        # should appear in missing_samples.
        joined = " | ".join(out["missing_samples"])
        assert "time series forecasting" in joined
        assert out["overlap_ratio"] < 0.5

    def test_stopword_only_ngrams_excluded(self):
        # Only stopwords in generated → no missing_samples entry would be
        # meaningful; ratio is 0 but missing_samples should NOT carry pure
        # stopword n-grams.
        out = compute_grounding_overlap("the and or", ["completely different text"], n=3)
        assert all(
            not all(w in {"the", "and", "or", "but", "in", "on"} for w in s.split())
            for s in out["missing_samples"]
        )

    def test_short_input_returns_zero_total(self):
        # Fewer than n tokens → no n-grams produced
        out = compute_grounding_overlap("hi", ["whatever"], n=3)
        assert out["total_ngrams"] == 0
        assert out["missing_samples"] == []

    def test_missing_samples_capped_at_ten(self):
        source = "alpha bravo charlie"
        # Many novel 3-grams in generated
        generated = " ".join(f"word{i}" for i in range(40))
        out = compute_grounding_overlap(generated, [source], n=3)
        assert len(out["missing_samples"]) <= 10


class TestFabricatedSpecifics:
    """L0 deterministic fabricated-specifics detector. Mirrors the
    TestGroundingOverlap pattern: exact match → 0; novel number → flagged;
    within-tolerance → not flagged; out-of-tolerance → flagged; entity
    aliasing → not flagged. No LLM, no model weights."""

    def test_empty_inputs(self):
        out = compute_fabricated_specifics("", [])
        assert out["fabricated_specifics_rate"] == 0.0
        assert out["total_specifics"] == 0
        assert out["flagged_samples"] == []

    def test_exact_source_match_zero_fabrication(self):
        source = ["Built dashboards serving 30 teams using PostgreSQL."]
        generated = "- Built dashboards serving 30 teams using PostgreSQL."
        out = compute_fabricated_specifics(generated, source)
        assert out["fabricated_specifics_rate"] == 0.0
        assert out["flagged"] == 0

    def test_novel_number_flagged(self):
        source = ["Built customer dashboards for the analytics team."]
        generated = "- Increased conversion by 250% across 14 markets."
        out = compute_fabricated_specifics(generated, source)
        assert out["fabricated_specifics_rate"] > 0.0
        joined = " | ".join(out["flagged_samples"])
        assert "250%" in joined
        assert "14" in joined

    def test_within_numeric_tolerance_not_flagged(self):
        # ~30 → 30+  : same canonical value 30 → grounded.
        source = ["Led a team of ~30 engineers."]
        generated = "- Led a team of 30+ engineers."
        out = compute_fabricated_specifics(generated, source)
        assert out["fabricated_specifics_rate"] == 0.0
        assert "30+" not in " | ".join(out["flagged_samples"])

    def test_out_of_numeric_tolerance_flagged(self):
        # ~30 → 100+ : different magnitude → flagged.
        source = ["Led a team of ~30 engineers."]
        generated = "- Led a team of 100+ engineers."
        out = compute_fabricated_specifics(generated, source)
        assert out["fabricated_specifics_rate"] > 0.0
        assert "100+" in " | ".join(out["flagged_samples"])

    def test_entity_aliasing_not_flagged(self):
        # Source says "Kubernetes"; output says "k8s" → alias-normalized match.
        source = ["Deployed services on Kubernetes in production."]
        generated = "- Migrated workloads to k8s with zero downtime."
        out = compute_fabricated_specifics(generated, source)
        assert "k8s" not in " | ".join(out["flagged_samples"])
        assert out["fabricated_specifics_rate"] == 0.0

    def test_embedded_digit_not_leaked_as_number(self):
        # The "8" inside "k8s" / "3" inside "S3" must NOT be matched as a
        # numeric specific — they belong to the entity token.
        source = ["Ran services on k8s and stored blobs in S3."]
        generated = "- Ran services on k8s and stored blobs in S3."
        out = compute_fabricated_specifics(generated, source)
        assert out["fabricated_specifics_rate"] == 0.0

    def test_severity_weighting_number_outweighs_entity(self):
        # A fabricated NUMBER (weight 2) must move the rate more than a
        # fabricated ENTITY (weight 1), holding the other grounded.
        ent_fabricated = compute_fabricated_specifics(
            "- Scaled to 50 servers on FakeCloudX.",
            ["Provisioned 50 servers in the datacenter."],  # 50 grounded, entity novel
        )
        num_fabricated = compute_fabricated_specifics(
            "- Ran 50 jobs on FakeCloudX.",
            ["Ran nightly jobs on FakeCloudX platform."],  # entity grounded, 50 novel
        )
        assert (
            num_fabricated["fabricated_specifics_rate"]
            > ent_fabricated["fabricated_specifics_rate"]
        )

    def test_per_bullet_shape(self):
        source = ["Built things with many users and people."]
        generated = "- Built X with 30 users.\n- Led 5 people."
        out = compute_fabricated_specifics(generated, source)
        assert out["total_bullets"] == 2
        assert len(out["per_bullet"]) == 2
        for entry in out["per_bullet"]:
            assert {"bullet", "n_specifics", "flagged"} <= entry.keys()
            assert entry["flagged"]  # both bullets carry a novel number

    def test_flagged_samples_capped_at_ten(self):
        source = ["No numeric content in this source text."]
        generated = "- " + " ".join(f"{i}%" for i in range(20))
        out = compute_fabricated_specifics(generated, source)
        assert len(out["flagged_samples"]) <= 10


class TestAssembleSourceUnion:
    """assemble_source_union folds primary + supplementals + clarification
    answers into one list, the single source-of-truth shared by the iteration
    clarifier and the L0 metric."""

    def test_union_includes_all_three_sources(self):
        ctx: dict = {
            "resume": {"text": "primary resume body"},
            "supplemental_resumes": [{"text": "supplemental body"}],
            "clarifications": {"q1": "clarified fact answer"},
        }
        union = assemble_source_union(ctx)
        assert "primary resume body" in union
        assert "supplemental body" in union
        assert "clarified fact answer" in union

    def test_skips_empty_and_missing_fields(self):
        ctx: dict = {
            "resume": {"text": ""},
            "supplemental_resumes": [{"text": "only this"}],
        }
        union = assemble_source_union(ctx)
        assert union == ["only this"]

    def test_prior_clarifications_widen_the_union(self):
        """D5 (feat/clarifications-to-corpus): cross-JD confirmed facts staged
        onto context_set["prior_clarifications"] must count as grounding source
        material too, or the metric would over-report Compose drafting content
        legitimately sourced from them as fabrication."""
        ctx: dict = {
            "resume": {"text": "primary resume body"},
            "prior_clarifications": [
                {"question": "SRE experience?", "answer": "Led on-call for 12 engineers."},
                {"question": "empty answer dropped", "answer": ""},
            ],
        }
        union = assemble_source_union(ctx)
        assert "Led on-call for 12 engineers." in union
        assert len(union) == 2  # primary + the one non-empty prior answer

    def test_absent_prior_clarifications_unaffected(self):
        """Legacy (file-based) contexts never populate prior_clarifications —
        the union must be identical to pre-D5 behavior."""
        ctx: dict = {"resume": {"text": "primary resume body"}}
        assert assemble_source_union(ctx) == ["primary resume body"]


class TestCallCost:
    def test_known_sonnet_record(self):
        record = {
            "model": "claude-sonnet-4-6",
            "input_tokens": 1_000_000,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        # 1M input @ $3/M = $3.00. Sonnet 4.6 is retained in MODEL_PRICING so
        # historical llm_calls.jsonl records keep costing correctly.
        assert compute_call_cost(record) == 3.0

    def test_known_sonnet5_record(self):
        # Guards the active Sonnet model against the unknown-model → 0.0 path.
        record = {
            "model": "claude-sonnet-5",
            "input_tokens": 1_000_000,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        # 1M input @ $3/M = $3.00
        assert compute_call_cost(record) == 3.0

    def test_haiku_with_cache(self):
        record = {
            "model": "claude-haiku-4-5-20251001",
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 1_000_000,
        }
        # 1M cache_read @ $0.08/M = $0.08
        assert compute_call_cost(record) == 0.08

    def test_unknown_model_returns_zero(self, caplog):
        record = {
            "model": "claude-opus-9000",
            "input_tokens": 100,
            "output_tokens": 100,
        }
        cost = compute_call_cost(record)
        assert cost == 0.0

    def test_missing_model_no_warning_just_zero(self):
        record = {"input_tokens": 100, "output_tokens": 100}
        assert compute_call_cost(record) == 0.0

    def test_realistic_analyze_call(self):
        # Real values from a recent eval run
        record = {
            "model": "claude-sonnet-4-6",
            "input_tokens": 2050,
            "output_tokens": 4829,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        # 2050*3 + 4829*15 = 6150 + 72435 = 78585 / 1M = $0.078585
        assert compute_call_cost(record) == 0.078585


class TestContextSetClarificationFields:
    """Round-trip and back-compat tests for the new clarify-step fields."""

    def _base_context(self) -> dict:
        return {
            "timestamp": "2026-05-11T12:00:00",
            "candidate": {
                "name": "Alice",
                "email": "",
                "phone": "",
                "linkedin_url": "",
                "website_url": "",
                "skills": [],
                "certifications": [],
                "education_summary": "",
                "notes": "",
                "profile_text": "",
            },
            "resume": {
                "format": ".docx",
                "sections": [],
                "text": "x",
                "filename": "alice.docx",
                "path": "",
            },
            "supplemental_resumes": [],
            "job_description": "jd",
            "deterministic_analysis": {
                "jd_keywords": {},
                "resume_keywords": {},
                "keyword_overlap": {},
                "ats_warnings": [],
            },
        }

    def test_pre_clarify_context_round_trips(self, tmp_path):
        """A context saved before the clarify-step fields existed must load
        without errors and produce equivalent JSON."""
        ctx = self._base_context()
        path = save_context_set(ctx, "alice", str(tmp_path))
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        # No clarification fields should sneak in
        assert "clarifications" not in loaded
        assert "clarification_questions" not in loaded
        assert loaded["candidate"]["name"] == "Alice"

    def test_post_clarify_context_round_trips(self, tmp_path):
        """A context with clarification_questions and clarifications fields
        must round-trip through save and reload as plain JSON."""
        ctx = self._base_context()
        ctx["clarification_questions"] = [
            {
                "id": "q1",
                "text": "Used K8s?",
                "kind": "experience_probe",
                "target_gap": "k8s missing",
            },
        ]
        ctx["clarifications"] = {"q1": "Briefly in 2024."}
        path = save_context_set(ctx, "alice", str(tmp_path))
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        assert loaded["clarification_questions"][0]["kind"] == "experience_probe"
        assert loaded["clarifications"]["q1"] == "Briefly in 2024."


class TestComputeTopThirdDensity:
    _BULLETS = (
        "- Led cloud migration\n- Wrote python automation scripts\n- Managed kubernetes clusters\n"
    )
    _JD_KW: ClassVar[dict] = {
        "keywords": {"kubernetes": 5, "cloud": 4, "python": 3},
        "total_unique": 3,
    }

    def test_empty_resume_returns_zero(self):
        out = compute_top_third_density("", self._JD_KW)
        assert out["density"] == 0.0
        assert out["bullets_checked"] == 0

    def test_empty_jd_keywords_returns_zero(self):
        out = compute_top_third_density(self._BULLETS, {})
        assert out["density"] == 0.0
        assert out["bullets_with_essential"] == 0

    def test_all_three_bullets_hit(self):
        # All three top essentials appear in the bullets
        out = compute_top_third_density(self._BULLETS, self._JD_KW)
        assert out["top3_essentials"] == ["kubernetes", "cloud", "python"]
        assert out["bullets_checked"] == 3
        assert out["bullets_with_essential"] == 3
        assert out["density"] == 1.0

    def test_no_bullets_match_essential(self):
        resume = "- Authored design docs\n- Reviewed pull requests\n- Attended stand-ups\n"
        out = compute_top_third_density(resume, self._JD_KW)
        assert out["bullets_with_essential"] == 0
        assert out["density"] == 0.0

    def test_experience_header_scopes_search(self):
        # Skills section has kubernetes but experience section doesn't
        resume = (
            "## Skills\n- kubernetes, cloud\n\n"
            "## Experience\n- Coordinated sprints\n- Wrote reports\n- Ran retrospectives\n"
        )
        out = compute_top_third_density(resume, self._JD_KW)
        # Experience bullets don't contain top essentials
        assert out["bullets_with_essential"] == 0

    def test_partial_match_gives_fractional_density(self):
        resume = "- Deployed kubernetes clusters\n- Wrote documentation\n- Attended meetings\n"
        out = compute_top_third_density(resume, self._JD_KW)
        assert out["bullets_with_essential"] == 1
        assert abs(out["density"] - 0.333) < 0.001


class TestComputeQuantificationRate:
    def test_empty_resume_returns_zero(self):
        out = compute_quantification_rate("")
        assert out["rate"] == 0.0
        assert out["total_bullets"] == 0

    def test_no_bullets_returns_zero(self):
        out = compute_quantification_rate("Just a paragraph without bullets.")
        assert out["rate"] == 0.0

    def test_all_bullets_quantified(self):
        resume = "- Reduced latency by 40%\n- Saved $2M annually\n- Scaled to 10k users\n"
        out = compute_quantification_rate(resume)
        assert out["total_bullets"] == 3
        assert out["bullets_with_quantity"] == 3
        assert out["rate"] == 1.0

    def test_no_bullets_quantified(self):
        resume = "- Led the initiative\n- Collaborated with teams\n- Improved the process\n"
        out = compute_quantification_rate(resume)
        assert out["bullets_with_quantity"] == 0
        assert out["rate"] == 0.0

    def test_partial_quantification(self):
        resume = "- Cut costs by 30%\n- Improved team culture\n- Delivered 5 projects\n"
        out = compute_quantification_rate(resume)
        assert out["bullets_with_quantity"] == 2
        assert abs(out["rate"] - 0.667) < 0.001

    def test_currency_and_scale_words_match(self):
        resume = "- Managed $500k budget\n- Grew platform to 2 million users\n"
        out = compute_quantification_rate(resume)
        assert out["bullets_with_quantity"] == 2
        assert out["rate"] == 1.0


class TestComputeDateGrounding:
    """KW6 guard: heading date ranges must trace to the corpus (warn-only)."""

    CORPUS: ClassVar[list[dict]] = [
        {"id": 1, "company": "Acme", "start_date": "2024-01", "end_date": None},
        {"id": 2, "company": "Acme", "start_date": "2016-01", "end_date": "2018-12"},
        {"id": 3, "company": "Acme", "start_date": "2012-01", "end_date": "2016-12"},
    ]

    def test_all_headings_correct_passes(self):
        resume = (
            "# Jane Doe\n\n## Experience\n\n"
            "### Acme, Product Lead\t2024 – Present\n- Did a thing.\n\n"
            "### Acme, Design Lead\t2016 – 2018\n- Did a thing.\n\n"
            "### Acme, Junior Designer\t2012 – 2016\n- Did a thing.\n"
        )
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["status"] == "pass"
        assert out["checked"] == 3
        assert out["flagged"] == []

    def test_kw6_duplicated_range_flags(self):
        # The KW6 shape: the model "reconciled" the 2012–2016 role onto the
        # adjacent role's 2016–2018 range while reordering; 2012–2016 vanished.
        resume = (
            "# Jane Doe\n\n## Experience\n\n"
            "### Acme, Product Lead\t2024 – Present\n- Did a thing.\n\n"
            "### Acme, Design Lead\t2016 – 2018\n- Did a thing.\n\n"
            "### Acme, Junior Designer\t2016 – 2018\n- Did a thing.\n"
        )
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["status"] == "flag"
        assert len(out["flagged"]) == 1
        assert out["flagged"][0]["found"] == "2016 – 2018"
        assert "Junior Designer" in out["flagged"][0]["heading"]

    def test_altered_range_flags(self):
        resume = "## Experience\n\n### Acme, Design Lead\t2017 – 2019\n- Did a thing.\n"
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["status"] == "flag"
        assert out["flagged"][0]["found"] == "2017 – 2019"

    def test_month_names_and_present_variants_tolerated(self):
        resume = (
            "## Experience\n\n"
            "### Acme, Product Lead\tJanuary 2024 – present\n- Did a thing.\n\n"
            "### Acme, Design Lead\tJan 2016 – Dec 2018\n- Did a thing.\n"
        )
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["status"] == "pass"
        assert out["checked"] == 2

    def test_no_corpus_is_benign_pass(self):
        resume = "## Experience\n\n### Acme, Lead\t2016 – 2018\n"
        assert compute_date_grounding(resume, [])["status"] == "pass"

    def test_empty_resume_is_benign_pass(self):
        assert compute_date_grounding("", self.CORPUS)["status"] == "pass"

    def test_headings_without_date_tab_ignored(self):
        resume = "## Experience\n\n### Acme, Product Lead\n- Did a thing.\n"
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["checked"] == 0
        assert out["status"] == "pass"

    def test_education_section_years_not_scanned(self):
        # Degree years live outside the corpus; the scan is scoped to the
        # experience section so they never false-flag.
        resume = (
            "## Experience\n\n"
            "### Acme, Design Lead\t2016 – 2018\n- Did a thing.\n\n"
            "## Education\n\n"
            "### State University, BFA\t2008 – 2012\n"
        )
        out = compute_date_grounding(resume, self.CORPUS)
        assert out["status"] == "pass"
        assert out["checked"] == 1

    def test_corpus_with_unparseable_start_skipped(self):
        corpus = [{"id": 9, "company": "X", "start_date": "unknown", "end_date": None}]
        resume = "## Experience\n\n### X, Lead\t2020 – Present\n"
        out = compute_date_grounding(resume, corpus)
        # No parseable corpus range -> unverifiable -> benign pass, not a flag.
        assert out["status"] == "pass"
        assert out["checked"] == 0

    def test_duplicate_range_legitimately_in_corpus_passes(self):
        corpus = [
            {"id": 1, "company": "A", "start_date": "2016-01", "end_date": "2018-12"},
            {"id": 2, "company": "B", "start_date": "2016-03", "end_date": "2018-06"},
        ]
        resume = "## Experience\n\n### A, Lead\t2016 – 2018\n\n### B, Advisor\t2016 – 2018\n"
        out = compute_date_grounding(resume, corpus)
        assert out["status"] == "pass"
        assert out["checked"] == 2


class TestWriteContextAtomic:
    """The context file must never be observable half-written.

    `Path.write_text` truncates the destination *before* it writes, so a concurrent
    reader saw an empty or partial file and its `json.loads` raised. In the app that
    surfaced as a 400 from `POST /draft-summary`, which the Compose client then
    swallowed — leaving a positioning summary that never arrived and a "Drafting your
    summary…" placeholder that never cleared, on 64% of CI attempts
    (`fix/compose-summary-draft-settle-hole`).
    """

    @staticmethod
    def _torn_reads(path: Path, writer, iters: int = 40, readers: int = 3) -> list[str]:
        """Hammer `path` with readers while `writer` rewrites it; collect torn reads.

        Writer-side `PermissionError` is swallowed on purpose. On Windows `os.replace`
        is blocked while any reader holds the destination open (production handles that
        with a bounded retry — see `hardening._REPLACE_ATTEMPTS`). It is NOT the
        invariant under test: "a reader never observes a partial file" is, and that has
        to hold on every platform regardless of who wins the write.
        """
        payload = {"blob": ["x" * 64] * 4000}  # ~1 MB — a wide truncate-to-rewrite window
        writer(path, payload)
        torn: list[str] = []
        stop = threading.Event()

        def _write() -> None:
            try:
                for i in range(iters):
                    # PermissionError is platform noise, not the invariant — see docstring.
                    with contextlib.suppress(PermissionError):
                        writer(path, {"i": i, **payload})
                    time.sleep(0.002)
            finally:
                stop.set()

        def _read() -> None:
            while not stop.is_set():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    torn.append(str(exc))
                except OSError:
                    # Windows-only platform noise: a concurrent os.replace can
                    # briefly deny a reader (PermissionError, an OSError
                    # subclass). That is not a torn read — the invariant under
                    # test is that JSONDecodeError never fires — so ignore it.
                    pass
                time.sleep(0.004)

        write_thread = threading.Thread(target=_write)
        read_threads = [threading.Thread(target=_read) for _ in range(readers)]
        for t in (*read_threads, write_thread):
            t.start()
        for t in (write_thread, *read_threads):
            t.join(timeout=60)
        return torn

    def test_reader_never_observes_a_partial_file(self, tmp_path):
        """Subject and control in one test.

        The control is load-bearing: without it, a green `atomic == 0` could simply
        mean the race never fired, and the guard would be vacuous. `write_text` MUST
        tear under this harness — that tear IS the bug.
        """

        def _write_naive(path: Path, ctx) -> None:
            path.write_text(json.dumps(ctx, indent=2), encoding="utf-8")

        naive = self._torn_reads(tmp_path / "naive.json", _write_naive)
        atomic = self._torn_reads(tmp_path / "atomic.json", write_context_atomic)

        assert naive, "harness never reproduced a torn read — the assertion below proves nothing"
        assert not atomic, f"write_context_atomic exposed a partial file: {atomic[:3]}"

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "nested" / "deeper" / "context_1.json"
        write_context_atomic(path, {"a": 1})
        assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}


class TestContextTransaction:
    """No writer's delta may be erased by another writer's stale write-back.

    Atomic writes stop torn *reads* and do nothing about lost *updates*: twelve
    routes each read the whole `context_*.json`, spend seconds in an LLM call, then
    write the whole (now stale) dict back. Whoever wrote inside that window has
    their delta silently deleted. That was live and user-visible — a drafted
    positioning summary persisted, then vanished for good
    (`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`, O-2 / O-4 / O-7).
    """

    @staticmethod
    def _race(path: Path, apply_delta, writers: int = 8) -> dict:
        """Have `writers` threads each add their own key, with a slow window mid-cycle.

        `apply_delta(path, i)` performs one writer's whole read-modify-write. The
        sleep inside each writer's window is what an LLM call is in production: the
        thing that makes two cycles overlap.
        """
        write_context_atomic(path, {"base": True})
        threads = [threading.Thread(target=apply_delta, args=(path, i)) for i in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return json.loads(path.read_text(encoding="utf-8"))

    def test_concurrent_writers_do_not_erase_each_other(self, tmp_path):
        """Subject and control in one test.

        The control is load-bearing, exactly as in `TestWriteContextAtomic`: without
        it, a green subject could just mean the race never fired. The naive
        read-modify-write MUST lose updates under this harness — that loss IS the
        bug, and it is the one the two shipped-but-wrong fixes never touched.
        """

        def _naive(path: Path, i: int) -> None:
            ctx = json.loads(path.read_text(encoding="utf-8"))
            time.sleep(0.02)  # the LLM call: the window in which the copy goes stale
            ctx[f"k{i}"] = i
            write_context_atomic(path, ctx)  # atomic, and STILL a lost update

        def _transactional(path: Path, i: int) -> None:
            json.loads(path.read_text(encoding="utf-8"))  # the optimistic pre-call read
            time.sleep(0.02)  # the LLM call — deliberately OUTSIDE the lock
            with context_transaction(path) as fresh:
                fresh[f"k{i}"] = i

        naive = self._race(tmp_path / "naive.json", _naive)
        txn = self._race(tmp_path / "txn.json", _transactional)

        naive_keys = {k for k in naive if k.startswith("k")}
        txn_keys = {k for k in txn if k.startswith("k")}

        assert len(naive_keys) < 8, (
            "harness never reproduced a lost update — the assertion below proves nothing"
        )
        assert txn_keys == {f"k{i}" for i in range(8)}, (
            f"context_transaction lost a delta: only {sorted(txn_keys)} survived"
        )

    def test_the_yielded_dict_is_a_fresh_read_not_the_callers_copy(self, tmp_path):
        """The whole fix in one assertion: the optimistic pre-call copy is discarded."""
        path = tmp_path / "context_1.json"
        write_context_atomic(path, {"a": 1})

        stale = json.loads(path.read_text(encoding="utf-8"))  # caller's pre-call read
        write_context_atomic(path, {"a": 1, "landed_meanwhile": "x"})  # someone else writes

        with context_transaction(path) as fresh:
            assert fresh["landed_meanwhile"] == "x", "the in-lock read was not fresh"
            fresh["mine"] = True

        final = json.loads(path.read_text(encoding="utf-8"))
        assert final["landed_meanwhile"] == "x", "the concurrent delta was erased"
        assert final["mine"] is True
        assert "landed_meanwhile" not in stale  # the copy that would have erased it

    def test_a_raising_block_writes_nothing(self, tmp_path):
        path = tmp_path / "context_1.json"
        write_context_atomic(path, {"a": 1})

        # The raising body lives in a helper so the `raise` is not the terminal
        # statement of the `with pytest.raises(...)` block: CodeQL does not model
        # pytest.raises suppressing it and would otherwise flag the assert below
        # as unreachable (py/unreachable-statement). Behavior is identical.
        def _raise_inside_transaction() -> None:
            with context_transaction(path) as fresh:
                fresh["half"] = "landed"
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            _raise_inside_transaction()

        assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}, (
            "a failed delta half-landed — the write must be skipped entirely"
        )

    def test_the_lock_is_released_after_a_raising_block(self, tmp_path):
        """A leaked lock would deadlock every later write to the same file."""
        path = tmp_path / "context_1.json"
        write_context_atomic(path, {"a": 1})

        with contextlib.suppress(RuntimeError), context_transaction(path) as fresh:
            raise RuntimeError("boom")

        with context_transaction(path) as fresh:
            fresh["after"] = True
        assert json.loads(path.read_text(encoding="utf-8"))["after"] is True

    def test_two_spellings_of_one_path_share_a_lock(self, tmp_path):
        """Keyed on the RESOLVED path — else the serialization is a fiction."""
        path = tmp_path / "context_1.json"
        write_context_atomic(path, {"a": 1})
        indirect = tmp_path / "sub" / ".." / "context_1.json"
        (tmp_path / "sub").mkdir()

        from hardening import _context_lock

        assert _context_lock(path) is _context_lock(indirect)

    def test_success_leaves_no_temp_debris(self, tmp_path):
        write_context_atomic(tmp_path / "context_1.json", {"a": 1})
        assert [p.name for p in tmp_path.iterdir()] == ["context_1.json"]

    def test_failed_write_preserves_target_and_leaves_no_debris(self, tmp_path):
        """A write that can't serialize must not destroy the file it was replacing."""
        path = tmp_path / "context_1.json"
        write_context_atomic(path, {"ok": 1})

        with pytest.raises(TypeError):
            write_context_atomic(path, {"bad": object()})

        assert json.loads(path.read_text(encoding="utf-8")) == {"ok": 1}
        assert [p.name for p in tmp_path.iterdir()] == ["context_1.json"]
