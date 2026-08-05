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


def substantive(body: str) -> str:
    """Strip the parts of a section that anyone gets for free: comments, sub-headings,
    template placeholders, blank lines. What survives is what the author actually wrote.

    Public because the C-10 consumer-enumeration gate
    (`guards/require_consumer_enumeration.py`) applies the identical "did you actually
    write something, or just `cp` the template" test to its own `## Consumers` section.
    One implementation, so the two gates cannot drift apart on what counts as filled in.
    """
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
    observed = substantive(section(text, "Observed"))
    if len(observed) < _MIN_EVIDENCE_CHARS:
        return False
    return not (template and observed == substantive(section(template, "Observed")))


#: What counts as a citation in `## Observed` (charter **C-12**). Deliberately broad — the
#: point is to reject a section of pure unsourced narrative, not to dictate a format:
#:   - a URL (a CI run, a job log, an issue)
#:   - a long numeric id (GitHub run/job ids are 11 digits here)
#:   - `path/to/file.py:123` — a file:line anchor
#:   - a pytest nodeid (`file.py::test_name`)
#:   - a fenced block (a pasted artifact: a traceback, a log line, a command's output)
#:   - `PR #12` / `#12`
_CITATION_RES = (
    re.compile(r"https?://\S+"),
    re.compile(r"\b\d{9,}\b"),
    re.compile(r"[\w./\\-]+\.\w{1,5}:\d+"),
    re.compile(r"\S+\.\w{1,5}::\w+"),
    re.compile(r"^\s*```", re.MULTILINE),
    re.compile(r"#\d+\b"),
)


def observed_citations(text: str) -> int:
    """How many distinct citation markers `## Observed` carries. 0 == unsourced narrative."""
    observed = substantive(section(text, "Observed"))
    return sum(1 for pattern in _CITATION_RES if pattern.search(observed))


def has_observed_citation(text: str) -> bool:
    """True iff `## Observed` cites at least one artifact (charter **C-12**).

    **This is a floor, not a density check, and the difference is stated rather than
    glossed.** It rejects the specific failure of filling `## Observed` with plausible
    narrative and no artifact behind any of it — which is how a reconstruction becomes a
    premise and then gets cited as fact. It does **not** verify that each individual claim
    in the section is sourced, and one citation does not license twenty unsourced sentences
    around it.

    Two things it deliberately does not do, with reasons:

    - **No per-bullet requirement.** Real dossiers in this repo open `## Observed` with a
      framing sentence and carry evidence in tables and numbered entries; a per-line rule
      would block legitimate writing and train people to pad lines with fake anchors.
    - **No causal-language ban.** Rejecting "because"/"caused by" under `## Observed` (they
      belong under `## Inferred`) was considered and rejected for now: on a *blocking* gate,
      false positives are expensive, and a gate that blocks honest prose trains evasion
      rather than rigor. Recorded here so the next person knows it was a decision, not an
      oversight.

    **It cannot detect a fabricated citation** — a made-up run id passes. The honest claim is
    that an unsourced assertion becomes non-committable, not that a dishonest one becomes
    impossible.
    """
    return observed_citations(text) > 0


def replay_text(text: str) -> str:
    """The `## Observed` + `## Falsified` sections, rendered for re-injection into context.

    Returns "" when there is nothing worth replaying, so callers can stay silent.
    """
    parts = [
        f"## {name}\n\n{body}"
        for name in REPLAY_SECTIONS
        if (body := section(text, name)) and substantive(body)
    ]
    return "\n\n".join(parts)
