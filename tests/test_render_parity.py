"""Branch 1 — single-render-engine parity + section-title fidelity (D3).

Two invariants this suite pins:

1. **Download == preview.** The `.docx` download renders from the SAME
   `md_to_json_resume()` document the HTML/PDF preview renders — not a second,
   divergent markdown parse. We prove it by comparing the JSON Resume sidecar
   `generate_resume()` writes (the download's source of truth) against
   `md_to_json_resume()` of the normalized content (the preview's source of
   truth), and by confirming every preview bullet/summary/skill appears in the
   generated `.docx`.

2. **Non-canonical section titles survive.** A résumé that titles its sections
   "Professional Summary" / "Core Competencies" / "Professional Experience"
   (very common, and exactly what plain Word imports produce) must land in the
   canonical JSON Resume fields, not silently drop to `meta.sartor.unparsed`.
"""

from __future__ import annotations

import json
from pathlib import Path

import docx
import pytest

from generator import _normalize_markdown, generate_resume
from json_resume import _SECTION_MAP, md_to_json_resume

# Uses non-canonical (but ubiquitous) headings + metric-bearing bullets — the
# shape a plain Word résumé import produces.
RESUME_MD = (
    "# Robert Cooksey\n"
    "Product Manager\n"
    "robert@example.com | 555-010-2200 | linkedin.com/in/robert\n\n"
    "## Professional Summary\n"
    "Product leader with 10+ years shipping hardware + software.\n\n"
    "## Professional Experience\n\n"
    "### Core Impact, Co-Founder & Head of Product\t2021 – Present\n"
    "- Owned product vision and success metrics (engagement, retention, NPS).\n"
    "- Grew pipeline via a sales flywheel producing $1M in adoption.\n\n"
    "### Intel, Product Experience Architect\t2016 – 2021\n"
    "- Compressed a 3-4 week documentation cycle to sprint-level integration.\n\n"
    "## Core Competencies\n"
    "Product Strategy · Roadmapping · PRDs\n"
)


class TestSectionTitleAliases:
    @pytest.mark.parametrize(
        ("heading", "canonical"),
        [
            ("Professional Summary", "_summary"),
            ("Summary of Qualifications", "_summary"),
            ("Profile", "_summary"),
            ("Professional Experience", "work"),
            ("Work History", "work"),
            ("Technical Skills", "skills"),
            ("Core Competencies", "skills"),
            ("Areas of Expertise", "skills"),
        ],
    )
    def test_alias_maps_to_canonical_key(self, heading: str, canonical: str) -> None:
        assert _SECTION_MAP[heading.lower()] == canonical

    def test_noncanonical_summary_and_skills_are_captured(self) -> None:
        jr = md_to_json_resume(RESUME_MD)
        assert jr["basics"]["summary"].startswith("Product leader")
        assert [s["name"] for s in jr["skills"]] == ["Product Strategy", "Roadmapping", "PRDs"]
        assert len(jr["work"]) == 2
        # Nothing was silently dropped to the unparsed bucket.
        assert jr["meta"]["sartor"]["unparsed"] == []


class TestDownloadPreviewParity:
    def test_docx_sidecar_equals_preview_json(self, tmp_path: Path) -> None:
        """The JSON Resume sidecar (download's source) equals the preview's source."""
        path = generate_resume(RESUME_MD, ".docx", "parity", base_dir=str(tmp_path))
        sidecar = Path(path).with_suffix(".jsonresume.json")
        got = json.loads(sidecar.read_text(encoding="utf-8"))
        expected = md_to_json_resume(_normalize_markdown(RESUME_MD))
        assert got == expected

    def test_docx_carries_every_preview_bullet_and_field(self, tmp_path: Path) -> None:
        jr = md_to_json_resume(_normalize_markdown(RESUME_MD))
        path = generate_resume(RESUME_MD, ".docx", "parity", base_dir=str(tmp_path))
        paras = [p.text for p in docx.Document(path).paragraphs if p.text.strip()]
        text = "\n".join(paras)

        # Every preview bullet made it into the download (metrics included).
        for job in jr["work"]:
            for highlight in job.get("highlights", []):
                assert highlight in text, f"bullet missing from .docx: {highlight}"
        assert jr["basics"]["summary"] in text
        assert "Product Strategy" in text

    def test_docx_emits_canonical_headings_not_source_titles(self, tmp_path: Path) -> None:
        """The writer renders canonical section names, so preview and download agree."""
        path = generate_resume(RESUME_MD, ".docx", "parity", base_dir=str(tmp_path))
        paras = [p.text for p in docx.Document(path).paragraphs if p.text.strip()]
        assert "Summary" in paras and "Professional Summary" not in paras
        assert "Experience" in paras and "Professional Experience" not in paras
        assert "Skills" in paras and "Core Competencies" not in paras


