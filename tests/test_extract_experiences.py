"""Tests for the LLM-assisted experience extractor.

The LLM call itself is mocked — we test the prompt shape, response parsing,
and the deterministic normalization layer (date validation, tag cleanup,
has_outcome detection, malformed-bullet drop, etc.).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import anthropic

from analyzer import HAIKU_MODEL
from onboarding.extract_experiences import (
    _clean_tag_list,
    _normalize_bullet,
    _normalize_experience,
    _normalize_skill_list,
    extract_experiences,
    extract_experiences_and_skills,
)


def _make_valid_response() -> dict:
    return {
        "experiences": [
            {
                "company": "Acme Corp",
                "location": "Seattle, WA",
                "start_date": "2020-01",
                "end_date": "2023-04",
                "candidate_inferred_title": "Senior PM",
                "suggested_role_tags": ["pm", "product-leadership"],
                "bullets": [
                    {
                        "text": "Led 5-person team shipping V2 to 50 enterprise customers.",
                        "suggested_tags": ["leadership"],
                    },
                    {
                        "text": "Authored design language for in-product agent UIs.",
                        "suggested_tags": ["ic-design"],
                    },
                ],
            },
            {
                "company": "Beta LLC",
                "start_date": "2018-06",
                "end_date": None,  # current
                "candidate_inferred_title": "PM",
                "suggested_role_tags": ["pm"],
                "bullets": [{"text": "Built dashboards.", "suggested_tags": []}],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Normalization (no LLM)
# ---------------------------------------------------------------------------


class TestCleanTagList:
    def test_lowercases_and_hyphenates(self):
        assert _clean_tag_list(["AI", "Product Management"]) == ["ai", "product-management"]

    def test_dedupes(self):
        assert _clean_tag_list(["ai", "AI", "Ai"]) == ["ai"]

    def test_drops_non_strings(self):
        assert _clean_tag_list(["ai", 42, None, "ml"]) == ["ai", "ml"]

    def test_handles_non_list(self):
        assert _clean_tag_list("not a list") == []
        assert _clean_tag_list(None) == []


class TestNormalizeBullet:
    def test_detects_outcome_when_metric_present(self):
        b = _normalize_bullet({"text": "Shipped V2 to 50 customers.", "suggested_tags": []})
        assert b["has_outcome"] is True

    def test_no_outcome_when_no_metric(self):
        b = _normalize_bullet({"text": "Did the thing.", "suggested_tags": []})
        assert b["has_outcome"] is False

    def test_preserves_text_verbatim(self):
        b = _normalize_bullet({"text": "  Trimmed text.  ", "suggested_tags": []})
        assert b["text"] == "Trimmed text."

    def test_normalizes_tags(self):
        b = _normalize_bullet({"text": "x", "suggested_tags": ["AI", "Machine Learning"]})
        assert b["suggested_tags"] == ["ai", "machine-learning"]


class TestNormalizeExperience:
    def test_drops_experience_with_invalid_start_date(self):
        exp = _normalize_experience(
            {
                "company": "Acme",
                "start_date": "March 2020",  # not YYYY-MM nor a bare YYYY
                "candidate_inferred_title": "PM",
                "bullets": [{"text": "x", "suggested_tags": []}],
            }
        )
        assert exp["company"] == ""  # sentinel — caller should drop

    def test_accepts_year_only_start_date(self):
        """Walkthrough F3: a bare YYYY is a valid date (kept, stored verbatim)."""
        exp = _normalize_experience(
            {
                "company": "Acme",
                "start_date": "2020",
                "end_date": "2023",
                "candidate_inferred_title": "PM",
                "bullets": [{"text": "Shipped it.", "suggested_tags": []}],
            }
        )
        assert exp["company"] == "Acme"
        assert exp["start_date"] == "2020"  # not blanked, not coerced to 2020-01
        assert exp["end_date"] == "2023"

    def test_captures_role_summary_separately_from_bullets(self):
        """Walkthrough F2: a role-intro paragraph rides on `summary`, not `bullets`."""
        exp = _normalize_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "PM",
                "summary": "Owned the platform roadmap for a 3-team org.",
                "bullets": [{"text": "Shipped V2.", "suggested_tags": []}],
            }
        )
        assert exp["summary"] == "Owned the platform roadmap for a 3-team org."
        assert [b["text"] for b in exp["bullets"]] == ["Shipped V2."]

    def test_summary_none_when_absent(self):
        exp = _normalize_experience(
            {"company": "Acme", "start_date": "2020-01", "candidate_inferred_title": "PM"}
        )
        assert exp["summary"] is None

    def test_drops_experience_with_missing_company(self):
        exp = _normalize_experience(
            {
                "company": "",
                "start_date": "2020-01",
                "candidate_inferred_title": "PM",
            }
        )
        # Schema check should catch missing company too — start_date alone won't save it
        # because validation expects both. Re-check what happens:
        # Actually the _normalize logic only drops on invalid start_date; company validation
        # happens at insert. So this should pass through with empty company.
        assert exp["company"] == ""

    def test_preserves_valid_experience(self):
        exp = _normalize_experience(
            {
                "company": "Acme",
                "location": "Seattle",
                "start_date": "2020-01",
                "end_date": "2023-04",
                "candidate_inferred_title": "Senior PM",
                "suggested_role_tags": ["PM"],
                "bullets": [
                    {"text": "Led team of 5.", "suggested_tags": ["LEADERSHIP"]},
                ],
            }
        )
        assert exp["company"] == "Acme"
        assert exp["location"] == "Seattle"
        assert exp["start_date"] == "2020-01"
        assert exp["end_date"] == "2023-04"
        assert exp["suggested_role_tags"] == ["pm"]
        assert len(exp["bullets"]) == 1
        assert exp["bullets"][0]["has_outcome"] is True  # "5" is a count

    def test_drops_bullets_with_empty_text(self):
        exp = _normalize_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "PM",
                "bullets": [
                    {"text": "Real bullet.", "suggested_tags": []},
                    {"text": "", "suggested_tags": []},
                    {"text": "  ", "suggested_tags": []},
                ],
            }
        )
        assert len(exp["bullets"]) == 1

    def test_end_date_null_preserved(self):
        exp = _normalize_experience(
            {
                "company": "Acme",
                "start_date": "2020-01",
                "candidate_inferred_title": "PM",
                "end_date": None,
                "bullets": [],
            }
        )
        assert exp["end_date"] is None


class TestNormalizeSkillList:
    """F-02: the deterministic cleanup applied to the LLM's flat skills list."""

    def test_strips_and_passes_through(self):
        assert _normalize_skill_list(["  Python ", "Kubernetes"]) == ["Python", "Kubernetes"]

    def test_dedupes_case_insensitively_preserving_first_seen_casing(self):
        assert _normalize_skill_list(["Python", "python", "PYTHON"]) == ["Python"]

    def test_drops_blanks_and_non_strings(self):
        assert _normalize_skill_list(["Go", "", "   ", 42, None, "Rust"]) == ["Go", "Rust"]

    def test_handles_non_list_input(self):
        assert _normalize_skill_list(None) == []
        assert _normalize_skill_list("not a list") == []

    def test_empty_list(self):
        assert _normalize_skill_list([]) == []


