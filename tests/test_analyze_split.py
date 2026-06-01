"""Tests for the two-pass analyze split (r1/analyze-split-retry).

`analyze()` = Haiku extraction → Sonnet synthesis → merge into the existing
AnalyzeResponse contract. `analyze_streaming()` re-introduces the
`("phase", {...})` sentinel. The extraction pass enforces the typed
HiddenQualityItem shape at parse time (the guardrail against the original
clarification_quality regression).

No real LLM calls — `_call_llm` / `_call_llm_streaming` are monkeypatched at the
analyzer boundary, mirroring the pattern in test_analyzer.py.
"""

import json

import analyzer
from analyzer import (
    ANALYZE_REQUIRED_KEYS,
    EXTRACTION_SYSTEM_PROMPT,
    HAIKU_MODEL,
    SONNET_MODEL,
    _StreamDone,
)

# A minimal context_set carrying just the deterministic_analysis the prompt
# builders read. _stable_user_prefix is stubbed per-test so we don't need the
# full corpus/résumé shape.
_CONTEXT = {
    "deterministic_analysis": {
        "keyword_overlap": {
            "match_score": 0.5,
            "matched": ["docker"],
            "missing_from_resume": ["kubernetes"],
        },
        "ats_warnings": [],
    },
}


def _extraction_json(hidden_qualities=None) -> str:
    if hidden_qualities is None:
        hidden_qualities = [
            {"category": "operating_context", "signal": "regulated, workflow-heavy environments"}
        ]
    return json.dumps({
        "essential_skills": ["kubernetes"],
        "preferred_skills": ["terraform"],
        "industry_keywords": ["sre"],
        "hidden_qualities": hidden_qualities,
        "professional_vocabulary": ["slo"],
        "keyword_placement": [
            {"keyword": "kubernetes", "suggested_location": "Experience", "how": "..."}
        ],
    })


def _synthesis_json() -> str:
    return json.dumps({
        "comparison": {"strengths": [], "gaps": ["No K8s"], "title_alignment": "ok"},
        "suggestions": [{"section": "Skills", "action": "add k8s", "rationale": "gap"}],
        "overall_strategy": "Position as a platform SRE.",
    })


# ---------- analyze() — two-pass orchestration -----------------------------

def test_analyze_runs_extraction_then_synthesis_and_merges(monkeypatch):
    monkeypatch.setattr(analyzer, "_stable_user_prefix", lambda cs: "PREFIX")
    calls: list[dict] = []
    responses = [_extraction_json(), _synthesis_json()]

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id,
             system_prompt="", model=None, **kwargs):
        calls.append({
            "call_kind": call_kind, "system_prompt": system_prompt,
            "model": model, "cached_user_prefix": cached_user_prefix,
        })
        return responses.pop(0)

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = analyzer.analyze(client=None, context_set=_CONTEXT, username="u", run_id="r")

    # Two passes, in order, with the right persona + model each.
    assert [c["call_kind"] for c in calls] == ["analyze_extraction", "analyze_synthesis"]
    assert calls[0]["system_prompt"] == EXTRACTION_SYSTEM_PROMPT
    assert calls[0]["model"] == HAIKU_MODEL
    # Synthesis does NOT override the system prompt — it runs under the default
    # SYSTEM_PROMPT so its cached prefix matches generate()'s (cache reclaim).
    assert calls[1]["system_prompt"] == ""
    assert calls[1]["model"] in (None, SONNET_MODEL)  # synthesis defaults to Sonnet
    # Both passes share one byte-identical cached prefix (cache chain into generate()).
    assert calls[0]["cached_user_prefix"] == calls[1]["cached_user_prefix"] == "PREFIX"

    # Merged result satisfies the (post-phantom-drop) contract.
    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert "ats_improvements" not in result
    assert "ideal_resume_profile" not in result
    assert result["overall_strategy"] == "Position as a platform SRE."
    assert result["hidden_qualities"][0]["category"] == "operating_context"
    assert result["essential_skills"] == ["kubernetes"]


def test_extraction_bare_string_hidden_quality_triggers_retry(monkeypatch):
    """A legacy bare-string hidden_qualities item fails AnalyzeExtractionResponse
    validation → _parse_or_retry retries the extraction pass with the structured
    error. This is the guardrail carried onto the Haiku extraction."""
    monkeypatch.setattr(analyzer, "_stable_user_prefix", lambda cs: "PREFIX")
    calls: list[str] = []
    responses = [
        _extraction_json(hidden_qualities=["autonomous"]),  # invalid bare string
        _extraction_json(),                                 # valid retry
        _synthesis_json(),
    ]

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id,
             system_prompt="", model=None, **kwargs):
        calls.append(call_kind)
        return responses.pop(0)

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = analyzer.analyze(client=None, context_set=_CONTEXT)

    assert calls == ["analyze_extraction", "analyze_extraction_retry", "analyze_synthesis"]
    assert result["hidden_qualities"][0]["category"] == "operating_context"


