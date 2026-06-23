"""Offline grounding signal scorers for the eval harness.

Two belt-and-suspenders grounding detectors, gated behind
``python evals/runner.py --grounding-signals``. Never imported
by the production pipeline.

Models:
    DeBERTa-v3-base-mnli-fever-anli (Apache 2.0, ~180 MB)
        NLI entailment: is each bullet entailed by the source material?
    MiniCheck flan-t5-large (~3 GB on first download to HuggingFace cache)
        Factual grounding: is each bullet supported by the source document?

Install:
    See CONTRIBUTING.md "Grounding signal scorers (optional, dev-only)" for
    torch CPU/CUDA instructions and model download details.
"""

from __future__ import annotations

from typing import Any

_NLI_MODEL_ID = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
_MINICHECK_MODEL_NAME = "flan-t5-large"
# P(contradiction) threshold above which nli_contradiction_flag fires.
# Conservative at 0.4: flags strong contradictions, not weak disagreements.
_CONTRADICTION_THRESHOLD = 0.4


def extract_bullets(generated_resume: str) -> list[str]:
    """Extract bullet lines from a generated markdown résumé.

    Matches lines that start with '- ' after stripping leading whitespace.
    Returns plain text with the leading marker stripped.
    """
    bullets = []
    for line in generated_resume.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            text = stripped[2:].strip()
            if text:
                bullets.append(text)
    return bullets


