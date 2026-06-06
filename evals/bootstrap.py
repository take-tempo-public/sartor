"""Corpus bootstrap engine — one seed × N JDs → annotation material.

Drives a single corpus ``seed.json`` against many job descriptions through the
REAL product pipeline (``analyze`` → ``clarify`` → ``generate``, all in
``analyzer.py``), then deterministically collates the generated bullets/skills
across JDs into a ``bootstrap.json``. That file is the durable contract the next
branch (``eval/annotation-contract``) turns into ``expected.json`` fixtures + an
improvement brief.

Cross-JD collation is the point. A corpus bullet that stays near-identical across
many JDs is grounded core; one that re-skins itself per JD — swapping in each
JD's domain terms not present in source — is **JD-pandering**, a fabrication mode
only visible by comparing across JDs. The dedup clusters surface that signal:
``size`` / ``len(jd_files)`` is the JD-invariance measure (wide span ⇒ grounded
core; ``size: 1`` ⇒ JD-specific candidate to annotate).

This module ORCHESTRATES LLM calls (it lives in ``evals/``, off the P1 hardening
boundary — same as ``evals/runner.py``), but every collation step (token
normalization, Jaccard dedup, document assembly) is deterministic and LLM-free.
It reuses the public pipeline primitives the runner uses — it does NOT duplicate
the LLM-call logic (that lives in ``analyzer.py``) and it does NOT touch the
runner's file-based or ``--seed`` paths.

Usage:

    python -m evals.bootstrap --seed evals/fixtures/real/alex/seed.json \\
        --jd-dir path/to/jds/ [--out PATH] [--grounding-signals] [--jaccard 0.75]

The seed is eager-validated and the ``--jd-dir`` resolved BEFORE any paid LLM
call. The output is written under the gitignored ``evals/fixtures/real/`` tree; a
``_within`` guard (mirroring ``scripts/export_corpus_seed.py``) refuses to emit a
PII-bearing snapshot anywhere else.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

# Make project root importable so `python -m evals.bootstrap` and direct script
# invocation both resolve the top-level analyzer/db/hardening imports. Mirrors
# evals/runner.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.utils import secure_filename  # noqa: E402

from analyzer import (  # noqa: E402
    analyze,
    clarify,
    effective_prompt_version,
    generate,
)
from db.build_context import build_context_set_from_db  # noqa: E402
from evals.grounding_signals import extract_bullets  # noqa: E402
from evals.seed_import import load_seed, seeded_session  # noqa: E402

if TYPE_CHECKING:
    import anthropic
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BOOTSTRAP_SCHEMA_VERSION = 1
GENERATOR = "evals/bootstrap.py"
DEFAULT_JACCARD = 0.75

# The only directory bootstrap.json is ever written into. Already gitignored
# (evals/fixtures/real/* in .gitignore), so the snapshot's PII stays untracked.
ALLOWED_ROOT = PROJECT_ROOT / "evals" / "fixtures" / "real"

# A "grounding function" matches run_grounding_signals' shape: (resume_md,
# source_texts) -> signal dict. Injected so the optional grounding pass is
# testable with a mock and the heavy import stays deferred.
GroundingFn = Callable[[str, list[str]], dict[str, Any]]


class Cluster(TypedDict):
    """A dedup cluster of near-identical generated texts across JDs."""

    representative: str
    members: list[str]
    jd_files: list[str]
    size: int


# ---------------------------------------------------------------------------
# Deterministic collation — token normalization + Jaccard dedup. LLM-free.
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z+#.-]{1,}\b")


def _normalize_tokens(text: str) -> frozenset[str]:
    """Lowercase word set (len > 2) for Jaccard scoring.

    Same shape as ``db/build_context.py:_tokenize`` so dedup similarity is
    measured on the same token basis the corpus scorer uses.
    """
    return frozenset(w for w in _WORD_RE.findall((text or "").lower()) if len(w) > 2)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity |a∩b| / |a∪b|. Two empty sets are defined as 0.0."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def dedup_texts(items: Iterable[tuple[str, str]], threshold: float) -> list[Cluster]:
    """Greedy cross-JD dedup of ``(jd_file, text)`` items at a Jaccard threshold.

    Each item joins the FIRST existing cluster whose representative scores
    ≥ ``threshold`` against it, else opens a new cluster (its representative).
    Deterministic: stable input order in ⇒ stable clusters out. A cluster records
    its representative (the first text that opened it), every member text, the
    distinct ``jd_files`` it spans (first-appearance order), and ``size`` (member
    count). ``len(jd_files)`` is the JD-invariance signal.
    """
    acc: list[dict[str, Any]] = []
    for jd_file, text in items:
        toks = _normalize_tokens(text)
        for c in acc:
            if _jaccard(toks, c["tokens"]) >= threshold:
                c["members"].append(text)
                if jd_file not in c["jd_files"]:
                    c["jd_files"].append(jd_file)
                break
        else:
            acc.append({
                "representative": text,
                "members": [text],
                "jd_files": [jd_file],
                "tokens": toks,
            })
    return [
        Cluster(
            representative=c["representative"],
            members=c["members"],
            jd_files=c["jd_files"],
            size=len(c["members"]),
        )
        for c in acc
    ]


# ---------------------------------------------------------------------------
# Deterministic extraction from a generated résumé. LLM-free.
# ---------------------------------------------------------------------------


def _heading_text(line: str) -> str | None:
    """Return a section heading's text if ``line`` is a heading, else None.

    Recognizes markdown ``#``-prefixed headings and standalone bold headings
    (``**Skills**`` / ``__Skills__``) — the shapes this product's synthesized and
    LLM-generated résumés use. Deliberately conservative: a colon-suffixed prose
    line is NOT treated as a heading (avoids false section breaks).
    """
    if not line:
        return None
    if line.startswith("#"):
        return line.lstrip("#").strip().rstrip(":").strip()
    m = re.fullmatch(r"\*\*(.+?)\*\*:?|__(.+?)__:?", line)
    if m:
        return (m.group(1) or m.group(2) or "").strip()
    return None


def _split_skill_line(line: str) -> list[str]:
    """Split one content line under a Skills heading into individual skills.

    Strips a leading bullet marker, then splits on commas / semicolons / pipes /
    middots. Returns trimmed, non-empty parts.
    """
    line = re.sub(r"^[-*•]\s+", "", line)
    return [p.strip() for p in re.split(r"[,;|·•]", line) if p.strip()]


def _extract_skills(resume_md: str) -> list[str]:
    """Best-effort deterministic parse of the Skills section of a generated résumé.

    Walks headings; while inside a heading whose text contains "skill", collects
    skills from each content line (comma/bullet lists both handled). Order-
    preserving, case-insensitive dedup.
    """
    out: list[str] = []
    in_skills = False
    for raw in resume_md.splitlines():
        stripped = raw.strip()
        heading = _heading_text(stripped)
        if heading is not None:
            in_skills = "skill" in heading.lower()
            continue
        if not in_skills or not stripped:
            continue
        out.extend(_split_skill_line(stripped))
    seen: set[str] = set()
    result: list[str] = []
    for s in out:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result


# ---------------------------------------------------------------------------
# Document assembly — pure (except the optional injected grounding_fn).
# ---------------------------------------------------------------------------


def build_bootstrap_document(
    per_jd: list[dict[str, Any]],
    *,
    username: str,
    seed_path: str,
    threshold: float,
    corpus_source: str,
    grounding_fn: GroundingFn | None = None,
) -> dict[str, Any]:
    """Assemble the ``bootstrap.json`` document from per-JD pipeline records.

    Deterministic apart from the optional ``grounding_fn``: it dedups every
    generated bullet and (separately) every skill across all JDs at ``threshold``.
    When ``grounding_fn`` is supplied, the dedup BULLET cluster representatives are
    rendered as a ``- text`` markdown list and scored against ``corpus_source``
    (the synthesized corpus résumé text, identical across JDs) — the second
    ``run_grounding_signals`` call site. The result lands under
    ``grounding_signals`` (``None`` when no ``grounding_fn``).
    """
    all_bullets = [(rec["jd_file"], b) for rec in per_jd for b in rec["bullets"]]
    all_skills = [(rec["jd_file"], s) for rec in per_jd for s in rec["skills"]]
    bullet_clusters = dedup_texts(all_bullets, threshold)
    skill_clusters = dedup_texts(all_skills, threshold)

    grounding: dict[str, Any] | None = None
    if grounding_fn is not None:
        reps_md = "\n".join(f"- {c['representative']}" for c in bullet_clusters)
        grounding = grounding_fn(reps_md, [corpus_source])

    return {
        "bootstrap_schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "generator": GENERATOR,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_username": username,
        "seed_path": seed_path,
        "prompt_version": effective_prompt_version(),
        "jaccard_threshold": threshold,
        "jd_count": len(per_jd),
        "per_jd": per_jd,
        "dedup": {
            "bullets": {
                "cluster_count": len(bullet_clusters),
                "clusters": bullet_clusters,
            },
            "skills": {
                "cluster_count": len(skill_clusters),
                "clusters": skill_clusters,
            },
        },
        "grounding_signals": grounding,
    }


# ---------------------------------------------------------------------------
# Pipeline orchestration — reuses the public analyze/clarify/generate primitives.
# ---------------------------------------------------------------------------


# A "progress function" lets a caller (e.g. the browser bootstrap SSE route) observe
# each per-JD step without this module knowing anything about SSE: (event, payload).
# Events: "jd_start" / "analyzing" / "clarifying" / "generating" / "jd_done".
ProgressFn = Callable[[str, dict[str, Any]], None]


def run_pipeline_over_jds(
    client: anthropic.Anthropic,
    session: Session,
    username: str,
    jd_paths: list[Path],
    *,
    progress: ProgressFn | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """File-path entry point for the corpus pipeline — reads each JD then delegates.

    Behavior-preserving thin wrapper over ``run_pipeline_over_jd_texts``: reads
    each ``jd_path`` into a ``(name, text)`` pair (preserving the CLI's filename
    as ``jd_file``) and runs the shared in-memory pipeline. Kept so the CLI
    (``evals/bootstrap.py``) path is unchanged.
    """
    jds = [(p.name, p.read_text(encoding="utf-8")) for p in jd_paths]
    return run_pipeline_over_jd_texts(
        client, session, username, jds, progress=progress,
    )


def run_pipeline_over_jd_texts(
    client: anthropic.Anthropic,
    session: Session,
    username: str,
    jds: list[tuple[str, str]],
    *,
    progress: ProgressFn | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Run analyze→clarify→generate for each in-memory JD over one corpus session.

    ``jds`` is a list of ``(jd_name, jd_text)`` — the in-memory form the browser
    bootstrap wrapper uses (pasted JDs, no temp files). Returns
    ``(per_jd_records, corpus_source_text)``. Each JD mints a fresh ``run_id`` and
    a context via ``build_context_set_from_db`` (the REAL corpus→context path),
    then runs the same public pipeline calls the runner uses. A ``clarify``
    failure is non-fatal — it degrades that JD's clarify block only.
    ``corpus_source_text`` (identical across JDs since one corpus) is captured once
    for the grounding pass. ``progress`` (optional) is invoked at each step so a
    caller can stream coarse per-JD progress; it never alters the result.
    """
    def _emit(event: str, **payload: Any) -> None:
        if progress is not None:
            progress(event, payload)

    per_jd: list[dict[str, Any]] = []
    corpus_source = ""
    total = len(jds)
    for index, (jd_name, jd_text) in enumerate(jds):
        run_id = uuid.uuid4().hex[:12]
        username_tag = f"bootstrap:{Path(jd_name).stem}"
        logger.info("JD %s: building context + running pipeline (run_id=%s)", jd_name, run_id)
        _emit("jd_start", jd_file=jd_name, index=index, total=total, run_id=run_id)

        context, _application, _run = build_context_set_from_db(
            session, candidate_username=username, jd_text=jd_text, run_id=run_id,
        )
        if not corpus_source:
            corpus_source = context["resume"]["text"]

        _emit("analyzing", jd_file=jd_name, index=index, total=total)
        analysis = analyze(client, context, username=username_tag, run_id=run_id)

        clar_questions: list[dict[str, Any]] = []
        clar_reasoning = ""
        try:
            _emit("clarifying", jd_file=jd_name, index=index, total=total)
            clar = clarify(client, context, analysis, username=username_tag, run_id=run_id)
            clar_questions = clar.get("questions", [])
            clar_reasoning = clar.get("reasoning", "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Clarify failed for %s, continuing without it: %s", jd_name, exc)

        _emit("generating", jd_file=jd_name, index=index, total=total)
        result = generate(client, context, analysis, username=username_tag, run_id=run_id)
        resume_md = result.get("resume_content", "")

        per_jd.append({
            "jd_file": jd_name,
            "run_id": run_id,
            "analysis": analysis,
            "clarification_questions": clar_questions,
            "clarification_reasoning": clar_reasoning,
            "generated_resume": resume_md,
            "generated_cover_letter": result.get("cover_letter_content", ""),
            "bullets": extract_bullets(resume_md),
            "skills": _extract_skills(resume_md),
        })
        logger.info(
            "  %s → %d bullets, %d skills, %d clarify questions",
            jd_name, len(per_jd[-1]["bullets"]),
            len(per_jd[-1]["skills"]), len(clar_questions),
        )
        _emit(
            "jd_done", jd_file=jd_name, index=index, total=total,
            bullets=len(per_jd[-1]["bullets"]), skills=len(per_jd[-1]["skills"]),
            questions=len(clar_questions),
        )
    return per_jd, corpus_source


