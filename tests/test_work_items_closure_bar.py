"""Teeth tests for the charter **C-11** closure bar in `scripts/work_items.py`.

A gate that has not been shown to **reject** a bad input is not evidence of anything — this
repo's own standard (`tests/test_evidence_gate.py`). So every rule here is asserted twice:
a deliberately non-compliant fixture that must be rejected, and the compliant version of the
same fixture that must pass.

Why the bar exists, from this repo's measured record rather than from principle: three of
epic 19's five closures read as resolved while resting on "not reproduced" (item 28) or on a
fix for a *different* defect with a matching symptom (item 30, whose own resolution text said
"not confirmed as the historical cause"). Item 30 then recurred in CI five days later. Prose
in `resolution` was satisfied by all three. `verified_by` is not.
"""

from __future__ import annotations

from pathlib import Path

from scripts.work_items import _CLOSURE_BAR_GRANDFATHERED, structural_errors
from tests.test_work_items import _item_text, _write_item

_REPO_ROOT = Path(__file__).resolve().parent.parent

# A closed item's id must be outside the grandfather set for the bar to bind it.
_UNGRANDFATHERED = 9001
assert _UNGRANDFATHERED not in _CLOSURE_BAR_GRANDFATHERED


def _errors_for(tmp_path: Path, text: str, filename: str) -> list[str]:
    _write_item(tmp_path, filename, text)
    _items, errors = structural_errors(tmp_path / "items")
    return errors


class TestRuleAClosureNeedsAFalsifiableArtifact:
    """`status = "closed"` requires `verified_by` or an owner-named `closure_exception`."""

    def test_prose_resolution_alone_is_rejected(self, tmp_path: Path) -> None:
        """The exact shape items 28 and 30 closed under, and it must not pass again."""
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="closed",
            extra='resolution = "Not reproduced across a 24-run campaign; closing."\n',
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert any("requires a non-empty `verified_by`" in e for e in errors), errors

    def test_verified_by_satisfies_the_bar(self, tmp_path: Path) -> None:
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="closed",
            extra=(
                'resolution = "Root-caused and fixed."\n'
                'verified_by = ["tests/test_hardening.py::test_reader_never_observes_a_partial_file"]\n'
            ),
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert not any("verified_by" in e for e in errors), errors

    def test_closure_exception_satisfies_the_bar_but_must_be_written_down(
        self, tmp_path: Path
    ) -> None:
        """The escape hatch is deliberate — it is named and attributed, never silent.

        If this starts appearing routinely, that is itself the signal, and it is visible in
        the diff rather than buried in prose.
        """
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="closed",
            extra=(
                'resolution = "Closed without a reproduction."\n'
                'closure_exception = "owner accepted 2026-08-05: cost of reproduction exceeds value"\n'
            ),
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert not any("verified_by" in e for e in errors), errors

    def test_grandfathered_id_is_not_bound(self, tmp_path: Path) -> None:
        """Pre-adoption closures are not retroactively forced to invent artifacts."""
        grandfathered = min(_CLOSURE_BAR_GRANDFATHERED)
        text = _item_text(
            id=grandfathered,
            status="closed",
            extra='resolution = "Closed before the bar was adopted."\n',
        )
        errors = _errors_for(tmp_path, text, f"{grandfathered:04d}-example.md")
        assert not any("verified_by" in e for e in errors), errors


class TestRuleBReopenedItemNeedsAGuardrail:
    """C-11's teeth: recognizing a recurrence obligates a mechanism, not a note."""

    def test_reopened_item_without_a_guardrail_is_rejected(self, tmp_path: Path) -> None:
        """`resolution` + a non-closed status == this was closed once and came back."""
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="watching",
            extra='resolution = "Fixed 2026-07-31."\n',
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert any("requires a `guardrail`" in e for e in errors), errors

    def test_guardrail_satisfies_it(self, tmp_path: Path) -> None:
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="watching",
            extra=(
                'resolution = "Fixed 2026-07-31."\n'
                'guardrail = "scripts/ci_wait.py exit 3 surfaces the absorbed rerun that hid this"\n'
            ),
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert not any("guardrail" in e for e in errors), errors

    def test_guardrail_deferred_satisfies_it(self, tmp_path: Path) -> None:
        """Saying plainly that no mechanism was authored is compliant; silence is not.

        C-11 permits "no mechanism was possible" — it forbids leaving that implied.
        """
        text = _item_text(
            id=_UNGRANDFATHERED,
            status="open",
            extra=(
                'resolution = "Fixed 2026-07-31."\n'
                'guardrail_deferred = "no deterministic reproduction yet; nothing to gate on"\n'
            ),
        )
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert not any("guardrail" in e for e in errors), errors

    def test_a_never_closed_item_is_untouched(self, tmp_path: Path) -> None:
        """No `resolution` means it was never closed — the rule must not fire."""
        text = _item_text(id=_UNGRANDFATHERED, status="open")
        errors = _errors_for(tmp_path, text, f"{_UNGRANDFATHERED:04d}-example.md")
        assert not any("guardrail" in e for e in errors), errors


class TestGrandfatherListIsClosed:
    """Maintained-list + audit-test shape, mirroring `tests/test_egress_allowlist.py`."""

    def test_membership_is_pinned_exactly(self) -> None:
        """Adding an id to the allowlist must require editing this test too.

        That is the whole mechanism: a new closure cannot be quietly waved through by
        appending its id to the exemption set — the diff has to say so out loud.
        """
        assert sorted(_CLOSURE_BAR_GRANDFATHERED) == [
            1, 6, 11, 12, 13, 14, 15, 17, 21, 22, 26, 27, 28, 29, 31, 32, 33, 35, 44,
        ]  # fmt: skip

    def test_every_grandfathered_id_has_a_real_item_file(self) -> None:
        """The exemption cannot name an item that does not exist."""
        items_dir = _REPO_ROOT / "docs" / "dev" / "work" / "items"
        on_disk = {int(p.name[:4]) for p in items_dir.glob("[0-9][0-9][0-9][0-9]-*.md")}
        missing = sorted(_CLOSURE_BAR_GRANDFATHERED - on_disk)
        assert not missing, f"grandfathered ids with no item file: {missing}"


class TestTheRealBacklogSatisfiesTheBar:
    """The rule is not hypothetical — it binds this repo's own items right now."""

    def test_repo_items_pass_structural_validation(self) -> None:
        items_dir = _REPO_ROOT / "docs" / "dev" / "work" / "items"
        _items, errors = structural_errors(items_dir)
        assert errors == [], errors
