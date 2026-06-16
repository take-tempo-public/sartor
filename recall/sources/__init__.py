"""`recall.sources` — the concrete retrieval tiers (Stage 1, Sprint 7.5).

The S1 wiki, S2 `git grep`, and S5-P1 session-buffer `Source` implementations that
turn the Stage-0 substrate into a working assistant. Each is **project-agnostic by
construction** — roots and the audience resolver are injected at construction, so no
module here hardcodes a project path or a project audience rule. That keeps the whole
`recall/` package stdlib-only and refactor-immune (`tests/test_recall_boundary.py`,
including the `recall/sources/` no-hardcoded-roots guard). The callback-specific
bindings live in the wiring layer (`blueprints/assistant.py`), never here.

See `docs/dev/memory-architecture.md` §"Tiers" for the family model and §"Reuse
boundary" for why the generic tiers ship inside `recall/`.
"""

from __future__ import annotations

from recall.sources.git_grep_source import GitGrepSource
from recall.sources.session_source import SessionSource
from recall.sources.wiki_source import WikiSource

__all__ = [
    "GitGrepSource",
    "SessionSource",
    "WikiSource",
]
