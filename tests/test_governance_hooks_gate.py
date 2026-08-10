"""Governance hook witness/blocker gate — PX-29 (F-gov-04 KEEP) / v1.0.8 item 8.4.

The 2026-06 product-excellence review affirmed (``F-gov-04``, KEEP) that the repo's
enforcement hooks are real and honestly separated: enforced **blockers** (a reachable
``exit 2`` that stops the tool call) cleanly distinct from **witnesses** (always
``exit 0`` — they only nudge). That split is what keeps the "witness, not approver"
governance posture honest; it was hand-verified at the review pin with no test behind it.

This commits the counts + the split as a do-not-regress gate, the egress-allowlist
way: named frozensets, so adding, removing, or reclassifying a hook forces a
deliberate, reviewed edit here. It also cross-checks the live wiring in
``.claude/settings.json`` — blockers wired as PreToolUse pre-gates, witnesses as
PostToolUse observers, context hooks on the session-lifecycle events — so a hook can't
be silently unwired or a witness promoted to a gate.

**Amended 2026-07-14** (`fix/compose-summary-draft-settle-hole`), and the amendment is
the gate doing its job: the C-7/C-8 work added three hooks and this file was not
updated, so the suite went red — and stayed red, unnoticed, because the full gate takes
longer than an agent's shell cap and therefore never ran (carry-forward ledger, "the
quality gate is unrunnable by an agent"). Two changes, both deliberate:

- ``require-evidence-before-fix`` is an **eighth blocker** (charter C-7). F-gov-04's
  "exactly seven" was true at the review pin; a new *enforced* rule legitimately moves
  the count, which is precisely the reviewed edit this gate is designed to force.
- ``restore-evidence`` (SessionStart) and ``capture-before-compact`` (PreCompact) are a
  **third category**. They fit neither box: they gate nothing and they are not
  PostToolUse nudges — they carry evidence *across* context boundaries (charter C-8).
  They delegate to a different adapter (``claude_context_hook.py``), and its only
  ``return 2`` is a CLI-misuse guard on a bad ``argv``, never a policy decision — so on
  any real payload they return 0. Asserted below rather than assumed.

Since `feat/portable-enforcement-core` (2026-07-08), seven of the eight blockers are
thin wrappers that exec the shared Claude adapter
(``scripts/enforcement/adapters/claude_hook.py``), so their reachable-``exit 2``
proof moved from "the script text contains ``exit 2``" to a two-part invariant:
the wrapper must delegate its own guard name to that adapter, and the adapter must
behaviorally translate a blocked guard into exit code 2 (asserted in-process below;
the full per-guard block/allow matrix through the real wrappers lives in
``tests/test_enforcement_core.py``). ``check-plan-approved`` stays a standalone
Claude-only script and keeps the literal-text check.

**Amended 2026-07-20** (`chore/hook-dispatcher`, PX-37): five of the "core-delegated"
blockers (``require-feature-branch``, ``require-evidence-before-fix``,
``block-secrets``, ``validate-context``, ``route-security-lint``) no longer each ship
their own file on the ``Edit|Write`` matcher — they run *inside* one new
``hooks/edit-write-dispatcher.sh`` (``scripts/enforcement/adapters/
claude_dispatcher.py``), which runs all five and aggregates every blocked guard's
messages (no short-circuit). This is exactly the
"deliberate, reviewed edit" this file's docstring above says a hook-count change must
force: the **governance invariant stays eight enforced rules** (``BLOCKER_RULE_NAMES``),
but the **on-disk file classification** (``BLOCKER_HOOKS``, what ``test_every_hook_is_
classified`` globs against) now has five members, not eight, because four rules share
one file. Hook scripts also re-homed from ``.claude-plugin/hooks/`` to root ``hooks/``
(kit-adoption commitment 3's hooks half) in the same branch.

**Amended 2026-08-06** (`feat/verify-dont-assume-guard`): two changes, both deliberate,
mirroring the 2026-07-20 amendment's own shape for the ``Bash`` matcher:

- **``verify-binary-on-path`` is a NINTH enforced blocker RULE** (owner-directed
  2026-08-04 — a PreToolUse guard that blocks a Bash command whose leading binary is
  not on ``PATH``). ``BLOCKER_RULE_NAMES`` grows to nine; this is the same kind of
  deliberate governance-count bump ``require-evidence-before-fix`` was for C-7.
- **The three previously-standalone ``Bash``-matcher blockers (``block-merge-to-main``,
  ``block-secrets``, ``ruff-changed``) no longer ship their own file** — they, plus
  the new ``verify-binary-on-path``, run *inside* one new ``hooks/bash-dispatcher.sh``
  (``scripts/enforcement/adapters/bash_dispatcher.py``), which runs all four and
  aggregates every blocked guard's messages (no short-circuit), mirroring
  ``edit-write-dispatcher.sh``'s pattern exactly. ``CORE_DELEGATED_BLOCKERS`` — the
  category for a guard that is a *standalone* thin wrapper exec'ing the shared adapter
  directly, with no dispatcher in between — is now empty and removed: every core-shared
  guard runs through one of the two dispatchers, none through its own lone file.
  ``BLOCKER_HOOKS`` drops ``block-merge-to-main``/``block-secrets``/``ruff-changed`` and
  gains ``bash-dispatcher`` — three on-disk files collapse into one, the same shape as
  the 2026-07-20 amendment, just on the other matcher.

**Known, pre-existing gap surfaced while making this edit, deliberately NOT fixed here**
(filed instead in this branch's own handoff, per C-11/C-12 "declare the gap"): the
``BLOCKER_RULE_NAMES`` "eight enforced rules" count this file tracked before today never
included ``require-consumer-enumeration`` (charter C-10), even though that guard is real,
enforced, and already a member of ``DISPATCHED_GUARD_NAMES`` below — this file was
evidently never updated when C-10 landed (`feat/consumer-enumeration-gate`). Fixing that
undercount is a separate, deliberate governance-count correction (C-10 would make the
count ten, not nine) and is out of scope for this branch's own two deliverables — named
here rather than silently absorbed into this edit or silently left for the next reader to
rediscover from scratch.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scripts.enforcement.adapters import (
    bash_dispatcher,
    claude_context_hook,
    claude_dispatcher,
    claude_hook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / "hooks"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

# The nine enforced RULES (governance invariant — grew by one on
# feat/verify-dont-assume-guard; only the on-disk file layout has moved since
# PX-37, not the count of enforced behaviors, until this branch's own addition).
BLOCKER_RULE_NAMES = frozenset(
    {
        "block-merge-to-main",
        "block-secrets",
        "check-plan-approved",
        "require-evidence-before-fix",
        "require-feature-branch",
        "route-security-lint",
        "ruff-changed",
        "validate-context",
        "verify-binary-on-path",
    }
)

# The on-disk blocker .sh stems (what test_every_hook_is_classified globs
# against, and what test_wiring_matches_witness_blocker_split pins).
# require-feature-branch/require-evidence-before-fix/require-consumer-
# enumeration/block-secrets/validate-context/route-security-lint collapsed
# into edit-write-dispatcher (PX-37); block-merge-to-main/block-secrets/
# ruff-changed/verify-binary-on-path collapsed into bash-dispatcher
# (feat/verify-dont-assume-guard) — block-secrets is dispatched by BOTH.
# check-plan-approved is the sole rule still shipping its own standalone file.
BLOCKER_HOOKS = frozenset(
    {
        "check-plan-approved",
        "edit-write-dispatcher",
        "bash-dispatcher",
    }
)

# The Edit|Write rules that run INSIDE edit-write-dispatcher.sh rather than
# shipping their own standalone file. block-secrets is here AND in
# BASH_DISPATCHED_GUARD_NAMES below — its decide() inspects both the Bash
# `command` field and the Edit/Write `file_path`/`new_string`/`content`
# fields, and (since feat/verify-dont-assume-guard) it needs no standalone
# file for either matcher anymore; verified directly against each
# dispatcher's own guard list below rather than assumed via .sh-file-globbing.
DISPATCHED_GUARD_NAMES = frozenset(
    {
        "require-feature-branch",
        "require-evidence-before-fix",
        "require-consumer-enumeration",
        "block-secrets",
        "validate-context",
        "route-security-lint",
    }
)

# The Bash rules that run INSIDE bash-dispatcher.sh (feat/verify-dont-assume-
# guard) rather than shipping their own standalone file — the Bash-matcher
# mirror of DISPATCHED_GUARD_NAMES above. See that constant's docstring for
# why block-secrets is a member of both.
BASH_DISPATCHED_GUARD_NAMES = frozenset(
    {
        "block-secrets",
        "block-merge-to-main",
        "ruff-changed",
        "verify-binary-on-path",
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

# The two context hooks (charter C-8) — they gate nothing. They carry evidence ACROSS
# a context boundary: `restore-evidence` replays the dossier into a fresh (or
# post-compaction) window; `capture-before-compact` warns the USER before a window is
# discarded with nothing written down. Neither is a PreToolUse gate nor a PostToolUse
# nudge, so neither belongs in the two sets above.
CONTEXT_HOOKS = frozenset(
    {
        "capture-before-compact",
        "restore-evidence",
    }
)

# Which settings.json event each category must be wired on.
BLOCKER_EVENT = "PreToolUse"
WITNESS_EVENT = "PostToolUse"
CONTEXT_EVENTS = {"restore-evidence": "SessionStart", "capture-before-compact": "PreCompact"}


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
    """The set of hook scripts equals BLOCKER ∪ WITNESS ∪ CONTEXT — a new hook (or a
    deletion) fails until it is deliberately classified here."""
    on_disk = _hook_stems()
    classified = BLOCKER_HOOKS | WITNESS_HOOKS | CONTEXT_HOOKS
    unclassified = sorted(on_disk - classified)
    missing = sorted(classified - on_disk)
    assert not unclassified, (
        f"Unclassified hook script(s): {unclassified}. Add each to BLOCKER_HOOKS "
        "(reaches exit 2), WITNESS_HOOKS (always exit 0, PostToolUse nudge), or "
        "CONTEXT_HOOKS (session-lifecycle; carries evidence across a context boundary)."
    )
    assert not missing, f"Classified hook(s) missing from disk: {missing}."


def test_the_three_categories_are_disjoint() -> None:
    """A hook cannot be two things at once — that is how a gate quietly becomes a nudge."""
    assert not (BLOCKER_HOOKS & WITNESS_HOOKS)
    assert not (BLOCKER_HOOKS & CONTEXT_HOOKS)
    assert not (WITNESS_HOOKS & CONTEXT_HOOKS)


# --------------------------------------------------------------------------- #
# 2. The nine blockers each reach exit 2.
# --------------------------------------------------------------------------- #
def test_blockers_reach_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every enforced blocker has a reachable `exit 2`.

    Standalone scripts prove it textually (a literal ``exit 2``); dispatched
    guards (all nine now, since feat/verify-dont-assume-guard collapsed the
    last three core-delegated standalone files into bash-dispatcher.sh) prove
    it via their dispatcher's own guard list + a behavioral check that the
    shared adapter's ``main`` returns 2 for a blocked payload — the exact exit
    code the dispatcher's own ``exec`` propagates. Per-guard block/allow
    coverage through the real wrappers: ``tests/test_enforcement_core.py``.
    """
    assert len(BLOCKER_RULE_NAMES) == 9, (
        "Nine enforced blocker RULES: F-gov-04's seven, plus require-evidence-before-fix "
        "(charter C-7) and verify-binary-on-path (feat/verify-dont-assume-guard). Changing "
        "this count is a governance change — make it deliberately."
    )

    # Standalone blockers: the script text itself must reach exit 2. Both
    # dispatcher .sh files just `exec` a Python module (no literal `exit 2`
    # of their own — their exit-2 path is proven behaviorally below instead).
    standalone = BLOCKER_HOOKS - {"edit-write-dispatcher", "bash-dispatcher"}
    toothless = sorted(s for s in standalone if "exit 2" not in _hook_text(s))
    assert not toothless, (
        f"Standalone blocker hook(s) with no reachable `exit 2`: {toothless}. A blocker "
        "that cannot exit 2 does not block — fix it or reclassify it as a witness."
    )

    # ...and the shared adapter really turns a blocked guard into exit code 2.
    # This is the generic proof every dispatched guard's teeth route through,
    # whichever dispatcher (edit-write or bash) actually calls it.
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo sk-ant-" + "a" * 30}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert claude_hook.main(["claude_hook.py", "block-secrets"]) == 2, (
        "The shared Claude adapter must exit 2 on a blocked guard — the delegated "
        "blockers' teeth all route through this path."
    )