class TestSectionSpacing:
    """O1a (round-2 quick win): the .docx writer inserts a blank-paragraph
    spacer between top-level sections and between consecutive work entries, so
    the output stops reading as a dense wall of text. On the default (no
    template) path, no role carries captured spacing, so every spacer fires —
    that is the invariant pinned here. Content parity is unaffected (the
    existing parity tests filter `p.text.strip()`, so spacers are invisible to
    them and every bullet/field still lands)."""

    @staticmethod
    def _all_paras(path: str) -> list[str]:
        # Include EMPTY paragraphs — the spacers are empty, so we must not
        # filter them out here (unlike the content-parity tests).
        return [p.text for p in docx.Document(path).paragraphs]

    def test_blank_spacer_before_each_later_section(self, tmp_path: Path) -> None:
        path = generate_resume(RESUME_MD, ".docx", "spacing", base_dir=str(tmp_path))
        paras = self._all_paras(path)
        # The first section (Summary) gets no leading spacer; every later
        # section heading is immediately preceded by a blank paragraph.
        for heading in ("Experience", "Skills"):
            assert heading in paras, f"missing section heading: {heading}"
            idx = paras.index(heading)
            assert idx > 0 and paras[idx - 1] == "", (
                f"expected a blank spacer before the '{heading}' heading"
            )
        # Summary is first — it must NOT be preceded by a spacer.
        s_idx = paras.index("Summary")
        assert paras[s_idx - 1] != "", "first section (Summary) should have no leading spacer"

    def test_blank_spacer_between_work_entries(self, tmp_path: Path) -> None:
        path = generate_resume(RESUME_MD, ".docx", "spacing", base_dir=str(tmp_path))
        paras = self._all_paras(path)
        # RESUME_MD has two work entries; a blank paragraph separates them.
        first = next(i for i, t in enumerate(paras) if t.startswith("Core Impact"))
        second = next(i for i, t in enumerate(paras) if t.startswith("Intel"))
        assert first < second
        assert "" in paras[first + 1 : second], (
            "expected a blank spacer between the two work entries"
        )

    def test_spacers_do_not_disturb_content_parity(self, tmp_path: Path) -> None:
        """Every non-blank line still matches the preview source (spacers add
        emptiness, never text)."""
        jr = md_to_json_resume(_normalize_markdown(RESUME_MD))
        path = generate_resume(RESUME_MD, ".docx", "spacing", base_dir=str(tmp_path))
        text = "\n".join(p.text for p in docx.Document(path).paragraphs if p.text.strip())
        for job in jr["work"]:
            for highlight in job.get("highlights", []):
                assert highlight in text
        assert jr["basics"]["summary"] in text


class TestAtsScrubAndIdentityOverrideParity:
    """fix/output-identity-and-dates: the ATS scrub and identity override run
    inside generate_resume() itself (right after md_to_json_resume), so
    .docx / .md / the jsonresume.json sidecar can never disagree."""

    UNSAFE_MD = (
        "# Dana [QA] Cole\n"
        'Staff Engineer "the closer"\n'
        "dana@example.com\n\n"
        "## Summary\n"
        "Shipped {v2} with <b>bold</b> claims and <50ms latency.\n\n"
        "## Experience\n\n"
        "### Acme, Staff Engineer\t2022-01 – present\n"
        "- Cut p99 latency to <50ms using C++ and C#.\n"
    )

    def test_docx_md_and_sidecar_agree_on_scrubbed_text(self, tmp_path: Path) -> None:
        docx_path = generate_resume(self.UNSAFE_MD, ".docx", "scrub", base_dir=str(tmp_path))
        md_path = generate_resume(self.UNSAFE_MD, ".md", "scrub", base_dir=str(tmp_path))
        sidecar = Path(docx_path).with_suffix(".jsonresume.json")
        sidecar_doc = json.loads(sidecar.read_text(encoding="utf-8"))

        docx_text = "\n".join(p.text for p in docx.Document(docx_path).paragraphs if p.text.strip())
        md_text = Path(md_path).read_text(encoding="utf-8")

        for surface_name, text in (("docx", docx_text), ("md", md_text)):
            assert "[" not in text and "]" not in text, surface_name
            assert "{" not in text and "}" not in text, surface_name
            assert '"' not in text, surface_name
            assert "<b>" not in text, surface_name
            # tag-shaped <...> stripped, but a bare "<50ms" (no closing '>')
            # and C++/C# (neither char is in the strip set) survive.
            assert "<50ms" in text, surface_name
            assert "C++" in text and "C#" in text, surface_name

        assert sidecar_doc["meta"]["sartor"]["ats_scrubbed"]

    def test_identity_override_applies_to_docx_and_md_alike(self, tmp_path: Path) -> None:
        identity = {
            "name": "Real Name",
            "email": "real@example.com",
            "phone": "",
            "linkedin_url": "",
            "website_url": "",
        }
        stale_md = (
            "# Old Name\nold@example.com | https://stray-site.example\n\n## Summary\nBody text.\n"
        )
        docx_path = generate_resume(
            stale_md, ".docx", "identity", base_dir=str(tmp_path), identity_override=identity
        )
        md_path = generate_resume(
            stale_md, ".md", "identity", base_dir=str(tmp_path), identity_override=identity
        )
        docx_text = "\n".join(p.text for p in docx.Document(docx_path).paragraphs if p.text.strip())
        md_text = Path(md_path).read_text(encoding="utf-8")
        for surface_name, text in (("docx", docx_text), ("md", md_text)):
            assert "Real Name" in text, surface_name
            assert "real@example.com" in text, surface_name
            assert "Old Name" not in text, surface_name
            assert "old@example.com" not in text, surface_name
            assert "stray-site.example" not in text, surface_name
