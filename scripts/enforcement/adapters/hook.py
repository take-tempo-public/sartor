#!/usr/bin/env python3
"""The one launcher every ``.claude/settings.json`` hook runs (item 152).

Each settings entry is exactly::

    python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>

``<name>`` is the hook's identity: the same name ``docs/dev/tooling.md`` lists and
``tests/test_governance_hooks_gate.py`` classifies. There is no shell wrapper in between.
Hooks used to be ``hooks/<name>.sh`` files that ``exec``-ed Python. A bash in the chain
made enforcement depend on whichever bash the harness found (item 152's busy-looping
Monitor). It also cost an MSYS start-up per hook on Windows (item 111).
``tests/test_settings_hooks_python_direct.py`` fails if a settings command takes any other
shape.

The handler module is imported only for the name being run, so a hook pays for its own
imports and nothing else. The interpreter name ``python3`` is the one every retired wrapper
``exec``-ed. **Known limit (C-0):** a machine whose Python has no ``python3`` on PATH (a
python.org Windows install) cannot start any hook, and the harness treats that as a
non-blocking error, so the gates fail open. The ``shell-probe`` hook cannot report it, since
it needs ``python3`` too. ``docs/governance/enforcement.md`` records this.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

#: Hook name -> (handler module, the argv tail its ``main`` expects).
HOOKS: dict[str, tuple[str, tuple[str, ...]]] = {
    "edit-write-dispatcher": ("scripts.enforcement.adapters.claude_dispatcher", ()),
    "bash-dispatcher": ("scripts.enforcement.adapters.bash_dispatcher", ()),
    "plan-write-landed": ("scripts.enforcement.plan_gate", ("plan-write-landed",)),
    "mark-plan-approved": ("scripts.enforcement.plan_gate", ("mark-plan-approved",)),
    "wiki-freshness-reminder": ("scripts.enforcement.adapters.wiki_reminder_hook", ()),
    "interrogative-prompt-witness": ("scripts.enforcement.adapters.prompt_witness_hook", ()),
    "restore-evidence": ("scripts.enforcement.adapters.claude_context_hook", ("restore-evidence",)),
    "capture-before-compact": (
        "scripts.enforcement.adapters.claude_context_hook",
        ("capture-before-compact",),
    ),
    "shell-probe": ("scripts.enforcement.shell_probe", ()),
}


def main(argv: list[str]) -> int:
    """``argv[1]`` is a name in ``HOOKS``; stdin is the hook payload, read by the handler."""
    if len(argv) != 2 or argv[1] not in HOOKS:
        print(f"usage: hook.py <{'|'.join(HOOKS)}>", file=sys.stderr)
        return 1  # not 2: a misconfigured hook must not block every tool call
    module_name, tail = HOOKS[argv[1]]
    module = importlib.import_module(module_name)
    result: int = module.main([module_name, *tail])
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv))
