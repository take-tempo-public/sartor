"""The golden-set prose generator: a model writes the text of a cell's slots, code checks every word.

Step 3a builds and tests this against a stub client. **It has never made a real call**: no paid call
was authorized for 3a, so the live request shape (the ``thinking`` and ``output_config`` values below)
is as documented, not observed. Step 3b is the first real run, under ``--max-spend``.

**Why this lives beside the judges, not in ``analyzer.py``.** ``AGENTS.md`` says every product LLM call
lives in ``analyzer.py``. This is not a product call: it writes the eval dataset. It follows the judge
pattern (``evals.runner._judge_create``): a direct ``client.messages.create`` and a telemetry row
through ``analyzer.log_judge_call``, under ``call_kind="dataset_author"``. The catalog marks it
``exempt`` (it is the dataset tooling's own call, never evaluated).

**Why it takes the client as an argument and imports no network library.** The only code that builds a
client is ``evals.runner._get_client``, which is already on the egress allowlist; the CLI reaches it
with a function-local import. Nothing here needs its own entry in ``tests/test_egress_allowlist.py``.

**The model is a pin of its own** (``AUTHOR_MODEL``), outside the product pins and both arms of the
Haiku 5.5 comparison (item 137), so no evaluated model wrote its own test set. Claude Opus 5.5 rejects
``thinking: {"type": "disabled"}`` and a thinking budget at every effort level; the only settings it
accepts are adaptive thinking (what omitting the field means) and an effort. This module sends both
explicitly, so the request settings in the log say what ran. It does NOT go through the product's
``THINKING_POLICY``: adding a row there would also make Opus 5.5 a legal ``--model-override`` target
for product calls nobody has validated against it (forced ``tool_choice`` and sampling parameters are
400s on it). The price is in ``hardening.MODEL_PRICING`` (read from the pricing page 2026-10-22).

**No fallback model.** The API can route a request the safety classifiers decline to another model. That
would make the recorded ``model`` wrong for the text it wrote. A refusal on résumé prose is a finding
to look at, so it raises ``AuthorError`` and the cell is not written.

**Bounded.** One request per cell; a second only for the slots that failed the checks; then it raises
``AuthorRejected``. The CLI needs ``--confirm-paid`` and ``--max-spend``, and stops before the next cell
once the spend reaches the cap (it can overshoot by one cell).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from analyzer import log_judge_call
from evals import golden_set as gs
from hardening import compute_call_cost

#: The model that writes the dataset. Not SONNET_MODEL / HAIKU_MODEL / JUDGE_MODEL, and not moved by them.
AUTHOR_MODEL = "claude-opus-5-5"
#: Opus 5.5's default effort is `medium`; sent explicitly so the logged settings say what ran.
AUTHOR_EFFORT = "medium"
#: Bump with ANY change to ``AUTHOR_SYSTEM_PROMPT`` or ``build_user_prompt``. ``write_manifest`` records
#: it with the prompt's hash, and `check_suite` fails a generated cell whose version is not recorded.
AUTHOR_PROMPT_VERSION = "golden-author-1"
#: Non-streaming (under the SDK's HTTP timeout). A cell is a few thousand tokens of prose; adaptive
#: thinking spends from the same budget, so this leaves a wide margin.
AUTHOR_MAX_TOKENS = 16000
#: The first request, plus one for the slots that failed the checks.
MAX_ATTEMPTS = 2
EXIT_OVER_BUDGET = 4

AUTHOR_SYSTEM_PROMPT = """\
You write text for a synthetic résumé dataset used to test a résumé tailoring tool. Every candidate, \
employer, school and address is invented. You are given the facts about one candidate and a list of \
slots to fill. Write the text of each slot.

Rules, all of them binding:

