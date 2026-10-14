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
when action is wanted. Subagent Edit/Write calls (payload carries
`agent_id`) are skipped by `claude_check`, so they can no longer consume the
main agent's pause (item 94). Known limit: non-user events such as a
subagent's hand-back re-arm the pause (observed,
`docs/dev/diagnosis/witness-subagent-scope.md`), so the main agent may pause
on an edit no user prompt preceded. That costs one re-run.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.guards.result import GuardResult

#: Env var overriding where per-session witness state lives (tests point it
#: at a tmpdir; unset, state lives under the OS temp dir).
STATE_DIR_ENV = "SARTOR_WITNESS_STATE_DIR"

#: Env var overriding the sibling-refusal window in seconds (0 disables it). Item 164.
BATCH_WINDOW_ENV = "SARTOR_WITNESS_BATCH_WINDOW_S"

#: Seconds after a pause during which main-agent Edit/Write calls are refused as siblings of
#: the paused call. One sibling was observed at 1.13 s (`docs/dev/diagnosis/recurrence-guardrails.md`
#: O8, n=1; each hook is a fresh interpreter, so the figure is a floor on a loaded machine); a
#: re-run needs a full model turn. A timing heuristic, labeled as one in `decide`.
DEFAULT_BATCH_WINDOW_S = 3.0

#: A UserPromptSubmit whose prompt begins with this tag is a background-task or subagent
#: notification, not something the owner typed. Observed: 2 of 2 notifications in the trace
#: (O6), and the hook payload carries no `origin` field to key on instead. Anything else, and
#: any shape not seen, still arms the pause (today's behavior).
_NON_HUMAN_PROMPT_RE = re.compile(r"\s*<task-notification>")

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


