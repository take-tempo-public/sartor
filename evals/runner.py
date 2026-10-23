"""sartor. eval harness.

Loads synthetic and/or real fixtures, runs the full analyze + generate
pipeline against each, dispatches per-rubric grading via Claude Haiku,
and writes per-grading JSONL records to evals/results/{timestamp}.jsonl.

Usage:
    python evals/runner.py --suite synthetic
    python evals/runner.py --suite synthetic --subset smoke
    python evals/runner.py --suite anchor --subset smoke
    python evals/runner.py --suite real
    python evals/runner.py --fixture sre-mid-level
    python evals/runner.py --list
    python evals/runner.py --suite synthetic --subset smoke --estimate
    python evals/runner.py --suite synthetic --max-spend 1.00

Exit code: 0 if every grading scored >= 4, 2 if any failed, 1 on
configuration error, 4 when --max-spend refused the run (the estimate is
over the cap) or stopped it (the spend reached the cap).
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
from collections.abc import Callable
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

import anthropic
from sqlalchemy.orm import Session

# Make project root importable so this script works whether invoked as
# `python evals/runner.py` or `python -m evals.runner`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import call_identity  # noqa: E402
import preflight  # noqa: E402
import sartor_home  # noqa: E402
from analyzer import (  # noqa: E402
    HAIKU_MODEL,
    SONNET_MODEL,
    active_model_overrides,
    analyze,
    clarify,
    clarify_iteration,
    current_trace_context,
    effective_prompt_version,
    generate,
    log_judge_call,
    model_overrides,
    prompt_overrides,
    recommend_bullets,
    recommend_summaries,
    thinking_setting,
    trace_context,
)

# F-11 (2026-07 UX review) — the "assemble" eval mode drives the SAME
# Compose -> freeze -> assemble path corpus-mode /api/generate uses, instead of
# the LLM generate() fallback, so the harness can score the deterministically
# ASSEMBLED résumé body users actually download. Reuses the product's own
# resolver/gate/assembler functions (do not reimplement): recommend_bullets /
# recommend_summaries (above, Haiku) populate the same context keys the
# /recommend + /recommend-summary routes write; freeze_approved_composition is
# the exact function Compose's Save-and-continue calls; _frozen_composition /
# _assemble_from_frozen_composition are the exact gate + assembler
# /api/generate calls once a composition is frozen. Module-level (not a lazy
# import inside the assemble helper) so tests can monkeypatch these the same
# way they already monkeypatch `analyze` / `clarify` / `generate` above.
from blueprints.generation import (  # noqa: E402
    _assemble_from_frozen_composition,
    _frozen_composition,
)
from corpus_to_json_resume import freeze_approved_composition  # noqa: E402
from evals import eval_catalog  # noqa: E402
from evals.seed_import import load_seed, seeded_session  # noqa: E402
from hardening import (  # noqa: E402
    ContextSet,
    assemble_source_union,
    build_context_set,
    check_ats_format,
    compute_call_cost,
    compute_fabricated_specifics,
    compute_grounding_overlap,
    compute_keyword_overlap,
    compute_letter_date,
    compute_quantification_rate,
    compute_specificity_density,
    compute_top_third_density,
    compute_verb_diversity,
    corpus_handles,
    extract_company_terms,
    extract_jd_label,
    extract_keywords,
    find_leaked_handles,
    handle_snippet,
    is_candidate_record,
    iter_prose_leaves,
    source_handle_tokens,
)
from parser import parse_resume  # noqa: E402

# Same JSONL telemetry sink analyzer.py writes to — read here to compute
# per-eval cost by tailing entries written during this run. Both follow the data root
# (item 145); a dev who exports `SARTOR_HOME` would otherwise read a log nothing writes.
LLM_LOG_PATH = sartor_home.data_path("logs", "llm_calls.jsonl")

EVALS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVALS_DIR / "fixtures"
RUBRICS_DIR = EVALS_DIR / "rubrics"
RESULTS_DIR = EVALS_DIR / "results"
ANCHOR_DIR = EVALS_DIR / "anchors" / "anchor-v1"
# The golden set's rendered fixtures (evals/golden_set.py): one directory per cell and JD, each with its
# own seed.json. Same layout as the anchor, so `_suite_of` names it `golden-v1`.
GOLDEN_DIR = EVALS_DIR / "golden" / "golden-v1" / "fixtures"
WEIGHTS_PATH = EVALS_DIR / "callback_weights.json"

JUDGE_MODEL = "claude-haiku-4-5-20251001"

# Derived from the analyzer's pins, not hand-copied, so a model swap cannot leave the eval
# records naming the old model (item 175 gap 6). `sonnet` / `haiku_judge` keep their keys.
MODEL_SNAPSHOTS = {
    "sonnet": SONNET_MODEL,
    "haiku": HAIKU_MODEL,
    "haiku_judge": JUDGE_MODEL,
}


def _model_provenance_fields() -> dict[str, Any]:
    """The model fields every eval record carries: what ran, and (candidate runs only) why it differs.

    With no `model_overrides()` active this is exactly ``{"model_snapshots": MODEL_SNAPSHOTS}``, the
    record shape every earlier run wrote. Under an override, ``model_snapshots`` names the models
    actually sent (the judge stays ``JUDGE_MODEL``) and ``model_overrides`` records the pin -> candidate
    mapping, which `hardening.is_candidate_record` reads to keep the run out of baseline views.
    """
    overrides = active_model_overrides()
    if not overrides:
        return {"model_snapshots": MODEL_SNAPSHOTS}
    snapshots = dict(MODEL_SNAPSHOTS)
    if "SONNET_MODEL" in overrides:
        snapshots["sonnet"] = overrides["SONNET_MODEL"]
    if "HAIKU_MODEL" in overrides:
        snapshots["haiku"] = overrides["HAIKU_MODEL"]
    return {"model_snapshots": snapshots, "model_overrides": overrides}


def _trace_fields() -> dict[str, Any]:
    """The ids every eval record carries inside a run (item 181): the run's ``trace_id``, the case
    (fixture) it belongs to and the case span the product and judge calls are children of.

    Empty outside a trace context. The key names mirror the call-log row's, so a record and its
    rows join on ``trace_id`` + ``case_id`` instead of on a time window.
    """
    ctx = current_trace_context()
    if ctx is None:
        return {}
    fields: dict[str, Any] = {"trace_id": ctx.trace_id}
    if ctx.case_id is not None:
        fields["case_id"] = ctx.case_id
    if ctx.parent_span_id is not None:
        fields["span_id"] = ctx.parent_span_id
    return fields


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

# A coarse progress sartor: (event_name, payload) → None. Optional everywhere;
# the default `run_suite` path passes None and every emit is a no-op, so the
# written JSONL bytes are unchanged. The console SSE route passes one to stream
# per-fixture/per-rubric progress to the browser.
ProgressFn = Callable[[str, dict[str, Any]], None]


@dataclass
class EvalRunResult:
    """Structured outcome of one ``run_suite`` invocation.

    ``exit_code`` preserves the historical CLI contract (0 = every rubric passed
    and no regressions fired; 2 = at least one fail/regression). ``out_path`` is
    the JSONL results file written this run, or None when no fixtures/rubrics
    matched and nothing ran. The remaining fields let a caller (the console route)
    report the run without re-reading the file.
    """

    exit_code: int
    out_path: Path | None
    n_pass: int
    n_fail: int
    regressions: list[dict[str, Any]]
    improvements: list[dict[str, Any]]
    candidate_version: str | None = None
    cancelled: bool = False
    # Item 181. The run's trace id; the judge's spend, which a record's ``cost_usd`` leaves out by
    # design; and the run's whole spend (generation + judge), read from the call log by trace id.
    trace_id: str | None = None
    judge_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    # Item 182. Why a run stopped early: "max_spend" (the cap was reached) or "cancelled" (the caller's
    # ``cancel_check`` said so); None for a run that ran to the end. Appended last with a default
    # because ``EvalRunResult`` is built positionally in several places.
    stop_reason: str | None = None


# ``--max-spend``: the run was refused (its estimate is over the cap) or stopped (the spend reached it).
# 0, 1 and 2 are taken (every grading passed, configuration error, a grading failed or regressed).
EXIT_OVER_BUDGET = 4


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        key_file = preflight.api_key_path()
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set and no .api_key file found in the data root")
    return anthropic.Anthropic(api_key=api_key)


def _load_fixture(
    fixture_dir: Path, *, seed_mode: bool = False, seed_path: Path | None = None
) -> dict[str, Any]:
    """Load a fixture: jd.txt + resume.{md|docx|pdf} + expected.json.

    In ``seed_mode`` the corpus comes from a ``--seed`` seed.json instead of a
    resume file, so the resume file is ignored (``resume_path`` stays None) and
    the fixture hash is computed over jd.txt + expected.json only. The default
    (``seed_mode=False``) is byte-identical to the prior behavior — a resume file
    is required.

    ``seed_path`` is the fixture's OWN seed (a golden cell, ``evals/golden_set.py``): it is part of
    the fixture's input, so its bytes join the hash. Left ``None`` (the ``--seed`` path, and every
    existing suite) the hash is unchanged.
    """
    jd = (fixture_dir / "jd.txt").read_text(encoding="utf-8")

    resume_path = None
    if not seed_mode:
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
    if resume_path is not None:
        h.update(resume_path.read_bytes())
    h.update((fixture_dir / "expected.json").read_bytes())
    if seed_path is not None:
        h.update(seed_path.read_bytes())
    # F-14: computed once and reused at every downstream record-write site —
    # never re-derived per rubric. Prefer a value already stamped into
    # expected.json (a collated real fixture — see annotation.collate_expected)
    # over re-deriving from the header text, so the anchor's own resolved
    # label wins; fall back to deriving fresh for synthetic/legacy fixtures.
    # NOT included in the hash above — fixture_hash must stay a pure function
    # of file bytes so existing baseline joins hold.
    jd_label = expected.get("jd_label") or extract_jd_label(jd)
    return {
        "name": fixture_dir.name,
        "jd": jd,
        "resume_path": resume_path,
        "expected": expected,
        "hash": h.hexdigest(),
        "jd_label": jd_label,
    }


def _build_context(fixture: dict[str, Any]) -> ContextSet:
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
    overlap = compute_keyword_overlap(
        resume_keywords,
        jd_keywords,
        company_terms=extract_company_terms(fixture["jd"]),
    )
    ats_warnings = check_ats_format(parsed)
    return build_context_set(
        fixture["jd"],
        parsed,
        config,
        profile_text="",
        jd_keywords=jd_keywords,
        resume_keywords=resume_keywords,
        keyword_overlap=overlap,
        ats_warnings=ats_warnings,
        original_resume_path=str(fixture["resume_path"]),
    )


def _build_context_from_seed(
    session: Session,
    *,
    candidate_username: str,
    jd_text: str,
    run_id: str,
) -> tuple[ContextSet, Any]:
    """Build a ContextSet from an imported corpus seed via the REAL product path.

    Drives ``db.build_context.build_context_set_from_db`` — the same function the
    Flask app uses for corpus-backed analyze — so eval traffic exercises the
    production corpus→context path, not the file-parsed ``_build_context``. The
    application row is NOT persisted beyond the seeded in-memory session (only the
    ContextSet is graded); it is returned (not discarded) so ``mode="assemble"`` can
    freeze a composition against its ``candidate_id`` / ``application_id`` — the
    generate-mode default path never reads the returned application. The deferred
    import keeps the default file-based path's import surface unchanged.
    """
    from db.build_context import build_context_set_from_db

    context, application, _run = build_context_set_from_db(
        session,
        candidate_username=candidate_username,
        jd_text=jd_text,
        run_id=run_id,
    )
    return context, application


def _groundedness_composite(fabricated_specifics: dict[str, Any]) -> dict[str, Any]:
    """The single reportable groundedness signal, L0-only by default.

    Folds the deterministic L0 fabricated-specifics rate into one block that
    rides along on every eval record (nested in deterministic_metrics) and is
    attributable by prompt_version on the dashboard's score-over-time chart.
    `_enrich_groundedness` later layers in the eval-only L1/L2 signals when
    `--grounding-signals` runs; absent that flag the composite stays honest
    L0-only. `score` is a 0–5 projection (higher = better) so it plugs straight
    into the existing 0–5 chart; `fabricated_specifics_rate` (0–1) is kept too.
    """
    rate = fabricated_specifics.get("fabricated_specifics_rate", 0.0)
    return {
        "layers": ["L0"],
        "fabricated_specifics_rate": rate,
        "flagged_count": fabricated_specifics.get("flagged", 0),
        "score": round(5.0 * (1.0 - rate), 3),
    }


def _enrich_groundedness(block: dict[str, Any], grounding_signals_data: dict[str, Any]) -> None:
    """Layer the eval-only L1/L2 signals into the groundedness composite in
    place. Pure dict mutation — called only when `--grounding-signals` produced
    real scores, so default runs (no torch) keep the L0-only composite.
    L1/L2 behavior itself is read, never re-tuned (calibration is deferred-B)."""
    nli = grounding_signals_data.get("nli_summary", {})
    minicheck = grounding_signals_data.get("minicheck_summary", {})
    bullet_count = grounding_signals_data.get("bullet_count", 0) or 0
    low_scores = minicheck.get("low_score_count", 0)
    block["layers"] = ["L0", "L1", "L2"]
    block["mean_entailment"] = nli.get("mean_entailment", 0.0)
    block["contradiction_count"] = nli.get("contradiction_count", 0)
    block["mean_minicheck"] = minicheck.get("mean_score", 0.0)
    block["unsupported_claim_rate"] = round(low_scores / bullet_count, 3) if bullet_count else 0.0


def _post_generation_metrics(
    generated_resume: str,
    generated_cover_letter: str,
    sources: list[str],
    jd_keywords: dict[str, Any] | None = None,
    source_union: list[str] | None = None,
) -> dict[str, Any]:
    """Compute post-generation deterministic metrics.

    `sources` is the list of source texts the LLM was allowed to draw from
    (primary resume + supplementals). Verb diversity and specificity density
    are computed over the generated resume only; grounding overlap is computed
    over the resume + cover letter combined (both must trace to source).
    `jd_keywords` is the hardening-extracted keyword dict used to compute
    top_third_density; pass None to skip that metric.

    `source_union` is the dynamic ground-truth union (primary + supplementals +
    clarification answers) the L0 fabricated-specifics check scores against;
    when None it falls back to `sources`. It is kept separate so the existing
    `grounding_overlap` source set (and its baseline numbers) are not perturbed.
    """
    combined = f"{generated_resume}\n\n{generated_cover_letter}"
    fabricated_specifics = compute_fabricated_specifics(
        combined, source_union if source_union is not None else sources
    )
    return {
        "verb_diversity": compute_verb_diversity(generated_resume),
        "specificity_density": compute_specificity_density(generated_resume),
        "grounding_overlap": compute_grounding_overlap(combined, sources, n=3),
        "top_third_density": compute_top_third_density(generated_resume, jd_keywords or {}),
        "quantification_rate": compute_quantification_rate(generated_resume),
        "fabricated_specifics": fabricated_specifics,
        "groundedness": _groundedness_composite(fabricated_specifics),
    }


def _leak_report(
    *,
    context: ContextSet,
    analysis: dict[str, Any],
    clarify_questions: list[dict[str, Any]],
    clarify_reasoning: str,
    result: dict[str, Any],
    capture: dict[str, Any],
    run_date: date,
) -> dict[str, Any]:
    """Item 140: internal id handles in every prose field the pipeline produced, plus the letter date.

    Scans all string leaves of each section, not just the letter, so the instrument is wider than
    the hypothesis that the letter's handle came from the analysis. Handles are the ones the
    prompts shipped (the corpus `e`/`t`/`b` ids and the clarification question ids); a handle that
    also occurs in real source text is excluded. `letter_carriers` maps each handle found in the
    cover letter to the OTHER sections whose text also holds it. Kept out of `det_metrics`, which is
    passed to the judge, so rubric inputs stay identical to history. One O(n) pass per field over
    data already in hand.
    """
    q_ids = [str(q.get("id")) for q in clarify_questions if q.get("id")]
    handles = corpus_handles(cast("list[Any]", context.get("career_corpus") or []), q_ids)
    src_tokens = source_handle_tokens([*assemble_source_union(context), context["job_description"]])
    sections: dict[str, object] = {
        "analysis": analysis,
        "clarify": {"questions": clarify_questions, "reasoning": clarify_reasoning},
        "resume_content": result.get("resume_content", ""),
        "cover_letter_content": result.get("cover_letter_content", ""),
        "changes_made": result.get("changes_made", ""),
        "proofread_notes": result.get("proofread_notes", ""),
        **{f"recommend.{k}": v for k, v in capture.items()},
    }
    findings: list[dict[str, str]] = []
    by_section: dict[str, set[str]] = {}
    for name, value in sections.items():
        for path, text in iter_prose_leaves(value, name):
            for handle in find_leaked_handles(text, handles, src_tokens):
                # The snippet is what lets a reader audit a finding: no response text is persisted elsewhere.
                findings.append(
                    {
                        "section": name,
                        "path": path,
                        "handle": handle,
                        "snippet": handle_snippet(text, handle),
                    }
                )
                by_section.setdefault(name, set()).add(handle)
    letter_handles = by_section.get("cover_letter_content", set())
    letter_carriers = {
        h: sorted(s for s, hs in by_section.items() if s != "cover_letter_content" and h in hs)
        for h in sorted(letter_handles)
    }
    return {
        "handles_shipped": len(handles["prefixed"]),
        "total": len(findings),
        "findings": findings,
        "letter_carriers": letter_carriers,
        "letter_date": compute_letter_date(result.get("cover_letter_content", ""), run_date),
        "letter_head": str(result.get("cover_letter_content", ""))[:160],
    }


def _judge_create(
    client: anthropic.Anthropic,
    *,
    call_kind: str,
    fixture_name: str,
    **request: Any,
) -> tuple[Any, str | None]:
    """``client.messages.create`` for an eval judge, with its telemetry row (item 175 gap 5).

    Returns ``(message, api_request_id)``. The row is written under ``call_kind`` (``judge_*``)
    and ``eval:<fixture_name>``, and inside a run it carries the trace and case ids (item 181), so
    the spend is found by id; `_trace_cost` splits ``judge_*`` rows out so a fixture's ``cost_usd``
    stays generation-only. A failed call logs its error row and re-raises.

    The judge model's `thinking` value comes from the product's `THINKING_POLICY` (item 137), so
    moving ``JUDGE_MODEL`` cannot silently switch a judge to adaptive thinking; a model with no
    policy is refused here, before anything is sent, with its error row.
    """
    t0 = time.perf_counter()
    username = f"eval:{fixture_name}" if fixture_name else "eval"
    try:
        thinking = thinking_setting(request["model"])
        if thinking is not None:
            request["thinking"] = thinking
        msg = client.messages.create(**request)
    except Exception as exc:
        log_judge_call(
            call_kind=call_kind,
            username=username,
            model=JUDGE_MODEL,
            request_kwargs=request,
            response=None,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
            error=exc,
        )
        raise
    request_id = log_judge_call(
        call_kind=call_kind,
        username=username,
        model=JUDGE_MODEL,
        request_kwargs=request,
        response=msg,
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
    )
    return msg, request_id


def _score_distinctiveness(
    client: anthropic.Anthropic,
    generated_resume: str,
    job_description: str,
    fixture_name: str = "",
) -> dict[str, Any]:
    """Lightweight Haiku call scoring how distinctive/memorable the résumé is.

    Eval-time only — not called from the production pipeline. Returns
    {"score": float | None, "summary": str}. On judge failure returns
    {"score": None, "summary": "judge_error"} so the composite gracefully
    skips it rather than crashing.

    Score 1–5:
      5 = immediately memorable; standout specific achievements
      4 = clearly distinctive; strong specifics throughout
      3 = average; some specifics but generic framing in places
      2 = generic; could describe any candidate
      1 = completely generic; no distinguishing details
    """
    prompt = (
        "You are a recruiter who has reviewed 80 résumés today. Score this one on "
        "distinctiveness: how memorable and specific it is compared to a generic "
        "template résumé for the role described in the job description.\n\n"
        f"## Job Description\n\n{job_description[:2000]}\n\n"
        f"## Résumé\n\n{generated_resume[:3000]}\n\n"
        "Output ONLY valid JSON with keys 'score' (float 1.0–5.0, one decimal) "
        "and 'summary' (one sentence). No prose outside the JSON."
    )
    request_id: str | None = None
    try:
        msg, request_id = _judge_create(
            client,
            call_kind="judge_distinctiveness",
            fixture_name=fixture_name,
            model=JUDGE_MODEL,
            max_tokens=128,
            system="You are a strict, terse grader. Output only valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = getattr(msg.content[0], "text", "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()
        result = cast("dict[str, Any]", json.loads(raw))
        if result.get("score") is not None:
            result["score"] = float(result["score"])
        result["judge_request_id"] = request_id
        return result
    except Exception as exc:
        logger.warning("_score_distinctiveness failed: %s", exc)
        return {"score": None, "summary": "judge_error", "judge_request_id": request_id}


def _log_offset() -> int:
    """Byte size of the call log now: where a scan for rows written from here on can begin."""
    try:
        return LLM_LOG_PATH.stat().st_size
    except OSError:
        return 0


def _trace_cost(
    start_offset: int, trace_id: str, case_id: str | None = None
) -> tuple[float, float]:
    """``(generation_usd, judge_usd)`` of the call-log rows carrying ``trace_id`` (and ``case_id``).

    Rows are selected by id, not by a time window (item 181): two runs overlapping on one fixture
    each carry their own trace id, so neither sums the other's spend. Only the bytes written since
    ``start_offset`` are read, so a scan costs this run's rows and not the whole log's history
    (every writer appends whole lines, so an offset taken between calls lies on a line boundary;
    an offset past the end means the file was rotated and is read from the start). ``judge_*``
    rows are split out so `cost_usd` stays generation-only, whatever order the rollup runs in
    relative to the judge calls (item 175). Best-effort: a missing log is ``(0.0, 0.0)``.
    """
    generation = judge = 0.0
    try:
        with LLM_LOG_PATH.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(start_offset if start_offset <= size else 0)
            for raw in f:
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(rec, dict) or rec.get("trace_id") != trace_id:
                    continue
                if case_id is not None and rec.get("case_id") != case_id:
                    continue
                cost = compute_call_cost(rec)
                if str(rec.get("call", "")).startswith("judge_"):
                    judge += cost
                else:
                    generation += cost
    except OSError as exc:
        logger.warning("eval cost rollup failed: %s", exc)
        return 0.0, 0.0
    return round(generation, 6), round(judge, 6)


def _case_cost(start_offset: int, *, judge: bool = False) -> float:
    """Generation (or, with ``judge=True``, judge) spend of the case in the active trace context."""
    ctx = current_trace_context()
    if ctx is None or ctx.case_id is None:
        return 0.0
    generation, judge_usd = _trace_cost(start_offset, ctx.trace_id, ctx.case_id)
    return judge_usd if judge else generation


class _SpendMeter:
    """The running spend of one trace, read forward from where it last stopped (``--max-spend``).

    `_trace_cost` rescans from a fixed offset, which is right once at the end of a run and wasteful
    on every poll. This reads only the bytes written since the last poll, so polling at every phase
    boundary costs the new rows, not the run's history. A line that does not yet end in a newline is
    left for the next poll (a writer may be mid-write); an offset past the end means the log was
    rotated and is read from the start. Rows are selected by ``trace_id`` exactly as `_trace_cost`
    selects them, so the two agree on the total.
    """

    def __init__(self, start_offset: int, trace_id: str) -> None:
        self._offset = start_offset
        self._trace_id = trace_id
        self.total_usd = 0.0

    def poll(self) -> float:
        try:
            with LLM_LOG_PATH.open("rb") as f:
                f.seek(0, 2)
                if self._offset > f.tell():
                    self._offset = 0
                f.seek(self._offset)
                for raw in f:
                    if not raw.endswith(b"\n"):
                        break
                    self._offset += len(raw)
                    try:
                        rec = json.loads(raw)
                    except ValueError:
                        continue
                    if isinstance(rec, dict) and rec.get("trace_id") == self._trace_id:
                        self.total_usd += compute_call_cost(rec)
        except OSError as exc:
            logger.warning("spend meter could not read the call log: %s", exc)
        return self.total_usd


BASELINE_JSON = RESULTS_DIR / "baseline_v1.json"


def _load_baseline_scores(out_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Return the most-recent (fixture, rubric) → record map for regression detection.

    Seeds from baseline_v1.json (schema_version 3) when present, so the alerter
    compares against the stable 5-run aggregate mean rather than the noisiest
    single prior run. Real JSONL records (timestamp > "0000…") always win —
    except candidate records (a prompt or model override, `is_candidate_record`),
    which are skipped: a candidate run must never become the next run's "prior
    run", or its scores would seed (or hide) regression alerts for a baseline run.
    """
    if not RESULTS_DIR.exists():
        return {}

    baseline: dict[tuple[str, str], dict[str, Any]] = {}

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
                    if not fixture or not rubric or score is None or is_candidate_record(rec):
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
    bdata: dict[str, Any],
) -> dict[str, Any] | None:
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
    baseline: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any] | None:
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


