"""Work-item backlog validator and board generator (schema per `docs/dev/work/SCHEMA.md`).

Vendored from `spolia` (`C:\\Dev\\spolia\\scripts\\work_items.py`), which built and
proved this design; adapted with one addition (`depends_on`, see below) — see
`docs/dev/work/SCHEMA.md` for the full rationale.

Two subcommands:

  check         Validate every file in `docs/dev/work/items/` and confirm
                `docs/dev/work/BOARD.md` matches what regenerating it now
                would produce. A malformed item file is a blocked gate
                (charter C-9 / `docs/dev/prov/SPEC.md` -- corrupted input
                surfaces as the first error, never silently skipped).
  board         Regenerate `docs/dev/work/BOARD.md` from the item/epic
                files (default: check only; `--write` rewrites the file).
                Refuses to run if `check`'s structural rules fail -- an ID
                collision or dangling reference would make the board
                silently wrong.

Wired into `scripts/gate.py` as its 5th step, alongside ruff/mypy/pytest.

Board comparison is newline-normalized text, never raw bytes. (Corrected
2026-08-12: this note used to claim `.gitattributes` had no `*.md` rule; it has
pinned `*.md text eol=lf` since the initial commit, so BOARD.md checks out LF
everywhere.) Normalizing is still correct as defense-in-depth: an editor can
save CRLF into any working-tree file regardless of checkout policy, and this
comparison reads the working tree -- the same class of bug
`scripts/verify_doc_template.py`'s `fingerprint` already fixed once. Coverage
of `.gitattributes` itself is now gated by
`tests/test_gitattributes_coverage.py` (charter C-11).

Board-staleness deferral (`docs/dev/work/BOARD_DEFERRAL.md`)
---------------------------------------------------------------------------
`check` normally fails whenever `BOARD.md` doesn't match a fresh render --
correct almost always, but `docs/dev/epic-a-chain-design-corrections.md`
§15.2 authorizes an explicit, named, epic-scoped exception: a chain epic may
defer `BOARD.md` regeneration to its close, filing items per-sprint without
regenerating the board each time. A well-formed `docs/dev/work/BOARD_DEFERRAL.md`
marker (fenced ```toml frontmatter naming `epic`, `declared`, and
`authorization`) is the ONLY thing that tolerates staleness -- there is no
separate flag to also set. Absent the marker, or if it is malformed (missing
or empty any of the three fields, invalid TOML, no fence), behavior is
byte-identical to no-deferral: `check()`'s `deferral_path` parameter defaults
to `None`, so nothing about this mechanism changes any existing caller unless
it opts in by passing the path. When a deferral IS exercised, `main()`'s
`check` output names it unmissably rather than printing a plain "OK" -- see
`check_with_deferral()`. `board --write` never reads the marker: it always
regenerates from source, regardless of whether staleness is currently being
tolerated.

A well-formed marker is not, on its own, proof that the epic it names is real
or still running -- an adversarial review flagged that `epic` is free text
nobody verified against actual backlog state, so `check_with_deferral()` also
cross-checks it: the named epic must match a real `docs/dev/work/items/*.md`
entry with `kind = "epic"` and `status != "closed"` (matched via that item's
declared `branches`, see `_find_deferral_epic()`), or the marker grants
nothing -- same fail-closed treatment as a structurally malformed marker, just
with a distinct error message so the CLI can tell the two apart. **What this
still does not verify** (deliberately, per C-12 -- declare the gap rather than
silently narrow it): that the *current* branch is actually a member of the
named epic. A marker naming a real, open epic that the working branch has
nothing to do with still passes today; closing that is out of scope here and
tracked as a future design-pass data point rather than solved by branch
introspection now.

Usage:

    python -m scripts.work_items check
    python -m scripts.work_items board
    python -m scripts.work_items board --write
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORK_DIR = _REPO_ROOT / "docs" / "dev" / "work"
_ITEMS_DIR = _WORK_DIR / "items"
_BOARD_PATH = _WORK_DIR / "BOARD.md"
_BOARD_DEFERRAL_PATH = _WORK_DIR / "BOARD_DEFERRAL.md"

_WIP_CEILING = 10
_STATUS_ORDER = ("open", "blocked", "deferred", "watching")
_VALID_STATUS = frozenset({*_STATUS_ORDER, "closed"})
_VALID_KIND = frozenset({"item", "epic"})
_VALID_OWNER = frozenset({"user", "agent"})
_KNOWN_KEYS = frozenset(
    {
        "schema",
        "id",
        "kind",
        "title",
        "status",
        "decision_owner",
        "blocked_on",
        "resolution",
        "epic",
        "depends_on",
        "branches",
        "refs",
        "summary",
        "verified_by",
        "closure_exception",
        "guardrail",
        "guardrail_deferred",
        "x",
    }
)

#: Charter **C-11** closure bar. Items closed BEFORE the bar was adopted (2026-08-05,
#: `feat/enforcement-first-governance`). Requiring `verified_by` retroactively would force
#: either fabricating artifacts for closures made before the rule existed, or 19 edits
#: asserting things nobody verified — both worse than the problem this bar solves.
#:
#: **This list is closed.** It is the exact set of `status = "closed"` ids at the adopting
#: commit, and `tests/test_work_items_closure_bar.py` fails if an id is added to it. A new
#: closure gets no grandfathering; that is the entire point. Same maintained-list +
#: audit-test shape as `tests/test_egress_allowlist.py`'s SANCTIONED_EGRESS_FILES.
_CLOSURE_BAR_GRANDFATHERED = frozenset(
    {1, 6, 11, 12, 13, 14, 15, 17, 21, 22, 26, 27, 28, 29, 31, 32, 33, 35, 44}
)

_FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
_FRONTMATTER_OPEN = "```toml"
_FRONTMATTER_CLOSE = "```"


@dataclass(frozen=True)
class Item:
    path: Path
    rel: str
    id: int
    kind: str
    title: str
    status: str
    decision_owner: str
    summary: str
    blocked_on: str | None
    resolution: str | None
    epic: int | None
    depends_on: tuple[int, ...]
    branches: tuple[str, ...]
    refs: tuple[str, ...]


@dataclass(frozen=True)
class ParsedFile:
    rel: str
    item_id: int | None
    item: Item | None
    errors: list[str]


@dataclass(frozen=True)
class BoardDeferral:
    """A validated `docs/dev/work/BOARD_DEFERRAL.md` marker. Its mere existence, well
    formed, is the entire exemption -- there is no separate boolean to also flip, so
    there is exactly one place to check and exactly one place to delete when the
    deferral ends (charter C-11: a mechanism with a second switch is a mechanism with
    a second way to leave it on by accident)."""

    epic: str
    declared: str
    authorization: str
    path: Path


def _split_frontmatter(content: str) -> str | None:
    """Return the raw TOML text inside a leading ```toml fence, or None if
    the file does not open with one."""
    lines = content.splitlines()
    if not lines or lines[0].rstrip() != _FRONTMATTER_OPEN:
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == _FRONTMATTER_CLOSE:
            return "\n".join(lines[1:i])
    return None


def _normalize_newlines(text: str) -> str:
    return "\n".join(text.splitlines())


def _rel(path: Path) -> str:
    """`path` relative to the repo root as a POSIX string, or `path` itself
    if it lies outside the repo root (e.g. a test's `tmp_path` fixture)."""
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_file(path: Path) -> ParsedFile:
    """Parse one item/epic file. `item` is None if the file could not be
    fully validated -- a malformed file blocks its own cross-file checks
    (dangling-epic, etc.) but never silently drops out of `errors`."""
    rel = _rel(path)
    errors: list[str] = []

    name_match = _FILENAME_RE.match(path.name)
    if name_match is None:
        errors.append(f"{rel}: filename does not match NNNN-slug.md")

    toml_text = _split_frontmatter(path.read_text(encoding="utf-8"))
    if toml_text is None:
        errors.append(f"{rel}: does not open with a ```toml fenced frontmatter block")
        return ParsedFile(rel=rel, item_id=None, item=None, errors=errors)

    try:
        data: dict[str, Any] = tomllib.loads(toml_text)
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{rel}: invalid TOML frontmatter: {exc}")
        return ParsedFile(rel=rel, item_id=None, item=None, errors=errors)

    unknown = set(data) - _KNOWN_KEYS
    if unknown:
        errors.append(f"{rel}: unrecognized frontmatter key(s): {', '.join(sorted(unknown))}")

    def require_str(key: str) -> str | None:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel}: missing or empty required field `{key}`")
            return None
        return value

    def require_int(key: str) -> int | None:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{rel}: missing or non-integer required field `{key}`")
            return None
        return value

    def optional_str(key: str) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            errors.append(f"{rel}: `{key}` must be a string")
            return None
        return value

    def optional_str_list(key: str) -> tuple[str, ...]:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"{rel}: `{key}` must be a list of strings")
            return ()
        return tuple(value)

    def optional_int_list(key: str) -> tuple[int, ...]:
        value = data.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(v, int) and not isinstance(v, bool) for v in value
        ):
            errors.append(f"{rel}: `{key}` must be a list of integers")
            return ()
        return tuple(value)

    schema = require_int("schema")
    item_id = require_int("id")
    kind = require_str("kind")
    title = require_str("title")
    status = require_str("status")
    decision_owner = require_str("decision_owner")
    summary = require_str("summary")

    if schema is not None and schema != 1:
        errors.append(f"{rel}: unsupported schema {schema} (expected 1)")
    if kind is not None and kind not in _VALID_KIND:
        errors.append(f"{rel}: kind must be one of {sorted(_VALID_KIND)}, got {kind!r}")
    if status is not None and status not in _VALID_STATUS:
        errors.append(f"{rel}: status must be one of {sorted(_VALID_STATUS)}, got {status!r}")
    if decision_owner is not None and decision_owner not in _VALID_OWNER:
        errors.append(
            f"{rel}: decision_owner must be one of {sorted(_VALID_OWNER)}, got {decision_owner!r}"
        )
    if summary is not None and len(summary) > 120:
        errors.append(f"{rel}: summary is {len(summary)} chars, exceeds the 120-char cap")

    if item_id is not None and name_match is not None:
        expected_prefix = f"{item_id:04d}"
        if name_match.group(1) != expected_prefix:
            errors.append(
                f"{rel}: filename prefix {name_match.group(1)} does not match id {item_id} "
                f"(expected {expected_prefix}-...)"
            )

    blocked_on = optional_str("blocked_on")
    if status in ("blocked", "deferred") and not blocked_on:
        errors.append(f"{rel}: status {status!r} requires a non-empty `blocked_on`")

    resolution = optional_str("resolution")
    if status == "closed" and not resolution:
        errors.append(f'{rel}: status "closed" requires a non-empty `resolution`')

    # --- charter C-11 closure bar ------------------------------------------------------
    # Prose in `resolution` alone is too easy to satisfy: three of epic 19's five closures
    # read as resolved while resting on "not reproduced" or on a fix for a DIFFERENT defect
    # with a matching symptom, and the one that came back (item 30) was one of the three.
    verified_by = optional_str_list("verified_by")
    closure_exception = optional_str("closure_exception")
    guardrail = optional_str("guardrail")
    guardrail_deferred = optional_str("guardrail_deferred")

    if (
        status == "closed"
        and item_id is not None
        and item_id not in _CLOSURE_BAR_GRANDFATHERED
        and not verified_by
        and not closure_exception
    ):
        errors.append(
            f'{rel}: status "closed" requires a non-empty `verified_by` naming a falsifiable '
            f"artifact (a test path, a gate, a guard, or a CI run id) — or a "
            f"`closure_exception` naming the owner who accepted the closure without one "
            f"(charter C-11)"
        )

    # An item carrying a `resolution` while NOT closed was closed once and reopened. C-11
    # makes that recognition the trigger: the branch that reopens it authors a mechanism,
    # or says plainly that it did not and why. Detectable from the file alone — no history.
    if status != "closed" and resolution and not guardrail and not guardrail_deferred:
        errors.append(
            f"{rel}: this item was closed and reopened (it carries `resolution` with status "
            f"{status!r}), so charter C-11 requires a `guardrail` naming the mechanism "
            f"authored in response — or `guardrail_deferred` stating plainly that none was "
            f"and why"
        )

    epic_raw = data.get("epic")
    epic: int | None = None
    if epic_raw is not None:
        if not isinstance(epic_raw, int) or isinstance(epic_raw, bool):
            errors.append(f"{rel}: `epic` must be an integer")
        else:
            epic = epic_raw
    if kind == "epic" and epic is not None:
        errors.append(f"{rel}: an epic must not itself set `epic` (nesting depth 1)")

    depends_on = optional_int_list("depends_on")
    branches = optional_str_list("branches")
    refs = optional_str_list("refs")

    if (
        errors
        or item_id is None
        or kind is None
        or title is None
        or status is None
        or decision_owner is None
        or summary is None
    ):
        return ParsedFile(rel=rel, item_id=item_id, item=None, errors=errors)

    item = Item(
        path=path,
        rel=rel,
        id=item_id,
        kind=kind,
        title=title,
        status=status,
        decision_owner=decision_owner,
        summary=summary,
        blocked_on=blocked_on,
        resolution=resolution,
        epic=epic,
        depends_on=depends_on,
        branches=branches,
        refs=refs,
    )
    return ParsedFile(rel=rel, item_id=item_id, item=item, errors=errors)


