"""Unit tests for hardening.py — the deterministic layer.

These functions must remain LLM-free and produce stable output for given input.
"""

import json

from hardening import (
    check_ats_format,
    compute_call_cost,
    compute_grounding_overlap,
    compute_keyword_overlap,
    compute_quantification_rate,
    compute_specificity_density,
    compute_top_third_density,
    compute_verb_diversity,
    extract_keywords,
    save_context_set,
    validate_config,
)


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
        text = (
            "- Built dashboards.\n"
            "- Built reports.\n"
            "- Built ETL.\n"
            "- Maintained the warehouse.\n"
        )
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


class TestCallCost:
    def test_known_sonnet_record(self):
        record = {
            "model": "claude-sonnet-4-6",
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
                "name": "Alice", "email": "", "phone": "", "linkedin_url": "",
                "website_url": "", "skills": [], "certifications": [],
                "education_summary": "", "notes": "", "profile_text": "",
            },
            "resume": {
                "format": ".docx", "sections": [], "text": "x",
                "filename": "alice.docx", "path": "",
            },
            "supplemental_resumes": [],
            "job_description": "jd",
            "deterministic_analysis": {
                "jd_keywords": {}, "resume_keywords": {},
                "keyword_overlap": {}, "ats_warnings": [],
            },
        }

    def test_pre_clarify_context_round_trips(self, tmp_path):
        """A context saved before the clarify-step fields existed must load
        without errors and produce equivalent JSON."""
        ctx = self._base_context()
        path = save_context_set(ctx, "alice", str(tmp_path))
        loaded = json.loads(open(path, encoding="utf-8").read())
        # No clarification fields should sneak in
        assert "clarifications" not in loaded
        assert "clarification_questions" not in loaded
        assert loaded["candidate"]["name"] == "Alice"

    def test_post_clarify_context_round_trips(self, tmp_path):
        """A context with clarification_questions and clarifications fields
        must round-trip through save and reload as plain JSON."""
        ctx = self._base_context()
        ctx["clarification_questions"] = [
            {"id": "q1", "text": "Used K8s?", "kind": "experience_probe",
             "target_gap": "k8s missing"},
        ]
        ctx["clarifications"] = {"q1": "Briefly in 2024."}
        path = save_context_set(ctx, "alice", str(tmp_path))
        loaded = json.loads(open(path, encoding="utf-8").read())
        assert loaded["clarification_questions"][0]["kind"] == "experience_probe"
        assert loaded["clarifications"]["q1"] == "Briefly in 2024."


class TestComputeTopThirdDensity:
    _BULLETS = "- Led cloud migration\n- Wrote python automation scripts\n- Managed kubernetes clusters\n"
    _JD_KW: dict = {"keywords": {"kubernetes": 5, "cloud": 4, "python": 3}, "total_unique": 3}

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
