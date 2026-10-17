"""The prompt half of item 140: the no-ids rule on the personas, and the supplied letter date.

The runtime half (a validator that rejects a leaked handle) is `tests/test_handle_guard.py`. These
tests pin that the rule reaches every persona that is shown ids or analysis prose, that a persona
with nothing to leak is left alone, and that both cover-letter prompts carry today's date from one
clock seam instead of asking the model to invent it.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

import analyzer
from analyzer import (
    _BASE_SYSTEM_PROMPTS,
    _COVER_LETTER_RULES_BLOCK,
    _NO_HANDLES_IN_PROSE_RULE,
    PROPOSAL_CRITIQUE_SYSTEM_PROMPT,
    _build_generate_prompt,
    _letter_date_block,
    _stable_user_prefix,
    generate_cover_letter_against_resume,
)
from tests.test_corpus_mode_prompt import _make_legacy_context


def _ctx() -> Any:
    return _make_legacy_context()


# The personas that are shown id-bearing markup or analysis prose that quotes it.
RULE_PERSONAS = [
    "SYSTEM_PROMPT",
    "EXTRACTION_SYSTEM_PROMPT",
    "CLARIFY_SYSTEM_PROMPT",
    "CLARIFY_ITERATION_SYSTEM_PROMPT",
    "PROPOSAL_CRITIQUE_SYSTEM_PROMPT",
    "RECOMMEND_SYSTEM_PROMPT",
    "RECOMMEND_SUMMARIES_SYSTEM_PROMPT",
    "RECOMMEND_EXPERIENCE_SUMMARIES_SYSTEM_PROMPT",
    "RECOMMEND_SKILLS_SYSTEM_PROMPT",
    "SUGGEST_SKILLS_SYSTEM_PROMPT",
    "SUGGEST_SKILLS_FROM_CORPUS_SYSTEM_PROMPT",
    "DRAFT_GAP_FILL_SYSTEM_PROMPT",
    "DRAFT_EXPERIENCE_SUMMARIES_SYSTEM_PROMPT",
    "DRAFT_SURGICAL_REFINEMENT_SYSTEM_PROMPT",
]
# Registered personas that ship no id handles (see EXEMPT_CALL_KINDS in test_handle_guard.py).
UNTOUCHED_PERSONAS = [
    "DRAFT_SUMMARY_SYSTEM_PROMPT",
    "PROMOTE_CLARIFICATION_SYSTEM_PROMPT",
    "SCOPE_CHECK_SYSTEM_PROMPT",
]


class TestNoHandlesRule:
    @pytest.mark.parametrize("name", RULE_PERSONAS)
    def test_rule_is_on_the_persona_and_in_the_registry(self, name: str) -> None:
        assert getattr(analyzer, name).endswith(_NO_HANDLES_IN_PROSE_RULE)
        assert _BASE_SYSTEM_PROMPTS[name] is getattr(analyzer, name)

    @pytest.mark.parametrize("name", UNTOUCHED_PERSONAS)
    def test_personas_with_nothing_to_leak_are_unchanged(self, name: str) -> None:
        # Control for the parametrised test above: the rule is added deliberately, not to everything.
        assert _NO_HANDLES_IN_PROSE_RULE not in getattr(analyzer, name)

    def test_rule_names_the_failure_and_carries_a_worked_pair(self) -> None:
        rule = _NO_HANDLES_IN_PROSE_RULE
        assert "NEVER IN PROSE" in rule
        assert "NOT OK:" in rule
        assert "OK:" in rule.replace("NOT OK:", "")

    def test_registry_covers_every_persona_that_carries_the_rule(self) -> None:
        carrying = {
            n for n, text in _BASE_SYSTEM_PROMPTS.items() if _NO_HANDLES_IN_PROSE_RULE in text
        }
        assert carrying == set(RULE_PERSONAS)

    def test_critique_example_no_longer_teaches_an_id_in_prose(self) -> None:
        assert "b41" not in PROPOSAL_CRITIQUE_SYSTEM_PROMPT


class TestLetterDate:
    @pytest.fixture(autouse=True)
    def _pin_clock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(analyzer, "_clock_today", lambda: date(2033, 7, 9))

    def test_block_format_has_no_zero_padded_day(self) -> None:
        assert _letter_date_block() == "<letter_date>July 9, 2033</letter_date>\n"

    def test_the_format_rule_points_at_the_block_and_has_a_worked_pair(self) -> None:
        assert "<letter_date>" in _COVER_LETTER_RULES_BLOCK
        assert "Never invent" in _COVER_LETTER_RULES_BLOCK
        assert "DATE —" in _COVER_LETTER_RULES_BLOCK

    def test_generate_prompt_carries_the_date_only_with_a_letter(self) -> None:
        with_cl, _ = _build_generate_prompt(_ctx(), {}, with_cover_letter=True)
        without_cl, _ = _build_generate_prompt(_ctx(), {}, with_cover_letter=False)
        assert "<letter_date>July 9, 2033</letter_date>" in with_cl
        assert "<letter_date>" not in without_cl

    def test_the_date_never_enters_the_cached_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ctx = _ctx()
        before = _stable_user_prefix(ctx)
        monkeypatch.setattr(analyzer, "_clock_today", lambda: date(2032, 4, 4))
        assert _stable_user_prefix(ctx) == before
        assert "2031" not in before and "letter_date" not in before

    def test_the_date_changes_with_the_clock_and_the_prompt_follows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Control: the date in the prompt tracks the seam, so the assertions above are not constants.
        monkeypatch.setattr(analyzer, "_clock_today", lambda: date(2032, 12, 25))
        prompt, _ = _build_generate_prompt(_ctx(), {}, with_cover_letter=True)
        assert "<letter_date>December 25, 2032</letter_date>" in prompt
        assert "July 9, 2033" not in prompt

    def test_the_dedicated_cover_letter_call_carries_the_date(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_parse(client: Any, prompt: str, **kwargs: Any) -> dict[str, Any]:
            seen["prompt"] = prompt
            return {"cover_letter_content": "x", "proofread_notes": []}

        monkeypatch.setattr(analyzer, "_parse_or_retry", fake_parse)
        generate_cover_letter_against_resume(None, _ctx(), {}, "resume text")  # type: ignore[arg-type]
        assert "<letter_date>July 9, 2033</letter_date>" in seen["prompt"]
