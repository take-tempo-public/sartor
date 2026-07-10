"""DOC-STATUS trigger-reconciliation gate — PX-50 (F-doc-09) / v1.0.9 CI merge-gate item.

WHY: [`docs/dev/documentation-architecture.md`](../docs/dev/documentation-architecture.md)
defines the ``DOC-STATUS`` flag convention — an invisible HTML-comment marker next to a
front-door claim that will go stale once a named release/sprint ships — plus a "Hook point
(proposed)": *"the freshness gate can grep for DOC-STATUS markers whose trigger sprint has
tagged and fail the build until the line is reconciled."* The 2026-07 efficiency review
(F-doc-09) found the convention defined and markers placed, with **zero enforcement** — a
doc can promise "update this when v1.0.X ships" and nothing ever checks that v1.0.X shipping
actually reconciled the claim. This gate is that hook, built.

THE GRAMMAR (as documented, verbatim from documentation-architecture.md:113):
``<!-- DOC-STATUS(<key>): <claim state> — update when <sprint> lands <PX/finding ids>.
Canonical: <home> -->``

The convention is **free-text prose inside a fielded shell**, not a strict machine grammar:
``<key>`` is a short handle, but ``<claim state>`` / ``<sprint>`` / ``<PX/finding ids>`` are
unstructured English, and real markers in the tree do not all phrase the trigger the same way
(some say "update when X lands", others "owed at vX", "convention-only until X", "PROVISIONAL
— update when: X"). There is no enumerated STATUS field and no single trigger-version token
position. This gate therefore enforces the **minimal subset that IS machine-checkable**, and
deliberately does not attempt full free-text semantic parsing:

WHAT THIS GATE CHECKS:
  1. **Grammar shape.** Every ``<!-- DOC-STATUS(...): ... -->`` instance in the tracked doc
     tree (git ls-files ``*.md``) has a non-empty ``<key>`` matching a slug shape and a
     ``Canonical:`` clause in its body — the two structurally-required fields the convention
     names. A marker missing either is malformed and fails here (never caught by any other
     gate — HTML comments are invisible to readers and to markdown linters).
  2. **Version-trigger reconciliation.** Any ``vX.Y`` / ``vX.Y.Z`` version token immediately
     preceded (within a short character window — the grammar's real idiom always phrases the
     trigger word *before* its version: "owed at vX", "until vX", "update when vX lands") by
     one of a documented set of "still open" trigger phrases (``owed``, ``until``,
     ``unpinned``, ``convention-only``, ``provisional``, ``not yet``, ``update when``) is a
     *phrase-gated* version — the marker's own text frames it as an open promise, not a
     passing mention. If a phrase-gated version is **<= the current ``[project].version`` in
     ``pyproject.toml``** (i.e. that release has already tagged), the marker is unreconciled:
     it promised an update "when vX lands" and vX has landed, but the marker was never
     revisited. This is the literal hook point the architecture doc proposes. The proximity
     pairing (rather than "any stale phrase anywhere in the body") matters because a single
     marker legitimately mixes a resolved past trigger with a distinct, still-open future one
     (e.g. "v1.0.8 landed PX-19; update when v1.1.0 lands PX-2") — a blanket match would
     wrongly flag the resolved half forever.

WHAT THIS GATE DELIBERATELY DOES NOT CHECK (documented limitation, not an oversight):
  - It does not verify the *visible* reader-facing prose next to a marker is itself accurate
    (only the invisible marker's own claim-state text) — that is an editorial/content
    judgment, not a grep-checkable property.
  - It does not cross-reference the named PX/finding ids against their actual ship status in
    ``docs/governance/enforcement.md`` / ``RELEASE_CHECKLIST.md`` — those are free-text prose
    documents with no stable machine-parseable schema; wiring that up would be a second,
    much larger gate (a full doc-fact cross-reference checker), not this one.
  - It does not fail on a marker that mentions a past version *without* a "still open" phrase
    (e.g. a purely historical "shipped in vX.Y" note) — mentioning a past release is not
    itself staleness; only an un-reconciled *open trigger* against a past release is.
  - The "still open" phrase list is a documented, reviewed set grounded in the actual
    phrasing used by the markers in this tree at authoring time (see
    ``_STALE_SIGNAL_PHRASES``), not a claim of exhaustive natural-language coverage — a new
    marker phrased with a novel "still open" word this list doesn't know about would need the
    list extended (mirrors the reviewed-exemption-registry idiom of
    ``tests/test_route_containment_gate.py``, except here the registry is a phrase set, not a
    route allowlist).

SCOPE: markers whose ``<key>`` or body contains an angle-bracket placeholder token (e.g. the
grammar-definition line's own literal ``<key>``/``<sprint>``/``<home>``) are the documented
*template*, not a live instance, and are excluded — with a teeth test proving the exclusion
targets exactly that line and does not silently swallow a real marker.

SKIP: enumeration needs ``git ls-files``; when git is unavailable this is not a git checkout
and the enumeration-based test SKIPs (the parser + phrase-matcher teeth tests still run).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"

# The documented grammar: <!-- DOC-STATUS(<key>): <body> --> (body may not itself contain "-->").
_MARKER_RE = re.compile(r"<!--\s*DOC-STATUS\(([^)]*)\)\s*:\s*(.*?)\s*-->", re.DOTALL)

# A conformant <key> is a short slug (documentation-architecture.md's "<key>" handle).
_KEY_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# The documented grammar says "Canonical: <home>", but real markers also use the plural
# "Canonical homes: <a> + <b>" (a marker citing more than one canonical file) — a real,
# observed deviation from the literal grammar string, tolerated here rather than treated
# as malformed (see module docstring's grammar-ambiguity note).
_CANONICAL_RE = re.compile(r"\bcanonical\b[a-z ]{0,20}:", re.IGNORECASE)

# Version tokens the convention embeds in free text, e.g. "v1.0.8", "v1.1.0-gate".
_VERSION_RE = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?\b")

# The documented "still open" trigger vocabulary — grounded in the real markers in this tree
# at authoring time (see module docstring §"WHAT THIS GATE DELIBERATELY DOES NOT CHECK").
_STALE_SIGNAL_PHRASES = (
    "owed",
    "until",
    "unpinned",
    "convention-only",
    "provisional",
    "not yet",
    "update when",
)
_STALE_SIGNAL_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _STALE_SIGNAL_PHRASES) + r")\b",
    re.IGNORECASE,
)

# A stale-signal phrase only gates the version it actually precedes — the grammar's real
# idiom phrases the trigger word BEFORE the version ("owed at vX", "until vX", "update when
# vX lands"). A marker legitimately mixes a resolved past trigger with a still-open future
# one ("v1.0.8 landed ...; still open — update when v1.1.0 lands ..."); a blanket "any stale
# phrase anywhere in the body" match would wrongly tag the resolved half too. This window
# (chars a phrase may precede its version) makes the pairing proximity-based instead.
_PROXIMITY_WINDOW = 60

# Teeth threshold: the enumeration must find the real marker surface, not a vacuous empty set.
_MIN_LIVE_MARKERS = 1


class DocStatusMarker:
    """One parsed ``<!-- DOC-STATUS(key): body -->`` instance."""

    def __init__(self, path: str, key: str, body: str) -> None:
        self.path = path
        self.key = key
        self.body = body

    @property
    def is_template_placeholder(self) -> bool:
        """True for the grammar-definition line itself (angle-bracket placeholders), not a
        live instance — e.g. key == "<key>" or body containing "<sprint>"/"<home>"."""
        return ("<" in self.key and ">" in self.key) or bool(re.search(r"<\w[\w /]*>", self.body))

    @property
    def has_valid_key(self) -> bool:
        return bool(_KEY_SLUG_RE.match(self.key))

    @property
    def has_canonical_clause(self) -> bool:
        return bool(_CANONICAL_RE.search(self.body))

    @property
    def mentioned_versions(self) -> list[tuple[int, int, int]]:
        out = []
        for m in _VERSION_RE.finditer(self.body):
            major, minor, patch = m.group(1), m.group(2), m.group(3)
            out.append((int(major), int(minor), int(patch or 0)))
        return out

    @property
    def has_stale_signal_phrase(self) -> bool:
        return bool(_STALE_SIGNAL_RE.search(self.body))

    @property
    def phrase_gated_versions(self) -> list[tuple[int, int, int]]:
        """Versions immediately preceded (within ``_PROXIMITY_WINDOW`` chars) by a
        stale-signal phrase — i.e. versions this marker's own text frames as an open
        trigger, as opposed to a version merely mentioned in passing (a historical
        "shipped in vX" note, or a *different*, still-future trigger elsewhere in the
        same marker)."""
        gated = []
        for vm in _VERSION_RE.finditer(self.body):
            window_start = max(0, vm.start() - _PROXIMITY_WINDOW)
            preceding = self.body[window_start : vm.start()]
            if _STALE_SIGNAL_RE.search(preceding):
                major, minor, patch = vm.group(1), vm.group(2), vm.group(3)
                gated.append((int(major), int(minor), int(patch or 0)))
        return gated


def _current_pyproject_version() -> tuple[int, int, int]:
    """Parse ``[project].version`` from pyproject.toml as a (major, minor, patch) tuple."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    raw = data["project"]["version"]
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", raw)
    assert m, f"pyproject.toml [project].version {raw!r} did not parse as a semver-ish string"
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def _tracked_md_or_skip() -> list[str]:
    """All tracked ``*.md`` (repo-relative, forward-slashed); skip if git is unavailable."""
    try:
        out = subprocess.run(  # git ls-files: static, trusted argv
            ["git", "ls-files", "*.md"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(
            "git ls-files unavailable — the DOC-STATUS gate enumerates tracked docs via git "
            "(CI runs in a git checkout, so the gate has teeth there)."
        )
    files = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    if not files:
        pytest.skip("git ls-files returned no .md files — not a populated git checkout.")
    return files


def _all_markers() -> list[DocStatusMarker]:
    markers: list[DocStatusMarker] = []
    for rel in _tracked_md_or_skip():
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")
        for m in _MARKER_RE.finditer(text):
            markers.append(DocStatusMarker(rel, m.group(1).strip(), m.group(2).strip()))
    return markers


def _live_markers() -> list[DocStatusMarker]:
    """Real marker instances only — the grammar-definition template line excluded."""
    return [m for m in _all_markers() if not m.is_template_placeholder]


# --------------------------------------------------------------------------- #
# 1. The parser has teeth — it finds the real marker surface and correctly
#    tells the template line apart from live instances.
# --------------------------------------------------------------------------- #
def test_marker_discovery_has_teeth() -> None:
    """No vacuous pass: at least one live marker must be found (README.md carries the
    documented worked examples — documentation-architecture.md:140), and the
    grammar-definition template line in documentation-architecture.md must be recognized
    as a template, not counted as a live (and inevitably malformed, since it is literally
    ``<key>``/``<home>`` placeholders) instance."""
    live = _live_markers()
    assert len(live) >= _MIN_LIVE_MARKERS, (
        f"found only {len(live)} live DOC-STATUS marker(s) (< {_MIN_LIVE_MARKERS}) — the "
        "marker-discovery regex looks broken, or every marker in the tree was removed."
    )
    all_markers = _all_markers()
    templates = [m for m in all_markers if m.is_template_placeholder]
    assert templates, (
        "expected the grammar-definition template line in documentation-architecture.md "
        "to be discovered and classified as a template placeholder — the exclusion filter "
        "looks broken (or the template line moved/changed shape)."
    )
    assert len(templates) < len(all_markers), (
        "every discovered marker classified as a template placeholder — the live/template "
        "split looks inverted (would make every check below vacuously pass)."
    )


# --------------------------------------------------------------------------- #
# 1b. The version + stale-signal matchers have teeth on synthetic cases.
# --------------------------------------------------------------------------- #
def test_staleness_matcher_has_teeth() -> None:
    """A synthetic marker with a past-due version + an open-trigger phrase must be
    detectable as both version-past-due and phrase-flagged; a future version must not be
    past-due; a past version with no open-trigger phrase (purely historical mention) must
    not be phrase-flagged — the documented deliberate non-goal (see module docstring)."""
    current = (1, 0, 8)

    stale = DocStatusMarker(
        "synthetic.md", "demo", "still owed at v1.0.6 (PX-1). Canonical: docs/x.md"
    )
    assert stale.has_valid_key
    assert stale.has_canonical_clause
    assert (1, 0, 6) in stale.mentioned_versions
    assert min(stale.mentioned_versions) <= current
    assert stale.has_stale_signal_phrase
    assert (1, 0, 6) in stale.phrase_gated_versions

    future = DocStatusMarker(
        "synthetic.md", "demo", "update when v9.9.9 lands PX-1. Canonical: docs/x.md"
    )
    assert all(v > current for v in future.mentioned_versions)

    historical = DocStatusMarker(
        "synthetic.md", "demo", "shipped in v1.0.1, superseded. Canonical: docs/x.md"
    )
    assert (1, 0, 1) in historical.mentioned_versions
    assert not historical.has_stale_signal_phrase
    assert historical.phrase_gated_versions == []

    # Mixed marker: a resolved past trigger sits next to a still-open future one. The
    # blanket "any stale phrase anywhere" signal is present (has_stale_signal_phrase), but
    # proximity pairing must attribute "update when" to v1.1.0 (which follows it), not to
    # v1.0.8 (which precedes it and carries no gating phrase of its own) — else a doc that
    # correctly reconciled its past trigger while leaving a real future one open would be
    # wrongly flagged for the resolved half.
    mixed = DocStatusMarker(
        "synthetic.md",
        "demo",
        "v1.0.8 landed PX-19; still open — update when v1.1.0 lands PX-2. Canonical: docs/x.md",
    )
    assert mixed.has_stale_signal_phrase
    assert (1, 0, 8) not in mixed.phrase_gated_versions
    assert (1, 1, 0) in mixed.phrase_gated_versions

    malformed = DocStatusMarker("synthetic.md", "not a slug!", "no canonical clause here")
    assert not malformed.has_valid_key
    assert not malformed.has_canonical_clause


# --------------------------------------------------------------------------- #
# 2. Every live marker conforms to the documented grammar shape.
# --------------------------------------------------------------------------- #
def test_every_live_marker_matches_the_documented_grammar() -> None:
    """Per documentation-architecture.md:113, a marker is
    ``DOC-STATUS(<key>): ... Canonical: <home>``. A malformed marker is invisible to every
    other gate (it's an HTML comment) and defeats the convention's own purpose."""
    offenders = []
    for m in _live_markers():
        problems = []
        if not m.has_valid_key:
            problems.append(f"key {m.key!r} is not a slug ([a-z][a-z0-9-]*)")
        if not m.has_canonical_clause:
            problems.append("body has no 'Canonical:' clause")
        if problems:
            offenders.append(f"{m.path} DOC-STATUS({m.key}): {'; '.join(problems)}")
    assert not offenders, (
        "Malformed DOC-STATUS marker(s) — fix to match "
        "'<!-- DOC-STATUS(<key>): <claim state> ... Canonical: <home> -->' "
        f"(documentation-architecture.md:113): {offenders}"
    )


# --------------------------------------------------------------------------- #
# 3. No live marker cites an already-tagged version while still reading "open".
# --------------------------------------------------------------------------- #
def test_no_marker_has_an_unreconciled_past_trigger() -> None:
    """The gate's raison d'etre (F-doc-09 / the architecture doc's proposed hook point):
    a marker that says "update when vX lands" / "owed at vX" / "convention-only until vX"
    is unreconciled once vX <= the current pyproject.toml version — that release already
    tagged, so the marker's own trigger fired and the line was never revisited. See the
    module docstring for exactly what phrase vocabulary this checks and what it does not."""
    current = _current_pyproject_version()
    offenders = []
    for m in _live_markers():
        past_due = [v for v in m.phrase_gated_versions if v <= current]
        if past_due:
            offenders.append(
                f"{m.path} DOC-STATUS({m.key}): open-trigger phrase gates already-tagged "
                f"version(s) {['.'.join(map(str, v)) for v in past_due]} (current: "
                f"{'.'.join(map(str, current))})"
            )
    assert not offenders, (
        "DOC-STATUS marker(s) with an unreconciled past-due trigger — the named release "
        "already tagged but the marker still reads as an open promise. Update the marker "
        f"(and, if the visible prose beside it repeats the claim, that too): {offenders}"
    )