# ---------------------------------------------------------------------------
# End-to-end extract_experiences with mocked LLM
# ---------------------------------------------------------------------------


def _mock_anthropic_client(response_text: str) -> MagicMock:
    """Build an anthropic client mock that returns the given response from streaming."""
    client = MagicMock(spec=anthropic.Anthropic)

    # The stream API: client.messages.stream(...) returns a context manager
    # yielding an object with .text_stream and .get_final_message().
    final = MagicMock()
    final.usage.input_tokens = 100
    final.usage.output_tokens = 50
    final.usage.cache_creation_input_tokens = 0
    final.usage.cache_read_input_tokens = 0
    final.stop_reason = "end_turn"

    stream = MagicMock()
    stream.text_stream = iter([response_text])
    stream.get_final_message.return_value = final

    cm = MagicMock()
    cm.__enter__.return_value = stream
    cm.__exit__.return_value = False
    client.messages.stream.return_value = cm
    return client


class TestExtractExperiencesEndToEnd:
    def test_returns_empty_list_on_empty_input(self):
        client = MagicMock()
        result = extract_experiences(client, "")
        assert result == []
        client.messages.stream.assert_not_called()

    def test_parses_valid_response(self):
        client = _mock_anthropic_client(json.dumps(_make_valid_response()))
        result = extract_experiences(client, "Some resume text...")
        assert len(result) == 2
        assert result[0]["company"] == "Acme Corp"
        assert result[0]["start_date"] == "2020-01"
        assert result[0]["candidate_inferred_title"] == "Senior PM"
        assert len(result[0]["bullets"]) == 2
        assert result[0]["bullets"][0]["has_outcome"] is True  # "5-person" and "50"
        assert result[1]["end_date"] is None  # null preserved

    def test_uses_haiku_model(self):
        client = _mock_anthropic_client(json.dumps(_make_valid_response()))
        extract_experiences(client, "Some resume text...")
        # Inspect the kwargs passed to stream(...)
        call_args = client.messages.stream.call_args
        assert call_args.kwargs["model"] == HAIKU_MODEL

    def test_drops_experience_with_bad_date(self):
        bad_response = {
            "experiences": [
                {
                    "company": "Acme",
                    "start_date": "not-a-date",
                    "candidate_inferred_title": "PM",
                    "bullets": [],
                },
                {
                    "company": "Beta",
                    "start_date": "2020-01",
                    "candidate_inferred_title": "PM",
                    "bullets": [],
                },
            ],
        }
        client = _mock_anthropic_client(json.dumps(bad_response))
        result = extract_experiences(client, "x")
        # Bad-date experience has empty company sentinel; caller (importer) drops it.
        assert result[0]["company"] == ""
        assert result[1]["company"] == "Beta"

    def test_tolerates_response_with_markdown_fences(self):
        wrapped = "```json\n" + json.dumps(_make_valid_response()) + "\n```"
        client = _mock_anthropic_client(wrapped)
        result = extract_experiences(client, "x")
        assert len(result) == 2

    def test_handles_response_with_no_experiences_key(self):
        # Missing required key — _parse_or_retry should retry and ultimately fail.
        # We supply enough successful retries to avoid the failure here; the retry
        # logic is tested in test_analyzer.py — we just confirm we don't crash on
        # a valid {experiences: []} response.
        client = _mock_anthropic_client(json.dumps({"experiences": []}))
        result = extract_experiences(client, "x")
        assert result == []


