"""Instrument — a résumé-only regenerate blanks the cover letter in the context (item 162).

`fix/regenerate-keeps-cover-letter`. Landed as commit 1, the reproduction (charter C-7: it
comes before any fix). Evidence record:
`docs/dev/diagnosis/regenerate-keeps-cover-letter.md`.

Item 162 was filed from `fix/regenerate-persistence`'s O4: after a detached cover letter
(`/api/generate-cover-letter`), the next résumé-only generate writes
`last_generated_cover_letter = ""` into the child context. Item 160 fixed the DB column
only. The user-facing effect was inferred, never observed. This file observes it.

Every arm drives the REAL routes (the rig from tests/test_frozen_composition_staleness.py: a
fresh migrated DB, the analyzer stubbed) and prints one JSON observation record per arm
(`-rA` shows it; it is also in each assertion message). The arms are wider than the filed
hypothesis on purpose (AGENT_FAILURE_PATTERNS §5f): both generate routes, the context file
AND each surface that reads it (the styled preview, the iteration interview, the next
with-letter generate), and a typed letter edit, which the same helper also discards.

What each B-arm asserts is the invariant the route's own docstring promises
(`blueprints/generation.py` `run_generate_cover_letter`: the letter is stored "so
subsequent /api/generate calls (résumé refinements) preserve the cover letter"). B5's
invariant (a saved typed edit survives a résumé regenerate) extends that promise to
`edited_cover_letter_text`; it is a proposal for the owner to confirm, not an observed
defect, and the dossier says so.

The defect invariants are `xfail(strict=True, raises=AssertionError)` on the base tip
(quoted in the diagnosis, with `--runxfail`); the fix commit deletes only those markers.
The controls hold throughout.

A control inside a B-arm (the drive worked, the letter rendered before the regenerate)
raises `ControlFailed`, never a bare `assert`: the marker accepts only `AssertionError`, so
a broken setup FAILS the arm instead of reading as the expected defect. Only the defect
invariant itself is a plain `assert`.
"""

from __future__ import annotations

from typing import Any

import pytest

import analyzer
import blueprints.analysis as banalysis
import blueprints.generation as bgen
from tests.test_frozen_composition_staleness import USER, _parse_sse
from tests.test_frozen_composition_staleness import rig as _rig_fixture
from tests.test_regenerate_persistence import _follow, _observe
from tests.test_regenerate_persistence import persists as _persists_fixture

# The staleness instrument's rig and the item-160 persist recorder, registered here.
rig = _rig_fixture
persists = _persists_fixture

LETTER = "ZEBRA-LETTER first detached cover letter for the billing role"
REWRITTEN = "ZEBRA-REWRITTEN a second, regenerated cover letter"
TYPED = "ZEBRA-TYPED-LETTER a hand edit the candidate saved over the letter"
PLACEHOLDER = "No cover letter yet"

DEFECT = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="item 162: a résumé-only regenerate blanks the cover letter",
)


class ControlFailed(Exception):
    """A drive or control step did not hold, so the arm proves nothing (not the defect)."""


def _control(ok: bool, what: object) -> None:
    if not ok:
        raise ControlFailed(str(what))


# -------------------------------------------------------------------
# Drive helpers
# -------------------------------------------------------------------