1. Use only the facts you are given. Invent no employer, job title, product, school, certification, \
date, place or number that is not in them. Say nothing about skills the candidate does not list.
2. Numbers. A slot lists the numbers it allows in `allowed_numbers`. Write no digit at all unless it \
belongs to one of those numbers, written exactly as listed. If the list is empty, write no digits and \
spell out any number as a word.
3. Every string in a slot's `must_include` appears in its text, spelled as given.
4. Length. Stay between `min_words` and `max_words`.
5. Format. A `bullet`, `intro` or `summary` slot is one line of plain prose: no line break, no \
leading dash or bullet character, no markdown, no quotation marks around it. A `jd` slot is a job \
description section: it may have several lines, and where the brief asks for bullet lines each starts \
with "- ". No double spaces.
6. Voice. A bullet for a past role is in the past tense and starts with a verb. A bullet for the \
current role (its end date is "present") is in the present tense. A summary is third person without \
a pronoun at the start. Write plainly: no superlatives, no "results-driven", no "passionate".
7. Do not repeat the same opening words across the bullets of one role.

Reply with one JSON object and nothing else: {"slots": {"<slot id>": "<text>", ...}} containing \
exactly the slot ids you were asked for.
"""


class AuthorError(RuntimeError):
    """The model's reply could not be used at all (refusal, truncation, not JSON, no text)."""


class AuthorRejected(AuthorError):
    """After the allowed attempts, slots still failed the checks; ``problems`` lists them."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(
            "slots failed the checks after the allowed attempts:\n  " + "\n  ".join(problems)
        )
        self.problems = problems


def author_prompt_sha() -> str:
    """The hash `check_suite` compares a manifest's recorded prompt hash to."""
    return gs.sha256_text(AUTHOR_SYSTEM_PROMPT)


def build_user_prompt(
    profile: dict[str, Any],
    slot_ids: list[str],
    *,
    previous: dict[str, tuple[str, list[str]]] | None = None,
) -> str:
    """The facts and the slots to fill, as sorted-key JSON. ``previous`` carries a failed text and why."""
    roles = [r for s in profile["sections"] if s["kind"] == "experience" for r in s["roles"]]
    education = [i for s in profile["sections"] if s["kind"] == "education" for i in s["items"]]
    payload: dict[str, Any] = {
        "facts": {
            "level": profile["level"],
            "roles": [
                {
                    "title": r["title"],
                    "company": r["company"],
                    "start": gs.month_label(r["start"]),
                    "end": gs.month_label(r["end"]),
                }
                for r in roles
            ],
            "education": [
                {k: e[k] for k in ("degree", "field", "institution", "year")} for e in education
            ],
            "skills": [s["name"] for s in profile["skills"]],
            "job_descriptions": [
                {"id": jd["slug"], "header": jd["header_lines"]} for jd in profile["jds"]
            ],
        },
        "slots": {
            sid: {
                k: profile["slots"][sid][k]
                for k in (
                    "kind",
                    "brief",
                    "must_include",
                    "allowed_numbers",
                    "min_words",
                    "max_words",
                )
            }
            for sid in slot_ids
        },
    }
    if previous:
        payload["rewrite"] = {
            sid: {"previous_text": text, "problems": problems}
            for sid, (text, problems) in sorted(previous.items())
        }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _author_create(
    client: Any,
    *,
    call_kind: str,
    model: str,
    system_prompt: str,
    username: str,
    **request: Any,
) -> tuple[Any, str | None]:
    """``client.messages.create`` for the dataset author, with its telemetry row.

    The judge pattern (``evals.runner._judge_create``): returns ``(message, api_request_id)``; a failed
    call logs its error row and re-raises. Row ``prompt_version`` is `AUTHOR_PROMPT_VERSION`, so the
    author's rows never read as a product prompt version. No ``thinking_setting`` lookup: see the module
    docstring.
    """
    request = {"model": model, "system": system_prompt, **request}
    t0 = time.perf_counter()
    try:
        msg = client.messages.create(**request)
    except Exception as exc:
        log_judge_call(
            call_kind=call_kind,
            username=username,
            model=model,
            request_kwargs=request,
            response=None,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
            error=exc,
            prompt_version=AUTHOR_PROMPT_VERSION,
        )
        raise
    request_id = log_judge_call(
        call_kind=call_kind,
        username=username,
        model=model,
        request_kwargs=request,
        response=msg,
        elapsed_ms=int((time.perf_counter() - t0) * 1000),
        prompt_version=AUTHOR_PROMPT_VERSION,
    )
    return msg, request_id


