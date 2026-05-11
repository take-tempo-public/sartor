"""Tests for iteration-aware behavior in analyzer.py.

Phase 1 focus:
  - _supplemental_block: demotion language when iteration > 0
  - _stable_user_prefix: <resume> block uses current draft (edited > last_gen)
                         when iteration > 0; supplementals demote to historical.
  - generate(): consumes edited_resume_text and edited_cover_letter_text;
                grounding worked-examples include the typed-edits pair.

Phase 2 will add clarify_iteration() coverage in this same file.
"""

import json

import analyzer
from analyzer import (
    _current_cover_letter_draft,
    _current_draft_text,
    _stable_user_prefix,
    _supplemental_block,
)

# ---------- _supplemental_block --------------------------------------------

def test_supplemental_block_iteration_zero_uses_supplemental_wrapper():
    ctx = {
        "resume": {"text": "primary", "filename": "p.docx"},
        "supplemental_resumes": [{"filename": "old.docx", "text": "old role"}],
    }
    block = _supplemental_block(ctx, iteration=0)
    assert "<supplemental_resumes" in block
    assert "<historical_resumes" not in block
    assert "old role" in block


def test_supplemental_block_iteration_zero_empty_when_no_supplements():
    ctx = {"resume": {"text": "primary"}, "supplemental_resumes": []}
    assert _supplemental_block(ctx, iteration=0) == ""


def test_supplemental_block_iteration_one_demotes_to_historical():
    ctx = {
        "resume": {"text": "primary text", "filename": "primary.docx"},
        "supplemental_resumes": [{"filename": "old.docx", "text": "old role"}],
    }
    block = _supplemental_block(ctx, iteration=1)
    assert "<historical_resumes" in block
    assert "<supplemental_resumes" not in block
    # Demotion language must explicitly tell the LLM these are NOT the current draft
    assert "EARLIER VERSIONS" in block
    assert "current draft" in block
    assert "NEVER let a historical resume override" in block


def test_supplemental_block_iteration_one_includes_original_primary():
    """At iteration > 0 the original primary resume must move into the
    historical block alongside supplementals — the current draft in <resume>
    has taken over as authoritative."""
    ctx = {
        "resume": {"text": "ORIGINAL PRIMARY TEXT", "filename": "primary.docx"},
        "supplemental_resumes": [{"filename": "side.docx", "text": "SIDE PROJECT TEXT"}],
    }
    block = _supplemental_block(ctx, iteration=1)
    assert "ORIGINAL PRIMARY TEXT" in block
    assert "SIDE PROJECT TEXT" in block
    assert 'count="2"' in block


def test_supplemental_block_iteration_one_no_supplementals_still_demotes_primary():
    """Even with no supplementals, the original primary alone must show up as
    historical so iteration N's prompt reflects that the current draft is
    different from the source-of-truth resume."""
    ctx = {
        "resume": {"text": "ORIGINAL PRIMARY", "filename": "p.docx"},
        "supplemental_resumes": [],
    }
    block = _supplemental_block(ctx, iteration=1)
    assert "<historical_resumes" in block
    assert "ORIGINAL PRIMARY" in block


# ---------- _current_draft_text --------------------------------------------

def test_current_draft_text_iteration_zero_returns_primary():
    ctx = {
        "iteration": 0,
        "resume": {"text": "PRIMARY"},
        "edited_resume_text": "EDITED",
        "last_generated_resume": "GENERATED",
    }
    text, label = _current_draft_text(ctx)
    assert text == "PRIMARY"
    assert label == "primary"


def test_current_draft_text_iteration_one_prefers_edited_over_generated():
    ctx = {
        "iteration": 1,
        "resume": {"text": "PRIMARY"},
        "edited_resume_text": "EDITED",
        "last_generated_resume": "GENERATED",
    }
    text, label = _current_draft_text(ctx)
    assert text == "EDITED"
    assert label == "edited"


def test_current_draft_text_iteration_one_falls_back_to_last_generated():
    ctx = {
        "iteration": 1,
        "resume": {"text": "PRIMARY"},
        "last_generated_resume": "GENERATED",
    }
    text, label = _current_draft_text(ctx)
    assert text == "GENERATED"
    assert label == "last_generated"


