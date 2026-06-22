"""Corpus seam — the Career-Corpus CRUD + curation family of routes.

The third (and largest) domain blueprint extracted from `app.py` (Sprint 8.3d,
the app.py -> blueprints decomposition). Owns the 42 routes that manage a
candidate's structured corpus — experiences, bullets, titles, summaries,
experience-summaries, skills, tags, duplicates, resume upload + ingest, the
pending-review accept workflow, and the LLM-proposal lifecycle (critique /
decide / promote-to-bullet).

Authored as a **sub-package** (owner decision, Sprint 8.3d): one
`corpus_bp = Blueprint("corpus", __name__)` (defined in `_bp.py`); the route
submodules attach their handlers to it; the cross-cutting serializers live in
`_shared.py`. Registered with **no url_prefix** so the full `/api/...` paths stay
byte-identical.

Submodules (route count):
    experiences.py  experiences + bullets + titles + experience-summaries (15)
    summaries.py    candidate-level summary items (4)
    skills.py       skills (4)
    tags.py         tag suggest + link/unlink (7) + tag-mutation helpers
    curation.py     upload + list-resumes + duplicates + ingest + accept + pending-counts (9)
    proposals.py    critique + decide + promote-to-bullet (3) — the only `anthropic` submodule

Import-order contract (circular-import-safe): `corpus_bp` comes from `_bp` (a leaf),
then the shared serializers are re-exported (for `app.py`'s still-resident
applications routes, which import `_tag_list` / `_skill_to_dict` from here per the
Sprint 8.3d owner decision), then the route submodules are imported for their
decorator side-effects. Submodules import `corpus_bp` from `._bp` and serializers
from `._shared`; neither imports anything from this package root. Like every
blueprint, this package never imports `app.py` (leaf-ward direction only); DB-layer
imports stay lazy inside each function.
"""

from __future__ import annotations

from blueprints.corpus._bp import corpus_bp
from blueprints.corpus._shared import _skill_to_dict, _tag_list

__all__ = ["_skill_to_dict", "_tag_list", "corpus_bp"]
