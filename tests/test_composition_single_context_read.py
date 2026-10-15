"""GET /api/applications/<id>/composition reads its context file exactly once.

Item 161. The route used to call eleven `_read_*` helpers that each validated, read and
`json.loads`'d the same context file; the eleventh was added by
`fix/frozen-composition-staleness` and the consolidation was deferred. The count only ever
grows by one helper at a time, so this is the fail-closed guard against the next one:
a helper that opens the file itself brings `reads_per_get` to 2 and fails here.

Evidence and the before/after measurement:
`docs/dev/diagnosis/compose-single-context-parse.md`.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest


@pytest.fixture
def composition_app(tmp_path, monkeypatch, _migrated_template_db):
    """Factory-built app over a per-test copy of the migrated template DB.

    Same shape as `tests/test_composition_summary.py::composition_app` (PX-44 rollout):
    returns `(namespace, output_dir)`.
    """
    from tests.conftest import _fresh_migrated_db

    db_file = _fresh_migrated_db(
        tmp_path, monkeypatch, _migrated_template_db, filename="comp.sqlite"
    )

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    output_dir = cfg.output_dir
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (output_dir / "casey").mkdir()

    from db.session import init_db

    assert init_db(db_file) is False, "expected the pre-registered copy to skip alembic"
    return types.SimpleNamespace(app=app), output_dir


def _seed_application() -> int:
    from db.models import Application, Candidate
    from db.session import get_session

    session = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        session.add(c)
        session.flush()
        a = Application(
            candidate_id=c.id,
            title="Senior PM",
            jd_text="Senior PM building AI platforms.",
            jd_fingerprint="f" * 16,
        )
        session.add(a)
        session.commit()
        return int(a.id)
    finally:
        session.close()


def _context_path(output_dir: Path, document: str) -> str:
    path = output_dir / "casey" / "ctx0.json"
    path.write_text(document, encoding="utf-8")
    return str(path)


def test_get_composition_reads_the_context_file_exactly_once(
    composition_app, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, output_dir = composition_app
    aid = _seed_application()
    ctx = {
        "application_id": aid,
        "iteration": 0,
        "llm_analysis": {"essential_skills": ["ai-platform"]},
        "composition_overrides": {"pinned": [], "excluded": [], "added": []},
        "career_corpus": [{"id": 1, "company": "Acme", "titles": ["Senior PM"], "bullets": []}],
    }
    ctx_path = _context_path(output_dir, json.dumps(ctx))

    real_read_text = Path.read_text
    reads: list[str] = []

    def counting_read_text(self: Path, *args, **kwargs):
        if str(self) == ctx_path:
            reads.append(str(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    r = app.app.test_client().get(f"/api/applications/{aid}/composition?context_path={ctx_path}")

    assert r.status_code == 200
    assert len(reads) == 1, (
        f"GET /composition read the context file {len(reads)} times; it must be exactly once "
        "(a new _read_* helper opening the file itself is the usual cause)"
    )


@pytest.mark.parametrize("document", ["null", "[1, 2]", '"text"', "{not json"])
def test_get_composition_degrades_on_a_non_object_context(composition_app, document: str) -> None:
    """A context that is not a JSON object is treated as absent, not as a 500."""
    app, output_dir = composition_app
    aid = _seed_application()
    ctx_path = _context_path(output_dir, document)

    r = app.app.test_client().get(f"/api/applications/{aid}/composition?context_path={ctx_path}")

    assert r.status_code == 200
    body = r.get_json()
    assert body["has_gap_fill"] is False
    assert body["has_frozen_composition"] is False
    assert body["composition_stale"] is False
    assert body["skills"]["has_recommendation"] is False
