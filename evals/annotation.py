"""Annotation contract for the eval tuning loop — bootstrap.json → expected.json.

The human-in-the-loop seam of the v1.0.4 eval tuning loop. ``evals/bootstrap.py``
produces a ``bootstrap.json`` (one corpus seed × N JDs, with the generated
bullets/skills deduped across JDs into clusters and optional MiniCheck/NLI
pre-scores). This module turns a human's verdicts on those clusters into two
durable artifacts:

  1. an ``expected.json`` ``--suite real`` regression fixture (the schema
     ``evals/runner.py:_load_fixture`` reads — ``must_keywords`` /
     ``forbidden_inventions`` / ``min_*_score``), and
  2. an improvement brief (markdown) — the source material the next branch
     (``tuning/draft-and-gate-skill``) reads to draft prompt edits.

Two steps, both **deterministic and LLM-free** (P1 hardening posture — an
``evals/`` helper that consumes ``bootstrap.json`` and never calls a model):

  * ``build_annotation_template`` emits a blank ``annotations.json`` skeleton
    pre-filled with every cluster + clarification question + the inline grounding
    pre-scores, so a human annotates with the model pre-scores in view. This is
    the headless stand-in for the v1.0.5 annotation UI, which later wraps this
    same file format — so the format is the durable contract, not throwaway.
  * ``collate_expected`` + ``build_improvement_brief`` read a completed
    ``annotations.json`` (validated fail-closed, mirroring
    ``evals/seed_import.py``) and produce the fixture + brief.

The verdict enum is ``keep`` / ``fix`` / ``omit`` / ``fabricated`` — disposition
verbs that map 1:1 to a collation action. The grounding *subtype* of a finding
(``jd_pandering``, ``invented_metric``, …) is carried in ``failed_rules``, reusing
the existing rubric vocabulary in ``evals/rubrics/`` — that reuse is not a prompt
change and bumps no ``PROMPT_VERSION``.

Usage:

    # 1. emit a blank annotations.json beside the bootstrap.json
    python -m evals.annotation --bootstrap evals/fixtures/real/alex/bootstrap.json \\
        --emit-template

    # 2. (human fills in verdicts) … then collate into a runnable fixture + brief
    python -m evals.annotation --bootstrap evals/fixtures/real/alex/bootstrap.json \\
        --annotations evals/fixtures/real/alex/annotations.json \\
        --collate --jd-dir path/to/jds/

The produced fixture runs immediately:

    python evals/runner.py --suite real --seed evals/fixtures/real/alex/seed.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

# Make project root importable so `python -m evals.annotation` and direct script
# invocation both resolve top-level imports. Mirrors evals/bootstrap.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.utils import secure_filename  # noqa: E402

logger = logging.getLogger(__name__)

ANNOTATION_SCHEMA_VERSION = 1

# The schema versions THIS module knows how to read. Declared independently of
# ANNOTATION_SCHEMA_VERSION on purpose (same rationale as
# seed_import.SUPPORTED_SEED_SCHEMA_VERSIONS): a future annotations v2 with a
# changed shape must be REJECTED here until this module is taught to read it, not
# silently half-collated because the writer bumped its own constant.
SUPPORTED_ANNOTATION_SCHEMA_VERSIONS = frozenset({1})

# Disposition verdicts. Each maps 1:1 to a collation action — see module docstring
# and collate_expected / build_improvement_brief.
VERDICTS = frozenset({"keep", "fix", "omit", "fabricated"})

# Allowed failure-mode slugs, harvested from EVERY rubric in evals/rubrics/. The
# annotation reuses this existing vocabulary rather than minting its own. Slugs may
# be bare (``jd_pandering``) or parameterized (``missing_must_keyword:python``);
# validation checks the prefix before the first ``:``. Keep this in sync if a
# rubric adds a slug — it is a vocabulary mirror, not a prompt.
ALLOWED_FAILED_RULES = frozenset(
    {
        # grounding.md
        "invented_metric",
        "invented_role",
        "invented_company",
        "invented_credential",
        "invented_timeframe",
        "forbidden_pattern_match",
        "scope_inflation",
        "verb_overreach",
        "jd_pandering",
        # clarification_quality.md
        "wrong_count",
        "too_few_experience_probes",
        "generic_question",
        "fabricated_gap",
        "compound_question",
        "leading_question",
        "over_word_limit",
        "missing_expected_theme",
        "redundant_with_resume",
        # keyword_coverage.md
        "missing_must_keyword",
        "low_coverage",
        "keyword_stuffing",
        "forced_phrasing",
        # ats_format.md
        "missing_heading",
        "length_overflow",
        "table_layout",
        "missing_contact",
        # tone.md
        "throat_clearing_opener",
        "banned_phrase",
        "hedging",
        "length_under",
        "generic_hook",
        # callback_likelihood.md
        "weak_opening_bullets",
        "low_quantification",
        "generic_framing",
        "missing_role_tailoring",
        # iteration_quality.md
        "redundant_question",
        "missed_recent_edit",
        "targets_stale_draft",
        "too_few_experience_iteration_probes",
    }
)

# Default per-rubric pass thresholds for a produced expected.json (README
# "Anatomy of a fixture": 4 for grounding/keyword/ATS, 3 for the more subjective
# tone, 4 for clarification). An annotations.json may override via ``min_scores``.
DEFAULT_MIN_SCORES = {
    "grounding": 4.0,
    "keyword_coverage": 4.0,
    "ats_format": 4.0,
    "tone": 3.0,
    "clarification_quality": 4.0,
}

# The only directory annotation artifacts are ever written into. Already
# gitignored (evals/fixtures/real/* in .gitignore), so the PII-bearing snapshot
# stays untracked. Mirrors evals/bootstrap.py:ALLOWED_ROOT.
ALLOWED_ROOT = PROJECT_ROOT / "evals" / "fixtures" / "real"

_TOP_LEVEL_REQUIRED_KEYS = (
    "annotation_schema_version",
    "bullets",
    "skills",
    "clarification_ratings",
)


# ---------------------------------------------------------------------------
# Fail-closed validation. Mirrors evals/seed_import.py:validate_seed.
# ---------------------------------------------------------------------------


def _slug_base(slug: str) -> str:
    """Return the part of a failed_rules slug before its first ``:`` parameter."""
    return slug.split(":", 1)[0]


def _validate_failed_rules(rules: Any, where: str) -> None:
    if not isinstance(rules, list):
        raise ValueError(f"{where}: failed_rules must be a list, got {type(rules).__name__}")
    for slug in rules:
        if not isinstance(slug, str) or not slug:
            raise ValueError(f"{where}: failed_rules entries must be non-empty strings")
        if _slug_base(slug) not in ALLOWED_FAILED_RULES:
            raise ValueError(
                f"{where}: unknown failed_rules slug {slug!r}; base "
                f"{_slug_base(slug)!r} is not in the rubric vocabulary"
            )


def _validate_item(item: Any, where: str) -> None:
    """Validate one bullet/skill annotation item (verdict-aware, fail-closed)."""
    if not isinstance(item, dict):
        raise ValueError(f"{where}: item must be an object, got {type(item).__name__}")

    verdict = item.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(
            f"{where}: verdict must be one of {sorted(VERDICTS)}, got {verdict!r} "
            f"(an unfilled template skeleton is expected to fail here until annotated)"
        )

    _validate_failed_rules(item.get("failed_rules", []), where)

    # Verdict-aware requirements: the disposition dictates which payload field
    # must be present, so the collation downstream can rely on it.
    if verdict == "fix":
        rewrite = item.get("honest_rewrite")
        if not isinstance(rewrite, str) or not rewrite.strip():
            raise ValueError(f"{where}: verdict 'fix' requires a non-empty honest_rewrite")
    if verdict == "fabricated":
        pattern = item.get("forbidden_pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError(
                f"{where}: verdict 'fabricated' requires a non-empty forbidden_pattern"
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(
                f"{where}: forbidden_pattern {pattern!r} is not a compilable regex: {exc}"
            ) from exc


def _validate_rating(rating: Any, where: str) -> None:
    """Validate one clarification-question rating record."""
    if not isinstance(rating, dict):
        raise ValueError(f"{where}: rating must be an object, got {type(rating).__name__}")
    score = rating.get("rating")
    if score is not None:
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError(f"{where}: rating must be a number 0-5 or null, got {score!r}")
        if not 0.0 <= float(score) <= 5.0:
            raise ValueError(f"{where}: rating {score!r} out of range 0-5")
    _validate_failed_rules(rating.get("failed_rules", []), where)


def validate_annotations(doc: Any) -> None:
    """Raise ValueError unless ``doc`` is a readable annotation_schema_version-1 doc.

    Fail-closed: an unsupported version, missing top-level collections, an unknown
    verdict or failed_rules slug, or a verdict whose required payload is absent (a
    ``fix`` without an ``honest_rewrite``, a ``fabricated`` without a compilable
    ``forbidden_pattern``) is rejected rather than half-collated. The message names
    ``annotation_schema_version`` so callers/tests can match on it.
    """
    if not isinstance(doc, dict):
        raise ValueError(f"annotations must be a JSON object, got {type(doc).__name__}")
    version = doc.get("annotation_schema_version")
    if version not in SUPPORTED_ANNOTATION_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported annotation_schema_version={version!r}; this module reads "
            f"{sorted(SUPPORTED_ANNOTATION_SCHEMA_VERSIONS)}"
        )
    missing = [k for k in _TOP_LEVEL_REQUIRED_KEYS if k not in doc]
    if missing:
        raise ValueError(f"annotations is missing required keys: {missing}")

    for kind in ("bullets", "skills"):
        items = doc[kind]
        if not isinstance(items, list):
            raise ValueError(f"{kind} must be a list, got {type(items).__name__}")
        for i, item in enumerate(items):
            _validate_item(item, f"{kind}[{i}]")

    ratings = doc["clarification_ratings"]
    if not isinstance(ratings, list):
        raise ValueError(f"clarification_ratings must be a list, got {type(ratings).__name__}")
    for i, rating in enumerate(ratings):
        _validate_rating(rating, f"clarification_ratings[{i}]")


def load_annotations(path: str | Path) -> dict[str, Any]:
    """Read + validate an annotations.json from disk. Raises on bad JSON or drift."""
    doc = cast("dict[str, Any]", json.loads(Path(path).read_text(encoding="utf-8")))
    validate_annotations(doc)
    return doc


# ---------------------------------------------------------------------------
# Template emitter — bootstrap.json → blank annotations.json skeleton. LLM-free.
# ---------------------------------------------------------------------------


def _grounding_by_index(
    bootstrap_doc: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (nli_list, minicheck_list) from a bootstrap doc's grounding_signals.

    bootstrap.py scores the bullet-cluster representatives, rendered as a ``- ``
    list in cluster order, so these lists align BY INDEX with
    ``dedup.bullets.clusters``. Returns empty lists when the bootstrap was run
    without ``--grounding-signals`` (``grounding_signals is null``).
    """
    gs = bootstrap_doc.get("grounding_signals")
    if not gs:
        return [], []
    return gs.get("nli", []) or [], gs.get("minicheck", []) or []


