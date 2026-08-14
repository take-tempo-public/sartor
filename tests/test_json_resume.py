"""Tests for `json_resume.md_to_json_resume` (Phase β.2).

Pins down the deterministic markdown → JSON Resume v1.0 parser. Cases
mirror the LLM-emitted shapes documented in the analyzer prompt
(analyzer.py:1174-1192) plus the kinds of malformed input we've seen
during this branch's normalizer iterations.

The parser is intentionally forgiving — missing sections produce
empty arrays, malformed lines land under meta.sartor.unparsed
rather than raising.
"""

from __future__ import annotations

import re

from json_resume import (
    EDUCATION_FIELD_SEPARATOR,
    SCHEMA_URI,
    apply_identity_override,
    education_position_text,
    format_date_range,
    format_month_year,
    is_month_precise,
    json_resume_to_markdown,
    md_to_json_resume,
    needs_month_precision,
    scrub_ats_unsafe,
    split_outside_brackets,
)

# ---------------------------------------------------------------------
# Empty / minimal
# ---------------------------------------------------------------------


class TestEmpty:
    def test_empty_string_returns_skeleton(self):
        doc = md_to_json_resume("")
        assert doc["$schema"] == SCHEMA_URI
        assert doc["basics"] == {}
        assert doc["work"] == []
        assert doc["skills"] == []
        assert doc["meta"]["sartor"]["version"] == "1.0"

    def test_whitespace_only_returns_skeleton(self):
        doc = md_to_json_resume("   \n\n   \n")
        assert doc["basics"] == {}
        assert doc["work"] == []

    def test_name_only(self):
        doc = md_to_json_resume("# Jane Doe\n")
        assert doc["basics"]["name"] == "Jane Doe"
        assert "label" not in doc["basics"]


# ---------------------------------------------------------------------
# Header block (basics)
# ---------------------------------------------------------------------


class TestHeaderBlock:
    def test_full_header_per_prompt_example(self):
        md = (
            "# Jane Doe\n"
            "Senior Site Reliability Engineer\n"
            "jane@example.com | (555) 010-2200 | linkedin.com/in/janedoe\n"
        )
        doc = md_to_json_resume(md)
        basics = doc["basics"]
        assert basics["name"] == "Jane Doe"
        assert basics["label"] == "Senior Site Reliability Engineer"
        assert basics["email"] == "jane@example.com"
        # Phone tolerates the (555) 010-2200 form
        assert "555" in basics["phone"]
        # LinkedIn parsed as a profile
        profiles = basics.get("profiles", [])
        assert any(p["network"] == "LinkedIn" for p in profiles)
        assert any("janedoe" in p["username"] for p in profiles)

    def test_separator_dot_middle(self):
        # sartor.'s preferred contact separator is "·"
        md = (
            "# Casey Rivera\n"
            "Principal Product Designer\n"
            "casey@example.com · 555-0142 · linkedin.com/in/casey-rivera-test\n"
        )
        doc = md_to_json_resume(md)
        basics = doc["basics"]
        assert basics["name"] == "Casey Rivera"
        assert basics["label"] == "Principal Product Designer"
        assert basics["email"] == "casey@example.com"

    def test_url_without_protocol_gets_https(self):
        md = "# Jane Doe\nEngineer\njane@example.com | janedoe.com\n"
        doc = md_to_json_resume(md)
        # Bare-domain URL becomes the website (basics.url) with https
        # added; "Website" network classification routes it there.
        assert doc["basics"]["url"].startswith("https://")
        assert "janedoe.com" in doc["basics"]["url"]

    def test_github_profile(self):
        md = "# Jane Doe\nEngineer\njane@example.com | github.com/janedoe\n"
        doc = md_to_json_resume(md)
        profiles = doc["basics"].get("profiles", [])
        assert any(p["network"] == "GitHub" for p in profiles)


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------


class TestSummary:
    def test_single_paragraph_summary(self):
        md = (
            "# Jane Doe\n"
            "Engineer\n"
            "jane@example.com\n"
            "\n"
            "## Summary\n"
            "Two-sentence positioning paragraph.\n"
        )
        doc = md_to_json_resume(md)
        assert doc["basics"]["summary"] == "Two-sentence positioning paragraph."

    def test_multi_line_summary_joined(self):
        md = (
            "# Jane Doe\n"
            "Engineer\n"
            "\n"
            "## Summary\n"
            "Senior SRE with a decade of\n"
            "platform reliability leadership.\n"
        )
        doc = md_to_json_resume(md)
        assert doc["basics"]["summary"] == (
            "Senior SRE with a decade of platform reliability leadership."
        )


