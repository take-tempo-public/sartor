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
