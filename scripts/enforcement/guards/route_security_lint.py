"""route-security-lint guard.

A new/edited Flask route (`app.py` or `blueprints/**.py`) that touches the
filesystem must call both `_safe_username()` and `_within()` (charter C-1 /
`docs/governance/enforcement.md` F-sec-05). Ported from
`.claude-plugin/hooks/route-security-lint.sh` (behavior preserved
byte-for-byte; see `tests/test_enforcement_core.py`). Heuristic, not perfect —
`tests/test_route_containment_gate.py` is the whole-tree, AST-based
do-not-regress gate this hook only samples at edit time.

Scope (PX-21, v1.0.8 blueprint split): `app.py` + `blueprints/**.py`. The
read-only `dashboard/` diagnostics surface is deliberately NOT covered — its
routes are localhost-gated, take no `<username>`, and read fixed diagnostic
dirs, so the `_safe_username`/`_within` user-path guards do not apply there.
"""

from __future__ import annotations

import re
from typing import Any

from scripts.enforcement import gitutil
from scripts.enforcement.guards.result import GuardResult

_ROUTE_FILE_RE = re.compile(r"(^|/)app\.py$|(^|/)blueprints/.*\.py$")
_ROUTE_DECORATOR_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*\.(route|get|post|put|delete|patch)\(")
_FS_INDICATOR_RE = re.compile(
    r"\b(open\(|send_file\(|send_from_directory\(|Path\(|read_text\(|write_text\("
    r"|\.exists\(\)|os\.path\.|RESUMES_DIR|OUTPUT_DIR)\b"
)

_MESSAGE_TEMPLATE = (
    "BLOCKED (route-security-lint): proposed route-module edit defines a route",
    "that touches the filesystem without calling:{missing}",
    "",
    "See CLAUDE.md 'Key Patterns — Security' for the required call sequence.",
    "If this is a false positive (e.g., a partial Edit that doesn't show the",
    "guards), include the full route block in the new_string.",
)


def decide(file_path: str, content: str) -> GuardResult:
    """Pure decision over one file's proposed/committed content."""
    norm = (file_path or "").replace("\\", "/")
    if not _ROUTE_FILE_RE.search(norm):
        return GuardResult.allow()
    if not content:
        return GuardResult.allow()
    if not _ROUTE_DECORATOR_RE.search(content):
        return GuardResult.allow()
    if not _FS_INDICATOR_RE.search(content):
        return GuardResult.allow()

    missing = ""
    if "_safe_username" not in content:
        missing += " _safe_username()"
    if "_within" not in content:
        missing += " _within()"
    if not missing:
        return GuardResult.allow()

    lines = tuple(line.format(missing=missing) for line in _MESSAGE_TEMPLATE)
    return GuardResult.block(*lines)


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: extract `file_path` + the proposed `new_string`/`content`."""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "") or ""
    content = tool_input.get("new_string", "") or tool_input.get("content", "") or ""
    return decide(file_path, content)


def git_precommit_check() -> GuardResult:
    """Native git pre-commit adapter: scan each staged route file's FULL staged
    content.

    Git shows the whole file, not a hunk — a STRONGER check than the Claude
    adapter (which only sees one proposed Edit's `new_string`), matching the
    whole-file scope `tests/test_route_containment_gate.py` already commits
    as the do-not-regress gate. Hunk-level diffing isn't attempted here: git
    doesn't expose it simply, and whole-file is the correct, already-validated
    unit for this check.
    """
    for path in gitutil.staged_files():
        norm = path.replace("\\", "/")
        if not _ROUTE_FILE_RE.search(norm):
            continue
        content = gitutil.staged_content(path)
        result = decide(path, content)
        if result.blocked:
            return result
    return GuardResult.allow()
