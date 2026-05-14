"""Tests for db.ats_roundtrip.run_ats_roundtrip (Phase C.3).

The round-trip check parses a generated .docx back through parser.py and
counts bullets + sections recovered vs emitted. Tests use the bundled
templates as known-good fixtures since they ship with 3 bullets + 3
known section headings.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_DIR = REPO_ROOT / "personas" / "bundled"


class TestRunAtsRoundtrip:
    def test_clean_template_returns_pass(self):
        """Each bundled template ships with 3 bullets + 3 known sections.
        Emitting matching markdown should round-trip clean."""
        from db.ats_roundtrip import run_ats_roundtrip
        md = (
            "# Casey Rivera\n\n"
            "## Experience\n"
            "- Sample bullet 1\n- Sample bullet 2\n- Sample bullet 3\n\n"
            "## Education\n"
            "## Skills\n"
        )
        out = run_ats_roundtrip(BUNDLED_DIR / "classic.docx", md)
        assert out["status"] == "pass"
        assert out["bullet_count_emitted"] == 3
        assert out["bullet_count_recovered"] == 3
        assert set(s.lower() for s in out["sections_emitted"]) == {
            "experience", "education", "skills",
        }

    def test_missing_docx_returns_fail(self, tmp_path):
        from db.ats_roundtrip import run_ats_roundtrip
        out = run_ats_roundtrip(tmp_path / "does-not-exist.docx", "## Experience\n- x")
        assert out["status"] == "fail"
        assert any("missing" in n for n in out["notes"])

    def test_high_bullet_loss_flags_fail(self):
        """Emit 10 bullets, classic ships with 3 → loss ratio 70% → fail."""
        from db.ats_roundtrip import run_ats_roundtrip
        md = "## Experience\n" + "\n".join(f"- Bullet {i}" for i in range(10))
        out = run_ats_roundtrip(BUNDLED_DIR / "classic.docx", md)
        assert out["status"] == "fail"
        assert any("bullet loss too high" in n for n in out["notes"])

    def test_moderate_bullet_loss_flags_warning(self):
        """Emit 4 bullets, classic recovers 3 → 25% loss → warning."""
        from db.ats_roundtrip import run_ats_roundtrip
        md = "## Experience\n" + "\n".join(f"- Bullet {i}" for i in range(4))
        out = run_ats_roundtrip(BUNDLED_DIR / "classic.docx", md)
        assert out["status"] == "warning"

    def test_missing_section_flags_fail(self):
        """Emit a Summary section the template doesn't contain → fail
        (the test fixture template has only Experience/Education/Skills)."""
        from db.ats_roundtrip import run_ats_roundtrip
        md = "## Summary\nSome summary text.\n## Experience\n- bullet"
        out = run_ats_roundtrip(BUNDLED_DIR / "classic.docx", md)
        assert out["status"] == "fail"
        assert any("sections missing" in n for n in out["notes"])

    def test_handles_corrupt_docx_gracefully(self, tmp_path):
        """A 'bad' .docx (just zeros) should fail cleanly, not raise."""
        from db.ats_roundtrip import run_ats_roundtrip
        bad = tmp_path / "broken.docx"
        bad.write_bytes(b"\x00" * 100)
        out = run_ats_roundtrip(bad, "## Experience\n- x")
        assert out["status"] == "fail"


class TestStatusEscalation:
    """The _escalate_status helper takes the more severe of two statuses.
    Tests cover transitions so adding a new check level later is safe."""

    def test_warning_escalates_to_fail(self):
        from db.ats_roundtrip import _escalate_status
        assert _escalate_status("warning", "fail") == "fail"

    def test_fail_does_not_downgrade(self):
        from db.ats_roundtrip import _escalate_status
        assert _escalate_status("fail", "warning") == "fail"
        assert _escalate_status("fail", "pass") == "fail"

    def test_pass_escalates_to_warning(self):
        from db.ats_roundtrip import _escalate_status
        assert _escalate_status("pass", "warning") == "warning"


class TestStructuralBulletCount:
    """The _count_list_bullet_paragraphs helper counts paragraphs styled
    as List Bullet (or any list style). Critical: this is the path that
    catches the generator's bullet output, which uses Word's List Bullet
    style without text glyphs."""

    def test_counts_bundled_template_bullets(self):
        from db.ats_roundtrip import _count_list_bullet_paragraphs
        count = _count_list_bullet_paragraphs(BUNDLED_DIR / "classic.docx")
        # Each bundled template ships with 3 sample bullets
        assert count == 3

    def test_returns_zero_on_unopenable_file(self, tmp_path):
        from db.ats_roundtrip import _count_list_bullet_paragraphs
        bad = tmp_path / "not_a_docx.txt"
        bad.write_text("plain text")
        assert _count_list_bullet_paragraphs(bad) == 0
