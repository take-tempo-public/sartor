```toml
schema = 1
id = 58
kind = "item"
title = "A handoff amended after its `generated` stamp blocks the next session, with nothing warning at authoring time"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/handoffs/epic-a-chain-design-corrections.md",
  "scripts/verify_doc_template.py",
  "docs/dev/prov/SPEC.md",
]
summary = "Handoff amended after its generated row; fingerprint and stamp both drift, and the next session hits a C-9 block."
```

**Observed, 2026-08-08, at the start of `feat/corpus-polish`.** The incoming
handoff failed its C-9 consumption gate:

```
python scripts/verify_doc_template.py \
  docs/dev/handoffs/epic-a-chain-design-corrections.md \
  docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent claude-opus-5
-> BLOCKED: fingerprint mismatch: doc is c5b7dac135ae,
   last 'generated' ledger record was 0ff3cae9f13c
```

The cause was benign in origin and is fully reconstructible from the artifacts:

1. The authoring session stamped `generated` at `2026-08-08T16:16:10Z`,
   fingerprint `0ff3cae9f13c`, commit `d9c9f6f`
   (`docs/dev/ledger/808060be-fabe-421c-9cf3-c13945ac1c6e.jsonl`).
2. Commit `b191de5` (2026-08-08T17:01:26Z, the CI-red fix on PR #115) then
   **amended the handoff** — +19 lines adding finding 10, and "Three recognized
   recurrences" → "Four" with a new recurrence 4.
3. No `generated` event was ever written for the amended content.

Structural and verbatim validation of the amended file **passes** (a bare
`verify_doc_template.py` run returns `OK (fingerprint c5b7dac135ae)`), so this is
a provenance-chain break, not content corruption. The guard failed closed
correctly. Resolution required an out-of-band re-stamp by the authoring session.

**A second, quieter half of the same drift:** the handoff's own in-doc stamp
(`docs/dev/handoffs/epic-a-chain-design-corrections.md:1`) still reads
`commit=d9c9f6f` while the content it describes is `b191de5`'s. Nothing compares
the stamp's `commit=` against reality, so that half produced no block at all — it
was found only by reading the line.

**Candidate mechanism, deliberately not built here.** A commit-time check could
compare a changed `docs/dev/handoffs/*.md` against the most recent `generated`
row for that path and refuse the commit when they disagree — catching both halves
at authoring time instead of at the next session's first move. It is not built on
this branch: `docs/dev/prov/SPEC.md` and the verifier are C-10 gated surfaces, the
change belongs on its own branch with a blast-radius dossier, and it is outside
sprint A1's scope.

**C-11 status, stated explicitly:** this is the **first** observed instance of
this shape, not a recurrence, so filing rather than gating is compliant *this
time*. A second instance triggers C-11 and the response is then a mechanism that
fails closed, not another item update. That is the clock this entry starts.

## Updates

### 2026-08-08 — filed on `feat/corpus-polish` (found consuming the incoming handoff)
