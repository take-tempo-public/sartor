"""Judge-scored before/after relevance eval for the S3 vector tier — the v1.0.8
gate-override validation (RELEASE_CHECKLIST carry-forward #2; Sprint 8.5).

The S3 ``VectorSource`` (Sprint 7.6) was built **ahead of** the formal eval gate at
owner direction. ``scripts/vector_index_probe.py`` is the LLM-free *qualitative*
corroboration (lexical-miss recovery + new cites). This script is the **quantitative**
companion the carry-forward ledger owes: for a fixed dev/code-vocabulary question set it
runs ``recall.assemble`` with the lexical tiers (wiki + git + session) and again with the
S3 vector tier added, then asks the Haiku eval-judge to score how well each retrieval set
answers the question (0–5). The aggregate **delta** + the vector-only contribution is the
evidence for the keep/demote decision on the ``numpy`` + ``model2vec`` dependency footprint.

Retrieval corpus = the committed wiki + code (project-global, no user PII), so the printed
summary and the JSONL result are safe to commit / quote in the findings backlog. The
per-run JSONL lands in ``evals/results/`` (gitignored).

LLM-call boundary: this is eval tooling. It does **no** network egress of its own — it
reuses ``evals.runner._get_client`` + ``evals.runner._grade`` (the allowlisted judge
call-site), so it never imports the ``anthropic`` SDK directly. It changes no production
prompt; ``PROMPT_VERSION`` is untouched.

Usage:
    python -m scripts.build_vector_index          # rebuild the index first if stale
    python -m scripts.vector_before_after_eval     # ~24 Haiku judge calls (cheap)
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from blueprints.assistant import _VECTOR_INDEX_DIR, _build_sources, _make_embedder
from evals.runner import _get_client, _grade
from recall import Scope, Tier, VectorSource, assemble
from recall.models import Unit
from scripts.vector_index_probe import QUESTIONS as DEFAULT_QUESTIONS

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "evals" / "results"

_BASE_TIERS = frozenset({Tier.WIKI, Tier.GIT, Tier.SESSION})

# Relevance rubric for the judge. Deliberately NOT placed under evals/rubrics/ —
# the resume eval runner globs that directory and would mis-apply this rubric to
# résumé fixtures. _grade() reads a rubric file, so we write this to a tempfile.
_RELEVANCE_RUBRIC = """\
# Retrieval relevance rubric

You are grading a RETRIEVAL set, not a résumé. Given a developer's natural-language
question and the set of source snippets a retrieval system returned (each with a
`path:line` or `[[wiki]]` citation), score how well the SET as a whole would let a
careful reader answer the question from the cited sources.

Score 0.0–5.0 (one decimal allowed):
- 5 = the set directly contains the answer with a precise, on-topic citation.
- 4 = the answer is clearly derivable; the most relevant source is present.
- 3 = partially relevant; the reader gets pointed in the right direction but must
      bridge a gap.
- 2 = tangential; same general area but the key source is missing.
- 1 = mostly off-topic noise.
- 0 = nothing relevant.

