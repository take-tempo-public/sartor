```toml
schema = 1
id = 25
kind = "item"
title = "app.run(threaded=True) governance decision - deliberately deferred"
status = "deferred"
decision_owner = "user"
blocked_on = "owner governance call not yet made; touches the C-1-sensitive loopback-bind area, deliberately kept out of the diagnostics epic and every branch since"
refs = [
  "docs/dev/RELEASE_ARC.md:1471-1474",
]
summary = "Single-threaded app.run() freezes the app during a diagnostics run; making it threaded is an owner-gated C-1 call."
```

Found during the 2026-07-29 old-system-vs-board migration-gap sweep
(`fix/bootstrap-annotation-overwrite`). `RELEASE_ARC.md:1471-1474`: `app.py`'s
`app.run()` has no `threaded=True`, so the whole app freezes while a
diagnostics run executes. Explicitly called out as "a separate governance
decision (NOT epic bug work)" — making it threaded touches the C-1-sensitive
loopback-bind area, so it was deliberately kept out of the Diagnostics-DX
epic and left as an owner-gated call. Referenced consistently the same way
across multiple later branches (e.g. `docs/dev/diagnosis/compose-summary-draft-settle-hole.md:303-306`,
`docs/dev/handoffs/diagnostics-run-cancel.md:73`) into late July, always as
still-open, never resolved.

Never migrated onto `docs/dev/work/BOARD.md` — it lived in `RELEASE_ARC.md`'s
epic prose, not the Carry-forward ledger the old-system migration covered.

## Updates

### 2026-07-29 — filed during fix/bootstrap-annotation-overwrite, migration-gap sweep
