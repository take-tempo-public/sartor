# Documentation architecture — how Sartor's docs are organized & published

> **Purpose:** the documentation *publishing model*: the layered source chain, how the
> governed markdown is projected to the hosted Fumadocs site, the merge=publish gates that
> keep the site honest, and the `DOC-STATUS` flag convention.
> **Audience:** `dev`
> **Authoritative for:** the L0–L3 documentation layering; the Fumadocs-as-projection model;
> the merge=publish gate set; the `DOC-STATUS` flag convention. It **defers** to
> [`docs-ia-design.md`](docs-ia-design.md) for the `docs/user/` vs `docs/dev/` tree, the
> onboarding ladders, the link policy and the planned doc lints; to
> [`../../scripts/doc_registry.py`](../../scripts/doc_registry.py) for *which* docs are
> published; to [`system-model.md`](system-model.md) for the seven pillars and the one law;
> to [`../wiki/SCHEMA.md`](../wiki/SCHEMA.md) for the wiki contract and the `user`/`dev`
> audience tag; and to [`memory-architecture.md`](memory-architecture.md) for the recall
> disclosure plane. On conflict the charter
> ([`../governance/charter.md`](../governance/charter.md)) governs.

---

## Context

Sartor publishes a **hosted Fumadocs site**, rebuilt from `main` on every merge
([`.github/workflows/docs-deploy.yml`](../../.github/workflows/docs-deploy.yml); it also
builds on every pull request so a broken site fails a visible check). One rule shapes
everything below: **the site is a projection of the governed markdown, never a second
source of truth.** Every fact is edited in the repo; the site is a pure function of `main`.
[`docs-site-deploy.md`](docs-site-deploy.md) is the deploy runbook.

## The source chain (L0 → L3, one-way)

```
L0  GOVERNANCE (north star)        vision.md · governance/{charter,enforcement,metrics}.md
        ^ everything answers up to this
L1  AUTHORED SOURCE OF TRUTH       the docs listed in scripts/doc_registry.py PUBLISHED
    (ONE home per fact; every        (user tier: README, vision, docs/user/**, …;
     published doc has a P/A/A       dev tier: docs/dev/*.md, AGENTS.md, CLAUDE.md,
     header)                          CONTRIBUTING, governance/**, …)
        |  /wiki-ingest (diff-driven, git-as-engine, .last_ingest_sha checkpoint)
        v
L2  COMPILED SUBSTRATE             wiki/** (synthesized · path:line cited · audience-stamped ·
    (lossy synthesis, cited)         lint-gated) -> feeds recall/ + the assistant + llms.txt
        |  scripts/project_docs_to_mdx.py (build step -> MDX content tree + meta.json)
        v
L3  PUBLISHED PRESENTATION         the Fumadocs site: the L1 registry set, plus the
    (derived, never authoritative)   assistant over L2
```

**The one-way law (from [`system-model.md`](system-model.md)):** `L3 -> L2 -> L1 -> L0`,
never the reverse; Production code depends on none of them.

**Records are not L1.** Handoffs, the provenance ledger, diagnosis and blast-radius dossiers,
reviews, perf records and `docs/dev/archive/` are frozen history. They are never published
and never rewritten; `doc_registry.RECORD_PREFIXES` is the single list of them. A record's link
to a doc that has since moved resolves through
[`moved-paths.json`](moved-paths.json) (docs-ia-design §3).

## Two axes, reconciled

- **The seven pillars = ownership.** Substrate · Production · Evaluation · Operation ·
  Memory · Regulation · Governance is how L1 is owned: each fact's single home maps to a
  pillar ([`system-model.md`](system-model.md)).
- **The two tiers = navigation.** A reader enters as a user (job seeker or coach) or as a
  developer. Each published doc has exactly one tier in the registry. The site nav is
  generated from it as two sections, "Using Sartor" and "Building on Sartor"
  (`build_meta_pages_order`, [`project_docs_to_mdx.py`](../../scripts/project_docs_to_mdx.py)).
  Each tier's reading order is its ladder: [`../user/README.md`](../user/README.md) and
  [`README.md`](README.md).
- **The bridge is the `user`/`dev` audience tag** ([`../wiki/SCHEMA.md`](../wiki/SCHEMA.md)).
  The same tag gates the assistant's disclosure plane and the site's nav: one mechanism, two
  consumers.

## Fumadocs sourcing (the mechanism)

`project_docs_to_mdx.py` reads the registry, not the tree. For each `PUBLISHED` entry, the
existing `Purpose / Audience / Authoritative-for` header maps onto frontmatter:

| Header line | -> frontmatter | Drives |
|---|---|---|
| **Purpose:** | `title` / `description` | page identity |
| **Audience:** `` `user`/`dev` `` | `audience: [<registry tier>]` | the nav section the page sits in. The header must name the registry tier (`check_doc_frontmatter.py`) |
| **Authoritative for:** | `authoritativeFor: [...]` | the canonical-home marker; cross-refs link here |

- **Canonical `.md` stays in the repo.** The MDX content tree and `meta.json` are generated
  at build time, so editing happens in the governed source.
- **Portability.** All load-bearing content stays plain markdown that reads correctly on
  GitHub. Frontmatter and `meta.json` are additive; no Fumadocs-only component holds a fact.
- **Cross-doc links are rewritten at projection time, not in the source.** A link to a
  projected doc becomes its site route. A link to anything the site doesn't carry (source
  files, `docs/wiki/**`, records) becomes the GitHub URL. The rewrite is a pure function of
  the projection's own slug map, so the site can't assert anything the source doesn't.
