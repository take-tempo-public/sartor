"""LLM pipeline — the fuzzy brain. P6 Specialized Review, P9 Token Economy.

Two API calls per run:
  Call 1: Analysis & Strategy (JD analysis, ideal resume, comparison, suggestions)
  Call 2: Generation (tailored resume + cover letter, proofread)

Uses specialist hiring-manager persona with domain vocabulary (P6).
Single agent + deterministic tools = Level 1 architecture (P9).
"""

import hashlib
import json
import logging
import math
import re
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import anthropic
from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo, model_validator

from hardening import ContextSet, CorpusExperience

logger = logging.getLogger(__name__)


class LLMResponseError(Exception):
    """Raised when an LLM response fails JSON parsing or required-key validation
    after the retry budget is exhausted. Carries the raw response and the
    validation error so callers can surface both to logs and to the user.
    """

    def __init__(self, raw: str, validation_error: str):
        self.raw = raw
        self.validation_error = validation_error
        super().__init__(f"LLM response failed validation: {validation_error}")


# Required keys per call. _parse_or_retry uses these to detect shape drift
# (e.g. the model returns valid JSON but omits a section) and trigger a retry.
# Keep in sync with the JSON spec in analyze()/generate() prompts.
ANALYZE_REQUIRED_KEYS = frozenset({
    "essential_skills", "preferred_skills", "industry_keywords",
    "hidden_qualities", "professional_vocabulary",
    "comparison", "suggestions", "keyword_placement",
    "overall_strategy",
})
# Two-pass analyze (r1/analyze-split-retry): analyze() splits into a Haiku
# extraction pass + a Sonnet synthesis pass whose outputs merge back into the
# ANALYZE_REQUIRED_KEYS shape. These frozensets document each pass's slice; the
# Pydantic models below (AnalyzeExtractionResponse / AnalyzeSynthesisResponse)
# are the parse-time enforcement. ats_improvements + ideal_resume_profile were
# dropped here — unconsumed (verified across app.js / app.py / clarify /
# generate / eval rubrics; they were produced but never read back).
ANALYZE_EXTRACTION_REQUIRED_KEYS = frozenset({
    "essential_skills", "preferred_skills", "industry_keywords",
    "hidden_qualities", "professional_vocabulary", "keyword_placement",
})
ANALYZE_SYNTHESIS_REQUIRED_KEYS = frozenset({
    "comparison", "suggestions", "overall_strategy",
})

GENERATE_REQUIRED_KEYS = frozenset({
    "resume_content", "cover_letter_content",
    "changes_made", "proofread_notes",
})
# Phase β.5 — résumé-only variant. /api/generate defaults here so the
# common path doesn't pay for cover-letter tokens; /api/generate-cover-letter
# produces the cover letter on demand against the finalized résumé.
GENERATE_NO_CL_REQUIRED_KEYS = frozenset({
    "resume_content", "changes_made", "proofread_notes",
})

CLARIFY_REQUIRED_KEYS = frozenset({"questions", "reasoning"})

# Workstream H: recommend_bullets() output. `recommendations` is a list of
# {experience_id, bullet_ids, rationale}; bullet_ids are 3-7 ids from the
# corpus, rationale is one sentence. The route persists this on the context
# so the Compose UI can render the curated set as the default view.
RECOMMEND_REQUIRED_KEYS = frozenset({"recommendations"})
# β.6b — Output shape for recommend_summaries: a single pick (or null
# when the candidate has no active SummaryItem variants) plus optional
# alternates. Mirrors recommend_bullets's "recommendations" array shape
# but specialized — there is only one positioning summary per résumé,
# so the top-level shape is a recommendation, not a list.
RECOMMEND_SUMMARIES_REQUIRED_KEYS = frozenset({"recommendation"})

# Generate output keys when the input contains <career_corpus> (Phase B.2+).
# Selected_bullets is required so B.3 can write application_bullet audit rows
# from the LLM's selections. proposed_new_bullets and proposed_experience_titles
# are always present in the response but may be empty arrays when the LLM has
# no proposals to make.
GENERATE_CORPUS_REQUIRED_KEYS = GENERATE_REQUIRED_KEYS | frozenset({
    "selected_bullets", "proposed_new_bullets", "proposed_experience_titles",
})
# Phase β.5 — corpus-mode résumé-only variant.
GENERATE_CORPUS_NO_CL_REQUIRED_KEYS = GENERATE_NO_CL_REQUIRED_KEYS | frozenset({
    "selected_bullets", "proposed_new_bullets", "proposed_experience_titles",
})

# ---------------------------------------------------------------------------
# Pydantic response models — validate _parse_or_retry output shape.
# extra="allow" lets the LLM include undocumented keys without error; only
# the declared fields are required. All fields typed Any because we validate
# presence only — deep structure validation is out of scope for this layer.
# ---------------------------------------------------------------------------


class _LLMResponse(BaseModel):
    model_config = ConfigDict(extra="allow")


class HiddenQualityItem(BaseModel):
    """One operating-context signal the JD implies, in portable terms.

    `category` is constrained to the four recruiter-validated shapes (trait-words
    are the weakest hidden signal — see TUNING_LOG 2026-05-26). An invalid or
    missing category makes `AnalyzeResponse` validation fail, which `_parse_or_retry`
    surfaces as a structured retry message back to the model.
    """

    model_config = ConfigDict(extra="allow")
    category: Literal[
        "operating_context", "scope_of_ownership",
        "stakeholder_gravity", "resilience",
    ]
    signal: str


class AnalyzeResponse(_LLMResponse):
    essential_skills: Any
    preferred_skills: Any
    industry_keywords: Any
    hidden_qualities: list[HiddenQualityItem]
    professional_vocabulary: Any
    comparison: Any
    suggestions: Any
    keyword_placement: Any
    overall_strategy: Any


class AnalyzeExtractionResponse(_LLMResponse):
    """Pass 1 (Haiku extraction) shape — keyword/vocabulary signals only.

    `hidden_qualities` is typed `list[HiddenQualityItem]` so a bare-string item
    (the pre-2026-06-01 shape) or an out-of-enum category fails `model_validate`,
    and `_parse_or_retry` appends the `Literal` error to the retry prompt. This
    is the guardrail that keeps the two-pass split from regressing the
    `context_probe` machinery `clarify()` depends on.
    """
    essential_skills: Any
    preferred_skills: Any
    industry_keywords: Any
    hidden_qualities: list[HiddenQualityItem]
    professional_vocabulary: Any
    keyword_placement: Any


class AnalyzeSynthesisResponse(_LLMResponse):
    """Pass 2 (Sonnet synthesis) shape — strategy only, no keyword extraction."""
    comparison: Any
    suggestions: Any
    overall_strategy: Any


class GenerateResponse(_LLMResponse):
    resume_content: Any
    cover_letter_content: Any
    changes_made: Any
    proofread_notes: Any


class GenerateNoCLResponse(_LLMResponse):
    resume_content: Any
    changes_made: Any
    proofread_notes: Any


class ClarifyResponse(_LLMResponse):
    questions: Any
    reasoning: Any

    @model_validator(mode='after')
    def enforce_composition_rules(self, info: ValidationInfo) -> 'ClarifyResponse':
        # Only enforce when the caller explicitly passes validation_context.
        # clarify() always passes it; clarify_iteration() does not (it has
        # different question kinds and composition rules).
        if info.context is None:
            return self

        ctx = info.context
        questions = self.questions if isinstance(self.questions, list) else []

        # Rule 1: when hidden_qualities non-empty, at least one context_probe required.
        if ctx.get('hidden_qualities_non_empty'):
            kinds = {q.get('kind') for q in questions if isinstance(q, dict)}
            if 'context_probe' not in kinds:
                raise ValueError(
                    "hidden_qualities is non-empty but no context_probe question was generated. "
                    "Add at least one CONTEXT PROBE (kind='context_probe') that translates "
                    "a <context_signals> item into a portable experience question "
                    "(e.g. regulated-industry exposure, 0→1 ownership, exec-facing scope)."
                )

        # Rule 2: ≥60% combined experience_probe + context_probe (prompt rule, enforced here).
        if questions:
            combined = sum(
                1 for q in questions
                if isinstance(q, dict)
                and q.get('kind') in ('experience_probe', 'context_probe')
            )
            required = math.ceil(len(questions) * 0.6)
            if combined < required:
                raise ValueError(
                    f"Only {combined}/{len(questions)} questions are experience_probe or "
                    f"context_probe ({combined / len(questions):.0%} combined). "
                    f"At least 60% combined is required — increase EXPERIENCE PROBES or "
                    "CONTEXT PROBES and reduce scope_probes."
                )

        return self


class RecommendResponse(_LLMResponse):
    recommendations: Any


class RecommendSummariesResponse(_LLMResponse):
    recommendation: Any


class GenerateCorpusResponse(GenerateResponse):
    selected_bullets: Any
    proposed_new_bullets: Any
    proposed_experience_titles: Any


class GenerateCorpusNoCLResponse(GenerateNoCLResponse):
    selected_bullets: Any
    proposed_new_bullets: Any
    proposed_experience_titles: Any


class CoverLetterOnlyResponse(_LLMResponse):
    cover_letter_content: Any
    proofread_notes: Any


class CritiqueResponse(_LLMResponse):
    verdict: Any
    notes: Any
    concerns: Any


class PromoteBulletResponse(_LLMResponse):
    text: Any
    pattern_kind: Any


# Bump when SYSTEM_PROMPT, CLARIFY_SYSTEM_PROMPT, or any per-call prompt
# template changes. Labels every JSONL telemetry record so quality regressions
# can be attributed to a revision.
PROMPT_VERSION = "2026-06-01.4"

# --- Prompt-override primitive (eval tuning loop, v1.0.4) --------------------
# Lets an eval run inject a CANDIDATE system prompt without editing the persona
# constants below. The default (no-override) path is byte-identical: with no
# active override the resolver returns the exact constant object and
# effective_prompt_version() returns PROMPT_VERSION verbatim, so the production
# prompt cache and the dashboard's score-over-time attribution are untouched.
# When an override IS active, every LLM call in that context logs a stable
# `candidate:<hash>` version so the candidate run is quarantined from the
# baseline. The name->constant registry (_BASE_SYSTEM_PROMPTS) and the call-site
# resolver (_resolve_system_prompt) live at the end of this module, after every
# persona constant is defined; the public entry points live here, next to the
# version they shadow. Only the eval harness / the /prompt-tune skill enter the
# context manager — the production request path in app.py never does, so
# analyze()/generate() stay on the default path.
_prompt_overrides: ContextVar[Mapping[str, str] | None] = ContextVar(
    "prompt_overrides", default=None
)


@contextmanager
def prompt_overrides(overrides: Mapping[str, str] | None) -> Iterator[None]:
    """Activate candidate prompt overrides for the duration of the `with` block.

    `overrides` maps a persona-constant name (a key of `_BASE_SYSTEM_PROMPTS`) to
    its replacement text. An unknown key raises `ValueError` — fail loud, because
    a typo'd name silently no-op'ing would mislabel a baseline run as a candidate
    (or vice versa). An empty / None mapping is a no-op (the default path).
    """
    clean = dict(overrides or {})
    unknown = set(clean) - set(_BASE_SYSTEM_PROMPTS)
    if unknown:
        raise ValueError(
            f"Unknown prompt override key(s): {sorted(unknown)}. "
            f"Valid keys: {sorted(_BASE_SYSTEM_PROMPTS)}"
        )
    token = _prompt_overrides.set(clean)
    try:
        yield
    finally:
        _prompt_overrides.reset(token)