def test_current_draft_text_treats_whitespace_only_edits_as_absent():
    """User clearing the preview to whitespace must not leak into the prompt
    — fall back to last_generated as if no edit happened."""
    ctx = {
        "iteration": 1,
        "resume": {"text": "PRIMARY"},
        "edited_resume_text": "   \n  \t ",
        "last_generated_resume": "GENERATED",
    }
    text, _ = _current_draft_text(ctx)
    assert text == "GENERATED"


# ---------- _current_cover_letter_draft ------------------------------------

def test_cover_letter_draft_empty_at_iteration_zero():
    ctx = {"iteration": 0, "edited_cover_letter_text": "x", "last_generated_cover_letter": "y"}
    text, label = _current_cover_letter_draft(ctx)
    assert text == ""
    assert label == "none"


def test_cover_letter_draft_prefers_edited_at_iteration_one():
    ctx = {
        "iteration": 1,
        "edited_cover_letter_text": "USER LETTER",
        "last_generated_cover_letter": "GEN LETTER",
    }
    text, label = _current_cover_letter_draft(ctx)
    assert text == "USER LETTER"
    assert label == "edited"


# ---------- _stable_user_prefix --------------------------------------------

def _minimal_ctx_for_prefix(iteration: int = 0, **extras) -> dict:
    base: dict = {
        "iteration": iteration,
        "candidate": {"name": "Alice", "skills": []},
        "resume": {"text": "PRIMARY", "filename": "alice.docx"},
        "supplemental_resumes": [],
        "job_description": "JD body",
        "deterministic_analysis": {"keyword_overlap": {}},
    }
    base.update(extras)
    return base


def test_stable_prefix_iteration_zero_uses_primary_in_resume_block():
    ctx = _minimal_ctx_for_prefix(iteration=0)
    prefix = _stable_user_prefix(ctx)
    assert 'iteration="0"' in prefix
    assert "PRIMARY" in prefix
    assert "<historical_resumes" not in prefix


def test_stable_prefix_iteration_one_uses_edited_text_in_resume_block():
    ctx = _minimal_ctx_for_prefix(
        iteration=1,
        edited_resume_text="USER EDITED VERSION",
        last_generated_resume="STALE LLM OUTPUT",
    )
    prefix = _stable_user_prefix(ctx)
    assert "USER EDITED VERSION" in prefix
    # Stale text must not appear in <resume> — it would confuse the LLM
    # about which version to author from.
    assert "STALE LLM OUTPUT" not in prefix.split("</resume>")[0]
    # Original primary moves to historical and IS allowed to appear later
    assert "<historical_resumes" in prefix
    assert "PRIMARY" in prefix


def test_stable_prefix_iteration_one_falls_back_to_last_generated_when_no_edits():
    ctx = _minimal_ctx_for_prefix(
        iteration=1,
        last_generated_resume="LAST GEN VERSION",
    )
    prefix = _stable_user_prefix(ctx)
    assert "LAST GEN VERSION" in prefix.split("</resume>")[0]


# ---------- generate(): edited text consumption + grounding update --------

def _capture_prompt(monkeypatch):
    """Return (captured_prompts list, captured_prefixes list) and stub _call_llm."""
    captured_prompts: list[str] = []
    captured_prefixes: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt=""):
        captured_prompts.append(prompt)
        captured_prefixes.append(cached_user_prefix)
        return json.dumps({
            "resume_content": "# Out", "cover_letter_content": "Letter",
            "changes_made": [], "proofread_notes": [],
        })

    monkeypatch.setattr(analyzer, "_call_llm", fake)
    return captured_prompts, captured_prefixes


def _minimal_analysis() -> dict:
    return {
        "essential_skills": [], "keyword_placement": [], "suggestions": [],
        "overall_strategy": "", "professional_vocabulary": [],
    }


def test_generate_uses_edited_resume_text_in_cached_prefix(monkeypatch):
    prompts, prefixes = _capture_prompt(monkeypatch)
    ctx = _minimal_ctx_for_prefix(
        iteration=1,
        edited_resume_text="USER TYPED THIS",
        last_generated_resume="OLD GEN",
    )
    analyzer.generate(client=None, context_set=ctx, analysis=_minimal_analysis())

    prefix = prefixes[0]
    resume_section = prefix.split("</resume>")[0]
    assert "USER TYPED THIS" in resume_section
    assert "OLD GEN" not in resume_section


