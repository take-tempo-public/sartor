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

**Amended 2026-08-12** (`feat/interrogative-prompt-witness`, work item 87): two changes,
both deliberate:

- **``interrogative-witness`` is a TENTH enforced blocker RULE** (owner-directed
  2026-08-12): the first Edit/Write after each user prompt is refused ONCE with the
  interrogative-vs-directive consideration, and the refusal self-clears. Semantically the
  item calls it a momentum WITNESS — but this file's taxonomy is mechanical (reaches
  ``exit 2`` = blocker), and classifying a hook that can refuse a tool call as a
  never-exit-2 witness would be the exact "gate quietly becomes a nudge" (in reverse)
  this gate exists to block. It runs inside ``edit-write-dispatcher.sh``, so
  ``DISPATCHED_GUARD_NAMES`` grows with it; ``BLOCKER_HOOKS`` is unchanged (no new
  on-disk blocker file). The C-10 undercount above remains open and is again NOT
  absorbed here — the count goes 9 → 10 for this branch's own guard only.
- **``interrogative-prompt-witness`` (UserPromptSubmit) is a FOURTH category**,
  ``PROMPT_WITNESS_HOOKS``: it fires on prompt submission — before any tool, so neither
  a PreToolUse gate nor a PostToolUse nudge — always exits 0, and injects a
  non-blocking reminder via plain stdout (the UserPromptSubmit context channel, same
  as SessionStart's). Asserted below rather than assumed, the context-hook way.

**Amended 2026-09-24** (Epic C C1c, ``feat/llm-call-error-capture``; owner-directed):
**``block-subagent-git-stash`` is an ELEVENTH enforced blocker RULE.** A Bash command
issued by a subagent (the payload carries ``agent_id``) that runs a state-changing
``git stash`` is refused. It is the C-11 guard for a recurrence: pipeline run
``wf_9f0c8afe-bf9``'s refuter stashed and popped the shared tree mid-review. It runs
inside ``bash-dispatcher.sh``, so ``BASH_DISPATCHED_GUARD_NAMES`` grows with it, and
``BLOCKER_HOOKS`` is unchanged (there is no new on-disk file). The count goes 10 → 11.

**Amended 2026-10-07** (``fix/python-direct-hooks-plan-gate``, items 152/111/154/143;
owner-chosen group). Three changes, all deliberate:

- **There are no hook files any more.** Every settings.json hook is
  ``python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>``, so a
  hook's identity is its ``<name>`` (``hook.HOOKS``), not a ``hooks/*.sh`` stem. The
  "script text contains ``exit 2``" checks became behavioral checks on the handler.
  ``check-plan-approved`` now runs inside ``edit-write-dispatcher``
  (``DISPATCHED_GUARD_NAMES`` grows; ``BLOCKER_HOOKS`` loses it). The rule itself stays.
- **``plan-write-landed`` is a TWELFTH enforced blocker RULE** and a blocker hook (PreToolUse
  ExitPlanMode, item 143). It refuses approval while the plan file's last Write/Edit has
  not landed. The count goes 11 → 12.
- **``cleanup-plan-on-merge`` is retired** (owner decision, 2026-10-06): its output-grep
  archived a live plan (diagnosis O2), and the edit-time reconciler covers every merge
  channel. F-gov-04's three witnesses are now two. **``shell-probe``** (SessionStart,
  item 152) joins the context hooks: it warns, never gates.