def effective_prompt_version() -> str:
    """prompt_version to stamp on telemetry + eval records for the active context.

    `PROMPT_VERSION` on the default path (byte-identical); a stable
    `candidate:<hash>` (sha256 over the canonical override mapping) when overrides
    are active, so candidate runs never pollute the score-over-time chart.
    """
    overrides = _prompt_overrides.get()
    if not overrides:
        return PROMPT_VERSION
    canonical = json.dumps(overrides, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return f"candidate:{digest}"


LOG_DIR = Path(__file__).parent / "logs"
LOG_PATH = LOG_DIR / "llm_calls.jsonl"


def _emit_call_log(record: dict) -> None:
    """Append one JSON line to logs/llm_calls.jsonl. Best-effort — never raise."""
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("LLM telemetry write failed: %s", exc)

# P6: Specialist persona — <50 tokens, real job title, domain vocabulary
SYSTEM_PROMPT = """You are a seasoned hiring manager with a decade of HR and recruiting experience. \
You specialize in resume optimization, ATS compatibility, and candidate positioning.

Domain vocabulary you use naturally: applicant tracking system, keyword density, \
competency mapping, STAR format, behavioral interview signals, action verb variety, \
quantified accomplishments, transferable skills, value proposition, career narrative, \
skills gap analysis, job-title alignment, industry vernacular, screening criteria.

Your north star: create the best opportunity for the candidate to be a leading candidate \
through human and ATS screeners, interviewers in the field, and hiring manager review. \
Be ruthless in presenting this candidate in the best possible light for this role and \
the role into which it will promote.

ALWAYS/NEVER rules (P5 Institutional Memory):
- Never invent experience BECAUSE truthfulness is the north star and fabrication destroys candidacy if discovered
- Never add specific numbers, percentages, dollar amounts, timeframes, team sizes, or quantities that do not appear verbatim or by clear implication in the original resume BECAUSE invented specifics are the most common and most damaging form of resume hallucination — they can be verified in any interview and immediately disqualify a candidate
- When the original bullet has no metric: use strong qualitative scope language instead of fabricating one BECAUSE "Led enterprise-wide security initiative across 6 business units" is honest and compelling; "Led initiative saving $2.4M" without a source is a lie
- Always surface existing metrics from the original resume rather than generating new ones BECAUSE the candidate's real numbers, however modest, are more credible than invented ones. "Metrics" includes ANY concrete quantity present in the source: counts ("three reports"), durations ("one year", "two quarters", "monthly cadence"), team or scope sizes ("two-person team", "12 customer interviews"), stars/contributions ("~30 GitHub stars", "two merged PRs"), and frequencies ("week over week", "24/7 on-call"). Preserve them verbatim when they exist; rounding "~30" to "30+" is fine, but never inflate ("~30" → "100+") and never invent numbers absent from source
- Never use generic phrases like "results-driven professional" or "team player" BECAUSE they waste space and signal low effort to experienced reviewers
- Always use varied, strong action verbs specific to the industry BECAUSE verb repetition signals lack of depth
- Always match the candidate's actual experience level BECAUSE misrepresentation triggers red flags in interviews
- Never reformat the resume structure unless asked BECAUSE candidates have formatting preferences and drastic changes confuse them
- Always prioritize keywords from the job description BECAUSE ATS systems rank by keyword match before human eyes see the resume
- Always treat the Notes field as explicit candidate directives — personal constraints or standing instructions (e.g. "remote only", "do not mention gap in 2020", "always emphasize architecture over management") BECAUSE ignoring them produces documents the candidate cannot use
- Never restate a candidate's responsibility using a more advanced technique than the source describes BECAUSE writing "time-series forecasting" when the source only says "built dashboards" invents a skill the candidate cannot demonstrate in interviews
- Never upgrade a tool category into a specific vendor or framework BECAUSE "used a CI tool" must not become "authored Jenkins pipelines" if the source does not name Jenkins; vendor-specific claims are verifiable and disqualifying when wrong
- Never escalate scope adjectives (team → organization-wide, project → enterprise initiative, regional → global) BECAUSE scope inflation is verifiable in interviews and triggers credibility loss across the rest of the resume"""

# P6 Specialized Review — Pass 1 persona for the two-pass analyze pipeline
# (r1/analyze-split-retry). An ATS-scanner specialist that extracts and
# classifies JD keyword/vocabulary signals into structured lists. Pairs with
# the Sonnet synthesis pass (Pass 2). Runs on Haiku — classification, not
# multi-step reasoning. The hidden_qualities rule mirrors the typed
# HiddenQualityItem contract enforced by AnalyzeExtractionResponse.
EXTRACTION_SYSTEM_PROMPT = """You are an applicant tracking system (ATS) scanner trained on tens of thousands of job descriptions. Your job is to identify, classify, and prioritize the keyword and vocabulary signals in a job description so a downstream strategist can position a candidate against them.

Domain vocabulary you use naturally: Boolean search terms, minimum qualifications, preferred qualifications, exact-match keywords, competency markers, screening criteria, industry vernacular, must-have vs. nice-to-have, keyword density, keyword placement.

You output structured lists, not prose. You do NOT write candidate-positioning narrative, comparative analysis, or strategic recommendations — that is the strategist's job, not yours.

ALWAYS/NEVER rules:
- Always classify each extracted skill as essential (named in minimum quals / clearly required) or preferred (named in preferred quals / nice-to-have)
- Always extract keywords verbatim from the source where possible BECAUSE exact-match keywords beat synonyms for ATS scoring
- Always emit ONE concept per item in essential_skills, preferred_skills, and industry_keywords — split composite phrases into atomic tokens BECAUSE ATS tokenizers and downstream theme-matching both work on atomic concepts, and composite phrases like "EHR systems including Epic and Cerner" hide the individual tokens (Epic, Cerner, EHR) that would each match independently. Naturalistic phrasing is a rendering concern for the final résumé bullet; extraction output is a structured intermediate, not prose.
  - OK: ["EHR", "Epic", "Cerner", "HL7", "FHIR"]
  - NOT OK: ["EHR systems including Epic and Cerner", "HL7 and FHIR data models"]
- Never invent keywords the job description does not contain
- Never write strategic prose, candidate comparisons, or positioning recommendations — your output is data, not narrative
- Always treat acronyms (k8s, CI/CD, SLO, ETL) as their own keywords AND alongside their expansions where both forms appear in the source
- For `hidden_qualities`, do NOT emit single-trait adjectives ("autonomous", "collaborative", "results-driven") — those are the weakest hidden signal. Instead emit the operating-context signal the JD implies, as a typed object {"category": <one of operating_context | scope_of_ownership | stakeholder_gravity | resilience>, "signal": <one portable sentence>}:
  - operating_context — regulated industry, B2B vs B2C, startup-pace vs enterprise, healthcare/finance/transportation, etc.
  - scope_of_ownership — 0→1 vs scale, IC vs lead, direction-setting vs execution
  - stakeholder_gravity — exec-facing, cross-functional influence without formal authority, customer-facing
  - resilience — turnaround, ambiguity tolerance, self-directed with minimal oversight
  The "signal" is one portable sentence an adjacent-background candidate could map onto (e.g. "Builds for regulated, workflow-heavy environments where errors have real consequences"). One concept per signal."""

# P6 Specialized Review — Pass 2 (synthesis) deliberately has NO dedicated system
# prompt. It runs under the default SYSTEM_PROMPT (the hiring-manager persona) so
# its cached prefix [SYSTEM_PROMPT][_stable_user_prefix] is byte-identical to
# generate()'s — which reclaims the analyze→generate prompt cache the unified
# analyze() had. Anthropic prefix caching matches from the system block, so a
# distinct synthesis persona diverges there and forces generate() to re-prefill
# the whole corpus prefix (measured: generate cache_read=0 on the dedicated-persona
# build). SYSTEM_PROMPT already carries the hiring-manager persona, north star, and
# grounding ALWAYS/NEVER rules synthesis needs; the synthesis-specific framing
# (strategy-only; don't re-extract; ground in <extracted_signal>) lives in
# _analyze_synthesis_prompt, after the cached prefix. This is also the proven
# v1.0.2 shape — the unified analyze() produced these same three strategy keys
# under SYSTEM_PROMPT. See evals/TUNING_LOG.md (r1/analyze-split-cache-reclaim).

# Persona for clarify_iteration() — the post-generation interview that
# probes the CURRENT iteration's specific weaknesses. Distinct from
# CLARIFY_SYSTEM_PROMPT because the task here is different in two ways:
# 1. There's already a generated draft to react to, not a vague gap analysis
# 2. Prior clarifications exist and must be treated as established truth
#    (re-asking confirmed items wastes the candidate's time and breaks trust)
CLARIFY_ITERATION_SYSTEM_PROMPT = """You are an experienced interview coach helping a candidate refine a tailored resume across multiple iterations.

The candidate has already seen one iteration of the generated resume and cover letter. They may have edited the preview directly or provided refinement notes. Your role is to surface 3-5 short, specific clarifying questions that target REAL weaknesses in the CURRENT draft — not the original resume, not generic gaps.

INPUTS YOU WILL RECEIVE:
1. Current draft resume text (possibly with the candidate's first-person edits)
2. Current draft cover letter text (possibly edited)
3. A summary of what the candidate just edited or asked for
4. Deterministic metric weaknesses (low specificity, weak verb variety, grounding gaps, missing must-have keywords)
5. Prior clarifications already confirmed by the candidate

QUESTION KINDS:
- "experience_probe" — for an essential JD skill or technology that is STILL missing or weak in the current draft. Goal: source real experience the candidate didn't write down.
- "scope_probe" — for an ambiguity in the current draft (often introduced by an edit, or surviving from prior iterations).
- "iteration_probe" — for a follow-up that builds on a recent edit or prior clarification. Example: candidate just typed "shipped V2 to enterprise" — ask for the customer segment, the timeframe, or the team scope so it can be quantified honestly.

RULES:
- Each question ≤ 25 words. One question per line, no compound questions.
- Each question must reference a SPECIFIC current-draft weakness — name the bullet, the metric, the missing keyword, or the recent edit it follows up on.
- BUILD ON prior clarifications, do not re-ask them. If the candidate already said "yes, used Terraform on a side project", don't ask "Have you used Terraform?" again — ask the next-level question (scale, cadence, ownership).
- Bias toward EXPERIENCE PROBES and ITERATION PROBES (≥50% combined) — these are the most likely to surface new ground truth. SCOPE PROBES second.
- Do not invent weaknesses. If all four signal sources look healthy, return fewer questions (minimum 3).
- Output JSON only, no markdown fences, no preamble.

WORKED EXAMPLES — iteration probe quality:
  When the recent edit introduces a SUBSTANTIVE CLAIM (named numbers, ownership words, framework names, customer segments), probe DEPTH of the claim. Ask WHO else was involved, WHICH scope it covers, HOW MUCH/HOW MANY, and at WHAT cadence. Avoid asking WHY (motivation isn't source material) or WHETHER (yes/no dichotomies yield no new detail).

    Recent edit: "Shipped V2 to enterprise customers."
    OK iteration probe: "Which enterprise segment? How many customers in the first quarter?"
    NOT OK: "Was the V2 launch successful?" (yes/no, no new ground truth)
    NOT OK: "Why did you ship V2?" (motivation, not source material)

    Recent edit: "Defined and owned SLOs (99.9% availability, p95 latency under 250ms) on the API edge layer."
    OK iteration probe: "Sole owner or co-defined with the platform team? Review cadence?"
    OK iteration probe: "Beyond the API edge, did SLO ownership extend to other services?"
    NOT OK: "What was the root cause of the error-budget exhaustion you fixed?" (asks about cause, not the substance of the SLO claim)
    NOT OK: "Was the SLO definition deliberate or reactive?" (leading dichotomy; no detail surfaces either way)

  The pattern: substance-of-claim follow-ups produce citable detail (named collaborators, numeric scope). Cause/effect or yes/no follow-ups don't."""

# Dedicated short persona for the clarify() step. Smaller than SYSTEM_PROMPT
# because the task is narrowly scoped (question generation, not resume
# authoring) — narrower context yields tighter grounding and cheaper tokens
# (P9). Composition rule (≥50% experience probes) is enumerated below and
# graded by the clarification_quality eval rubric.
CLARIFY_SYSTEM_PROMPT = """You are an experienced technical recruiter helping a candidate prepare a tailored resume. You think like the recruiter who would interview this candidate next, not like a generic question generator.

The candidate has just been analyzed against a job description. Your role is to surface 3-5 short, specific clarifying questions that, when answered, would let a resume writer produce a stronger, more truthful, more interview-generating document.

The single most important property of a great clarifying question: when answered, it produces a bullet the candidate would not have written unprompted. Tool-name probes ("have you used Epic?") are dead ends when the answer is "no" — they create fatigue and don't surface adjacent experience. Context probes that translate JD requirements into PORTABLE experience asks let candidates from adjacent backgrounds map their experience onto the role. That's the recruiter move.

Three kinds of questions, in roughly this mix:

1. EXPERIENCE PROBES (kind="experience_probe"):
   For each job-description-required skill or technology that does NOT appear in the résumé — or appears only weakly — ask whether the candidate has hands-on experience with it OR with an adjacent/related technology that should be elevated. The goal is to source REAL experience the candidate has but didn't write down. Always offer an adjacent-experience escape hatch so a "no" still yields signal. Examples:
   - "The JD requires Kubernetes; your résumé mentions Docker. Have you used Kubernetes or another container orchestration platform in production, even briefly?"
   - "The role emphasizes Terraform. Have you authored or maintained Terraform modules in any past engagement, even a side project?"
   - "The JD asks for cross-functional leadership. Can you point to a specific time you set technical direction across a team you didn't manage directly?"

2. CONTEXT PROBES (kind="context_probe"):
   For each `hidden_qualities` item from the analysis (operating-context fit, scope of ownership, stakeholder gravity, resilience signal), ask a PORTABLE experience question that translates the JD's implied context into something an adjacent-background candidate can map to. The goal is to surface relevant experience the tool-name probes would miss. Examples:
   - JD context: regulated/healthcare workflows. Probe: "Have you built products for users in regulated, workflow-heavy environments where errors have real-world consequences — healthcare, fintech, transportation, anything similar?"
   - JD context: 0→1 product ownership. Probe: "Have you owned a product or feature from concept to first customer, including the decision of what to build and what to cut?"
   - JD context: exec-facing stakeholder gravity. Probe: "What's the most senior audience you've regularly presented direction to — and were you setting the agenda or responding to it?"
   - JD context: cross-functional influence without authority. Probe: "Walk me through a time you got teams you didn't manage to commit to a deadline or trade-off."

3. SCOPE PROBES (kind="scope_probe"):
   For ambiguities the analyzer flagged in the comparison — role scope, shipped-vs-prototype, decision authority, team size, audience — ask the candidate to disambiguate so the résumé can use precise language. Examples:
   - "The project X engagement reads as senior IC work. Were you setting technical direction, or executing on a defined roadmap?"
   - "Did the K8s migration ship to production, or remain a proof of concept?"

RULES:
- Each question ≤ 25 words. One question per line, no compound questions (no "and"/"or" joining two distinct asks).
- Do not ask leading questions ("Don't you agree that...?"). Do not ask generic prompts ("Tell me about yourself").
- Each question must cite a SPECIFIC source: name the JD-required skill that's missing (experience_probe), the hidden_qualities context signal (context_probe), or the analyzer-flagged ambiguity (scope_probe).
- Bias toward EXPERIENCE PROBES + CONTEXT PROBES (≥60% combined) — these are the most likely to surface real experience the candidate didn't write down. Tool-name-only probes without an adjacent-experience escape hatch are dead ends; do not emit them.
- When the JD strongly implies an operating-context or scope-of-ownership signal (regulated industry, 0→1, exec-facing, etc.), prefer a context_probe over a narrow tool-name experience_probe. The context_probe surfaces transferable experience; the tool-name probe only confirms or denies a specific item.
- Output JSON only, no markdown fences, no preamble."""

# Model selection rationale:
#   - Sonnet 4.6 for analyze() and generate(): the work needs reasoning depth
#     for JD analysis and instruction-following on the long generate prompt
#     (~3K tokens of resume_rules + cover_letter_rules + output_format).
#     Same per-token price as older Sonnet versions; the newer revision has
#     better structured-output adherence and grounding behavior.
#   - clarify() uses Haiku 4.5 as of 2026-06-01 (r1/clarify-model-trial). The
#     prior note parked it on Sonnet "until the rubrics clear 4.0 stably";
#     post-R1-split they do (clarification_quality floor ds 4.20 / pm 4.26 /
#     sre 4.02), so the cheaper model is in play. The switch is eval-gated: no
#     clarification_quality drop > 0.5 vs the 2026-06-01 floor AND a healthy
#     clarify_retry rate (Haiku must still satisfy the ClarifyResponse
#     context_probe + ≥60%-combined parse rules). See evals/TUNING_LOG.md.
#   - clarify_iteration() stays on Sonnet: iteration_quality is still
#     fixture-fragile (fires ~1/5 runs) and not yet stably ≥ 4.0 — not a
#     candidate for the cheaper model yet.
#   - Haiku 4.5 for scope check (_check_refinement_scope), eval grading
#     (evals/runner.py), and onboarding extraction (extract_experiences):
#     binary classification, structured rubric application, and one-shot
#     structured extraction are the Haiku sweet spot. Volume + structure
#     beats reasoning depth there.
#   - Opus is intentionally not used: ~5x the cost of Sonnet without a
#     proportional win on this workload. Reserve for future debugging
#     sessions if grounding regressions resist prompt-tightening.
SONNET_MODEL = "claude-sonnet-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
# Backward-compat alias — historical code uses MODEL as the default Sonnet handle.
# New code should reference SONNET_MODEL / HAIKU_MODEL explicitly.
MODEL = SONNET_MODEL
# Per-call output cap. analyze() returns a comprehensive JSON with 10+ keyed
# sections; Sonnet 4.6 is more verbose than older Sonnet 4 was and routinely
# uses 4–6K tokens on detail-rich real inputs. 8192 leaves headroom without
# inviting runaway output. _call_llm logs a warning on stop_reason="max_tokens"
# so truncation surfaces as a clear telemetry signal, not a silent JSON parse
# failure downstream.
MAX_TOKENS = 8192
MAX_SUPPLEMENTAL_CHARS = 6_000  # per-file cap — keeps total context manageable


def _current_draft_text(context_set: ContextSet) -> tuple[str, str]:
    """Return (resume_text, source_label) for the <resume> prompt block.

    Selection precedence at iteration > 0:
      1. edited_resume_text  — user typed edits since last generation
      2. last_generated_resume — most recent LLM output, no user edits
      3. resume.text — original primary (only if iteration > 0 yet no draft
         exists; this should be a rare degenerate case)

    At iteration 0 (no generate yet), always returns the original primary.
    The source_label is for telemetry/debugging only — not embedded in the prompt.
    """
    iteration = int(context_set.get("iteration", 0) or 0)
    if iteration <= 0:
        return context_set["resume"].get("text", ""), "primary"

    edited = (context_set.get("edited_resume_text") or "").strip()
    if edited:
        return edited, "edited"
    last_gen = (context_set.get("last_generated_resume") or "").strip()
    if last_gen:
        return last_gen, "last_generated"
    return context_set["resume"].get("text", ""), "primary_fallback"


def _stable_user_prefix(context_set: ContextSet) -> str:
    """Build the stable, cacheable portion of the user message.

    This block is identical across analyze() and generate() calls within the
    same iteration of the same context_set, enabling Anthropic prompt caching
    to hit on the second call. Sonnet's cache requires 1024+ tokens to engage;
    bundling the resume + JD + supplementals + candidate profile reliably
    exceeds that.

    Across iterations, the prefix legitimately changes (the <resume> block
    swaps to the current draft and supplementals demote to <historical_resumes>).
    Cross-iteration cache misses are expected behavior — the source material
    actually changed. Within one iteration (e.g. analyze→generate, or a retry),
    the prefix remains byte-identical and the cache hits.

    Phase B.2: when `context_set["career_corpus"]` is populated, the prefix
    emits a structured `<career_corpus>` block with ID-tagged experiences and
    bullets in place of the legacy `<resume>` + `<supplemental_resumes>` blocks.
    The LLM's selected_bullets output then references bullet IDs directly,
    making structural grounding cheap to enforce in B.3. The legacy path
    (no career_corpus field) is unchanged.

    Tag names, field order, and the inclusion-condition for the online profile
    are all load-bearing. Do not change one without the other.
    """
    candidate = context_set["candidate"]
    online_profile = candidate.get("profile_text", "").strip()
    iteration = int(context_set.get("iteration", 0) or 0)

    parts = [
        "<job_description>",
        context_set["job_description"],
        "</job_description>",
        "",
    ]

    corpus = context_set.get("career_corpus")
    if corpus:
        # Workstream B: honor the Compose step's pin/exclude overrides.
        # Workstream H: when llm_recommendations are present, restrict the
        # per-experience bullets to the curated effective set:
        #   (recommended ∪ added ∪ pinned) − excluded
        # The user_added "added" list comes from the per-experience drawer
        # (Workstream I). When no recommendations are present, behavior
        # is the prior pin/exclude-only filter (cache stays byte-identical).
        ov = context_set.get("composition_overrides") or {}
        excluded_ids = {int(x) for x in (ov.get("excluded") or [])}
        pinned_ids = {int(x) for x in (ov.get("pinned") or [])}
        added_ids = {int(x) for x in (ov.get("added") or [])}
        recommendations = context_set.get("llm_recommendations") or {}
        # `recommendations` is keyed by experience-id string when persisted
        # from JSON; coerce both shapes (dict or list) into per-exp sets.
        rec_by_exp: dict[int, set[int]] = {}
        if isinstance(recommendations, dict):
            for k, v in recommendations.items():
                try:
                    eid = int(k)
                except (TypeError, ValueError):
                    continue
                ids = v.get("bullet_ids") if isinstance(v, dict) else v
                rec_by_exp[eid] = {int(x) for x in (ids or [])}
        elif isinstance(recommendations, list):
            # Defensive: the LLM sometimes echoes "e3"/"b12" prefix
            # despite the prompt rule; strip before int(). See the
            # matching defense in app.py:recommend_application_bullets.
            def _norm_id(v: object) -> int | None:
                if v is None:
                    return None
                try:
                    return int(str(v).strip().lstrip("eEbB"))
                except (TypeError, ValueError):
                    return None
            for rec in recommendations:
                if not isinstance(rec, dict):
                    continue
                eid_int = _norm_id(rec.get("experience_id"))
                if eid_int is None:
                    continue
                bullet_ints = {bi for bi in (_norm_id(x) for x in (rec.get("bullet_ids") or [])) if bi is not None}
                rec_by_exp[eid_int] = bullet_ints

        use_recommendations = bool(rec_by_exp)
        if excluded_ids or use_recommendations:
            new_corpus: list[CorpusExperience] = []
            for exp in corpus:
                raw_eid = exp.get("id")
                if raw_eid is None:
                    new_corpus.append(exp)
                    continue
                eid = int(raw_eid)
                exp_bullets = exp.get("bullets") or []
                if use_recommendations:
                    effective = rec_by_exp.get(eid, set()) | added_ids | pinned_ids
                    exp_bullets = [b for b in exp_bullets
                                   if int(b.get("id") or 0) in effective]
                if excluded_ids:
                    exp_bullets = [b for b in exp_bullets
                                   if b.get("id") not in excluded_ids]
                new_exp: CorpusExperience = {**exp, "bullets": exp_bullets}
                new_corpus.append(new_exp)
            corpus = new_corpus
        # feat/bullet-drag-reorder — honor the user's explicit per-experience
        # bullet order from the Compose drag/keyboard UI. Persisted as
        # composition_overrides.bullet_order = {experience_id: [bullet_id, ...]}.
        # Present for an experience ⇒ authoritative over the corpus's
        # display_order; absent ⇒ untouched (default path stays byte-identical,
        # so the analyze→generate cache keeps hitting). Bullets not named in the
        # saved order keep their relative order at the END (covers a bullet added
        # via the drawer AFTER ordering — never silently re-sorts). This reorders
        # DATA, not the prompt template → no PROMPT_VERSION bump.
        bullet_order_raw = ov.get("bullet_order") or {}
        bullet_order: dict[int, list[int]] = {}
        if isinstance(bullet_order_raw, dict):
            for k, v in bullet_order_raw.items():
                try:
                    bullet_order[int(k)] = [int(x) for x in (v or [])]
                except (TypeError, ValueError):
                    continue
        if bullet_order:
            reordered: list[CorpusExperience] = []
            for exp in corpus:
                raw_eid = exp.get("id")
                oid = int(raw_eid) if raw_eid is not None else None
                order = bullet_order.get(oid) if oid is not None else None
                if not order:
                    reordered.append(exp)
                    continue
                rank = {bid: i for i, bid in enumerate(order)}
                exp_bullets = exp.get("bullets") or []
                # Stable sort: listed bullets take ranks 0..n-1; unlisted ones
                # share rank len(rank) and keep their original relative order.
                ordered_bullets = sorted(
                    exp_bullets,
                    key=lambda b: rank.get(int(b.get("id") or 0), len(rank)),
                )
                ordered_exp: CorpusExperience = {**exp, "bullets": ordered_bullets}
                reordered.append(ordered_exp)
            corpus = reordered
        parts.append(_corpus_block(
            corpus, iteration=iteration, pinned_ids=pinned_ids,
        ))
    else:
        resume_text, _ = _current_draft_text(context_set)
        resume_filename = context_set["resume"].get("filename", "primary")
        parts.extend([
            f'<resume filename="{resume_filename}" iteration="{iteration}">',
            resume_text,
            "</resume>",
            _supplemental_block(context_set, iteration=iteration),
        ])

    parts.extend([
        "<candidate_profile>",
        f"Name: {candidate.get('name', '')}",
        f"Email: {candidate.get('email', '')}",
        f"Phone: {candidate.get('phone', '')}",
        f"LinkedIn: {candidate.get('linkedin_url', '')}",
        f"Website: {candidate.get('website_url', '')}",
        f"Skills: {', '.join(candidate.get('skills', []))}",
        f"Certifications: {', '.join(candidate.get('certifications', []))}",
        f"Education: {candidate.get('education_summary', '')}",
        f"Notes: {candidate.get('notes', '')}",
        "</candidate_profile>",
    ])

    if online_profile:
        parts.extend([
            "",
            "<candidate_online_profile>",
            online_profile,
            "</candidate_online_profile>",
        ])

    return "\n".join(parts)


def _corpus_block(
    experiences: list[CorpusExperience],
    iteration: int,
    pinned_ids: frozenset[int] | set[int] = frozenset(),
) -> str:
    """Emit the `<career_corpus>` XML block when DB-backed mode is active.

    Each `<experience>` lists all eligible titles (the LLM picks the right
    framing per JD) and every active bullet with `id`, `tags`, `has_outcome`.
    The LLM's generate output is required to reference bullet IDs in
    `selected_bullets` and may propose new bullets / new titles in
    `proposed_new_bullets` / `proposed_experience_titles`.

    Markup conventions are load-bearing: GENERATE_CORPUS_PROMPT_GUIDE below
    documents the contract the LLM is told about.
    """
    parts: list[str] = [f'<career_corpus iteration="{iteration}">']
    for exp in experiences:
        end = exp.get("end_date") or "present"
        attrs = (
            f'id="e{exp["id"]}" '
            f'company="{_attr_escape(exp.get("company", ""))}" '
            f'dates="{exp.get("start_date", "")} → {end}"'
        )
        if exp.get("location"):
            attrs += f' location="{_attr_escape(exp["location"])}"'
        parts.append(f"  <experience {attrs}>")
        for t in exp.get("eligible_titles", []) or []:
            official = "true" if t.get("is_official") else "false"
            parts.append(
                f'    <eligible_title id="t{t["id"]}" official="{official}">'
                f'{_attr_escape(t.get("title", ""))}</eligible_title>'
            )
        for b in exp.get("bullets", []) or []:
            tags = ",".join(b.get("tags") or [])
            outcome = "true" if b.get("has_outcome") else "false"
            pinned_attr = ' pinned="true"' if b.get("id") in pinned_ids else ""
            parts.append(
                f'    <bullet id="b{b["id"]}" tags="{tags}" '
                f'has_outcome="{outcome}"{pinned_attr}>'
                f'{_attr_escape(b.get("text", ""))}</bullet>'
            )
        parts.append("  </experience>")
    parts.append("</career_corpus>")
    return "\n".join(parts)


def _attr_escape(value: str) -> str:
    """Minimal XML attribute escaping for the values we control.

    `&` MUST be replaced first or it captures the `&` we introduce when
    escaping `"` and `<`, producing `&amp;quot;` instead of `&quot;`. Tested
    by tests/test_corpus_mode_prompt.py::test_escapes_double_quotes_in_attributes.
    """
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _supplemental_block(context_set: ContextSet, iteration: int = 0) -> str:
    """Build the supplemental-resumes XML block for prompts.

    At iteration 0 (no generate yet) the block is `<supplemental_resumes>` —
    additional source material with equal standing to the primary.

    At iteration >= 1 the wrapper switches to `<historical_resumes>` and also
    folds in the original primary resume. Both are demoted to "earlier
    versions / historical reference only" so the LLM treats the current draft
    in <resume> as authoritative and only mines these for forgotten facts the
    candidate had on a prior version.

    Returns empty string only if iteration == 0 and there are no supplementals.
    """
    supplements = list(context_set.get("supplemental_resumes", []) or [])

    if iteration <= 0:
        if not supplements:
            return ""
        parts = [
            f"<supplemental_resumes count=\"{len(supplements)}\">",
            "The candidate has the following additional resume(s) as supplemental source material.",
            "All job titles, bullet points, and experience from these files may be used.",
            "When roles overlap across resumes, synthesize the richest version — do not duplicate.",
            "",
        ]
        for i, r in enumerate(supplements, 1):
            fname = r.get("filename", f"resume_{i}")
            text = r.get("text", "")
            if len(text) > MAX_SUPPLEMENTAL_CHARS:
                text = text[:MAX_SUPPLEMENTAL_CHARS] + "\n[truncated]"
            parts.append(f"<resume_{i} filename=\"{fname}\">")
            parts.append(text)
            parts.append(f"</resume_{i}>")
            parts.append("")
        parts.append("</supplemental_resumes>")
        return "\n".join(parts)

    # iteration >= 1 — fold the original primary in alongside supplementals
    # under the demoted wrapper. The current draft in <resume> is now the
    # authoritative version; everything below is historical reference only.
    historicals: list[dict[str, str]] = []
    primary_text = (context_set["resume"].get("text") or "").strip()
    primary_filename = context_set["resume"].get("filename", "primary")
    if primary_text:
        historicals.append({"filename": primary_filename, "text": primary_text})
    # Project SupplementalResume entries down to the (filename, text) shape we
    # render — keeps mypy happy and signals that `sections` is intentionally
    # unused in the historical-block prompt.
    for s in supplements:
        historicals.append({
            "filename": s.get("filename", ""),
            "text": s.get("text", ""),
        })

    if not historicals:
        return ""

    parts = [
        f"<historical_resumes count=\"{len(historicals)}\">",
        "These are EARLIER VERSIONS of the candidate's resumes provided as historical",
        "reference only. They are NOT the current draft. Use them only to surface",
        "specific facts (metrics, titles, dates, technologies) that the candidate had",
        "on a prior resume but may have forgotten to include in the current draft above.",
        "NEVER let a historical resume override or contradict the current draft.",
        "",
    ]
    # Rename loop variable from `r` (used in the iteration<=0 branch as
    # SupplementalResume) so mypy doesn't carry that narrowing into this scope.
    for i, h in enumerate(historicals, 1):
        fname = h.get("filename", f"historical_{i}")
        text = h.get("text", "")
        if len(text) > MAX_SUPPLEMENTAL_CHARS:
            text = text[:MAX_SUPPLEMENTAL_CHARS] + "\n[truncated]"
        parts.append(f"<historical_{i} filename=\"{fname}\">")
        parts.append(text)
        parts.append(f"</historical_{i}>")
        parts.append("")
    parts.append("</historical_resumes>")
    return "\n".join(parts)


class _StreamDone:
    """Sentinel yielded as the LAST item of `_call_llm_streaming`. Carries
    the accumulated text plus the stop_reason from the final message so
    parse/retry logic can decide what to do next.

    Distinguishable from text-chunk yields by isinstance check; callers
    that don't care about streaming chunks can drain via `_call_llm` below.
    """

    __slots__ = ("text", "stop_reason")

    def __init__(self, text: str, stop_reason: str | None):
        self.text = text
        self.stop_reason = stop_reason


def _call_llm_streaming(
    client: anthropic.Anthropic,
    user_prompt: str,
    *,
    cached_user_prefix: str = "",
    call_kind: str = "analyze",
    username: str = "",
    run_id: str = "",
    system_prompt: str = "",
    model: str | None = None,
) -> Iterator[str | _StreamDone]:
    """Streaming generator yielding text deltas, then a final `_StreamDone`.

    Yields:
        - `str` for each text delta as it arrives from the Anthropic stream
        - `_StreamDone` exactly once at the end with the full accumulated
          text + `stop_reason` from the final Message

    Telemetry, caching, and model-selection semantics match the non-streaming
    `_call_llm` (which is now a wrapper over this generator). One JSONL
    record per call, emitted in the finally block.

    Caching: the system block is sent with cache_control; when
    `cached_user_prefix` is non-empty it is sent as a cacheable user block
    preceding `user_prompt`. Anthropic's cache requires 1024+ tokens to
    engage on Sonnet — the system prompt alone is typically below that
    threshold, so the user-prefix block is what actually drives cache hits
    across analyze→generate within a session.

    The optional `system_prompt` argument lets narrowly-scoped calls (e.g.
    clarify()) use a smaller dedicated persona without overloading
    SYSTEM_PROMPT. Calls with a non-default system_prompt will not hit the
    system-block cache established by analyze/generate, which is acceptable
    for cheap small calls.

    The optional `model` argument lets cheap structured-output calls (e.g.
    extract_experiences) opt into Haiku for cost without bypassing this
    helper's caching + telemetry machinery. Defaults to SONNET_MODEL.
    """
    effective_model = model or SONNET_MODEL
    user_content: list[dict] = []
    if cached_user_prefix:
        user_content.append({
            "type": "text",
            "text": cached_user_prefix,
            "cache_control": {"type": "ephemeral"},
        })
    user_content.append({"type": "text", "text": user_prompt})

    # Calls that omit system_prompt fall back to SYSTEM_PROMPT — resolved through
    # the override registry so a candidate SYSTEM_PROMPT reaches analyze_synthesis,
    # generate, generate_cover_letter, etc. With no override active this returns
    # the SYSTEM_PROMPT constant unchanged (default-path byte-identity).
    effective_system = system_prompt or _resolve_system_prompt("SYSTEM_PROMPT")

    logger.info(
        "LLM call starting — call=%s cached_prefix=%d chars, prompt=%d chars",
        call_kind, len(cached_user_prefix), len(user_prompt),
    )
    t0 = time.perf_counter()
    status = "ok"
    final = None
    chunks: list[str] = []
    try:
        with client.messages.stream(
            model=effective_model,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": effective_system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],  # type: ignore[typeddict-item]
        ) as stream:
            for delta in stream.text_stream:
                chunks.append(delta)
                yield delta
            final = stream.get_final_message()
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        usage = getattr(final, "usage", None) if final is not None else None
        stop_reason = getattr(final, "stop_reason", None) if final is not None else None
        _emit_call_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "username": username,
            "run_id": run_id,
            "call": call_kind,
            "model": effective_model,
            "prompt_version": effective_prompt_version(),
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
            "latency_ms": elapsed_ms,
            "stop_reason": stop_reason,
            "status": status,
        })

    if stop_reason == "max_tokens":
        logger.warning(
            "LLM call hit MAX_TOKENS — call=%s output truncated at %d tokens. "
            "Downstream JSON parse will likely fail. Consider raising MAX_TOKENS "
            "or tightening the prompt's output_format spec.",
            call_kind, final.usage.output_tokens,
        )

    logger.info(
        "LLM call complete — call=%s in=%d out=%d cache_create=%d cache_read=%d stop=%s %dms",
        call_kind,
        final.usage.input_tokens,
        final.usage.output_tokens,
        getattr(final.usage, "cache_creation_input_tokens", 0),
        getattr(final.usage, "cache_read_input_tokens", 0),
        stop_reason,
        elapsed_ms,
    )
    yield _StreamDone(text="".join(chunks), stop_reason=stop_reason)


