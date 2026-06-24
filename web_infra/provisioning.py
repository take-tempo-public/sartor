"""Candidate provisioning helper shared by `app.py` and the blueprints.

`_get_or_provision_candidate` returns the candidate row for a user, creating it
from the user's config on first corpus write. It moved here (Sprint 8.3a) from
`app.py` and takes an explicit `configs_dir` (keyword-only) that it threads into
`onboarding.corpus_import.import_candidate_from_config` — so the onboarding layer
stops carrying its own path-constant front. Blueprints pass
`current_app.config["CONFIGS_DIR"]`.

`db.models` + `onboarding.corpus_import` are imported lazily inside the function
(as the original did) so `web_infra/` stays a light leaf that does not pull
SQLAlchemy / the importer at import time. `corpus_import` is LLM-free on this path.

P1 Hardening boundary: deterministic, no LLM calls (charter C-6).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from db.models import Candidate


def _get_or_provision_candidate(
    session: Session, safe_user: str, *, configs_dir: Path
) -> Candidate | None:
    """Return the candidate row for safe_user, creating it from config if absent.

    Replaces the old "no candidate row yet -> needs_onboarding" gate. Every user
    starts config-only (create_user writes a config, not a DB row); the first
    corpus write provisions the row on demand. Reuses the idempotent,
    non-destructive import_candidate_from_config (identity + skills + certs +
    education from configs/{user}.config). The caller owns the commit.
    """
    from db.models import Candidate

    candidate = session.query(Candidate).filter_by(username=safe_user).first()
    if candidate is None:
        from onboarding.corpus_import import import_candidate_from_config

        import_candidate_from_config(safe_user, session, configs_dir=configs_dir)  # add + flush
        candidate = session.query(Candidate).filter_by(username=safe_user).first()
    return candidate
