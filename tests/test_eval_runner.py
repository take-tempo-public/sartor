"""Unit tests for evals/runner.py and dashboard normalization.

These cover the eval-result schema migration (0-5 int → 0.0-5.0 float),
the score-coercion safety net at the judge boundary, and the dashboard's
backward-compatible record normalization.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dashboard.routes import _normalize_eval_record


class TestNormalizeEvalRecord:
    """The dashboard reads old (int score) and new (float score) records side
    by side. _normalize_eval_record coerces them to a single shape."""

    def test_int_score_becomes_float(self):
        out = _normalize_eval_record({"score": 4, "rubric": "grounding"})
        assert isinstance(out["score"], float)
        assert out["score"] == 4.0

    def test_float_score_passes_through(self):
        out = _normalize_eval_record({"score": 3.7, "rubric": "grounding"})
        assert out["score"] == pytest.approx(3.7)

    def test_none_score_preserved(self):
        out = _normalize_eval_record({"score": None, "rubric": "grounding"})
        assert out["score"] is None

    def test_missing_score_field_left_absent(self):
        # Pipeline-error rows may legitimately lack the field
        out = _normalize_eval_record({"rubric": None, "status": "pipeline_error"})
        assert "score" not in out or out.get("score") is None

    def test_malformed_score_becomes_none(self):
        out = _normalize_eval_record({"score": "not-a-number", "rubric": "grounding"})
        assert out["score"] is None

    def test_defaults_for_missing_fields(self):
        out = _normalize_eval_record({"score": 5, "rubric": "grounding"})
        assert out["schema_version"] == 1  # legacy default
        assert out["score_max"] == 5.0
        assert out["prompt_version"] == ""
        assert out["failed_rules"] == []
        assert out["reasons"] == []

    def test_existing_fields_retained(self):
        out = _normalize_eval_record(
            {
                "score": 5,
                "schema_version": 2,
                "score_max": 5.0,
                "prompt_version": "2026-05-09.1",
                "run_id": "abc123def456",
                "failed_rules": ["invented_metric"],
                "reasons": ["test"],
            }
        )
        assert out["schema_version"] == 2
        assert out["prompt_version"] == "2026-05-09.1"
        assert out["run_id"] == "abc123def456"
        assert out["failed_rules"] == ["invented_metric"]

    def test_default_run_id_is_empty_string(self):
        # Legacy records without run_id should normalize to "" so the dashboard
        # template's `or "—"` fallback works without raising.
        out = _normalize_eval_record({"score": 5, "rubric": "grounding"})
        assert out["run_id"] == ""

    def test_does_not_mutate_input(self):
        original = {"score": 4, "rubric": "grounding"}
        _normalize_eval_record(original)
        assert original == {"score": 4, "rubric": "grounding"}


class TestPassThreshold:
    """4.0 should pass; 3.9 should fail. Verifies the float boundary."""

    def test_pass_threshold_is_float(self):
        from evals.runner import PASS_THRESHOLD

        assert PASS_THRESHOLD == 4.0
        assert isinstance(PASS_THRESHOLD, float)

    def test_classification_at_boundary(self):
        from evals.runner import PASS_THRESHOLD

        assert PASS_THRESHOLD <= 4.0
        assert PASS_THRESHOLD > 3.9
        assert PASS_THRESHOLD <= 4.1


class TestGradeCoercion:
    """Haiku judges occasionally emit integer scores. The runner must coerce
    to float at the boundary so all downstream code can assume float."""

    def _make_judge_response(self, json_text: str) -> MagicMock:
        msg = MagicMock()
        msg.content = [MagicMock(text=json_text)]
        return msg

    def test_integer_score_coerced_to_float(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": 4, "reasons": ["ok"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert isinstance(grade["score"], float)
        assert grade["score"] == 4.0

    def test_fractional_score_preserved(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": 4.3, "reasons": ["nearly"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert isinstance(grade["score"], float)
        assert grade["score"] == pytest.approx(4.3)

    def test_string_score_falls_back_to_zero(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response(
            '{"score": "high", "reasons": ["bad judge output"], "failed_rules": []}'
        )

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        # Coercion failure → score becomes 0.0 (a clear "did not pass")
        assert grade["score"] == 0.0

    def test_unparseable_json_returns_zero(self, tmp_path: Path):
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response("not json at all")

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert grade["score"] == 0
        assert "raw" in grade

    def test_unparseable_json_marks_status_judge_error(self, tmp_path: Path):
        """Malformed judge responses must be flagged as judge_error so
        _detect_regression and the summary roll-up skip them. Without
        this, the caller's grade.setdefault('status', 'ok') labels the
        record as a successful 0-score grading and fires a
        false-positive WARN against the baseline.
        """
        from evals.runner import _grade

        client = MagicMock()
        client.messages.create.return_value = self._make_judge_response("not json at all")

        rubric = tmp_path / "rubric.md"
        rubric.write_text("Grade this.", encoding="utf-8")

        grade = _grade(client, rubric, {"fixture": "test"})
        assert grade["status"] == "judge_error"
        assert "judge response was not valid JSON" in grade["reasons"]


class TestSchemaConstants:
    """Schema version + score max constants must be exported from the runner."""

    def test_schema_version_present(self):
        from evals.runner import SCHEMA_VERSION

        assert SCHEMA_VERSION == 3

    def test_score_max_present(self):
        from evals.runner import SCORE_MAX

        assert SCORE_MAX == 5.0


class TestRegressionDetection:
    """The runner compares each new (fixture, rubric) score to the most-recent
    prior score and warns when the drop exceeds REGRESSION_DELTA."""

    def test_no_baseline_returns_none(self):
        from evals.runner import _detect_regression

        out = _detect_regression("a", "grounding", 4.5, baseline={})
        assert out is None

    def test_score_drop_flagged_as_regression(self, monkeypatch):
        # Force a tight delta so any drop > 0.1 trips
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.1)
        from evals.runner import _detect_regression

        baseline = {("a", "grounding"): {"score": 4.8, "prompt_version": "v1"}}
        out = _detect_regression("a", "grounding", 3.5, baseline)
        assert out is not None
        assert out["is_regression"] is True
        assert out["is_improvement"] is False
        assert out["delta"] == -1.3
        assert out["prev_prompt_version"] == "v1"

    def test_score_improvement_flagged(self, monkeypatch):
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.1)
        from evals.runner import _detect_regression

        baseline = {("a", "tone"): {"score": 3.8}}
        out = _detect_regression("a", "tone", 4.7, baseline)
        assert out is not None
        assert out["is_improvement"] is True
        assert out["is_regression"] is False
        assert out["delta"] == 0.9

    def test_within_delta_is_neither(self, monkeypatch):
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.5)
        from evals.runner import _detect_regression

        baseline = {("a", "tone"): {"score": 4.5}}
        out = _detect_regression("a", "tone", 4.2, baseline)
        assert out is not None
        assert out["is_regression"] is False
        assert out["is_improvement"] is False
        # delta = -0.3, within ±0.5

    def test_int_baseline_score_handled(self, monkeypatch):
        # Legacy int score in baseline should still compare
        monkeypatch.setattr("evals.runner.REGRESSION_DELTA", 0.5)
        from evals.runner import _detect_regression

        baseline = {("a", "grounding"): {"score": 5}}
        out = _detect_regression("a", "grounding", 3.0, baseline)
        assert out is not None
        assert out["is_regression"] is True
        assert out["prev_score"] == 5.0

    def test_load_baseline_excludes_current_file(self, tmp_path, monkeypatch):
        # Two prior result files + a "current" one. Current file's records
        # should be excluded so the new run can be compared against history only.
        from evals.runner import _load_baseline_scores

        results_dir = tmp_path / "results"
        results_dir.mkdir()
        monkeypatch.setattr("evals.runner.RESULTS_DIR", results_dir)

        (results_dir / "20260501_000000Z.jsonl").write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 4.5, "timestamp": "2026-05-01T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (results_dir / "20260507_000000Z.jsonl").write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 4.8, "timestamp": "2026-05-07T00:00:00Z"}\n',
            encoding="utf-8",
        )
        current = results_dir / "20260509_000000Z.jsonl"
        current.write_text(
            '{"fixture": "a", "rubric": "grounding", "score": 1.0, "timestamp": "2026-05-09T00:00:00Z"}\n',
            encoding="utf-8",
        )
        baseline = _load_baseline_scores(current)
        # Should pick the more-recent prior run (4.8), not the current one (1.0)
        assert baseline[("a", "grounding")]["score"] == 4.8


class TestLegacyResultCompatibility:
    """A real result line from before the migration must still load via the
    dashboard normalize helper without raising."""

    def test_v1_record_loads(self):
        v1_record = json.loads(
            '{"timestamp": "2026-05-06T23:50:05Z", "source": "eval", '
            '"fixture": "data-scientist-junior", "rubric": "grounding", '
            '"score": 2, "reasons": ["a", "b"], "failed_rules": ["invented_metric"], '
            '"status": "ok"}'
        )
        out = _normalize_eval_record(v1_record)
        assert out["score"] == 2.0
        assert out["schema_version"] == 1
        assert out["failed_rules"] == ["invented_metric"]


class TestGroundednessComposite:
    """The reportable groundedness signal is L0-only by default and gracefully
    enriches to L0+L1+L2 only when --grounding-signals produced real scores."""

    def test_l0_only_by_default(self):
        from evals.runner import _groundedness_composite

        block = _groundedness_composite({"fabricated_specifics_rate": 0.2, "flagged": 3})
        assert block["layers"] == ["L0"]
        assert block["fabricated_specifics_rate"] == 0.2
        assert block["flagged_count"] == 3
        # score is a 0–5 projection: 5 * (1 - 0.2) = 4.0
        assert block["score"] == 4.0
        # No L1/L2 keys until enriched.
        assert "mean_entailment" not in block

    def test_clean_l0_scores_five(self):
        from evals.runner import _groundedness_composite

        block = _groundedness_composite({"fabricated_specifics_rate": 0.0, "flagged": 0})
        assert block["score"] == 5.0

    def test_enrich_adds_l1_l2_in_place(self):
        from evals.runner import _enrich_groundedness, _groundedness_composite

        block = _groundedness_composite({"fabricated_specifics_rate": 0.0, "flagged": 0})
        _enrich_groundedness(
            block,
            {
                "bullet_count": 10,
                "nli_summary": {"mean_entailment": 0.82, "contradiction_count": 1},
                "minicheck_summary": {"mean_score": 0.74, "low_score_count": 2},
            },
        )
        assert block["layers"] == ["L0", "L1", "L2"]
        assert block["mean_entailment"] == 0.82
        assert block["contradiction_count"] == 1
        assert block["mean_minicheck"] == 0.74
        # unsupported_claim_rate = low_score_count / bullet_count = 2 / 10
        assert block["unsupported_claim_rate"] == 0.2

    def test_enrich_handles_zero_bullets(self):
        from evals.runner import _enrich_groundedness, _groundedness_composite

        block = _groundedness_composite({"fabricated_specifics_rate": 0.0, "flagged": 0})
        _enrich_groundedness(
            block,
            {
                "bullet_count": 0,
                "nli_summary": {"mean_entailment": 0.0, "contradiction_count": 0},
                "minicheck_summary": {"mean_score": 0.0, "low_score_count": 0},
            },
        )
        assert block["unsupported_claim_rate"] == 0.0


class TestRunSuite:
    """The importable core extracted from main(): structured args + an optional
    progress sartor + an EvalRunResult return. main() is now a thin wrapper, and
    the no-flag default path forwards nothing extra (the byte-identical guarantee)."""

    def test_main_delegates_to_run_suite(self, monkeypatch):
        """main() parses flags and forwards them to run_suite, returning its
        exit_code — the thin-wrapper contract."""
        import evals.runner as runner
        from evals.runner import EvalRunResult

        captured: dict = {}

        def fake_run_suite(**kwargs):
            captured.update(kwargs)
            return EvalRunResult(
                exit_code=2,
                out_path=None,
                n_pass=1,
                n_fail=1,
                regressions=[],
                improvements=[],
            )

        monkeypatch.setattr(runner, "run_suite", fake_run_suite)
        rc = runner.main(["--suite", "anchor", "--subset", "smoke"])
        assert rc == 2
        assert captured["suite"] == "anchor"
        assert captured["subset"] == "smoke"
        assert captured["fixture_name"] is None
        assert captured["grounding_signals"] is False

    def test_main_default_path_forwards_no_overrides(self, monkeypatch):
        """The no-flag default path injects nothing — the byte-identical guarantee
        at the wrapper boundary (run_suite's default path is itself unchanged)."""
        import evals.runner as runner
        from evals.runner import EvalRunResult

        captured: dict = {}

        def fake_run_suite(**kwargs):
            captured.update(kwargs)
            return EvalRunResult(0, None, 0, 0, [], [])

        monkeypatch.setattr(runner, "run_suite", fake_run_suite)
        rc = runner.main([])
        assert rc == 0
        assert captured["suite"] == "synthetic"
        assert captured["subset"] == "full"
        assert captured["seed_data"] is None
        assert captured["prompt_overrides_map"] == {}
        assert captured["grounding_signals"] is False

    def _stub_pipeline(self, runner, monkeypatch, tmp_path):
        """Stub every paid call + isolate baseline lookup to tmp_path. The real
        deterministic pipeline (parse/keywords/metrics) still runs on the committed
        synthetic fixtures, so no API calls and no real baseline interference."""
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
        monkeypatch.setattr(
            runner,
            "generate",
            lambda *a, **k: {
                "resume_content": "- Led a project\n- Built a system",
                "cover_letter_content": "Dear team,",
            },
        )
        monkeypatch.setattr(
            runner,
            "_grade",
            lambda *a, **k: {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"},
        )
        monkeypatch.setattr(
            runner,
            "_score_distinctiveness",
            lambda *a, **k: {"score": 4.0, "summary": "ok"},
        )

    def test_run_suite_writes_records_with_stubbed_llm(self, tmp_path, monkeypatch):
        """run_suite writes the same JSONL records and returns a populated
        EvalRunResult. No paid calls (every LLM hop stubbed)."""
        import evals.runner as runner
        from evals.runner import EvalRunResult, run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path)
        result = run_suite(
            suite="synthetic",
            subset="smoke",
            out_dir=tmp_path,
            client=MagicMock(),
        )
        assert isinstance(result, EvalRunResult)
        assert result.out_path is not None and result.out_path.exists()
        assert result.candidate_version is None
        # 3 committed synthetic fixtures, grounding rubric each, all stub-passing.
        assert result.n_pass == 3
        assert result.n_fail == 0
        assert result.exit_code == 0

        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        grounding = [r for r in lines if r.get("rubric") == "grounding"]
        assert len(grounding) == 3
        assert all(r["status"] == "ok" and r["score"] == 4.5 for r in grounding)
        # Default (no-override) path stamps the real PROMPT_VERSION, not candidate:<hash>.
        assert all(not str(r["prompt_version"]).startswith("candidate:") for r in grounding)

    def test_run_suite_progress_sartor_fires(self, tmp_path, monkeypatch):
        """The optional progress sartor is invoked with (event, payload) at the
        documented milestones; the default (None) path stays a no-op."""
        import evals.runner as runner
        from evals.runner import run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path)
        events: list[str] = []
        run_suite(
            suite="synthetic",
            subset="smoke",
            fixture_name="sre-mid-level",
            out_dir=tmp_path,
            client=MagicMock(),
            progress=lambda ev, payload: events.append(ev),
        )
        for milestone in (
            "fixture_start",
            "analyzing",
            "generating",
            "rubric_done",
            "fixture_done",
        ):
            assert milestone in events, f"missing progress event: {milestone}"

    def test_run_suite_unknown_fixture_raises(self, tmp_path, monkeypatch):
        """An unknown --fixture surfaces as FileNotFoundError for the caller to map
        (main → exit 1; the route → 4xx) rather than a half-written run."""
        import evals.runner as runner
        from evals.runner import run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path)
        with pytest.raises(FileNotFoundError):
            run_suite(fixture_name="does-not-exist", out_dir=tmp_path, client=MagicMock())


