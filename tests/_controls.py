"""Shared control-step helper for tests that pin a defect with `xfail(strict=True)`.

**Why this exists** (item 167, `docs/dev/diagnosis/recurrence-guardrails.md` O5). An
`xfail(strict=True)` arm that sets up a scenario with bare `assert`s reads a *broken drive* as
the expected defect: the setup fails with an `AssertionError`, pytest calls that "xfailed", and
the arm proves nothing while looking like a confirmation. `strict` only catches the opposite
mistake (an unexpected pass).

**The convention.** Every drive step and every control raises `ControlFailed` (via `control`),
never a bare `assert`. The marker carries `raises=AssertionError`, so only the one invariant
the arm exists to pin, written as a plain `assert`, can be the expected failure; a
`ControlFailed` is not an `AssertionError`, so it surfaces as a real failure.
`tests/test_xfail_controls_gate.py` enforces the marker shape and the single definition.
Verify an arm both ways: `--runxfail` must fail at the invariant line, and the committed run
must show N xfailed with no `ControlFailed`.

**What no mechanism here can check** (C-0): that a given step *uses* `control` rather than a
bare `assert`. That needs a call graph through each arm's drive helpers.
"""

from __future__ import annotations


class ControlFailed(Exception):
    """A drive or control step did not hold, so the arm proves nothing (not the defect)."""


def control(ok: bool, what: object) -> None:
    """Raise `ControlFailed(what)` unless `ok`. Use for every drive step and control."""
    if not ok:
        raise ControlFailed(str(what))