def test_dispatcher_delegates_to_claude_dispatcher() -> None:
    """`edit-write-dispatcher.sh` must exec the new dispatcher module — the file
    that actually owns the five dispatched guards' exit-2 path."""
    text = _hook_text("edit-write-dispatcher")
    assert "scripts/enforcement/adapters/claude_dispatcher.py" in text


def test_bash_dispatcher_delegates_to_bash_dispatcher_module() -> None:
    """`bash-dispatcher.sh` must exec the new dispatcher module — the Bash-matcher
    mirror of `test_dispatcher_delegates_to_claude_dispatcher` above
    (feat/verify-dont-assume-guard)."""
    text = _hook_text("bash-dispatcher")
    assert "scripts/enforcement/adapters/bash_dispatcher.py" in text


def test_bash_dispatcher_guard_list_matches_the_dispatched_names() -> None:
    """The Bash dispatcher's internal guard list is this file's other source of
    truth for the rules feat/verify-dont-assume-guard folded out of their own
    standalone .sh files (or, for verify-binary-on-path, never gave one)."""
    assert set(bash_dispatcher._GUARD_ORDER) == BASH_DISPATCHED_GUARD_NAMES


def test_dispatcher_guard_list_matches_the_dispatched_names() -> None:
    """The dispatcher's internal guard list is this file's other source of truth
    for the rules PX-37 folded out of their own standalone .sh files."""
    assert set(claude_dispatcher._GUARD_ORDER) == DISPATCHED_GUARD_NAMES


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
    assert wired.get(BLOCKER_EVENT, set()) == BLOCKER_HOOKS, (
        f"{BLOCKER_EVENT} hooks {sorted(wired.get(BLOCKER_EVENT, set()))} != the "
        f"blockers {sorted(BLOCKER_HOOKS)}. Blockers gate before the tool runs."
    )
    assert wired.get(WITNESS_EVENT, set()) == WITNESS_HOOKS, (
        f"{WITNESS_EVENT} hooks {sorted(wired.get(WITNESS_EVENT, set()))} != the three "
        f"witnesses {sorted(WITNESS_HOOKS)}. Witnesses observe after the tool runs."
    )