**Amended 2026-10-07** (``fix/heredoc-escape-guard``, item 142; owner-directed):
**``block-doubled-backslash`` is a THIRTEENTH enforced blocker RULE.** On Windows, a Bash
command containing two consecutive backslashes is refused, because the Bash tool halves
every doubled backslash before bash parses (``docs/dev/diagnosis/heredoc-escape-guard.md``).
It is the C-11 guard for a recurrence of at least nine corrupted files and patterns. It runs
inside ``bash-dispatcher``, so ``BASH_DISPATCHED_GUARD_NAMES`` grows with it, and
``BLOCKER_HOOKS`` is unchanged. The count goes 12 → 13.
"""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import pytest

from scripts.enforcement import plan_gate
from scripts.enforcement.adapters import (
    bash_dispatcher,
    claude_context_hook,
    claude_dispatcher,
    claude_hook,
    hook,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

# The thirteen enforced RULES (governance invariant). See the amendments above for each
# deliberate change in the count.
BLOCKER_RULE_NAMES = frozenset(
    {
        "block-merge-to-main",
        "block-secrets",
        "check-plan-approved",
        "interrogative-witness",
        "plan-write-landed",
        "require-evidence-before-fix",
        "require-feature-branch",
        "route-security-lint",
        "ruff-changed",
        "validate-context",
        "verify-binary-on-path",
        "block-subagent-git-stash",
        "block-doubled-backslash",
    }
)

# The blocker HOOKS: wired PreToolUse entries that can reach exit 2. Two dispatchers
# run most rules in one process each; plan-write-landed is its own ExitPlanMode entry.
BLOCKER_HOOKS = frozenset(
    {
        "edit-write-dispatcher",
        "bash-dispatcher",
        "plan-write-landed",
    }
)

# The Edit|Write rules that run INSIDE edit-write-dispatcher. block-secrets is here AND
# in BASH_DISPATCHED_GUARD_NAMES below: its decide() inspects both the Bash `command`
# field and the Edit/Write `file_path`/`new_string`/`content` fields.
DISPATCHED_GUARD_NAMES = frozenset(
    {
        "check-plan-approved",
        "require-feature-branch",
        "require-evidence-before-fix",
        "require-consumer-enumeration",
        "block-secrets",
        "validate-context",
        "route-security-lint",
        "interrogative-witness",
    }
)

# The Bash rules that run INSIDE bash-dispatcher.
BASH_DISPATCHED_GUARD_NAMES = frozenset(
    {
        "block-secrets",
        "block-merge-to-main",
        "ruff-changed",
        "verify-binary-on-path",
        "block-subagent-git-stash",
        "block-doubled-backslash",
    }
)

# The witnesses: PostToolUse, always exit 0; they nudge or record, never block.
WITNESS_HOOKS = frozenset(
    {
        "mark-plan-approved",
        "wiki-freshness-reminder",
    }
)

# The prompt witness (work item 87): UserPromptSubmit, always exit 0. Its stdout is
# injected into context. Its Edit|Write pause sibling is the `interrogative-witness`
# RULE above, not a hook here.
PROMPT_WITNESS_HOOKS = frozenset({"interrogative-prompt-witness"})
PROMPT_WITNESS_EVENT = "UserPromptSubmit"

# Context hooks: they gate nothing. `restore-evidence` and `capture-before-compact` carry
# evidence across a context boundary (charter C-8); `shell-probe` (item 152) says which
# shells lack basic tools. None is a PreToolUse gate or a PostToolUse nudge.
CONTEXT_HOOKS = frozenset({"capture-before-compact", "restore-evidence", "shell-probe"})

BLOCKER_EVENT = "PreToolUse"
WITNESS_EVENT = "PostToolUse"
CONTEXT_EVENTS = {
    "restore-evidence": "SessionStart",
    "shell-probe": "SessionStart",
    "capture-before-compact": "PreCompact",
}

_NAME = re.compile(r"/scripts/enforcement/adapters/hook\.py\" (?P<name>[a-z-]+)$")


def _wired_by_event() -> dict[str, set[str]]:
    """Event -> set of wired hook names (the `hook.py` argument), from settings.json."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for event, groups in settings.get("hooks", {}).items():
        names: set[str] = set()
        for group in groups:
            for h in group.get("hooks", []):
                m = _NAME.search(h.get("command", ""))
                if m:
                    names.add(m["name"])
        out[event] = names
    return out


def _handler(name: str) -> tuple[str, tuple[str, ...]]:
    return hook.HOOKS[name]


