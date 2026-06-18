"""Unit tests for `analyzer.avatar_answer_streaming` — the doc-grounded avatar.

LLM-free: `_call_llm_streaming` is monkeypatched to yield canned deltas then the
`_StreamDone` sentinel, so these exercise prompt construction + the chunk/done
contract without an API call.
"""

from __future__ import annotations

import re
from pathlib import Path

import analyzer
from recall.models import Audience, Context, Tier, Unit

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _ctx(units: tuple[Unit, ...] = (), *, truncated: bool = False) -> Context:
    return Context(query="q", units=units, token_estimate=0, truncated=truncated)


def _two_units() -> tuple[Unit, ...]:
    return (
        Unit("The grounding check rejects invented facts.", Tier.WIKI, "wiki",
             "[[generation-and-grounding]]", Audience.USER, "a" * 40, score=2.0),
        Unit("SYSTEM_PROMPT = ...", Tier.GIT, "git", "analyzer.py:353", Audience.DEV, "a" * 40, score=1.0),
    )


def _install_stub(monkeypatch, captured: dict, deltas=("Hello ", "world.")):
    def _fake_stream(client, user_prompt, **kwargs):
        captured["user_prompt"] = user_prompt
        captured["kwargs"] = kwargs
        yield from deltas
        yield analyzer._StreamDone("".join(deltas), "end_turn")

    monkeypatch.setattr(analyzer, "_call_llm_streaming", _fake_stream)


def test_yields_chunks_then_done(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(analyzer.avatar_answer_streaming(None, "how does grounding work?", _ctx(_two_units())))
    assert events[0] == ("chunk", "Hello ")
    assert events[1] == ("chunk", "world.")
    name, payload = events[-1]
    assert name == "done"
    assert payload["answer"] == "Hello world."


def test_done_payload_carries_citations_and_flags(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(
        analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units(), truncated=True), allow_dev=True)
    )
    _, payload = events[-1]
    assert payload["citations"] == ["[[generation-and-grounding]]", "analyzer.py:353"]
    assert payload["truncated"] is True
    assert payload["allow_dev"] is True


def test_prompt_includes_each_citation_and_question(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "explain the grounding check", _ctx(_two_units())))
    prompt = captured["user_prompt"]
    assert "[[generation-and-grounding]]" in prompt
    assert "analyzer.py:353" in prompt
    assert "explain the grounding check" in prompt


def test_dev_mode_marked_in_prompt(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units()), allow_dev=True))
    assert "<mode>dev</mode>" in captured["user_prompt"]


def test_user_mode_marked_in_prompt(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units()), allow_dev=False))
    assert "<mode>user</mode>" in captured["user_prompt"]


def test_avatar_uses_haiku_and_own_call_kind(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units())))
    assert captured["kwargs"]["model"] == analyzer.HAIKU_MODEL
    assert captured["kwargs"]["call_kind"] == "avatar_answer"
    assert captured["kwargs"]["system_prompt"] == analyzer.AVATAR_SYSTEM_PROMPT


def test_empty_context_renders_fallback(monkeypatch):
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    events = list(analyzer.avatar_answer_streaming(None, "q", _ctx(())))
    assert "no relevant context" in captured["user_prompt"]
    _, payload = events[-1]
    assert payload["citations"] == []


def test_avatar_prompt_version_is_distinct_from_prompt_version():
    # The avatar carries its own version so persona tweaks don't bump PROMPT_VERSION.
    assert analyzer.AVATAR_PROMPT_VERSION != analyzer.PROMPT_VERSION
    assert "AVATAR_SYSTEM_PROMPT" not in analyzer._BASE_SYSTEM_PROMPTS


