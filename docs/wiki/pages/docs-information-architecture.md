# Docs information architecture

> **Audience:** `dev`
> **Concept:** how Sartor's docs are organized, kept honest, and published — the
> user/dev tree split; the explicit publication registry; the moved-paths policy for
> frozen records; the shared corpus that powers the doc lints; and the doc-writing
> skill that orders the rules so no lint is missed.
> **Sources:** [`docs/dev/docs-ia-design.md`](../../dev/docs-ia-design.md) (design,
> tree, link policy, lints, ladders) · [`docs/dev/documentation-architecture.md`](../../dev/documentation-architecture.md)
> (L0–L3 chain, gates, `DOC-STATUS`) · [`scripts/doc_registry.py`](../../../scripts/doc_registry.py) (publication registry,
> record classes) · [`scripts/docs_move.py`](../../../scripts/docs_move.py) (link rewriting,
> moved-paths map) · [`scripts/doc_corpus.py`](../../../scripts/doc_corpus.py) (shared
> corpus) · [`scripts/doc_lints.py`](../../../scripts/doc_lints.py) (the §5 lints) ·
> [`scripts/project_docs_to_mdx.py`](../../../scripts/project_docs_to_mdx.py) (projector,
> frontmatter, sourcing) · [`skills/doc-writing/SKILL.md`](../../../skills/doc-writing/SKILL.md) (the ordering).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md). This page references rules, not
> restates them; per D5, each rule's home governs.

---

## The one-way law: L0 → L1 → L2 → L3

Documentation obeys one binding rule: **the repo at git HEAD is the source of truth;
everything else is derived** `[synthesis]`.

The four-layer chain (`documentation-architecture.md` "The source chain") is:

1. **L0: Governance** — `vision.md`, `docs/governance/charter.md` / `enforcement.md` / `metrics.md` — the north star. Every fact answers upstream to this layer.
2. **L1: Authored source** — tracked markdown files with Purpose/Audience/Authoritative-for headers, edited in the repo. The one home per fact. The published set is `scripts/doc_registry.py:PUBLISHED` `[synthesis]`.
3. **L2: Compiled substrate** — the wiki at `docs/wiki/pages/`, synthesized from L1 via `/wiki-ingest`, cited with `path:line` anchors, and stamped with `[synthesis]` tags.
4. **L3: Projection** — the Fumadocs site, a pure function of L1 via `scripts/project_docs_to_mdx.py`, with frontmatter, nav order, and link rewrites (but no invented claims).

**Records are not L1.** Handoffs, diagnosis dossiers, reviews, perf records, and `docs/dev/archive/` are frozen history. `doc_registry.is_record()` identifies them; they are never published and never link-rewritten by `scripts/docs_move.py` `[synthesis]` (docs-ia-design §3).

## The docs tree: user and dev audiences, two ladders

A single principle organizes every published doc: **one audience tier per doc**. The tree is `docs/user/` (zero-technical-knowledge product docs) and `docs/dev/` (contributor + maintainer docs), plus root files. The user ladder and the dev ladder (D0–D5) each assume the previous rung as prerequisite. See [`docs/user/README.md`](../../user/README.md) and [`docs/dev/README.md`](../../dev/README.md) for the full ladders `[synthesis]` (docs-ia-design §4).

## Publication: the registry, not a convention

**Before Epic D, "published" had two conflicting definitions** (docs-ia-design §1, DX-05). Now there is one: `scripts/doc_registry.py:PUBLISHED` is the ordered list of every published doc with its tier. The projector publishes only registry entries; `check_doc_frontmatter.py` checks only them; `meta.json` is generated from them. A doc outside the registry is never published, whatever its header says `[synthesis]` (doc_registry.py preamble).

The record-path classes live in one place, [`scripts/doc_registry.py:RECORD_PREFIXES`](../../../scripts/doc_registry.py), with `CHANGELOG*.md` matched separately by `is_record`.

## Link policy: records frozen, live docs rewritten, moved-paths map

The link policy (`docs-ia-design.md` §3) has three parts:

1. **Records are never rewritten.** A handoff, diagnosis or perf record keeps the paths that were true when it was written `[synthesis]`.
2. **Live docs are rewritten by script, in the same commit as the move** via `scripts/docs_move.py`, which performs `git mv`s and rewrites relative links in live docs only `[synthesis]`.
3. **The moved-paths map keeps records green** without rewriting them. `docs/dev/moved-paths.json` (old → new) is written by `docs_move.py` and consulted by `check_doc_links.py` **only for links originating in a record**. When such a link's target is missing, it resolves through the map `[synthesis]` (docs_move.py docstring).

## Gates and enforcement: the shared corpus powers the lints

**One shared read, many checks.** `scripts/doc_corpus.py` does one pass: list tracked files (one `git ls-files`), read each doc once, expose the unfenced lines and the tracked-path set, and answer link-target existence from that set. `check_doc_links.py`, `check_doc_frontmatter.py`, `check_doc_single_home.py` and the §5 lints in `doc_lints.py` all read through it `[synthesis]` (doc_corpus.py docstring, docs-ia-design.md §5 intro).

**Lint coverage** (docs-ia-design.md §5, rows 5.1–5.9; doc_lints.py module docstring):

- **5.1 Publication registry:** One registry lists every published doc. `project_docs_to_mdx.py` publishes **only** entries; a record-path entry fails the gate.
- **5.2 Audience token:** Every registered doc's `**Audience:**` begins with `` `user` `` or `` `dev` ``.
- **5.3 Diátaxis type:** User-tier docs carry `**Type:**` (tutorial/how-to/reference/explanation). Presence is enforced; correctness is unenforced (judgment).
- **5.4 Wordmark:** Flag `sartor.` mid-sentence in published docs, excluding `docs/wiki/`, `docs/dev/reviews/`, records and `CHANGELOG*.md`; warn on the ambiguous end-of-sentence form.
- **5.5 Enumeration drift:** Gate steps, deterministic modules, subagents, charter clause ranges and the `docs/dev/tooling.md` roster — a doc that enumerates them must match the code, or link instead.
- **5.6 Banned words:** A block list and a warn list on the user tier.
- **5.7 Jargon + tracker IDs:** User tier: a closed acronym list must be expanded at first use; tracker IDs are blocked.
- **5.8 Wikilinks + charter clauses:** `[[wikilink]]` outside `docs/wiki/`, and a missing charter-clause heading or a citation past the last clause.
- **5.9 Single-home, widened (report-only, unenforced):** wiki pages that share a run of 25+ words with a published doc (the design says "~25 tokens"; `doc_lints.SHINGLE` counts words).

The gated lints run as pytest modules (`tests/test_doc_lints.py`), so they run in `python -m scripts.gate` and CI's required `quality` job (documentation-architecture.md "Gates").

## The doc-writing skill: order, don't restate

The skill at `skills/doc-writing/SKILL.md` **orders and invokes** the rules in a sequence. It restates none of them; each rule's single home is named at the step, and that home governs `[synthesis]` (SKILL.md preamble). The steps: pick tier and type; find the rung; write the header; cite, don't restate, code enumerations; register it; run and fix lints; add to `docs/dev/tooling.md` if new (SKILL.md "The order").

## Related

- [[llm-wiki-design]] — the wiki's SCHEMA and synthesis contract; the one-way law extends to the wiki (L1 → L2).
- [[governance-extraction]] — where the L0 layer came from; the constitutional separation from descriptive docs.
- [[code-module-map]] — the code side of what enumerations must match (charter clauses, deterministic modules).
- [[openapi-api-reference]] — published via the registry, not a separate path.
