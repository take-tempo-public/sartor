"""Demo-mode canned analyzer payloads (F-19 — offline demo mode).

`SARTOR_DEMO=1` lets a technical evaluator walk the tailoring pipeline
without a billed Anthropic key. This module holds the deterministic,
fixture-derived stand-ins `analyzer.py` returns for each LLM call kind
instead of calling Anthropic — the "demo shim" the call-kind functions
delegate to when `is_demo_mode()` is true.

**LLM-free by construction** — like `hardening.py` / `parser.py` /
`generator.py`, this module never imports `anthropic` and never makes a
network call (P1 Hardening boundary, charter C-6). It is NOT one of the
listed deterministic core modules, but holds itself to the same rule
because its whole job is to stand in for the LLM boundary honestly.

**Story source.** The canned analysis/clarify/résumé/cover-letter text is
adapted from `evals/fixtures/synthetic/sre-mid-level/` (jd.txt / resume.md /
expected.json) so a demo walkthrough — paste that JD, seed a corpus that
looks like Alex Chen's résumé — tells one coherent story end to end. Where a
call kind's real output must be a *selection over caller-supplied data*
(the `recommend_*` family), the demo shim selects deterministically from
whatever `context_set` the caller actually staged, rather than returning
fixture-fixed ids that would not exist in a real corpus.

**Honesty over completeness.** For call kinds that require genuine grounded
judgment the demo shim cannot fake without risking fabrication
(`suggest_skills`, `draft_gap_fill_bullets`, `draft_positioning_summary`,
`critique_proposal`, `promote_clarification_to_bullet`), the canned output is
a conservative, clearly-labeled no-op (empty proposals, the input echoed
back unchanged, or a note that says plainly no review was performed) —
never invented content standing in as if it were a real judgment.

Product code — never import this from `tests/`; the UX test stubs
(`tests/ux/stubs.py`) are a separate, intentionally different seam (DB-aware,
built for test speed) that predates this module and is not replaced by it.
"""

from __future__ import annotations

import os
from typing import Any

# --- Activation --------------------------------------------------------------


def is_demo_mode() -> bool:
    """True when `SARTOR_DEMO=1` is set — the single source of truth.

    Checked directly against the environment (not Flask config) so both
    `config.Config` (which surfaces it to `create_app`/templates as
    `DEMO_MODE`) and `analyzer.py` (which must also work outside a Flask
    request context — evals/runner.py, onboarding scripts, tests) read the
    exact same flag. Demo mode NEVER activates implicitly: a missing/blank
    API key alone leaves this False, so `web_infra._get_client()` and every
    analyzer call kind behave byte-identically to before this module existed
    unless the flag is explicitly set. A real key + `SARTOR_DEMO=1` still
    means demo — this flag is checked before any key lookup, so a demo run
    never spends.
    """
    return os.environ.get("SARTOR_DEMO") == "1"


# --- Story source: adapted from evals/fixtures/synthetic/sre-mid-level/ ------

DEMO_BANNER_TEXT = "Demo mode — canned AI responses, no API calls"

# Shaped to exactly what static/app.js's _renderAnalysis reads: string-array
# skills, {category,signal} hidden qualities, {strengths,gaps,title_alignment}
# comparison, {section,action,rationale} suggestions, {keyword,
# suggested_location,how} placement. Themed to the sre-mid-level fixture (JD:
# Lattice Cloud SRE; candidate: Alex Chen) so a demo walkthrough that pastes
# that JD sees an analysis that actually matches it.
CANNED_ANALYSIS: dict[str, Any] = {
    "essential_skills": ["Kubernetes", "Terraform", "Prometheus", "Grafana"],
    "preferred_skills": ["Istio", "Linkerd", "distributed tracing"],
    "industry_keywords": ["SRE", "SLO", "SLI", "incident response", "postmortem", "on-call"],
    "hidden_qualities": [
        {
            "category": "scope_of_ownership",
            "signal": "Owns reliability end-to-end for a control-plane-class system, not just a feature.",
        },
        {
            "category": "resilience",
            "signal": "Comfortable leading incident response and turning postmortems into completed action items.",
        },
    ],
    "professional_vocabulary": ["error budget", "MTTR", "runbook", "control plane"],
    "comparison": {
        "strengths": [
            "Direct Kubernetes + Terraform + Prometheus/Grafana experience.",
            "Has led postmortems for Sev-1 incidents and tracked action items to completion.",
        ],
        "gaps": [
            "No documented service-mesh (Istio/Linkerd) exposure.",
            "SLO/SLI ownership reads as ad-hoc rather than a formal, named framework.",
        ],
        "title_alignment": "strong",
    },
    "suggestions": [
        {
            "section": "Summary",
            "action": "Lead with control-plane reliability ownership and incident-response leadership.",
            "rationale": "The JD's first paragraph is about control-plane reliability and postmortem culture.",
        },
        {
            "section": "Experience",
            "action": "Name the SLO/SLI work explicitly wherever it appears, even informally.",
            "rationale": "The JD asks for defining and instrumenting SLOs — surface any adjacent evidence.",
        },
    ],
    "keyword_placement": [
        {
            "keyword": "Terraform",
            "suggested_location": "Experience — most recent role",
            "how": "name the modules authored and who adopted them",
        },
        {
            "keyword": "SLO",
            "suggested_location": "Summary",
            "how": "state the ownership explicitly, even if the framing was informal",
        },
    ],
    "overall_strategy": (
        "Demo mode: canned analysis (no API call was made). Position as a mid-level SRE "
        "who already owns control-plane-adjacent reliability work and can step directly "
        "into formal SLO ownership and postmortem-culture leadership."
    ),
}