def structural_errors(items_dir: Path) -> tuple[dict[int, Item], list[str]]:
    """Parse every item file and run cross-file checks. Returns the map of
    cleanly-parsed items (by id) and the full error list -- per-file parse
    errors first, in filename order, then cross-file errors."""
    parsed = [parse_file(p) for p in sorted(items_dir.glob("*.md"))]

    errors: list[str] = []
    by_id: dict[int, list[str]] = {}
    for pf in parsed:
        if pf.item_id is not None:
            by_id.setdefault(pf.item_id, []).append(pf.rel)
    for item_id, paths in sorted(by_id.items()):
        if len(paths) > 1:
            errors.append(f"id {item_id} used by multiple files: {', '.join(paths)}")

    for pf in parsed:
        errors.extend(pf.errors)

    items = {pf.item.id: pf.item for pf in parsed if pf.item is not None}

    for item in items.values():
        if item.epic is None:
            continue
        parent = items.get(item.epic)
        if parent is None:
            errors.append(f"{item.rel}: epic {item.epic} not found")
        elif parent.kind != "epic":
            errors.append(f'{item.rel}: epic {item.epic} is not kind = "epic"')

    for item in items.values():
        for dep_id in item.depends_on:
            if dep_id not in items:
                errors.append(f"{item.rel}: depends_on {dep_id} not found")

    for epic in items.values():
        if epic.kind != "epic":
            continue
        children = [i for i in items.values() if i.epic == epic.id]
        if epic.status == "closed":
            open_children = [c.id for c in children if c.status != "closed"]
            if open_children:
                errors.append(f"{epic.rel}: epic is closed but children {open_children} are not")

    return items, errors


