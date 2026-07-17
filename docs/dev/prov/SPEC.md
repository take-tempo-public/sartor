<!-- provenance: schema=1 session=43e0e87c-9df9-4209-81bc-e3ead85b2813 branch=feat/handoff-integrity-kit commit=0daf6df actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-07-17 -->

# Provenance spec (schema 1)

One page. Defines the doc stamp, the privacy tiers, and the ledger event
schema that `scripts/verify_doc_template.py` and every durable doc under
this repo's handoff-integrity conventions implement. Vendored from spolia
(`c:/Dev/spolia`, formerly ai-research), where this design was built and
proved through two real branches; rationale (the handoff-corruption
incident) lives in [`../handoff-integrity-design.md`](../handoff-integrity-design.md).

Design constraints (non-negotiable, inherited from spolia's own source):
generic names, self-contained, each part usable independently, stdlib
only, no daemons/databases — graphs are derived on demand by joining
files, never stored.

## 1. The provenance stamp

Every durable doc this kit governs (handoffs, this spec) opens with one
HTML comment on its own line, before the title:

```
<!-- provenance: schema=1 session=<uuid> branch=<name> commit=<short-sha> actor=<name> agent=<vendor/model-or-human> generated_at=<YYYY-MM-DD> -->
```

Fields:

- `schema` — this document's format version (currently `1`). Bump when the
  stamp vocabulary changes; records outlive tools.
- `session` — the writing session's own transcript id (the `<uuid>` in
  `~/.claude/projects/<project-slug>/<uuid>.jsonl`). Tier 1 (below) — an
  opaque join key, not resolvable by anyone but the transcript's owner.
- `branch` — the git branch checked out when the doc was written.
- `commit` — the short commit sha the doc was written against (usually
  `HEAD` at generation time, before this doc's own commit exists).
- `actor` — the accountable human, matching the git author identity
  (`git config user.name`). Accountability always stays with a person.
- `agent` — the executing instrument, vendor-qualified: `anthropic/
  claude-sonnet-5`, `anthropic/claude-fable-5`, `human` for hand-authored
  content. Never inferred — always stated explicitly by whatever wrote the
  doc.
- `generated_at` — the date the doc was written, `YYYY-MM-DD`.

No `fingerprint` field lives in the stamp itself — a fingerprint embedded
in a doc would need updating every time the doc changes, which is
circular. Fingerprints instead live in the **ledger** (§3), recorded
externally at generation time and re-checked at consumption time. That
comparison — not a self-reported field — is what catches corruption.

## 2. Privacy tiers

Stated guarantees for what crosses which boundary:

- **Tier 0 — shared.** `branch`, `commit`, `actor`, `generated_at`,
  `fingerprint`. Nothing here that git itself doesn't already disclose to
  anyone with repo access.
- **Tier 1 — opaque join key.** `session`. Resolvable only by whoever owns
  `~/.claude/projects/<slug>/`. Lets the owner trace a doc back to its full
  transcript without exposing that transcript to anyone else.
- **Tier 2 — never shared.** Transcript content itself. Crosses a trust
  boundary only via a curated doc (a runbook, a memory entry, a handoff) —
  never by raw transcript excerpt or pointer-plus-access.

## 3. Ledger event schema

One JSON object per line, one physical file per **writing session**
(never a single shared file — concurrent sessions would merge-conflict on
it):

```
docs/dev/ledger/<session>.jsonl
```

Each line, in this field order:

```json
{"event": "generated", "doc": "docs/dev/handoffs/feat-handoff-integrity-kit.md", "session": "<uuid>", "branch": "feat/handoff-integrity-kit", "commit": "abc1234", "actor": "amodal1", "agent": "anthropic/claude-sonnet-5", "ts": "2026-07-17T21:03:00Z", "fingerprint": "9f3a1c2e8b7d"}
```

- `event` — one of `generated`, `consumed`, `failed`, `blocked`.
  - `generated`: a doc was produced and passed structural + verbatim
    validation against its template.
  - `failed`: a doc was produced but validation failed at generation time
    (authoring corruption — e.g. a heading dropped mid-edit). Surfaced,
    never silently patched over.
  - `consumed`: a later session read the doc, validation passed, and its
    fingerprint matched the most recent `generated` event on record for
    that same `doc` path.
  - `blocked`: a later session read the doc and either validation failed
    or the fingerprint did not match the last `generated` record —
    corrupted input is a blocked gate: surface and stop, never silently
    reconstruct.
- `doc` — the doc's path, relative to repo root, POSIX separators.
- `session`, `branch`, `commit`, `actor`, `agent` — same meaning as the
  stamp (§1), describing the session that ran the check, not necessarily
  the session that originally wrote the doc.
- `ts` — UTC timestamp, `YYYY-MM-DDTHH:MM:SSZ`.
- `fingerprint` — `sha256` of the doc's newline-normalized text,
  hex-digest truncated to 12 chars, computed fresh by the checking tool at
  the moment it runs. This is the value compared across `generated` →
  `consumed`/`blocked` pairs for the same `doc` path.

Reads join across every shard (`docs/dev/ledger/*.jsonl`) on demand — the
ledger is never aggregated into a second stored form.

## 4. Verbatim sections and structural checks

A template (e.g. `docs/dev/AGENT_HANDOFF_TEMPLATE.md`) declares two kinds
of content:

- **Structural headings** — any ATX heading (`##` or deeper; the template's
  own `#` title is exempt, since instantiated docs get their own title).
  A doc built from the template must contain every one of these headings,
  in the same relative order. Placeholder spans in a template's heading
  text (`<!-- like-this -->`) match anything in the doc's corresponding
  heading.
- **Verbatim sections** — a heading whose body's first non-blank line is
  exactly the marker `<!-- verbatim -->`. Everything from the line after
  that marker to the next heading of equal-or-shallower depth is canonical
  text that every instantiated doc must reproduce byte-for-byte (trailing
  whitespace per line ignored). Headings without the marker are
  structural-only — required to exist, free-form underneath.

`scripts/verify_doc_template.py <doc> <template>` implements both checks,
generically, for any doc/template pair — see that script's own docstring
for the CLI.

## 5. Workflow

1. **Generation.** The writing session builds the doc from its template,
   fills in the stamp (§1), then runs:
   `python scripts/verify_doc_template.py <doc> <template> --event generated --agent <agent>`.
   A failure here is authoring corruption — fix the doc, don't silence the
   check.
2. **Consumption.** The reading session, before acting on the doc's
   content, runs the same command with `--event consumed`. A `blocked`
   result is the doc's first output to the user — surface it and stop.
   Never reconstruct silently, even if the reconstruction looks obviously
   correct.