def demo_analysis() -> dict[str, Any]:
    """Canned merged analyze() result — see `CANNED_ANALYSIS`."""
    return dict(CANNED_ANALYSIS)


# Clarify questions — adapted from expected.json's expected_clarification_themes
# (experience_probes / scope_probes) for the sre-mid-level fixture.
CANNED_CLARIFY_QUESTIONS: dict[str, Any] = {
    "questions": [
        {
            "id": "q1",
            "kind": "experience_probe",
            "text": "Have you used a service mesh (Istio, Linkerd) in production or a side project?",
            "target_gap": "Preferred skill 'service mesh' not evidenced in the résumé",
        },
        {
            "id": "q2",
            "kind": "experience_probe",
            "text": "Any distributed tracing beyond Prometheus/Grafana — OpenTelemetry, Jaeger, Honeycomb?",
            "target_gap": "JD asks for structured tracing beyond the existing Prometheus/Grafana stack",
        },
        {
            "id": "q3",
            "kind": "scope_probe",
            "text": "Was your Terraform standardization your own initiative, or an assigned rollout?",
            "target_gap": "Analyzer flagged ambiguous ownership scope on the Terraform-adoption claim",
        },
    ],
    "reasoning": (
        "Demo mode: canned clarify questions (no API call was made). Two experience "
        "probes on JD-preferred skills the résumé doesn't evidence, one scope probe "
        "disambiguating an ownership claim."
    ),
}


def demo_clarify() -> dict[str, Any]:
    """Canned clarify() result — see `CANNED_CLARIFY_QUESTIONS`."""
    return {
        "questions": [dict(q) for q in CANNED_CLARIFY_QUESTIONS["questions"]],
        "reasoning": CANNED_CLARIFY_QUESTIONS["reasoning"],
    }


# Iteration-round clarify — adapted from expected.json's iteration_scenarios.
CANNED_ITERATION_QUESTIONS: dict[str, Any] = {
    "questions": [
        {
            "id": "p1",
            "kind": "iteration_probe",
            "text": "For the SLOs you just described, were you the sole owner or a co-owner with the platform team?",
            "target_gap": "Follow-up on the just-typed SLO ownership claim — scope of ownership",
        },
        {
            "id": "p2",
            "kind": "iteration_probe",
            "text": "What was the review cadence for the SLO / error-budget numbers you mentioned?",
            "target_gap": "Follow-up on the just-typed SLO claim — review cadence unspecified",
        },
        {
            "id": "p3",
            "kind": "experience_probe",
            "text": "Have you worked on a multi-region control plane, or only a single-region API edge?",
            "target_gap": "JD emphasizes a multi-region control plane; current draft reads single-region",
        },
    ],
    "reasoning": (
        "Demo mode: canned iteration-clarify questions (no API call was made). "
        "Two iteration probes following up on the most recent edit, one experience "
        "probe on a still-uncovered JD requirement."
    ),
}


def demo_clarify_iteration() -> dict[str, Any]:
    """Canned clarify_iteration() result — see `CANNED_ITERATION_QUESTIONS`."""
    return {
        "questions": [dict(q) for q in CANNED_ITERATION_QUESTIONS["questions"]],
        "reasoning": CANNED_ITERATION_QUESTIONS["reasoning"],
    }