def _reply_slots(msg: Any) -> dict[str, str]:
    """The ``{"slots": {...}}`` object a reply holds, or `AuthorError`."""
    if msg.stop_reason != "end_turn":
        raise AuthorError(
            f"the reply stopped with stop_reason={msg.stop_reason!r}, not 'end_turn'"
            + (
                " (a refusal; no fallback model is used on purpose)"
                if msg.stop_reason == "refusal"
                else ""
            )
        )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "text") == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuthorError(f"the reply is not JSON: {exc}") from exc
    slots = data.get("slots") if isinstance(data, dict) else None
    if not isinstance(slots, dict) or not all(isinstance(v, str) for v in slots.values()):
        raise AuthorError('the reply is not {"slots": {id: text}}')
    return slots


def _usage_totals(messages: list[Any]) -> dict[str, int]:
    total = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    for msg in messages:
        for key in total:
            total[key] += int(getattr(msg.usage, key, 0) or 0)
    return total


def author_cell(client: Any, profile: dict[str, Any]) -> dict[str, Any]:
    """Write a cell's prose with the model and return the ``prose.json`` document.

    Every slot is checked with `golden_set.check_slot_text`; the slots that fail get one rewrite
    request that shows the model its text and the problems. Raises `AuthorError` for an unusable reply
    and `AuthorRejected` when slots still fail, and writes nothing either way.
    """
    unsound = gs.validate_profile(profile)
    if unsound:
        raise AuthorError("the profile is not sound:\n  " + "\n  ".join(unsound))
    traps = list(profile["expected"].get("forbidden_inventions", []))
    texts: dict[str, str] = {}
    pending = sorted(profile["slots"])
    previous: dict[str, tuple[str, list[str]]] = {}
    messages: list[Any] = []
    request_ids: list[str | None] = []
    failures: dict[str, list[str]] = {}
    for _ in range(MAX_ATTEMPTS):
        msg, request_id = _author_create(
            client,
            call_kind="dataset_author",
            model=AUTHOR_MODEL,
            system_prompt=AUTHOR_SYSTEM_PROMPT,
            username=f"golden:{profile['cell']}",
            max_tokens=AUTHOR_MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": AUTHOR_EFFORT},
            messages=[
                {"role": "user", "content": build_user_prompt(profile, pending, previous=previous)}
            ],
        )
        messages.append(msg)
        request_ids.append(request_id)
        reply = _reply_slots(msg)
        failures = {}
        for slot_id in pending:
            slot = profile["slots"][slot_id]
            if slot_id not in reply:
                failures[slot_id] = [f"{slot_id}: the reply has no text for this slot"]
                continue
            found = gs.check_slot_text(
                slot_id, slot, reply[slot_id], [] if slot["kind"] == "jd" else traps
            )
            if found:
                failures[slot_id] = found
                previous[slot_id] = (reply[slot_id], found)
            else:
                texts[slot_id] = reply[slot_id]
        pending = sorted(failures)
        if not pending:
            break
    if failures:
        raise AuthorRejected([p for found in failures.values() for p in found])
    answered = {str(getattr(m, "model", "")) for m in messages}
    return {
        "schema": gs.SCHEMA,
        "cell": profile["cell"],
        "provenance": {
            "kind": "generated",
            "model": sorted(answered)[0] if len(answered) == 1 else sorted(answered),
            "requested_model": AUTHOR_MODEL,
            "effort": AUTHOR_EFFORT,
            "prompt_version": AUTHOR_PROMPT_VERSION,
            "prompt_sha256": author_prompt_sha(),
            "profile_sha256": gs.sha256_text(gs.canonical_json(profile)),
            "request_ids": request_ids,
            "attempts": len(messages),
            "usage": _usage_totals(messages),
        },
        "slots": {sid: texts[sid] for sid in sorted(texts)},
    }