def test_generate_includes_cover_letter_draft_block_when_iterating(monkeypatch):
    prompts, _ = _capture_prompt(monkeypatch)
    ctx = _minimal_ctx_for_prefix(
        iteration=1,
        last_generated_cover_letter="prior LLM cover letter body",
    )
    analyzer.generate(client=None, context_set=ctx, analysis=_minimal_analysis())

    prompt = prompts[0]
    assert "<current_cover_letter_draft>" in prompt
    assert "prior LLM cover letter body" in prompt
    assert "EVOLVE this draft" in prompt


def test_generate_uses_edited_cover_letter_over_last_generated(monkeypatch):
    prompts, _ = _capture_prompt(monkeypatch)
    ctx = _minimal_ctx_for_prefix(
        iteration=1,
        edited_cover_letter_text="USER WROTE THIS LETTER",
        last_generated_cover_letter="STALE LLM LETTER",
    )
    analyzer.generate(client=None, context_set=ctx, analysis=_minimal_analysis())

    prompt = prompts[0]
    assert "USER WROTE THIS LETTER" in prompt
    assert "STALE LLM LETTER" not in prompt


def test_generate_omits_cover_letter_draft_block_at_iteration_zero(monkeypatch):
    prompts, _ = _capture_prompt(monkeypatch)
    ctx = _minimal_ctx_for_prefix(
        iteration=0,
        # Even if these fields are accidentally present at iter 0 (legacy
        # context, manual edit), the block must not appear — there's no
        # meaningful "prior draft" before the first generation.
        last_generated_cover_letter="ghost",
    )
    analyzer.generate(client=None, context_set=ctx, analysis=_minimal_analysis())
    assert "<current_cover_letter_draft>" not in prompts[0]


def test_generate_grounding_block_widened_for_typed_edits(monkeypatch):
    """The grounding worked-examples must include the typed-edits pair so
    the LLM knows it can cite first-person edits but must not extend them."""
    prompts, _ = _capture_prompt(monkeypatch)
    ctx = _minimal_ctx_for_prefix(iteration=0)
    analyzer.generate(client=None, context_set=ctx, analysis=_minimal_analysis())

    prompt = prompts[0]
    # The teaching signal: an OK / NOT OK pair specifically about typed edits
    assert "first-person edit" in prompt
    assert "Shipped V2 to enterprise" in prompt
    # And the grounding question itself acknowledges typed edits as ground truth
    assert "typed in" in prompt or "typed edits" in prompt


# ---------- clarify_iteration() (Phase 2) ----------------------------------

def _minimal_iter_clarify_response() -> str:
    return json.dumps({
        "questions": [
            {
                "id": "q1",
                "text": "Recent edit added 'shipped V2' — which customer segment?",
                "target_gap": "Recent edit added 'shipped V2 to enterprise'",
                "kind": "iteration_probe",
            },
            {
                "id": "q2",
                "text": "Terraform still missing — any side-project ownership?",
                "target_gap": "Essential skill Terraform missing from current draft",
                "kind": "experience_probe",
            },
            {
                "id": "q3",
                "text": "Current draft says 'led platform' — direct reports or matrix?",
                "target_gap": "Scope ambiguity in current draft platform bullet",
                "kind": "scope_probe",
            },
        ],
        "reasoning": "Mix of iteration follow-up, missing-skill probe, and scope.",
    })


def test_clarify_iteration_uses_dedicated_system_prompt(monkeypatch):
    """The iteration interview must use CLARIFY_ITERATION_SYSTEM_PROMPT
    (not the main SYSTEM_PROMPT, not CLARIFY_SYSTEM_PROMPT) so the LLM
    is briefed on iteration-specific rules — build on priors, target current
    draft, etc."""
    received_systems: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt=""):
        received_systems.append(system_prompt)
        assert cached_user_prefix == ""  # no cached prefix for compact call
        assert call_kind == "iterate_clarify"
        return _minimal_iter_clarify_response()

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = analyzer.clarify_iteration(
        client=None,
        context_set={"deterministic_analysis": {"keyword_overlap": {}}},
        analysis={"comparison": {"gaps": []}, "essential_skills": []},
        current_resume_text="# Resume\n- bullet one",
        current_cover_letter_text="Letter body",
        recent_edits_summary="user added 'shipped V2'",
        deterministic_signals={"verb_diversity": {"diversity_ratio": 0.32}},
        prior_clarifications=[],
    )

    assert "questions" in result and len(result["questions"]) == 3
    assert received_systems == [analyzer.CLARIFY_ITERATION_SYSTEM_PROMPT]