def _grade(
    client: anthropic.Anthropic,
    rubric_path: Path,
    payload: dict[str, Any],
    fixture_name: str = "",
) -> dict[str, Any]:
    """Send one (rubric × payload) to Haiku and parse the JSON verdict.

    The verdict carries ``judge_request_id`` (the API request id of that call), so a score
    joins to its `judge_grade` row in `logs/llm_calls.jsonl`.
    """
    rubric = rubric_path.read_text(encoding="utf-8")
    user_msg = (
        f"{rubric}\n\n"
        "## Material to grade\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```\n\n"
        "Output the JSON verdict now. No prose outside the JSON."
    )
    msg, request_id = _judge_create(
        client,
        call_kind="judge_grade",
        fixture_name=fixture_name,
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
        grade = cast("dict[str, Any]", json.loads(raw))
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
            "judge_request_id": request_id,
        }
    # Force-float at the boundary: rubrics now allow fractional scores
    # (0.0–5.0, one decimal), but Haiku still occasionally emits an integer.
    # Downstream aggregations rely on a uniform numeric type.
    if grade.get("score") is not None:
        try:
            grade["score"] = float(grade["score"])
        except (TypeError, ValueError):
            grade["score"] = 0.0
    grade["judge_request_id"] = request_id
    return grade