def is_non_human_prompt(text: str) -> bool:
    """True when `text` is a task-notification turn rather than a prompt the owner typed.

    Known limit: an owner who pastes text beginning `<task-notification>` is treated the same
    way (no pause for that turn), which is the fail-open direction.
    """
    return bool(_NON_HUMAN_PROMPT_RE.match(text or ""))


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
    path = state_path(session_id, env)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = _load_state(path)
    seq = int(previous.get("prompt_seq", 0)) + 1
    if is_non_human_prompt(prompt):
        # A background-task or subagent notification is not the owner's prompt: it must not
        # re-arm the pause (item 164, `docs/dev/diagnosis/recurrence-guardrails.md` O6). Only
        # the event counter moves; an arm the owner's real prompt left unconsumed stays as it
        # was, and a session that has no state yet gets none (decide() allows on no state).
        state = {**previous, "prompt_seq": seq} if previous else {"prompt_seq": seq}
        path.write_text(json.dumps(state), encoding="utf-8")
        return False
    interrogative = classify_prompt(prompt)
    state = {
        "prompt_seq": seq,
        "armed_seq": int(previous.get("armed_seq", 0)) + 1,
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


#: How much of the transcript's end `batch_siblings` reads. A parallel batch is written within
#: the last few lines; 256 KB bounds the cost and keeps the read off the common path.
_TRANSCRIPT_TAIL_BYTES = 256 * 1024

#: Payload keys never copied into the trace (paths, and the prompt text itself).
_TRACE_SKIP_KEYS = frozenset({"prompt", "session_id", "transcript_path", "cwd"})

#: A prompt that begins with an XML-ish tag (e.g. a task-notification) is traced as that tag
#: alone: the tag is the discriminator under test, anything after it is content.
_LEADING_TAG_RE = re.compile(r"<[A-Za-z][\w:-]*>")


def trace(session_id: str, event: str, fields: dict[str, Any], env: Mapping[str, str]) -> None:
    """Append one record to this session's witness trace (item 164 instrument). Never raises.

    Lives beside the state file, under the OS temp dir: untracked, never committed. It records
    payload KEY NAMES and small scalar metadata only, never prompt text, so the observation the
    fix keys on (what distinguishes a typed prompt from a notification) is captured without
    keeping what the owner typed.
    """
    try:
        path = state_path(session_id, env).with_suffix(".trace.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"event": event, "ts": round(time.time(), 3), **fields}
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        return


def payload_trace_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Key names, small scalar/dict metadata and the leading tag of `prompt`, never its text."""
    prompt = payload.get("prompt")
    head = ""
    if isinstance(prompt, str):
        tag = _LEADING_TAG_RE.match(prompt.lstrip())
        head = tag.group(0) if tag else "(text)"
    meta = {
        key: value
        for key, value in payload.items()
        if key not in _TRACE_SKIP_KEYS
        and isinstance(value, str | int | float | bool | dict)
        and len(json.dumps(value, default=str)) <= 200
    }
    return {"keys": sorted(payload), "prompt_head": head, "meta": meta}


def batch_siblings(transcript_path: str, tool_use_id: str) -> dict[str, Any]:
    """Which tool calls share `tool_use_id`'s assistant message, per the transcript's tail.

    Claude Code writes one JSONL line per `tool_use` block, all sharing `message.id`
    (observed, `docs/dev/diagnosis/recurrence-guardrails.md` O2). Reads only the last
    `_TRANSCRIPT_TAIL_BYTES`, and is meant for the pause path (rare), not every call.
    Returns ``{"found": bool, "message_id": str | None, "sibling_ids": [...], "tail_bytes": n}``;
    an unreadable transcript or an id outside the tail is ``found: False``, never an exception.
    """
    result: dict[str, Any] = {
        "found": False,
        "message_id": None,
        "sibling_ids": [],
        "tail_bytes": 0,
    }
    if not transcript_path or not tool_use_id:
        return result
    try:
        with open(transcript_path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - _TRANSCRIPT_TAIL_BYTES)
            handle.seek(start)
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return result
    result["tail_bytes"] = len(raw)
    blocks: list[tuple[str, str]] = []  # (message id, tool_use id), in file order
    for line in raw.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue  # the first line of a mid-file tail is usually cut
        message = entry.get("message") if isinstance(entry, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                blocks.append((str(message.get("id") or ""), str(block.get("id") or "")))
    message_id = next((mid for mid, tid in blocks if tid == tool_use_id), None)
    if message_id:
        result.update(
            found=True,
            message_id=message_id,
            sibling_ids=[tid for mid, tid in blocks if mid == message_id],
        )
    return result


_PAUSE_HEADER = "PAUSE (interrogative-witness): first Edit/Write since the last user prompt."
_PAUSE_CLASSIFIED = "The prompt-receipt heuristic classified that prompt as a QUESTION."
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


_SIBLING_LINES: tuple[str, ...] = (
    "PAUSE (interrogative-witness): sibling of a paused call.",
    "An Edit/Write was paused a moment ago and this call arrived within the batch window, so it"
    " is refused with it: nothing in that batch was applied.",
    "Re-run every call from the batch (this one included). The pause is spent, so the re-runs"
    " proceed.",
    "(Timing heuristic, not proof of a shared batch; fail-open once the window passes.)",
)


def batch_window_seconds(env: Mapping[str, str]) -> float:
    """The sibling-refusal window (`SARTOR_WITNESS_BATCH_WINDOW_S`); 0 or unparsable-to-0 disables."""
    raw = env.get(BATCH_WINDOW_ENV, "")
    try:
        value = float(raw) if raw else DEFAULT_BATCH_WINDOW_S
    except ValueError:
        return DEFAULT_BATCH_WINDOW_S
    return max(value, 0.0)


def decide(
    session_id: str, env: Mapping[str, str] | None = None, now: float | None = None
) -> GuardResult:
    """Edit|Write half: refuse the first Edit/Write per recorded prompt, once.

    Marking `witnessed` BEFORE returning the refusal is what makes the pause
    self-clearing; every failure path allows (fail-open by design — see the
    module docstring).

    A pause also stamps `paused_at`. Calls that arrive within the batch window after it are
    refused as siblings of the paused call (item 164): a PreToolUse hook judges one call and
    cannot see its batch (the transcript has not been written yet at hook time, O7), so a
    paused call's batch-mates would otherwise land while it did not. The window is a timing
    heuristic, not proof of a shared batch, and it fails open once it has passed.
    """
    if env is None:
        env = os.environ
    stamp = time.time() if now is None else now
    try:
        path = state_path(session_id, env)
        state = _load_state(path)
        if not state or state.get("witnessed", True):
            paused_at = state.get("paused_at") if state else None
            window = batch_window_seconds(env)
            if (
                window > 0
                and isinstance(paused_at, int | float)
                and 0 <= stamp - float(paused_at) < window
            ):
                return GuardResult.block(*_SIBLING_LINES)
            return GuardResult.allow()
        state["witnessed"] = True
        state["paused_at"] = stamp
        path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        return GuardResult.allow()
    lines = [_PAUSE_HEADER]
    if state.get("interrogative"):
        lines.append(_PAUSE_CLASSIFIED)
    lines.extend(_PAUSE_BODY)
    return GuardResult.block(*lines)


def claude_check(payload: dict[str, Any], env: Mapping[str, str] | None = None) -> GuardResult:
    """Claude PreToolUse adapter: the pause keys off `session_id`, main agent only.

    A subagent's payload carries `agent_id`; the main agent's does not
    (observed 2026-09-22, `docs/dev/diagnosis/witness-subagent-scope.md`).
    Subagents share the invoker's `session_id`, so without this skip a
    subagent's first edit consumed the main agent's pause and died as a
    `hook_block` (item 94, Epic B run 6). A subagent never receives the
    owner's prompt, so the pause protects nothing there. Only a PRESENT
    (truthy) `agent_id` skips; absent or blank falls back to pausing.
    """
    if payload.get("agent_id"):
        return GuardResult.allow()
    if env is None:
        env = os.environ
    session_id = str(payload.get("session_id") or "")
    result = decide(session_id, env)
    # Item 164 instrument (A1): every main-agent Edit/Write is traced with a timestamp (how far
    # apart do a batch's calls arrive?), and a pause also records whether the paused call's
    # batch siblings are already in the transcript at PreToolUse time. Fail-open.
    fields: dict[str, Any] = {
        "tool_name": payload.get("tool_name"),
        "tool_use_id": payload.get("tool_use_id"),
        "blocked": result.blocked,
    }
    kind = "call"
    if result.blocked:
        is_sibling = bool(result.messages) and result.messages[0] == _SIBLING_LINES[0]
        kind = "sibling" if is_sibling else "pause"
        if not is_sibling:
            fields["batch"] = batch_siblings(
                str(payload.get("transcript_path") or ""),
                str(payload.get("tool_use_id") or ""),
            )
    trace(session_id, kind, fields, env)
    return result
