"""Which enforcement binds WHICH agents — a maintained classification with teeth.

**Why this test exists.** sartor's guards reach agents through three adapters with very
different coverage:

* ``adapters/git_hook.py`` — the opt-in ``.githooks/`` install. **Tool-agnostic**: it fires
  for Codex, Cursor, Aider, a human on the CLI, anything that runs ``git``.
* ``ci_backstop.py`` / ``scripts/gate.py`` — CI and the quality gate. **Binds everyone**,
  including an agent that never installed a hook.
* ``adapters/claude_hook.py`` / ``claude_dispatcher.py`` / ``claude_context_hook.py`` —
  Claude Code PreToolUse/SessionStart/PreCompact. **Claude Code only.**

That split is invisible from any single file, and it is load-bearing for the planned
governance extraction into a separate project: a clause enforced *only* by a Claude Code
hook does not travel. Discovered while writing C-11/C-12 (2026-08-05) — **C-7's and C-10's
guards are Claude-Code-only**, which nothing stated anywhere.

**The mechanism, not the note (charter C-11).** The classification below is *derived* from
the adapters at runtime and compared against a pinned expectation. Adding a new guard, or
moving one between adapters, fails this test until its reach is declared. So the coverage
gap cannot be silently inherited by whoever performs the extraction — it has to be answered.

Same shape as ``tests/test_egress_allowlist.py``'s SANCTIONED_EGRESS_FILES and
``scripts/work_items._CLOSURE_BAR_GRANDFATHERED``.
"""

from __future__ import annotations

from pathlib import Path

from scripts.enforcement.adapters import git_hook

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GUARDS_DIR = _REPO_ROOT / "scripts" / "enforcement" / "guards"

#: Guard module -> does it reach NON-Claude agents (via the tool-agnostic git hooks)?
#:
#: `True`  = routed by `adapters/git_hook.py`, so it binds Codex/Cursor/Aider/a human too.
#: `False` = **Claude Code only.** These are the extraction gap: the clause they enforce is
#:           real, but outside Claude Code nothing enforces it.
_BINDS_NON_CLAUDE_AGENTS: dict[str, bool] = {
    "block_merge_to_main": True,
    "block_secrets": True,  # also the CI backstop (ci_backstop.py) — the widest reach here
    "require_feature_branch": True,
    "route_security_lint": True,
    "ruff_changed": True,
    "validate_context": True,
    # --- the gap -------------------------------------------------------------------------
    "require_evidence_before_fix": False,  # charter C-7 — Claude Code PreToolUse only
    "require_consumer_enumeration": False,  # charter C-10 — Claude Code PreToolUse only
    "verify_binary_on_path": False,  # feat/verify-dont-assume-guard — Claude Code PreToolUse only;
    # no git-native adapter was built (out of scope for this branch — the Bash-command-string
    # parsing this guard does has no equivalent in a git pre-commit/pre-push hook's input shape)
}

#: Guards whose clause has **no** tool-agnostic enforcement at all. Kept as its own constant
#: so the extraction has one thing to read. Derived, not hand-listed — see the test below.
EXTRACTION_GAP = frozenset(name for name, binds in _BINDS_NON_CLAUDE_AGENTS.items() if not binds)


def _guard_modules_on_disk() -> set[str]:
    """Every real guard module (excluding the package marker and the shared result type)."""
    return {p.stem for p in _GUARDS_DIR.glob("*.py") if p.stem not in {"__init__", "result"}}


def _guards_routed_by_git_hook() -> set[str]:
    """Guard modules `adapters/git_hook.py` actually imports — derived, never hand-listed."""
    routed: set[str] = set()
    for value in vars(git_hook).values():
        module_name = getattr(value, "__name__", "")
        if module_name.startswith("scripts.enforcement.guards."):
            routed.add(module_name.rsplit(".", 1)[-1])
    return routed - {"result"}


class TestClassificationIsComplete:
    def test_every_guard_on_disk_is_classified(self) -> None:
        """A new guard cannot be added without declaring whether it binds non-Claude agents.

        This is the teeth. Without it, someone adds a guard, wires it to the Claude
        dispatcher only, and the extraction gap grows silently — which is exactly how C-7's
        and C-10's Claude-only status went unrecorded until 2026-08-05.
        """
        unclassified = _guard_modules_on_disk() - set(_BINDS_NON_CLAUDE_AGENTS)
        assert not unclassified, (
            f"guard(s) with no declared enforcement reach: {sorted(unclassified)}. "
            "Add them to _BINDS_NON_CLAUDE_AGENTS and say whether git_hook.py routes them."
        )

    def test_classification_names_no_phantom_guard(self) -> None:
        """The table cannot describe a guard that no longer exists."""
        phantom = set(_BINDS_NON_CLAUDE_AGENTS) - _guard_modules_on_disk()
        assert not phantom, f"classified but absent from disk: {sorted(phantom)}"


class TestClassificationMatchesReality:
    def test_derived_routing_matches_the_declared_table(self) -> None:
        """The declaration is checked against what `git_hook.py` *actually* imports.

        A hand-maintained list rots in both directions (charter C-10 rule 3), so it is not
        trusted: moving a guard into or out of the git-hook adapter fails here until the
        table is updated to match.
        """
        derived = _guards_routed_by_git_hook()
        declared = {name for name, binds in _BINDS_NON_CLAUDE_AGENTS.items() if binds}
        assert derived == declared, (
            f"git_hook.py routes {sorted(derived)} but the table declares {sorted(declared)}"
        )


class TestTheExtractionGapIsPinned:
    def test_gap_membership_is_pinned_exactly(self) -> None:
        """Closing (or widening) the gap must be a deliberate, visible edit.

        If a future branch gives C-7 or C-10 a git-hook path, this fails — which is the
        point: that is a governance-coverage change and it should not land silently.
        """
        assert sorted(EXTRACTION_GAP) == [
            "require_consumer_enumeration",
            "require_evidence_before_fix",
            "verify_binary_on_path",
        ]

    def test_gap_is_documented_where_the_extraction_will_look(self) -> None:
        """`docs/governance/enforcement.md` is the canonical enforcement home.

        A pinned constant nobody reads is not a flag. The gap must also be written where a
        person performing the extraction would actually look, and this asserts it is.
        """
        text = (_REPO_ROOT / "docs" / "governance" / "enforcement.md").read_text(encoding="utf-8")
        assert "Enforcement reach" in text, "enforcement.md lost its reach section"
        for guard in EXTRACTION_GAP:
            assert guard in text, f"{guard} is in the gap but unnamed in enforcement.md"
