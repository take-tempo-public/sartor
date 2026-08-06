"""verify-binary-on-path guard.

Blocks a `Bash` command whose leading binary is not found on `PATH`, with a
message naming exactly what was checked — instead of letting a multi-step
command die deep inside with a bare "command not found" once the missing
binary is finally reached. Owner-directed 2026-08-04 (see the
`project-verify-dont-assume-enforcement-gap` memory this branch inherited):
a session lost ~1h to two `Monitor` watches emitting nothing while a
required CI check was already red, because a `| jq` pipeline silently died
on a binary this machine does not have.

**Scope, stated plainly — do not overclaim (charter C-0).** This closes ONE
specific, deterministically-detectable slice of "verify, don't assume": a
missing binary on `PATH`. It does not, and cannot, verify that a *claim*
("I checked this") is actually true — that is not mechanizable (see
`scripts/enforcement/evidence.py`'s own "a ceremony check, not a truth
check" concession, and charter C-0 generally). Nothing in this module's
messages should say "never assume" or otherwise imply broader coverage than
a `PATH` lookup.

**Fail-open on uncertainty, by design.** A guard that misparses a
legitimate command and blocks it is worse than no guard — false BLOCKs cost
real work; false ALLOWs cost nothing this guard wasn't already failing to
catch. This module does not implement shell grammar. Whenever a construct
appears that this scanner does not model with confidence — unbalanced
quotes, `$(...)`/backtick command substitution, `(...)` subshells or
grouping, or a heredoc redirect (`<<`) — the ENTIRE command is treated as
unparseable and ALLOWED without any check (see `_split_top_level`). Within
an otherwise-parseable command, a segment that resolves to a variable
expansion (`$FOO`) or that this guard cannot tokenize at all is skipped
(allowed) rather than guessed at.

**Deliberate exemptions (named, not silent):**
- Shell builtins/keywords (`cd`, `if`, `test`, `[`, ...) never resolve via
  `PATH` — checking them would either always miss or check the wrong thing.
- `command`, `which`, `type`, `hash` are themselves existence probes — the
  guard would be redundant with (and could shadow) the very check the
  command is already performing.
- A segment immediately followed by `||` is treated as an intentional,
  defensive probe (`foo --version || echo "no foo"`) and is not checked —
  the command's own author has already written a fallback path for exactly
  the failure this guard would otherwise flag. The segment on the OTHER
  side of the `||` (the fallback) is still checked normally.
- Wrapper binaries that take another program as an argument (`env`, `sudo`,
  `time`, `nice`, `nohup`, `xargs`, ...) are checked only for the wrapper
  itself, never the program they launch — recursing into wrapper semantics
  is out of scope for this pass; stated here rather than silently doing it
  halfway.
- A Git-Bash/MSYS-style absolute path (`/c/Users/...`) is skipped (allowed),
  never checked. **Hand-tested finding, not a hypothesis:** this hook runs
  under native Windows Python (see `reference-hook-manual-testing`'s Gotcha
  #3 — the same interpreter other guards' `pathlib`/`subprocess` calls hit),
  which does not understand `/c/...` notation the way Git Bash itself does.
  Probing this directly (see this branch's design note) showed a REAL,
  existing binary referenced via its `/c/...` form reads as missing —
  `shutil.which("/c/Users/.../python.EXE")` returns `None` even though the
  identical binary at the native `C:` path resolves fine and the
  command would run without issue under Git Bash. That is a false BLOCK, the
  mirror image of the false-ALLOW this exact path shape has historically
  produced in *other* guards' `cwd`/`file_path` resolution. Per this
  module's own fail-open rule, the fix is not a clever path translation
  (which risks getting a different case wrong in a different way) — it is
  refusing to guess: skip the check.
"""

from __future__ import annotations

import re
import shlex
import shutil
from typing import Any

from scripts.enforcement.guards.result import GuardResult

