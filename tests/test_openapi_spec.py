"""Tests for the spectree/OpenAPI Layer B Phase 1 wiring (`feat/spectree-openapi-emit`).

Two things this file proves:

1. **Parity** — decorating each of the 5 read-only GET routes with
   `@spec.validate(resp=..., skip_validation=True, ...)` changed NOTHING about
   the route's actual behavior (status code + JSON body). The decorator is
   `resp=`/`skip_validation=True` only (no `json=`/`query=`/`headers=` request
   validation, so no route body was touched), and it sits BELOW the Flask
   route decorator on every route (see `web_infra/openapi.py`'s module
   docstring on why that order — not the mission's literal "directly above"
   phrasing — is the one that actually registers the route into the spec;
   spectree's `skip_validation=True` wrapper is a thin passthrough either
   way). Combined with the pre-existing, much larger per-blueprint suites
   (`test_users_routes.py` / `test_career_corpus_routes.py` /
   `test_application_routes.py` — all still green, untouched by this branch),
   this is the before/after parity proof the mission asks for.
2. **The generator** (`scripts/generate_openapi_spec.py`) produces a valid
   OpenAPI dict containing all 5 decorated paths.

Factory-built (`create_app(Config(base_dir=tmp_path))`): no module-global
monkeypatching, every path under tmp_path — mirrors the existing per-blueprint
route-test fixtures.
"""

from __future__ import annotations

import hashlib

import pytest


@pytest.fixture
def spec_app(tmp_path, monkeypatch):
    """Factory app on a fresh sqlite DB + temp config dir."""
    import db.session as db_session_mod

    db_file = tmp_path / "openapi.sqlite"
    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config
    from db.session import init_db

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output
    # `_load_config`'s empty-config check (`if not config: 404`) means a bare
    # "{}" file reads as falsy — write a non-empty config, as `create_user`
    # (the real write path) always would.
    (cfg.configs_dir / "alice.config").write_text('{"name": "Alice Test"}', encoding="utf-8")
    init_db(db_file)
    return app


def _seed_candidate(username: str = "alice") -> int:
    from db.models import Candidate
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username=username, name="Alice Test")
        session.add(c)
        session.commit()
        return c.id
    finally:
        session.close()


def _seed_application(
    candidate_id: int, title: str = "Senior PM @ Foo", company: str = "Foo Inc"
) -> int:
    from db.models import Application
    from db.session import get_session

    jd_text = "Long JD text here."
    session = get_session()
    try:
        a = Application(
            candidate_id=candidate_id,
            title=title,
            company=company,
            jd_text=jd_text,
            status="draft",
            jd_fingerprint=hashlib.sha256(jd_text.encode()).hexdigest()[:16],
        )
        session.add(a)
        session.commit()
        return a.id
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Parity — one assertion per spectree-decorated route.
# ---------------------------------------------------------------------------


class TestDecoratedRouteParity:
    def test_list_users(self, spec_app):
        client = spec_app.test_client()
        r = client.get("/api/users")
        assert r.status_code == 200
        assert r.get_json() == ["alice"]

    def test_get_config(self, spec_app):
        client = spec_app.test_client()
        r = client.get("/api/users/alice/config")
        assert r.status_code == 200
        body = r.get_json()
        assert body["needs_onboarding"] is True

    def test_list_experiences_needs_onboarding(self, spec_app):
        client = spec_app.test_client()
        r = client.get("/api/users/alice/experiences")
        assert r.status_code == 200
        assert r.get_json() == {"experiences": [], "needs_onboarding": True}

    def test_list_applications_needs_onboarding(self, spec_app):
        client = spec_app.test_client()
        r = client.get("/api/users/alice/applications")
        assert r.status_code == 200
        assert r.get_json() == {"applications": [], "needs_onboarding": True}

    def test_get_application(self, spec_app):
        cid = _seed_candidate()
        aid = _seed_application(cid)
        client = spec_app.test_client()
        r = client.get(f"/api/applications/{aid}")
        assert r.status_code == 200
        body = r.get_json()
        assert body["id"] == aid
        assert body["title"] == "Senior PM @ Foo"
        assert body["candidate_username"] == "alice"
        assert body["runs"] == []


# ---------------------------------------------------------------------------
# 2. The standalone generator produces a valid OpenAPI dict with all 5 paths.
# ---------------------------------------------------------------------------


class TestGeneratedSpec:
    def test_build_spec_contains_all_five_decorated_paths(self):
        from scripts.generate_openapi_spec import _EXPECTED_PATHS, build_spec

        spec_dict = build_spec()
        assert spec_dict.get("openapi", "").startswith("3.")
        assert spec_dict["info"]["title"] == "sartor. API"
        for path in _EXPECTED_PATHS:
            assert path in spec_dict["paths"], f"missing path {path} in generated spec"

    def test_main_writes_valid_json_file(self, tmp_path, monkeypatch):
        """`main()` writes docs-site/openapi.json; redirect OUTPUT_PATH under tmp_path
        so this test never touches the real (gitignored) build artifact location."""
        import json

        import scripts.generate_openapi_spec as gen_mod

        out_path = tmp_path / "openapi.json"
        monkeypatch.setattr(gen_mod, "OUTPUT_PATH", out_path)

        exit_code = gen_mod.main()
        assert exit_code == 0
        written = json.loads(out_path.read_text(encoding="utf-8"))
        for path in gen_mod._EXPECTED_PATHS:
            assert path in written["paths"]
