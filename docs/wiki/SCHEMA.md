# Wiki SCHEMA — conventions for `docs/wiki/`

> **Purpose:** the rulebook for sartor.'s committed LLM-wiki — what each file is
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
  what sartor. is *for* and what it must never do.

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
| `pages/` | Flat, slug-named synthesized pages. Populated by ingest — the excellence-walk content pass (WS-4a step 4) + the code cold-ingest (WS-4b). |

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

## Audience tag

Every content page carries a machine-parseable **audience tier** — `user` or `dev` —
as a line in its blockquote header:

```
> **Audience:** `dev`
```

or, with optional human prose after an em-dash:

```
> **Audience:** `user` — anyone meeting the project.
```

The parse target is the **backtick-wrapped token** immediately after `**Audience:**`
(`user` or `dev`); any prose after the em-dash is for human readers only. This is the
boundary the planned doc-grounded assistant's **access / disclosure plane** gates on —
the `user`/`dev` toggle sets which tiers a question may reach, and `dev`-tier content
is never surfaced to a `user`-scoped turn. Authored here **once**, because the same
boundary serves three consumers: the assistant's access plane, the Sprint-6.5
education user/dev split, and the later governance extraction. The WHY lives in
[`../dev/memory-architecture.md`](../dev/memory-architecture.md) (decision #2 + the
access plane) — referenced, not restated (D5).

**Blanket path→audience rules** — a page's tier follows the source it describes:

| Source it describes | Tier |
|---|---|
| code (`*.py`, `static/`, `templates/`), `docs/dev/`, `evals/`, `dashboard/` | `dev` |
| `README.md`, `docs/install.md`, `docs/walkthrough*.md`, `vision.md`, wiki `overview.md` | `user` |

[`overview.md`](overview.md) (the front door) plus the five Sprint-6.5 education guides
under `pages/` (`using-sartor`, `tailoring-a-resume`, `career-corpus`,
`resume-templates`, `candidate-memory`) are the `user`-tier pages — authored INTO the
wiki by `feat/education-tailor-corpus-wizard`. Infra files (`index.md`, `log.md`, this
`SCHEMA.md`, `.last_ingest_sha`) are wiki meta, not retrieval Units, and are **not**
stamped.

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

Read, query, ingest, lint, audit, and **self-update** are **`/wiki-*` Claude Code
skills**, adapted from `kfchou/wiki-skills`, landing in the next branch
(`feat/wiki-skills`, WS-4a step 3). Trigger is a **manual** skill invocation plus a
lightweight commit-time freshness *reminder* (not auto-ingest — per-commit LLM cost);
`wiki-lint` runs periodically and as a pre-release gate. Every run appends to
[`log.md`](log.md).

`wiki-self-update` is the **self-documenting loop**: a bounded, cost-aware Haiku
diff-pass that composes the above ops — it delegates per-page synthesis to a `wiki-scribe`
subagent and a per-page adversarial grounding audit to a separate `wiki-grounding-auditor`
subagent (author ≠ auditor), runs `wiki-lint` as the deterministic gate, advances
`.last_ingest_sha`, and **presents a reviewable diff — it never auto-commits**. Its trigger
is a **bounded checkpoint** (branch close-out / pre-tag), not a scheduler, and the freshness
reminder escalates its message past a drift threshold to point at it. The design is
[`../dev/self-documenting-loop-design.md`](../dev/self-documenting-loop-design.md); the
cross-document link/cite checker stays a **separate** follow-on (this loop is
`docs/wiki/`-scoped only).

## Status

**Populated.** `pages/` carries the excellence-walk content pages (WS-4a step 4), the
code-architecture pages (WS-4b code cold-ingest), and the Sprint-6.5 user-facing
education guides (`feat/education-tailor-corpus-wizard`, hand-authored). `.last_ingest_sha`
holds the HEAD the *code* pass was authored against — the education sweep was a content
pass and deliberately did not advance it. The `user`-tier pages are
[`overview.md`](overview.md) plus the five education guides under `pages/`. See
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5 and [`log.md`](log.md) for the
record.
