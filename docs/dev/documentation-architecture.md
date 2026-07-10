# Documentation architecture — how sartor.'s docs are organized & published

> **Purpose:** the documentation *publishing strategy* — the layered source chain, the
> three-audience navigation spine, the Fumadocs projection, the merge=publish gate, and the
> deterministic gates + flag convention that keep the published site honest as it grows to
> include a hosted Fumadocs site.
> **Audience:** `dev`
> **Authoritative for:** the L0–L3 documentation layering; the ICP-ladder navigation spine;
> the Fumadocs-as-projection model; the merge=publish gate; the `DOC-STATUS` flag convention.
> It **defers** to [`../system-model.md`](../system-model.md) for the seven pillars + the one
> law, to [`../wiki/SCHEMA.md`](../wiki/SCHEMA.md) for the wiki contract + the `user`/`dev`
> audience tag, and to [`memory-architecture.md`](memory-architecture.md) for the recall
> disclosure plane. It **extends** the prior
> [`docs-wiki-architecture`](reviews/2026-06-product-excellence/01-maps/domain-guides/docs-wiki-architecture.md)
> domain guide and the
> [`wiki-architecture-proposal`](reviews/2026-06-product-excellence/03-prescriptions/wiki-architecture-proposal.md);
> on conflict the charter ([`../governance/charter.md`](../governance/charter.md)) governs.

---

## Context

sartor. is adding a **hosted Fumadocs site**, generated from `main` on each merge. That
raises a design question with one right answer under the project's existing disciplines:
**Fumadocs must be a projection of the governed corpus, never a second source of truth.**
This doc states the layering, the navigation spine, the sourcing mechanism, and the gates so
the site strengthens the documentation practice rather than forking it. It is the canonical
home for the *publishing strategy*; the wiki SCHEMA already states the same one-way model for
the wiki, and this generalizes it to the hosted site.

## The source chain (L0 → L3, one-way)

```
L0  GOVERNANCE (north star)        vision.md · governance/{charter,enforcement,metrics}.md
        ^ everything answers up to this
L1  AUTHORED SOURCE OF TRUTH       AGENTS.md/CLAUDE.md · architecture.md · PRODUCT_SHAPE.md ·
    (ONE home per fact; every        system-model.md · install.md · walkthrough.md · dev/** ·
     doc has a P/A/A header)         README.md (the front door)
        |  /wiki-ingest (diff-driven, git-as-engine, .last_ingest_sha checkpoint)
        v
L2  COMPILED SUBSTRATE             wiki/** (synthesized · path:line cited · audience-stamped ·
    (lossy synthesis, cited)         lint-gated) -> feeds recall/ + the avatar + llms.txt
        |  projection / sync adapter (build step -> MDX content tree)
        v
L3  PUBLISHED PRESENTATION         Fumadocs site (renders a curated public subset of L1;
    (derived, never authoritative)   surfaces L2 as Search + the "Ask" avatar)
```

**The one-way law (from [`../system-model.md`](../system-model.md)):** `L3 -> L2 -> L1 -> L0`,
never the reverse; Production code depends on none of them. The hosted site is a *pure
function of `main` HEAD* — repo and site cannot drift by construction. This is the wiki's
"git HEAD is the source" rule extended to the public site.

## Two axes, reconciled

- **The seven pillars = ownership / source structure.** Substrate · Production · Evaluation ·
  Operation · Memory · Regulation · Governance is how **L1 is owned** — each fact's single
  home maps to a pillar. The developer/governance map.
- **The three ICPs = navigation / entry.** Job seeker -> coach -> developer
  (`one -> many -> extend`) is how the **site is entered**. The cumulative ladder is the
  navigation spine; its canonical home is [`../../README.md`](../../README.md).
- **The bridge is the `user`/`dev` audience tag** ([`../wiki/SCHEMA.md`](../wiki/SCHEMA.md)).
  It already gates the avatar's disclosure plane; it now also gates Fumadocs nav depth. One
  mechanism, two consumers. ICPs are the front of house; the pillars are the structure behind
  it.

## Fumadocs sourcing (the mechanism)

The existing `Purpose / Audience / Authoritative-for` header maps 1:1 onto frontmatter — no
new convention:

| Existing header line | -> frontmatter | Drives |
|---|---|---|
| **Purpose:** | `title` / `description` | page identity |
| **Audience:** `` `user`/`dev` `` | `audience: [...]` (reuse the SCHEMA backtick-token parse) | which ICP front door it appears under; the leak check |
| **Authoritative for:** | `authoritativeFor: [...]` | the canonical-home marker; cross-refs link here |

- Canonical `.md` stays in-repo; the MDX content tree is **generated/synced** (a build step),
  so editing happens in the governed source. `meta.json` encodes the ICP + pillar ordering.
- **"Ask" = the avatar over L2**, citations preserved, gated by the same `user`/`dev` plane —
  in-product help and the public docs chat become one memory system, two front ends.
- **`llms.txt`** is the machine sibling of the human nav (already points at the wiki index).
- **Portability:** all load-bearing content stays plain markdown that degrades on GitHub;
  frontmatter + `meta.json` are additive only. No Fumadocs-only component holds a fact. This
  is what guarantees the corpus is self-contained locally, with or without the site.

## Gates — merge = publish

Because every merge to `main` republishes the site, **the PR merge gate is the publish gate.**
Promote the doc checks from local reminders to PR-blocking CI (extends `block-merge-to-main` +
`wiki-lint`):

