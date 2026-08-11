"""Targeted corpus-mode probe for `analyzer.draft_experience_summaries` (A3).

**Why this exists and why it is not a `--suite synthetic` fixture.**
`evals/runner.py`'s suites grade a whole generated résumé against LLM-judge
rubrics, and its `synthetic` fixtures are FILE-BASED (`resume.md` + `jd.txt`) —
they never touch the corpus DB, so no fixture in that suite can reach a
corpus-mode Compose drafting call at all. That is work item 16's territory, not
a gap this sprint could close by adding a flat sibling directory under
`evals/fixtures/synthetic/` next to `data-scientist-junior`/`pm-senior`/
`sre-mid-level`: `evals/runner.py`'s `_select_fixtures` selector treats every
immediate subdirectory there as a `--suite synthetic` fixture and requires a
`resume.*` file, so a flat sibling would be picked up as a broken one.

The fixture's files (`seed.json` + `jd.txt` + `analysis.json`, no `resume.*`)
live at `evals/fixtures/synthetic/corpus/role-summary-drafting/` — nested one
level under a `corpus/` segment rather than flat, both to read as clearly
corpus-mode (not a resume+JD fixture) and to keep it out of
`--suite synthetic`'s per-fixture grading loop. The `evals/fixtures/synthetic/`
prefix itself is not optional here: `tests/test_zero_pii_clone.py`'s allowlist
requires every git-tracked path under `evals/fixtures/` to live under either
`evals/fixtures/real/.gitkeep` or `evals/fixtures/synthetic/`. One known,
harmless side effect of that placement: `_select_fixtures`'s `iterdir()` still
picks up the immediate `evals/fixtures/synthetic/corpus/` directory itself as
a spurious `--suite synthetic` candidate on every run; `_load_fixture` fails
to find `jd.txt`/`resume.*` directly inside it, `run_suite` catches that,
logs one `Fixture load failed: corpus — ...` line, and skips it — the suite
still runs and grades the 3 real fixtures normally. Confirmed via
`tests/test_eval_runner.py::TestJdLabelOnRecords::test_every_record_carries_jd_label`
still passing after this fixture moved under `evals/fixtures/synthetic/`.

So this is a separate, deliberately small harness in the shape the repo already
uses for corpus-mode validation — one paid call, deterministic scoring, a
`TUNING_LOG.md` entry — matching the D5 precedent (`evals/TUNING_LOG.md`,
"D5 clarifications-to-corpus", validated with a throwaway sandbox candidate
rather than the synthetic suite, for exactly this reason). The difference is
that the sandbox is now a COMMITTED synthetic fixture, so the run is repeatable
by anyone and comparable across `PROMPT_VERSION`s.

**No LLM judge.** Scoring is deterministic only: the L0 fabricated-specifics
check and grounding overlap from `hardening`, scored against
`hardening.assemble_source_union` — the same union the prompt is shown, which is
the property A3 widened and therefore the property most worth measuring.
Judge-graded quality of a one-line intro is a rubric this repo does not have;
inventing one here would be a bigger change than the call being tested.

**Cost.** ONE Sonnet call per run. Measured, not estimated, from the telemetry
row the call itself writes (see `--out`).

Usage::

    python -m evals.corpus_drafting_probe                       # default fixture
    python -m evals.corpus_drafting_probe --fixture <dir-name>
    python -m evals.corpus_drafting_probe --dry-run             # no LLM call

`--dry-run` builds and prints the exact staged targets + prompt-side inputs and
exits without spending anything — use it to confirm the fixture is wired before
paying for a real run.

Telemetry containment: the call writes one row to the real
`logs/llm_calls.jsonl`, deliberately. This is a REAL run against the REAL
provider, so it belongs in the cost log like any other real call — unlike the
test suite, which must never touch it (`tests/test_call_kind_telemetry.py`).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:  # `python evals/corpus_drafting_probe.py` support
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = REPO_ROOT / "evals" / "fixtures" / "synthetic" / "corpus"
DEFAULT_FIXTURE = "role-summary-drafting"

logger = logging.getLogger(__name__)


def _load_fixture(name: str) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Return (seed, jd_text, llm_analysis) for a corpus fixture directory."""
    from evals.seed_import import load_seed

    fixture_dir = FIXTURES_DIR / name
    if not fixture_dir.is_dir():
        raise FileNotFoundError(f"No corpus fixture at {fixture_dir}")
    seed = load_seed(fixture_dir / "seed.json")
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    analysis_path = fixture_dir / "analysis.json"
    analysis: dict[str, Any] = {}
    if analysis_path.exists():
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        analysis.pop("_why_this_file_is_hand_written", None)
    return seed, jd_text, analysis


