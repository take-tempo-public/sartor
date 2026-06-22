"""Tests for the users/config seam routes (Sprint 8.3g, blueprints/users.py).

list_users + create_user had no dedicated unit coverage before the seam move
(create_user was only ever exercised indirectly via the wizard). These pin the two
routes on the factory app — in particular create_user's `RESUMES_DIR` write, which
the move swapped from a module global to `current_app.config["RESUMES_DIR"]` and is
the one moved line that was otherwise untested.

Factory-built (`create_app(Config(base_dir=tmp_path))`): no module-global
monkeypatching, every path under tmp_path.
"""

from __future__ import annotations

import types

import pytest


@pytest.fixture
def users_app(tmp_path):
    """Factory app whose Config points every path under tmp_path."""
    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)  # ensure_dirs() makes configs/resumes/output
    return types.SimpleNamespace(
        app=create_app(cfg),
        configs_dir=cfg.configs_dir,
        resumes_dir=cfg.resumes_dir,
    )


class TestListUsers:
    def test_empty_returns_empty_list(self, users_app):
        client = users_app.app.test_client()
        r = client.get("/api/users")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_lists_config_stems(self, users_app):
        (users_app.configs_dir / "alice.config").write_text("{}", encoding="utf-8")
        (users_app.configs_dir / "bob.config").write_text("{}", encoding="utf-8")
        client = users_app.app.test_client()
        r = client.get("/api/users")
        assert r.status_code == 200
        assert sorted(r.get_json()) == ["alice", "bob"]


class TestCreateUser:
    def test_happy_path_writes_config_and_resumes_dir(self, users_app):
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"username": "bob", "name": "Bob"})
        assert r.status_code == 200
        body = r.get_json()
        assert body["username"] == "bob"
        assert body["config"]["name"] == "Bob"
        # The config file lands inside the injected CONFIGS_DIR …
        assert (users_app.configs_dir / "bob.config").exists()
        # … and the per-user resumes dir is created under the injected RESUMES_DIR
        # (this is the line the seam move swapped to current_app.config).
        assert (users_app.resumes_dir / "bob").is_dir()

    def test_missing_username_returns_400(self, users_app):
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"name": "Nobody"})
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_traversal_username_sanitized_and_contained(self, users_app):
        # secure_filename flattens "../../evil" → "evil"; the config + resumes
        # dir land inside the injected dirs, never in a parent directory.
        client = users_app.app.test_client()
        r = client.post("/api/users", json={"username": "../../evil"})
        assert r.status_code == 200
        assert r.get_json()["username"] == "evil"
        assert (users_app.configs_dir / "evil.config").exists()
        assert not (users_app.configs_dir.parent / "evil.config").exists()