# ---------------------------------------------------------------------
# Experience (work)
# ---------------------------------------------------------------------


class TestExperience:
    def test_full_experience_per_prompt_example(self):
        md = (
            "# Jane Doe\n"
            "SRE\n"
            "jane@example.com\n"
            "\n"
            "## Experience\n"
            "\n"
            "### Acme Cloud, Senior SRE\tMarch 2023 – present\n"
            "Player-coach across the platform team and on-call leadership.\n"
            "- Bullet one with a verb up front.\n"
            "- Bullet two integrating a JD keyword naturally.\n"
            "\n"
            "### Stratford Analytics, Production Engineer\tAugust 2021 – March 2023\n"
            "- Bullet one.\n"
        )
        doc = md_to_json_resume(md)
        work = doc["work"]
        assert len(work) == 2

        first = work[0]
        assert first["name"] == "Acme Cloud"
        assert first["position"] == "Senior SRE"
        assert first["startDate"] == "March 2023"
        assert first["endDate"] == "present"
        assert "Player-coach" in first["summary"]
        assert first["highlights"] == [
            "Bullet one with a verb up front.",
            "Bullet two integrating a JD keyword naturally.",
        ]

        second = work[1]
        assert second["name"] == "Stratford Analytics"
        assert second["position"] == "Production Engineer"
        assert second["startDate"] == "August 2021"
        assert second["endDate"] == "March 2023"
        assert second["highlights"] == ["Bullet one."]
        assert "summary" not in second

    def test_iso_date_format(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Experience\n"
            "### Polaris Cognition, Senior Designer\t2022-09 – present\n"
            "- Built a thing.\n"
        )
        doc = md_to_json_resume(md)
        assert doc["work"][0]["startDate"] == "2022-09"
        assert doc["work"][0]["endDate"] == "present"

    def test_em_dash_position_separator(self):
        # Some LLM emits use " — " instead of ", " between company + role
        md = (
            "# Jane\n"
            "\n"
            "## Experience\n"
            "### Polaris — Senior Engineer\t2022-09 – 2024-06\n"
            "- Did things.\n"
        )
        doc = md_to_json_resume(md)
        assert doc["work"][0]["name"] == "Polaris"
        assert doc["work"][0]["position"] == "Senior Engineer"


# ---------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------


class TestSkills:
    def test_dot_middle_separator(self):
        md = "# Jane Doe\n\n## Skills\nPython · TypeScript · Postgres · Kubernetes\n"
        doc = md_to_json_resume(md)
        assert len(doc["skills"]) == 4
        assert doc["skills"][0] == {"name": "Python"}
        assert doc["skills"][-1] == {"name": "Kubernetes"}

    def test_comma_separator(self):
        md = "# Jane Doe\n\n## Skills\nPython, TypeScript, Postgres\n"
        doc = md_to_json_resume(md)
        names = [s["name"] for s in doc["skills"]]
        assert names == ["Python", "TypeScript", "Postgres"]

    def test_grouped_bullet_form(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Skills\n"
            "- Languages: Python, TypeScript, Rust\n"
            "- Infra: Kubernetes, Terraform\n"
        )
        doc = md_to_json_resume(md)
        assert len(doc["skills"]) == 2
        assert doc["skills"][0]["name"] == "Languages"
        assert doc["skills"][0]["keywords"] == ["Python", "TypeScript", "Rust"]
        assert doc["skills"][1]["name"] == "Infra"
        assert doc["skills"][1]["keywords"] == ["Kubernetes", "Terraform"]

    def test_plain_bullet_form(self):
        md = "# Jane Doe\n\n## Skills\n- Python\n- TypeScript\n"
        doc = md_to_json_resume(md)
        names = [s["name"] for s in doc["skills"]]
        assert names == ["Python", "TypeScript"]

    def test_empty_section(self):
        md = "# Jane Doe\n\n## Skills\n"
        doc = md_to_json_resume(md)
        assert doc["skills"] == []

    def test_comma_inside_parenthetical_not_split(self):
        # item 15: a comma-list skill whose name itself contains a comma
        # inside parens must survive as one skill, not fragment.
        md = (
            "# Jane Doe\n\n## Skills\n"
            "Eval Framework Design (LLM-as-judge, rubric-based), "
            "Retrieval Systems (hybrid search, reciprocal-rank fusion)\n"
        )
        doc = md_to_json_resume(md)
        names = [s["name"] for s in doc["skills"]]
        assert names == [
            "Eval Framework Design (LLM-as-judge, rubric-based)",
            "Retrieval Systems (hybrid search, reciprocal-rank fusion)",
        ]

    def test_grouped_bullet_form_comma_inside_parenthetical_not_split(self):
        md = "# Jane Doe\n\n## Skills\n- Languages: Python (3.11, 3.12), Go\n"
        doc = md_to_json_resume(md)
        assert doc["skills"][0]["keywords"] == ["Python (3.11, 3.12)", "Go"]


