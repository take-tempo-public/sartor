"""Unit tests for parser.py — file-format-agnostic resume parsing."""

import pytest

from parser import _infer_sections, parse_resume


class TestInferSections:
    def test_extracts_known_headings(self):
        text = "## Experience\nSomething\n## Education\nMore"
        sections = _infer_sections(text)
        headings = [s["heading"].lower() for s in sections]
        assert any("experience" in h for h in headings)
        assert any("education" in h for h in headings)

    def test_handles_no_headings(self):
        sections = _infer_sections("Just plain text with no resume sections")
        assert isinstance(sections, list)


class TestParseResume:
    def test_unsupported_format_raises(self, tmp_path):
        bogus = tmp_path / "resume.txt"
        bogus.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported format"):
            parse_resume(str(bogus))

    def test_markdown_returns_expected_keys(self, tmp_path):
        md = tmp_path / "resume.md"
        md.write_text("# Jane Smith\n## Experience\nWorked at Acme")
        result = parse_resume(str(md))
        assert set(result.keys()) >= {"text", "format", "sections", "filename", "filepath"}
        assert result["format"] == ".md"
        assert result["filename"] == "resume.md"
