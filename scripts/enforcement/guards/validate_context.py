"""validate-context guard.

`output/**/context_*.json` proposed content must be valid JSON (and pass the
`context_set` schema once `evals/schemas/context_set.schema.json` exists).
Ported from `.claude-plugin/hooks/validate-context.sh` (behavior preserved
byte-for-byte; see `tests/test_enforcement_core.py`). These files are
normally written by the running app via `hardening.save_context_set()`; an
Edit/Write or a staged commit touching one usually means debugging or replay
— guard against malformed JSON either way.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.enforcement import gitutil
from scripts.enforcement.guards.result import GuardResult

_CONTEXT_PATH_RE = re.compile(r"(^|/)output/[^/]+/context_[^/]*\.json$")


def _schema_path(repo_root: Path) -> Path:
    return repo_root / "evals" / "schemas" / "context_set.schema.json"


def decide(file_path: str, content: str, repo_root: Path) -> GuardResult:
    """Pure decision over one context-set file's proposed/committed content."""
    norm = (file_path or "").replace("\\", "/")
    if not _CONTEXT_PATH_RE.search(norm):
        return GuardResult.allow()
    if not content:
        return GuardResult.allow()

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return GuardResult.block(
            f"BLOCKED (validate-context): Proposed content for {norm} is not valid JSON."
        )

    schema_path = _schema_path(repo_root)
    if schema_path.is_file():
        try:
            import jsonschema
        except ImportError:
            return GuardResult.allow()  # jsonschema not installed; skip silently
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as exc:
            return GuardResult.block(
                f"BLOCKED (validate-context): schema violation — {exc.message}"
            )

    return GuardResult.allow()


def claude_check(payload: dict[str, Any], repo_root: Path) -> GuardResult:
    """Claude PreToolUse adapter: extract `file_path` + the proposed `new_string`/`content`."""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "") or ""
    content = tool_input.get("new_string", "") or tool_input.get("content", "") or ""
    return decide(file_path, content, repo_root)


def git_precommit_check(repo_root: Path) -> GuardResult:
    """Native git pre-commit adapter: scan any staged context-set files.

    `output/` is gitignored (AGENTS.md), so this is defense-in-depth for the
    rare `git add -f` case rather than a path that fires in normal use.
    """
    for path in gitutil.staged_files():
        norm = path.replace("\\", "/")
        if not _CONTEXT_PATH_RE.search(norm):
            continue
        content = gitutil.staged_content(path)
        result = decide(path, content, repo_root)
        if result.blocked:
            return result
    return GuardResult.allow()
