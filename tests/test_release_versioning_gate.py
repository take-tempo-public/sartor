"""Charter D-7 — release versioning + release-notes discipline (committed gate).

Two claims are made at a release, both machine-read before any human reads them:

1. **The version number.** `pyproject.toml`'s version and the git tag are the same
   release in two dialects (PEP 440 and semver). If they disagree, pip's resolver
   is the thing that finds out — in users' installs, not in ours.
2. **The release notes.** Every released CHANGELOG section states which publicly
   known vulnerabilities in Sartor's own code it fixes, or says there were none.

The disclosure test below checks that the STATEMENT EXISTS, not that it is true —
no test can verify "we disclosed every CVE we knew about." The point is to make the
claim unavoidable at release-cut time, in front of a human, rather than letting
silence pass for a disclosure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import release_version as rv  # noqa: E402 - path insert must precede this import

CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Charter D-7 was adopted 2026-07-13, for the v1.1.0 public cut onward. Releases
# published before it are left as the historical record — a governance rule that
# retroactively fails already-shipped history is one nobody can trust going forward.
D7_ADOPTED_FROM = "1.1.0"

# A released section heading: "## [1.1.0] — 2026-07-13" (not "## [Unreleased]").
_RELEASED_HEADING_RE = re.compile(r"^## \[(?P<version>\d[^\]]*)\]", re.MULTILINE)

# The disclosure sentence D-7.4 requires. Either form satisfies it: a named CVE/GHSA,
# or an explicit "none" statement. The marker is what makes the claim greppable.
_DISCLOSURE_RE = re.compile(
    r"(?:^|\n)#{3,4}\s*Fixed vulnerabilities|"  # a "### Fixed vulnerabilities" block
    r"No publicly known vulnerabilities|"
    r"no publicly known vulnerabilities",
)


# ---------------------------------------------------------------------------
# D-7.1 / D-7.2 / D-7.3 — the version ladder
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("semver", "pep440"),
    [
        ("1.1.0", "1.1.0"),
        ("1.1.0-alpha.1", "1.1.0a1"),
        ("1.1.0-beta.2", "1.1.0b2"),
        ("1.1.0-beta.11", "1.1.0b11"),
        ("1.1.0-rc.1", "1.1.0rc1"),
        ("2.0.0-rc.10", "2.0.0rc10"),
    ],
)
def test_semver_maps_to_pep440(semver: str, pep440: str) -> None:
    assert rv.semver_to_pep440(semver) == pep440


def test_sanctioned_ladder_orders_identically_in_both_dialects() -> None:
    """The whole reason the ladder is a SUBSET of semver: pip must agree with the tag
    about which release is newer. `beta.11` sorts AFTER `beta.2` (numeric, not
    lexicographic) — the classic trap this pins."""
    from packaging.version import Version

    ladder = [
        "1.1.0-alpha.1",
        "1.1.0-beta.2",
        "1.1.0-beta.11",
        "1.1.0-rc.1",
        "1.1.0",
    ]
    parsed = [Version(rv.semver_to_pep440(v)) for v in ladder]
    assert parsed == sorted(parsed), "PEP 440 must order the ladder the same way semver does"


@pytest.mark.parametrize(
    "bad",
    [
        "1.0.0-alpha.beta",  # semver-legal, but PEP 440 cannot express it -> unorderable by pip
        "1.0.0-rc1",  # missing the dot-separated counter
        "1.0.0-preview.1",  # rung outside alpha/beta/rc
        "1.1",  # not MAJOR.MINOR.PATCH
        "v1.1.0",  # the "v" belongs to the tag, not the version
    ],
)
def test_versions_outside_the_ladder_are_rejected(bad: str) -> None:
    with pytest.raises(rv.VersionPolicyError):
        rv.semver_to_pep440(bad)


@pytest.mark.parametrize("bad", ["1.1.0.dev3", "1.1.0.post1", "1!1.1.0", "1.1", "not-a-version"])
def test_package_versions_outside_the_ladder_are_rejected(bad: str) -> None:
    with pytest.raises(rv.VersionPolicyError):
        rv.check_package_version(bad)


def test_tag_matches_package_across_the_two_dialects() -> None:
    # The bug this exists to prevent: a raw string compare of these two fails.
    assert rv.tag_matches_package("v1.1.0-rc.1", "1.1.0rc1")
    assert rv.tag_matches_package("v1.1.0", "1.1.0")
    assert not rv.tag_matches_package("v1.1.0-rc.2", "1.1.0rc1")
    assert not rv.tag_matches_package("v1.2.0", "1.1.0")


def test_shipped_pyproject_version_satisfies_the_policy() -> None:
    """The live version in `pyproject.toml` — the one a tag will be cut against."""
    rv.check_package_version(rv.package_version())


# ---------------------------------------------------------------------------
# D-7.4 — release notes disclose fixed vulnerabilities
# ---------------------------------------------------------------------------


def _released_sections() -> list[tuple[str, str]]:
    """(version, body) for every released CHANGELOG section, newest first."""
    text = CHANGELOG.read_text(encoding="utf-8")
    matches = list(_RELEASED_HEADING_RE.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((m.group("version"), text[m.start() : end]))
    return sections


def test_changelog_has_released_sections() -> None:
    assert _released_sections(), "no released CHANGELOG sections found — the parser is wrong"


def test_current_release_notes_disclose_fixed_vulnerabilities() -> None:
    """D-7.4: the release being cut must state which publicly known vulnerabilities in
    Sartor's own code it fixes — or say plainly that there were none.

    Scoped to the NEWEST released section on purpose. The rule was adopted 2026-07-13
    (charter D-7) and is not applied retroactively to already-published history: a
    rule that rewrites the past is a rule nobody can trust going forward.
    """
    from packaging.version import Version

    sections = _released_sections()
    if not sections:
        pytest.skip("no released sections yet")
    version, body = sections[0]
    if Version(rv.semver_to_pep440(version)) < Version(D7_ADOPTED_FROM):
        pytest.skip(
            f"[{version}] predates charter D-7 (adopted at {D7_ADOPTED_FROM}); "
            f"the rule is not applied retroactively"
        )
    assert _DISCLOSURE_RE.search(body), (
        f"CHANGELOG section [{version}] carries no fixed-vulnerability statement (charter "
        f"D-7.4). Add a '### Fixed vulnerabilities' block naming each CVE/GHSA in Sartor's "
        f"OWN code that this release fixes — or state 'No publicly known vulnerabilities in "
        f"Sartor's own code were fixed in this release.' Dependency advisories are out of "
        f"scope for this statement; silence is not a disclosure."
    )
