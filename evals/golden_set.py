"""The golden set's format: a cell's source files, the deterministic renderer, and the checks.

Deterministic, LLM-free, stdlib-only (P1 hardening boundary: an ``evals/`` helper, no model calls).
The prose generator that calls a model lives in ``evals/golden_author.py``; this module only
describes what it must write and checks what it wrote.

**A cell** is one profession at one level. Its SOURCE files are written by code or by the generator
and are the only files a person edits:

* ``cells/<cell>/profile.json``, written by code: the candidate, the ordered résumé sections, every
  prose *slot* (what it is for, which facts it must carry, which numbers it may contain), the JDs,
  the invention traps, the iteration scenario and the ground truth.
* ``cells/<cell>/prose.json``: the text for each slot, with provenance (``generated`` by a model, or
  ``converted`` from an existing persona).

Everything else is DERIVED by ``render_fixtures`` and must equal a re-render byte for byte:
``fixtures/<cell>--<industry>/{resume.md, jd.txt, expected.json, seed.json}``. One fixture per JD, so the
runner's one-``jd.txt``-per-fixture contract is unchanged. ``seed.json`` is in the exporter's shape
(``scripts/export_corpus_seed.py``), and the tests import it and export it back: a key the importer does
not read comes back different, which is how the old ``area`` / ``study_type`` drop would be caught.

``manifest.json`` records the version, the level ladder (each rule marked ``authored`` or ``sourced``),
the professions and their O*NET attribution, the author prompt versions and a sha256 per file. A
``frozen`` manifest must have no pilot waivers: the version is then ground truth, and a later version
adds cells and never edits one in place (design doc 6.4).

Limits, stated: the prose validator cannot tell an invented employer from a real one, only digits,
required facts, traps and length; the downstream grounding metric is the check on that. Freezing is not
enforced against git history, so a later commit could rewrite a cell and its manifest hash together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = 1
#: The manifest's own schema. Cells and prose stay at `SCHEMA`, so moving the manifest to a ladder per family
#: (2) changes no committed cell byte.
MANIFEST_SCHEMA = 2
#: A role shorter than this is not a job a résumé lists; a ladder must fit its roles at this length.
MIN_ROLE_MONTHS = 12
SUITE = "golden-v1"
GOLDEN_ROOT = Path(__file__).resolve().parent / "golden"
SUITE_DIR = GOLDEN_ROOT / SUITE

LEVELS = ("entry", "mid", "senior", "lead")
STATUSES = ("draft", "frozen")
SECTION_KINDS = ("summary", "experience", "education", "bullets", "skills")
SLOT_KINDS = ("summary", "intro", "bullet", "jd")
PROSE_KINDS = ("generated", "converted")

#: The dataset's own "now". A fixed month, never the clock, so a rendered date does not drift.
ASOF = "2026-10"

#: Seed keys that change on every export and are not part of the comparison.
SEED_VOLATILE_KEYS = ("generator", "exported_at")

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Invented names. Any resemblance to a person or an organisation is coincidental; every address is
# example.com and every phone number is in the reserved 555-01xx style.
_FIRST_NAMES = (
    "Alex", "Jordan", "Priya", "Morgan", "Sam", "Riley", "Casey", "Taylor", "Avery", "Quinn",
    "Devon", "Harper",
)  # fmt: skip
_LAST_NAMES = (
    "Chen", "Park", "Mehta", "Reyes", "Okafor", "Lindqvist", "Haddad", "Novak", "Silva", "Brandt",
    "Kowalski", "Ito",
)  # fmt: skip
_EMPLOYERS = (
    "Alder Systems", "Brightwater Labs", "Calloway Group", "Dunmore Technologies",
    "Elmstead Partners", "Fairhaven Works", "Granite Ridge", "Halcyon Services",
    "Ironbridge Co", "Juniper Row", "Kestrel Works", "Lantern Hill", "Meridian Cross",
    "Northfield Group", "Oakmont Systems", "Pinecrest Labs",
)  # fmt: skip
_SCHOOLS = (
    "State University",
    "Lakeshore University",
    "Ridgeway College",
    "Northern Plains University",
)

#: Invention patterns every cell carries, whatever its profession.
GENERIC_TRAPS = ("PhD", "Master'?s? (degree|in)", "managed [0-9]+", "10\\+ years")

# --------------------------------------------------------------------------------------------------
# Files: canonical JSON, hashes, paths
# --------------------------------------------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    """The one serialisation every committed JSON file uses: sorted keys, 2-space indent, LF, UTF-8."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:  # LF on Windows too (.gitattributes)
        fh.write(text)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_name(cell: str, jd_slug: str) -> str:
    return f"{cell}--{jd_slug}"


# --------------------------------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------------------------------


def month_label(iso: str | None) -> str:
    """``2024-07`` -> ``July 2024``; ``None`` -> ``present``."""
    if iso is None:
        return "present"
    match = re.fullmatch(r"(\d{4})-(\d{2})", iso)
    if match is None or not 1 <= int(match.group(2)) <= 12:
        raise ValueError(f"not a YYYY-MM month: {iso!r}")
    return f"{_MONTHS[int(match.group(2)) - 1]} {match.group(1)}"


def month_iso(label: str) -> str | None:
    """The inverse of `month_label`."""
    if label == "present":
        return None
    name, _, year = label.partition(" ")
    if name not in _MONTHS or not re.fullmatch(r"\d{4}", year):
        raise ValueError(f"not a 'Month YYYY' label: {label!r}")
    return f"{year}-{_MONTHS.index(name) + 1:02d}"


def _months(iso: str) -> int:
    year, month = iso.split("-")
    return int(year) * 12 + int(month) - 1


def _iso(months: int) -> str:
    return f"{months // 12:04d}-{months % 12 + 1:02d}"


# --------------------------------------------------------------------------------------------------
# The profile: what slots exist, and the checks on its shape
# --------------------------------------------------------------------------------------------------


def section_slots(section: dict[str, Any]) -> list[str]:
    """Every résumé slot id one section uses, in render order."""
    kind = section["kind"]
    if kind in ("summary", "bullets"):
        return list(section["slots"])
    if kind == "experience":
        out: list[str] = []
        for role in section["roles"]:
            out.extend(role["bullet_slots"])
        return out
    if kind == "education":
        return [s for item in section["items"] for s in item.get("slots", [])]
    return []


def resume_slots(profile: dict[str, Any]) -> list[str]:
    """Slots that appear in ``resume.md``. The extra summary variants and the intros are seed-only."""
    out: list[str] = []
    for section in profile["sections"]:
        slots = section_slots(section)
        out.extend(slots[:1] if section["kind"] == "summary" else slots)
    return out


def seed_only_slots(profile: dict[str, Any]) -> list[str]:
    """Summary variants after the first, and every per-role intro: corpus text the résumé does not show."""
    out: list[str] = []
    for section in profile["sections"]:
        if section["kind"] == "summary":
            out.extend(section["slots"][1:])
        elif section["kind"] == "experience":
            for role in section["roles"]:
                out.extend(role.get("intro_slots", []))
    return out


