"""Instrument — a generate that would lose a typed edit must ask first (item 170).

`feat/confirm-before-overwriting-typed-edits`. Landed as commit 1, the instrument (charter
C-7/C-10: the dossier `docs/dev/blast-radius/confirm-before-overwriting-typed-edits.md` and
this file come before any production edit).

Item 170 (owner request, 2026-10-14): warn with Continue or Cancel **before** a typed edit is
overwritten. The owner chose a server handshake: the route answers a pre-persist, pre-LLM
`409 {error, edits_would_be_discarded: true, discards: [...]}`, and the client re-sends with
`confirm_discard_edits: true` after Continue. Cancel sends nothing, so a refused request must
have changed nothing.

The three cases (all driven through the REAL routes on the staleness rig: a fresh migrated DB,
the analyzer stubbed):

1. **Résumé edit** (frozen path only): a re-approved composition changed the résumé a typed
   résumé edit was made over (`_typed_edits_disposition`, decision 4 of
   `fix/frozen-composition-staleness`). `/api/generate` and `/api/generate/stream`.
2. **Letter edit, with-letter generate**: a generate that produces a letter consumes the typed
   letter edit unless `carry_edits` keeps it. Both generate routes, legacy and frozen paths.
3. **Letter edit, detached**: `/api/generate-cover-letter` pops the typed letter edit.

What each defect arm asserts, in this order:

* a `409` carrying `edits_would_be_discarded` and the right `discards` list (the invariant,
  a plain `assert`, the only expected failure);
* **no LLM spend** (the cover-letter call happens INSIDE `_assemble_from_frozen_composition`,
  so the check must run before it);
* **nothing changed**: the context file's bytes, the output directory's file list and the run
  row's audit state are identical to before the request (Cancel changes nothing).

The controls hold on `main` and after the fix: the cases where a prompt must **not** fire
(`carry_edits`, résumé-only, no typed edit, a confirm flag with nothing to discard) and the
Continue path (the flag is sent, the request succeeds, the edit is discarded as today). On
`main` the flag is an unknown key and is ignored, so the Continue controls already pass.

The defect invariants are `xfail(strict=True, raises=AssertionError)`; the fix commit deletes
only those markers. Drive steps and controls raise `ControlFailed` through
`tests._controls.control`, never a bare `assert`, so a broken drive fails the arm instead of
passing as the defect it exists to catch (item 167).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import analyzer
from json_resume import json_resume_to_markdown
from tests._controls import control as _control
from tests.test_frozen_composition_staleness import B1, USER, _freeze, _parse_sse
from tests.test_frozen_composition_staleness import TYPED as TYPED_RESUME
from tests.test_frozen_composition_staleness import rig as _rig_fixture
from tests.test_regenerate_cover_letter import REWRITTEN, TYPED, _detach_letter
from tests.test_regenerate_persistence import _follow, _observe
from tests.test_regenerate_persistence import persists as _persists_fixture
from tests.test_run_row_letter_edit import (
    _generate_stub,
    _letter_then_typed_edit,
    _run_row,
    _type_letter_edit,
)

# The staleness instrument's rig and the item-160 persist recorder, registered here.
rig = _rig_fixture
persists = _persists_fixture

_DEFECT = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="item 170: a generate that loses a typed edit does not ask first",
)

_HOWS = ["json", "stream"]
_EDITED = "ZEBRA-CHANGED"


# -------------------------------------------------------------------
# Drive + observation helpers
# -------------------------------------------------------------------


def _post(rig, how: str, **extra: Any) -> dict[str, Any]:
    """POST a generate route; return `{status, body}` for both a JSON and an SSE answer.

    A refusal is plain JSON on both routes (the stream route answers before it opens). A
    success on the stream route is the SSE `done` payload.
    """
    url = "/api/generate" if how == "json" else "/api/generate/stream"
    r = rig.client.post(
        url,
        json={"username": USER, "context_path": rig.cp, "output_format": ".md", **extra},
    )
    if r.mimetype == "text/event-stream":
        events = _parse_sse(r.get_data(as_text=True))
        done = next((p for ev, p in events if ev == "done"), None)
        err = next((p for ev, p in events if ev == "error"), None)
        body = dict(done if done is not None else (err or {"_events": [ev for ev, _ in events]}))
        return {"status": r.status_code, "body": body, "sse": True}
    return {"status": r.status_code, "body": dict(r.get_json() or {}), "sse": False}


def _post_letter(rig, **extra: Any) -> dict[str, Any]:
    """POST the detached cover-letter route."""
    r = rig.client.post(
        "/api/generate-cover-letter",
        json={"username": USER, "context_path": rig.cp, **extra},
    )
    return {"status": r.status_code, "body": dict(r.get_json() or {}), "sse": False}


def _count_detached(monkeypatch, text: str = REWRITTEN) -> dict[str, int]:
    """Stub the detached letter LLM (imported inside the route, so patch `analyzer`) and count it."""
    seen = {"calls": 0}

    def _letter(*a: Any, **k: Any) -> dict[str, str]:
        seen["calls"] += 1
        return {"cover_letter_content": text}

    monkeypatch.setattr(analyzer, "generate_cover_letter_against_resume", _letter)
    return seen


def _llm_total(rig, detached: dict[str, int] | None = None) -> int:
    """Every LLM stub call so far: résumé, streamed résumé, the in-assemble letter, detached."""
    n = sum(rig.calls[k] for k in ("generate", "generate_streaming", "cover_letter_llm"))
    return n + (detached["calls"] if detached else 0)


def _snapshot(rig, persists) -> dict[str, Any]:
    """Everything a refused request must leave alone: context bytes, files, run-row audit chain."""
    obs = _observe(rig, persists, "snapshot")
    obs.pop("arm", None)
    row = _run_row(rig)
    files = sorted(
        str(p.relative_to(rig.output_dir)) for p in rig.output_dir.rglob("*") if p.is_file()
    )
    return {
        "context_sha256": hashlib.sha256(Path(rig.cp).read_bytes()).hexdigest(),
        "files": files,
        "run_row": row,
        "observe": obs,
    }


def _case1_setup(rig, monkeypatch, *, letter_edit: bool) -> None:
    """Frozen, a typed résumé edit saved, then Compose changed and re-approved.

    The mirror of `test_run_row_letter_edit.py` C3. With `letter_edit`, a letter exists and a
    typed letter edit was saved in the same call (the decision-4 discard consumes only the
    résumé edit, so the letter edit survives and is not part of `discards`).
    """
    _freeze(rig)
    first = rig.generate()
    _control(first["status"] == 200, first)
    _follow(rig, first["child"])
    payload: dict[str, Any] = {
        "username": USER,
        "context_path": rig.cp,
        "edited_resume": first["resume_md"].replace(B1, TYPED_RESUME),
    }
    if letter_edit:
        _detach_letter(rig, monkeypatch)
        payload["edited_cover_letter"] = TYPED
    saved = rig.client.post("/api/save-edits", json=payload)
    _control(saved.status_code == 200, saved.get_data(as_text=True))
    rig.compose_corpus_edit("PUT", f"/api/bullets/{rig.ids['b1']}", {"text": _EDITED})
    _freeze(rig)
    ctx = rig.ctx()
    _control(bool(ctx.get("edited_resume_text")), "typed résumé edit is not in the context")
    # The exact condition `_typed_edits_disposition` discards on, read from the context itself.
    _control(
        json_resume_to_markdown(ctx["approved_composition"]) != ctx.get("last_generated_resume"),
        "the approved composition did not change under the typed edit",
    )
    if letter_edit:
        _control(ctx.get("edited_cover_letter_text") == TYPED, "typed letter edit not saved")


def _case2_frozen_setup(rig, monkeypatch) -> None:
    """Frozen, a letter exists, a typed LETTER edit saved, no typed résumé edit (so no carry)."""
    _freeze(rig)
    first = rig.generate()
    _control(first["status"] == 200, first)
    _follow(rig, first["child"])
    _detach_letter(rig, monkeypatch)
    _type_letter_edit(rig)
    _control(not rig.ctx().get("edited_resume_text"), "a typed résumé edit exists; this is carry")


def _carry_setup(rig, monkeypatch) -> None:
    """Frozen, typed résumé AND letter edits over an UNCHANGED composition (`carry_edits`)."""
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
    ctx = rig.ctx()
    _control(
        json_resume_to_markdown(ctx["approved_composition"]) == ctx.get("last_generated_resume"),
        "the composition changed; this is not the carry case",
    )


def _refusal(
    arm: str,
    res: dict[str, Any],
    *,
    llm_spent: int,
    unchanged: bool,
    discards: list[str],
) -> dict[str, Any]:
    """One JSON observation record per defect arm (`-rA` shows it; it is in the assert message)."""
    rec = {
        "arm": arm,
        "status": res["status"],
        "edits_would_be_discarded": res["body"].get("edits_would_be_discarded"),
        "discards": res["body"].get("discards"),
        "expected_discards": discards,
        "composition_stale": res["body"].get("composition_stale"),
        "llm_calls_spent": llm_spent,
        "unchanged": unchanged,
    }
    print(json.dumps(rec, default=str, sort_keys=True))
    return rec


def _assert_refused(rec: dict[str, Any], res: dict[str, Any], discards: list[str]) -> None:
    """The handshake contract: refuse with the right body, spend nothing, change nothing."""
    assert res["status"] == 409, rec
    assert res["body"].get("edits_would_be_discarded") is True, rec
    assert res["body"].get("discards") == discards, rec
    assert not res["body"].get("composition_stale"), rec  # a different 409; do not conflate
    assert res["body"].get("error"), rec
    assert rec["llm_calls_spent"] == 0, rec
    assert rec["unchanged"] is True, rec


# -------------------------------------------------------------------
# Controls (hold on main, and after the fix)
# -------------------------------------------------------------------


class TestControls:
    @pytest.mark.parametrize("how", _HOWS)
    def test_c1_continue_proceeds_and_discards_the_resume_edit(
        self, rig, persists, monkeypatch, how
    ):
        """Case 1 with the flag: succeeds and discards, exactly as today (decision 4)."""
        _case1_setup(rig, monkeypatch, letter_edit=True)
        res = _post(rig, how, confirm_discard_edits=True)
        assert res["status"] == 200, res
        assert res["body"].get("edits_discarded") is True, res["body"]
        assert res["body"].get("edited_resume_text") == "", res["body"]
        # The typed LETTER edit is independent of the composition (owner decision D4).
        assert res["body"].get("edited_cover_letter_text") == TYPED, res["body"]
        assert _run_row(rig)["run_edited_resume_text"] is None

    @pytest.mark.parametrize("how", _HOWS)
    def test_c2_continue_proceeds_and_consumes_the_letter_edit(
        self, rig, persists, monkeypatch, how
    ):
        """Case 2 with the flag: the new letter replaces the typed edit, on both sides (item 163)."""
        _letter_then_typed_edit(
            rig,
            monkeypatch,
            second={"resume_content": "# SECOND", "cover_letter_content": REWRITTEN},
        )
        res = _post(rig, how, generate_cover_letter=True, confirm_discard_edits=True)
        assert res["status"] == 200, res
        assert res["body"].get("cover_letter_preview") == REWRITTEN, res["body"]
        assert res["body"].get("edited_cover_letter_text") == "", res["body"]
        assert _run_row(rig)["run_edited_cover_letter_text"] is None

    def test_c3_continue_proceeds_and_consumes_the_letter_edit_detached(
        self, rig, persists, monkeypatch
    ):
        """Case 3 with the flag: the detached letter replaces the typed edit."""
        _letter_then_typed_edit(rig, monkeypatch, second={"resume_content": "# SECOND"})
        _count_detached(monkeypatch)
        res = _post_letter(rig, confirm_discard_edits=True)
        assert res["status"] == 200, res
        assert res["body"].get("cover_letter_preview") == REWRITTEN, res["body"]
        assert rig.ctx().get("edited_cover_letter_text") is None
        assert _run_row(rig)["run_edited_cover_letter_text"] is None

    @pytest.mark.parametrize("how", _HOWS)
    def test_c4_carry_keeps_the_typed_letter_so_nothing_is_asked(
        self, rig, persists, monkeypatch, how
    ):
        """Over an unchanged composition both edits are carried: nothing is lost, no prompt."""
        _carry_setup(rig, monkeypatch)
        res = _post(rig, how, generate_cover_letter=True)
        assert res["status"] == 200, res
        assert res["body"].get("edits_discarded") is False, res["body"]
        assert res["body"].get("edited_cover_letter_text") == TYPED, res["body"]
        assert not res["body"].get("edits_would_be_discarded"), res["body"]

    @pytest.mark.parametrize("how", _HOWS)
    def test_c5_a_resume_only_generate_never_reads_the_letter_edit(
        self, rig, persists, monkeypatch, how
    ):
        """Owner decision D4: no letter requested, so the typed letter edit is not at risk."""
        _case2_frozen_setup(rig, monkeypatch)
        res = _post(rig, how)  # no generate_cover_letter
        assert res["status"] == 200, res
        assert not res["body"].get("edits_would_be_discarded"), res["body"]
        assert res["body"].get("edited_cover_letter_text") == TYPED, res["body"]

    @pytest.mark.parametrize("how", _HOWS)
    def test_c6_a_with_letter_generate_with_no_typed_edit_asks_nothing(
        self, rig, persists, monkeypatch, how
    ):
        _freeze(rig)
        first = rig.generate()
        _control(first["status"] == 200, first)
        _follow(rig, first["child"])
        _control(not rig.ctx().get("edited_cover_letter_text"), "unexpected typed letter edit")
        res = _post(rig, how, generate_cover_letter=True)
        assert res["status"] == 200, res
        assert not res["body"].get("edits_would_be_discarded"), res["body"]

    def test_c7_a_detached_letter_with_no_typed_edit_asks_nothing(self, rig, persists, monkeypatch):
        _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"})
        first = _post(rig, "json")
        _control(first["status"] == 200, first)
        _follow(rig, first["body"]["context_path"])
        _control(not rig.ctx().get("edited_cover_letter_text"), "unexpected typed letter edit")
        _count_detached(monkeypatch)
        res = _post_letter(rig)
        assert res["status"] == 200, res
        assert not res["body"].get("edits_would_be_discarded"), res["body"]

    @pytest.mark.parametrize("how", _HOWS)
    def test_c8_the_flag_with_nothing_to_discard_is_harmless(self, rig, persists, monkeypatch, how):
        _freeze(rig)
        first = rig.generate()
        _control(first["status"] == 200, first)
        _follow(rig, first["child"])
        res = _post(rig, how, generate_cover_letter=True, confirm_discard_edits=True)
        assert res["status"] == 200, res
        assert not res["body"].get("edits_would_be_discarded"), res["body"]


# -------------------------------------------------------------------
# Defect invariants (fail on main: the request is served, the edit is lost)
# -------------------------------------------------------------------


@_DEFECT
@pytest.mark.parametrize("how", _HOWS)
def test_a1_a_discarded_resume_edit_is_refused_until_confirmed(rig, persists, monkeypatch, how):
    """Case 1: the re-approved composition would drop the typed résumé edit."""
    _case1_setup(rig, monkeypatch, letter_edit=False)
    before, spent = _snapshot(rig, persists), _llm_total(rig)
    res = _post(rig, how)
    unchanged = _snapshot(rig, persists) == before
    rec = _refusal(
        f"A1-{how}",
        res,
        llm_spent=_llm_total(rig) - spent,
        unchanged=unchanged,
        discards=["resume"],
    )
    _assert_refused(rec, res, ["resume"])


@_DEFECT
@pytest.mark.parametrize("how", _HOWS)
def test_a2_both_edits_are_named_when_both_would_be_lost(rig, persists, monkeypatch, how):
    """Case 1 plus a letter request: the résumé edit is discarded AND the letter consumed."""
    _case1_setup(rig, monkeypatch, letter_edit=True)
    before, spent = _snapshot(rig, persists), _llm_total(rig)
    res = _post(rig, how, generate_cover_letter=True)
    unchanged = _snapshot(rig, persists) == before
    rec = _refusal(
        f"A2-{how}",
        res,
        llm_spent=_llm_total(rig) - spent,
        unchanged=unchanged,
        discards=["resume", "cover_letter"],
    )
    _assert_refused(rec, res, ["resume", "cover_letter"])


@_DEFECT
@pytest.mark.parametrize("how", _HOWS)
def test_a3_a_with_letter_generate_is_refused_before_the_letter_llm_call_legacy(
    rig, persists, monkeypatch, how
):
    """Case 2, legacy path: the new letter would consume the typed letter edit."""
    _letter_then_typed_edit(
        rig,
        monkeypatch,
        second={"resume_content": "# SECOND", "cover_letter_content": REWRITTEN},
    )
    before, spent = _snapshot(rig, persists), _llm_total(rig)
    res = _post(rig, how, generate_cover_letter=True)
    unchanged = _snapshot(rig, persists) == before
    rec = _refusal(
        f"A3-{how}",
        res,
        llm_spent=_llm_total(rig) - spent,
        unchanged=unchanged,
        discards=["cover_letter"],
    )
    _assert_refused(rec, res, ["cover_letter"])


@_DEFECT
@pytest.mark.parametrize("how", _HOWS)
def test_a4_a_with_letter_generate_is_refused_before_the_letter_llm_call_frozen(
    rig, persists, monkeypatch, how
):
    """Case 2, frozen path: the letter LLM call is INSIDE the assemble, so it must come after."""
    _case2_frozen_setup(rig, monkeypatch)
    before, spent = _snapshot(rig, persists), _llm_total(rig)
    res = _post(rig, how, generate_cover_letter=True)
    unchanged = _snapshot(rig, persists) == before
    rec = _refusal(
        f"A4-{how}",
        res,
        llm_spent=_llm_total(rig) - spent,
        unchanged=unchanged,
        discards=["cover_letter"],
    )
    _assert_refused(rec, res, ["cover_letter"])


@_DEFECT
def test_a5_the_detached_letter_route_is_refused_over_a_typed_edit(rig, persists, monkeypatch):
    """Case 3: `/api/generate-cover-letter` would pop the typed letter edit."""
    _letter_then_typed_edit(rig, monkeypatch, second={"resume_content": "# SECOND"})
    detached = _count_detached(monkeypatch)
    before, spent = _snapshot(rig, persists), _llm_total(rig, detached)
    res = _post_letter(rig)
    unchanged = _snapshot(rig, persists) == before
    rec = _refusal(
        "A5",
        res,
        llm_spent=_llm_total(rig, detached) - spent,
        unchanged=unchanged,
        discards=["cover_letter"],
    )
    _assert_refused(rec, res, ["cover_letter"])
