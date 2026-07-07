"""Diagnostics blueprint — annotation / bootstrap / eval / tune (Sprint 8.3h).

The dev-diagnostics write/SSE backend: the seventh and last domain seam extracted
from ``app.py`` (after it this module owns every former ``app.py`` route and the
monolith is the thin factory + WSGI handle + ``main()`` only).

Localhost-only, keyed by a real candidate username + a fixture slug, writing ONLY
under ``current_app.config["ANNOTATION_ROOT"]`` (``evals/fixtures/real/``). The
annotation contract + bootstrap collation are reused verbatim from
``evals.annotation`` / ``evals.bootstrap`` (deterministic, LLM-free) — these routes
are the thin Flask seam. The read-only UI lives in the ``/_dashboard`` "Annotate"
tab; the dashboard blueprint itself stays separate + read-only.

Security pattern per CLAUDE.md "Key Patterns — Security": ``_safe_username()`` +
``secure_filename()`` + ``_within()``. The 5 SSE routes follow the established
blueprint pattern (analysis/generation): every config value is captured as a local
**before** the ``stream()`` generator (which runs lazily, after the view returns),
so the generator never touches ``current_app``.

LLM-free at this layer: the paid work is delegated to ``evals.runner`` /
``evals.bootstrap`` / ``evals.grounding_signals`` and the ``web_infra`` client
factory, so this module imports no ``anthropic`` and is NOT on the egress allowlist.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from analyzer import prompt_overrides
from web_infra import _get_client, _is_localhost_request, _safe_username, _sse, _within

logger = logging.getLogger(__name__)

diagnostics_bp = Blueprint("diagnostics", __name__)


# ---------------------------------------------------------------------------
# Annotation + bootstrap write surface (the console's READ-WRITE routes).
#
# The domain helpers below are pure: each takes its containing directory (or the
# annotation root) explicitly rather than reading a module global, so they are
# testable without a request context (design §3.2 — non-request helpers take an
# explicit path arg). The routes read the root from `current_app.config` and pass
# it down.
# ---------------------------------------------------------------------------


def _annotation_fixture_path(slug: str, annotation_root: Path) -> Path | None:
    """Sanitize a fixture slug into a dir path under ``annotation_root``.

    Returns None when the slug sanitizes to empty. Does NOT check containment —
    every caller MUST still apply ``_within(path, annotation_root)`` (the gate is
    kept visible in each route per the security pattern).
    """
    safe = secure_filename(slug or "")
    if not safe:
        return None
    return annotation_root / safe


def _load_bootstrap_doc(fixture_dir: Path) -> dict | None:
    """Read a fixture's bootstrap.json. None if absent or malformed."""
    bootstrap_path = fixture_dir / "bootstrap.json"
    if not bootstrap_path.exists():
        return None
    try:
        return json.loads(bootstrap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_seed_json(fixture_dir: Path, seed: dict) -> Path:
    """Canonical writer for a fixture's seed.json corpus snapshot.

    The single source of the dump format, shared by the paid bootstrap route (which
    captures the seed as a side effect of the run) and the standalone export route.
    The caller owns the `_within` containment check + `fixture_dir.mkdir`.
    """
    seed_path = fixture_dir / "seed.json"
    seed_path.write_text(
        json.dumps(seed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return seed_path


def _patch_annotation_scores(ann_path: Path, grounding_signals: dict) -> int:
    """Patch ONLY the inline grounding score fields onto an existing annotations.json.

    Joins the freshly-computed nli/minicheck lists to each bullet by cluster_index
    (the same index alignment ``build_annotation_template`` uses) and overwrites the
    three score fields, leaving every human-entered verdict / note / rewrite intact.
    Returns the number of bullet items patched. Best-effort: a malformed file is left
    untouched (returns 0). Does NOT re-validate — an in-progress annotations.json is
    intentionally incomplete and must not be rejected by a score backfill.
    """
    try:
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(doc, dict):
        return 0
    nli_list = grounding_signals.get("nli", []) or []
    mc_list = grounding_signals.get("minicheck", []) or []
    patched = 0
    for item in doc.get("bullets", []) or []:
        if not isinstance(item, dict):
            continue
        idx = item.get("cluster_index")
        if not isinstance(idx, int):
            continue
        changed = False
        if 0 <= idx < len(nli_list):
            item["nli_entailment_score"] = nli_list[idx].get("nli_entailment_score")
            item["nli_contradiction_flag"] = nli_list[idx].get("nli_contradiction_flag")
            changed = True
        if 0 <= idx < len(mc_list):
            item["minicheck_grounding_score"] = mc_list[idx].get("minicheck_grounding_score")
            changed = True
        if changed:
            patched += 1
    if patched:
        ann_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return patched


@diagnostics_bp.route("/api/annotation/fixtures", methods=["GET"])
def annotation_fixtures() -> ResponseReturnValue:
    """List bootstrap fixtures under ANNOTATION_ROOT (localhost-only, read-only).

    Reads only the fixed ANNOTATION_ROOT tree (no user-supplied path), so there is
    no traversal vector here; the localhost guard is the access control.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    fixtures = []
    if annotation_root.exists():
        for entry in sorted(annotation_root.iterdir()):
            if not entry.is_dir():
                continue
            doc = _load_bootstrap_doc(entry)
            if doc is None:
                continue
            dedup = doc.get("dedup", {}) or {}
            fixtures.append(
                {
                    "slug": entry.name,
                    "candidate_username": doc.get("candidate_username", ""),
                    "prompt_version": doc.get("prompt_version", ""),
                    "jd_count": doc.get("jd_count", 0),
                    "bullet_clusters": (dedup.get("bullets", {}) or {}).get("cluster_count", 0),
                    "skill_clusters": (dedup.get("skills", {}) or {}).get("cluster_count", 0),
                    "has_annotations": (entry / "annotations.json").exists(),
                    "has_expected": (entry / "expected.json").exists(),
                }
            )
    return jsonify({"fixtures": fixtures})


@diagnostics_bp.route("/api/annotation/fixture/<username>/<slug>", methods=["GET"])
def annotation_load(username: str, slug: str) -> ResponseReturnValue:
    """Return the working annotations doc for a fixture (localhost-only, read).

    Existing annotations.json if present, else a blank template built from the
    bootstrap (`build_annotation_template`). Also returns the verdict +
    failed_rules vocabulary so the UI can render constrained controls.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug, annotation_root)
    if fixture_dir is None or not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404

    from evals.annotation import (
        ALLOWED_FAILED_RULES,
        VERDICTS,
        build_annotation_template,
    )

    ann_path = fixture_dir / "annotations.json"
    if ann_path.exists():
        doc = json.loads(ann_path.read_text(encoding="utf-8"))
    else:
        doc = build_annotation_template(
            bootstrap,
            bootstrap_source=str(fixture_dir / "bootstrap.json"),
        )
    return jsonify(
        {
            "annotations": doc,
            "has_annotations": ann_path.exists(),
            "vocab": {
                "verdicts": sorted(VERDICTS),
                "failed_rules": sorted(ALLOWED_FAILED_RULES),
            },
        }
    )


@diagnostics_bp.route("/api/annotation/fixture/<username>/<slug>", methods=["POST"])
def annotation_save(username: str, slug: str) -> ResponseReturnValue:
    """Write a completed annotations.json (localhost-only, fail-closed).

    Validation is `evals.annotation.validate_annotations` — the SAME fail-closed
    contract the CLI uses, so the on-disk file is always collation-ready (every
    bullet/skill has a verdict; fix→honest_rewrite; fabricated→compilable
    forbidden_pattern). An incomplete doc is rejected with the validator message.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug, annotation_root)
    if fixture_dir is None or not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400
    if not (fixture_dir / "bootstrap.json").exists():
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404
    doc = request.get_json(silent=True)
    if not isinstance(doc, dict):
        return jsonify({"error": "Request body must be a JSON annotations object"}), 400

    from evals.annotation import validate_annotations

    try:
        validate_annotations(doc)
    except ValueError as exc:
        return jsonify({"error": "Annotations failed validation", "detail": str(exc)}), 400

    fixture_dir.mkdir(parents=True, exist_ok=True)
    out_path = fixture_dir / "annotations.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info(
        "Saved annotations for fixture %s (%d bullets, %d skills)",
        slug,
        len(doc.get("bullets", [])),
        len(doc.get("skills", [])),
    )
    return jsonify(
        {
            "ok": True,
            "path": str(out_path),
            "bullets": len(doc.get("bullets", [])),
            "skills": len(doc.get("skills", [])),
        }
    )


@diagnostics_bp.route("/api/annotation/fixture/<username>/<slug>/collate", methods=["POST"])
def annotation_collate(username: str, slug: str) -> ResponseReturnValue:
    """Collate a saved annotations.json → expected.json + improvement_brief.md.

    Deterministic, LLM-free: reuses `collate_expected` + `build_improvement_brief`
    + `pick_anchor_jd`. Writes the fixture artifacts beside the bootstrap, plus a
    `jd.txt` copied from the saved `jds/<anchor>` (the wrapper stores pasted JDs
    there) so the produced fixture is runnable by `runner.py --suite real`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug, annotation_root)
    if fixture_dir is None or not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404
    ann_path = fixture_dir / "annotations.json"
    if not ann_path.exists():
        return jsonify({"error": "Save annotations before collating"}), 400

    from evals.annotation import (
        build_improvement_brief,
        collate_expected,
        pick_anchor_jd,
        validate_annotations,
    )

    annotations = json.loads(ann_path.read_text(encoding="utf-8"))
    try:
        validate_annotations(annotations)
    except ValueError as exc:
        return jsonify({"error": "Annotations failed validation", "detail": str(exc)}), 400

    expected = collate_expected(annotations, bootstrap)
    brief = build_improvement_brief(annotations, bootstrap)

    # Anchor JD text → jd.txt (best-effort; the wrapper saves pasted JDs in jds/).
    anchor_name = pick_anchor_jd(bootstrap)
    anchor_src = (fixture_dir / "jds" / secure_filename(anchor_name)) if anchor_name else None
    jd_written = False
    if anchor_src is not None and _within(anchor_src, annotation_root) and anchor_src.exists():
        (fixture_dir / "jd.txt").write_text(
            anchor_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        jd_written = True

    expected_path = fixture_dir / "expected.json"
    brief_path = fixture_dir / "improvement_brief.md"
    expected_path.write_text(
        json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    brief_path.write_text(brief, encoding="utf-8")
    logger.info(
        "Collated fixture %s: %d must_keywords, %d forbidden_inventions",
        slug,
        len(expected.get("must_keywords", [])),
        len(expected.get("forbidden_inventions", [])),
    )
    return jsonify(
        {
            "ok": True,
            "expected_path": str(expected_path),
            "brief_path": str(brief_path),
            "jd_written": jd_written,
            "anchor_jd": anchor_name,
            "must_keywords": len(expected.get("must_keywords", [])),
            "forbidden_inventions": len(expected.get("forbidden_inventions", [])),
            "run_command": (
                f"python evals/runner.py --suite real --seed "
                f"evals/fixtures/real/{secure_filename(slug)}/seed.json"
            ),
        }
    )


@diagnostics_bp.route("/api/annotation/fixture/<username>/<slug>/score", methods=["POST"])
def annotation_score_grounding(username: str, slug: str) -> ResponseReturnValue:
    """Backfill grounding pre-scores onto an existing bootstrap.json (localhost, SSE).

    Runs the offline grounding scorers (DeBERTa NLI + MiniCheck-FT5) over the deduped
    bullet-cluster representatives, scoring against the corpus the bootstrap was built
    from — recovered by importing the fixture's `seed.json` into a throwaway in-memory
    SQLite (no live-DB writes) and synthesizing the same résumé text the pipeline saw.
    Writes the result back under `grounding_signals` and patches any existing
    annotations.json score fields. NO paid LLM calls — pure CPU work on already-generated
    bullets — so a user who bootstrapped *before* installing the `[eval-grounding]` extras
    can light up the annotation editor without re-running the (paid) pipeline. Streams
    `start` / `scoring` / `done` / `error`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    fixture_dir = _annotation_fixture_path(slug, annotation_root)
    if fixture_dir is None or not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400
    bootstrap = _load_bootstrap_doc(fixture_dir)
    if bootstrap is None:
        return jsonify({"error": "No bootstrap.json for this fixture"}), 404

    seed_path = fixture_dir / "seed.json"
    if not seed_path.exists():
        return jsonify(
            {
                "error": "No seed.json for this fixture — re-run the bootstrap to capture the "
                "corpus snapshot, then score.",
            }
        ), 409

    clusters = ((bootstrap.get("dedup", {}) or {}).get("bullets", {}) or {}).get(
        "clusters", []
    ) or []
    if not clusters:
        return jsonify({"error": "Bootstrap has no bullet clusters to score"}), 400

    # grounding_signals is pure-Python (heavy deps import lazily inside the scorer),
    # so this import always succeeds; a missing `[eval-grounding]` extra surfaces as
    # an ImportError when the scorer runs (handled in the worker below).
    from evals.grounding_signals import run_grounding_signals

    # Score against the corpus this bootstrap was built from: import its seed.json
    # into a throwaway in-memory SQLite (no live-DB writes, no Application anchor on
    # the real DB) and synthesize the same résumé text the pipeline saw. This stays
    # faithful even if the live corpus was edited since the bootstrap ran.
    try:
        from db.build_context import build_context_set_from_db
        from evals.seed_import import seeded_session

        with seeded_session(seed_path) as (seed_session, seed_user):
            ctx, _app, _run = build_context_set_from_db(
                seed_session,
                candidate_username=seed_user,
                jd_text="(grounding backfill)",
                run_id="grounding-backfill",
            )
            corpus_source = (ctx["resume"]["text"] or "").strip()
    except Exception as exc:
        logger.warning("Grounding backfill: could not read corpus from seed for %s: %s", slug, exc)
        return jsonify({"error": "Could not read corpus from seed.json", "detail": str(exc)}), 500
    if not corpus_source:
        return jsonify({"error": "Corpus snapshot is empty — nothing to score against"}), 400

    # Render representatives exactly as build_bootstrap_document does, so the
    # returned nli/minicheck lists stay index-aligned with dedup.bullets.clusters.
    reps_md = "\n".join(f"- {c.get('representative', '')}" for c in clusters)
    bootstrap_path = fixture_dir / "bootstrap.json"
    ann_path = fixture_dir / "annotations.json"

    def stream() -> Iterator[str]:
        """SSE generator: stream grounding-signal scoring progress, then the terminal result/error event."""
        import queue as _queue
        import threading

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker() -> None:
            """Thread target: run grounding signals over the corpus; stash the result/error and signal done."""
            try:
                result["gs"] = run_grounding_signals(reps_md, [corpus_source])
            except ImportError as exc:
                result["import_error"] = exc
            except Exception as exc:
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {"slug": slug, "bullet_clusters": len(clusters)})
        yield _sse(
            "scoring",
            {
                "message": f"Scoring {len(clusters)} bullet clusters (DeBERTa NLI + MiniCheck, "
                "~2-4s each)…",
            },
        )

        # Single scorer call (no incremental progress) — block until the worker is done.
        while events.get() is not sentinel:
            pass

        if "import_error" in result:
            logger.warning(
                "Grounding backfill: extras not installed for %s: %s", slug, result["import_error"]
            )
            yield _sse(
                "error",
                {
                    "error": "Grounding extras not installed.",
                    "detail": "Install with: pip install -e '.[eval-grounding]' (see CONTRIBUTING.md).",
                    "http_status": 400,
                },
            )
            return
        if "error" in result:
            logger.error(
                "Grounding backfill failed for %s: %s",
                slug,
                result["error"],
                exc_info=result["error"],
            )
            yield _sse(
                "error",
                {
                    "error": "Grounding scoring failed.",
                    "detail": str(result["error"]),
                    "http_status": 500,
                },
            )
            return

        gs = result["gs"]
        bootstrap["grounding_signals"] = gs
        bootstrap_path.write_text(
            json.dumps(bootstrap, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        patched = _patch_annotation_scores(ann_path, gs) if ann_path.exists() else 0
        bullet_count = gs.get("bullet_count", 0)
        logger.info(
            "Grounding backfill wrote %s (%d bullets scored, %d annotations patched)",
            slug,
            bullet_count,
            patched,
        )
        yield _sse(
            "done",
            {
                "slug": slug,
                "bullet_count": bullet_count,
                "mean_entailment": (gs.get("nli_summary", {}) or {}).get("mean_entailment", 0.0),
                "mean_minicheck": (gs.get("minicheck_summary", {}) or {}).get("mean_score", 0.0),
                "annotations_patched": patched,
            },
        )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@diagnostics_bp.route("/api/annotation/seed/export", methods=["POST"])
def annotation_seed_export() -> ResponseReturnValue:
    """Export one candidate's corpus to seed.json — deterministic, LLM-free (localhost).

    The no-cost counterpart to the paid bootstrap's seed snapshot: reads the LIVE DB
    via `scripts.export_corpus_seed.export_seed` (read-only, no model calls) and writes
    `<ANNOTATION_ROOT>/<slug>/seed.json` through the shared `_write_seed_json` helper.
    Lets a user capture a corpus seed for the eval runner (`--seed`) / grounding backfill
    without paying for a bootstrap. Fast + synchronous, so a plain JSON response (no SSE).
    Security per CLAUDE.md "Key Patterns — Security": _safe_username() + secure_filename()
    + _within(seed_path, ANNOTATION_ROOT).
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    data = request.get_json(silent=True) or {}
    safe_user = _safe_username(
        data.get("username", ""), configs_dir=current_app.config["CONFIGS_DIR"]
    )
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    slug = secure_filename(data.get("slug") or f"{safe_user}-bootstrap")
    if not slug:
        return jsonify({"error": "Invalid fixture slug"}), 400
    fixture_dir = _annotation_fixture_path(slug, annotation_root)
    if fixture_dir is None or not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400
    seed_path = fixture_dir / "seed.json"
    if not _within(seed_path, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400

    from db.session import get_session, init_db
    from scripts.export_corpus_seed import export_seed

    init_db()
    session = get_session()
    try:
        seed = export_seed(session, candidate_username=safe_user)
    except ValueError as exc:
        # Config exists (passed _safe_username) but no Candidate corpus row yet —
        # same needs-onboarding shape as /api/analyze. Distinct from the 400 above.
        return jsonify(
            {
                "error": "No corpus for this user yet — import a résumé / build the corpus first.",
                "detail": str(exc),
            }
        ), 409
    finally:
        session.close()

    fixture_dir.mkdir(parents=True, exist_ok=True)
    _write_seed_json(fixture_dir, seed)

    n_bullets = sum(len(e["bullets"]) for e in seed["experiences"])
    logger.info(
        "Seed export wrote %s/seed.json (%d experiences, %d bullets)",
        slug,
        len(seed["experiences"]),
        n_bullets,
    )
    return jsonify(
        {
            "ok": True,
            "slug": slug,
            "candidate": safe_user,
            "experiences": len(seed["experiences"]),
            "bullets": n_bullets,
            "summary_items": len(seed["summary_items"]),
            "skills": len(seed["skills"]),
            "path": f"evals/fixtures/real/{slug}/seed.json",
        }
    )


@diagnostics_bp.route("/api/annotation/bootstrap", methods=["POST"])
def annotation_bootstrap_stream() -> ResponseReturnValue:
    """Browser bootstrap wrapper — run the live pipeline over N pasted JDs (SSE).

    Reuses the streaming pattern of /api/analyze/stream and the analyzer
    primitives (via evals.bootstrap.run_pipeline_over_jd_texts — analyze → clarify
    → generate per JD against the LIVE corpus), then the deterministic
    `build_bootstrap_document` dedup, writing bootstrap.json + a seed.json corpus
    snapshot + the pasted JDs under ANNOTATION_ROOT/<slug>/. PAID (Sonnet/Haiku) +
    slow (~70s/JD). With `grounding_signals: true` it also runs the offline grounding
    scorers over the deduped bullets (eval-only models; degrades to an un-scored
    bootstrap + `warning` if the `[eval-grounding]` extras are missing). Progress
    streams as `start` / per-JD `jd_start`/`analyzing`/`clarifying`/`generating`/
    `jd_done` / optional `scoring` / optional `warning` / `done` / `error` events.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    annotation_root = current_app.config["ANNOTATION_ROOT"]
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    safe_user = _safe_username(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400

    # Opt-in: run the offline grounding scorers (DeBERTa NLI + MiniCheck-FT5) over
    # the deduped bullet representatives. Eval-only models (~3.2 GB, ~2-4 s/bullet),
    # gated by the same `[eval-grounding]` extras the CLI `--grounding-signals` uses.
    # Missing extras or a runtime scoring failure degrades to an un-scored bootstrap
    # with a warning event — never a 500 (the paid pipeline output is preserved).
    grounding_requested = bool(data.get("grounding_signals"))

    raw_jds = data.get("jds", [])
    jds: list[tuple[str, str]] = []
    for item in raw_jds if isinstance(raw_jds, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        text = str(item.get("text", "")).strip()
        if name and text:
            jds.append((name, text))
    if not jds:
        return jsonify({"error": "Provide at least one JD as {name, text}"}), 400

    slug = secure_filename(data.get("slug") or f"{safe_user}-bootstrap")
    if not slug:
        return jsonify({"error": "Invalid fixture slug"}), 400
    fixture_dir = annotation_root / slug
    if not _within(fixture_dir, annotation_root):
        return jsonify({"error": "Invalid fixture slug"}), 400

    from evals.bootstrap import (
        DEFAULT_JACCARD,
        build_bootstrap_document,
        run_pipeline_over_jd_texts,
    )
    from scripts.export_corpus_seed import export_seed

    client = _get_client()

    def stream() -> Iterator[str]:
        """SSE generator: stream the annotation-bootstrap pipeline's progress, then the terminal event."""
        import queue as _queue
        import threading

        from db.session import get_session, init_db

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker() -> None:
            """Thread target: run the bootstrap pipeline in a fresh DB session; stash result/error and signal done."""
            try:
                init_db()
                session = get_session()
                try:
                    per_jd, corpus = run_pipeline_over_jd_texts(
                        client,
                        session,
                        safe_user,
                        jds,
                        progress=lambda ev, payload: events.put(("progress", ev, payload)),
                    )
                    result["per_jd"] = per_jd
                    result["corpus"] = corpus
                    # Snapshot the entire approved corpus to a seed.json (read-only,
                    # LLM-free) while the live session is open. This is the durable
                    # source of truth the downstream eval (`runner.py --seed`) and the
                    # grounding backfill score against — and the file collate's
                    # `--seed` run-command already references. Non-fatal: a snapshot
                    # failure must never discard the (paid) pipeline output.
                    try:
                        result["seed"] = export_seed(session, candidate_username=safe_user)
                    except Exception as exc:
                        logger.warning("Could not export seed.json for %s: %s", safe_user, exc)
                        result["seed"] = None
                finally:
                    session.close()
            except Exception as exc:
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse("start", {"total": len(jds), "slug": slug, "candidate": safe_user})

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Bootstrap wrapper failed: %s", result["error"], exc_info=result["error"])
            yield _sse(
                "error",
                {
                    "error": "Bootstrap pipeline failed.",
                    "detail": str(result["error"]),
                    "http_status": 500,
                },
            )
            return

        # Optional grounding scorers (eval-only models), resolved AFTER the paid
        # pipeline so a missing dep never wastes the LLM spend. The grounding_signals
        # module is pure-Python (the heavy deps import lazily inside the scorer), so
        # the import here always succeeds; any scorer failure (a missing
        # `[eval-grounding]` extra, a drifted dep, a failed model download) is now
        # absorbed *inside* build_bootstrap_document, which degrades to an un-scored
        # doc rather than raising (window-8.5-findings EV-2) — so the paid pipeline
        # output is never lost and this route never 500s on a grounding hiccup.
        grounding_fn = None
        grounding_note = None
        if grounding_requested:
            from evals.grounding_signals import run_grounding_signals

            grounding_fn = run_grounding_signals
            yield _sse(
                "scoring",
                {
                    "message": "Running grounding scorers (DeBERTa NLI + MiniCheck) over "
                    "deduped bullets — this is CPU-bound (~2-4s/bullet)…",
                },
            )

        # Deterministic collation + write (LLM-free apart from the optional scorers).
        # build_bootstrap_document fails soft on grounding, so this never raises for
        # a scoring failure; we surface a note below from the outcome.
        doc = build_bootstrap_document(
            result["per_jd"],
            username=safe_user,
            seed_path="(browser bootstrap wrapper)",
            threshold=DEFAULT_JACCARD,
            corpus_source=result.get("corpus", ""),
            grounding_fn=grounding_fn,
        )
        if grounding_requested and doc.get("grounding_signals") is None:
            grounding_note = (
                "Grounding unavailable — bootstrap saved without scores (see the server "
                "log for detail; if the extras are missing, install with "
                "pip install -e '.[eval-grounding]' — see CONTRIBUTING.md)."
            )
        fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "bootstrap.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Persist the corpus snapshot so the fixture is runnable by
        # `runner.py --suite real --seed …/seed.json` and so the grounding backfill
        # can score against the exact corpus this bootstrap was built from.
        seed = result.get("seed")
        if seed is not None:
            _write_seed_json(fixture_dir, seed)
        # Persist the pasted JDs so collate can later produce the fixture jd.txt.
        jds_dir = fixture_dir / "jds"
        jds_dir.mkdir(parents=True, exist_ok=True)
        for name, text in jds:
            safe_name = secure_filename(name) or "jd"
            if not safe_name.endswith(".txt"):
                safe_name = f"{safe_name}.txt"
            jd_file = jds_dir / safe_name
            if _within(jd_file, annotation_root):
                jd_file.write_text(text, encoding="utf-8")
        grounded = doc.get("grounding_signals") is not None
        logger.info(
            "Bootstrap wrapper wrote %s (%d JDs, %d bullet clusters, grounded=%s)",
            slug,
            doc["jd_count"],
            doc["dedup"]["bullets"]["cluster_count"],
            grounded,
        )
        if grounding_note:
            yield _sse("warning", {"message": grounding_note})
        yield _sse(
            "done",
            {
                "slug": slug,
                "candidate": safe_user,
                "jd_count": doc["jd_count"],
                "bullet_clusters": doc["dedup"]["bullets"]["cluster_count"],
                "skill_clusters": doc["dedup"]["skills"]["cluster_count"],
                "grounded": grounded,
            },
        )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@diagnostics_bp.route("/api/eval/run", methods=["POST"])
def eval_run_stream() -> ResponseReturnValue:
    """Run an eval suite from the console (localhost-only, SSE).

    The browser counterpart to `python evals/runner.py …`: drives the extracted
    `evals.runner.run_suite` in a worker thread and streams coarse progress so the
    paid wait reads as alive. Two modes:
      • Quality "Run eval": {suite, subset, grounding_signals} → the committed
        synthetic/anchor fixtures (no corpus seed).
      • Annotate "Run this fixture": {suite:"real", fixture:<slug>, slug:<slug>,
        username:<candidate>} → resolve evals/fixtures/real/<slug>/seed.json and run
        that one fixture against its corpus — the collate `--seed` command, in-browser.

    PAID (Sonnet + Haiku): ~$0.35-0.40 smoke / ~$0.30 full per the runner's cost table;
    the UI shows a cost-band confirm() before POSTing. Streams `start` /
    `fixture_start` / `analyzing` / `clarifying` / `generating` / `rubric_done` /
    `fixture_done` / `done` / `error`. All eager validation (bad suite / unknown
    user / missing seed) returns a JSON 4xx BEFORE the worker spends anything.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}

    suite = str(data.get("suite", "synthetic"))
    if suite not in {"synthetic", "real", "all", "anchor", "exploration"}:
        return jsonify({"error": f"Invalid suite: {suite}"}), 400
    subset = "smoke" if str(data.get("subset", "full")) == "smoke" else "full"
    grounding_signals = bool(data.get("grounding_signals"))

    # Optional single-fixture scope (e.g. the collated <slug>). Sanitize with
    # secure_filename: it feeds FIXTURES_DIR/<suite>/<fixture> in run_suite, a
    # traversal-sensitive path join.
    raw_fixture = str(data.get("fixture", "")).strip()
    fixture_name = secure_filename(raw_fixture) if raw_fixture else None

    # Optional corpus-seed mode (the Annotate "Run this fixture" button). The seed
    # lives under ANNOTATION_ROOT/<slug>/seed.json (gitignored, PII-bearing). Resolve
    # + contain it and confirm the candidate user exists, all before any paid call.
    seed_data: dict | None = None
    raw_slug = str(data.get("slug", "")).strip()
    if raw_slug:
        annotation_root = current_app.config["ANNOTATION_ROOT"]
        safe_user = _safe_username(
            str(data.get("username", "")), configs_dir=current_app.config["CONFIGS_DIR"]
        )
        if not safe_user:
            return jsonify({"error": "Invalid or unknown user"}), 400
        fixture_dir = _annotation_fixture_path(raw_slug, annotation_root)
        if fixture_dir is None or not _within(fixture_dir, annotation_root):
            return jsonify({"error": "Invalid fixture slug"}), 400
        seed_path = fixture_dir / "seed.json"
        if not _within(seed_path, annotation_root) or not seed_path.exists():
            return jsonify(
                {
                    "error": "No seed.json for this fixture — re-run the bootstrap to "
                    "capture the corpus snapshot, then run the eval.",
                }
            ), 409
        from evals.seed_import import load_seed

        try:
            seed_data = load_seed(str(seed_path))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": "Could not load seed.json", "detail": str(exc)}), 400

    from evals.runner import run_suite

    def stream() -> Iterator[str]:
        """SSE generator: stream the eval-suite run's progress, then the terminal result/error event."""
        import queue as _queue
        import threading

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def worker() -> None:
            """Thread target: run the eval suite; stash the result/error and signal done."""
            try:
                result["res"] = run_suite(
                    suite=suite,
                    subset=subset,
                    fixture_name=fixture_name,
                    seed_data=seed_data,
                    grounding_signals=grounding_signals,
                    progress=lambda ev, payload: events.put(("progress", ev, payload)),
                )
            except Exception as exc:
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse(
            "start",
            {
                "suite": suite,
                "subset": subset,
                "fixture": fixture_name,
                "grounding": grounding_signals,
                "seeded": seed_data is not None,
            },
        )

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Console eval run failed: %s", result["error"], exc_info=result["error"])
            yield _sse(
                "error",
                {
                    "error": "Eval run failed.",
                    "detail": str(result["error"]),
                    "http_status": 500,
                },
            )
            return

        res = result["res"]
        logger.info(
            "Console eval run complete: %d pass, %d fail → %s", res.n_pass, res.n_fail, res.out_path
        )
        yield _sse(
            "done",
            {
                "suite": suite,
                "subset": subset,
                "out_file": res.out_path.name if res.out_path else None,
                "n_pass": res.n_pass,
                "n_fail": res.n_fail,
                "regressions": len(res.regressions),
                "exit_code": res.exit_code,
            },
        )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@diagnostics_bp.route("/api/tune/run", methods=["POST"])
def tune_run_stream() -> ResponseReturnValue:
    """Run a candidate-vs-baseline prompt A/B from the console (localhost-only, SSE).

    The browser face of the prompt-override tuning loop: drives `run_suite` TWICE in
    one worker — baseline (no overrides) then candidate (the pasted override map) — and
    streams a per-(fixture, rubric) delta computed by the LLM-free `evals.tune` helpers.
    The candidate run self-stamps `prompt_version=candidate:<hash>` via the override
    primitive, so it never pollutes score-over-time. **Promote stays manual** — this
    route never edits `analyzer.py`; it only surfaces the delta + candidate text.

    Input JSON: `prompt_overrides` ({CONSTANT_NAME: candidate_text}, required, one of
    the eight `analyzer._BASE_SYSTEM_PROMPTS` keys) + the same `suite`/`subset`/
    `grounding_signals` (and optional `slug`+`username` seed mode) as `/api/eval/run`.

    PAID (Sonnet + Haiku) — ~2× a single run (the UI confirm() surfaces the band). All
    eager validation (bad suite / empty or unknown override / unknown user / missing
    seed) returns a JSON 4xx BEFORE the worker spends anything — load-bearing because
    the baseline runs first, so a doomed candidate key must be caught here. Streams
    `start` / phased progress (`phase`=baseline|candidate) / `delta` / `error`.
    """
    if not _is_localhost_request():
        return jsonify({"error": "localhost only"}), 403
    data = request.get_json(silent=True) or {}

    suite = str(data.get("suite", "synthetic"))
    if suite not in {"synthetic", "real", "all", "anchor", "exploration"}:
        return jsonify({"error": f"Invalid suite: {suite}"}), 400
    subset = "smoke" if str(data.get("subset", "full")) == "smoke" else "full"
    grounding_signals = bool(data.get("grounding_signals"))

    # Candidate override map: {CONSTANT_NAME: text}. Required + shape-checked here, then
    # the prompt-NAMES validated via analyzer's canonical validator (raises ValueError on
    # an unknown key) — all before any paid call, so a typo never spends the baseline run.
    raw_overrides = data.get("prompt_overrides")
    if not isinstance(raw_overrides, dict) or not raw_overrides:
        return jsonify(
            {"error": "prompt_overrides must be a non-empty object {CONSTANT_NAME: candidate_text}"}
        ), 400
    overrides: dict[str, str] = {}
    for key, value in raw_overrides.items():
        if not isinstance(value, str) or not value.strip():
            return jsonify({"error": f"Candidate text for {key} is empty"}), 400
        overrides[str(key)] = value
    try:
        with prompt_overrides(overrides):
            pass
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Optional single-fixture scope (e.g. the collated <slug>). Sanitized like eval/run.
    raw_fixture = str(data.get("fixture", "")).strip()
    fixture_name = secure_filename(raw_fixture) if raw_fixture else None

    # Optional corpus-seed mode — identical contract to /api/eval/run. The seed lives
    # under ANNOTATION_ROOT/<slug>/seed.json (gitignored, PII-bearing); resolve + contain
    # it and confirm the candidate user exists, all before any paid call.
    seed_data: dict | None = None
    raw_slug = str(data.get("slug", "")).strip()
    if raw_slug:
        annotation_root = current_app.config["ANNOTATION_ROOT"]
        safe_user = _safe_username(
            str(data.get("username", "")), configs_dir=current_app.config["CONFIGS_DIR"]
        )
        if not safe_user:
            return jsonify({"error": "Invalid or unknown user"}), 400
        fixture_dir = _annotation_fixture_path(raw_slug, annotation_root)
        if fixture_dir is None or not _within(fixture_dir, annotation_root):
            return jsonify({"error": "Invalid fixture slug"}), 400
        seed_path = fixture_dir / "seed.json"
        if not _within(seed_path, annotation_root) or not seed_path.exists():
            return jsonify(
                {
                    "error": "No seed.json for this fixture — re-run the bootstrap to "
                    "capture the corpus snapshot, then run the A/B.",
                }
            ), 409
        from evals.seed_import import load_seed

        try:
            seed_data = load_seed(str(seed_path))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return jsonify({"error": "Could not load seed.json", "detail": str(exc)}), 400

    from evals.runner import EvalRunResult, run_suite
    from evals.tune import build_delta_table, format_delta_table, load_scores

    def stream() -> Iterator[str]:
        """SSE generator: stream the baseline-then-candidate tuning run's progress, then the terminal event."""
        import queue as _queue
        import threading
        from dataclasses import asdict

        events: _queue.Queue = _queue.Queue()
        sentinel = object()
        result: dict = {}

        def _run(phase: str, overrides_map: dict[str, str] | None) -> EvalRunResult:
            """Run the suite for one ``phase`` (with optional ``overrides_map``), emitting phase-tagged progress."""
            return run_suite(
                suite=suite,
                subset=subset,
                fixture_name=fixture_name,
                seed_data=seed_data,
                grounding_signals=grounding_signals,
                prompt_overrides_map=overrides_map,
                progress=lambda ev, payload: events.put(
                    ("progress", ev, {**payload, "phase": phase})
                ),
            )

        def worker() -> None:
            """Thread target: run baseline then candidate; stash results/error and signal done."""
            try:
                result["baseline"] = _run("baseline", None)
                result["candidate"] = _run("candidate", overrides)
            except Exception as exc:
                result["error"] = exc
            finally:
                events.put(sentinel)

        threading.Thread(target=worker, daemon=True).start()
        yield _sse(
            "start",
            {
                "mode": "tune",
                "runs": 2,
                "suite": suite,
                "subset": subset,
                "fixture": fixture_name,
                "grounding": grounding_signals,
                "seeded": seed_data is not None,
                "overrides": sorted(overrides),
            },
        )

        while True:
            item = events.get()
            if item is sentinel:
                break
            _, event_kind, payload = item
            yield _sse(event_kind, payload)

        if "error" in result:
            logger.error("Console tune A/B failed: %s", result["error"], exc_info=result["error"])
            yield _sse(
                "error",
                {
                    "error": "Tune A/B failed.",
                    "detail": str(result["error"]),
                    "http_status": 500,
                },
            )
            return

        base = result["baseline"]
        cand = result["candidate"]
        if base.out_path is None or cand.out_path is None:
            yield _sse("error", {"error": "No fixtures matched — nothing to compare."})
            return

        rows = build_delta_table(load_scores(base.out_path), load_scores(cand.out_path))
        logger.info(
            "Console tune A/B complete: baseline %d/%d, candidate %d/%d (%s) → %d row(s)",
            base.n_pass,
            base.n_fail,
            cand.n_pass,
            cand.n_fail,
            cand.candidate_version,
            len(rows),
        )
        yield _sse(
            "delta",
            {
                "table": format_delta_table(rows),
                "rows": [asdict(r) for r in rows],
                "candidate_version": cand.candidate_version,
                "baseline_file": base.out_path.name,
                "candidate_file": cand.out_path.name,
                "regressed": sum(1 for r in rows if r.regressed),
                "baseline": {"n_pass": base.n_pass, "n_fail": base.n_fail},
                "candidate": {"n_pass": cand.n_pass, "n_fail": cand.n_fail},
            },
        )

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
