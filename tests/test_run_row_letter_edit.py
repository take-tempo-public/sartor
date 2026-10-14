"""Instrument — a generate that consumes the typed letter edit leaves it on the run row (item 163).

`fix/run-row-letter-edit-shadow`. Landed as commit 1, the reproduction (charter C-7: it
comes before any fix). Evidence record: `docs/dev/diagnosis/run-row-letter-edit-shadow.md`.

Item 163 was filed from `fix/regenerate-keeps-cover-letter`'s control C3: after a typed
letter edit, a with-letter generate consumes the edit in the CONTEXT but not on the run row,
and `resume_state` reads `r.edited_cover_letter_text or r.generated_cover_letter_md`
(`blueprints/applications.py` `_build_resume_state`), so a Pipeline resume shows the typed
text while the wizard shows the new letter. That half was observed; the same shadow after
`/api/generate-cover-letter` was only inferred. This file observes both.

Every arm drives the REAL routes (the rig from tests/test_frozen_composition_staleness.py: a
fresh migrated DB, the analyzer stubbed) and prints one JSON observation record per arm
(`-rA` shows it; it is also in each assertion message). The arms are wider than the filed
hypothesis on purpose (AGENT_FAILURE_PATTERNS §5f): both generate routes, the detached
cover-letter route, the `has_edits` flag the same column feeds, and the frozen
`carry_edits=True` path, which keeps the typed edit over a produced letter by design.

The defect invariants are `xfail(strict=True, raises=AssertionError)` on the base tip (quote
them with `--runxfail`); the fix commit deletes only those markers. Drive steps and controls
raise `ControlFailed` through `tests._controls.control`, never a bare `assert`, so a broken
drive fails the arm instead of passing as the defect it exists to catch.
"""

from __future__ import annotations

from typing import Any

import pytest

import blueprints.generation as bgen
from tests._controls import control as _control
from tests.test_frozen_composition_staleness import B1, USER, _freeze
from tests.test_frozen_composition_staleness import TYPED as TYPED_RESUME
from tests.test_frozen_composition_staleness import rig as _rig_fixture
from tests.test_regenerate_cover_letter import (
    REWRITTEN,
    TYPED,
    _detach_letter,
    _post_generate,
)
from tests.test_regenerate_persistence import _follow, _observe
from tests.test_regenerate_persistence import persists as _persists_fixture

# The staleness instrument's rig and the item-160 persist recorder, registered here.
rig = _rig_fixture
persists = _persists_fixture


# -------------------------------------------------------------------
# Drive + observation helpers
# -------------------------------------------------------------------


def _generate_stub(monkeypatch, rig, *results: dict[str, Any]) -> None:
    """Replace BOTH the JSON route's `generate` and the SSE route's `generate_streaming`.

    `tests/test_regenerate_cover_letter.py::_generate_stub` replaces only `generate`, so a
    `/api/generate/stream` drive reaches the rig's own stream stub, which never returns a
    letter. The `[stream]` arm of this file's first run raised `ControlFailed` on exactly
    that (the convention working). Results are consumed in call order across both routes.
    """
    queue = list(results)
    base = {
        "resume_content": "# LLM WROTE THIS",
        "cover_letter_content": "",
        "changes_made": [],
        "proofread_notes": [],
    }

    def _gen(*a: Any, **k: Any) -> dict[str, Any]:
        rig.calls["generate"] += 1
        return {**base, **queue.pop(0)}

    def _stream(*a: Any, **k: Any):
        rig.calls["generate_streaming"] += 1
        yield ("done", {**base, **queue.pop(0)})

    monkeypatch.setattr(bgen, "generate", _gen)
    monkeypatch.setattr(bgen, "generate_streaming", _stream)


