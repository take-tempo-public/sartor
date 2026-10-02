"""The docs assistant's path -> audience rule tracks the Epic D docs tree.

WHY: `blueprints/assistant.py:_path_audience` decides which repo docs a user-mode assistant
turn may draw on. Epic D D2 moved the user docs from `docs/install.md` / `docs/walkthrough*.md`
into `docs/user/`. A stale prefix would silently drop them from user-mode answers (they'd
fall through to the safe `dev` default), so this pins the rule to the tree.

D4 (re-verified against the new tree): the publication registry, `scripts/doc_registry.py`,
is the single home of each doc's tier, so it is the oracle here. The check found
`ACCESSIBILITY.md` (user tier) resolving `dev`; a doc added to the registry later can't
drift the same way unseen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from blueprints.assistant import _path_audience
from recall import Audience

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from doc_registry import PUBLISHED


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


@pytest.mark.parametrize("entry", PUBLISHED, ids=lambda e: e.path)
def test_every_registered_doc_resolves_to_its_registry_tier(entry) -> None:
    want = Audience.USER if entry.tier == "user" else Audience.DEV
    assert _path_audience(entry.path) is want, f"{entry.path}: registry tier {entry.tier}"


@pytest.mark.parametrize(
    ("path", "want"),
    [
        ("docs/user/README.md", Audience.USER),  # the user front door
        ("docs/dev/README.md", Audience.DEV),  # a README under a dev prefix is not the root README
        ("docs/work/BOARD.md", Audience.DEV),  # tracking, falls to the safe default
        ("docs/ux/notes.md", Audience.DEV),
        ("docs\\user\\install.md", Audience.USER),  # Windows separators
        ("docs\\dev\\tooling.md", Audience.DEV),
        ("docs/user/helper.py", Audience.DEV),  # code is dev wherever it sits
    ],
)
def test_edge_paths(path: str, want: Audience) -> None:
    assert _path_audience(path) is want
