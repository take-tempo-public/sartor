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
from typing import ClassVar
from unittest.mock import patch

import pytest

from analyzer import (
    _COVER_LETTER_RULES_BLOCK,
    GENERATE_CORPUS_REQUIRED_KEYS,
    GENERATE_REQUIRED_KEYS,
    RECOMMEND_SYSTEM_PROMPT,
    _build_generate_prompt,
    _corpus_block,
    _stable_user_prefix,
    generate,
)


def _make_legacy_context() -> dict:
    return {
        "timestamp": "2026-05-12T00:00:00",
        "candidate": {
            "name": "Casey",
            "email": "casey@example.com",
            "phone": "",
            "linkedin_url": "",
            "website_url": "",
            "skills": ["Python"],
            "certifications": [],
            "education_summary": "",
            "notes": "",
            "profile_text": "",
        },
        "resume": {
            "format": "md",
            "sections": [],
            "text": "Resume text here.",
            "filename": "resume.md",
            "path": "",
        },
        "supplemental_resumes": [],
        "job_description": "Senior PM at Foo",
        "deterministic_analysis": {
            "jd_keywords": {},
            "resume_keywords": {},
            "keyword_overlap": {},
            "ats_warnings": [],
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
                {
                    "id": 100,
                    "text": "Led 5-person team.",
                    "tags": ["pm"],
                    "has_outcome": True,
                    "source": "primary:r.md",
                },
                {
                    "id": 101,
                    "text": "Defined roadmap.",
                    "tags": [],
                    "has_outcome": False,
                    "source": "primary:r.md",
                },
            ],
        },
    ]
    return ctx


# ---------------------------------------------------------------------------
# _corpus_block / _stable_user_prefix dispatch
# ---------------------------------------------------------------------------


class TestCorpusBlockEmission:
    def test_emits_experience_with_titles_and_bullets(self):
        corpus = [
            {
                "id": 1,
                "company": "Polaris",
                "location": "",
                "start_date": "2022-09",
                "end_date": None,
                "eligible_titles": [{"id": 10, "title": "Senior PM", "is_official": True}],
                "bullets": [
                    {
                        "id": 100,
                        "text": "Led team.",
                        "tags": [],
                        "has_outcome": True,
                        "source": "primary:r.md",
                    }
                ],
            }
        ]
        out = _corpus_block(corpus, iteration=0)
        assert '<career_corpus iteration="0">' in out
        assert 'id="e1"' in out
        assert 'company="Polaris"' in out
        assert 'dates="2022-09 → present"' in out
        assert '<eligible_title id="t10" official="true">Senior PM</eligible_title>' in out
        assert '<bullet id="b100" tags="" has_outcome="true">Led team.</bullet>' in out
        assert "</career_corpus>" in out

    def test_escapes_double_quotes_in_attributes(self):
        corpus = [
            {
                "id": 1,
                "company": 'Big "Quoted" Inc',
                "location": "",
                "start_date": "2020-01",
                "end_date": "2021-12",
                "eligible_titles": [],
                "bullets": [],
            }
        ]
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


class TestWebPresenceBlock:
    """PX-02 — the opt-in profile/website/portfolio scrape rides a DEDICATED
    <candidate_web_presence> block, separate from profile_text (the β.6
    positioning summary, carried by the vestigially-named
    <candidate_online_profile> block). Conditional ⇒ the empty path is
    byte-identical to the pre-PX-02 prefix (the analyze→generate cache + eval
    invariance both depend on this)."""

    def test_block_emitted_when_present(self):
        ctx = _make_legacy_context()
        ctx["candidate"]["online_profile_text"] = "Scraped LinkedIn headline + bio."
        prefix = _stable_user_prefix(ctx)
        assert "<candidate_web_presence>" in prefix
        assert "Scraped LinkedIn headline + bio." in prefix
        assert "</candidate_web_presence>" in prefix

    def test_absent_when_empty_byte_identical(self):
        """Empty online_profile_text must not perturb the cached prefix."""
        baseline = _stable_user_prefix(_make_legacy_context())
        ctx = _make_legacy_context()
        ctx["candidate"]["online_profile_text"] = ""
        assert _stable_user_prefix(ctx) == baseline
        assert "<candidate_web_presence>" not in _stable_user_prefix(ctx)

    def test_missing_key_byte_identical(self):
        """A pre-PX-02 saved context (no online_profile_text key at all) must
        still produce the baseline prefix — the analyzer reads via .get()."""
        baseline_ctx = _make_legacy_context()
        baseline = _stable_user_prefix(baseline_ctx)
        ctx = _make_legacy_context()
        ctx["candidate"].pop("online_profile_text", None)
        assert _stable_user_prefix(ctx) == baseline

    def test_distinct_from_positioning_summary_block(self):
        """Scrape (web_presence) and profile_text (positioning summary) are
        independent: both can be present, in their own blocks."""
        ctx = _make_legacy_context()
        ctx["candidate"]["profile_text"] = "Senior PM positioning summary."
        ctx["candidate"]["online_profile_text"] = "Scraped portfolio text."
        prefix = _stable_user_prefix(ctx)
        assert "<candidate_online_profile>" in prefix
        assert "Senior PM positioning summary." in prefix
        assert "<candidate_web_presence>" in prefix
        assert "Scraped portfolio text." in prefix


