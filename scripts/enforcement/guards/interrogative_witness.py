"""interrogative-witness guard — the momentum pause half of work item 87.

A session with a hot execution frame treats an interrogative prompt as a
work order: it answers, then unilaterally begins "fixing" something nobody
asked about (third recorded instance 2026-08-12; full spec in
`docs/dev/work/items/0087-interrogative-prompt-witness-hook.md`). The
owner's directed mitigation is not a hard gate on action — it is a
technique that strips momentum and forces the interrogative-vs-directive
consideration to be explicit, then trusts the judgment.

Two cooperating halves share this module:

* **Prompt receipt** (`record_prompt`, called by
  `adapters/prompt_witness_hook.py` on UserPromptSubmit): a cheap heuristic
  classifier — trailing ``?``, or a leading interrogative word — records
  per-session state and, on a match, the adapter injects a non-blocking
  "the deliverable is the ANSWER" reminder into context. Always exit 0.
* **First action** (`decide`, dispatched by `claude_dispatcher.py` on
  Edit|Write): the first Edit/Write after each recorded user prompt is
  refused ONCE with the consideration question, and the refusal itself
  clears the state — re-running the identical tool call proceeds. One
  pause per prompt, never two.

Stated limits (charter C-0/C-11 — labeled, not papered over): intent
classification is not deterministic, so both halves are WITNESSES that
force the consideration to happen, not gates that prove intent. Mechanically
the pause does reach exit 2 (once, self-clearing), which is why
`tests/test_governance_hooks_gate.py` counts it in `BLOCKER_RULE_NAMES` —
that file's taxonomy is mechanical and honesty there matters more than the
witness label here. Every failure path — no state file (a session started
before the UserPromptSubmit hook existed, or the hook not firing), corrupt
state, an unwritable state dir — is fail-open by design, matching the
owner's stated trust in momentum-free judgment. A heuristic false negative
(a directive phrased as a question) is acceptable: the owner is explicit
when action is wanted. Known limit: PreToolUse also fires for subagents'
Edit/Write calls, so a subagent's first edit can consume the turn's one
pause on the main agent's behalf.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.guards.result import GuardResult

#: Env var overriding where per-session witness state lives (tests point it
#: at a tmpdir; unset, state lives under the OS temp dir).
STATE_DIR_ENV = "SARTOR_WITNESS_STATE_DIR"

#: Leading tokens that classify a prompt as interrogative (work item 87's
#: spec list, verbatim — deliberately not extended without an owner ask).
INTERROGATIVE_LEADS = frozenset(
    {
        "is",
        "are",
        "was",
        "should",
        "would",
        "could",
        "why",
        "what",
        "when",
        "how",
        "does",
        "do",
        "did",
        "can",
        "whether",
        "who",
        "which",
    }
)

#: Trailing characters a closing "?" may legitimately hide behind.
_CLOSERS = "\"'`)]}»”’*_"

#: Punctuation stripped from the leading token before the set lookup.
_LEAD_STRIP = ".,:;!?\"'`([{<>-—–*_#"

#: Injected into context by the UserPromptSubmit adapter when the heuristic
#: classifies the prompt as a question. Non-blocking — plain stdout on exit 0.
REMINDER_LINES: tuple[str, ...] = (
    "interrogative-prompt-witness: this prompt reads as a QUESTION"
    " (heuristic: trailing '?' or an interrogative lead word).",
    "The deliverable is the ANSWER. Answer first; do not edit or begin work;"
    " propose any follow-on work at the end and wait for an explicit ask.",
    "An explicit directive from the user overrides this reminder."
    " (Fail-open witness, not a gate — intent classification is not"
    " deterministic; charter C-0.)",
)


def classify_prompt(text: str) -> bool:
    """Return True when `text` reads as an interrogative, per the item-87 heuristic.

    Trailing ``?`` (possibly inside closing quotes/brackets) or a leading
    interrogative token. Errs toward True — a false positive costs one
    reminder; a false negative costs nothing because the owner is explicit
    when action is wanted.
    """
    stripped = (text or "").strip()
    if not stripped:
        return False
    if stripped.rstrip(_CLOSERS).endswith("?"):
        return True
    lead = stripped.split(None, 1)[0].strip(_LEAD_STRIP).lower()
    return lead in INTERROGATIVE_LEADS


def _state_dir(env: Mapping[str, str]) -> Path:
    override = env.get(STATE_DIR_ENV, "")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "sartor-interrogative-witness"


def state_path(session_id: str, env: Mapping[str, str]) -> Path:
    """Per-session state file; the session id is sanitized before use as a filename."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")
    return _state_dir(env) / f"{safe or 'default'}.json"


def record_prompt(session_id: str, prompt: str, env: Mapping[str, str] | None = None) -> bool:
    """UserPromptSubmit half: classify `prompt`, reset the per-prompt pause state.

    Returns the classification so the adapter can decide whether to print
    the reminder. Any I/O failure propagates to the adapter, whose contract
    is to swallow it (fail-open) — this function stays honest about errors.
    """
    if env is None:
        env = os.environ
    interrogative = classify_prompt(prompt)
    path = state_path(session_id, env)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = _load_state(path)
    state = {
        "prompt_seq": int(previous.get("prompt_seq", 0)) + 1,
        "interrogative": interrogative,
        "witnessed": False,
    }
    path.write_text(json.dumps(state), encoding="utf-8")
    return interrogative


def _load_state(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


_PAUSE_HEADER = (
    "PAUSE (interrogative-witness): first Edit/Write since the last user prompt."
)
_PAUSE_CLASSIFIED = (
    "The prompt-receipt heuristic classified that prompt as a QUESTION."
)
_PAUSE_BODY: tuple[str, ...] = (
    "Was the triggering prompt an INTERROGATIVE needing an answer, or a"
    " directive calling for action?",
    "- A question's deliverable is the ANSWER: answer it and stop; propose"
    " follow-on work at the end, don't begin it.",
    "- A directive: re-run this exact tool call — the pause self-clears and"
    " will not fire again for this prompt.",
    "(One-shot momentum witness, not a gate: intent classification is not"
    " deterministic (charter C-0); fail-open by design — work item 87.)",
)


def decide(session_id: str, env: Mapping[str, str] | None = None) -> GuardResult:
    """Edit|Write half: refuse the first Edit/Write per recorded prompt, once.

    Marking `witnessed` BEFORE returning the refusal is what makes the pause
    self-clearing; every failure path allows (fail-open by design — see the
    module docstring).
    """
    if env is None:
        env = os.environ
    try:
        path = state_path(session_id, env)
        state = _load_state(path)
        if not state or state.get("witnessed", True):
            return GuardResult.allow()
        state["witnessed"] = True
        path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        return GuardResult.allow()
    lines = [_PAUSE_HEADER]
    if state.get("interrogative"):
        lines.append(_PAUSE_CLASSIFIED)
    lines.extend(_PAUSE_BODY)
    return GuardResult.block(*lines)


def claude_check(payload: dict[str, Any], env: Mapping[str, str] | None = None) -> GuardResult:
    """Claude PreToolUse adapter: the pause keys off `session_id` only."""
    return decide(str(payload.get("session_id") or ""), env)
