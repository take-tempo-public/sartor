"""The committed facts (``evals/golden/golden-v1/facts/``) build the whole matrix, with no model and no money.

What step 3b-ii promises before any paid call: every profession in the manifest has facts that pass the
format's checks, each profession and tier builds a sound profile with one job description, and together they
make the 96 fixtures the owner asked for, in the four groups, across all five settings, with about 5 percent
in the public-sector register. A change to a facts file that breaks any of that fails here, not in a paid run.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pytest

from evals import golden_set as gs

MANIFEST = gs.load_manifest(gs.SUITE_DIR)
PROFESSIONS = sorted(MANIFEST["professions"])


def _facts(profession: str) -> dict[str, Any]:
    facts: dict[str, Any] = json.loads(
        (gs.SUITE_DIR / "facts" / f"{profession}.json").read_text(encoding="utf-8")
    )
    return facts


def _profile(profession: str, level: str) -> dict[str, Any]:
    return gs.build_profile(_facts(profession), gs.ladder_for(MANIFEST, profession, level), level)


def test_every_profession_has_a_facts_file_and_no_file_is_a_stray() -> None:
    on_disk = {p.stem for p in (gs.SUITE_DIR / "facts").glob("*.json")}
    assert on_disk == set(PROFESSIONS)


def test_there_are_24_professions_in_the_four_groups() -> None:
    groups = Counter(row["group"] for row in MANIFEST["professions"].values())
    assert len(PROFESSIONS) == 24
    assert groups == {
        "tech-and-product": 9,
        "business-and-office": 6,
        "health-education-and-community": 4,
        "trades-and-construction": 5,
    }


def test_every_family_the_manifest_defines_is_used() -> None:
    used = {row["family"] for row in MANIFEST["professions"].values()}
    assert used == set(MANIFEST["families"])


@pytest.mark.parametrize("profession", PROFESSIONS)
def test_a_profession_builds_four_sound_cells_with_one_jd_each(profession: str) -> None:
    facts = _facts(profession)
    assert gs.validate_facts(facts) == []
    for level in gs.LEVELS:
        profile = _profile(profession, level)
        assert gs.validate_profile(profile) == [], (profession, level)
        (jd,) = profile["jds"]
        assert [jd["slug"]] == gs.industries_for(facts, level)
        assert profile["cell"] == f"{profession}-{level}"


@pytest.mark.parametrize("profession", PROFESSIONS)
def test_a_cells_credentials_are_asked_dated_and_ordered_like_a_real_career(
    profession: str,
) -> None:
    """The three faults hand-reading found in item 194, as invariants over every committed profession and tier.

    The posting requires the highest credential held; years do not fall as the tier rises; and a mid-or-higher
    credential is dated no later than the earliest role titled for its tier (a Journeyman licence after the
    Journeyman role began is a fault no check of the prose can see). An entry-tier credential has no role of its
    own, so it is dated no later than the earliest role of any title (the career's start).
    """
    facts = _facts(profession)
    tier_of = {c["name"]: gs.LEVELS.index(c["level"]) for c in facts.get("certifications", [])}
    for level in gs.LEVELS:
        profile = _profile(profession, level)
        certs = [
            c for s in profile["sections"] if s["kind"] == "certifications" for c in s["items"]
        ]
        where = f"{profession}-{level}"
        years = [int(c["year"]) for c in certs]
        assert years == sorted(years), (where, "a higher tier is dated before a lower one", certs)
        roles = [r for s in profile["sections"] if s["kind"] == "experience" for r in s["roles"]]
        for cert in certs:
            tier = tier_of[cert["name"]]
            starts = [
                int(r["start"][:4])
                for r in roles
                if tier == 0 or r["title"] == facts["titles"][gs.LEVELS[tier]]
            ]
            if starts:
                assert int(cert["year"]) <= min(starts), (where, cert["name"], cert["year"], starts)
        if certs:
            wanted = f"State {certs[-1]['name']} as a required licence or certification."
            needs = [s["brief"] for sid, s in profile["slots"].items() if sid.endswith(".needs")]
            assert needs and all(wanted in brief for brief in needs), (where, wanted)


@pytest.mark.parametrize("profession", PROFESSIONS)
def test_each_tier_is_posted_where_its_industry_says(profession: str) -> None:
    facts = _facts(profession)
    by_tier = {i["level"]: i for i in facts["industries"]}
    for level in gs.LEVELS:
        (jd,) = _profile(profession, level)["jds"]
        assert jd["setting"] == by_tier[level]["setting"]
        assert by_tier[level]["location"] in jd["header_lines"][1]


def test_the_matrix_is_96_fixtures_with_distinct_names() -> None:
    names = [
        gs.fixture_name(profile["cell"], jd["slug"])
        for profession in PROFESSIONS
        for level in gs.LEVELS
        for profile in [_profile(profession, level)]
        for jd in profile["jds"]
    ]
    assert len(names) == 96
    assert len(set(names)) == 96


def test_about_five_percent_of_fixtures_use_the_public_sector_register() -> None:
    settings = Counter(
        jd["setting"]
        for profession in PROFESSIONS
        for level in gs.LEVELS
        for jd in _profile(profession, level)["jds"]
    )
    assert sum(settings.values()) == 96
    assert set(settings) == set(gs.SETTINGS), "every setting appears"
    assert settings["public-sector"] == 5  # 5.2 percent: the owner's "about 5%" of 96


def test_no_trap_matches_the_skills_a_cell_lists() -> None:
    """A trap is a regex against text the model writes; it must not match a skill the cell does list."""
    import re

    for profession in PROFESSIONS:
        for level in gs.LEVELS:
            profile = _profile(profession, level)
            held = [s["name"] for s in profile["skills"]]
            for trap in profile["expected"]["forbidden_inventions"]:
                hits = [name for name in held if re.search(trap, name)]
                assert not hits, (profession, level, trap, hits)
