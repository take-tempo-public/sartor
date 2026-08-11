#!/usr/bin/env python3
"""Claude Code SessionStart / PreCompact adapter — the charter **C-8** controls.

C-8 ("durable before deep") says the context window is not a durable store. These two hooks
make that structurally true rather than merely aspirational: the branch's diagnosis dossier
becomes the source of truth, and it is replayed into every fresh context automatically.

    restore-evidence      SessionStart (startup|resume|compact)
    capture-before-compact  PreCompact (auto|manual)

**What each one can actually do** — verified against the hooks reference, not assumed, because
assuming a mechanism is the exact sin these hooks exist to prevent:

- **SessionStart**: plain stdout **is added to Claude's context**, on every matcher — including
  `compact`, which fires on the fresh context *after* a compaction. That is the whole ballgame:
  the evidence re-enters the window every time the window is rebuilt. Output is capped at
  10,000 characters, so we budget below that.
- **PreCompact**: **cannot inject context.** It supports `{"decision": "block"}` and
  `{"systemMessage": ...}` (shown to the *user*, not to Claude); plain stdout goes to the debug
  log only. So `capture-before-compact` warns **the human** that a window is about to be
  discarded while this fix branch has no captured evidence. It deliberately does **not** block
  compaction — a blocked auto-compact can wedge a session, and the cure would be worse than the
  disease.

The real enforcement of C-8 on a `fix/*` branch is therefore structural, not advisory: the
`require-evidence-before-fix` PreToolUse guard means no production code gets written until the
dossier exists — so by the time any compaction happens, there is always something for
`restore-evidence` to replay.

Invoked by the thin wrappers in root `hooks/`:

    exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_context_hook.py" <name>
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Make `scripts.enforcement.*` importable however this file is invoked (a direct script path,
# as the wrapper `.sh` files do — not `-m`). Mirrors `claude_hook.py`.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.evidence import (  # noqa: E402
    diagnosis_path,
    has_observed_evidence,
    replay_text,
    template_text,
)
from scripts.enforcement.gitutil import git_branch  # noqa: E402

_HOOK_NAMES = ("restore-evidence", "capture-before-compact")

#: Claude Code caps hook output at 10,000 characters (anything longer is spilled to a file and
#: replaced by a preview). Stay comfortably under it: a dossier long enough to hit this has
#: outgrown what belongs in every fresh context anyway, and the file is one Read away.
_MAX_REPLAY_CHARS = 8_000

_PREAMBLE = (
    "=== EVIDENCE ON THIS BRANCH (charter C-8 — replayed from {path}) ===",
    "",
    "This is the DURABLE record for the bug you are working on. It was expensive to produce.",
    "Do not re-derive it, and do not re-chase anything under '## Falsified' — those are dead,",
    "and each one cost real money to kill.",
    "",
    "'## Inferred' is deliberately NOT replayed here. If you need the current hypothesis, open",
    "the file and read it as a hypothesis — an unproven mechanism, re-injected as context, reads",
    "like established fact within a few turns. That is the rot this hook exists to prevent.",
    "",
)

_TRUNCATED = "\n\n[... truncated — read the full dossier at {path} ...]"


def _project_dir(payload: dict[str, Any]) -> Path:
    """Repo root: `CLAUDE_PROJECT_DIR` if set, else the payload's `cwd`, else the cwd."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")


def _dossier(payload: dict[str, Any]) -> tuple[str, Path, str | None]:
    """`(branch, dossier_path, text_or_None)` for the checked-out branch."""
    repo_root = _project_dir(payload)
    branch = git_branch(str(repo_root))
    path = diagnosis_path(repo_root, branch)
    try:
        return branch, path, path.read_text(encoding="utf-8")
    except OSError:
        return branch, path, None


#: Charter **C-12**. Injected on SessionStart(`compact`) REGARDLESS of branch type. The
#: pre-C-12 hook keyed entirely off a `fix/*` dossier and returned "" otherwise -- so a
#: compaction on a `feat/*`/`chore/*` branch (i.e. most branches) injected NOTHING, and the
#: rebuilt context had no way to know it had lost anything. That silence is the failure mode:
#: the model fills the gap from plausibility and proceeds as though it were sourced.
_COMPACTION_NOTICE = (
    "=== INFORMATION WAS LOST (charter C-12 - a compaction just occurred) ===",
    "",
    "This context was REBUILT from a summary. You are missing things you previously knew,",
    "and you cannot tell from the inside which things. Compactions on record this session: {n}.",
    "",
    "Before you assert ANY fact you cannot see in front of you right now - a file's contents,",
    "a command's output, what a test did, what was already decided - reconcile against the",
    "repo and git. Do not continue from the summary as though it were the evidence.",
    "",
    "If you find a gap, SAY SO. 'I no longer have this' and 'I did not verify this' are",
    "required outputs, not admissions of failure. Reconstructing a lost fact from",
    "plausibility, and then proceeding as though it were sourced, is a C-0 violation and is",
    "the single mechanism underneath most of this project's expensive wrong turns.",
    "",
    "",
)


