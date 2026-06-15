---
description: Answer a question from the committed docs/wiki/ with [[citations]] — read the wiki for the map, drop to the cited source for fidelity, and offer to file the answer back as a page. Read-first; only writes on explicit confirmation.
argument-hint: <question>
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
---

Answer `$ARGUMENTS` from the committed LLM-wiki under `docs/wiki/`, grounded in its pages
and their cited sources, per [`docs/wiki/SCHEMA.md`](../../docs/wiki/SCHEMA.md). Read the
wiki for the map; drop to the source (code at HEAD, or the living docs it cites) for full
fidelity.

## Steps

1. **Find the relevant pages.** Read [`docs/wiki/index.md`](../../docs/wiki/index.md) (the
   one-line-per-page map) to locate the pages that bear on the question, then read those
   `docs/wiki/pages/*.md` and follow their `[[backlinks]]`.
2. **Answer, grounded.** Cite the pages you used as `[[page-slug]]`, and surface the page's
   `path:line` cites where the claim is about code — so the reader can verify at the source.
   Distinguish a `[synthesis]` conclusion from a quoted fact when it matters to confidence.
3. **Handle gaps honestly** (the one grounding rule cuts both ways):
   - If the wiki does not cover it, **say so** and answer from the source directly
     (`Grep`/`Read` the code or living docs), labeling that the wiki has no page yet.
   - If [`docs/wiki/.last_ingest_sha`](../../docs/wiki/.last_ingest_sha) lags `HEAD` (or is
     the sentinel), note the wiki may be **stale** and suggest [`/wiki-ingest`](wiki-ingest.md)
     (and [`/wiki-lint`](wiki-lint.md) for the drift report). Do not silently trust a stale page.
4. **Offer to file it back.** Ask whether to capture the answer as a new or updated
   `docs/wiki/pages/<slug>.md`. **Only on an explicit yes:**
   - Write the page per the SCHEMA conventions (one concept, kebab slug, `[[backlinks]]`,
     `path:line` cites, `[synthesis]` tags) — asserting nothing the cited sources don't support.
   - Add/refresh its one-line entry in `index.md` and append a dated entry to
     [`docs/wiki/log.md`](../../docs/wiki/log.md).
   - Do **not** advance `.last_ingest_sha` — that checkpoint belongs to `/wiki-ingest`, not a
     hand-filed answer.

If the question is about the project's operating rules (the security gate, the
deterministic/LLM boundary, `PROMPT_VERSION` discipline, branch conventions), answer from
the canonical [`AGENTS.md`](../../AGENTS.md) / [`CLAUDE.md`](../../CLAUDE.md) /
[`vision.md`](../../vision.md) — the wiki references those, it does not own them (D5).