def _bullet_item_template(
    index: int,
    cluster: dict[str, Any],
    nli_list: list[dict[str, Any]],
    mc_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """One blank bullet-annotation item with grounding pre-scores joined by index."""
    rep = cluster.get("representative", "")
    nli_score: float | None = None
    contradiction: bool | None = None
    mc_score: float | None = None

    if index < len(nli_list):
        nli = nli_list[index]
        if nli.get("bullet") not in (None, rep):
            logger.warning(
                "grounding/cluster misalignment at index %d: nli bullet %r != representative %r",
                index,
                nli.get("bullet"),
                rep,
            )
        nli_score = nli.get("nli_entailment_score")
        contradiction = nli.get("nli_contradiction_flag")
    if index < len(mc_list):
        mc_score = mc_list[index].get("minicheck_grounding_score")

    return {
        "cluster_index": index,
        "representative": rep,
        "jd_files": cluster.get("jd_files", []),
        "size": cluster.get("size", len(cluster.get("members", []))),
        "nli_entailment_score": nli_score,
        "nli_contradiction_flag": contradiction,
        "minicheck_grounding_score": mc_score,
        "verdict": None,
        "failed_rules": [],
        "note": "",
        "should_omit": False,
        "honest_rewrite": None,
        "forbidden_pattern": None,
    }


def _skill_item_template(index: int, cluster: dict[str, Any]) -> dict[str, Any]:
    """One blank skill-annotation item. Skills carry no grounding pre-scores
    (bootstrap scores bullets only)."""
    return {
        "cluster_index": index,
        "representative": cluster.get("representative", ""),
        "jd_files": cluster.get("jd_files", []),
        "size": cluster.get("size", len(cluster.get("members", []))),
        "nli_entailment_score": None,
        "nli_contradiction_flag": None,
        "minicheck_grounding_score": None,
        "verdict": None,
        "failed_rules": [],
        "note": "",
        "should_omit": False,
        "honest_rewrite": None,
        "forbidden_pattern": None,
    }


def build_annotation_template(
    bootstrap_doc: dict[str, Any],
    *,
    bootstrap_source: str = "",
) -> dict[str, Any]:
    """Emit a blank annotations.json skeleton from a bootstrap document.

    Pre-fills every bullet cluster, skill cluster, and clarification question with
    its representative text + the inline MiniCheck/NLI pre-scores (joined by index
    from ``bootstrap_doc["grounding_signals"]``), leaving ``verdict`` and
    ``rating`` blank for a human to fill. Deterministic and LLM-free. The emitted
    skeleton is intentionally NOT valid per ``validate_annotations`` (blank
    verdicts) until annotated — that is the fill-me signal.
    """
    nli_list, mc_list = _grounding_by_index(bootstrap_doc)
    bullet_clusters = bootstrap_doc.get("dedup", {}).get("bullets", {}).get("clusters", [])
    skill_clusters = bootstrap_doc.get("dedup", {}).get("skills", {}).get("clusters", [])

    bullets = [
        _bullet_item_template(i, c, nli_list, mc_list) for i, c in enumerate(bullet_clusters)
    ]
    skills = [_skill_item_template(i, c) for i, c in enumerate(skill_clusters)]

    clarification_ratings: list[dict[str, Any]] = []
    for rec in bootstrap_doc.get("per_jd", []):
        jd_file = rec.get("jd_file", "")
        for q in rec.get("clarification_questions", []):
            clarification_ratings.append(
                {
                    "jd_file": jd_file,
                    "question_id": q.get("id", ""),
                    "question_text": q.get("text", ""),
                    "kind": q.get("kind", ""),
                    "rating": None,
                    "failed_rules": [],
                    "note": "",
                }
            )

    return {
        "annotation_schema_version": ANNOTATION_SCHEMA_VERSION,
        "bootstrap_source": bootstrap_source,
        "candidate_username": bootstrap_doc.get("candidate_username", ""),
        "prompt_version": bootstrap_doc.get("prompt_version", ""),
        "bullets": bullets,
        "skills": skills,
        "clarification_ratings": clarification_ratings,
        "min_scores": dict(DEFAULT_MIN_SCORES),
        "notes": "",
    }


# ---------------------------------------------------------------------------
# Collation → expected.json fixture. Deterministic, matches _load_fixture schema.
# ---------------------------------------------------------------------------


def _dedup_preserve_order(values: list[str], *, casefold: bool = True) -> list[str]:
    """Order-preserving dedup of non-empty trimmed strings.

    ``casefold`` (default) dedups case-insensitively — right for keyword lists.
    Pass ``casefold=False`` for ``forbidden_inventions``, whose entries are regexes
    where case is significant (``Epic\\b`` ≠ ``epic\\b``).
    """
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        trimmed = v.strip()
        key = trimmed.lower() if casefold else trimmed
        if trimmed and key not in seen:
            seen.add(key)
            out.append(trimmed)
    return out


def collate_expected(
    annotations_doc: dict[str, Any],
    bootstrap_doc: dict[str, Any],
) -> dict[str, Any]:
    """Collate a completed annotations.json into an expected.json fixture dict.

    Deterministic and LLM-free. Produces exactly the field set
    ``evals/runner.py:_load_fixture`` reads:

    - ``candidate_name``: the bootstrap's ``candidate_username`` (display only).
    - ``must_keywords``: the representatives of ``keep``-verdict SKILL clusters
      (skills are already clean keyword tokens), case-insensitively deduped — the
      grounded core that must survive into output (graded by ``keyword_coverage``).
    - ``forbidden_inventions``: the ``forbidden_pattern`` of every
      ``fabricated``-verdict bullet and skill (validation guaranteed each compiles)
      — the JD-invariant fabrication patterns (graded by ``grounding``).
    - ``min_*_score``: from ``annotations.min_scores`` if present, else
      ``DEFAULT_MIN_SCORES``.
    - ``notes``: the annotator notes plus a one-line provenance stamp.
    """
    validate_annotations(annotations_doc)

    must_keywords = _dedup_preserve_order(
        [
            s["representative"].lower()
            for s in annotations_doc["skills"]
            if s.get("verdict") == "keep" and s.get("representative")
        ]
    )

    forbidden = [
        item["forbidden_pattern"]
        for item in (*annotations_doc["bullets"], *annotations_doc["skills"])
        if item.get("verdict") == "fabricated" and item.get("forbidden_pattern")
    ]
    forbidden_inventions = _dedup_preserve_order(forbidden, casefold=False)

    min_scores = {**DEFAULT_MIN_SCORES, **(annotations_doc.get("min_scores") or {})}

    candidate = bootstrap_doc.get("candidate_username", "")
    prompt_version = bootstrap_doc.get("prompt_version", "")
    n_fab = len(forbidden_inventions)
    n_keep = len(must_keywords)
    annotator_notes = (annotations_doc.get("notes") or "").strip()
    provenance = (
        f"Collated from bootstrap (prompt_version={prompt_version}) for candidate "
        f"{candidate!r}: {n_keep} grounded-skill keyword(s), {n_fab} fabrication "
        f"pattern(s). Run via: python evals/runner.py --suite real --seed <seed.json>."
    )
    notes = f"{annotator_notes}\n\n{provenance}" if annotator_notes else provenance

    return {
        "candidate_name": candidate,
        "must_keywords": must_keywords,
        "forbidden_inventions": forbidden_inventions,
        "min_grounding_score": min_scores["grounding"],
        "min_keyword_coverage_score": min_scores["keyword_coverage"],
        "min_ats_format_score": min_scores["ats_format"],
        "min_tone_score": min_scores["tone"],
        "min_clarification_quality_score": min_scores["clarification_quality"],
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Collation → improvement brief (markdown). Deterministic. Next branch's input.
# ---------------------------------------------------------------------------


def pick_anchor_jd(bootstrap_doc: dict[str, Any], override: str | None = None) -> str:
    """Return the anchor JD filename for the produced fixture.

    Default: the JD appearing in the most bullet clusters — the widest-span / most
    JD-invariant posting, the best single regression representative. Ties break on
    sorted filename for determinism. ``override`` (a jd_file name) wins if given.
    Falls back to the first ``per_jd`` jd_file when there are no bullet clusters.
    """
    if override:
        return override
    counts: Counter[str] = Counter()
    for cluster in bootstrap_doc.get("dedup", {}).get("bullets", {}).get("clusters", []):
        for jd in cluster.get("jd_files", []):
            counts[jd] += 1
    if counts:
        # Deterministic: highest cluster count, ties broken lexicographically.
        best_count = max(counts.values())
        return sorted(jd for jd, n in counts.items() if n == best_count)[0]
    per_jd = bootstrap_doc.get("per_jd", [])
    return per_jd[0].get("jd_file", "") if per_jd else ""


def _scorer_disagreements(annotations_doc: dict[str, Any]) -> list[str]:
    """Lines where a human bullet verdict disagrees with the inline grounding scores.

    The v1.0.4 tag criterion 'annotations validate the automated scorers' lives
    here: a ``fabricated`` verdict on a bullet the model scored highly grounded, or
    a ``keep`` verdict the NLI flagged as a contradiction, is exactly the
    signal that tells us whether MiniCheck/NLI are catching what humans catch.
    """
    lines: list[str] = []
    for item in annotations_doc["bullets"]:
        verdict = item.get("verdict")
        mc = item.get("minicheck_grounding_score")
        contradiction = item.get("nli_contradiction_flag")
        rep = item.get("representative", "")
        if verdict == "fabricated" and isinstance(mc, (int, float)) and mc >= 0.5:
            lines.append(
                f"- human=`fabricated` but MiniCheck={mc} (≥0.5 = scorer thinks grounded): {rep!r}"
            )
        if verdict == "keep" and contradiction is True:
            lines.append(f"- human=`keep` but NLI flagged a contradiction: {rep!r}")
    return lines


def build_improvement_brief(
    annotations_doc: dict[str, Any],
    bootstrap_doc: dict[str, Any],
) -> str:
    """Assemble the markdown improvement brief — the next branch's source material.

    Deterministic and LLM-free. Five sections: fabrication patterns (widest-span
    first), rewrites (``fix`` items as OK/NOT-OK worked-example seeds), omissions,
    clarification ratings, and scorer agreement.
    """
    validate_annotations(annotations_doc)

    candidate = bootstrap_doc.get("candidate_username", "")
    prompt_version = bootstrap_doc.get("prompt_version", "")
    jd_count = bootstrap_doc.get("jd_count", len(bootstrap_doc.get("per_jd", [])))

    all_items: list[tuple[str, dict[str, Any]]] = [
        ("bullet", b) for b in annotations_doc["bullets"]
    ] + [("skill", s) for s in annotations_doc["skills"]]

    out: list[str] = []
    out.append(f"# Improvement brief — {candidate}")
    out.append("")
    out.append(
        f"Source: bootstrap over {jd_count} JD(s) at `prompt_version={prompt_version}`. "
        f"Generated deterministically from `annotations.json`. This is the source "
        f"material for the next branch (`tuning/draft-and-gate-skill`) — not a prompt edit."
    )
    out.append("")

    # 1. Fabrication patterns — widest JD span first (most systemic).
    fab = [(kind, item) for kind, item in all_items if item.get("verdict") == "fabricated"]
    fab.sort(key=lambda ki: len(ki[1].get("jd_files", [])), reverse=True)
    out.append("## Fabrication patterns")
    out.append("")
    if fab:
        for kind, item in fab:
            span = len(item.get("jd_files", []))
            slugs = ", ".join(item.get("failed_rules", [])) or "(no slug)"
            out.append(
                f"- **{kind}** (span {span} JD(s); `{slugs}`): {item.get('representative', '')!r}"
            )
            out.append(f"  - forbidden_pattern: `{item.get('forbidden_pattern', '')}`")
            if item.get("note"):
                out.append(f"  - note: {item['note']}")
    else:
        out.append("_None flagged._")
    out.append("")

    # 2. Rewrites — fix items become OK/NOT-OK worked-example seeds.
    fixes = [(kind, item) for kind, item in all_items if item.get("verdict") == "fix"]
    out.append("## Rewrites (worked-example seeds: NOT OK → OK)")
    out.append("")
    if fixes:
        for kind, item in fixes:
            slugs = ", ".join(item.get("failed_rules", [])) or "(no slug)"
            out.append(f"- **{kind}** (`{slugs}`)")
            out.append(f"  - NOT OK: {item.get('representative', '')!r}")
            out.append(f"  - OK: {item.get('honest_rewrite', '')!r}")
            if item.get("note"):
                out.append(f"  - note: {item['note']}")
    else:
        out.append("_None flagged._")
    out.append("")

    # 3. Omissions — verdict omit OR explicit should_omit.
    omits = [
        (kind, item)
        for kind, item in all_items
        if item.get("verdict") == "omit" or item.get("should_omit") is True
    ]
    out.append("## Omissions (real but should not appear)")
    out.append("")
    if omits:
        for kind, item in omits:
            note = item.get("note") or "(no note)"
            out.append(f"- **{kind}**: {item.get('representative', '')!r} — {note}")
    else:
        out.append("_None flagged._")
    out.append("")

    # 4. Clarification ratings — weakest first.
    ratings = [r for r in annotations_doc["clarification_ratings"] if r.get("rating") is not None]
    ratings.sort(key=lambda r: float(r["rating"]))
    out.append("## Clarification-question ratings")
    out.append("")
    if ratings:
        for r in ratings:
            slugs = ", ".join(r.get("failed_rules", [])) or "—"
            out.append(
                f"- [{r['rating']}/5] ({r.get('jd_file', '')}) {r.get('question_text', '')!r} "
                f"— slugs: {slugs}" + (f" — {r['note']}" if r.get("note") else "")
            )
    else:
        out.append("_No questions rated._")
    out.append("")

    # 5. Scorer agreement — where humans and the offline scorers disagree.
    out.append("## Scorer agreement (human verdict vs MiniCheck/NLI pre-scores)")
    out.append("")
    disagreements = _scorer_disagreements(annotations_doc)
    if disagreements:
        out.extend(disagreements)
    else:
        out.append("_No disagreements between human verdicts and the offline grounding scorers._")
    out.append("")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Write-path guard — mirrors evals/bootstrap.py. Refuses to emit (PII-bearing)
# artifacts anywhere except evals/fixtures/real/.
# ---------------------------------------------------------------------------


def _within(path: Path, parent: Path) -> bool:
    """Return True only if path resolves to within parent. Mirrors app.py:_within."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _guard(target: Path) -> Path:
    """Resolve ``target`` and enforce containment under ALLOWED_ROOT (fail closed)."""
    resolved = target.expanduser()
    if not _within(resolved, ALLOWED_ROOT):
        raise ValueError(
            f"refusing to write outside {ALLOWED_ROOT.as_posix()} "
            f"(resolved target: {resolved.resolve().as_posix()})"
        )
    return resolved.resolve()


def _resolve_template_path(
    candidate_username: str, bootstrap_path: Path, out_arg: str | None
) -> Path:
    """Compute the annotations.json path (default: beside the bootstrap) and guard it."""
    if out_arg:
        return _guard(Path(out_arg))
    return _guard(bootstrap_path.parent / "annotations.json")


def _resolve_fixture_slug(candidate_username: str, slug_arg: str | None) -> str:
    """Sanitize the fixture directory slug; default ``<candidate>-bootstrap``."""
    raw = slug_arg or f"{candidate_username}-bootstrap"
    slug = secure_filename(raw)
    if not slug:
        raise ValueError(f"fixture slug {raw!r} sanitizes to empty; pass --fixture-slug")
    return slug


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_bootstrap(path_str: str) -> tuple[dict[str, Any], Path]:
    """Read a bootstrap.json (validating its schema version) and return (doc, path)."""
    path = Path(path_str).expanduser()
    doc = json.loads(path.read_text(encoding="utf-8"))
    version = doc.get("bootstrap_schema_version")
    if version != 1:
        raise ValueError(f"unsupported bootstrap_schema_version={version!r}; this module reads 1")
    return doc, path


def _cmd_emit_template(
    bootstrap_doc: dict[str, Any], bootstrap_path: Path, out_arg: str | None
) -> int:
    candidate = str(bootstrap_doc.get("candidate_username", ""))
    out_path = _resolve_template_path(candidate, bootstrap_path, out_arg)
    template = build_annotation_template(bootstrap_doc, bootstrap_source=str(bootstrap_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info(
        "annotation template: %d bullet clusters, %d skill clusters, %d clarification "
        "questions → %s",
        len(template["bullets"]),
        len(template["skills"]),
        len(template["clarification_ratings"]),
        out_path.as_posix(),
    )
    return 0


def _cmd_collate(
    bootstrap_doc: dict[str, Any],
    bootstrap_path: Path,
    annotations_path: str,
    jd_dir_arg: str,
    slug_arg: str | None,
    anchor_arg: str | None,
) -> int:
    annotations_doc = load_annotations(annotations_path)
    candidate = str(bootstrap_doc.get("candidate_username", ""))

    jd_dir = Path(jd_dir_arg).expanduser()
    if not jd_dir.is_dir():
        logger.error("--jd-dir is not a directory: %s", jd_dir)
        return 1
    anchor_name = pick_anchor_jd(bootstrap_doc, anchor_arg)
    if not anchor_name:
        logger.error("could not determine an anchor JD (no bullet clusters and empty per_jd)")
        return 1
    anchor_src = jd_dir / anchor_name
    if not anchor_src.is_file():
        logger.error("anchor JD %s not found in --jd-dir %s", anchor_name, jd_dir.as_posix())
        return 1

    slug = _resolve_fixture_slug(candidate, slug_arg)
    fixture_dir = _guard(ALLOWED_ROOT / slug)
    expected_path = _guard(fixture_dir / "expected.json")
    jd_path = _guard(fixture_dir / "jd.txt")
    brief_path = _guard(bootstrap_path.parent / "improvement_brief.md")

    expected = collate_expected(annotations_doc, bootstrap_doc)
    brief = build_improvement_brief(annotations_doc, bootstrap_doc)

    fixture_dir.mkdir(parents=True, exist_ok=True)
    expected_path.write_text(
        json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil.copyfile(anchor_src, jd_path)
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief, encoding="utf-8")

    logger.info(
        "collated fixture %s: %d must_keywords, %d forbidden_inventions (anchor JD %s) → %s",
        slug,
        len(expected["must_keywords"]),
        len(expected["forbidden_inventions"]),
        anchor_name,
        fixture_dir.as_posix(),
    )
    logger.info("improvement brief → %s", brief_path.as_posix())
    logger.info(
        "run it: python evals/runner.py --suite real --seed evals/fixtures/real/%s/seed.json",
        candidate,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    ap = argparse.ArgumentParser(description="sartor. eval annotation contract")
    ap.add_argument(
        "--bootstrap",
        required=True,
        metavar="PATH",
        help="Path to a bootstrap.json (from evals.bootstrap).",
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--emit-template",
        action="store_true",
        help="Write a blank annotations.json skeleton beside the bootstrap.json.",
    )
    mode.add_argument(
        "--collate",
        action="store_true",
        help="Collate a completed annotations.json into a --suite real fixture + brief.",
    )
    ap.add_argument("--out", default=None, metavar="PATH", help="Override template output path.")
    ap.add_argument(
        "--annotations", default=None, metavar="PATH", help="Completed annotations.json (collate)."
    )
    ap.add_argument(
        "--jd-dir",
        default=None,
        metavar="PATH",
        help="JD directory used for the bootstrap (collate).",
    )
    ap.add_argument(
        "--fixture-slug",
        default=None,
        metavar="NAME",
        help="Fixture dir slug (default <candidate>-bootstrap).",
    )
    ap.add_argument(
        "--anchor-jd",
        default=None,
        metavar="NAME",
        help="JD filename to use as the fixture's jd.txt.",
    )
    args = ap.parse_args(argv)

    try:
        bootstrap_doc, bootstrap_path = _load_bootstrap(args.bootstrap)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Could not load --bootstrap %s: %s", args.bootstrap, exc)
        return 1

    try:
        if args.emit_template:
            return _cmd_emit_template(bootstrap_doc, bootstrap_path, args.out)
        if not args.annotations:
            logger.error("--collate requires --annotations PATH")
            return 1
        if not args.jd_dir:
            logger.error(
                "--collate requires --jd-dir PATH (the JD directory used for the bootstrap)"
            )
            return 1
        return _cmd_collate(
            bootstrap_doc,
            bootstrap_path,
            args.annotations,
            args.jd_dir,
            args.fixture_slug,
            args.anchor_jd,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("%s", exc)
        return 1


__all__ = [
    "ALLOWED_FAILED_RULES",
    "ANNOTATION_SCHEMA_VERSION",
    "DEFAULT_MIN_SCORES",
    "SUPPORTED_ANNOTATION_SCHEMA_VERSIONS",
    "VERDICTS",
    "build_annotation_template",
    "build_improvement_brief",
    "collate_expected",
    "load_annotations",
    "pick_anchor_jd",
    "validate_annotations",
]


if __name__ == "__main__":
    raise SystemExit(main())
