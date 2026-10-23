"""The eval catalog: one TOML file per LLM call kind (eval redesign step 2, item 182).

``evals/catalog/<call>.toml`` says, for one ``call_kind``, which model pin and which system
prompt the call uses, which group it belongs to, and whether an eval for it exists, is pending
a named work item, or is exempt with an owner-named reason. ``tests/test_eval_catalog.py`` fails
the gate when the catalog and the production source disagree (design: ``docs/dev/eval-redesign-design.md``
section 5.1). ``evals/catalog/costs.json`` holds the measured token means that ``--estimate``
prices; ``python -m evals.eval_catalog measure --write`` refreshes it.

Stdlib only, and lazy by construction (charter C-13): ``names()`` lists file names and parses
nothing, ``load()`` parses the one file it is asked for, and ``load_all()`` is the only eager
path. Nothing here imports ``analyzer`` or ``evals.runner`` at module level, so reading the
catalog does not load the product; ``measure`` imports them on demand.

Nothing stored here is a float (the factory's C-6): ``n`` and ``pending_on`` are integers,
token means are integers, and dollars are derived at estimate time from ``hardening.MODEL_PRICING``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

CATALOG_DIR = Path(__file__).resolve().parent / "catalog"
COSTS_PATH = CATALOG_DIR / "costs.json"

SCHEMA = 1
KIND = "eval"
STATUSES = ("covered", "pending", "exempt")
# AUTHOR_MODEL is the golden-set author's model (evals/golden_author.py): a pin of its own, outside the
# product pins, so a product swap cannot move the model that wrote the dataset.
PINS = ("SONNET_MODEL", "HAIKU_MODEL", "JUDGE_MODEL", "AUTHOR_MODEL")
GROUPS = (
    "analyze-clarify",
    "compose",
    "generate-letter",
    "ingest",
    "assistant",
    "proposals",
    "flows",
    "sentinel",
    "dataset",
)
LEANS = ("false_positive", "false_negative")
MIN_EXEMPT_REASON = 40
TOKEN_FIELDS = ("input", "output", "cache_write", "cache_read")

# The call-log field behind each TOKEN_FIELDS name, in the same order.
_LOG_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)

_CALL_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# `module.CONST` (a prompt constant the gate resolves) or `inline:module` (a string at the call site).
_PROMPT_RE = re.compile(r"^(inline:[a-z_][a-z0-9_.]*|[a-z_][a-z0-9_.]*\.[A-Z][A-Z0-9_]*)$")

_COMMON_KEYS = frozenset({"schema", "kind", "call", "status", "model_pin", "prompt", "groups"})
_KEYS_BY_STATUS: dict[str, frozenset[str]] = {
    "covered": frozenset({"cases", "rubrics", "checks", "lean", "lean_why", "n"}),
    "pending": frozenset({"pending_on"}),
    "exempt": frozenset({"exempt", "exempt_approved"}),
}
_REQUIRED_BY_STATUS: dict[str, frozenset[str]] = {
    "covered": frozenset({"cases", "rubrics", "lean", "lean_why", "n"}),
    "pending": frozenset({"pending_on"}),
    "exempt": frozenset({"exempt", "exempt_approved"}),
}


class CatalogError(ValueError):
    """A catalog entry or the cost file is malformed; the message names the file and the field."""


@dataclass(frozen=True)
class CatalogEntry:
    """One call kind's catalog entry. Fields beyond the common ones are set by ``status`` only."""

    call: str
    status: str
    model_pin: str
    prompt: str
    groups: tuple[str, ...]
    cases: tuple[str, ...] = ()
    rubrics: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    lean: str = ""
    lean_why: str = ""
    n: int = 0
    pending_on: int = 0
    exempt: str = ""
    exempt_approved: str = ""


# ---------- reading --------------------------------------------------------------------------


def names() -> list[str]:
    """The call kinds that have an entry, from file names. Parses nothing."""
    return sorted(p.stem for p in CATALOG_DIR.glob("*.toml"))


def _read_toml(path: Path) -> dict[str, Any]:
    """The one parse point for an entry; the laziness test counts calls to it."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CatalogError(f"{path.name}: {exc}") from exc


def load(call: str) -> CatalogEntry:
    """Parse and validate exactly one entry. ``call`` must match its file's ``call`` field."""
    if not _CALL_RE.match(call):
        raise CatalogError(f"{call!r} is not a call kind name")
    path = CATALOG_DIR / f"{call}.toml"
    if not path.is_file():
        raise CatalogError(f"no catalog entry for call kind {call!r}")
    return _build(_read_toml(path), call, path.name)