def jd_slots(profile: dict[str, Any]) -> list[str]:
    return [s for jd in profile["jds"] for s in jd["slots"]]


def all_slot_ids(profile: dict[str, Any]) -> list[str]:
    return resume_slots(profile) + seed_only_slots(profile) + jd_slots(profile)


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Problems with a profile's shape, empty when it is sound. Never raises on bad content."""
    problems: list[str] = []
    for key in (
        "schema",
        "cell",
        "profession",
        "level",
        "cell_seed",
        "candidate",
        "sections",
        "slots",
        "jds",
    ):
        if key not in profile:
            problems.append(f"profile is missing {key!r}")
    if problems:
        return problems
    if profile["schema"] != SCHEMA:
        problems.append(f"profile schema {profile['schema']!r}, this reader knows {SCHEMA}")
    if profile["level"] not in LEVELS:
        problems.append(f"level {profile['level']!r} is not one of {LEVELS}")
    if not isinstance(profile["cell_seed"], int):
        problems.append("cell_seed must be an integer")
    for key in ("name", "email", "phone", "linkedin", "username"):
        if not profile["candidate"].get(key):
            problems.append(f"candidate.{key} is empty")
    for section in profile["sections"]:
        if section.get("kind") not in SECTION_KINDS:
            problems.append(f"section kind {section.get('kind')!r} is not one of {SECTION_KINDS}")
            return problems
    ids = all_slot_ids(profile)
    for slot_id in sorted({s for s in ids if ids.count(s) > 1}):
        problems.append(f"slot {slot_id!r} is used more than once")
    declared = set(profile["slots"])
    for slot_id in sorted(set(ids) - declared):
        problems.append(f"slot {slot_id!r} is used but not declared in slots")
    for slot_id in sorted(declared - set(ids)):
        problems.append(f"slot {slot_id!r} is declared but never used")
    for slot_id, slot in profile["slots"].items():
        if slot.get("kind") not in SLOT_KINDS:
            problems.append(
                f"slot {slot_id!r}: kind {slot.get('kind')!r} is not one of {SLOT_KINDS}"
            )
        if not 0 < int(slot.get("min_words", 0)) <= int(slot.get("max_words", 0)):
            problems.append(f"slot {slot_id!r}: need 0 < min_words <= max_words")
        if not all(isinstance(n, str) and n.isdigit() for n in slot.get("allowed_numbers", [])):
            problems.append(f"slot {slot_id!r}: allowed_numbers must be strings of digits")
    if not profile["jds"]:
        problems.append("a cell needs at least one JD")
    slugs = [jd["slug"] for jd in profile["jds"]]
    if len(set(slugs)) != len(slugs):
        problems.append(f"duplicate JD slugs {slugs}")
    for jd in profile["jds"]:
        if not re.fullmatch(r"[a-z0-9-]+", jd["slug"]):
            problems.append(f"JD slug {jd['slug']!r} must be lowercase letters, digits and hyphens")
    expected = profile.get("expected", {})
    if not expected.get("must_keywords"):
        problems.append("expected.must_keywords is empty")
    iteration = profile.get("iteration")
    if iteration is not None:
        if iteration.get("mode") not in ("verbatim", "derived"):
            problems.append(f"iteration.mode {iteration.get('mode')!r} is not verbatim or derived")
        elif (
            iteration["mode"] == "derived" and iteration.get("target_slot") not in profile["slots"]
        ):
            problems.append(f"iteration.target_slot {iteration.get('target_slot')!r} is not a slot")
    return problems


# --------------------------------------------------------------------------------------------------
# Prose: the checks on the text a slot holds
# --------------------------------------------------------------------------------------------------


def check_slot_text(slot_id: str, slot: dict[str, Any], text: str, traps: list[str]) -> list[str]:
    """Problems with one slot's text. The rules a generator's output must meet before it is kept."""
    problems: list[str] = []
    if text != text.strip():
        problems.append(f"{slot_id}: text has leading or trailing whitespace")
    one_line = slot["kind"] != "jd"
    if one_line and ("\n" in text or "\r" in text):
        problems.append(f"{slot_id}: a {slot['kind']} slot is one line")
    if "  " in text:
        problems.append(f"{slot_id}: text has a double space")
    words = len(text.split())
    if not slot["min_words"] <= words <= slot["max_words"]:
        problems.append(
            f"{slot_id}: {words} words, expected {slot['min_words']} to {slot['max_words']}"
        )
    allowed = set(slot.get("allowed_numbers", []))
    for run in re.findall(r"\d+", text):
        if run not in allowed:
            problems.append(
                f"{slot_id}: the number {run} is not one the slot allows {sorted(allowed)}"
            )
    lowered = text.lower()
    for token in slot.get("must_include", []):
        if token.lower() not in lowered:
            problems.append(f"{slot_id}: required fact {token!r} is missing")
    for trap in traps:
        if re.search(trap, text):
            problems.append(f"{slot_id}: matches the invention trap {trap!r}")
    return problems


def check_prose(profile: dict[str, Any], prose: dict[str, Any]) -> list[str]:
    """Slot-set equality plus `check_slot_text` on every slot."""
    texts = prose.get("slots", {})
    declared = set(profile["slots"])
    problems = [f"prose has no text for slot {s!r}" for s in sorted(declared - set(texts))]
    problems += [f"prose has text for undeclared slot {s!r}" for s in sorted(set(texts) - declared)]
    traps = list(profile.get("expected", {}).get("forbidden_inventions", []))
    # The traps are written against eval OUTPUT ("MUST NOT appear in the generated output",
    # evals/rubrics/grounding.md). They guard model-written dataset prose against claiming what the
    # candidate lacks. Converted persona text is the source those traps were written against, and may
    # contain a match legitimately (the data-scientist persona names a "senior data scientist"
    # colleague while the trap forbids claiming the title), so it is not held to them.
    converted = prose.get("provenance", {}).get("kind") == "converted"
    for slot_id in sorted(declared & set(texts)):
        slot = profile["slots"][slot_id]
        # A JD names the skills the candidate lacks on purpose (that is the stretch), so the traps
        # are not applied to JD text either.
        slot_traps = [] if converted or slot["kind"] == "jd" else traps
        problems += check_slot_text(slot_id, slot, texts[slot_id], slot_traps)
    return problems


# --------------------------------------------------------------------------------------------------
# The renderer
# --------------------------------------------------------------------------------------------------


