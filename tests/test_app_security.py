"""Security helper tests — _safe_username and _within (path-traversal defenses).

These guard every Flask route that touches the filesystem. Regressions here
are CVE-class. The helpers live in the leaf `web_infra` package (the app.py-local
copies retired with the last route seam, Sprint 8.3h).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def app_module(tmp_path):
    """The `web_infra` security/config helpers, bound to a temp CONFIGS_DIR.

    Post-Sprint-8.3h the helpers are canonical in `web_infra` (the app.py copies
    retired with the diagnostics seam — the last route move). `_safe_username`
    checks `(configs_dir / "{user}.config").exists()`, so a real config is seeded in
    the temp dir and threaded as the keyword-only `configs_dir`. The namespace binds
    that temp dir so the helper-test bodies below stay unchanged (1-arg calls).
    """
    import web_infra

    (tmp_path / "alice.config").write_text("{}", encoding="utf-8")
    return SimpleNamespace(
        _safe_username=lambda u: web_infra._safe_username(u, configs_dir=tmp_path),
        _within=web_infra._within,
        _load_config=lambda u: web_infra._load_config(u, configs_dir=tmp_path),
        _save_config=lambda u, cfg: web_infra._save_config(u, cfg, configs_dir=tmp_path),
    )


@pytest.fixture
def config_route_app(tmp_path):
    """Factory-built app for the config ROUTES (get_config / update_config).

    Those routes moved to blueprints/users.py (Sprint 8.3g) and read
    `current_app.config["CONFIGS_DIR"]`, so they need a `create_app(Config(base_dir=
    tmp))` app. The helper-level classes above test the same containment one layer
    down, calling the canonical `web_infra` helpers directly (the `app_module`
    fixture binds them to a temp `configs_dir`).
    """
    import types

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)  # ensure_dirs() makes configs/resumes/output
    return types.SimpleNamespace(app=create_app(cfg), configs_dir=cfg.configs_dir)


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

    def test_all_strip_username_returns_400(self, config_route_app):
        # "..." reaches the handler (not a special path segment); secure_filename
        # reduces it to "" → the call-site guard returns 400, not a 500.
        client = config_route_app.app.test_client()
        assert client.get("/api/users/.../config").status_code == 400

    def test_reaching_value_writes_inside_configs_dir(self, config_route_app):
        # "x..y" is a single segment that reaches the handler and sanitizes to
        # itself → the config is written inside CONFIGS_DIR, never outside.
        configs_dir = config_route_app.configs_dir
        client = config_route_app.app.test_client()
        resp = client.put("/api/users/x..y/config", json={"name": "X"})
        assert resp.status_code == 200
        assert (configs_dir / "x..y.config").exists()
        assert not (configs_dir.parent / "x..y.config").exists()

    def test_encoded_slash_traversal_rejected_by_routing(self, config_route_app):
        # NOTE: this proves werkzeug rejects an encoded-slash path segment at
        # routing (404) — NOT that the helper contains traversal. The helper
        # containment is proved by TestConfigHelperContainment above.
        client = config_route_app.app.test_client()
        assert client.get("/api/users/..%2f../config").status_code == 404
