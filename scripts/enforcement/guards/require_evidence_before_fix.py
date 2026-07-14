"""require-evidence-before-fix guard — charter **C-7**, "evidence before mechanism".

On a `fix/*` branch, block edits to **production code** until
`docs/dev/diagnosis/<branch-slug>.md` exists with a filled-in `## Observed` section.

**Why this is a hook and not a paragraph.** The guidance already existed —
`docs/dev/AGENT_FAILURE_PATTERNS.md` §5a (diagnostics-as-fix), §5b (cascading fixes), §5e
(misplaced confidence) — and an agent read it, judged it inapplicable, and shipped two
confidently-wrong fixes for a bug it had never once observed. Both fixes were for *real*
defects, which is exactly what made them so convincing; neither was **the** defect. A day and
~30% of a weekly token budget, no solution. The failure mode *is* an agent deciding the rule
does not apply this time, so the rule cannot be advice. See
`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`.

**There is no escape hatch, and none is needed** — unlike `CLAUDE_ALLOW_MAIN_EDITS=1` or
`CLAUDE_CONFIRM_MERGE=1`, this guard can never wedge you. Docs and tests stay writable
(exemptions below), so the way through is always open and is always the same: **write down
what you saw.** If you cannot fill in `## Observed`, you have not looked yet — and that is the
finding, not an obstacle to it.

Exemptions, each load-bearing:
- `docs/**` — **the dossier lives here.** Block it and the guard forbids its own remedy.
- `tests/**` — **the instrument and the reproduction are tests.** C-7's first clause is "the
  first commit is the instrument, never the fix"; blocking tests would forbid the very thing
  the clause demands.
- any `*.md` — CHANGELOG, ledger, notes. Nothing to gain by blocking prose.
- `.claude/plans` — plan files must always stay writable (same carve-out every guard makes).
- not a `fix/*` branch / not a git repo / detached HEAD — never wedge the caller on an edge
  case (mirrors `require_feature_branch.py`).
"""

from __future__ import annotations

import os
import posixpath
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.evidence import diagnosis_path, has_observed_evidence, template_text
from scripts.enforcement.gitutil import git_branch
from scripts.enforcement.guards.result import GuardResult

#: Path prefixes that stay writable on a `fix/*` branch with no evidence yet. These are the
#: tools for *producing* the evidence — see the module docstring.
_EXEMPT_PREFIXES = ("docs/", "tests/", ".claude/plans")

_BRANCH_PREFIX = "fix/"


def _repo_root_for(norm_path: str, env: Mapping[str, str]) -> Path:
    """Best-effort repo root: `CLAUDE_PROJECT_DIR` if set, else walk up from the target."""
    project_dir = env.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    directory = Path(posixpath.dirname(norm_path) or ".")
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path(".")


def _is_exempt(norm_path: str, repo_root: Path) -> bool:
    """True for paths that must stay writable so the evidence can be written at all."""
    if norm_path.endswith(".md"):
        return True
    rel = norm_path
    try:
        rel = Path(norm_path).resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        # Outside the repo, or unresolvable — fall back to substring matching below.
        pass
    return any(rel.startswith(p) or p in norm_path for p in _EXEMPT_PREFIXES)


def _message(branch: str, dossier: Path, repo_root: Path, exists: bool) -> tuple[str, ...]:
    try:
        shown = dossier.resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        shown = dossier.as_posix()
    why = "has no filled-in '## Observed' section" if exists else "does not exist"
    # ASCII only. Hook stderr lands on a cp1252 console on Windows, where a stray em-dash
    # comes back as a replacement char -- every other guard's message here is ASCII too.
    return (
        f"BLOCKED (require-evidence-before-fix): on '{branch}', but {shown} {why}.",
        "",
        "Charter C-7 -- evidence before mechanism. For a defect you cannot reproduce on",
        "demand, the FIRST commit on the branch is the instrument or the reproduction,",
        "never the fix. A plausible mechanism you found by reading code is a HYPOTHESIS.",
        "",
        "To proceed, write what you SAW (not what you think is happening):",
        f"  cp docs/dev/diagnosis/TEMPLATE.md {shown}",
        "  # Fill in '## Observed' -- log lines, response bodies, a CI run id, a failing",
        "  # test. Keep '## Inferred' strictly separate: that is the part you have NOT",
        "  # proven, and it is the part that costs days when you forget which is which.",
        "",
        "docs/**, tests/** and *.md stay writable -- instrument and reproduce freely.",
        "There is no escape hatch, and none is needed: if you cannot fill in '## Observed',",
        "you have not looked yet, and that is the finding.",
    )


def decide(file_path: str, env: Mapping[str, str]) -> GuardResult:
    """Pure decision: may we edit `file_path` given the current branch and its dossier?"""
    norm_path = (file_path or "").replace("\\", "/")
    if not norm_path:
        return GuardResult.allow()

    repo_root = _repo_root_for(norm_path, env)
    if _is_exempt(norm_path, repo_root):
        return GuardResult.allow()

    directory = posixpath.dirname(norm_path) or "."
    while directory not in ("/", ".") and not Path(directory).is_dir():
        directory = posixpath.dirname(directory) or "."
    branch = git_branch(directory)
    if not branch.startswith(_BRANCH_PREFIX):
        return GuardResult.allow()

    dossier = diagnosis_path(repo_root, branch)
    try:
        text = dossier.read_text(encoding="utf-8")
    except OSError:
        return GuardResult.block(*_message(branch, dossier, repo_root, exists=False))
    if not has_observed_evidence(text, template_text(repo_root)):
        return GuardResult.block(*_message(branch, dossier, repo_root, exists=True))
    return GuardResult.allow()


def claude_check(payload: dict[str, Any], env: Mapping[str, str] | None = None) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.file_path`."""
    if env is None:
        env = os.environ
    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    return decide(file_path, env)
