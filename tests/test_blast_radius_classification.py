"""Blast-radius classification audit — keeps `scripts/enforcement/blast_radius.py` honest.

Mirrors `tests/test_wiki_relevance_classification.py` (itself mirroring
`tests/test_egress_allowlist.py`'s `SANCTIONED_EGRESS_FILES`) — the house pattern for a
maintained classification list that cannot silently rot. The check runs in **both**
directions:

- **stale** — a registry entry whose path no longer exists is dead weight that hides the
  next real gap;
- **offenders** — a first-party Python module whose measured import fan-in crosses
  `FAN_IN_THRESHOLD` but appears in neither `GATED` nor `ACKNOWLEDGED_NOT_GATED` is an
  *unreviewed* gap, and fails here so somebody has to make a decision about it.

The offenders half is the load-bearing one. A list that only detects *removed* entries
rots in the safe direction and gives false confidence; this one fails when the codebase
grows a new widely-consumed helper nobody classified.

**The fan-in walk is deliberately here and not in the hook.** `blast_radius.classify()`
runs inside a PreToolUse guard on every single Edit/Write, so it is a dict lookup that
never touches the filesystem. This AST walk over every tracked `.py` file is the
expensive half, and it belongs in the test suite where it runs once.
"""

from __future__ import annotations

import ast
import collections
import subprocess
from pathlib import Path

from scripts.enforcement import blast_radius

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: Directory prefixes excluded from the offenders audit. `tests/` is exempt from the
#: guard itself (writing a test is part of *doing* an enumeration), so a widely-imported
#: test helper is not a gap — gating it would block writes it can never usefully guard.
_OFFENDER_EXEMPT_PREFIXES = ("tests/", "evals/fixtures/")


def _tracked_python_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line]


def _module_index(tracked: list[str]) -> dict[str, str]:
    """Dotted first-party module name -> repo-relative path."""
    index: dict[str, str] = {}
    for rel in tracked:
        dotted = rel[:-3].replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        index[dotted] = rel
    return index


def _non_test_fan_in() -> dict[str, int]:
    """Count, per tracked module, how many NON-test first-party modules import it.

    Non-test importers are the meaningful signal: a shared helper's blast radius is the
    production code that breaks, and the test suite is the safety net rather than the
    radius. Counting tests would rank `tests/ux/seeding.py` above `db/models.py`.
    """
    tracked = _tracked_python_files()
    index = _module_index(tracked)
    fan_in: dict[str, set[str]] = collections.defaultdict(set)

    for rel in tracked:
        if rel.startswith("tests/"):
            continue
        try:
            tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, OSError):
            continue
        targets: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                targets.add(node.module)
                # `from pkg.mod import name` where `name` is itself a module
                targets.update(f"{node.module}.{alias.name}" for alias in node.names)
        for target in targets:
            resolved = index.get(target)
            if resolved and resolved != rel:
                fan_in[resolved].add(rel)

    return {path: len(importers) for path, importers in fan_in.items()}


def test_no_stale_registry_entries() -> None:
    """Every gated path must still exist. A dangling entry hides the next real gap."""
    missing = [path for path in blast_radius.GATED if not (_REPO_ROOT / path).exists()]
    missing += [
        prefix for prefix in blast_radius.GATED_PREFIXES if not (_REPO_ROOT / prefix).is_dir()
    ]
    assert not missing, (
        f"Registry rot — these gated paths no longer exist: {sorted(missing)}. "
        "Remove them from scripts/enforcement/blast_radius.py so the gate stays tight."
    )


def test_no_stale_acknowledgements() -> None:
    """An acknowledged-not-gated module must still exist AND still be widely consumed."""
    fan_in = _non_test_fan_in()
    stale = [
        path
        for path in blast_radius.ACKNOWLEDGED_NOT_GATED
        if not (_REPO_ROOT / path).exists() or fan_in.get(path, 0) < blast_radius.FAN_IN_THRESHOLD
    ]
    assert not stale, (
        f"Acknowledgement rot — these no longer exist or dropped below "
        f"FAN_IN_THRESHOLD={blast_radius.FAN_IN_THRESHOLD}: {sorted(stale)}. "
        "Remove them from ACKNOWLEDGED_NOT_GATED; an acknowledgement for something that "
        "is no longer widely consumed is noise that hides a real one."
    )


def test_widely_consumed_modules_are_all_classified() -> None:
    """The offenders half: crossing the fan-in threshold forces a conscious decision.

    A module many others import is either gated (C-10 applies to it) or explicitly
    acknowledged as deliberately-not-gated with a written reason. What it may NOT be is
    silently unreviewed — that is exactly how a new shared helper acquires 15 consumers
    without anyone ever deciding whether changing it needs an enumeration.
    """
    fan_in = _non_test_fan_in()
    offenders = {
        path: count
        for path, count in fan_in.items()
        if count >= blast_radius.FAN_IN_THRESHOLD
        and not path.startswith(_OFFENDER_EXEMPT_PREFIXES)
        and path not in blast_radius.GATED
        and path not in blast_radius.ACKNOWLEDGED_NOT_GATED
        and not any(path.startswith(prefix) for prefix in blast_radius.GATED_PREFIXES)
    }
    assert not offenders, (
        "Unclassified widely-consumed module(s) — "
        f"{sorted(offenders.items(), key=lambda kv: -kv[1])} "
        f"cross FAN_IN_THRESHOLD={blast_radius.FAN_IN_THRESHOLD} non-test importers but "
        "appear in neither GATED nor ACKNOWLEDGED_NOT_GATED. Decide, in "
        "scripts/enforcement/blast_radius.py: does changing this need a consumer "
        "enumeration first (GATED), or not (ACKNOWLEDGED_NOT_GATED, with the reason)?"
    )


def test_every_acknowledgement_carries_a_reason() -> None:
    """An acknowledgement without a stated reason is an oversight wearing a decision's hat."""
    empty = [
        path for path, reason in blast_radius.ACKNOWLEDGED_NOT_GATED.items() if len(reason) < 30
    ]
    assert not empty, f"ACKNOWLEDGED_NOT_GATED entries missing a real reason: {sorted(empty)}"


def test_every_gated_surface_carries_kind_and_reason() -> None:
    """The block message quotes `why` back at the reader; an empty one wastes the block."""
    bad = [
        surface.path
        for surface in (*blast_radius.GATED.values(), *blast_radius.GATED_PREFIXES.values())
        if surface.kind not in {"schema", "contract", "helper"} or len(surface.why) < 30
    ]
    assert not bad, f"Gated surfaces with a missing/short `why` or an unknown `kind`: {sorted(bad)}"


def test_classify_matches_known_shapes() -> None:
    assert blast_radius.classify("db/models.py") is not None  # exact gated path
    assert blast_radius.classify("db/migrations/versions/0011_x.py") is not None  # prefix
    assert blast_radius.classify("blueprints/applications.py") is None  # ordinary work
    assert blast_radius.classify("analyzer.py") is None  # acknowledged, deliberately ungated
    assert blast_radius.classify("") is None
    # Windows separators arrive from the PreToolUse payload; they must normalize.
    assert blast_radius.classify("db\\models.py") is not None


def test_gated_and_acknowledged_are_disjoint() -> None:
    """A path claiming both buckets is a contradiction the block message cannot explain."""
    overlap = set(blast_radius.GATED) & set(blast_radius.ACKNOWLEDGED_NOT_GATED)
    assert not overlap, f"Paths in BOTH GATED and ACKNOWLEDGED_NOT_GATED: {sorted(overlap)}"
