"""Governance hook witness/blocker gate — PX-29 (F-gov-04 KEEP) / v1.0.8 item 8.4.

The 2026-06 product-excellence review affirmed (``F-gov-04``, KEEP) that the repo's
enforcement hooks are real and honestly separated: **seven enforced blockers** (a
reachable ``exit 2`` that stops the tool call) cleanly distinct from **three
witnesses** (always ``exit 0`` — they only nudge). That split is what keeps the
"witness, not approver" governance posture honest; it was hand-verified at the
review pin with no test behind it.

This commits the count + the split as a do-not-regress gate, the egress-allowlist
way: two named frozensets, so adding, removing, or reclassifying a hook forces a
deliberate, reviewed edit here. It also cross-checks the live wiring in
``.claude/settings.json`` — blockers wired as PreToolUse pre-gates, witnesses as
PostToolUse observers — so a hook can't be silently unwired or a witness promoted
to a gate.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".claude-plugin" / "hooks"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

# The seven enforced blockers — each reaches `exit 2` to stop a tool call.
BLOCKER_HOOKS = frozenset(
    {
        "block-merge-to-main",
        "block-secrets",
        "check-plan-approved",
        "require-feature-branch",
        "route-security-lint",
        "ruff-changed",
        "validate-context",
    }
)

# The three witnesses — always `exit 0`; they emit a nudge, never block.
WITNESS_HOOKS = frozenset(
    {
        "cleanup-plan-on-merge",
        "mark-plan-approved",
        "wiki-freshness-reminder",
    }
)


def _hook_stems() -> set[str]:
    """Names (without .sh) of every hook script in the hooks dir."""
    return {p.stem for p in HOOKS_DIR.glob("*.sh")}


def _hook_text(stem: str) -> str:
    return (HOOKS_DIR / f"{stem}.sh").read_text(encoding="utf-8")


def _wired_by_event() -> dict[str, set[str]]:
    """PreToolUse / PostToolUse -> set of wired hook stems (from settings.json)."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for event, groups in settings.get("hooks", {}).items():
        stems: set[str] = set()
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command", "")
                name = command.rsplit("/", 1)[-1]  # forward-slash commands
                if name.endswith(".sh"):
                    stems.add(name[:-3])
        out[event] = stems
    return out


# --------------------------------------------------------------------------- #
# 1. Every hook script is classified (no unclassified hook can sneak in).
# --------------------------------------------------------------------------- #
def test_every_hook_is_classified() -> None:
    """The set of hook scripts equals BLOCKER ∪ WITNESS — a new hook (or a
    deletion) fails until it is deliberately classified here."""
    on_disk = _hook_stems()
    classified = BLOCKER_HOOKS | WITNESS_HOOKS
    unclassified = sorted(on_disk - classified)
    missing = sorted(classified - on_disk)
    assert not unclassified, (
        f"Unclassified hook script(s): {unclassified}. Add each to BLOCKER_HOOKS "
        "(reaches exit 2) or WITNESS_HOOKS (always exit 0)."
    )
    assert not missing, f"Classified hook(s) missing from disk: {missing}."


# --------------------------------------------------------------------------- #
# 2. The seven blockers each reach exit 2.
# --------------------------------------------------------------------------- #
def test_seven_blockers_reach_exit_2() -> None:
    """F-gov-04: exactly seven enforced blockers, each with a reachable `exit 2`."""
    assert len(BLOCKER_HOOKS) == 7, "F-gov-04 affirms exactly seven enforced blockers."
    toothless = sorted(s for s in BLOCKER_HOOKS if "exit 2" not in _hook_text(s))
    assert not toothless, (
        f"Blocker hook(s) with no reachable `exit 2`: {toothless}. A blocker that "
        "cannot exit 2 does not block — fix it or reclassify it as a witness."
    )


# --------------------------------------------------------------------------- #
# 3. The three witnesses never exit 2.
# --------------------------------------------------------------------------- #
def test_three_witnesses_never_block() -> None:
    """F-gov-04: exactly three witnesses, none of which can `exit 2` (witness, not
    approver). Keeps the honest 'observe, never gate' posture from regressing."""
    assert len(WITNESS_HOOKS) == 3, "F-gov-04 affirms exactly three witnesses."
    blockers = sorted(s for s in WITNESS_HOOKS if "exit 2" in _hook_text(s))
    assert not blockers, (
        f"Witness hook(s) that can `exit 2`: {blockers}. A witness must never block "
        "(charter 'witness, not approver') — remove the exit 2 or reclassify it."
    )


# --------------------------------------------------------------------------- #
# 4. The wiring matches the split (blockers pre-gate, witnesses post-observe).
# --------------------------------------------------------------------------- #
def test_wiring_matches_witness_blocker_split() -> None:
    """settings.json wires every blocker as a PreToolUse pre-gate and every witness
    as a PostToolUse observer — and nothing else. Pins the wiring so a hook can't be
    silently unwired, nor a witness promoted into the gate path."""
    wired = _wired_by_event()
    assert wired.get("PreToolUse", set()) == BLOCKER_HOOKS, (
        f"PreToolUse hooks {sorted(wired.get('PreToolUse', set()))} != the seven "
        f"blockers {sorted(BLOCKER_HOOKS)}. Blockers gate before the tool runs."
    )
    assert wired.get("PostToolUse", set()) == WITNESS_HOOKS, (
        f"PostToolUse hooks {sorted(wired.get('PostToolUse', set()))} != the three "
        f"witnesses {sorted(WITNESS_HOOKS)}. Witnesses observe after the tool runs."
    )
