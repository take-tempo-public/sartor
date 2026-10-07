"""Item 152's rule as a gate: every Claude Code hook is Python, launched directly.

Each ``.claude/settings.json`` hook command must be exactly::

    python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>

with ``<name>`` registered in ``hook.HOOKS``. No ``.sh`` file and no shell interpreter. Why:
the shell wrappers made enforcement depend on whichever bash the harness found (item 152's
busy-looping Monitor). They also cost an MSYS start-up per hook, and under memory pressure
that pushed the gates past their timeouts. A cancelled PreToolUse hook does not block
(``docs/dev/diagnosis/python-direct-hooks-plan-gate.md`` O1).
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.enforcement.adapters import hook

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

COMMAND_SHAPE = re.compile(
    r'^python3 "\$\{CLAUDE_PROJECT_DIR\}/scripts/enforcement/adapters/hook\.py" (?P<name>[a-z-]+)$'
)
SHELLS = re.compile(
    r"(?:^|[\s/\\\"'])(?:bash|sh|zsh|dash|pwsh|powershell|cmd)(?:\.exe)?(?:[\s\"']|$)"
)


def _commands(settings: dict[str, Any]) -> list[tuple[str, str]]:
    """(event, command) for every hook in a settings document."""
    return [
        (event, h.get("command", ""))
        for event, groups in settings.get("hooks", {}).items()
        for group in groups
        for h in group.get("hooks", [])
    ]


def violations(settings: dict[str, Any]) -> list[str]:
    """Every way a settings document breaks the rule; [] when it holds."""
    found: list[str] = []
    for event, command in _commands(settings):
        if ".sh" in command:
            found.append(f"{event}: invokes a .sh file: {command}")
        if SHELLS.search(command):
            found.append(f"{event}: invokes a shell interpreter: {command}")
        m = COMMAND_SHAPE.match(command)
        if m is None:
            found.append(f"{event}: not the hook.py shape: {command}")
        elif m["name"] not in hook.HOOKS:
            found.append(f"{event}: '{m['name']}' is not in hook.HOOKS")
    return found


def _settings() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SETTINGS.read_text(encoding="utf-8"))
    return data


def test_every_settings_hook_is_python_direct() -> None:
    assert violations(_settings()) == []


def test_every_registered_hook_is_wired_exactly_once() -> None:
    names = [COMMAND_SHAPE.match(c)["name"] for _, c in _commands(_settings())]  # type: ignore[index]
    assert sorted(names) == sorted(hook.HOOKS), (
        "hook.HOOKS and the settings wiring must name the same hooks, once each"
    )


def test_the_rule_rejects_a_shell_wrapper() -> None:
    """Mutation check: the shapes this gate exists to refuse are refused."""
    for bad in (
        "${CLAUDE_PROJECT_DIR}/hooks/check-plan-approved.sh",
        'bash "${CLAUDE_PROJECT_DIR}/scripts/x.py"',
        'python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" no-such-hook',
        'pwsh -c "python3 x.py"',
    ):
        doc = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": bad}]}]}}
        assert violations(doc), f"not refused: {bad}"


def test_every_handler_module_has_a_main() -> None:
    for name, (module_name, _) in hook.HOOKS.items():
        module = importlib.import_module(module_name)
        assert callable(getattr(module, "main", None)), f"{name}: {module_name} has no main()"


def test_an_unknown_hook_name_never_blocks() -> None:
    """Exit 2 would block every call on that matcher (and wedge prompt submission on
    UserPromptSubmit); a misconfiguration must be loud on stderr instead, never a gate."""
    assert hook.main(["hook.py", "no-such-hook"]) == 1
    assert hook.main(["hook.py"]) == 1


def test_no_shell_hook_scripts_remain() -> None:
    assert not list((REPO_ROOT / "hooks").glob("**/*.sh")), "hooks/*.sh were retired by item 152"
