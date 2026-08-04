"""require-consumer-enumeration guard — charter **C-10**, "enumerate before you edit".

Block edits to a **schema, shared contract, or widely-consumed helper** (as classified by
`scripts/enforcement/blast_radius.py`) until `docs/dev/blast-radius/<branch-slug>.md`
exists with a filled-in `## Consumers` section **that names the surface being edited**.

**Why this is a hook and not a paragraph.** The guidance already existed, and the repo
had already converged on the discipline by hand — three times, each time caught by a
person rather than a mechanism (`docs/dev/diagnosis/compose-unawaited-reloads.md`'s
5-fixed-then-9-more-found, item 33's un-redirected telemetry call sites, and sprint A1's
brief needing an *adversarial-review amendment* to add the audit at all). The failure
mode is not ignorance of the rule; it is an agent, mid-change, judging that this
particular change is small enough not to need it. That is precisely what a rule may not
leave to judgment — the same reasoning that made C-7 a hook.

**There is no escape hatch, and none is needed.** The way through is always the same and
always available: **write down who consumes it.** If you cannot fill in `## Consumers`,
you have not looked yet — and that is the finding.

Two deliberate departures from `require_evidence_before_fix.py`, both load-bearing:

- **No blanket `*.md` exemption.** C-7 exempts every `.md` ("nothing to gain by blocking
  prose"). Here that would defeat the guard outright: `AGENT_HANDOFF_TEMPLATE.md`,
  `docs/dev/prov/SPEC.md` and the SCHEMA docs *are* contracts, and amending a
  `<!-- verbatim -->` section can block a handoff already in flight. Only the dossier's
  own directory is exempt.
- **Every branch, not just `fix/*`.** C-7 gates `fix/*` because that is where defects
  live. Schema and contract changes are normally `feat/*` or `chore/*`; gating on
  `fix/*` would miss the common case entirely.

Exemptions, each load-bearing:
- `docs/dev/blast-radius/**` — **the dossier lives here.** Block it and the guard
  forbids its own remedy. This exempts the branch's own dossier; note the classifier
  still lists `docs/dev/blast-radius/TEMPLATE.md` as a gated contract, so the exemption
  is what keeps *writing a dossier* free while *changing the template* stays gated.
- `tests/**` — a test proving a consumer still works is part of *doing* the enumeration,
  and `ui_pages/`-style page objects are test infrastructure the gate cannot usefully
  guard.
- `.claude/plans` — plan files must always stay writable (same carve-out every guard
  makes).
- not a git repo / detached HEAD / unclassified path — never wedge the caller on an edge
  case (mirrors `require_feature_branch.py`).
"""

from __future__ import annotations

import contextlib
import os
import posixpath
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.enforcement.blast_radius import Surface, classify
from scripts.enforcement.evidence import branch_slug, section, substantive
from scripts.enforcement.gitutil import git_branch
from scripts.enforcement.guards.result import GuardResult

BLAST_RADIUS_DIR = "docs/dev/blast-radius"

#: Path prefixes that stay writable even when the target is a gated surface. These are
#: the tools for *producing* the enumeration — see the module docstring.
_EXEMPT_PREFIXES = ("docs/dev/blast-radius/", "tests/", ".claude/plans")

#: Minimum non-boilerplate characters in `## Consumers` for it to count as filled in.
#: Matches `evidence._MIN_EVIDENCE_CHARS`'s bargain: low enough that one honest row
#: clears it, high enough that a stray heading does not.
_MIN_ENUMERATION_CHARS = 40


def dossier_path(repo_root: Path, branch: str) -> Path:
    """Where `branch`'s enumeration must live. Deterministic — the block message names it."""
    return repo_root / BLAST_RADIUS_DIR / f"{branch_slug(branch)}.md"


