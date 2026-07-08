"""Shared result type every guard's `decide()` returns."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuardResult:
    """The outcome of one guard's decision.

    `messages` is an ordered tuple of stderr lines, reproduced verbatim (one
    `print(..., file=sys.stderr)` per entry) by every adapter — this is what
    keeps the migrated hooks' block messages byte-identical to the
    pre-migration standalone scripts.
    """

    blocked: bool
    messages: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def allow(cls) -> GuardResult:
        """No objection — the action proceeds."""
        return cls(blocked=False)

    @classmethod
    def block(cls, *messages: str) -> GuardResult:
        """Refuse the action; `messages` are printed to stderr, one per line."""
        return cls(blocked=True, messages=tuple(messages))