def _generate_stub(monkeypatch, rig, *results: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace the rig's LLM `generate` with one returning `results` in order.

    Returns a log, one entry per call: the `with_cover_letter` flag and the cover-letter
    draft the real `generate()` would build its prompt from
    (`analyzer._current_cover_letter_draft` of the context it was handed).
    """
    queue = list(results)
    seen: list[dict[str, Any]] = []

    def _gen(client, context_set, analysis, **kw: Any) -> dict[str, Any]:
        rig.calls["generate"] += 1
        draft, label = analyzer._current_cover_letter_draft(context_set)
        seen.append(
            {
                "with_cover_letter": bool(kw.get("with_cover_letter")),
                "draft": draft,
                "draft_source": label,
            }
        )
        base = {
            "resume_content": "# LLM WROTE THIS",
            "cover_letter_content": "",
            "changes_made": [],
            "proofread_notes": [],
        }
        return {**base, **queue.pop(0)}

    monkeypatch.setattr(bgen, "generate", _gen)
    return seen


def _post_generate(rig, how: str = "json", **extra: Any) -> dict[str, Any]:
    """POST the generate route and return the response body (the SSE `done` payload)."""
    url = "/api/generate" if how == "json" else "/api/generate/stream"
    r = rig.client.post(
        url,
        json={"username": USER, "context_path": rig.cp, "output_format": ".md", **extra},
    )
    if how == "json":
        _control(r.status_code == 200, r.get_data(as_text=True))
        return dict(r.get_json())
    events = _parse_sse(r.get_data(as_text=True))
    done = next((p for ev, p in events if ev == "done"), None)
    _control(done is not None, [ev for ev, _ in events])
    return dict(done or {})


def _detach_letter(rig, monkeypatch, text: str = LETTER) -> None:
    """Run /api/generate-cover-letter against the rig's current context, as Step 6 does.

    The route imports `generate_cover_letter_against_resume` inside the function, so the
    stub goes on `analyzer`, not on `blueprints.generation` (item 160, recurrence 1).
    """
    monkeypatch.setattr(
        analyzer,
        "generate_cover_letter_against_resume",
        lambda *a, **k: {"cover_letter_content": text},
    )
    r = rig.client.post(
        "/api/generate-cover-letter", json={"username": USER, "context_path": rig.cp}
    )
    _control(r.status_code == 200, r.get_data(as_text=True))
    _control(rig.ctx().get("last_generated_cover_letter") == text, "the letter was not stored")


def _letter_preview(rig, context_path: str) -> str:
    r = rig.client.get(
        f"/api/applications/{rig.aid}/cover-letter-preview",
        query_string={"context_path": context_path},
    )
    _control(r.status_code == 200, r.get_data(as_text=True))
    return r.get_data(as_text=True)


def _ctx_letters(rig, path: str) -> dict[str, Any]:
    ctx = rig.ctx(path)
    return {
        "child_last_generated_cover_letter": ctx.get("last_generated_cover_letter"),
        "child_edited_cover_letter_text": ctx.get("edited_cover_letter_text"),
        "child_iteration": ctx.get("iteration"),
    }


# -------------------------------------------------------------------
# Controls (hold on the base tip, and after the fix)
# -------------------------------------------------------------------


class TestControls:
    def test_c1_a_first_generate_with_no_letter_has_no_letter(self, rig, persists, monkeypatch):
        _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"})
        body = _post_generate(rig)
        rec = _observe(
            rig,
            persists,
            "C1",
            **_ctx_letters(rig, body["context_path"]),
            cover_letter_preview=body["cover_letter_preview"],
        )
        assert rec["child_last_generated_cover_letter"] == "", rec
        assert body["cover_letter_preview"] == "", rec

    def test_c2_a_with_letter_regenerate_replaces_the_letter(self, rig, persists, monkeypatch):
        _generate_stub(
            monkeypatch,
            rig,
            {"resume_content": "# FIRST"},
            {"resume_content": "# SECOND", "cover_letter_content": REWRITTEN},
        )
        first = _post_generate(rig)
        _follow(rig, first["context_path"])
        _detach_letter(rig, monkeypatch)
        second = _post_generate(rig, generate_cover_letter=True)
        rec = _observe(
            rig,
            persists,
            "C2",
            **_ctx_letters(rig, second["context_path"]),
            cover_letter_preview=second["cover_letter_preview"],
        )
        assert rec["child_last_generated_cover_letter"] == REWRITTEN, rec
        assert second["cover_letter_preview"] == REWRITTEN, rec
        assert rec["run_cover_letter_md"] == REWRITTEN, rec


# -------------------------------------------------------------------
# Defect invariants (diagnosis B1-B6)
# -------------------------------------------------------------------


@DEFECT
@pytest.mark.parametrize("how", ["json", "stream"])
def test_b1_b2_a_resume_only_regenerate_keeps_the_letter_in_the_context(
    rig, persists, monkeypatch, how
):
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"}, {"resume_content": "# SECOND"})
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    second = _post_generate(rig, how)
    rec = _observe(
        rig,
        persists,
        f"B1B2-{how}",
        **_ctx_letters(rig, second["context_path"]),
        cover_letter_preview=second["cover_letter_preview"],
        cover_letter_path=second["cover_letter_path"],
    )
    # DB control (item 160's fix): the run row keeps the letter whichever way the context goes.
    _control(rec["run_cover_letter_md"] == LETTER, rec)
    assert rec["child_last_generated_cover_letter"] == LETTER, rec
    assert second["cover_letter_preview"] == LETTER, rec


@DEFECT
def test_b3_the_styled_cover_letter_preview_survives_a_resume_regenerate(
    rig, persists, monkeypatch
):
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"}, {"resume_content": "# SECOND"})
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    before = _letter_preview(rig, rig.cp)
    second = _post_generate(rig)
    after = _letter_preview(rig, second["context_path"])
    rec = _observe(
        rig,
        persists,
        "B3",
        before_has_letter=LETTER in before,
        after_has_letter=LETTER in after,
        after_is_placeholder=PLACEHOLDER in after,
    )
    _control(rec["before_has_letter"] is True, rec)  # it rendered before the regenerate
    assert LETTER in after, rec


@DEFECT
def test_b4_the_iteration_interview_still_sees_the_letter(rig, persists, monkeypatch):
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"}, {"resume_content": "# SECOND"})
    captured: dict[str, Any] = {}

    def _fake_clarify_iteration(client, context_set, analysis, **kw: Any) -> dict[str, Any]:
        captured["current_cover_letter_text"] = kw.get("current_cover_letter_text")
        return {"questions": [], "reasoning": ""}

    monkeypatch.setattr(banalysis, "clarify_iteration", _fake_clarify_iteration)

    def _interview_letter(path: str) -> Any:
        captured.clear()
        r = rig.client.post("/api/iterate-clarify", json={"username": USER, "context_path": path})
        _control(r.status_code == 200, r.get_data(as_text=True))
        return captured.get("current_cover_letter_text")

    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    # Control: the interview on the context that holds the letter is handed it.
    _control(_interview_letter(rig.cp) == LETTER, dict(captured))
    second = _post_generate(rig)
    after = _interview_letter(second["context_path"])
    rec = _observe(rig, persists, "B4", current_cover_letter_text=after)
    assert rec["current_cover_letter_text"] == LETTER, rec


@DEFECT
def test_b5_a_saved_typed_letter_edit_survives_a_resume_regenerate(rig, persists, monkeypatch):
    _generate_stub(monkeypatch, rig, {"resume_content": "# FIRST"}, {"resume_content": "# SECOND"})
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    saved = rig.client.post(
        "/api/save-edits",
        json={"username": USER, "context_path": rig.cp, "edited_cover_letter": TYPED},
    )
    _control(saved.status_code == 200, saved.get_data(as_text=True))
    before = _letter_preview(rig, rig.cp)
    second = _post_generate(rig)
    after = _letter_preview(rig, second["context_path"])
    rec = _observe(
        rig,
        persists,
        "B5",
        **_ctx_letters(rig, second["context_path"]),
        before_shows_typed=TYPED in before,
        after_shows_typed=TYPED in after,
        after_is_placeholder=PLACEHOLDER in after,
    )
    _control(rec["before_shows_typed"] is True, rec)  # the edit rendered before
    assert TYPED in after, rec


@DEFECT
def test_b6_the_next_with_letter_generate_is_handed_the_prior_letter(rig, persists, monkeypatch):
    seen = _generate_stub(
        monkeypatch,
        rig,
        {"resume_content": "# FIRST"},
        {"resume_content": "# SECOND"},
        {"resume_content": "# THIRD", "cover_letter_content": REWRITTEN},
    )
    first = _post_generate(rig)
    _follow(rig, first["context_path"])
    _detach_letter(rig, monkeypatch)
    second = _post_generate(rig)
    _follow(rig, second["context_path"])
    third = _post_generate(rig, generate_cover_letter=True)
    rec = _observe(
        rig, persists, "B6", generate_calls=seen, third_letter=third["cover_letter_preview"]
    )
    # Controls: the with-letter generate ran, and the generate before the résumé regenerate
    # was handed the letter (so a blank draft is the regenerate's doing).
    _control(rec["third_letter"] == REWRITTEN, rec)
    _control(seen[-1]["with_cover_letter"] is True, rec)
    _control(seen[1]["draft"] == LETTER, rec)
    assert seen[-1]["draft"] == LETTER, rec
