"""Tests for `json_resume.md_to_json_resume` (Phase β.2).

Pins down the deterministic markdown → JSON Resume v1.0 parser. Cases
mirror the LLM-emitted shapes documented in the analyzer prompt
(analyzer.py:1174-1192) plus the kinds of malformed input we've seen
during this branch's normalizer iterations.

The parser is intentionally forgiving — missing sections produce
empty arrays, malformed lines land under meta.callback.unparsed
rather than raising.
"""

from __future__ import annotations

from json_resume import SCHEMA_URI, md_to_json_resume

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
        assert doc["meta"]["callback"]["version"] == "1.0"

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
        # callback.'s preferred contact separator is "·"
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
        md = (
            "# Jane Doe\n"
            "Engineer\n"
            "jane@example.com | janedoe.com\n"
        )
        doc = md_to_json_resume(md)
        # Bare-domain URL becomes the website (basics.url) with https
        # added; "Website" network classification routes it there.
        assert doc["basics"]["url"].startswith("https://")
        assert "janedoe.com" in doc["basics"]["url"]

    def test_github_profile(self):
        md = (
            "# Jane Doe\n"
            "Engineer\n"
            "jane@example.com | github.com/janedoe\n"
        )
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
        md = (
            "# Jane Doe\n"
            "\n"
            "## Skills\n"
            "Python · TypeScript · Postgres · Kubernetes\n"
        )
        doc = md_to_json_resume(md)
        assert len(doc["skills"]) == 4
        assert doc["skills"][0] == {"name": "Python"}
        assert doc["skills"][-1] == {"name": "Kubernetes"}

    def test_comma_separator(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Skills\n"
            "Python, TypeScript, Postgres\n"
        )
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
        md = (
            "# Jane Doe\n"
            "\n"
            "## Skills\n"
            "- Python\n"
            "- TypeScript\n"
        )
        doc = md_to_json_resume(md)
        names = [s["name"] for s in doc["skills"]]
        assert names == ["Python", "TypeScript"]

    def test_empty_section(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Skills\n"
        )
        doc = md_to_json_resume(md)
        assert doc["skills"] == []


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
        md = (
            "# Jane Doe\n"
            "\n"
            "## Certifications\n"
            "- AWS Solutions Architect Professional\n"
        )
        doc = md_to_json_resume(md)
        assert doc["certificates"][0]["name"] == "AWS Solutions Architect Professional"


# ---------------------------------------------------------------------
# Unknown sections → meta.callback.unparsed
# ---------------------------------------------------------------------


class TestUnknownSections:
    def test_unknown_section_goes_to_unparsed(self):
        md = (
            "# Jane Doe\n"
            "\n"
            "## Hobbies and Other Things\n"
            "Long-distance cycling.\n"
        )
        doc = md_to_json_resume(md)
        unparsed = doc["meta"]["callback"]["unparsed"]
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
        assert doc["meta"]["callback"]["unparsed"] == []

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