class TestGroundingSignalsDegrade:
    """Fix (2026-07-08): a grounding-scorer exception must degrade the fixture
    to un-scored and continue the run, never abort it — run_suite now honors
    the same contract as evals/bootstrap.py's build_bootstrap_document (EV-2,
    "grounding failure degrades to un-scored, never discards paid work").
    Before this fix, run_grounding_signals(...) sat outside the per-fixture
    try/except, so a scorer exception (e.g. transformers' offload_folder
    error on a low-RAM host) aborted the ENTIRE run via the worker-thread
    handler in blueprints/diagnostics.py — this exact scenario had zero
    coverage across the existing suite.
    """

    def _stub_pipeline(self, runner, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
        monkeypatch.setattr(
            runner,
            "generate",
            lambda *a, **k: {
                "resume_content": "- Led a project\n- Built a system",
                "cover_letter_content": "Dear team,",
            },
        )
        monkeypatch.setattr(
            runner,
            "_grade",
            lambda *a, **k: {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"},
        )
        monkeypatch.setattr(
            runner,
            "_score_distinctiveness",
            lambda *a, **k: {"score": 4.0, "summary": "ok"},
        )

    def test_scorer_exception_degrades_to_unscored_and_continues(self, tmp_path, monkeypatch):
        import evals.grounding_signals as grounding_signals_module
        import evals.runner as runner
        from evals.runner import run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path)

        def _raise(*_a, **_k):
            raise RuntimeError(
                "The current device_map had weights offloaded to the disk. "
                "Please provide an offload_folder for them."
            )

        monkeypatch.setattr(grounding_signals_module, "run_grounding_signals", _raise)

        events: list[tuple[str, dict]] = []
        result = run_suite(
            suite="synthetic",
            subset="smoke",
            out_dir=tmp_path,
            client=MagicMock(),
            grounding_signals=True,
            progress=lambda ev, payload: events.append((ev, payload)),
        )

        # The run completes to the end — paid analyze/clarify/generate/judge
        # work is never discarded because the scorer blew up.
        assert result.n_pass == 3
        assert result.n_fail == 0
        assert result.exit_code == 0

        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        grounding = [r for r in lines if r.get("rubric") == "grounding"]
        assert len(grounding) == 3
        # Records are written un-scored on the grounding_signals axis; the
        # judge-graded score/status are completely untouched by the failure.
        assert all(r["status"] == "ok" and r["score"] == 4.5 for r in grounding)
        assert all(r["grounding_signals"] is None for r in grounding)

        # A "warning" progress event fired per fixture instead of the run
        # raising out of run_suite (which would abort the worker thread in
        # blueprints/diagnostics.py's /api/eval/run route).
        warnings = [p for ev, p in events if ev == "warning"]
        assert len(warnings) == 3
        assert all("Grounding signals failed" in w.get("message", "") for w in warnings)

    def test_scorer_success_path_unaffected(self, tmp_path, monkeypatch):
        """Sanity companion: when the scorer succeeds, grounding_signals_data
        still lands on every record and no warning fires (the try/except/else
        split didn't disturb the happy path)."""
        import evals.grounding_signals as grounding_signals_module
        import evals.runner as runner
        from evals.runner import run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path)

        fake_signals = {
            "bullet_count": 2,
            "nli": [],
            "nli_summary": {"mean_entailment": 0.9, "contradiction_count": 0},
            "minicheck": [],
            "minicheck_summary": {"mean_score": 0.85, "low_score_count": 0},
        }
        monkeypatch.setattr(
            grounding_signals_module, "run_grounding_signals", lambda *a, **k: fake_signals
        )

        events: list[str] = []
        result = run_suite(
            suite="synthetic",
            subset="smoke",
            out_dir=tmp_path,
            client=MagicMock(),
            grounding_signals=True,
            progress=lambda ev, payload: events.append(ev),
        )
        assert result.n_fail == 0
        assert "warning" not in events

        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        grounding = [r for r in lines if r.get("rubric") == "grounding"]
        assert all(r["grounding_signals"] == fake_signals for r in grounding)


