"""Tests for the Phase B.2 prompt-shape switch.

When `context_set["career_corpus"]` is populated:
- `_stable_user_prefix` emits a `<career_corpus>` XML block in place of the
  legacy `<resume>` + `<supplemental_resumes>` blocks
- `generate()` injects a `<corpus_mode>` instruction block and demands the
  extended output schema (`selected_bullets`, `proposed_new_bullets`,
  `proposed_experience_titles`)
- The legacy path (no `career_corpus`) produces byte-identical output to
  prior versions
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from analyzer import (
    GENERATE_CORPUS_REQUIRED_KEYS,
    GENERATE_REQUIRED_KEYS,
    _corpus_block,
    _stable_user_prefix,
    generate,
)


def _make_legacy_context() -> dict:
    return {
        "timestamp": "2026-05-12T00:00:00",
        "candidate": {
            "name": "Casey", "email": "casey@example.com",
            "phone": "", "linkedin_url": "", "website_url": "",
            "skills": ["Python"], "certifications": [],
            "education_summary": "", "notes": "",
            "profile_text": "",
        },
        "resume": {
            "format": "md", "sections": [], "text": "Resume text here.",
            "filename": "resume.md", "path": "",
        },
        "supplemental_resumes": [],
        "job_description": "Senior PM at Foo",
        "deterministic_analysis": {
            "jd_keywords": {}, "resume_keywords": {},
            "keyword_overlap": {}, "ats_warnings": [],
        },
    }


def _make_corpus_context() -> dict:
    ctx = _make_legacy_context()
    ctx["career_corpus"] = [
        {
            "id": 1,
            "company": "Polaris",
            "location": "Remote",
            "start_date": "2022-09",
            "end_date": None,
            "eligible_titles": [
                {"id": 10, "title": "Senior PM", "is_official": True},
                {"id": 11, "title": "AI Product Lead", "is_official": False},
            ],
            "bullets": [
                {"id": 100, "text": "Led 5-person team.", "tags": ["pm"],
                 "has_outcome": True, "source": "primary:r.md"},
                {"id": 101, "text": "Defined roadmap.", "tags": [],
                 "has_outcome": False, "source": "primary:r.md"},
            ],
        },
    ]
    return ctx


# ---------------------------------------------------------------------------
# _corpus_block / _stable_user_prefix dispatch
# ---------------------------------------------------------------------------


class TestCorpusBlockEmission:
    def test_emits_experience_with_titles_and_bullets(self):
        corpus = [{
            "id": 1, "company": "Polaris", "location": "",
            "start_date": "2022-09", "end_date": None,
            "eligible_titles": [{"id": 10, "title": "Senior PM", "is_official": True}],
            "bullets": [{"id": 100, "text": "Led team.", "tags": [],
                        "has_outcome": True, "source": "primary:r.md"}],
        }]
        out = _corpus_block(corpus, iteration=0)
        assert '<career_corpus iteration="0">' in out
        assert 'id="e1"' in out
        assert 'company="Polaris"' in out
        assert 'dates="2022-09 → present"' in out
        assert '<eligible_title id="t10" official="true">Senior PM</eligible_title>' in out
        assert '<bullet id="b100" tags="" has_outcome="true">Led team.</bullet>' in out
        assert "</career_corpus>" in out

    def test_escapes_double_quotes_in_attributes(self):
        corpus = [{
            "id": 1, "company": 'Big "Quoted" Inc', "location": "",
            "start_date": "2020-01", "end_date": "2021-12",
            "eligible_titles": [], "bullets": [],
        }]
        out = _corpus_block(corpus, iteration=0)
        assert 'company="Big &quot;Quoted&quot; Inc"' in out

    def test_iteration_attribute_propagates(self):
        out = _corpus_block([], iteration=3)
        assert 'iteration="3"' in out


class TestStableUserPrefixDispatch:
    def test_legacy_path_emits_resume_block(self):
        ctx = _make_legacy_context()
        prefix = _stable_user_prefix(ctx)
        assert "<resume filename=" in prefix
        assert "Resume text here." in prefix
        assert "<career_corpus" not in prefix

    def test_corpus_path_emits_career_corpus_block_not_resume(self):
        ctx = _make_corpus_context()
        prefix = _stable_user_prefix(ctx)
        assert "<career_corpus" in prefix
        assert "Led 5-person team." in prefix
        assert "AI Product Lead" in prefix
        # Legacy <resume> block must be ABSENT in corpus mode
        assert "<resume filename=" not in prefix
        # Supplemental block should also be absent (corpus is unified)
        assert "<supplemental_resumes>" not in prefix
        assert "<historical_resumes>" not in prefix

    def test_corpus_path_keeps_candidate_profile_block(self):
        ctx = _make_corpus_context()
        prefix = _stable_user_prefix(ctx)
        # candidate_profile is independent of corpus/legacy mode
        assert "<candidate_profile>" in prefix
        assert "Name: Casey" in prefix


# ---------------------------------------------------------------------------
# generate() — required key dispatch
# ---------------------------------------------------------------------------


def _mock_llm_call(captured: dict, fake_response: dict):
    """Build a fake _call_llm that records the kwargs it received."""

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id,
            system_prompt="", **kwargs):
        captured["prompt"] = prompt
        captured["cached_user_prefix"] = cached_user_prefix
        captured["call_kind"] = call_kind
        captured["model"] = kwargs.get("model")
        return json.dumps(fake_response)

    return fake


class TestGenerateDispatch:
    def test_legacy_context_uses_legacy_required_keys(self, monkeypatch):
        ctx = _make_legacy_context()
        analysis = {
            "essential_skills": [], "keyword_placement": [],
            "suggestions": [], "overall_strategy": "",
            "professional_vocabulary": [],
        }
        captured: dict = {}
        fake_response = {
            "resume_content": "x", "cover_letter_content": "y",
            "changes_made": [], "proofread_notes": [],
        }
        with patch("analyzer._call_llm", _mock_llm_call(captured, fake_response)):
            result = generate(None, ctx, analysis, username="u", run_id="r")
        # Legacy mode: prompt should NOT contain the corpus_mode block
        assert "<corpus_mode>" not in captured["prompt"]
        # selected_bullets etc. should not be in the output_format schema
        assert "selected_bullets" not in captured["prompt"]
        assert result == fake_response

    def test_corpus_context_injects_corpus_mode_block(self, monkeypatch):
        ctx = _make_corpus_context()
        analysis = {
            "essential_skills": [], "keyword_placement": [],
            "suggestions": [], "overall_strategy": "",
            "professional_vocabulary": [],
        }
        captured: dict = {}
        fake_response = {
            "resume_content": "x", "cover_letter_content": "y",
            "changes_made": [], "proofread_notes": [],
            "selected_bullets": [
                {"experience_id": "e1", "chosen_title_id": "t10",
                 "bullet_ids_in_order": ["b100"]}
            ],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        with patch("analyzer._call_llm", _mock_llm_call(captured, fake_response)):
            result = generate(None, ctx, analysis, username="u", run_id="r")
        # Corpus mode prompt MUST contain the corpus_mode block + new output keys
        assert "<corpus_mode>" in captured["prompt"]
        assert "selected_bullets" in captured["prompt"]
        assert "proposed_new_bullets" in captured["prompt"]
        assert "proposed_experience_titles" in captured["prompt"]
        # The cached prefix must be the corpus shape, not the legacy resume
        assert "<career_corpus" in captured["cached_user_prefix"]
        # Response passes through with all extended fields
        assert result["selected_bullets"][0]["chosen_title_id"] == "t10"

    def test_corpus_response_missing_selected_bullets_raises(self, monkeypatch):
        """When career_corpus is set, the response MUST include selected_bullets
        + proposed_new_bullets + proposed_experience_titles. Missing any of these
        triggers _parse_or_retry's missing-key validation."""
        from analyzer import LLMResponseError
        ctx = _make_corpus_context()
        analysis = {
            "essential_skills": [], "keyword_placement": [],
            "suggestions": [], "overall_strategy": "",
            "professional_vocabulary": [],
        }
        # Response that's valid for the legacy schema but missing the corpus keys
        incomplete_response = {
            "resume_content": "x", "cover_letter_content": "y",
            "changes_made": [], "proofread_notes": [],
        }
        captured: dict = {}
        with patch("analyzer._call_llm", _mock_llm_call(captured, incomplete_response)):
            with pytest.raises(LLMResponseError) as excinfo:
                generate(None, ctx, analysis, username="u", run_id="r")
        assert "selected_bullets" in str(excinfo.value.validation_error)


