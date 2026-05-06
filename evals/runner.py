"""Resume Optimizer eval harness.

Loads synthetic and/or real fixtures, runs the full analyze + generate
pipeline against each, dispatches per-rubric grading via Claude Haiku,
and writes per-grading JSONL records to evals/results/{timestamp}.jsonl.

Usage:
    python evals/runner.py --suite synthetic
    python evals/runner.py --suite synthetic --subset smoke
    python evals/runner.py --suite real
    python evals/runner.py --fixture sre-mid-level

Exit code: 0 if every grading scored >= 4, 2 if any failed, 1 on
configuration error.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# Make project root importable so this script works whether invoked as
# `python evals/runner.py` or `python -m evals.runner`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analyzer import analyze, generate  # noqa: E402
from hardening import (  # noqa: E402
    build_context_set,
    check_ats_format,
    compute_keyword_overlap,
    extract_keywords,
)
from parser import parse_resume  # noqa: E402

EVALS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVALS_DIR / "fixtures"
RUBRICS_DIR = EVALS_DIR / "rubrics"
RESULTS_DIR = EVALS_DIR / "results"

JUDGE_MODEL = "claude-haiku-4-5-20251001"
PASS_THRESHOLD = 4

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
    return {
        "name": fixture_dir.name,
        "jd": jd,
        "resume_path": resume_path,
        "expected": expected,
    }


def _build_context(fixture: dict) -> dict:
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0, "reasons": ["judge response was not valid JSON"], "raw": raw}


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
    return fixtures


def _select_rubrics(subset: str) -> list[Path]:
    """Smoke = grounding only; full = every rubric."""
    all_rubrics = sorted(RUBRICS_DIR.glob("*.md"))
    if subset == "smoke":
        return [r for r in all_rubrics if r.stem == "grounding"]
    return all_rubrics


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description="Resume Optimizer eval harness")
    ap.add_argument("--suite", choices=["synthetic", "real", "all"], default="synthetic")
    ap.add_argument("--subset", choices=["smoke", "full"], default="full")
    ap.add_argument("--fixture", help="Run a single named fixture (overrides --suite)")
    ap.add_argument("--out-dir", default=str(RESULTS_DIR))
    args = ap.parse_args(argv)

    try:
        fixtures = _select_fixtures(args.suite, args.fixture)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if not fixtures:
        logger.warning("No fixtures matched the selection")
        return 0

    rubrics = _select_rubrics(args.subset)
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
    out_path = out_dir / f"{timestamp}.jsonl"

    n_pass = n_fail = 0

    with out_path.open("a", encoding="utf-8") as out:
        for fdir in fixtures:
            try:
                fixture = _load_fixture(fdir)
            except Exception as exc:
                logger.error("Fixture load failed: %s — %s", fdir.name, exc)
                continue

            logger.info("Fixture %s: building context + running pipeline", fixture["name"])
            t0 = time.perf_counter()
            try:
                context = _build_context(fixture)
                analysis = analyze(client, context, username=f"eval:{fixture['name']}")
                result = generate(
                    client, context, analysis,
                    username=f"eval:{fixture['name']}",
                )
            except Exception as exc:
                logger.error("Pipeline failed for %s: %s", fixture["name"], exc)
                out.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "eval",
                    "fixture": fixture["name"],
                    "rubric": None,
                    "score": None,
                    "status": "pipeline_error",
                    "error": str(exc),
                }) + "\n")
                n_fail += 1
                continue

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.info("  pipeline %s done in %dms", fixture["name"], elapsed_ms)

            for rubric_path in rubrics:
                payload = {
                    "fixture": fixture["name"],
                    "expected": fixture["expected"],
                    "original_resume": context["resume"]["text"],
                    "supplemental_resumes": context["supplemental_resumes"],
                    "job_description": context["job_description"],
                    "deterministic_analysis": context["deterministic_analysis"],
                    "analysis": analysis,
                    "generated_resume": result.get("resume_content", ""),
                    "generated_cover_letter": result.get("cover_letter_content", ""),
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

                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "eval",
                    "fixture": fixture["name"],
                    "rubric": rubric_path.stem,
                    "score": grade.get("score"),
                    "reasons": grade.get("reasons", []),
                    "failed_rules": grade.get("failed_rules", []),
                    "status": grade.get("status", "ok"),
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

    logger.info(
        "Eval complete: %d pass, %d fail. Results: %s",
        n_pass, n_fail, out_path,
    )
    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
