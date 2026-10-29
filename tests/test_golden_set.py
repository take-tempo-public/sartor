"""The golden set's format (`evals/golden_set.py`): determinism, the renderer, the checks, the converter.

Everything here builds its cells in ``tmp_path``. Nothing reads or writes the committed suite except
`TestCommittedSuite`, which runs the suite checker over it. LLM-free: the prose in these tests is
made by `_prose`, which writes the shortest text that meets each slot's rules.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any, ClassVar

import pytest

from db.build_context import build_context_set_from_db
from evals import golden_set as gs
from evals.seed_import import seeded_session
from scripts.export_corpus_seed import export_seed
from tests._controls import control

REPO_ROOT = Path(__file__).resolve().parent.parent
PERSONAS = REPO_ROOT / "evals" / "fixtures" / "synthetic"

FACTS: dict[str, Any] = {
    "profession": "demo-ops",
    "display": "operations",
    "titles": {
        "entry": "Junior Operator",
        "mid": "Operator",
        "senior": "Senior Operator",
        "lead": "Lead Operator",
    },
    "skills": [
        {"name": name, "category": "tool"}
        for name in (
            "Alphaflow",
            "Betamesh",
            "Gammaqueue",
            "Deltaprobe",
            "Epsilonlog",
            "Zetavault",
            "Etagrid",
            "Thetaline",
            "Iotabus",
            "Kappatrace",
            "Lambdarun",
            "Mugate",
        )
    ],
    "work_themes": [
        "incident handling",
        "capacity planning",
        "release coordination",
        "runbook upkeep",
        "cost review",
        "vendor management",
    ],
    "education": {"degree": "B.S.", "field": "Operations"},
    "settings": ["startup", "enterprise"],
    "industries": [
        {
            "slug": "hospital",
            "company": "Northwind Health",
            "phrase": "a regional hospital network",
            "setting": "health-nonprofit",
            "location": "On site, Tampa, FL",
        },
        {
            "slug": "bank",
            "company": "Cedar Bank",
            "phrase": "a mid-size retail bank",
            "setting": "enterprise",
            "location": "Hybrid, Charlotte, NC",
        },
    ],
}


def _ladder(level: str) -> dict[str, Any]:
    return {
        "entry": {"years": [0, 2], "roles": 1, "bullets_per_role": 3},
        "mid": {"years": [3, 5], "roles": 2, "bullets_per_role": 3},
        "senior": {"years": [6, 10], "roles": 3, "bullets_per_role": 3},
        "lead": {"years": [10, 16], "roles": 3, "bullets_per_role": 4},
    }[level] | {
        "intro_variants": 2,
        "summary_variants": 2,
        "skill_count": 8,
        "scope": "owning the service end to end",
        "rule_source": "authored",
        "label": level,
    }


def _manifest(status: str = "draft", waivers: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": gs.MANIFEST_SCHEMA,
        "suite": gs.SUITE,
        "version": 1,
        "status": status,
        "families": {"demo": {"levels": {level: _ladder(level) for level in gs.LEVELS}}},
        "professions": {"demo-ops": {"display": "operations", "family": "demo"}},
        "author": {"model": "stub", "prompt_versions": {"t1": "sha256:prompt"}},
        "pilot_waivers": waivers or [],
    }


def _put(path: Path, text: str) -> None:
    """Write ``text`` with LF on every platform, as the module under test does."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _text_for(slot: dict[str, Any]) -> str:
    words = [str(w) for w in slot["must_include"]]
    while len(" ".join(words).split()) < slot["min_words"]:
        words.append("steady")
    return " ".join(words)


def _prose(profile: dict[str, Any], *, kind: str = "generated") -> dict[str, Any]:
    provenance: dict[str, Any] = {"kind": kind}
    if kind == "generated":
        provenance |= {
            "model": "stub",
            "prompt_version": "t1",
            "prompt_sha256": "sha256:prompt",
            "profile_sha256": gs.sha256_text(gs.canonical_json(profile)),
        }
    return {
        "schema": gs.SCHEMA,
        "cell": profile["cell"],
        "provenance": provenance,
        "slots": {sid: _text_for(slot) for sid, slot in profile["slots"].items()},
    }


def _built(level: str = "mid") -> tuple[dict[str, Any], dict[str, Any]]:
    profile = gs.build_profile(FACTS, _ladder(level), level)
    return profile, _prose(profile)


def _suite(tmp_path: Path, *levels: str, status: str = "draft") -> Path:
    root = tmp_path / "golden-v1"
    for level in levels or ("mid",):
        profile, prose = _built(level)
        gs.write_cell(root, profile, prose)
    (root / "facts").mkdir(parents=True, exist_ok=True)
    _put(root / "facts" / "demo-ops.json", gs.canonical_json(FACTS))
    gs.write_manifest(root, _manifest(status))
    return root


# ---------------------------------------------------------------------------------------------------
# Dates, hashes and the builder's determinism
# ---------------------------------------------------------------------------------------------------


class TestPrimitives:
    def test_month_label_round_trips(self) -> None:
        assert gs.month_label("2024-07") == "July 2024"
        assert gs.month_label(None) == "present"
        assert gs.month_iso("July 2024") == "2024-07"
        assert gs.month_iso("present") is None

    @pytest.mark.parametrize("bad", ["2024-13", "2024-7", "July", ""])
    def test_a_bad_month_is_refused(self, bad: str) -> None:
        with pytest.raises(ValueError):
            gs.month_label(bad)

    def test_the_cell_seed_is_pinned(self) -> None:
        # Every pseudo-random choice in a cell derives from this. A change flips every committed
        # cell, so it is a version bump (golden-v2), never an edit: this test makes that loud.
        assert gs.cell_seed_for("demo-ops", "mid") == 2143629550
        assert gs.cell_seed_for("sre-ops", "senior") == 827368465

    def test_canonical_json_is_lf_sorted_and_unicode(self) -> None:
        text = gs.canonical_json({"b": "—", "a": 1})
        assert text == '{\n  "a": 1,\n  "b": "—"\n}\n'
        assert "\r" not in text


class TestBuilder:
    def test_the_same_inputs_write_the_same_bytes(self) -> None:
        one = gs.build_profile(FACTS, _ladder("senior"), "senior")
        two = gs.build_profile(copy.deepcopy(FACTS), _ladder("senior"), "senior")
        assert gs.canonical_json(one) == gs.canonical_json(two)

    def test_every_built_profile_is_sound(self) -> None:
        for level in gs.LEVELS:
            profile = gs.build_profile(FACTS, _ladder(level), level)
            assert gs.validate_profile(profile) == [], level

    def test_levels_differ_in_shape(self) -> None:
        sizes = {
            level: len(gs.build_profile(FACTS, _ladder(level), level)["slots"])
            for level in gs.LEVELS
        }
        assert sizes["entry"] < sizes["mid"] < sizes["senior"] < sizes["lead"]

    def test_a_built_cell_holds_what_every_call_kind_needs(self) -> None:
        profile, _ = _built("mid")
        assert gs.failing_predicates(profile) == []

    def test_the_candidate_is_synthetic(self) -> None:
        for level in gs.LEVELS:
            cand = gs.build_profile(FACTS, _ladder(level), level)["candidate"]
            assert cand["email"].endswith("@example.com")
            assert re.fullmatch(r"\(555\) 010-\d{4}", cand["phone"])
            assert cand["linkedin"].startswith("linkedin.com/in/example-")

    def test_dates_run_back_from_the_fixed_month(self) -> None:
        roles = gs.build_profile(FACTS, _ladder("senior"), "senior")["sections"][1]["roles"]
        assert roles[0]["end"] is None
        assert roles[0]["start"] < gs.ASOF
        assert roles[1]["end"] == roles[0]["start"]
        assert roles[2]["end"] == roles[1]["start"]

    def test_the_jd_asks_for_skills_the_candidate_lacks_and_the_traps_forbid_claiming_them(
        self,
    ) -> None:
        profile, _ = _built("mid")
        have = {s["name"] for s in profile["skills"]}
        traps = profile["expected"]["forbidden_inventions"]
        missing = [s["name"] for s in FACTS["skills"] if s["name"] not in have]
        assert missing and any("(?i)" + re.escape(m) in traps for m in missing)
        needs = profile["slots"]["jd.hospital.needs"]["must_include"]
        assert set(needs) & set(missing), "the JD should name a skill the candidate lacks"


def _iso_months(iso: str) -> int:
    year, month = iso.split("-")
    return int(year) * 12 + int(month)


