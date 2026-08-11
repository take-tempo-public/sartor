```toml
schema = 1
id = 81
kind = "item"
title = "wiki_freshness.py counts a deleted file as drift identically to a new one"
status = "watching"
decision_owner = "user"
refs = [
  "scripts/wiki_freshness.py:105-110",
  "docs/dev/epic-a-chain-design-corrections.md",
  "docs/dev/work/items/0065-wiki-freshness-counter-measures-the-wrong-thing.md",
]
summary = "drift_count() has no change-status filter -- a deletion inflates drift exactly like new content needing ingestion."
```

**The bug.** `scripts/wiki_freshness.py:105-110`'s `drift_count()` runs
`git diff --name-only <checkpoint> HEAD` and counts every wiki-relevant line
with **no filter on change status** — a deletion (`D`) counts identically to
an addition (`A`) or modification (`M`). A deleted file can never be
"ingested" — its only exit from the drift count is the checkpoint advancing
past it, which is exactly backwards: nothing about a deletion needs a wiki
pass to catch up on.

**How this was found.** `docs/dev/epic-a-chain-design-corrections.md`'s
pre-Epic-B robustness design pass (§16.1.D, §17 case 9) measured the current
2-file drift at `f42b2ea`→HEAD and found one of the two —
`docs/dev/work/BOARD_DEFERRAL.md` — was counted as drift **because it was
deleted** (`6c4aeda`; `git diff --name-status` returns `D`), not because
anything about it needed documenting.

**Relationship to item 65.** This is a mechanically distinct sub-case of item
65's already-diagnosed class (the counter measures "changed since checkpoint,"
not "coverage current") — the first instance with a cause traced to a
specific line rather than a judgement about page content. §17/§18 of the
design-corrections doc recommend folding this in as a concrete data point
toward item 65's eventual fix (leaning toward its "coverage-shaped drift"
option), not treating it as a separate mechanism.

**No mechanism authored here** — this is a production-code change to
`scripts/wiki_freshness.py`, out of scope for the governance-interval branch
that found it (`docs/pre-epic-b-review`). `decision_owner = "user"` because
it redesigns an existing enforcement/reporting surface.

## Updates

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed per C-11 (three confirmed false-drift instances is the bar for "a
recurring class, not a first sighting" — see §17 of
`docs/dev/epic-a-chain-design-corrections.md`).