def _cost_for_run(run_id: str) -> tuple[float, int]:
    """(usd, row_count) for this run's telemetry rows.

    Reads the rows the call just wrote rather than estimating from token counts:
    an estimate that drifts from `hardening.MODEL_PRICING` is worse than no
    number, and the log is where every other cost view in this project reads
    from. One bounded tail scan, not a full parse of a growing file.
    """
    from analyzer import LOG_PATH
    from hardening import compute_call_cost

    if not LOG_PATH.exists():
        return 0.0, 0
    total = 0.0
    rows = 0
    # The probe's own rows are always the last few; 200 lines is a generous
    # bound that keeps this O(1) as the log grows.
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()[-200:]
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("run_id") != run_id:
            continue
        rows += 1
        total += compute_call_cost(rec)
    return total, rows


def run(fixture: str = DEFAULT_FIXTURE, *, dry_run: bool = False) -> dict[str, Any]:
    """Build the corpus context, draft the role intros, score them deterministically."""
    from blueprints.applications import (
        _active_intros_by_experience,
        _build_experience_summary_targets,
    )
    from db.build_context import build_context_set_from_db
    from evals.seed_import import seeded_session
    from hardening import (
        assemble_source_union,
        compute_fabricated_specifics,
        compute_grounding_overlap,
    )

    seed, jd_text, analysis = _load_fixture(fixture)
    run_id = f"probe_{uuid.uuid4().hex[:10]}"

    with seeded_session(seed) as (session, username):
        context, application, _run = build_context_set_from_db(
            session,
            candidate_username=username,
            jd_text=jd_text,
            run_id=run_id,
        )
        # Same underlying dict (a type-checker hint, no copy) — used only for the
        # transient staging keys that fall outside the ContextSet TypedDict, the
        # identical idiom `evals/runner.py::_run_assemble_pipeline` uses for
        # `jd_text` / `summary_items`.
        ctx = cast("dict[str, Any]", context)
        if analysis:
            ctx["llm_analysis"] = analysis

        # Reuse the ROUTE's own target builder rather than reimplementing it —
        # a probe that stages its inputs differently from production measures a
        # prompt production never sends. That includes the live is_active
        # intersection (item 75), staged here exactly as the route stages it.
        from db.models import Experience

        intros_by_exp = _active_intros_by_experience(session, application.candidate_id)
        active_exp_ids = {
            row[0]
            for row in session.query(Experience.id).filter_by(
                candidate_id=application.candidate_id, is_active=1
            )
        }
        targets = _build_experience_summary_targets(ctx, intros_by_exp, active_exp_ids)
        ctx["experience_summary_targets"] = targets
        ctx["jd_text"] = jd_text

        source_union = assemble_source_union(context)
        report: dict[str, Any] = {
            "fixture": fixture,
            "run_id": run_id,
            "roles_staged": len(targets),
            "roles_with_existing_intros": sum(1 for t in targets if t["existing_intros"]),
            "source_union_blocks": len(source_union),
        }

        if dry_run:
            report["dry_run"] = True
            report["targets"] = targets
            return report

        from analyzer import PROMPT_VERSION, draft_experience_summaries
        from web_infra import _get_client

        result = draft_experience_summaries(
            _get_client(),
            context,
            username=username,
            run_id=run_id,
        )
        drafts = result.get("drafts") or []
        # MUST be markdown bullet lines. `compute_fabricated_specifics` splits its
        # input with `hardening.BULLET_LINE_RE` (`^\s*[-*•]\s+`) and returns
        # rate 0.0 on ZERO matched bullets — so feeding it bare sentences scores a
        # vacuous, meaningless pass. Found the hard way on this probe's first run
        # (the initial version passed raw text and reported rate 0.0 with
        # total_bullets 0). A role intro is `work[].summary`, not a highlight, so
        # the `- ` prefix here is a scoring-unit adapter, not a claim about how
        # the text renders.
        drafted_text = "\n".join(f"- {str(d.get('text') or '').strip()}" for d in drafts)

        fabricated = compute_fabricated_specifics(drafted_text, source_union)
        overlap = compute_grounding_overlap(drafted_text, source_union, n=3)
        cost_usd, telemetry_rows = _cost_for_run(run_id)

        report.update(
            {
                "prompt_version": PROMPT_VERSION,
                "drafts": drafts,
                "drafts_returned": len(drafts),
                "roles_omitted_by_the_model": len(targets) - len(drafts),
                "fabricated_specifics_rate": fabricated.get("fabricated_specifics_rate"),
                # Reported so a rate of 0.0 can be told apart from a VACUOUS 0.0
                # (zero scored units). A run with total_bullets == 0 measured
                # nothing, whatever its rate says.
                "l0_total_bullets": fabricated.get("total_bullets"),
                "l0_total_specifics": fabricated.get("total_specifics"),
                "flagged_samples": fabricated.get("flagged_samples"),
                "grounding_overlap": overlap,
                "cost_usd": round(cost_usd, 6),
                "telemetry_rows": telemetry_rows,
            }
        )
        return report


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Stage everything and print it WITHOUT making the paid LLM call.",
    )
    ap.add_argument("--out", help="Write the full JSON report here as well as stdout.")
    args = ap.parse_args(argv)

    report = run(args.fixture, dry_run=args.dry_run)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