def render_board(items: dict[int, Item]) -> str:
    # An item filed under an epic renders only inside that epic's own section --
    # showing it in both places would be the exact duplicated-listing drift
    # this schema exists to remove.
    top_level = sorted(
        (i for i in items.values() if i.kind == "item" and i.epic is None), key=lambda i: i.id
    )
    epics = sorted((i for i in items.values() if i.kind == "epic"), key=lambda i: i.id)
    children_of: dict[int, list[Item]] = {e.id: [] for e in epics}
    for item in items.values():
        if item.epic is not None and item.epic in children_of:
            children_of[item.epic].append(item)
    for kids in children_of.values():
        kids.sort(key=lambda i: i.id)

    open_count = sum(1 for i in items.values() if i.status == "open")
    status_counts = {s: sum(1 for i in top_level if i.status == s) for s in _STATUS_ORDER}
    closed_items = sorted((i for i in items.values() if i.status == "closed"), key=lambda i: i.id)

    ceiling_flag = "" if open_count <= _WIP_CEILING else " -- OVER"
    lines: list[str] = [
        "# Work-item board",
        "",
        "Generated from `docs/dev/work/items/` by `scripts/work_items.py` -- "
        "never hand-edited. Regenerate with `python -m scripts.work_items board --write`.",
        "",
        f"**Open {open_count} / {_WIP_CEILING} ceiling{ceiling_flag}** | "
        f"Blocked {status_counts['blocked']} | "
        f"Deferred {status_counts['deferred']} | "
        f"Watching {status_counts['watching']} | "
        f"Epics {len(epics)} | "
        f"Closed {len(closed_items)}",
    ]

    for status in _STATUS_ORDER:
        lines.append("")
        lines.append(f"## {status.capitalize()}")
        group = [i for i in top_level if i.status == status]
        lines.append("")
        if not group:
            lines.append("None.")
        else:
            lines.extend(_render_item_line(i) for i in group)

    lines.append("")
    lines.append("## Epics")
    if not epics:
        lines.append("")
        lines.append("None.")
    for epic in epics:
        lines.append("")
        lines.append(f"### {epic.id} -- {epic.title} ({epic.status})")
        lines.append("")
        lines.append(epic.summary)
        kids = children_of[epic.id]
        lines.append("")
        if kids:
            lines.extend(_render_item_line(child) for child in kids)
        else:
            lines.append("No children filed yet.")

    lines.append("")
    lines.append(f"## Closed ({len(closed_items)})")
    lines.append("")
    if not closed_items:
        lines.append("None.")
    else:
        lines.extend(f"- {i.id} -- {i.title} ({i.resolution})" for i in closed_items)

    return "\n".join(lines) + "\n"