# ---------------------------------------------------------------------------
# generate() — required key dispatch
# ---------------------------------------------------------------------------


def _mock_llm_call(captured: dict, fake_response: dict):
    """Build a fake _call_llm that records the kwargs it received."""

    def fake(
        client,
        prompt,
        *,
        cached_user_prefix,
        call_kind,
        username,
        run_id,
        system_prompt="",
        **kwargs,
    ):
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
            "essential_skills": [],
            "keyword_placement": [],
            "suggestions": [],
            "overall_strategy": "",
            "professional_vocabulary": [],
        }
        captured: dict = {}
        fake_response = {
            "resume_content": "x",
            "cover_letter_content": "y",
            "changes_made": [],
            "proofread_notes": [],
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
            "essential_skills": [],
            "keyword_placement": [],
            "suggestions": [],
            "overall_strategy": "",
            "professional_vocabulary": [],
        }
        captured: dict = {}
        fake_response = {
            "resume_content": "x",
            "cover_letter_content": "y",
            "changes_made": [],
            "proofread_notes": [],
            "selected_bullets": [
                {"experience_id": "e1", "chosen_title_id": "t10", "bullet_ids_in_order": ["b100"]}
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

    def test_corpus_mode_block_documents_title_pin_rule(self, monkeypatch):
        """feat/compose-add-title — the corpus_mode instructions tell the model
        that a pinned <eligible_title> MUST be used (the generate half of the
        per-JD title pin). This is the PROMPT_VERSION-bumping change."""
        ctx = _make_corpus_context()
        analysis = {
            "essential_skills": [],
            "keyword_placement": [],
            "suggestions": [],
            "overall_strategy": "",
            "professional_vocabulary": [],
        }
        captured: dict = {}
        fake_response = {
            "resume_content": "x",
            "cover_letter_content": "y",
            "changes_made": [],
            "proofread_notes": [],
            "selected_bullets": [],
            "proposed_new_bullets": [],
            "proposed_experience_titles": [],
        }
        with patch("analyzer._call_llm", _mock_llm_call(captured, fake_response)):
            generate(None, ctx, analysis, username="u", run_id="r")
        assert "the candidate has CHOSEN it for this application" in captured["prompt"]

    # -- v1.0.8 walkthrough generation-quality (PROMPT_VERSION 2026-07-01.1) --

    _ANALYSIS: ClassVar[dict] = {
        "essential_skills": [],
        "keyword_placement": [],
        "suggestions": [],
        "overall_strategy": "",
        "professional_vocabulary": [],
    }
    _FAKE: ClassVar[dict] = {
        "resume_content": "x",
        "cover_letter_content": "y",
        "changes_made": [],
        "proofread_notes": [],
        "selected_bullets": [],
        "proposed_new_bullets": [],
        "proposed_experience_titles": [],
    }

    def _run(self, ctx):
        captured: dict = {}
        with patch("analyzer._call_llm", _mock_llm_call(captured, self._FAKE)):
            generate(None, ctx, self._ANALYSIS, username="u", run_id="r")
        return captured["prompt"]

    def test_corpus_prompt_has_per_role_coverage_rule(self):
        """C1: the corpus prompt forbids leaving a role that HAS bullets empty."""
        prompt = self._run(_make_corpus_context())
        assert "COVERAGE" in prompt
        assert "never zero a role out" in prompt.lower()

    def test_grounding_check_forbids_tenure_fabrication(self):
        """E5: the grounding check names the invented '10 years' tenure failure."""
        prompt = self._run(_make_corpus_context())
        assert "10 years of end-to-end product ownership" in prompt
        assert "NEVER assert a years-of-experience" in prompt

    def test_refine_injects_current_resume_draft_only_when_edited(self):
        """E2: iteration>0 with edits carries the draft (so edits survive refine);
        iteration 0 does not (byte-identical default path)."""
        assert "<current_resume_draft>" not in self._run(_make_corpus_context())

        ctx = _make_corpus_context()
        ctx["iteration"] = 1
        ctx["edited_resume_text"] = "# Jane\n## Experience\n### Polaris\n- My hand-added bullet."
        prompt = self._run(ctx)
        assert "<current_resume_draft>" in prompt
        assert "My hand-added bullet." in prompt

    def test_multi_role_clarification_attribution(self):
        """H1: a clarification answer spanning multiple roles must split per role."""
        ctx = _make_corpus_context()
        ctx["clarification_questions"] = [
            {"id": "q1", "kind": "context_probe", "text": "Where did you lead teams?"}
        ]
        ctx["clarifications"] = {"q1": "At Polaris and at Acme I led delivery teams."}
        prompt = self._run(ctx)
        assert "ATTRIBUTE each part to ITS role" in prompt

    def test_summary_rule_asks_for_two_sentences(self):
        """Richness: the weak one-sentence summary rule is replaced by a targeted
        two-sentence positioning paragraph."""
        prompt = self._run(_make_corpus_context())
        assert "TWO-SENTENCE positioning" in prompt

    def test_skills_section_is_a_required_rule(self):
        """Richness: a `## Skills` section is now an explicit rule, not just an
        example heading — the fix for 'no skills in any preview'."""
        prompt = self._run(_make_corpus_context())
        assert "## Skills" in prompt
        assert "Skills are short noun phrases" in prompt

    def test_corpus_grounding_blesses_summary_and_skills(self):
        """The corpus verbatim-bullet grounding must explicitly NOT suppress the
        Summary paragraph and Skills list (previously they read as forbidden
        'other bullets' and the model dropped them)."""
        prompt = self._run(_make_corpus_context())
        assert "are NOT resume bullets and are EXPECTED sections" in prompt

    def test_corpus_response_missing_selected_bullets_raises(self, monkeypatch):
        """When career_corpus is set, the response MUST include selected_bullets
        + proposed_new_bullets + proposed_experience_titles. Missing any of these
        triggers _parse_or_retry's missing-key validation."""
        from analyzer import LLMResponseError

        ctx = _make_corpus_context()
        analysis = {
            "essential_skills": [],
            "keyword_placement": [],
            "suggestions": [],
            "overall_strategy": "",
            "professional_vocabulary": [],
        }
        # Response that's valid for the legacy schema but missing the corpus keys
        incomplete_response = {
            "resume_content": "x",
            "cover_letter_content": "y",
            "changes_made": [],
            "proofread_notes": [],
        }
        captured: dict = {}
        with (
            patch("analyzer._call_llm", _mock_llm_call(captured, incomplete_response)),
            pytest.raises(LLMResponseError) as excinfo,
        ):
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
            "selected_bullets",
            "proposed_new_bullets",
            "proposed_experience_titles",
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
        assert "Led 5-person team." in prefix  # recommended → kept
        assert "Defined roadmap." not in prefix  # non-recommended → dropped

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

    def test_unrecommended_role_keeps_its_bullets_not_starved(self):
        """Anti-starvation floor: when recommendations exist for SOME roles, a role
        with NO curation signal (no recommendation, pin, or added) keeps its active
        bullets instead of collapsing to a title-only entry — the fix for the
        reported '1 weak bullet per role' / empty-role bug. Recommended roles still
        narrow; un-recommended roles pass through so generate's COVERAGE rule can
        pick their strongest. This also aligns generate with the Compose preview,
        which already keeps all active bullets for an un-recommended role."""
        ctx = _make_corpus_context()
        # A SECOND experience that will NOT be recommended.
        ctx["career_corpus"].append(
            {
                "id": 2,
                "company": "Vega",
                "location": "",
                "start_date": "2019-01",
                "end_date": "2022-08",
                "eligible_titles": [{"id": 20, "title": "PM", "is_official": True}],
                "bullets": [
                    {
                        "id": 200,
                        "text": "Shipped mobile app to 1M users.",
                        "tags": [],
                        "has_outcome": True,
                        "source": "primary:r.md",
                    },
                    {
                        "id": 201,
                        "text": "Ran discovery interviews.",
                        "tags": [],
                        "has_outcome": False,
                        "source": "primary:r.md",
                    },
                ],
            }
        )
        # Recommend ONLY exp 1 (bullet 100); exp 2 gets no recommendation at all.
        ctx["llm_recommendations"] = {"1": {"bullet_ids": [100], "rationale": "x"}}
        prefix = _stable_user_prefix(ctx)
        # Exp 1 (curated) still narrows to its recommendation.
        assert "Led 5-person team." in prefix
        assert "Defined roadmap." not in prefix
        # Exp 2 (no signal) survives in full — never starved to title-only.
        assert "Shipped mobile app to 1M users." in prefix
        assert "Ran discovery interviews." in prefix


class TestRecommendPromptGenerous:
    """The Compose recommender must be generous + metric-first and never zero
    out a role — the fix for '1 weak bullet per role, metrics dropped'."""

    def test_recommend_is_generous_and_metric_first(self):
        assert "Be generous, not stingy" in RECOMMEND_SYSTEM_PROMPT
        assert "Never zero out a role" in RECOMMEND_SYSTEM_PROMPT
        assert "has_outcome" in RECOMMEND_SYSTEM_PROMPT  # metric preference

    def test_recommend_drops_stingy_language(self):
        # The old "down to 1 / soft ceiling / recruiters skim" stinginess is gone.
        assert "down to 1" not in RECOMMEND_SYSTEM_PROMPT
        assert "soft ceiling" not in RECOMMEND_SYSTEM_PROMPT


class TestBulletOrderHonored:
    """feat/bullet-drag-reorder — composition_overrides.bullet_order reorders
    the <career_corpus> bullets that reach generate(). Present ⇒ authoritative;
    absent/empty ⇒ default path byte-identical (the analyze→generate cache stays
    warm). This reorders DATA, not the prompt template (no PROMPT_VERSION bump)."""

    def _index_of(self, prefix: str, bullet_id: int) -> int:
        idx = prefix.find(f'id="b{bullet_id}"')
        assert idx != -1, f"b{bullet_id} not emitted"
        return idx

    def test_bullet_order_reorders_bullets(self):
        ctx = _make_corpus_context()  # corpus order: 100 then 101
        ctx["composition_overrides"] = {"bullet_order": {"1": [101, 100]}}
        prefix = _stable_user_prefix(ctx)
        assert self._index_of(prefix, 101) < self._index_of(prefix, 100)

    def test_unlisted_bullets_go_to_end(self):
        ctx = _make_corpus_context()
        ctx["career_corpus"][0]["bullets"].append(
            {
                "id": 102,
                "text": "Shipped launch.",
                "tags": [],
                "has_outcome": True,
                "source": "primary:r.md",
            }
        )
        # Order names 102 then 100; 101 is unlisted → must land at the END,
        # never silently re-sorted away (the drawer-added-later edge case).
        ctx["composition_overrides"] = {"bullet_order": {"1": [102, 100]}}
        prefix = _stable_user_prefix(ctx)
        assert (
            self._index_of(prefix, 102) < self._index_of(prefix, 100) < self._index_of(prefix, 101)
        )

    def test_absent_bullet_order_is_default_corpus_order(self):
        prefix = _stable_user_prefix(_make_corpus_context())
        assert self._index_of(prefix, 100) < self._index_of(prefix, 101)

    def test_empty_bullet_order_byte_identical(self):
        """An empty bullet_order (full reset) must not perturb the cached
        prefix — guards the analyze→generate prompt cache."""
        baseline = _stable_user_prefix(_make_corpus_context())
        ctx = _make_corpus_context()
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "bullet_order": {},
        }
        assert _stable_user_prefix(ctx) == baseline

    def test_string_and_int_experience_keys_both_accepted(self):
        """JSON persists keys as strings; defensive int keys also resolve."""
        ctx = _make_corpus_context()
        ctx["composition_overrides"] = {"bullet_order": {1: [101, 100]}}
        prefix = _stable_user_prefix(ctx)
        assert self._index_of(prefix, 101) < self._index_of(prefix, 100)


class TestTitlePinEmission:
    """feat/compose-add-title — composition_overrides.pinned_title_ids marks the
    chosen <eligible_title pinned="true"> in the cached prefix. Absent/empty ⇒
    byte-identical (the title pin never busts the analyze→generate cache for
    users who didn't pin a title — exactly like bullet pins)."""

    def test_pinned_title_emits_pinned_attr(self):
        ctx = _make_corpus_context()
        ctx["composition_overrides"] = {"pinned_title_ids": {"1": 11}}
        prefix = _stable_user_prefix(ctx)
        assert (
            '<eligible_title id="t11" official="false" pinned="true">'
            "AI Product Lead</eligible_title>"
        ) in prefix
        # The non-pinned sibling title carries no pin attr.
        assert ('<eligible_title id="t10" official="true">Senior PM</eligible_title>') in prefix

    def test_no_pin_no_attr(self):
        prefix = _stable_user_prefix(_make_corpus_context())
        assert 'pinned="true"' not in prefix

    def test_empty_pinned_title_ids_byte_identical(self):
        baseline = _stable_user_prefix(_make_corpus_context())
        ctx = _make_corpus_context()
        ctx["composition_overrides"] = {
            "pinned": [],
            "excluded": [],
            "added": [],
            "pinned_title_ids": {},
        }
        assert _stable_user_prefix(ctx) == baseline

    def test_pin_matched_by_title_id_regardless_of_key_shape(self):
        """The pin is flattened to its title-id values, so the experience-key
        shape (str vs int) is immaterial — both resolve the same."""
        for key in ("1", 1):
            ctx = _make_corpus_context()
            ctx["composition_overrides"] = {"pinned_title_ids": {key: 11}}
            prefix = _stable_user_prefix(ctx)
            assert 'id="t11" official="false" pinned="true"' in prefix


# ---------------------------------------------------------------------------
# PV-3 — cover-letter worked OK/NOT-OK opener+close examples
# ---------------------------------------------------------------------------


class TestCoverLetterWorkedExamples:
    """PV-3 (2026-06-23.1): the cover-letter contract gained a WORKED EXAMPLES
    sub-block (OK/NOT-OK pairs for the OPENER and CLOSE) to reinforce adherence
    to the existing throat-clearing/hedging bans — the documented v1.0.3 tone
    lapse was an adherence slip, and a worked example is the project's standard
    fix (AGENTS.md). Assert on the scaffold tokens, NOT the example sentences,
    so finalizing the wording never churns this test."""

    _ANALYSIS: ClassVar[dict] = {}

    def test_block_contains_worked_examples_section(self):
        block = _COVER_LETTER_RULES_BLOCK
        assert "WORKED EXAMPLES" in block
        assert "OPENER" in block
        assert "CLOSE" in block
        # one OK and one NOT OK per surface (opener + close)
        assert block.count("NOT OK:") >= 2
        assert block.count("OK:") >= 4  # "NOT OK:" also contains "OK:"

    def test_block_present_when_cover_letter_enabled(self):
        prompt, _ = _build_generate_prompt(
            _make_legacy_context(),
            self._ANALYSIS,
            with_cover_letter=True,
        )
        assert "<cover_letter_rules>" in prompt
        assert "WORKED EXAMPLES" in prompt

    def test_block_absent_when_cover_letter_disabled(self):
        prompt, _ = _build_generate_prompt(
            _make_legacy_context(),
            self._ANALYSIS,
            with_cover_letter=False,
        )
        assert "<cover_letter_rules>" not in prompt
        assert "WORKED EXAMPLES" not in prompt
