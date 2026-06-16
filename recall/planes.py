"""The access / disclosure plane — an orthogonal filter, not a source.

Stage 0 skeleton (Sprint 7.4). Pure, deterministic functions that decide which
`Unit`s a `Scope` is allowed to see. Two gates, both AND-ed:

  * **audience** — `user` units are always allowed; `dev` units only when the
    `Scope.allow_dev` toggle is on;
  * **tier** — a unit's source family must be in `Scope.enabled_tiers`.

This is the plane that keeps model-detected progressive disclosure honest: the
avatar may *propose* depth, but it only crosses into dev-tier content if the
toggle here admits it (`docs/dev/memory-architecture.md` §"The two cross-cutting
planes" — "detected depth proposes; the access plane disposes"). The day this is
multi-user, this plane is the authorization boundary — designed as a plane now so
that is a policy change, not a re-architecture.

The companion **provenance plane** lives in `recall/models.py` (the mandatory
`Unit` stamp). Deterministic + stdlib-only — P1 Hardening boundary (charter C-6).
"""

from __future__ import annotations

from collections.abc import Iterable

from recall.models import Audience, Scope, Unit


def allowed_audiences(scope: Scope) -> frozenset[Audience]:
    """The audience tags `scope` may surface: `user` always, `dev` only when the
    toggle is on."""
    if scope.allow_dev:
        return frozenset({Audience.USER, Audience.DEV})
    return frozenset({Audience.USER})


def within_scope(unit: Unit, scope: Scope) -> bool:
    """True iff `unit` passes both the audience gate and the tier gate."""
    return unit.audience in allowed_audiences(scope) and unit.tier in scope.enabled_tiers


def filter_units(units: Iterable[Unit], scope: Scope) -> list[Unit]:
    """Drop every `Unit` that exceeds `scope` (over-audience or disabled tier),
    preserving the input order of the survivors."""
    return [unit for unit in units if within_scope(unit, scope)]
