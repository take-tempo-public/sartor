"""Item 182: the eval catalog and its gate (eval redesign step 2).

`evals/catalog/<call>.toml` has one entry per LLM call kind. This file is the gate that keeps the
catalog true, inside `python -m scripts.gate`:

- the catalog's file names are exactly the `call_kind="<literal>"` keywords in the production source
  (the scan `tests/test_call_kind_telemetry.py` pins to `EXPECTED_CALL_KINDS`), both directions;
- for every call site, the model pin and the system prompt the call really uses, read from the AST
  with `_call_llm`'s defaults applied, agree with the entry. A site this reader cannot read FAILS the
  gate instead of being skipped, so a new call shape cannot slip past it;
- a covered entry names cases and rubrics that exist, a pending entry names a work item that exists,
  an exempt entry carries a reason and an approval;
- the loader is lazy (`names()` parses nothing, `load()` parses one file) and nothing stored is a float.

Stated limits (charter C-0): the gate checks that the catalog agrees with the source, not that an eval
of a covered call is any good; `lean_why` is authored prose; and a call made through a wrapper that is
not in `_ROUTED` is refused here rather than followed.
"""

from __future__ import annotations

import ast
import functools
import importlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

import analyzer
import hardening
from evals import eval_catalog as cat
from evals import runner
from tests._repo_files import REPO_ROOT, repo_files

# Directory parts that take a .py file out of the production scan: the same set as
# tests/test_call_kind_telemetry.py's `_SCAN_EXCLUDE_PARTS`.
_SCAN_EXCLUDE_PARTS = frozenset(
    {"tests", ".venv", "venv", ".git", "build", "dist", "__pycache__", "versions"}
)

# The callees a `call_kind=` literal is passed to. Their defaults are the ones this gate applies when a
# site omits `model=` (analyzer.py `_call_llm_streaming`: `model or SONNET_MODEL`) or `system_prompt=`
# (`system_prompt or _resolve_system_prompt("SYSTEM_PROMPT")`). Any other callee is refused: the gate
# does not know its defaults.
_ROUTED = frozenset(
    {
        "_parse_or_retry",
        "_parse_or_retry_streaming",
        "_call_llm",
        "_call_llm_streaming",
        "_judge_create",
    }
)

_ITEMS_DIR = REPO_ROOT / "docs" / "dev" / "work" / "items"

# Where a `<suite>/<name>` case lives. Only committed suites resolve: `real` fixtures are gitignored.
_SUITE_DIRS = {
    "synthetic": runner.FIXTURES_DIR / "synthetic",
    "anchor-v1": runner.ANCHOR_DIR / "fixtures",
}


class GateCannotRead(AssertionError):
    """A call site is in a shape this gate does not understand; teach it, do not skip it."""


@dataclass(frozen=True)
class Site:
    call: str
    where: str
    pin: str
    prompt: str


# ---------- reading call sites out of the source ---------------------------------------------


def _module_of(rel: str) -> str:
    return Path(rel).with_suffix("").as_posix().replace("/", ".")


