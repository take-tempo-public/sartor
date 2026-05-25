"""Tests for the LLM-response parsing layer in analyzer.py.

Covers _strip_fences and _parse_or_retry. The retry helper is exercised by
monkey-patching analyzer._call_llm to return a pre-scripted list of responses,
which keeps the tests free of any real Anthropic SDK or network dependency.
"""

import json

import pytest

import analyzer
from analyzer import (
    ANALYZE_REQUIRED_KEYS,
    LLMResponseError,
    _parse_or_retry,
    _strip_fences,
)

# ---------- _strip_fences ---------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"a": 1}', '{"a": 1}'),
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('  ```json\n{"a": 1}\n```  ', '{"a": 1}'),
        ('```json{"a": 1}```', '{"a": 1}'),
    ],
)
def test_strip_fences_variants(raw, expected):
    assert _strip_fences(raw) == expected


# ---------- _parse_or_retry happy paths -------------------------------------

def _scripted_call_llm(responses):
    """Build a fake _call_llm that pops one response per call.

    Records call_kinds it was invoked with so tests can assert on retry naming.
    Accepts **kwargs so it tolerates future _call_llm signature additions without
    test breakage (e.g. system_prompt was added for the clarify step).
    """
    calls: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, **kwargs):
        calls.append(call_kind)
        return responses.pop(0)

    fake.calls = calls
    return fake


def _valid_analysis_json() -> str:
    body = {k: [] if k != "ideal_resume_profile" and k != "overall_strategy"
            and k != "comparison" else
            ("text" if k != "comparison" else {})
            for k in ANALYZE_REQUIRED_KEYS}
    return json.dumps(body)


def test_parse_or_retry_happy_path(monkeypatch):
    fake = _scripted_call_llm([_valid_analysis_json()])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze"]  # no retry needed


def test_parse_or_retry_strips_markdown_fences(monkeypatch):
    fenced = f"```json\n{_valid_analysis_json()}\n```"
    fake = _scripted_call_llm([fenced])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze"]


def test_parse_or_retry_tolerates_literal_control_chars_in_strings(monkeypatch):
    """Claude sometimes emits raw newlines inside JSON string values
    instead of escaping them as `\\n`. Strict `json.loads()` rejects
    those with `Invalid control character at: line N column M`. We
    pass `strict=False` to widen tolerance — multi-line content in
    résumé / cover-letter fields is exactly the case we observe.

    Regression guard: the user hit this on Step 5 Generate
    (2026-05-25). Before the fix this would have failed parse and
    consumed a retry; after the fix it parses on the first attempt.
    """
    # Build a valid analyze payload then inject a literal newline
    # inside the `overall_strategy` string. Mirrors what Sonnet 4.6
    # produces for multi-line résumé content (the actual case
    # observed had a 4471-token résumé body with embedded \n).
    body = json.loads(_valid_analysis_json())
    body["overall_strategy"] = "First line.\nSecond line.\nThird line."
    # Bypass json.dumps's default escaping so the response contains
    # literal newlines, the way the LLM actually emits them.
    raw = json.dumps(body).replace("\\n", "\n")

    fake = _scripted_call_llm([raw])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert result["overall_strategy"] == "First line.\nSecond line.\nThird line."
    assert fake.calls == ["analyze"]  # NO retry consumed


# ---------- _parse_or_retry retry succeeds ----------------------------------