# --------------------------------------------------------------------------- #
# Deterministic tone checks (voice/tone tuning, AVATAR_PROMPT_VERSION 2026-06-18.1).
#
# The guidance doc (docs/dev/avatar-voice-tone-guidance.md §6.2) specifies an
# LLM-free layer that runs on the gate. These cover the cheap-and-load-bearing
# guards: the byte-exact refusal sync, the persona clauses that must stay present,
# the brand-mark + GitHub-link microcopy invariants, and the reusable scanners
# (banned-phrase / no-URL-in-output / cite-membership) that the manual §6.3
# transcript review applies to live answers. The scanners are tested here on
# fixtures so the checker itself is trustworthy when run over a real transcript.
# --------------------------------------------------------------------------- #

# The byte-exact refusal — load-bearing, lives in L1 (AVATAR_SYSTEM_PROMPT) AND L2
# (the per-turn closer). Both must carry it identically (guidance §6.2 / L4 sync).
_REFUSAL = "I don't have that in my docs."

# Output tells the avatar must never emit (guidance §5 DON'T list): the two
# over-promise round-ups, performed honesty, performed empathy, choice-validation,
# and the cheer openers / trailing recaps. Scanned case-insensitively over an answer.
_BANNED_OUTPUT_TELLS = (
    "reaches a human",
    "improves your chances",
    "i'd rather be straight",
    "to be honest with you",
    "that sounds exhausting",
    "i know this is stressful",
    "you're in the right place",
    "you've come to the right",
    "great question",
    "happy to help",
    "hope this helps",
    "anything else",
)

# The avatar cites in clean SINGLE square brackets at the end of a sentence —
# [page-slug] for wiki, [path:line] for code. This token parser tolerates a stray
# double bracket too (it captures the inner slug), so the check is robust if the
# model occasionally regresses to [[ ]].
_CITE_TOKEN = re.compile(r"\[([\w][\w./:-]*?)\]")


def _scan_banned_tells(answer: str) -> list[str]:
    """Return the banned tells present in an answer (empty == clean)."""
    low = answer.lower()
    hits = [tell for tell in _BANNED_OUTPUT_TELLS if tell in low]
    if "!" in answer:
        hits.append("exclamation")
    return hits


def _scan_urls(answer: str) -> list[str]:
    """A raw URL in model output means the model fabricated/echoed a link — the
    GitHub link belongs ONLY in the L3 chrome, never in the grounded answer."""
    low = answer.lower()
    return [tok for tok in ("http://", "https://", "github.com") if tok in low]


def _norm_cite(c: str) -> str:
    """Bare citation token: '[[slug]]' / '[slug]' -> 'slug'; 'path:line' unchanged."""
    return c.strip("[]")


def _emitted_citations(answer: str) -> set[str]:
    return set(_CITE_TOKEN.findall(answer))


def _cite_membership_violations(answer: str, units: tuple[Unit, ...]) -> set[str]:
    """Citations the answer emits that were NOT in the recalled units (guidance
    §6.2 'the single highest-value guardrail' — citation-shaped hallucination).
    Compared on normalized bare tokens, so the bracket style doesn't matter."""
    given = {_norm_cite(u.citation) for u in units}
    return _emitted_citations(answer) - given


def test_refusal_string_byte_synced_across_l1_and_l2(monkeypatch):
    # L4 sync: the refusal is byte-identical in the system prompt and the per-turn
    # closer. The closer is built inside avatar_answer_streaming, so capture it.
    assert _REFUSAL in analyzer.AVATAR_SYSTEM_PROMPT
    captured: dict = {}
    _install_stub(monkeypatch, captured)
    list(analyzer.avatar_answer_streaming(None, "q", _ctx(_two_units())))
    assert _REFUSAL in captured["user_prompt"]