class TestTenure:
    """Level is the axis the golden set measures, so a cell's career length sits inside its ladder's years."""

    @staticmethod
    def _career_months(profile: dict[str, Any]) -> int:
        roles = next(s for s in profile["sections"] if s["kind"] == "experience")["roles"]
        return _iso_months(gs.ASOF) - _iso_months(roles[-1]["start"])

    @pytest.mark.parametrize("level", gs.LEVELS)
    def test_the_career_length_sits_inside_the_ladder_years(self, level: str) -> None:
        low, high = _ladder(level)["years"]
        outside = []
        for n in range(40):
            facts = FACTS | {"profession": f"demo-{n}"}
            months = self._career_months(gs.build_profile(facts, _ladder(level), level))
            if not low * 12 <= months <= high * 12:
                outside.append((facts["profession"], months))
        assert outside == [], f"{level}: ladder {low}-{high} years, outside: {outside[:5]}"

    @pytest.mark.parametrize("level", gs.LEVELS)
    def test_every_role_is_at_least_the_minimum_and_the_roles_sum_to_the_career(
        self, level: str
    ) -> None:
        ladder = _ladder(level)
        for seed in range(60):
            tenures = gs._tenures(seed, ladder)
            assert len(tenures) == ladder["roles"]
            assert min(tenures) >= gs.MIN_ROLE_MONTHS, (seed, tenures)
            low, high = ladder["years"]
            assert max(low * 12, ladder["roles"] * gs.MIN_ROLE_MONTHS) <= sum(tenures) <= high * 12

    def test_the_career_length_is_not_one_value(self) -> None:
        # A window that collapsed to a point would pass the bounds test and hide the same defect.
        spans = {sum(gs._tenures(seed, _ladder("senior"))) for seed in range(60)}
        assert len(spans) > 10

    @pytest.mark.parametrize("level", gs.LEVELS)
    def test_the_stated_years_match_the_career_length(self, level: str) -> None:
        # The summary brief and the JD requirement both quote "about N years"; N must be the career length.
        profile = gs.build_profile(FACTS, _ladder(level), level)
        years = max(1, round(self._career_months(profile) / 12))
        assert profile["slots"]["summary.1"]["allowed_numbers"] == [str(years)]


class TestFacts:
    """A profession's facts file is checked before a cell is built from it."""

    def test_sound_facts_have_no_problems(self) -> None:
        assert gs.validate_facts(FACTS) == []

    @pytest.mark.parametrize(
        "key", ["titles", "skills", "work_themes", "education", "industries", "settings"]
    )
    def test_a_missing_key_is_named(self, key: str) -> None:
        facts = {k: v for k, v in FACTS.items() if k != key}
        assert gs.validate_facts(facts) == [f"facts are missing {key!r}"]

    def test_a_missing_title_tier_is_found(self) -> None:
        facts = copy.deepcopy(FACTS)
        del facts["titles"]["lead"]
        assert gs.validate_facts(facts) == ["titles has no 'lead'"]

    def test_an_unknown_career_setting_is_found(self) -> None:
        assert any(
            "settings must be" in p for p in gs.validate_facts(FACTS | {"settings": ["moon"]})
        )
        assert any("settings must be" in p for p in gs.validate_facts(FACTS | {"settings": []}))

    @pytest.mark.parametrize("key", ["setting", "location", "company", "phrase"])
    def test_an_industry_needs_its_setting_location_company_and_phrase(self, key: str) -> None:
        facts = copy.deepcopy(FACTS)
        facts["industries"][0][key] = "" if key != "setting" else "moon"
        assert any(f"industry 'hospital': {key}" in p for p in gs.validate_facts(facts))

    @pytest.mark.parametrize(
        ("name", "needle"),
        [
            ("Python3", "a digit in a name"),
            ("Go", "under three characters"),
        ],
    )
    def test_a_skill_name_the_checks_cannot_hold_is_found(self, name: str, needle: str) -> None:
        facts = copy.deepcopy(FACTS)
        facts["skills"][0]["name"] = name
        assert any(f"skill {name!r}" in p and needle in p for p in gs.validate_facts(facts))

    def test_a_skill_name_inside_another_is_found(self) -> None:
        # A trap or a required fact is a substring test, so "Git" would match "GitHub" and the reverse.
        facts = copy.deepcopy(FACTS)
        facts["skills"][0]["name"] = "Git"
        facts["skills"][1]["name"] = "GitHub"
        assert any("'Git' is inside skill 'GitHub'" in p for p in gs.validate_facts(facts))
        assert not any("'GitHub' is inside" in p for p in gs.validate_facts(facts))

    def test_the_overlap_check_ignores_case(self) -> None:
        facts = copy.deepcopy(FACTS)
        facts["skills"][0]["name"] = "SQL"
        facts["skills"][1]["name"] = "Postgresql"
        assert any("'SQL' is inside skill 'Postgresql'" in p for p in gs.validate_facts(facts))

    def test_a_skill_inside_a_certification_name_is_found(self) -> None:
        facts = copy.deepcopy(CERT_FACTS)
        facts["skills"][0]["name"] = "Journeyman"
        assert any(
            "skill 'Journeyman'" in p and "certification" in p for p in gs.validate_facts(facts)
        )

    def test_two_industries_cannot_share_a_slug(self) -> None:
        facts = copy.deepcopy(FACTS)
        facts["industries"][1]["slug"] = "hospital"
        assert any("distinct slug" in p for p in gs.validate_facts(facts))

    def test_the_builder_refuses_bad_facts_with_every_reason(self) -> None:
        facts = copy.deepcopy(FACTS)
        facts["industries"][0]["location"] = ""
        facts["settings"] = ["moon"]
        with pytest.raises(ValueError, match=r"settings must be.*location is empty"):
            gs.build_profile(facts, _ladder("mid"), "mid")


TIERED_FACTS: dict[str, Any] = FACTS | {
    "industries": [
        {**FACTS["industries"][0], "level": "entry"},
        {**FACTS["industries"][1], "level": "mid"},
        {
            "slug": "county",
            "company": "Fairmont County Office",
            "phrase": "a county government office",
            "setting": "public-sector",
            "location": "On site, Fairmont, OH",
            "level": "senior",
        },
        {
            "slug": "shop",
            "company": "Redfern Family Trades",
            "phrase": "a family-owned shop",
            "setting": "small-business",
            "location": "On site, Dayton, OH",
            "level": "lead",
        },
    ]
}


class TestOneJdPerTier:
    """One JD per cell (the 96-fixture ceiling): a profession names the industry each tier is posted in."""

    def test_tiered_facts_are_sound(self) -> None:
        assert gs.validate_facts(TIERED_FACTS) == []

    @pytest.mark.parametrize(
        ("level", "slug"),
        [("entry", "hospital"), ("mid", "bank"), ("senior", "county"), ("lead", "shop")],
    )
    def test_the_tier_names_its_industry(self, level: str, slug: str) -> None:
        assert gs.industries_for(TIERED_FACTS, level) == [slug]

    def test_facts_without_tiers_keep_the_default(self) -> None:
        assert gs.industries_for(FACTS, "mid") is None
        assert [jd["slug"] for jd in gs.build_profile(FACTS, _ladder("mid"), "mid")["jds"]] == [
            "hospital",
            "bank",
        ]

    @pytest.mark.parametrize("level", gs.LEVELS)
    def test_a_tiered_profession_builds_one_jd_in_that_industry(self, level: str) -> None:
        profile = gs.build_profile(TIERED_FACTS, _ladder(level), level)
        (jd,) = profile["jds"]
        assert [jd["slug"]] == gs.industries_for(TIERED_FACTS, level)
        assert sorted(s for s in profile["slots"] if s.startswith("jd.")) == [
            f"jd.{jd['slug']}.about",
            f"jd.{jd['slug']}.duties",
            f"jd.{jd['slug']}.needs",
        ]
        assert gs.validate_profile(profile) == []
        assert jd["setting"] == next(
            i["setting"] for i in TIERED_FACTS["industries"] if i["slug"] == jd["slug"]
        )

    def test_an_explicit_choice_still_wins(self) -> None:
        profile = gs.build_profile(TIERED_FACTS, _ladder("mid"), "mid", ["county", "shop"])
        assert [jd["slug"] for jd in profile["jds"]] == ["county", "shop"]

    def test_a_missing_tier_is_found(self) -> None:
        facts = copy.deepcopy(TIERED_FACTS)
        del facts["industries"][3]
        assert any("each tier exactly once" in p and "lead" in p for p in gs.validate_facts(facts))

    def test_a_repeated_tier_is_found(self) -> None:
        facts = copy.deepcopy(TIERED_FACTS)
        facts["industries"][3]["level"] = "senior"
        problems = gs.validate_facts(facts)
        assert any("each tier exactly once" in p and "senior" in p for p in problems)

    def test_an_unknown_tier_is_found(self) -> None:
        facts = copy.deepcopy(TIERED_FACTS)
        facts["industries"][0]["level"] = "principal"
        assert any("industry 'hospital': level" in p for p in gs.validate_facts(facts))

    def test_an_industry_without_a_tier_among_tiered_ones_is_found(self) -> None:
        facts = copy.deepcopy(TIERED_FACTS)
        del facts["industries"][0]["level"]
        assert any("industry 'hospital': level" in p for p in gs.validate_facts(facts))


