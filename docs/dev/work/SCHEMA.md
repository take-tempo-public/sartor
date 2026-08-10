<!-- provenance: schema=1 session=2db3a371-1d98-4695-9e1c-fbdd2ac51d2d branch=chore/work-item-tracking commit=fbc160f actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-28 -->

# Work-item schema (schema 1)

One page. Defines the item/epic file format, the frontmatter vocabulary, and
the validation rules that `scripts/work_items.py` and `docs/dev/work/BOARD.md`
implement. Vendored from `spolia` (`C:\Dev\spolia`, same parent directory),
where this design was built and proved through 2 days of live use; sibling to
`docs/dev/prov/SPEC.md`, which this doc mirrors in shape (spolia's own
`[x]` escape-hatch field was written explicitly anticipating this vendoring —
see that project's `docs/dev/work/SCHEMA.md:57`).

Replaces the prose Carry-forward ledger in `RELEASE_CHECKLIST.md` as the
backlog's structured source of truth for **live** items. Closed/resolved
history is not migrated — it stays exactly where it is (git history,
`RELEASE_CHECKLIST.md`'s Resolved archive) and gets cited via `refs` when a
new item needs to point at it.

Design constraints (non-negotiable, inherited from spolia's own source):
generic names, self-contained, each part usable independently, stdlib only,
no daemons/databases — graphs (children of an epic, the board) are derived on
demand by joining files, never stored.

## 1. Item and epic files

One file per item or epic, at `docs/dev/work/items/<NNNN>-<slug>.md`, `NNNN`
the zero-padded `id`. The numeric prefix is parsed as `id` and must match the
frontmatter — that is the only naming rule enforced. `<slug>` is a mutable
label; correcting it is not a schema violation and does not change `id`.

Items and epics share one file, one directory, and one integer ID namespace
(`kind` distinguishes them) — a shared namespace is what lets an item be
promoted to an epic without a cross-namespace ID change or a stale reference.
`id` is canonical and immutable once filed: never reused, even after a file
is deleted or an item closes. **This is a fresh namespace, independent of the
PX-/F-/C-/D-/W-/O- numbering schemes elsewhere in this repo** — a clean
break, not an attempt to unify them. When a new item is the live-work
counterpart of a legacy PX/F-numbered finding, cite the legacy id in `refs`
or the body; never reuse it as this schema's `id`.

**Nesting depth is 1.** A file with `kind = "epic"` must not itself set
`epic`. An epic's children are *derived* by scanning every other file's
`epic` field — an epic file never lists its own children. Two files agreeing
on a child list is exactly the drift class this schema exists to remove.

## 2. Frontmatter

A fenced ` ```toml ` block, first thing in the file, parsed with stdlib
`tomllib`. Fenced rather than a bare `+++`/`---` block so item files stay
parseable by generic Markdown tooling (including `scripts/verify_doc_template.py`'s
own heading parser, which already skips fenced code) without adding a second,
incompatible delimiter convention.

| field | type | required | notes |
|---|---|---|---|
| `schema` | int | yes | this file's format version, currently `1` |
| `id` | int | yes | canonical, immutable, never reused |
| `kind` | str | yes | `"item"` \| `"epic"` |
| `title` | str | yes | short |
| `status` | str | yes | `"open"` \| `"blocked"` \| `"deferred"` \| `"watching"` \| `"closed"` |
| `decision_owner` | str | yes | `"user"` \| `"agent"` — the highest-value field: distinguishes "an agent can proceed" from "blocked on a human decision" |
| `blocked_on` | str | when `status` is `"blocked"` or `"deferred"` | what the block is, one line — `decision_owner` names *who*, this names *what on* |
| `resolution` | str | when `status` is `"closed"` | why it closed |
| `epic` | int | no | upward pointer to a parent `kind = "epic"` file's `id` |
| `depends_on` | array of int | no | **sartor addition, not in spolia's schema.** Peer-level sequencing (item A can't start before item B), distinct from `epic`'s parent/child relationship. Each id, if set, must refer to an existing file — checked the same way `epic` is. Does not block closing; it is sequencing information, not a closure gate. Added because sartor's own `RELEASE_ARC.md` history showed real information loss from ad-hoc peer dependency notation (an arrow-suffix convention used in one phase only, a single unrepeated "Blocked by/Blocks" pair) — see the branch that authored this schema for the fuller rationale. |
| `branches` | array of str | no | a record, not a reference — never checked against git, branches die |
| `refs` | array of str | no | doc/path pointers (e.g. `"blueprints/diagnostics.py:817-820"`) — not existence-checked |
| `summary` | str | yes | one line, **hard-capped at 120 characters** |
| `verified_by` | array of str | **when `status` is `"closed"`** (unless `closure_exception`) | **Charter C-11 closure bar.** A falsifiable artifact that would fail without the fix: a test path, a gate, a guard, or a CI run id. Prose belongs in `resolution`; this field is for the thing someone else can re-run. Not existence-checked — the gate enforces that a claim was *made*, not that it is true (stated limit, C-0) |
| `closure_exception` | str | alternative to `verified_by` | The escape, deliberately **named and attributed**: who accepted a closure with no falsifiable artifact, and when. Silent exceptions are the failure mode; a visible one in the diff is the signal |
| `guardrail` | str | **when the item carries `resolution` but is not `closed`** | i.e. it was closed once and **reopened**. Charter C-11: recognizing a recurrence obligates a *mechanism*, and this names it. A note, a memory, or a ledger row is not a mechanism |
| `guardrail_deferred` | str | alternative to `guardrail` | Says plainly that no mechanism was authored, and why. C-11 permits "none was possible"; it forbids leaving that implied |
| `[x]` | table | no | opaque namespace, ignored wholesale by the validator — an escape hatch for a field this schema doesn't have, without forking the script |

No other top-level key is permitted outside `[x]`.

**The C-11 closure bar is grandfathered, once.** `scripts/work_items._CLOSURE_BAR_GRANDFATHERED`
holds the exact set of ids that were already `closed` when the bar was adopted (2026-08-05).
Requiring `verified_by` retroactively would mean either fabricating artifacts or asserting
things nobody verified. **The list is closed** —
`tests/test_work_items_closure_bar.py::TestGrandfatherListIsClosed` pins its membership
exactly, so adding an id requires editing that test in the same diff. New closures get no
grandfathering; that is the entire point.

**Item files carry no `<!-- provenance -->` HTML comment stamp.** The
frontmatter already carries the file's own identity; a second, differently-shaped
metadata block on the same file is redundant. This document does carry one, per
`docs/dev/prov/SPEC.md` §1 — `SCHEMA.md` is prose, not a generated or migrated
record.

## 3. Body

Free-form prose, plus one required section, `## Updates`.

**The body's description is append-only.** Never rewrite a filed item's
description to reflect new understanding — append a dated block instead:

```markdown
## Updates

### 2026-07-28 — filed during chore/work-item-tracking

...
```

This binds the prose description only. Frontmatter fields — `status`, `epic`,
`depends_on`, `branches`, `decision_owner` — are mutable by definition;
updating them is not an append-only violation. There is no `updated`
timestamp field: an item's last-touched date is derived by parsing the most
recent `### YYYY-MM-DD` block under `## Updates`, never stored redundantly.

**An item or epic never restates scope that a design doc already owns — it
points**, via `refs`. The 120-character `summary` cap exists specifically to
make a third copy of a design doc's table structurally impossible.

## 4. Validation

`python -m scripts.work_items check` (see the script's own docstring for the
full CLI) enforces, over every file in `docs/dev/work/items/`:

- filename numeric prefix parses and matches frontmatter `id`
- no duplicate `id`
- `epic`, if set, refers to an existing file with `kind = "epic"`
- `depends_on`, if set, refers only to ids that exist (any kind)
- nesting depth 1 (an epic does not itself set `epic`)
- an epic is not `closed` while any child is non-terminal (open, blocked,
  deferred, or watching)
- `closed` requires a non-empty `resolution`
- `blocked` or `deferred` requires a non-empty `blocked_on`
- `decision_owner` is present and is exactly `"user"` or `"agent"`
- `status` is one of the five defined values
- `summary` is present and ≤120 characters
- no unrecognized top-level frontmatter key outside `[x]`
- `docs/dev/work/BOARD.md` matches what regenerating it now would produce
  (compared as decoded, newline-normalized text — never raw bytes, since this
  repo's markdown is CRLF on a local Windows checkout and LF in CI)

A file that fails to parse as TOML, or is missing a required field, is
**a blocked gate** — surfaced as the check's first-reported error and the run
stops there, the same rule `docs/dev/prov/SPEC.md` §5 applies to a corrupted
handoff and charter **C-9** applies to a corrupted pointer: never silently
skip or reconstruct a malformed record.

`python -m scripts.work_items board --write` regenerates `docs/dev/work/BOARD.md`
from the item/epic files. **`board` refuses to run when `check` fails** — an ID
collision or dangling reference would make the generated board silently wrong,
so the two subcommands are independently invocable but not independently
correct; state this explicitly rather than let it surprise on discovery.

## 5. WIP ceiling

**10**, counting `status = "open"` items only (`blocked`/`deferred`/`watching`
items occupy no active slot) — the same number charter **W-1.4** already uses
for the ~8–10 reduction-sprint threshold, so the two stay in agreement rather
than drifting into two different ceilings for the same concern. `BOARD.md`
prints the count against the ceiling. Advisory only — exceeding it never
fails `check` or the gate; it is a prompt to flag a reduction sprint, per the
existing W-1.4 convention.

## 6. Workflow

1. **Filing.** File a new item the turn you learn it — not at branch
   close-out — per charter **C-8** ("durable before deep"). Allocate the
   next unused `id`.
2. **Working an item.** Append to `## Updates`, adjust frontmatter (`status`,
   `blocked_on`, `epic`, `depends_on`, `branches`) as understanding changes.
   Never rewrite the existing description.
3. **Closing an item.** Set `status = "closed"` and fill `resolution`.
4. **Before every gate run.** Regenerate the board:
   `python -m scripts.work_items board --write`. A stale board fails `check`
   with that exact command in its error output.

## 7. Relationship to `RELEASE_ARC.md` / `RELEASE_CHECKLIST.md`

`RELEASE_ARC.md`'s structured tables (version map, phase table, window map)
and `RELEASE_CHECKLIST.md`'s Resolved archive are unaffected — they stay
exactly as they are. What this schema replaces is the **live** portion of
`RELEASE_CHECKLIST.md`'s Carry-forward ledger and `RELEASE_ARC.md`'s
"Individual branch sequence" prose-narrative for **not-yet-DONE** steps only;
both documents now point at `docs/dev/work/BOARD.md` rather than restating
current state inline. Charter **W-1.4** names this relocation with a single
written rationale line at the clause itself (not the full C-0…C-9 amendment
ceremony — W-1.4 is a working-model clause, not a constitutional one) per
`docs/governance/charter.md`'s own amendment-ceremony section.
