"""Fail-closed gate on the UX harness's `_get_client` coverage (charter C-11).

**Why this file exists — the measurement, not a vibe.** The same defect has been
found three separate times by three separate investigations, each time by a
person reading code, never by a mechanism:

- **item 21** — `check_refinement_scope` was unstubbed, so every UX refinement
  flow was silently exercising only that call's fail-open path. Found while
  diagnosing something else.
- **item 22's diagnosis** (`docs/dev/diagnosis/never-logged-call-kinds.md`) — a
  latent `draft_surgical_refinement` stub gap, fixed prophylactically.
- **item 34** — `blueprints/corpus/skills.py` and `blueprints/corpus/proposals.py`
  bind `_get_client` at import time and were covered by none of the four
  `monkeypatch.setattr` lines `install_llm_stubs` carried. On a developer machine
  with a valid `.api_key` — which this repo's own `CLAUDE.local.md` documents as
  the norm — that is a **real, billed Anthropic API call** the moment any UX test
  reaches one of those routes, with no assertion pointing at the cost.

Item 34's own hand-written `refs` list named two corpus modules. Enumerating
fresh on `feat/role-summary-drafting` found **four** unpatched modules:
`blueprints/corpus/curation.py` and `blueprints/assistant.py` as well. That is
C-10's "a hand-maintained consumer list is stale until re-derived", observed
directly, and it is why the fix for item 34 is this test rather than two more
`setattr` lines.

**What it asserts.** The set of `blueprints/**.py` modules that bind
`_get_client` at import time is EXACTLY
`tests.ux.stubs._GET_CLIENT_BLUEPRINT_MODULES`. Both directions matter: an
unlisted module is an unstubbed billed-call path; a listed module that no longer
imports the name is a stale entry that would make `monkeypatch.setattr` fail
noisily later, in an unrelated test.

**Stated limit (C-0).** This proves the *client* is neutralized for every
blueprint that resolves `_get_client` from its own namespace. It does NOT prove
every analyzer entry point is stubbed — a route that reaches a real analyzer
function with a `None` client still produces an error row rather than a billed
call, which is the failure item 21 documents. That second half stays covered by
`tests/test_call_kind_telemetry.py` and by the per-function `fake_*` stubs, not
by this file.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLUEPRINTS_DIR = REPO_ROOT / "blueprints"


def _module_name(path: Path) -> str:
    """`blueprints/corpus/skills.py` -> `blueprints.corpus.skills`."""
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(rel.parts)


def _binds_get_client(tree: ast.AST) -> bool:
    """True when this module binds the NAME `_get_client` at import time.

    Catches both forms the repo actually uses:
    `from web_infra import _get_client, ...` and
    `from web_infra import (\\n    _get_client,\\n ...)` — the same node either
    way. A local `from x import _get_client` inside a function body would also
    match; that is deliberate, since such a module still needs patching (the
    name it resolves at call time is the real one).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(
            alias.asname is None and alias.name == "_get_client" for alias in node.names
        ):
            return True
    return False


def _blueprint_modules_binding_get_client() -> set[str]:
    found: set[str] = set()
    for path in sorted(BLUEPRINTS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _binds_get_client(tree):
            found.add(_module_name(path))
    return found


def test_every_blueprint_binding_get_client_is_stubbed_in_the_ux_harness() -> None:
    from tests.ux.stubs import _GET_CLIENT_BLUEPRINT_MODULES

    declared = set(_GET_CLIENT_BLUEPRINT_MODULES)
    found = _blueprint_modules_binding_get_client()

    unstubbed = found - declared
    assert not unstubbed, (
        f"Blueprint module(s) bind `_get_client` but are NOT patched by "
        f"tests/ux/stubs.py::install_llm_stubs: {sorted(unstubbed)}. On a machine "
        f"with a real .api_key this is a billed Anthropic call the moment a UX "
        f"test reaches one of their routes (work item 34). Add each to "
        f"_GET_CLIENT_BLUEPRINT_MODULES."
    )

    stale = declared - found
    assert not stale, (
        f"_GET_CLIENT_BLUEPRINT_MODULES names module(s) that no longer bind "
        f"`_get_client`: {sorted(stale)}. Remove them — monkeypatch.setattr on a "
        f"missing attribute raises, so a stale entry breaks the whole UX tier."
    )


def test_the_walk_actually_finds_something() -> None:
    """Guard against the guard silently passing on an empty set.

    An AST walk that finds zero modules would make the assertions above
    vacuously true forever. This is the control arm: `blueprints/applications.py`
    is known to bind `_get_client` and must appear.
    """
    found = _blueprint_modules_binding_get_client()
    assert len(found) >= 4, f"suspiciously few blueprint modules found: {sorted(found)}"
    assert "blueprints.applications" in found
