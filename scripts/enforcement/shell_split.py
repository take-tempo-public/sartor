"""Shared, deliberately partial shell-command scanning for the Bash-matcher guards.

Moved here from `guards/verify_binary_on_path.py` (item 136) so `block-merge-to-main` can
judge a command by its segments instead of its raw text. Behavior is unchanged by the move.

This is not a shell grammar. It splits at top-level operators and tokenizes one segment, and
it says so -- returning `None` -- whenever a construct appears that it does not model with
confidence. Each caller decides what `None` means for it: `verify-binary-on-path` fails open
(allows), `block-merge-to-main` fails closed (falls back to its raw-text regexes).
"""

from __future__ import annotations

import shlex

# Stand-in for a literal backslash while tokenizing (see `tokenize`) -- swapped back
# immediately after. A shell command string cannot contain a real NUL byte (bash cannot even
# represent one in argv), so this never collides with real input.
_BACKSLASH_SENTINEL = "\x00"


def split_top_level(command: str) -> tuple[list[str], list[str]] | None:
    """Split `command` into segments at top-level `&&`, `||`, `;`, `|`, `&`,
    and newlines, respecting single/double-quoted spans.

    Returns `(segments, operators)` where `operators[i]` is the operator that
    follows `segments[i]` (so `len(operators) == len(segments) - 1`).

    Returns `None` when the command contains a construct this scanner does
    not model with confidence: unbalanced quotes, `$(...)`/backtick command
    substitution, `(...)` subshell/grouping, or a heredoc redirect (`<<`).
    Segment boundaries found by a scanner that does not understand these
    constructs cannot be trusted.
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


def tokenize(segment: str) -> list[str] | None:
    """The words of one segment, quotes removed; `None` on an unbalanced quote.

    posix=True correctly merges a quoted span with adjacent unquoted text into ONE token
    (e.g. `BAZ="a b"` -> one token, quotes stripped) — `posix=False` does NOT do this merge
    (hand-verified: it splits `BAZ="a b"` into TWO tokens, `BAZ="a` and `b"`, which then
    mis-tokenizes any env-assignment with a quoted, spaced value). But posix mode also treats
    `\\` as an escape character, which would mangle the Windows-style backslash paths this
    repo's commands routinely carry (`C:\\Program Files\\...`). Route around both problems:
    swap every literal backslash for a sentinel byte before splitting (so posix mode has no
    backslash to "escape" with at all), then swap it back in every resulting token.
    """
    try:
        tokens = shlex.split(segment.replace("\\", _BACKSLASH_SENTINEL), posix=True)
    except ValueError:
        return None
    return [t.replace(_BACKSLASH_SENTINEL, "\\") for t in tokens]
