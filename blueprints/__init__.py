"""`blueprints/` — Flask route modules split out of the `app.py` monolith.

Born in Sprint 7.5 with the doc-grounded assistant (`assistant.py`). It is
deliberately blueprint-shaped so the v1.0.8 `app.py`→blueprints refactor (§Phase 4.8,
8.3) is a *move* of the remaining routes into this package, not a rewrite. Mirrors the
existing `dashboard/` blueprint package.
"""

from __future__ import annotations

from blueprints.analysis import analysis_bp
from blueprints.assistant import assistant_bp
from blueprints.corpus import corpus_bp
from blueprints.generation import generation_bp

__all__ = ["analysis_bp", "assistant_bp", "corpus_bp", "generation_bp"]