def _select_fixtures(suite: str, single: str | None) -> list[Path]:
    """Resolve fixture directories from --suite and --fixture flags."""
    if single:
        for sub in ("synthetic", "real"):
            cand = FIXTURES_DIR / sub / single
            if cand.exists():
                return [cand]
        golden = GOLDEN_DIR / single
        if golden.exists():
            return [golden]
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
    # Not in "all": a pass over this suite is up to 96 cases (one fixture per JD) and must be asked for.
    if suite == "golden-v1" and GOLDEN_DIR.exists():
        fixtures.extend(sorted(p for p in GOLDEN_DIR.iterdir() if p.is_dir()))
    return fixtures


def _suite_of(fixture_dir: Path) -> str:
    """The suite a fixture directory belongs to: ``synthetic``, ``real``, ``anchor-v1`` or ``exploration``.

    Read from the directory's own parents (``.../<suite>/<name>``, or ``.../<suite>/fixtures/<name>``
    for the anchor), never from ``FIXTURES_DIR``, so a test that patches ``FIXTURES_DIR`` to a tmp
    path still gets a label. It is the first half of a ``case_id``, ``<suite>/<name>`` (item 182);
    the bare fixture name was the same string for ``synthetic/pm-senior`` and ``anchor-v1/pm-senior``.
    """
    parent = fixture_dir.parent
    return parent.parent.name if parent.name == "fixtures" else parent.name


def _select_rubrics(subset: str) -> list[Path]:
    """Smoke = grounding only; full = every rubric.

    iteration_quality is special: it only runs against fixtures that have
    `iteration_scenarios` defined in their expected.json. The runner skips
    iteration_quality grading silently for fixtures without a scenario rather
    than emitting score=None rows that would muddy the dashboard's heatmap.

    All suites (anchor, synthetic, exploration) use the shared evals/rubrics/
    directory as the single source of truth. Rubric definitions evolve with the
    product; only fixtures (jd.txt, resume.md, expected.json) are frozen per
    anchor version.
    """
    all_rubrics = sorted(RUBRICS_DIR.glob("*.md"))
    if subset == "smoke":
        return [r for r in all_rubrics if r.stem == "grounding"]
    return all_rubrics


# ---------- the call plan and the spend estimate (item 182) -------------------------------------

# What `run_suite` calls for ONE fixture, by mode, before any rubric is graded. `analyze` fires two call
# kinds. This table is declared, not derived from the code above it: `tests/test_eval_spend.py` ties it to
# the calls a stubbed `run_suite` really fires, in both modes, so a change to the flow fails that test.
_FIXTURE_CALLS: dict[str, tuple[str, ...]] = {
    "generate": (
        "analyze_extraction",
        "analyze_synthesis",
        "clarify",
        "generate",
        "judge_distinctiveness",
    ),
    "assemble": (
        "analyze_extraction",
        "analyze_synthesis",
        "clarify",
        "recommend",
        "generate_cover_letter",
        "judge_distinctiveness",
    ),
}
# Calls a mode MAY make, not counted in the plan, with the reason.
_CONDITIONAL_CALLS: dict[str, dict[str, str]] = {
    "generate": {},
    "assemble": {
        "recommend_summary": "makes no call below two summary variants (analyzer.recommend_summaries)"
    },
}
# The extra calls of a fixture that has `iteration_scenarios`, when `iteration_quality` is in the subset.
_ITERATION_CALLS = ("iterate_clarify", "judge_grade")


def _check_mode_name(mode: str) -> None:
    """Refuse an unknown mode, before anything is read or spent."""
    if mode not in ("generate", "assemble"):
        raise ValueError(f"Unknown mode {mode!r}; expected 'generate' or 'assemble'")


def _seed_source(mode: str, *, has_seed: bool, fixtures: list[Path] | None) -> str:
    """Where the corpus for a run comes from: ``global``, ``per_fixture`` or ``none``.

    ``global``: a ``--seed`` was given, one corpus for every fixture (the path every earlier suite
    uses, unchanged). ``per_fixture``: ``assemble`` mode with no ``--seed``, where each selected
    fixture carries its OWN ``seed.json`` (a golden cell). ``none``: the file-based path. A fixture's
    ``seed.json`` is read ONLY in assemble mode: real fixtures can already hold one (the console runs
    them in generate mode), and reading it by presence would silently change ``--suite real``.

    ``assemble`` with neither source raises before anything is spent, naming the fixtures that lack a
    seed. It needs the selected fixtures, so the caller runs it after ``_select_fixtures``.
    """
    if has_seed:
        return "global"
    if mode != "assemble":
        return "none"
    if fixtures and all((f / "seed.json").is_file() for f in fixtures):
        return "per_fixture"
    missing = [f.name for f in fixtures or [] if not (f / "seed.json").is_file()]
    raise ValueError(
        "mode='assemble' requires --seed — frozen-composition assembly needs a "
        "real corpus (candidate + application rows), not a file-parsed résumé; "
        "or a seed.json in every selected fixture"
        + (f" (without one: {', '.join(missing[:5])})" if missing else "")
    )


def _check_mode(mode: str, *, has_seed: bool, fixtures: list[Path] | None = None) -> str:
    """`_check_mode_name` then `_seed_source`: the whole pre-spend mode check, returning the seed source."""
    _check_mode_name(mode)
    return _seed_source(mode, has_seed=has_seed, fixtures=fixtures)


def _fixture_iterates(fixture_dir: Path, *, seed_mode: bool) -> bool | None:
    """Whether the fixture has an iteration scenario; ``None`` when `_load_fixture` would fail on it.

    Mirrors `_load_fixture`'s requirements (``jd.txt``, ``expected.json``, and a résumé file unless in
    seed mode) without parsing a résumé, so a plan costs a few ``stat`` calls and one small JSON read
    per fixture. The ``synthetic/corpus`` directory is an example of a fixture that does not load.
    """
    try:
        if not (fixture_dir / "jd.txt").is_file():
            return None
        if not seed_mode and not any(
            (fixture_dir / f"resume{ext}").exists() for ext in (".md", ".docx", ".pdf")
        ):
            return None
        expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return isinstance(expected, dict) and bool(expected.get("iteration_scenarios"))


def _call_plan(
    fixtures: list[Path], rubrics: list[Path], *, mode: str, seed_mode: bool
) -> tuple[dict[str, int], dict[str, str], list[str]]:
    """``(calls per kind, conditional kinds with their reason, fixtures that will not load)``.

    The calls a run is set to make, one per planned call. A grading `run_suite` skips because clarify
    failed is still counted, and a retry is not (an estimate prices the plan).
    """
    counts: dict[str, int] = {}
    skipped: list[str] = []

    def add(kinds: tuple[str, ...]) -> None:
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1

    stems = [r.stem for r in rubrics]
    for fdir in fixtures:
        iterates = _fixture_iterates(fdir, seed_mode=seed_mode)
        if iterates is None:
            skipped.append(fdir.name)
            continue
        add(_FIXTURE_CALLS[mode])
        for stem in stems:
            if stem == "iteration_quality":
                if iterates:
                    add(_ITERATION_CALLS)
            else:
                add(("judge_grade",))
    return counts, dict(_CONDITIONAL_CALLS[mode]), skipped


def _pin_models(model_overrides_map: dict[str, str] | None) -> dict[str, str]:
    """Pin name -> the model id a run sends: the pins, with a ``--model-override`` applied (never the judge)."""
    pins = {"SONNET_MODEL": SONNET_MODEL, "HAIKU_MODEL": HAIKU_MODEL, "JUDGE_MODEL": JUDGE_MODEL}
    for pin, model in (model_overrides_map or {}).items():
        if pin in ("SONNET_MODEL", "HAIKU_MODEL"):
            pins[pin] = model
    return pins


