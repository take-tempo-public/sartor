"""Security helper tests — _safe_username and _within (path-traversal defenses).

These guard every Flask route that touches the filesystem. Regressions here
are CVE-class.
"""

from pathlib import Path

import pytest


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    """Import app.py with CONFIGS_DIR redirected to a temp dir.

    `_safe_username` checks `(CONFIGS_DIR / "{user}.config").exists()`, so we
    redirect CONFIGS_DIR before populating it.
    """
    import app as _app

    monkeypatch.setattr(_app, "CONFIGS_DIR", tmp_path)
    (tmp_path / "alice.config").write_text("{}", encoding="utf-8")
    return _app


class TestSafeUsername:
    def test_valid_existing_user_passes(self, app_module):
        assert app_module._safe_username("alice") == "alice"

    def test_unknown_user_returns_none(self, app_module):
        assert app_module._safe_username("nobody") is None

    def test_path_traversal_attempt_returns_none(self, app_module):
        # secure_filename strips ../ and the resulting "etcpasswd" config doesn't exist
        assert app_module._safe_username("../../etc/passwd") is None

    def test_empty_string_returns_none(self, app_module):
        assert app_module._safe_username("") is None

    def test_only_traversal_chars_returns_none(self, app_module):
        # secure_filename reduces "../.." to empty
        assert app_module._safe_username("../..") is None


class TestWithin:
    def test_path_inside_parent_returns_true(self, tmp_path, app_module):
        child = tmp_path / "subdir" / "file.txt"
        child.parent.mkdir(parents=True)
        child.write_text("x")
        assert app_module._within(child, tmp_path) is True

    def test_path_outside_parent_returns_false(self, tmp_path, app_module):
        outside = Path(tmp_path).parent / "elsewhere.txt"
        assert app_module._within(outside, tmp_path) is False

    def test_path_equal_to_parent_returns_true(self, tmp_path, app_module):
        # A path that resolves to the parent itself is considered "within"
        assert app_module._within(tmp_path, tmp_path) is True

    def test_traversal_in_path_caught(self, tmp_path, app_module):
        attacker = tmp_path / ".." / "etc" / "passwd"
        assert app_module._within(attacker, tmp_path) is False
