"""The docs assistant's path -> audience rule tracks the Epic D docs tree.

WHY: `blueprints/assistant.py:_path_audience` decides which repo docs a user-mode assistant
turn may draw on. Epic D D2 moved the user docs from `docs/install.md` / `docs/walkthrough*.md`
into `docs/user/`. A stale prefix would silently drop them from user-mode answers (they'd
fall through to the safe `dev` default), so this pins the rule to the tree.
"""

from __future__ import annotations

from blueprints.assistant import _path_audience
from recall import Audience


def test_user_tier_docs_are_user() -> None:
    for path in (
        "README.md",
        "vision.md",
        "docs/user/install.md",
        "docs/user/walkthrough.md",
        "docs/user/walkthrough-example.md",
    ):
        assert _path_audience(path) is Audience.USER, path


def test_dev_docs_and_code_are_dev() -> None:
    for path in ("docs/dev/architecture.md", "app.py", "docs/governance/charter.md", "AGENTS.md"):
        assert _path_audience(path) is Audience.DEV, path