def _load_nli_pipeline() -> Any:
    """Load the DeBERTa NLI text-classification pipeline. Lazy-imports transformers."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise ImportError(
            "transformers is required for NLI scoring. "
            "See CONTRIBUTING.md 'Grounding signal scorers' for install instructions."
        ) from exc
    return pipeline(
        "text-classification",
        model=_NLI_MODEL_ID,
        device=-1,   # CPU; pass device=0 for CUDA
        top_k=None,  # return all three label scores
    )


def _load_minicheck_scorer() -> Any:
    """Load the MiniCheck flan-t5-large scorer. Lazy-imports minicheck.

    First call downloads ~3 GB of model weights to the HuggingFace cache
    (~/.cache/huggingface/ on Linux/Mac, %USERPROFILE%\\.cache\\huggingface\\ on Windows).

    Note: ``flan-t5-large`` is a non-vLLM checkpoint, so the pinned minicheck
    (see pyproject ``eval-grounding``) routes it through the transformers
    ``Inferencer`` path and selects the device internally — the constructor no
    longer accepts a ``device`` kwarg (it is vLLM-only on the LLM checkpoints).
    """
    try:
        from minicheck.minicheck import MiniCheck
    except ImportError as exc:
        raise ImportError(
            "minicheck is required for MiniCheck scoring. "
            "See CONTRIBUTING.md 'Grounding signal scorers' for install instructions."
        ) from exc
    _ensure_minicheck_nltk_data()
    return MiniCheck(
        model_name=_MINICHECK_MODEL_NAME,
        enable_prefix_caching=False,
    )


def _ensure_minicheck_nltk_data() -> None:
    """Ensure NLTK's ``punkt_tab`` tokenizer data is present before MiniCheck runs.

    MiniCheck sentence-splits documents with NLTK; ``nltk>=3.9`` renamed the
    ``punkt`` resource to ``punkt_tab``, and a fresh install does not ship it, so
    ``MiniCheck.score()`` crashes with a ``LookupError`` deep inside the library
    (the EV-1 never-run-setup class — window-8.5-findings). Download it once if
    missing. Dev-only tooling; mirrors the implicit HuggingFace weight download
    above (NLTK is not a sanctioned-egress library — see test_egress_allowlist).
    """
    import nltk  # noqa: PLC0415

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def score_nli_bullets(
    bullets: list[str],
    source_text: str,
    *,
    _pipeline: Any = None,
) -> list[dict[str, Any]]:
    """NLI entailment check: is each bullet entailed by source_text?

    Model: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli (Apache 2.0, ~180 MB).

    Args:
        bullets: Plain-text bullet strings extracted from the generated résumé.
        source_text: Concatenated source material (résumé + clarification answers).
        _pipeline: Pre-loaded pipeline instance; loaded on demand if None.
                   Pass a mock here in tests to avoid any model download.

    Returns:
        List of dicts per bullet: {"bullet", "nli_entailment_score", "nli_contradiction_flag"}.
        nli_contradiction_flag is True when P(contradiction) > _CONTRADICTION_THRESHOLD.
    """
    if not bullets or not source_text:
        return []

    nli = _pipeline or _load_nli_pipeline()
    results: list[dict[str, Any]] = []
    for bullet in bullets:
        raw = nli({"text": source_text, "text_pair": bullet}, truncation=True)
        # raw: [{"label": str, "score": float}, ...] for all three NLI classes
        scores = {item["label"].lower(): item["score"] for item in raw}
        results.append({
            "bullet": bullet,
            "nli_entailment_score": round(scores.get("entailment", 0.0), 4),
            "nli_contradiction_flag": scores.get("contradiction", 0.0) > _CONTRADICTION_THRESHOLD,
        })
    return results


def score_minicheck_bullets(
    bullets: list[str],
    source_text: str,
    *,
    _scorer: Any = None,
) -> list[dict[str, Any]]:
    """MiniCheck-FT5 factual grounding check: is each bullet supported by source_text?

    Model: flan-t5-large fine-tuned checkpoint (~3 GB on first download).

    Args:
        bullets: Plain-text bullet strings extracted from the generated résumé.
        source_text: Concatenated source material (résumé + clarification answers).
        _scorer: Pre-loaded MiniCheck instance; loaded on demand if None.
                 Pass a mock here in tests to avoid any model download.

    Returns:
        List of dicts per bullet: {"bullet", "minicheck_grounding_score"}.
        Score 0.0–1.0; higher = more likely grounded in source.
    """
    if not bullets or not source_text:
        return []

    scorer = _scorer or _load_minicheck_scorer()
    # MiniCheck.score() returns a 4-tuple (pred_labels, raw_prob_scores,
    # used_chunks, raw_arrays); we want the 2nd element, the per-claim support
    # probabilities. (The pinned minicheck annotates this `-> List[float]`, which
    # is wrong — the runtime value is the 4-tuple. Verified against the real model.)
    _, raw_probs, _, _ = scorer.score(
        docs=[source_text] * len(bullets),
        claims=bullets,
    )
    return [
        {
            "bullet": bullet,
            "minicheck_grounding_score": round(float(prob), 4),
        }
        for bullet, prob in zip(bullets, raw_probs, strict=True)
    ]


def run_grounding_signals(
    generated_resume: str,
    source_texts: list[str],
) -> dict[str, Any]:
    """Orchestrate bullet extraction + NLI + MiniCheck scoring.

    Models are loaded once and passed through to both scorers.

    Args:
        generated_resume: Raw markdown string from generate().
        source_texts: Source texts to ground against (résumé text + clarification answers).

    Returns:
        Dict with bullet_count, per-bullet nli/minicheck results, and summary stats.
        Returns a zero-state dict when no bullets are found in the resume.
    """
    bullets = extract_bullets(generated_resume)
    if not bullets:
        return {
            "bullet_count": 0,
            "nli": [],
            "nli_summary": {"mean_entailment": 0.0, "contradiction_count": 0},
            "minicheck": [],
            "minicheck_summary": {"mean_score": 0.0, "low_score_count": 0},
        }

    source_text = " ".join(t for t in source_texts if t)

    nli_pipeline = _load_nli_pipeline()
    mc_scorer = _load_minicheck_scorer()

    nli_results = score_nli_bullets(bullets, source_text, _pipeline=nli_pipeline)
    mc_results = score_minicheck_bullets(bullets, source_text, _scorer=mc_scorer)

    nli_entailments = [r["nli_entailment_score"] for r in nli_results]
    mc_scores = [r["minicheck_grounding_score"] for r in mc_results]

    return {
        "bullet_count": len(bullets),
        "nli": nli_results,
        "nli_summary": {
            "mean_entailment": round(sum(nli_entailments) / len(nli_entailments), 4),
            "contradiction_count": sum(1 for r in nli_results if r["nli_contradiction_flag"]),
        },
        "minicheck": mc_results,
        "minicheck_summary": {
            "mean_score": round(sum(mc_scores) / len(mc_scores), 4),
            "low_score_count": sum(1 for s in mc_scores if s < 0.5),
        },
    }
