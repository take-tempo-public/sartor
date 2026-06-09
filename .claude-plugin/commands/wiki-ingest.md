---
description: Compile changed sources into docs/wiki/ pages — diff-driven off .last_ingest_sha → HEAD (empty/sentinel SHA, or --full, = a full cold pass), per the docs/wiki/SCHEMA.md contract. Advances the checkpoint and appends to log.md.
argument-hint: [--full]
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
---

Ingest the repository into the committed LLM-wiki under `docs/wiki/`, following the
**git-as-engine source model** and the **one grounding rule** in
[`docs/wiki/SCHEMA.md`](../../docs/wiki/SCHEMA.md). The repo at **git HEAD is the source
of truth**; the wiki is a compiled, link-back artifact — never a copy of the code.

> **This is an LLM-heavy op.** A cold pass reads the whole repo (chunked per module); a
> diff pass is cheap (only changed files). Surface the scope before you start — like
> [`/eval`](eval.md) surfacing cost — so the user can scope or cancel.

## Steps

1. **Pick the mode.** Read [`docs/wiki/.last_ingest_sha`](../../docs/wiki/.last_ingest_sha).
   - No 40-char SHA present (empty / sentinel), **or** `--full` was passed ⇒ **cold pass**:
     a whole-repo pass, chunked per module using [`docs/architecture.md`](../../docs/architecture.md)
     as the module map (the deterministic core, `analyzer.py`, the routes, `db/`, the eval
     harness, the frontend).
   - A real SHA is present ⇒ **diff pass**: `git diff --name-status <sha> HEAD` selects only
     the changed files (renames/deletes tracked). Report the file list before synthesizing.
2. **Synthesize / update pages.** For each changed or in-scope source, create or update the
   affected `docs/wiki/pages/<slug>.md` per the SCHEMA page conventions:
   - **One concept per page**, flat in `pages/`, **kebab-case** slug
     (`context-set-contract.md`, `llm-routing.md`).
   - **`[[backlinks]]`** to related page slugs, kept **bidirectional** — a page names what
     it depends on and what depends on it.
   - **`path:line` cites** for every code claim; prefer a **symbol or anchor**
     (`analyzer.py:SYSTEM_PROMPT`) over a bare line number — line numbers drift.
   - **`[synthesis]`** tag on any statement that is *concluded* rather than quoted, so a
     later [`/wiki-audit`](wiki-audit.md) knows to fact-check it.
3. **Hold the one grounding rule.** *A wiki page may not assert anything its cited sources
   do not support.* The wiki may select, condense, and connect what the sources say; it may
   not invent past them. This is the same discipline the product enforces on résumé bullets.
4. **Update the map + backlinks.** Add or revise the one-line entry per new/changed page in
   [`docs/wiki/index.md`](../../docs/wiki/index.md), and reconcile `[[backlinks]]` in both
   directions (a new inbound link gets a matching outbound mention where it belongs).
5. **Advance the checkpoint.** Write the current `git rev-parse HEAD` (full 40-char SHA)
   into [`docs/wiki/.last_ingest_sha`](../../docs/wiki/.last_ingest_sha), replacing the
   sentinel line on a cold pass.
6. **Log it.** Append a dated entry to [`docs/wiki/log.md`](../../docs/wiki/log.md) (newest
   last): the branch, the mode (cold / diff), the files read, and the pages created/changed.

Do not duplicate the project's operating rules into the wiki — `SCHEMA.md` **references**
[`AGENTS.md`](../../AGENTS.md) / [`CLAUDE.md`](../../CLAUDE.md) / [`vision.md`](../../vision.md)
(design fork D5); on any conflict, those canonical docs win and the wiki is what's wrong.
