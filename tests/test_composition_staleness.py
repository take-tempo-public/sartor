"""Regression tests for the frozen-composition staleness fix (items 106, 66, 132).

`fix/frozen-composition-staleness`. The behavior-level reproduction lives in
tests/test_frozen_composition_staleness.py (its rig is reused here); this module
pins the fix's own mechanisms:

- `hardening.composition_inputs_digest` / `composition_is_stale` (unit);
- the digest's inputs equal what `build_json_resume_from_corpus` reads, derived by
  recording its reads rather than by a hand list (C-11: a staleness input the
  builder gains later fails this test instead of silently never staling);
- `POST /composition/touch`, the generate routes' 409, and the typed-edits
  carry/discard (owner decision 4);
- a static check that every corpus call in Compose's section of static/app.js goes
  through `_composeCorpusFetch` / `_composeCorpusJson` (the touch-first wrappers),
  so a new Compose corpus edit can't bypass the stale mark.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from hardening import (
    COMPOSITION_INPUT_KEYS,
    composition_inputs_digest,
    composition_is_stale,
)
from tests.test_frozen_composition_staleness import (
    B1,
    EDITED,
    TYPED,
    USER,
    _freeze,
    _r2_pin,
)
from tests.test_frozen_composition_staleness import rig as _rig_fixture

# The instrument's rig (real routes, analyzer stubbed), registered here under its name.
rig = _rig_fixture

REPO = Path(__file__).resolve().parents[1]


def _frozen_ctx(**inputs: Any) -> dict[str, Any]:
    """A minimal frozen context whose snapshot was stamped from `inputs`."""
    ctx: dict[str, Any] = {
        "career_corpus": [{"id": 1}],
        **inputs,
    }
    ctx["approved_composition"] = {
        "work": [{"name": "Acme"}],
        "meta": {"sartor": {"frozen": True, "inputs_digest": composition_inputs_digest(ctx)}},
    }
    return ctx


# -------------------------------------------------------------------
# hardening: digest + predicate
# -------------------------------------------------------------------


class TestDigestAndPredicate:
    def test_digest_ignores_key_order_and_int_vs_str_keys(self):
        a = {"llm_recommendations": {3: {"bullet_ids": [1, 2]}}, "composition_overrides": {}}
        b = {"composition_overrides": {}, "llm_recommendations": {"3": {"bullet_ids": [1, 2]}}}
        assert composition_inputs_digest(a) == composition_inputs_digest(b)

    def test_digest_ignores_keys_outside_the_inputs(self):
        a = {"composition_overrides": {"pinned": [1]}}
        b = {
            "composition_overrides": {"pinned": [1]},
            "clarifications": {"q1": "x"},
            "iteration": 4,
        }
        assert composition_inputs_digest(a) == composition_inputs_digest(b)

    def test_fresh_after_freeze_stale_after_an_input_change_fresh_after_undo(self):
        ctx = _frozen_ctx(composition_overrides={"pinned": []})
        assert composition_is_stale(ctx) is False
        ctx["composition_overrides"] = {"pinned": [7]}
        assert composition_is_stale(ctx) is True
        ctx["composition_overrides"] = {"pinned": []}
        assert composition_is_stale(ctx) is False

    def test_a_corpus_edit_counter_bump_stales(self):
        ctx = _frozen_ctx(composition_overrides={})
        ctx["compose_corpus_edits"] = 1
        assert composition_is_stale(ctx) is True

    def test_never_stale_without_a_frozen_document(self):
        assert composition_is_stale({"compose_corpus_edits": 5}) is False
        assert composition_is_stale({"approved_composition": {"work": [1]}}) is False  # no corpus

    def test_legacy_snapshot_without_digest_fails_open_until_a_corpus_edit(self):
        ctx = _frozen_ctx(composition_overrides={})
        del ctx["approved_composition"]["meta"]["sartor"]["inputs_digest"]
        ctx["composition_overrides"] = {"pinned": [9]}  # undetectable without a digest
        assert composition_is_stale(ctx) is False
        ctx["compose_corpus_edits"] = 1
        assert composition_is_stale(ctx) is True


# -------------------------------------------------------------------
# Derived set: the digest's inputs == what the builder reads (both directions)
# -------------------------------------------------------------------


def _recording(data: dict[str, Any], seen: set[str]) -> dict[str, Any]:
    """A dict that records every top-level key read from it into `seen`.

    The subclass closes over `seen` instead of storing it on the instance, so it adds
    no state that equality would have to account for.
    """

    class _Recording(dict):
        def get(self, key, default=None):
            seen.add(key)
            return super().get(key, default)

        def __getitem__(self, key):
            seen.add(key)
            return super().__getitem__(key)

        def __contains__(self, key):
            seen.add(key)
            return super().__contains__(key)

    return _Recording(data)


class TestDerivedInputSet:
    def test_builder_reads_exactly_the_digest_inputs(self, rig):
        """Every top-level key the builder reads is a staleness input (a missed one
        would let an edit through unnoticed), and every input but the corpus-edit
        counter is read (a dead one would stale on writes that change nothing)."""
        from corpus_to_json_resume import build_json_resume_from_corpus
        from db.session import get_session

        _freeze(rig)
        rig.save(pinned=[rig.ids["b2"]], summary_text="ZEBRA summary", summary_text_edited=True)
        seen: set[str] = set()
        s = get_session()
        try:
            for ctx in ({}, rig.ctx()):
                build_json_resume_from_corpus(
                    s,
                    rig.ids["candidate"],
                    application_id=rig.aid,
                    context_data=_recording(ctx, seen),
                )
        finally:
            s.close()
        assert seen == set(COMPOSITION_INPUT_KEYS) - {"compose_corpus_edits"}, sorted(seen)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


class TestTouchRoute:
    def _touch(self, rig, aid=None, path=None):
        return rig.client.post(
            f"/api/applications/{aid or rig.aid}/composition/touch",
            json={"context_path": rig.cp if path is None else path},
        )

    def test_bumps_the_counter_and_reports_stale_on_a_frozen_composition(self, rig):
        _freeze(rig)
        r = self._touch(rig)
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json()["stale"] is True
        assert rig.ctx()["compose_corpus_edits"] == 1
        assert self._touch(rig).get_json()["stale"] is True
        assert rig.ctx()["compose_corpus_edits"] == 2

    def test_writes_nothing_before_the_first_freeze(self, rig):
        before = Path(rig.cp).read_bytes()
        r = self._touch(rig)
        assert r.status_code == 200 and r.get_json()["stale"] is False
        assert Path(rig.cp).read_bytes() == before

    def test_save_and_continue_clears_it(self, rig):
        _freeze(rig)
        self._touch(rig)
        assert _freeze(rig)["stale"] is False

    def test_refuses_a_context_outside_output_and_a_foreign_application(self, rig):
        assert self._touch(rig, path="../../etc/passwd").status_code == 400
        assert self._touch(rig, path="").status_code == 400
        assert self._touch(rig, aid=rig.aid + 999).status_code == 404


class TestCompositionResponses:
    def test_an_identical_autosave_after_the_freeze_is_not_stale(self, rig):
        _freeze(rig)
        assert rig.save()["stale"] is False

    def test_an_edit_autosave_is_stale_and_reverting_it_is_not(self, rig):
        _freeze(rig)
        assert rig.save(pinned=[rig.ids["b2"]])["stale"] is True
        assert rig.save(pinned=[])["stale"] is False

    def test_get_composition_and_resume_state_report_the_same_answer(self, rig):
        _freeze(rig)
        _r2_pin(rig)
        view = json.loads(rig.compose_view())
        assert view["has_frozen_composition"] is True and view["composition_stale"] is True
        rs = rig.client.get(f"/api/applications/{rig.aid}").get_json()["resume_state"]
        assert rs["has_frozen_composition"] is True and rs["composition_stale"] is True


class TestGenerateRefusesStale:
    @pytest.mark.parametrize("route", ["/api/generate", "/api/generate/stream"])
    def test_409_with_no_llm_call(self, rig, route):
        _freeze(rig)
        _r2_pin(rig)
        before = dict(rig.calls)
        r = rig.client.post(
            route, json={"username": USER, "context_path": rig.cp, "output_format": ".md"}
        )
        assert r.status_code == 409, r.get_data(as_text=True)
        body = r.get_json()
        assert body["composition_stale"] is True
        assert "Save and continue" in body["error"]
        assert rig.calls == before  # no generate, no streaming generate, no cover letter

    def test_an_iteration_child_inherits_a_fresh_approval(self, rig):
        _freeze(rig)
        first = rig.generate()
        assert first["status"] == 200, first
        assert composition_is_stale(rig.ctx(first["child"])) is False
        again = rig.generate(first["child"])
        assert again["status"] == 200, again


class TestTypedEdits:
    def _save_typed(self, rig, child: str, base_md: str) -> None:
        r = rig.client.post(
            "/api/save-edits",
            json={
                "context_path": child,
                "username": USER,
                "edited_resume": base_md.replace(B1, TYPED),
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)

    def test_kept_over_an_unchanged_regenerate(self, rig):
        _freeze(rig)
        first = rig.generate()
        self._save_typed(rig, first["child"], first["resume_md"])
        r = rig.client.post(
            "/api/generate",
            json={"username": USER, "context_path": first["child"], "output_format": ".md"},
        )
        body = r.get_json()
        assert r.status_code == 200, body
        assert body["edits_discarded"] is False
        assert TYPED in body["edited_resume_text"]
        assert TYPED in rig.ctx(body["context_path"])["edited_resume_text"]

    def test_discarded_and_cleared_after_a_re_approval(self, rig):
        _freeze(rig)
        first = rig.generate()
        child = first["child"]
        self._save_typed(rig, child, first["resume_md"])
        # Re-approve a different composition on the child (the client's context
        # after a generate), then regenerate.
        rig.cp = child
        rig.state["context_path"] = child
        rig.compose_corpus_edit("PUT", f"/api/bullets/{rig.ids['b1']}", {"text": EDITED})
        _freeze(rig)
        # The user's Continue (item 170): without the flag this is a 409 that names the
        # résumé edit (tests/test_confirm_overwrite_edits.py A1).
        r = rig.client.post(
            "/api/generate",
            json={
                "username": USER,
                "context_path": child,
                "output_format": ".md",
                "confirm_discard_edits": True,
            },
        )
        body = r.get_json()
        assert r.status_code == 200, body
        assert body["edits_discarded"] is True and body["edited_resume_text"] == ""
        assert "edited_resume_text" not in rig.ctx(body["context_path"])
        # The run row no longer carries the discarded edit, so resuming the
        # application can't reload it; it shows THIS generate (the re-approved
        # composition), now that a second generate of the same run persists
        # (item 160, fix/regenerate-persistence).
        from db.models import ApplicationRun
        from db.session import get_session

        s = get_session()
        try:
            run = s.query(ApplicationRun).filter_by(id=rig.ctx()["application_run_id"]).one()
            assert run.edited_resume_text is None
        finally:
            s.close()
        rs = rig.client.get(f"/api/applications/{rig.aid}").get_json()["resume_state"]
        assert TYPED not in rs["resume_md"]
        assert rs["resume_md"] == body["resume_preview"]
        assert EDITED in rs["resume_md"]


# -------------------------------------------------------------------
# Static: Compose's corpus writes all go through the touch-first wrappers
# -------------------------------------------------------------------

_CALL = re.compile(r"\b(fetch|_postJson|_putJson|_deleteJson)\(\s*[`'\"](/api/[^`'\"$]*)")


def _compose_section() -> str:
    src = (REPO / "static" / "app.js").read_text(encoding="utf-8")
    start = src.index("// Workstream E — Step 3 Compose (fit-ranked bullets/titles)")
    end = src.index("// Workstream E — shared tag-chip component (Compose + Career Corpus)")
    return src[start:end]


class TestComposeCorpusCallsAreTouched:
    def test_no_raw_corpus_call_in_the_compose_section(self):
        """Fails closed on a new Compose corpus write that skips the stale mark.

        Every raw fetch/_postJson/_putJson/_deleteJson in Compose's section may only
        target /api/applications/... (context writes the digest already sees); a
        corpus route (/api/bullets, /api/skills, /api/experiences, ...) must go
        through `_composeCorpusFetch` / `_composeCorpusJson`.
        """
        section = _compose_section()
        raw = [
            (fn, url)
            for fn, url in _CALL.findall(section)
            if not url.startswith("/api/applications/")
        ]
        assert raw == [], raw

    def test_the_six_known_corpus_writes_use_the_wrappers(self):
        """Pin the count so a removed or added wrapper call is a visible decision."""
        section = _compose_section()
        calls = re.findall(
            r"\b_composeCorpus(?:Fetch|Json)\(\s*(?:'[A-Z]+',\s*)?`(/api/[^`]*)`", section
        )
        assert sorted(calls) == sorted(
            [
                "/api/skills/${skillId}",
                "/api/skills/${skillId}",
                "/api/experiences/${expId}/summaries",
                "/api/experiences/${expId}/titles",
                "/api/bullets/${b.id}/accept",
                "/api/bullets/${b.id}",
            ]
        ), calls