# Canned résumé markdown — adapted from evals/fixtures/synthetic/sre-mid-level/
# resume.md (Alex Chen), lightly re-angled toward the JD's control-plane framing
# so it reads as a plausible "tailored" output rather than a raw copy. Must be
# well-formed in the shape generator.py's parser expects (`# Name` header +
# contact line before the first `##`, `## Section`, `### Title` with a
# company/date subtitle line, `-` bullets) — it renders through the SAME
# deterministic `generate_resume()` a real generation would.
CANNED_RESUME_MD = """# Alex Chen
alex.chen@example.com | (555) 010-2200 | linkedin.com/in/example-alex

## Summary
Site Reliability Engineer with four years operating Kubernetes-based control planes in \
production. Owns incident response end to end and turns postmortems into completed \
corrective actions. Comfortable in Python and Go.

## Experience

### Site Reliability Engineer
Holden Networks · March 2023 – present
- Owned reliability of the API edge for a B2B SaaS serving roughly 800 customer tenants on AWS EKS.
- Tightened retry semantics in the ingress layer and shipped an on-call dashboard used every shift.
- Authored Terraform modules for VPC peering and IAM role provisioning adopted as the platform standard.
- Led postmortems for two Sev-1 incidents on a roughly one-week-in-four on-call rotation, tracking every action item to completion.
- Wrote a runbook library covering the top ten alert types, cutting MTTR for those alerts noticeably.

### Production Engineer
Stratford Analytics · August 2021 – March 2023
- Migrated the monitoring stack from a SaaS APM to self-hosted Prometheus + Grafana.
- Built a Slack bot in Python that posted incident timelines as they unfolded.
- Mentored two interns through their first on-call shadow rotations.

## Education

### B.S. Computer Science
State University · 2021

## Skills
Kubernetes, Prometheus, Grafana, Terraform, AWS (EKS, IAM, VPC, S3), Python, Go, Bash, \
Kafka, Envoy, distributed tracing, incident response, runbooks, on-call leadership.
"""

CANNED_COVER_LETTER = """Demo mode: canned cover letter (no API call was made).

Dear Hiring Team,

I'm writing to apply for the Senior Site Reliability Engineer role. Over the past four \
years I've owned reliability for a Kubernetes-based control plane end to end — from \
authoring the Terraform modules that became my team's IaC standard to leading postmortems \
for Sev-1 incidents and tracking every action item to completion.

I'd welcome the chance to bring that same ownership to your control plane, and to grow \
into the formal SLO practice your team is building.

Alex Chen"""


def demo_generate(with_cover_letter: bool = True) -> dict[str, Any]:
    """Canned generate()/generate_streaming() result — see `CANNED_RESUME_MD`."""
    return {
        "resume_content": CANNED_RESUME_MD,
        "cover_letter_content": CANNED_COVER_LETTER if with_cover_letter else "",
        "changes_made": ["Demo mode: canned generation — no real tailoring was performed."],
        "proofread_notes": [],
    }


def demo_cover_letter() -> dict[str, Any]:
    """Canned generate_cover_letter_against_resume() result."""
    return {"cover_letter_content": CANNED_COVER_LETTER, "proofread_notes": []}


# --- Conservative no-op shims for calls needing genuine grounded judgment ----


def demo_refinement_scope() -> dict[str, Any]:
    """Canned check_refinement_scope() result — fails open, same as a real outage."""
    return {"valid": True}


def demo_critique_proposal() -> dict[str, Any]:
    """Canned critique_proposal() result — explicitly flags that no real review ran.

    Deliberately NOT "good": a demo verdict must never read as if a real
    fabrication review happened.
    """
    return {
        "verdict": "caution",
        "notes": "Demo mode: no fabrication review was performed by a real model.",
        "concerns": ["Demo mode: critique not performed — review this proposal yourself."],
        "suggested_revisions": [],
    }


def demo_suggest_skills() -> dict[str, Any]:
    """Canned suggest_skills() result — empty. Proposing a skill without a real, corpus-grounded review risks fabrication, so demo mode proposes nothing."""
    return {"proposals": []}


def demo_draft_gap_fill_bullets() -> dict[str, Any]:
    """Canned draft_gap_fill_bullets() result — empty, for the same grounding reason as `demo_suggest_skills`."""
    return {"proposals": []}


