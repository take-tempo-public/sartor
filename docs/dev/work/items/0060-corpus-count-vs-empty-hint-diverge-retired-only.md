```toml
schema = 1
id = 60
kind = "item"
title = "Corpus count reads \"0 experiences\" while retired cards render, when every role is retired and Show retired is ticked"
status = "watching"
decision_owner = "agent"
refs = [
  "static/app.js",
]
summary = "Count reports live roles; the empty hint branches on total rows, so they disagree when every role is retired."
```

**Found by the sprint A1b adversarial review of the staged diff**
(`fix/experience-soft-retire`), not in production use.

Sprint A1b made the "Show retired" toggle govern the role LIST, not just card
bodies. Two nearby readers of `_corpusExperiences` now use different denominators:

1. `_corpusLiveCountText()` filters to `e.is_active !== false` — the count
   deliberately reports **live** roles, so the user is not told they have more
   experience available to a résumé than can actually reach one.
2. `_renderCorpusList` branches its empty-state hint on
   `_corpusExperiences.length === 0` — the **total**, retired included.

When a candidate's only roles are retired and the box is ticked, the list renders
those cards (each correctly flagged `RETIRED`) while the count above reads
"0 experiences". No crash, no wrong data, and "0 live roles" is defensible on its
own terms — but the two numbers visibly disagree on the same screen.

**Deliberately not fixed mid-sprint.** The A1b brief was the zero-bullet retire
no-op; this is a cosmetic seam the fix exposed rather than a defect in it, and the
per-sprint sequence files lower-severity review findings rather than chasing them.

Candidate fix when picked up: have the count append a retired suffix when the two
denominators diverge (e.g. `0 experiences · 2 retired`), which also removes the
only case where the count is silent about why the list is non-empty. That is a
copy decision as much as a code one.

**Not verified in a browser.** The divergence is read off both functions in
`static/app.js`; no UX-tier test covers role-level retire at all (recorded as an
inherited open risk in `docs/dev/handoffs/experience-soft-retire.md`), so this is
a reading, not an observation (C-7).

## Updates

### 2026-08-08 — filed on `fix/experience-soft-retire` (sprint A1b review finding, non-blocking)