def test_clarify_iteration_includes_signal_sources_in_prompt(monkeypatch):
    """All four signal sources from the plan must reach the LLM prompt:
    current draft, recent edits, deterministic signals, and prior clarifications
    (with their answers, so the LLM knows what's established truth)."""
    captured_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt=""):
        captured_prompts.append(prompt)
        return _minimal_iter_clarify_response()

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    analyzer.clarify_iteration(
        client=None,
        context_set={
            "deterministic_analysis": {"keyword_overlap": {"missing_from_resume": ["terraform"]}},
        },
        analysis={
            "comparison": {"gaps": ["No K8s mentioned"], "title_alignment": "underleveled"},
            "essential_skills": ["kubernetes", "terraform"],
        },
        current_resume_text="# Current Draft\n- shipped V2 to enterprise",
        current_cover_letter_text="Current cover letter body",
        recent_edits_summary="user added 'shipped V2 to enterprise' to the platform bullet",
        deterministic_signals={
            "verb_diversity": {"diversity_ratio": 0.32, "top_repeated": [["led", 4]]},
            "specificity_density": {"density": 0.25},
            "grounding_overlap": {"overlap_ratio": 0.18, "missing_samples": ["kubernetes deployment"]},
            "keyword_coverage": {"still_missing_from_current_draft": ["terraform"]},
        },
        prior_clarifications=[
            {"question": "Have you used K8s?", "answer": "Yes, in prod 2023.", "kind": "experience_probe"},
        ],
    )

    prompt = captured_prompts[0]
    # Signal 1: current draft text included
    assert "shipped V2 to enterprise" in prompt
    # Signal 2: recent edits summary included
    assert "platform bullet" in prompt
    # Signal 3: deterministic signals as JSON
    assert "verb_diversity" in prompt
    assert "0.32" in prompt
    # Signal 4: prior clarifications (with answers, so LLM doesn't re-ask)
    assert "Have you used K8s?" in prompt
    assert "Yes, in prod 2023" in prompt
    # And the analyzer gaps still inform the prompt
    assert "No K8s mentioned" in prompt
    assert "terraform" in prompt


def test_clarify_iteration_excludes_skipped_prior_clarifications(monkeypatch):
    """Prior clarifications with empty answers must NOT appear in the prompt.
    A skipped question is not established truth — it's an open gap. Showing
    skipped-with-blank-answer pairs would confuse the LLM."""
    captured_prompts: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt=""):
        captured_prompts.append(prompt)
        return _minimal_iter_clarify_response()

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    analyzer.clarify_iteration(
        client=None,
        context_set={"deterministic_analysis": {"keyword_overlap": {}}},
        analysis={"comparison": {}, "essential_skills": []},
        current_resume_text="r",
        current_cover_letter_text="",
        recent_edits_summary="",
        deterministic_signals={},
        prior_clarifications=[
            {"question": "Empty answer Q", "answer": "", "kind": "experience_probe"},
            {"question": "Real answer Q", "answer": "real", "kind": "scope_probe"},
        ],
    )

    prompt = captured_prompts[0]
    assert "Empty answer Q" not in prompt
    assert "Real answer Q" in prompt


def test_clarify_iteration_retries_on_missing_keys(monkeypatch):
    """The retry budget should apply to the iteration call too — if the LLM
    omits 'reasoning' (CLARIFY_REQUIRED_KEYS), we retry once."""
    responses = [
        json.dumps({"questions": []}),  # missing 'reasoning'
        _minimal_iter_clarify_response(),
    ]
    calls: list[str] = []

    def fake(client, prompt, *, cached_user_prefix, call_kind, username, run_id, system_prompt=""):
        calls.append(call_kind)
        return responses.pop(0)

    monkeypatch.setattr(analyzer, "_call_llm", fake)

    result = analyzer.clarify_iteration(
        client=None,
        context_set={"deterministic_analysis": {"keyword_overlap": {}}},
        analysis={"comparison": {}, "essential_skills": []},
        current_resume_text="r", current_cover_letter_text="",
        recent_edits_summary="", deterministic_signals={},
        prior_clarifications=[],
    )
    assert "questions" in result
    assert calls == ["iterate_clarify", "iterate_clarify_retry"]
