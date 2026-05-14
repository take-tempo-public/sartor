"""End-to-end smoke for Phase B.1 — DB-backed analyze + generate.

Runs the full pipeline against the testuser corpus using a real JD from
the eval fixtures. Prints analysis summary, generated resume, generated
cover letter, deterministic grounding check, and cost/timing summary.

Cost: ~$0.08-0.10 per run (analyze + generate, both Sonnet).

Usage:
    python -m scripts.smoke_phase_b1
    python -m scripts.smoke_phase_b1 --jd evals/fixtures/synthetic/sre-mid-level/jd.txt
    python -m scripts.smoke_phase_b1 --user testuser
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import anthropic

from analyzer import LLMResponseError, analyze, generate
from db.build_context import build_context_set_from_db
from db.session import get_session, init_db

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JD = REPO_ROOT / "evals" / "fixtures" / "synthetic" / "pm-senior" / "jd.txt"


def _resolve_api_key() -> str | None:
    import os
    env = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env:
        return env
    key_file = REPO_ROOT / ".api_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip() or None
    return None


def _check_bullet_grounding(generated_resume_md: str, corpus_text: str) -> tuple[int, int, list[str]]:
    """Heuristic: each output bullet should substring-match the corpus text.

    Returns (matched_count, total_count, suspicious_bullets). A bullet is
    suspicious if no contiguous 30-char window of it appears in the corpus.
    This is a quick eyeball check, not the structural grounding that B.3
    will enforce via application_bullet rows.
    """
    bullets = [
        line.lstrip("- ").strip()
        for line in generated_resume_md.splitlines()
        if line.lstrip().startswith("- ") and len(line.strip()) > 5
    ]
    matched = 0
    suspicious: list[str] = []
    corpus_lower = corpus_text.lower()
    for b in bullets:
        # Pick a few 30-char windows from the middle; if any appear in corpus,
        # call it grounded. Loose check — full match is too strict for LLM
        # paraphrasing, and zero match is the bright-line fabrication signal.
        windows = [b[i:i+30].lower() for i in range(0, max(1, len(b) - 30), 20)]
        if any(w and w in corpus_lower for w in windows):
            matched += 1
        else:
            suspicious.append(b[:120])
    return matched, len(bullets), suspicious


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase B.1 smoke against DB-backed pipeline.")
    parser.add_argument("--user", default="testuser", help="Username (must already be imported)")
    parser.add_argument("--jd", default=str(DEFAULT_JD), help="JD text file path")
    parser.add_argument(
        "--db", default=None,
        help="Override DB path (defaults to db/resume.sqlite)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    jd_path = Path(args.jd)
    if not jd_path.exists():
        print(f"ERROR: JD file not found: {jd_path}", file=sys.stderr)
        return 2
    jd_text = jd_path.read_text(encoding="utf-8")

    api_key = _resolve_api_key()
    if not api_key:
        print("ERROR: No API key. Set ANTHROPIC_API_KEY or .api_key at repo root.", file=sys.stderr)
        return 2

    init_db(args.db)
    session = get_session() if args.db is None else None
    if session is None:
        from db.session import make_engine, make_session_factory
        session = make_session_factory(make_engine(args.db))()

    client = anthropic.Anthropic(api_key=api_key)
    run_id = uuid.uuid4().hex[:12]

    print(f"=== Phase B.1 smoke: user={args.user}, run_id={run_id} ===\n")
    print(f"JD source: {jd_path}")
    print(f"JD length: {len(jd_text)} chars\n")

    try:
        # ---- Build context from DB ----
        t0 = time.perf_counter()
        try:
            context_set, application, application_run = build_context_set_from_db(
                session,
                candidate_username=args.user,
                jd_text=jd_text,
                run_id=run_id,
                application_title=f"smoke-{run_id}",
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        t_build = time.perf_counter() - t0

        corpus_text = context_set["resume"]["text"]
        snapshot = json.loads(application_run.corpus_snapshot_json)
        print(f"[ctx]  built in {t_build:.2f}s")
        print(f"       application_id={application.id} run_id={run_id}")
        print(f"       corpus snapshot: {len(snapshot['bullet_ids'])} bullets, "
              f"{len(snapshot['experience_title_ids'])} eligible titles")
        print(f"       synthesized resume: {len(corpus_text)} chars")
        print(f"       keyword match_score: "
              f"{context_set['deterministic_analysis']['keyword_overlap']['match_score']:.2f}\n")

        # ---- Analyze ----
        t0 = time.perf_counter()
        try:
            analysis = analyze(client, context_set, username=args.user, run_id=run_id)
        except LLMResponseError as exc:
            print(f"ERROR: analyze() validation failed: {exc.validation_error}", file=sys.stderr)
            session.rollback()
            return 1
        t_analyze = time.perf_counter() - t0
        application_run.analysis_json = json.dumps(analysis)
        context_set["llm_analysis"] = analysis

        print(f"[anlz] {t_analyze:.2f}s — essential_skills={len(analysis.get('essential_skills', []))}, "
              f"gaps={len(analysis.get('comparison', {}).get('gaps', []))}, "
              f"suggestions={len(analysis.get('suggestions', []))}")
        if analysis.get("essential_skills"):
            print(f"       essential_skills[:5]: "
                  f"{[s.get('skill') if isinstance(s, dict) else s for s in analysis['essential_skills'][:5]]}")
        print()

        # ---- Generate ----
        t0 = time.perf_counter()
        try:
            result = generate(client, context_set, analysis, username=args.user, run_id=run_id)
        except LLMResponseError as exc:
            print(f"ERROR: generate() validation failed: {exc.validation_error}", file=sys.stderr)
            session.rollback()
            return 1
        t_generate = time.perf_counter() - t0

        resume_md = result["resume_content"]
        cover_md = result["cover_letter_content"]
        print(f"[gen]  {t_generate:.2f}s — resume={len(resume_md)} chars, "
              f"cover={len(cover_md)} chars")
        print(f"       changes_made: {len(result.get('changes_made', []))}, "
              f"proofread_notes: {len(result.get('proofread_notes', []))}\n")

        # ---- Grounding heuristic check ----
        matched, total, suspicious = _check_bullet_grounding(resume_md, corpus_text)
        print(f"[grnd] bullets in generated resume: {total}")
        print(f"       substring-grounded against corpus: {matched}/{total}")
        if suspicious:
            print(f"       {len(suspicious)} suspicious bullet(s) (no 30-char window matched corpus):")
            for s in suspicious[:5]:
                print(f"         - {s}")

        # ---- Cost summary from JSONL telemetry ----
        from hardening import compute_call_cost
        log_path = REPO_ROOT / "logs" / "llm_calls.jsonl"
        total_cost = 0.0
        cache_read_total = 0
        if log_path.exists():
            with log_path.open(encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("run_id") != run_id:
                        continue
                    total_cost += compute_call_cost(rec)
                    cache_read_total += rec.get("cache_read_input_tokens", 0)
        print(f"\n[cost] this run: ${total_cost:.4f}, cache_read={cache_read_total} tokens")

        # ---- Phase B.3: persist structured output to DB audit chain ----
        from db.models import (
            ApplicationBullet,
            Bullet,
            ExperienceTitle,
            IterationLog,
            ProposalReview,
        )
        from db.persist_run import persist_corpus_generation

        report = persist_corpus_generation(
            session, application_run, result, candidate_id=application.candidate_id,
        )
        print(f"\n[persist] application_bullet rows: {report.application_bullets_created}")
        print(f"          application_run_title rows: {report.application_run_titles_created}")
        print(f"          proposed new bullets:        {report.proposed_bullets_created}")
        print(f"          proposed new titles:         {report.proposed_titles_created}")
        print(f"          proposal_review rows:        {report.proposal_reviews_created}")
        if report.bullets_referenced_but_missing:
            print(f"          {len(report.bullets_referenced_but_missing)} hallucinated bullet_id(s) skipped")
        if report.titles_referenced_but_missing:
            print(f"          {len(report.titles_referenced_but_missing)} hallucinated title_id(s) skipped")
        if report.skipped_due_to_malformed_payload:
            print(f"          {report.skipped_due_to_malformed_payload} malformed entries skipped")

        # Sanity-check: every bullet selected should match a real bullet text
        app_bullets = session.query(ApplicationBullet).filter_by(
            application_run_id=application_run.id,
        ).all()
        pending_bullets = session.query(Bullet).filter(
            Bullet.is_pending_review == 1,
            Bullet.source == f"llm_proposed:{run_id}",
        ).all()
        pending_titles = session.query(ExperienceTitle).filter(
            ExperienceTitle.is_pending_review == 1,
            ExperienceTitle.source == f"llm_proposed:{run_id}",
        ).all()
        pending_proposals = session.query(ProposalReview).filter_by(
            application_run_id=application_run.id, decision="pending",
        ).all()
        print(f"\n[verify] application_bullet rows in DB:    {len(app_bullets)}")
        print(f"         pending llm_proposed bullets:      {len(pending_bullets)}")
        print(f"         pending llm_proposed titles:       {len(pending_titles)}")
        print(f"         pending proposal_review rows:      {len(pending_proposals)}")
        print(f"         iteration_log rows for this run:   "
              f"{session.query(IterationLog).filter_by(application_run_id=application_run.id).count()}")

        # ---- Outputs ----
        print(f"\n{'=' * 70}\nGENERATED RESUME\n{'=' * 70}")
        print(resume_md)
        print(f"\n{'=' * 70}\nGENERATED COVER LETTER\n{'=' * 70}")
        print(cover_md)

        # Persist the run for inspection. Don't commit changes that would
        # pollute the DB beyond the smoke run.
        session.commit()
        print(f"\n[done] application_id={application.id} application_run_id={application_run.id}")
        print("       Wipe the smoke rows later with:")
        # The next print shows the user a sqlite3 command they could run to
        # wipe the smoke rows — it is NOT SQL execution from this process.
        # Bandit's S608 fires on the f-string content; suppressing on the
        # assignment line where it's flagged.
        wipe_cmd = f'sqlite3 db/resume.sqlite "DELETE FROM application WHERE id={application.id}"'  # noqa: S608
        print(f"       {wipe_cmd}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