def template_text(repo_root: Path) -> str:
    """The blast-radius TEMPLATE's own text; "" if it is missing."""
    try:
        return (repo_root / BLAST_RADIUS_DIR / "TEMPLATE.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def has_consumer_enumeration(text: str, surface_path: str, template: str = "") -> bool:
    """True iff `## Consumers` carries real content **and** mentions `surface_path`.

    This is a **ceremony check, not a truth check** — the same bargain
    `evidence.has_observed_evidence` makes. It cannot tell a complete enumeration from a
    plausible-looking one, and it does not try. Its whole job is to make you go looking
    before you edit, because the act of trying to fill this in is what surfaces the
    consumers you did not know about.

    The `surface_path` mention is what stops one dossier rubber-stamping edits to an
    unrelated contract: a dossier that never names the file you are editing is a dossier
    for some other change. Matching is on the basename too, so a table row written as
    ``models.py:88`` still counts.
    """
    consumers = substantive(section(text, "Consumers"))
    if len(consumers) < _MIN_ENUMERATION_CHARS:
        return False
    if template and consumers == substantive(section(template, "Consumers")):
        return False
    haystack = text.replace("\\", "/")
    return surface_path in haystack or posixpath.basename(surface_path) in haystack


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


def _relative_to_repo(norm_path: str, repo_root: Path) -> str:
    """Repo-relative POSIX form of `norm_path`, or the input unchanged if outside."""
    with contextlib.suppress(ValueError, OSError):
        return Path(norm_path).resolve().relative_to(repo_root.resolve()).as_posix()
    return norm_path


def _is_exempt(rel_path: str, norm_path: str) -> bool:
    """True for paths that must stay writable so the enumeration can be written at all.

    `docs/dev/blast-radius/TEMPLATE.md` is carved back OUT of the dossier-directory
    exemption: a branch's own dossier must always be writable, but the template every
    future dossier is copied from is a contract like any other, and a blanket directory
    exemption would silently make its `GATED` entry dead code.
    """
    if rel_path == f"{BLAST_RADIUS_DIR}/TEMPLATE.md":
        return False
    return any(rel_path.startswith(p) or p in norm_path for p in _EXEMPT_PREFIXES)


def _message(surface: Surface, dossier: Path, repo_root: Path, exists: bool) -> tuple[str, ...]:
    try:
        shown = dossier.resolve().relative_to(repo_root.resolve()).as_posix()
    except (ValueError, OSError):
        shown = dossier.as_posix()
    why = f"has no '## Consumers' section naming {surface.path}" if exists else "does not exist"
    # ASCII only. Hook stderr lands on a cp1252 console on Windows, where a stray em-dash
    # comes back as a replacement char -- every other guard's message here is ASCII too.
    return (
        f"BLOCKED (require-consumer-enumeration): {surface.path} is a gated",
        f"{surface.kind} surface, but {shown} {why}.",
        "",
        f"Why this file is gated: {surface.why}",
        "",
        "Charter C-10 -- enumerate consumers before you edit. Before changing a schema,",
        "a shared contract, or a widely-consumed helper, find every site that depends on",
        "it (grep-complete, whole tree, every name it goes by) and decide-and-document",
        "each one BEFORE the first edit. An enumeration written afterwards is a",
        "description of what you did; written first, it is what tells you the change is",
        "bigger than you thought.",
        "",
        "To proceed:",
        f"  cp docs/dev/blast-radius/TEMPLATE.md {shown}",
        "  # Fill in '## Enumeration' (the exact commands + counts) and '## Consumers'",
        f"  # (one row per site, each with a decision). It must name {surface.path}.",
        "  # Sites you deliberately skip go under '## Deferred' WITH a reason.",
        "",
        "docs/dev/blast-radius/**, tests/** and unclassified files stay writable.",
        "There is no escape hatch, and none is needed: if you cannot fill in",
        "'## Consumers', you have not looked yet, and that is the finding.",
    )


def decide(file_path: str, env: Mapping[str, str]) -> GuardResult:
    """Pure decision: may we edit `file_path` given the branch and its enumeration?"""
    norm_path = (file_path or "").replace("\\", "/")
    if not norm_path:
        return GuardResult.allow()

    repo_root = _repo_root_for(norm_path, env)
    rel_path = _relative_to_repo(norm_path, repo_root)
    if _is_exempt(rel_path, norm_path):
        return GuardResult.allow()

    surface = classify(rel_path)
    if surface is None:
        return GuardResult.allow()

    directory = posixpath.dirname(norm_path) or "."
    while directory not in ("/", ".") and not Path(directory).is_dir():
        directory = posixpath.dirname(directory) or "."
    branch = git_branch(directory)
    # gitutil documents ""/"HEAD" as "don't know" (not a repo, detached HEAD, no git).
    # Never wedge the caller on an edge case -- mirrors require_feature_branch.py.
    if not branch or branch == "HEAD":
        return GuardResult.allow()

    dossier = dossier_path(repo_root, branch)
    try:
        text = dossier.read_text(encoding="utf-8")
    except OSError:
        return GuardResult.block(*_message(surface, dossier, repo_root, exists=False))
    if not has_consumer_enumeration(text, surface.path, template_text(repo_root)):
        return GuardResult.block(*_message(surface, dossier, repo_root, exists=True))
    return GuardResult.allow()


def claude_check(payload: dict[str, Any], env: Mapping[str, str] | None = None) -> GuardResult:
    """Claude PreToolUse adapter: extract `tool_input.file_path`."""
    if env is None:
        env = os.environ
    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    return decide(file_path, env)
