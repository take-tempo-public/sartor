"""Generic doc/template validator (schema per `docs/dev/prov/SPEC.md`).

Checks that a doc instantiated from a template:

  1. contains every one of the template's structural headings (`##` or
     deeper — the template's own `#` title is exempt), in the same
     relative order. A placeholder span in a template heading's text
     (`<!-- like-this -->`) matches anything in the doc's heading.
  2. reproduces every "verbatim section" (a heading whose body's first
     non-blank line is the marker `<!-- verbatim -->`) byte-for-byte
     (trailing whitespace per line ignored) against the template's
     canonical text for that section.

With `--event generated|consumed`, also appends a JSON-lines event to this
session's ledger shard (`docs/dev/ledger/<session>.jsonl`):

  - `--event generated`: validation pass -> `generated`, fail -> `failed`.
  - `--event consumed`: also compares the doc's current fingerprint
    against the most recent `generated` event on record for the same doc
    path (scanned across all ledger shards); a structural/verbatim/
    fingerprint failure logs `blocked` (corrupted input is a blocked
    gate — surfaced, never silently reconstructed).

Usage:

    python scripts/verify_doc_template.py <doc> <template>
    python scripts/verify_doc_template.py <doc> <template> \\
        --event generated --agent anthropic/claude-sonnet-5
    python scripts/verify_doc_template.py <doc> <template> \\
        --event consumed --agent anthropic/claude-sonnet-5 \\
        --session <uuid> --branch <name> --actor <name>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VERBATIM_MARKER = "<!-- verbatim -->"
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PLACEHOLDER_RE = re.compile(r"<!--.*?-->")
_FENCE_RE = re.compile(r"^```")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int  # 0-based index into the split-lines list


def parse_headings(content: str) -> list[Heading]:
    """Extract ATX headings, skipping fenced code blocks."""
    headings: list[Heading] = []
    in_fence = False
    for i, raw_line in enumerate(content.splitlines()):
        if _FENCE_RE.match(raw_line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING_RE.match(raw_line)
        if match:
            headings.append(Heading(level=len(match.group(1)), text=match.group(2), line=i))
    return headings


def heading_pattern(text: str) -> re.Pattern[str]:
    """Build a regex matching `text` with `<!-- ... -->` spans as wildcards."""
    parts: list[str] = []
    last = 0
    for m in _PLACEHOLDER_RE.finditer(text):
        parts.append(re.escape(text[last : m.start()]))
        parts.append(".*?")
        last = m.end()
    parts.append(re.escape(text[last:]))
    return re.compile("^" + "".join(parts) + "$")


def required_headings(template_headings: list[Heading]) -> list[Heading]:
    """Template headings a doc must contain — everything but the `#` title."""
    return [h for h in template_headings if h.level >= 2]


def match_headings(
    template_headings: list[Heading], doc_headings: list[Heading]
) -> tuple[list[int | None], list[str]]:
    """Match each required template heading to a doc heading, in order.

    Returns (matches, errors): `matches[i]` is the index into `doc_headings`
    matched for `template_headings[i]`, or `None` if not found.
    """
    matches: list[int | None] = []
    errors: list[str] = []
    cursor = 0
    for heading in template_headings:
        pattern = heading_pattern(heading.text)
        found: int | None = None
        for j in range(cursor, len(doc_headings)):
            candidate = doc_headings[j]
            if candidate.level == heading.level and pattern.match(candidate.text):
                found = j
                break
        matches.append(found)
        if found is None:
            errors.append(
                f"required heading not found (or out of order): "
                f"{'#' * heading.level} {heading.text}"
            )
        else:
            cursor = found + 1
    return matches, errors


def _section_bounds(headings: list[Heading], index: int, total_lines: int) -> tuple[int, int]:
    """Line range `[start, end)` of the body directly under `headings[index]`."""
    level = headings[index].level
    start = headings[index].line + 1
    end = total_lines
    for later in headings[index + 1 :]:
        if later.level <= level:
            end = later.line
            break
    return start, end


def _normalize(lines: list[str]) -> str:
    trimmed = [line.rstrip() for line in lines]
    while trimmed and trimmed[0] == "":
        trimmed.pop(0)
    while trimmed and trimmed[-1] == "":
        trimmed.pop()
    return "\n".join(trimmed)


def _split_off_marker(lines: list[str]) -> tuple[bool, list[str]]:
    """Drop a leading `<!-- verbatim -->` marker line (after leading blank
    lines), if present. Returns whether one was found."""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip() == _VERBATIM_MARKER:
        return True, lines[i + 1 :]
    return False, lines


def verbatim_sections(content: str, headings: list[Heading]) -> dict[int, str]:
    """Map template heading index -> canonical verbatim body text, for
    headings whose body opens with the `<!-- verbatim -->` marker."""
    lines = content.splitlines()
    sections: dict[int, str] = {}
    for i in range(len(headings)):
        start, end = _section_bounds(headings, i, len(lines))
        has_marker, body = _split_off_marker(lines[start:end])
        if not has_marker:
            continue
        sections[i] = _normalize(body)
    return sections


def check_verbatim(
    doc_content: str,
    template_content: str,
    template_headings: list[Heading],
    doc_headings: list[Heading],
    matches: list[int | None],
) -> list[str]:
    errors: list[str] = []
    canonical = verbatim_sections(template_content, template_headings)
    doc_lines = doc_content.splitlines()
    for i, canonical_text in canonical.items():
        doc_index = matches[i]
        if doc_index is None:
            continue  # already reported as a structural error
        start, end = _section_bounds(doc_headings, doc_index, len(doc_lines))
        _has_marker, doc_body = _split_off_marker(doc_lines[start:end])
        doc_text = _normalize(doc_body)
        if doc_text != canonical_text:
            heading = template_headings[i]
            errors.append(
                f"verbatim section does not match template: "
                f"{'#' * heading.level} {heading.text} "
                f"(template sha256={_sha256(canonical_text)[:12]}, "
                f"doc sha256={_sha256(doc_text)[:12]})"
            )
    return errors


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(path: Path) -> str:
    """Content fingerprint, newline-normalized so it is stable across a
    platform's line-ending checkout behavior (e.g. Windows `core.autocrlf`)
    and matches the LF-normalized bytes git stores in the object database."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:12]