def test_context_hooks_are_wired_on_their_lifecycle_events() -> None:
    """A context hook wired on the wrong event is silently useless.

    `restore-evidence` only replays evidence if it fires on SessionStart (which
    includes `compact` — the window rebuild that C-8 exists for), and
    `capture-before-compact` only warns in time if it fires on PreCompact.
    """
    wired = _wired_by_event()
    for stem, event in CONTEXT_EVENTS.items():
        assert wired.get(event, set()) == {stem}, (
            f"{event} must wire exactly {{{stem!r}}}, found {sorted(wired.get(event, set()))}."
        )
    assert set(CONTEXT_EVENTS) == set(CONTEXT_HOOKS), (
        "Every context hook needs a declared lifecycle event (and vice versa)."
    )


def test_context_hooks_never_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """The C-8 hooks carry evidence; they do not block. Asserted, not assumed.

    `claude_context_hook.main` does contain a `return 2` — but it is a CLI-misuse
    guard on a bad ``argv``, not a policy decision. On a real payload, both hooks
    return 0 whatever they find, so neither can ever stop a tool call or wedge a
    compaction. (`capture-before-compact` deliberately does not block: a blocked
    auto-compact can wedge a session, and that cure is worse than the disease.)
    """
    for stem in sorted(CONTEXT_HOOKS):
        text = _hook_text(stem)
        assert "claude_context_hook.py" in text and stem in text, (
            f"{stem}.sh must delegate to the context adapter naming its own hook."
        )
        assert "exit 2" not in text, f"{stem}.sh is a context hook — it must never gate."

    for stem in sorted(CONTEXT_HOOKS):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(REPO_ROOT)})))
        assert claude_context_hook.main(["claude_context_hook.py", stem]) == 0, (
            f"{stem} returned non-zero on a real payload — a context hook must never gate."
        )