# Bash builtins/keywords that never resolve via PATH. Extend conservatively —
# an unrecognized leading word is treated as a real binary and checked, so
# omitting a builtin here risks a false BLOCK, not a false ALLOW.
_BUILTINS_AND_KEYWORDS = frozenset(
    {
        "cd",
        "echo",
        "pwd",
        "exit",
        "return",
        "break",
        "continue",
        "true",
        "false",
        ":",
        "export",
        "unset",
        "set",
        "shift",
        "read",
        "readonly",
        "local",
        "declare",
        "typeset",
        "let",
        "eval",
        "exec",
        "source",
        ".",
        "if",
        "then",
        "else",
        "elif",
        "fi",
        "for",
        "while",
        "until",
        "do",
        "done",
        "case",
        "esac",
        "function",
        "select",
        "in",
        "time",
        "[",
        "[[",
        "test",
        "trap",
        "wait",
        "jobs",
        "bg",
        "fg",
        "kill",
        "ulimit",
        "umask",
        "hash",
        "getopts",
        "alias",
        "unalias",
        "shopt",
        "pushd",
        "popd",
        "dirs",
        "history",
        "printf",
    }
)

# These commands ARE existence probes (or report on it) — never block them;
# see module docstring "Deliberate exemptions".
_PROBE_COMMANDS = frozenset({"command", "which", "type", "hash"})

_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# A Git-Bash/MSYS-style absolute path (`/c/...`, `/d/...`): a single letter
# directly under root. Native Windows Python does not resolve these (see
# module docstring, "Deliberate exemptions" — hand-tested, not assumed) —
# skip rather than risk a false BLOCK on a binary that is actually present.
_MSYS_ABS_PATH_RE = re.compile(r"^/[A-Za-z](?:/|$)")

# Stand-in for a literal backslash while tokenizing (see `_leading_binary_
# token`) — swapped back immediately after. A shell command string cannot
# contain a real NUL byte (bash cannot even represent one in argv), so this
# never collides with real input.
_BACKSLASH_SENTINEL = "\x00"

_MESSAGE_HEADER = "BLOCKED (verify-binary-on-path): {names} not found on PATH."
_MESSAGE_FOOTER = (
    "This is a PATH lookup only — it does not verify what the command does or "
    "any claim you made about it (verifying a claim is not mechanizable; see "
    "charter C-0). If this is a false positive (a shell function, alias, or "
    "builtin this guard does not know about), that is exactly the fail-open "
    "case this guard is designed to also get wrong safely in the other "
    "direction — say so and proceed. Otherwise install/expose the binary on "
    "PATH, or fix the typo, before re-running."
)


def _split_top_level(command: str) -> tuple[list[str], list[str]] | None:
    """Split `command` into segments at top-level `&&`, `||`, `;`, `|`, `&`,
    and newlines, respecting single/double-quoted spans.

    Returns `(segments, operators)` where `operators[i]` is the operator that
    follows `segments[i]` (so `len(operators) == len(segments) - 1`).

    Returns `None` when the command contains a construct this scanner does
    not model with confidence: unbalanced quotes, `$(...)`/backtick command
    substitution, `(...)` subshell/grouping, or a heredoc redirect (`<<`).
    The caller must then ALLOW THE WHOLE COMMAND — segment boundaries found
    by a scanner that does not understand these constructs cannot be
    trusted (fail open; see module docstring).
    """
    segments: list[str] = []
    operators: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            # Never interpret the escape — just don't let the escaped char
            # (which could itself be a quote or operator) confuse the scan.
            buf.append(ch)
            buf.append(command[i + 1])
            i += 2
            continue
        if ch == "$" and i + 1 < n and command[i + 1] == "(":
            return None
        if ch == "`":
            return None
        if ch in "()":
            return None
        if ch == "<" and i + 1 < n and command[i + 1] == "<":
            return None
        if ch == "&":
            if i + 1 < n and command[i + 1] == "&":
                segments.append("".join(buf))
                buf = []
                operators.append("&&")
                i += 2
                continue
            # Fd-duplication/combined redirection (`2>&1`, `>&2`, `&>out`):
            # `&` immediately adjacent to `>`/`<` is redirection syntax, NOT
            # the background/separator operator. Hand-tested finding, not a
            # hypothesis: without this, `python -m mypy . 2>&1 | tail -5`
            # split "1" out as its own segment and got checked (and BLOCKED)
            # as if it were a binary name. Treat the whole run as literal.
            prev = buf[-1] if buf else ""
            if prev in (">", "<"):
                buf.append(ch)
                i += 1
                continue
            if i + 1 < n and command[i + 1] == ">":
                buf.append(ch)
                buf.append(command[i + 1])
                i += 2
                continue
            segments.append("".join(buf))
            buf = []
            operators.append("&")
            i += 1
            continue
        if ch == "|":
            if i + 1 < n and command[i + 1] == "|":
                segments.append("".join(buf))
                buf = []
                operators.append("||")
                i += 2
                continue
            segments.append("".join(buf))
            buf = []
            operators.append("|")
            i += 1
            continue
        if ch in (";", "\n"):
            segments.append("".join(buf))
            buf = []
            operators.append(";")
            i += 1
            continue
        buf.append(ch)
        i += 1
    if quote is not None:
        return None
    segments.append("".join(buf))
    return segments, operators


