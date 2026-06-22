"""The shared `corpus_bp` Blueprint object for the corpus sub-package.

Isolated in its own tiny module so every route submodule can
`from blueprints.corpus._bp import corpus_bp` without an import cycle, and so the
package `__init__` keeps all imports at the top of the file (no E402). Defined here
rather than in `__init__` because `__init__` imports the route submodules for their
decorator side-effects, and those submodules need `corpus_bp` to already exist.
"""

from __future__ import annotations

from flask import Blueprint

corpus_bp = Blueprint("corpus", __name__)