class TestAssembleMode:
    """F-11 (2026-07 UX review) — ``--mode assemble`` drives the SAME Compose ->
    freeze -> assemble path corpus-mode ``/api/generate`` uses (instead of the LLM
    ``generate()`` fallback), so the harness scores the deterministically ASSEMBLED
    résumé body users actually download, not an LLM-authored stand-in."""

    def test_requires_seed(self):
        """mode='assemble' without seed_data is a config error, raised before any
        paid call — mirrors the unknown-prompt-override-name ValueError contract."""
        from evals.runner import run_suite

        with pytest.raises(ValueError, match="requires --seed"):
            run_suite(mode="assemble", seed_data=None, client=MagicMock())

    def test_unknown_mode_rejected(self):
        from evals.runner import run_suite

        with pytest.raises(ValueError, match="Unknown mode"):
            run_suite(mode="bogus", client=MagicMock())

    def _seed_corpus(self, db_session):
        """Insert one real candidate (experience + official title + 2 active
        bullets + 1 active SummaryItem), then export it to a seed dict via the
        SAME exporter --seed corpus-backed runs consume. Returns (seed_data,
        experience_id, bullet1_id, bullet2_id, summary_item_id)."""
        from db.models import Bullet, Candidate, Experience, ExperienceTitle, SummaryItem
        from scripts.export_corpus_seed import export_seed

        c = Candidate(
            username="casey_assemble",
            name="Casey Rivera",
            email="casey@example.com",
            profile_text="Fallback text — must not win; a SummaryItem exists.",
        )
        db_session.add(c)
        db_session.flush()

        e = Experience(
            candidate_id=c.id,
            company="Polaris",
            location="Remote",
            start_date="2022-09",
            end_date=None,
            display_order=0,
            summary="Backend.",
        )
        db_session.add(e)
        db_session.flush()

        db_session.add(
            ExperienceTitle(
                experience_id=e.id,
                title="Senior SRE",
                is_official=1,
                truthful_enough_to_use=1,
                is_pending_review=0,
                source="official",
            )
        )
        b1 = Bullet(
            experience_id=e.id,
            text="Cut p99 latency 40% by redesigning the caching tier.",
            display_order=0,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
            pattern_kind=None,
            has_outcome=1,
        )
        b2 = Bullet(
            experience_id=e.id,
            text="Ran incident response for the Kafka pipeline fleet.",
            display_order=1,
            is_active=1,
            is_pending_review=0,
            source="primary:r.md",
            pattern_kind=None,
            has_outcome=0,
        )
        db_session.add_all([b1, b2])
        s1 = SummaryItem(
            candidate_id=c.id,
            text="Platform SRE who ships reliability wins under real production load.",
            display_order=0,
            is_active=1,
        )
        db_session.add(s1)
        db_session.flush()
        db_session.commit()

        seed = export_seed(db_session, candidate_username="casey_assemble")
        return seed, e.id, b1.id, b2.id, s1.id

    def test_assemble_mode_scores_the_deterministic_frozen_composition(
        self, db_session, tmp_path, monkeypatch
    ):
        """The résumé text graded in assemble mode is BYTE-IDENTICAL to
        freeze_approved_composition(...) -> json_resume_to_markdown(...) — the exact
        product resolver + serializer — not an LLM-authored string. analyzer.generate()
        is never called (patched to raise); the cover letter stays a real LLM call
        (Sonnet parity with the legacy generate() default); the record carries
        eval_mode="assemble" and is exempt from baseline-regression comparison."""
        import evals.runner as runner
        from corpus_to_json_resume import freeze_approved_composition
        from evals.runner import run_suite
        from evals.seed_import import seeded_session
        from json_resume import json_resume_to_markdown

        seed_data, exp_id, b1_id, b2_id, summary_id = self._seed_corpus(db_session)

        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})

        def _generate_must_not_be_called(*a, **k):
            raise AssertionError("analyzer.generate() must not run in mode='assemble'")

        monkeypatch.setattr(runner, "generate", _generate_must_not_be_called)
        monkeypatch.setattr(
            runner,
            "recommend_bullets",
            lambda *a, **k: {
                "recommendations": [
                    {"experience_id": exp_id, "bullet_ids": [b1_id, b2_id], "rationale": "fit"}
                ]
            },
        )
        monkeypatch.setattr(
            runner,
            "recommend_summaries",
            lambda *a, **k: {
                "recommendation": {"summary_item_id": summary_id, "rationale": "fit"},
                "alternates": [],
            },
        )

        cover_letter_calls = {"n": 0}

        def _fake_cover_letter(client, ctx, analysis, resume_content, username="", run_id=""):
            cover_letter_calls["n"] += 1
            return {"cover_letter_content": "Dear hiring manager, ..."}

        import blueprints.generation as bgen

        monkeypatch.setattr(bgen, "generate_cover_letter_against_resume", _fake_cover_letter)

        captured_payloads: list[dict] = []

        def _capture_grade(client, rubric_path, payload):
            captured_payloads.append(payload)
            return {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"}

        monkeypatch.setattr(runner, "_grade", _capture_grade)
        monkeypatch.setattr(
            runner, "_score_distinctiveness", lambda *a, **k: {"score": 4.0, "summary": "ok"}
        )

        result = run_suite(
            suite="synthetic",
            subset="smoke",
            fixture_name="sre-mid-level",
            seed_data=seed_data,
            mode="assemble",
            out_dir=tmp_path,
            client=MagicMock(),
        )
        assert result.exit_code == 0
        assert result.n_fail == 0
        assert cover_letter_calls["n"] == 1  # cover letter stays a real LLM call
        assert len(captured_payloads) == 1  # exactly one grounding-rubric grade call
        graded_resume = captured_payloads[0]["generated_resume"]

        # Independently re-derive the expected text via the SAME product resolver +
        # serializer, against a FRESH import of the identical seed — proves the
        # assembled artifact IS freeze_approved_composition's output, not a
        # generate()-shaped stand-in.
        with seeded_session(seed_data) as (session2, username2):
            from db.models import Candidate

            candidate2 = session2.query(Candidate).filter_by(username=username2).first()
            expected_doc = freeze_approved_composition(
                session2,
                candidate2.id,
                application_id=999,
                context_data={
                    "llm_recommendations": {
                        str(exp_id): {"bullet_ids": [b1_id, b2_id], "rationale": "fit"}
                    },
                    "llm_summary_recommendation": {
                        "recommendation": {"summary_item_id": summary_id, "rationale": "fit"},
                        "alternates": [],
                    },
                },
            )
        expected_md = json_resume_to_markdown(expected_doc)
        assert graded_resume == expected_md
        assert "Cut p99 latency 40%" in graded_resume

        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        grounding = [r for r in lines if r.get("rubric") == "grounding"]
        assert len(grounding) == 1
        assert grounding[0]["eval_mode"] == "assemble"
        # F-11: assemble-mode scores are never compared against the generate-mode
        # baseline_v1.json population.
        assert grounding[0]["baseline_comparison"] is None

    def test_generate_mode_default_never_touches_assemble_helpers(self, tmp_path, monkeypatch):
        """mode='generate' (the default) is the byte-identical historical path: it
        never calls recommend_bullets / recommend_summaries / freeze_approved_composition
        — patched here to raise, proving the default path never reaches them — and
        every record carries eval_mode="generate"."""
        import evals.runner as runner
        from evals.runner import run_suite

        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
        monkeypatch.setattr(
            runner,
            "generate",
            lambda *a, **k: {
                "resume_content": "- Led a project\n- Built a system",
                "cover_letter_content": "Dear team,",
            },
        )
        monkeypatch.setattr(
            runner,
            "_grade",
            lambda *a, **k: {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"},
        )
        monkeypatch.setattr(
            runner, "_score_distinctiveness", lambda *a, **k: {"score": 4.0, "summary": "ok"}
        )

        def _must_not_be_called(*a, **k):
            raise AssertionError("mode='generate' must not touch the assemble-mode helpers")

        monkeypatch.setattr(runner, "recommend_bullets", _must_not_be_called)
        monkeypatch.setattr(runner, "recommend_summaries", _must_not_be_called)
        monkeypatch.setattr(runner, "freeze_approved_composition", _must_not_be_called)

        result = run_suite(suite="synthetic", subset="smoke", out_dir=tmp_path, client=MagicMock())
        assert result.exit_code == 0
        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        grounding = [r for r in lines if r.get("rubric") == "grounding"]
        assert len(grounding) == 3
        assert all(r["eval_mode"] == "generate" for r in grounding)


class TestEvalGateGuard:
    """PX-13 — guard the eval-smoke gate's exit-2 failure path so it can't silently rot.

    The gate is a real machine gate: ``run_suite`` returns process exit-code 2 on
    EITHER a sub-``PASS_THRESHOLD`` rubric fail OR a regression past
    ``REGRESSION_DELTA`` vs the committed baseline
    (``evals/runner.py``: ``exit_code = 0 if (n_fail == 0 and not regressions) else 2``).
    These two LLM-free meta-tests pin BOTH exit-2 contributors, so a future change that
    quietly softens the gate (e.g. dropping ``not regressions``, or loosening the
    threshold) fails here in the default ``pytest`` run. See the
    "Do-not-regress (machine-enforced)" note in ``evals/README.md``.
    """

    def _stub_pipeline(self, runner, monkeypatch, tmp_path, grade_score):
        """Mirror of ``TestRunSuite._stub_pipeline`` with the judge score as a
        parameter, so each arm can drive a specific (fixture × grounding) result.
        Every paid call is stubbed; the real deterministic pipeline still runs on the
        committed synthetic fixtures; the baseline lookup is isolated to ``tmp_path``."""
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
        monkeypatch.setattr(
            runner,
            "generate",
            lambda *a, **k: {
                "resume_content": "- Led a project\n- Built a system",
                "cover_letter_content": "Dear team,",
            },
        )
        monkeypatch.setattr(
            runner,
            "_grade",
            lambda *a, **k: {
                "score": grade_score,
                "reasons": [],
                "failed_rules": [],
                "status": "ok",
            },
        )
        monkeypatch.setattr(
            runner,
            "_score_distinctiveness",
            lambda *a, **k: {"score": 4.0, "summary": "ok"},
        )

    def test_subthreshold_score_forces_exit_2(self, tmp_path, monkeypatch):
        """Threshold arm: a grounding score below ``PASS_THRESHOLD`` (4.0) fails the
        gate with exit-code 2 via ``n_fail`` — no baseline involved."""
        import evals.runner as runner
        from evals.runner import run_suite

        self._stub_pipeline(runner, monkeypatch, tmp_path, grade_score=3.5)
        result = run_suite(
            suite="synthetic",
            subset="smoke",
            out_dir=tmp_path,
            client=MagicMock(),
        )
        # 3 committed synthetic fixtures × grounding, all below threshold.
        assert result.n_fail == 3
        assert result.n_pass == 0
        assert result.regressions == []  # no baseline seeded → nothing to regress against
        assert result.exit_code == 2

    def test_regression_past_delta_forces_exit_2(self, tmp_path, monkeypatch):
        """Regression arm: a grounding score that PASSES the absolute threshold
        (4.2 >= 4.0, so ``n_fail == 0``) but drops past ``REGRESSION_DELTA`` (0.5)
        below the committed baseline mean (4.8) STILL fails the gate with exit-code 2,
        via ``regressions``. This is the exact "grounding drop near/past 0.5 vs the
        committed baseline" the PX-13 prescription names."""
        import evals.runner as runner
        from evals.runner import run_suite

        baseline = {
            "schema_version": 3,
            "baseline_id": "px13-meta-test",
            "prompt_version": "px13-test",
            "fixtures": {
                name: {"grounding": {"mean": 4.8, "stdev": 0.0, "n": 5, "min": 4.8, "max": 4.8}}
                for name in ("data-scientist-junior", "pm-senior", "sre-mid-level")
            },
        }
        (tmp_path / "baseline_v1.json").write_text(json.dumps(baseline), encoding="utf-8")

        self._stub_pipeline(runner, monkeypatch, tmp_path, grade_score=4.2)
        result = run_suite(
            suite="synthetic",
            subset="smoke",
            out_dir=tmp_path,
            client=MagicMock(),
        )
        # 4.2 >= PASS_THRESHOLD → zero threshold fails; 4.8 - 4.2 = 0.6 > REGRESSION_DELTA.
        assert result.n_fail == 0
        assert len(result.regressions) == 3
        assert result.exit_code == 2


class TestGroundingSignalsAnnotationPersistence:
    """RH-1 (2026-07 e2e-run-health-review): grounding signals computed during a
    ``--suite real`` eval run land in every JSONL result record but, before this
    fix, never made it back to the fixture's ``annotations.json`` — the
    ground-truth file the Annotate tab edits (the SAME
    ``evals/fixtures/real/<slug>/`` directory ``--suite real --fixture <slug>``
    reads ``jd.txt``/``expected.json`` from — ``evals/fixtures/real`` ==
    ``blueprints.diagnostics``'s ``ANNOTATION_ROOT``).

    Drives the REAL ``run_suite`` (every LLM hop + the grounding scorer
    STUBBED — the DeBERTa/MiniCheck ``[eval-grounding]`` extras are heavy
    CPU-bound models not assumed installed in a dev worktree) against a SCRATCH
    fixture this test creates under a monkeypatched ``FIXTURES_DIR`` — never the
    owner's e2e clone or ``evals/fixtures/real/robert-bootstrap/``.
    """

    _BULLET_TEXT = "Cut p99 latency 40% by redesigning the caching tier."

    def _write_scratch_fixture(self, tmp_path: Path, slug: str) -> Path:
        fdir = tmp_path / "real" / slug
        fdir.mkdir(parents=True)
        (fdir / "jd.txt").write_text("Senior SRE role.", encoding="utf-8")
        (fdir / "expected.json").write_text(
            json.dumps(
                {
                    "candidate_name": "Casey Rivera",
                    "must_keywords": [],
                    "forbidden_inventions": [],
                    "min_grounding_score": 4.0,
                    "min_keyword_coverage_score": 4.0,
                    "min_ats_format_score": 4.0,
                    "min_tone_score": 3.0,
                    "min_clarification_quality_score": 4.0,
                    "notes": "scratch fixture (RH-1 test)",
                }
            ),
            encoding="utf-8",
        )
        return fdir

    def _annotations_doc(self) -> dict:
        return {
            "annotation_schema_version": 1,
            "bootstrap_source": "scratch",
            "candidate_username": "casey_rh1",
            "prompt_version": "2026-07-06.3",
            "bullets": [
                {
                    "cluster_index": 0,
                    "representative": self._BULLET_TEXT,
                    "jd_files": ["jd.txt"],
                    "size": 1,
                    "nli_entailment_score": None,
                    "nli_contradiction_flag": None,
                    "minicheck_grounding_score": None,
                    "verdict": "keep",
                    "failed_rules": [],
                    "note": "human note — must survive the patch",
                    "should_omit": False,
                    "honest_rewrite": None,
                    "forbidden_pattern": None,
                }
            ],
            "skills": [],
            "clarification_ratings": [],
            "min_scores": {},
            "notes": "",
        }

    def _stub_pipeline(self, runner, monkeypatch, resume_content):
        monkeypatch.setattr(runner, "analyze", lambda *a, **k: {"overall_strategy": "ok"})
        monkeypatch.setattr(runner, "clarify", lambda *a, **k: {"questions": [], "reasoning": ""})
        monkeypatch.setattr(
            runner,
            "generate",
            lambda *a, **k: {
                "resume_content": resume_content,
                "cover_letter_content": "Dear team,",
            },
        )
        monkeypatch.setattr(
            runner,
            "_grade",
            lambda *a, **k: {"score": 4.5, "reasons": [], "failed_rules": [], "status": "ok"},
        )
        monkeypatch.setattr(
            runner, "_score_distinctiveness", lambda *a, **k: {"score": 4.0, "summary": "ok"}
        )

    def test_persists_grounding_scores_by_bullet_text(self, db_session, tmp_path, monkeypatch):
        import evals.grounding_signals as grounding_signals_module
        import evals.runner as runner
        from db.models import Candidate
        from evals.runner import run_suite
        from scripts.export_corpus_seed import export_seed

        db_session.add(Candidate(username="casey_rh1", name="Casey Rivera"))
        db_session.commit()
        seed_data = export_seed(db_session, candidate_username="casey_rh1")

        slug = "scratch-rh1"
        self._write_scratch_fixture(tmp_path, slug)
        ann_path = tmp_path / "real" / slug / "annotations.json"
        ann_path.write_text(json.dumps(self._annotations_doc()), encoding="utf-8")

        monkeypatch.setattr(runner, "FIXTURES_DIR", tmp_path)
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        self._stub_pipeline(
            runner,
            monkeypatch,
            f"- {self._BULLET_TEXT}\n- An unrelated, unmatched bullet.\n",
        )

        def _fake_scorer(resume_md, source_texts):
            """STUBBED scorer — proves the persistence SEAM, not the DeBERTa/
            MiniCheck models themselves (covered separately, gated on the
            [eval-grounding] extras, by tests/test_grounding_signals.py)."""
            bullets = [
                ln[2:].strip() for ln in resume_md.splitlines() if ln.strip().startswith("- ")
            ]
            return {
                "bullet_count": len(bullets),
                "nli": [
                    {"bullet": b, "nli_entailment_score": 0.93, "nli_contradiction_flag": False}
                    for b in bullets
                ],
                "nli_summary": {"mean_entailment": 0.93, "contradiction_count": 0},
                "minicheck": [{"bullet": b, "minicheck_grounding_score": 0.81} for b in bullets],
                "minicheck_summary": {"mean_score": 0.81, "low_score_count": 0},
            }

        monkeypatch.setattr(grounding_signals_module, "run_grounding_signals", _fake_scorer)

        result = run_suite(
            suite="real",
            subset="smoke",
            fixture_name=slug,
            seed_data=seed_data,
            grounding_signals=True,
            out_dir=tmp_path,
            client=MagicMock(),
        )
        assert result.n_fail == 0
        assert result.out_path is not None and result.out_path.exists()

        # The eval RESULT record carries the grounding signals (already worked
        # before this fix)...
        lines = [
            json.loads(ln)
            for ln in result.out_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        assert lines[0]["grounding_signals"]["bullet_count"] == 2

        # ...and now so does the fixture's annotations.json (the RH-1 fix): the
        # matching bullet is patched by TEXT, the human verdict/note untouched,
        # and no spurious new item was invented for the unmatched 2nd bullet.
        patched = json.loads(ann_path.read_text(encoding="utf-8"))
        assert len(patched["bullets"]) == 1
        item = patched["bullets"][0]
        assert item["nli_entailment_score"] == 0.93
        assert item["minicheck_grounding_score"] == 0.81
        assert item["verdict"] == "keep"
        assert item["note"] == "human note — must survive the patch"

    def test_no_annotations_json_is_a_silent_noop(self, db_session, tmp_path, monkeypatch):
        """When the fixture has no annotations.json (most --suite real fixtures,
        e.g. a freshly-collated one before any grounding run), the RH-1 hook must
        not create one or raise — it only patches an EXISTING file."""
        import evals.grounding_signals as grounding_signals_module
        import evals.runner as runner
        from db.models import Candidate
        from evals.runner import run_suite
        from scripts.export_corpus_seed import export_seed

        db_session.add(Candidate(username="casey_rh1b", name="Casey Rivera"))
        db_session.commit()
        seed_data = export_seed(db_session, candidate_username="casey_rh1b")

        slug = "scratch-rh1b"
        self._write_scratch_fixture(tmp_path, slug)
        # Deliberately NO annotations.json written.

        monkeypatch.setattr(runner, "FIXTURES_DIR", tmp_path)
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        self._stub_pipeline(runner, monkeypatch, f"- {self._BULLET_TEXT}\n")
        monkeypatch.setattr(
            grounding_signals_module,
            "run_grounding_signals",
            lambda resume_md, source_texts: {
                "bullet_count": 1,
                "nli": [
                    {
                        "bullet": self._BULLET_TEXT,
                        "nli_entailment_score": 0.9,
                        "nli_contradiction_flag": False,
                    }
                ],
                "nli_summary": {"mean_entailment": 0.9, "contradiction_count": 0},
                "minicheck": [{"bullet": self._BULLET_TEXT, "minicheck_grounding_score": 0.8}],
                "minicheck_summary": {"mean_score": 0.8, "low_score_count": 0},
            },
        )

        result = run_suite(
            suite="real",
            subset="smoke",
            fixture_name=slug,
            seed_data=seed_data,
            grounding_signals=True,
            out_dir=tmp_path,
            client=MagicMock(),
        )
        assert result.n_fail == 0
        assert not (tmp_path / "real" / slug / "annotations.json").exists()


class TestZeroResultGuard:
    """RH-2 (2026-07 e2e-run-health-review): a run whose fixture loop writes ZERO
    result records must fail loudly + clean up any empty file, not report success
    against a silent 0-byte results file — the ``20260709_014042Z.jsonl`` finding."""

    def test_all_fixtures_failing_to_load_raises_and_cleans_up(self, tmp_path, monkeypatch):
        import evals.runner as runner
        from evals.runner import run_suite

        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        monkeypatch.setattr(runner, "BASELINE_JSON", tmp_path / "baseline_v1.json")
        monkeypatch.setattr(runner, "FIXTURES_DIR", tmp_path)

        # A "real" fixture directory that exists but has no jd.txt/expected.json —
        # _load_fixture raises for it, caught by the per-fixture try/except
        # (continue), so the loop completes having written NOTHING — exactly the
        # silent-empty-results-file scenario.
        (tmp_path / "real" / "broken-fixture").mkdir(parents=True)

        with pytest.raises(RuntimeError, match="zero result records"):
            run_suite(
                suite="real",
                subset="smoke",
                fixture_name="broken-fixture",
                out_dir=tmp_path,
                client=MagicMock(),
            )

        # No 0-byte (or any) results file left behind under out_dir.
        assert list(tmp_path.glob("*.jsonl")) == []

    def test_main_maps_zero_result_runtimeerror_to_exit_1(self, monkeypatch):
        """main() surfaces the RH-2 guard's RuntimeError as a clean exit 1
        (logged), not an unhandled traceback — mirrors the FileNotFoundError /
        ValueError mapping already in place for run_suite's other failure modes."""
        import evals.runner as runner

        def _raise(**kwargs):
            raise RuntimeError("Eval run wrote zero result records (suite='real')")

        monkeypatch.setattr(runner, "run_suite", _raise)
        rc = runner.main(["--suite", "real", "--fixture", "broken-fixture"])
        assert rc == 1