# ---------- prompt builders -------------------------------------------------

def test_extraction_prompt_uses_typed_hidden_qualities_and_no_strategy():
    prompt = analyzer._analyze_extraction_prompt(_CONTEXT)
    assert '"hidden_qualities"' in prompt
    # Names all four typed categories.
    for cat in ("operating_context", "scope_of_ownership", "stakeholder_gravity", "resilience"):
        assert cat in prompt
    # Extraction must not ask for the synthesis-only keys.
    assert "overall_strategy" not in prompt
    assert "comparison" not in prompt
    assert "suggestions" not in prompt


def test_synthesis_prompt_carries_extracted_signal():
    extraction = json.loads(_extraction_json())
    prompt = analyzer._analyze_synthesis_prompt(_CONTEXT, extraction)
    assert "<extracted_signal>" in prompt
    assert "kubernetes" in prompt                       # essential skill forwarded
    assert "[operating_context]" in prompt              # typed hidden quality rendered
    assert "regulated, workflow-heavy environments" in prompt


def test_synthesis_prompt_tolerates_legacy_bare_string_hidden_qualities():
    """Defensive: a reloaded older analysis could carry list[str]; the render
    must not KeyError."""
    extraction = json.loads(_extraction_json(hidden_qualities=["legacy signal"]))
    prompt = analyzer._analyze_synthesis_prompt(_CONTEXT, extraction)
    assert "- legacy signal" in prompt


# ---------- analyze_streaming() — phase sentinel ----------------------------

def _scripted_streaming(responses_in_order):
    """Fake _call_llm_streaming yielding one chunk + a _StreamDone per call,
    popping `responses_in_order` (extraction first, then synthesis)."""
    attempts = iter(responses_in_order)
    call_kinds: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, **kwargs):
        call_kinds.append(call_kind)
        text = next(attempts)
        yield text
        yield _StreamDone(text=text, stop_reason="end_turn")

    fake.call_kinds = call_kinds
    return fake


def test_analyze_streaming_emits_phase_sentinels_and_single_merged_done(monkeypatch):
    monkeypatch.setattr(analyzer, "_stable_user_prefix", lambda cs: "PREFIX")
    fake = _scripted_streaming([_extraction_json(), _synthesis_json()])
    monkeypatch.setattr(analyzer, "_call_llm_streaming", fake)

    events = list(analyzer.analyze_streaming(client=None, context_set=_CONTEXT))
    kinds = [k for k, _ in events]

    # Two phase events, in order, extraction before synthesis.
    phases = [p["phase"] for k, p in events if k == "phase"]
    assert phases == ["extraction", "synthesis"]
    # First event is the extraction phase (before any chunk).
    assert kinds[0] == "phase" and events[0][1]["phase"] == "extraction"
    # Exactly one merged done, last, satisfying the contract with no phantoms.
    dones = [p for k, p in events if k == "done"]
    assert len(dones) == 1
    assert kinds[-1] == "done"
    assert set(dones[0].keys()) >= ANALYZE_REQUIRED_KEYS
    assert "ats_improvements" not in dones[0]
    assert dones[0]["overall_strategy"] == "Position as a platform SRE."
    # Both passes ran on the right call_kinds.
    assert fake.call_kinds == ["analyze_extraction", "analyze_synthesis"]
    # Chunks from both passes are forwarded (not swallowed with the inner done).
    assert kinds.count("chunk") == 2


def test_analyze_streaming_synthesis_phase_follows_extraction_parse(monkeypatch):
    """The synthesis phase sentinel must not fire until extraction has parsed —
    synthesis depends on the extracted signal."""
    monkeypatch.setattr(analyzer, "_stable_user_prefix", lambda cs: "PREFIX")
    fake = _scripted_streaming([_extraction_json(), _synthesis_json()])
    monkeypatch.setattr(analyzer, "_call_llm_streaming", fake)

    events = list(analyzer.analyze_streaming(client=None, context_set=_CONTEXT))
    kinds = [k for k, _ in events]

    extraction_phase_idx = next(
        i for i, (k, p) in enumerate(events) if k == "phase" and p["phase"] == "extraction"
    )
    synthesis_phase_idx = next(
        i for i, (k, p) in enumerate(events) if k == "phase" and p["phase"] == "synthesis"
    )
    # At least one chunk (the extraction stream) sits between the two phases.
    assert extraction_phase_idx < synthesis_phase_idx
    assert "chunk" in kinds[extraction_phase_idx:synthesis_phase_idx]
