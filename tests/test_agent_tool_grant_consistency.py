"""A subagent must not be told to create a file its tool grant cannot create (item 141).

`agents/wiki-scribe.md` granted `Read`/`Grep`/`Glob`/`Edit` while its step 5 said
"create `pages/<kebab-slug>.md`". `Edit` cannot create a file, so three runs returned the
page text and reported the creation as "delegated to orchestrator"; nothing on the
orchestrator side said that would happen. This pins the grant and the instructions together
for every subagent: no `Write` (and no `Bash`) means no instruction to create a file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
_CREATE_FILE = re.compile(r"(?i)\bcreate\s+`[^`\s]+\.\w+`")


def _split(path: Path) -> tuple[list[str], str]:
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    tools = re.findall(r"^\s+-\s+(\w+)\s*$", front.split("tools:", 1)[-1], flags=re.M)
    return tools, body


def _agent_files() -> list[Path]:
    files = sorted(_AGENTS_DIR.glob("*.md"))
    assert files, f"no subagent definitions found under {_AGENTS_DIR}"
    return files


@pytest.mark.parametrize("path", _agent_files(), ids=lambda p: p.stem)
def test_no_create_instruction_without_a_creating_tool(path: Path) -> None:
    tools, body = _split(path)
    assert tools, f"{path.name}: no tools: list parsed from frontmatter"
    if "Write" in tools or "Bash" in tools:
        return
    hits = _CREATE_FILE.findall(body)
    assert not hits, (
        f"{path.name} grants {tools} (no Write/Bash) but instructs {hits}; "
        "say what to hand back instead, or grant the tool"
    )


@pytest.mark.parametrize(
    "path", [*_agent_files(), _AGENTS_DIR.parent / "SECURITY.md"], ids=lambda p: p.stem
)
def test_no_retired_plugin_hook_path(path: Path) -> None:
    """Item 54: hooks moved from `.claude-plugin/hooks/` to root `hooks/`, and since item 152
    there are no hook scripts at all (each hook is `python3 hook.py <name>`). A live doc
    naming either old path sends a reader to a file that does not exist."""
    text = path.read_text(encoding="utf-8")
    assert ".claude-plugin/hooks" not in text, path.name
    assert not re.search(r"\bhooks/[\w/-]+\.sh\b", text), path.name
    assert not (_AGENTS_DIR.parent / ".claude-plugin" / "hooks").exists()


def test_the_check_catches_the_original_wording() -> None:
    """Control arm: the pre-fix step 5 wording must trip the pattern."""
    original = "5. **For a genuinely new concept** with no existing page, create\n   `pages/<kebab-slug>.md` with the full SCHEMA shape"
    assert _CREATE_FILE.search(original)