# ---------------------------------------------------------------------
# split_outside_brackets — the shared depth-aware split primitive
# ---------------------------------------------------------------------


class TestSplitOutsideBrackets:
    def test_no_brackets_behaves_like_plain_split(self):
        got = split_outside_brackets("a, b, c", re.compile(r",\s*"))
        assert got == ["a", "b", "c"]

    def test_comma_inside_parens_not_split(self):
        got = split_outside_brackets(
            "Eval Framework Design (LLM-as-judge, rubric-based), Go",
            re.compile(r",\s*"),
        )
        assert got == ["Eval Framework Design (LLM-as-judge, rubric-based)", "Go"]

    def test_comma_inside_square_brackets_not_split(self):
        got = split_outside_brackets("Go [x, y], Rust", re.compile(r",\s*"))
        assert got == ["Go [x, y]", "Rust"]

    def test_nested_parens(self):
        got = split_outside_brackets("A (b (c, d) e), F", re.compile(r",\s*"))
        assert got == ["A (b (c, d) e)", "F"]

    def test_stray_closing_bracket_does_not_go_negative_depth(self):
        got = split_outside_brackets("Python), Go", re.compile(r",\s*"))
        assert got == ["Python)", "Go"]

    def test_unbalanced_opening_bracket_swallows_rest_of_string(self):
        got = split_outside_brackets("Python (advanced, Go", re.compile(r",\s*"))
        assert got == ["Python (advanced, Go"]

    def test_whitespace_required_delimiter_pattern_is_honored(self):
        # json_resume's single-paragraph pattern requires trailing whitespace —
        # the shared helper must not override a caller's own delimiter semantics.
        got = split_outside_brackets("a,b", re.compile(r"\s*[·•|,]\s+"))
        assert got == ["a,b"]


# ---------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------


class TestEducation:
    def test_education_entry(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Education\n"
            "### Polytechnic Institute of Test, MS Human-Computer Interaction\t2014 – 2016\n"
        )
        doc = md_to_json_resume(md)
        ed = doc["education"][0]
        assert ed["institution"] == "Polytechnic Institute of Test"
        assert ed["area"] == "MS Human-Computer Interaction"
        assert ed["startDate"] == "2014"
        assert ed["endDate"] == "2016"
        # An entry with no separator is all `area` — the pre-2026-08-13 on-disk
        # form and what a hand-written résumé produces. No phantom studyType.
        assert "studyType" not in ed


_EDU_FULL = {
    "institution": "State University",
    "area": "Bachelor of Science",  # corpus maps Education.degree here
    "studyType": "Computer Science",  # corpus maps Education.field here
    "startDate": "2010-09",
    "endDate": "2014-05",
}


