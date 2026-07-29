```toml
schema = 1
id = 17
kind = "item"
title = "PERFORMANCE_HISTORY.md and RELEASE_ARC.md contradict on eval-vs-live traffic source"
status = "closed"
decision_owner = "agent"
resolution = "Closed 2026-07-28 (docs/pipeline-truth-and-era4-baseline). Wider than filed: PERFORMANCE_HISTORY.md's self-contradiction was removed by replacing the whole Open Item section with the new Era 4 section; RELEASE_ARC.md:1358 (step 12) got a RESOLVED note explaining the harness method never could have worked (evals/runner.py hardcodes eval: at 5 call sites and uses it as its own cost-attribution key); COMPOSE_REWRITE_DIAL.md:157-166 also assumed the harness method and got corrected (item 8's evidence premise). Also widened the taxonomy beyond eval:/non-eval: to a 3-way eval:/bootstrap:/live split, documented in PERFORMANCE_HISTORY.md's Era 4 caveats."
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

### 2026-07-28 — CLOSED, docs/pipeline-truth-and-era4-baseline

Confirmed the three-way tension exactly as filed, plus a fourth file
materially affected: `COMPOSE_REWRITE_DIAL.md:159-163` piggybacked on
RELEASE_ARC step 12's harness method for its own evidence plan (item 8) — that
assumption is now also corrected. All four fixed in this branch; see item 6's
closure for the Era 4 baseline this resolved into.