def _render_item_line(item: Item) -> str:
    line = f"- **{item.id}** -- {item.title} (`{item.decision_owner}`) -- {item.summary}"
    if item.depends_on:
        line += f" [depends on: {', '.join(str(d) for d in item.depends_on)}]"
    if item.blocked_on:
        line += f" [blocked on: {item.blocked_on}]"
    return line


_REGEN_HINT = "run `python -m scripts.work_items board --write`"

#: Required fields of a well-formed `BOARD_DEFERRAL.md`. All three are non-empty
#: strings or the marker grants nothing -- see `_read_board_deferral()`.
_DEFERRAL_REQUIRED_FIELDS = ("epic", "declared", "authorization")


def _board_status(board_path: Path, generated: str) -> str | None:
    """An error message if `board_path` doesn't match `generated`, else None."""
    if not board_path.is_file():
        return f"{_rel(board_path)} does not exist -- {_REGEN_HINT}"
    existing = board_path.read_text(encoding="utf-8")
    if _normalize_newlines(existing) != _normalize_newlines(generated):
        return f"BOARD.md is stale -- {_REGEN_HINT}"
    return None


def _read_board_deferral(deferral_path: Path | None) -> BoardDeferral | None:
    """Parse and validate a `BOARD_DEFERRAL.md` marker. Returns `None` on ANY
    problem -- no path given, file missing, no ```toml fence, invalid TOML, or any
    of `epic` / `declared` / `authorization` absent or empty -- so a malformed
    marker is indistinguishable from no marker at all: fail closed on bad input,
    never fail open. This mirrors `parse_file()`'s own required-field checks
    rather than inventing a second validation shape."""
    if deferral_path is None or not deferral_path.is_file():
        return None
    toml_text = _split_frontmatter(deferral_path.read_text(encoding="utf-8"))
    if toml_text is None:
        return None
    try:
        data: dict[str, Any] = tomllib.loads(toml_text)
    except tomllib.TOMLDecodeError:
        return None

    values: dict[str, str] = {}
    for key in _DEFERRAL_REQUIRED_FIELDS:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            return None
        values[key] = value.strip()

    return BoardDeferral(
        epic=values["epic"],
        declared=values["declared"],
        authorization=values["authorization"],
        path=deferral_path,
    )