class TestEducationStudyTypeRoundTrip:
    """`studyType` survives markdown serialization (`fix/b1-education-render`).

    Before this branch the field of study was dropped by BOTH halves of the
    round-trip — the emitter never wrote it and the parser had nowhere to put it
    (`docs/dev/diagnosis/b1-education-render.md` O-5). Each test below fails on
    the pre-fix tree.
    """

    @staticmethod
    def _doc(*education):
        return {"basics": {"name": "Jane Doe"}, "education": list(education)}

    def test_position_helper_joins_both_fields_in_order(self):
        assert education_position_text(_EDU_FULL) == (
            f"Bachelor of Science{EDUCATION_FIELD_SEPARATOR}Computer Science"
        )

    def test_position_helper_never_flips_the_pair(self):
        """Render-both, never-flip: `area` leads, `studyType` follows, always."""
        joined = education_position_text(_EDU_FULL)
        assert joined.index("Bachelor of Science") < joined.index("Computer Science")

    def test_separator_is_an_em_dash_not_the_date_en_dash(self):
        """The two separators must stay distinguishable — dates use EN (U+2013)."""
        assert EDUCATION_FIELD_SEPARATOR == " — "
        assert "–" not in EDUCATION_FIELD_SEPARATOR

    def test_emitted_header_carries_both_fields(self):
        md = json_resume_to_markdown(self._doc(_EDU_FULL))
        assert (
            "### State University, Bachelor of Science — Computer Science\t09/2010 – 05/2014"
        ) in md

    def test_study_type_survives_the_round_trip(self):
        back = md_to_json_resume(json_resume_to_markdown(self._doc(_EDU_FULL)))["education"][0]
        assert back["institution"] == "State University"
        assert back["area"] == "Bachelor of Science"
        assert back["studyType"] == "Computer Science"

    def test_round_trip_is_idempotent(self):
        md = json_resume_to_markdown(self._doc(_EDU_FULL))
        assert json_resume_to_markdown(md_to_json_resume(md)) == md

    def test_entry_without_study_type_serializes_exactly_as_before(self):
        """The common case must not gain a separator — no churn for existing docs."""
        without = {k: v for k, v in _EDU_FULL.items() if k != "studyType"}
        md = json_resume_to_markdown(self._doc(without))
        assert "### State University, Bachelor of Science\t09/2010 – 05/2014" in md
        assert EDUCATION_FIELD_SEPARATOR not in md
        assert "studyType" not in md_to_json_resume(md)["education"][0]

    def test_study_type_without_area_re_keys_to_area_and_stays_stable(self):
        """Documented asymmetry, pinned rather than left to surprise someone.

        With no `area` there is no separator to encode, so the value round-trips
        into `area`. It still RENDERS correctly (the field of study appears), and
        the cycle is idempotent. The corpus UI blocks an empty `institution` at
        both create and edit (`blueprints/corpus/career_assets.py:104-106,
        168-172` — both return 400), so "field without degree, institution
        present" is the asymmetric shape the product's own forms can produce.
        (`Education.institution` being `nullable=False` at the DB layer does
        NOT itself exclude an empty string — see the institution-LESS case
        pinned by `test_institution_less_entry_re_keys_studytype_into_area_on_emit`
        below, which the emitter can still be handed directly.)
        """
        only_study = {"institution": "State University", "studyType": "Computer Science"}
        md = json_resume_to_markdown(self._doc(only_study))
        assert "### State University, Computer Science" in md
        back = md_to_json_resume(md)["education"][0]
        assert back == {"institution": "State University", "area": "Computer Science"}
        assert json_resume_to_markdown(self._doc(back)) == md

    def test_institution_less_entry_re_keys_studytype_into_area_on_emit(self):
        """The institution-less collision the branch's refuter flagged (F1) — NOT a
        regression, pinned as a known limit rather than left to surprise someone.

        `education_position_text` emits `f"{area} — {studyType}"` as the entry's sole
        non-institution field. When `institution` is empty the emitted h3 is just that
        joined string, and `_split_h3_header`'s `" — "` fallback (`json_resume.py:
        455-456`) — which exists for `work`/`project` entries and predates this branch
        — treats it as the WHOLE name/position left segment: the joined
        `area — studyType` string re-parses into `institution=<area>, area=<studyType>`,
        and the original `studyType` is gone. This is a strict improvement over the
        pre-fix behavior, which dropped the value from the emitted markdown entirely
        (see `docs/dev/diagnosis/b1-education-render.md`, "Known limits"). Stable from
        the second cycle onward: the re-keyed shape is a fixed point of the round-trip.
        """
        only_area_and_study = {"area": "Bachelor of Science", "studyType": "Computer Science"}
        md = json_resume_to_markdown(self._doc(only_area_and_study))
        assert "### Bachelor of Science — Computer Science" in md
        back = md_to_json_resume(md)["education"][0]
        assert back == {"institution": "Bachelor of Science", "area": "Computer Science"}
        # Second cycle: a fixed point, not a further drift.
        back2 = md_to_json_resume(json_resume_to_markdown(self._doc(back)))["education"][0]
        assert back2 == back

    def test_normalizer_does_not_break_the_em_dash_header(self):
        """`_normalize_markdown` re-injects newlines at `- <Capital>` boundaries.

        The em dash is not in `_MD_BULLET_BOUNDARY_RE`'s class
        (`generator.py:_MD_BULLET_BOUNDARY_RE`), so the header must pass through
        whole rather than being split into a phantom bullet.
        """
        from generator import _normalize_markdown

        md = json_resume_to_markdown(self._doc(_EDU_FULL))
        assert _normalize_markdown(md) == md
        assert md_to_json_resume(_normalize_markdown(md))["education"][0]["studyType"] == (
            "Computer Science"
        )