def demo_promote_clarification_to_bullet(answer: str) -> dict[str, Any]:
    """Canned promote_clarification_to_bullet() result — echoes the candidate's own answer verbatim (zero fabrication risk) rather than rewriting it."""
    text = (answer or "").strip() or "Demo mode: no clarification answer was provided."
    return {
        "text": text,
        "pattern_kind": "manual",
        "rationale": "Demo mode: the clarification answer was carried over verbatim, not rewritten.",
    }


def demo_positioning_summary(source_text: str) -> dict[str, Any]:
    """Canned draft_positioning_summary() result — returns the candidate's existing positioning unchanged (mirrors the real function's own no-JD short-circuit, so nothing is invented)."""
    return {"summary": source_text}


# --- Selection shims: pick deterministically from the caller's OWN staged data,
# never from fixture-fixed ids that would not exist in a real corpus. `object`
# parameter types (narrowed internally via isinstance, mirroring the analyzer.py
# call sites' own "transient key, coerce defensively" idiom for these same
# context_set values — see e.g. recommend_summaries's `items_raw`) sidestep list
# invariance against the strongly-typed `list[CorpusExperience]` career_corpus
# without weakening the caller's own typing.


def _as_dict_list(value: object) -> list[dict[str, Any]]:
    """Best-effort coerce a `context_set`-staged value to a list of dicts."""
    if not isinstance(value, list):
        return []
    return [it for it in value if isinstance(it, dict)]


def demo_recommend_bullets(career_corpus: object) -> dict[str, Any]:
    """Canned recommend_bullets() result — every experience's active bullets, up to 6, in existing order (mirrors the real prompt's "be generous" instruction without an LLM call)."""
    recommendations: list[dict[str, Any]] = []
    for exp in _as_dict_list(career_corpus):
        bullet_ids = []
        for b in exp.get("bullets") or []:
            if not isinstance(b, dict):
                continue
            bid = b.get("id")
            if bid is not None:
                bullet_ids.append(int(bid))
        if not bullet_ids:
            continue
        recommendations.append(
            {
                "experience_id": int(exp.get("id", 0)),
                "bullet_ids": bullet_ids[:6],
                "rationale": "Demo mode: recommending all available bullets for this role.",
            }
        )
    return {"recommendations": recommendations}


def demo_recommend_summaries(summary_items: object) -> dict[str, Any]:
    """Canned recommend_summaries() result — the first staged variant, no LLM call."""
    items = [it for it in _as_dict_list(summary_items) if (it.get("text") or "").strip()]
    if not items:
        return {"recommendation": None, "alternates": []}
    return {
        "recommendation": {
            "summary_item_id": int(items[0].get("id", 0)),
            "rationale": "Demo mode: first available positioning variant.",
        },
        "alternates": [],
    }


def demo_recommend_experience_summaries(experience_summary_items: object) -> dict[str, Any]:
    """Canned recommend_experience_summaries() result — first variant per role, no LLM call."""
    recommendations: list[dict[str, Any]] = []
    for group in _as_dict_list(experience_summary_items):
        items = [it for it in _as_dict_list(group.get("items")) if (it.get("text") or "").strip()]
        if not items:
            continue
        recommendations.append(
            {
                "experience_id": int(group.get("experience_id", 0)),
                "summary_item_id": int(items[0].get("id", 0)),
                "rationale": "Demo mode: first available intro variant.",
                "alternates": [],
            }
        )
    return {"recommendations": recommendations}


def demo_recommend_skills(skill_items: object) -> dict[str, Any]:
    """Canned recommend_skills() result — every staged skill, in existing order, no LLM call."""
    items = [it for it in _as_dict_list(skill_items) if (it.get("name") or "").strip()]
    ids = [int(it.get("id", 0)) for it in items]
    return {
        "recommendation": {
            "skill_ids": ids,
            "rationale": "Demo mode: all available skills, unranked.",
        }
    }


# --- Avatar (doc-grounded assistant) — a separate LLM subsystem (7.5) --------

DEMO_AVATAR_ANSWER = (
    "Demo mode: this is a canned answer — no API call was made and no retrieval "
    "grounding was applied. Turn off SARTOR_DEMO and ask again for a real, "
    "cited answer from the docs."
)


def demo_avatar_answer() -> dict[str, Any]:
    """Canned avatar_answer_streaming() `done` payload — no citations (nothing was actually retrieved-and-cited)."""
    return {
        "answer": DEMO_AVATAR_ANSWER,
        "citations": [],
        "truncated": False,
        "allow_dev": False,
    }
