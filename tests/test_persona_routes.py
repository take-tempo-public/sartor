"""Tests for the Phase C.2 persona template routes.

Covers list / get / upload / update / delete / download flows. Tests use
in-memory SQLite + the existing fixture machinery from conftest, plus a
fresh per-test app reload so module-level state stays isolated.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest


@pytest.fixture
def persona_app(tmp_path, monkeypatch):
    """Factory-built app on a fresh sqlite DB + temp tree (Sprint 8.3e).

    The persona/preview routes moved to blueprints/templates.py and read
    current_app.config[...] at request time, so create_app(Config(base_dir=
    tmp_path)) replaces the old reload + monkeypatch-the-globals fixture (and its
    8.3c /api/download-edited config-injection stopgap). The DB-path monkeypatch
    stays (distinct seam). Returns a small namespace exposing the factory app +
    the Config-derived paths + the moved resolver helpers (each wrapped in an app
    context, since they now read current_app.config) so the existing test bodies
    keep referencing `persona_app.app` / `.BASE_DIR` / `._resolve_*` unchanged.
    """
    import types

    db_file = tmp_path / "personas.sqlite"

    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)  # ensure_dirs() makes configs/resumes/output
    cfg.bundled_personas_dir.mkdir(parents=True, exist_ok=True)
    (cfg.configs_dir / "alice.config").write_text("{}", encoding="utf-8")

    # Materialize the schema. The seed migration populates the canonical bundled
    # rows — tests using bundled rows assert their counts against this baseline.
    from db.session import init_db

    init_db(db_file)

    import blueprints.templates as templates_mod

    def _ctx(fn):
        def wrapped(*a, **k):
            with app.app_context():
                return fn(*a, **k)

        return wrapped

    return types.SimpleNamespace(
        app=app,
        BASE_DIR=cfg.base_dir,
        CONFIGS_DIR=cfg.configs_dir,
        OUTPUT_DIR=cfg.output_dir,
        RESUMES_DIR=cfg.resumes_dir,
        PERSONAS_DIR=cfg.personas_dir,
        BUNDLED_PERSONAS_DIR=cfg.bundled_personas_dir,
        _resolve_persona_template_path=_ctx(templates_mod._resolve_persona_template_path),
        _resolve_default_persona_template_path=_ctx(
            templates_mod._resolve_default_persona_template_path
        ),
    )


def _seed_candidate(app_module, username="alice"):
    """Insert a candidate row + return its id."""
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


def _seed_bundled_persona_file(app_module, filename="dummy.docx"):
    """Drop a minimal valid .docx into personas/bundled/ and insert a
    matching DB row. Returns the row id and the on-disk path."""
    from docx import Document

    from db.models import PersonaTemplate
    from db.session import get_session

    bundled_dir = app_module.BASE_DIR / "personas" / "bundled"
    target = bundled_dir / filename
    doc = Document()
    doc.add_paragraph("Bundled persona placeholder for tests.")
    doc.save(str(target))

    session = get_session()
    try:
        row = PersonaTemplate(
            candidate_id=None,
            name=filename.replace(".docx", "").title(),
            path=f"personas/bundled/{filename}",
            source="bundled",
            is_default=0,
        )
        session.add(row)
        session.commit()
        return row.id, target
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /api/personas/bundled
# ---------------------------------------------------------------------------


class TestListBundled:
    def test_lists_bundled_rows_for_anonymous_caller(self, persona_app):
        _seed_bundled_persona_file(persona_app, "alpha.docx")
        _seed_bundled_persona_file(persona_app, "beta.docx")
        client = persona_app.app.test_client()
        r = client.get("/api/personas/bundled")
        assert r.status_code == 200
        body = r.get_json()
        # 4 v1.0.0-curated bundled (classic / modern / spacious / tech;
        # migration 0005 drops Compact and renames Hybrid Tech) +
        # 2 test additions = 6
        assert len(body) == 6
        names = {p["name"] for p in body}
        assert "Alpha" in names
        assert "Beta" in names
        assert all(p["source"] == "bundled" for p in body)
        assert all(p["candidate_id"] is None for p in body)


# ---------------------------------------------------------------------------
# GET /api/users/<u>/personas
# ---------------------------------------------------------------------------


class TestListUserPersonas:
    def test_returns_bundled_plus_owned(self, persona_app):
        cid = _seed_candidate(persona_app)
        _seed_bundled_persona_file(persona_app, "gamma.docx")
        # Add an owned row
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            (persona_app.BASE_DIR / "personas" / "alice").mkdir(parents=True, exist_ok=True)
            owned_path = persona_app.BASE_DIR / "personas" / "alice" / "mine.docx"
            owned_path.write_bytes(b"placeholder")
            s.add(
                PersonaTemplate(
                    candidate_id=cid,
                    name="My Persona",
                    path="personas/alice/mine.docx",
                    source="user_upload",
                )
            )
            s.commit()
        finally:
            s.close()

        client = persona_app.app.test_client()
        r = client.get("/api/users/alice/personas")
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        # 4 v1.0.0-curated bundled rows + the Gamma test row = 5
        assert len(body["bundled"]) == 5
        assert any(p["name"] == "Gamma" for p in body["bundled"])
        assert len(body["owned"]) == 1
        assert body["owned"][0]["name"] == "My Persona"

    def test_unknown_user_returns_400(self, persona_app):
        client = persona_app.app.test_client()
        r = client.get("/api/users/ghost/personas")
        assert r.status_code == 400

    def test_known_user_without_candidate_returns_200_needs_onboarding(self, persona_app):
        # config exists, but no candidate row in DB. A read precondition is
        # NOT a conflict: the route returns 200 + needs_onboarding (empty
        # lists) so the UI offers the legacy-import flow without a red console
        # error. (POST writes keep 409.)
        client = persona_app.app.test_client()
        r = client.get("/api/users/alice/personas")
        assert r.status_code == 200
        body = r.get_json()
        assert body["needs_onboarding"] is True
        assert body["bundled"] == []
        assert body["owned"] == []


# ---------------------------------------------------------------------------
# POST /api/users/<u>/personas — upload
# ---------------------------------------------------------------------------


class TestUploadPersona:
    def test_upload_saves_file_and_creates_db_row(self, persona_app):
        _seed_candidate(persona_app)
        client = persona_app.app.test_client()
        payload = {
            "file": (io.BytesIO(b"PK\x03\x04dummy docx bytes"), "my_persona.docx"),
            "name": "Brand New",
        }
        r = client.post(
            "/api/users/alice/personas",
            data=payload,
            content_type="multipart/form-data",
        )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["name"] == "Brand New"
        assert body["source"] == "user_upload"
        assert body["path"].startswith("personas/alice/")
        # File landed on disk
        assert (persona_app.BASE_DIR / body["path"]).exists()
        # The uploaded bytes aren't a real .docx, so companion generation fails
        # (walkthrough residuals item 3): upload still succeeds (degrade, don't
        # block) but the response carries a warning instead of silence.
        assert "companion_warning" in body
        assert not (persona_app.BASE_DIR / body["path"]).with_suffix(".html").exists()
        # DB row landed
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            count = s.query(PersonaTemplate).filter_by(source="user_upload").count()
            assert count == 1
        finally:
            s.close()

    def test_upload_with_valid_docx_has_no_companion_warning(self, persona_app):
        """A real, single-column .docx generates its companion cleanly — no warning."""
        _seed_candidate(persona_app)
        repo_root = Path(__file__).resolve().parents[1]
        docx_bytes = (repo_root / "personas" / "bundled" / "tech.docx").read_bytes()
        client = persona_app.app.test_client()
        r = client.post(
            "/api/users/alice/personas",
            data={"file": (io.BytesIO(docx_bytes), "mine.docx")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert "companion_warning" not in body
        assert (persona_app.BASE_DIR / body["path"]).with_suffix(".html").exists()

    def test_rejects_non_docx_extension(self, persona_app):
        _seed_candidate(persona_app)
        client = persona_app.app.test_client()
        r = client.post(
            "/api/users/alice/personas",
            data={"file": (io.BytesIO(b"x"), "evil.exe")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 400
        assert ".docx" in r.get_json()["error"]


# ---------------------------------------------------------------------------
# PUT /api/personas/<id>
# ---------------------------------------------------------------------------


class TestUpdatePersona:
    def test_rejects_updating_bundled(self, persona_app):
        pid, _ = _seed_bundled_persona_file(persona_app)
        client = persona_app.app.test_client()
        r = client.put(
            f"/api/personas/{pid}",
            json={"name": "Renamed"},
        )
        assert r.status_code == 403
        assert "immutable" in r.get_json()["error"].lower()

    def test_updates_name_on_owned(self, persona_app):
        cid = _seed_candidate(persona_app)
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            row = PersonaTemplate(
                candidate_id=cid,
                name="Old Name",
                path="personas/alice/x.docx",
                source="user_upload",
            )
            s.add(row)
            s.commit()
            pid = row.id
        finally:
            s.close()

        client = persona_app.app.test_client()
        r = client.put(f"/api/personas/{pid}", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.get_json()["name"] == "New Name"

    def test_rejects_empty_name(self, persona_app):
        cid = _seed_candidate(persona_app)
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            row = PersonaTemplate(
                candidate_id=cid,
                name="x",
                path="personas/alice/x.docx",
                source="user_upload",
            )
            s.add(row)
            s.commit()
            pid = row.id
        finally:
            s.close()

        client = persona_app.app.test_client()
        r = client.put(f"/api/personas/{pid}", json={"name": "  "})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/personas/<id>
# ---------------------------------------------------------------------------


class TestDeletePersona:
    def test_rejects_deleting_bundled(self, persona_app):
        pid, _ = _seed_bundled_persona_file(persona_app)
        client = persona_app.app.test_client()
        r = client.delete(f"/api/personas/{pid}")
        assert r.status_code == 403

    def test_deletes_owned_file_and_row(self, persona_app):
        cid = _seed_candidate(persona_app)
        owned_dir = persona_app.BASE_DIR / "personas" / "alice"
        owned_dir.mkdir(parents=True, exist_ok=True)
        disk_path = owned_dir / "del.docx"
        disk_path.write_bytes(b"placeholder")

        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            row = PersonaTemplate(
                candidate_id=cid,
                name="ToDelete",
                path="personas/alice/del.docx",
                source="user_upload",
            )
            s.add(row)
            s.commit()
            pid = row.id
        finally:
            s.close()

        client = persona_app.app.test_client()
        r = client.delete(f"/api/personas/{pid}")
        assert r.status_code == 200
        assert not disk_path.exists()
        # Row gone
        s = get_session()
        try:
            assert s.query(PersonaTemplate).filter_by(id=pid).first() is None
        finally:
            s.close()


# ---------------------------------------------------------------------------
# GET /api/personas/<id>/download
# ---------------------------------------------------------------------------


class TestDownloadPersona:
    def test_downloads_bundled_file(self, persona_app):
        pid, target = _seed_bundled_persona_file(persona_app, "dl.docx")
        client = persona_app.app.test_client()
        r = client.get(f"/api/personas/{pid}/download")
        assert r.status_code == 200
        assert len(r.data) > 50  # has body

    def test_404_when_row_missing(self, persona_app):
        client = persona_app.app.test_client()
        r = client.get("/api/personas/99999/download")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Resolver helpers
# ---------------------------------------------------------------------------


class TestResolveHelpers:
    def test_resolves_persona_to_absolute_path(self, persona_app):
        pid, target = _seed_bundled_persona_file(persona_app, "resolve.docx")
        path = persona_app._resolve_persona_template_path(pid)
        assert path is not None
        assert Path(path).exists()
        assert Path(path).name == "resolve.docx"

    def test_resolver_returns_none_when_file_missing(self, persona_app):
        pid, target = _seed_bundled_persona_file(persona_app, "ghost.docx")
        target.unlink()  # delete the file but keep the DB row
        path = persona_app._resolve_persona_template_path(pid)
        assert path is None

    def test_resolver_returns_none_for_unknown_id(self, persona_app):
        path = persona_app._resolve_persona_template_path(99999)
        assert path is None


# ---------------------------------------------------------------------------
# Workstream C — preview-with-resume + download-edited persona path
# ---------------------------------------------------------------------------


def _seed_app_run_with_resume(candidate_id, md="# Jane\n\n## Experience\n\n- Did X"):
    import hashlib

    from db.models import Application, ApplicationRun
    from db.session import get_session

    s = get_session()
    try:
        a = Application(
            candidate_id=candidate_id,
            title="T",
            jd_text="jd",
            jd_fingerprint=hashlib.sha256(b"jd").hexdigest()[:16],
        )
        s.add(a)
        s.flush()
        s.add(
            ApplicationRun(
                application_id=a.id,
                iteration=0,
                run_id="prevrun12345",
                prompt_version="t",
                corpus_snapshot_json="{}",
                generated_resume_md=md,
            )
        )
        s.commit()
    finally:
        s.close()


class TestPersonaPreview:
    def test_preview_streams_docx_from_latest_resume(self, persona_app):
        cid = _seed_candidate(persona_app)
        pid, _ = _seed_bundled_persona_file(persona_app, "prev.docx")
        _seed_app_run_with_resume(cid)
        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/preview", json={"username": "alice"})
        assert r.status_code == 200, r.get_json() if r.is_json else r.data[:200]
        # python-docx files are PK zip archives
        assert r.data[:2] == b"PK"

    def test_preview_409_when_no_generated_resume(self, persona_app):
        _seed_candidate(persona_app)
        pid, _ = _seed_bundled_persona_file(persona_app, "prev2.docx")
        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/preview", json={"username": "alice"})
        assert r.status_code == 409
        assert "generate" in r.get_json()["error"].lower()

    def test_preview_404_unknown_persona(self, persona_app):
        _seed_candidate(persona_app)
        client = persona_app.app.test_client()
        r = client.post("/api/personas/99999/preview", json={"username": "alice"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/personas/<id>/copy (Wave 2 recruiter tier — UX review F-16)
# ---------------------------------------------------------------------------


def _seed_owned_persona_file(
    persona_app, candidate_id, owner_username, filename="house.docx", name="House Style"
):
    """Drop a fake .docx under personas/<owner>/ and insert a user_upload row."""
    from db.models import PersonaTemplate
    from db.session import get_session

    owner_dir = persona_app.BASE_DIR / "personas" / owner_username
    owner_dir.mkdir(parents=True, exist_ok=True)
    disk_path = owner_dir / filename
    disk_path.write_bytes(b"PK\x03\x04not a real docx but good enough for a copy")

    s = get_session()
    try:
        row = PersonaTemplate(
            candidate_id=candidate_id,
            name=name,
            path=f"personas/{owner_username}/{filename}",
            source="user_upload",
        )
        s.add(row)
        s.commit()
        return row.id
    finally:
        s.close()


class TestCopyPersonaToCandidate:
    def test_copies_file_and_creates_row_for_target(self, persona_app):
        alice_id = _seed_candidate(persona_app, "alice")
        (persona_app.CONFIGS_DIR / "bob.config").write_text("{}", encoding="utf-8")
        bob_id = _seed_candidate(persona_app, "bob")
        pid = _seed_owned_persona_file(persona_app, alice_id, "alice")

        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "bob"})
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body["name"] == "House Style"
        assert body["source"] == "user_upload"
        assert body["candidate_id"] == bob_id
        assert body["path"].startswith("personas/bob/")
        assert (persona_app.BASE_DIR / body["path"]).exists()

        # Original untouched — both rows now exist, each owned by its candidate.
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            rows = s.query(PersonaTemplate).filter_by(source="user_upload").all()
            assert len(rows) == 2
            assert {row.candidate_id for row in rows} == {alice_id, bob_id}
            assert (persona_app.BASE_DIR / "personas" / "alice" / "house.docx").exists()
        finally:
            s.close()

    def test_rejects_bundled_source(self, persona_app):
        pid, _ = _seed_bundled_persona_file(persona_app, "bundled_copy.docx")
        (persona_app.CONFIGS_DIR / "bob.config").write_text("{}", encoding="utf-8")
        _seed_candidate(persona_app, "bob")

        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "bob"})
        assert r.status_code == 400
        assert "uploaded" in r.get_json()["error"].lower()

    def test_404_unknown_persona(self, persona_app):
        (persona_app.CONFIGS_DIR / "bob.config").write_text("{}", encoding="utf-8")
        _seed_candidate(persona_app, "bob")
        client = persona_app.app.test_client()
        r = client.post("/api/personas/99999/copy", json={"username": "bob"})
        assert r.status_code == 404

    def test_400_unknown_target_user(self, persona_app):
        alice_id = _seed_candidate(persona_app, "alice")
        pid = _seed_owned_persona_file(persona_app, alice_id, "alice")
        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "ghost"})
        assert r.status_code == 400

    def test_400_traversal_target_username_sanitized(self, persona_app):
        # secure_filename flattens "../../evil" -> "evil"; no config exists for
        # it, so _safe_username rejects — same traversal-sanitize contract as
        # create_user (tests/test_users_routes.py::test_traversal_username_...).
        alice_id = _seed_candidate(persona_app, "alice")
        pid = _seed_owned_persona_file(persona_app, alice_id, "alice")
        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "../../evil"})
        assert r.status_code == 400
        assert not (persona_app.PERSONAS_DIR / "evil").exists()

    def test_400_copy_to_same_owner(self, persona_app):
        alice_id = _seed_candidate(persona_app, "alice")
        pid = _seed_owned_persona_file(persona_app, alice_id, "alice")
        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "alice"})
        assert r.status_code == 400
        assert "already belongs" in r.get_json()["error"].lower()

    def test_403_when_source_path_escapes_personas_dir(self, persona_app):
        # A corrupted DB row (path escaping PERSONAS_DIR) must not be readable
        # via the copy route — the _within re-check on the source is the guard.
        alice_id = _seed_candidate(persona_app, "alice")
        (persona_app.CONFIGS_DIR / "bob.config").write_text("{}", encoding="utf-8")
        _seed_candidate(persona_app, "bob")
        from db.models import PersonaTemplate
        from db.session import get_session

        s = get_session()
        try:
            row = PersonaTemplate(
                candidate_id=alice_id,
                name="Escapee",
                path="../outside.docx",
                source="user_upload",
            )
            s.add(row)
            s.commit()
            pid = row.id
        finally:
            s.close()

        client = persona_app.app.test_client()
        r = client.post(f"/api/personas/{pid}/copy", json={"username": "bob"})
        assert r.status_code == 403

    def test_duplicate_copy_gets_a_suffixed_filename_not_clobbered(self, persona_app):
        alice_id = _seed_candidate(persona_app, "alice")
        (persona_app.CONFIGS_DIR / "bob.config").write_text("{}", encoding="utf-8")
        _seed_candidate(persona_app, "bob")
        pid = _seed_owned_persona_file(persona_app, alice_id, "alice", filename="dup.docx")

        client = persona_app.app.test_client()
        r1 = client.post(f"/api/personas/{pid}/copy", json={"username": "bob"})
        assert r1.status_code == 201
        path1 = r1.get_json()["path"]

        r2 = client.post(f"/api/personas/{pid}/copy", json={"username": "bob"})
        assert r2.status_code == 201
        path2 = r2.get_json()["path"]

        assert path1 != path2
        assert (persona_app.BASE_DIR / path1).exists()
        assert (persona_app.BASE_DIR / path2).exists()


class TestDownloadEditedPersona:
    def test_persona_template_id_resolves_under_personas_dir(self, persona_app):
        """F-10: download-edited returns a download_url; the GET serves the file.

        The route used to stream the bytes on the POST response; it now hands
        back a URL onto GET /api/download/<path> (send_file(as_attachment=True))
        so the client can follow it as a plain navigation the browser's download
        manager handles natively. Both halves are asserted: the JSON contract,
        and that the URL actually serves the templated .docx with an attachment
        Content-Disposition.
        """
        _seed_candidate(persona_app)
        pid, _ = _seed_bundled_persona_file(persona_app, "dl.docx")
        client = persona_app.app.test_client()
        r = client.post(
            "/api/download-edited",
            json={
                "username": "alice",
                "content": "# Jane\n\n## Experience\n\n- Built things",
                "type": "resume",
                "original_format": ".docx",
                "persona_template_id": pid,
            },
        )
        assert r.status_code == 200
        body = r.get_json()
        assert body["download_url"].startswith("/api/download/")
        assert body["filename"].endswith(".docx")

        dl = client.get(body["download_url"])
        assert dl.status_code == 200
        assert "attachment" in (dl.headers.get("Content-Disposition") or "")
        assert dl.data[:2] == b"PK"  # produced a real .docx (templated, not dropped)


# ---------------------------------------------------------------------------
# F-10 — GET /api/download/<path> containment (relative re-anchor + legacy abs)
# ---------------------------------------------------------------------------


class TestDownloadFileContainment:
    """The F-10 relative-path re-anchor must not weaken the _within gate."""

    def test_relative_path_serves_from_output_dir(self, persona_app):
        target = persona_app.OUTPUT_DIR / "alice" / "resume_x.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# hi", encoding="utf-8")
        client = persona_app.app.test_client()
        r = client.get("/api/download/alice/resume_x.md")
        assert r.status_code == 200
        assert "attachment" in (r.headers.get("Content-Disposition") or "")
        assert r.data == b"# hi"

    def test_relative_traversal_to_existing_file_is_403(self, persona_app):
        # A real file just OUTSIDE OUTPUT_DIR: exists() passes, _within must 403.
        # The alice/ dir must exist so the OS can walk the ".." components.
        (persona_app.OUTPUT_DIR / "alice").mkdir(parents=True, exist_ok=True)
        secret = persona_app.OUTPUT_DIR.parent / "secret.txt"
        secret.write_text("nope", encoding="utf-8")
        client = persona_app.app.test_client()
        r = client.get("/api/download/alice/../../secret.txt")
        assert r.status_code == 403

    # The absolute-path (legacy) branch is exercised at the view level: an
    # absolute POSIX path in the URL would open with "/" and double-slash the
    # route (Werkzeug merge_slashes 308s it), so the HTTP layer can't carry it
    # portably — which is exactly why download-edited now hands back a
    # RELATIVE download_url. The branch itself must keep working for any
    # legacy caller that still passes an absolute path.

    def test_absolute_path_inside_output_dir_still_serves(self, persona_app):
        from blueprints.generation import download_file

        target = persona_app.OUTPUT_DIR / "alice" / "resume_abs.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# abs", encoding="utf-8")
        with persona_app.app.test_request_context():
            resp = download_file(str(target))
        assert not isinstance(resp, tuple)  # a streamed 200, not (error, code)
        assert "attachment" in (resp.headers.get("Content-Disposition") or "")
        assert resp.status_code == 200
        resp.close()  # release the send_file handle (Windows file lock)

    def test_absolute_path_outside_output_dir_is_403(self, persona_app):
        from blueprints.generation import download_file

        secret = persona_app.OUTPUT_DIR.parent / "secret_abs.txt"
        secret.write_text("nope", encoding="utf-8")
        with persona_app.app.test_request_context():
            resp = download_file(str(secret))
        assert isinstance(resp, tuple) and resp[1] == 403