#: Pre-Epic-B robustness design pass (2026-08-11). Sessions bounded to roughly one branch's
#: worth of work measured 1-5 compactions in this repo's own ledger history; sessions that
#: chained multiple sprints in one continuous window measured 11 and 14. This threshold sits
#: just above the single-branch range -- a deliberate margin, not a precise measurement.
_COMPACTION_THRESHOLD = 5

#: Deliberately EXTERNAL, unlike a self-assessed "I'm running low" -- stop 3 of Epic A already
#: falsified that an agent's own predicted remaining capacity is a reliable trigger (it declared
#: a limit early, then worked productively well past the point it had declared). Advisory only:
#: PreCompact cannot block (see the module docstring), and neither does this -- it fires on
#: SessionStart, where the only lever is what enters context, not whether the session continues.
_COMPACTION_THRESHOLD_NOTICE = (
    "=== COMPACTION THRESHOLD ({n} on record this session/branch) ===",
    "",
    "This count is EXTERNAL evidence, not a self-assessment of how much capacity remains.",
    "Treat it, not how capable you currently feel, as the signal to seriously consider",
    "handing off now rather than continuing further sprints/branches in this session.",
    "",
)


def compaction_threshold_notice(payload: dict[str, Any]) -> str:
    """A deterministic nudge once `compaction_count` crosses `_COMPACTION_THRESHOLD` ("" below
    it). Fires on EVERY SessionStart, not only `source == "compact"` like `compaction_notice`
    above -- the count must stay visible even on a fresh, non-compacted start within the same
    session lineage, since that is exactly when a hand-off decision is still actionable."""
    count = compaction_count(payload)
    if count < _COMPACTION_THRESHOLD:
        return ""
    return "\n".join(line.format(n=count) for line in _COMPACTION_THRESHOLD_NOTICE)


def _ledger_shard(payload: dict[str, Any]) -> Path | None:
    """This session's provenance-ledger shard (`docs/dev/prov/SPEC.md`), or None."""
    session = payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session:
        return None
    return _project_dir(payload) / "docs" / "dev" / "ledger" / f"{session}.jsonl"


def compaction_count(payload: dict[str, Any]) -> int:
    """How many `compacted` receipts this session's ledger shard already holds."""
    shard = _ledger_shard(payload)
    if shard is None:
        return 0
    try:
        lines = shard.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    return sum(1 for line in lines if '"event": "compacted"' in line)