def _call_llm(
    client: anthropic.Anthropic,
    user_prompt: str,
    *,
    cached_user_prefix: str = "",
    call_kind: str = "analyze",
    username: str = "",
    run_id: str = "",
    system_prompt: str = "",
    model: str | None = None,
) -> str:
    """Non-streaming wrapper — drain `_call_llm_streaming` and return the
    accumulated text. Preserves the existing call signature for all callers
    that don't need token-level streaming; new SSE routes use the underlying
    generator directly.
    """
    final_text = ""
    for item in _call_llm_streaming(
        client, user_prompt,
        cached_user_prefix=cached_user_prefix,
        call_kind=call_kind,
        username=username,
        run_id=run_id,
        system_prompt=system_prompt,
        model=model,
    ):
        if isinstance(item, _StreamDone):
            final_text = item.text
    return final_text


_FENCE_RE = re.compile(r"^```(?:[a-zA-Z]+)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _strip_fences(raw: str) -> str:
    """Strip leading/trailing markdown code fences from an LLM response.

    The system prompt instructs JSON-only output, but Sonnet still occasionally
    wraps the body in ```json ... ```. Tolerate that without retrying.
    """
    cleaned = raw.strip()
    m = _FENCE_RE.match(cleaned)
    if m:
        return m.group(1).strip()
    return cleaned


def _parse_or_retry_streaming(
    client: anthropic.Anthropic,
    base_prompt: str,
    *,
    cached_user_prefix: str,
    response_model: type[BaseModel],
    call_kind: str,
    username: str,
    run_id: str,
    max_attempts: int = 2,
    system_prompt: str = "",
    model: str | None = None,
) -> Iterator[tuple[str, object]]:
    """Streaming generator variant of `_parse_or_retry`.

    Yields:
        - `("chunk", str)` for each text delta as it arrives from the LLM
        - `("retry", str)` when a parse attempt fails and a retry begins;
          the str is a short human-readable reason
        - `("done", dict)` exactly once on success with the parsed JSON

    Raises `LLMResponseError` if retries are exhausted (same as the
    non-streaming variant).

    The streaming behavior follows the same retry shape as
    `_parse_or_retry`: the first attempt streams chunks; if parsing
    fails, a `retry` event fires and the retry's chunks begin streaming.
    The caller is expected to render chunks live for perceived-latency
    purposes; `_strip_fences` + `json.loads` only runs on the
    fully-accumulated text once each attempt's stream completes.
    """
    base_text = ""
    retry_prompt = base_prompt
    current_kind = call_kind
    for attempt in range(max_attempts):
        accumulated = ""
        for item in _call_llm_streaming(
            client, retry_prompt,
            cached_user_prefix=cached_user_prefix,
            call_kind=current_kind,
            username=username,
            run_id=run_id,
            system_prompt=system_prompt,
            model=model,
        ):
            if isinstance(item, _StreamDone):
                accumulated = item.text
            else:
                yield ("chunk", item)
        base_text = accumulated
        try:
            data = json.loads(_strip_fences(accumulated), strict=False)
            response_model.model_validate(data)
            yield ("done", data)
            return
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt + 1 >= max_attempts:
                logger.error(
                    "LLM response validation failed after %d attempts — call=%s err=%s",
                    max_attempts, call_kind, e,
                )
                raise LLMResponseError(accumulated, str(e)) from e
            logger.warning(
                "LLM response validation failed on attempt %d — call=%s err=%s, retrying",
                attempt + 1, call_kind, e,
            )
            yield ("retry", str(e))
            retry_prompt = (
                f"{base_prompt}\n\n<retry_reason>Your previous response failed "
                f"validation: {e}. Respond again with valid JSON matching the "
                f"exact structure requested above. Output JSON only, no markdown "
                f"fences, no commentary.</retry_reason>"
            )
            current_kind = f"{call_kind}_retry"
    raise LLMResponseError(base_text, "exhausted retries")


def _parse_or_retry(
    client: anthropic.Anthropic,
    base_prompt: str,
    *,
    cached_user_prefix: str,
    response_model: type[BaseModel],
    call_kind: str,
    username: str,
    run_id: str,
    max_attempts: int = 2,
    system_prompt: str = "",
    model: str | None = None,
    validation_context: dict | None = None,
) -> dict:
    """Parse an LLM JSON response, retrying once with the validation error
    appended on parse failure or missing required keys.

    The cached_user_prefix is byte-identical across attempts so the retry
    hits Anthropic's prompt cache (only the per-call base_prompt + retry
    reason differs). Each attempt emits its own JSONL telemetry record;
    retries use call_kind="<kind>_retry" so dashboard breakdowns can
    distinguish them from first-pass calls.

    Raises LLMResponseError after max_attempts failures so the caller never
    silently degrades on bad output.
    """
    raw = _call_llm(
        client, base_prompt,
        cached_user_prefix=cached_user_prefix,
        call_kind=call_kind, username=username, run_id=run_id,
        system_prompt=system_prompt, model=model,
    )
    for attempt in range(max_attempts):
        try:
            # `strict=False` allows ASCII control characters (0x00-0x1F)
            # to appear inside JSON string values. Claude sometimes emits
            # literal newlines/tabs inside multi-line content fields
            # (résumé markdown, cover-letter prose) — the spec says to
            # escape them but the model doesn't always comply, and
            # appending the error to a retry prompt does not reliably
            # fix it. Structural malformations (missing brace, trailing
            # comma) still fail and trigger the retry path; we are only
            # widening tolerance for the one quirky case we observe.
            data = json.loads(_strip_fences(raw), strict=False)
            response_model.model_validate(data, context=validation_context)
            return data
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt + 1 >= max_attempts:
                logger.error(
                    "LLM response validation failed after %d attempts — call=%s err=%s",
                    max_attempts, call_kind, e,
                )
                raise LLMResponseError(raw, str(e)) from e
            logger.warning(
                "LLM response validation failed on attempt %d — call=%s err=%s, retrying",
                attempt + 1, call_kind, e,
            )
            retry_prompt = (
                f"{base_prompt}\n\n<retry_reason>Your previous response failed "
                f"validation: {e}. Respond again with valid JSON matching the "
                f"exact structure requested above. Output JSON only, no markdown "
                f"fences, no commentary.</retry_reason>"
            )
            raw = _call_llm(
                client, retry_prompt,
                cached_user_prefix=cached_user_prefix,
                call_kind=f"{call_kind}_retry", username=username, run_id=run_id,
                system_prompt=system_prompt, model=model,
            )
    raise LLMResponseError(raw, "exhausted retries")


def analyze(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    username: str = "",
    run_id: str = "",
) -> dict:
    """Call 1: Analysis & Strategy — two-pass split (r1/analyze-split-retry).

    Pass 1 (Haiku 4.5, EXTRACTION_SYSTEM_PROMPT): extracts the JD keyword/
    vocabulary signals (essential_skills, preferred_skills, industry_keywords,
    the typed hidden_qualities, professional_vocabulary, keyword_placement).
    Structurally Haiku-friendly — classification, not multi-step reasoning.

    Pass 2 (Sonnet 4.6, the shared default SYSTEM_PROMPT): produces comparison,
    suggestions, overall_strategy. Receives Pass 1's output as
    <extracted_signal> so it grounds its synthesis on concrete extracted
    signals rather than re-extracting in line. It runs under SYSTEM_PROMPT (NOT
    a dedicated synthesis persona) on purpose — that keeps its cached prefix
    byte-identical to generate()'s, reclaiming the analyze→generate prompt cache.

    Returns the merged dict — the same AnalyzeResponse shape every downstream
    consumer expects (frontend renderer, clarify(), generate(), eval rubrics,
    the recommend_* Haiku calls). The username threads through to JSONL
    telemetry; run_id correlates both passes with the sibling generate() call
    and any eval result that consumed the output.

    Rationale (P6 Specialized Review): two narrower personas with task-specific
    vocabulary outperform one broad persona doing extraction AND strategy in one
    pass. P9 Token Economy counterweight: the split is justified by the measured
    single-call latency; the eval dual gate is the quality-floor enforcement.
    """
    # P2 Context Hygiene: stable inputs (résumé + JD + profile) live in the
    # cached prefix; both passes share it byte-identically so Pass 2 (Sonnet)
    # writes the prompt-cache block that the later generate() call reads.
    prefix = _stable_user_prefix(context_set)
    extraction = _parse_or_retry(
        client, _analyze_extraction_prompt(context_set),
        cached_user_prefix=prefix,
        response_model=AnalyzeExtractionResponse,
        call_kind="analyze_extraction",
        username=username, run_id=run_id,
        system_prompt=_resolve_system_prompt("EXTRACTION_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    )
    # Synthesis runs under the DEFAULT SYSTEM_PROMPT (no system_prompt override),
    # NOT a dedicated synthesis persona, so its cached prefix
    # [SYSTEM_PROMPT][prefix] is byte-identical to generate()'s — which reclaims
    # the analyze→generate prompt cache. Anthropic prefix caching matches from the
    # system block, so a distinct synthesis persona would diverge there and force
    # generate to re-prefill the whole corpus. The synthesis-specific framing
    # (strategy-only; ground in <extracted_signal>) lives in the user prompt,
    # after the cached prefix.
    synthesis = _parse_or_retry(
        client, _analyze_synthesis_prompt(context_set, extraction),
        cached_user_prefix=prefix,
        response_model=AnalyzeSynthesisResponse,
        call_kind="analyze_synthesis",
        username=username, run_id=run_id,
        # system_prompt + model default to SYSTEM_PROMPT + SONNET_MODEL in _call_llm
    )
    return {**extraction, **synthesis}


def _analyze_extraction_prompt(context_set: ContextSet) -> str:
    """Build the Pass 1 (extraction) user prompt — Haiku target.

    Keyword/vocabulary extraction only — no strategy, comparison, or positioning
    narrative (those are Pass 2's job). The deterministic keyword analysis is
    included so the model can classify matched vs missing with full context. The
    hidden_qualities schema matches the typed HiddenQualityItem contract that
    AnalyzeExtractionResponse enforces at parse time.
    """
    return f"""<task>Extract and classify the keyword and vocabulary signals in this job description. Output JSON only — no prose, no strategy, no positioning recommendations.</task>

<deterministic_analysis>
Keyword match score: {context_set['deterministic_analysis']['keyword_overlap']['match_score']}
Keywords already matched (present in candidate's source material): {', '.join(context_set['deterministic_analysis']['keyword_overlap']['matched'][:20])}
Keywords missing from candidate's source material: {', '.join(context_set['deterministic_analysis']['keyword_overlap']['missing_from_resume'][:20])}
</deterministic_analysis>

<instructions>
For "hidden_qualities", surface the operating-context signals the JD implies — NOT trait-words
("collaborative", "autonomous"). Each item is an object with a "category" (one of exactly
"operating_context", "scope_of_ownership", "stakeholder_gravity", "resilience") and a "signal":
one portable sentence describing the context an adjacent-background candidate could map onto
(e.g. "Builds for regulated, workflow-heavy environments where errors have real consequences").
One concept per signal.

Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "essential_skills": ["atomic skill — ONE concept per item, named in minimum quals or clearly required"],
  "preferred_skills": ["atomic skill — ONE concept per item, named in preferred quals or nice-to-have"],
  "industry_keywords": ["atomic domain term, acronym, framework, or methodology — ONE concept per item"],
  "hidden_qualities": [
    {{"category": "operating_context", "signal": "portable context the JD implies, one concept"}}
  ],
  "professional_vocabulary": ["specialized term the JD uses that résumés in this field should adopt"],
  "keyword_placement": [
    {{
      "keyword": "missing keyword (atomic)",
      "suggested_location": "Where in the résumé to add it (section / bullet area)",
      "how": "How to incorporate naturally without keyword-stuffing"
    }}
  ]
}}
</instructions>"""


def _analyze_synthesis_prompt(context_set: ContextSet, extraction: dict) -> str:
    """Build the Pass 2 (synthesis) user prompt — Sonnet target.

    Receives Pass 1's extraction output as <extracted_signal> so the strategist
    grounds comparison + suggestions on concrete extracted signals rather than
    re-extracting in line. Deterministic ATS warnings stay visible so structural
    format issues fold into the suggestions narrative. Kept lean — this is the
    latency bottleneck on the two-pass path.
    """
    # Render typed {category, signal} hidden_qualities as readable lines.
    # Tolerant of a bare-string item defensively — extraction validates the
    # typed shape, but the render must not KeyError if that ever changes.
    hq_lines: list[str] = []
    for item in extraction.get('hidden_qualities', []):
        if isinstance(item, dict):
            hq_lines.append(f"- [{item.get('category', 'context')}] {item.get('signal', '')}")
        else:
            hq_lines.append(f"- {item}")
    hidden_qualities_block = "\n".join(hq_lines) if hq_lines else "(none)"

    return f"""<task>This is the STRATEGY pass of a two-pass analysis. An ATS scanner has already extracted the job description's keyword and vocabulary signals — they are given below as <extracted_signal>. Do NOT re-extract or re-list keywords. Produce ONLY the strategic positioning: where this candidate is strong, where they are weak, and what specific changes lift them to a callback. Ground every strength, gap, and suggestion in <extracted_signal>, the candidate's source material, or the deterministic analysis, and cite the specific signal by name.</task>

<extracted_signal>
Essential skills (from JD, required): {json.dumps(extraction.get('essential_skills', []))}
Preferred skills (from JD, nice-to-have): {json.dumps(extraction.get('preferred_skills', []))}
Industry keywords: {json.dumps(extraction.get('industry_keywords', []))}
Operating-context signals:
{hidden_qualities_block}
Professional vocabulary: {json.dumps(extraction.get('professional_vocabulary', []))}
Keyword placement suggestions: {json.dumps(extraction.get('keyword_placement', []))}
</extracted_signal>

<deterministic_analysis>
Keyword match score: {context_set['deterministic_analysis']['keyword_overlap']['match_score']}
ATS warnings: {json.dumps(context_set['deterministic_analysis']['ats_warnings'])}
</deterministic_analysis>

<instructions>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "comparison": {{
    "strengths": ["specific strength — cite an extracted skill or résumé item by name"],
    "gaps": ["specific gap — cite an essential_skill that's missing or weak"],
    "title_alignment": "Assessment of how well current titles align with the target role"
  }},
  "suggestions": [
    {{
      "section": "Section name in résumé",
      "action": "Concrete change to make",
      "rationale": "Why this improves candidacy — cite an extracted signal or gap"
    }}
  ],
  "overall_strategy": "2-3 sentence positioning narrative for this candidate against this role"
}}
</instructions>"""


def analyze_streaming(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    username: str = "",
    run_id: str = "",
) -> Iterator[tuple[str, object]]:
    """Streaming counterpart to `analyze()` — the two-pass orchestrator.

    Yields:
        - `("phase", {"phase": "extraction"})` once before Pass 1 starts
        - `("chunk", str)` / `("retry", str)` events from Pass 1 (Haiku)
        - `("phase", {"phase": "synthesis"})` once before Pass 2 starts
        - `("chunk", str)` / `("retry", str)` events from Pass 2 (Sonnet)
        - `("done", merged_dict)` once on success with the full merged analysis

    The per-pass `done` events from `_parse_or_retry_streaming` are intercepted
    (captured, not forwarded); only the final merged `done` reaches the caller.
    The `phase` events let the SSE route swap the frontend status label per pass.
    Both passes share one cached_user_prefix so Pass 2 hits the prompt cache.
    """
    prefix = _stable_user_prefix(context_set)

    yield ("phase", {"phase": "extraction"})
    extraction: dict | None = None
    for event_name, payload in _parse_or_retry_streaming(
        client, _analyze_extraction_prompt(context_set),
        cached_user_prefix=prefix,
        response_model=AnalyzeExtractionResponse,
        call_kind="analyze_extraction",
        username=username, run_id=run_id,
        system_prompt=_resolve_system_prompt("EXTRACTION_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    ):
        if event_name == "done" and isinstance(payload, dict):
            extraction = payload
        else:
            yield (event_name, payload)

    if extraction is None:
        # _parse_or_retry_streaming raises LLMResponseError on exhausted retries,
        # so reaching here with extraction=None is a helper contract violation.
        raise LLMResponseError("", "extraction phase ended without a parsed result")

    yield ("phase", {"phase": "synthesis"})
    synthesis: dict | None = None
    # Synthesis under the default SYSTEM_PROMPT (no override) so its cached prefix
    # matches generate()'s and reclaims the analyze→generate cache (see analyze()).
    for event_name, payload in _parse_or_retry_streaming(
        client, _analyze_synthesis_prompt(context_set, extraction),
        cached_user_prefix=prefix,
        response_model=AnalyzeSynthesisResponse,
        call_kind="analyze_synthesis",
        username=username, run_id=run_id,
    ):
        if event_name == "done" and isinstance(payload, dict):
            synthesis = payload
        else:
            yield (event_name, payload)

    if synthesis is None:
        raise LLMResponseError("", "synthesis phase ended without a parsed result")

    yield ("done", {**extraction, **synthesis})


def clarify(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict,
    username: str = "",
    run_id: str = "",
) -> dict:
    """Optional interview step between analyze() and generate().

    Generates 3-5 targeted questions based on the analyzer's output:
      - EXPERIENCE PROBES for JD-required skills missing from the resume
        (goal: source real experience the candidate didn't write down)
      - SCOPE PROBES for ambiguities flagged in comparison_analysis
        (goal: disambiguate role scope, shipped-vs-prototype, etc.)

    Returns:
      {
        "questions": [
          {"id": "q1", "text": "...", "target_gap": "...", "kind": "experience_probe"},
          ...
        ],
        "reasoning": "1-2 sentence summary of how questions were composed"
      }

    Uses CLARIFY_SYSTEM_PROMPT (smaller, focused) rather than the full
    hiring-manager SYSTEM_PROMPT. The user prefix here is intentionally
    compact — just the analysis output and deterministic keyword gaps —
    because the full resume/JD has already been digested by the analyzer.
    """
    # Compact inputs — the analyzer has already digested the resume + JD.
    # We pass only the structured outputs the clarifier needs to identify gaps.
    overlap = context_set.get("deterministic_analysis", {}).get("keyword_overlap", {})
    missing_jd_keywords = overlap.get("missing_from_resume", [])[:20]
    candidate_skills = context_set.get("candidate", {}).get("skills", [])

    hidden_qualities = analysis.get('hidden_qualities', [])
    # Render each context signal as "- [category] signal". Tolerant of legacy
    # list[str] items from analyses produced before the hidden_qualities schema
    # change (an iteration can reload an older context file).
    _signal_lines = []
    for _hq in hidden_qualities:
        if isinstance(_hq, dict):
            _signal_lines.append(f"- [{_hq.get('category', 'context')}] {_hq.get('signal', '')}")
        else:
            _signal_lines.append(f"- {_hq}")
    context_signals_block = "\n".join(_signal_lines) if _signal_lines else "(none)"

    prompt = f"""<task>Generate 3-5 targeted clarifying questions for the candidate.</task>

<analyzer_output>
Essential skills (from JD): {json.dumps(analysis.get('essential_skills', []))}
Preferred skills (from JD): {json.dumps(analysis.get('preferred_skills', []))}
Comparison strengths: {json.dumps(analysis.get('comparison', {}).get('strengths', []))}
Comparison gaps: {json.dumps(analysis.get('comparison', {}).get('gaps', []))}
Title alignment: {analysis.get('comparison', {}).get('title_alignment', '')}
Keyword placements suggested: {json.dumps(analysis.get('keyword_placement', []))}
Overall strategy: {analysis.get('overall_strategy', '')}
</analyzer_output>

<context_signals>
Operating-context / scope / stakeholder / resilience signals implied by the JD (use
these to drive CONTEXT PROBES — translate each into a portable experience question
that lets an adjacent-background candidate map their work onto this role):
{context_signals_block}
</context_signals>

<deterministic_gaps>
JD keywords missing from résumé: {json.dumps(missing_jd_keywords)}
Candidate's self-listed skills: {json.dumps(candidate_skills)}
</deterministic_gaps>

<instructions>
Compose 3-5 questions across three kinds:
- EXPERIENCE PROBES (kind="experience_probe") — JD-required skill missing or weak; always include an adjacent-experience escape hatch
- CONTEXT PROBES (kind="context_probe") — translate a `<context_signals>` item into a portable experience question
- SCOPE PROBES (kind="scope_probe") — analyzer-flagged ambiguity in comparison gaps or title alignment

At least 60% combined must be EXPERIENCE PROBES + CONTEXT PROBES. When the JD strongly implies an operating-context / scope-of-ownership / stakeholder / resilience signal, prefer a context_probe over a narrow tool-name experience_probe — the context_probe surfaces transferable experience; the tool-name probe only confirms or denies a specific item.

Each question's target_gap field must cite the specific source: the missing JD skill name (experience_probe), the `<context_signals>` item (context_probe), or the analyzer's gap text / keyword_placement item (scope_probe). Do not invent gaps that aren't in the analyzer output or context signals.

Respond with valid JSON only. No markdown fences. Use this exact structure:
{{
  "questions": [
    {{
      "id": "q1",
      "text": "The question text, <=25 words, no compound or leading questions.",
      "target_gap": "Specific source — e.g. 'Essential skill Kubernetes missing from résumé', 'Context signal: regulated-industry workflows', or 'Analyzer flagged ambiguity in title_alignment: ...'",
      "kind": "experience_probe"
    }}
  ],
  "reasoning": "1-2 sentence summary of how the question mix was composed."
}}
</instructions>"""

    # No cached_user_prefix: this call uses a dedicated small system prompt
    # and a compact per-call user message. Cache miss is cheap (~1K tokens
    # of input) and keeps the call focused.
    return _parse_or_retry(
        client, prompt,
        cached_user_prefix="",
        response_model=ClarifyResponse,
        call_kind="clarify",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("CLARIFY_SYSTEM_PROMPT"),
        # Haiku 4.5 for clarify (r1/clarify-model-trial, 2026-06-01): short
        # structured output; clarification_quality cleared 4.0 stably after the
        # R1 two-pass split. Switch is eval-gated — see evals/TUNING_LOG.md.
        model=HAIKU_MODEL,
        validation_context={"hidden_qualities_non_empty": bool(hidden_qualities)},
    )


def clarify_iteration(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict,
    current_resume_text: str,
    current_cover_letter_text: str,
    recent_edits_summary: str,
    deterministic_signals: dict,
    prior_clarifications: list[dict],
    username: str = "",
    run_id: str = "",
) -> dict:
    """Iteration-aware variant of clarify().

    Generates 3-5 questions targeting weaknesses in the CURRENT iteration's
    draft (not the original resume). The four signal sources documented in the
    plan ride along:

      1. current resume vs JD gap (via analysis.comparison.gaps + current draft)
      2. recent_edits_summary — what the candidate just typed/asked for
      3. deterministic_signals — verb diversity, specificity, grounding,
         must-have keyword coverage on the current draft
      4. prior_clarifications — already-confirmed truths the LLM must build
         on rather than re-ask

    Uses CLARIFY_ITERATION_SYSTEM_PROMPT (separate from CLARIFY_SYSTEM_PROMPT)
    because the task is materially different — there's a draft to react to and
    confirmed truths to respect.

    Returns the same shape as clarify(): {questions: [...], reasoning: ...}.
    """
    # Compact prior-clarifications block — pair each question with its answer
    # so the LLM sees what's already established. Only confirmed (non-empty)
    # answers count; skipped questions are not "established truth".
    if prior_clarifications:
        confirmed_lines = []
        for c in prior_clarifications:
            q_text = (c.get("question") or "").strip()
            a_text = (c.get("answer") or "").strip()
            if not q_text or not a_text:
                continue
            confirmed_lines.append(f"- Q: {q_text}\n  A: {a_text}")
        confirmed_block = "\n".join(confirmed_lines) or "(none)"
    else:
        confirmed_block = "(none)"

    # Pull the current draft's gap sources from the analyzer output. The
    # analyzer's comparison.gaps was computed against the ORIGINAL resume, but
    # those gaps still inform what the JD wants — items missing from the
    # current draft remain valid probes.
    comparison = analysis.get("comparison", {}) or {}
    overlap = (context_set.get("deterministic_analysis", {}) or {}).get("keyword_overlap", {}) or {}

    # Cover letter is included as compact context, not the focus — interview
    # questions almost always target the resume because that's where source
    # material drives generation. Truncate aggressively to keep the prompt tight.
    cl_excerpt = (current_cover_letter_text or "").strip()
    if len(cl_excerpt) > 1500:
        cl_excerpt = cl_excerpt[:1500] + "\n[truncated]"

    prompt = f"""<task>Generate 3-5 targeted clarifying questions for the candidate, focused on the CURRENT iteration's draft.</task>

<current_draft_resume>
{current_resume_text}
</current_draft_resume>

<current_draft_cover_letter>
{cl_excerpt or "(no cover letter draft yet)"}
</current_draft_cover_letter>

<recent_edits>
{recent_edits_summary or "(no recent edits — the candidate has not modified the preview since the last generation)"}
</recent_edits>

<deterministic_signals>
{json.dumps(deterministic_signals, indent=2)}
</deterministic_signals>

<analyzer_gaps_still_relevant>
Comparison gaps (from original analysis): {json.dumps(comparison.get("gaps", []))}
Title alignment: {comparison.get("title_alignment", "")}
JD essential skills: {json.dumps(analysis.get("essential_skills", []))}
JD keywords still missing from current draft: {json.dumps(overlap.get("missing_from_resume", [])[:20])}
</analyzer_gaps_still_relevant>

<already_confirmed_clarifications>
The candidate has already confirmed the following in prior interview rounds.
DO NOT re-ask these. Build on them with follow-up questions if relevant.
{confirmed_block}
</already_confirmed_clarifications>

<instructions>
Compose 3-5 questions. At least half (combined) must be EXPERIENCE PROBES (kind="experience_probe") or ITERATION PROBES (kind="iteration_probe"). The rest may be SCOPE PROBES (kind="scope_probe").

Each question's target_gap field MUST cite the specific current-draft source:
  - For experience_probe: name the JD essential skill or keyword still missing from the current draft.
  - For iteration_probe: name the recent edit, prior clarification, or deterministic-signal weakness it follows up on.
  - For scope_probe: quote the ambiguous bullet, role, or assertion in the current draft.

Do not invent gaps that none of the four signal sources support. If signals look healthy across the board, return only 3 questions rather than padding to 5.

Respond with valid JSON only. No markdown fences. Use this exact structure:
{{
  "questions": [
    {{
      "id": "q1",
      "text": "The question text, <=25 words, no compound or leading questions.",
      "target_gap": "Specific source — e.g. 'Essential skill Terraform missing from current draft' or 'Recent edit added \\'shipped V2\\' — needs scope/timeframe' or 'Deterministic signal: verb_diversity 0.32, top_repeated led/managed'",
      "kind": "iteration_probe"
    }}
  ],
  "reasoning": "1-2 sentence summary of how the question mix was composed and which signals it draws from."
}}
</instructions>"""

    # Same caching rationale as clarify(): dedicated short system prompt,
    # compact per-call user message — no cached prefix benefit. The current
    # draft varies per iteration anyway, so a cached prefix wouldn't hit.
    return _parse_or_retry(
        client, prompt,
        cached_user_prefix="",
        response_model=ClarifyResponse,
        call_kind="iterate_clarify",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("CLARIFY_ITERATION_SYSTEM_PROMPT"),
    )


def _current_cover_letter_draft(context_set: ContextSet) -> tuple[str, str]:
    """Return (cover_letter_text, source_label) for the optional draft block.

    Mirrors _current_draft_text but for the cover letter, where there is no
    "original" — the cover letter only exists once the LLM produces one. So at
    iteration 0 the result is empty and the prompt omits the draft block.

    Selection precedence (iteration >= 1):
      1. edited_cover_letter_text — user typed edits since last generation
      2. last_generated_cover_letter — most recent LLM output
      3. empty — no draft to evolve (rare degenerate case)
    """
    iteration = int(context_set.get("iteration", 0) or 0)
    if iteration <= 0:
        return "", "none"
    edited = (context_set.get("edited_cover_letter_text") or "").strip()
    if edited:
        return edited, "edited"
    last_gen = (context_set.get("last_generated_cover_letter") or "").strip()
    if last_gen:
        return last_gen, "last_generated"
    return "", "none"


# The cover-letter contract — VP-level voice, 3-paragraph structure,
# format rules, banned phrases. Used by both generate() (when
# with_cover_letter=True) and the dedicated
# generate_cover_letter_against_resume() (β.5). Promoted to a module-level
# constant so the two call sites stay byte-identical and the cover-letter
# contract has one source of truth.
_COVER_LETTER_RULES_BLOCK = """<cover_letter_rules>
VOICE — VP-level professional: courteous, concise, direct, confident, considerate. A clear outlier.

  Sentence construction:
  - Average sentence length: 12-16 words. Never exceed 25 words in a single sentence.
  - Vary rhythm deliberately: a longer setup sentence followed by a short, punchy payoff.
    Example: "Scaling a platform from 50K to 4M users taught me where distributed systems actually break. I've since rebuilt three of them."
  - One idea per sentence. Split compound thoughts ruthlessly.
  - Lead every sentence with the subject and an active verb. Cut the run-up.
    Weak: "I have had the opportunity to work with cross-functional teams to deliver..."
    Strong: "I've led cross-functional teams through four product launches, each on schedule."
  - No hedging: never "I believe," "I think," "I hope," "I feel," "I would like to."
    State it: "I will," "I have," "I deliver," "I build."
  - No throat-clearing: never "I am excited to," "I am pleased to," "I am writing to."
    The letter's existence says that. Open with substance.
  - Do not start consecutive sentences with "I." Recast where needed.
  - Confident, not arrogant. Acknowledge the company's work specifically; show you've done homework.

STRUCTURE — 3 paragraphs, 250-320 words total, one page only:

Paragraph 1 — HOOK (2-3 sentences):
  Open with a specific observation about the company or role — something that signals genuine attention.
  Name the exact role in the first or second sentence. Lead with what you bring, not what you want.
  Never open with "I am writing to apply for..." or any variation.

Paragraph 2 — EVIDENCE (3-5 sentences):
  Connect 2-3 specific, quantified accomplishments directly to the role's key requirements.
  Tell the story, not the bullet point. Show cause and effect: what you did, the result, why it matters here.
  Weave in 2-3 of the JD's essential keywords naturally — never force them.
  Do not repeat the resume verbatim. The letter illuminates; the resume documents.

Paragraph 3 — CLOSE (2-3 sentences):
  Confident forward look — not "I hope to hear from you." More: "I'd welcome a direct conversation about what this team is building."
  One sentence on fit or timing if relevant. Close cleanly. No trailing pleasantries.

FORMAT:
  - Date, then hiring manager name/title/company (use "Hiring Manager" if name unknown)
  - Salutation: "Dear [Name]," or "Dear Hiring Manager,"
  - Close: "Sincerely," or "Best regards,"
  - Match industry register: measured for finance/law; direct for tech; considered for mission-driven orgs
  - Banned phrases: "passionate about," "team player," "detail-oriented," "hard worker," "results-driven," "leverage," "synergy"
  - The letter must stand alone. Assume the reader has not seen the resume.
</cover_letter_rules>"""


def _build_generate_prompt(
    context_set: ContextSet,
    analysis: dict,
    refinement_notes: str = "",
    with_cover_letter: bool = True,
) -> tuple[str, type[BaseModel]]:
    """Build the generate-prompt + the matching response_model for the
    expected JSON output. Shared by `generate()` and `generate_streaming()`
    so the prompt template lives in one place. Returns (prompt, response_model).

    Mirrors `_analyze_prompt` — extracted 2026-05-26 to support the R2
    streaming path without duplicating ~80 lines of conditional prompt
    construction (clarifications block / cover-letter rules / corpus mode /
    refinement instructions / output schema).
    """
    # Build the optional candidate clarifications block. The clarify step is
    # opt-in — most contexts won't have these fields. When present, the answers
    # are first-person ground truth and may be cited as source material even
    # though they are not in the resume text. Skipped questions are simply absent
    # from the answers dict and omitted from the prompt.
    clarifications_block = ""
    answers = context_set.get("clarifications") or {}
    questions = context_set.get("clarification_questions") or []
    if answers and questions:
        cb_lines = [
            "<candidate_clarifications>",
            "The candidate answered the following clarifying questions after "
            "seeing the analysis. These answers are FIRST-PERSON GROUND TRUTH "
            "from the candidate. You MAY cite the experience and details they "
            "reveal even when those details are not present in the resume above "
            "— they are legitimate source material. You MUST NOT invent any "
            "specifics BEYOND what the candidate explicitly states.",
            "",
        ]
        for q in questions:
            qid = q.get("id", "")
            ans = answers.get(qid, "").strip()
            if not ans:
                continue
            kind = q.get("kind", "")
            cb_lines.append(f'<q id="{qid}" kind="{kind}">')
            cb_lines.append(f"Question: {q.get('text', '')}")
            cb_lines.append(f"Candidate answer: {ans}")
            cb_lines.append("</q>")
            cb_lines.append("")
        if any(answers.get(q.get("id", ""), "").strip() for q in questions):
            cb_lines.append("</candidate_clarifications>")
            clarifications_block = "\n".join(cb_lines) + "\n\n"

    cover_letter_rules_block = _COVER_LETTER_RULES_BLOCK if with_cover_letter else ""

    refinement_target = (
        "to both the resume and cover letter" if with_cover_letter
        else "to the resume"
    )

    cover_letter_schema_line = (
        '"cover_letter_content": "The complete cover letter as plain text",\n  '
        if with_cover_letter else ""
    )

    cover_draft, _ = _current_cover_letter_draft(context_set) if with_cover_letter else ("", "")
    cover_letter_draft_block = ""
    if cover_draft:
        cover_letter_draft_block = (
            "<current_cover_letter_draft>\n"
            "This is the prior iteration's cover letter (possibly with the "
            "candidate's first-person edits typed in). EVOLVE this draft rather "
            "than starting from scratch — preserve its voice and structure unless "
            "an explicit refinement instruction or cover_letter_rules constraint "
            "requires a change. Treat candidate-typed text in this draft as "
            "first-person ground truth subject to the GROUNDING CHECK below.\n"
            f"{cover_draft}\n"
            "</current_cover_letter_draft>\n\n"
        )

    in_corpus_mode = bool(context_set.get("career_corpus"))
    corpus_mode_block = ""
    extra_output_fields = ""
    if in_corpus_mode:
        corpus_mode_block = """<corpus_mode>
The candidate's experience pool is the <career_corpus> block above (not a free-text <resume>). Each <experience> carries:
- One or more <eligible_title> elements — the candidate has approved these framings. Pick the one that best matches THIS JD's positioning.
- One or more <bullet id="bN" ...> elements — VERBATIM text from the candidate's resumes. Treat each bullet as immutable ground truth: select, reorder, and reframe SURROUNDING context, but the bullet text itself MUST appear verbatim in your resume_content.

When an essential JD requirement is not covered by any existing bullet, you MAY propose a new bullet in `proposed_new_bullets` (see output schema below). The user reviews proposals before they join the canonical corpus.

When none of an experience's <eligible_title> elements fits the JD's framing, you MAY propose a new title in `proposed_experience_titles`. Same review semantics as proposed bullets.

A <bullet> marked `pinned="true"` was explicitly pinned by the user for this application. You MUST include every pinned bullet's id in `selected_bullets` (the user has decided it belongs). Bullets the user excluded are already removed from the corpus above.

GROUNDING for corpus mode:
  Every bullet you emit in resume_content must EITHER (a) reproduce a <bullet> text verbatim from the corpus (just record its `id` in selected_bullets), OR (b) be listed in proposed_new_bullets so the user knows it's a new claim. No other bullets are permitted. The legacy GROUNDING CHECK below still governs cover_letter_content and any reframing language between bullets.
</corpus_mode>

"""
        extra_output_fields = """,
  "selected_bullets": [
    {
      "experience_id": "e<int>",
      "chosen_title_id": "t<int>",
      "bullet_ids_in_order": ["b<int>", "b<int>", ...]
    }
  ],
  "proposed_new_bullets": [
    {
      "experience_id": "e<int>",
      "text": "Verbatim text the LLM is proposing as a new bullet",
      "pattern_kind": "xyz" | "car" | "manual",
      "rationale": "Why this fills a JD gap the existing bullets miss"
    }
  ],
  "proposed_experience_titles": [
    {
      "experience_id": "e<int>",
      "title": "New title framing",
      "rationale": "Why no eligible_title fits this JD"
    }
  ]"""

    prompt = f"""<task>Generate a tailored resume and cover letter for the candidate based on the analysis.</task>

<output_rules>
The `resume_content` field MUST use markdown heading markers. Without them the
document generator produces undifferentiated plain paragraphs and loses the
template's heading visual styles entirely. This applies even when the original
resume above uses ALL CAPS, bold-only, or any other plain-text heading convention
— convert those to the markers below in the output.

REQUIRED markers:
- `# ` exactly once, on the first non-empty line, for the candidate's full name.
- The 1–2 lines directly after the name (a title/subtitle and a contact line)
  are unmarked plain text. The renderer center-aligns them when the template
  has a centered header zone.
- `## ` for top-level section headings (Summary, Experience, Education, Skills,
  Certifications, Projects, etc.). One `##` per section.
- `### ` for company / role / job-title lines within the Experience section.
  When a date range applies, put it on the SAME line as the title separated
  by a single tab character `\t`. The renderer aligns the date to the right
  margin via the template's tab stop. Format:
  `### Company, Title\tStart – End`
- `-` (hyphen) at the start of every bullet point.
- `**text**` for inline bold; `*text*` for inline italic. Use sparingly.

Example of the required `resume_content` shape (note `\t` before the date):
```
# Jane Doe
Senior Site Reliability Engineer
jane@example.com | (555) 010-2200 | linkedin.com/in/janedoe

## Summary
Two-sentence positioning paragraph.

## Experience

### Acme Cloud, Senior SRE\tMarch 2023 – present
Player-coach across the platform team and on-call leadership.
- Bullet one with a verb up front.
- Bullet two integrating a JD keyword naturally.

### Stratford Analytics, Production Engineer\tAugust 2021 – March 2023
- Bullet one.
```

DO NOT skip the `# `, `## `, `### ` markers. DO NOT use ALL CAPS as a substitute
for `## `. The downstream Python writer dispatches on these markers to apply the
template's heading styles, list numbering, and bold runs — without them the
output is plain paragraphs.

CRITICAL — EMIT LITERAL NEWLINES BETWEEN EVERY LINE OF THE RESUME.
Inside the JSON string, every section heading, job entry, bullet, and the
contact line MUST be separated by `\n` (escaped JSON newline). If you
emit `# Name` followed immediately by `Subtitle` with no `\n` between,
the downstream renderer cannot tell the lines apart. Every example
shape above has line breaks; reproduce them exactly. A resume on one
long line is malformed output regardless of how complete the text is.
</output_rules>

<analysis>
Essential skills: {', '.join(analysis.get('essential_skills', []))}
Missing keywords: {json.dumps(analysis.get('keyword_placement', []))}
Suggestions: {json.dumps(analysis.get('suggestions', []))}
Strategy: {analysis.get('overall_strategy', '')}
Professional vocabulary: {', '.join(analysis.get('professional_vocabulary', []))}
</analysis>

{clarifications_block}{cover_letter_draft_block}{corpus_mode_block}<resume_rules>
GROUNDING CHECK — apply this before writing every bullet:
  Ask: "Does this specific claim — including every number, technology, title, company, and timeframe — trace to the resume above (the current draft, which may include first-person edits the candidate typed in), any historical or supplemental resume above, OR a candidate clarification answer above?"
  If YES: reframe, strengthen, and keyword-align it freely. Both clarification answers AND first-person typed edits in the current draft are ground truth and may be cited even when the original primary resume did not mention them.
  If NO: do not write it. Reframe what IS there, or omit the bullet.

  Worked examples — what to do and what NOT to do:
    Source bullet: "Built customer-facing dashboards for the analytics team."
    OK to write:   "Designed customer-facing analytics dashboards for the data team."
    NOT OK:        "Built time-series forecasting dashboards for executive stakeholders."
                   ← invents "time-series forecasting" (advanced technique not in source) and "executive stakeholders" (audience not in source).

    Source bullet: "Used a CI tool to automate test runs."
    OK to write:   "Automated test execution via continuous integration."
    NOT OK:        "Authored Jenkins pipelines for nightly regression suites."
                   ← invents "Jenkins" (vendor not in source) and "nightly regression" (cadence not in source).

    Source bullet: "Improved the team's reporting workflow."
    OK to write:   "Streamlined the team's reporting workflow."
    NOT OK:        "Led an organization-wide reporting transformation."
                   ← scope inflation: "team" became "organization-wide", "improved workflow" became "transformation".

    Candidate typed into the preview (first-person edit in current draft): "Shipped V2 to enterprise."
    OK to write:   "Shipped V2 to enterprise customers."
    NOT OK:        "Led V2 launch to 50 enterprise customers."
                   ← invents headcount the candidate did not type. First-person edits ARE ground truth, but never extend them with specifics the candidate did not state.

1. Include a targeted summary sentence answering: what title you seek, what makes you special, what you bring to the team. If it cannot fit in one sentence, use a sentence with a very short bullet list.
2. Do NOT invent experience. Every bullet must trace directly to the original resume. Reframe language; never invent facts.
3. Metrics: surface numbers that exist in the original. If a bullet has no metric, use qualitative scope and impact language — do not fabricate a number to fill the gap.
4. Prioritize keywords from the job description. Integrate them into existing bullets naturally; do not create new bullets to house keywords.
5. Reorder bullet points by relevance to THIS job — within each section, most relevant first.
6. Strengthen verb choices: replace weak or repeated verbs with strong, varied, industry-specific action verbs.
7. Preserve the original resume's section structure and ordering.
8. Ensure all content is ATS-compatible — no tables, columns, or special characters.
</resume_rules>
{cover_letter_rules_block}
{f'''
<refinement_instructions>
The user has reviewed the generated documents and provided the following adjustment instructions.
Apply ALL of the following {refinement_target}.
Earlier instructions remain in effect unless explicitly superseded by a later one.
Do NOT make any other changes beyond what is requested here.

{refinement_notes}
</refinement_instructions>
''' if refinement_notes.strip() else ''}
<output_format>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "resume_content": "The complete tailored resume. CRITICAL: use \\n (JSON newline escape) between every section, job entry, and bullet. Never collapse the resume into one long line. Example: '# Name\\nEmail | Phone\\n\\n## Summary\\nText.\\n\\n## Experience\\n\\n### Title — Company\\n- Bullet one\\n- Bullet two'",
  {cover_letter_schema_line}"changes_made": ["change1", "change2"],
  "proofread_notes": ["Any grammar, spelling, or formatting issues found and fixed"]{extra_output_fields}
}}
</output_format>"""

    if in_corpus_mode:
        model_cls: type[BaseModel] = (GenerateCorpusResponse if with_cover_letter
                    else GenerateCorpusNoCLResponse)
    else:
        model_cls = (GenerateResponse if with_cover_letter
                    else GenerateNoCLResponse)

    return prompt, model_cls


def generate(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict,
    refinement_notes: str = "",
    username: str = "",
    run_id: str = "",
    with_cover_letter: bool = True,
) -> dict:
    """Call 2: Generation.

    Produces tailored resume content and (optionally) a cover letter.
    Includes proofreading pass. The username is threaded through to JSONL
    telemetry only — no behavior depends on it. The run_id (when provided)
    lets dashboard tooling correlate this call's telemetry with its sibling
    analyze() call and any eval result that consumed the output.

    `with_cover_letter` (Phase β.5):
      Default True for backward compatibility with existing callers + the
      iteration loop. When False (e.g. the route layer's default for the
      common résumé-only path), the cover_letter_rules block is dropped
      from the prompt, the JSON schema does not include
      cover_letter_content, and the returned dict has cover_letter_content
      set to "" so downstream renderers that always touch the field don't
      KeyError. The user can call /api/generate-cover-letter later to
      produce a cover letter against the finalized résumé.

    When the context_set contains clarifications (set by /api/answer-clarifications
    after the optional interview step), they are injected into the prompt as
    first-person ground truth and the GROUNDING CHECK is widened to accept
    them as legitimate source material.

    Iteration-aware behavior (iteration >= 1):
      - The <resume> block in the cached prefix already shows the current
        draft (edited > last_generated) via _current_draft_text. Originals
        live under <historical_resumes>.
      - A <current_cover_letter_draft> block is inserted so the LLM evolves
        the prior cover letter rather than starting fresh. (Skipped when
        with_cover_letter is False.)
      - Grounding wording widens to acknowledge first-person typed edits as
        legitimate source material (mirrors the clarification carve-out).
    """
    prompt, model_cls = _build_generate_prompt(
        context_set, analysis,
        refinement_notes=refinement_notes,
        with_cover_letter=with_cover_letter,
    )
    result = _parse_or_retry(
        client, prompt,
        cached_user_prefix=_stable_user_prefix(context_set),
        response_model=model_cls,
        call_kind="generate",
        username=username,
        run_id=run_id,
    )
    if not with_cover_letter:
        result.setdefault("cover_letter_content", "")
    return result


def generate_streaming(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict,
    refinement_notes: str = "",
    username: str = "",
    run_id: str = "",
    with_cover_letter: bool = True,
) -> Iterator[tuple[str, object]]:
    """Streaming generator counterpart to `generate()`.

    Yields the same event shape as `_parse_or_retry_streaming`:
        - `("chunk", str)` per text delta
        - `("retry", str)` if a parse attempt fails and a retry begins
        - `("done", dict)` on success with the parsed generation result.
          When `with_cover_letter` is False the dict carries an empty
          `cover_letter_content` so downstream renderers don't KeyError —
          same shape as the non-streaming `generate()` return.

    Routes that want token-level SSE call this generator and forward
    each event as a Server-Sent Event. Existing non-streaming callers
    keep using `generate()`.
    """
    prompt, model_cls = _build_generate_prompt(
        context_set, analysis,
        refinement_notes=refinement_notes,
        with_cover_letter=with_cover_letter,
    )
    for event in _parse_or_retry_streaming(
        client, prompt,
        cached_user_prefix=_stable_user_prefix(context_set),
        response_model=model_cls,
        call_kind="generate",
        username=username,
        run_id=run_id,
    ):
        kind, payload = event
        if kind == "done" and not with_cover_letter and isinstance(payload, dict):
            # Mirror generate()'s post-parse setdefault so callers that
            # always touch cover_letter_content don't KeyError.
            payload.setdefault("cover_letter_content", "")
            yield ("done", payload)
        else:
            yield event




# β.5 — required keys for the focused cover-letter-only call below.
COVER_LETTER_ONLY_REQUIRED_KEYS = frozenset({
    "cover_letter_content", "proofread_notes",
})


def generate_cover_letter_against_resume(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    analysis: dict,
    resume_content: str,
    refinement_notes: str = "",
    username: str = "",
    run_id: str = "",
) -> dict:
    """Phase β.5 — focused cover-letter call against a finalized résumé.

    Used by /api/generate-cover-letter after the user has run a résumé
    generation and (optionally) iterated on it. Produces ONLY a cover
    letter — no résumé regeneration, no token cost for résumé rules. The
    finalized résumé is provided as input context so the letter can echo
    its concrete numbers + framing.

    Returns a dict with at least `cover_letter_content` (string) and
    `proofread_notes` (list). The shape mirrors generate()'s return so
    downstream code (the iteration loop, refine flow, edit-detect modal)
    sees the same fields. `resume_content` is NOT in the response — the
    caller passes the existing finalized résumé through unchanged.

    The same clarifications + iteration-aware draft block + grounding-
    widening that generate() uses are applied here so a cover letter
    iterated multiple times stays consistent with the candidate's
    typed-in edits and clarification answers.
    """
    # Reuse the clarifications + iteration draft block construction
    # from generate(). These are pure functions of context_set so we
    # can build them inline here without duplicating logic.
    clarifications_block = ""
    answers = context_set.get("clarifications") or {}
    questions = context_set.get("clarification_questions") or []
    if answers and questions:
        cb_lines = [
            "<candidate_clarifications>",
            "First-person ground truth from the candidate. You MAY cite "
            "the experience and details they reveal even when those details "
            "are not in the résumé. You MUST NOT invent specifics BEYOND "
            "what the candidate explicitly states.",
            "",
        ]
        for q in questions:
            qid = q.get("id", "")
            ans = answers.get(qid, "").strip()
            if not ans:
                continue
            kind = q.get("kind", "")
            cb_lines.append(f'<q id="{qid}" kind="{kind}">')
            cb_lines.append(f"Question: {q.get('text', '')}")
            cb_lines.append(f"Candidate answer: {ans}")
            cb_lines.append("</q>")
            cb_lines.append("")
        if any(answers.get(q.get("id", ""), "").strip() for q in questions):
            cb_lines.append("</candidate_clarifications>")
            clarifications_block = "\n".join(cb_lines) + "\n\n"

    cover_draft, _ = _current_cover_letter_draft(context_set)
    cover_letter_draft_block = ""
    if cover_draft:
        cover_letter_draft_block = (
            "<current_cover_letter_draft>\n"
            "This is the prior iteration's cover letter (possibly with the "
            "candidate's first-person edits typed in). EVOLVE this draft "
            "rather than starting from scratch — preserve its voice and "
            "structure unless an explicit refinement instruction requires "
            "a change. Treat candidate-typed text as first-person ground "
            "truth.\n\n"
            f"{cover_draft}\n"
            "</current_cover_letter_draft>\n\n"
        )

    # The canonical key in ContextSet is `job_description` (defined in
    # hardening.py and populated by build_context_set). The pre-fix code
    # read `jd_text`, which is the name of the function parameter that
    # POPULATES `job_description` — not the field name on the context.
    # Symptom of the bug: cover-letter LLM received an empty <jd>
    # block, produced generic / off-target prose, and surfaced as a UI-
    # facing "no job description was attached to this request" complaint.
    jd_excerpt = (context_set.get("job_description") or "")
    if isinstance(jd_excerpt, str):
        jd_excerpt = jd_excerpt[:6000]

    prompt = f"""<task>Write a tailored cover letter for the candidate based on the finalized résumé and JD.</task>

{clarifications_block}{cover_letter_draft_block}<finalized_resume>
{resume_content}
</finalized_resume>

<jd>
{jd_excerpt}
</jd>

<analysis>
Essential skills: {', '.join(analysis.get('essential_skills', []))}
Strategy: {analysis.get('overall_strategy', '')}
Professional vocabulary: {', '.join(analysis.get('professional_vocabulary', []))}
</analysis>

{_COVER_LETTER_RULES_BLOCK}
{f'''
<refinement_instructions>
The user has reviewed the cover letter and provided the following adjustment instructions.
Apply ALL of the following to the cover letter.
Earlier instructions remain in effect unless explicitly superseded by a later one.
Do NOT make any other changes beyond what is requested here.

{refinement_notes}
</refinement_instructions>
''' if refinement_notes.strip() else ''}
<output_format>
Respond with valid JSON only. No markdown code fences. Use this exact structure:
{{
  "cover_letter_content": "The complete cover letter as plain text",
  "proofread_notes": ["Any grammar, spelling, or formatting issues found and fixed"]
}}
</output_format>"""

    return _parse_or_retry(
        client, prompt,
        cached_user_prefix="",  # focused one-shot; cache benefit is small
        response_model=CoverLetterOnlyResponse,
        call_kind="generate_cover_letter",
        username=username,
        run_id=run_id,
    )


SCOPE_CHECK_MODEL = "claude-haiku-4-5-20251001"


def check_refinement_scope(client: anthropic.Anthropic, note: str) -> dict:
    """Classify whether a refinement note is within allowed document-editing scope.

    Uses Haiku — binary classification doesn't need Sonnet reasoning depth.
    Fails open (valid=True) if the response can't be parsed, so a model outage
    never blocks the user from refining.

    Allowed: tone, emphasis, keyword/phrasing, ordering existing content,
             formatting, structural adjustments within source material.
    Out of scope: inventing experience, changing factual data, adding credentials
                  not in source, repurposing for a different role.
    """
    prompt = f"""A user submitted the following instruction for refining their resume and cover letter:

<note>{note}</note>

Allowed scope: adjustments to tone, emphasis, keyword placement, phrasing, language style, \
ordering/prioritizing existing content, and formatting preferences.

Out of scope: inventing new experience or accomplishments, changing factual data \
(dates, titles, companies, metrics), adding skills or certifications not present in the \
source material, or repurposing the documents for a fundamentally different role.

Respond with valid JSON only — no markdown, no explanation outside the JSON:
{{"valid": true}} if the note is within scope, or
{{"valid": false, "reason": "one sentence explaining what specifically is not allowed"}} if not."""

    try:
        msg = client.messages.create(
            model=SCOPE_CHECK_MODEL,
            max_tokens=128,
            system="You are a strict scope classifier. Respond with JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        raw = getattr(msg.content[0], "text", "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())
    except Exception as e:
        # Fail open — scope check failure must never block refinement
        logger.warning("scope check failed, failing open: %s", e)
        return {"valid": True}


# ---------------------------------------------------------------------------
# Phase B.4: critique LLM-proposed bullets/titles + promote clarifications
# ---------------------------------------------------------------------------

# Required keys for the critique response. `concerns` may be an empty list when
# the critique is clean, but the field must be present.
CRITIQUE_REQUIRED_KEYS = frozenset({"verdict", "notes", "concerns"})

# Critique persona — short, sharp, fabrication-focused. Inspired by the
# SYSTEM_PROMPT ALWAYS/NEVER rules but specialized for proposal review.
PROPOSAL_CRITIQUE_SYSTEM_PROMPT = """You are a rigorous reviewer evaluating LLM-proposed resume bullets and titles for fabrication risk. You read the original LLM proposal, any user edit, the candidate's source experience (company, official title, existing canonical bullets), the candidate's first-person clarifications, and the JD that triggered the proposal. Your job is to spot fabrication, scope inflation, and grounding drift.

Output JSON only — no markdown fences, no commentary. Required keys:
{
  "verdict": "good" | "caution" | "risky",
  "notes": "one to two sentences summarizing your judgment",
  "concerns": ["specific concern 1", "specific concern 2", ...],
  "suggested_revisions": ["alternative phrasing 1", ...]   // optional, may be []
}

VERDICT RULES (load-bearing — anti-rubber-stamping):
- "good" is reserved for proposals that genuinely preserve grounding. To use "good", `concerns` MUST be empty AND `notes` MUST explicitly state what specifically traces to source ("preserves the 800-unit fleet metric from the Acme bullet" / "no fabricated specifics; verb downgraded from 'Owned' to 'Contributed to' matches source"). Vague "looks good" is a "caution".
- "caution" when there are concerns the user should weigh but no outright fabrication.
- "risky" when the text invents specifics, escalates scope, contradicts clarifications, or claims experience the candidate's corpus doesn't support.

CHECK FOR (and cite specifically in concerns):
1. **Fabricated specifics** — numbers, tech names, vendor names, customer segments, dollar amounts, team sizes not in the source experience or clarifications.
2. **Scope inflation** — "team" → "organization", "project" → "company-wide initiative", "two engineers" → "engineering org".
3. **Domain drift** — adding industry experience the candidate doesn't have (healthcare claim with no healthcare corpus, EHR familiarity with no clinical clarification, etc.).
4. **Title elevation** — claiming seniority beyond the candidate's official title or clarified scope.
5. **Verb overreach** — "Owned" / "Led" / "Drove" when source says "Contributed" / "Supported" / "Helped".

When a concern fires, NAME the specific claim ("the '800-unit fleet' phrase appears in source bullet b41 — OK", or "'24 clinicians interviewed' has no source — fabricated specific").

Be brief. 1-3 concerns is plenty per critique."""


def critique_proposal(
    client: anthropic.Anthropic,
    *,
    original_text: str,
    user_edited_text: str | None,
    subject_kind: str,  # "bullet" or "experience_title"
    experience_context: dict,
    clarifications: list[tuple[str, str]] | None = None,
    jd_excerpt: str = "",
    username: str = "",
    run_id: str = "",
) -> dict:
    """Critique a user edit to an LLM-proposed bullet or title.

    Uses Haiku — proposal critique is structured rubric application, not
    reasoning-depth work. Output schema validated via `_parse_or_retry` with
    CRITIQUE_REQUIRED_KEYS. Returns the critique dict unchanged for the caller
    to persist on `proposal_review.llm_critique_json`.

    `experience_context` should carry: company, location, start_date,
    end_date, official_title, and a list of existing bullet texts. The
    critique uses these as the grounding pool. `clarifications` is a list of
    (question, answer) tuples — first-person ground truth.

    `subject_kind` toggles minor wording in the prompt so a title critique
    doesn't read like a bullet critique.
    """
    edit_block = (
        f"The user edited the proposal to:\n  {user_edited_text}"
        if user_edited_text and user_edited_text.strip() != original_text.strip()
        else "The user has not edited the proposal; they are considering accepting it as-is."
    )

    company = experience_context.get("company", "(unknown)")
    official_title = experience_context.get("official_title", "(unknown)")
    dates = (
        f"{experience_context.get('start_date', '?')} → "
        f"{experience_context.get('end_date') or 'present'}"
    )
    location = experience_context.get("location", "")
    canonical_bullets = experience_context.get("existing_bullets", []) or []
    bullets_block = "\n".join(f"  - {b}" for b in canonical_bullets[:20])
    if not bullets_block:
        bullets_block = "  (no existing canonical bullets for this experience)"

    clar_lines = []
    for q, a in (clarifications or [])[:30]:
        clar_lines.append(f"  Q: {q}\n  A: {a}")
    clar_block = "\n\n".join(clar_lines) if clar_lines else "  (no relevant candidate clarifications)"

    jd_block = jd_excerpt.strip() or "(no JD excerpt provided)"

    user_prompt = f"""<task>Critique this LLM-proposed {subject_kind} for fabrication risk against the candidate's source. Output JSON only.</task>

<original_proposal>
{original_text}
</original_proposal>

<user_action>
{edit_block}
</user_action>

<experience_context>
Company: {company}
Official title: {official_title}
Dates: {dates}
{f"Location: {location}" if location else ""}

Existing canonical bullets for this experience:
{bullets_block}
</experience_context>

<candidate_clarifications>
{clar_block}
</candidate_clarifications>

<jd_excerpt>
{jd_block}
</jd_excerpt>"""

    return _parse_or_retry(
        client,
        user_prompt,
        cached_user_prefix="",  # one-shot, no caching benefit
        response_model=CritiqueResponse,
        call_kind="critique_proposal",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("PROPOSAL_CRITIQUE_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    )


# ---------------------------------------------------------------------------
# Workstream H: per-application bullet recommendations (the "Compose" view)
# ---------------------------------------------------------------------------


RECOMMEND_SYSTEM_PROMPT = """You are helping a candidate curate a tailored resume for ONE specific job. The candidate's full bullet corpus is given as <career_corpus> XML; the job is given as <jd>. You see the analyst's prior breakdown of the JD in <analysis> when present.

Your one task: for EACH experience in the corpus, pick 3-7 bullets that best fit THIS JD. Optimize for: relevance to JD requirements, variety (don't pick three bullets that say the same thing), measurable outcomes when present, and recency where signal-equivalent.

NEVER invent bullets. NEVER reword bullets — return only ids from the corpus. If an experience has fewer than 3 strong fits, return as few as you genuinely recommend (down to 1); don't pad.

**Quality over quantity.** The 3-7 range is a soft ceiling, not a target. Stop including bullets the moment the next-best pick would be a clear step down from your previous one. If 4 bullets are obviously strong and the 5th would be middling, return 4. If only 3 clear the bar, return 3. Adding bullet #6 only makes sense if it would noticeably strengthen the résumé over not adding it. A short list of clearly-strong bullets always beats a long list with weak tail picks — recruiters skim, so every bullet present must earn its place.

**No near-duplicates.** The corpus often contains multiple phrasings of the same achievement (different resumes wrote the same accomplishment differently). NEVER select more than one bullet describing the same achievement. When two bullets read as near-restatements of each other, pick the single strongest phrasing (prefer the one with measurable outcomes, then the more specific verb set) and skip the rest. A safety pass downstream removes any leaked duplicates, but you should not produce them in the first place.

Output JSON only, this exact shape:
{
  "recommendations": [
    {
      "experience_id": <int>,
      "bullet_ids": [<int>, <int>, ...],
      "rationale": "one-sentence reason these bullets fit this JD"
    },
    ...
  ]
}

Skip experiences whose bullets don't fit at all (omit them from the array entirely; don't return empty bullet_ids). Use the numeric ids only — do NOT prefix with "b" or "e"."""


def recommend_bullets(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    *,
    username: str = "",
    run_id: str = "",
) -> dict:
    """Pick the 3-7 most-relevant bullets per experience for this JD.

    Haiku call — structured selection, not reasoning-depth work. Fires
    automatically after `analyze()` succeeds so the Compose UI can render
    a curated set as the default. Returns the parsed dict; the caller
    persists it on `context_set["llm_recommendations"]`.

    Caller must populate `context_set` with a corpus-mode payload
    (`career_corpus` + `llm_analysis` after analyze). Falls back to
    raising the same LLMResponseError as the other calls when the model
    output can't be parsed after a retry.
    """
    corpus = context_set.get("career_corpus") or []
    if not corpus:
        # No corpus means nothing to recommend — return an empty payload
        # so callers can persist a benign value and the UI falls back to
        # deterministic ordering.
        return {"recommendations": []}

    corpus_block = _corpus_block(list(corpus), iteration=0)
    # The JD lives on the application row; the route stashes it on the
    # context as `jd_text` before calling us. Coerce to str so mypy is
    # happy even though the field isn't in the ContextSet TypedDict.
    jd_value = context_set.get("jd_text", "")
    jd_str = (str(jd_value) if jd_value else "").strip() or "(JD text unavailable in context)"
    analysis = context_set.get("llm_analysis") or {}

    essential = ", ".join(analysis.get("essential_skills", []) or [])
    preferred = ", ".join(analysis.get("preferred_skills", []) or [])
    keywords = ", ".join(analysis.get("industry_keywords", []) or [])

    user_prompt = f"""<task>Pick 3-7 best-fit bullet ids per experience for this JD. Output JSON only.</task>

{corpus_block}

<jd>
{jd_str}
</jd>

<analysis>
Essential skills the JD names: {essential or '(none surfaced)'}
Preferred skills: {preferred or '(none)'}
Industry keywords: {keywords or '(none)'}
</analysis>"""

    result = _parse_or_retry(
        client,
        user_prompt,
        cached_user_prefix="",  # one-shot per application; cache benefit is small
        response_model=RecommendResponse,
        call_kind="recommend",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("RECOMMEND_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    )
    # Workstream B1.2 safety pass: even with the explicit prompt rule, the
    # LLM occasionally returns two near-restatements of the same achievement
    # in one experience's bullet_ids. Drop them deterministically (Jaccard
    # ≥ 0.75 on bullet text), preferring outcome-bearing bullets and
    # preserving original order otherwise.
    _dedup_recommendations(result, corpus)
    return result


def _dedup_recommendations(result: dict, corpus: list[CorpusExperience]) -> None:
    """Mutate result['recommendations'][i]['bullet_ids'] in place to drop
    near-duplicate bullet ids per experience. Same-experience scope only —
    two experiences referring to the same achievement is rare but legal."""
    from hardening import bullet_jaccard
    text_by_id: dict[int, str] = {}
    has_outcome_by_id: dict[int, bool] = {}
    for exp in corpus or []:
        for b in exp.get("bullets", []) or []:
            try:
                bid = int(b.get("id"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            text_by_id[bid] = b.get("text", "") or ""
            has_outcome_by_id[bid] = bool(b.get("has_outcome"))
    for rec in result.get("recommendations", []) or []:
        ids = [int(x) for x in (rec.get("bullet_ids") or [])]
        kept: list[int] = []
        for bid in ids:
            text = text_by_id.get(bid, "")
            dropped = False
            for i, k in enumerate(kept):
                if bullet_jaccard(text, text_by_id.get(k, "")) >= 0.75:
                    # Prefer the outcome-bearing bullet between the two.
                    if has_outcome_by_id.get(bid) and not has_outcome_by_id.get(k):
                        kept[i] = bid
                    dropped = True
                    break
            if not dropped:
                kept.append(bid)
        rec["bullet_ids"] = kept


# ---------------------------------------------------------------------------
# β.6b — recommend the best positioning summary variant per JD.
# Mirrors recommend_bullets's pattern: Haiku call, no-near-duplicates
# rule, deterministic Jaccard dedup safety pass. The candidate has
# multiple SummaryItem variants ("AI platform PM", "early-stage
# builder PM", etc.); this pick chooses one + optional alternates.
# ---------------------------------------------------------------------------


RECOMMEND_SUMMARIES_SYSTEM_PROMPT = """You are helping a candidate pick the strongest positioning summary for ONE specific job. The candidate's available summary variants are given as <summary_items> XML; the job is given as <jd>. You see the analyst's JD breakdown in <analysis> when present.

Your one task: pick the SINGLE best-fit summary variant for THIS JD, and (optionally) name 1-2 alternates worth surfacing to the user. Optimize for: relevance to JD requirements, framing alignment (the JD's primary domain language), measurable outcomes when the variant includes them, and tone match (the JD's seniority + industry register).

**No near-duplicates.** The candidate's variant set sometimes contains near-restatements of the same positioning. NEVER surface two near-restatements (the primary recommendation + an alternate that is essentially the same text). When two variants read alike, pick the single strongest phrasing and skip the rest. A safety pass downstream removes leaked duplicates, but you should not produce them in the first place.

**Quality over quantity.** Only name alternates that are genuinely different positionings the user might prefer. If the chosen recommendation is obviously the only fit, return alternates as []. Do not pad.

NEVER invent summaries. NEVER reword variants — return only ids from the <summary_items> block.

Output JSON only, this exact shape:
{
  "recommendation": {
    "summary_item_id": <int>,
    "rationale": "one-sentence reason this positioning fits this JD"
  },
  "alternates": [
    {
      "summary_item_id": <int>,
      "rationale": "one-sentence reason this variant is also worth considering"
    },
    ...
  ]
}

If the candidate has zero summary variants in <summary_items>, return:
{"recommendation": null, "alternates": []}

Use the numeric ids only — do NOT prefix with "s"."""


def recommend_summaries(
    client: anthropic.Anthropic,
    context_set: ContextSet,
    *,
    username: str = "",
    run_id: str = "",
) -> dict:
    """β.6b — pick the best SummaryItem variant for this JD.

    Haiku call, mirroring recommend_bullets. Caller stages the active
    SummaryItem variants on `context_set["summary_items"]` as a list
    of {id, text, label, has_outcome} dicts before calling. Returns:

        {
          "recommendation": {"summary_item_id": int, "rationale": str} | None,
          "alternates":     [{"summary_item_id": int, "rationale": str}, ...],
        }

    Short-circuits without an LLM call when the candidate has zero or
    one variants (no decision to make + saves the token cost).
    `recommendation` is None when there are zero variants; the single
    variant otherwise. Alternates is always [].
    """
    # context_set is a TypedDict; `summary_items` is a transient key the
    # route stashes, so it's typed as object. Coerce defensively.
    items_raw = context_set.get("summary_items") or []
    items: list[dict] = list(items_raw) if isinstance(items_raw, list) else []
    items = [it for it in items if (it.get("text") or "").strip()]  # ignore blank rows

    # Short-circuit — no LLM needed when the answer is trivial
    if len(items) == 0:
        return {"recommendation": None, "alternates": []}
    if len(items) == 1:
        only = items[0]
        return {
            "recommendation": {
                "summary_item_id": int(only.get("id", 0)),
                "rationale": "Only variant available — no alternates to weigh.",
            },
            "alternates": [],
        }

    items_block = _summary_items_block(items)
    jd_value = context_set.get("jd_text", "")
    jd_str = (str(jd_value) if jd_value else "").strip() or "(JD text unavailable in context)"
    analysis = context_set.get("llm_analysis") or {}
    essential = ", ".join(analysis.get("essential_skills", []) or [])
    preferred = ", ".join(analysis.get("preferred_skills", []) or [])
    keywords = ", ".join(analysis.get("industry_keywords", []) or [])

    user_prompt = f"""<task>Pick the single best-fit summary variant id for this JD (with optional alternates). Output JSON only.</task>

{items_block}

<jd>
{jd_str}
</jd>

<analysis>
Essential skills the JD names: {essential or '(none surfaced)'}
Preferred skills: {preferred or '(none)'}
Industry keywords: {keywords or '(none)'}
</analysis>"""

    result = _parse_or_retry(
        client,
        user_prompt,
        cached_user_prefix="",  # one-shot per application
        response_model=RecommendSummariesResponse,
        call_kind="recommend_summary",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("RECOMMEND_SUMMARIES_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    )
    # Ensure the alternates key exists even when the LLM omits it
    result.setdefault("alternates", [])
    # β.6b safety pass: drop alternates that are near-restatements of
    # the recommendation or of each other. Same Jaccard ≥ 0.75 threshold
    # as _dedup_recommendations on bullets.
    _dedup_summary_recommendations(result, items)
    return result


def _summary_items_block(items: list[dict]) -> str:
    """XML-format the candidate's SummaryItem variants for the prompt.
    Mirrors `_corpus_block`'s shape conventions: numeric ids only, no
    free-form metadata that the LLM might echo back into a bullet."""
    from xml.sax.saxutils import escape

    lines = ["<summary_items>"]
    for it in items:
        try:
            sid = int(it.get("id", 0))
        except (TypeError, ValueError):
            continue
        text = (it.get("text") or "").strip()
        if not text:
            continue
        label = (it.get("label") or "").strip()
        has_outcome = bool(it.get("has_outcome"))
        attrs = f'id="{sid}"'
        if label:
            attrs += f' label="{escape(label)}"'
        if has_outcome:
            attrs += ' has_outcome="true"'
        lines.append(f"  <summary_item {attrs}>{escape(text)}</summary_item>")
    lines.append("</summary_items>")
    return "\n".join(lines)


def _dedup_summary_recommendations(result: dict, items: list[dict]) -> None:
    """Mutate result['alternates'] in place to drop entries that are
    near-restatements of the recommendation (or of each other). Jaccard
    ≥ 0.75 on the variant text, same threshold as bullets.

    The recommendation itself is preserved — the LLM's top pick is the
    user's primary surface and we don't touch it. Only alternates get
    trimmed."""
    from hardening import bullet_jaccard

    text_by_id: dict[int, str] = {}
    for it in items or []:
        try:
            sid = int(it.get("id", 0))
        except (TypeError, ValueError):
            continue
        text_by_id[sid] = (it.get("text") or "").strip()

    rec = result.get("recommendation") or {}
    rec_id_raw = rec.get("summary_item_id")
    try:
        rec_id = int(rec_id_raw) if rec_id_raw is not None else None
    except (TypeError, ValueError):
        rec_id = None
    rec_text = text_by_id.get(rec_id, "") if rec_id is not None else ""

    kept: list[dict] = []
    kept_texts: list[str] = [rec_text] if rec_text else []
    for alt in result.get("alternates", []) or []:
        try:
            sid = int(alt.get("summary_item_id", 0))
        except (TypeError, ValueError):
            continue
        if sid == rec_id:
            continue  # never surface the primary pick as its own alternate
        text = text_by_id.get(sid, "")
        if not text:
            continue
        is_dup = any(
            bullet_jaccard(text, k) >= 0.75 for k in kept_texts
        )
        if is_dup:
            continue
        kept.append(alt)
        kept_texts.append(text)
    result["alternates"] = kept


# ---------------------------------------------------------------------------
# Phase B.4: promote a clarification Q&A into a bullet candidate
# ---------------------------------------------------------------------------


PROMOTE_BULLET_REQUIRED_KEYS = frozenset({"text", "pattern_kind"})

PROMOTE_CLARIFICATION_SYSTEM_PROMPT = """You convert a candidate's clarification Q&A pair into a single resume bullet candidate. The bullet must:

- Be written in past-tense or active voice (the resume voice), not Q&A voice.
- Start with a strong action verb (Led / Built / Owned / Designed / etc. — NOT "Responsible for" / "Helped with").
- Preserve every concrete specific (numbers, technologies, scope, durations) the candidate stated, VERBATIM. Do NOT invent specifics.
- Stay under 35 words.
- Follow one of these patterns (per docs/bullet_patterns.md):
  - "xyz" — Accomplished X as measured by Y by doing Z. Use when a measurable outcome is in the answer.
  - "car" — Challenge / Action / Result. Use when context matters.
  - "manual" — generic past-tense action; use when the answer is short and qualitative.

The user reviews and edits before this becomes canonical. Your job is to give them a strong starting draft, not a final bullet.

Output JSON only — no markdown fences:
{
  "text": "the proposed bullet text",
  "pattern_kind": "xyz" | "car" | "manual",
  "rationale": "one sentence explaining the framing choice"
}"""


def promote_clarification_to_bullet(
    client: anthropic.Anthropic,
    *,
    question: str,
    answer: str,
    target_company: str = "",
    target_official_title: str = "",
    username: str = "",
    run_id: str = "",
) -> dict:
    """Convert a clarification Q&A into a proposed bullet candidate.

    Returns a dict with `text`, `pattern_kind`, and `rationale`. The caller
    inserts the bullet (with `is_pending_review=1, source='clarification:<id>'`)
    and creates a `proposal_review` row keyed to it so the critique loop can
    examine the result.
    """
    target_block = ""
    if target_company or target_official_title:
        target_block = (
            "<target_experience>\n"
            f"Company: {target_company or '(unspecified)'}\n"
            f"Official title: {target_official_title or '(unspecified)'}\n"
            "</target_experience>\n\n"
        )

    user_prompt = f"""<task>Convert the clarification answer into a proposed resume bullet.</task>

{target_block}<clarification>
Question: {question}
Answer: {answer}
</clarification>"""

    return _parse_or_retry(
        client,
        user_prompt,
        cached_user_prefix="",
        response_model=PromoteBulletResponse,
        call_kind="promote_clarification_to_bullet",
        username=username,
        run_id=run_id,
        system_prompt=_resolve_system_prompt("PROMOTE_CLARIFICATION_SYSTEM_PROMPT"),
        model=HAIKU_MODEL,
    )


# --- Prompt-override registry + resolver (see prompt_overrides() above) -------
# Maps each overridable persona-constant name to its baseline value. Defined at
# module end, after every constant exists. _resolve_system_prompt() is called at
# each LLM call site (and in _call_llm_streaming's SYSTEM_PROMPT fallback); with
# no active override it returns the identical constant object, so the bytes sent
# to the API are unchanged. Keep this in sync if a new overridable persona
# constant is added.
_BASE_SYSTEM_PROMPTS: dict[str, str] = {
    "SYSTEM_PROMPT": SYSTEM_PROMPT,
    "EXTRACTION_SYSTEM_PROMPT": EXTRACTION_SYSTEM_PROMPT,
    "CLARIFY_SYSTEM_PROMPT": CLARIFY_SYSTEM_PROMPT,
    "CLARIFY_ITERATION_SYSTEM_PROMPT": CLARIFY_ITERATION_SYSTEM_PROMPT,
    "PROPOSAL_CRITIQUE_SYSTEM_PROMPT": PROPOSAL_CRITIQUE_SYSTEM_PROMPT,
    "RECOMMEND_SYSTEM_PROMPT": RECOMMEND_SYSTEM_PROMPT,
    "RECOMMEND_SUMMARIES_SYSTEM_PROMPT": RECOMMEND_SUMMARIES_SYSTEM_PROMPT,
    "PROMOTE_CLARIFICATION_SYSTEM_PROMPT": PROMOTE_CLARIFICATION_SYSTEM_PROMPT,
}


def _resolve_system_prompt(name: str) -> str:
    """Return the active text for a persona-constant `name`: the candidate
    override when one is in scope, else the baseline constant (the identical
    object -> default-path byte-identity). `name` must be a registry key.
    """
    return (_prompt_overrides.get() or {}).get(name, _BASE_SYSTEM_PROMPTS[name])
