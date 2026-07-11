"""OpenAPI spec-emission leaf — the spectree wiring (kit Decisions 1/2a, Layer B Phase 1).

**Scope — spec emission only, decorator + `resp=` only.** This module builds ONE
shared `SpecTree` instance (`spec`) that `blueprints/**.py` decorate onto exactly
five read-only GET routes (see each route's `@spec.validate(...)` call site:
`users.list_users`, `users.get_config`, `corpus.experiences.list_experiences`,
`applications.list_applications`, `applications.get_application`). Nothing here
adds request (`json=`/`query=`/`headers=`) validation — that would rewrite route
bodies (`request.json` -> `request.context.json`), the exact edit class that once
dropped `_within` in the 8.3 blueprint split (see
`tests/test_route_containment_gate.py`). Every decorated route also passes
`skip_validation=True`, so the response models below are a documentation aid, not
a runtime contract — an imperfect model (e.g. a permissive union approximating a
discriminated success/needs-onboarding shape) is safe by construction.

`scripts/generate_openapi_spec.py` is the actual spec CONSUMER: it builds its own
`create_app()` instance, calls `spec.register(app)` on it, and writes the cached
`spec.spec` dict to `docs-site/openapi.json` (a build artifact, gitignored).
Fumadocs RENDERING that JSON into a hosted HTTP-API reference page is a separate,
later branch (Layer B's remaining half) — out of scope here.

`mode="strict"` (see `spectree.config.ModeEnum`) restricts spec collection to
ONLY routes this `spec` instance decorates — spectree's default ("normal") mode
also collects every UNDECORATED route with an empty/schema-less entry, which
would misrepresent the other ~85 routes as "documented" when Phase 1 has
deliberately scoped only 5. `annotations=False` opts out of spectree's
function-signature-driven validation mode (we always pass `resp=`/`skip_validation=`
explicitly, never typed view-function params), which also silences a
`skip_validation`-vs-`annotations` `UserWarning` that mode emits by default.

P1 Hardening boundary: this module makes no LLM calls (charter C-6). Leaf rule
(enforced by `tests/test_web_infra_is_leaf.py`): no import of `app.py`, any
blueprint, or `config.py` — `spectree` + `pydantic` only.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel
from spectree import SpecTree

__all__ = [
    "ApplicationDetail",
    "ApplicationRunSummary",
    "ApplicationSummaryItem",
    "ApplicationsListResponse",
    "ApplicationsNeedsOnboarding",
    "ExperienceSummaryItem",
    "ExperiencesListResponse",
    "ExperiencesNeedsOnboarding",
    "UserConfigResponse",
    "UsersListResponse",
    "spec",
]


def _app_version() -> str:
    """The installed `sartor` distribution version, with a fallback.

    Falls back when the package metadata isn't discoverable (e.g. running from
    a source checkout that was never `pip install -e .`'d) rather than raising
    out of module import — spec emission should never hard-fail on a cosmetic
    version string.
    """
    try:
        return _pkg_version("sartor")
    except PackageNotFoundError:
        return "0.0.0-dev"


spec = SpecTree(
    "flask",
    title="sartor. API",
    version=_app_version(),
    annotations=False,
    mode="strict",
)


# ---------------------------------------------------------------------------
# Response models — permissive-base convention (mirrors analyzer.py's
# `_LLMResponse`: `extra="allow"` so an under-specified field list never
# breaks schema generation). Do NOT reuse analyzer's LLM-response models —
# these describe deterministic route JSON, not LLM output.
# ---------------------------------------------------------------------------


class _PermissiveModel(BaseModel):
    """Permissive base for route response models (extra keys allowed)."""

    model_config = ConfigDict(extra="allow")


# --- GET /api/users -> list_users (blueprints/users.py) ---------------------


class UsersListResponse(RootModel[list[str]]):
    """Bare JSON array of usernames — `jsonify(users)` in `users.list_users`."""


# --- GET /api/users/<username>/config -> get_config (blueprints/users.py) ---


class UserConfigResponse(_PermissiveModel):
    """The saved profile config, spread with `needs_onboarding` (`users.get_config`)."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None
    portfolio_urls: list[str] = Field(default_factory=list)
    skills: list[Any] = Field(default_factory=list)
    certifications: list[Any] = Field(default_factory=list)
    education_summary: str | None = None
    notes: str | None = None
    needs_onboarding: bool = False


