"""block-merge-to-main guard.

Blocks `git merge`/`git push` targeting `main`/`master` unless the command (or
the caller's environment, for the git-native adapters) opts in with
`CLAUDE_CONFIRM_MERGE=1`. Ported from
`.claude-plugin/hooks/block-merge-to-main.sh` — and fixes the two defects
filed against it (`docs/dev/RELEASE_CHECKLIST.md`, "Portable-enforcement-core
migration" ledger row, Train-1 note, 2026-07-07):

(i) **merge-base/merge-tree false positive.** The original
    `\\bgit[[:space:]]+merge\\b` pattern's trailing `\\b` is satisfied at the
    `e`→`-` transition (both are non-word-adjacent), so a READ-ONLY
    `git merge-base main HEAD` (or `git merge-tree`) matched as if it were a
    real merge. Fixed with a negative lookahead: `merge` must NOT be
    immediately followed by `-` (a real `git merge` invocation is always
    followed by whitespace, an option, a ref, or end of string).

(ii) **cwd resolved in the hook's own process, not the caller's worktree.**
     The dominant "checkout main, then `git merge feature --no-ff`" direction
     resolved HEAD via a bare `git rev-parse --abbrev-ref HEAD`, which runs in
     the hook *process's* ambient cwd. Under W-1 (parallel worktree sessions)
     that cwd is not guaranteed to be the invoking agent's own worktree, so a
     session working in a feature-branch worktree could be judged against
     whatever branch the main checkout happens to sit on (or vice versa).
     Fixed by resolving against the invocation's own working directory, taken
     from the PreToolUse hook-input `cwd` field every hook receives alongside
     `tool_input` (see `plugin-dev:hook-development`) — never the hook
     process's own ambient cwd.

The git-native adapters (`git_operation_check` / `git_push_check`) don't need
either fix: git itself supplies the exact operation (a real merge/push, never
`merge-base`) and resolves HEAD in the invoking worktree by construction, so
there is no regex to tighten and no cwd to hand off.

**Wiki-freshness extension (`ci/doc-merge-gate`, merge=publish gate item 5).**
`docs/dev/documentation-architecture.md` ("Gates — merge = publish") names this
guard as the intended home for the freshness check: a merge to `main` is the
moment the (future) hosted site would republish a stale wiki. Once a command
would otherwise be ALLOWED (not targeting main, or targeting main with
`CLAUDE_CONFIRM_MERGE=1` already present), `_wiki_freshness_result()` runs
`scripts/wiki_freshness.check()` against the invoking worktree and blocks if
the drift is past `wiki_freshness.BLOCK_THRESHOLD`. Deliberately **not**
bypassed by `CLAUDE_CONFIRM_MERGE=1` — that token confirms the merge *target*,
not doc freshness; the only way through is running `/wiki-self-update` (or
`/wiki-ingest`) to genuinely advance the checkpoint, mirroring the
`DOC-STATUS` gate's no-escape-hatch design. Silent (allows) when there is no
real ingest baseline yet — same "sentinel = not an error" rule
`wiki-freshness-reminder.sh` already uses.

**Wiki-freshness re-scope to push-only (`chore/merge-channel-alignment`,
2026-07-19).** The arm above was wired to *both* merge and push. That made a
branch which had just refreshed the wiki unmergeable: standing on `main` to
merge it, `_wiki_freshness_result()` read **main's** still-stale checkpoint
against **main's** HEAD and blocked — the block was triggered by the state the
merge would fix. Observed on `refactor/css-cascade-collapse` (RELEASE_CHECKLIST
carry-forward item 18, filed then dissolved here rather than patched).

The fix is not a better drift computation; it is putting the check at the right
event. **A local merge publishes nothing** — so it carries no freshness arm now.
The publish moments are:
  * `git push origin main` — still gated here (see `git_push_check` / the push
    branch of `decide`), because that genuinely republishes.
  * the **PR merge** — gated in CI, not locally: `tests/test_wiki_freshness_gate.py`
    runs inside `python -m scripts.gate`, which is the required
    "Lint, type-check, test" status check on every PR to `main`. CI evaluates the
    PR's *merge ref*, i.e. the post-merge state — precisely the thing the local
    hook could not see and got wrong.
Since `main` is PR-only under branch protection, that PR-side CI check is the
enforcement point that actually matters; the local arms are the backstop for the
two paths CI cannot observe (a local merge, and a direct push).

**Judged by segment, not by raw text (items 136 + 149, `fix/hook-guard-false-blocks`).** The
three regexes used to run over the whole command string, which failed both ways: merge *text*
in an argument (`grep -E 'git merge --no-ff|main' ...`) blocked (136), and a real merge with a
git global option in front (`git -C . merge main`) was allowed, because the regexes needed
`merge` right after `git` (149). `targets_main` now splits the command at top-level operators
(`scripts/enforcement/shell_split.py`, shared with `verify-binary-on-path`) and judges each
segment by its command word:

  * `git` -- read past its global options to the subcommand. `merge`/`push` are judged on
    their arguments **and** by the raw regexes on that segment, so a git merge or push can
    only gain a block, never lose one. Any other subcommand is ignored unless a bare `merge`
    or `push` word appears in it (an unknown global option could have hidden the real
    subcommand); then the segment gets the raw regexes.
  * a text-only command (`grep`, `rg`, `echo`, `printf`, `cat`, ...) -- ignored: its
    arguments are text, and it cannot run them.
  * anything else -- interpreters (`bash -c`, `python`), `eval`, `xargs`, `sudo`, a brace
    group -- gets the raw regexes on that segment, widened to allow global options.

Heredoc bodies are cut out before splitting and always get the raw regexes, since a body may
be executed by whatever reads it. A command the splitter cannot model (`$(...)`, backticks,
subshells, an unclosed heredoc) gets the raw regexes on the whole text, as before. So the
parser can stop over-blocking only where the text is provably an argument to a command that
cannot execute it; everywhere it is unsure, it fails closed. **Known limit (C-0):** a heredoc
body that merely *mentions* a merge to main (Python source, prose) still blocks.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.gitutil import git_branch
from scripts.enforcement.guards.result import GuardResult
from scripts.enforcement.shell_split import split_top_level, tokenize
from scripts.wiki_freshness import BLOCK_THRESHOLD as _WIKI_BLOCK_THRESHOLD
from scripts.wiki_freshness import check as _wiki_freshness_check

_CONFIRM_TOKEN = "CLAUDE_CONFIRM_MERGE=1"  # noqa: S105 - not a credential; the literal escape-hatch token this guard's command-string parser matches

# Defect (i): `(?!-)` refuses to match when `merge` is immediately followed by
# `-` (merge-base / merge-tree / any future `git merge-*` plumbing subcommand).
# Item 149: up to six words (global options and their values, `-C .`, `-c k=v`) may sit
# between `git` and the subcommand. Bounded so a long line cannot pair a far-off `git` with an
# unrelated `merge`.
_GIT_PREFIX = r"\bgit(?:\s+\S+){0,6}?\s+"
_MERGE_MAIN_RE = re.compile(_GIT_PREFIX + r"merge(?!-)\b.*\b(?:main|master)\b")
_MERGE_RE = re.compile(_GIT_PREFIX + r"merge(?!-)\b")
_PUSH_MAIN_RE = re.compile(_GIT_PREFIX + r"push\b.*\borigin\s+(?:main|master)\b")
_MAIN_WORD_RE = re.compile(r"\b(?:main|master)\b")

_MAIN_BRANCHES = frozenset({"main", "master"})
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Commands whose arguments are only ever text: they cannot run a merge they mention. Kept
# short on purpose. `sed` (GNU `e`), `awk` (`system()`), `find -exec` and `xargs` CAN execute,
# so they are absent and get the raw regexes.
_TEXT_ONLY_COMMANDS = frozenset(
    {"grep", "egrep", "fgrep", "rg", "echo", "printf", "cat", "head", "tail", "wc", "less"}
)

# git global options that consume the NEXT word as their value (`git -C <path> merge`).
# Others (`--no-pager`, `-P`, `--git-dir=<x>`) are a single word.
_GIT_VALUE_OPTIONS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
)

# A heredoc operator: `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`; never `<<<` (a here-string).
_HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")

_MESSAGE_LINES = (
    "BLOCKED (block-merge-to-main): git merge/push targeting main or master.",
    "`main` is PR-only: branch protection requires a pull request + passing checks, so a "
    "local merge/push is rejected for a non-admin and silently bypasses those checks for an "
    "admin. Land work with: git push -u origin <branch> -> open the PR -> wait for required "
    "checks -> gh pr merge <n> --merge (never --squash/--rebase) -> git pull --ff-only.",
    "If you really intend this anyway, prefix the command with: CLAUDE_CONFIRM_MERGE=1",
    "Example: CLAUDE_CONFIRM_MERGE=1 git merge feature-branch --no-ff -m '...'",
)


def _wiki_freshness_result(invocation_cwd: str) -> GuardResult | None:
    """None = no objection; a block GuardResult when the wiki is stale past threshold.

    `invocation_cwd` must be the invoking worktree (never this file's own on-disk
    location) — see module docstring "defect (ii)" and `scripts/wiki_freshness.py`'s
    module docstring for why.
    """
    ok, drift = _wiki_freshness_check(Path(invocation_cwd or "."))
    if ok:
        return None
    return GuardResult.block(
        "BLOCKED (block-merge-to-main): docs/wiki/ is "
        f"{drift} file(s) stale vs HEAD (>= the {_WIKI_BLOCK_THRESHOLD}-file "
        "merge=publish threshold — see scripts/wiki_freshness.py).",
        "Run /wiki-self-update (bounded Haiku diff-pass) or /wiki-ingest (full cold pass) "
        "to advance docs/wiki/.last_ingest_sha before merging to main.",
        "Not bypassed by CLAUDE_CONFIRM_MERGE=1 (that token confirms the merge target, "
        "not doc freshness); /wiki-lint prints the drift report.",
    )


class _Verdict:
    """Accumulates what the segments say; the cwd branch is read at most once, lazily."""

    def __init__(self, invocation_cwd: str) -> None:
        self._cwd = invocation_cwd or "."
        self._branch: str | None = None
        self.merge_main = False
        self.push_main = False

    def _on_main(self) -> bool:
        if self._branch is None:
            self._branch = git_branch(self._cwd)
        return self._branch in _MAIN_BRANCHES

    def raw(self, text: str) -> None:
        """The old whole-text judgment, applied to `text` (widened for global options)."""
        if _MERGE_MAIN_RE.search(text):
            self.merge_main = True
        if _PUSH_MAIN_RE.search(text):
            self.push_main = True
        if not self.merge_main and _MERGE_RE.search(text) and self._on_main():
            self.merge_main = True

    def merge(self, args: list[str]) -> None:
        if any(_MAIN_WORD_RE.search(arg) for arg in args) or self._on_main():
            self.merge_main = True

    def push(self, args: list[str]) -> None:
        positional = [a for a in args if not a.startswith("-")]
        for refspec in positional[1:]:  # positional[0] is the remote
            dst = refspec.lstrip("+").rsplit(":", 1)[-1].removeprefix("refs/heads/")
            if dst in _MAIN_BRANCHES:
                self.push_main = True


def _cut_heredocs(command: str) -> tuple[str, list[str]] | None:
    """`(command_without_heredoc_bodies, bodies)`, or `None` if a heredoc never closes.

    Quote-unaware on purpose: a `<<WORD` inside quotes is taken for a heredoc too. That only
    moves lines into a body, and every body gets the raw regexes, so a mistake here can add a
    block but never remove one.
    """
    if "<<" not in command:
        return command, []
    kept: list[str] = []
    bodies: list[str] = []
    pending: list[tuple[bool, str]] = []  # (strip_tabs, delimiter), in order
    body: list[str] = []
    for line in command.split("\n"):
        if pending:
            strip_tabs, delimiter = pending[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                bodies.append("\n".join(body))
                body = []
                pending.pop(0)
            else:
                body.append(line)
            continue
        for match in _HEREDOC_RE.finditer(line):
            pending.append((match.group(1) == "-", match.group(3)))
        kept.append(_HEREDOC_RE.sub("", line))
    if pending:
        return None
    return "\n".join(kept), bodies


def _git_subcommand(tokens: list[str]) -> tuple[str, list[str]]:
    """`(subcommand, its_args)` for a `git ...` token list, past git's global options."""
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in _GIT_VALUE_OPTIONS else 1
    if i >= len(tokens):
        return "", []
    return tokens[i], tokens[i + 1 :]