def render_resume(profile: dict[str, Any], texts: dict[str, str]) -> str:
    """``resume.md`` from the ordered sections. Reproduces the existing personas' layout exactly."""
    cand = profile["candidate"]
    out = [
        f"# {cand['name']}",
        "",
        " | ".join(x for x in (cand["email"], cand["phone"], cand["linkedin"]) if x),
        "",
    ]
    for section in profile["sections"]:
        out += [f"## {section['heading']}", ""]
        kind = section["kind"]
        if kind == "summary":
            out += [texts[section["slots"][0]], ""]
        elif kind == "experience":
            for role in section["roles"]:
                out += [
                    f"### {role['title']} — {role['company']}",
                    f"*{month_label(role['start'])} – {month_label(role['end'])}*",
                    "",
                ]
                out += [f"- {texts[s]}" for s in role["bullet_slots"]]
                out.append("")
        elif kind == "education":
            for item in section["items"]:
                out.append(
                    f"**{item['degree']} {item['field']}** — {item['institution']}, {item['year']}"
                )
                out += [f"- {texts[s]}" for s in item.get("slots", [])]
                out.append("")
        elif kind == "bullets":
            out += [f"- {texts[s]}" for s in section["slots"]]
            out.append("")
        else:  # skills
            out += [", ".join(section["skills"]) + ".", ""]
    return "\n".join(out).rstrip("\n") + "\n"


def render_jd(jd: dict[str, Any], texts: dict[str, str]) -> str:
    chunks: list[str] = []
    if jd["header_lines"]:
        chunks.append("\n".join(jd["header_lines"]))
    chunks += [texts[s] for s in jd["slots"]]
    return "\n\n".join(chunks) + "\n"


def pick_edit_target(text: str) -> str:
    """A distinctive run of words from ``text`` to use as an iteration edit target.

    The longest stretch between punctuation, cut to ten words. It is a substring of ``text`` (slots
    never hold a double space), and the runner needs it to survive generation, so it is as long as is
    safe and free of the commas a model reflows.
    """
    best = max((seg.strip() for seg in re.split(r"[,;:()]", text)), key=lambda s: len(s.split()))
    words = best.split()
    if len(words) < 5:
        raise ValueError(f"no stretch of five words without punctuation to edit in {text!r}")
    target = " ".join(words[:10])
    assert target in text
    return target


