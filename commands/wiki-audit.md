---
description: Fact-check one docs/wiki/ page against its cited sources — verify each path:line cite and [synthesis] claim still holds at HEAD, classify SUPPORTED / DRIFTED / UNSUPPORTED, and offer to re-anchor drifted cites. Surfaces unsupported claims; never deletes silently. Appends to log.md.
argument-hint: <page-slug>
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
---

Audit a single wiki page against the sources it cites, enforcing the **one grounding rule**
from [`docs/wiki/SCHEMA.md`](../docs/wiki/SCHEMA.md): *a page may not assert anything its
cited sources do not support.* An LLM is an unreliable narrator of its own synthesis — this
command is the falsification step that keeps a synthesis error from silently becoming a "fact."

## Steps

1. **Load the page.** Read `docs/wiki/pages/<page-slug>.md` (resolve `<page-slug>` against
   [`docs/wiki/index.md`](../docs/wiki/index.md); if it doesn't exist, list the available
   slugs and stop).
2. **Check each claim against its source.** For every `path:line` cite and every `[synthesis]`
   statement, open the cited source (code at HEAD, or the living doc) and quote-match the
   claim against what the source actually says.
3. **Classify each** (one line per claim):
   - **SUPPORTED** — the source still says what the page says.
   - **DRIFTED** — the claim holds but the cite has moved (line numbers shifted, symbol
     renamed). The fact is fine; the pointer rotted.
   - **UNSUPPORTED** — the source does not support the claim. This is the load-bearing
     failure: a grounding violation.
4. **Resolve, with the user in the loop:**
   - Offer to **re-anchor DRIFTED cites** (prefer a symbol/anchor over a bare line number) —
     apply on confirmation.
   - **Surface UNSUPPORTED claims to the user** for correction or removal. Do **not** silently
     delete or rewrite a claim — flag it, propose the fix, and let the user decide (the page is
     committed history; an unsupported claim may signal a real code/doc change worth tracing).
5. **Log it.** Append a dated entry to [`docs/wiki/log.md`](../docs/wiki/log.md): the page
   audited and the per-tier counts (supported / drifted / unsupported).

For a breadth check across the whole wiki (which pages to audit, what drifted at the file
level), run [`/wiki-lint`](wiki-lint.md) first — `lint` finds *where* to look; `audit` checks
*whether the words are true*.
