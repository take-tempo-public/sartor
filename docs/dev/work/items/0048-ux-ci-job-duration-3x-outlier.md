```toml
schema = 1
id = 48
kind = "item"
status = "watching"
decision_owner = "agent"
title = "UX CI job ran 14m49s against a ~5m baseline on PR #102 — 3x outlier, green, uncharacterized"
refs = [
  ".github/workflows/ci.yml",
  "scripts/ci_wait.py",
]
summary = "ux job took 14m49s on PR #102 vs ~5m1s on PR #100 — zero reruns, so not a flake; the runtime is the anomaly."
```

Observed 2026-08-05 on PR #102 (`feat/ci-wait-wrapper`), reported by
`python -m scripts.ci_wait 102`:

- **PR #102** — `UX / a11y / PDF (Playwright, py3.12)` → `pass`, **14m49s**
- **PR #100** — same job, same workflow → `pass`, **5m1s** (recorded in the item-44 closure)

Roughly **3x** the established duration, on a branch whose diff contains **no UX-tier
change at all** (`scripts/ci_wait.py`, `tests/test_ci_wait.py` and docs; the 21 new tests
are non-UX and the local ux tier was unchanged at 138 passed / 1 xfailed / 1 xpassed).

**This is not a flake, and it must not be filed as one.** The job passed, and the wrapper
scanned the job log directly and found **zero `RERUN` markers and zero rerun-rate alarm
lines** — so no test needed a retry. Whatever this is, it is not the absorbed-retry class
items 44/46/47 cover. Filing it as a flake would corrupt that class's evidence base.

**Why it is worth watching rather than ignoring.** The UX tier's whole documented flake
class is timing/contention-sensitive (`ci.yml`'s "Flake policy" block; item 29's
CPU-saturation mechanism). A runner slow enough to triple the wall-clock is, by
construction, a runner under materially different load than the one the 5m baseline came
from — which is the same variable those flakes are sensitive to. A duration outlier is
therefore a **leading indicator** for that class even when the run is green.

**Deliberately not diagnosed here (n=1).** One sample cannot distinguish a slow shared
runner, a cache miss on the ~150MB Chromium download (`actions/cache` step), or a real
slowdown in the suite. The honest statement is that it is uncharacterized.

**What would settle it:** per-job duration is already in `gh pr checks --json` output;
`scripts/ci_wait.py` reads that JSON and currently discards the elapsed field. Recording it
per run — or having the wrapper flag a job exceeding some multiple of its own recent median
— would turn this from an anecdote into a series, at no extra API cost. Not built on this
branch (scope was the wrapper itself).

## Updates

### 2026-08-05 — filed during feat/ci-wait-wrapper (owner-directed)

Filed at the owner's explicit direction after the wrapper surfaced the duration on its
first real use. Owner context: the UX-suite flake class has consumed more than a month of
sessions, and a full redesign of the suite is under active consideration.
