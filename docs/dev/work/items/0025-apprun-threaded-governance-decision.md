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

### 2026-10-18 - premise falsified, `fix/threaded-server-claim` (item 177 point 1)

**The premise that `app.run()` is single-threaded is false.** `Flask.run()` applies `threaded=True` by default, and
`tests/test_production_server_concurrency.py` answers a full request against `python app.py` itself while another connection
is half-sent, with the debug reloader on and off (Flask 3.1.3; the 3.0.0 source has the same default). Evidence and the
controls: `docs/dev/diagnosis/threaded-server-claim.md`. Nothing in `app.py` changed.

So the "governance decision" as framed (flip `threaded=True`) is already the behaviour. What remains is the owner's call on
whether to make it explicit or to say anything about the C-1 loopback-bind posture in light of it. The reported **freeze
during a diagnostics run** was never observed and single-threading does not explain it; its cause is unknown. I did not
change this item's status or summary (the board summary still repeats the false premise); that is for the owner.
