"""Instrument — a regenerate of the same application run never reaches the DB (item 160).

`fix/regenerate-persistence`. Landed as commit 1, the reproduction (charter C-7: it
comes before any fix); kept as the regression suite once the fix lands. Evidence
record: `docs/dev/diagnosis/regenerate-persistence.md`.

Every test drives the REAL routes (the rig from
tests/test_frozen_composition_staleness.py: a fresh migrated DB, the analyzer stubbed)
and observes the DB audit chain, `resume_state`, and every persist attempt's outcome.
The persist helper is wrapped to record success or the exception text, because the
routes swallow the exception and app loggers are silent under pytest. Each test
prints its observation record as one JSON line (`-rA` shows it) and puts it in its
assertion message.

The arms are wider than item 160's filed mechanism on purpose
(AGENT_FAILURE_PATTERNS §5f): the frozen and LLM paths, both routes, the title rows
as well as the bullet rows, the cover letter, proposals, a duplicate within ONE
result, and whether a persist failure reaches the user at all. Each A-arm isolates
one mechanism (A4 and A5 select no bullets, so the bullet collision can't mask them).

The defect invariants were `xfail(strict=True)` on the base tip (quoted in the
diagnosis, `--runxfail`); the fix commit deleted only those markers. Controls held
throughout.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

import blueprints.generation as bgen
from tests.test_frozen_composition_staleness import EDITED, USER, _freeze
from tests.test_frozen_composition_staleness import rig as _rig_fixture

# The staleness instrument's rig (real routes, analyzer stubbed), registered here.
rig = _rig_fixture

PROPOSED = "ZEBRA-PROPOSED shipped usage-based pricing for the billing platform"
ALT_TITLE = "ZEBRA-ALT Group Product Manager"
LETTER = "LLM COVER LETTER"  # what the rig's cover-letter stub returns


@pytest.fixture
def persists(monkeypatch) -> list[str]:
    """Every `_persist_corpus_generation_to_db` call's outcome: 'ok' or the exception."""
    log: list[str] = []
    real = bgen._persist_corpus_generation_to_db

    def _recording(*a: Any, **k: Any) -> None:
        try:
            real(*a, **k)
        except Exception as exc:
            log.append(f"RAISED {type(exc).__name__}: {str(exc).splitlines()[0]}")
            raise
        log.append("ok")

    monkeypatch.setattr(bgen, "_persist_corpus_generation_to_db", _recording)
    return log


def _llm_results(monkeypatch, rig, *results: dict[str, Any]) -> None:
    """Replace the rig's LLM `generate` stub with one returning `results` in order."""
    queue = list(results)

    def _gen(*a: Any, **k: Any) -> dict[str, Any]:
        rig.calls["generate"] += 1
        base = {
            "resume_content": "# LLM WROTE THIS",
            "cover_letter_content": "",
            "changes_made": [],
            "proofread_notes": [],
        }
        return {**base, **queue.pop(0)}

    monkeypatch.setattr(bgen, "generate", _gen)


def _official_title_id(rig) -> int:
    from db.models import ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        return int(
            s.query(ExperienceTitle).filter_by(experience_id=rig.ids["exp"], is_official=1).one().id
        )
    finally:
        s.close()


def _add_alt_title(rig) -> int:
    from db.models import ExperienceTitle
    from db.session import get_session

    s = get_session()
    try:
        t = ExperienceTitle(
            experience_id=rig.ids["exp"],
            title=ALT_TITLE,
            is_official=0,
            truthful_enough_to_use=1,
            is_pending_review=0,
            source="manual",
        )
        s.add(t)
        s.commit()
        return int(t.id)
    finally:
        s.close()


def _observe(rig, persists: list[str], arm: str, **extra: Any) -> dict[str, Any]:
    """The DB audit chain + resume_state + the newest context, as one record."""
    from db.models import (
        ApplicationBullet,
        ApplicationRun,
        ApplicationRunTitle,
        Bullet,
        IterationLog,
        ProposalReview,
    )
    from db.session import get_session

    run_pk = rig.ctx()["application_run_id"]
    s = get_session()
    try:
        run = s.query(ApplicationRun).filter_by(id=run_pk).one()
        rec: dict[str, Any] = {
            "arm": arm,
            "persists": list(persists),
            "run_resume_md": run.generated_resume_md,
            "run_cover_letter_md": run.generated_cover_letter_md,
            "bullets": [
                (r.bullet_id, r.position)
                for r in s.query(ApplicationBullet)
                .filter_by(application_run_id=run_pk)
                .order_by(ApplicationBullet.position)
            ],
            "titles": {
                r.experience_id: r.experience_title_id
                for r in s.query(ApplicationRunTitle).filter_by(application_run_id=run_pk)
            },
            "iteration_logs": s.query(IterationLog).filter_by(application_run_id=run_pk).count(),
            "proposed_bullets": s.query(Bullet).filter_by(text=PROPOSED).count(),
            "proposal_reviews": s.query(ProposalReview)
            .filter_by(application_run_id=run_pk, original_text=PROPOSED)
            .count(),
        }
    finally:
        s.close()
    rs = rig.client.get(f"/api/applications/{rig.aid}").get_json()["resume_state"]
    rec["resume_state_resume_md"] = rs.get("resume_md")
    rec["resume_state_cover_letter_md"] = rs.get("cover_letter_md")
    rec.update(extra)
    print(json.dumps(rec, default=str))
    return rec


