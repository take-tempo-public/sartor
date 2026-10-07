#!/usr/bin/env python3
"""PostToolUse hook on Bash: after a ``git commit``, a NON-BLOCKING nudge when ``docs/wiki/``
may be stale. A witness, never a gate: it always returns 0.

A reminder, not an auto-ingest: an ingest costs LLM tokens, so the hook only surfaces the
drift and a human decides when to pay for one (``docs/wiki/SCHEMA.md`` "Ops").

Ported from ``hooks/wiki-freshness-reminder.sh`` (item 152). The drift count is
``scripts.wiki_freshness.drift_count``, the same classification the merge-blocking gate uses.
Below ``THRESHOLD`` it nudges toward ``/wiki-ingest``; at or above it, toward the bounded
``/wiki-self-update`` loop. Only the words change.

Silent when:
- the command was not a ``git commit``. Only ``tool_input.command`` is read, never the tool's
  output; the retired merge hook's output-grep false-fired (diagnosis O2);
- ``docs/wiki/.last_ingest_sha`` has no real baseline yet;
- nothing wiki-relevant changed since it.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.gitutil import repo_root  # noqa: E402

THRESHOLD = 10
_COMMIT = re.compile(r"\bgit\s+commit\b")


def message(payload: dict[str, Any]) -> str:
    """The ``systemMessage`` text, or "" to stay silent."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not _COMMIT.search(command):
        return ""
    from scripts.wiki_freshness import drift_count, last_ingest_sha

    # The repo the command ran in; `repo_root` alone falls back to CLAUDE_PROJECT_DIR (item 148).
    cwd = str(payload.get("cwd") or ".")
    root = repo_root(cwd, os.environ, default=cwd)
    sha = last_ingest_sha(root)
    if sha is None:
        return ""
    changed = drift_count(root, sha)
    if not changed:
        return ""
    short = sha[:8]
    if changed >= THRESHOLD:
        return (
            f"wiki may be stale: {changed} file(s) changed since the last ingest ({short}) "
            "— the diff is large enough to run the loop. Consider /wiki-self-update "
            "(bounded Haiku diff-pass); /wiki-lint for the drift report."
        )
    return (
        f"wiki may be stale: {changed} file(s) changed since the last ingest ({short}). "
        "Consider /wiki-ingest; /wiki-lint for the drift report."
    )


def main(argv: list[str]) -> int:
    del argv
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        text = message(payload) if isinstance(payload, dict) else ""
    except Exception:
        return 0
    if text:
        print(json.dumps({"systemMessage": text}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
