"""The golden-set prose generator: a model writes the text of a cell's slots, code checks every word.

Step 3a built and tested this against a stub client. Step 3b-ii made the first real calls (2026-10-28,
item 191): 96 cells, at about $0.05 to $0.09 each, all at effort ``medium``. The request shape below was
accepted as documented. The tests still use a stub; nothing in the test suite spends money.

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
``AuthorRejected``. A request is made once (no SDK retry) with a bounded wait, and a paid run asks Windows
not to sleep. The CLI needs ``--confirm-paid``, ``--max-spend`` and ``--max-total-spend``. The total cap
is read from the call log, so it spans runs and counts the requests of cells that were rejected; before
each cell the run stops if that cell, priced like the dearest so far, would reach either cap. A batch
resumes with ``--skip-existing``, stops after repeated rejections, and keeps a rejected reply.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import analyzer
from analyzer import log_judge_call
from evals import golden_set as gs
from hardening import compute_call_cost

#: The model that writes the dataset. Not SONNET_MODEL / HAIKU_MODEL / JUDGE_MODEL, and not moved by them.
AUTHOR_MODEL = "claude-opus-5-5"
#: Opus 5.5's default effort is `medium`; sent explicitly so the logged settings say what ran.
AUTHOR_EFFORT = "medium"
#: Bump with ANY change to ``AUTHOR_SYSTEM_PROMPT`` or ``build_user_prompt``. ``write_manifest`` records
#: it with the prompt's hash, and `check_suite` fails a generated cell whose version is not recorded.
AUTHOR_PROMPT_VERSION = "golden-author-2"
#: Non-streaming (under the SDK's HTTP timeout). A cell is a few thousand tokens of prose; adaptive
#: thinking spends from the same budget, so this leaves a wide margin.
AUTHOR_MAX_TOKENS = 16000
#: The first request, plus one for the slots that failed the checks.
MAX_ATTEMPTS = 2
EXIT_OVER_BUDGET = 4
#: A request that has not answered by then is abandoned (the SDK's default is 600 s, with two silent retries).
#: Observed 2026-10-28: the heaviest cell (26 slots, 3,449 output tokens) answered in 31 s, so this is about
#: six times the slowest request seen. It bounds a stall; it is not a guess at normal latency.
AUTHOR_TIMEOUT_SECONDS = 180.0
#: The batch stops after this many cells in a row are rejected: a brief that fails twice in a row is a
#: fault to look at, not a cost to repeat across the remaining cells.
DEFAULT_MAX_CONSECUTIVE_FAILURES = 2
REJECTS_DIR_NAME = "golden_rejects"

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
3. Every string in a slot's `must_include` appears in its text with the same letters; the check ignores \
capitalisation. Write a skill, tool or technique as a person would: in lower case in the middle of a \
sentence, capitalised only for a proper or product name (Python, Kubernetes), an acronym, or the first word \
of a sentence or bullet.
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
    """The model's reply could not be used at all (refusal, truncation, not JSON, no text).

    A request that was sent was paid for, so the error carries what it cost and what the model said:
    ``usage`` (token totals over every request of the cell), ``replies`` (each reply's text) and
    ``request_ids``. `author_cell` fills them in before it raises.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.usage: dict[str, int] = _usage_totals([])
        self.replies: list[str] = []
        self.request_ids: list[str | None] = []


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
    certifications = [
        i for s in profile["sections"] if s["kind"] == "certifications" for i in s["items"]
    ]
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
    if (
        certifications
    ):  # only when a cell has any, so a cell without them keeps its prompt byte for byte
        payload["facts"]["certifications"] = [
            {k: c[k] for k in ("name", "issuer", "year")} for c in certifications
        ]
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


def _reply_text(msg: Any) -> str:
    """The text blocks of a reply, joined."""
    return "".join(b.text for b in msg.content if getattr(b, "type", "text") == "text").strip()


_FENCE = re.compile(r"\A```[A-Za-z]*[ \t]*\n(.*)\n```\Z", re.DOTALL)


def _unfence(text: str) -> str:
    """The JSON inside a reply that is wrapped, and only wrapped, in one markdown code fence.

    The prompt asks for a bare JSON object; once in 77 paid requests the model added a ```json fence and
    the strict parse refused a cell that had been paid for. Prose before or after the fence, or an
    unclosed fence, is still not JSON. Every slot is checked on its own, so the wrapper carries no risk.
    """
    match = _FENCE.match(text.strip())
    return match.group(1) if match else text


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
    text = _unfence(_reply_text(msg))
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
    replies: list[str] = []
    failures: dict[str, list[str]] = {}
    # A derived iteration edits one slot's text, and the renderer needs a five-word run in it to quote.
    # Checking that here keeps a reply that would fail at the write inside the same rewrite budget.
    iteration = profile.get("iteration") or {}
    edit_slot = iteration.get("target_slot") if iteration.get("mode") == "derived" else None

    def carry(exc: AuthorError) -> AuthorError:
        exc.usage = _usage_totals(messages)
        exc.replies = list(replies)
        exc.request_ids = list(request_ids)
        return exc

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
        replies.append(_reply_text(msg))
        try:
            reply = _reply_slots(msg)
        except AuthorError as exc:
            raise carry(exc) from None
        failures = {}
        for slot_id in pending:
            slot = profile["slots"][slot_id]
            if slot_id not in reply:
                failures[slot_id] = [f"{slot_id}: the reply has no text for this slot"]
                continue
            found = gs.check_slot_text(
                slot_id, slot, reply[slot_id], [] if slot["kind"] == "jd" else traps
            )
            if not found and slot_id == edit_slot:
                try:
                    gs.pick_edit_target(reply[slot_id])
                except ValueError:
                    found = [
                        f"{slot_id}: the text has no run of five words free of commas, semicolons, "
                        "colons and brackets; the iteration edit quotes one"
                    ]
            if found:
                failures[slot_id] = found
                previous[slot_id] = (reply[slot_id], found)
            else:
                texts[slot_id] = reply[slot_id]
        pending = sorted(failures)
        if not pending:
            break
    if failures:
        raise carry(AuthorRejected([p for found in failures.values() for p in found]))
    # The write must not be where a paid cell is lost: render now, while a rewrite is still possible.
    try:
        gs.render_fixtures(profile, {"slots": texts})
    except ValueError as exc:
        raise carry(AuthorError(f"the accepted text does not render: {exc}")) from None
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


def cost_of_usage(usage: dict[str, int]) -> float:
    """Dollars for a token total, priced from ``hardening.MODEL_PRICING``."""
    return compute_call_cost({"model": AUTHOR_MODEL, **usage})


def cost_of(prose: dict[str, Any]) -> float:
    """Dollars for the requests behind one cell's prose."""
    return cost_of_usage(prose["provenance"]["usage"])


#: Windows power flags for `SetThreadExecutionState`.
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _set_execution_state(flags: int) -> None:
    """Ask Windows not to put the machine to sleep while a paid run is in flight; a no-op elsewhere.

    Observed 2026-10-28: the laptop entered Modern Standby for ten minutes in the middle of one request.
    The client's timeout counts awake time, so it never fired, the connection was dead on wake
    (``APIConnectionError`` at 622.9 s against a 180 s timeout), and a request the server may have
    billed was logged with no tokens. Best-effort: a failure here must never stop the run, and closing
    the lid can still sleep a machine that is set to.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags))
    except Exception:
        return


def _flush_progress() -> None:
    """Make progress lines appear as they are printed.

    Redirected to a file, stdout is block-buffered: a background run's log stayed empty until the run
    exited (observed 2026-10-28) and looked like a hung or failed run. Best-effort.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(line_buffering=True)


def _log_offset() -> int:
    """Byte size of the call log now: where a scan for rows written from here on can begin."""
    try:
        return analyzer.LOG_PATH.stat().st_size
    except OSError:
        return 0


def logged_spend(since: int = 0) -> float:
    """Dollars of the author's rows in the call log, from byte offset ``since`` (default: all of it).

    The spend a cap must span: it counts every request the log recorded, including those of a cell that
    was then rejected, and it survives a restart. Two limits, stated: it trusts a log that is written
    best-effort (so the run also counts its own usage and caps on the larger of the two), and a request
    that errored client side is logged with no tokens and cannot be priced. An offset past the end means
    the file was rotated and is read from the start.
    """
    total = 0.0
    try:
        with analyzer.LOG_PATH.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(since if since <= size else 0)
            for raw in fh:
                try:
                    row = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get("call") == "dataset_author":
                    total += compute_call_cost(row)
    except OSError:
        return 0.0
    return round(total, 6)


def _keep_reject(
    cell: str,
    error: str,
    problems: list[str],
    *,
    usage: dict[str, int],
    replies: list[str],
    request_ids: list[str | None],
    prose: dict[str, Any] | None = None,
) -> Path | None:
    """Save what a paid-for cell that was not written said, so it is studied and not bought again.

    Under the call log's own directory (the user's data directory, outside the repository). Never
    overwrites: a second rejection of the same cell goes to ``<cell>.2.json`` and so on. Best-effort.
    """
    folder = analyzer.LOG_PATH.parent / REJECTS_DIR_NAME
    record: dict[str, Any] = {
        "cell": cell,
        "error": error,
        "problems": problems,
        "prompt_version": AUTHOR_PROMPT_VERSION,
        "usage": usage,
        "replies": replies,
        "request_ids": request_ids,
    }
    if prose is not None:
        record["prose"] = prose
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{cell}.json"
        for n in range(2, 1000):
            if not path.exists():
                break
            path = folder / f"{cell}.{n}.json"
        with path.open("w", encoding="utf-8", newline="\n") as fh:  # LF on every platform
            fh.write(gs.canonical_json(record))
    except OSError as exc:
        print(
            f"golden_author: could not keep the rejected reply for {cell}: {exc}", file=sys.stderr
        )
        return None
    return path


def _parse_cell(ap: argparse.ArgumentParser, text: str) -> tuple[str, str]:
    """``PROFESSION:LEVEL`` as ``(profession, level)``; a usage error otherwise."""
    profession, sep, level = text.partition(":")
    if not sep or not profession or level not in gs.LEVELS:
        ap.error(
            f"--cell {text!r}: expected PROFESSION:LEVEL with LEVEL one of {', '.join(gs.LEVELS)}"
        )
    return profession, level


def main(argv: list[str] | None = None) -> int:
    """``python -m evals.golden_author --cell P:L [--cell P:L ...] --max-spend USD --max-total-spend USD --confirm-paid``.

    Builds each cell's profile from ``facts/<P>.json`` and the manifest's ladder, asks the model for the
    prose, writes the cell, and re-stamps the manifest. A cell that exists is never touched: it refuses
    the batch, or with ``--skip-existing`` is passed over, so a run that stopped can be started again and
    continues where it stopped. Every profile is built before the first request, so a bad facts file
    costs nothing.

    Two caps. ``--max-spend`` bounds this run; ``--max-total-spend`` bounds the author spend in the call
    log across every run, counting the requests of cells that were then rejected. Before each cell the
    run stops if the larger of what it counted and what the log shows, plus the dearest cell so far,
    would reach either cap (the first cell has no such estimate and can pass a very small cap).

    One attempt per request and a bounded wait, so a stall fails instead of being sent again and billed
    again. A rejected cell's replies are kept under the data directory's ``logs/golden_rejects/``. The
    run stops after ``--max-consecutive-failures`` cells in a row are not written, and at once on a
    transport fault.

    Exit 0 done, 1 a cell was not written, 3 nothing sent (no ``--confirm-paid``), 4 a cap was reached.
    """
    ap = argparse.ArgumentParser(
        prog="python -m evals.golden_author",
        description="Write golden-set cells' prose with a model (paid). Needs --confirm-paid, "
        "--max-spend and --max-total-spend.",
    )
    ap.add_argument("--root", type=Path, default=gs.SUITE_DIR)
    ap.add_argument("--profession", help="with --level: the profession whose cells to write")
    ap.add_argument("--level", action="append", choices=gs.LEVELS)
    ap.add_argument(
        "--cell",
        action="append",
        default=[],
        metavar="PROFESSION:LEVEL",
        help="a cell to write; repeat for a batch, written in the order given",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="pass over a cell that already exists instead of refusing the batch",
    )
    ap.add_argument("--max-spend", type=float, required=True, metavar="USD", help="this run's cap")
    ap.add_argument(
        "--max-total-spend",
        type=float,
        metavar="USD",
        help="cap on all author spend in the call log, this run included (required with --confirm-paid)",
    )
    ap.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=DEFAULT_MAX_CONSECUTIVE_FAILURES,
        metavar="N",
        help="stop after N cells in a row are not written (default %(default)s)",
    )
    ap.add_argument("--confirm-paid", action="store_true", help="required: this spends money")
    args = ap.parse_args(argv)
    _flush_progress()
    if args.max_spend <= 0:
        ap.error("--max-spend must be positive")
    if args.max_total_spend is not None and args.max_total_spend <= 0:
        ap.error("--max-total-spend must be positive")
    if args.confirm_paid and args.max_total_spend is None:
        ap.error("--max-total-spend is required with --confirm-paid")
    if args.max_consecutive_failures < 1:
        ap.error("--max-consecutive-failures must be at least 1")
    if bool(args.profession) != bool(args.level):
        ap.error("--profession and --level go together")
    wanted = [_parse_cell(ap, text) for text in args.cell]
    if args.profession:
        wanted += [(args.profession, level) for level in args.level]
    if not wanted:
        ap.error("name the cells to write: --cell PROFESSION:LEVEL, or --profession with --level")
    wanted = list(dict.fromkeys(wanted))  # a cell named twice is written once

    root: Path = args.root
    manifest = gs.load_manifest(root)
    facts_by_profession: dict[str, dict[str, Any]] = {}
    profiles: list[dict[str, Any]] = []
    for profession, level in wanted:
        if profession not in facts_by_profession:
            try:
                facts_by_profession[profession] = json.loads(
                    (root / "facts" / f"{profession}.json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError) as exc:
                print(
                    f"golden_author: facts/{profession}.json cannot be read: {exc}", file=sys.stderr
                )
                return 1
        try:
            ladder = gs.ladder_for(manifest, profession, level)
            profile = gs.build_profile(facts_by_profession[profession], ladder, level)
        except KeyError as exc:
            print(f"golden_author: {exc.args[0]}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"golden_author: facts/{profession}.json: {exc}", file=sys.stderr)
            return 1
        if (root / "cells" / profile["cell"]).exists():
            if args.skip_existing:
                print(f"golden_author: {profile['cell']} exists, skipped")
                continue
            print(
                f"golden_author: cell {profile['cell']} exists; a version adds cells and never edits one",
                file=sys.stderr,
            )
            return 1
        profiles.append(profile)
    if not profiles:
        print("golden_author: every named cell exists; nothing to write")
        return 0
    for profile in profiles:
        print(
            f"golden_author: {profile['cell']}: {len(profile['slots'])} slots, {AUTHOR_MODEL} at effort {AUTHOR_EFFORT}"
        )
    if not args.confirm_paid:
        print(
            "golden_author: nothing was sent. Pass --confirm-paid to spend "
            "(caps: --max-spend, --max-total-spend).",
            file=sys.stderr,
        )
        return 3

    assert args.max_total_spend is not None  # --confirm-paid requires it, checked above
    cap_total: float = args.max_total_spend
    start = _log_offset()
    prior = logged_spend()
    if prior >= cap_total:
        print(
            f"golden_author: the call log already holds ${prior:.4f} of author spend, at or over "
            f"--max-total-spend ${cap_total:.4f}; nothing was sent",
            file=sys.stderr,
        )
        return EXIT_OVER_BUDGET

    from evals import (
        runner,
    )  # function-local: the one place a client is built, already on the egress allowlist

    # One attempt per request and a bounded wait: the SDK's defaults re-send a stalled request (two
    # silent retries, none logged) after 600 s, which would bill the same cell more than once.
    client = runner._get_client().with_options(timeout=AUTHOR_TIMEOUT_SECONDS, max_retries=0)
    counted = 0.0
    costs: list[float] = []
    failed: list[str] = []
    streak = 0
    over_budget = False
    transport_fault = False

    def spend() -> tuple[float, float]:
        """``(this run, with earlier runs)``: the larger of what was counted and what the log shows."""
        run = max(counted, logged_spend(since=start))
        return run, prior + run

    _set_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        for profile in profiles:
            cell = profile["cell"]
            run, total = spend()
            likely = max(costs, default=0.0)
            if total + likely >= cap_total or run + likely >= args.max_spend:
                print(
                    f"golden_author: stopping before {cell}: this run ${run:.4f} and ${total:.4f} in all, "
                    f"and a cell costs about ${likely:.4f}, would reach --max-spend ${args.max_spend:.4f} "
                    f"or --max-total-spend ${cap_total:.4f}",
                    file=sys.stderr,
                )
                over_budget = True
                break
            try:
                prose = author_cell(client, profile)
            except AuthorError as exc:
                cost = cost_of_usage(exc.usage)
                counted += cost
                costs.append(cost)
                kept = _keep_reject(
                    cell,
                    type(exc).__name__,
                    exc.problems if isinstance(exc, AuthorRejected) else [str(exc)],
                    usage=exc.usage,
                    replies=exc.replies,
                    request_ids=exc.request_ids,
                )
                print(f"golden_author: {cell} not written: {exc}", file=sys.stderr)
                if kept is not None:
                    print(f"golden_author: the replies are kept at {kept}", file=sys.stderr)
                failed.append(cell)
                streak += 1
                if streak >= args.max_consecutive_failures:
                    print(
                        f"golden_author: stopping: {streak} consecutive cells were not written",
                        file=sys.stderr,
                    )
                    break
                continue
            except Exception as exc:  # a transport fault is not a content fault: stop, do not go on
                transport_fault = True
                print(
                    f"golden_author: {cell} not written: {type(exc).__name__}: {exc}\n"
                    "golden_author: stopping; start the same command again with --skip-existing to continue",
                    file=sys.stderr,
                )
                failed.append(cell)
                break
            cost = cost_of(prose)
            counted += cost
            costs.append(cost)
            try:
                gs.write_cell(root, profile, prose)
            except (ValueError, OSError) as exc:
                kept = _keep_reject(
                    cell,
                    type(exc).__name__,
                    [str(exc)],
                    usage=prose["provenance"]["usage"],
                    replies=[],
                    request_ids=prose["provenance"]["request_ids"],
                    prose=prose,
                )
                print(f"golden_author: {cell} was paid for but not written: {exc}", file=sys.stderr)
                if kept is not None:
                    print(f"golden_author: the prose is kept at {kept}", file=sys.stderr)
                failed.append(cell)
                streak += 1
                if streak >= args.max_consecutive_failures:
                    print(
                        f"golden_author: stopping: {streak} consecutive cells were not written",
                        file=sys.stderr,
                    )
                    break
                continue
            streak = 0
            manifest = gs.load_manifest(root)
            manifest.setdefault("author", {}).setdefault("prompt_versions", {})[
                AUTHOR_PROMPT_VERSION
            ] = author_prompt_sha()
            gs.write_manifest(root, manifest)
            run, total = spend()
            print(
                f"golden_author: wrote {cell} (${cost:.4f}; this run ${run:.4f}, "
                f"${total:.4f} of ${cap_total:.4f} in all)"
            )
    finally:
        _set_execution_state(ES_CONTINUOUS)
        logged = logged_spend(since=start)
        total = prior + max(counted, logged)
        print(
            f"golden_author: this run counted ${counted:.4f}; the call log shows ${logged:.4f}; "
            f"with earlier runs ${total:.4f} of ${cap_total:.4f}"
        )
        if abs(counted - logged) > 0.0001:
            print(
                "golden_author: the two differ; the caps use the larger. The call log is written "
                "best-effort, so a missing row is a reason to look, not a reason to trust the smaller.",
                file=sys.stderr,
            )
        if transport_fault:
            print(
                "golden_author: a request failed client side. The call log records it with no tokens, "
                "so its cost, if the server finished it, is in neither figure above.",
                file=sys.stderr,
            )
    if over_budget:
        return EXIT_OVER_BUDGET
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
