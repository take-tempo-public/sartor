"""Tests for the typed `Config` (Sprint 8.3a factory foundation).

The load-bearing assertion is the `ensure_dirs()` byte-identical pin: it must
create ONLY configs/resumes/output (mirroring the retired app.py:85-86 loop) and
must NOT create annotation_root / personas / bundled (those are made lazily by
their writers today; eager creation would be a behavior change).
"""

from __future__ import annotations

from pathlib import Path

from config import Config


class TestDerivedRoots:
    def test_single_base_dir_repoints_all_seven(self, tmp_path: Path) -> None:
        cfg = Config(base_dir=tmp_path)
        assert cfg.configs_dir == tmp_path / "configs"
        assert cfg.resumes_dir == tmp_path / "resumes"
        assert cfg.output_dir == tmp_path / "output"
        assert cfg.annotation_root == tmp_path / "evals" / "fixtures" / "real"
        assert cfg.personas_dir == tmp_path / "personas"
        assert cfg.bundled_personas_dir == tmp_path / "personas" / "bundled"

    def test_defaults_mirror_production_globals(self) -> None:
        # Default base_dir is the repo root (config.py is top-level, like app.py).
        cfg = Config()
        repo_root = Path(__file__).resolve().parent.parent
        assert cfg.base_dir == repo_root
        assert cfg.configs_dir == repo_root / "configs"
        assert cfg.host == "127.0.0.1"  # PX-19
        assert cfg.allowed_extensions == frozenset({".docx", ".pdf", ".md"})


class TestEnsureDirs:
    def test_creates_only_configs_resumes_output(self, tmp_path: Path) -> None:
        cfg = Config(base_dir=tmp_path)
        cfg.ensure_dirs()
        # The three the import loop made.
        assert cfg.configs_dir.is_dir()
        assert cfg.resumes_dir.is_dir()
        assert cfg.output_dir.is_dir()

    def test_does_not_create_annotation_personas_or_bundled(self, tmp_path: Path) -> None:
        # The byte-identical pin: eager creation of these would be a behavior change.
        cfg = Config(base_dir=tmp_path)
        cfg.ensure_dirs()
        assert not cfg.annotation_root.exists()
        assert not cfg.personas_dir.exists()
        assert not cfg.bundled_personas_dir.exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        cfg = Config(base_dir=tmp_path)
        cfg.ensure_dirs()
        cfg.ensure_dirs()  # exist_ok=True — no raise on second call
        assert cfg.configs_dir.is_dir()


class TestAsFlaskConfig:
    def test_uppercase_keys_match_legacy_global_names(self, tmp_path: Path) -> None:
        flask_cfg = Config(base_dir=tmp_path).as_flask_config()
        assert set(flask_cfg) == {
            "BASE_DIR",
            "CONFIGS_DIR",
            "RESUMES_DIR",
            "OUTPUT_DIR",
            "ANNOTATION_ROOT",
            "PERSONAS_DIR",
            "BUNDLED_PERSONAS_DIR",
            "ALLOWED_EXTENSIONS",
            "HOST",
            # F-19 demo mode (feat/ux-w3-demo-mode) — not a legacy app.py global;
            # surfaces Config.demo_mode to templates as config.DEMO_MODE.
            "DEMO_MODE",
        }
        assert flask_cfg["CONFIGS_DIR"] == tmp_path / "configs"
        assert flask_cfg["HOST"] == "127.0.0.1"
        assert flask_cfg["ALLOWED_EXTENSIONS"] == frozenset({".docx", ".pdf", ".md"})
