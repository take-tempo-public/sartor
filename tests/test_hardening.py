"""Unit tests for hardening.py — the deterministic layer.

These functions must remain LLM-free and produce stable output for given input.
"""

import json
from pathlib import Path
from typing import ClassVar

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
    extract_keywords,
    save_context_set,
    strip_cover_letter_block,
    validate_config,
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
