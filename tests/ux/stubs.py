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
    """Recommend the candidate's first active summary variant (deterministic,
    DB-only). Returns the REAL `{recommendation, alternates}` shape — the old
    placeholder (`{recommended_item_id}`) never set `has_recommendation`, so the
    positioning card's auto-fire re-fired on every reload (an infinite loop) once
    2+ candidate variants existed. Most flow tests seed none, so this is a no-op
    for them; it only matters when the positioning card actually renders."""
    from db.models import Candidate, SummaryItem
    from db.session import get_session

    session = get_session()
    try:
        cand = session.query(Candidate).filter_by(username=username).first()
        if cand is None:
            return {"recommendation": None, "alternates": []}
        first = (session.query(SummaryItem)
                 .filter_by(candidate_id=cand.id, is_active=1)
                 .order_by(SummaryItem.display_order, SummaryItem.id).first())
        if first is None:
            return {"recommendation": None, "alternates": []}
        return {
            "recommendation": {"summary_item_id": first.id,
                               "rationale": "stubbed: first variant"},
            "alternates": [],
        }
    finally:
        session.close()


def fake_recommend_experience_summaries(client: Any, ctx: Any, username: str = "",
                                        run_id: str = "") -> dict[str, Any]:
    """B.4 — recommend the first active intro variant per role (deterministic,
    DB-only). Mirrors `recommend_experience_summaries`'s return shape so the
    Compose 'Add role intros' toggle defaults each role without a real Haiku
    call. Only fires when a role has 2+ variants (the frontend gate)."""
    from db.models import Candidate, Experience, ExperienceSummaryItem
    from db.session import get_session

    session = get_session()
    try:
        cand = session.query(Candidate).filter_by(username=username).first()
        if cand is None:
            return {"recommendations": []}
        recs: list[dict[str, Any]] = []
        for exp in session.query(Experience).filter_by(candidate_id=cand.id).all():
            rows = (session.query(ExperienceSummaryItem)
                    .filter_by(experience_id=exp.id, is_active=1)
                    .order_by(ExperienceSummaryItem.display_order,
                              ExperienceSummaryItem.id).all())
            if rows:
                recs.append({
                    "experience_id": exp.id,
                    "summary_item_id": rows[0].id,
                    "rationale": "stubbed: first variant",
                    "alternates": [],
                })
        return {"recommendations": recs}
    finally:
        session.close()


def fake_recommend_skills(client: Any, ctx: Any, username: str = "",
                          run_id: str = "") -> dict[str, Any]:
    """B.5 — recommend all the candidate's active+approved skills in display
    order (deterministic, DB-only). Returns the real
    {recommendation:{skill_ids, rationale}} shape so the Compose skills card's
    auto-fire stops re-firing (has_recommendation becomes true)."""
    from db.models import Candidate, Skill
    from db.session import get_session

    session = get_session()
    try:
        cand = session.query(Candidate).filter_by(username=username).first()
        if cand is None:
            return {"recommendation": {"skill_ids": [], "rationale": "stub: no candidate"}}
        ids = [
            s.id for s in session.query(Skill)
            .filter_by(candidate_id=cand.id, is_active=1, is_pending_review=0)
            .order_by(Skill.display_order, Skill.id).all()
        ]
        return {"recommendation": {"skill_ids": ids, "rationale": "stubbed: all active skills"}}
    finally:
        session.close()


def fake_suggest_skills(client: Any, ctx: Any, username: str = "",
                        run_id: str = "") -> dict[str, Any]:
    """B.5 — propose one grounded skill (deterministic, DB-only). Returns the
    real {proposals:[...]} shape; the route inserts it as a pending row."""
    return {"proposals": [
        {"name": "Stubbed Skill", "category": "domain",
         "evidence": {"experience_id": None, "bullet_id": None, "quote": "stub"},
         "rationale": "stubbed proposal"},
    ]}


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