def _judge_segment(segment: str, verdict: _Verdict) -> None:
    tokens = tokenize(segment)
    if tokens is None:
        verdict.raw(segment)
        return
    while tokens and _ENV_ASSIGN_RE.match(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return
    word = tokens[0]
    if word in _TEXT_ONLY_COMMANDS:
        return
    if word != "git":
        verdict.raw(segment)
        return
    subcommand, args = _git_subcommand(tokens)
    if subcommand == "merge":
        verdict.merge(args)
        verdict.raw(segment)
    elif subcommand == "push":
        verdict.push(args)
        verdict.raw(segment)
    elif "merge" in tokens or "push" in tokens:
        verdict.raw(segment)  # an unknown global option may have hidden the subcommand


def _judge(command: str, invocation_cwd: str) -> _Verdict:
    verdict = _Verdict(invocation_cwd)
    cut = _cut_heredocs(command)
    split = split_top_level(cut[0]) if cut is not None else None
    if cut is None or split is None:
        verdict.raw(command)
        return verdict
    for body in cut[1]:
        verdict.raw(body)
    for segment in split[0]:
        _judge_segment(segment, verdict)
    return verdict


def targets_main(command: str, invocation_cwd: str) -> bool:
    """True if `command` is a merge/push that lands on `main`/`master`.

    `invocation_cwd` is consulted ONLY for the dominant "checkout main, then
    `git merge feature`" direction (defect ii) — it must be the invoking
    agent's own working directory (the PreToolUse `cwd` field), never the
    hook process's ambient cwd. Segments are judged as the module docstring describes.
    """
    verdict = _judge(command, invocation_cwd)
    return verdict.merge_main or verdict.push_main


def decide(command: str, invocation_cwd: str) -> GuardResult:
    """Pure decision for the Claude Bash-command-string path.

    The wiki-freshness arm is scoped to **push** only (see module docstring
    "Wiki-freshness re-scope"): a local merge publishes nothing, so gating it on
    doc freshness blocked the one branch that had just refreshed the wiki.
    """
    verdict = _judge(command, invocation_cwd)
    if not (verdict.merge_main or verdict.push_main):
        return GuardResult.allow()
    if _CONFIRM_TOKEN not in command:
        return GuardResult.block(*_MESSAGE_LINES)
    if verdict.push_main:
        return _wiki_freshness_result(invocation_cwd) or GuardResult.allow()
    return GuardResult.allow()


def claude_check(payload: dict[str, Any]) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.command` + top-level `cwd`."""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    invocation_cwd = payload.get("cwd", "") or ""
    return decide(command, invocation_cwd)


def git_operation_check(
    current_branch: str, env: Mapping[str, str] | None = None, repo_root: str = "."
) -> GuardResult:
    """Native git `pre-merge-commit` adapter.

    Git already knows this IS a real merge (plumbing commands like
    `merge-base`/`merge-tree` never invoke this hook) and already resolves
    HEAD correctly in the invoking worktree — no regex, no cwd handoff.

    `repo_root` is **currently unread** and retained deliberately: it is part of
    this adapter's published signature (the git `pre-merge-commit` wiring and the
    enforcement-core tests both pass it), and it was the wiki-freshness arm's
    argument before that arm was scoped to push-only. Keeping it costs nothing and
    avoids a signature break; re-adding a repo-scoped check here would use it.
    """
    if env is None:
        env = os.environ
    if current_branch not in ("main", "master"):
        return GuardResult.allow()
    if env.get("CLAUDE_CONFIRM_MERGE") != "1":
        return GuardResult.block(*_MESSAGE_LINES)
    # No wiki-freshness arm here: a local merge publishes nothing. The publish
    # moment is the push (below) or the PR merge (gated in CI by the required
    # `tests/test_wiki_freshness_gate.py` check). See module docstring.
    return GuardResult.allow()


def git_push_check(
    remote_ref: str, env: Mapping[str, str] | None = None, repo_root: str = "."
) -> GuardResult:
    """Native git `pre-push` adapter.

    Git supplies the exact remote ref being updated (e.g. `refs/heads/main`)
    on stdin — no shell-string regex parsing needed at all. `repo_root` defaults
    to "." for the same reason as `git_operation_check`.
    """
    if env is None:
        env = os.environ
    branch = remote_ref.removeprefix("refs/heads/")
    if branch not in ("main", "master"):
        return GuardResult.allow()
    if env.get("CLAUDE_CONFIRM_MERGE") != "1":
        return GuardResult.block(*_MESSAGE_LINES)
    return _wiki_freshness_result(repo_root) or GuardResult.allow()
