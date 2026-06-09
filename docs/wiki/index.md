# Wiki index — `docs/wiki/`

> One-line summary per page. Doubles as the map the root
> [`llms.txt`](../../llms.txt) points at. Pages are added as they are ingested —
> see [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5.

## Pages

- [`overview.md`](overview.md) — what callback. is and how the whole system is shaped
  (seeded from, and deferring to, [`../system-model.md`](../system-model.md)).

## Wiki infrastructure

- [`SCHEMA.md`](SCHEMA.md) — wiki conventions, the one grounding rule, the
  git-as-engine source model.
- [`log.md`](log.md) — append-only record of ingest / lint runs.

## Reserved / planned (not yet ingested)

- `pages/` — flat, slug-named, `[[backlinked]]`, `path:line`-grounded synthesized
  pages. **Empty for now.** Populated by `wiki/ingest-excellence-walk` (the preserved
  excellence-walk source) and `wiki/cold-ingest-code` (the code architecture) — see
  [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5 (WS-4a step 4 + WS-4b).