# ---------------------------------------------------------------------------
# Write-path guard — defense against emitting the (PII-bearing) snapshot
# anywhere except evals/fixtures/real/. Mirrors scripts/export_corpus_seed.py.
# ---------------------------------------------------------------------------


def _within(path: Path, parent: Path) -> bool:
    """Return True only if path resolves to within parent. Mirrors app.py:_within."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_output_path(username: str, out_arg: str | None) -> Path:
    """Compute the bootstrap.json path and enforce containment under ALLOWED_ROOT.

    Default: ``<ALLOWED_ROOT>/<secure_filename(username)>/bootstrap.json``. With
    ``--out``, the given path is resolved and must still live under ALLOWED_ROOT.
    Raises ValueError on a sanitized-empty username or an out-of-bounds target —
    the guard fails closed (no write).
    """
    if out_arg:
        target = Path(out_arg).expanduser()
    else:
        safe = secure_filename(username)
        if not safe:
            raise ValueError(f"username {username!r} sanitizes to empty; cannot place bootstrap.json")
        target = ALLOWED_ROOT / safe / "bootstrap.json"

    if not _within(target, ALLOWED_ROOT):
        raise ValueError(
            f"refusing to write outside {ALLOWED_ROOT.as_posix()} "
            f"(resolved target: {target.resolve().as_posix()})"
        )
    return target.resolve()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description="callback. corpus bootstrap engine")
    ap.add_argument(
        "--seed", required=True, metavar="PATH",
        help="Path to a corpus seed.json (from scripts.export_corpus_seed).",
    )
    ap.add_argument(
        "--jd-dir", required=True, metavar="PATH",
        help="Directory of job-description files (*.txt / *.jd), one JD per file.",
    )
    ap.add_argument(
        "--out", default=None, metavar="PATH",
        help="Output path (must resolve under evals/fixtures/real/). "
             "Default: evals/fixtures/real/<candidate>/bootstrap.json",
    )
    ap.add_argument(
        "--grounding-signals", action="store_true", default=False,
        help="Run DeBERTa NLI + MiniCheck-FT5 offline grounding scorers over the "
             "deduplicated bullet cluster representatives. Requires the eval-grounding "
             "extra (see CONTRIBUTING.md); first run downloads ~3.2 GB of weights.",
    )
    ap.add_argument(
        "--jaccard", type=float, default=DEFAULT_JACCARD, metavar="FLOAT",
        help=f"Cross-JD dedup similarity threshold (default {DEFAULT_JACCARD}).",
    )
    args = ap.parse_args(argv)

    # Eager-validate the seed BEFORE any paid LLM call (bad path / malformed JSON /
    # unsupported schema version all exit non-zero immediately).
    try:
        seed = load_seed(args.seed)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Could not load --seed %s: %s", args.seed, exc)
        return 1

    # Eager-resolve the JD directory.
    jd_dir = Path(args.jd_dir).expanduser()
    if not jd_dir.is_dir():
        logger.error("--jd-dir is not a directory: %s", jd_dir)
        return 1
    jd_paths = sorted(p for p in jd_dir.iterdir() if p.suffix.lower() in (".txt", ".jd"))
    if not jd_paths:
        logger.error("No *.txt or *.jd files in --jd-dir: %s", jd_dir)
        return 1

    # Resolve + guard the output path before spending anything.
    username = str(seed["candidate_username"])
    try:
        out_path = _resolve_output_path(username, args.out)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    logger.info(
        "Bootstrap: candidate=%s, %d JDs from %s, jaccard=%.2f%s",
        username, len(jd_paths), jd_dir.as_posix(), args.jaccard,
        ", grounding-signals ON" if args.grounding_signals else "",
    )

    # Deferred imports: keep them off the module's import surface and only pay for
    # them when actually running (not when a test imports a helper).
    from evals.runner import _get_client  # noqa: PLC0415

    client = _get_client()
    with seeded_session(seed) as (session, seed_username):
        per_jd, corpus_source = run_pipeline_over_jds(client, session, seed_username, jd_paths)

    grounding_fn: GroundingFn | None = None
    if args.grounding_signals:
        from evals.grounding_signals import run_grounding_signals  # noqa: PLC0415
        grounding_fn = run_grounding_signals

    doc = build_bootstrap_document(
        per_jd,
        username=username,
        seed_path=str(args.seed),
        threshold=args.jaccard,
        corpus_source=corpus_source,
        grounding_fn=grounding_fn,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info(
        "bootstrap: %d JDs → %d bullet clusters, %d skill clusters → %s",
        doc["jd_count"],
        doc["dedup"]["bullets"]["cluster_count"],
        doc["dedup"]["skills"]["cluster_count"],
        out_path.as_posix(),
    )
    return 0


__all__ = [
    "BOOTSTRAP_SCHEMA_VERSION",
    "Cluster",
    "ProgressFn",
    "build_bootstrap_document",
    "dedup_texts",
    "run_pipeline_over_jd_texts",
    "run_pipeline_over_jds",
]


if __name__ == "__main__":
    raise SystemExit(main())
