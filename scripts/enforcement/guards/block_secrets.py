"""block-secrets guard.

Blocks tool input that contains an Anthropic API key, a hard-coded credential
env-var assignment, or an Edit/Write to a known secret-file path. Reading
these files is fine; only writing/embedding is blocked. Ported from
`.claude-plugin/hooks/block-secrets.sh` (behavior preserved byte-for-byte;
see `tests/test_enforcement_core.py`).
"""

from __future__ import annotations

import re
from typing import Any

from scripts.enforcement import gitutil
from scripts.enforcement.guards.result import GuardResult

_API_KEY_RE = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")
_ENV_ASSIGN_RE = re.compile(
    r"(?:ANTHROPIC_API_KEY|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN)="
    r"[A-Za-z0-9_-]{16,}"
)
_SECRET_PATH_RE = re.compile(
    r"(^|/)(\.api_key|\.env|\.env\.[A-Za-z0-9_-]+|[^/]+\.pem|[^/]+\.p12|[^/]+\.key|[^/]+\.crt)$"
)

_API_KEY_MESSAGE = (
    "BLOCKED (block-secrets): Anthropic API key detected in tool input.",
    "Never embed API keys in code, commands, or commits.",
)
_ENV_ASSIGN_MESSAGE = (
    "BLOCKED (block-secrets): Hard-coded API-key env-var assignment detected.",
    "Set credentials in your shell before launching Claude, not in tool input.",
)


def _secret_file_message(norm_path: str) -> tuple[str, ...]:
    return (
        f"BLOCKED (block-secrets): Edit/Write to a secret file ({norm_path}).",
        "Modify these outside Claude Code so the contents don't appear in transcripts.",
    )


def haystack(tool_input: dict[str, Any]) -> str:
    """The same haystack the original hook scans: command / file_path / new_string / content."""
    parts = [
        tool_input.get("command", ""),
        tool_input.get("file_path", ""),
        tool_input.get("new_string", ""),
        tool_input.get("content", ""),
    ]
    return "\n".join(p for p in parts if isinstance(p, str) and p)


def decide(tool_name: str, tool_input: dict[str, Any]) -> GuardResult:
    """Pure decision, in the original hook's exact check order."""
    text = haystack(tool_input)

    if _API_KEY_RE.search(text):
        return GuardResult.block(*_API_KEY_MESSAGE)

    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "") or ""
        norm = file_path.replace("\\", "/")
        if _SECRET_PATH_RE.search(norm):
            return GuardResult.block(*_secret_file_message(norm))

    if _ENV_ASSIGN_RE.search(text):
        return GuardResult.block(*_ENV_ASSIGN_MESSAGE)

    return GuardResult.allow()


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_name` + `tool_input`."""
    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}
    return decide(tool_name, tool_input)


def git_precommit_check() -> GuardResult:
    """Native git pre-commit adapter: scan staged file paths + staged content.

    Git already knows the full staged set — no JSON `tool_input` to parse, and
    (unlike the Claude adapter, which sees one proposed edit at a time) every
    staged file is checked in one pass.
    """
    staged_paths = gitutil.staged_files()

    for path in staged_paths:
        norm = path.replace("\\", "/")
        if _SECRET_PATH_RE.search(norm):
            return GuardResult.block(*_secret_file_message(norm))

    text = "\n".join(gitutil.staged_content(path) for path in staged_paths)
    if _API_KEY_RE.search(text):
        return GuardResult.block(*_API_KEY_MESSAGE)
    if _ENV_ASSIGN_RE.search(text):
        return GuardResult.block(*_ENV_ASSIGN_MESSAGE)

    return GuardResult.allow()
