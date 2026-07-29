```toml
schema = 1
id = 23
kind = "item"
title = "analyzer.py split (prompts.py + client.py seams) - design-first, deferred"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/reviews/2026-07-efficiency/prescriptions.md:61",
]
summary = "PX-52, WATCH: extract prompts.py/client.py when prompt work next opens the file, not a standalone refactor."
```

Found during the 2026-07-29 old-system-vs-board migration-gap sweep
(`fix/bootstrap-annotation-overwrite`). PX-52 (`docs/dev/reviews/2026-07-efficiency/prescriptions.md:61`)
was disposed **WATCH** during the 2026-07 efficiency review: "Extract
prompts.py + client.py along the identified seams when prompt work next
opens the file; not a standalone pre-public refactor. Judges agreed." —
explicitly deferred post-v1.1.0, trigger = next major prompt-surface work.
It was never migrated onto `docs/dev/work/BOARD.md` when the old-ledger
migration happened (`chore/work-item-tracking`), because it lived in the
efficiency-review register, not `RELEASE_CHECKLIST.md`'s Carry-forward
ledger — outside that migration's scope, not an oversight in it.

`decision_owner = "user"`: this touches `analyzer.py`, the sole home of
every LLM call boundary (charter C-6) — a structural split of that file is
an architecture change, not a mechanical one.

## Updates

### 2026-07-29 — filed during fix/bootstrap-annotation-overwrite, migration-gap sweep