class TestTrapsIgnoreCase:
    """The author may write a skill in lower case mid-sentence, so a trap against a skill the cell lacks must too."""

    _SLOT: ClassVar[dict[str, Any]] = {
        "kind": "bullet",
        "min_words": 1,
        "max_words": 40,
        "allowed_numbers": [],
        "must_include": [],
    }

    def test_a_skill_the_cell_lacks_is_caught_in_any_capitalisation(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("mid"), "mid")
        listed = {s["name"] for s in profile["skills"]}
        absent = next(s["name"] for s in FACTS["skills"] if s["name"] not in listed)
        traps = profile["expected"]["forbidden_inventions"]
        for spelling in (absent, absent.lower(), absent.upper()):
            found = gs.check_slot_text("r1.b1", self._SLOT, f"Worked with {spelling} daily.", traps)
            assert any("invention trap" in p for p in found), spelling

    def test_a_certification_the_cell_lacks_is_caught_in_any_capitalisation(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("entry"), "entry")
        traps = profile["expected"]["forbidden_inventions"]
        for spelling in ("Master Licence", "master licence", "MASTER LICENCE"):
            found = gs.check_slot_text("r1.b1", self._SLOT, f"Holds a {spelling} now.", traps)
            assert any("invention trap" in p for p in found), spelling

    def test_a_required_skill_may_be_written_in_lower_case(self) -> None:
        slot = self._SLOT | {"must_include": ["Month-end close"]}
        text = "Led the month-end close for the whole team every period."
        assert gs.check_slot_text("r1.b1", slot, text, []) == []

    def test_the_generic_traps_are_unchanged(self) -> None:
        # "PhD" is a claim only in that spelling; a case-insensitive "phd" would match inside other words.
        assert gs.GENERIC_TRAPS == (
            "PhD",
            "Master'?s? (degree|in)",
            "managed [0-9]+",
            "10\\+ years",
        )


LEADERSHIP = "directing the weekly crew huddle"
LEADER_FACTS: dict[str, Any] = FACTS | {"leadership_themes": [LEADERSHIP]}


def _briefs(profile: dict[str, Any]) -> dict[str, str]:
    return {sid: slot["brief"] for sid, slot in profile["slots"].items()}


class TestLeadershipThemes:
    """An apprentice does not direct a crew: some work only reads true from the senior tiers up."""

    def test_the_theme_is_never_given_to_an_entry_or_mid_cell(self) -> None:
        for level in ("entry", "mid"):
            briefs = _briefs(gs.build_profile(LEADER_FACTS, _ladder(level), level))
            assert not [sid for sid, brief in briefs.items() if LEADERSHIP in brief], level

    def test_a_lower_role_of_a_lead_cell_does_not_get_it_either(self) -> None:
        profile = gs.build_profile(LEADER_FACTS, _ladder("lead"), "lead")
        roles = profile["sections"][1]["roles"]  # newest first: lead, senior, mid
        used = [
            any(LEADERSHIP in profile["slots"][sid]["brief"] for sid in role["bullet_slots"])
            for role in roles
        ]
        assert used[0] or used[1]
        assert used[2] is False, "the mid-tier role must not direct a crew"

    def test_a_lead_cell_does_use_it(self) -> None:
        briefs = _briefs(gs.build_profile(LEADER_FACTS, _ladder("lead"), "lead"))
        assert [sid for sid, brief in briefs.items() if LEADERSHIP in brief]

    @pytest.mark.parametrize("bad", [[], [""], "leading", ["a", "a"]])
    def test_bad_leadership_themes_are_found(self, bad: Any) -> None:
        assert any(
            "leadership_themes" in p for p in gs.validate_facts(FACTS | {"leadership_themes": bad})
        )


class TestEvenCoverage:
    """Skills and themes are used evenly, not drawn with replacement (one skill in 6 of 12 bullets)."""

    def _bullets(self, level: str) -> list[dict[str, Any]]:
        profile = gs.build_profile(FACTS, _ladder(level), level)
        return [
            profile["slots"][sid]
            for sec in profile["sections"]
            if sec["kind"] == "experience"
            for role in sec["roles"]
            for sid in role["bullet_slots"]
        ]

    def test_no_skill_is_used_twice_before_all_are_used_once(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("lead"), "lead")
        listed = [s["name"] for s in profile["skills"]]
        used = [
            next(s for s in listed if f"using {s}." in slot["brief"])
            for slot in self._bullets("lead")
        ]
        assert (
            len(used) == 12 and len(listed) == 8
        )  # three roles of four bullets, eight skills listed
        assert set(used[: len(listed)]) == set(listed), used
        assert max(used.count(s) for s in listed) == 2  # four skills twice, four once

    def test_no_theme_is_used_twice_before_all_are_used_once(self) -> None:
        pool = FACTS["work_themes"]
        briefs = [slot["brief"] for slot in self._bullets("lead")]
        used = [next(t for t in pool if f": {t}," in b) for b in briefs]
        assert set(used[: len(pool)]) == set(pool), used
        assert max(used.count(t) for t in pool) == 2  # 12 bullets over 6 themes: each exactly twice

    def test_the_two_intro_variants_of_a_role_differ(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("senior"), "senior")
        for role in profile["sections"][1]["roles"]:
            one, two = (profile["slots"][sid]["brief"] for sid in role["intro_slots"])
            theme = lambda brief: brief.rsplit("about ", 1)[1]  # noqa: E731
            assert theme(one) != theme(two)

    def test_it_is_still_a_pure_function_of_the_facts(self) -> None:
        one = gs.build_profile(FACTS, _ladder("senior"), "senior")
        two = gs.build_profile(copy.deepcopy(FACTS), _ladder("senior"), "senior")
        assert gs.canonical_json(one) == gs.canonical_json(two)


class TestACellIsTheFunctionOfItsFacts:
    """A generated cell is rebuilt from its facts when the suite is checked, so editing the facts afterwards,
    which would leave the cell describing a profession the facts no longer say, is found."""

    def _suite_with_facts(self, tmp_path: Path) -> Path:
        return _suite(tmp_path)

    def test_a_cell_built_from_the_facts_passes(self, tmp_path: Path) -> None:
        assert gs.check_suite(self._suite_with_facts(tmp_path)) == []

    def test_changing_the_facts_after_the_cell_was_written_is_found(self, tmp_path: Path) -> None:
        root = self._suite_with_facts(tmp_path)
        changed = copy.deepcopy(FACTS)
        changed["work_themes"] = [*changed["work_themes"], "a theme added afterwards"]
        _put(root / "facts" / "demo-ops.json", gs.canonical_json(changed))
        gs.write_manifest(root, gs.load_manifest(root))
        assert any(
            "demo-ops-mid" in p and "differs from a fresh build" in p for p in gs.check_suite(root)
        )

    def test_a_generated_cell_whose_facts_are_gone_is_found(self, tmp_path: Path) -> None:
        root = self._suite_with_facts(tmp_path)
        (root / "facts" / "demo-ops.json").unlink()
        gs.write_manifest(root, gs.load_manifest(root))
        assert any("demo-ops-mid" in p and "facts/demo-ops.json" in p for p in gs.check_suite(root))

    def test_a_converted_cell_is_not_rebuilt(self, tmp_path: Path) -> None:
        profile, _ = _built()
        converted = _prose(profile, kind="converted")
        root = tmp_path / "golden-v1"
        gs.write_cell(root, profile, converted)
        (root / "facts").mkdir(parents=True)
        gs.write_manifest(root, _manifest())
        assert not any("fresh build" in p for p in gs.check_suite(root))


class TestSetting:
    """Where a job sits sets its employers, its JD register and its place (not a tech startup by default)."""

    def test_every_setting_has_a_voice_and_enough_employers(self) -> None:
        assert set(gs._EMPLOYERS_BY_SETTING) == set(gs.SETTINGS) == set(gs._JD_VOICE)
        longest_career = max(_ladder(level)["roles"] for level in gs.LEVELS)
        for setting, pool in gs._EMPLOYERS_BY_SETTING.items():
            assert len(set(pool)) >= longest_career, setting
        for voice in gs._JD_VOICE.values():
            assert set(voice) == {"about", "duties", "needs", "register"}

    def test_the_jd_header_names_the_industrys_place_and_never_a_default(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("mid"), "mid")
        headers = {jd["slug"]: jd["header_lines"][1] for jd in profile["jds"]}
        assert headers == {
            "hospital": "Northwind Health — On site, Tampa, FL",
            "bank": "Cedar Bank — Hybrid, Charlotte, NC",
        }
        assert all("Remote (US)" not in h for h in headers.values())

    def test_each_jd_is_briefed_in_its_settings_headings_and_register(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("mid"), "mid")
        hospital = gs._JD_VOICE["health-nonprofit"]
        bank = gs._JD_VOICE["enterprise"]
        assert f"'{hospital['about']}' paragraph" in profile["slots"]["jd.hospital.about"]["brief"]
        assert hospital["register"] in profile["slots"]["jd.hospital.about"]["brief"]
        assert f"'{hospital['needs']}' heading" in profile["slots"]["jd.hospital.needs"]["brief"]
        assert f"'{bank['duties']}' heading" in profile["slots"]["jd.bank.duties"]["brief"]
        assert {jd["slug"]: jd["setting"] for jd in profile["jds"]} == {
            "hospital": "health-nonprofit",
            "bank": "enterprise",
        }

    @pytest.mark.parametrize("setting", gs.SETTINGS)
    def test_a_career_draws_its_employers_from_its_settings(self, setting: str) -> None:
        facts = FACTS | {"settings": [setting]}
        for level in gs.LEVELS:
            roles = gs.build_profile(facts, _ladder(level), level)["sections"][1]["roles"]
            companies = [r["company"] for r in roles]
            assert set(companies) <= set(gs._EMPLOYERS_BY_SETTING[setting]), (level, companies)
            assert len(set(companies)) == len(companies), (level, companies)

    def test_a_profession_may_name_its_own_employers(self) -> None:
        # A teacher in the public-sector pool could work for a transit authority; the facts can say who hires.
        schools = [
            "Willowbrook Elementary",
            "Cedar Grove Academy",
            "Hillcrest School",
            "Maple Street School",
        ]
        facts = FACTS | {"settings": ["public-sector"], "employers": schools}
        assert gs.validate_facts(facts) == []
        for level in gs.LEVELS:
            roles = gs.build_profile(facts, _ladder(level), level)["sections"][1]["roles"]
            companies = [r["company"] for r in roles]
            assert set(companies) <= set(schools), (level, companies)
            assert len(set(companies)) == len(companies), (level, companies)

    def test_named_employers_change_nothing_for_facts_that_do_not_name_any(self) -> None:
        assert gs.canonical_json(
            gs.build_profile(FACTS, _ladder("senior"), "senior")
        ) == gs.canonical_json(gs.build_profile(copy.deepcopy(FACTS), _ladder("senior"), "senior"))

    @pytest.mark.parametrize(
        "employers",
        [
            [],
            ["Only One", "Only Two"],
            ["A School", "A School", "Another School"],
            ["A", "", "B"],
            "School",
        ],
    )
    def test_bad_employers_are_found(self, employers: Any) -> None:
        facts = FACTS | {"employers": employers}
        assert any("employers" in p for p in gs.validate_facts(facts))

    def test_a_mixed_career_uses_more_than_one_setting_across_cells(self) -> None:
        seen: set[str] = set()
        for n in range(30):
            facts = FACTS | {"profession": f"demo-{n}", "settings": ["startup", "small-business"]}
            roles = gs.build_profile(facts, _ladder("senior"), "senior")["sections"][1]["roles"]
            for role in roles:
                for setting in facts["settings"]:
                    if role["company"] in gs._EMPLOYERS_BY_SETTING[setting]:
                        seen.add(setting)
        assert seen == {"startup", "small-business"}


