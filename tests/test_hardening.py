"""Unit tests for hardening.py — the deterministic layer.

These functions must remain LLM-free and produce stable output for given input.
"""

from hardening import (
    check_ats_format,
    compute_keyword_overlap,
    extract_keywords,
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
