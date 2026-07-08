---
description: Severity-tiered drift/coverage report on docs/wiki/ — staleness (.last_ingest_sha vs HEAD), structural integrity (backlinks, path:line cites, index ↔ pages), and coverage gaps. Read-only. Designated periodic + pre-release gate. Appends to log.md.
argument-hint: [--since <sha>]
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

Health-check the committed LLM-wiki under `docs/wiki/` against the
[`docs/wiki/SCHEMA.md`](../docs/wiki/SCHEMA.md) contract and report what has drifted,
broken, or gone uncovered. **Read-only — this command reports, it does not fix.** Run it
periodically and as a **pre-release gate** (it fits the
[`docs/dev/RELEASE_CHECKLIST.md`](../docs/dev/RELEASE_CHECKLIST.md) discipline — the
wiki must be honest before a tag).

## Checks

1. **Staleness (drift).** Read [`docs/wiki/.last_ingest_sha`](../docs/wiki/.last_ingest_sha)
   (or `--since <sha>`). If a real SHA is present, count and list the source files changed via
   `git diff --name-status <sha> HEAD` (excluding `docs/wiki/` itself) — that is the ingest
   debt. If it is the sentinel, report **no ingest has run yet** (a full cold pass is pending —
   not an error).
2. **Structural integrity.**
   - Every `docs/wiki/pages/*.md` has the required shape (a clear concept, not an empty stub).
   - Every `[[backlink]]` resolves to an existing page slug — flag dangling ones (a forward-link
     to a not-yet-written page is allowed only if intentional; call it out).
   - Every `path:line` cite points at a file that exists (cheap existence check; deeper
     quote-matching is [`/wiki-audit`](wiki-audit.md)'s job).
   - **Orphans:** pages with no inbound `[[links]]` from any other page.
   - **Index agreement:** the `pages/` set and the [`docs/wiki/index.md`](../docs/wiki/index.md)
     listing match — flag pages missing from the index and index entries with no page.
3. **Coverage gaps.** Source areas (modules in [`docs/architecture.md`](../docs/architecture.md),
   key routes, the eval harness) with no corresponding page — where the wiki is silent on
   something load-bearing.

## Output

- Group findings into three tiers:
  - **ERROR** — broken `path:line` cite, dangling `[[backlink]]`, page missing from the index
    (or vice versa). The wiki is internally inconsistent.
  - **WARN** — staleness past a sane threshold, orphan pages, thin/stub pages.
  - **INFO** — coverage suggestions (areas worth a page).
- Append a dated summary line to [`docs/wiki/log.md`](../docs/wiki/log.md) (counts per tier).
- State the gate verdict plainly: **pass** (no ERROR) or **needs attention** (ERRORs present)
  so a release driver can act on it.
