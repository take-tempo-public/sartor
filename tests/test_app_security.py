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


class TestConfigHelperContainment:
    """PX-21 — _load_config / _save_config sanitize the username at the helper,
    so containment to CONFIGS_DIR holds even when a caller passes raw input.
    Regressions here are CVE-class.
    """

    def test_save_config_traversal_username_stays_contained(self, tmp_path, app_module):
        app_module._save_config("../../evil", {"name": "x"})
        # secure_filename flattens "../../evil" → "evil"; the write lands inside
        # CONFIGS_DIR (tmp_path), never in a parent directory.
        assert (tmp_path / "evil.config").exists()
        assert not (tmp_path.parent / "evil.config").exists()
        assert not (tmp_path.parent.parent / "evil.config").exists()

    def test_load_config_traversal_username_returns_empty(self, app_module):
        # No file resolves for the sanitized name → {} (callers treat as "no user").
        assert app_module._load_config("../../etc/passwd") == {}

    def test_save_config_empty_after_sanitize_raises(self, app_module):
        # An all-stripped username sanitizes to "" → refused, never written as a
        # junk ".config". (Unreachable in practice — every real caller pre-sanitizes.)
        with pytest.raises(ValueError):
            app_module._save_config("...", {"name": "x"})

    def test_save_config_existing_user_is_byte_compatible(self, tmp_path, app_module):
        # secure_filename is idempotent on an already-safe name → no path change.
        app_module._save_config("alice", {"name": "Alice"})
        assert (tmp_path / "alice.config").exists()
        assert app_module._load_config("alice") == {"name": "Alice"}


class TestConfigRouteContainment:
    """PX-21 — the two raw-input config routes (get_config / update_config)
    reject a nonsense username with a clean 400, and the value that actually
    reaches the handler stays contained to CONFIGS_DIR.
    """

    def test_all_strip_username_returns_400(self, app_module):
        # "..." reaches the handler (not a special path segment); secure_filename
        # reduces it to "" → the call-site guard returns 400, not a 500.
        client = app_module.app.test_client()
        assert client.get("/api/users/.../config").status_code == 400

    def test_reaching_value_writes_inside_configs_dir(self, tmp_path, app_module):
        # "x..y" is a single segment that reaches the handler and sanitizes to
        # itself → the config is written inside CONFIGS_DIR, never outside.
        client = app_module.app.test_client()
        resp = client.put("/api/users/x..y/config", json={"name": "X"})
        assert resp.status_code == 200
        assert (tmp_path / "x..y.config").exists()
        assert not (tmp_path.parent / "x..y.config").exists()

    def test_encoded_slash_traversal_rejected_by_routing(self, app_module):
        # NOTE: this proves werkzeug rejects an encoded-slash path segment at
        # routing (404) — NOT that the helper contains traversal. The helper
        # containment is proved by TestConfigHelperContainment above.
        client = app_module.app.test_client()
        assert client.get("/api/users/..%2f../config").status_code == 404