# Canned résumé markdown for `fake_generate_streaming`. The generate route runs
# the REAL deterministic `generate_resume()` on this, so it must be well-formed
# in the shape the parser/`_write_docx` expect: `# Name` header (+ contact lines
# before the first `##`), `## Section`, `### Title` (with the company/date
# subtitle on the next line), and `-` bullets. This renders for both `.md` and
# `.docx` (the bundled persona template resolves via the real BASE_DIR).
CANNED_RESUME_MD = """# Alice Candidate
alice@example.com · 555-0100 · Seattle, WA

## Summary
Senior platform engineer who led a Kafka migration and owns an event-driven
logistics platform end-to-end.

## Experience

### Senior Backend Engineer
Acme Logistics · 2020 – 2024
- Led a Kafka migration that cut consumer lag by 40% across 12 services.
- Owned partition strategy and the event-driven platform end-to-end.

### Backend Engineer
Globex · 2017 – 2020
- Built Postgres-backed services handling 5k requests per second.
- Reduced p99 latency 30% by reworking the consumer pool.
"""


def fake_generate_streaming(client: Any, context_set: Any, analysis: Any,
                            refinement_notes: str = "", username: str = "",
                            run_id: str = "", with_cover_letter: bool = True,
                            ) -> Iterator[tuple[str, object]]:
    """Mirror `analyzer.generate_streaming`'s event protocol (`("chunk"|"retry"|
    "done", payload)`). The route forwards these as SSE and, on `done`, runs the
    real deterministic `generate_resume()` + persists the iteration context — so
    the wizard reaches a genuine post-generation state (`iteration>=1`, a new
    context path) that the iteration-interview flow needs."""
    yield ("chunk", "Drafting résumé…")
    done: dict[str, Any] = {"resume_content": CANNED_RESUME_MD}
    # Mirror generate()'s contract: callers always read cover_letter_content.
    done["cover_letter_content"] = CANNED_RESUME_MD if with_cover_letter else ""
    yield ("done", done)


def fake_clarify_iteration(client: Any, context_set: Any, analysis: Any,
                           current_resume_text: str = "",
                           current_cover_letter_text: str = "",
                           recent_edits_summary: str = "",
                           deterministic_signals: Any = None,
                           prior_clarifications: Any = None,
                           username: str = "", run_id: str = "",
                           ) -> dict[str, Any]:
    """Mirror `analyzer.clarify_iteration`'s return shape ({questions, reasoning})
    so the /api/iterate-clarify route runs for real (re-keys ids, appends to the
    context) while staying deterministic + offline. The route renames the ids to
    `iterN_qM`, so the ids here are placeholders; the renderer reads
    id/text/kind/target_gap."""
    return {
        "questions": [
            {"id": "p1", "kind": "iteration_probe",
             "text": "Which Kafka metrics improved after the migration?",
             "target_gap": "Quantify the platform impact in the current draft"},
            {"id": "p2", "kind": "scope_probe",
             "text": "How many engineers did you coordinate on the cutover?",
             "target_gap": "Leadership scope still ambiguous after iteration 1"},
        ],
        "reasoning": "Two iteration probes targeting the draft's weakest claims.",
    }


def install_llm_stubs(ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every analyzer entry point the wizard can hit deterministic +
    offline. Apply before navigating."""
    import analyzer

    monkeypatch.setattr(ux_app, "analyze_streaming", fake_analyze_streaming)
    monkeypatch.setattr(ux_app, "_get_client", lambda: None)
    monkeypatch.setattr(analyzer, "recommend_bullets", fake_recommend_bullets)
    monkeypatch.setattr(analyzer, "recommend_summaries", fake_recommend_summaries)
    monkeypatch.setattr(analyzer, "recommend_experience_summaries",
                        fake_recommend_experience_summaries)
    # B.5 — skill matcher + grounded generator (imported locally in their
    # routes → patch on the analyzer module, like recommend_bullets).
    monkeypatch.setattr(analyzer, "recommend_skills", fake_recommend_skills)
    monkeypatch.setattr(analyzer, "suggest_skills", fake_suggest_skills)
    # `clarify` is a top-level import in app.py (called bare at app.py:790) →
    # patch on the app module, like analyze_streaming.
    monkeypatch.setattr(ux_app, "clarify", fake_clarify)
    # `generate_streaming` + `clarify_iteration` are also top-level imports in
    # app.py → patch on the app module. Additive: existing flow tests never reach
    # generate/iterate-clarify, so stubbing these is a no-op for them and unlocks
    # the full analyze→generate→iteration-interview drive for the polish test.
    monkeypatch.setattr(ux_app, "generate_streaming", fake_generate_streaming)
    monkeypatch.setattr(ux_app, "clarify_iteration", fake_clarify_iteration)
