"""Internal id handles in prose (item 140): the deterministic detectors in `hardening.py`.

Prompts ship ids (`e12`, `t4`, `b173`, `q2`, bare `id="44"`) so the model can name them in JSON
id fields. The detectors flag one only when the prompt actually shipped it, so ordinary tokens
("b2b", "S3", "Q1 2024") cannot cost a paid retry. Every negative case below has a control that
shows the same text WOULD hit under a looser rule, so the negative is not vacuous.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from hardening import (
    HandleSet,
    compute_letter_date,
    corpus_handles,
    find_leaked_handles,
    find_leaked_handles_in,
    handles_from_markup,
    merge_handles,
    source_handle_tokens,
)
from tests._controls import control


def _hs(*prefixed: str, bare: tuple[str, ...] = ()) -> HandleSet:
    return {"prefixed": frozenset(prefixed), "bare": frozenset(bare)}


class TestFindLeakedHandles:
    def test_flags_the_two_observed_leaks(self) -> None:
        hs = _hs("b173", "b180")
        assert find_leaked_handles(
            "implied by company name and b173 ('4M+ daily shipments')", hs
        ) == ["b173"]
        assert find_leaked_handles("Earlier, at b180, I led a refactor.", hs) == ["b180"]

    def test_flags_punctuation_neighbours(self) -> None:
        hs = _hs("b12", "q2", "e7")
        assert find_leaked_handles("(b12) per q2; see e7.", hs) == ["b12", "q2", "e7"]

    def test_reports_each_handle_once_in_order(self) -> None:
        assert find_leaked_handles("b9 then b4 then b9", _hs("b4", "b9")) == ["b9", "b4"]

    def test_ordinary_tokens_are_not_flagged(self) -> None:
        # Each of these is shaped like a handle but is not one the prompt shipped, or is not a bare token.
        hs = _hs("b2", "s3", "q1", "t2")
        for text in (
            "a b2b marketplace",
            "S3 buckets",
            "Q1 2024 revenue",
            "a t2.micro instance",
            "b12 shipped",
        ):
            assert find_leaked_handles(text, hs) == [], text

    def test_negative_cases_have_teeth(self) -> None:
        # Control: under a rule with no boundary and no lowercase-only rule the same texts WOULD hit.
        loose = re.compile(r"([A-Za-z]\d+)")
        hs = _hs("b2", "S3", "Q1", "t2")
        for text in ("a b2b marketplace", "S3 buckets", "Q1 2024 revenue", "a t2.micro instance"):
            control(
                any(t in hs["prefixed"] for t in loose.findall(text)),
                f"loose rule must hit {text!r}",
            )

    def test_handle_in_real_source_text_is_excluded(self) -> None:
        hs = _hs("t3")
        src = source_handle_tokens(["ran 40 t3 instances behind the queue"])
        control(find_leaked_handles("ran t3 nodes", hs) == ["t3"], "without exclusion it would hit")
        assert find_leaked_handles("ran t3 nodes", hs, src) == []

    def test_bare_ids_only_flag_inside_an_id_phrase(self) -> None:
        hs = _hs(bare=("44",))
        assert find_leaked_handles("see id 44 for detail", hs) == ["id 44"]
        assert find_leaked_handles("ID: 44", hs) == ["id 44"]
        assert find_leaked_handles("cut latency 44% across 44 services", hs) == []

    def test_empty_inputs(self) -> None:
        assert find_leaked_handles("", _hs("b1")) == []
        assert find_leaked_handles("b1", _hs()) == []


class TestFindLeakedHandlesIn:
    def test_walks_nested_prose_and_reports_paths(self) -> None:
        obj = {
            "comparison": {"gaps": ["fine", "implied by b173"]},
            "suggestions": [{"rationale": "uses e7"}],
        }
        found = find_leaked_handles_in(obj, _hs("b173", "e7"))
        assert found == [("comparison.gaps[1]", "b173"), ("suggestions[0].rationale", "e7")]

    def test_id_fields_are_legal(self) -> None:
        obj = {
            "selected_bullets": [{"experience_id": "e1", "bullet_ids_in_order": ["b12", "b14"]}],
            "evidence": {"bullet_id": "b12", "quote": "led the migration"},
            "recommendations": [{"id": "b12", "bullet_ids": ["b12"], "rationale": "solid"}],
        }
        assert find_leaked_handles_in(obj, _hs("b12", "b14", "e1")) == []

    def test_id_key_exemption_has_teeth(self) -> None:
        # Control: the same ids in a prose-named key DO leak, so the exemption is by key, not blanket.
        obj = {"rationale": "b12 and b14 show depth"}
        assert find_leaked_handles_in(obj, _hs("b12", "b14")) == [
            ("rationale", "b12"),
            ("rationale", "b14"),
        ]


class TestHandleCollection:
    def test_markup_prefixed_and_bare(self) -> None:
        markup = (
            '<career_corpus><experience id="e12" company="Acme">'
            '<eligible_title id="t4">Eng</eligible_title><bullet id="b173" tags="">x</bullet>'
            '</experience></career_corpus><summary_items><summary_item id="44">y</summary_item></summary_items>'
            '<role experience_id="7" title="z"></role>'
        )
        hs = handles_from_markup(markup)
        assert {"e12", "t4", "b173", "s44", "e7"} <= hs["prefixed"]
        assert {"12", "4", "173", "44", "7"} <= hs["bare"]

    def test_corpus_handles(self) -> None:
        corpus = [
            {
                "id": 3,
                "eligible_titles": [{"id": 5, "title": "Eng"}],
                "bullets": [{"id": 180, "text": "x"}, {"id": 181, "text": "y"}],
            }
        ]
        hs = corpus_handles(corpus, ["q1", ""])  # type: ignore[arg-type]
        assert hs["prefixed"] == frozenset({"e3", "t5", "b180", "b181", "q1"})
        assert "180" in hs["bare"]

    def test_merge(self) -> None:
        merged = merge_handles(_hs("b1", bare=("1",)), _hs("e2", bare=("2",)))
        assert merged["prefixed"] == frozenset({"b1", "e2"})
        assert merged["bare"] == frozenset({"1", "2"})


class TestComputeLetterDate:
    RUN = date(2026, 10, 17)

    def test_invented_date_is_a_mismatch(self) -> None:
        r = compute_letter_date(
            "March 2025\n\nHiring Manager\nAcme\n\nDear Hiring Manager,", self.RUN
        )
        assert r == {"found": "March 2025", "run_date": "October 2026", "matches_run_date": False}

    def test_correct_date_with_a_day_matches(self) -> None:
        r = compute_letter_date("October 17, 2026\nHiring Manager\n", self.RUN)
        assert r["found"] == "October 2026"
        assert r["matches_run_date"] is True

    def test_body_dates_are_not_the_letter_date(self) -> None:
        letter = "Dear Hiring Manager,\nHello.\nSecond line.\nIn March 2019, I led a migration."
        r = compute_letter_date(letter, self.RUN)
        assert r["found"] is None
        assert r["matches_run_date"] is None

    def test_body_date_control_would_hit_if_scanned_whole(self) -> None:
        # Control: scanning the whole letter WOULD find the body date, so the head-only rule is doing the work.
        letter = "Dear Hiring Manager,\nHello.\nSecond line.\nIn March 2019, I led a migration."
        assert re.search(r"March 2019", letter) is not None

    def test_no_date_at_all(self) -> None:
        assert compute_letter_date("", self.RUN)["matches_run_date"] is None


class TestEvalLeakReport:
    """`evals.runner._leak_report`: wider than the letter, and it names the upstream carrier."""

    def _report(self, **over: object) -> dict[str, Any]:
        from evals import runner

        context = {
            "resume": {"text": "Led the billing migration."},
            "job_description": "Backend engineer, shipments platform.",
            "career_corpus": [
                {
                    "id": 3,
                    "eligible_titles": [{"id": 5, "title": "Eng"}],
                    "bullets": [{"id": 180, "text": "x"}, {"id": 173, "text": "y"}],
                }
            ],
        }
        args: dict[str, object] = {
            "context": context,
            "analysis": {
                "overall_strategy": "Lead with b180.",
                "comparison": {"gaps": ["see b173"]},
            },
            "clarify_questions": [{"id": "q1", "text": "How big?"}],
            "clarify_reasoning": "",
            "result": {
                "resume_content": "Clean.",
                "cover_letter_content": "March 2025\n\nEarlier, at b180, I led it.",
            },
            "capture": {
                "bullets": {
                    "recommendations": [{"rationale": "b173 is strong", "bullet_ids": ["b173"]}]
                }
            },
            "run_date": date(2026, 10, 17),
        }
        args.update(over)
        return runner._leak_report(**args)  # type: ignore[arg-type]

    def test_scans_every_section_and_maps_the_carrier(self) -> None:
        r = self._report()
        sections = {f["section"] for f in r["findings"]}
        assert sections == {"analysis", "cover_letter_content", "recommend.bullets"}
        assert r["letter_carriers"] == {"b180": ["analysis"]}
        assert r["letter_date"]["matches_run_date"] is False

    def test_recommended_ids_in_id_fields_are_not_findings(self) -> None:
        r = self._report(analysis={}, result={"cover_letter_content": "", "resume_content": ""})
        assert [f["path"] for f in r["findings"]] == [
            "recommend.bullets.recommendations[0].rationale"
        ]

    def test_clean_run_reports_zero(self) -> None:
        r = self._report(
            analysis={"overall_strategy": "Lead with the migration."},
            result={
                "resume_content": "Clean.",
                "cover_letter_content": "October 17, 2026\n\nDear Hiring Manager,",
            },
            capture={},
        )
        assert r["total"] == 0
        assert r["letter_carriers"] == {}
        assert r["letter_date"]["matches_run_date"] is True


class TestSnippetAndLeaves:
    def test_snippet_is_centred_on_the_handle(self) -> None:
        from hardening import handle_snippet

        text = "x" * 80 + " implied by b173 (4M+ daily shipments) " + "y" * 80
        snip = handle_snippet(text, "b173", width=20)
        assert "b173" in snip
        assert len(snip) <= 20 + 4 + 20

    def test_snippet_for_a_bare_id_phrase_finds_the_number(self) -> None:
        from hardening import handle_snippet

        assert "44" in handle_snippet("see id 44 for detail", "id 44", width=10)

    def test_iter_prose_leaves_skips_id_keys_only(self) -> None:
        from hardening import iter_prose_leaves

        obj = {"rationale": "r", "bullet_ids": ["b1"], "nested": [{"id": "e1", "text": "t"}]}
        assert dict(iter_prose_leaves(obj)) == {"rationale": "r", "nested[0].text": "t"}
