```toml
schema = 1
id = 82
kind = "item"
title = "BOARD.md's header line mixes two different item populations across its four counts"
status = "watching"
decision_owner = "user"
refs = [
  "scripts/work_items.py:437-438",
  "docs/dev/handoffs/pre-epic-b-intermediate-steps.md",
]
summary = "open_count sums ALL items; the other three counts sum top-level only -- one header line, two populations, undisclosed."
```

**The bug.** `scripts/work_items.py:437-438`:

```python
open_count = sum(1 for i in items.values() if i.status == "open")
status_counts = {s: sum(1 for i in top_level if i.status == s) for s in _STATUS_ORDER}
```

`open_count` (used for the `Open N / 10 ceiling` figure) sums over **every**
item, including epics and items nested under an epic. `status_counts` (used
for `Blocked`, `Deferred`, `Watching`) sums over `top_level` only — items
with `kind = "item"` and `epic = None`, deliberately excluding anything
rendered nested under an epic's own section (documented, intentional
behavior for the rendered list itself; the bug is that the **header
counts** silently inherit that exclusion for three of four figures while the
fourth does not).

**Measured impact, this session:** `open` all-items=4 / top-level=1;
`blocked` 8 / 3; `deferred` 7 / 7 (agree only by coincidence — no nested
deferred items exist); `watching` **40** / **37**. The three epic-nested
watching items are **30**, **34**, **57**.

**This is the unresolved discrepancy the incoming pre-Epic-B handoff could
not reconcile.** That handoff (`docs/dev/handoffs/pre-epic-b-intermediate-steps.md`,
"Carried-forward observations" section) found items 30 and 34 nested under
epics, landed "one short of 36" against the header's watching count, and
published an explicit "not independently reconciled to 36 exactly" caveat
rather than a clean number. **Item 57 is the one it missed**, and the header
line's population mismatch is *why* no single recount from either the flat
section or the epic-nested items alone could ever reproduce it — the four
counts on that one line were never counting the same set of things.

**Not a staleness bug.** `python -m scripts.work_items check` reports `OK`
throughout — `BOARD.md` is correctly regenerated from the item files; the
defect is in what the header line **means**, not whether it matches its
source.

**Recurrence class, per C-11.** This is a fifth instance of "a number that
reads as one thing and is computed as another" in this project's own recent
history — after item 76's unchecked `declared` date, item 65's wrong-proxy
drift counter, §11.12's unbacked halt points, and the finding (recorded in the
incoming handoff) that `work_items.py`'s `depends_on` field is validated only
for referential existence, never for the referenced item actually being
`closed`. It is the **second** instance specifically inside `work_items.py`.

**No mechanism authored here** — a production-code change to
`scripts/work_items.py`'s `render_board()`, out of scope for the
governance-interval branch that found it. Recommendation, not endorsed: make
both counts sum over the same population (whichever one; `open` matching all
items is arguably the more useful figure since the 10-item WIP ceiling is
meant to reflect true total load), plus a test asserting the header
reconciles against an independent recount — closing exactly the gap that
cost the incoming handoff its own clean number.

## Updates

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed after reconciling the incoming handoff's own unresolved watching-count
discrepancy; root cause confirmed by reading `render_board()` directly, not
inferred from the count mismatch alone.
