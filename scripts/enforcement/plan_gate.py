"""The plan-approval gate: Claude Code's plan-mode lifecycle, in one Python module.

Ported from the retired ``hooks/check-plan-approved.sh``, ``hooks/mark-plan-approved.sh`` and
``hooks/lib/retire-approved-plan.sh`` (items 111/152, ``fix/python-direct-hooks-plan-gate``).
The state files, their names, the per-project key and the ``plan-archived`` receipt are
unchanged, so an approval written by the shell hooks is honoured here.

Three entry points, all reached through ``scripts/enforcement/adapters/hook.py``:

* ``claude_check(payload)``: the PreToolUse Edit|Write gate, run first inside
  ``claude_dispatcher.py`` as the ``check-plan-approved`` rule. Writes to
  ``~/.claude/plans/`` are always allowed, and each one is recorded. Any other edit needs a
  live approval whose plan has not changed since, and that no newer unapproved plan has
  superseded. The approval is retired (archived, never deleted) once its branch has merged or
  is gone.
* ``main(["", "mark-plan-approved"])``: PostToolUse ExitPlanMode. Records the approval.
* ``main(["", "plan-write-landed"])``: PreToolUse ExitPlanMode (item 143). Refuses approval
  when the last Write/Edit of the plan file never reached it, so the dialog would show the
  old text.

**Why speed is a correctness property here** (``docs/dev/diagnosis/python-direct-hooks-plan-
gate.md`` O1): the harness cancels a hook that outruns its timeout, and a cancelled PreToolUse
hook does not block. The shell version forked ``python3``, ``git``, ``cygpath``, ``tr`` and
``grep`` on every edit, and measured 28-35 s against a 20 s timeout under memory pressure, so
the gate was off. This module forks nothing on the steady path. It calls ``git`` only to
reconcile a stamp whose refs have moved (at most three calls).

**Kill-safe ordering.** Each write sequence is ordered so that an interruption at any point
leaves "no approval" (fail closed), never a live marker beside a stale stamp:

* retire removes the pointers before it archives anything;
* mark removes the old marker and the stamp before it writes the new marker, atomically.

**Project key.** ``CLAUDE_PROJECT_DIR`` names the session's project. The approval belongs to
that session, not to whichever worktree an edit lands in, so this module reads it directly as
an identity key. That is a deliberate second exception to "only ``gitutil`` reads
``CLAUDE_PROJECT_DIR``" (``tests/test_evidence_gate.py``): the variable is used as a key, never
as a dossier root.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.enforcement.guards.result import GuardResult  # noqa: E402

NO_APPROVAL = (
    "NO EDIT APPROVAL: No approved plan found for this project.",
    "Write a plan and call ExitPlanMode.",
)

_DRIVE_PATH = re.compile(r"^/([A-Za-z])(/|$)")
_CLOCK_TOLERANCE_NS = 250_000_000

#: Env var relocating the state dir (default ``~/.claude/plans``). A test seam, the
#: ``SARTOR_WITNESS_STATE_DIR`` way: ``tests/conftest.py`` points it at a per-test dir so no
#: test touches a live session's approval. It is not a bypass: the gate still needs a marker
#: there, and only ``ExitPlanMode`` writes one.
PLANS_DIR_ENV = "SARTOR_PLANS_DIR"


def _native(path: str) -> str:
    """An MSYS-style ``/c/Users/x`` path as ``C:/Users/x`` on Windows; anything else unchanged.

    A hook launched through Git Bash can hand Python a ``HOME`` in MSYS form, which native
    Windows Python reads as ``C:\\c\\Users\\x``. Done in-process, where the shell version
    forked ``cygpath`` four times.
    """
    if os.name == "nt":
        m = _DRIVE_PATH.match(path)
        if m:
            return f"{m.group(1).upper()}:/{path[m.end() :]}"
    return path


def project_key(project_dir: str) -> str:
    """``tr -c 'A-Za-z0-9' '-'`` byte for byte: every non-alphanumeric BYTE becomes ``-``, so
    a non-ASCII character becomes one dash per UTF-8 byte, as it did in the shell version."""
    raw = project_dir.encode("utf-8")
    return "".join(chr(b) if chr(b).isascii() and chr(b).isalnum() else "-" for b in raw)


class _State:
    """The per-project state file paths under ``~/.claude/plans``."""

    def __init__(self, env: Mapping[str, str]) -> None:
        override = env.get(PLANS_DIR_ENV)
        if override:
            self.plans = Path(_native(override))
        else:
            home = env.get("HOME") or str(Path.home())
            self.plans = Path(_native(home)) / ".claude" / "plans"
        self.project_dir = env.get("CLAUDE_PROJECT_DIR", "")
        self.key = project_key(self.project_dir or "unknown")
        self.marker = self.plans / f".approved-{self.key}"
        self.current = self.plans / f".current-{self.key}"
        self.stamp = self.plans / f".approved-branch-{self.key}"
        self.attempt = self.plans / f".plan-attempt-{self.key}"


def _first_line(path: Path) -> str:
    """The first line of ``path`` without its line ending; "" when absent or unreadable."""
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            return f.readline().rstrip("\r\n")
    except OSError:
        return ""


def _mtime(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _newer(a: Path, b: Path) -> bool:
    """bash ``[ a -nt b ]``: ``a`` exists and is newer than ``b``, or ``b`` does not exist."""
    ma, mb = _mtime(a), _mtime(b)
    return ma is not None and (mb is None or ma > mb)


def _unlink(*paths: Path) -> None:
    for p in paths:
        with contextlib.suppress(OSError):
            p.unlink()


# --------------------------------------------------------------------------- #
# git refs, read from .git directly (no fork on the steady path)
# --------------------------------------------------------------------------- #


def _ref_sha(gitdir: Path, ref: str) -> str:
    """The SHA a loose or packed ``refs/heads/<ref>`` points at; "" if unresolvable."""
    sha = _first_line(gitdir / "refs" / "heads" / ref).strip()
    if sha:
        return sha
    target = f"refs/heads/{ref}"
    try:
        lines = (gitdir / "packed-refs").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in lines.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == target:
            return parts[0]
    return ""


def _current_branch(gitdir: Path) -> str:
    """The checked-out branch from ``.git/HEAD``; "" for a detached or unreadable HEAD."""
    head = _first_line(gitdir / "HEAD")
    prefix = "ref: refs/heads/"
    return head[len(prefix) :] if head.startswith(prefix) else ""


def _git(project_dir: str, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell, local git only
            ["git", "-C", project_dir, *args],  # noqa: S607 - `git` resolved from PATH
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None


def _should_archive(project_dir: str, gitdir: Path, main_ref: str, branch: str, base: str) -> bool:
    """True iff the stamped ``branch`` has merged into ``main_ref`` and moved past ``base``,
    or no longer exists. Fails open (False, "leave it alone") on anything ambiguous: no
    ``git``, an unexpected exit code, an unresolvable ref.

    ``base`` (main's tip when the stamp was written) is what stops a zero-commit branch from
    being archived the moment main moves for an unrelated reason.
    """
    if not branch or shutil.which("git") is None:
        return False
    tip = _ref_sha(gitdir, branch)
    if not tip:
        # Not found by a direct read: confirm with git before calling it gone (a ref store
        # this reader does not understand must not look like a deleted branch).
        r = _git(project_dir, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
        if r is None:
            return False
        if r.returncode == 1:
            return True  # branch is gone: re-earn approval
        if r.returncode != 0:
            return False
        r = _git(project_dir, "rev-parse", f"refs/heads/{branch}")
        tip = r.stdout.strip() if r is not None and r.returncode == 0 else ""
        if not tip:
            return False
    r = _git(project_dir, "merge-base", "--is-ancestor", tip, f"refs/heads/{main_ref}")
    if r is None or r.returncode != 0:
        return False  # not confirmed merged: fail open
    if not base:
        return True  # merged, no base recorded (malformed stamp): conservative default
    r = _git(project_dir, "merge-base", "--is-ancestor", tip, base)
    return r is not None and r.returncode == 1  # merged AND moved past the fork point


# --------------------------------------------------------------------------- #
# retire: archive, never delete
# --------------------------------------------------------------------------- #


def retire(state: _State, branch: str, session: str) -> None:
    """Retire this project's approval: remove the pointers, archive the plan files, then write
    the local manifest and the tracked ``plan-archived`` receipt.

    Owner directive (item 45): never silently delete approval state. Archive it, with a
    receipt. Every failure after the pointer removal is swallowed: retiring is bookkeeping on
    top of the caller's gate decision, not itself a gate.
    """
    approved_plan = _first_line(state.marker)
    current_plan = _first_line(state.current)
    _unlink(state.marker, state.current, state.stamp)  # kill-safe: fail closed from here on

    key_hash = hashlib.sha256(state.key.encode("utf-8")).hexdigest()[:12]
    now = datetime.now(UTC)
    archive_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{key_hash}"
    archive_dir = state.plans / "archive" / archive_id
    archived_basename = ""

    targets = [approved_plan]
    if current_plan != approved_plan:
        targets.append(current_plan)
    for plan in targets:
        if not plan:
            continue
        src = Path(_native(plan))
        if not src.is_file():
            continue
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(archive_dir / src.name))
        except OSError:
            continue
        if plan == approved_plan:
            archived_basename = src.name

    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if archive_dir.is_dir():
        manifest = {
            "approved_plan": approved_plan,
            "current_plan": current_plan,
            "project_dir": state.project_dir,
            "archive_id": archive_id,
            "archived_at": ts,
        }
        with contextlib.suppress(OSError):
            (archive_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

    # Tracked ledger receipt: basename only, never the absolute path (the repo is public).
    # newline="\n" keeps CR bytes out of the working tree
    # (tests/test_verify_doc_template.py::TestLedgerWorkingTreeBytes).
    if state.project_dir and session and archived_basename:
        record = {
            "event": "plan-archived",
            "session": session,
            "branch": branch or "unknown",
            "archive_id": archive_id,
            "plan": archived_basename,
            "ts": ts,
        }
        with contextlib.suppress(OSError):
            ledger = Path(state.project_dir) / "docs" / "dev" / "ledger"
            ledger.mkdir(parents=True, exist_ok=True)
            with (ledger / f"{session}.jsonl").open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(record) + "\n")


# --------------------------------------------------------------------------- #
# check-plan-approved (PreToolUse Edit|Write)
# --------------------------------------------------------------------------- #


def _session(payload: Mapping[str, Any], env: Mapping[str, str]) -> str:
    return str(payload.get("session_id") or env.get("CLAUDE_CODE_SESSION_ID") or "")


def check(payload: Mapping[str, Any], env: Mapping[str, str]) -> GuardResult:
    """The Edit|Write gate. See the module docstring."""
    state = _State(env)
    tool_input = payload.get("tool_input") or {}
    file_path = str(tool_input.get("file_path", "")) if isinstance(tool_input, dict) else ""
    norm = file_path.replace("\\", "/")

    if ".claude/plans" in norm:
        # The plan file must always be writable. Record which plan THIS project is writing
        # (for mark), and when the attempt was made (for plan-write-landed, item 143).
        # Recorded before any other guard in the dispatcher can pause the write.
        if norm.endswith(".md"):
            with contextlib.suppress(OSError):
                state.plans.mkdir(parents=True, exist_ok=True)
                state.current.write_text(norm + "\n", encoding="utf-8", newline="\n")
                state.attempt.write_text(
                    f"{time.time_ns()}\t{norm}\n", encoding="utf-8", newline="\n"
                )
        return GuardResult.allow()

    if not state.marker.is_file():
        return GuardResult.block(*NO_APPROVAL)

    approved = _first_line(state.marker)
    approved_path = Path(_native(approved)) if approved else None
    if (
        approved_path is not None
        and approved_path.is_file()
        and _newer(approved_path, state.marker)
    ):
        return GuardResult.block(
            f"PLAN NOT APPROVED: '{approved_path.name}' is newer than approval marker.",
            "Call ExitPlanMode and get user approval before editing files.",
        )

    # A plan written after the live approval, and not the approved one, means the approval
    # no longer describes the work: ExitPlanMode was not called, or its `mark` hook was
    # killed before it wrote (O1). Edits must not run on under the previous approval.
    current = _first_line(state.current)
    if current and current != approved:
        current_path = Path(_native(current))
        if current_path.is_file() and _newer(current_path, state.marker):
            return GuardResult.block(
                f"PLAN NOT APPROVED: '{current_path.name}' was written after the last "
                "approval, and the live approval is for a different plan.",
                "Call ExitPlanMode and get user approval before editing files.",
            )

    return _reconcile(state, payload, env)


def _reconcile(state: _State, payload: Mapping[str, Any], env: Mapping[str, str]) -> GuardResult:
    """Branch-merge reconciliation (item 45 / D3(c)), then the late-bound stamp.

    ExitPlanMode fires while HEAD is still on main, so the stamp naming the approved branch is
    written on the first production edit after the switch, never at approval time. Covers an
    ordinary checkout only (``.git`` a directory); a linked worktree is skipped, as before.
    """
    project_dir = state.project_dir
    if not project_dir:
        return GuardResult.allow()
    gitdir = Path(project_dir) / ".git"
    if not gitdir.is_dir():
        return GuardResult.allow()
    if _ref_sha(gitdir, "main"):
        main_ref = "main"
    elif _ref_sha(gitdir, "master"):
        main_ref = "master"
    else:
        return GuardResult.allow()
    cur_branch = _current_branch(gitdir)

    # Reconcile whatever is stamped FIRST, before the late-bind below can overwrite it: the
    # stamped branch may have merged and been left within the same session
    # (docs/dev/diagnosis/plan-approval-branch-switch-gap.md).
    lines = [*_read_lines(state.stamp), "", ""]
    stamped_branch = lines[0].removeprefix("branch=")
    stamped_base = lines[1].removeprefix("base=")
    if stamped_branch:
        heads = gitdir / "refs" / "heads"
        branch_ref = heads / stamped_branch
        # A packed ref (after `git gc`) has no loose file. The shell version read that as
        # "missing" and paid the git calls on every edit; a packed-refs entry is present,
        # and packed-refs' own mtime below still catches it moving.
        present = branch_ref.exists() or bool(_ref_sha(gitdir, stamped_branch))
        need_check = (
            not present
            or ((heads / "main").is_file() and _newer(heads / "main", state.stamp))
            or ((heads / "master").is_file() and _newer(heads / "master", state.stamp))
            or ((gitdir / "packed-refs").is_file() and _newer(gitdir / "packed-refs", state.stamp))
            or _newer(branch_ref, state.stamp)
        )
        if need_check:
            if _should_archive(project_dir, gitdir, main_ref, stamped_branch, stamped_base):
                retire(state, cur_branch, _session(payload, env))
                return GuardResult.block(
                    f"PLAN RETIRED: branch '{stamped_branch}' has already merged (or no "
                    "longer exists) — its approval was archived, not deleted.",
                    "Write a plan and call ExitPlanMode to start the next task.",
                )
            # Nothing to do: advance the baseline so the pre-filter above stays fork-free
            # until something actually changes again.
            with contextlib.suppress(OSError):
                os.utime(state.stamp, None)

    if cur_branch and cur_branch not in ("main", "master") and stamped_branch != cur_branch:
        base = _ref_sha(gitdir, main_ref)
        if base:
            with contextlib.suppress(OSError):
                state.stamp.write_text(
                    f"branch={cur_branch}\nbase={base}\n", encoding="utf-8", newline="\n"
                )
    return GuardResult.allow()


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[:2]
    except OSError:
        return []


def claude_check(payload: Mapping[str, Any]) -> GuardResult:
    """The dispatcher's entry point (``check-plan-approved``)."""
    return check(payload, os.environ)


# --------------------------------------------------------------------------- #
# mark-plan-approved (PostToolUse ExitPlanMode) and plan-write-landed (PreToolUse)
# --------------------------------------------------------------------------- #


def mark(env: Mapping[str, str]) -> None:
    """Record the approval of the plan this project was writing.

    Fail-closed order: drop the old marker, drop the stamp, then write the new marker
    atomically. A kill between any two steps leaves no approval (the next edit says NO EDIT
    APPROVAL), never a fresh marker beside a stale stamp that retires it (O1).
    """
    state = _State(env)
    _unlink(state.marker, state.stamp)
    try:
        content = state.current.read_bytes() if state.current.is_file() else b""
    except OSError:
        content = b""
    with contextlib.suppress(OSError):
        state.plans.mkdir(parents=True, exist_ok=True)
        tmp = state.marker.with_name(state.marker.name + ".tmp")
        tmp.write_bytes(content)
        os.replace(tmp, state.marker)


def plan_write_landed(env: Mapping[str, str]) -> GuardResult:
    """Item 143: refuse ExitPlanMode when the last recorded Write/Edit of the plan file did not
    reach it (its mtime is older than the attempt). The approval dialog shows the file, so
    approving now would approve the OLD text.

    Known limit (C-0): this covers the plan file only. Any other call batched after a
    paused Write still runs on stale input; a per-call hook cannot cancel the rest of a batch.
    """
    state = _State(env)
    line = _first_line(state.attempt)
    stamp, _, plan = line.partition("\t")
    if not plan or not stamp.isdigit():
        return GuardResult.allow()
    plan_path = Path(_native(plan))
    mtime = _mtime(plan_path)
    # NTFS stamps mtime from the coarse system clock (~15.6 ms ticks) while time_ns() is
    # precise, so a write landing just after its attempt can read marginally EARLIER. A
    # paused write leaves the previous write's mtime, at least a prompt turn older, so this
    # tolerance cannot hide one. (A 2 s-granularity filesystem such as FAT is not covered.)
    if mtime is not None and mtime >= int(stamp) - _CLOCK_TOLERANCE_NS:
        return GuardResult.allow()
    return GuardResult.block(
        f"PLAN NOT SAVED (plan-write-landed): the last Write/Edit of '{plan_path.name}' never "
        "reached the file (it was paused or refused), so this approval would show the OLD "
        "plan text.",
        "Re-run that Write on its own, then call ExitPlanMode in a separate message.",
    )


def main(argv: list[str]) -> int:
    """CLI: ``argv[1]`` is ``check-plan-approved``, ``mark-plan-approved`` or
    ``plan-write-landed``; stdin is the hook payload."""
    name = argv[1] if len(argv) == 2 else ""
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if name == "mark-plan-approved":
        mark(os.environ)
        return 0
    if name == "check-plan-approved":
        result = check(payload, os.environ)
    elif name == "plan-write-landed":
        result = plan_write_landed(os.environ)
    else:
        print(
            "usage: plan_gate.py <check-plan-approved|mark-plan-approved|plan-write-landed>",
            file=sys.stderr,
        )
        return 2
    for message in result.messages:
        print(message, file=sys.stderr)
    return 2 if result.blocked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
