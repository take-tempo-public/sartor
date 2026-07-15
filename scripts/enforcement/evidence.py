"""Locate + read the diagnosis dossier for a branch — the C-7/C-8 evidence primitive.

One artifact, three enforcement points. `docs/dev/diagnosis/<branch-slug>.md` is:

- **the thing you must write before you may fix** — `guards/require_evidence_before_fix.py`
  blocks production edits on a `fix/*` branch until its `## Observed` section is non-empty
  (charter **C-7**, "evidence before mechanism");
- **the thing that is re-injected into every fresh context** — the `restore-evidence`
  SessionStart hook replays `## Observed` + `## Falsified` on startup, on resume, and
  (crucially) after a compaction (charter **C-8**, "durable before deep");
- **the thing a compaction warns you is missing** — the `capture-before-compact` PreCompact
  hook.

The point of the `## Observed` / `## Inferred` split is that conflating them is the failure
this whole mechanism exists to prevent: reading code and finding a plausible mechanism is a
*hypothesis*, and shipping a fix for a hypothesis is how a day gets burned with nothing to
show. See `docs/dev/diagnosis/compose-summary-draft-settle-hole.md` — the worked example, and
the reason this module exists.
"""

from __future__ import annotations

import re
from pathlib import Path

DIAGNOSIS_DIR = "docs/dev/diagnosis"

#: Sections the SessionStart hook replays into a fresh context. `## Inferred` is
#: DELIBERATELY excluded — an unproven mechanism re-injected as context reads like an
#: established fact by the third turn, which is precisely the rot we are guarding against.
REPLAY_SECTIONS = ("Observed", "Falsified")

#: Minimum non-boilerplate characters in `## Observed` for it to count as filled in. Low
#: enough that one honest sentence clears it; high enough that a stray heading does not.
_MIN_EVIDENCE_CHARS = 40

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
#: The TEMPLATE's placeholder lines are wholly-italic (`_like this_`). A dossier that still
#: carries them has not been filled in, so they must not count toward the evidence floor.
_PLACEHOLDER_RE = re.compile(r"^\s*[_*].*[_*]\s*$")


def branch_slug(branch: str) -> str:
    """`fix/compose-summary-draft-settle-hole` -> `compose-summary-draft-settle-hole`.

    Strips the leading `<type>/` so the dossier's filename is the branch's own name. A
    branch with extra slashes keeps them flattened to `-`, so the path is always one file.
    """
    tail = branch.split("/", 1)[1] if "/" in branch else branch
    return tail.replace("/", "-")


def diagnosis_path(repo_root: Path, branch: str) -> Path:
    """Where `branch`'s dossier must live. Deterministic — the block message can name it."""
    return repo_root / DIAGNOSIS_DIR / f"{branch_slug(branch)}.md"


def section(text: str, heading: str) -> str:
    """Return the body under `## <heading>`, up to the next heading of the same level.

    Case-insensitive on the heading, so `## Observed` and `## OBSERVED` both match.
    """
    pattern = re.compile(
        rf"^\s{{0,3}}##\s+{re.escape(heading)}\s*$(?P<body>.*?)(?=^\s{{0,3}}##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group("body").strip() if match else ""


def _substantive(body: str) -> str:
    """Strip the parts of a section that anyone gets for free: comments, sub-headings,
    template placeholders, blank lines. What survives is what the author actually wrote."""
    body = _HTML_COMMENT_RE.sub("", body)
    kept = [
        line
        for line in body.splitlines()
        if line.strip() and not _HEADING_RE.match(line) and not _PLACEHOLDER_RE.match(line)
    ]
    return "\n".join(kept).strip()


def template_text(repo_root: Path) -> str:
    """The diagnosis TEMPLATE's own text; "" if it is missing."""
    try:
        return (repo_root / DIAGNOSIS_DIR / "TEMPLATE.md").read_text(encoding="utf-8")
    except OSError:
        return ""


def has_observed_evidence(text: str, template: str = "") -> bool:
    """True iff `## Observed` carries real, non-placeholder content.

    This is a **ceremony check, not a truth check** — the same bargain
    `check-plan-approved` makes. It cannot tell a real observation from a plausible story,
    and it does not try. Its whole job is to make you write down what you *saw* before you
    are allowed to write a fix, because the act of trying to fill this section in is what
    surfaces the fact that you have not actually looked.

    Passing `template` rejects an untouched copy of `TEMPLATE.md` outright: the template's
    own guidance prose would otherwise clear the character floor on its own, and a gate that
    a `cp` satisfies is theater. (Found by hand-testing this function — it did exactly that.)
    """
    observed = _substantive(section(text, "Observed"))
    if len(observed) < _MIN_EVIDENCE_CHARS:
        return False
    return not (template and observed == _substantive(section(template, "Observed")))


def replay_text(text: str) -> str:
    """The `## Observed` + `## Falsified` sections, rendered for re-injection into context.

    Returns "" when there is nothing worth replaying, so callers can stay silent.
    """
    parts = [
        f"## {name}\n\n{body}"
        for name in REPLAY_SECTIONS
        if (body := section(text, name)) and _substantive(body)
    ]
    return "\n\n".join(parts)
