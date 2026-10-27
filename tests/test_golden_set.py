"""The golden set's format (`evals/golden_set.py`): determinism, the renderer, the checks, the converter.

Everything here builds its cells in ``tmp_path``. Nothing reads or writes the committed suite except
`TestCommittedSuite`, which runs the suite checker over it. LLM-free: the prose in these tests is
made by `_prose`, which writes the shortest text that meets each slot's rules.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, ClassVar

import pytest

from db.build_context import build_context_set_from_db
from evals import golden_set as gs
from evals.seed_import import seeded_session
from scripts.export_corpus_seed import export_seed

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
    "industries": [
        {
            "slug": "hospital",
            "company": "Northwind Health",
            "phrase": "a regional hospital network",
        },
        {"slug": "bank", "company": "Cedar Bank", "phrase": "a mid-size retail bank"},
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
        assert missing and any(re.escape(m) in traps for m in missing)
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