FACTS_AP: dict[str, Any] = FACTS | {"profession": "demo-ap", "display": "administration"}


def _common_term(resume_text: str, jd_text: str) -> str:
    """A skill (or the filler word) both texts mention, so a pair can name a truly transferable term."""
    for term in [s["name"] for s in FACTS["skills"]] + ["steady"]:
        if gs._mentions(resume_text, term) and gs._mentions(jd_text, term):
            return term
    raise AssertionError("the two texts share no term")


def _pair_suite(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Three cells (demo-ops mid and senior, demo-ap mid) and a manifest listing an advance and a change pair."""
    root = tmp_path / "golden-v1"
    for facts, level in ((FACTS, "mid"), (FACTS, "senior"), (FACTS_AP, "mid")):
        profile = gs.build_profile(facts, _ladder(level), level)
        gs.write_cell(root, profile, _prose(profile))
    manifest = _manifest()
    manifest["professions"]["demo-ap"] = {"display": "administration", "family": "demo"}
    for facts in (
        FACTS,
        FACTS_AP,
    ):  # a generated cell is rebuilt from its facts when the suite is checked
        (root / "facts").mkdir(parents=True, exist_ok=True)
        _put(root / "facts" / f"{facts['profession']}.json", gs.canonical_json(facts))

    def text(cell: str, slug: str, name: str) -> str:
        return (root / "fixtures" / f"{cell}--{slug}" / name).read_text(encoding="utf-8")

    manifest["pairs"] = [
        {
            "id": "ops-mid-to-senior",
            "kind": "advance",
            "resume_fixture": "demo-ops-mid--hospital",
            "jd_fixture": "demo-ops-senior--hospital",
            "transferable": [
                _common_term(
                    text("demo-ops-mid", "hospital", "resume.md"),
                    text("demo-ops-senior", "hospital", "jd.txt"),
                )
            ],
            "note": "A mid operator reaching for the senior role.",
        },
        {
            "id": "ops-to-admin",
            "kind": "change",
            "resume_fixture": "demo-ops-mid--bank",
            "jd_fixture": "demo-ap-mid--bank",
            "transferable": [
                _common_term(
                    text("demo-ops-mid", "bank", "resume.md"), text("demo-ap-mid", "bank", "jd.txt")
                )
            ],
            "note": "An operator moving to administration.",
        },
    ]
    gs.write_pairs(root, manifest)
    gs.write_manifest(root, manifest)
    return root, manifest


class TestPairs:
    """A résumé against another cell's job description: derived, never authored by hand, and checked."""

    def test_a_sound_suite_of_pairs_passes_the_suite_check(self, tmp_path: Path) -> None:
        root, _ = _pair_suite(tmp_path)
        assert gs.check_suite(root) == []

    def test_each_pair_fixture_is_the_résumé_of_one_cell_and_the_jd_of_another(
        self, tmp_path: Path
    ) -> None:
        root, manifest = _pair_suite(tmp_path)
        fx = root / "fixtures"
        for pair in manifest["pairs"]:
            got = fx / gs.pair_fixture_name(pair["id"])
            assert sorted(p.name for p in got.iterdir()) == sorted(gs.PAIR_FILES)
            for name, source in (
                ("resume.md", pair["resume_fixture"]),
                ("seed.json", pair["resume_fixture"]),
                ("jd.txt", pair["jd_fixture"]),
            ):
                assert (got / name).read_bytes() == (fx / source / name).read_bytes(), name

    def test_the_ground_truth_is_built_for_a_candidate_who_does_not_fit(
        self, tmp_path: Path
    ) -> None:
        root, manifest = _pair_suite(tmp_path)
        pair = manifest["pairs"][1]
        got = json.loads(
            (root / "fixtures" / "pair--ops-to-admin" / "expected.json").read_text("utf-8")
        )
        assert got["must_keywords"] == sorted({t.lower() for t in pair["transferable"]})
        assert got["pair"] == {
            "id": "ops-to-admin",
            "kind": "change",
            "resume_fixture": "demo-ops-mid--bank",
            "jd_fixture": "demo-ap-mid--bank",
            "resume_cell": "demo-ops-mid",
            "jd_cell": "demo-ap-mid",
            "transferable": sorted({t.lower() for t in pair["transferable"]}),
        }
        # No keyword-coverage minimum: that rubric would punish the honest answer.
        assert "min_keyword_coverage_score" not in got
        assert "not callback" in got["notes"]
        # A built cell's JD names skills: each one the résumé lacks is trapped as well as listed.
        assert got["jd_requirements_not_shown"]
        assert [t.removeprefix("(?i)").replace("\\", "") for t in got["forbidden_inventions"]][
            : len(got["jd_requirements_not_shown"])
        ] == got["jd_requirements_not_shown"]
        resume = (root / "fixtures" / "pair--ops-to-admin" / "resume.md").read_text("utf-8")
        jd = (root / "fixtures" / "pair--ops-to-admin" / "jd.txt").read_text("utf-8")
        # Every forbidden requirement is one the JD asks for and the résumé does not show.
        own = gs.build_profile(FACTS, _ladder("mid"), "mid")["expected"]["forbidden_inventions"]
        for trap in got["forbidden_inventions"]:
            if trap in own:
                continue
            term = trap.removeprefix("(?i)").replace("\\", "")
            assert gs._mentions(jd, term) or term in jd.lower(), term
            assert not gs._mentions(resume, term), term
        assert all(t in got["forbidden_inventions"] for t in own)

    def test_a_pair_is_deterministic(self, tmp_path: Path) -> None:
        one, _ = _pair_suite(tmp_path / "a")
        two, _ = _pair_suite(tmp_path / "b")
        for pair in ("pair--ops-mid-to-senior", "pair--ops-to-admin"):
            for name in gs.PAIR_FILES:
                assert (one / "fixtures" / pair / name).read_bytes() == (
                    two / "fixtures" / pair / name
                ).read_bytes()

    def test_a_changed_source_cell_makes_its_pair_stale(self, tmp_path: Path) -> None:
        root, _ = _pair_suite(tmp_path)
        profile, prose = gs.load_cell(root, "demo-ops-senior")
        prose["slots"]["jd.hospital.about"] += " Extra words that change the job description."
        gs.write_cell(
            root, profile, prose
        )  # the cell's own fixtures are re-rendered; the pair is not
        gs.write_manifest(root, gs.load_manifest(root))
        found = gs.check_suite(root)
        assert any(
            "pair--ops-mid-to-senior/jd.txt differs from a fresh derivation" in p for p in found
        )

    def test_a_flipped_byte_a_missing_file_and_an_extra_file_are_found(
        self, tmp_path: Path
    ) -> None:
        root, _ = _pair_suite(tmp_path)
        base = root / "fixtures" / "pair--ops-to-admin"
        (base / "resume.md").write_bytes((base / "resume.md").read_bytes() + b"x")
        (base / "seed.json").unlink()
        (base / "notes.txt").write_text("stray", encoding="utf-8")
        found = " | ".join(gs.check_pairs(root, gs.load_manifest(root)))
        assert "pair--ops-to-admin/resume.md differs" in found
        assert "pair--ops-to-admin/seed.json is missing" in found
        assert "pair--ops-to-admin/notes.txt is not a file of a pair fixture" in found

    def test_a_pair_directory_the_manifest_does_not_list_is_found(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        gs.write_manifest(root, manifest | {"pairs": manifest["pairs"][:1]})
        found = gs.check_suite(root)
        assert any("fixtures/pair--ops-to-admin belongs to no pair" in p for p in found)
        assert not any("belongs to no cell" in p for p in found)

    def test_a_listed_pair_with_no_fixture_on_disk_is_found(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        for name in gs.PAIR_FILES:
            (root / "fixtures" / "pair--ops-to-admin" / name).unlink()
        gs.write_manifest(root, manifest)
        found = gs.check_suite(root)
        assert any("pair--ops-to-admin/resume.md is missing" in p for p in found)

    @pytest.mark.parametrize(
        ("change", "needle"),
        [
            ({"id": "Bad Id"}, "id must be lowercase"),
            ({"kind": "swap"}, "kind must be one of"),
            ({"note": ""}, "note must say why"),
            ({"resume_fixture": "demo-ops-mid--nowhere"}, "has no fixture"),
            ({"resume_fixture": "ghost-mid--bank"}, "is not '<cell>--<jd slug>'"),
            ({"jd_fixture": "demo-ap-mid"}, "is not '<cell>--<jd slug>'"),
            ({"transferable": []}, "transferable must be a non-empty list"),
            ({"transferable": ["Quasar"]}, "'Quasar' is not in the résumé"),
            ({"kind": "advance"}, "an advance pair keeps the profession"),
        ],
    )
    def test_a_bad_pair_is_found(self, tmp_path: Path, change: dict[str, Any], needle: str) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[1].update(change)
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any(needle in p for p in gs.check_suite(root)), gs.check_suite(root)

    def test_a_term_missing_from_the_jd_is_found(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        resume = (root / "fixtures" / "demo-ops-mid--bank" / "resume.md").read_text("utf-8")
        jd = (root / "fixtures" / "demo-ap-mid--bank" / "jd.txt").read_text("utf-8")
        only_resume = next(
            s["name"]
            for s in FACTS["skills"]
            if gs._mentions(resume, s["name"]) and not gs._mentions(jd, s["name"])
        )
        pairs[1]["transferable"] = [only_resume]
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any(
            f"{only_resume!r} is not in the job description" in p for p in gs.check_suite(root)
        )

    @pytest.mark.parametrize(
        ("resume", "jd"),
        [
            ("demo-ops-senior--hospital", "demo-ops-mid--hospital"),  # down a tier
            ("demo-ops-mid--hospital", "demo-ops-mid--bank"),  # the same tier
        ],
    )
    def test_an_advance_pair_asks_for_exactly_the_next_tier_up(
        self, tmp_path: Path, resume: str, jd: str
    ) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[0] |= {"resume_fixture": resume, "jd_fixture": jd, "transferable": ["steady"]}
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any("not one step" in p for p in gs.check_suite(root))

    def test_an_advance_pair_cannot_skip_a_tier(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        lead = gs.build_profile(FACTS, _ladder("lead"), "lead")
        gs.write_cell(root, lead, _prose(lead))  # mid to lead leaves out senior
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[0] |= {"jd_fixture": "demo-ops-lead--hospital", "transferable": ["steady"]}
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any("mid to lead is not one step" in p for p in gs.check_suite(root))

    def test_a_change_pair_must_cross_professions(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[1] |= {"jd_fixture": "demo-ops-senior--bank", "transferable": ["steady"]}
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any("a change pair crosses professions" in p for p in gs.check_suite(root))

    def test_two_pairs_cannot_share_an_id(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[1]["id"] = pairs[0]["id"]
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert any("the id is used twice" in p for p in gs.check_suite(root))

    def test_write_pairs_refuses_a_bad_pair_and_writes_nothing(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = [
            *copy.deepcopy(manifest["pairs"]),
            {**manifest["pairs"][0], "id": "late", "kind": "swap"},
        ]
        with pytest.raises(ValueError, match="kind must be one of"):
            gs.write_pairs(root, manifest | {"pairs": pairs})
        assert not (root / "fixtures" / "pair--late").exists()

    def test_the_command_line_writes_the_pairs_and_the_check_then_passes(
        self, tmp_path: Path
    ) -> None:
        root, manifest = _pair_suite(tmp_path)
        shutil.rmtree(root / "fixtures" / "pair--ops-to-admin")
        assert gs.main(["pairs", "--root", str(root)]) == 0
        gs.write_manifest(root, manifest)
        assert gs.check_suite(root) == []

    def test_the_command_line_reports_a_bad_pair_instead_of_raising(self, tmp_path: Path) -> None:
        root, manifest = _pair_suite(tmp_path)
        pairs = copy.deepcopy(manifest["pairs"])
        pairs[0]["note"] = ""
        gs.write_manifest(root, manifest | {"pairs": pairs})
        assert gs.main(["pairs", "--root", str(root)]) == 1

    def test_pair_fixtures_are_hashed_by_the_manifest(self, tmp_path: Path) -> None:
        root, _ = _pair_suite(tmp_path)
        files = gs.load_manifest(root)["files"]
        for pair in ("pair--ops-mid-to-senior", "pair--ops-to-admin"):
            assert all(f"fixtures/{pair}/{name}" in files for name in gs.PAIR_FILES)


CERT_FACTS: dict[str, Any] = FACTS | {
    "education": {
        "degree": "Certificate",
        "field": "Electrical Technology",
        "institutions": ["Tri-County Trade Institute"],
    },
    "certifications": [
        {"name": "Master Licence", "issuer": "State Licensing Board", "level": "senior"},
        {"name": "OSHA 30-Hour Card", "issuer": "Safety Council", "level": "entry"},
        {"name": "Journeyman Licence", "issuer": "State Licensing Board", "level": "mid"},
    ],
}


def _cert_names(profile: dict[str, Any]) -> list[str]:
    sections = [s for s in profile["sections"] if s["kind"] == "certifications"]
    return [c["name"] for s in sections for c in s["items"]]


class TestCertifications:
    """Licences and certifications are facts the candidate holds by tier, and claims the candidate must not make."""

    def test_the_posting_requires_the_highest_certification_the_candidate_holds(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("senior"), "senior")
        held = _cert_names(profile)  # lowest tier first
        # The drive and its controls raise ControlFailed, never a bare assert: a broken setup must not
        # read as the defect (tests/_controls.py).
        control(
            len(held) >= 2, f"the senior cell must hold two or more certifications, holds {held}"
        )
        needs_briefs = [s["brief"] for sid, s in profile["slots"].items() if sid.endswith(".needs")]
        control(len(needs_briefs) >= 1, "the cell must have at least one posting with a needs slot")
        # The one invariant the arm pins, a plain assert (it is the expected AssertionError): every posting
        # of the cell requires the highest certification the candidate holds.
        wanted = f"State {held[-1]} as a required licence or certification."
        assert all(wanted in brief for brief in needs_briefs)

    @pytest.mark.parametrize(
        ("level", "held"),
        [
            ("entry", ["OSHA 30-Hour Card"]),
            ("mid", ["OSHA 30-Hour Card", "Journeyman Licence"]),
            ("senior", ["OSHA 30-Hour Card", "Journeyman Licence", "Master Licence"]),
        ],
    )
    def test_a_candidate_holds_the_certifications_at_or_below_the_level(
        self, level: str, held: list[str]
    ) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder(level), level)
        assert _cert_names(profile) == held

    def test_the_certifications_follow_education_and_a_cell_without_any_has_no_section(
        self,
    ) -> None:
        kinds = [s["kind"] for s in gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")["sections"]]
        assert kinds == ["summary", "experience", "education", "certifications", "skills"]
        plain = gs.build_profile(FACTS, _ladder("mid"), "mid")
        assert [s["kind"] for s in plain["sections"]] == [
            "summary",
            "experience",
            "education",
            "skills",
        ]
        assert gs.render_seed(plain, _prose(plain)["slots"])["certifications"] == []

    def test_a_certification_the_candidate_has_not_reached_is_a_forbidden_invention(self) -> None:
        mid = gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")
        senior = gs.build_profile(CERT_FACTS, _ladder("senior"), "senior")
        assert any(re.search(t, "Master Licence") for t in mid["expected"]["forbidden_inventions"])
        assert not any(
            re.search(t, "Master Licence") for t in senior["expected"]["forbidden_inventions"]
        )
        probes = mid["expected"]["expected_clarification_themes"]["experience_probes"]
        assert "any progress toward Master Licence" in probes
        assert "Master Licence" in mid["expected"]["notes"]

    def test_the_jd_requires_a_held_certification_and_names_the_next_as_preferred(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")
        needs = profile["slots"]["jd.hospital.needs"]
        # The highest-tier held certification is required; the lowest-tier one not yet held is preferred.
        assert "Journeyman Licence" in needs["must_include"]
        assert "Master Licence" in needs["must_include"]
        assert "OSHA 30-Hour Card" not in needs["must_include"]
        assert "State Journeyman Licence as a required" in needs["brief"]
        assert "State Master Licence as preferred" in needs["brief"]
        # A digit in a certification's name is not an invented number: the entry-tier card is the one
        # with the "30", so a cell that holds only it asks for it and allows the digit.
        entry = gs.build_profile(CERT_FACTS, _ladder("entry"), "entry")
        assert "30" in entry["slots"]["jd.hospital.needs"]["allowed_numbers"]

    def test_the_résumé_lists_them_with_issuer_and_a_year_inside_the_career(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")
        text = gs.render_resume(profile, _prose(profile)["slots"])
        assert "## Certifications\n\n- OSHA 30-Hour Card — Safety Council, " in text
        first = int(profile["sections"][1]["roles"][-1]["start"][:4])
        for cert in profile["sections"][3]["items"]:
            assert first <= int(cert["year"]) <= int(gs.ASOF[:4])

    def test_they_reach_the_seed_and_survive_the_importer_and_exporter(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("senior"), "senior")
        seed = gs.render_seed(profile, _prose(profile)["slots"])
        assert [c["name"] for c in seed["certifications"]] == _cert_names(profile)
        assert all(c["issued"] and c["issuer"] for c in seed["certifications"])
        with seeded_session(seed) as (session, username):
            back = export_seed(session, candidate_username=username)
        stable = {k: v for k, v in seed.items() if k not in gs.SEED_VOLATILE_KEYS}
        assert {k: v for k, v in back.items() if k not in gs.SEED_VOLATILE_KEYS} == stable

    def test_the_education_uses_the_professions_own_institutions(self) -> None:
        profile = gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")
        item = profile["sections"][2]["items"][0]
        assert item["institution"] == "Tri-County Trade Institute"
        assert item["degree"] == "Certificate"

    def test_a_built_cell_with_certifications_checks_clean_on_disk(self, tmp_path: Path) -> None:
        root = tmp_path / "golden-v1"
        profile = gs.build_profile(CERT_FACTS, _ladder("mid"), "mid")
        gs.write_cell(root, profile, _prose(profile))
        assert gs.check_cell(root, "demo-ops-mid") == []

    def test_a_section_kind_with_no_renderer_is_refused_not_rendered_as_skills(self) -> None:
        profile = gs.build_profile(FACTS, _ladder("mid"), "mid")
        profile["sections"].append({"kind": "bullets-ish", "heading": "Other"})
        with pytest.raises(ValueError, match="cannot render a section of kind"):
            gs.render_resume(profile, _prose(profile)["slots"])

    @pytest.mark.parametrize(
        ("change", "needle"),
        [
            ({"issuer": ""}, "issuer is empty"),
            ({"level": "principal"}, "level must be one of"),
            ({"name": ""}, "need a distinct, non-empty name"),
        ],
    )
    def test_bad_certification_facts_are_found(self, change: dict[str, str], needle: str) -> None:
        facts = copy.deepcopy(CERT_FACTS)
        facts["certifications"][0].update(change)
        assert any(needle in p for p in gs.validate_facts(facts))

    def test_two_certifications_cannot_share_a_name(self) -> None:
        facts = copy.deepcopy(CERT_FACTS)
        facts["certifications"][1]["name"] = facts["certifications"][0]["name"]
        assert any("distinct, non-empty name" in p for p in gs.validate_facts(facts))

    @pytest.mark.parametrize("institutions", [[], [""], "State University"])
    def test_bad_institutions_are_found(self, institutions: Any) -> None:
        facts = copy.deepcopy(CERT_FACTS)
        facts["education"]["institutions"] = institutions
        assert any("institutions" in p for p in gs.validate_facts(facts))


# ---------------------------------------------------------------------------------------------------
# The profile and prose checks
# ---------------------------------------------------------------------------------------------------


class TestProfileChecks:
    def test_a_used_slot_must_be_declared_and_a_declared_slot_must_be_used(self) -> None:
        profile, _ = _built()
        profile["slots"].pop("r1.b1")
        assert any("used but not declared" in p for p in gs.validate_profile(profile))
        profile, _ = _built()
        profile["slots"]["orphan"] = copy.deepcopy(profile["slots"]["r1.b1"])
        assert any("declared but never used" in p for p in gs.validate_profile(profile))

    def test_a_slot_used_twice_is_refused(self) -> None:
        profile, _ = _built()
        sections = profile["sections"]
        sections[1]["roles"][0]["bullet_slots"].append("r1.b1")
        assert any("used more than once" in p for p in gs.validate_profile(profile))

    def test_a_missing_key_does_not_raise(self) -> None:
        assert gs.validate_profile({"schema": 1}) != []

    def test_a_bad_level_and_an_empty_candidate_field_are_found(self) -> None:
        profile, _ = _built()
        profile["level"] = "principal"
        profile["candidate"]["email"] = ""
        problems = gs.validate_profile(profile)
        assert any("principal" in p for p in problems)
        assert any("candidate.email" in p for p in problems)


class TestSlotText:
    SLOT: ClassVar[dict[str, Any]] = {
        "kind": "bullet",
        "min_words": 3,
        "max_words": 8,
        "must_include": ["Alphaflow"],
        "allowed_numbers": ["25"],
    }

    def _check(self, text: str, traps: list[str] | None = None) -> list[str]:
        return gs.check_slot_text("s", self.SLOT, text, traps or [])

    def test_good_text_passes(self) -> None:
        assert self._check("Ran Alphaflow and cut cost 25 percent") == []

    @pytest.mark.parametrize(
        ("text", "needle"),
        [
            ("Ran Alphaflow and cut cost 30 percent", "number 30"),
            ("Ran something else entirely here", "required fact"),
            ("Alphaflow", "words"),
            ("Alphaflow " + "word " * 12, "words"),
            (" Ran Alphaflow here", "whitespace"),
            ("Ran Alphaflow\nhere today", "one line"),
            ("Ran Alphaflow  here today", "double space"),
        ],
    )
    def test_each_rule_fires(self, text: str, needle: str) -> None:
        assert any(needle in p for p in self._check(text)), text

    def test_a_trap_fires(self) -> None:
        assert any("trap" in p for p in self._check("Ran Alphaflow with a PhD", ["PhD"]))

    def test_traps_do_not_apply_to_a_jd(self) -> None:
        profile, prose = _built()
        absent = next(
            s["name"]
            for s in FACTS["skills"]
            if s["name"] not in {k["name"] for k in profile["skills"]}
        )
        jd_id = "jd.hospital.needs"
        prose["slots"][jd_id] += f" {absent}"
        profile["slots"][jd_id]["must_include"].append(absent)
        assert not [p for p in gs.check_prose(profile, prose) if jd_id in p and "trap" in p]

    def test_traps_hold_generated_prose_but_not_converted_prose(self) -> None:
        profile, prose = _built()
        trap = profile["expected"]["forbidden_inventions"][0]
        claim = re.sub(r"\\(.)", r"\1", trap)  # the literal the trap would match
        assert re.search(trap, claim)
        prose["slots"]["r1.b2"] += f" {claim}"
        profile["slots"]["r1.b2"]["max_words"] += 5
        assert any("trap" in p for p in gs.check_prose(profile, prose))
        prose["provenance"] = {"kind": "converted"}
        assert not any("trap" in p for p in gs.check_prose(profile, prose))

    def test_prose_must_cover_exactly_the_declared_slots(self) -> None:
        profile, prose = _built()
        prose["slots"].pop("r1.b1")
        prose["slots"]["extra"] = "text"
        problems = gs.check_prose(profile, prose)
        assert any("no text for slot 'r1.b1'" in p for p in problems)
        assert any("undeclared slot 'extra'" in p for p in problems)


# ---------------------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------------------


class TestRender:
    def test_one_fixture_per_jd(self) -> None:
        profile, prose = _built()
        fixtures = gs.render_fixtures(profile, prose)
        assert sorted(fixtures) == [f"{profile['cell']}--bank", f"{profile['cell']}--hospital"]
        for files in fixtures.values():
            assert sorted(files) == ["expected.json", "jd.txt", "resume.md", "seed.json"]

    def test_the_résumé_shows_the_first_summary_only(self) -> None:
        profile, prose = _built()
        prose["slots"]["summary.2"] = prose["slots"]["summary.2"] + " second"
        resume = gs.render_fixtures(profile, prose)[f"{profile['cell']}--bank"]["resume.md"]
        assert prose["slots"]["summary.1"] in resume
        assert prose["slots"]["summary.2"] not in resume

    def test_rendering_is_deterministic_and_lf(self) -> None:
        profile, prose = _built()
        assert gs.render_fixtures(profile, prose) == gs.render_fixtures(profile, prose)
        for files in gs.render_fixtures(profile, prose).values():
            assert not any("\r" in text for text in files.values())

    def test_the_iteration_target_is_a_substring_of_the_slot(self) -> None:
        profile, prose = _built()
        scenario = json.loads(
            gs.render_fixtures(profile, prose)[f"{profile['cell']}--bank"]["expected.json"]
        )["iteration_scenarios"][0]
        slot_text = prose["slots"][profile["iteration"]["target_slot"]]
        assert scenario["edit_target_substring"] in slot_text
        assert scenario["edit_target_substring"] in scenario["edit_replacement"]

    def test_pick_edit_target_needs_five_words(self) -> None:
        with pytest.raises(ValueError, match="five words"):
            gs.pick_edit_target("Too short, really")
        assert (
            gs.pick_edit_target("one two three four five six, seven")
            == "one two three four five six"
        )


class TestSeed:
    """The seed round-trips through the importer and the exporter, so a key either drops or it does not."""

    @staticmethod
    def _roundtrip(seed: dict[str, Any]) -> dict[str, Any]:
        with seeded_session(seed) as (session, username):
            return export_seed(session, candidate_username=username)

    @staticmethod
    def _stable(seed: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in seed.items() if k not in gs.SEED_VOLATILE_KEYS}

    @pytest.mark.parametrize("level", gs.LEVELS)
    def test_a_built_cell_survives_import_and_export_unchanged(self, level: str) -> None:
        profile, prose = _built(level)
        seed = gs.render_seed(profile, prose["slots"])
        assert self._stable(self._roundtrip(seed)) == self._stable(seed)

    def test_a_key_the_importer_does_not_read_would_be_caught(self) -> None:
        # The control arm: the committed corpus seed's `area` / `study_type` are dropped on import,
        # which is exactly what this round trip exists to expose.
        profile, prose = _built()
        seed = gs.render_seed(profile, prose["slots"])
        seed["educations"][0]["area"] = seed["educations"][0].pop("field")
        assert self._stable(self._roundtrip(seed)) != self._stable(seed)

    def test_the_seed_feeds_the_real_context_builder(self) -> None:
        profile, prose = _built()
        seed = gs.render_seed(profile, prose["slots"])
        jd = gs.render_jd(profile["jds"][0], prose["slots"])
        with seeded_session(seed) as (session, username):
            context: dict[str, Any] = dict(
                build_context_set_from_db(
                    session, candidate_username=username, jd_text=jd, run_id="golden-test"
                )[0]
            )
        assert context["candidate"]["name"] == profile["candidate"]["name"]
        assert len(context["career_corpus"]) == len(profile["sections"][1]["roles"])
        assert context["candidate"]["skills"]

    def test_the_summary_variants_and_intros_reach_the_seed(self) -> None:
        profile, prose = _built()
        seed = gs.render_seed(profile, prose["slots"])
        assert len(seed["summary_items"]) == 2
        assert all(len(exp["summary_items"]) == 2 for exp in seed["experiences"])


# ---------------------------------------------------------------------------------------------------
# Cells and the suite on disk
# ---------------------------------------------------------------------------------------------------


class TestCellFiles:
    def test_a_written_cell_checks_clean(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        assert gs.check_cell(root, "demo-ops-mid") == []

    def test_write_refuses_an_unsound_cell(self, tmp_path: Path) -> None:
        profile, prose = _built()
        prose["slots"]["r1.b1"] = "no figure and no skill here at all today"
        with pytest.raises(ValueError, match="not sound"):
            gs.write_cell(tmp_path / "g", profile, prose)

    def test_a_flipped_byte_in_a_derived_file_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        target = root / "fixtures" / "demo-ops-mid--bank" / "resume.md"
        target.write_bytes(target.read_bytes().replace(b"steady", b"steadY", 1))
        assert any("differs from a fresh render" in p for p in gs.check_cell(root, "demo-ops-mid"))

    def test_a_missing_derived_file_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        (root / "fixtures" / "demo-ops-mid--bank" / "seed.json").unlink()
        assert any("seed.json is missing" in p for p in gs.check_cell(root, "demo-ops-mid"))

    def test_an_edited_profile_makes_generated_prose_stale(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        path = root / "cells" / "demo-ops-mid" / "profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["expected"]["notes"] = "edited after the prose was written"
        _put(path, gs.canonical_json(profile))
        assert any("different profile" in p for p in gs.check_cell(root, "demo-ops-mid"))

    def test_a_fixture_no_jd_produces_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        (root / "fixtures" / "demo-ops-mid--gone").mkdir()
        assert any("no JD of this cell produces" in p for p in gs.check_cell(root, "demo-ops-mid"))

    def test_the_files_are_written_with_lf(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        listed = gs.tracked_files(root)
        assert listed, "the suite wrote no files"
        for relative in [*listed, "manifest.json"]:
            assert b"\r" not in (root / relative).read_bytes(), relative


class TestSuiteChecks:
    def test_a_sound_draft_suite_passes(self, tmp_path: Path) -> None:
        assert gs.check_suite(_suite(tmp_path, "entry", "mid")) == []

    def test_a_changed_file_is_found_through_the_manifest(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        path = root / "facts" / "demo-ops.json"
        _put(path, path.read_text(encoding="utf-8") + " ")
        assert any("changed since the manifest" in p for p in gs.check_suite(root))

    def test_a_file_missing_from_the_manifest_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        _put(root / "facts" / "new.json", "{}\n")
        assert any("on disk but not in the manifest" in p for p in gs.check_suite(root))

    def test_an_unknown_profession_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root) | {"professions": {}}
        gs.write_manifest(root, manifest)
        assert any("not in the manifest" in p for p in gs.check_suite(root))

    def test_a_generated_prompt_version_must_be_recorded_with_its_hash(
        self, tmp_path: Path
    ) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["author"]["prompt_versions"] = {}
        gs.write_manifest(root, manifest)
        assert any("not recorded in the manifest" in p for p in gs.check_suite(root))

    def test_an_orphan_fixture_directory_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        (root / "fixtures" / "stray--x").mkdir()
        gs.write_manifest(root, gs.load_manifest(root))
        assert any("belongs to no cell" in p for p in gs.check_suite(root))

    def test_a_bad_level_rule_source_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["families"]["demo"]["levels"]["mid"]["rule_source"] = "guessed"
        gs.write_manifest(root, manifest)
        assert any("rule_source" in p for p in gs.check_suite(root))

    def test_a_schema_one_manifest_is_refused(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        gs.write_manifest(root, gs.load_manifest(root) | {"schema": 1})
        assert any("manifest schema 1" in p for p in gs.check_suite(root))

    def test_a_profession_must_name_a_family_the_manifest_has(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["professions"]["demo-ops"]["family"] = "nowhere"
        gs.write_manifest(root, manifest)
        assert any("family 'nowhere' is not in the manifest" in p for p in gs.check_suite(root))

    def _write_facts(self, root: Path, name: str, facts: dict[str, Any]) -> None:
        _put(root / "facts" / f"{name}.json", gs.canonical_json(facts))
        gs.write_manifest(root, gs.load_manifest(root))

    def test_a_facts_file_that_breaks_a_rule_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        bad = copy.deepcopy(FACTS)
        bad["skills"][0]["name"] = "Go"
        self._write_facts(root, "demo-ops", bad)
        assert any(
            "facts/demo-ops.json:" in p and "under three characters" in p
            for p in gs.check_suite(root)
        )

    def test_a_facts_file_is_named_for_its_profession(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        self._write_facts(root, "other-name", FACTS)
        assert any(
            "facts/other-name.json" in p and "the file is named 'other-name'" in p
            for p in gs.check_suite(root)
        )

    def test_a_facts_file_for_a_profession_the_manifest_lacks_is_found(
        self, tmp_path: Path
    ) -> None:
        root = _suite(tmp_path)
        self._write_facts(root, "stray", FACTS | {"profession": "stray"})
        assert any(
            "facts/stray.json" in p and "not in the manifest" in p for p in gs.check_suite(root)
        )

    def test_a_facts_file_that_cannot_feed_its_ladder_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        thin = copy.deepcopy(FACTS)
        thin["skills"] = thin["skills"][
            :9
        ]  # the ladder lists 8 and a JD needs 2 more the cell lacks
        self._write_facts(root, "demo-ops", thin)
        assert any(
            "facts/demo-ops.json" in p and "9 skills" in p and "8 plus 2" in p
            for p in gs.check_suite(root)
        )

    def test_an_unreadable_facts_file_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        _put(root / "facts" / "demo-ops.json", "{not json")
        gs.write_manifest(root, gs.load_manifest(root))
        assert any("facts/demo-ops.json cannot be read" in p for p in gs.check_suite(root))

    def test_a_profession_may_name_one_of_the_four_groups(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["professions"]["demo-ops"]["group"] = gs.GROUPS[0]
        gs.write_manifest(root, manifest)
        assert gs.check_suite(root) == []

    @pytest.mark.parametrize("group", ["", "tech", 3])
    def test_a_group_the_set_does_not_define_is_found(self, tmp_path: Path, group: Any) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["professions"]["demo-ops"]["group"] = group
        gs.write_manifest(root, manifest)
        assert any("profession demo-ops: group" in p for p in gs.check_suite(root))

    def test_the_four_groups_are_the_ones_the_design_names(self) -> None:
        assert gs.GROUPS == (
            "tech-and-product",
            "business-and-office",
            "health-education-and-community",
            "trades-and-construction",
        )

    def test_a_family_must_have_exactly_the_four_tiers(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        del manifest["families"]["demo"]["levels"]["lead"]
        gs.write_manifest(root, manifest)
        assert any("family demo: levels" in p for p in gs.check_suite(root))

    @pytest.mark.parametrize("label", [None, ""])
    def test_a_level_needs_its_own_label(self, tmp_path: Path, label: str | None) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["families"]["demo"]["levels"]["mid"]["label"] = label
        gs.write_manifest(root, manifest)
        assert any("label must be a non-empty string" in p for p in gs.check_suite(root))

    @pytest.mark.parametrize("years", [[5, 3], [3], ["3", "5"], [-1, 2]])
    def test_a_level_needs_a_sound_years_window(self, tmp_path: Path, years: list[Any]) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["families"]["demo"]["levels"]["mid"]["years"] = years
        gs.write_manifest(root, manifest)
        assert any("years must be" in p for p in gs.check_suite(root))

    def test_a_ladder_whose_roles_do_not_fit_its_years_is_found(self, tmp_path: Path) -> None:
        root = _suite(tmp_path)
        manifest = gs.load_manifest(root)
        manifest["families"]["demo"]["levels"]["lead"]["years"] = [1, 2]  # 3 roles need 36 months
        gs.write_manifest(root, manifest)
        assert any("do not fit in 2 years" in p for p in gs.check_suite(root))


class TestLadderFor:
    def test_it_finds_the_rule_through_the_family(self) -> None:
        assert gs.ladder_for(_manifest(), "demo-ops", "senior") == _ladder("senior")

    def test_an_unknown_profession_or_level_says_which(self) -> None:
        with pytest.raises(KeyError, match="no family in the manifest"):
            gs.ladder_for(_manifest(), "nope", "mid")
        with pytest.raises(KeyError, match="no rule for level"):
            gs.ladder_for(_manifest(), "demo-ops", "principal")


class TestWaivers:
    """A pilot's missing richness is listed, exactly; a frozen suite lists none."""

    def _pilot_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "golden-v1"
        profile, prose = gs.profile_from_persona(
            PERSONAS / "data-scientist-junior",
            cell="demo-ops-entry",
            profession="demo-ops",
            level="entry",
            industry="insurance",
            username="gold_pilot",
        )
        gs.write_cell(root, profile, prose)
        gs.write_manifest(root, _manifest())
        return root

    def test_a_pilot_fails_exactly_the_predicates_a_converted_persona_cannot_meet(
        self, tmp_path: Path
    ) -> None:
        root = self._pilot_root(tmp_path)
        profile, _ = gs.load_cell(root, "demo-ops-entry")
        assert gs.failing_predicates(profile) == [
            "clarifications",
            "refinement_notes",
            "role_intro_variants",
            "summary_variants",
        ]

    def test_an_unwaived_gap_and_a_stale_waiver_are_both_found(self, tmp_path: Path) -> None:
        root = self._pilot_root(tmp_path)
        problems = gs.check_suite(root)
        assert any("fails and is not waived" in p for p in problems)
        fixture = "demo-ops-entry--insurance"
        waivers = [
            f"{fixture}:{p}"
            for p in (
                "clarifications",
                "refinement_notes",
                "role_intro_variants",
                "summary_variants",
            )
        ]
        manifest = gs.load_manifest(root) | {"pilot_waivers": [*waivers, f"{fixture}:skills"]}
        gs.write_manifest(root, manifest)
        problems = gs.check_suite(root)
        assert problems == [f"stale waiver, the predicate holds: {fixture}:skills"]
        gs.write_manifest(root, manifest | {"pilot_waivers": waivers})
        assert gs.check_suite(root) == []

    def test_a_frozen_suite_with_a_gap_is_refused(self, tmp_path: Path) -> None:
        root = self._pilot_root(tmp_path)
        gs.write_manifest(root, gs.load_manifest(root) | {"status": "frozen"})
        assert any("frozen suite has no waivers" in p for p in gs.check_suite(root))

    def test_a_frozen_suite_of_rich_cells_passes(self, tmp_path: Path) -> None:
        assert gs.check_suite(_suite(tmp_path, "mid", status="frozen")) == []


# ---------------------------------------------------------------------------------------------------
# Converting the existing personas
# ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("persona", ["data-scientist-junior", "pm-senior", "sre-mid-level"])
class TestConverter:
    def _convert(self, persona: str) -> tuple[dict[str, Any], dict[str, Any]]:
        return gs.profile_from_persona(
            PERSONAS / persona,
            cell="pilot-cell",
            profession="pilot",
            level="mid",
            industry="demo",
            username="gold_pilot",
        )

    def test_the_cell_renders_back_to_the_persona_byte_for_byte(self, persona: str) -> None:
        profile, prose = self._convert(persona)
        files = gs.render_fixtures(profile, prose)["pilot-cell--demo"]
        assert files["resume.md"].encode() == (PERSONAS / persona / "resume.md").read_bytes()
        assert files["jd.txt"].encode() == (PERSONAS / persona / "jd.txt").read_bytes()

    def test_the_ground_truth_is_the_same_json(self, persona: str) -> None:
        profile, prose = self._convert(persona)
        rendered = json.loads(
            gs.render_fixtures(profile, prose)["pilot-cell--demo"]["expected.json"]
        )
        original = json.loads((PERSONAS / persona / "expected.json").read_text(encoding="utf-8"))
        assert rendered == original

    def test_the_converted_cell_is_sound_and_its_seed_round_trips(self, persona: str) -> None:
        profile, prose = self._convert(persona)
        assert gs.validate_profile(profile) == []
        assert gs.check_prose(profile, prose) == []
        seed = gs.render_seed(profile, prose["slots"])
        assert TestSeed._stable(TestSeed._roundtrip(seed)) == TestSeed._stable(seed)

    def test_the_provenance_names_the_source_files(self, persona: str) -> None:
        _, prose = self._convert(persona)
        provenance = prose["provenance"]
        assert provenance["kind"] == "converted"
        assert provenance["persona"] == persona
        assert set(provenance["source_sha256"]) == {"resume.md", "jd.txt", "expected.json"}


class TestParser:
    def test_skills_split_outside_parentheses_only(self) -> None:
        assert gs._split_skills("Python (pandas, NumPy), SQL, git") == [
            "Python (pandas, NumPy)",
            "SQL",
            "git",
        ]

    def test_a_layout_it_does_not_understand_is_refused(self) -> None:
        with pytest.raises(ValueError):
            gs.parse_resume("# Name\n\nonly one line\n")
        with pytest.raises(ValueError, match="full stop"):
            gs.parse_resume(
                "# N\n\na@b.com | (555) 010-0000 | l.in/x\n\n## Skills\n\nno full stop\n"
            )

    def test_the_converter_refuses_a_persona_it_cannot_reproduce(self, tmp_path: Path) -> None:
        source = PERSONAS / "pm-senior"
        copy_dir = tmp_path / "persona"
        copy_dir.mkdir()
        for name in ("resume.md", "jd.txt", "expected.json"):
            (copy_dir / name).write_bytes((source / name).read_bytes())
        (copy_dir / "jd.txt").write_text("A JD\nwith no trailing newline", encoding="utf-8")
        with pytest.raises(ValueError, match=r"jd\.txt"):
            gs.profile_from_persona(
                copy_dir, cell="c", profession="p", level="mid", industry="x", username="u"
            )


class TestCommittedSuite:
    """The committed `evals/golden/golden-v1/`, once it exists, passes its own checker."""

    def test_the_committed_suite_is_sound(self) -> None:
        if not (gs.SUITE_DIR / "manifest.json").is_file():
            pytest.skip("no committed suite yet")
        assert gs.check_suite(gs.SUITE_DIR) == []

    def test_no_converted_pilot_is_left_and_no_waiver_with_it(self) -> None:
        # The three converted pilots were replaced by generated cells (item 191); a frozen suite has none.
        manifest = gs.load_manifest(gs.SUITE_DIR)
        assert manifest["pilot_waivers"] == []
        for cell in gs.cell_names(gs.SUITE_DIR):
            kind = gs.load_cell(gs.SUITE_DIR, cell)[1]["provenance"]["kind"]
            assert kind == "generated", cell

    def test_every_committed_pair_traps_what_the_resume_lacks_and_not_what_it_has(self) -> None:
        manifest = gs.load_manifest(gs.SUITE_DIR)
        assert manifest["pairs"], "the set has pairs once the pairs step has run"
        fixtures = gs.SUITE_DIR / "fixtures"
        for pair in manifest["pairs"]:
            expected = json.loads(
                (fixtures / gs.pair_fixture_name(pair["id"]) / "expected.json").read_text("utf-8")
            )
            resume = json.loads(
                (fixtures / pair["resume_fixture"] / "expected.json").read_text("utf-8")
            )
            traps = expected["forbidden_inventions"]
            # The posting's requirements the resume does not show are inventions to avoid ...
            for missing in expected["jd_requirements_not_shown"]:
                assert "(?i)" + re.escape(missing) in traps, (pair["id"], missing)
            # ... the resume cell's own traps still stand ...
            assert set(resume["forbidden_inventions"]) <= set(traps), pair["id"]
            # ... and a term the candidate truly has, which the pair lists as transferable, is never trapped.
            for term in pair["transferable"]:
                assert "(?i)" + re.escape(term) not in traps, (pair["id"], term)
            assert (
                expected["must_keywords"] == sorted({t.lower() for t in pair["transferable"]})[:6]
            )