def _follow(rig, child: str) -> None:
    """Point the rig at a generate's child context, as the client does."""
    rig.cp = child
    rig.state["context_path"] = child


# -------------------------------------------------------------------
# Controls
# -------------------------------------------------------------------


class TestControls:
    def test_c1_one_frozen_generate_persists(self, rig, persists):
        _freeze(rig)
        g = rig.generate()
        assert g["status"] == 200, g
        rec = _observe(rig, persists, "C1")
        assert rec["persists"] == ["ok"], rec
        assert rec["run_resume_md"] == g["resume_md"], rec
        assert rec["resume_state_resume_md"] == g["resume_md"], rec
        assert rec["iteration_logs"] == 1, rec

    def test_c2_a_context_without_a_run_attempts_no_persist(self, rig, persists):
        ctx = rig.ctx()
        ctx.pop("application_run_id")
        rig.write_ctx(ctx)
        g = rig.generate()
        assert g["status"] == 200, g
        assert persists == [], persists


# -------------------------------------------------------------------
# Defect invariants (failed on the base tip; diagnosis O1-O7)
# -------------------------------------------------------------------


def _regenerate_after_reapproval(rig, how: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Freeze → generate → (on the child) a Compose edit → re-freeze → generate again."""
    drive = rig.generate if how == "json" else rig.generate_stream
    _freeze(rig)
    first = drive()
    assert first["status"] == 200, first
    _follow(rig, first["child"])
    rig.compose_corpus_edit("PUT", f"/api/bullets/{rig.ids['b1']}", {"text": EDITED})
    _freeze(rig)
    second = drive()
    assert second["status"] == 200, second
    assert EDITED in second["resume_md"]
    _follow(rig, second["child"])
    return first, second


@pytest.mark.parametrize("how", ["json", "stream"])
def test_a1_a2_regenerate_reaches_the_run_and_resume_state(rig, persists, how):
    _first, second = _regenerate_after_reapproval(rig, how)
    rec = _observe(rig, persists, f"A1A2-{how}")
    assert rec["persists"] == ["ok", "ok"], rec
    assert rec["run_resume_md"] == second["resume_md"], rec
    assert EDITED in (rec["resume_state_resume_md"] or ""), rec
    assert rec["iteration_logs"] == 2, rec


def test_a3_the_run_rows_are_the_latest_selection(rig, persists, monkeypatch):
    exp, b1, b2 = rig.ids["exp"], rig.ids["b1"], rig.ids["b2"]
    t_official, t_alt = _official_title_id(rig), _add_alt_title(rig)
    _llm_results(
        monkeypatch,
        rig,
        {
            "resume_content": "# FIRST",
            "selected_bullets": [
                {
                    "experience_id": f"e{exp}",
                    "chosen_title_id": f"t{t_official}",
                    "bullet_ids_in_order": [f"b{b1}", f"b{b2}"],
                }
            ],
        },
        {
            "resume_content": "# SECOND",
            "selected_bullets": [
                {
                    "experience_id": f"e{exp}",
                    "chosen_title_id": f"t{t_alt}",
                    "bullet_ids_in_order": [f"b{b2}"],
                }
            ],
        },
    )
    first = rig.generate()
    assert first["status"] == 200, first
    _follow(rig, first["child"])
    second = rig.generate()
    assert second["status"] == 200, second
    rec = _observe(rig, persists, "A3")
    assert rec["persists"] == ["ok", "ok"], rec
    assert rec["bullets"] == [(b2, 0)], rec
    assert rec["titles"] == {exp: t_alt}, rec
    # The corpus path re-renders the résumé, so compare with what the route returned.
    assert rec["run_resume_md"] == second["resume_md"], rec


def test_a4_a_resume_only_regenerate_keeps_the_detached_cover_letter(rig, persists, monkeypatch):
    import analyzer

    # The cover-letter route imports this inside the function, so the rig's patch on
    # blueprints.generation never reaches it; patch it at its source.
    monkeypatch.setattr(
        analyzer,
        "generate_cover_letter_against_resume",
        lambda *a, **k: {"cover_letter_content": LETTER},
    )
    # No selected bullets on either generate, so no collision can mask this arm.
    _llm_results(monkeypatch, rig, {"resume_content": "# FIRST"}, {"resume_content": "# SECOND"})
    first = rig.generate()
    assert first["status"] == 200, first
    _follow(rig, first["child"])
    cl = rig.client.post(
        "/api/generate-cover-letter", json={"username": USER, "context_path": rig.cp}
    )
    assert cl.status_code == 200, cl.get_data(as_text=True)
    between = _observe(rig, persists, "A4-after-letter")
    assert between["run_cover_letter_md"] == LETTER, between
    second = rig.generate()
    assert second["status"] == 200, second
    child_letter = rig.ctx(second["child"]).get("last_generated_cover_letter")
    _follow(rig, second["child"])
    rec = _observe(rig, persists, "A4", child_ctx_last_generated_cover_letter=child_letter)
    assert rec["persists"] == ["ok", "ok"], rec
    assert rec["run_resume_md"] == second["resume_md"], rec
    assert rec["run_cover_letter_md"] == LETTER, rec
    assert rec["resume_state_cover_letter_md"] == LETTER, rec


def test_a5_the_same_proposal_twice_is_one_pending_bullet(rig, persists, monkeypatch):
    proposal = {
        "proposed_new_bullets": [
            {"experience_id": f"e{rig.ids['exp']}", "text": PROPOSED, "pattern_kind": "xyz"}
        ]
    }
    _llm_results(monkeypatch, rig, dict(proposal), dict(proposal))
    first = rig.generate()
    assert first["status"] == 200, first
    _follow(rig, first["child"])
    second = rig.generate()
    assert second["status"] == 200, second
    rec = _observe(rig, persists, "A5")
    assert rec["persists"] == ["ok", "ok"], rec
    assert rec["proposed_bullets"] == 1, rec
    assert rec["proposal_reviews"] == 1, rec


def test_a6_a_duplicate_within_one_result_still_persists(rig, persists, monkeypatch):
    exp, b1, b2 = rig.ids["exp"], rig.ids["b1"], rig.ids["b2"]
    t_official = _official_title_id(rig)
    _llm_results(
        monkeypatch,
        rig,
        {
            "resume_content": "# DUPES",
            "selected_bullets": [
                {
                    "experience_id": f"e{exp}",
                    "chosen_title_id": f"t{t_official}",
                    "bullet_ids_in_order": [f"b{b1}", f"b{b1}"],
                },
                {
                    "experience_id": f"e{exp}",
                    "chosen_title_id": f"t{t_official}",
                    "bullet_ids_in_order": [f"b{b2}"],
                },
            ],
        },
    )
    g = rig.generate()
    assert g["status"] == 200, g
    _follow(rig, g["child"])
    rec = _observe(rig, persists, "A6")
    assert rec["persists"] == ["ok"], rec
    assert rec["run_resume_md"] == g["resume_md"], rec
    assert [bid for bid, _ in rec["bullets"]] == [b1, b2], rec


@pytest.mark.parametrize("how", ["json", "stream"])
def test_a7_a_persist_failure_reaches_the_response(rig, monkeypatch, how):
    import db.persist_run

    def _boom(*a: Any, **k: Any) -> None:
        raise RuntimeError("forced persist failure")

    monkeypatch.setattr(db.persist_run, "persist_corpus_generation", _boom)
    _freeze(rig)
    if how == "json":
        r = rig.client.post(
            "/api/generate",
            json={"username": USER, "context_path": rig.cp, "output_format": ".md"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
    else:
        from tests.test_frozen_composition_staleness import _parse_sse

        r = rig.client.post(
            "/api/generate/stream",
            json={"username": USER, "context_path": rig.cp, "output_format": ".md"},
        )
        body = next(p for ev, p in _parse_sse(r.get_data(as_text=True)) if ev == "done")
    record = {"arm": f"A7-{how}", "response_keys": sorted(body)}
    print(json.dumps(record))
    assert body.get("persist_failed") is True, record


@pytest.mark.parametrize("how", ["json", "stream"])
def test_a7_control_a_successful_persist_reports_no_failure(rig, how):
    _freeze(rig)
    if how == "json":
        g = rig.client.post(
            "/api/generate",
            json={"username": USER, "context_path": rig.cp, "output_format": ".md"},
        )
        body = g.get_json()
    else:
        from tests.test_frozen_composition_staleness import _parse_sse

        g = rig.client.post(
            "/api/generate/stream",
            json={"username": USER, "context_path": rig.cp, "output_format": ".md"},
        )
        body = next(p for ev, p in _parse_sse(g.get_data(as_text=True)) if ev == "done")
    assert body["persist_failed"] is False, sorted(body)


def test_the_client_shows_the_persist_failure():
    """The banner exists, and `_renderOutput` toggles it from the payload field."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    html = (repo / "templates" / "index.html").read_text(encoding="utf-8")
    js = (repo / "static" / "app.js").read_text(encoding="utf-8")
    assert 'id="persistFailedNotice"' in html
    start = js.index("function _renderOutput(data)")
    body = js[start : js.index("\n}\n", start)]
    assert "getElementById('persistFailedNotice')" in body
    assert "!data.persist_failed" in body