def cost_of(prose: dict[str, Any]) -> float:
    """Dollars for the requests behind one cell's prose, priced from ``hardening.MODEL_PRICING``."""
    usage = prose["provenance"]["usage"]
    return compute_call_cost({"model": AUTHOR_MODEL, **usage})


def main(argv: list[str] | None = None) -> int:
    """``python -m evals.golden_author --profession P --level L [--level L ...] --max-spend USD --confirm-paid``.

    Builds each cell's profile from ``facts/<P>.json`` and the manifest's ladder, asks the model for the
    prose, writes the cell, and re-stamps the manifest. Refuses to touch a cell that already exists
    (a version adds cells and never edits one). Exit 0 done, 1 a cell failed, 3 nothing sent (no
    ``--confirm-paid``), 4 the spend cap was reached.
    """
    ap = argparse.ArgumentParser(
        prog="python -m evals.golden_author",
        description="Write a golden-set cell's prose with a model (paid). Needs --confirm-paid and --max-spend.",
    )
    ap.add_argument("--root", type=Path, default=gs.SUITE_DIR)
    ap.add_argument("--profession", required=True)
    ap.add_argument("--level", action="append", required=True, choices=gs.LEVELS)
    ap.add_argument("--max-spend", type=float, required=True, metavar="USD")
    ap.add_argument("--confirm-paid", action="store_true", help="required: this spends money")
    args = ap.parse_args(argv)
    if args.max_spend <= 0:
        ap.error("--max-spend must be positive")

    root: Path = args.root
    manifest = gs.load_manifest(root)
    facts = json.loads((root / "facts" / f"{args.profession}.json").read_text(encoding="utf-8"))
    profiles: list[dict[str, Any]] = []
    for level in args.level:
        profile = gs.build_profile(facts, manifest["levels"][level], level)
        if (root / "cells" / profile["cell"]).exists():
            print(
                f"golden_author: cell {profile['cell']} exists; a version adds cells and never edits one",
                file=sys.stderr,
            )
            return 1
        profiles.append(profile)
    for profile in profiles:
        print(
            f"golden_author: {profile['cell']}: {len(profile['slots'])} slots, {AUTHOR_MODEL} at effort {AUTHOR_EFFORT}"
        )
    if not args.confirm_paid:
        print(
            "golden_author: nothing was sent. Pass --confirm-paid to spend (cap: --max-spend).",
            file=sys.stderr,
        )
        return 3

    from evals import (
        runner,
    )  # function-local: the one place a client is built, already on the egress allowlist

    client = runner._get_client()
    spent = 0.0
    for profile in profiles:
        if spent >= args.max_spend:
            print(
                f"golden_author: stopping before {profile['cell']}: ${spent:.4f} reached --max-spend ${args.max_spend:.4f}",
                file=sys.stderr,
            )
            return EXIT_OVER_BUDGET
        try:
            prose = author_cell(client, profile)
        except AuthorError as exc:
            print(f"golden_author: {profile['cell']} not written: {exc}", file=sys.stderr)
            return 1
        gs.write_cell(root, profile, prose)
        spent += cost_of(prose)
        manifest = gs.load_manifest(root)
        manifest.setdefault("author", {}).setdefault("prompt_versions", {})[
            AUTHOR_PROMPT_VERSION
        ] = author_prompt_sha()
        gs.write_manifest(root, manifest)
        print(f"golden_author: wrote {profile['cell']} (${spent:.4f} so far)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