- **The assistant over L2** answers on the site and in the app from the same memory
  system, with citations, gated by the same `user`/`dev` plane.
- **`llms.txt`** is the machine sibling of the human nav.

## Gates — merge = publish

Every merge to `main` republishes the site, so **the PR merge gate is the publish gate.**
Each check below runs inside `pytest`, so it runs in `python -m scripts.gate` and in CI's
required `quality` job:

| Gate | Blocks merge if… | Checker (test) |
|---|---|---|
| link-integrity + cite-resolution | a relative link or `#anchor` is dead at HEAD, or the file a `path:line` / `path:SYMBOL` cite names doesn't exist (an existence check; lines and symbols aren't resolved) | [`check_doc_links.py`](../../scripts/check_doc_links.py) ([`test_doc_links.py`](../../tests/test_doc_links.py)) |
| frontmatter + audience | a published doc lacks Purpose/Audience/Authoritative-for, or its Audience omits its registry tier | [`check_doc_frontmatter.py`](../../scripts/check_doc_frontmatter.py) ([`test_doc_frontmatter_gate.py`](../../tests/test_doc_frontmatter_gate.py)) |
| single-home (D5) | two published docs carry the same long paragraph (a heuristic, documented as one) | [`check_doc_single_home.py`](../../scripts/check_doc_single_home.py) ([`test_doc_single_home_gate.py`](../../tests/test_doc_single_home_gate.py)) |
| doc lints (design §5) | a user-tier doc lacks its Diátaxis `**Type:**`, uses a banned word, an unexpanded acronym or a tracker ID; a published doc uses `sartor.` mid-sentence; a live doc's list of deterministic modules, subagents or gate steps drifts from the code; `docs/dev/tooling.md` drifts from the tree; a `[[wikilink]]` sits outside the wiki; a charter clause lacks its heading | [`doc_lints.py`](../../scripts/doc_lints.py) ([`test_doc_lints.py`](../../tests/test_doc_lints.py)) |
| DOC-STATUS reconciliation | a `DOC-STATUS` marker is malformed, or its trigger has shipped without the claim being reconciled | [`test_doc_status_gate.py`](../../tests/test_doc_status_gate.py) |
| wiki-freshness | the wiki's checkpoint is staler than the threshold against the PR's merge ref | [`wiki_freshness.py`](../../scripts/wiki_freshness.py) ([`test_wiki_freshness_gate.py`](../../tests/test_wiki_freshness_gate.py)); a local push to `main` is also checked by `block-merge-to-main` |

The doc checks read through one shared corpus,
[`doc_corpus.py`](../../scripts/doc_corpus.py): one `git ls-files`, each file read once,
link targets answered from the tracked set.

**Freshness nuance:** CI *checks* `.last_ingest_sha` against HEAD; it never runs the LLM
`/wiki-ingest` (cost, and manual by SCHEMA). A session runs the bounded `/wiki-self-update` at
close-out or pre-tag. The gate measures how stale the checkpoint is, not how stale each page
is (item 98).

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

**Enforced by** [`tests/test_doc_status_gate.py`](../../tests/test_doc_status_gate.py) (PX-50),
which checks the machine-checkable subset of the grammar. Live examples are in
[`../../README.md`](../../README.md) (governance status; egress claim).

## Disciplines this rests on

- **Single home / cite-don't-restate (D5).** Each fact lives once; the wiki and the site
  link, never fork. The README is a *front door of links*, not a parallel encyclopedia.
- **Recursive grounding (the through-line).** "Discover/cite; never assert beyond source"
  governs the résumé generator, the doc assistant
  ([`memory-architecture.md`](memory-architecture.md)), **and this documentation itself**:
  the wiki may not assert beyond its cited sources ([`../wiki/SCHEMA.md`](../wiki/SCHEMA.md)).
- **The agent-contract carve-out.** `AGENTS.md` keeps the code rules inline, because
  non-Claude agents read it raw (the "don't let this become a pure import shell" rule). The
  owner's session protocol lives in [`maintainer-lane.md`](maintainer-lane.md), which
  `CLAUDE.md` imports. Neither file is the canonical home for governance: the charter is.

## Status

Shipped:
- the projector and the registry-driven two-tier nav;
- the deploy on merge, and the PR build;
- all five gates above;
- the D2 split into `docs/user/` and `docs/dev/`;
- the D3 user and dev content.

What's next is Epic D sprint D4: screenshots and diagram refresh, in-app "Learn more" links,
and the docs IA design's §5 lints (enumeration drift, wordmark, and the shared doc corpus).
[`RELEASE_ARC.md`](RELEASE_ARC.md) §"Epic D" owns the sequence;
[`docs-ia-design.md`](docs-ia-design.md) §5 owns the lint designs.

## Canonical homes this cites

[`docs-ia-design.md`](docs-ia-design.md) (the tree, ladders, link policy, lints) ·
[`../../scripts/doc_registry.py`](../../scripts/doc_registry.py) (what is published, and the
record classes) ·
[`system-model.md`](system-model.md) (seven pillars + one law) ·
[`../wiki/SCHEMA.md`](../wiki/SCHEMA.md) (wiki contract + audience tag) ·
[`memory-architecture.md`](memory-architecture.md) (recall disclosure plane) ·
[`../governance/charter.md`](../governance/charter.md) (D5 + the binding rules) ·
[`docs-site-deploy.md`](docs-site-deploy.md) (deploy runbook).
