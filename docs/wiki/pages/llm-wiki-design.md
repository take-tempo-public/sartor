# Why the wiki is shaped this way (WS-4 design)

> **Audience:** `dev`
> **Concept:** the design rationale behind this wiki — the pattern it adapts, the
> source-model decision, why a `raw/` layer exists at all, and why the ops are manual
> skills + a reminder hook rather than auto-ingest. The *why* behind the conventions.
> **Defers to:** [`../SCHEMA.md`](../SCHEMA.md) for the now-canonical conventions — the
> source model, the one grounding rule, the page conventions, the `raw/` note. This page
> does **not** restate them; it records the reasoning SCHEMA encodes.
> **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "Q4 — WORKING", "WS-4 design sketch", "D1 analysis", and the `raw/` sections.
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The pattern it adapts

The wiki follows the **LLM-wiki** pattern: a knowledge base structured *for a model to
query*, not just a human to browse — immutable sources compiled into an interlinked set
of `.md` pages (summaries, backlinks, concept articles) governed by a schema file, with
three core ops: **ingest** (compile sources → pages), **query** (answer from the wiki +
verify against source), **lint** (drift / contradiction / coverage checks). The
**codebase variant** makes the repo at git HEAD the source and grounds claims in
`path:line` cites a freshness check can verify. A lighter companion,
[`llms.txt`](../../../llms.txt), is the curated root "sitemap for LLMs." The ops here are
adapted from the `kfchou/wiki-skills` Claude Code implementation rather than reinvented
`[synthesis]`.

## The convergence insight (why this was worth doing now)

The **dev docs**, the **Sprint 6.5 in-app education content**, and the
**v1.0.7 doc-grounded assistant** are *one knowledge base in three renderings*. The
assistant's job ("how do I rename a job-experience title" ↔ "how does the grounding
suite work") is exactly the wiki **query** op over the repo + docs — and Sprint 6.5 is
about to author content across that whole range. Deciding the authoring pattern *before*
6.5 writes it makes the assistant nearly free later; deciding after means retrofitting a
mountain of docs. **Q4 has a clock; the other workstreams don't** — which is why WS-4's
substrate is front-loaded (see [[engineering-workstreams]]).

## The source-model decision (D1): git-as-engine

The wiki is **git-as-engine**: the repo at HEAD is the source, ingest is diff-driven off
a saved checkpoint, and code is never copied. This was chosen over a strict `raw/`-only
model because freezing living docs into `raw/` would mean duplication + rot and would not
natively track a living codebase — you would end up bolting git-as-engine on anyway. The
mechanics, checkpoint, and diff rules are canonical in
[`../SCHEMA.md`](../SCHEMA.md) "Source model (git-as-engine)"; the reasoning is: single
source of truth, incremental + cheap in steady state, and **staleness becomes
measurable** (saved SHA vs HEAD) `[synthesis]`.

## Why a `raw/` layer at all — and why ours starts empty

The wiki is *synthesis* (lossy, fast to query); a `raw/` layer would be *ground truth*
(immutable, full-fidelity). The argument for keeping both is that **an LLM is an
unreliable narrator of its own synthesis**: with no source to falsify against, a
synthesis error silently becomes a "fact." `raw/` would buy a verification anchor, a
fact-vs-interpretation provenance split, fidelity on demand, and a stable citation
target.

This is **the same move as the product's own grounding check**:

> `raw/` : wiki pages :: the source résumé : generated bullets — synthesis may not invent
> beyond its source.

But **in a codebase, git already *is* a `raw/` layer** — every commit is an immutable,
diffable, rebuildable snapshot with provenance. So `raw/` only earns its place for
knowledge git *cannot* see (external papers, point-in-time rationale) — and it therefore
**starts at zero**, introduced later by [[governance-extraction]], not invented eagerly.
Copying a live git-tracked doc into `raw/` would be pure duplication `[synthesis]`. The
canonical statement of this is [`../SCHEMA.md`](../SCHEMA.md) "The `raw/` constitutional
layer."

## Ops + trigger + cost

The ops are **manually-invoked Claude Code skills** — `/wiki-ingest`, `/wiki-query`,
`/wiki-lint`, `/wiki-audit` under `commands/` — **plus a lightweight
commit-time freshness *reminder* hook, deliberately NOT auto-ingest**, because ingesting
on every commit would spend LLM cost on every commit. `wiki-lint` runs periodically and
as a **pre-release gate** (it fits the existing release-checklist discipline). Ownership
is the branch close-out + the pre-release lint gate `[synthesis]`.

## Related

- [[excellence-walk]] — the walk this design belongs to.
- [[engineering-workstreams]] — WS-4 in the backlog context.
- [[project-self-assessment]] — the Q4 docs-discoverability watch-out this answers.
- [[governance-extraction]] — the follow-on that introduces the constitutional `raw/`.