def load_all() -> dict[str, CatalogEntry]:
    """Every entry, parsed. Eager on purpose: the collection is the answer here.

    ``--list`` prints all of them and the gate checks all of them against the source; a lazy
    version would parse the same files one at a time for the same total cost (charter C-13's
    "when the collection is the answer" exception). A run of one kind must use ``load()``.
    """
    return {call: load(call) for call in names()}


# ---------- validation -----------------------------------------------------------------------


def _no_floats(value: object, where: str) -> None:
    if isinstance(value, float):
        raise CatalogError(f"{where}: a float is stored ({value!r}); use an integer")
    if isinstance(value, dict):
        for key, item in value.items():
            _no_floats(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _no_floats(item, f"{where}[{index}]")


def _str(data: Mapping[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{where}: `{key}` must be a non-empty string")
    return value


def _str_tuple(data: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise CatalogError(f"{where}: `{key}` must be a list of non-empty strings")
    return tuple(value)


def _int(data: Mapping[str, Any], key: str, where: str, *, minimum: int) -> int:
    value = data.get(key)
    if type(value) is not int or value < minimum:
        raise CatalogError(f"{where}: `{key}` must be an integer >= {minimum}")
    return value


def _build(data: dict[str, Any], stem: str, where: str) -> CatalogEntry:
    _no_floats(data, where)
    if data.get("schema") != SCHEMA:
        raise CatalogError(f"{where}: `schema` must be {SCHEMA}")
    if data.get("kind") != KIND:
        raise CatalogError(f'{where}: `kind` must be "{KIND}" (the document type)')
    call = _str(data, "call", where)
    if call != stem:
        raise CatalogError(f"{where}: `call` is {call!r} but the file is named for {stem!r}")
    status = _str(data, "status", where)
    if status not in STATUSES:
        raise CatalogError(f"{where}: `status` must be one of {STATUSES}, got {status!r}")

    allowed = _COMMON_KEYS | _KEYS_BY_STATUS[status]
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise CatalogError(f"{where}: key(s) {unknown} are not valid for status {status!r}")
    missing = sorted(_REQUIRED_BY_STATUS[status] - set(data))
    if missing:
        raise CatalogError(f"{where}: status {status!r} requires {missing}")

    model_pin = _str(data, "model_pin", where)
    if model_pin not in PINS:
        raise CatalogError(f"{where}: `model_pin` must be one of {PINS}, got {model_pin!r}")
    prompt = _str(data, "prompt", where)
    if not _PROMPT_RE.match(prompt):
        raise CatalogError(
            f"{where}: `prompt` must be `module.CONSTANT` or `inline:module`, got {prompt!r}"
        )
    groups = _str_tuple(data, "groups", where)
    bad_groups = sorted(set(groups) - set(GROUPS))
    if bad_groups:
        raise CatalogError(f"{where}: unknown group(s) {bad_groups}; known: {GROUPS}")

    common: dict[str, Any] = {
        "call": call,
        "status": status,
        "model_pin": model_pin,
        "prompt": prompt,
        "groups": groups,
    }
    if status == "covered":
        lean = _str(data, "lean", where)
        if lean not in LEANS:
            raise CatalogError(f"{where}: `lean` must be one of {LEANS}, got {lean!r}")
        return CatalogEntry(
            **common,
            cases=_str_tuple(data, "cases", where),
            rubrics=_str_tuple(data, "rubrics", where),
            checks=_str_tuple(data, "checks", where),
            lean=lean,
            lean_why=_str(data, "lean_why", where),
            n=_int(data, "n", where, minimum=1),
        )
    if status == "pending":
        return CatalogEntry(**common, pending_on=_int(data, "pending_on", where, minimum=1))
    reason = _str(data, "exempt", where)
    if len(reason) <= MIN_EXEMPT_REASON:
        raise CatalogError(
            f"{where}: `exempt` is a reason of {len(reason)} characters; it needs more than "
            f"{MIN_EXEMPT_REASON} (a one-word reason is the silence this field exists to prevent)"
        )
    return CatalogEntry(
        **common, exempt=reason, exempt_approved=_str(data, "exempt_approved", where)
    )


# ---------- measured cost --------------------------------------------------------------------


def _reject_float(text: str) -> float:
    raise CatalogError(f"costs.json: a float ({text}) is stored; token means are integers")


def read_costs() -> dict[str, dict[str, Any]]:
    """The measured token means per call kind, or ``{}`` when no file exists yet.

    Each value holds ``model`` (the model the means were measured on), ``rows`` and the four
    ``TOKEN_FIELDS`` as integers, plus ``measured_on``. Read once per estimate.
    """
    try:
        text = COSTS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text, parse_float=_reject_float)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"costs.json: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise CatalogError(f"costs.json: `schema` must be {SCHEMA}")
    kinds = data.get("kinds")
    if not isinstance(kinds, dict):
        raise CatalogError("costs.json: `kinds` must be an object")
    for call, row in kinds.items():
        if not isinstance(row, dict) or not isinstance(row.get("model"), str):
            raise CatalogError(f"costs.json: `{call}` needs a `model` string")
        if not isinstance(row.get("measured_on"), str):
            raise CatalogError(f"costs.json: `{call}` needs a `measured_on` string")
        for field in ("rows", *TOKEN_FIELDS):
            if type(row.get(field)) is not int or row[field] < 0:
                raise CatalogError(f"costs.json: `{call}.{field}` must be a non-negative integer")
    return dict(kinds)


def _log_ints(row: Mapping[str, Any]) -> list[int] | None:
    """The four token counts of a call-log row in ``TOKEN_FIELDS`` order, or None if any is not a count."""
    out: list[int] = []
    for field in _LOG_FIELDS:
        value = row.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
        out.append(value)
    return out


def aggregate(
    rows: Iterable[Mapping[str, Any]], pin_models: Mapping[str, str]
) -> dict[str, dict[str, Any]]:
    """Per call kind, the integer mean token use of its successful rows on its pinned model.

    ``pin_models`` maps a call kind to the model id it is measured on; a row for any other kind,
    any other model, an errored call or a ``<kind>_retry`` row is skipped. Retry rows are left
    out on purpose: an estimate prices the planned calls, so it is a floor and says so. One pass,
    constant memory.
    """
    sums: dict[str, list[int]] = {}
    for row in rows:
        call = row.get("call")
        if not isinstance(call, str) or call.endswith("_retry"):
            continue
        want = pin_models.get(call)
        if want is None or row.get("model") != want or row.get("status", "ok") != "ok":
            continue
        values = _log_ints(row)
        if values is None:
            continue
        acc = sums.setdefault(call, [0, 0, 0, 0, 0])
        acc[0] += 1
        for index, value in enumerate(values, start=1):
            acc[index] += value
    out: dict[str, dict[str, Any]] = {}
    for call, acc in sums.items():
        count = acc[0]
        means = {f: (acc[i] + count // 2) // count for i, f in enumerate(TOKEN_FIELDS, start=1)}
        out[call] = {"model": pin_models[call], "rows": count, **means}
    return out


def _iter_log(path: Path) -> Iterable[dict[str, Any]]:
    """Stream the call log's JSON object rows; a bad line is skipped, never fatal."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def _pin_models(entries: Mapping[str, CatalogEntry]) -> dict[str, str]:
    """Each kind's current pin as a model id. Imports the product, so only ``measure`` calls it."""
    import analyzer
    from evals import golden_author, runner

    models = {
        "SONNET_MODEL": analyzer.SONNET_MODEL,
        "HAIKU_MODEL": analyzer.HAIKU_MODEL,
        "JUDGE_MODEL": runner.JUDGE_MODEL,
        "AUTHOR_MODEL": golden_author.AUTHOR_MODEL,
    }
    return {call: models[entry.model_pin] for call, entry in entries.items()}


def main(argv: list[str] | None = None) -> int:
    """``python -m evals.eval_catalog measure [--write] [--log PATH]``."""
    ap = argparse.ArgumentParser(prog="python -m evals.eval_catalog")
    sub = ap.add_subparsers(dest="command", required=True)
    measure = sub.add_parser("measure", help="aggregate the call log into per-kind token means")
    measure.add_argument("--write", action="store_true", help="write evals/catalog/costs.json")
    measure.add_argument("--log", metavar="PATH", help="call log (default: the data root's)")
    args = ap.parse_args(argv)

    import sartor_home

    log_path = Path(args.log) if args.log else sartor_home.data_path("logs", "llm_calls.jsonl")
    if not log_path.is_file():
        print(f"eval_catalog: no call log at {log_path}", file=sys.stderr)
        return 1
    entries = load_all()
    measured = aggregate(_iter_log(log_path), _pin_models(entries))
    today = date.today().isoformat()
    kinds = {call: {**row, "measured_on": today} for call, row in sorted(measured.items())}

    print(
        f"{'call kind':34s} {'rows':>5s} {'input':>8s} {'output':>8s} {'c.write':>8s} {'c.read':>8s}"
    )
    for call, row in kinds.items():
        print(
            f"{call:34s} {row['rows']:5d} {row['input']:8d} {row['output']:8d} "
            f"{row['cache_write']:8d} {row['cache_read']:8d}"
        )
    unmeasured = sorted(set(entries) - set(kinds))
    print(f"unmeasured ({len(unmeasured)}): {', '.join(unmeasured) or 'none'}")
    if not args.write:
        print("dry run; pass --write to save evals/catalog/costs.json")
        return 0
    payload = json.dumps({"schema": SCHEMA, "kinds": kinds}, indent=2, sort_keys=True) + "\n"
    COSTS_PATH.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {COSTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
