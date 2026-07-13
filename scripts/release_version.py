"""The one place that knows how a Sartor version is spelled (charter D-7).

A release is one fact in two dialects:

    git tag         v1.1.0-rc.1     Semantic Versioning 2.0.0 (semver.org)
    pyproject.toml    1.1.0rc1      PEP 440 (what pip and PyPI actually parse)

Both must agree, and a raw string comparison of the two ALWAYS fails on a
pre-release — which is the kind of bug that only surfaces at publish time, on the
tag, when the release is already public. So the comparison happens here, after
normalization, and `.github/workflows/release.yml` calls this module rather than
re-implementing the rule in shell.

**The sanctioned ladder (D-7.2).** Pre-releases use `alpha` / `beta` / `rc` plus a
numeric counter, and nothing else:

    1.1.0-alpha.1 < 1.1.0-beta.1 < 1.1.0-beta.11 < 1.1.0-rc.1 < 1.1.0

That is a deliberate SUBSET of semver. Semver also permits free-form alphanumeric
identifiers (`1.0.0-alpha.beta`), and PEP 440 cannot express them — so pip could not
order them, and the git tag and the published package would disagree about which
release is newer. The ladder above is the intersection where both systems sort
identically (including `beta.2 < beta.11`, which is numeric, not lexicographic).

Run directly to check the two against each other:

    python -m scripts.release_version --tag v1.1.0-rc.1
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"

# The sanctioned semver spelling: MAJOR.MINOR.PATCH, optionally followed by one of
# the three pre-release rungs and a numeric counter. Anything else is out of policy
# (D-7.2) — including semver-legal forms, deliberately.
SEMVER_RE = re.compile(r"^(?P<release>\d+\.\d+\.\d+)(?:-(?P<rung>alpha|beta|rc)\.(?P<n>\d+))?$")

# PEP 440's own spelling of the same three rungs.
_PEP440_RUNG = {"alpha": "a", "beta": "b", "rc": "rc"}


class VersionPolicyError(ValueError):
    """A version string that violates charter D-7."""


def semver_to_pep440(semver: str) -> str:
    """`1.1.0-rc.1` -> `1.1.0rc1`. Raises on anything outside the D-7 ladder."""
    m = SEMVER_RE.match(semver)
    if not m:
        raise VersionPolicyError(
            f"{semver!r} is not a sanctioned version (charter D-7). Expected "
            f"MAJOR.MINOR.PATCH optionally followed by -alpha.N / -beta.N / -rc.N — "
            f"e.g. 1.1.0, 1.1.0-beta.2, 1.1.0-rc.1."
        )
    release, rung, n = m.group("release"), m.group("rung"), m.group("n")
    return release if rung is None else f"{release}{_PEP440_RUNG[rung]}{n}"


def check_package_version(version: str) -> Version:
    """Validate a `pyproject.toml` version against D-7; return it parsed.

    The version must be valid PEP 440 *and* inside the sanctioned ladder — a
    PEP-440-legal version like `1.1.0.dev3` or `1.1.0.post1` parses fine but has no
    semver tag we would agree to cut, so it is rejected here rather than at the tag.
    """
    try:
        parsed = Version(version)
    except InvalidVersion as exc:
        raise VersionPolicyError(f"{version!r} is not valid PEP 440: {exc}") from exc

    if parsed.dev is not None or parsed.post is not None or parsed.epoch:
        raise VersionPolicyError(
            f"{version!r} uses a PEP 440 form outside the D-7 ladder "
            f"(dev/post/epoch releases are not part of the release policy)."
        )
    if parsed.pre is not None and parsed.pre[0] not in ("a", "b", "rc"):
        raise VersionPolicyError(f"{version!r} has a pre-release rung outside alpha/beta/rc.")
    if len(parsed.release) != 3:  # semver is exactly MAJOR.MINOR.PATCH
        raise VersionPolicyError(f"{version!r} is not MAJOR.MINOR.PATCH (semver requires 3 parts).")
    return parsed


def package_version() -> str:
    """The version declared in `pyproject.toml` — the packaged truth."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def tag_matches_package(tag: str, version: str) -> bool:
    """Do a git tag (`v1.1.0-rc.1`) and a package version (`1.1.0rc1`) name the same
    release? Compared after PEP 440 normalization — never as raw strings."""
    semver = tag[1:] if tag.startswith("v") else tag
    return Version(semver_to_pep440(semver)) == check_package_version(version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="git tag to check against pyproject.toml (e.g. v1.1.0-rc.1)")
    args = parser.parse_args(argv)

    version = package_version()
    try:
        check_package_version(version)
    except VersionPolicyError as exc:
        print(f"::error::pyproject version violates charter D-7: {exc}")
        return 1

    if args.tag:
        try:
            ok = tag_matches_package(args.tag, version)
        except VersionPolicyError as exc:
            print(f"::error::tag violates charter D-7: {exc}")
            return 1
        if not ok:
            print(
                f"::error::git tag {args.tag} does not name the packaged version {version} "
                f"(expected tag v{args.tag.lstrip('v')} <-> {semver_to_pep440(args.tag.lstrip('v'))})"
            )
            return 1
        print(f"tag {args.tag} agrees with pyproject version {version}")
    else:
        print(f"pyproject version {version} satisfies charter D-7")
    return 0


if __name__ == "__main__":
    sys.exit(main())
