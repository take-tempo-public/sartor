# Wiki SCHEMA — conventions for `docs/wiki/`

> **Purpose:** the rulebook for callback.'s committed LLM-wiki — what each file is
> for, how pages are written and grounded, and how the wiki stays honest against the
> code. It governs the wiki; it is **not** a second copy of the project's rules.
> **Audience:** any human or LLM agent reading, querying, or ingesting into the wiki.
> The `/wiki-*` ops that read and write here land next (see
> [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5); until then the wiki is
> authored by hand.
> **Authoritative for:** the wiki's file layout, the page + grounding conventions, and
> the git-as-engine source model. It is **NOT** authoritative for the project's
> operating rules — those live in [`../../AGENTS.md`](../../AGENTS.md) /
> [`../../CLAUDE.md`](../../CLAUDE.md) / [`../../vision.md`](../../vision.md) and are
> **referenced** here, never duplicated (design fork D5).

---

## What this wiki is

A committed, synthesized knowledge layer over the repository, following the LLM-wiki
pattern. The repo **at git HEAD is the source of truth**; the wiki is a *compiled
artifact* that links back to it. You read the wiki for the map and drop to the source
(code, or the docs it cites) for full fidelity. Because it is committed in-repo it is
versioned, reviewable, and servable to an assistant — and its staleness is
*measurable* (the saved ingest SHA vs. HEAD).

This is the project's own grounding contract turned on its documentation: the wiki may
**select, condense, and connect** what the sources say, but it may not assert beyond
them. `raw / source` is to `wiki page` as the source résumé is to a generated bullet —
synthesis may not invent past its source. See [`overview.md`](overview.md) for the
system this wiki describes.

## The contract lives elsewhere (D5)

The project's **binding rules** are stated **once**, in their canonical homes, and the
wiki only **cites** them:

- [`../../AGENTS.md`](../../AGENTS.md) — the universal AI-agent contract: the
  `_safe_username` / `_within` security gate, the deterministic / LLM boundary, branch
  + commit conventions, the `PROMPT_VERSION`-bump discipline, and the "what NOT to do"
  list.
- [`../../CLAUDE.md`](../../CLAUDE.md) — Claude-Code-specific overrides (hooks, the
  plan-mode workflow, the skill catalog).
- [`../../vision.md`](../../vision.md) + the 10 Principles — the product north-star:
  what callback. is *for* and what it must never do.

The wiki does not restate these. **On any conflict, the canonical docs win** and the
wiki is the thing that is wrong (file it back via a `/wiki-*` op once those land).

## File layout

| File | What it is |
|---|---|
| [`SCHEMA.md`](SCHEMA.md) | This file — wiki conventions, grounding rule, source model. |
| [`index.md`](index.md) | One-line summary per page; doubles as the map the root [`llms.txt`](../../llms.txt) points at. |
| [`overview.md`](overview.md) | The wiki's front door — a one-page orientation, seeded from and deferring to [`../system-model.md`](../system-model.md). |
| [`log.md`](log.md) | Append-only record of every ingest / lint run. |
| `.last_ingest_sha` | The codebase-variant diff checkpoint (see "Source model"). |
| `pages/` | Flat, slug-named synthesized pages. **Empty until ingest** (steps 4 + WS-4b). |

## Page conventions

- **One concept per page.** Pages live flat in `pages/`, named in kebab-case
  (`context-set-contract.md`, `llm-routing.md`).
- **Backlinks.** Relate pages with `[[double-bracket]]` links to other page slugs;
  links are bidirectional — a page names what it depends on and what depends on it.
- **Grounding for code claims.** Cite code as `path:line` (e.g.
  `analyzer.py:SYSTEM_PROMPT`) so a reader can verify the claim at its source. Prefer a
  symbol or anchor over a bare line number when one exists — line numbers drift.
- **Mark synthesis.** Tag a statement that is *concluded* rather than quoted with
  `[synthesis]`, so a later audit knows to fact-check it against its cited sources.

## The one grounding rule

> A wiki page may not assert anything its cited sources do not support.

This is the load-bearing invariant. The wiki is *lossy synthesis*; the sources (code
at HEAD, the living docs, and — when it exists — `raw/`) are *ground truth*. An LLM is
an unreliable narrator of its own synthesis: with no source to falsify against, a
synthesis error silently becomes a "fact." Grounding (`[[links]]` + `path:line` cites +
quote-matching) is what keeps that from happening.

## Source model (git-as-engine)

The repo at **git HEAD is the source**; the wiki is never a copy of the code. Ingest is
**diff-driven**: `git diff --name-status <.last_ingest_sha> HEAD` selects only changed
files, the affected pages + backlinks are updated, and the checkpoint is advanced.

- `.last_ingest_sha` holds the 40-character git SHA of the last successful code ingest.
- An **empty or sentinel** `.last_ingest_sha` (no 40-char SHA present) means **no
  ingest has run yet** → the next ingest is a **full cold pass** over the repo. That is
  the seeded state of this skeleton.
- Cold first ingest = one whole-repo pass (chunked per module). Steady state = tiny
  per-branch diffs → cheap. Queries read the small curated wiki, not the repo.

## The `raw/` constitutional layer (not yet present)

`raw/` is reserved for **prescriptive, externally-homeless** sources — the north-star
material everything downstream must stay consistent with (durable design rationale,
point-in-time notes, external references) that git cannot otherwise track as a living
doc. It **starts at zero**: in a codebase git already *is* a raw/ layer (every commit
is an immutable, diffable snapshot with provenance), so `raw/` only earns its place for
knowledge git can't see. It is introduced by the later, gated Governance-extraction
branch — not here. Copying a live git-tracked doc into `raw/` would be pure duplication
and rot; don't.

## Ops

Read, query, ingest, lint, and audit are **`/wiki-*` Claude Code skills**, adapted from
`kfchou/wiki-skills`, landing in the next branch (`feat/wiki-skills`, WS-4a step 3).
Trigger is a **manual** skill invocation plus a lightweight commit-time freshness
*reminder* (not auto-ingest — per-commit LLM cost); `wiki-lint` runs periodically and
as a pre-release gate. Every run appends to [`log.md`](log.md).

## Status

**Skeleton only.** `pages/` is empty; [`overview.md`](overview.md) is the one seeded
entry. Population is later branches — see
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5 (WS-4a steps 3–4 + WS-4b).