def _deferral_names_branch(deferral_epic: str, item: Item) -> bool:
    """True if `item` (expected to be `kind = "epic"`) is the epic
    `BoardDeferral.epic` names. `BoardDeferral.epic` is free prose (e.g.
    `"epic/a-app-core (board item 36 -- ...)"`, the real marker's current
    value) -- there is no structured id field to compare directly. Every real
    epic item declares its `branches`, though, so matching on whether a
    declared branch string appears literally inside the marker's free-text
    `epic` field ties the claim to something nobody hand-types into the
    marker in isolation: the branch name has to already be true of a real
    backlog item."""
    return any(branch and branch in deferral_epic for branch in item.branches)


def _find_deferral_epic(
    deferral: BoardDeferral, items: dict[int, Item]
) -> tuple[Item | None, str | None]:
    """Cross-check `BoardDeferral.epic` against the real backlog. Returns
    `(matched_item, None)` if a `kind = "epic"` item with `status != "closed"`
    matches (see `_deferral_names_branch`); otherwise `(None, message)` where
    `message` distinguishes "no epic in the backlog matches this claim at
    all" from "it matches, but that epic is closed" -- two different failure
    shapes a fixer needs to tell apart, even though both mean the deferral
    grants nothing."""
    candidates = sorted(
        (
            i
            for i in items.values()
            if i.kind == "epic" and _deferral_names_branch(deferral.epic, i)
        ),
        key=lambda i: i.id,
    )
    if not candidates:
        return None, (
            f'{_rel(deferral.path)}: names epic {deferral.epic!r}, but no `kind = "epic"` item '
            f"in the backlog declares a matching `branches` entry -- deferral grants nothing "
            f"(the claimed epic is not a real backlog item)"
        )
    open_candidates = [i for i in candidates if i.status != "closed"]
    if not open_candidates:
        ids = ", ".join(str(i.id) for i in candidates)
        if len(candidates) > 1:
            return None, (
                f"{_rel(deferral.path)}: names epic {deferral.epic!r}, which matches backlog "
                f'items {ids}, but they are all status = "closed" -- deferral grants nothing '
                f"(the epic it names is not open)"
            )
        return None, (
            f"{_rel(deferral.path)}: names epic {deferral.epic!r}, which matches backlog "
            f'item {ids}, but it is status = "closed" -- deferral grants nothing '
            f"(the epic it names is not open)"
        )
    return open_candidates[0], None