# --------------------------------------------------------------------------- #
# 1. Every hook is classified (no unclassified hook can sneak in).
# --------------------------------------------------------------------------- #
def test_every_hook_is_classified() -> None:
    """The registered hooks equal BLOCKER ∪ WITNESS ∪ PROMPT-WITNESS ∪ CONTEXT. A new hook
    (or a removal) fails until it is deliberately classified here."""
    registered = set(hook.HOOKS)
    classified = BLOCKER_HOOKS | WITNESS_HOOKS | PROMPT_WITNESS_HOOKS | CONTEXT_HOOKS
    unclassified = sorted(registered - classified)
    missing = sorted(classified - registered)
    assert not unclassified, (
        f"Unclassified hook(s): {unclassified}. Add each to BLOCKER_HOOKS (reaches exit 2), "
        "WITNESS_HOOKS (always exit 0, PostToolUse), PROMPT_WITNESS_HOOKS (always exit 0, "
        "UserPromptSubmit), or CONTEXT_HOOKS (session lifecycle, never gates)."
    )
    assert not missing, f"Classified hook(s) missing from hook.HOOKS: {missing}."


def test_the_four_categories_are_disjoint() -> None:
    """A hook cannot be two things at once — that is how a gate quietly becomes a nudge."""
    assert not (BLOCKER_HOOKS & WITNESS_HOOKS)
    assert not (BLOCKER_HOOKS & CONTEXT_HOOKS)
    assert not (WITNESS_HOOKS & CONTEXT_HOOKS)
    assert not (PROMPT_WITNESS_HOOKS & (BLOCKER_HOOKS | WITNESS_HOOKS | CONTEXT_HOOKS))


# --------------------------------------------------------------------------- #
# 2. The blockers each reach exit 2.
# --------------------------------------------------------------------------- #
def test_blockers_reach_exit_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every enforced blocker has a reachable exit 2, proven behaviorally.

    The dispatched rules route through `claude_hook.dispatch`, and the shared adapter must
    turn a blocked guard into exit 2 (the per-guard matrix through the real hook entry is
    `tests/test_enforcement_core.py`). `plan-write-landed` is proven on its own handler.
    """
    assert len(BLOCKER_RULE_NAMES) == 13, (
        "Thirteen enforced blocker RULES: F-gov-04's seven, plus require-evidence-before-fix "
        "(C-7), verify-binary-on-path, interrogative-witness (item 87), "
        "block-subagent-git-stash (Epic C C1c), plan-write-landed (item 143) and "
        "block-doubled-backslash (item 142). Changing this count is a governance change — "
        "make it deliberately."
    )
    dispatched = DISPATCHED_GUARD_NAMES | BASH_DISPATCHED_GUARD_NAMES
    assert BLOCKER_RULE_NAMES - {"plan-write-landed"} <= dispatched | {
        "require-consumer-enumeration"
    }
    assert set(claude_hook._GUARD_NAMES) >= dispatched

    payload = {"tool_name": "Bash", "tool_input": {"command": "echo sk-ant-" + "a" * 30}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert claude_hook.main(["claude_hook.py", "block-secrets"]) == 2, (
        "The shared Claude adapter must exit 2 on a blocked guard — the dispatched "
        "blockers' teeth all route through this path."
    )

    # plan-write-landed: an attempt recorded after the plan file's mtime is refused.
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    plan = plans / "p.md"
    plan.write_text("# old\n", encoding="utf-8")
    key = plan_gate.project_key(str(tmp_path / "proj"))
    (plans / f".plan-attempt-{key}").write_text(
        f"{time.time_ns() + 10**10}\t{plan.as_posix()}\n", encoding="utf-8"
    )
    monkeypatch.delenv(plan_gate.PLANS_DIR_ENV, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "proj"))
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    module_name, tail = _handler("plan-write-landed")
    assert module_name == "scripts.enforcement.plan_gate"
    assert plan_gate.main([module_name, *tail]) == 2


def test_dispatchers_are_the_registered_handlers() -> None:
    """`edit-write-dispatcher` and `bash-dispatcher` launch the modules that own the
    dispatched guards' exit-2 path."""
    assert _handler("edit-write-dispatcher")[0] == claude_dispatcher.__name__
    assert _handler("bash-dispatcher")[0] == bash_dispatcher.__name__


def test_bash_dispatcher_guard_list_matches_the_dispatched_names() -> None:
    assert set(bash_dispatcher._GUARD_ORDER) == BASH_DISPATCHED_GUARD_NAMES


def test_dispatcher_guard_list_matches_the_dispatched_names() -> None:
    assert set(claude_dispatcher._GUARD_ORDER) == DISPATCHED_GUARD_NAMES


