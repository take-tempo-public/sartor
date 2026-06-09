# Wiki log

> Append-only record of ingest + lint runs and structural changes to the wiki.
> Newest entry last. See [`SCHEMA.md`](SCHEMA.md) for the source model these record.

## 2026-06-08 — skeleton stood up (`docs/wiki-skeleton`)

Created the committed `docs/wiki/` skeleton (WS-4a step 2):
[`SCHEMA.md`](SCHEMA.md), [`index.md`](index.md), [`overview.md`](overview.md)
(seeded from and deferring to [`../system-model.md`](../system-model.md)), this
`log.md`, `.last_ingest_sha` (sentinel — no ingest yet), and the empty `pages/` home.
Added the root [`llms.txt`](../../llms.txt).

**No code ingest yet.** `pages/` is empty and `.last_ingest_sha` carries no SHA, so the
first `/wiki-ingest` (after the `/wiki-*` skills land in `feat/wiki-skills`, WS-4a step
3) performs a full cold pass. See
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5.

## 2026-06-09 — first ingest: the excellence-walk source (`wiki/ingest-excellence-walk`)

**Mode: content-scoped ingest — NOT a code cold pass / diff pass** (WS-4a step 4). The
first real population of `pages/`. Scoped to the preserved excellence-walk source only,
synthesized per [`SCHEMA.md`](SCHEMA.md)'s page conventions + one grounding rule.

**Sources read** (all under [`../dev/excellence-walk/`](../dev/excellence-walk/)):
`excellence-walk.md` (master capture), `q1-overview.md`, `q2-consistency.md`,
`q3-downloads.md`, `README.md`. `walkthrough-sprint-plan.md` was read for provenance only
(its content is already folded into [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase
4.5) and got no page.

**Pages created (8):** `excellence-walk` (provenance hub), `system-model-derivation`,
`project-self-assessment`, `consistency-tracks-enforcement`, `non-dependency-downloads`,
`engineering-workstreams`, `llm-wiki-design`, `governance-extraction`. `index.md` updated;
`[[backlinks]]` reconciled bidirectionally.

**`.last_ingest_sha` deliberately LEFT at the sentinel.** That checkpoint tracks the last
successful **code** ingest (per [`SCHEMA.md`](SCHEMA.md) "Source model"); this was a
*docs* ingest, not a code pass. Advancing it would falsely assert the code was ingested
and would prematurely silence the commit-time freshness reminder before WS-4b ever runs.
It stays the sentinel until `wiki/cold-ingest-code` (WS-4b, after Sprint 6.4). The
excellence-walk pages are grounded in committed docs, so they are not subject to the
`sha → HEAD` code-staleness check.

**The source stays put — it already *is* the raw layer.** `docs/dev/excellence-walk/`
remains a frozen, git-tracked source. Per [`SCHEMA.md`](SCHEMA.md), git already provides
the raw-layer role for tracked material (immutable, diffable, provenanced), so `raw/`
stays at zero and **nothing is copied or relocated into a `raw/` folder** — the wiki pages
synthesize *from* this source and cite it. (Any future `raw/` is the Governance pass's
concern, scoped to genuinely-homeless *prescriptive* material — not a relocation home for
this descriptive capture; see [`pages/governance-extraction.md`](pages/governance-extraction.md).)

**Verification (lint + audit checks, per the `/wiki-lint` + `/wiki-audit` procedures).**
Lint: **PASS** (no ERROR) — all 8 pages present and listed in `index.md`; every
`[[backlink]]` resolves to an existing page slug; every relative link target resolves
(22/22); no orphans; staleness = sentinel (a code cold pass is pending — expected, not an
error); code-module coverage = INFO (WS-4b). Audit (`consistency-tracks-enforcement` +
`governance-extraction`): all load-bearing claims **SUPPORTED** against cited sources; no
UNSUPPORTED. Freshness reminder confirmed **silent** (sentinel carries no 40-char SHA).
