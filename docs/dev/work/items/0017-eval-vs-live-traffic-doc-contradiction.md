```toml
schema = 1
id = 17
kind = "item"
title = "PERFORMANCE_HISTORY.md and RELEASE_ARC.md contradict on eval-vs-live traffic source"
status = "open"
decision_owner = "agent"
depends_on = [6]
refs = ["docs/dev/perf/PERFORMANCE_HISTORY.md:178-194", "RELEASE_ARC.md step 12"]
summary = "PERFORMANCE_HISTORY asks for non-eval:* runs; RELEASE_ARC step 12 prescribes the harness, which DOES carry that prefix."
```

Found 2026-07-28 during PX-39 research. `PERFORMANCE_HISTORY.md`'s Open
Item says "A FEW real (non-eval:*) analyze -> clarify -> generate runs,"
but its own parenthetical allows `evals/runner.py --suite real` — and the
runner prefixes every fixture's `username` with `eval:` (`evals/runner.py:1219`
et al.), so a harness run would NOT satisfy its own "non-eval:*" phrasing.
`RELEASE_ARC.md` step 12 meanwhile explicitly prescribes the harness. Item 6
(PX-39) resolves this by using live-app historical traffic instead of either
— genuinely non-`eval:`-prefixed and not dependent on the currently-broken
`--suite real` path (item 16) — but the contradiction in the docs themselves
is still there and should get a one-line fix when item 6 lands.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking
