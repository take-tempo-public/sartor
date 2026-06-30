"""Unit tests for the deterministic experience-similarity scorer."""

from __future__ import annotations

from onboarding.experience_match import (
    ExperienceLike,
    bullet_overlap,
    company_similarity,
    date_similarity,
    normalize_company,
    score_experiences,
    title_similarity,
)


def test_normalize_company_strips_legal_suffix_and_punct():
    assert normalize_company("Acme, Inc.") == "acme"
    assert normalize_company("Acme Corporation") == "acme"
    assert normalize_company("Globex LLC") == "globex"
    assert normalize_company("Initech") == "initech"


def test_company_similarity_equal_after_normalization():
    assert company_similarity("Acme, Inc.", "Acme") == 1.0
    assert company_similarity("Acme", "Globex") < 0.6


def test_title_similarity_token_overlap():
    assert title_similarity("Senior Product Manager", "Senior Product Manager") == 1.0
    assert title_similarity("Product Manager", "Senior Product Manager") >= 0.6
    assert title_similarity("Product Manager", "Janitor") < 0.4


def test_date_similarity_same_start_is_one():
    assert date_similarity("2020-01", "2023-06", "2020-01", "2024-01") == 1.0


def test_date_similarity_overlapping_ranges_high():
    # 2020-01..2023-06 vs 2021-03..2024-01 overlap substantially.
    assert date_similarity("2020-01", "2023-06", "2021-03", "2024-01") > 0.5


def test_date_similarity_adjacent_promotion_moderate():
    # 2018-01..2019-12 then 2020-01..2021-12 — adjacent (1 month gap).
    sim = date_similarity("2018-01", "2019-12", "2020-01", "2021-12")
    assert 0.0 < sim <= 0.5


def test_date_similarity_disjoint_low():
    assert date_similarity("2010-01", "2011-01", "2020-01", "2021-01") == 0.0


def test_bullet_overlap_exact_and_fuzzy():
    a = ("Led a team of 5 engineers.", "Shipped V2 of the platform.")
    b = ("Led a team of 5 engineers!", "Owned the eval framework.")
    # First bullet matches (punctuation-insensitive); 1 of 2 shared.
    assert bullet_overlap(a, b) == 0.5
    assert bullet_overlap((), b) == 0.0


def test_score_same_role_different_dates_is_similar():
    # The reported bug: same job, drifted title + dates, shared bullets.
    a = ExperienceLike(
        company="Acme Corp",
        start_date="2020-01",
        end_date="2023-06",
        titles=("Product Manager",),
        bullets=("Led roadmap for 3 products.", "Grew ARR 40%."),
    )
    b = ExperienceLike(
        company="Acme, Inc.",
        start_date="2021-03",
        end_date="2024-01",
        titles=("Senior Product Manager",),
        bullets=("Led roadmap for 3 products.", "Hired 6 PMs."),
    )
    result = score_experiences(a, b)
    assert result.band == "SIMILAR"
    assert "company" in result.matched_signals
    assert "bullets" in result.matched_signals


def test_score_different_company_is_distinct():
    a = ExperienceLike("Acme Corp", "2020-01", "2023-06", ("Engineer",), ("Built X.",))
    b = ExperienceLike("Globex", "2020-01", "2023-06", ("Engineer",), ("Built X.",))
    assert score_experiences(a, b).band == "DISTINCT"


def test_score_exact_company_and_start_is_exact():
    a = ExperienceLike("Acme", "2020-01", "2023-06", ("Engineer",), ("Built X.",))
    b = ExperienceLike("Acme, Inc.", "2020-01", "2022-01", ("Senior Engineer",), ("Built Y.",))
    assert score_experiences(a, b).band == "EXACT"


def test_score_same_company_unrelated_roles_distinct():
    # Two genuinely different, non-overlapping roles at the same company,
    # no shared bullets, far-apart dates → should NOT be suggested.
    a = ExperienceLike("Acme", "2012-01", "2014-01", ("Receptionist",), ("Answered phones.",))
    b = ExperienceLike(
        "Acme", "2020-01", "2022-01", ("Staff Engineer",), ("Designed the data platform.",)
    )
    assert score_experiences(a, b).band == "DISTINCT"