def render_expected(profile: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    """``expected.json`` as a dict: the ground truth the profile carries, plus the iteration scenarios."""
    expected: dict[str, Any] = {
        "candidate_name": profile["candidate"]["name"],
        **profile["expected"],
    }
    iteration = profile.get("iteration")
    if iteration is None:
        return expected
    if iteration["mode"] == "verbatim":
        expected["iteration_scenarios"] = iteration["scenarios"]
    else:
        target = pick_edit_target(texts[iteration["target_slot"]])
        expected["iteration_scenarios"] = [
            {
                "name": iteration["name"],
                "edit_target_substring": target,
                "edit_replacement": iteration["replacement"].format(target=target),
                "clarification_answers": {"iter1_q1": iteration["clarification_answer"]},
                "expected_iteration_themes": iteration["themes"],
            }
        ]
    expected["min_iteration_quality_score"] = iteration.get("min_score", 4)
    return expected


def _links() -> list[dict[str, Any]]:
    return []


def render_seed(profile: dict[str, Any], texts: dict[str, str]) -> dict[str, Any]:
    """``seed.json`` in the exporter's v1 shape. Every key the exporter writes is written, nulls included."""
    cand = profile["candidate"]
    slots = profile["slots"]
    experiences: list[dict[str, Any]] = []
    bullet_id = 300
    intro_id = 400
    roles = [r for sec in profile["sections"] if sec["kind"] == "experience" for r in sec["roles"]]
    for index, role in enumerate(roles):
        bullets = []
        for order, slot_id in enumerate(role["bullet_slots"]):
            bullet_id += 1
            bullets.append(
                {
                    "id": bullet_id,
                    "text": texts[slot_id],
                    "display_order": order,
                    "is_active": True,
                    "is_pending_review": False,
                    "source": "primary:resume.md",
                    "pattern_kind": None,
                    "has_outcome": bool(slots[slot_id]["has_outcome"]),
                    "tag_links": _links(),
                }
            )
        intros = []
        for order, slot_id in enumerate(role.get("intro_slots", [])):
            intro_id += 1
            intros.append(
                {
                    "id": intro_id,
                    "text": texts[slot_id],
                    "label": f"variant {order + 1}",
                    "display_order": order,
                    "is_active": True,
                    "is_pending_review": False,
                    "source": "manual",
                    "has_outcome": bool(slots[slot_id]["has_outcome"]),
                }
            )
        experiences.append(
            {
                "id": 101 + index,
                "company": role["company"],
                "location": role.get("location"),
                "start_date": role["start"],
                "end_date": role["end"],
                "display_order": index,
                "summary": None,
                "is_active": True,
                "titles": [
                    {
                        "id": 201 + index,
                        "title": role["title"],
                        "is_official": True,
                        "truthful_enough_to_use": True,
                        "is_pending_review": False,
                        "source": "official",
                        "tag_links": _links(),
                    }
                ],
                "bullets": bullets,
                "summary_items": intros,
            }
        )
    summary_items: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    educations: list[dict[str, Any]] = []
    for section in profile["sections"]:
        if section["kind"] == "summary":
            for order, slot_id in enumerate(section["slots"]):
                summary_items.append(
                    {
                        "id": 501 + order,
                        "text": texts[slot_id],
                        "label": "default" if order == 0 else f"variant {order + 1}",
                        "display_order": order,
                        "is_active": True,
                        "is_pending_review": False,
                        "source": "manual",
                        "has_outcome": bool(slots[slot_id]["has_outcome"]),
                        "tag_links": _links(),
                    }
                )
        elif section["kind"] == "education":
            for order, item in enumerate(section["items"]):
                educations.append(
                    {
                        "id": 701 + order,
                        "institution": item["institution"],
                        "degree": item["degree"],
                        "field": item["field"],
                        "start_date": None,
                        "end_date": item["year"],
                        "display_order": order,
                        "is_active": True,
                        "notes": None,
                    }
                )
    for order, skill in enumerate(profile["skills"]):
        skills.append(
            {
                "id": 601 + order,
                "name": skill["name"],
                "category": skill["category"],
                "proficiency": None,
                "years": None,
            }
        )
    skills.sort(key=lambda s: (s["name"], s["id"]))  # the exporter orders by name, then id
    return {
        "seed_schema_version": 1,
        "candidate_username": cand["username"],
        "candidate": {
            "username": cand["username"],
            "name": cand["name"],
            "email": cand["email"],
            "phone": cand["phone"],
            "linkedin_url": cand["linkedin"],
            "website_url": None,
            "notes": None,
            "profile_text": None,
        },
        "tags": [],
        "experiences": experiences,
        "summary_items": summary_items,
        "skills": skills,
        "educations": educations,
        "certifications": [],
    }


def render_fixtures(profile: dict[str, Any], prose: dict[str, Any]) -> dict[str, dict[str, str]]:
    """``{fixture directory name: {file name: content}}`` for every JD of the cell."""
    texts: dict[str, str] = prose["slots"]
    resume = render_resume(profile, texts)
    expected = canonical_json(render_expected(profile, texts))
    seed = canonical_json(render_seed(profile, texts))
    return {
        fixture_name(profile["cell"], jd["slug"]): {
            "resume.md": resume,
            "jd.txt": render_jd(jd, texts),
            "expected.json": expected,
            "seed.json": seed,
        }
        for jd in profile["jds"]
    }


# --------------------------------------------------------------------------------------------------
# Cell and suite files
# --------------------------------------------------------------------------------------------------


def write_cell(root: Path, profile: dict[str, Any], prose: dict[str, Any]) -> None:
    """Write a cell's two source files and re-render its fixtures. Refuses an unsound cell."""
    problems = validate_profile(profile) + check_prose(profile, prose)
    if problems:
        raise ValueError("cell is not sound:\n  " + "\n  ".join(problems))
    cell = profile["cell"]
    _write(root / "cells" / cell / "profile.json", canonical_json(profile))
    _write(root / "cells" / cell / "prose.json", canonical_json(prose))
    for name, files in render_fixtures(profile, prose).items():
        for filename, content in files.items():
            _write(root / "fixtures" / name / filename, content)


def load_cell(root: Path, cell: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = root / "cells" / cell
    return _read_json(base / "profile.json"), _read_json(base / "prose.json")


def cell_names(root: Path) -> list[str]:
    return (
        sorted(p.name for p in (root / "cells").iterdir() if p.is_dir())
        if (root / "cells").is_dir()
        else []
    )


def check_cell(root: Path, cell: str) -> list[str]:
    """Every way one cell can be wrong: shape, prose, and each derived file against a fresh render."""
    try:
        profile, prose = load_cell(root, cell)
    except (OSError, ValueError) as exc:
        return [f"{cell}: cannot read the source files ({exc})"]
    problems = validate_profile(profile)
    if profile.get("cell") != cell:
        problems.append(f"profile names cell {profile.get('cell')!r}, directory is {cell!r}")
    if problems:
        return [f"{cell}: {p}" for p in problems]
    problems = check_prose(profile, prose)
    provenance = prose.get("provenance", {})
    if provenance.get("kind") not in PROSE_KINDS:
        problems.append(f"provenance.kind {provenance.get('kind')!r} is not one of {PROSE_KINDS}")
    elif provenance["kind"] == "generated" and provenance.get("profile_sha256") != sha256_file(
        root / "cells" / cell / "profile.json"
    ):
        problems.append("the prose was written for a different profile (profile_sha256 differs)")
    if problems:
        return [f"{cell}: {p}" for p in problems]
    wanted = render_fixtures(profile, prose)
    for name, files in wanted.items():
        for filename, content in files.items():
            path = root / "fixtures" / name / filename
            if not path.is_file():
                problems.append(f"{name}/{filename} is missing")
            elif path.read_bytes() != content.encode("utf-8"):
                problems.append(f"{name}/{filename} differs from a fresh render")
    fixtures = root / "fixtures"
    prefix = f"{cell}--"
    present = {p.name for p in fixtures.iterdir() if p.is_dir()} if fixtures.is_dir() else set()
    for name in sorted(n for n in present if n.startswith(prefix) and n not in wanted):
        problems.append(f"{name} is a fixture no JD of this cell produces")
    return [f"{cell}: {p}" for p in problems]


def tracked_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for sub in ("facts", "cells", "fixtures"):
        base = root / sub
        if base.is_dir():
            for path in sorted(p for p in base.rglob("*") if p.is_file()):
                out[path.relative_to(root).as_posix()] = sha256_file(path)
    return out


def write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Stamp ``files`` from what is on disk and write ``manifest.json``."""
    manifest = {**manifest, "files": tracked_files(root)}
    _write(root / "manifest.json", canonical_json(manifest))
    return manifest


def load_manifest(root: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = _read_json(root / "manifest.json")
    return manifest


def ladder_for(manifest: dict[str, Any], profession: str, level: str) -> dict[str, Any]:
    """The rule for ``level`` in the family ``profession`` belongs to. Raises ``KeyError`` with the reason."""
    try:
        family = manifest["professions"][profession]["family"]
    except KeyError:
        raise KeyError(f"profession {profession!r} has no family in the manifest") from None
    try:
        rule: dict[str, Any] = manifest["families"][family]["levels"][level]
    except KeyError:
        raise KeyError(f"family {family!r} has no rule for level {level!r}") from None
    return rule


def _check_ladders(manifest: dict[str, Any]) -> list[str]:
    """Every way the manifest's families and its professions' family links can be wrong."""
    problems: list[str] = []
    families = manifest.get("families", {})
    if not families:
        problems.append("manifest has no families")
    for name, family in sorted(families.items()):
        levels = family.get("levels", {})
        if sorted(levels) != sorted(LEVELS):
            problems.append(
                f"family {name}: levels {sorted(levels)} must be exactly {sorted(LEVELS)}"
            )
        for level, rule in sorted(levels.items()):
            where = f"family {name}, level {level}"
            if rule.get("rule_source") not in ("authored", "sourced"):
                problems.append(f"{where}: rule_source must be authored or sourced")
            if not isinstance(rule.get("label"), str) or not rule["label"]:
                problems.append(f"{where}: label must be a non-empty string")
            years = rule.get("years")
            if not (
                isinstance(years, list)
                and len(years) == 2
                and all(isinstance(y, int) for y in years)
                and 0 <= years[0] <= years[1]
            ):
                problems.append(f"{where}: years must be [low, high] whole years, low <= high")
            elif years[1] * 12 < rule.get("roles", 0) * MIN_ROLE_MONTHS:
                problems.append(
                    f"{where}: {rule.get('roles')} roles of at least {MIN_ROLE_MONTHS} months do not fit in {years[1]} years"
                )
    for profession, row in sorted(manifest.get("professions", {}).items()):
        if row.get("family") not in families:
            problems.append(
                f"profession {profession}: family {row.get('family')!r} is not in the manifest"
            )
    return problems


def check_suite(root: Path, author_prompt_sha: dict[str, str] | None = None) -> list[str]:
    """Every way the suite can be wrong. ``author_prompt_sha`` maps a prompt version to its text's hash."""
    try:
        manifest = load_manifest(root)
    except (OSError, ValueError) as exc:
        return [f"manifest.json cannot be read ({exc})"]
    problems: list[str] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        problems.append(
            f"manifest schema {manifest.get('schema')!r}, this reader knows {MANIFEST_SCHEMA}"
        )
    if manifest.get("status") not in STATUSES:
        problems.append(f"manifest status {manifest.get('status')!r} is not one of {STATUSES}")
    problems += _check_ladders(manifest)
    cells = cell_names(root)
    failing: set[str] = set()
    for cell in cells:
        problems += check_cell(root, cell)
        try:
            profile, prose = load_cell(root, cell)
        except (OSError, ValueError):
            continue
        if profile.get("profession") not in manifest.get("professions", {}):
            problems.append(
                f"{cell}: profession {profile.get('profession')!r} is not in the manifest"
            )
        provenance = prose.get("provenance", {})
        if provenance.get("kind") == "generated":
            version = provenance.get("prompt_version")
            want = (author_prompt_sha or {}).get(version)
            recorded = manifest.get("author", {}).get("prompt_versions", {}).get(version)
            if recorded is None or provenance.get("prompt_sha256") != recorded:
                problems.append(
                    f"{cell}: prompt_version {version!r} is not recorded in the manifest with this hash"
                )
            if want is not None and recorded != want:
                problems.append(
                    f"{cell}: the manifest's hash for prompt {version!r} differs from the prompt text"
                )
        if not validate_profile(profile):
            for jd in profile["jds"]:
                for predicate in failing_predicates(profile):
                    failing.add(f"{fixture_name(cell, jd['slug'])}:{predicate}")
    waived = set(manifest.get("pilot_waivers", []))
    if manifest.get("status") == "frozen":
        if waived or failing:
            problems.append("a frozen suite has no waivers and no failing richness predicate")
    else:
        for item in sorted(failing - waived):
            problems.append(f"richness predicate fails and is not waived: {item}")
        for item in sorted(waived - failing):
            problems.append(f"stale waiver, the predicate holds: {item}")
    on_disk = tracked_files(root)
    recorded_files: dict[str, str] = manifest.get("files", {})
    for path in sorted(set(on_disk) - set(recorded_files)):
        problems.append(f"{path} is on disk but not in the manifest")
    for path in sorted(set(recorded_files) - set(on_disk)):
        problems.append(f"{path} is in the manifest but not on disk")
    for path in sorted(set(on_disk) & set(recorded_files)):
        if on_disk[path] != recorded_files[path]:
            problems.append(f"{path} changed since the manifest was written")
    fixture_dirs = (
        {p.name for p in (root / "fixtures").iterdir() if p.is_dir()}
        if (root / "fixtures").is_dir()
        else set()
    )
    for name in sorted(fixture_dirs):
        if not any(name.startswith(f"{c}--") for c in cells):
            problems.append(f"fixtures/{name} belongs to no cell")
    return problems


# --------------------------------------------------------------------------------------------------
# Converting an existing persona into a cell (the pilots)
# --------------------------------------------------------------------------------------------------


def _split_skills(line: str) -> list[str]:
    """Split on ', ' outside parentheses."""
    items: list[str] = []
    depth = 0
    current = ""
    index = 0
    while index < len(line):
        char = line[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0 and line[index + 1 : index + 2] == " ":
            items.append(current)
            current = ""
            index += 2
            continue
        current += char
        index += 1
    items.append(current)
    return items


def parse_resume(text: str) -> dict[str, Any]:
    """Read one of the existing personas' ``resume.md`` into a name, contact parts and ordered sections.

    Only the layout those files use is understood; anything else raises, because a converter that
    guesses would write a cell that does not render back to its source.
    """
    lines = text.split("\n")
    if not lines[0].startswith("# ") or len(lines) < 4:
        raise ValueError("a résumé starts with '# Name' and a contact line")
    contact = lines[2].split(" | ")
    if len(contact) != 3:
        raise ValueError(f"expected 'email | phone | linkedin', got {lines[2]!r}")
    blocks: list[tuple[str, list[str]]] = []
    for line in lines[3:]:
        if line.startswith("## "):
            blocks.append((line[3:], []))
        elif blocks:
            blocks[-1][1].append(line)
        elif line.strip():
            raise ValueError(f"text before the first section: {line!r}")
    sections: list[dict[str, Any]] = []
    for heading, body in blocks:
        body = list(body)
        while body and not body[-1].strip():
            body.pop()
        sections.append(_parse_section(heading, body))
    return {
        "name": lines[0][2:],
        "email": contact[0],
        "phone": contact[1],
        "linkedin": contact[2],
        "sections": sections,
    }


def _parse_section(heading: str, body: list[str]) -> dict[str, Any]:
    nonblank = [ln for ln in body if ln.strip()]
    if heading == "Summary":
        if len(nonblank) != 1:
            raise ValueError("a Summary is one paragraph on one line")
        return {"kind": "summary", "heading": heading, "texts": nonblank}
    if heading == "Experience":
        roles: list[dict[str, Any]] = []
        for line in body:
            if line.startswith("### "):
                title, sep, company = line[4:].partition(" — ")
                if not sep:
                    raise ValueError(f"role heading without ' — ': {line!r}")
                roles.append(
                    {"title": title, "company": company, "start": None, "end": None, "texts": []}
                )
            elif (
                line.startswith("*") and line.endswith("*") and roles and roles[-1]["start"] is None
            ):
                start, sep, end = line[1:-1].partition(" – ")
                if not sep:
                    raise ValueError(f"dates without ' – ': {line!r}")
                roles[-1]["start"], roles[-1]["end"] = month_iso(start), month_iso(end)
            elif line.startswith("- ") and roles:
                roles[-1]["texts"].append(line[2:])
            elif line.strip():
                raise ValueError(f"unexpected line in Experience: {line!r}")
        return {"kind": "experience", "heading": heading, "roles": roles}
    if heading == "Education":
        items: list[dict[str, Any]] = []
        for line in nonblank:
            if line.startswith("**"):
                match = re.fullmatch(r"\*\*(\S+) (.+?)\*\* — (.+), (\d{4})", line)
                if match is None:
                    raise ValueError(f"education line not understood: {line!r}")
                items.append(
                    {
                        "degree": match.group(1),
                        "field": match.group(2),
                        "institution": match.group(3),
                        "year": match.group(4),
                        "texts": [],
                    }
                )
            elif line.startswith("- ") and items:
                items[-1]["texts"].append(line[2:])
            else:
                raise ValueError(f"unexpected line in Education: {line!r}")
        return {"kind": "education", "heading": heading, "items": items}
    if heading == "Skills":
        if len(nonblank) != 1 or not nonblank[0].endswith("."):
            raise ValueError("Skills is one line ending in a full stop")
        return {"kind": "skills", "heading": heading, "skills": _split_skills(nonblank[0][:-1])}
    if all(ln.startswith("- ") for ln in nonblank):
        return {"kind": "bullets", "heading": heading, "texts": [ln[2:] for ln in nonblank]}
    raise ValueError(f"section {heading!r} is not understood")


def _converted_slot(kind: str, text: str) -> dict[str, Any]:
    words = len(text.split())
    return {
        "kind": kind,
        "brief": "converted from an existing persona; not generated",
        "must_include": [],
        "allowed_numbers": sorted(set(re.findall(r"\d+", text))),
        "min_words": 1,
        "max_words": max(words, 1),
        "has_outcome": bool(re.search(r"\d", text)),
    }


def profile_from_persona(
    persona_dir: Path, *, cell: str, profession: str, level: str, industry: str, username: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Turn ``evals/fixtures/synthetic/<persona>`` into a cell's ``(profile, prose)``.

    The persona's text becomes the prose, unchanged (``kind: converted``). The cell must render back to
    the persona's ``resume.md`` and ``jd.txt`` byte for byte, or this raises: a converted pilot is the
    same text, not a rewrite of it. The expected ground truth is copied as it is.
    """
    resume_text = (persona_dir / "resume.md").read_text(encoding="utf-8")
    jd_text = (persona_dir / "jd.txt").read_text(encoding="utf-8")
    expected = _read_json(persona_dir / "expected.json")
    parsed = parse_resume(resume_text)
    if parsed["name"] != expected["candidate_name"]:
        raise ValueError(f"résumé name {parsed['name']!r} differs from expected.candidate_name")
    slots: dict[str, dict[str, Any]] = {}
    texts: dict[str, str] = {}

    def add(slot_id: str, kind: str, text: str) -> str:
        slots[slot_id] = _converted_slot(kind, text)
        texts[slot_id] = text
        return slot_id

    sections: list[dict[str, Any]] = []
    for index, sec in enumerate(parsed["sections"]):
        kind = sec["kind"]
        if kind == "summary":
            sections.append(
                {
                    "kind": kind,
                    "heading": sec["heading"],
                    "slots": [add("summary.1", "summary", sec["texts"][0])],
                }
            )
        elif kind == "experience":
            roles = []
            for r_index, role in enumerate(sec["roles"], start=1):
                bullet_slots = [
                    add(f"r{r_index}.b{b}", "bullet", t)
                    for b, t in enumerate(role["texts"], start=1)
                ]
                roles.append(
                    {
                        "title": role["title"],
                        "company": role["company"],
                        "start": role["start"],
                        "end": role["end"],
                        "location": None,
                        "bullet_slots": bullet_slots,
                        "intro_slots": [],
                    }
                )
            sections.append({"kind": kind, "heading": sec["heading"], "roles": roles})
        elif kind == "education":
            items = []
            for e_index, item in enumerate(sec["items"], start=1):
                item_slots = [
                    add(f"e{e_index}.b{b}", "bullet", t)
                    for b, t in enumerate(item["texts"], start=1)
                ]
                items.append(
                    {k: item[k] for k in ("degree", "field", "institution", "year")}
                    | {"slots": item_slots}
                )
            sections.append({"kind": kind, "heading": sec["heading"], "items": items})
        elif kind == "bullets":
            sections.append(
                {
                    "kind": kind,
                    "heading": sec["heading"],
                    "slots": [
                        add(f"x{index}.b{b}", "bullet", t)
                        for b, t in enumerate(sec["texts"], start=1)
                    ],
                }
            )
        else:
            sections.append({"kind": kind, "heading": sec["heading"], "skills": sec["skills"]})
    jd_slot = add(f"jd.{industry}.full", "jd", jd_text.removesuffix("\n"))
    skills: list[str] = next((s["skills"] for s in sections if s["kind"] == "skills"), [])
    ground_truth = {
        k: v
        for k, v in expected.items()
        if k not in ("candidate_name", "iteration_scenarios", "min_iteration_quality_score")
    }
    iteration: dict[str, Any] | None = None
    if "iteration_scenarios" in expected:
        iteration = {
            "mode": "verbatim",
            "scenarios": expected["iteration_scenarios"],
            "min_score": expected.get("min_iteration_quality_score", 4),
        }
    profile: dict[str, Any] = {
        "schema": SCHEMA,
        "cell": cell,
        "profession": profession,
        "level": level,
        "cell_seed": 0,
        "candidate": {
            "name": parsed["name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "linkedin": parsed["linkedin"],
            "username": username,
        },
        "sections": sections,
        "skills": [{"name": s, "category": "converted"} for s in skills],
        "slots": slots,
        "jds": [{"slug": industry, "header_lines": [], "slots": [jd_slot]}],
        "expected": ground_truth,
        "iteration": iteration,
        "clarifications": [],
        "refinement_notes": [],
    }
    prose = {
        "schema": SCHEMA,
        "cell": cell,
        "provenance": {
            "kind": "converted",
            "persona": persona_dir.name,
            "source_sha256": {
                n: sha256_file(persona_dir / n) for n in ("resume.md", "jd.txt", "expected.json")
            },
        },
        "slots": texts,
    }
    rendered = render_fixtures(profile, prose)[fixture_name(cell, industry)]
    if rendered["resume.md"] != resume_text:
        raise ValueError(f"{persona_dir.name}: the cell does not render back to resume.md")
    if rendered["jd.txt"] != jd_text:
        raise ValueError(f"{persona_dir.name}: the cell does not render back to jd.txt")
    return profile, prose


# --------------------------------------------------------------------------------------------------
# Building a profile from facts and the ladder
# --------------------------------------------------------------------------------------------------


def _hash_int(seed: int, label: str) -> int:
    """A stable integer from ``(seed, label)``. Not `random`: its helpers are not stable across versions."""
    return int.from_bytes(hashlib.sha256(f"{seed}:{label}".encode()).digest()[:8], "big")


def _pick(seq: tuple[str, ...] | list[str], seed: int, label: str) -> str:
    return seq[_hash_int(seed, label) % len(seq)]


def _sample(seq: list[str], count: int, seed: int, label: str) -> list[str]:
    """``count`` distinct items, ordered by a per-item hash."""
    ranked = sorted(seq, key=lambda item: _hash_int(seed, f"{label}:{item}"))
    return ranked[:count]


def _tenures(seed: int, ladder: dict[str, Any]) -> list[int]:
    """Each role's length in months, newest first. They sum to a career length inside ``ladder['years']``.

    The total is drawn from the ladder's window (never shorter than ``MIN_ROLE_MONTHS`` a role), so the level
    controls career length; the total is then split by hashed weights, every role at least ``MIN_ROLE_MONTHS``.
    """
    roles = int(ladder["roles"])
    low_years, high_years = ladder["years"]
    floor = roles * MIN_ROLE_MONTHS
    low = max(low_years * 12, floor)
    high = max(high_years * 12, low)
    total = low + _hash_int(seed, "tenure:total") % (high - low + 1)
    weights = [1 + _hash_int(seed, f"tenure:w{i}") % 8 for i in range(roles)]
    spare = total - floor
    shares = [spare * w // sum(weights) for w in weights]
    shares[0] += spare - sum(shares)  # the integer remainder goes to the newest role
    return [MIN_ROLE_MONTHS + share for share in shares]


def cell_seed_for(profession: str, level: str) -> int:
    """The integer every pseudo-random choice in a cell derives from. A function of the cell's name only."""
    return _hash_int(0, f"{SUITE}:{profession}:{level}") % (2**31)


def _slot(
    kind: str,
    brief: str,
    *,
    must: list[str] | None = None,
    numbers: list[str] | None = None,
    lo: int,
    hi: int,
    outcome: bool = False,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "brief": brief,
        "must_include": must or [],
        "allowed_numbers": sorted(set(numbers or [])),
        "min_words": lo,
        "max_words": hi,
        "has_outcome": outcome,
    }


def build_profile(
    facts: dict[str, Any], ladder: dict[str, Any], level: str, industries: list[str] | None = None
) -> dict[str, Any]:
    """A profile for ``facts['profession']`` at ``level``, with no prose. A pure function of its inputs.

    ``facts`` carries the profession's O*NET-derived skills, per-level titles, work themes, education
    and industries. ``ladder`` is the manifest's rule for the level. Every choice derives from
    `cell_seed_for`, so the same inputs write the same bytes. What the model is asked to write is the
    slot briefs; everything else (names, employers, dates, figures, skills, traps, JD requirements) is
    decided here.
    """
    profession = facts["profession"]
    seed = cell_seed_for(profession, level)
    cell = f"{profession}-{level}"
    name = f"{_pick(_FIRST_NAMES, seed, 'first')} {_pick(_LAST_NAMES, seed, 'last')}"
    handle = name.lower().replace(" ", ".")
    candidate = {
        "name": name,
        "email": f"{handle}@example.com",
        "phone": f"(555) 010-{_hash_int(seed, 'phone') % 10000:04d}",
        "linkedin": f"linkedin.com/in/example-{name.split()[0].lower()}-{cell}",
        "username": "gold_" + cell.replace("-", "_"),
    }
    slots: dict[str, dict[str, Any]] = {}
    skill_names = _sample(
        [s["name"] for s in facts["skills"]], ladder["skill_count"], seed, "skills"
    )
    category = {s["name"]: s["category"] for s in facts["skills"]}
    themes = list(facts["work_themes"])
    employers = _sample(list(_EMPLOYERS), ladder["roles"], seed, "employers")
    # Dates run back from ASOF: the newest role is current, each older one ends where the next began.
    titles = [
        facts["titles"][LEVELS[max(LEVELS.index(level) - i, 0)]] for i in range(ladder["roles"])
    ]
    roles: list[dict[str, Any]] = []
    end: str | None = None
    cursor = _months(ASOF)
    total_months = 0
    for index, duration in enumerate(_tenures(seed, ladder)):
        start_months = cursor - duration
        total_months += duration
        bullet_slots: list[str] = []
        for b in range(1, ladder["bullets_per_role"] + 1):
            theme = _pick(themes, seed, f"theme:{index}:{b}")
            skill = _pick(skill_names, seed, f"skill:{index}:{b}")
            outcome = b % 2 == 1
            figure = str(10 + 5 * (_hash_int(seed, f"figure:{index}:{b}") % 10))
            slot_id = f"r{index + 1}.b{b}"
            if outcome:
                brief = f"One résumé bullet for a {titles[index]} at {employers[index]}: {theme}, using {skill}. State a measured result of {figure} percent."
                slots[slot_id] = _slot(
                    "bullet",
                    brief,
                    must=[skill, figure],
                    numbers=[figure],
                    lo=10,
                    hi=40,
                    outcome=True,
                )
            else:
                brief = f"One résumé bullet for a {titles[index]} at {employers[index]}: {theme}, using {skill}. Include no number."
                slots[slot_id] = _slot("bullet", brief, must=[skill], lo=8, hi=40)
            bullet_slots.append(slot_id)
        intro_slots: list[str] = []
        for v in range(1, ladder["intro_variants"] + 1):
            slot_id = f"r{index + 1}.i{v}"
            theme = _pick(themes, seed, f"intro:{index}:{v}")
            slots[slot_id] = _slot(
                "intro",
                f"Variant {v} of a one-sentence role introduction for a {titles[index]} at {employers[index]}, about {theme}. Include no number.",
                lo=8,
                hi=35,
            )
            intro_slots.append(slot_id)
        roles.append(
            {
                "title": titles[index],
                "company": employers[index],
                "start": _iso(start_months),
                "end": end,
                "location": None,
                "bullet_slots": bullet_slots,
                "intro_slots": intro_slots,
            }
        )
        end = _iso(start_months)
        cursor = start_months
    years = max(1, round(total_months / 12))
    summary_slots: list[str] = []
    for v in range(1, ladder["summary_variants"] + 1):
        slot_id = f"summary.{v}"
        top = ", ".join(skill_names[:3])
        slots[slot_id] = _slot(
            "summary",
            f"Variant {v} of a two-sentence résumé summary for a {ladder.get('label', level)}-level {facts['display']} professional with about {years} years of experience, scope: {ladder['scope']}. Mention {top}.",
            must=skill_names[:3],
            numbers=[str(years)],
            lo=15,
            hi=60,
        )
        summary_slots.append(slot_id)
    oldest_year = roles[-1]["start"][:4]
    education = {
        "degree": facts["education"]["degree"],
        "field": facts["education"]["field"],
        "institution": _pick(_SCHOOLS, seed, "school"),
        "year": oldest_year,
        "slots": [],
    }
    sections = [
        {"kind": "summary", "heading": "Summary", "slots": summary_slots},
        {"kind": "experience", "heading": "Experience", "roles": roles},
        {"kind": "education", "heading": "Education", "items": [education]},
        {"kind": "skills", "heading": "Skills", "skills": skill_names},
    ]
    # JDs: each asks for four of the candidate's skills and two it does not have.
    absent_pool = [s["name"] for s in facts["skills"] if s["name"] not in skill_names]
    chosen = industries or [i["slug"] for i in facts["industries"]][:2]
    industry_by_slug = {i["slug"]: i for i in facts["industries"]}
    jds: list[dict[str, Any]] = []
    present_by_jd: list[list[str]] = []
    absent_by_jd: list[list[str]] = []
    for slug in chosen:
        industry = industry_by_slug[slug]
        present = _sample(skill_names, min(4, len(skill_names)), seed, f"jd-present:{slug}")
        absent = _sample(absent_pool, min(2, len(absent_pool)), seed, f"jd-absent:{slug}")
        present_by_jd.append(present)
        absent_by_jd.append(absent)
        title = facts["titles"][level]
        jd_slots_for = [f"jd.{slug}.about", f"jd.{slug}.duties", f"jd.{slug}.needs"]
        slots[jd_slots_for[0]] = _slot(
            "jd",
            f"The 'About the role' paragraph of a job description for a {title} at {industry['company']}, {industry['phrase']}. Include no number.",
            lo=25,
            hi=90,
        )
        slots[jd_slots_for[1]] = _slot(
            "jd",
            f"A 'What you'll do' heading and four to six bullet lines for a {title}, about {', '.join(_sample(themes, 3, seed, f'duties:{slug}'))}. Include no number.",
            lo=40,
            hi=160,
        )
        slots[jd_slots_for[2]] = _slot(
            "jd",
            f"A 'What we're looking for' heading and four to six bullet lines. Require {', '.join(present + absent)}, and {years} or more years of experience.",
            must=present + absent,
            numbers=[str(years)],
            lo=30,
            hi=160,
        )
        jds.append(
            {
                "slug": slug,
                "header_lines": [title, f"{industry['company']} — Remote (US)"],
                "slots": jd_slots_for,
            }
        )
    absent_all = sorted({s for group in absent_by_jd for s in group})
    present_all = [s for group in present_by_jd for s in group]
    must_keywords = sorted({s.lower() for s in present_all})[:6]
    traps = [re.escape(s) for s in absent_all] + list(GENERIC_TRAPS)
    target_slot = "r1.b2" if "r1.b2" in slots else roles[0]["bullet_slots"][0]
    profile: dict[str, Any] = {
        "schema": SCHEMA,
        "cell": cell,
        "profession": profession,
        "level": level,
        "cell_seed": seed,
        "candidate": candidate,
        "sections": sections,
        "skills": [{"name": s, "category": category[s]} for s in skill_names],
        "slots": slots,
        "jds": jds,
        "expected": {
            "must_keywords": must_keywords,
            "forbidden_inventions": traps,
            "min_grounding_score": 4,
            "min_keyword_coverage_score": 3,
            "min_ats_format_score": 4,
            "min_tone_score": 3,
            "min_clarification_quality_score": 4,
            "expected_clarification_themes": {
                "experience_probes": [
                    f"any exposure to {s}, in work or side projects" for s in absent_all
                ],
                "scope_probes": [
                    f"{roles[0]['title']} at {roles[0]['company']}: sole owner or team member?"
                ],
            },
            "notes": f"{level}-level {facts['display']}. The profile has no {', '.join(absent_all)}; generation must not claim them.",
        },
        "iteration": {
            "mode": "derived",
            "name": "user_typed_scope",
            "target_slot": target_slot,
            "replacement": "{target}, " + ladder["scope"],
            "clarification_answer": f"Yes. {ladder['scope'].capitalize()}.",
            "themes": {
                "iteration_probes": [
                    "follow up on the just-typed scope: how large, and who else was involved"
                ],
                "experience_probes": [
                    f"{absent_all[0]} exposure not yet covered by prior clarifications"
                ]
                if absent_all
                else [],
                "scope_probes": ["ownership versus team contribution if not yet covered"],
            },
            "min_score": 4,
        },
        "clarifications": [
            {
                "question": f"Did you use {absent_all[0] if absent_all else skill_names[0]} on this role?",
                "answer": "Yes, in a limited way, on one project.",
            }
        ],
        "refinement_notes": [
            {"note": f"Mention {skill_names[0]} in the first bullet.", "in_scope": True},
            {"note": "Say that I led a team of fifty engineers.", "in_scope": False},
        ],
    }
    return profile


# --------------------------------------------------------------------------------------------------
# Richness predicates and reachability
# --------------------------------------------------------------------------------------------------


def _roles(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for sec in profile["sections"] if sec["kind"] == "experience" for r in sec["roles"]]


def _has_summary_variants(profile: dict[str, Any]) -> bool:
    return any(len(sec["slots"]) >= 2 for sec in profile["sections"] if sec["kind"] == "summary")


def _has_skills(profile: dict[str, Any]) -> bool:
    return len(profile["skills"]) >= 2


def _has_role_intros(profile: dict[str, Any]) -> bool:
    return any(len(r.get("intro_slots", [])) >= 2 for r in _roles(profile))


def _has_refinement_notes(profile: dict[str, Any]) -> bool:
    notes = profile.get("refinement_notes", [])
    return any(n["in_scope"] for n in notes) and any(not n["in_scope"] for n in notes)


def _has_clarifications(profile: dict[str, Any]) -> bool:
    return bool(profile.get("clarifications"))


def _has_bullets(profile: dict[str, Any]) -> bool:
    return any(r["bullet_slots"] for r in _roles(profile))


#: Predicates a cell must satisfy for the call kinds that need an input the dataset has to hold. The
#: names are what a pilot waiver cites. Each is the staging rule of the route that reaches the kind
#: (see `REACHABILITY`), checked here statically because `run_suite` never reaches that route.
PREDICATES: dict[str, Callable[[dict[str, Any]], bool]] = {
    "summary_variants": _has_summary_variants,
    "skills": _has_skills,
    "role_intro_variants": _has_role_intros,
    "refinement_notes": _has_refinement_notes,
    "clarifications": _has_clarifications,
    "bullets": _has_bullets,
}


def failing_predicates(profile: dict[str, Any]) -> list[str]:
    return sorted(name for name, check in PREDICATES.items() if not check(profile))


RUN_SUITE = "run_suite"
STATIC = "static"
INDEPENDENT = "independent"
EXEMPT = "exempt"

#: Every call kind and how the golden set reaches it. ``run_suite``: fired by the runner (the optional
#: predicate is what the cell must hold for it to fire). ``static``: reached by a route the runner does
#: not call, so the cell is checked to hold the input that route stages. ``independent``: the input is
#: not a dataset cell. ``exempt``: the dataset tooling's own call. `tests/test_golden_reachability.py`
#: ties the keys to the catalog both ways.
REACHABILITY: dict[str, tuple[str, str | None]] = {
    "analyze_extraction": (RUN_SUITE, None),
    "analyze_synthesis": (RUN_SUITE, None),
    "clarify": (RUN_SUITE, None),
    "iterate_clarify": (RUN_SUITE, None),
    "generate": (RUN_SUITE, None),
    "generate_cover_letter": (RUN_SUITE, None),
    "recommend": (RUN_SUITE, "bullets"),
    "recommend_summary": (RUN_SUITE, "summary_variants"),
    "judge_grade": (RUN_SUITE, None),
    "judge_distinctiveness": (RUN_SUITE, None),
    "recommend_skill": (STATIC, "skills"),
    "suggest_skill": (STATIC, "skills"),
    "suggest_skill_from_corpus": (STATIC, "skills"),
    "recommend_experience_summary": (STATIC, "role_intro_variants"),
    "draft_summary": (STATIC, "bullets"),
    "draft_gap_fill": (STATIC, "bullets"),
    "draft_experience_summary": (STATIC, "bullets"),
    "draft_surgical_refinement": (STATIC, "refinement_notes"),
    "check_refinement_scope": (STATIC, "refinement_notes"),
    "critique_proposal": (STATIC, "bullets"),
    "promote_clarification_to_bullet": (STATIC, "clarifications"),
    "extract_experiences": (STATIC, "bullets"),
    "avatar_answer": (INDEPENDENT, None),
    "dataset_author": (EXEMPT, None),
}


def main(argv: list[str] | None = None) -> int:
    """``python -m evals.golden_set check [--root DIR]`` and ``manifest [--root DIR]`` (re-stamp ``files``)."""
    ap = argparse.ArgumentParser(prog="python -m evals.golden_set")
    ap.add_argument("command", choices=("check", "manifest"))
    ap.add_argument("--root", type=Path, default=SUITE_DIR)
    args = ap.parse_args(argv)
    if args.command == "manifest":
        write_manifest(args.root, load_manifest(args.root))
        print(f"golden_set: wrote {args.root / 'manifest.json'}")
        return 0
    problems = check_suite(args.root)
    for problem in problems:
        print(f"golden_set: {problem}", file=sys.stderr)
    print(f"golden_set: {'FAILED' if problems else 'OK'} ({len(cell_names(args.root))} cells)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