def _callee(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ast.unparse(func)


def _pin(kws: dict[str, ast.expr], where: str) -> str:
    node = kws.get("model")
    if node is None:
        return "SONNET_MODEL"
    if isinstance(node, ast.Name) and node.id in cat.PINS:
        return node.id
    raise GateCannotRead(
        f"{where}: model={ast.unparse(node)!r} is not one of the pins {cat.PINS}; "
        f"teach tests/test_eval_catalog.py this shape before adding the call"
    )


def _prompt(kws: dict[str, ast.expr], module: str, where: str) -> str:
    system_prompt, system = kws.get("system_prompt"), kws.get("system")
    if system_prompt is not None and system is not None:
        raise GateCannotRead(f"{where}: passes both system_prompt= and system=")
    if system_prompt is None and system is None:
        return "analyzer.SYSTEM_PROMPT"
    if system_prompt is not None:
        if (
            isinstance(system_prompt, ast.Call)
            and isinstance(system_prompt.func, ast.Name)
            and system_prompt.func.id == "_resolve_system_prompt"
            and len(system_prompt.args) == 1
            and isinstance(system_prompt.args[0], ast.Constant)
            and isinstance(system_prompt.args[0].value, str)
        ):
            return f"analyzer.{system_prompt.args[0].value}"
        if isinstance(system_prompt, ast.Name):
            return f"{module}.{system_prompt.id}"
        raise GateCannotRead(
            f"{where}: system_prompt={ast.unparse(system_prompt)!r} is neither a constant nor "
            f'_resolve_system_prompt("CONSTANT"); teach tests/test_eval_catalog.py this shape'
        )
    assert (
        system is not None
    )  # both-None returned above; system_prompt-is-not-None returned or raised
    if isinstance(system, ast.Constant) and isinstance(system.value, str):
        return f"inline:{module}"
    raise GateCannotRead(f"{where}: system={ast.unparse(system)!r} is not a string literal")


def sites_in(tree: ast.AST, rel: str) -> list[Site]:
    """Every `call_kind="<literal>"` call in one module AST, with the pin and prompt it really uses."""
    module = _module_of(rel)
    found: list[Site] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kws = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        kind = kws.get("call_kind")
        if not (isinstance(kind, ast.Constant) and isinstance(kind.value, str)):
            continue
        where = f"{rel}:{node.lineno}"
        callee = _callee(node)
        if callee not in _ROUTED:
            raise GateCannotRead(
                f"{where}: call_kind={kind.value!r} is passed to {callee}(), which this gate "
                f"does not know the defaults of; add it to _ROUTED with its defaults"
            )
        found.append(Site(kind.value, where, _pin(kws, where), _prompt(kws, module, where)))
    return found


@functools.cache
def production_sites() -> tuple[Site, ...]:
    """Every call site in the repo's production Python. One pass; a file with no `call_kind` is not parsed."""
    found: list[Site] = []
    for path in repo_files(".py", root=REPO_ROOT):
        rel_path = path.relative_to(REPO_ROOT)
        if any(part in _SCAN_EXCLUDE_PARTS for part in rel_path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if "call_kind" not in text:
            continue
        found.extend(sites_in(ast.parse(text, filename=str(path)), rel_path.as_posix()))
    return tuple(found)


def mismatches(entry: cat.CatalogEntry, site: Site) -> list[str]:
    problems = []
    if entry.model_pin != site.pin:
        problems.append(
            f"{site.where}: {site.call} uses {site.pin} but evals/catalog/{site.call}.toml says {entry.model_pin}"
        )
    if entry.prompt != site.prompt:
        problems.append(
            f"{site.where}: {site.call} uses {site.prompt} but evals/catalog/{site.call}.toml says {entry.prompt}"
        )
    return problems


# ---------- the gate ---------------------------------------------------------------------------


def test_catalog_has_an_entry_for_every_call_kind_and_no_other():
    found = {site.call for site in production_sites()}
    have = set(cat.names())
    missing, stale = sorted(found - have), sorted(have - found)
    assert not missing, (
        f"call kind(s) with no catalog entry: {missing}. Add evals/catalog/<call>.toml "
        f'(status "pending" with the work item that will build the eval is a complete answer).'
    )
    assert not stale, f"catalog entries for call kinds no longer in the source: {stale}"


def test_every_entry_loads_and_validates():
    entries = cat.load_all()
    assert set(entries) == set(cat.names())
    assert len(entries) >= 23


def test_each_call_site_agrees_with_its_entry():
    entries = cat.load_all()
    problems = [
        p
        for site in production_sites()
        if site.call in entries
        for p in mismatches(entries[site.call], site)
    ]
    assert not problems, "\n".join(problems)


def test_prompt_constants_resolve_to_text():
    for entry in cat.load_all().values():
        if entry.prompt.startswith("inline:"):
            continue
        module, _, const = entry.prompt.rpartition(".")
        text = getattr(importlib.import_module(module), const, None)
        assert isinstance(text, str) and text.strip(), (
            f"{entry.call}: {entry.prompt} is not prompt text"
        )


def _pin_model(pin: str) -> str:
    return {
        "SONNET_MODEL": analyzer.SONNET_MODEL,
        "HAIKU_MODEL": analyzer.HAIKU_MODEL,
        "JUDGE_MODEL": runner.JUDGE_MODEL,
    }[pin]


def test_every_pin_resolves_to_a_priced_model():
    for entry in cat.load_all().values():
        model = _pin_model(entry.model_pin)
        assert model in hardening.MODEL_PRICING, f"{entry.call}: {model} has no MODEL_PRICING entry"


def test_covered_entries_name_real_cases_and_rubrics():
    covered = [e for e in cat.load_all().values() if e.status == "covered"]
    assert covered
    for entry in covered:
        for case in entry.cases:
            suite, _, name = case.partition("/")
            base = _SUITE_DIRS.get(suite)
            assert base is not None, (
                f"{entry.call}: case {case!r} names suite {suite!r}, which this gate cannot resolve "
                f"(committed suites: {sorted(_SUITE_DIRS)})"
            )
            assert (base / name).is_dir(), f"{entry.call}: no fixture directory for case {case!r}"
        for rubric in entry.rubrics:
            assert (runner.RUBRICS_DIR / f"{rubric}.md").is_file(), (
                f"{entry.call}: no rubric {rubric!r}"
            )
        if "iteration_quality" in entry.rubrics:
            for case in entry.cases:
                suite, _, name = case.partition("/")
                expected = json.loads(
                    (_SUITE_DIRS[suite] / name / "expected.json").read_text("utf-8")
                )
                assert expected.get("iteration_scenarios"), (
                    f"{entry.call}: iteration_quality only runs on fixtures with iteration_scenarios; "
                    f"{case} has none"
                )


def test_pending_entries_name_an_existing_work_item():
    pending = [e for e in cat.load_all().values() if e.status == "pending"]
    assert pending
    for entry in pending:
        assert list(_ITEMS_DIR.glob(f"{entry.pending_on:04d}-*.md")), (
            f"{entry.call}: pending_on = {entry.pending_on} but there is no such work item"
        )


def test_costs_file_holds_integer_means_for_catalog_kinds_on_their_current_pin():
    costs = cat.read_costs()  # refuses a float, a negative count or a missing field
    assert costs, (
        "evals/catalog/costs.json is empty; run `python -m evals.eval_catalog measure --write`"
    )
    entries = cat.load_all()
    assert set(costs) <= set(entries), (
        f"costs for unknown kinds: {sorted(set(costs) - set(entries))}"
    )
    stale = [
        call for call, row in costs.items() if row["model"] != _pin_model(entries[call].model_pin)
    ]
    assert not stale, (
        f"costs measured on a model that is no longer the pin for {stale}; "
        f"re-run `python -m evals.eval_catalog measure --write`"
    )


# ---------- laziness (charter C-13) ------------------------------------------------------------


def test_names_parses_nothing_and_load_parses_exactly_one_file(monkeypatch):
    parsed: list[str] = []
    real = cat._read_toml

    def counting(path):
        parsed.append(path.name)
        return real(path)

    monkeypatch.setattr(cat, "_read_toml", counting)
    assert len(cat.names()) >= 23
    assert parsed == []
    cat.load("clarify")
    assert parsed == ["clarify.toml"]


def test_load_refuses_a_name_that_is_not_a_call_kind():
    for bad in ("../costs", "Clarify", "a/b", "", "clarify.toml"):
        with pytest.raises(cat.CatalogError):
            cat.load(bad)


# ---------- the scan can fail (control arms) ---------------------------------------------------


def test_the_reader_derives_pin_and_prompt_from_each_call_shape():
    tree = ast.parse(
        "_parse_or_retry(c, p, call_kind='a', model=HAIKU_MODEL, "
        "system_prompt=_resolve_system_prompt('A_SYSTEM_PROMPT'))\n"
        "_call_llm_streaming(c, p, call_kind='b', model=HAIKU_MODEL, system_prompt=B_PROMPT)\n"
        "_parse_or_retry(c, p, call_kind='c')\n"
        "_judge_create(c, call_kind='d', model=JUDGE_MODEL, system='grade it')\n"
    )
    by_call = {s.call: s for s in sites_in(tree, "onboarding/thing.py")}
    assert (by_call["a"].pin, by_call["a"].prompt) == ("HAIKU_MODEL", "analyzer.A_SYSTEM_PROMPT")
    assert (by_call["b"].pin, by_call["b"].prompt) == ("HAIKU_MODEL", "onboarding.thing.B_PROMPT")
    assert (by_call["c"].pin, by_call["c"].prompt) == ("SONNET_MODEL", "analyzer.SYSTEM_PROMPT")
    assert (by_call["d"].pin, by_call["d"].prompt) == ("JUDGE_MODEL", "inline:onboarding.thing")


@pytest.mark.parametrize(
    "source",
    [
        "_parse_or_retry(c, p, call_kind='x', model=pick_model())",
        "_parse_or_retry(c, p, call_kind='x', system_prompt=build_prompt())",
        "_parse_or_retry(c, p, call_kind='x', system='a', system_prompt=P)",
        "_judge_create(c, call_kind='x', model=JUDGE_MODEL, system=build())",
        "some_new_wrapper(c, call_kind='x', model=HAIKU_MODEL)",
    ],
)
def test_a_shape_the_reader_cannot_read_fails_instead_of_being_skipped(source):
    with pytest.raises(GateCannotRead):
        sites_in(ast.parse(source), "analyzer.py")


def test_a_disagreement_between_site_and_entry_is_reported():
    entry = cat.load("clarify")
    right = Site("clarify", "analyzer.py:1", entry.model_pin, entry.prompt)
    assert mismatches(entry, right) == []
    wrong_pin = Site("clarify", "analyzer.py:1", "SONNET_MODEL", entry.prompt)
    wrong_prompt = Site("clarify", "analyzer.py:1", entry.model_pin, "analyzer.SYSTEM_PROMPT")
    assert len(mismatches(entry, wrong_pin)) == 1
    assert len(mismatches(entry, wrong_prompt)) == 1


def test_the_production_scan_sees_the_known_sites():
    sites = production_sites()
    assert (
        len(sites) == 26
    )  # tests/test_call_kind_telemetry.py: "23 distinct literals across 26 call sites"
    assert {s.call for s in sites} >= {"clarify", "judge_grade", "extract_experiences"}


# ---------- the validator ----------------------------------------------------------------------

_PENDING = {
    "schema": 1,
    "kind": "eval",
    "call": "x_kind",
    "status": "pending",
    "model_pin": "HAIKU_MODEL",
    "prompt": "analyzer.CLARIFY_SYSTEM_PROMPT",
    "groups": ["compose"],
    "pending_on": 185,
}
_COVERED = {
    **{k: v for k, v in _PENDING.items() if k != "pending_on"},
    "status": "covered",
    "cases": ["synthetic/pm-senior"],
    "rubrics": ["grounding"],
    "lean": "false_positive",
    "lean_why": "because",
    "n": 1,
}
_EXEMPT = {
    **{k: v for k, v in _PENDING.items() if k != "pending_on"},
    "status": "exempt",
    "exempt": "This call is exercised only inside another eval that already grades it end to end.",
    "exempt_approved": "owner 2026-10-22",
}


def _build(data):
    return cat._build(data, "x_kind", "x_kind.toml")


def test_a_valid_entry_of_each_status_builds():
    assert _build(_PENDING).pending_on == 185
    assert _build(_COVERED).n == 1
    assert _build(_EXEMPT).exempt_approved == "owner 2026-10-22"


@pytest.mark.parametrize(
    ("base", "edit", "fragment"),
    [
        (_PENDING, {"schema": 2}, "schema"),
        (_PENDING, {"kind": "item"}, "kind"),
        (_PENDING, {"call": "other_kind"}, "named for"),
        (_PENDING, {"status": "done"}, "status"),
        (_PENDING, {"model_pin": "OPUS_MODEL"}, "model_pin"),
        (_PENDING, {"prompt": "no-dot-here"}, "prompt"),
        (_PENDING, {"groups": ["nonsense"]}, "unknown group"),
        (_PENDING, {"pending_on": 1.5}, "float"),
        (_PENDING, {"pending_on": True}, "pending_on"),
        (_PENDING, {"pending_on": 0}, "pending_on"),
        (_PENDING, {"cases": ["a/b"]}, "not valid for status"),
        (_PENDING, {"surprise": 1}, "not valid"),
        (_COVERED, {"n": 0}, "`n`"),
        (_COVERED, {"n": 1.0}, "float"),
        (_COVERED, {"lean": "sideways"}, "lean"),
        (_COVERED, {"lean_why": ""}, "lean_why"),
        (_EXEMPT, {"exempt": "too short"}, "needs more than"),
        (_EXEMPT, {"exempt_approved": ""}, "exempt_approved"),
    ],
)
def test_the_validator_refuses(base, edit, fragment):
    with pytest.raises(cat.CatalogError, match=fragment):
        _build({**base, **edit})


@pytest.mark.parametrize(
    ("base", "dropped"),
    [
        (_PENDING, "pending_on"),
        (_COVERED, "rubrics"),
        (_COVERED, "lean_why"),
        (_EXEMPT, "exempt_approved"),
    ],
)
def test_the_validator_refuses_a_missing_required_field(base, dropped):
    with pytest.raises(cat.CatalogError, match="requires"):
        _build({k: v for k, v in base.items() if k != dropped})


# ---------- measured cost ----------------------------------------------------------------------


def _row(call, model="m1", status="ok", **tokens):
    base = {
        "call": call,
        "model": model,
        "status": status,
        "input_tokens": 100,
        "output_tokens": 10,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 1,
    }
    return {**base, **tokens}


def test_aggregate_means_are_integers_on_the_pinned_model_only():
    rows = [
        _row("clarify", input_tokens=100),
        _row("clarify", input_tokens=201),  # mean 150.5 -> rounds half up to 151
        _row("clarify", model="other"),  # another model
        _row("clarify", status="error"),  # an errored call
        _row("clarify_retry"),  # a retry is an extra call, not a planned one
        _row("recommend"),  # not in pin_models
        _row("clarify", input_tokens=-1),  # not a count
        _row("clarify", input_tokens=True),  # a bool is not a count
        "not a row",
    ]
    rows = [r for r in rows if isinstance(r, dict)]
    out = cat.aggregate(rows, {"clarify": "m1"})
    assert out == {
        "clarify": {
            "model": "m1",
            "rows": 2,
            "input": 151,
            "output": 10,
            "cache_write": 0,
            "cache_read": 1,
        }
    }
    assert all(type(v) is int for k, v in out["clarify"].items() if k != "model")


def test_a_float_in_costs_json_is_refused(monkeypatch, tmp_path):
    path = tmp_path / "costs.json"
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "kinds": {
                    "clarify": {
                        "model": "m",
                        "measured_on": "d",
                        "rows": 1,
                        "input": 1.5,
                        "output": 1,
                        "cache_write": 0,
                        "cache_read": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cat, "COSTS_PATH", path)
    with pytest.raises(cat.CatalogError, match="float"):
        cat.read_costs()


def test_a_missing_costs_file_means_nothing_is_measured(monkeypatch, tmp_path):
    monkeypatch.setattr(cat, "COSTS_PATH", tmp_path / "absent.json")
    assert cat.read_costs() == {}
