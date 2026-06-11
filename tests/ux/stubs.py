"""LLM stubs for the UX flow tests — canned analyzer responses so the wizard
is deterministic, free, and offline.

We stub the **public** streaming/selection functions (above the parser), so
the real Flask routes still run — SSE framing, context-file writes, and DB
rows are all genuine (decided 2026-06-04: the public-streaming-fn seam, not
the lower `_call_llm` seam, which would couple these fixtures to each call
kind's raw output schema).

Binding styles (confirmed by reading `app.py`):
- `analyze_streaming` is a top-level import in `app` → patch on the **app
  module** (`ux_app`).
- `recommend_bullets` / `recommend_summaries` are imported **locally inside
  the route** at call time → patch on the **`analyzer` module**.
- `_get_client` is patched to a dummy so the suite needs no API key and makes
  no network call (the stubs ignore the client object entirely).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType
from typing import Any

import pytest

# Shaped to exactly what `_renderAnalysis` (static/app.js) reads, so the
# Step-1 render never throws: string-array skills, {category,signal} hidden
# qualities, {strengths,gaps,title_alignment} comparison, {section,action,
# rationale} suggestions, {keyword,suggested_location,how} placement.
CANNED_ANALYSIS: dict[str, Any] = {
    "essential_skills": ["Python", "Kafka", "Postgres"],
    "preferred_skills": ["Kubernetes"],
    "industry_keywords": ["logistics", "event-driven"],
    "hidden_qualities": [
        {"category": "scope_of_ownership", "signal": "owns the platform end-to-end"},
    ],
    "professional_vocabulary": ["partition strategy", "consumer lag"],
    "comparison": {
        "strengths": ["Kafka migration experience"],
        "gaps": ["No explicit team-size leadership claim"],
        "title_alignment": "strong",
    },
    "suggestions": [
        {"section": "Summary", "action": "Lead with Kafka platform ownership",
         "rationale": "JD weights Kafka as non-negotiable"},
    ],
    "keyword_placement": [
        {"keyword": "Kafka", "suggested_location": "Summary",
         "how": "name the topic / partition scale"},
    ],
    "overall_strategy": "Position as a senior platform IC who has led a Kafka migration.",
}


def fake_analyze_streaming(client: Any, context_set: Any, username: str = "",
                           run_id: str = "") -> Iterator[tuple[str, object]]:
    """Mirror `analyzer.analyze_streaming`'s tuple protocol (the route
    serializes these into SSE — we never touch wire framing)."""
    yield ("phase", {"phase": "extraction"})
    yield ("phase", {"phase": "synthesis"})
    yield ("done", dict(CANNED_ANALYSIS))


def fake_recommend_bullets(client: Any, ctx: Any, username: str = "",
                           run_id: str = "") -> dict[str, Any]:
    """Recommend every active bullet (the common path: recommendations exist,
    so Compose renders them in the GET's saved order rather than the
    no-recommendations score-sorted fallback). Deterministic + DB-only.

    The stub queries the DB by `username` (which the route passes through) —
    it never knows bullet ids at definition time, and this keeps the flow
    representative of real usage where recommend_bullets has run."""
    from db.models import Bullet, Candidate, Experience
    from db.session import get_session

    session = get_session()
    try:
        cand = session.query(Candidate).filter_by(username=username).first()
        if cand is None:
            return {"recommendations": []}
        recs: list[dict[str, Any]] = []
        for exp in session.query(Experience).filter_by(candidate_id=cand.id).all():
            bullet_ids = [
                b.id for b in session.query(Bullet)
                .filter_by(experience_id=exp.id, is_active=1)
                .order_by(Bullet.display_order).all()
            ]
            if bullet_ids:
                recs.append({
                    "experience_id": exp.id, "bullet_ids": bullet_ids,
                    "rationale": "stubbed: all active bullets",
                })
        return {"recommendations": recs}
    finally:
        session.close()


def fake_recommend_summaries(client: Any, ctx: Any, username: str = "",
                             run_id: str = "") -> dict[str, Any]:
    """Only invoked when 2+ summary variants exist; the flow tests seed none,
    so this is purely defensive against an unexpected real call."""
    return {"recommended_item_id": None, "rationale": ""}


def fake_clarify(client: Any, context_set: Any, analysis: Any,
                 username: str = "", run_id: str = "") -> dict[str, Any]:
    """Mirror `analyzer.clarify`'s return shape ({questions, reasoning}) so the
    /api/clarify route runs for real (persists questions onto the context) while
    staying deterministic + offline. Two questions, each with the id/text/kind/
    target_gap keys `_renderClarifyQuestions` (static/app.js) reads."""
    return {
        "questions": [
            {"id": "q1", "kind": "experience_probe",
             "text": "Have you run Kubernetes in production?",
             "target_gap": "Essential skill not evidenced in the resume"},
            {"id": "q2", "kind": "scope_probe",
             "text": "How large was the team you led on the Kafka migration?",
             "target_gap": "Leadership scope flagged as ambiguous"},
        ],
        "reasoning": "Two probes: one missing essential skill, one scope ambiguity.",
    }


def install_llm_stubs(ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every analyzer entry point the wizard can hit deterministic +
    offline. Apply before navigating."""
    import analyzer

    monkeypatch.setattr(ux_app, "analyze_streaming", fake_analyze_streaming)
    monkeypatch.setattr(ux_app, "_get_client", lambda: None)
    monkeypatch.setattr(analyzer, "recommend_bullets", fake_recommend_bullets)
    monkeypatch.setattr(analyzer, "recommend_summaries", fake_recommend_summaries)
    # `clarify` is a top-level import in app.py (called bare at app.py:790) →
    # patch on the app module, like analyze_streaming.
    monkeypatch.setattr(ux_app, "clarify", fake_clarify)