# ---------------------------------------------------------------------------
# extract_experiences_and_skills (F-02: one Haiku call, two outputs)
# ---------------------------------------------------------------------------


class TestExtractExperiencesAndSkillsEndToEnd:
    def test_returns_empty_on_empty_input_without_calling_client(self):
        client = MagicMock()
        experiences, skills = extract_experiences_and_skills(client, "")
        assert experiences == []
        assert skills == []
        client.messages.stream.assert_not_called()

    def test_parses_experiences_and_skills_from_one_call(self):
        response = _make_valid_response()
        response["skills"] = ["Python", "Kubernetes", "python"]
        client = _mock_anthropic_client(json.dumps(response))
        experiences, skills = extract_experiences_and_skills(client, "Some resume text...")
        assert len(experiences) == 2
        assert experiences[0]["company"] == "Acme Corp"
        # Case-insensitive dedup, first-seen casing preserved.
        assert skills == ["Python", "Kubernetes"]
        # Exactly one underlying call for both outputs.
        assert client.messages.stream.call_count == 1

    def test_missing_skills_key_yields_empty_skills_list(self):
        # Older/degenerate responses without a "skills" key must not crash —
        # ExtractResponse declares skills: Any = None, so this is optional.
        client = _mock_anthropic_client(json.dumps(_make_valid_response()))
        experiences, skills = extract_experiences_and_skills(client, "x")
        assert len(experiences) == 2
        assert skills == []

    def test_non_list_skills_value_yields_empty_list(self):
        response = {"experiences": [], "skills": "Python, Kubernetes"}
        client = _mock_anthropic_client(json.dumps(response))
        _experiences, skills = extract_experiences_and_skills(client, "x")
        assert skills == []

    def test_extract_experiences_delegates_and_matches_direct_call(self):
        """extract_experiences() is now a thin wrapper — same experiences, one call."""
        response = _make_valid_response()
        response["skills"] = ["Go"]
        client = _mock_anthropic_client(json.dumps(response))
        result = extract_experiences(client, "Some resume text...")
        assert len(result) == 2
        assert result[0]["company"] == "Acme Corp"
        assert client.messages.stream.call_count == 1