def test_the_plan_gate_runs_first_in_the_edit_write_dispatcher() -> None:
    """It records a plan-file write attempt before any later guard (the interrogative
    witness) can pause that write — item 143's mechanism depends on the order."""
    assert claude_dispatcher._GUARD_ORDER[0] == "check-plan-approved"


# --------------------------------------------------------------------------- #
# 3. The witnesses never exit 2.
# --------------------------------------------------------------------------- #
def test_witnesses_never_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """F-gov-04's witnesses, now two (cleanup-plan-on-merge retired 2026-10-06): neither
    can block, on a real payload or on garbage stdin."""
    assert len(WITNESS_HOOKS) == 2
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "proj"))
    for name in sorted(WITNESS_HOOKS):
        module_name, tail = _handler(name)
        module = __import__(module_name, fromlist=["main"])
        for stdin in (
            json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}),
            "{never json",
        ):
            monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
            assert module.main([module_name, *tail]) == 0, f"{name} returned non-zero"


# --------------------------------------------------------------------------- #
# 4. The wiring matches the split (blockers pre-gate, witnesses post-observe).
# --------------------------------------------------------------------------- #
def test_wiring_matches_witness_blocker_split() -> None:
    """settings.json wires every blocker as a PreToolUse pre-gate and every witness as a
    PostToolUse observer — and nothing else."""
    wired = _wired_by_event()
    assert wired.get(BLOCKER_EVENT, set()) == BLOCKER_HOOKS, (
        f"{BLOCKER_EVENT} hooks {sorted(wired.get(BLOCKER_EVENT, set()))} != the "
        f"blockers {sorted(BLOCKER_HOOKS)}. Blockers gate before the tool runs."
    )
    assert wired.get(WITNESS_EVENT, set()) == WITNESS_HOOKS, (
        f"{WITNESS_EVENT} hooks {sorted(wired.get(WITNESS_EVENT, set()))} != the "
        f"witnesses {sorted(WITNESS_HOOKS)}. Witnesses observe after the tool runs."
    )


def test_prompt_witness_is_wired_on_user_prompt_submit() -> None:
    wired = _wired_by_event()
    assert wired.get(PROMPT_WITNESS_EVENT, set()) == PROMPT_WITNESS_HOOKS


def test_prompt_witness_never_gates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The UserPromptSubmit half is fail-open by design (item 87): always exit 0, on a real
    payload AND on garbage stdin."""
    from scripts.enforcement.adapters import prompt_witness_hook
    from scripts.enforcement.guards import interrogative_witness

    for name in sorted(PROMPT_WITNESS_HOOKS):
        assert _handler(name)[0] == prompt_witness_hook.__name__

    monkeypatch.setenv(interrogative_witness.STATE_DIR_ENV, str(tmp_path))
    payload = {"session_id": "gate-test", "prompt": "is this hook fail-open?"}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert prompt_witness_hook.main(["prompt_witness_hook.py"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("{never json"))
    assert prompt_witness_hook.main(["prompt_witness_hook.py"]) == 0


def test_context_hooks_are_wired_on_their_lifecycle_events() -> None:
    """A context hook wired on the wrong event is silently useless."""
    wired = _wired_by_event()
    for event in set(CONTEXT_EVENTS.values()):
        expected = {name for name, ev in CONTEXT_EVENTS.items() if ev == event}
        assert wired.get(event, set()) == expected, (
            f"{event} must wire exactly {sorted(expected)}, found {sorted(wired.get(event, set()))}."
        )
    assert set(CONTEXT_EVENTS) == set(CONTEXT_HOOKS)


def test_context_hooks_never_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """The context hooks carry evidence or warnings; they do not block. Asserted, not
    assumed. (`claude_context_hook.main`'s `return 2` is a CLI-misuse guard on a bad argv,
    never a policy decision.)"""
    for name in sorted(CONTEXT_HOOKS):
        module_name, tail = _handler(name)
        if module_name == claude_context_hook.__name__:
            assert tail == (name,), f"{name} must name its own hook to the context adapter"
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"cwd": str(REPO_ROOT)})))
        module = __import__(module_name, fromlist=["main"])
        assert module.main([module_name, *tail]) == 0, (
            f"{name} returned non-zero on a real payload — a context hook must never gate."
        )
