"""callback. eval harness.

Loads synthetic and/or real fixtures, runs the full analyze + generate
pipeline against each, dispatches per-rubric grading via Claude Haiku,
and writes per-grading JSONL records to evals/results/{timestamp}.jsonl.

Usage:
    python evals/runner.py --suite synthetic
    python evals/runner.py --suite synthetic --subset smoke
    python evals/runner.py --suite anchor --subset smoke
    python evals/runner.py --suite real
    python evals/runner.py --fixture sre-mid-level

Exit code: 0 if every grading scored >= 4, 2 if any failed, 1 on
configuration error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# Make project root importable so this script works whether invoked as
# `python evals/runner.py` or `python -m evals.runner`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer import (  # noqa: E402
    PROMPT_VERSION,
    analyze,
    clarify,
    clarify_iteration,
    generate,
)
from hardening import (  # noqa: E402
    ContextSet,
    build_context_set,
    check_ats_format,
    compute_call_cost,
    compute_grounding_overlap,
    compute_keyword_overlap,
    compute_specificity_density,
    compute_verb_diversity,
    extract_keywords,
)
from parser import parse_resume  # noqa: E402

# Same JSONL telemetry sink analyzer.py writes to — read here to compute
# per-eval cost by tailing entries written during this run.
LLM_LOG_PATH = PROJECT_ROOT / "logs" / "llm_calls.jsonl"

EVALS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVALS_DIR / "fixtures"
RUBRICS_DIR = EVALS_DIR / "rubrics"
RESULTS_DIR = EVALS_DIR / "results"
ANCHOR_DIR = EVALS_DIR / "anchors" / "anchor-v1"

MODEL_SNAPSHOTS = {
    "sonnet": "claude-sonnet-4-6",
    "haiku_judge": "claude-haiku-4-5-20251001",
}

JUDGE_MODEL = "claude-haiku-4-5-20251001"
PASS_THRESHOLD = 4.0
SCORE_MAX = 5.0
# Bumped when the eval-result JSONL shape changes. Old records (no field) are
# treated as schema_version=1 with int scores; the dashboard normalizes both.
SCHEMA_VERSION = 3

# Regression-alert sensitivity: any (fixture, rubric) score that drops by
# more than this many points vs the previous run is logged as a regression.
# Default 0.5 leaves room for normal judge variance (Haiku is non-deterministic
# and can move scores by up to ~0.5 on identical inputs across runs) while
# still surfacing genuine prompt-induced drops. Override with REGRESSION_DELTA
# env var if your tuning loop needs tighter or looser bands.
REGRESSION_DELTA = float(os.environ.get("REGRESSION_DELTA", "0.5"))

logger = logging.getLogger(__name__)


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        key_file = PROJECT_ROOT / ".api_key"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set and no .api_key file found at project root"
        )
    return anthropic.Anthropic(api_key=api_key)


def _load_fixture(fixture_dir: Path) -> dict:
    """Load a fixture: jd.txt + resume.{md|docx|pdf} + expected.json."""
    jd = (fixture_dir / "jd.txt").read_text(encoding="utf-8")

    resume_path = None
    for ext in (".md", ".docx", ".pdf"):
        candidate = fixture_dir / f"resume{ext}"
        if candidate.exists():
            resume_path = candidate
            break
    if resume_path is None:
        raise FileNotFoundError(f"No resume file in fixture {fixture_dir.name}")

    expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))
    h = hashlib.sha256()
    h.update((fixture_dir / "jd.txt").read_bytes())
    h.update(resume_path.read_bytes())
    h.update((fixture_dir / "expected.json").read_bytes())
    return {
        "name": fixture_dir.name,
        "jd": jd,
        "resume_path": resume_path,
        "expected": expected,
        "hash": h.hexdigest(),
    }


def _build_context(fixture: dict) -> ContextSet:
    """Run the same hardening pipeline app.py uses, then return a context_set."""
    parsed = parse_resume(str(fixture["resume_path"]))
    config = {
        "name": fixture["expected"].get("candidate_name", "Synthetic Candidate"),
        "skills": [],
        "certifications": [],
        "notes": "",
    }
    jd_keywords = extract_keywords(fixture["jd"])
    resume_keywords = extract_keywords(parsed["text"])
    overlap = compute_keyword_overlap(resume_keywords, jd_keywords)
    ats_warnings = check_ats_format(parsed)
    return build_context_set(
        fixture["jd"], parsed, config, profile_text="",
        jd_keywords=jd_keywords,
        resume_keywords=resume_keywords,
        keyword_overlap=overlap,
        ats_warnings=ats_warnings,
        original_resume_path=str(fixture["resume_path"]),
    )


def _post_generation_metrics(
    generated_resume: str,
    generated_cover_letter: str,
    sources: list[str],
) -> dict:
    """Compute the four post-generation deterministic metrics.

    `sources` is the list of source texts the LLM was allowed to draw from
    (primary resume + supplementals). Verb diversity and specificity density
    are computed over the generated resume only; grounding overlap is computed
    over the resume + cover letter combined (both must trace to source).
    """
    combined = f"{generated_resume}\n\n{generated_cover_letter}"
    return {
        "verb_diversity": compute_verb_diversity(generated_resume),
        "specificity_density": compute_specificity_density(generated_resume),
        "grounding_overlap": compute_grounding_overlap(combined, sources, n=3),
    }


def _eval_cost_since(t0_iso: str, fixture_name: str) -> float:
    """Sum costs of every llm_calls.jsonl record written for this fixture
    since the eval run started. Best-effort: missing log → 0.0."""
    if not LLM_LOG_PATH.exists():
        return 0.0
    needle = f"eval:{fixture_name}"
    total = 0.0
    try:
        with LLM_LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("username") != needle:
                    continue
                ts = rec.get("timestamp", "")
                if ts < t0_iso:
                    continue
                total += compute_call_cost(rec)
    except OSError as exc:
        logger.warning("eval cost rollup failed: %s", exc)
        return 0.0
    return round(total, 6)


BASELINE_JSON = RESULTS_DIR / "baseline_v1.json"


def _load_baseline_scores(out_path: Path) -> dict[tuple[str, str], dict]:
    """Return the most-recent (fixture, rubric) → record map for regression detection.

    Seeds from baseline_v1.json (schema_version 3) when present, so the alerter
    compares against the stable 5-run aggregate mean rather than the noisiest
    single prior run. Real JSONL records (timestamp > "0000…") always win.
    """
    if not RESULTS_DIR.exists():
        return {}

    baseline: dict[tuple[str, str], dict] = {}

    # Seed from the static aggregate baseline when schema_version 3 is present.
    if BASELINE_JSON.exists():
        try:
            bdata = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
            if bdata.get("schema_version") == 3:
                prompt_ver = bdata.get("prompt_version", "")
                for fixture_name, rubrics in bdata.get("fixtures", {}).items():
                    for rubric_name, stats in rubrics.items():
                        mean = stats.get("mean")
                        if mean is None:
                            continue
                        key = (fixture_name, rubric_name)
                        baseline[key] = {
                            "fixture": fixture_name,
                            "rubric": rubric_name,
                            "score": mean,
                            "prompt_version": prompt_ver,
                            "timestamp": "0000-00-00T00:00:00+00:00",
                        }
        except (OSError, json.JSONDecodeError):
            pass

    # Layer real JSONL records on top; newer timestamp wins.
    for path in sorted(RESULTS_DIR.glob("*.jsonl")):
        if path == out_path:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    fixture = rec.get("fixture")
                    rubric = rec.get("rubric")
                    score = rec.get("score")
                    if not fixture or not rubric or score is None:
                        continue
                    key = (fixture, rubric)
                    prev = baseline.get(key)
                    if prev is None or rec.get("timestamp", "") > prev.get("timestamp", ""):
                        baseline[key] = rec
        except OSError:
            continue
    return baseline


def _compute_baseline_comparison(
    fixture_name: str,
    rubric_name: str,
    score: float | None,
    bdata: dict,
) -> dict | None:
    """Return baseline mean + delta for a (fixture, rubric, score) triple.

    Returns None when baseline data is absent or the pair isn't in the baseline.
    """
    if score is None or not bdata:
        return None
    rubric_stats = bdata.get("fixtures", {}).get(fixture_name, {}).get(rubric_name, {})
    mean = rubric_stats.get("mean")
    if mean is None:
        return None
    return {
        "baseline_id": bdata.get("baseline_id", ""),
        "mean": float(mean),
        "delta": round(float(score) - float(mean), 3),
    }


def _detect_regression(
    fixture: str,
    rubric: str,
    new_score: float,
    baseline: dict[tuple[str, str], dict],
) -> dict | None:
    """Compare a fresh score against the most-recent prior score for the same
    (fixture, rubric) pair. Returns a regression record if the drop exceeds
    REGRESSION_DELTA, otherwise None.

    A negative `delta` means the score dropped (regression). Positive means
    improvement (also returned, but only delta < -REGRESSION_DELTA is logged
    as WARN).
    """
    key = (fixture, rubric)
    prev = baseline.get(key)
    if prev is None:
        return None
    prev_score = prev.get("score")
    if not isinstance(prev_score, (int, float)):
        return None
    prev_score_f = float(prev_score)
    delta = new_score - prev_score_f
    return {
        "fixture": fixture,
        "rubric": rubric,
        "new_score": new_score,
        "prev_score": prev_score_f,
        "delta": round(delta, 2),
        "prev_prompt_version": prev.get("prompt_version", ""),
        "prev_timestamp": prev.get("timestamp", ""),
        "is_regression": delta < -REGRESSION_DELTA,
        "is_improvement": delta > REGRESSION_DELTA,
    }


def _grade(client: anthropic.Anthropic, rubric_path: Path, payload: dict) -> dict:
    """Send one (rubric × payload) to Haiku and parse the JSON verdict."""
    rubric = rubric_path.read_text(encoding="utf-8")
    user_msg = (
        f"{rubric}\n\n"
        "## Material to grade\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```\n\n"
        "Output the JSON verdict now. No prose outside the JSON."
    )
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        system="You are a strict, terse grader. Output only valid JSON matching the rubric's schema.",
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = getattr(msg.content[0], "text", "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()
    try:
        grade = json.loads(raw)
    except json.JSONDecodeError:
        # Mark explicitly as judge_error so _detect_regression and the
        # summary roll-up can skip this record. Without the status the
        # caller's `grade.setdefault("status", "ok")` would label a
        # judge-side malformation as a successful 0-score grading,
        # which fires a false-positive regression WARN against the
        # baseline.
        return {
            "score": 0,
            "reasons": ["judge response was not valid JSON"],
            "raw": raw,
            "status": "judge_error",
        }
    # Force-float at the boundary: rubrics now allow fractional scores
    # (0.0–5.0, one decimal), but Haiku still occasionally emits an integer.
    # Downstream aggregations rely on a uniform numeric type.
    if grade.get("score") is not None:
        try:
            grade["score"] = float(grade["score"])
        except (TypeError, ValueError):
            grade["score"] = 0.0
    return grade


def _select_fixtures(suite: str, single: str | None) -> list[Path]:
    """Resolve fixture directories from --suite and --fixture flags."""
    if single:
        for sub in ("synthetic", "real"):
            cand = FIXTURES_DIR / sub / single
            if cand.exists():
                return [cand]
        raise FileNotFoundError(f"Fixture not found: {single}")

    fixtures: list[Path] = []
    if suite in ("synthetic", "all"):
        synthetic_dir = FIXTURES_DIR / "synthetic"
        if synthetic_dir.exists():
            fixtures.extend(sorted(p for p in synthetic_dir.iterdir() if p.is_dir()))
    if suite in ("real", "all"):
        real_dir = FIXTURES_DIR / "real"
        if real_dir.exists():
            fixtures.extend(sorted(p for p in real_dir.iterdir() if p.is_dir()))
    if suite == "anchor":
        anchor_fixtures_dir = ANCHOR_DIR / "fixtures"
        if anchor_fixtures_dir.exists():
            fixtures.extend(sorted(p for p in anchor_fixtures_dir.iterdir() if p.is_dir()))
    if suite == "exploration":
        exploration_dir = EVALS_DIR / "exploration"
        if exploration_dir.exists():
            fixtures.extend(sorted(p for p in exploration_dir.iterdir() if p.is_dir()))
    return fixtures


def _select_rubrics(subset: str, rubrics_dir: Path | None = None) -> list[Path]:
    """Smoke = grounding only; full = every rubric.

    iteration_quality is special: it only runs against fixtures that have
    `iteration_scenarios` defined in their expected.json. The runner skips
    iteration_quality grading silently for fixtures without a scenario rather
    than emitting score=None rows that would muddy the dashboard's heatmap.

    `rubrics_dir` overrides the default RUBRICS_DIR; used by --suite anchor to
    load rubrics from the frozen anchor copy rather than the live evals/rubrics/.
    """
    dir_ = rubrics_dir or RUBRICS_DIR
    all_rubrics = sorted(dir_.glob("*.md"))
    if subset == "smoke":
        return [r for r in all_rubrics if r.stem == "grounding"]
    return all_rubrics


def _apply_simulated_edit(generated_resume: str, scenario: dict) -> tuple[str, bool]:
    """Apply a fixture-supplied edit to the freshly generated resume.

    Returns (edited_resume_text, edit_landed). edit_landed=False means the
    target substring wasn't found — the test scenario isn't aligned with
    what the LLM produced this run, and the iteration phase should skip
    (the recent_edits_summary would be empty, breaking the rubric premise).
    """
    target = scenario.get("edit_target_substring", "")
    replacement = scenario.get("edit_replacement", "")
    if not target or not replacement:
        return generated_resume, False
    if target not in generated_resume:
        return generated_resume, False
    return generated_resume.replace(target, replacement, 1), True


def _iteration_payload(
    fixture: dict,
    context: ContextSet,
    analysis: dict,
    iteration_questions: list[dict],
    iteration_reasoning: str,
    current_resume_text: str,
    current_cover_letter_text: str,
    recent_edits_summary: str,
    deterministic_signals: dict,
    prior_clarifications: list[dict],
) -> dict:
    """Build the judge payload for the iteration_quality rubric."""
    return {
        "fixture": fixture["name"],
        "expected": fixture["expected"],
        "original_resume": context["resume"]["text"],
        "current_draft_resume": current_resume_text,
        "current_draft_cover_letter": current_cover_letter_text,
        "recent_edits_summary": recent_edits_summary,
        "deterministic_signals": deterministic_signals,
        "prior_clarifications": prior_clarifications,
        "analysis": analysis,
        "iteration_questions": iteration_questions,
        "iteration_reasoning": iteration_reasoning,
    }


def _run_iteration_phase(
    *,
    client: anthropic.Anthropic,
    fixture: dict,
    context: ContextSet,
    analysis: dict,
    generate_result: dict,
    clarify_questions: list[dict],
    clarify_answers: dict,
    rubric_path: Path,
    run_id: str,
    det_metrics: dict,
    elapsed_ms: int,
    t0_iso: str,
) -> dict | None:
    """Run one simulated iteration cycle for fixtures with iteration_scenarios.

    Steps (per the plan):
      a) apply scripted edit to the freshly generated resume
      b) build a context snapshot mimicking what /api/iterate-clarify sees
      c) call clarify_iteration() with the four signal sources
      d) grade the questions against iteration_quality rubric

    Steps (d') and (e) — re-generate from the iteration context and re-grade
    against grounding/keyword_coverage — are deferred to keep the eval cost
    increase modest until iteration_quality scores are validated. See the
    2026-05-11.2 TUNING_LOG entry for the cost/value rationale.

    Returns a JSONL record dict to write, or None if the fixture has no
    iteration_scenarios (caller silently skips).
    """
    # Local imports to avoid import-time cost when the iteration phase is
    # never exercised (most fixtures don't have scenarios).
    from analyzer import LLMResponseError  # noqa: PLC0415
    from hardening import compute_iteration_signals, summarize_recent_edits  # noqa: PLC0415

    scenarios = fixture["expected"].get("iteration_scenarios") or []
    if not scenarios:
        return None  # signal: skip this rubric for this fixture

    scenario = scenarios[0]  # only the first scenario per fixture for now
    generated_resume = generate_result.get("resume_content", "")
    generated_cover = generate_result.get("cover_letter_content", "")

    edited_resume, edit_landed = _apply_simulated_edit(generated_resume, scenario)
    if not edit_landed:
        # The scripted edit_target_substring wasn't in the LLM output this
        # run. Without an edit, recent_edits_summary is empty and the rubric
        # premise breaks. Emit a pipeline_error row so the dashboard surfaces
        # the misalignment rather than silently degrading the iteration eval.
        return {
            "schema_version": SCHEMA_VERSION,
            "score_max": SCORE_MAX,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "eval",
            "fixture": fixture["name"],
            "rubric": rubric_path.stem,
            "score": None,
            "reasons": [
                f"Iteration scenario edit_target_substring "
                f"{scenario.get('edit_target_substring')!r} not found in this run's "
                "generated resume — fixture scenario needs realignment with current "
                "prompts."
            ],
            "failed_rules": ["scenario_misaligned"],
            "status": "scenario_misaligned",
            "prompt_version": PROMPT_VERSION,
            "run_id": run_id,
            "deterministic_metrics": det_metrics,
            "cost_usd": _eval_cost_since(t0_iso, fixture["name"]),
            "pipeline_latency_ms": elapsed_ms,
        }

    # Build the iteration-1 context: what /api/generate would have written
    # had the user clicked GENERATE, then USE EDITS AS BASELINE on the result.
    iter_context: ContextSet = json.loads(json.dumps(context))
    iter_context["iteration"] = 1
    iter_context["last_generated_resume"] = generated_resume
    iter_context["last_generated_cover_letter"] = generated_cover
    iter_context["edited_resume_text"] = edited_resume
    # Carry forward analyze-time clarifications so the iteration clarifier
    # treats them as established truths it must build on, not re-ask.
    # cast() avoids a structural-vs-nominal mismatch when the analyzer's
    # questions arrive as plain dicts but the TypedDict expects ClarificationQuestion.
    from typing import cast as _cast  # noqa: PLC0415

    from hardening import ClarificationQuestion  # noqa: PLC0415
    if clarify_questions:
        iter_context["clarification_questions"] = _cast(
            list[ClarificationQuestion], clarify_questions
        )
    if clarify_answers:
        iter_context["clarifications"] = clarify_answers

    # Compute signals via the same helpers /api/iterate-clarify uses, so the
    # eval grades against the EXACT inputs the live route produces.
    edits_summary = summarize_recent_edits(iter_context)
    signals = compute_iteration_signals(iter_context, edited_resume)

    prior_clarifications: list[dict] = []
    for q in clarify_questions or []:
        ans = (clarify_answers.get(q.get("id", ""), "") or "").strip()
        if ans:
            prior_clarifications.append({
                "question": q.get("text", ""),
                "answer": ans,
                "kind": q.get("kind", ""),
            })

    iter_status = "ok"
    iter_questions: list[dict] = []
    iter_reasoning = ""
    iter_error: str | None = None
    try:
        iter_result = clarify_iteration(
            client=client,
            context_set=iter_context,
            analysis=analysis,
            current_resume_text=edited_resume,
            current_cover_letter_text=generated_cover,
            recent_edits_summary=edits_summary,
            deterministic_signals=signals,
            prior_clarifications=prior_clarifications,
            username=f"eval:{fixture['name']}",
            run_id=run_id,
        )
        iter_questions = iter_result.get("questions", [])
        iter_reasoning = iter_result.get("reasoning", "")
    except LLMResponseError as exc:
        iter_status = "pipeline_error"
        iter_error = exc.validation_error
    except Exception as exc:  # noqa: BLE001
        iter_status = "pipeline_error"
        iter_error = str(exc)

    if iter_status != "ok":
        return {
            "schema_version": SCHEMA_VERSION,
            "score_max": SCORE_MAX,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "eval",
            "fixture": fixture["name"],
            "rubric": rubric_path.stem,
            "score": None,
            "reasons": [f"clarify_iteration failed: {iter_error}"],
            "failed_rules": [],
            "status": iter_status,
            "prompt_version": PROMPT_VERSION,
            "run_id": run_id,
            "deterministic_metrics": det_metrics,
            "cost_usd": _eval_cost_since(t0_iso, fixture["name"]),
            "pipeline_latency_ms": elapsed_ms,
        }

    payload = _iteration_payload(
        fixture=fixture, context=context, analysis=analysis,
        iteration_questions=iter_questions, iteration_reasoning=iter_reasoning,
        current_resume_text=edited_resume,
        current_cover_letter_text=generated_cover,
        recent_edits_summary=edits_summary,
        deterministic_signals=signals,
        prior_clarifications=prior_clarifications,
    )
    try:
        grade = _grade(client, rubric_path, payload)
        grade.setdefault("status", "ok")
    except Exception as exc:  # noqa: BLE001
        grade = {"score": None, "reasons": [str(exc)], "status": "judge_error"}

    return {
        "schema_version": SCHEMA_VERSION,
        "score_max": SCORE_MAX,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "eval",
        "fixture": fixture["name"],
        "rubric": rubric_path.stem,
        "score": grade.get("score"),
        "reasons": grade.get("reasons", []),
        "failed_rules": grade.get("failed_rules", []),
        "status": grade.get("status", "ok"),
        "prompt_version": PROMPT_VERSION,
        "run_id": run_id,
        "deterministic_metrics": det_metrics,
        "cost_usd": _eval_cost_since(t0_iso, fixture["name"]),
        "pipeline_latency_ms": elapsed_ms,
        "iteration_scenario": scenario.get("name"),
        "iteration_questions_count": len(iter_questions),
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description="callback. eval harness")
    ap.add_argument(
        "--suite",
        choices=["synthetic", "real", "all", "anchor", "exploration"],
        default="synthetic",
    )
    ap.add_argument("--subset", choices=["smoke", "full"], default="full")
    ap.add_argument("--fixture", help="Run a single named fixture (overrides --suite)")
    ap.add_argument("--out-dir", default=str(RESULTS_DIR))
    args = ap.parse_args(argv)

    # Load static baseline data once for baseline_comparison fields on JSONL records.
    baseline_v1_data: dict = {}
    if BASELINE_JSON.exists():
        try:
            _bdata = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
            if _bdata.get("schema_version") == 3:
                baseline_v1_data = _bdata
        except (OSError, json.JSONDecodeError):
            pass

    anchor_version: str | None = "v1" if args.suite == "anchor" else None

    try:
        fixtures = _select_fixtures(args.suite, args.fixture)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if not fixtures:
        logger.warning("No fixtures matched the selection")
        return 0

    rubrics_dir = ANCHOR_DIR / "rubrics" if args.suite == "anchor" else None
    rubrics = _select_rubrics(args.subset, rubrics_dir=rubrics_dir)
    rubric_versions = {rp: hashlib.sha256(rp.read_bytes()).hexdigest() for rp in rubrics}
    if not rubrics:
        logger.warning("No rubrics matched the selection")
        return 0

    logger.info(
        "Eval run: %d fixtures × %d rubrics = %d gradings (judge model: %s)",
        len(fixtures), len(rubrics), len(fixtures) * len(rubrics), JUDGE_MODEL,
    )

    client = _get_client()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_path_for_baseline = out_dir / f"{timestamp}.jsonl"
    baseline = _load_baseline_scores(out_path_for_baseline)
    regressions: list[dict] = []
    improvements: list[dict] = []
    if baseline:
        logger.info(
            "Regression-alert baseline: %d (fixture, rubric) pairs from prior runs (delta=%.1f)",
            len(baseline), REGRESSION_DELTA,
        )
    out_path = out_dir / f"{timestamp}.jsonl"

    n_pass = n_fail = 0

    with out_path.open("a", encoding="utf-8") as out:
        for fdir in fixtures:
            try:
                fixture = _load_fixture(fdir)
            except Exception as exc:
                logger.error("Fixture load failed: %s — %s", fdir.name, exc)
                continue

            # One run_id per fixture pipeline so the analyze + generate calls
            # share an ID. Lands in logs/llm_calls.jsonl AND on every per-rubric
            # eval result, letting the dashboard correlate which LLM calls
            # produced which graded output.
            run_id = uuid.uuid4().hex[:12]
            logger.info(
                "Fixture %s: building context + running pipeline (run_id=%s)",
                fixture["name"], run_id,
            )
            t0 = time.perf_counter()
            t0_iso = datetime.now(timezone.utc).isoformat()
            # clarify_questions is captured separately because the clarify
            # step is opt-in in production and we want the eval to keep
            # producing scores for the existing rubrics even if clarify
            # fails for some reason.
            clarify_questions: list[dict] = []
            clarify_reasoning = ""
            clarify_error: str | None = None
            _t_analyze: float | None = None
            _t_clarify: float | None = None
            _t_generate: float | None = None
            _t_generate_end: float | None = None
            try:
                context = _build_context(fixture)
                _t_analyze = time.perf_counter()
                analysis = analyze(
                    client, context,
                    username=f"eval:{fixture['name']}",
                    run_id=run_id,
                )
                _t_clarify = time.perf_counter()
                try:
                    clarify_result = clarify(
                        client, context, analysis,
                        username=f"eval:{fixture['name']}",
                        run_id=run_id,
                    )
                    clarify_questions = clarify_result.get("questions", [])
                    clarify_reasoning = clarify_result.get("reasoning", "")
                except Exception as exc:  # noqa: BLE001
                    # Non-fatal: degrade to score=None for the clarification
                    # rubric while still running generate + the other rubrics.
                    clarify_error = str(exc)
                    logger.warning(
                        "Clarify step failed for %s, continuing without it: %s",
                        fixture["name"], exc,
                    )
                _t_generate = time.perf_counter()
                result = generate(
                    client, context, analysis,
                    username=f"eval:{fixture['name']}",
                    run_id=run_id,
                )
                _t_generate_end = time.perf_counter()
            except Exception as exc:
                logger.error("Pipeline failed for %s: %s", fixture["name"], exc)
                out.write(json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "score_max": SCORE_MAX,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "eval",
                    "fixture": fixture["name"],
                    "rubric": None,
                    "score": None,
                    "status": "pipeline_error",
                    "error": str(exc),
                    "run_id": run_id,
                    "prompt_version": PROMPT_VERSION,
                    "anchor_version": anchor_version,
                    "suite": args.suite,
                    "fixture_hash": fixture["hash"],
                    "rubric_version": None,
                    "model_snapshots": MODEL_SNAPSHOTS,
                    "baseline_comparison": None,
                    "phase_latencies_ms": None,
                }) + "\n")
                n_fail += 1
                continue

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            phase_latencies_ms = {
                "analyze": int((_t_clarify - _t_analyze) * 1000) if (_t_analyze and _t_clarify) else None,
                "clarify": int((_t_generate - _t_clarify) * 1000) if (_t_clarify and _t_generate) else None,
                "generate": int((_t_generate_end - _t_generate) * 1000) if (_t_generate and _t_generate_end) else None,
            }
            logger.info("  pipeline %s done in %dms", fixture["name"], elapsed_ms)
            if clarify_error is None:
                exp_probes = sum(
                    1 for q in clarify_questions if q.get("kind") == "experience_probe"
                )
                logger.info(
                    "  clarify produced %d questions (%d experience probes, %d scope probes)",
                    len(clarify_questions), exp_probes, len(clarify_questions) - exp_probes,
                )

            # Compute the four post-generation deterministic metrics. These
            # ride along on every per-rubric record AND get passed to the
            # judge as part of `deterministic_analysis` — the grounding
            # rubric explicitly cites missing_samples as evidence of
            # fabrication.
            sources = [context["resume"]["text"]]
            for sup in context.get("supplemental_resumes", []):
                if sup.get("text"):
                    sources.append(sup["text"])
            det_metrics = _post_generation_metrics(
                result.get("resume_content", ""),
                result.get("cover_letter_content", ""),
                sources,
            )
            cost_usd = _eval_cost_since(t0_iso, fixture["name"])
            logger.info(
                "  metrics: verb_diversity=%.2f density=%.2f grounding_overlap=%.2f cost=$%.4f",
                det_metrics["verb_diversity"]["diversity_ratio"],
                det_metrics["specificity_density"]["density"],
                det_metrics["grounding_overlap"]["overlap_ratio"],
                cost_usd,
            )

            payload_det = dict(context["deterministic_analysis"])
            payload_det["post_generation"] = det_metrics

            for rubric_path in rubrics:
                # Skip judge entirely when clarify failed AND this is the
                # clarification_quality rubric — emit a pipeline_error row so
                # the dashboard surfaces it, but don't waste a judge call.
                if rubric_path.stem == "clarification_quality" and clarify_error is not None:
                    out.write(json.dumps({
                        "schema_version": SCHEMA_VERSION,
                        "score_max": SCORE_MAX,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "eval",
                        "fixture": fixture["name"],
                        "rubric": rubric_path.stem,
                        "score": None,
                        "reasons": [f"clarify step failed: {clarify_error}"],
                        "failed_rules": [],
                        "status": "pipeline_error",
                        "prompt_version": PROMPT_VERSION,
                        "run_id": run_id,
                        "deterministic_metrics": det_metrics,
                        "cost_usd": cost_usd,
                        "pipeline_latency_ms": elapsed_ms,
                        "anchor_version": anchor_version,
                        "suite": args.suite,
                        "fixture_hash": fixture["hash"],
                        "rubric_version": rubric_versions.get(rubric_path),
                        "model_snapshots": MODEL_SNAPSHOTS,
                        "baseline_comparison": None,
                        "phase_latencies_ms": phase_latencies_ms,
                    }) + "\n")
                    n_fail += 1
                    logger.info(
                        "  %s × clarification_quality → skipped (clarify failed)",
                        fixture["name"],
                    )
                    continue

                # iteration_quality is special: only graded on fixtures with an
                # `iteration_scenarios` block. The runner runs one simulated
                # iteration cycle (apply scripted edit → clarify_iteration →
                # grade questions). Re-generation + re-grading on the iterated
                # output is deferred — see TUNING_LOG entry for 2026-05-11.2.
                if rubric_path.stem == "iteration_quality":
                    iter_record = _run_iteration_phase(
                        client=client,
                        fixture=fixture,
                        context=context,
                        analysis=analysis,
                        generate_result=result,
                        clarify_questions=clarify_questions,
                        clarify_answers={},  # answers come from the scenario, not user input
                        rubric_path=rubric_path,
                        run_id=run_id,
                        det_metrics=det_metrics,
                        elapsed_ms=elapsed_ms,
                        t0_iso=t0_iso,
                    )
                    if iter_record is None:
                        # Fixture has no iteration_scenarios — silently skip,
                        # mirroring how the dashboard's heatmap handles N/A cells.
                        continue
                    iter_score = iter_record.get("score")
                    iter_record.update({
                        "anchor_version": anchor_version,
                        "suite": args.suite,
                        "fixture_hash": fixture["hash"],
                        "rubric_version": rubric_versions.get(rubric_path),
                        "model_snapshots": MODEL_SNAPSHOTS,
                        "baseline_comparison": _compute_baseline_comparison(
                            fixture["name"], rubric_path.stem,
                            iter_score if isinstance(iter_score, (int, float)) else None,
                            baseline_v1_data,
                        ),
                        "phase_latencies_ms": phase_latencies_ms,
                    })
                    out.write(json.dumps(iter_record) + "\n")
                    if isinstance(iter_score, (int, float)) and iter_score >= PASS_THRESHOLD:
                        n_pass += 1
                        verdict = "pass"
                    else:
                        n_fail += 1
                        verdict = "fail"
                    logger.info(
                        "  %s × iteration_quality → score=%s (%s)",
                        fixture["name"], iter_score, verdict,
                    )
                    if isinstance(iter_score, (int, float)):
                        delta = _detect_regression(
                            fixture["name"], rubric_path.stem, float(iter_score), baseline,
                        )
                        if delta is not None:
                            if delta["is_regression"]:
                                regressions.append(delta)
                            elif delta["is_improvement"]:
                                improvements.append(delta)
                    continue

                payload = {
                    "fixture": fixture["name"],
                    "expected": fixture["expected"],
                    "original_resume": context["resume"]["text"],
                    "supplemental_resumes": context["supplemental_resumes"],
                    "job_description": context["job_description"],
                    "deterministic_analysis": payload_det,
                    "analysis": analysis,
                    "generated_resume": result.get("resume_content", ""),
                    "generated_cover_letter": result.get("cover_letter_content", ""),
                    "clarification_questions": clarify_questions,
                    "clarification_reasoning": clarify_reasoning,
                }
                try:
                    grade = _grade(client, rubric_path, payload)
                    grade.setdefault("status", "ok")
                except Exception as exc:
                    logger.error(
                        "Grading failed for %s × %s: %s",
                        fixture["name"], rubric_path.stem, exc,
                    )
                    grade = {"score": None, "reasons": [str(exc)], "status": "judge_error"}

                _score = grade.get("score")
                record = {
                    "schema_version": SCHEMA_VERSION,
                    "score_max": SCORE_MAX,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "eval",
                    "fixture": fixture["name"],
                    "rubric": rubric_path.stem,
                    "score": _score,
                    "reasons": grade.get("reasons", []),
                    "failed_rules": grade.get("failed_rules", []),
                    "status": grade.get("status", "ok"),
                    "prompt_version": PROMPT_VERSION,
                    "run_id": run_id,
                    "deterministic_metrics": det_metrics,
                    "cost_usd": cost_usd,
                    "pipeline_latency_ms": elapsed_ms,
                    "anchor_version": anchor_version,
                    "suite": args.suite,
                    "fixture_hash": fixture["hash"],
                    "rubric_version": rubric_versions.get(rubric_path),
                    "model_snapshots": MODEL_SNAPSHOTS,
                    "baseline_comparison": _compute_baseline_comparison(
                        fixture["name"], rubric_path.stem,
                        _score if isinstance(_score, (int, float)) else None,
                        baseline_v1_data,
                    ),
                    "phase_latencies_ms": phase_latencies_ms,
                }
                out.write(json.dumps(record) + "\n")

                score = record["score"]
                if isinstance(score, (int, float)) and score >= PASS_THRESHOLD:
                    n_pass += 1
                    verdict = "pass"
                else:
                    n_fail += 1
                    verdict = "fail"
                logger.info(
                    "  %s × %s → score=%s (%s)",
                    fixture["name"], rubric_path.stem, score, verdict,
                )

                if isinstance(score, (int, float)) and record.get("status") != "judge_error":
                    delta = _detect_regression(
                        fixture["name"], rubric_path.stem, float(score), baseline,
                    )
                    if delta is not None:
                        if delta["is_regression"]:
                            regressions.append(delta)
                            logger.warning(
                                "REGRESSION: %s × %s dropped %.1f → %.1f (Δ=%+.1f) "
                                "vs prior run (prompt_version=%s, %s)",
                                delta["fixture"], delta["rubric"],
                                delta["prev_score"], delta["new_score"], delta["delta"],
                                delta["prev_prompt_version"] or "unknown",
                                delta["prev_timestamp"][:19] if delta["prev_timestamp"] else "—",
                            )
                        elif delta["is_improvement"]:
                            improvements.append(delta)

    logger.info(
        "Eval complete: %d pass, %d fail. Results: %s",
        n_pass, n_fail, out_path,
    )

    # Regression summary — concise, only printed when there's something to say.
    if regressions or improvements:
        logger.info("--- Regression check vs previous runs (delta=%.1f) ---", REGRESSION_DELTA)
        for d in regressions:
            logger.info(
                "  ✗ %s × %s: %.1f → %.1f (Δ=%+.1f)",
                d["fixture"], d["rubric"], d["prev_score"], d["new_score"], d["delta"],
            )
        for d in improvements:
            logger.info(
                "  ✓ %s × %s: %.1f → %.1f (Δ=%+.1f)",
                d["fixture"], d["rubric"], d["prev_score"], d["new_score"], d["delta"],
            )
        if regressions:
            logger.warning(
                "Found %d regression(s) ≥%.1f points. Inspect dashboard heatmap "
                "and check `failed_rules` for the affected (fixture, rubric) pairs.",
                len(regressions), REGRESSION_DELTA,
            )

    return 0 if (n_fail == 0 and not regressions) else 2


if __name__ == "__main__":
    sys.exit(main())
