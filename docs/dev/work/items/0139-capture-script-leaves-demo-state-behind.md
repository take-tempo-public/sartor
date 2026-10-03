```toml
schema = 1
id = 139
kind = "item"
title = "capture_screenshots leaves its demo user behind: cleanup skips on failure, and DB rows always persist"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement"]
refs = [
  "scripts/capture_screenshots.py:408",
  "scripts/capture_screenshots.py:536",
  "docs/dev/blast-radius/docs-assets-enforcement.md",
]
summary = "cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs."
```

**Observed (2026-10-01, `feat/docs-assets-enforcement`, D4 step 4):**
- Two capture runs failed at Generate, and each left `configs/demo.config`, `resumes/demo/`
  and `output/demo/` behind. `cleanup()` (`scripts/capture_screenshots.py:408`) is called
  only after a successful run (`:536`), not from a `finally`.
- The demo candidate's database rows are never removed, by design (the comment at the end
  of `cleanup()`). An earlier run had imported the synthetic résumé with year-only dates,
  and those rows kept tripping the month-precision gate on every later run. The full
  evidence trail is the D4 dossier's step-4 addendum. The owner had the stale rows removed
  by hand on this branch.

**Why it matters:** the capture's output depends on whatever earlier runs left in the
owner's database, not only on the fixture. A run can fail, or show duplicate roles, for
reasons the script never sees.

**Fix direction (not built):**
- Move `cleanup()` into a `finally`.
- Have the script start from a known-empty demo candidate. That needs a delete path for a
  candidate's corpus, which doesn't exist yet (item 133). Until it does, a pre-run check
  that **refuses** when the demo candidate already holds roles would at least fail loudly
  at the start, instead of at Step 5 after the paid calls.

### 2026-10-02 — re-parented out of epic 39 (`chore/release-v1.1.0`)

Epic 39 merged as PR #150 and closed. The owner directed its open children to stand on their own under Open, rather than hold the epic open.