def _usd_per_call(row: dict[str, Any], model: str) -> float:
    """Dollars for one call of the measured token means in ``row``, priced for ``model`` by `hardening`."""
    return compute_call_cost(
        {
            "model": model,
            "input_tokens": row["input"],
            "output_tokens": row["output"],
            "cache_creation_input_tokens": row["cache_write"],
            "cache_read_input_tokens": row["cache_read"],
        }
    )


@dataclass(frozen=True)
class SpendEstimate:
    """What a run is set to spend, priced from ``evals/catalog/costs.json``.

    A floor: retries and prompt-cache misses are not in it, and a kind with no measured tokens yet is
    listed in ``unmeasured`` and left out of ``total_usd`` (it is not priced at zero by accident).
    """

    calls: dict[str, int]
    conditional: dict[str, str]
    per_kind_usd: dict[str, float]
    unmeasured: tuple[str, ...]
    skipped_fixtures: tuple[str, ...]
    total_usd: float


def estimate_spend(
    fixtures: list[Path],
    rubrics: list[Path],
    *,
    mode: str,
    seed_mode: bool,
    model_overrides_map: dict[str, str] | None = None,
) -> SpendEstimate:
    """Price the call plan of a run. Reads ``costs.json`` once and parses one catalog entry per planned kind."""
    source = _check_mode(mode, has_seed=seed_mode, fixtures=fixtures)
    # Any seed source (global or per fixture) means no résumé file is read.
    calls, conditional, skipped = _call_plan(
        fixtures, rubrics, mode=mode, seed_mode=source != "none"
    )
    costs = eval_catalog.read_costs()
    pins = _pin_models(model_overrides_map)
    per_kind: dict[str, float] = {}
    unmeasured: list[str] = []
    for call, count in sorted(calls.items()):
        row = costs.get(call)
        if row is None:
            unmeasured.append(call)
            continue
        model = pins[eval_catalog.load(call).model_pin]
        per_kind[call] = round(_usd_per_call(row, model) * count, 6)
    return SpendEstimate(
        calls=calls,
        conditional=conditional,
        per_kind_usd=per_kind,
        unmeasured=tuple(unmeasured),
        skipped_fixtures=tuple(skipped),
        total_usd=round(sum(per_kind.values()), 6),
    )


def format_estimate(est: SpendEstimate, *, max_spend: float | None = None) -> str:
    """The estimate as the text ``--estimate`` prints."""
    lines = [f"{'call kind':34s} {'calls':>5s} {'$ (floor)':>10s}"]
    for call, count in sorted(est.calls.items()):
        priced = (
            f"{est.per_kind_usd[call]:10.4f}"
            if call in est.per_kind_usd
            else f"{'unmeasured':>10s}"
        )
        lines.append(f"{call:34s} {count:5d} {priced}")
    lines.append(f"{'total':34s} {sum(est.calls.values()):5d} {est.total_usd:10.4f}")
    lines.append("")
    lines.append(
        "This is a floor: retries and prompt-cache misses are not included, and the token means "
        "were measured on one machine's call log (python -m evals.eval_catalog measure)."
    )
    if est.unmeasured:
        lines.append(
            f"Not priced (no measured tokens yet, left out of the total): {', '.join(est.unmeasured)}."
        )
    for call, why in est.conditional.items():
        lines.append(f"May add calls, not counted: {call} ({why}).")
    if est.skipped_fixtures:
        lines.append(f"Will not load, no calls planned: {', '.join(est.skipped_fixtures)}.")
    if max_spend is not None:
        verdict = "OVER the cap" if est.total_usd > max_spend else "within the cap"
        lines.append(f"--max-spend ${max_spend:.4f}: the estimate is {verdict}.")
    return "\n".join(lines)


def format_catalog_list() -> str:
    """Every catalog entry, one line each, with its $/call at the current pins (the text ``--list`` prints)."""
    costs = eval_catalog.read_costs()
    pins = _pin_models(None)
    lines = [
        f"{'call kind':34s} {'status':8s} {'pin':13s} {'$/call':>8s}  groups / prompt",
    ]
    for call, entry in eval_catalog.load_all().items():
        row = costs.get(call)
        usd = f"{_usd_per_call(row, pins[entry.model_pin]):8.4f}" if row else f"{'-':>8s}"
        lines.append(
            f"{call:34s} {entry.status:8s} {entry.model_pin:13s} {usd}  "
            f"{','.join(entry.groups)} / {entry.prompt}"
        )
    return "\n".join(lines)


def _apply_simulated_edit(generated_resume: str, scenario: dict[str, Any]) -> tuple[str, bool]:
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
    fixture: dict[str, Any],
    context: ContextSet,
    analysis: dict[str, Any],
    iteration_questions: list[dict[str, Any]],
    iteration_reasoning: str,
    current_resume_text: str,
    current_cover_letter_text: str,
    recent_edits_summary: str,
    deterministic_signals: dict[str, Any],
    prior_clarifications: list[dict[str, Any]],
) -> dict[str, Any]:
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
    fixture: dict[str, Any],
    context: ContextSet,
    analysis: dict[str, Any],
    generate_result: dict[str, Any],
    clarify_questions: list[dict[str, Any]],
    clarify_answers: dict[str, Any],
    rubric_path: Path,
    run_id: str,
    det_metrics: dict[str, Any],
    elapsed_ms: int,
    case_offset: int,
) -> dict[str, Any] | None:
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
    from analyzer import LLMResponseError
    from hardening import compute_iteration_signals, summarize_recent_edits

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
            "jd_label": fixture["jd_label"],
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
            "prompt_version": effective_prompt_version(),
            "run_id": run_id,
            "deterministic_metrics": det_metrics,
            "cost_usd": _case_cost(case_offset),
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
    from typing import cast as _cast

    from hardening import ClarificationQuestion

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

    prior_clarifications: list[dict[str, Any]] = []
    for q in clarify_questions or []:
        ans = (clarify_answers.get(q.get("id", ""), "") or "").strip()
        if ans:
            prior_clarifications.append(
                {
                    "question": q.get("text", ""),
                    "answer": ans,
                    "kind": q.get("kind", ""),
                }
            )

    iter_status = "ok"
    iter_questions: list[dict[str, Any]] = []
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
    except Exception as exc:
        iter_status = "pipeline_error"
        iter_error = str(exc)

    if iter_status != "ok":
        return {
            "schema_version": SCHEMA_VERSION,
            "score_max": SCORE_MAX,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "eval",
            "fixture": fixture["name"],
            "jd_label": fixture["jd_label"],
            "rubric": rubric_path.stem,
            "score": None,
            "reasons": [f"clarify_iteration failed: {iter_error}"],
            "failed_rules": [],
            "status": iter_status,
            "prompt_version": effective_prompt_version(),
            "run_id": run_id,
            "deterministic_metrics": det_metrics,
            "cost_usd": _case_cost(case_offset),
            "pipeline_latency_ms": elapsed_ms,
        }

    payload = _iteration_payload(
        fixture=fixture,
        context=context,
        analysis=analysis,
        iteration_questions=iter_questions,
        iteration_reasoning=iter_reasoning,
        current_resume_text=edited_resume,
        current_cover_letter_text=generated_cover,
        recent_edits_summary=edits_summary,
        deterministic_signals=signals,
        prior_clarifications=prior_clarifications,
    )
    try:
        grade = _grade(client, rubric_path, payload, fixture_name=fixture["name"])
        grade.setdefault("status", "ok")
    except Exception as exc:
        grade = {"score": None, "reasons": [str(exc)], "status": "judge_error"}

    return {
        "schema_version": SCHEMA_VERSION,
        "score_max": SCORE_MAX,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "eval",
        "fixture": fixture["name"],
        "jd_label": fixture["jd_label"],
        "rubric": rubric_path.stem,
        "score": grade.get("score"),
        "reasons": grade.get("reasons", []),
        "failed_rules": grade.get("failed_rules", []),
        "status": grade.get("status", "ok"),
        "judge_request_id": grade.get("judge_request_id"),
        "prompt_version": effective_prompt_version(),
        "run_id": run_id,
        "deterministic_metrics": det_metrics,
        "cost_usd": _case_cost(case_offset),
        "pipeline_latency_ms": elapsed_ms,
        "iteration_scenario": scenario.get("name"),
        "iteration_questions_count": len(iter_questions),
    }