# --- GET /api/users/<username>/experiences -> list_experiences --------------
# (blueprints/corpus/experiences.py) — a union: bare array on success, or the
# discriminated needs-onboarding object when the candidate has no corpus row.


class ExperienceSummaryItem(_PermissiveModel):
    """Mirrors `_experience_summary_dict` (blueprints/corpus/_shared.py)."""

    id: int
    company: str
    location: str | None = None
    start_date: str
    end_date: str | None = None
    display_order: int
    summary: str | None = None
    official_title: str | None = None
    title_count: int
    bullet_count_active: int
    bullet_count_pending: int


class ExperiencesNeedsOnboarding(_PermissiveModel):
    """The `{"experiences": [], "needs_onboarding": true}` no-candidate-row shape."""

    experiences: list[Any] = Field(default_factory=list)
    needs_onboarding: bool = True


class ExperiencesListResponse(RootModel[list[ExperienceSummaryItem] | ExperiencesNeedsOnboarding]):
    """Union response for `list_experiences`.

    See the module docstring on why an imperfect union is safe
    (`skip_validation=True`).
    """


# --- GET /api/users/<username>/applications -> list_applications ------------
# (blueprints/applications.py) — same bare-array-or-onboarding-object union.


class ApplicationSummaryItem(_PermissiveModel):
    """Mirrors `_application_summary_dict` (blueprints/applications.py)."""

    id: int
    title: str
    company: str | None = None
    status: str
    jd_url: str | None = None
    jd_fingerprint: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    sent_at: str | None = None
    outcome_at: str | None = None
    is_active: bool
    iteration_count: int
    latest_iteration: int
    latest_run_id: str | None = None
    pending_proposals: int


class ApplicationsNeedsOnboarding(_PermissiveModel):
    """The `{"applications": [], "needs_onboarding": true}` no-candidate-row shape."""

    applications: list[Any] = Field(default_factory=list)
    needs_onboarding: bool = True


class ApplicationsListResponse(
    RootModel[list[ApplicationSummaryItem] | ApplicationsNeedsOnboarding]
):
    """Union response for `list_applications` (same rationale as `ExperiencesListResponse`)."""


# --- GET /api/applications/<int:application_id> -> get_application ---------
# (blueprints/applications.py)


class ApplicationRunSummary(_PermissiveModel):
    """One entry of `get_application`'s `runs` list."""

    id: int
    iteration: int
    run_id: str
    prompt_version: str | None = None
    persona_template_id: int | None = None
    created_at: str | None = None
    has_resume: bool
    has_cover_letter: bool
    has_edits: bool
    pending_proposals: int
    ats_roundtrip_status: str | None = None


class ApplicationDetail(_PermissiveModel):
    """Full detail for one application — `get_application`.

    `resume_state` is left as a permissive `dict[str, Any]` rather than a fully
    modeled shape: `_build_resume_state`'s keys legitimately vary by which wizard
    step is furthest reached (see its docstring) — a first-approximation, not a
    contract (`skip_validation=True` is what makes that safe).
    """

    id: int
    title: str
    company: str | None = None
    status: str
    # dec 7 (UX Cohesion Epic) — retire/restore moved from the roster card
    # into this detail modal, which needs is_active to pick the right button.
    is_active: bool = True
    jd_text: str | None = None
    jd_url: str | None = None
    jd_fingerprint: str | None = None
    candidate_username: str
    created_at: str | None = None
    updated_at: str | None = None
    sent_at: str | None = None
    outcome_at: str | None = None
    notes: str | None = None
    runs: list[ApplicationRunSummary] = Field(default_factory=list)
    resume_state: dict[str, Any] = Field(default_factory=dict)