# ---------------------------------------------------------------------------
# Required keys constants
# ---------------------------------------------------------------------------


class TestRequiredKeySets:
    def test_corpus_keys_extend_legacy_keys(self):
        assert GENERATE_REQUIRED_KEYS.issubset(GENERATE_CORPUS_REQUIRED_KEYS)
        new_in_corpus = GENERATE_CORPUS_REQUIRED_KEYS - GENERATE_REQUIRED_KEYS
        assert new_in_corpus == {
            "selected_bullets", "proposed_new_bullets", "proposed_experience_titles",
        }


# ---------------------------------------------------------------------------
# Workstream H — effective-set filter when llm_recommendations is present
# ---------------------------------------------------------------------------


class TestCorpusEffectiveSetFilter:
    def test_no_recommendations_keeps_all_bullets(self):
        """Without llm_recommendations the prompt is unchanged
        (cache-stable for applications that don't use the recommend call)."""
        ctx = _make_corpus_context()
        prefix = _stable_user_prefix(ctx)
        assert "Led 5-person team." in prefix
        assert "Defined roadmap." in prefix

    def test_recommendations_restrict_to_effective_set(self):
        """Only recommended ∪ added ∪ pinned bullets are emitted; the
        non-recommended ones are dropped from the prompt entirely."""
        ctx = _make_corpus_context()
        ctx["llm_recommendations"] = {
            "1": {"bullet_ids": [100], "rationale": "x"},
        }
        prefix = _stable_user_prefix(ctx)
        assert "Led 5-person team." in prefix     # recommended → kept
        assert "Defined roadmap." not in prefix   # non-recommended → dropped

    def test_added_and_pinned_join_recommended(self):
        ctx = _make_corpus_context()
        ctx["llm_recommendations"] = {
            "1": {"bullet_ids": [100], "rationale": "x"},
        }
        ctx["composition_overrides"] = {"pinned": [], "excluded": [], "added": [101]}
        prefix = _stable_user_prefix(ctx)
        assert "Led 5-person team." in prefix
        assert "Defined roadmap." in prefix  # added via drawer

    def test_excluded_drops_even_when_recommended(self):
        ctx = _make_corpus_context()
        ctx["llm_recommendations"] = {
            "1": {"bullet_ids": [100, 101], "rationale": "x"},
        }
        ctx["composition_overrides"] = {"pinned": [], "excluded": [100], "added": []}
        prefix = _stable_user_prefix(ctx)
        assert "Led 5-person team." not in prefix  # excluded wins
        assert "Defined roadmap." in prefix

    def test_pinned_attr_survives_with_recommendations(self):
        ctx = _make_corpus_context()
        ctx["llm_recommendations"] = {
            "1": {"bullet_ids": [100], "rationale": "x"},
        }
        ctx["composition_overrides"] = {"pinned": [100], "excluded": [], "added": []}
        prefix = _stable_user_prefix(ctx)
        assert 'pinned="true"' in prefix