def _leading_binary_token(segment: str) -> str | None:
    """The candidate binary token to check for `segment`, or `None` if there
    is nothing to check — a blank segment, a pure env-assignment, a shell
    builtin/keyword, an unresolvable variable/command substitution, or a
    dedicated existence-probe command. `None` always means "nothing checked
    here", never "blocked".
    """
    segment = segment.strip()
    if not segment:
        return None
    try:
        # posix=True correctly merges a quoted span with adjacent unquoted
        # text into ONE token (e.g. `BAZ="a b"` -> one token, quotes
        # stripped) — `posix=False` does NOT do this merge (hand-verified:
        # it splits `BAZ="a b"` into TWO tokens, `BAZ="a` and `b"`, which
        # then mis-tokenizes any env-assignment with a quoted, spaced
        # value). But posix mode also treats `\` as an escape character,
        # which would mangle the Windows-style backslash paths this repo's
        # commands routinely carry (`C:\Program Files\...`). Route around
        # both problems: swap every literal backslash for a sentinel byte
        # before splitting (so posix mode has no backslash to "escape" with
        # at all), then swap it back in every resulting token.
        tokens = shlex.split(segment.replace("\\", _BACKSLASH_SENTINEL), posix=True)
    except ValueError:
        return None  # unbalanced quote inside this segment -- fail open
    tokens = [t.replace(_BACKSLASH_SENTINEL, "\\") for t in tokens]
    while tokens and _ENV_ASSIGN_RE.match(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return None
    token = tokens[0]
    if token.startswith("$") or "$(" in token or "`" in token:
        return None  # variable/command substitution -- cannot resolve
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        token = token[1:-1]
    if not token:
        return None
    if token in _BUILTINS_AND_KEYWORDS or token in _PROBE_COMMANDS:
        return None
    if _MSYS_ABS_PATH_RE.match(token):
        return None  # e.g. /c/Users/... -- native Windows Python can't resolve this; fail open
    return token


def decide(command: str) -> GuardResult:
    """Pure decision over a raw Bash command string."""
    if not command or not command.strip():
        return GuardResult.allow()

    split = _split_top_level(command)
    if split is None:
        return GuardResult.allow()  # uncertain parse -- fail open

    segments, operators = split
    missing: list[str] = []
    seen: set[str] = set()
    for index, segment in enumerate(segments):
        guarded_by_or = index < len(operators) and operators[index] == "||"
        if guarded_by_or:
            continue  # defensive probe -- author already handles absence
        token = _leading_binary_token(segment)
        if token is None:
            continue
        if shutil.which(token) is not None:
            continue
        if token not in seen:
            seen.add(token)
            missing.append(token)

    if not missing:
        return GuardResult.allow()

    names = ", ".join(f"'{name}'" for name in missing)
    return GuardResult.block(_MESSAGE_HEADER.format(names=names), _MESSAGE_FOOTER)


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.command`."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    return decide(command)
