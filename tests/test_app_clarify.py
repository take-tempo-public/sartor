"""Tests for the /api/clarify and /api/answer-clarifications routes.

The routes live on `blueprints/analysis.py` (Sprint 8.3b). Tests build the app via
the `create_app(Config(base_dir=tmp_path))` factory — config paths are injected, not
module globals monkeypatched — and stub `analyzer.clarify` on the blueprint module
(the imported binding the route resolves) so they run without network or Anthropic SDK
calls. Verifies the security guards (_safe_username, _within) and the persistence
shape (clarification_questions, clarifications) written back to the context file.
"""

import json
import threading
from pathlib import Path

import pytest


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Factory-built test client with config paths under tmp_path.

    Also creates a saved context_*.json file under OUTPUT_DIR/alice/ so the
    routes have something to load. `blueprints.analysis.clarify` is replaced
    with a deterministic stub so no network or LLM call is made.
    """
    import blueprints.analysis as ban
    from app import create_app
    from config import Config

    # Stub clarify to return a deterministic payload; the route should accept it
    # whether or not the LLM was actually called.
    def _stub_clarify(client, context_set, analysis, username="", run_id=""):
        return {
            "questions": [
                {
                    "id": "q1",
                    "text": "Used Kubernetes in production?",
                    "target_gap": "Essential skill Kubernetes missing from resume",
                    "kind": "experience_probe",
                },
                {
                    "id": "q2",
                    "text": "Did the migration ship or remain a POC?",
                    "target_gap": "Scope ambiguity flagged in title_alignment",
                    "kind": "scope_probe",
                },
            ],
            "reasoning": "Two probes covering missing tech and shipped status.",
        }

    monkeypatch.setattr(ban, "clarify", _stub_clarify)
    # Avoid real API client construction
    monkeypatch.setattr(ban, "_get_client", lambda: object())

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    # ensure_dirs() (in the factory) already created configs/output under tmp_path.
    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    client = app.test_client()
    context_path = output_dir / "alice" / "context_20260511_120000.json"
    initial = {
        "timestamp": "2026-05-11T12:00:00",
        "candidate": {"name": "Alice", "skills": ["docker"]},
        "resume": {
            "text": "...",
            "filename": "alice.docx",
            "format": ".docx",
            "sections": [],
            "path": "",
        },
        "supplemental_resumes": [],
        "job_description": "K8s SRE role.",
        "deterministic_analysis": {
            "jd_keywords": {},
            "resume_keywords": {},
            "keyword_overlap": {"missing_from_resume": ["kubernetes"]},
            "ats_warnings": [],
        },
        "llm_analysis": {
            "essential_skills": ["kubernetes"],
            "preferred_skills": [],
            "comparison": {"strengths": [], "gaps": ["No K8s"], "title_alignment": ""},
            "keyword_placement": [],
            "overall_strategy": "",
            "ideal_resume_profile": "",
            "industry_keywords": [],
            "hidden_qualities": [],
            "professional_vocabulary": [],
            "suggestions": [],
            "ats_improvements": [],
        },
        "run_id": "abc123abc123",
    }
    context_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    return client, context_path, output_dir


class TestClarifyRoute:
    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/clarify", json={})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, output_dir = app_client
        # Path that's a sibling of OUTPUT_DIR — must be rejected by _within
        outside = tmp_path / "elsewhere.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post("/api/clarify", json={"context_path": str(outside)})
        assert resp.status_code == 403

    def test_nonexistent_context_file_returns_404(self, app_client, tmp_path):
        client, _, output_dir = app_client
        ghost = output_dir / "alice" / "context_ghost.json"
        resp = client.post("/api/clarify", json={"context_path": str(ghost)})
        assert resp.status_code == 404

    def test_context_without_analysis_returns_400(self, app_client, tmp_path):
        client, _, output_dir = app_client
        no_analysis = output_dir / "alice" / "context_blank.json"
        no_analysis.write_text(json.dumps({"timestamp": "x", "candidate": {}}), encoding="utf-8")
        resp = client.post("/api/clarify", json={"context_path": str(no_analysis)})
        assert resp.status_code == 400

    def test_happy_path_persists_questions_and_returns_them(self, app_client):
        client, context_path, _ = app_client
        resp = client.post("/api/clarify", json={"context_path": str(context_path)})
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["questions"]) == 2
        assert body["questions"][0]["kind"] == "experience_probe"
        assert "context_path" in body

        # Questions must be persisted on the same context file
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert "clarification_questions" in saved
        assert len(saved["clarification_questions"]) == 2

    def test_preserves_existing_run_id(self, app_client):
        client, context_path, _ = app_client
        client.post("/api/clarify", json={"context_path": str(context_path)})
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["run_id"] == "abc123abc123"


class TestAnswerClarificationsRoute:
    def _seed_questions(self, context_path: Path, include_iter: bool = False):
        """Pre-populate clarification_questions on the saved context.

        With include_iter=True, also append an iteration-round question
        (iter1_q1) so the two-round merge behavior can be exercised — the
        iterate interview appends its own questions to the same list.
        """
        ctx = json.loads(context_path.read_text(encoding="utf-8"))
        questions = [
            {"id": "q1", "text": "Q1?", "kind": "experience_probe", "target_gap": "k8s"},
            {"id": "q2", "text": "Q2?", "kind": "scope_probe", "target_gap": "scope"},
        ]
        if include_iter:
            questions.append(
                {
                    "id": "iter1_q1",
                    "text": "Iter Q1?",
                    "kind": "iteration_probe",
                    "target_gap": "draft weakness",
                },
            )
        ctx["clarification_questions"] = questions
        context_path.write_text(json.dumps(ctx, indent=2), encoding="utf-8")

    def test_missing_context_path_returns_400(self, app_client):
        client, _, _ = app_client
        resp = client.post("/api/answer-clarifications", json={"answers": {}})
        assert resp.status_code == 400

    def test_path_outside_output_dir_returns_403(self, app_client, tmp_path):
        client, _, _ = app_client
        outside = tmp_path / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        resp = client.post(
            "/api/answer-clarifications", json={"context_path": str(outside), "answers": {}}
        )
        assert resp.status_code == 403

    def test_answers_must_be_dict(self, app_client):
        client, context_path, _ = app_client
        resp = client.post(
            "/api/answer-clarifications",
            json={"context_path": str(context_path), "answers": ["not", "a", "dict"]},
        )
        assert resp.status_code == 400

    def test_stores_valid_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "Yes, used K8s briefly.", "q2": "Shipped to prod."},
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        # memory_rows == 0: this context is legacy/file-only (no
        # application_run_id), so the candidate-memory mirror is a no-op.
        assert body == {"ok": True, "answered": 2, "total": 2, "memory_rows": 0}

        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {
            "q1": "Yes, used K8s briefly.",
            "q2": "Shipped to prod.",
        }

    def test_filters_unknown_question_ids(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "real answer", "q_attacker": "injected"},
            },
        )
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert "q_attacker" not in saved["clarifications"]
        assert saved["clarifications"] == {"q1": "real answer"}

    def test_filters_empty_and_whitespace_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "   ", "q2": "real answer"},
            },
        )
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {"q2": "real answer"}

    def test_idempotent_overwrites_prior_answers(self, app_client):
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "first try"},
            },
        )
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "revised answer", "q2": "added later"},
            },
        )
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {
            "q1": "revised answer",
            "q2": "added later",
        }

    def test_merge_preserves_prior_round_answers(self, app_client):
        """KW4 regression: the iteration interview submits ONLY its own
        textareas (`_collectIterateClarifyAnswers`). With merge:true the route
        must keep the analyze-round answers already on the context, so
        generate() at iter>=1 reads the union as first-person ground truth.

        Pre-fix the route did a whole-map replace, so the 2nd-round submit
        dropped q1/q2 — this test fails on the pre-fix tree and guards the fix.
        """
        client, context_path, _ = app_client
        self._seed_questions(context_path, include_iter=True)

        # Round 1 — analyze-time answers.
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "Lead implementer.", "q2": "Shipped to prod."},
                "merge": True,
            },
        )
        # Round 2 — iteration interview submits only its own answer.
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"iter1_q1": "Reduced p99 latency by 40%."},
                "merge": True,
            },
        )
        assert resp.status_code == 200
        # `answered` reports this-submit count, not the cumulative total.
        assert resp.get_json()["answered"] == 1

        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {
            "q1": "Lead implementer.",
            "q2": "Shipped to prod.",
            "iter1_q1": "Reduced p99 latency by 40%.",
        }

    def test_merge_false_replaces_and_clears(self, app_client):
        """The skip path posts answers={} merge=false to deliberately clear
        previously-saved answers (replace semantics)."""
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "saved", "q2": "saved"},
                "merge": True,
            },
        )
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {},
                "merge": False,
            },
        )
        assert resp.status_code == 200
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {}

    def test_default_merges_when_flag_absent(self, app_client):
        """Omitting `merge` defaults to merge (the safe behavior): two single
        posts of different ids accumulate rather than the 2nd replacing the
        1st. Fails on the pre-fix tree (replace default)."""
        client, context_path, _ = app_client
        self._seed_questions(context_path)

        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "first id"},
            },
        )
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q2": "second id"},
            },
        )
        saved = json.loads(context_path.read_text(encoding="utf-8"))
        assert saved["clarifications"] == {"q1": "first id", "q2": "second id"}


# ---------------------------------------------------------------------------
# Candidate-memory mirror (KW7 / B.8 Part 1): answered clarifications on a
# corpus-backed context land as `clarification` DB rows.
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_client(tmp_path, monkeypatch):
    """app_client variant with a real temp DB so the memory write path can
    resolve context.application_run_id → run → application → candidate.

    The DB-path monkeypatch (db.session.DEFAULT_DB_PATH) is a distinct, legitimate
    seam — only the app-global path monkeypatch retires with the factory.
    """
    db_file = tmp_path / "memory.sqlite"
    import db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "DEFAULT_DB_PATH", db_file)
    db_session_mod._engine = None
    db_session_mod._SessionLocal = None

    from app import create_app
    from config import Config

    app = create_app(Config(base_dir=tmp_path))
    app.config["TESTING"] = True
    # ensure_dirs() (in the factory) already created configs/output under tmp_path.
    output_dir = tmp_path / "output"
    configs_dir = tmp_path / "configs"
    (configs_dir / "alice.config").write_text("{}", encoding="utf-8")
    (output_dir / "alice").mkdir()

    from db.session import init_db

    init_db(db_file)

    from db.models import Application, ApplicationRun, Candidate
    from db.session import get_session

    s = get_session()
    try:
        cand = Candidate(username="alice", name="Alice")
        s.add(cand)
        s.flush()
        app_row = Application(
            candidate_id=cand.id,
            title="SRE @ Foo",
            jd_text="K8s SRE role.",
            jd_fingerprint="f" * 16,
            status="draft",
        )
        s.add(app_row)
        s.flush()
        run = ApplicationRun(
            application_id=app_row.id,
            iteration=0,
            run_id="run123run123",
            prompt_version="2026-06-10.1",
            corpus_snapshot_json="{}",
        )
        s.add(run)
        s.commit()
        ids = {"candidate": cand.id, "application": app_row.id, "run": run.id}
    finally:
        s.close()

    context_path = output_dir / "alice" / "context_20260610_120000.json"
    context_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-06-10T12:00:00",
                "candidate": {"name": "Alice"},
                "job_description": "K8s SRE role.",
                "run_id": "run123run123",
                "application_run_id": ids["run"],
                "clarification_questions": [
                    {
                        "id": "q1",
                        "text": "Used Kubernetes in production?",
                        "kind": "experience_probe",
                        "target_gap": "k8s missing",
                    },
                    {
                        "id": "q2",
                        "text": "Worked in a regulated environment?",
                        "kind": "context_probe",
                        "target_gap": "Context signal: regulated industry",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return app.test_client(), context_path, ids


def _memory_rows(candidate_id):
    from db.models import Clarification
    from db.session import get_session

    s = get_session()
    try:
        return s.query(Clarification).filter_by(candidate_id=candidate_id).all()
    finally:
        s.close()


class TestClarificationMemoryWrite:
    def test_answers_create_memory_rows(self, memory_client):
        client, context_path, ids = memory_client
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "Yes, two years on EKS.", "q2": "HIPAA workflows."},
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["memory_rows"] == 2

        rows = {r.question: r for r in _memory_rows(ids["candidate"])}
        assert len(rows) == 2
        k8s = rows["Used Kubernetes in production?"]
        assert k8s.answer == "Yes, two years on EKS."
        assert k8s.kind == "experience_probe"
        assert k8s.target_gap == "k8s missing"
        assert k8s.origin_application_id == ids["application"]
        assert k8s.origin_run_id == ids["run"]
        # context_probe is not in the DB kind enum — files as experience_probe,
        # target_gap keeps the "Context signal: …" provenance.
        reg = rows["Worked in a regulated environment?"]
        assert reg.kind == "experience_probe"
        assert reg.target_gap == "Context signal: regulated industry"

    def test_resubmit_updates_answer_without_duplicating(self, memory_client):
        client, context_path, ids = memory_client
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "first answer"},
            },
        )
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "revised answer"},
            },
        )
        assert resp.get_json()["memory_rows"] == 1
        rows = _memory_rows(ids["candidate"])
        assert len(rows) == 1
        assert rows[0].answer == "revised answer"

    def test_unchanged_resubmit_writes_nothing(self, memory_client):
        client, context_path, ids = memory_client
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "same answer"},
            },
        )
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "same answer"},
            },
        )
        assert resp.get_json()["memory_rows"] == 0
        assert len(_memory_rows(ids["candidate"])) == 1

    def test_promoted_row_is_never_clobbered(self, memory_client):
        client, context_path, ids = memory_client
        client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "original answer"},
            },
        )
        from db.session import get_session

        s = get_session()
        try:
            row = _memory_rows(ids["candidate"])[0]
            s.query(type(row)).filter_by(id=row.id).update(
                {"is_promoted_to_bullet": 1},
            )
            s.commit()
        finally:
            s.close()

        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "attempted rewrite"},
            },
        )
        assert resp.get_json()["memory_rows"] == 0
        rows = _memory_rows(ids["candidate"])
        assert len(rows) == 1
        assert rows[0].answer == "original answer"

    def test_skip_writes_nothing(self, memory_client):
        client, context_path, ids = memory_client
        resp = client.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {},
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["memory_rows"] == 0
        assert _memory_rows(ids["candidate"]) == []


# -------------------------------------------------------------------
# The falsification experiment (charter C-7)
# -------------------------------------------------------------------


class TestConcurrentContextWriters:
    """Does a concurrent `/api/clarify` erase `/api/answer-clarifications`'s persisted delta?

    Specified in `docs/dev/diagnosis/fix-context-write-lost-update-gap.md`'s
    Falsification section. `/api/clarify` and `/api/answer-clarifications` share
    the read-whole-file / do-work / write-whole-dict-back shape that
    `docs/dev/diagnosis/compose-summary-draft-settle-hole.md` (O-4/O-7) already
    proved is a lost-update hazard at 12 other sites — but that proof was never
    run against these two routes specifically. This test exists to kill or
    confirm the hypothesis for this pairing, not to assume it.

    Forces the one ordering the hypothesis requires:

        1. `/api/clarify` reads the whole context          (analysis.py:459)
        2. `/api/answer-clarifications` reads, merges, and
           persists its answer                              (analysis.py:667)
        3. `/api/clarify` returns from its stubbed LLM call and writes its
           now-stale whole dict back                         (analysis.py:490)

    `/api/clarify` has necessarily completed its read by the time it reaches its
    LLM call, so stubbing that call is a precise, non-invasive probe of step 1.
    `/api/answer-clarifications` has no LLM call to stub — it runs synchronously
    in the main test thread while `/api/clarify`'s thread is parked, which is
    sufficient to force step 2 inside step 1-3's window.

    **If this test PASSES on HEAD the hypothesis is dead for this pairing —
    stop, do not fix, widen the instrument** (the dossier's Falsification section
    names the other 4 sites as further candidates).
    """

    def test_answer_clarifications_does_not_erase_a_concurrent_clarify(
        self, app_client, monkeypatch
    ):
        import blueprints.analysis as ban

        client, context_path, _output_dir = app_client
        app = client.application

        # Pre-seed a known clarification question so /api/answer-clarifications
        # has a valid id to merge an answer against.
        seeded = json.loads(context_path.read_text(encoding="utf-8"))
        seeded["clarification_questions"] = [
            {
                "id": "q1",
                "text": "Used Kubernetes in production?",
                "target_gap": "Essential skill Kubernetes missing from resume",
                "kind": "experience_probe",
            }
        ]
        context_path.write_text(json.dumps(seeded), encoding="utf-8")

        clarify_has_read = threading.Event()
        answer_has_persisted = threading.Event()

        def _slow_clarify(client_arg, context_set, analysis, username="", run_id=""):
            # Reaching here means /api/clarify already holds its in-memory copy
            # of the context (read at analysis.py:459, before this call at :471).
            # Hold the call open — as a real multi-second Haiku call would —
            # while /api/answer-clarifications reads, merges, and persists.
            clarify_has_read.set()
            assert answer_has_persisted.wait(timeout=20), (
                "/api/answer-clarifications never persisted"
            )
            return {
                "questions": [
                    {
                        "id": "q2",
                        "text": "Did the migration ship or remain a POC?",
                        "target_gap": "Scope ambiguity",
                        "kind": "scope_probe",
                    }
                ],
                "reasoning": "Probing shipped status.",
            }

        monkeypatch.setattr(ban, "clarify", _slow_clarify)

        status: dict[str, int] = {}

        def _fire_clarify() -> None:
            c = app.test_client()
            r = c.post("/api/clarify", json={"context_path": str(context_path)})
            status["clarify"] = r.status_code

        t_clarify = threading.Thread(target=_fire_clarify)
        t_clarify.start()
        assert clarify_has_read.wait(timeout=20), "/api/clarify never reached its LLM call"

        # /api/clarify is now provably parked mid-call, holding a pre-answer
        # copy of the context. Fire /api/answer-clarifications to completion
        # (read, merge, write) inside that window.
        c2 = app.test_client()
        r2 = c2.post(
            "/api/answer-clarifications",
            json={
                "context_path": str(context_path),
                "answers": {"q1": "Yes, led a K8s migration for a 12-person team."},
            },
        )
        status["answer"] = r2.status_code
        # Its write has landed on disk; release /api/clarify into its write-back.
        answer_has_persisted.set()

        t_clarify.join(timeout=30)
        assert not t_clarify.is_alive(), "/api/clarify thread hung"

        # Asserted BEFORE the lost-update check so a threading/500 failure is
        # never mistaken for the defect under test. Different failure, different line.
        assert status.get("answer") == 200, f"/api/answer-clarifications did not succeed: {status}"
        assert status.get("clarify") == 200, f"/api/clarify did not succeed: {status}"

        final = json.loads(context_path.read_text(encoding="utf-8"))

        # /api/clarify's own delta must land — it wrote last, so this holds on HEAD.
        assert len(final.get("clarification_questions", [])) == 1, "/api/clarify's delta is missing"

        # ...and it must NOT have cost us /api/answer-clarifications's. On HEAD it does.
        assert final.get("clarifications", {}).get("q1") == (
            "Yes, led a K8s migration for a 12-person team."
        ), (
            "LOST UPDATE: /api/clarify's whole-dict write-back erased the answer "
            "/api/answer-clarifications had already persisted."
        )