# ---------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------


class TestCertifications:
    def test_one_per_line(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Certifications\n"
            "Nielsen Norman Group UX Master Certification\n"
            "Certified Scrum Product Owner\n"
        )
        doc = md_to_json_resume(md)
        names = [c["name"] for c in doc["certificates"]]
        assert "Nielsen Norman Group UX Master Certification" in names
        assert "Certified Scrum Product Owner" in names

    def test_bullet_form_strips_marker(self):
        md = "# Jane Doe\n\n## Certifications\n- AWS Solutions Architect Professional\n"
        doc = md_to_json_resume(md)
        assert doc["certificates"][0]["name"] == "AWS Solutions Architect Professional"


# ---------------------------------------------------------------------
# Unknown sections → meta.sartor.unparsed
# ---------------------------------------------------------------------


class TestUnknownSections:
    def test_unknown_section_goes_to_unparsed(self):
        md = "# Jane Doe\n\n## Hobbies and Other Things\nLong-distance cycling.\n"
        doc = md_to_json_resume(md)
        unparsed = doc["meta"]["sartor"]["unparsed"]
        assert len(unparsed) == 1
        assert unparsed[0]["section"] == "Hobbies and Other Things"
        assert "cycling" in unparsed[0]["raw"]


# ---------------------------------------------------------------------
# Full realistic round-trip
# ---------------------------------------------------------------------


class TestRealisticFull:
    def test_full_resume_parses_all_sections(self):
        md = (
            "# Casey Rivera\n"
            "Principal Product Designer\n"
            "casey@example.com · 555-0142 · linkedin.com/in/casey-rivera-test\n"
            "\n"
            "## Summary\n"
            "Principal-level designer with a decade of owning end-to-end UX.\n"
            "\n"
            "## Experience\n"
            "\n"
            "### Polaris Cognition, Senior Product Designer\t2022-09 – present\n"
            "- Built functional prototypes for AI-native tooling.\n"
            "- Designed interaction patterns for agentic pipelines.\n"
            "- Wrote the first internal style guide for AI-product UX.\n"
            "\n"
            "### Acme Robotics, Director of Product Design\t2020-04 – 2022-08\n"
            "- Built the design org from 2 to 11 designers.\n"
            "- Set the design language for the first consumer AR product.\n"
            "\n"
            "## Skills\n"
            "UX Strategy · Interaction Design · Figma · Design Systems\n"
            "\n"
            "## Certifications\n"
            "Nielsen Norman Group UX Master Certification\n"
            "\n"
            "## Education\n"
            "### Polytechnic Institute of Test, MS HCI\t2014 – 2016\n"
        )
        doc = md_to_json_resume(md)

        # Basics
        assert doc["basics"]["name"] == "Casey Rivera"
        assert doc["basics"]["label"] == "Principal Product Designer"
        assert doc["basics"]["email"] == "casey@example.com"
        assert doc["basics"]["summary"].startswith("Principal-level designer")

        # Work
        assert len(doc["work"]) == 2
        assert doc["work"][0]["name"] == "Polaris Cognition"
        assert len(doc["work"][0]["highlights"]) == 3

        # Skills
        assert len(doc["skills"]) == 4
        assert doc["skills"][0]["name"] == "UX Strategy"

        # Certificates
        assert doc["certificates"][0]["name"].startswith("Nielsen Norman")

        # Education
        assert doc["education"][0]["institution"] == "Polytechnic Institute of Test"

        # No unparsed content
        assert doc["meta"]["sartor"]["unparsed"] == []

    def test_idempotent_on_re_parse(self):
        """Parsing the same markdown twice produces identical structure."""
        md = (
            "# Jane\n"
            "Engineer\n"
            "jane@example.com\n"
            "\n"
            "## Experience\n"
            "### Acme, Senior SRE\t2023 – present\n"
            "- Did a thing.\n"
        )
        first = md_to_json_resume(md)
        second = md_to_json_resume(md)
        assert first == second