def _run_row(rig) -> dict[str, Any]:
    """The run row's edit columns and the `has_edits` flag the same column feeds."""
    from db.models import ApplicationRun
    from db.session import get_session

    run_pk = rig.ctx()["application_run_id"]
    s = get_session()
    try:
        run = s.query(ApplicationRun).filter_by(id=run_pk).one()
        row = {
            "run_edited_cover_letter_text": run.edited_cover_letter_text,
            "run_edited_resume_text": run.edited_resume_text,
        }
    finally:
        s.close()
    body = rig.client.get(f"/api/applications/{rig.aid}").get_json()
    runs = [r for r in body["runs"] if r["id"] == run_pk]
    _control(len(runs) == 1, body.get("runs"))
    row["has_edits"] = runs[0]["has_edits"]
    return row


def _type_letter_edit(rig, **extra: Any) -> None:
    """Save a typed letter edit through `/api/save-edits`, as the editor does."""
    saved = rig.client.post(
        "/api/save-edits",
        json={"username": USER, "context_path": rig.cp, "edited_cover_letter": TYPED, **extra},
    )
    _control(saved.status_code == 200, saved.get_data(as_text=True))
    # The edit landed on BOTH sides before the arm's action, or the arm proves nothing.
    _control(rig.ctx().get("edited_cover_letter_text") == TYPED, "typed edit not in the context")
    _control(
        _run_row(rig)["run_edited_cover_letter_text"] == TYPED, "typed edit not on the run row"
    )


def _letter_then_typed_edit(rig, monkeypatch, *, second: dict[str, Any]) -> None:
    """Generate, detach a letter, type a letter edit; leave `rig.cp` on the editable context."""
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"}, second)
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    _type_letter_edit(rig)


def _record(rig, persists, arm: str, body: dict[str, Any] | None = None, **extra: Any):
    ctx_path = body["context_path"] if body else rig.cp
    child = rig.ctx(ctx_path)
    return _observe(
        rig,
        persists,
        arm,
        child_last_generated_cover_letter=child.get("last_generated_cover_letter"),
        child_edited_cover_letter_text=child.get("edited_cover_letter_text"),
        **_run_row(rig),
        **extra,
    )


# -------------------------------------------------------------------
# Controls (hold on the base tip, and after the fix)
# -------------------------------------------------------------------


class TestControls:
    def test_c1_saving_a_letter_edit_writes_the_context_and_the_run_row(
        self, rig, persists, monkeypatch
    ):
        _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"})
        first = _post_generate(rig)
        _follow(rig, first["context_path"])
        _detach_letter(rig, monkeypatch)
        _type_letter_edit(rig)
        rec = _record(rig, persists, "C1")
        assert rec["run_edited_cover_letter_text"] == TYPED, rec
        assert rec["has_edits"] is True, rec
        assert rec["resume_state_cover_letter_md"] == TYPED, rec

    @pytest.mark.parametrize("how", ["json", "stream"])
    def test_c2_a_resume_only_regenerate_keeps_the_run_row_letter_edit(
        self, rig, persists, monkeypatch, how
    ):
        """Owner decision D4: a generate that produced no letter never read the edit."""
        _letter_then_typed_edit(rig, monkeypatch, second={"resume_content": "# SECOND"})
        second = _post_generate(rig, how)
        rec = _record(rig, persists, f"C2-{how}", second)
        assert rec["child_edited_cover_letter_text"] == TYPED, rec
        assert rec["run_edited_cover_letter_text"] == TYPED, rec
        assert rec["resume_state_cover_letter_md"] == TYPED, rec

    def test_c3_a_discarded_resume_edit_keeps_the_run_row_letter_edit(
        self, rig, persists, monkeypatch
    ):
        """Decision 4 discards the typed RÉSUMÉ edit only (item 162's B8, run-row side)."""
        _freeze(rig)
        first = rig.generate()
        _control(first["status"] == 200, first)
        _follow(rig, first["child"])
        _detach_letter(rig, monkeypatch)
        saved = rig.client.post(
            "/api/save-edits",
            json={
                "username": USER,
                "context_path": rig.cp,
                "edited_resume": first["resume_md"].replace(B1, TYPED_RESUME),
                "edited_cover_letter": TYPED,
            },
        )
        _control(saved.status_code == 200, saved.get_data(as_text=True))
        rig.compose_corpus_edit("PUT", f"/api/bullets/{rig.ids['b1']}", {"text": "ZEBRA-CHANGED"})
        _freeze(rig)
        body = _post_generate(rig)
        _control(body.get("edits_discarded") is True, body)  # decision 4 held
        rec = _record(rig, persists, "C3", body)
        assert rec["run_edited_resume_text"] is None, rec
        assert rec["run_edited_cover_letter_text"] == TYPED, rec


