"""block-subagent-git-stash guard (Epic C, C1c; owner-directed 2026-09-24).

Refuses a state-changing `git stash` in a Bash command issued by a **subagent**.
Read-only `git stash list` / `git stash show` are allowed; the main agent is not
gated at all.

**Why (C-11: a recurrence gets a gate, not a note).** Pipeline run
`wf_9f0c8afe-bf9`'s refuter, which has a "read-only git" grant, ran
`git stash -u` / `git stash pop` mid-review. That unstaged the implementer's
diff, and it did so in the same repo whose only in-repo copy of C2's parked work
was `stash@{0}`. The sprint brief forbade it in prose
(`docs/dev/handoffs/epic-c-c1c-brief.md`, "No pipeline agent may run `git stash`
commands"), and nothing enforced that. This is not the first agent stash
incident: memory `reference-background-bash-kill-ceiling` records a killed
`stash && pytest && stash pop` that left a fix stranded in the stash. Both
escalation reviewers ruled it a recurrence under C-11. The owner directed:
"Build the stash guard."

**Who is a subagent.** A subagent's PreToolUse payload carries a truthy
`agent_id`. The main agent's payload does not. This is the same discriminator
`interrogative_witness.claude_check` uses (item 94; memory
`reference-subagent-pretooluse-agent-id`).

**Parsing: fail closed, the opposite of `verify-binary-on-path`.** That guard
fails open, because a false block of an ordinary command is costly. Here the
dangerous direction is the miss, and a false block costs a subagent nothing it
is entitled to. Any `git [global options] stash` invocation anywhere in the
command string counts. That covers pipelines, `&&` chains, `git -C <dir> stash`,
and `$(...)`. Only an explicit `list`/`show` subcommand escapes.

**Known limit (C-0).** This inspects the command *string*. A subagent that
reaches `git stash` indirectly, for example a script file that runs it, or
`python -c "subprocess.run(['git','stash'])"` with the words split across
arguments, is not caught. It closes the observed path, not every path.
"""

from __future__ import annotations

import re
from typing import Any

from scripts.enforcement.guards.result import GuardResult

# `git`, then zero or more GLOBAL options, then `stash` as the subcommand, then an
# optional first argument. Only real global-option shapes may sit between `git`
# and `stash`: `-C <dir>`/`-c <k=v>` (quoted or bare arg), `--long[=v]`, and a
# bare short flag. Anything else there means `stash` is an argument, not the
# subcommand, so `git commit -m "park the stash"` does not match. It is still
# fail-closed at the edges: `git log --grep stash` reads as a flag followed by the
# subcommand and IS blocked for subagents, which is a harmless false positive. A loose `git .* stash` would false-block the finalize closer's
# commit message, the one legitimate subagent write in the pipeline.
_ARG = r"(?:\"[^\"]*\"|'[^']*'|\S+)"
_GLOBAL_OPT = rf"(?:-[Cc]\s+{_ARG}|--[\w-]+(?:={_ARG})?|-[A-Za-z])"
_STASH_RE = re.compile(
    rf"(?<![\w./-])git(?:\s+{_GLOBAL_OPT})*\s+stash(?![\w-])(?:\s+(?P<sub>[^\s;&|)]+))?"
)

#: Subcommands that only read. `git stash show -p` and `git stash list --stat`
#: stay allowed because only the FIRST argument is checked.
_READ_ONLY_SUBCOMMANDS = frozenset({"list", "show"})

_MESSAGE_LINES = (
    "BLOCKED (block-subagent-git-stash): a subagent may not run a state-changing "
    "`git stash` (push/pop/apply/drop/clear/save/branch/store/create, or bare `git stash`).",
    "A stash moves the shared working tree and index out from under the invoking session "
    "and every other agent. Pipeline run wf_9f0c8afe-bf9's refuter did exactly this "
    "mid-review (C-11 recurrence).",
    "Compare states read-only instead: `git diff`, `git diff --cached`, "
    "`git show HEAD:<path>`, or `git stash list` / `git stash show` for an existing stash.",
    "If you genuinely need the tree changed, say so in your return (a flag), and the "
    "invoking session decides. There is no escape hatch for subagents.",
)


def stash_mutations(command: str) -> list[str]:
    """Every state-changing `git stash` invocation found in `command`.

    Returns the matched text for each one (empty list = nothing to block).
    `list`/`show` as the first argument are read-only and not returned.
    """
    hits: list[str] = []
    for match in _STASH_RE.finditer(command or ""):
        sub = match.group("sub")
        if sub is not None and sub.strip("'\"") in _READ_ONLY_SUBCOMMANDS:
            continue
        hits.append(match.group(0).strip())
    return hits


def decide(command: str, is_subagent: bool) -> GuardResult:
    """Pure decision: block a state-changing `git stash` issued by a subagent."""
    if not is_subagent:
        return GuardResult.allow()
    hits = stash_mutations(command)
    if not hits:
        return GuardResult.allow()
    return GuardResult.block(*_MESSAGE_LINES, f"Matched: {hits[0]!r}")


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: `tool_input.command` plus the `agent_id` discriminator."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    return decide(command, is_subagent=bool(payload.get("agent_id")))