# ---------------------------------------------------------------------
# format_month_year / format_date_range (fix/output-identity-and-dates)
# ---------------------------------------------------------------------


class TestFormatMonthYear:
    def test_iso_year_month_becomes_mm_yyyy(self):
        assert format_month_year("2022-09") == "09/2022"

    def test_year_only_passes_through(self):
        assert format_month_year("2022") == "2022"

    def test_empty_and_none(self):
        assert format_month_year("") == ""
        assert format_month_year(None) == ""

    def test_non_iso_text_passes_through_unchanged(self):
        """A literal 'present'/'current' or hand-typed date is not ISO-shaped
        — best-effort passthrough rather than mangling it."""
        assert format_month_year("present") == "present"
        assert format_month_year("March 2020") == "March 2020"


class TestFormatDateRange:
    def test_closed_range_both_mm_yyyy(self):
        assert format_date_range("2022-09", "2023-05") == "09/2022 – 05/2023"

    def test_open_ended_renders_present(self):
        """The DB's NULL-end-date = current convention (db.models.Experience)
        renders as 'Present' — the mechanical bug this fix closes."""
        assert format_date_range("2022-09", None) == "09/2022 – Present"
        assert format_date_range("2022-09", "") == "09/2022 – Present"

    def test_no_iso_yyyy_mm_pattern_in_output(self):
        import re

        result = format_date_range("2022-09", "2023-05")
        assert not re.search(r"\d{4}-\d{2}", result)

    def test_missing_start_falls_back_to_end(self):
        assert format_date_range(None, "2023-05") == "05/2023"

    def test_both_missing_is_empty(self):
        assert format_date_range(None, None) == ""

    def test_year_only_range(self):
        assert format_date_range("2020", "2023") == "2020 – 2023"


# ---------------------------------------------------------------------
# Month precision (B2/ATS-conformance)
# ---------------------------------------------------------------------


class TestMonthPrecision:
    def test_is_month_precise_iso_year_month_only(self):
        assert is_month_precise("2022-09") is True
        assert is_month_precise("2022") is False
        assert is_month_precise("") is False
        assert is_month_precise(None) is False
        assert is_month_precise("present") is False
        assert is_month_precise("2022-9") is False  # not the ISO two-digit shape

    def test_needs_month_when_either_side_year_only(self):
        assert needs_month_precision("2020", "2022-05") is True
        assert needs_month_precision("2020-01", "2022") is True
        assert needs_month_precision("2020", "2022") is True

    def test_month_precise_and_open_ended_do_not_need_month(self):
        assert needs_month_precision("2020-01", "2022-05") is False
        # Falsy end = the DB's NULL-means-current convention — never blocks.
        assert needs_month_precision("2020-01", None) is False
        assert needs_month_precision("2020-01", "") is False

    def test_malformed_values_are_the_validators_jurisdiction(self):
        """Non-ISO junk neither blocks nor counts as precise — the rule targets
        imprecise dates; malformed ones belong to the create/edit validators."""
        assert needs_month_precision("March 2020", "present") is False


# ---------------------------------------------------------------------
# scrub_ats_unsafe (fix/output-identity-and-dates)
# ---------------------------------------------------------------------