def test_l1_carries_the_locked_voice_clauses():
    p = analyzer.AVATAR_SYSTEM_PROMPT
    # Friendly-guide persona (Q1) delivered via helpfulness, not instructed wit.
    assert "friendly, grounded guide" in p
    # P0 precedence line, verbatim from the Voice Charter.
    assert "When voice and grounding conflict, grounding wins" in p
    # Near-mandatory cited redirect (Q8).
    assert "point to the nearest thing the context DOES cover, with its citation" in p
    # The GitHub "report it" rung (Q9) — behavior only, model must not invent a URL.
    assert "report it on the project's GitHub" in p
    assert "never invent a URL, contact, or person" in p
    # Calibrated middle (Q10) as a behavioral instruction, not a template.
    assert "A partial cited answer beats both a guess and a flat refusal" in p
    # Anti-over-promise (parseability, never the outcome round-up).
    assert "improves your chances" in p  # named as a forbidden phrasing
    # Connect-capability-to-concern on reassurance-fishing (Q11).
    assert "connect what the tool actually does" in p
    # The warmly-framed L5 dev-mode nudge (Q6), verbatim.
    assert (
        "Want the implementation detail? Tick Dev mode in the assistant panel "
        "and I can bring in the technical detail." in p
    )
    # Readable citations: clean SINGLE square brackets at the END of the sentence
    # (not [[ ]] mid-sentence) — for non-technical readers.
    assert "SINGLE square brackets" in p
    assert "END of the sentence" in p
    assert "[[slug]]" not in p  # the old double-bracket inline form is gone


def test_banned_tell_scanner_flags_overpromise_and_performed():
    not_ok = (
        "callback. keeps the output ATS-safe so it reaches a human.",
        "I'd rather be straight with you than guess.",
        "That sounds exhausting — but you're in the right place!",
        "Great question! Happy to help.",
    )
    for sample in not_ok:
        assert _scan_banned_tells(sample), f"should have flagged: {sample!r}"
    ok = (
        "You tailor a résumé in the wizard; it rewrites bullets from your corpus "
        "to fit the job [[tailoring-a-resume]]."
    )
    assert _scan_banned_tells(ok) == []


def test_no_url_scanner_flags_links_in_output():
    assert _scan_urls("Report it at https://github.com/amodal1/callback/issues")
    assert _scan_urls("see github.com/x")
    assert _scan_urls("You can report this on the project's GitHub.") == []


def test_cite_membership_flags_ungiven_citations():
    units = _two_units()  # citations: [[generation-and-grounding]], analyzer.py:353
    # Clean single-bracket, end-of-sentence form (what the avatar now emits).
    grounded = "The grounding check rejects invented facts [generation-and-grounding] [analyzer.py:353]."
    assert _cite_membership_violations(grounded, units) == set()
    fabricated = "See [made-up-page] and [analyzer.py:999] for details."
    assert _cite_membership_violations(fabricated, units) == {"made-up-page", "analyzer.py:999"}


def test_assistant_microcopy_brand_mark_and_github_link():
    html = (_REPO_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    # Plain-languaged intro + empty-state scope line landed. (ASCII-only substrings —
    # the line also contains "résumé", but asserting non-ASCII trips source-encoding
    # mismatches on Windows; the brand-mark/link checks below are what matter here.)
    assert "how callback. works" in html
    assert "won't touch your private resumes or configs" in html
    # The real repo issues URL is the SINGLE source of the link (the model never
    # emits a URL — it only states the behavior; cf. test_no_url_scanner_*).
    assert html.count("https://github.com/amodal1/callback/issues") == 1
    # Brand mark casing: never the wrong forms anywhere in the shell.
    assert "CallBack" not in html
    assert "Callback." not in html


def test_answer_node_is_not_a_live_region():
    # The aria-live streaming-flood fix (§5c): #assistantAnswer must NOT be a live
    # region (per-token announcements flood screen readers); #assistantStatus stays
    # the single polite announce channel.
    html = (_REPO_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    answer_tag = html[html.index('id="assistantAnswer"') - 20 : html.index('id="assistantAnswer"') + 120]
    assert 'aria-live' not in answer_tag
    assert 'aria-busy' in answer_tag
    # The status region keeps its polite live announcement.
    status_tag = html[html.index('id="assistantStatus"') - 20 : html.index('id="assistantStatus"') + 120]
    assert 'aria-live="polite"' in status_tag
