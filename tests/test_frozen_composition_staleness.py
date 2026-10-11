"""Instrument — a frozen composition goes stale silently (items 106, 66, 132).

`fix/frozen-composition-staleness`. Landed as commit 1, the reproduction (charter
C-7: it comes before any fix); kept as the regression suite once the fix landed.
Evidence record: `docs/dev/diagnosis/frozen-composition-staleness.md`.

Every test drives the REAL routes against a fresh DB with the analyzer stubbed (no
LLM): seed a corpus -> `POST /api/analyze` -> Compose "Save and continue"
(`POST /composition` with `freeze: true`) -> ONE post-freeze edit (the arm) -> every
surface that serves or reports the composition. Each test prints its observation
record as one JSON line (`-rA` shows it) and puts the whole record in its assertion
message.

The arms are wider than items 106/132 on purpose (AGENT_FAILURE_PATTERNS §5f): the
never-frozen and re-frozen controls, a Career-Corpus-panel edit that must NOT reach
an approved application, and every other kind of Compose edit, not just bullet text.

Two kinds of test:
- **Controls and design-kept facts** held before the fix and still hold after it.
- **Defect invariants** (D1, D3, D5, D6) failed on the base tip (`--runxfail`, as
  quoted in the diagnosis) and name no API of the fix's, so the fix commit only
  deleted their `xfail(strict=True)` markers and the one Compose-signal line in
  `_Rig.compose_corpus_edit`.

"Compose's state" below is the document a freeze would capture right now:
`build_json_resume_from_corpus` over the current context, which is what
"Save and continue" would approve.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import blueprints.generation as bgen
from json_resume import json_resume_to_markdown

USER = "alice"

B1 = "ZEBRA-B1 led the billing rewrite that cut churn"
B2 = "ZEBRA-B2 ran the vendor consolidation review"
B3 = "ZEBRA-B3 proposed onboarding funnel rebuild"
EDITED = "ZEBRA-EDITED led the billing rewrite that cut churn 18 percent"
SUMMARY0 = "ZEBRA-SUM0 platform PM who ships billing systems."
SUMMARY1 = "ZEBRA-SUM1 retyped positioning summary for this job."
SKILL_ACTIVE = "Zebralang"
SKILL_PENDING = "Zebrascript"
TITLE_NEW = "ZEBRA-TITLE Principal Product Manager"
GAP_TEXT = "ZEBRA-GAP drafted gap-fill bullet about pricing experiments"
TYPED = "ZEBRA-TYPED hand edit of the generated resume"

# The request fields `save_application_composition` reads (blueprints/applications.py,
# the `data.get(...)` calls at the top of the route). Its response echoes them back,
# so they are not server-derived state.
_COMPOSITION_REQUEST_FIELDS = frozenset(
    {
        "context_path",
        "pinned",
        "excluded",
        "added",
        "bullet_order",
        "pinned_summary_id",
        "pinned_title_ids",
        "use_experience_summaries",
        "chosen_experience_summary_ids",
        "pinned_skill_ids",
        "excluded_skill_ids",
        "skill_order",
        "summary_text",
        "summary_text_edited",
        "accepted_generated_bullet_ids",
        "retired_gap_fill_keys",
        "freeze",
    }
)

_ANALYSIS = {
    "essential_skills": ["billing"],
    "preferred_skills": [],
    "comparison": {"strengths": [], "gaps": [], "title_alignment": ""},
    "keyword_placement": [],
    "industry_keywords": [],
}


# -------------------------------------------------------------------
# The rig: app + stubs + seeded corpus + one analyzed application
# -------------------------------------------------------------------


@pytest.fixture
def rig(tmp_path, monkeypatch, _migrated_template_db):
    """Real app on a fresh DB; analyzer stubbed; one analyzed application.

    Combines `preview_app` (tests/test_live_preview_route.py: persona files so the
    preview route renders) with `gen_app`'s generate stubs and call counter
    (tests/test_deterministic_generate.py) and a capture stub on the Step-6
    refinement drafter.
    """
    import analyzer
    import blueprints.analysis as banalysis
    import blueprints.applications as bapps
    from tests.conftest import _fresh_migrated_db

    _fresh_migrated_db(tmp_path, monkeypatch, _migrated_template_db, filename="stale.sqlite")

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp_path)
    app = create_app(cfg)
    app.config["TESTING"] = True

    repo_root = Path(__file__).resolve().parents[1]
    cfg.bundled_personas_dir.mkdir(parents=True, exist_ok=True)
    for name in ("classic.html", "classic.css"):
        (cfg.bundled_personas_dir / name).write_text(
            (repo_root / "personas" / "bundled" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (cfg.personas_dir / "cover_letter.html").write_text(
        (repo_root / "personas" / "cover_letter.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    from docx import Document

    for filename in ("classic.docx", "modern.docx"):
        doc = Document()
        doc.add_paragraph(f"stub for {filename}")
        doc.save(str(cfg.bundled_personas_dir / filename))
    (cfg.configs_dir / f"{USER}.config").write_text("{}", encoding="utf-8")

    calls = {"generate": 0, "generate_streaming": 0, "cover_letter_llm": 0, "analyze": 0}
    captured: dict[str, Any] = {}

    def _fake_analyze(*a, **k):
        calls["analyze"] += 1
        return json.loads(json.dumps(_ANALYSIS))

    def _tracked_generate(*a, **k):
        calls["generate"] += 1
        return {
            "resume_content": "# LLM WROTE THIS",
            "cover_letter_content": "",
            "changes_made": [],
            "proofread_notes": [],
        }

    def _tracked_stream(*a, **k):
        calls["generate_streaming"] += 1
        yield (
            "done",
            {
                "resume_content": "# LLM WROTE THIS (stream)",
                "cover_letter_content": "",
                "changes_made": [],
                "proofread_notes": [],
            },
        )

    def _fake_cl(client, ctx, analysis, resume_content, username="", run_id=""):
        calls["cover_letter_llm"] += 1
        return {"cover_letter_content": "LLM COVER LETTER"}

    def _stub_letter_writer(content, user, base_dir):
        out = Path(base_dir) / user / "cover_stub.docx"
        out.write_text(content, encoding="utf-8")
        return str(out)

    def _capture_refinement(client, context_set, *, username="", run_id=""):
        captured["current_resume"] = analyzer._current_composition_block(
            context_set.get("approved_composition")
        )
        return {"target_kind": "none"}

    monkeypatch.setattr(banalysis, "analyze", _fake_analyze)
    monkeypatch.setattr(banalysis, "_get_client", lambda: object())
    monkeypatch.setattr(bapps, "_get_client", lambda: object())
    monkeypatch.setattr(analyzer, "draft_surgical_refinement", _capture_refinement)
    monkeypatch.setattr(bgen, "generate", _tracked_generate)
    monkeypatch.setattr(bgen, "generate_streaming", _tracked_stream)
    monkeypatch.setattr(bgen, "generate_cover_letter_against_resume", _fake_cl)
    monkeypatch.setattr(bgen, "generate_cover_letter", _stub_letter_writer)
    monkeypatch.setattr(bgen, "_get_client", lambda: object())

    r = _Rig(app.test_client(), cfg.output_dir, calls, captured)
    r.seed()
    r.analyze()
    return r


class _Rig:
    """Drives one application through the real routes and observes every surface."""

    def __init__(self, client, output_dir: Path, calls: dict, captured: dict) -> None:
        self.client = client
        self.output_dir = output_dir
        self.calls = calls
        self.captured = captured
        self.ids: dict[str, int] = {}
        self.cp = ""
        self.aid = 0
        # The full Compose state; POST /composition rebuilds composition_overrides
        # wholesale, so every save resends all of it (as _collectCompositionState does).
        self.state: dict[str, Any] = {}

    # ---- setup ----

    def seed(self) -> None:
        from db.models import Bullet, Candidate, Experience, ExperienceTitle, Skill, SummaryItem
        from db.session import get_session

        s = get_session()
        try:
            c = Candidate(
                username=USER, name="Alice Rivera", email="alice@example.com", profile_text=""
            )
            s.add(c)
            s.flush()
            s.add(SummaryItem(candidate_id=c.id, text=SUMMARY0, display_order=0, is_active=1))
            e = Experience(
                candidate_id=c.id,
                company="Acme",
                start_date="2021-01",
                end_date="2024-06",
                display_order=0,
            )
            s.add(e)
            s.flush()
            s.add(
                ExperienceTitle(
                    experience_id=e.id,
                    title="Senior PM",
                    is_official=1,
                    is_pending_review=0,
                    source="official",
                )
            )
            rows = {
                "b1": Bullet(
                    experience_id=e.id,
                    text=B1,
                    display_order=0,
                    is_active=1,
                    is_pending_review=0,
                    source="manual",
                    has_outcome=1,
                ),
                "b2": Bullet(
                    experience_id=e.id,
                    text=B2,
                    display_order=1,
                    is_active=1,
                    is_pending_review=0,
                    source="manual",
                    has_outcome=0,
                ),
                "b3": Bullet(
                    experience_id=e.id,
                    text=B3,
                    display_order=2,
                    is_active=1,
                    is_pending_review=1,
                    source="extracted",
                    has_outcome=0,
                ),
            }
            for b in rows.values():
                s.add(b)
            sk_active = Skill(
                candidate_id=c.id, name=SKILL_ACTIVE, is_active=1, is_pending_review=0
            )
            sk_pending = Skill(
                candidate_id=c.id, name=SKILL_PENDING, is_active=1, is_pending_review=1
            )
            s.add_all([sk_active, sk_pending])
            s.commit()
            self.ids = {
                "candidate": c.id,
                "exp": e.id,
                **{k: v.id for k, v in rows.items()},
                "skill_active": sk_active.id,
                "skill_pending": sk_pending.id,
            }
        finally:
            s.close()

    def analyze(self) -> None:
        r = self.client.post(
            "/api/analyze",
            json={"username": USER, "job_description": "Senior PM, billing platform. " * 5},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        body = r.get_json()
        self.cp = body["context_path"]
        self.aid = body["application_id"]
        # What the analyze-time Compose calls would have left on the context: a
        # bullet recommendation (B1 only), one clarify question, one gap-fill proposal.
        ctx = self.ctx()
        ctx["llm_recommendations"] = {str(self.ids["exp"]): {"bullet_ids": [self.ids["b1"]]}}
        ctx["clarification_questions"] = [
            {"id": "q1", "question": "What did the billing rewrite change?"}
        ]
        ctx["llm_gap_fill_proposals"] = [
            {
                "key": "gf1",
                "experience_id": self.ids["exp"],
                "text": GAP_TEXT,
                "pattern_kind": "manual",
            }
        ]
        self.write_ctx(ctx)
        # B3 (pending) is pulled in from the drawer; it renders only once approved.
        self.state = {
            "context_path": self.cp,
            "pinned": [],
            "excluded": [],
            "added": [self.ids["b3"]],
        }

    def ctx(self, path: str | None = None) -> dict[str, Any]:
        return json.loads(Path(path or self.cp).read_text(encoding="utf-8"))

    def write_ctx(self, ctx: dict[str, Any]) -> None:
        Path(self.cp).write_text(json.dumps(ctx), encoding="utf-8")

    # ---- Compose actions (what the client sends) ----

    def save(self, *, freeze: bool = False, **changes: Any) -> dict[str, Any]:
        self.state.update(changes)
        body = dict(self.state, freeze=True) if freeze else dict(self.state)
        r = self.client.post(f"/api/applications/{self.aid}/composition", json=body)
        assert r.status_code == 200, r.get_data(as_text=True)
        return dict(r.get_json())

    def compose_corpus_edit(self, method: str, url: str, body: dict | None = None) -> Any:
        """A corpus write issued from Compose: the touch first, then the corpus route.

        Mirrors `_composeCorpusFetch` in static/app.js. The touch is the only line the
        fix added to the instrument (before it, Compose sent just the corpus request).
        """
        t = self.client.post(
            f"/api/applications/{self.aid}/composition/touch", json={"context_path": self.cp}
        )
        assert t.status_code == 200, t.get_data(as_text=True)
        r = self.client.open(url, method=method, json=body or {})
        assert 200 <= r.status_code < 300, (url, r.get_data(as_text=True))
        return r.get_json()

    def corpus_panel_edit(self, method: str, url: str, body: dict | None = None) -> Any:
        """The same corpus write issued from the Career Corpus panel (outside Compose)."""
        r = self.client.open(url, method=method, json=body or {})
        assert 200 <= r.status_code < 300, (url, r.get_data(as_text=True))
        return r.get_json()

    # ---- observation ----

    def live_doc(self, path: str | None = None) -> dict[str, Any]:
        """What "Save and continue" would approve right now (Compose's state)."""
        from corpus_to_json_resume import build_json_resume_from_corpus
        from db.session import get_session

        s = get_session()
        try:
            return build_json_resume_from_corpus(
                s, self.ids["candidate"], application_id=self.aid, context_data=self.ctx(path)
            )
        finally:
            s.close()

    def state_projection(self) -> dict[str, Any]:
        """Every computed boolean the client can read about this application's freeze.

        `resume_state` (resume-into-wizard) plus an identical, edit-free autosave's
        response. The autosave response echoes its request fields back; those are
        excluded by name (`_COMPOSITION_REQUEST_FIELDS`), so the projection carries
        only what the server derived.
        """
        r = self.client.get(f"/api/applications/{self.aid}")
        assert r.status_code == 200, r.get_data(as_text=True)
        rs = r.get_json()["resume_state"]
        save = self.client.post(f"/api/applications/{self.aid}/composition", json=dict(self.state))
        assert save.status_code == 200, save.get_data(as_text=True)
        return {
            "resume_state": {k: v for k, v in rs.items() if isinstance(v, bool)},
            "autosave": {
                k: v
                for k, v in save.get_json().items()
                if isinstance(v, bool) and k not in _COMPOSITION_REQUEST_FIELDS
            },
        }

    def generate(self, path: str | None = None) -> dict[str, Any]:
        before = dict(self.calls)
        r = self.client.post(
            "/api/generate",
            json={"username": USER, "context_path": path or self.cp, "output_format": ".md"},
        )
        body = r.get_json() or {}
        rec: dict[str, Any] = {"status": r.status_code, "error": body.get("error")}
        if r.status_code == 200:
            rec["resume_md"] = body["resume_preview"]
            rec["file_md"] = Path(body["resume_path"]).read_text(encoding="utf-8")
            rec["child"] = body["context_path"]
        rec["llm_calls"] = {k: self.calls[k] - before[k] for k in self.calls}
        return rec

    def generate_stream(self, path: str | None = None) -> dict[str, Any]:
        before = dict(self.calls)
        r = self.client.post(
            "/api/generate/stream",
            json={"username": USER, "context_path": path or self.cp, "output_format": ".md"},
        )
        rec: dict[str, Any] = {"status": r.status_code}
        if r.mimetype == "text/event-stream":
            events = _parse_sse(r.get_data(as_text=True))
            done = next((p for ev, p in events if ev == "done"), None)
            err = next((p for ev, p in events if ev == "error"), None)
            rec["events"] = [ev for ev, _ in events]
            if done is not None:
                rec["resume_md"] = done["resume_preview"]
                rec["file_md"] = Path(done["resume_path"]).read_text(encoding="utf-8")
                rec["child"] = done["context_path"]
            if err is not None:
                rec["error"] = err.get("error")
        else:
            rec["error"] = (r.get_json() or {}).get("error")
        rec["llm_calls"] = {k: self.calls[k] - before[k] for k in self.calls}
        return rec

    def preview_html(self, path: str | None = None) -> tuple[int, str]:
        r = self.client.get(
            f"/api/applications/{self.aid}/preview", query_string={"context_path": path or self.cp}
        )
        return r.status_code, r.get_data(as_text=True)

    def compose_view(self) -> str:
        r = self.client.get(
            f"/api/applications/{self.aid}/composition", query_string={"context_path": self.cp}
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        return r.get_data(as_text=True)

    def refinement_input(self) -> str:
        self.captured.pop("current_resume", None)
        r = self.client.post(
            f"/api/applications/{self.aid}/draft-refinement",
            json={"context_path": self.cp, "note": "Sharpen the billing bullet."},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        return str(self.captured.get("current_resume", ""))


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for block in text.split("\n\n"):
        ev, data = "", ""
        for line in block.splitlines():
            if line.startswith("event: "):
                ev = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        if ev:
            out.append((ev, json.loads(data) if data else {}))
    return out


# -------------------------------------------------------------------
# The arms: one post-freeze edit each, as the client issues it today
# -------------------------------------------------------------------


def _r1_bullet_text(r: _Rig) -> str:
    r.compose_corpus_edit("PUT", f"/api/bullets/{r.ids['b1']}", {"text": EDITED})
    return EDITED


def _r2_pin(r: _Rig) -> str:
    r.save(pinned=[r.ids["b2"]])
    return B2


def _r3_exclude(r: _Rig) -> str:
    r.save(excluded=[r.ids["b1"]])
    return B1


def _r4_summary_retype(r: _Rig) -> str:
    r.save(summary_text=SUMMARY1, summary_text_edited=True)
    return SUMMARY1


def _r5_gap_fill_accept(r: _Rig) -> str:
    resp = r.client.post(
        f"/api/applications/{r.aid}/gap-fill-decide",
        json={"context_path": r.cp, "key": "gf1", "decision": "accept"},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    # The client folds the accepted id into its state so the next save resends it.
    r.state["accepted_generated_bullet_ids"] = resp.get_json()["accepted_generated_bullet_ids"]
    return GAP_TEXT


def _r7_approve_pending_bullet(r: _Rig) -> str:
    r.compose_corpus_edit("POST", f"/api/bullets/{r.ids['b3']}/accept")
    return B3


def _r8_approve_pending_skill(r: _Rig) -> str:
    r.compose_corpus_edit(
        "PUT", f"/api/skills/{r.ids['skill_pending']}", {"is_pending_review": False}
    )
    return SKILL_PENDING


def _r9_add_title_and_pin(r: _Rig) -> str:
    body = r.compose_corpus_edit(
        "POST",
        f"/api/experiences/{r.ids['exp']}/titles",
        {"title": TITLE_NEW, "truthful_enough_to_use": True},
    )
    r.save(pinned_title_ids={str(r.ids["exp"]): body["id"]})
    return TITLE_NEW


# Arms whose edit changes what "Save and continue" would approve.
CONTENT_ARMS = {
    "R1_bullet_text_item106": _r1_bullet_text,
    "R2_pin_item66": _r2_pin,
    "R3_exclude_item66": _r3_exclude,
    "R4_summary_retype_item66": _r4_summary_retype,
    "R5_gap_fill_accept": _r5_gap_fill_accept,
    "R7_approve_pending_bullet": _r7_approve_pending_bullet,
    "R8_approve_pending_skill": _r8_approve_pending_skill,
    "R9_add_title_and_pin": _r9_add_title_and_pin,
}

# The Step-6 refinement drafter's <current_resume> block carries the summary and the
# work bullets only (analyzer._current_composition_block), so a skill change is
# invisible to it by construction: R8 is not a D5 arm.
DRAFTER_ARMS = sorted(set(CONTENT_ARMS) - {"R8_approve_pending_skill"})


def _freeze(r: _Rig) -> dict[str, Any]:
    body = r.save(freeze=True)
    assert body["frozen"] is True, body
    return body


def _record(r: _Rig, arm: str, marker: str, **extra: Any) -> dict[str, Any]:
    """Observe every surface once, after the arm's edit. Printed as one JSON line."""
    snapshot_md = json_resume_to_markdown(r.ctx()["approved_composition"])
    live_md = json_resume_to_markdown(r.live_doc())
    preview_status, preview = r.preview_html()
    rec = {
        "arm": arm,
        "marker": marker,
        "marker_in_compose_state": marker in live_md,
        "marker_in_snapshot": marker in snapshot_md,
        "compose_state_equals_snapshot": live_md == snapshot_md,
        "marker_in_compose_view": marker in r.compose_view(),
        "preview": {"status": preview_status, "marker": marker in preview},
        **extra,
    }
    gen = r.generate()
    stream = r.generate_stream()
    for name, g in (("generate", gen), ("generate_stream", stream)):
        rec[name] = {
            "status": g["status"],
            "error": g.get("error"),
            "marker_in_body": marker in g.get("resume_md", ""),
            "marker_in_file": marker in g.get("file_md", ""),
            "body_equals_compose_state": g.get("resume_md") == live_md,
            "body_equals_snapshot": g.get("resume_md") == snapshot_md,
            "llm_calls": g["llm_calls"],
        }
    rec["_live_md"] = live_md
    rec["_gen"] = (gen, stream)
    print(json.dumps({k: v for k, v in rec.items() if not k.startswith("_")}, sort_keys=True))
    return rec


def _public(rec: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rec.items() if not k.startswith("_")}


# -------------------------------------------------------------------
# Controls — hold today, must still hold after the fix
# -------------------------------------------------------------------


class TestControls:
    @pytest.mark.parametrize("arm", sorted(CONTENT_ARMS))
    def test_each_content_arm_changes_what_save_and_continue_would_approve(self, rig, arm):
        """Arm validity, kept separate from the defect tests: every content arm really
        changes Compose's state, and (for the drafter arms) the drafter's block."""
        import analyzer

        _freeze(rig)
        marker = CONTENT_ARMS[arm](rig)
        live = rig.live_doc()
        snapshot = rig.ctx()["approved_composition"]
        rec = {
            "arm": arm,
            "marker_in_compose_state": marker in json_resume_to_markdown(live),
            "compose_state_equals_snapshot": (
                json_resume_to_markdown(live) == json_resume_to_markdown(snapshot)
            ),
            "drafter_blocks_differ": analyzer._current_composition_block(live)
            != analyzer._current_composition_block(snapshot),
        }
        print(json.dumps(rec, sort_keys=True))
        assert not rec["compose_state_equals_snapshot"], rec
        assert rec["drafter_blocks_differ"] == (arm in DRAFTER_ARMS), rec

    def test_c0_never_frozen_edit_reaches_the_freeze(self, rig):
        """An edit made BEFORE the first Save-and-continue is captured by it.

        Item 106's open question: does the failure need a freeze at all?
        Also records whether the analyze-time `career_corpus` snapshot carries the edit.
        """
        _r1_bullet_text(rig)
        corpus_text = json.dumps(rig.ctx().get("career_corpus"))
        _freeze(rig)
        rec = _record(
            rig, "C0_never_frozen", EDITED, edit_in_analyze_time_career_corpus=EDITED in corpus_text
        )
        for name in ("generate", "generate_stream"):
            assert rec[name]["status"] == 200 and rec[name]["marker_in_body"], _public(rec)
            assert rec[name]["marker_in_file"], _public(rec)
            assert rec[name]["llm_calls"]["generate"] == 0, _public(rec)
            assert rec[name]["llm_calls"]["generate_streaming"] == 0, _public(rec)

    def test_c1_frozen_no_edit_is_consistent_and_reads_write_nothing(self, rig):
        """No edit: every surface agrees with the snapshot; GETs don't touch the file."""
        _freeze(rig)
        before = Path(rig.cp).read_bytes()
        rig.compose_view()
        rig.compose_view()
        rig.client.get(f"/api/applications/{rig.aid}")
        assert Path(rig.cp).read_bytes() == before
        rec = _record(rig, "C1_frozen_no_edit", B1)
        assert rec["compose_state_equals_snapshot"], _public(rec)
        for name in ("generate", "generate_stream"):
            assert rec[name]["status"] == 200, _public(rec)
            assert rec[name]["body_equals_snapshot"], _public(rec)
            assert rec[name]["llm_calls"]["generate"] == 0, _public(rec)
            assert rec[name]["llm_calls"]["generate_streaming"] == 0, _public(rec)

    def test_c2_second_save_and_continue_picks_up_the_edit(self, rig):
        """Item 106's open question: re-freezing re-reads the corpus."""
        _freeze(rig)
        _r1_bullet_text(rig)
        _freeze(rig)
        rec = _record(rig, "C2_frozen_then_refrozen", EDITED)
        assert rec["marker_in_snapshot"], _public(rec)
        for name in ("generate", "generate_stream"):
            assert rec[name]["status"] == 200 and rec[name]["marker_in_body"], _public(rec)
            assert rec[name]["marker_in_file"], _public(rec)

    def test_c3_career_corpus_panel_edit_never_reaches_an_approved_application(self, rig):
        """Owner decision 1: edits outside this application's Compose leave it alone."""
        _freeze(rig)
        baseline = rig.state_projection()
        rig.corpus_panel_edit("PUT", f"/api/bullets/{rig.ids['b1']}", {"text": EDITED})
        after = rig.state_projection()
        rec = _record(rig, "C3_corpus_panel_edit", EDITED, projection=[baseline, after])
        assert after == baseline, _public(rec)
        for name in ("generate", "generate_stream"):
            assert rec[name]["status"] == 200, _public(rec)
            assert rec[name]["body_equals_snapshot"], _public(rec)
            assert not rec[name]["marker_in_body"], _public(rec)


# -------------------------------------------------------------------
# Design-kept facts — hold today, must still hold after the fix
# -------------------------------------------------------------------


class TestDesignKeptFacts:
    @pytest.mark.parametrize("arm", sorted(CONTENT_ARMS))
    def test_preview_keeps_serving_the_approved_snapshot(self, rig, arm):
        """The preview stays on what was approved (preview == download), edit or not."""
        _freeze(rig)
        marker = CONTENT_ARMS[arm](rig)
        snapshot_md = json_resume_to_markdown(rig.ctx()["approved_composition"])
        status, html = rig.preview_html()
        rec = {
            "arm": arm,
            "preview_status": status,
            "marker_in_preview": marker in html,
            "marker_in_snapshot": marker in snapshot_md,
        }
        print(json.dumps(rec, sort_keys=True))
        assert status == 200, rec
        assert rec["marker_in_preview"] == rec["marker_in_snapshot"], rec

    def test_o4_builder_reads_exactly_these_context_keys(self, rig):
        """The context keys `build_json_resume_from_corpus` reads (top level).

        Pinned so the fix's staleness inputs can be derived from it, not guessed.
        """
        from corpus_to_json_resume import build_json_resume_from_corpus
        from db.session import get_session

        _freeze(rig)
        _r5_gap_fill_accept(rig)
        rig.save(pinned=[rig.ids["b2"]], summary_text=SUMMARY1, summary_text_edited=True)
        seen: set[str] = set()

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

        s = get_session()
        try:
            build_json_resume_from_corpus(
                s, rig.ids["candidate"], application_id=rig.aid, context_data=_Recording(rig.ctx())
            )
        finally:
            s.close()
        print(json.dumps({"arm": "O4_builder_reads", "keys": sorted(seen)}))
        assert seen == {
            "composition_overrides",
            "llm_recommendations",
            "llm_skill_recommendations",
            "llm_summary_recommendation",
        }, sorted(seen)

    def test_o1_answers_then_regenerate_returns_the_identical_resume(self, rig):
        """Item 132, server half: answers are saved, the regenerate is byte-identical.

        This stays true after the fix (the frozen path is deterministic by design);
        the fix routes a frozen application's answers to Compose instead.
        """
        _freeze(rig)
        first = rig.generate()
        assert first["status"] == 200, first
        child = first["child"]
        r = rig.client.post(
            "/api/answer-clarifications",
            json={
                "context_path": child,
                "username": USER,
                "answers": {"q1": "ZEBRA-ANSWER it cut churn 18 percent"},
                "merge": True,
            },
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        second = rig.generate(child)
        third = rig.generate_stream(child)
        rec = {
            "arm": "O1_answers_then_regenerate_item132",
            "answer_saved_to_context": "ZEBRA-ANSWER"
            in json.dumps(rig.ctx(child)["clarifications"]),
            "generate_status": second["status"],
            "stream_status": third["status"],
            "generate_identical": second.get("resume_md") == first["resume_md"],
            "stream_identical": third.get("resume_md") == first["resume_md"],
            "answer_in_body": "ZEBRA-ANSWER" in second.get("resume_md", ""),
            "llm_calls": [second["llm_calls"], third["llm_calls"]],
        }
        print(json.dumps(rec, sort_keys=True))
        assert rec["answer_saved_to_context"], rec
        assert rec["generate_identical"] and rec["stream_identical"], rec
        assert not rec["answer_in_body"], rec
        assert second["llm_calls"]["generate"] == 0, rec
        assert third["llm_calls"]["generate_streaming"] == 0, rec


# -------------------------------------------------------------------
# Defect invariants — failed on the base tip; pass with the fix
# -------------------------------------------------------------------


class TestDefects:
    @pytest.mark.parametrize("arm", sorted(CONTENT_ARMS))
    def test_d1_generate_never_serves_a_body_that_contradicts_compose(self, rig, arm):
        """D1: after a post-freeze Compose edit, neither generate route returns 200
        with a résumé other than the one Compose shows (what Save-and-continue would
        approve). Refusing is allowed; silently serving the old snapshot is not."""
        _freeze(rig)
        marker = CONTENT_ARMS[arm](rig)
        rec = _record(rig, arm, marker)
        for name in ("generate", "generate_stream"):
            g = rec[name]
            assert g["status"] != 200 or g["body_equals_compose_state"], _public(rec)
            assert g["llm_calls"]["generate"] == 0, _public(rec)
            assert g["llm_calls"]["generate_streaming"] == 0, _public(rec)

    @pytest.mark.parametrize("arm", sorted(CONTENT_ARMS))
    def test_d3_the_server_reports_that_something_changed(self, rig, arm):
        """D3: some server-derived boolean the client reads (resume_state, an
        edit-free autosave's response) differs between "frozen, no edit" and
        "frozen, then edited in Compose". Today they are identical, so the client
        has no way to re-lock Step 5."""
        _freeze(rig)
        baseline = rig.state_projection()
        CONTENT_ARMS[arm](rig)
        after = rig.state_projection()
        print(json.dumps({"arm": arm, "projection": [baseline, after]}, sort_keys=True))
        assert after != baseline, {"arm": arm, "baseline": baseline, "after": after}

    @pytest.mark.parametrize("arm", DRAFTER_ARMS)
    def test_d5_refinement_drafter_reads_what_compose_shows(self, rig, arm):
        """D5: the Step-6 refinement drafter's <current_resume> is Compose's state,
        not the stale snapshot (a refinement drafted from stale text could revert
        the Compose edit)."""
        import analyzer

        _freeze(rig)
        CONTENT_ARMS[arm](rig)
        seen = rig.refinement_input()
        expected = analyzer._current_composition_block(rig.live_doc())
        stale = analyzer._current_composition_block(rig.ctx()["approved_composition"])
        rec = {
            "arm": arm,
            "drafter_sees_compose_state": seen == expected,
            "drafter_sees_snapshot": seen == stale,
            "blocks_differ": expected != stale,
        }
        print(json.dumps(rec, sort_keys=True))
        assert seen == expected, rec

    def test_d6_typed_edits_and_preview_agree_after_a_regenerate(self, rig):
        """D6 (the typed-edits drop): after "Use edits as baseline" and a regenerate
        of an unchanged frozen composition, the résumé the app resumes with and the
        preview it shows are the same document."""
        _freeze(rig)
        first = rig.generate()
        child = first["child"]
        typed = first["resume_md"].replace(B1, TYPED)
        assert typed != first["resume_md"]
        r = rig.client.post(
            "/api/save-edits",
            json={"context_path": child, "username": USER, "edited_resume": typed},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        _, preview_before = rig.preview_html(child)
        second = rig.generate(child)
        grandchild = second["child"]
        _, preview_after = rig.preview_html(grandchild)
        detail = rig.client.get(f"/api/applications/{rig.aid}").get_json()["resume_state"]
        rec = {
            "arm": "O2_typed_edits",
            "typed_in_preview_before_regenerate": TYPED in preview_before,
            "regenerate_identical": second["resume_md"] == first["resume_md"],
            "edited_text_kept_in_new_context": "edited_resume_text" in rig.ctx(grandchild),
            "typed_in_preview_after_regenerate": TYPED in preview_after,
            "typed_in_resume_state_md": TYPED in (detail.get("resume_md") or ""),
            "resume_state_context_is_newest": detail.get("context_path") == grandchild,
        }
        print(json.dumps(rec, sort_keys=True))
        assert rec["typed_in_preview_after_regenerate"] == rec["typed_in_resume_state_md"], rec