# -------------------------------------------------------------------
# Defect invariants (diagnosis A1-A3)
# -------------------------------------------------------------------

_DEFECT = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="item 163: the run row's letter edit is not consumed with the context's",
)


@_DEFECT
@pytest.mark.parametrize("how", ["json", "stream"])
def test_a1_a2_a_with_letter_generate_consumes_the_run_row_letter_edit(
    rig, persists, monkeypatch, how
):
    _letter_then_typed_edit(
        rig,
        monkeypatch,
        second={"resume_content": "# SECOND", "cover_letter_content": REWRITTEN},
    )
    second = _post_generate(rig, how, generate_cover_letter=True)
    rec = _record(rig, persists, f"A1A2-{how}", second)
    # Controls: the context did what it should, and the run row holds the new letter.
    _control(rec["child_last_generated_cover_letter"] == REWRITTEN, rec)
    _control(rec["child_edited_cover_letter_text"] is None, rec)
    _control(rec["run_cover_letter_md"] == REWRITTEN, rec)
    assert rec["run_edited_cover_letter_text"] is None, rec
    assert rec["resume_state_cover_letter_md"] == REWRITTEN, rec


@_DEFECT
def test_a3_the_detached_letter_route_consumes_the_run_row_letter_edit(rig, persists, monkeypatch):
    """The inferred half: `/api/generate-cover-letter` pops the context edit, writes only md."""
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"})
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    _type_letter_edit(rig)
    _detach_letter(rig, monkeypatch, REWRITTEN)  # a second detached letter, over the edit
    rec = _record(rig, persists, "A3")
    # Controls: the context consumed the edit, and the run row holds the new letter.
    _control(rec["child_last_generated_cover_letter"] == REWRITTEN, rec)
    _control(rec["child_edited_cover_letter_text"] is None, rec)
    _control(rec["run_cover_letter_md"] == REWRITTEN, rec)
    assert rec["run_edited_cover_letter_text"] is None, rec
    assert rec["resume_state_cover_letter_md"] == REWRITTEN, rec


# -------------------------------------------------------------------
# Observe-only (no invariant asserted; the record is the deliverable)
# -------------------------------------------------------------------


def test_a5_the_frozen_carry_path_keeps_the_typed_letter_over_a_produced_one(
    rig, persists, monkeypatch
):
    """`carry_edits=True` with a letter produced: record whether context and run row agree.

    The handoff carried this as "existing, unobserved". The frozen path keeps BOTH typed
    edits over an unchanged re-assemble by design (decision 4), so this arm asserts only
    that the context and the run row AGREE with each other; whether keeping the edit over
    a newly produced letter is right is an owner question, not decided here.
    """
    _freeze(rig)
    first = rig.generate()
    _control(first["status"] == 200, first)
    _follow(rig, first["child"])
    _detach_letter(rig, monkeypatch)
    saved = rig.client.post(
        "/api/save-edits",
        json={
            "username": USER,
            "context_path": rig.cp,
            "edited_resume": first["resume_md"].replace(B1, TYPED_RESUME),
            "edited_cover_letter": TYPED,
        },
    )
    _control(saved.status_code == 200, saved.get_data(as_text=True))
    body = _post_generate(rig, generate_cover_letter=True)
    _control(body.get("edits_discarded") is False, body)  # same composition: edits carried
    rec = _record(
        rig,
        persists,
        "A5",
        body,
        response_edited_cover_letter=body.get("edited_cover_letter_text"),
    )
    assert (rec["child_edited_cover_letter_text"] or None) == (
        rec["run_edited_cover_letter_text"] or None
    ), rec