def test_parse_or_retry_recovers_from_missing_keys(monkeypatch):
    """First response is missing required keys; second is valid."""
    fake = _scripted_call_llm([
        json.dumps({"essential_skills": []}),  # missing nearly everything
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_recovers_from_invalid_json(monkeypatch):
    """First response is unparseable; second is valid."""
    fake = _scripted_call_llm([
        "this is not json at all { unterminated",
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="analyze", username="u", run_id="r",
    )

    assert set(result.keys()) >= ANALYZE_REQUIRED_KEYS
    assert fake.calls == ["analyze", "analyze_retry"]


# ---------- _parse_or_retry retry exhausted ---------------------------------

def test_parse_or_retry_raises_on_persistent_missing_keys(monkeypatch):
    bad = json.dumps({"essential_skills": []})
    fake = _scripted_call_llm([bad, bad])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    with pytest.raises(LLMResponseError) as excinfo:
        _parse_or_retry(
            client=None, base_prompt="prompt",
            cached_user_prefix="prefix",
            required_keys=ANALYZE_REQUIRED_KEYS,
            call_kind="analyze", username="u", run_id="r",
        )

    assert "missing required keys" in excinfo.value.validation_error
    assert excinfo.value.raw == bad
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_raises_on_persistent_invalid_json(monkeypatch):
    junk = "not json"
    fake = _scripted_call_llm([junk, junk])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    with pytest.raises(LLMResponseError) as excinfo:
        _parse_or_retry(
            client=None, base_prompt="prompt",
            cached_user_prefix="prefix",
            required_keys=ANALYZE_REQUIRED_KEYS,
            call_kind="analyze", username="u", run_id="r",
        )

    assert excinfo.value.raw == junk
    assert fake.calls == ["analyze", "analyze_retry"]


def test_parse_or_retry_uses_retry_call_kind(monkeypatch):
    """Retry must use call_kind '<orig>_retry' for dashboard attribution."""
    fake = _scripted_call_llm([
        "junk",
        _valid_analysis_json(),
    ])
    monkeypatch.setattr(analyzer, "_call_llm", fake)

    _parse_or_retry(
        client=None, base_prompt="prompt",
        cached_user_prefix="prefix",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="generate", username="u", run_id="r",
    )

    assert fake.calls == ["generate", "generate_retry"]


# ---------- _parse_or_retry threads system_prompt to _call_llm --------------

def test_parse_or_retry_threads_system_prompt(monkeypatch):
    """The optional system_prompt arg must reach _call_llm so calls like
    clarify() use a dedicated persona rather than the main SYSTEM_PROMPT."""
    received_system_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        received_system_prompts.append(system_prompt)
        return _valid_analysis_json()

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    _parse_or_retry(
        client=None, base_prompt="p",
        cached_user_prefix="",
        required_keys=ANALYZE_REQUIRED_KEYS,
        call_kind="clarify", username="u", run_id="r",
        system_prompt="DEDICATED",
    )

    assert received_system_prompts == ["DEDICATED"]


# ---------- clarify() ------------------------------------------------------

def _minimal_clarify_response() -> str:
    """Valid CLARIFY_REQUIRED_KEYS shape for clarify() to return."""
    return json.dumps({
        "questions": [
            {
                "id": "q1",
                "text": "Have you used Kubernetes in production?",
                "target_gap": "Essential skill Kubernetes missing from resume",
                "kind": "experience_probe",
            },
            {
                "id": "q2",
                "text": "Did the K8s migration ship to production or remain a POC?",
                "target_gap": "Analyzer flagged ambiguity in shipped status",
                "kind": "scope_probe",
            },
        ],
        "reasoning": "Mix of experience and scope probes targeting analyzer gaps.",
    })


def test_clarify_returns_structured_questions(monkeypatch):
    """clarify() runs the dedicated CLARIFY_SYSTEM_PROMPT path and parses
    a questions/reasoning JSON response."""
    received_system_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        received_system_prompts.append(system_prompt)
        # clarify uses no cached prefix — the analyzer has already digested the resume/JD
        assert cached_user_prefix == ""
        assert call_kind == "clarify"
        return _minimal_clarify_response()

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    context_set = {
        "deterministic_analysis": {
            "keyword_overlap": {"missing_from_resume": ["kubernetes", "terraform"]},
        },
        "candidate": {"skills": ["docker", "linux"]},
    }
    analysis = {
        "essential_skills": ["kubernetes", "terraform"],
        "preferred_skills": [],
        "comparison": {"strengths": [], "gaps": ["No K8s mentioned"], "title_alignment": ""},
        "keyword_placement": [],
        "overall_strategy": "",
    }

    result = analyzer.clarify(client=None, context_set=context_set, analysis=analysis,
                              username="u", run_id="r")

    assert "questions" in result and "reasoning" in result
    assert len(result["questions"]) == 2
    assert result["questions"][0]["kind"] == "experience_probe"
    assert received_system_prompts == [analyzer.CLARIFY_SYSTEM_PROMPT]


def test_clarify_retries_on_missing_keys(monkeypatch):
    """clarify() must fail validation and retry when reasoning is missing."""
    responses = [
        json.dumps({"questions": []}),  # missing 'reasoning'
        _minimal_clarify_response(),
    ]
    calls: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        calls.append(call_kind)
        return responses.pop(0)

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    context_set = {"deterministic_analysis": {"keyword_overlap": {}}, "candidate": {}}
    analysis = {"essential_skills": [], "comparison": {}, "keyword_placement": []}

    result = analyzer.clarify(client=None, context_set=context_set, analysis=analysis)
    assert "questions" in result
    assert calls == ["clarify", "clarify_retry"]


# ---------- generate() injects clarifications into prompt -------------------

def test_generate_includes_clarification_block_when_present(monkeypatch):
    """When context_set has clarifications, the generate prompt must contain
    the <candidate_clarifications> block with paired question and answer."""
    captured_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        captured_prompts.append(prompt)
        return json.dumps({
            "resume_content": "# Name\n## Experience\n",
            "cover_letter_content": "Cover letter body",
            "changes_made": [],
            "proofread_notes": [],
        })

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    context_set = {
        "candidate": {"name": "x", "skills": []},
        "resume": {"text": "resume text", "filename": "x.docx"},
        "supplemental_resumes": [],
        "job_description": "jd",
        "deterministic_analysis": {"keyword_overlap": {}},
        "clarification_questions": [
            {"id": "q1", "text": "Used Kubernetes?", "kind": "experience_probe", "target_gap": "k8s"},
            {"id": "q2", "text": "Shipped?", "kind": "scope_probe", "target_gap": "scope"},
        ],
        "clarifications": {
            "q1": "Yes, briefly on the SRE rotation in 2024.",
            # q2 deliberately skipped — should be absent from prompt
        },
    }
    analysis = {
        "essential_skills": [], "keyword_placement": [], "suggestions": [],
        "overall_strategy": "", "professional_vocabulary": [],
    }

    analyzer.generate(client=None, context_set=context_set, analysis=analysis)

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    assert "<candidate_clarifications>" in prompt
    assert 'id="q1"' in prompt
    assert "briefly on the SRE rotation" in prompt
    # Skipped question must not appear
    assert 'id="q2"' not in prompt


def test_generate_omits_clarification_block_when_absent(monkeypatch):
    """When context_set has no clarifications, the generate prompt must NOT
    contain the <candidate_clarifications> block. Back-compat for pre-clarify
    contexts."""
    captured_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        captured_prompts.append(prompt)
        return json.dumps({
            "resume_content": "# Name\n",
            "cover_letter_content": "letter",
            "changes_made": [],
            "proofread_notes": [],
        })

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    context_set = {
        "candidate": {"name": "x", "skills": []},
        "resume": {"text": "resume text", "filename": "x.docx"},
        "supplemental_resumes": [],
        "job_description": "jd",
        "deterministic_analysis": {"keyword_overlap": {}},
    }
    analysis = {
        "essential_skills": [], "keyword_placement": [], "suggestions": [],
        "overall_strategy": "", "professional_vocabulary": [],
    }

    analyzer.generate(client=None, context_set=context_set, analysis=analysis)
    assert "<candidate_clarifications>" not in captured_prompts[0]


def test_generate_omits_clarification_block_when_all_skipped(monkeypatch):
    """If clarification_questions exist but all answers are empty/missing,
    the block must still be omitted — no empty wrapper in the prompt."""
    captured_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt="", **kwargs):
        captured_prompts.append(prompt)
        return json.dumps({
            "resume_content": "# x", "cover_letter_content": "x",
            "changes_made": [], "proofread_notes": [],
        })

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    context_set = {
        "candidate": {"name": "x", "skills": []},
        "resume": {"text": "r", "filename": "x.docx"},
        "supplemental_resumes": [],
        "job_description": "jd",
        "deterministic_analysis": {"keyword_overlap": {}},
        "clarification_questions": [
            {"id": "q1", "text": "Q?", "kind": "experience_probe", "target_gap": "g"},
        ],
        "clarifications": {},  # user clicked Skip
    }
    analysis = {"essential_skills": [], "keyword_placement": [], "suggestions": [],
                "overall_strategy": "", "professional_vocabulary": []}

    analyzer.generate(client=None, context_set=context_set, analysis=analysis)
    assert "<candidate_clarifications>" not in captured_prompts[0]