class TestScrubAtsUnsafe:
    def test_strips_brackets_braces_quotes_backtick(self):
        doc = {"basics": {"summary": 'Shipped [v2] with {config} "quotes" and `code`.'}}
        out = scrub_ats_unsafe(doc)
        assert out["basics"]["summary"] == "Shipped v2 with config quotes and code."

    def test_preserves_comparison_operators(self):
        """'<50ms' has no closing '>' — not tag-shaped — must survive verbatim."""
        doc = {"work": [{"highlights": ["Cut p99 latency to <50ms."]}]}
        out = scrub_ats_unsafe(doc)
        assert out["work"][0]["highlights"][0] == "Cut p99 latency to <50ms."

    def test_preserves_plus_plus_and_hash(self):
        doc = {"skills": [{"name": "C++"}, {"name": "C#"}]}
        out = scrub_ats_unsafe(doc)
        assert [s["name"] for s in out["skills"]] == ["C++", "C#"]

    def test_strips_tag_shaped_html(self):
        doc = {"basics": {"summary": "Built a <b>bold</b> <script>alert(1)</script> feature."}}
        out = scrub_ats_unsafe(doc)
        assert "<b>" not in out["basics"]["summary"]
        assert "<script>" not in out["basics"]["summary"]
        assert "bold" in out["basics"]["summary"]

    def test_records_changed_strings_in_meta(self):
        doc = {"basics": {"name": "Ann [Q] Lee"}, "meta": {"sartor": {"version": "1.0"}}}
        out = scrub_ats_unsafe(doc)
        scrubbed = out["meta"]["sartor"]["ats_scrubbed"]
        assert len(scrubbed) == 1
        assert scrubbed[0]["before"] == "Ann [Q] Lee"
        assert scrubbed[0]["after"] == "Ann Q Lee"

    def test_no_meta_key_when_nothing_changed(self):
        doc = {"basics": {"name": "Clean Name"}}
        out = scrub_ats_unsafe(doc)
        assert "meta" not in out or "ats_scrubbed" not in out.get("meta", {}).get("sartor", {})

    def test_walks_nested_lists_and_dicts(self):
        doc = {
            "work": [
                {"name": "Acme [Inc]", "highlights": ['Led "the" launch.']},
            ]
        }
        out = scrub_ats_unsafe(doc)
        assert out["work"][0]["name"] == "Acme Inc"
        assert out["work"][0]["highlights"][0] == "Led the launch."

    def test_does_not_touch_schema_or_meta_bookkeeping(self):
        doc = {"$schema": "http://x/[v1]", "meta": {"sartor": {"unparsed": ["[stray]"]}}}
        out = scrub_ats_unsafe(doc)
        assert out["$schema"] == "http://x/[v1]"
        assert out["meta"]["sartor"]["unparsed"] == ["[stray]"]


# ---------------------------------------------------------------------
# apply_identity_override (fix/output-identity-and-dates)
# ---------------------------------------------------------------------


class TestApplyIdentityOverride:
    def test_none_identity_is_a_no_op(self):
        doc = {"basics": {"name": "Stale Name", "url": "https://stray-site.example"}}
        out = apply_identity_override(doc, None)
        assert out["basics"]["name"] == "Stale Name"
        assert out["basics"]["url"] == "https://stray-site.example"

    def test_overrides_replace_stale_markdown_identity(self):
        """The reported bug: a website in the parsed markdown that isn't in
        the candidate's DB record must never survive into basics."""
        doc = {
            "basics": {
                "name": "Old Name",
                "url": "https://stray-site.example",
                "email": "old@example.com",
            }
        }
        out = apply_identity_override(
            doc,
            {
                "name": "Real Name",
                "email": "real@example.com",
                "phone": "",
                "linkedin_url": "",
                "website_url": "",
            },
        )
        assert out["basics"]["name"] == "Real Name"
        assert out["basics"]["email"] == "real@example.com"
        # Candidate has no website on file -> the stray URL is CLEARED, not kept.
        assert "url" not in out["basics"]

    def test_clears_fields_absent_from_candidate(self):
        doc = {"basics": {"phone": "555-0100"}}
        out = apply_identity_override(doc, {"name": "Real Name"})
        assert "phone" not in out["basics"]

    def test_linkedin_replaces_all_profiles_wholesale(self):
        """Candidate has no GitHub/Twitter columns — any such profile the LLM
        parsed from the markdown is dropped, not merged."""
        doc = {
            "basics": {
                "profiles": [
                    {"network": "GitHub", "url": "https://github.com/stray"},
                    {"network": "LinkedIn", "url": "https://linkedin.com/in/stale"},
                ]
            }
        }
        out = apply_identity_override(doc, {"linkedin_url": "https://linkedin.com/in/real"})
        assert out["basics"]["profiles"] == [
            {
                "network": "LinkedIn",
                "url": "https://linkedin.com/in/real",
                "username": "real",
            }
        ]

    def test_no_linkedin_clears_profiles(self):
        doc = {"basics": {"profiles": [{"network": "GitHub", "url": "https://github.com/x"}]}}
        out = apply_identity_override(doc, {"name": "Real Name"})
        assert "profiles" not in out["basics"]