def _coerce_bullet_recommendations(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Shape ``recommend_bullets()``'s output into the ``llm_recommendations`` dict
    ``build_json_resume_from_corpus`` reads (``{str(experience_id): {"bullet_ids":
    [...], "rationale": str}}``).

    ``RecommendResponse.recommendations`` is typed ``Any`` (not a strict schema), so
    — mirroring ``blueprints.applications.recommend_application_bullets`` verbatim —
    this defensively strips a stray ``"e3"``/``"b12"`` id prefix the LLM sometimes
    echoes back instead of a bare int. Small response-shaping glue, not a
    reimplementation of any resolver: the resolver is ``build_json_resume_from_corpus``
    / ``freeze_approved_composition``, called unmodified in ``_run_assemble_pipeline``.
    """

    def _to_int(v: object) -> int | None:
        if v is None:
            return None
        s = str(v).strip().lstrip("eEbB")
        try:
            return int(s)
        except (TypeError, ValueError):
            return None

    by_exp: dict[str, dict[str, Any]] = {}
    for rec in result.get("recommendations", []) or []:
        eid_int = _to_int(rec.get("experience_id"))
        if eid_int is None:
            continue
        bullet_ids_int = [
            bi for bi in (_to_int(b) for b in (rec.get("bullet_ids") or [])) if bi is not None
        ]
        by_exp[str(eid_int)] = {
            "bullet_ids": bullet_ids_int,
            "rationale": (rec.get("rationale") or "").strip(),
        }
    return by_exp


def _run_assemble_pipeline(
    *,
    client: anthropic.Anthropic,
    session: Session,
    application: Any,
    context: ContextSet,
    analysis: dict[str, Any],
    username: str,
    run_id: str,
    capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``mode="assemble"``: build the generate()-shaped result via the REAL Compose
    -> freeze -> assemble path instead of calling ``analyzer.generate()``.

    Mirrors what a user does opening Compose: the auto-fired bullet + positioning-
    summary recommend calls (Haiku — ``analyzer.recommend_bullets`` /
    ``recommend_summaries``, the SAME functions the ``/recommend`` and
    ``/recommend-summary`` routes call), landing on the context exactly where
    ``corpus_to_json_resume.build_json_resume_from_corpus`` reads them
    (``llm_recommendations`` / ``llm_summary_recommendation``). Skill curation is
    left at its documented product default (no ``recommend-skills`` call -> ALL
    active, approved skills — the same fallback ``build_json_resume_from_corpus``
    uses when there is no recommendation; not an eval shortcut).

    Then freezes via ``corpus_to_json_resume.freeze_approved_composition`` — the
    exact function ``/api/applications/<id>/composition``'s Save-and-continue calls
    — and assembles via ``blueprints.generation._assemble_from_frozen_composition``,
    the exact function ``/api/generate`` calls once a composition is frozen. Zero
    résumé-body LLM calls. The cover letter is opted in (``with_cover_letter=True``)
    to keep parity with the legacy ``generate()`` call's own default — the one the
    runner's ``mode="generate"`` path relies on to have cover-letter material for the
    ``tone`` rubric — and is a real Sonnet call via ``generate_cover_letter_against_resume``.

    Raises ``RuntimeError`` when the frozen composition has no content (e.g. an
    empty corpus); the caller's existing ``except Exception`` pipeline-error handling
    covers it like any other pipeline failure.
    """
    from db.models import SummaryItem

    # `cs` is the SAME underlying dict as `context` (the cast is a type-checker
    # hint only, no copy) — used only where a key falls outside the ContextSet
    # TypedDict schema (`jd_text` / `summary_items` are transient, route-stashed
    # keys; see recommend_summaries's own docstring). Calls typed to accept
    # ContextSet specifically (recommend_bullets/_summaries, _frozen_composition,
    # _assemble_from_frozen_composition) pass `context` itself.
    cs = cast(dict[str, Any], context)
    candidate_id = int(application.candidate_id)
    application_id = int(application.id)

    # Mirror the /recommend route: stash the JD text the analyzer prompt reads
    # (recommend_bullets/_summaries read context_set["jd_text"]), pop it once done
    # so the transient key doesn't leak into the graded payload.
    cs["jd_text"] = cs.get("job_description", "")

    bullet_rec = recommend_bullets(client, context, username=username, run_id=run_id)
    cs["llm_recommendations"] = _coerce_bullet_recommendations(bullet_rec)

    summary_rows = (
        session.query(SummaryItem)
        .filter_by(candidate_id=candidate_id, is_active=1)
        .order_by(SummaryItem.display_order, SummaryItem.id)
        .all()
    )
    cs["summary_items"] = [
        {"id": r.id, "text": r.text, "label": r.label, "has_outcome": bool(r.has_outcome)}
        for r in summary_rows
    ]
    cs["llm_summary_recommendation"] = recommend_summaries(
        client, context, username=username, run_id=run_id
    )
    cs.pop("jd_text", None)
    cs.pop("summary_items", None)
    if capture is not None:
        # The recommend rationales are user-visible prose that this function otherwise discards;
        # the item 140 leak scan reads them from here.
        capture["bullets"] = bullet_rec
        capture["summaries"] = cs["llm_summary_recommendation"]

    cs["approved_composition"] = freeze_approved_composition(
        session,
        candidate_id,
        application_id=application_id,
        context_data=cs,
    )
    frozen_doc = _frozen_composition(context)
    if frozen_doc is None:
        raise RuntimeError("mode='assemble': frozen composition has no content (empty corpus?)")
    return _assemble_from_frozen_composition(
        client,
        context,
        analysis,
        frozen_doc,
        with_cover_letter=True,
        username=username,
        run_id=run_id,
    )


def run_suite(
    *,
    suite: str = "synthetic",
    subset: str = "full",
    fixture_name: str | None = None,
    seed_data: dict[str, Any] | None = None,
    mode: str = "generate",
    prompt_overrides_map: dict[str, str] | None = None,
    model_overrides_map: dict[str, str] | None = None,
    grounding_signals: bool = False,
    out_dir: str | Path | None = None,
    client: anthropic.Anthropic | None = None,
    progress: ProgressFn | None = None,
    cancel_check: Callable[[], bool] | None = None,
    max_spend_usd: float | None = None,
) -> EvalRunResult:
    """Run one eval suite — the importable core extracted from ``main()``.

    Takes structured args (no argparse) so both the CLI wrapper ``main()`` and the
    localhost ``POST /api/eval/run`` console route share one implementation, and
    writes per-grading JSONL records to ``out_dir/{timestamp}.jsonl`` exactly as
    before.

    The default invocation (no seed, no overrides, ``mode="generate"``,
    ``progress=None``) is **byte-identical** to the historical ``main()`` path:
    ``prompt_overrides({})`` is a no-op, ``effective_prompt_version()`` returns the
    real ``PROMPT_VERSION``, and every ``_emit`` below is a no-op — so the
    analyze→generate prompt cache and the result-record bytes are unchanged.
    ``mode="generate"`` never touches ``recommend_bullets`` / ``recommend_summaries``
    / ``freeze_approved_composition`` / the frozen-composition assembler at all.

    ``seed_data`` is an already-loaded + validated corpus seed (the caller owns the
    file I/O, so a bad path fails before any paid call). ``prompt_overrides_map`` is
    the already-parsed name→text mapping; an unknown prompt-constant name raises
    ``ValueError`` here, before the fixture loop. ``model_overrides_map`` is the
    already-parsed pin-name→candidate-model-id mapping (``{"SONNET_MODEL": "claude-sonnet-5-5"}``);
    `analyzer.model_overrides` validates it here, before any paid call, and every record
    the run writes then carries ``model_overrides`` and the models actually sent in
    ``model_snapshots``. The judge model is never overridden. A run under either override
    is a candidate run: `hardening.is_candidate_record` keeps it out of the regression
    baseline and the dashboard's baseline views. An unknown ``--fixture`` raises
    ``FileNotFoundError``. ``progress`` (optional) is invoked with
    ``(event, payload)`` at coarse milestones so a caller can stream progress; it
    never alters the result. ``cancel_check`` (optional) is polled before each
    remaining paid Anthropic call (start of a fixture, before clarify, before
    generate/assemble, before the distinctiveness judge, before each rubric
    grading call) — the first ``True`` reading stops the run early and the
    returned ``EvalRunResult.cancelled`` is ``True``. Already-written JSONL
    records are kept; nothing already billed is discarded.

    ``max_spend_usd`` (optional, ``None`` leaves the run byte-identical) is a spend cap read at the
    same polls: once the run's spend, read from the call log by trace id (judge calls included),
    reaches the cap, the next poll stops the run, ``cancelled`` is ``True`` and ``stop_reason`` is
    ``"max_spend"``. The polls sit at phase boundaries, so a run can overshoot by up to one phase of
    paid calls; the cap bounds when the NEXT phase starts, it does not abort a call in flight.

    ``mode`` (F-11, 2026-07 UX review): ``"generate"`` (default) is the historical
    LLM-generate path, unchanged. ``"assemble"`` drives the SAME Compose -> freeze ->
    assemble path corpus-mode ``/api/generate`` uses instead of calling
    ``analyzer.generate()`` for the résumé body — so the rubrics score the
    deterministically-assembled document users actually download, not the LLM
    fallback. ``mode="assemble"`` REQUIRES a corpus: ``seed_data`` (frozen-composition
    assembly needs a real corpus + candidate/application rows) or, with none, a
    ``seed.json`` in every selected fixture (the golden suite: each cell carries its own,
    imported into its own in-memory DB). It raises ``ValueError`` before any paid call
    when neither exists.
    Every JSONL record this run writes carries ``eval_mode`` (``"generate"`` or
    ``"assemble"``) so the dashboard/baseline tooling can tell the two populations
    apart; assemble-mode scores are never compared against ``baseline_v1.json``
    (measured on the generate-mode population) — ``baseline_comparison`` is always
    ``None`` and assemble-mode scores never contribute to the regression-gate
    ``exit_code`` (sub-threshold scores still count via ``n_fail``).
    """

    _check_mode_name(mode)

    def _emit(event: str, **payload: Any) -> None:
        if progress is not None:
            progress(event, payload)

    stop_reason: str | None = None
    spend_meter: _SpendMeter | None = None  # created once the run's trace exists, below

    def _cancelled() -> bool:
        nonlocal stop_reason
        if cancel_check is not None and cancel_check():
            stop_reason = "cancelled"
            return True
        if (
            spend_meter is not None
            and max_spend_usd is not None
            and spend_meter.poll() >= max_spend_usd
        ):
            stop_reason = "max_spend"
            logger.warning(
                "--max-spend $%.4f reached ($%.4f spent so far); stopping before the next paid phase",
                max_spend_usd,
                spend_meter.total_usd,
            )
            return True
        return False

    # Candidate prompt overrides: the caller (CLI ``main`` / console route) has
    # already read + shape-validated the mapping; here we validate the prompt-NAMES
    # once (an unknown constant raises ValueError) and surface the candidate:<hash>
    # tag the run is kept out of the baseline under — all before any paid LLM call. An empty map
    # is a no-op, so the default path stays byte-identical. ``seed_data`` arrives
    # pre-loaded from the caller (file I/O + schema validation already done).
    overrides: dict[str, str] = dict(prompt_overrides_map or {})
    candidate_version: str | None = None
    if overrides:
        with prompt_overrides(overrides):
            candidate_version = effective_prompt_version()
        logger.warning(
            "PROMPT OVERRIDES ACTIVE — keys=%s; this run is logged as "
            "prompt_version=%s (kept out of the regression baseline and the dashboard's "
            "baseline views).",
            sorted(overrides),
            candidate_version,
        )
    # Candidate MODELS: same fail-before-spend rule. Entering the manager once validates every
    # entry (unknown pin, no-op swap, no THINKING_POLICY or MODEL_PRICING entry -> ValueError);
    # the real context is entered around the fixture loop below.
    model_overrides_in_effect: dict[str, str] = dict(model_overrides_map or {})
    if model_overrides_in_effect:
        with model_overrides(model_overrides_in_effect):
            pass
        logger.warning(
            "MODEL OVERRIDES ACTIVE — %s; every record is stamped with model_overrides "
            "(kept out of the regression baseline and the dashboard's baseline views). "
            "The judge stays on %s.",
            model_overrides_in_effect,
            JUDGE_MODEL,
        )

    # Load static baseline data once for baseline_comparison fields on JSONL records.
    baseline_v1_data: dict[str, Any] = {}
    if BASELINE_JSON.exists():
        try:
            _bdata = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
            if _bdata.get("schema_version") == 3:
                baseline_v1_data = _bdata
        except (OSError, json.JSONDecodeError):
            pass

    anchor_version: str | None = "v1" if suite == "anchor" else None

    fixtures = _select_fixtures(suite, fixture_name)
    # Needs the fixtures (a golden cell carries its own seed), so it runs here: after the cheap
    # directory listing, before a client, a seed import or a paid call.
    seed_source = _seed_source(mode, has_seed=seed_data is not None, fixtures=fixtures)

    if not fixtures:
        logger.warning("No fixtures matched the selection")
        return EvalRunResult(0, None, 0, 0, [], [], candidate_version)

    rubrics = _select_rubrics(subset)
    rubric_versions = {rp: hashlib.sha256(rp.read_bytes()).hexdigest() for rp in rubrics}
    if not rubrics:
        logger.warning("No rubrics matched the selection")
        return EvalRunResult(0, None, 0, 0, [], [], candidate_version)

    # Every cell's seed is read and validated BEFORE a client exists, so a bad one fails the run
    # without a paid call (a ValueError, exit 1 from `main`).
    cell_seeds: dict[Path, dict[str, Any]] = {}
    if seed_source == "per_fixture":
        cell_seeds = {fdir: load_seed(fdir / "seed.json") for fdir in fixtures}

    logger.info(
        "Eval run: %d fixtures × %d rubrics = %d gradings (judge model: %s)",
        len(fixtures),
        len(rubrics),
        len(fixtures) * len(rubrics),
        JUDGE_MODEL,
    )

    client = client or _get_client()
    # None resolves to the module's RESULTS_DIR now, not at def time: a default bound at def time
    # ignored a patched RESULTS_DIR and let tests write stub runs into the real directory (item 179).
    out_dir = Path(RESULTS_DIR if out_dir is None else out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_path_for_baseline = out_dir / f"{timestamp}.jsonl"
    baseline = _load_baseline_scores(out_path_for_baseline)
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    if baseline:
        logger.info(
            "Regression-alert baseline: %d (fixture, rubric) pairs from prior runs (delta=%.1f)",
            len(baseline),
            REGRESSION_DELTA,
        )
    out_path = out_dir / f"{timestamp}.jsonl"

    n_pass = n_fail = 0

    # One trace per invocation (item 181). `run_offset` bounds the end-of-run spend scan to the rows
    # this run could have written; selection within it is by trace id.
    trace_id = call_identity.new_trace_id()
    run_offset = _log_offset()
    if max_spend_usd is not None:
        spend_meter = _SpendMeter(run_offset, trace_id)

    weights: dict[str, float] = {}
    if WEIGHTS_PATH.exists():
        weights = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))

    # The override context spans the whole fixture loop so every analyze/clarify/
    # generate call (and the iteration-cycle helper, via the ContextVar) sees the
    # candidate prompt and stamps the candidate:<hash> version. No-op when empty.
    with ExitStack() as stack:
        stack.enter_context(prompt_overrides(overrides))
        stack.enter_context(model_overrides(model_overrides_in_effect))
        out = stack.enter_context(out_path.open("a", encoding="utf-8"))
        # Seed mode: one shared in-memory corpus DB for the entire fixture loop.
        # build_context_set_from_db mints a fresh application/run per call (unique
        # run_id), so the accumulation across fixtures is harmless (never read back).
        session: Session | None = None
        seed_username: str | None = None
        if seed_source == "global":
            assert seed_data is not None
            session, seed_username = stack.enter_context(seeded_session(seed_data))
        # Per-cell seeds: each fixture gets its own corpus, closed before the next one is opened (and
        # when the run ends). A reusable ExitStack because the loop body is too long to re-indent
        # under a `with`.
        cell_session_stack = ExitStack()
        stack.callback(cell_session_stack.close)
        total_fixtures = len(fixtures)
        cancelled = False
        for index, fdir in enumerate(fixtures):
            if _cancelled():
                cancelled = True
                logger.info(
                    "Eval run cancelled before fixture %d/%d started", index, total_fixtures
                )
                break
            try:
                if seed_source == "per_fixture":
                    cell_session_stack.close()  # the previous cell's corpus
                    session, seed_username = cell_session_stack.enter_context(
                        seeded_session(cell_seeds[fdir])
                    )
                fixture = _load_fixture(
                    fdir,
                    seed_mode=seed_source != "none",
                    seed_path=fdir / "seed.json" if seed_source == "per_fixture" else None,
                )
            except Exception as exc:
                logger.error("Fixture load failed: %s — %s", fdir.name, exc)
                continue
            _emit(
                "fixture_start",
                fixture=fixture["name"],
                index=index,
                total=total_fixtures,
            )

            # One run_id per fixture pipeline so the analyze + generate calls
            # share an ID. Lands in logs/llm_calls.jsonl AND on every per-rubric
            # eval result, letting the dashboard correlate which LLM calls
            # produced which graded output.
            run_id = uuid.uuid4().hex[:12]
            logger.info(
                "Fixture %s: building context + running pipeline (run_id=%s)",
                fixture["name"],
                run_id,
            )
            t0 = time.perf_counter()
            # The case (fixture) span: every product and judge call below is its child. Entered on the
            # run's ExitStack (the loop body is too long to re-indent under a `with`), so each fixture's
            # context replaces the previous one and all of them unwind, newest first, when the run ends.
            case_span_id = call_identity.new_span_id()
            stack.enter_context(
                trace_context(
                    trace_id,
                    case_id=f"{_suite_of(fdir)}/{fixture['name']}",
                    parent_span_id=case_span_id,
                )
            )
            case_offset = _log_offset()
            # clarify_questions is captured separately because the clarify
            # step is opt-in in production and we want the eval to keep
            # producing scores for the existing rubrics even if clarify
            # fails for some reason.
            clarify_questions: list[dict[str, Any]] = []
            clarify_reasoning = ""
            clarify_error: str | None = None
            recommend_capture: dict[str, Any] = {}
            _t_analyze: float | None = None
            _t_clarify: float | None = None
            _t_generate: float | None = None
            _t_generate_end: float | None = None
            seed_application: Any = None
            try:
                if seed_source != "none":
                    assert session is not None and seed_username is not None
                    context, seed_application = _build_context_from_seed(
                        session,
                        candidate_username=seed_username,
                        jd_text=fixture["jd"],
                        run_id=run_id,
                    )
                else:
                    context = _build_context(fixture)
                _t_analyze = time.perf_counter()
                _emit("analyzing", fixture=fixture["name"], index=index, total=total_fixtures)
                analysis = analyze(
                    client,
                    context,
                    username=f"eval:{fixture['name']}",
                    run_id=run_id,
                )
                if _cancelled():
                    cancelled = True
                    logger.info(
                        "Eval run cancelled after analyze for %s, before clarify",
                        fixture["name"],
                    )
                    break
                _t_clarify = time.perf_counter()
                _emit("clarifying", fixture=fixture["name"], index=index, total=total_fixtures)
                try:
                    clarify_result = clarify(
                        client,
                        context,
                        analysis,
                        username=f"eval:{fixture['name']}",
                        run_id=run_id,
                    )
                    clarify_questions = clarify_result.get("questions", [])
                    clarify_reasoning = clarify_result.get("reasoning", "")
                except Exception as exc:
                    # Non-fatal: degrade to score=None for the clarification
                    # rubric while still running generate + the other rubrics.
                    clarify_error = str(exc)
                    logger.warning(
                        "Clarify step failed for %s, continuing without it: %s",
                        fixture["name"],
                        exc,
                    )
                if _cancelled():
                    cancelled = True
                    logger.info(
                        "Eval run cancelled after clarify for %s, before generate",
                        fixture["name"],
                    )
                    break
                _t_generate = time.perf_counter()
                if mode == "assemble":
                    _emit("assembling", fixture=fixture["name"], index=index, total=total_fixtures)
                    assert session is not None and seed_application is not None
                    result = _run_assemble_pipeline(
                        client=client,
                        session=session,
                        application=seed_application,
                        context=context,
                        analysis=analysis,
                        username=f"eval:{fixture['name']}",
                        run_id=run_id,
                        capture=recommend_capture,
                    )
                else:
                    _emit("generating", fixture=fixture["name"], index=index, total=total_fixtures)
                    result = generate(
                        client,
                        context,
                        analysis,
                        username=f"eval:{fixture['name']}",
                        run_id=run_id,
                    )
                _t_generate_end = time.perf_counter()
            except Exception as exc:
                logger.error("Pipeline failed for %s: %s", fixture["name"], exc)
                out.write(
                    json.dumps(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "score_max": SCORE_MAX,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "eval",
                            "fixture": fixture["name"],
                            "jd_label": fixture["jd_label"],
                            "rubric": None,
                            "score": None,
                            "status": "pipeline_error",
                            "error": str(exc),
                            "run_id": run_id,
                            "prompt_version": effective_prompt_version(),
                            "anchor_version": anchor_version,
                            "suite": suite,
                            "fixture_hash": fixture["hash"],
                            "rubric_version": None,
                            **_model_provenance_fields(),
                            **_trace_fields(),
                            "baseline_comparison": None,
                            "phase_latencies_ms": None,
                            "eval_mode": mode,
                        }
                    )
                    + "\n"
                )
                n_fail += 1
                continue

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            phase_latencies_ms = {
                "analyze": int((_t_clarify - _t_analyze) * 1000)
                if (_t_analyze and _t_clarify)
                else None,
                "clarify": int((_t_generate - _t_clarify) * 1000)
                if (_t_clarify and _t_generate)
                else None,
                "generate": int((_t_generate_end - _t_generate) * 1000)
                if (_t_generate and _t_generate_end)
                else None,
            }
            logger.info("  pipeline %s done in %dms", fixture["name"], elapsed_ms)
            if clarify_error is None:
                exp_probes = sum(
                    1 for q in clarify_questions if q.get("kind") == "experience_probe"
                )
                ctx_probes = sum(1 for q in clarify_questions if q.get("kind") == "context_probe")
                scope_probes = sum(1 for q in clarify_questions if q.get("kind") == "scope_probe")
                logger.info(
                    "  clarify produced %d questions (%d experience, %d context, %d scope probes)",
                    len(clarify_questions),
                    exp_probes,
                    ctx_probes,
                    scope_probes,
                )

            # Compute post-generation deterministic metrics. These ride along on
            # every per-rubric record AND get passed to the judge as part of
            # `deterministic_analysis` — the grounding rubric explicitly cites
            # missing_samples as evidence of fabrication.
            sources = [context["resume"]["text"]]
            for sup in context.get("supplemental_resumes", []):
                if sup.get("text"):
                    sources.append(sup["text"])
            # The L0 fabricated-specifics check scores against the dynamic union
            # (primary + supplementals + clarification answers); the other
            # metrics keep using `sources` so their baselines are unperturbed.
            source_union = assemble_source_union(context)
            det_metrics = _post_generation_metrics(
                result.get("resume_content", ""),
                result.get("cover_letter_content", ""),
                sources,
                jd_keywords=context["deterministic_analysis"]["jd_keywords"],
                source_union=source_union,
            )
            if _cancelled():
                cancelled = True
                logger.info(
                    "Eval run cancelled after generate for %s, before distinctiveness scoring",
                    fixture["name"],
                )
                break
            det_metrics["distinctiveness"] = _score_distinctiveness(
                client,
                result.get("resume_content", ""),
                context["job_description"],
                fixture_name=fixture["name"],
            )
            cost_usd = _case_cost(case_offset)
            logger.info(
                "  metrics: verb_diversity=%.2f density=%.2f grounding_overlap=%.2f"
                " top_third_density=%.2f quantification_rate=%.2f"
                " fabricated_specifics=%.2f cost=$%.4f",
                det_metrics["verb_diversity"]["diversity_ratio"],
                det_metrics["specificity_density"]["density"],
                det_metrics["grounding_overlap"]["overlap_ratio"],
                det_metrics["top_third_density"]["density"],
                det_metrics["quantification_rate"]["rate"],
                det_metrics["fabricated_specifics"]["fabricated_specifics_rate"],
                cost_usd,
            )

            leak_report = _leak_report(
                context=context,
                analysis=analysis,
                clarify_questions=clarify_questions,
                clarify_reasoning=clarify_reasoning,
                result=result,
                capture=recommend_capture,
                run_date=date.today(),
            )
            logger.info(
                "  leaked_handles: %d found (of %d shipped); letter_date=%s",
                leak_report["total"],
                leak_report["handles_shipped"],
                leak_report["letter_date"]["found"],
            )

            payload_det = dict(context["deterministic_analysis"])
            payload_det["post_generation"] = det_metrics

            grounding_signals_data: dict[str, Any] | None = None
            if grounding_signals:
                from evals.grounding_signals import run_grounding_signals

                try:
                    grounding_signals_data = run_grounding_signals(
                        result.get("resume_content", ""),
                        sources,
                    )
                except Exception as exc:
                    # Grounding is an OPTIONAL enhancement layered on top of the
                    # already-completed (and paid) analyze/clarify/generate work
                    # above — a scorer failure (a drifted dep, a low-RAM host
                    # failing the MiniCheck load, missing [eval-grounding]
                    # extras) must NEVER discard that work or abort the rest of
                    # the run. Degrade to an un-scored fixture and keep going —
                    # same contract as evals/bootstrap.py's
                    # build_bootstrap_document() (EV-2, window-8.5-findings).
                    logger.warning(
                        "Grounding signals scoring failed for %s; continuing without it: %s",
                        fixture["name"],
                        exc,
                        exc_info=True,
                    )
                    _emit(
                        "warning",
                        fixture=fixture["name"],
                        index=index,
                        total=total_fixtures,
                        message=f"Grounding signals failed for {fixture['name']}: {exc}",
                    )
                    grounding_signals_data = None
                else:
                    logger.info(
                        "  grounding_signals: %d bullets  nli_mean=%.3f contradictions=%d"
                        "  minicheck_mean=%.3f low_scores=%d",
                        grounding_signals_data["bullet_count"],
                        grounding_signals_data["nli_summary"]["mean_entailment"],
                        grounding_signals_data["nli_summary"]["contradiction_count"],
                        grounding_signals_data["minicheck_summary"]["mean_score"],
                        grounding_signals_data["minicheck_summary"]["low_score_count"],
                    )
                    # Layer L1/L2 into the composite in place — det_metrics is
                    # embedded by reference in every record write, so this enriches
                    # all downstream records for this fixture at once.
                    _enrich_groundedness(det_metrics["groundedness"], grounding_signals_data)

                    # RH-1 (2026-07 e2e-run-health-review): persist the grounding
                    # signals just computed back into the fixture's
                    # annotations.json — before this, they landed in every JSONL
                    # result record above but never made it back to the
                    # ground-truth file the Annotate tab edits. `fdir` IS
                    # ANNOTATION_ROOT/<slug> for a `--suite real --fixture <slug>`
                    # run (evals/fixtures/real/ == blueprints.diagnostics's
                    # ANNOTATION_ROOT), so this only ever fires for a real
                    # fixture that already has an annotations.json; best-effort
                    # + non-raising (see patch_grounding_scores_by_text).
                    ann_path = fdir / "annotations.json"
                    if ann_path.exists():
                        from evals.annotation import patch_grounding_scores_by_text

                        patched = patch_grounding_scores_by_text(ann_path, grounding_signals_data)
                        if patched:
                            logger.info(
                                "  persisted grounding signals into %s "
                                "(%d annotation item(s) matched by bullet text)",
                                ann_path.as_posix(),
                                patched,
                            )

            fixture_scores: dict[str, float] = {}

            for rubric_path in rubrics:
                if _cancelled():
                    cancelled = True
                    logger.info(
                        "Eval run cancelled mid-rubric-grading for %s (before %s)",
                        fixture["name"],
                        rubric_path.stem,
                    )
                    break
                # Skip judge entirely when clarify failed AND this is the
                # clarification_quality rubric — emit a pipeline_error row so
                # the dashboard surfaces it, but don't waste a judge call.
                if rubric_path.stem == "clarification_quality" and clarify_error is not None:
                    out.write(
                        json.dumps(
                            {
                                "schema_version": SCHEMA_VERSION,
                                "score_max": SCORE_MAX,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "source": "eval",
                                "fixture": fixture["name"],
                                "jd_label": fixture["jd_label"],
                                "rubric": rubric_path.stem,
                                "score": None,
                                "reasons": [f"clarify step failed: {clarify_error}"],
                                "failed_rules": [],
                                "status": "pipeline_error",
                                "prompt_version": effective_prompt_version(),
                                "run_id": run_id,
                                "deterministic_metrics": det_metrics,
                                "leaked_handles": leak_report,
                                "cost_usd": cost_usd,
                                "pipeline_latency_ms": elapsed_ms,
                                "anchor_version": anchor_version,
                                "suite": suite,
                                "fixture_hash": fixture["hash"],
                                "rubric_version": rubric_versions.get(rubric_path),
                                **_model_provenance_fields(),
                                **_trace_fields(),
                                "baseline_comparison": None,
                                "phase_latencies_ms": phase_latencies_ms,
                                "grounding_signals": grounding_signals_data,
                                "eval_mode": mode,
                            }
                        )
                        + "\n"
                    )
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
                        case_offset=case_offset,
                    )
                    if iter_record is None:
                        # Fixture has no iteration_scenarios — silently skip,
                        # mirroring how the dashboard's heatmap handles N/A cells.
                        continue
                    iter_score = iter_record.get("score")
                    # F-11: assemble-mode scores are a different content-generation
                    # population than the generate-mode baseline — never attribute a
                    # baseline delta to them (see run_suite's mode docstring).
                    iter_baseline_comparison = (
                        _compute_baseline_comparison(
                            fixture["name"],
                            rubric_path.stem,
                            iter_score if isinstance(iter_score, (int, float)) else None,
                            baseline_v1_data,
                        )
                        if mode != "assemble"
                        else None
                    )
                    iter_record.update(
                        {
                            "anchor_version": anchor_version,
                            "suite": suite,
                            "fixture_hash": fixture["hash"],
                            "rubric_version": rubric_versions.get(rubric_path),
                            **_model_provenance_fields(),
                            **_trace_fields(),
                            "baseline_comparison": iter_baseline_comparison,
                            "phase_latencies_ms": phase_latencies_ms,
                            "grounding_signals": grounding_signals_data,
                            "eval_mode": mode,
                        }
                    )
                    out.write(json.dumps(iter_record) + "\n")
                    if isinstance(iter_score, (int, float)) and iter_score >= PASS_THRESHOLD:
                        n_pass += 1
                        verdict = "pass"
                    else:
                        n_fail += 1
                        verdict = "fail"
                    logger.info(
                        "  %s × iteration_quality → score=%s (%s)",
                        fixture["name"],
                        iter_score,
                        verdict,
                    )
                    # F-11: assemble-mode scores never feed the regression gate —
                    # baseline_v1.json was measured on the generate-mode population.
                    if mode != "assemble" and isinstance(iter_score, (int, float)):
                        delta = _detect_regression(
                            fixture["name"],
                            rubric_path.stem,
                            float(iter_score),
                            baseline,
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
                    grade = _grade(client, rubric_path, payload, fixture_name=fixture["name"])
                    grade.setdefault("status", "ok")
                except Exception as exc:
                    logger.error(
                        "Grading failed for %s × %s: %s",
                        fixture["name"],
                        rubric_path.stem,
                        exc,
                    )
                    grade = {"score": None, "reasons": [str(exc)], "status": "judge_error"}

                _score = grade.get("score")
                if isinstance(_score, (int, float)) and grade.get("status") != "judge_error":
                    fixture_scores[rubric_path.stem] = float(_score)
                # F-11: assemble-mode scores are a different content-generation
                # population than the generate-mode baseline — never attribute a
                # baseline delta to them (see run_suite's mode docstring).
                baseline_comparison = (
                    _compute_baseline_comparison(
                        fixture["name"],
                        rubric_path.stem,
                        _score if isinstance(_score, (int, float)) else None,
                        baseline_v1_data,
                    )
                    if mode != "assemble"
                    else None
                )
                record = {
                    "schema_version": SCHEMA_VERSION,
                    "score_max": SCORE_MAX,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "eval",
                    "fixture": fixture["name"],
                    "jd_label": fixture["jd_label"],
                    "rubric": rubric_path.stem,
                    "score": _score,
                    "reasons": grade.get("reasons", []),
                    "failed_rules": grade.get("failed_rules", []),
                    "status": grade.get("status", "ok"),
                    "judge_request_id": grade.get("judge_request_id"),
                    "prompt_version": effective_prompt_version(),
                    "run_id": run_id,
                    "deterministic_metrics": det_metrics,
                    "leaked_handles": leak_report,
                    "cost_usd": cost_usd,
                    "pipeline_latency_ms": elapsed_ms,
                    "anchor_version": anchor_version,
                    "suite": suite,
                    "fixture_hash": fixture["hash"],
                    "rubric_version": rubric_versions.get(rubric_path),
                    **_model_provenance_fields(),
                    **_trace_fields(),
                    "baseline_comparison": baseline_comparison,
                    "phase_latencies_ms": phase_latencies_ms,
                    "grounding_signals": grounding_signals_data,
                    "eval_mode": mode,
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
                    fixture["name"],
                    rubric_path.stem,
                    score,
                    verdict,
                )
                _emit(
                    "rubric_done",
                    fixture=fixture["name"],
                    rubric=rubric_path.stem,
                    score=score,
                    status=record.get("status"),
                    verdict=verdict,
                )

                # F-11: assemble-mode scores never feed the regression gate —
                # baseline_v1.json was measured on the generate-mode population.
                if (
                    mode != "assemble"
                    and isinstance(score, (int, float))
                    and record.get("status") != "judge_error"
                ):
                    delta = _detect_regression(
                        fixture["name"],
                        rubric_path.stem,
                        float(score),
                        baseline,
                    )
                    if delta is not None:
                        if delta["is_regression"]:
                            regressions.append(delta)
                            logger.warning(
                                "REGRESSION: %s × %s dropped %.1f → %.1f (Δ=%+.1f) "
                                "vs prior run (prompt_version=%s, %s)",
                                delta["fixture"],
                                delta["rubric"],
                                delta["prev_score"],
                                delta["new_score"],
                                delta["delta"],
                                delta["prev_prompt_version"] or "unknown",
                                delta["prev_timestamp"][:19] if delta["prev_timestamp"] else "—",
                            )
                        elif delta["is_improvement"]:
                            improvements.append(delta)

            if cancelled:
                break

            # Compute and write one eval_composite record per fixture.
            # Weighted average of available (non-error) rubric scores using
            # callback_weights.json. Uses only rubrics that were actually run
            # and scored; missing rubrics (e.g. smoke skips all but grounding)
            # are excluded from both numerator and denominator.
            if weights and fixture_scores:
                total_weight = sum(weights[r] for r in fixture_scores if r in weights)
                if total_weight > 0:
                    weighted_sum = sum(
                        fixture_scores[r] * weights[r] for r in fixture_scores if r in weights
                    )
                    eval_composite: float | None = round(weighted_sum / total_weight, 3)
                else:
                    eval_composite = None
            else:
                eval_composite = None
            out.write(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "eval",
                        "fixture": fixture["name"],
                        "jd_label": fixture["jd_label"],
                        "rubric": "eval_composite",
                        "score": eval_composite,
                        "run_id": run_id,
                        "prompt_version": effective_prompt_version(),
                        "weights_used": weights,
                        "scores_used": fixture_scores,
                        "anchor_version": anchor_version,
                        "suite": suite,
                        "fixture_hash": fixture["hash"],
                        **_model_provenance_fields(),
                        **_trace_fields(),
                        # Complete here, unlike on the per-rubric records written while later rubrics
                        # were still to be graded: the case's judge spend, by id (item 181).
                        "judge_cost_usd": _case_cost(case_offset, judge=True),
                        "phase_latencies_ms": phase_latencies_ms,
                        "eval_mode": mode,
                    }
                )
                + "\n"
            )
            logger.info(
                "  %s → eval_composite=%.3f (from %d rubrics)",
                fixture["name"],
                eval_composite if eval_composite is not None else 0.0,
                len(fixture_scores),
            )
            _emit(
                "fixture_done",
                fixture=fixture["name"],
                index=index,
                total=total_fixtures,
                eval_composite=eval_composite,
            )

    logger.info(
        "Eval %s: %d pass, %d fail. Results: %s",
        "cancelled" if cancelled else "complete",
        n_pass,
        n_fail,
        out_path,
    )

    # RH-2 (2026-07 e2e-run-health-review): a run whose fixture loop wrote ZERO
    # result records (every matched fixture failed `_load_fixture` or the grade
    # loop — e.g. via the #15 anchor-JD bug, or every rubric was
    # iteration_quality against fixtures with no scenarios) used to leave a
    # silent 0-byte `out_path` with no error trace on disk — the
    # `20260709_014042Z.jsonl` finding. Fail loudly instead of reporting success
    # against nothing: delete the empty file and raise, so the CLI `main()` /
    # console SSE routes (`/api/eval/run`, `/api/tune/run` — both already wrap
    # run_suite in try/except) surface a real error instead of a phantom
    # "0 pass / 0 fail" done event.
    # A cancellation can also leave a zero-byte file (e.g. cancelled before the
    # first fixture even started) — that is an intentional early stop, not the
    # RH-2 silent-failure case this guard exists to catch, so skip the raise.
    if n_pass == 0 and n_fail == 0 and out_path.exists() and out_path.stat().st_size == 0:
        out_path.unlink(missing_ok=True)
        if not cancelled:
            raise RuntimeError(
                f"Eval run wrote zero result records (suite={suite!r} subset={subset!r}"
                f"{f' fixture={fixture_name!r}' if fixture_name else ''}) — every matched "
                "fixture failed to load or grade; see the log above for the per-fixture "
                "error. No empty results file was left on disk."
            )

    # Regression summary — concise, only printed when there's something to say.
    if regressions or improvements:
        logger.info("--- Regression check vs previous runs (delta=%.1f) ---", REGRESSION_DELTA)
        for d in regressions:
            logger.info(
                "  ✗ %s × %s: %.1f → %.1f (Δ=%+.1f)",
                d["fixture"],
                d["rubric"],
                d["prev_score"],
                d["new_score"],
                d["delta"],
            )
        for d in improvements:
            logger.info(
                "  ✓ %s × %s: %.1f → %.1f (Δ=%+.1f)",
                d["fixture"],
                d["rubric"],
                d["prev_score"],
                d["new_score"],
                d["delta"],
            )
        if regressions:
            logger.warning(
                "Found %d regression(s) ≥%.1f points. Inspect dashboard heatmap "
                "and check `failed_rules` for the affected (fixture, rubric) pairs.",
                len(regressions),
                REGRESSION_DELTA,
            )

    exit_code = 0 if (n_fail == 0 and not regressions) else 2
    if stop_reason == "max_spend":
        exit_code = EXIT_OVER_BUDGET
    # Run totals from the log by trace id, so they hold on every path (a pipeline error, a cancel)
    # and count the judge calls `cost_usd` leaves out by design.
    generation_usd, judge_usd = _trace_cost(run_offset, trace_id)
    return EvalRunResult(
        exit_code=exit_code,
        out_path=out_path,
        n_pass=n_pass,
        n_fail=n_fail,
        regressions=regressions,
        improvements=improvements,
        candidate_version=candidate_version,
        cancelled=cancelled,
        trace_id=trace_id,
        judge_cost_usd=judge_usd,
        total_cost_usd=round(generation_usd + judge_usd, 6),
        stop_reason=stop_reason,
    )