def record_compaction(payload: dict[str, Any]) -> bool:
    """PreCompact: append a durable `compacted` receipt. True iff one was written.

    PreCompact cannot inject context (see the module docstring), so the loss would otherwise
    leave no trace at all once the window is gone. Writing it to the session's own ledger
    shard makes the data-loss event **auditable after the fact** rather than merely warned
    about in the moment -- and it is what `restore_evidence` counts on the way back in.
    """
    shard = _ledger_shard(payload)
    if shard is None:
        return False
    # `session` mirrors `_ledger_shard`'s own fallback three lines up -- prior to this fix it
    # read `payload.get("session_id", "unknown")` with NO environment fallback, so every row
    # in every shard recorded "unknown" even though the SHARD FILENAME (which does fall back
    # to CLAUDE_CODE_SESSION_ID) was always correct. Verified: 52/52 historical rows across
    # every ledger shard in this repo had `"session": "unknown"`. Two adjacent functions, same
    # input, different fallback behavior -- this brings them into agreement.
    session = payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or "unknown"
    record = {
        "event": "compacted",
        "session": session,
        "branch": git_branch(str(_project_dir(payload))),
        # `agent_id` / `agent_type` are present in the PreToolUse payload inside a subagent
        # per the Claude Code hooks reference (see docs/dev/epic-a-chain-design-corrections.md
        # §14.7); captured here too, when present, so a `compacted` row can be attributed to
        # a subagent rather than conflated with the orchestrator's own compactions -- pure
        # enrichment of an existing non-blocking record, omitted (not null-padded) when absent
        # so a main-session compaction's row stays exactly as it was before this change.
        **({"agent_id": payload["agent_id"]} if payload.get("agent_id") else {}),
        **({"agent_type": payload["agent_type"]} if payload.get("agent_type") else {}),
        # KNOWN GAP, not fixed here (C-12: declare, don't guess-fix): `trigger` also reads
        # "unknown" in all 52 historical rows, but unlike `session` above, the code's own
        # handling is already correct and already tested
        # (tests/test_c12_disclosure_gate.py:156-168 round-trips a literal `{"trigger": "auto"}`
        # payload through this exact function and asserts it comes through unchanged). That
        # means the defect, if real, is upstream -- either real PreCompact payloads in this
        # harness never carry a `trigger` key, or it arrives under a different name -- and
        # verifying which requires inspecting a live payload, not guessing a fallback with
        # nothing to fall back to (unlike `session_id`, there is no known environment-variable
        # equivalent for `trigger`). Filed as a work item rather than silently patched.
        "trigger": payload.get("trigger", "unknown"),
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        shard.parent.mkdir(parents=True, exist_ok=True)
        with shard.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        return False  # never wedge a compaction over a failed write
    return True


def compaction_notice(payload: dict[str, Any]) -> str:
    """The C-12 information-loss declaration, or "" when this is not a post-compaction start."""
    if payload.get("source") != "compact":
        return ""
    return "\n".join(line.format(n=compaction_count(payload)) for line in _COMPACTION_NOTICE)


def restore_evidence(payload: dict[str, Any]) -> str:
    """SessionStart: the text to replay into the fresh context ("" = stay silent).

    Silent unless there is genuinely something to say — a hook that greets every session with
    boilerplate trains the reader to skip it, and then it is worthless on the day it matters.
    """
    notice = compaction_notice(payload) + compaction_threshold_notice(payload)
    branch, path, text = _dossier(payload)
    if not branch.startswith("fix/") or text is None:
        return notice  # C-12: the loss is announced even with no dossier to replay
    body = replay_text(text)
    if not body:
        return notice
    shown = path.as_posix()
    if len(body) > _MAX_REPLAY_CHARS:
        body = body[:_MAX_REPLAY_CHARS].rstrip() + _TRUNCATED.format(path=shown)
    preamble = "\n".join(line.format(path=shown) for line in _PREAMBLE)
    return notice + preamble + body


def capture_before_compact(payload: dict[str, Any]) -> str:
    """PreCompact: a warning **for the user** ("" = stay silent).

    Cannot reach Claude (PreCompact has no context injection — see the module docstring), so
    this speaks to the one party who can actually intervene: the human watching the session.
    """
    branch, path, text = _dossier(payload)
    if not branch.startswith("fix/"):
        return ""
    if text is not None and has_observed_evidence(text, template_text(_project_dir(payload))):
        return ""  # evidence is on disk — the compaction is safe, say nothing
    return (
        f"⚠ Context is about to be compacted, and '{branch}' has no captured evidence "
        f"({path.as_posix()} is missing or its '## Observed' section is empty). "
        "Anything learned this session that is not written down is about to be lost — "
        "that is charter C-8, and it is exactly how a day got burned once already."
    )


def main(argv: list[str]) -> int:
    """CLI entry point: `argv[1]` is the hook name, stdin is the hook payload."""
    # `restore-evidence` replays whatever prose the dossier holds -- em-dashes, arrows, box
    # characters. On Windows stdout defaults to the locale codepage (cp1252), which mangles
    # all of it, so the context Claude gets back would be corrupted exactly where it is most
    # load-bearing. Force UTF-8; the hook runner reads it as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    if len(argv) != 2 or argv[1] not in _HOOK_NAMES:
        print(f"usage: claude_context_hook.py <{'|'.join(_HOOK_NAMES)}>", file=sys.stderr)
        return 2

    raw = sys.stdin.read()
    try:
        payload: dict[str, Any] = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    if argv[1] == "restore-evidence":
        # Plain stdout — SessionStart adds it to Claude's context verbatim, no JSON needed.
        if message := restore_evidence(payload):
            print(message)
    else:
        # PreCompact. The receipt is written UNCONDITIONALLY -- the warning below fires
        # only when evidence is missing, but the data-loss EVENT is always worth recording
        # (charter C-12), and it is what the SessionStart notice counts on the way back in.
        record_compaction(payload)
        if message := capture_before_compact(payload):
            # PreCompact reaches the USER only, and only via `systemMessage`.
            print(json.dumps({"systemMessage": message}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