Judge ONLY relevance to the question. Do not reward volume — more snippets is not
better. Output strictly this JSON and nothing else:
{"score": <float 0.0-5.0>, "reasons": ["<short>", "..."]}
"""


def _unit_payload(u: Unit, snippet_chars: int) -> dict:
    """A judge-facing, PII-free view of one retrieved unit."""
    return {
        "citation": u.citation,
        "tier": u.tier.value,
        "text": u.text[:snippet_chars].strip(),
    }


def _retrieve(query: str, tiers: frozenset[Tier], sources: list, top_k: int) -> list[Unit]:
    scope = Scope(allow_dev=True, enabled_tiers=tiers, token_budget=4000)
    return list(assemble(query, scope, sources).units)[:top_k]


def _grade_set(
    client, rubric_path: Path, question: str, units: list[Unit], snippet_chars: int
) -> dict:
    payload = {
        "question": question,
        "retrieved": [_unit_payload(u, snippet_chars) for u in units],
    }
    return _grade(client, rubric_path, payload)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=6, help="Units per condition (default 6).")
    ap.add_argument(
        "--snippet-chars", type=int, default=600, help="Per-unit text shown to the judge."
    )
    ap.add_argument(
        "--out-dir", default=str(RESULTS_DIR), help="Where to write the JSONL (gitignored)."
    )
    ap.add_argument(
        "--questions-file",
        help="Optional newline-delimited question file; defaults to the probe's set.",
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    sources = _build_sources([])
    if not any(isinstance(s, VectorSource) for s in sources):
        reason = "model not downloaded" if _make_embedder() is None else "index not built"
        logger.info(
            "S3 vector tier inactive (%s). Run `python -m scripts.build_vector_index` "
            "first. Index dir: %s",
            reason,
            _VECTOR_INDEX_DIR,
        )
        return 1

    if args.questions_file:
        questions = [
            q.strip()
            for q in Path(args.questions_file).read_text(encoding="utf-8").splitlines()
            if q.strip()
        ]
    else:
        questions = list(DEFAULT_QUESTIONS)

    client = _get_client()
    vec_tiers = _BASE_TIERS | {Tier.VECTOR}

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(_RELEVANCE_RUBRIC)
        rubric_path = Path(fh.name)

    records: list[dict] = []
    logger.info("%-52s | base | +S3 |  Δ  | new S3 cites", "question")
    logger.info("-" * 88)
    try:
        for q in questions:
            base_units = _retrieve(q, _BASE_TIERS, sources, args.top_k)
            vec_units = _retrieve(q, vec_tiers, sources, args.top_k)
            base_keys = {(u.source_id, u.citation) for u in base_units}
            vector_only = [
                u
                for u in vec_units
                if u.tier is Tier.VECTOR and (u.source_id, u.citation) not in base_keys
            ]

            base_grade = _grade_set(client, rubric_path, q, base_units, args.snippet_chars)
            vec_grade = _grade_set(client, rubric_path, q, vec_units, args.snippet_chars)
            base_score = float(base_grade.get("score") or 0.0)
            vec_score = float(vec_grade.get("score") or 0.0)
            delta = round(vec_score - base_score, 1)

            records.append(
                {
                    "question": q,
                    "top_k": args.top_k,
                    "base_score": base_score,
                    "vector_score": vec_score,
                    "delta": delta,
                    "base_reasons": base_grade.get("reasons", []),
                    "vector_reasons": vec_grade.get("reasons", []),
                    "vector_only_cites": [u.citation for u in vector_only],
                    "base_units": [asdict(u) for u in base_units],
                    "vector_units": [asdict(u) for u in vec_units],
                }
            )
            cites = ", ".join(u.citation for u in vector_only[:3]) or "-"
            logger.info(
                "%-52s | %4.1f | %4.1f | %+4.1f | %s", q[:52], base_score, vec_score, delta, cites
            )
    finally:
        rubric_path.unlink(missing_ok=True)

    n = len(records)
    mean_base = round(sum(r["base_score"] for r in records) / n, 2) if n else 0.0
    mean_vec = round(sum(r["vector_score"] for r in records) / n, 2) if n else 0.0
    improved = sum(1 for r in records if r["delta"] > 0)
    regressed = sum(1 for r in records if r["delta"] < 0)
    with_new_cites = sum(1 for r in records if r["vector_only_cites"])

    logger.info("-" * 88)
    logger.info(
        "mean relevance: base %.2f vs +S3 %.2f (Δ %+.2f) · improved %d/%d · regressed %d/%d "
        "· questions where S3 added a cite the lexical tiers missed: %d/%d",
        mean_base,
        mean_vec,
        round(mean_vec - mean_base, 2),
        improved,
        n,
        regressed,
        n,
        with_new_cites,
        n,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_path = out_dir / f"vector_before_after_{ts}.jsonl"
    summary = {
        "kind": "vector_before_after_summary",
        "generated_at": ts,
        "question_count": n,
        "top_k": args.top_k,
        "mean_base": mean_base,
        "mean_vector": mean_vec,
        "mean_delta": round(mean_vec - mean_base, 2),
        "improved": improved,
        "regressed": regressed,
        "questions_with_new_s3_cite": with_new_cites,
    }
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")
        for r in records:
            fh.write(json.dumps(r) + "\n")
    logger.info("wrote %s (gitignored)", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
