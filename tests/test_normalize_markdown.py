"""Tests for generator._normalize_markdown.

The LLM occasionally collapses the entire resume into a single line with
no newlines between sections, headers, or bullets. This deterministic
P1 Hardening pass re-injects newlines around unambiguous markdown
markers so the downstream renderers (.md export + .docx writer) see
proper structure.

These tests pin down:
  - the four passes (h1/h2/h3 boundary, bullet boundary, h2-body, collapse)
  - idempotency on well-formed input
  - the documented out-of-scope case (h1 + subtitle + contact smush)
"""

from generator import _normalize_markdown


class TestHeaderBoundary:
    def test_inserts_blank_line_before_h2(self):
        out = _normalize_markdown("text## Summary heading")
        assert "text\n\n## Summary" in out

    def test_inserts_blank_line_before_h3(self):
        out = _normalize_markdown("Present### Acme, Engineer")
        assert "Present\n\n### Acme" in out

    def test_does_not_break_in_middle_of_hash_marker(self):
        # Should not insert between the two `#` of `##` or three of `###`.
        out = _normalize_markdown("foo## Bar baz")
        assert "#\n#" not in out
        assert "##\n#" not in out

    def test_idempotent_on_well_formed_input(self):
        well_formed = "# Name\n\n## Summary\n\nBody text.\n"
        assert _normalize_markdown(well_formed) == well_formed


class TestBulletBoundary:
    def test_splits_bullet_after_period(self):
        out = _normalize_markdown("bullet one.- Built a thing")
        assert "one.\n- Built" in out

    def test_splits_bullet_after_section_title_tab_date(self):
        # The pattern after an h3 line: 'Present- Bullet starts' (the date
        # ends in text without a period; the bullet starts with capital).
        out = _normalize_markdown("Present- Built it")
        assert "Present\n- Built" in out

    def test_does_not_split_hyphenated_word(self):
        # 'front-end' should never be treated as a bullet boundary.
        out = _normalize_markdown("worked on front-end systems")
        assert "front-end" in out
        assert "front\n-end" not in out

    def test_requires_capital_after_bullet_marker(self):
        # A lowercase letter after '- ' isn't a bullet boundary.
        out = _normalize_markdown("worked- on systems")
        # No newline inserted — 'on' is lowercase.
        assert "worked\n- on" not in out


class TestH2BodyBoundary:
    def test_splits_between_h2_title_and_body(self):
        out = _normalize_markdown("## SummaryPrincipal engineer")
        assert "## Summary\n\nPrincipal" in out

    def test_splits_with_capital_capital_body(self):
        # '## SkillsUX Strategy' — body word starts UX (two capitals).
        out = _normalize_markdown("## SkillsUX Strategy")
        assert "## Skills\n\nUX Strategy" in out

    def test_does_not_split_h3_entries(self):
        # H3 job titles can legitimately have multiple capitalized words
        # ('Polaris Cognition, Senior Product Designer'). Don't break them.
        out = _normalize_markdown("### Polaris Cognition, Senior Engineer")
        # The h3 line stays intact (no inserted break inside it).
        assert "### Polaris Cognition" in out
        assert "Polaris\n\nCognition" not in out


class TestCollapseNewlines:
    def test_triple_newlines_become_double(self):
        out = _normalize_markdown("a\n\n\n\nb")
        assert "\n\n\n" not in out

    def test_strips_trailing_whitespace(self):
        out = _normalize_markdown("# Name\n\n\n\n")
        # Trailing collapse + final \n added.
        assert out.endswith("\n")
        assert not out.endswith("\n\n\n")


class TestEmpty:
    def test_empty_string_passes_through(self):
        assert _normalize_markdown("") == ""

    def test_none_passes_through(self):
        # Defensive: the function is annotated for str but be safe.
        assert _normalize_markdown(None) is None


class TestFullRealisticCase:
    def test_smushed_resume_gets_structured(self):
        smushed = (
            "# Casey Rivera"
            "Principal Product Designer"
            "casey.rivera@example.com | 555-0142"
            "## Summary"
            "Principal-level designer with a decade of experience."
            "## Experience"
            "### Polaris Cognition, Senior Designer\t2022-09 – Present"
            "- Built a thing."
            "- Designed another thing."
            "### Acme, Lead Designer\t2019-04 – 2022-08"
            "- Shipped a product."
        )
        out = _normalize_markdown(smushed)
        # Every section header on its own line
        assert "\n## Summary\n" in out
        assert "\n## Experience\n" in out
        # Every job entry on its own line
        assert "\n### Polaris Cognition" in out
        assert "\n### Acme" in out
        # Bullets all separated
        assert out.count("\n- ") >= 3
        # h2 → body split happened for Summary
        assert "## Summary\n\nPrincipal-level" in out