def _max_spend_arg(text: str) -> float:
    """argparse type for ``--max-spend``: a finite, non-negative dollar amount."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a dollar amount") from None
    if not 0.0 <= value < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} must be a finite amount, 0 or more")
    return value


def main(argv: list[str] | None = None) -> int:
    """Thin argparse wrapper over ``run_suite`` — preserves the CLI contract.

    Parses flags, performs the CLI-only file I/O (read + shape-validate the
    ``--prompt-overrides`` JSON; eager-load + validate the ``--seed`` corpus), then
    delegates to ``run_suite`` and returns its exit code. The no-flag invocation is
    byte-identical to the historical behavior.
    """
    # Windows console fix (EV-3 class): force UTF-8 so --help (the `→` epilog) and
    # any non-cp1252 progress char don't raise UnicodeEncodeError under a cp1252
    # console. Mirrors scripts/export_corpus_seed.py + capture_screenshots.py.
    for _stream in (sys.stdout, sys.stderr):
        # suppress on a non-reconfigurable stream (e.g. piped)
        with suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description="sartor. eval harness")
    ap.add_argument(
        "--suite",
        choices=["synthetic", "real", "all", "anchor", "exploration", "golden-v1"],
        default="synthetic",
    )
    ap.add_argument("--subset", choices=["smoke", "full"], default="full")
    ap.add_argument("--fixture", help="Run a single named fixture (overrides --suite)")
    ap.add_argument("--out-dir", default=str(RESULTS_DIR))
    ap.add_argument(
        "--grounding-signals",
        action="store_true",
        default=False,
        help=(
            "Run DeBERTa NLI + MiniCheck-FT5 offline grounding scorers per bullet. "
            "Requires: pip install -e '.[eval-grounding]' (see CONTRIBUTING.md). "
            "First run downloads ~3.2 GB of model weights to the HuggingFace cache."
        ),
    )
    ap.add_argument(
        "--prompt-overrides",
        metavar="PATH",
        help=(
            "Path to a JSON file mapping a system-prompt constant name "
            "(e.g. SYSTEM_PROMPT, CLARIFY_SYSTEM_PROMPT) to candidate override "
            "text. Injects the candidate prompt for THIS run only — analyzer.py is "
            "never edited and the run is logged as prompt_version 'candidate:<hash>' "
            "so the regression baseline and the dashboard's baseline views leave it out. "
            "Omit for the byte-identical default path."
        ),
    )
    ap.add_argument(
        "--model-override",
        action="append",
        default=[],
        metavar="PIN=MODEL_ID",
        help=(
            "Send a CANDIDATE model in place of a pin for THIS run only, e.g. "
            "SONNET_MODEL=claude-sonnet-5-5 (repeatable; pins: SONNET_MODEL, HAIKU_MODEL). "
            "analyzer.py is never edited and the judge stays on its own model. The target must "
            "already have a THINKING_POLICY and a MODEL_PRICING entry or the run is refused "
            "before any paid call. Every record carries model_overrides, and the run is kept "
            "out of the regression baseline and the dashboard's baseline views. Omit for the "
            "byte-identical default path."
        ),
    )
    ap.add_argument(
        "--seed",
        metavar="PATH",
        help=(
            "Path to a corpus seed.json (from scripts.export_corpus_seed). Builds "
            "each fixture's context via build_context_set_from_db over an in-memory "
            "SQLite import of the seed — the REAL corpus→context product path — "
            "instead of parsing the fixture's resume file. The fixture's jd.txt + "
            "expected.json still drive grading. Omit for the byte-identical "
            "file-based path."
        ),
    )
    ap.add_argument(
        "--mode",
        choices=["generate", "assemble"],
        default="generate",
        help=(
            "F-11 (2026-07 UX review): 'generate' (default) is the historical "
            "analyzer.generate() LLM path, byte-identical to before. 'assemble' "
            "drives the SAME Compose -> freeze -> assemble path corpus-mode "
            "/api/generate uses (recommend_bullets/recommend_summaries -> "
            "freeze_approved_composition -> deterministic assemble, zero "
            "résumé-body LLM calls) so the rubrics score the assembled document "
            "users actually download. REQUIRES --seed, or a seed.json in every selected "
            "fixture (the golden-v1 suite). Every JSONL record carries "
            "eval_mode; assemble-mode scores are never regression-gated against "
            "baseline_v1.json (a different, generate-mode population)."
        ),
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help=(
            "Print the eval catalog (one line per LLM call kind: status, model pin, prompt, groups, "
            "measured $ per call) and exit 0. Reads no key and builds no client."
        ),
    )
    ap.add_argument(
        "--estimate",
        action="store_true",
        help=(
            "Print what the selected run is set to spend, per call kind, priced from "
            "evals/catalog/costs.json, and exit 0 without a key or a client. A floor: retries and "
            "prompt-cache misses are not included, and a kind with no measured tokens yet is listed "
            "as unmeasured and left out of the total."
        ),
    )
    ap.add_argument(
        "--max-spend",
        type=_max_spend_arg,
        metavar="USD",
        help=(
            "Spend cap in dollars. Refuses the run (exit 4, nothing spent) when the estimate is over "
            "it; during the run, stops before the next paid phase once the spend, read from the call "
            "log by trace id (judge calls included), reaches it (exit 4). The check runs at phase "
            "boundaries, so a run can overshoot by up to one phase of paid calls."
        ),
    )
    args = ap.parse_args(argv)

    if args.list:
        try:
            print(format_catalog_list())
        except eval_catalog.CatalogError as exc:
            logger.error("%s", exc)
            return 1
        return 0

    # --prompt-overrides: read + shape-validate the file here (a CLI-file concern);
    # the prompt-NAME validation happens once inside run_suite, before any paid call.
    overrides: dict[str, str] = {}
    if args.prompt_overrides:
        ov_path = Path(args.prompt_overrides)
        try:
            loaded = json.loads(ov_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Could not read --prompt-overrides %s: %s", ov_path, exc)
            return 1
        if not isinstance(loaded, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in loaded.items()
        ):
            logger.error(
                "--prompt-overrides must be a JSON object mapping prompt-name "
                "(string) -> override text (string): %s",
                ov_path,
            )
            return 1
        overrides = loaded

    # --model-override PIN=ID (repeatable): shape-check here; the pin NAME and the target's
    # policy/price are validated once inside run_suite, before any paid call.
    model_override_map: dict[str, str] = {}
    for item in args.model_override:
        pin, sep, target = item.partition("=")
        if not sep or not pin.strip() or not target.strip():
            logger.error("--model-override must look like PIN=MODEL_ID (got %r)", item)
            return 1
        if pin.strip() in model_override_map:
            logger.error("--model-override given twice for %s", pin.strip())
            return 1
        model_override_map[pin.strip()] = target.strip()

    # --seed: eager-load + validate the corpus seed (bad path / JSON / schema → 1)
    # before any paid LLM call. Absent → seed_data=None and the file-based path is
    # byte-identical.
    seed_data: dict[str, Any] | None = None
    if args.seed:
        try:
            seed_data = load_seed(args.seed)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error("Could not load --seed %s: %s", args.seed, exc)
            return 1
        logger.warning(
            "SEED MODE ACTIVE — corpus from %s (candidate=%s, schema v%s); fixture "
            "resume files are ignored, JD + expected.json still grade.",
            args.seed,
            seed_data.get("candidate_username"),
            seed_data.get("seed_schema_version"),
        )

    # --estimate / --max-spend: price the plan BEFORE a client or a key exists. The same pre-spend
    # validation run_suite does (an unknown --fixture, a bad --mode/--seed pair, a --model-override
    # with no policy or price) fails here with exit 1, not after a paid call.
    if args.estimate or args.max_spend is not None:
        try:
            if model_override_map:
                with model_overrides(model_override_map):
                    pass
            estimate = estimate_spend(
                _select_fixtures(args.suite, args.fixture),
                _select_rubrics(args.subset),
                mode=args.mode,
                seed_mode=seed_data is not None,
                model_overrides_map=model_override_map,
            )
        except (
            FileNotFoundError,
            ValueError,
        ) as exc:  # unknown fixture; bad mode, override or catalog
            logger.error("%s", exc)
            return 1
        print(format_estimate(estimate, max_spend=args.max_spend))
        if args.estimate:
            return 0
        if estimate.total_usd > args.max_spend:
            logger.error(
                "The estimate ($%.4f) is over --max-spend ($%.4f); nothing was run.",
                estimate.total_usd,
                args.max_spend,
            )
            return EXIT_OVER_BUDGET

    try:
        result = run_suite(
            suite=args.suite,
            subset=args.subset,
            fixture_name=args.fixture,
            seed_data=seed_data,
            mode=args.mode,
            prompt_overrides_map=overrides,
            model_overrides_map=model_override_map,
            grounding_signals=args.grounding_signals,
            out_dir=args.out_dir,
            max_spend_usd=args.max_spend,
        )
    except FileNotFoundError as exc:  # unknown --fixture
        logger.error("%s", exc)
        return 1
    except ValueError as exc:  # unknown prompt-override constant name, or bad --mode/--seed combo
        logger.error("%s", exc)
        return 1
    except RuntimeError as exc:  # RH-2: zero-result-record run (empty-file guard)
        logger.error("%s", exc)
        return 1
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