def validate(doc_content: str, template_content: str) -> list[str]:
    """Run the structural + verbatim checks; return all error strings."""
    template_headings = required_headings(parse_headings(template_content))
    doc_headings = parse_headings(doc_content)
    matches, errors = match_headings(template_headings, doc_headings)
    errors.extend(
        check_verbatim(doc_content, template_content, template_headings, doc_headings, matches)
    )
    return errors


def read_ledger(ledger_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if not ledger_dir.is_dir():
        return records
    for shard in sorted(ledger_dir.glob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def latest_generated_fingerprint(records: list[dict[str, str]], doc_rel_path: str) -> str | None:
    generated = [
        r for r in records if r.get("doc") == doc_rel_path and r.get("event") == "generated"
    ]
    if not generated:
        return None
    return max(generated, key=lambda r: r["ts"])["fingerprint"]


def append_ledger_event(ledger_dir: Path, session: str, record: dict[str, str]) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    shard = ledger_dir / f"{session}.jsonl"
    with shard.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _git(*args: str) -> str | None:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["git", *args],  # noqa: S607 -- git on PATH, not attacker-controlled
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=_REPO_ROOT,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("doc", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("--event", choices=["generated", "consumed"], default=None)
    parser.add_argument(
        "--agent", default=None, help="vendor/model-or-human, e.g. anthropic/claude-sonnet-5"
    )
    parser.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    parser.add_argument("--branch", default=None)
    parser.add_argument("--actor", default=None)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--ledger-dir", type=Path, default=_REPO_ROOT / "docs" / "dev" / "ledger")
    args = parser.parse_args(argv)

    doc_path: Path = args.doc.resolve()
    template_path: Path = args.template.resolve()
    if not doc_path.is_file():
        print(f"verify_doc_template: doc not found: {doc_path}", file=sys.stderr)
        return 2
    if not template_path.is_file():
        print(f"verify_doc_template: template not found: {template_path}", file=sys.stderr)
        return 2

    if _REPO_ROOT not in doc_path.parents:
        print(
            f"verify_doc_template: doc is not inside the repo root ({_REPO_ROOT}): {doc_path}",
            file=sys.stderr,
        )
        return 2

    doc_content = doc_path.read_text(encoding="utf-8")
    template_content = template_path.read_text(encoding="utf-8")
    errors = validate(doc_content, template_content)
    doc_fingerprint = fingerprint(doc_path)
    doc_rel_path = doc_path.relative_to(_REPO_ROOT).as_posix()

    if args.event is None:
        if errors:
            print("verify_doc_template: FAILED", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 1
        print(f"verify_doc_template: OK (fingerprint {doc_fingerprint})")
        return 0

    if args.agent is None:
        parser.error("--agent is required with --event")
    session = args.session
    if not session:
        parser.error("--session is required with --event (or set CLAUDE_CODE_SESSION_ID)")
    branch = args.branch or _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    actor = args.actor or _git("config", "user.name") or "unknown"
    commit = args.commit or _git("rev-parse", "--short", "HEAD") or "unknown"

    ledger_records = read_ledger(args.ledger_dir)
    if args.event == "consumed":
        prior = latest_generated_fingerprint(ledger_records, doc_rel_path)
        if prior is None:
            print(
                f"verify_doc_template: no prior 'generated' ledger record found for "
                f"{doc_rel_path} — skipping fingerprint corroboration",
                file=sys.stderr,
            )
        elif prior != doc_fingerprint:
            errors.append(
                f"fingerprint mismatch: doc is {doc_fingerprint}, last 'generated' "
                f"ledger record was {prior} — content changed since generation"
            )

    passed = not errors
    if args.event == "generated":
        event = "generated" if passed else "failed"
    else:
        event = "consumed" if passed else "blocked"

    record = {
        "event": event,
        "doc": doc_rel_path,
        "session": session,
        "branch": branch,
        "commit": commit,
        "actor": actor,
        "agent": args.agent,
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fingerprint": doc_fingerprint,
    }
    append_ledger_event(args.ledger_dir, session, record)

    if not passed:
        print(f"verify_doc_template: {event.upper()}", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print(f"verify_doc_template: {event} (fingerprint {doc_fingerprint})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
