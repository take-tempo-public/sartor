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

Invoked by the thin wrappers in `.claude-plugin/hooks/`:

    exec python3 "$CLAUDE_PROJECT_DIR/scripts/enforcement/adapters/claude_context_hook.py" <name>
"""

from __future__ import annotations

import json
import os
import sys
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


def restore_evidence(payload: dict[str, Any]) -> str:
    """SessionStart: the text to replay into the fresh context ("" = stay silent).

    Silent unless there is genuinely something to say — a hook that greets every session with
    boilerplate trains the reader to skip it, and then it is worthless on the day it matters.
    """
    branch, path, text = _dossier(payload)
    if not branch.startswith("fix/") or text is None:
        return ""
    body = replay_text(text)
    if not body:
        return ""
    shown = path.as_posix()
    if len(body) > _MAX_REPLAY_CHARS:
        body = body[:_MAX_REPLAY_CHARS].rstrip() + _TRUNCATED.format(path=shown)
    preamble = "\n".join(line.format(path=shown) for line in _PREAMBLE)
    return preamble + body


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
    elif message := capture_before_compact(payload):
        # PreCompact reaches the USER only, and only via `systemMessage`.
        print(json.dumps({"systemMessage": message}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