def check_with_deferral(
    items_dir: Path,
    board_path: Path,
    deferral_path: Path | None = None,
) -> tuple[list[str], BoardDeferral | None]:
    """The full `check` rule set, reporting whether a `BoardDeferral` was actually
    EXERCISED -- i.e. it suppressed a genuine staleness failure -- not merely
    whether a marker file exists. Structural/cross-file validation always runs
    unconditionally; only the BOARD.md-staleness rule is ever tolerated, and only
    when `board_path` really is stale AND `deferral_path` names a well-formed
    marker (`_read_board_deferral`) whose `epic` field also names a real, open
    `kind = "epic"` backlog item (`_find_deferral_epic`). Returns `(errors,
    None)` whenever no deferral applied: no `deferral_path` given, no marker, a
    malformed marker, a marker naming an epic that isn't real or isn't open, or
    BOARD.md was not stale to begin with. Omitting `deferral_path` (the
    default) reproduces pre-deferral behavior byte-for-byte -- nothing about
    this mechanism can affect a caller that doesn't opt in."""
    items, errors = structural_errors(items_dir)
    if errors:
        return errors, None

    stale = _board_status(board_path, render_board(items))
    if stale is None:
        return errors, None

    deferral = _read_board_deferral(deferral_path)
    if deferral is None:
        errors.append(stale)
        return errors, None

    _matched_epic, epic_error = _find_deferral_epic(deferral, items)
    if epic_error is not None:
        errors.append(stale)
        errors.append(epic_error)
        return errors, None

    return errors, deferral


def check(items_dir: Path, board_path: Path, deferral_path: Path | None = None) -> list[str]:
    """The full `check` rule set: structural/cross-file validation, then
    (only if that passed) board staleness -- a broken backlog can't produce
    a trustworthy board to compare against. Thin wrapper over
    `check_with_deferral()` for callers that only need the error list; see that
    function for the `(errors, deferral)` shape the CLI uses to print an
    unmissable deferral notice rather than a quietly-green run."""
    errors, _deferral = check_with_deferral(items_dir, board_path, deferral_path)
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Validate items/ and check BOARD.md is up to date.")
    board_parser = subparsers.add_parser("board", help="Regenerate docs/dev/work/BOARD.md.")
    board_parser.add_argument(
        "--write",
        action="store_true",
        help="Write the regenerated board instead of just checking it.",
    )
    args = parser.parse_args(argv)

    if not _ITEMS_DIR.is_dir():
        print(f"work_items: items directory not found: {_ITEMS_DIR}", file=sys.stderr)
        return 2

    if args.command == "check":
        errors, deferral = check_with_deferral(_ITEMS_DIR, _BOARD_PATH, _BOARD_DEFERRAL_PATH)
        if errors:
            print("work_items: FAILED", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 1
        count = len(list(_ITEMS_DIR.glob("*.md")))
        if deferral is not None:
            print(
                f"work_items: OK ({count} files) -- BOARD.md staleness DEFERRED for "
                f"{deferral.epic} per {_rel(deferral.path)} ({deferral.authorization}) "
                f"-- NOT actually current"
            )
        else:
            print(f"work_items: OK ({count} files)")
        return 0

    # args.command == "board" -- the deferral marker is deliberately never consulted
    # here, in either mode. `--write` always regenerates from source regardless of
    # staleness, so a deferral can never make it produce a wrong board. The
    # read-only mode (below) intentionally stays exactly as strict as `check` was
    # BEFORE the deferral mechanism existed -- `board` is a manual convenience
    # command, not gate-wired (only `check` is, per scripts/gate.py), so leaving it
    # unconditionally strict costs nothing and gives a second, deferral-blind way to
    # see the real staleness state at any time.
    items, errors = structural_errors(_ITEMS_DIR)
    if errors:
        print("work_items: board FAILED -- fix `check` errors first", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    generated = render_board(items)
    if args.write:
        _BOARD_PATH.write_text(generated, encoding="utf-8", newline="\n")
        print(f"work_items: wrote {_rel(_BOARD_PATH)}")
        return 0

    stale = _board_status(_BOARD_PATH, generated)
    if stale is not None:
        print(f"work_items: {stale}", file=sys.stderr)
        return 1
    print("work_items: BOARD.md is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