| Gate | Blocks merge if… |
|---|---|
| link-integrity | any doc-map / cross-doc / `[[backlink]]` link is dead at HEAD |
| frontmatter + audience | a published page lacks Purpose/Audience/Authoritative-for |
| single-home (D5) | a page restates a fact owned elsewhere instead of linking |
| cite-resolution | any `path:line` cite is unresolvable at HEAD |
| wiki-freshness | the wiki is staler than threshold vs HEAD |

**Freshness nuance:** CI *checks* `.last_ingest_sha` vs HEAD and warns/blocks past threshold;
it does **not** run the LLM `/wiki-ingest` (cost + manual by SCHEMA). A human runs the bounded
`/wiki-self-update` at close-out / pre-tag so `main` carries a fresh wiki for Search + Ask.

## The `DOC-STATUS` flag convention

A front-door page that auto-publishes must not state a claim that silently goes stale. Two
layers:

- **Visible:** a short reader-facing "snapshot — updated as those sprints close; canonical:
  …" note, so the public reader knows it is a moving target and where the truth lives.
- **Invisible:** an HTML comment naming the exact update trigger —
  `<!-- DOC-STATUS(<key>): <claim state> — update when <sprint> lands <PX/finding ids>. Canonical: <home> -->`.
  Plain markdown — GitHub hides the `<!-- … -->` comment, and the Fumadocs
  projection rewrites it to an MDX `{/* … */}` comment the site hides (MDX has
  no raw-HTML-comment syntax, so the projector converts rather than relying on
  Fumadocs to hide it). Greppable in-repo either way.

**Hook point (proposed):** the freshness gate can `grep` for `DOC-STATUS` markers whose
trigger sprint has tagged and fail the build until the line is reconciled — turning "remember
to update the README when v1.0.8 ships" from vigilance into machinery. Live examples are in
[`../../README.md`](../../README.md) (governance status; egress claim).

## Disciplines this rests on

- **Single home / cite-don't-restate (D5).** Each fact lives once; the wiki and Fumadocs link,
  never fork. The README is a *thorough front door of links*, not a parallel encyclopedia.
- **Recursive grounding (the through-line).** "Discover/cite; never assert beyond source"
  governs the résumé generator, the doc-assistant avatar
  ([`memory-architecture.md`](memory-architecture.md)), **and this documentation itself** (the
  wiki may not assert beyond its cited sources — [`../wiki/SCHEMA.md`](../wiki/SCHEMA.md)). The
  docs are a third instance of the product's own discipline.
- **The agent-contract carve-out.** `AGENTS.md` / `CLAUDE.md` deliberately restate canonical
  governance inline (non-Claude agents read them raw — the "don't let this become a pure
  import shell" rule). They stay raw-readable in-repo and are **not** the site's canonical home
  for governance — the charter is.

## Recommendations / sequencing

> **Scheduled as the v1.0.9 "Documentation & docs-site" epic** — [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.9 owns the authoritative sequence, branch names, and the v1.0.8-tail policy; this section is the *rationale*. _(RELEASE_ARC and this doc mutually reference — co-merge `docs/release-arc-v1.0.9` with this branch at the top of v1.0.9 to keep both links live.)_

Status: the **README front door is shipped** (this branch — the L1 flagship + the ICP ladder +
the two C-0 corrections + the `DOC-STATUS` examples). The rest is proposed, in order:

1. **WS-B — verify the dev-tier homes carry the depth** the README now hooks into
   (behavior-corpus thesis -> `system-model.md`; extraction boundary + the two planes ->
   `memory-architecture.md`; pydantic-in-loop -> `architecture.md`). Verify-first; fill only
   genuine gaps; never duplicate. The 2026-06 architecture digest is a useful checklist.
2. **WS-E — the unification note** (recursive grounding + the shared audience plane) is folded
   into *this* doc; ensure `system-model.md` carries the one-law framing it cites.
3. **The Fumadocs adapter** — a build step that projects L1 + frontmatter -> MDX content tree;
   `meta.json` from the ICP ladder + audience tags. Deploy on merge to `main`.
4. **The CI merge-gate job** — the five gates above, extending `block-merge-to-main` +
   `wiki-lint`; plus the portability lint and the `DOC-STATUS`-trigger check.
5. **The wiki content pass** — refresh `overview.md` + the user-tier education pages to the
   three-audience ladder (a *content* pass; does **not** advance `.last_ingest_sha` per SCHEMA);
   refresh `llms.txt`.

Do not bloat the README to cover items 1–2 — surface hooks, keep depth in the homes. Each of
1–5 is its own branch (one item per branch).

## Canonical homes this cites

[`../system-model.md`](../system-model.md) (seven pillars + one law) ·
[`../wiki/SCHEMA.md`](../wiki/SCHEMA.md) (wiki contract + audience tag) ·
[`memory-architecture.md`](memory-architecture.md) (recall disclosure plane) ·
[`../governance/charter.md`](../governance/charter.md) (D5 + the binding rules) ·
[`../../README.md`](../../README.md) (the ICP ladder + the front door) ·
the prior
[`docs-wiki-architecture`](reviews/2026-06-product-excellence/01-maps/domain-guides/docs-wiki-architecture.md)
+ [`wiki-architecture-proposal`](reviews/2026-06-product-excellence/03-prescriptions/wiki-architecture-proposal.md).
