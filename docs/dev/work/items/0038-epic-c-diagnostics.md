```toml
schema = 1
id = 38
kind = "epic"
title = "Final March epic C - diagnostics console"
status = "closed"
decision_owner = "agent"
depends_on = [37]
branches = ["epic/c-diagnostics"]
refs = ["docs/dev/RELEASE_ARC.md"]
summary = "Run-lock gaps, sticky tabs, wait-state idioms; per-run drill-down modal; lay copy + info bubbles on every module."
resolution = "Merged to main as PR #148 (merge commit f3dd472). Closed on the owner's item-125 rule: merge PR plus its green CI run."
verified_by = [
  "PR #148 merge commit f3dd472 on main",
  "CI run 36360989332 (ci.yml, PR head): conclusion success; 8 pytest sessions, 0 reruns, 0 failures; re-check: gh run view 36360989332 --log | grep -c '[ux] RERUN' -> 0 (verified 2026-10-02)",
]
```

Third Final March epic. Briefs in `RELEASE_ARC.md` §"v1.1.0 Final March" (C1 fixes,
C2 per-run observability, C3 copy + progressive discovery).

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff

### 2026-10-02 — closed (`chore/release-v1.1.0`, E1 pre-flight)

Owner decision 2026-10-02 (item 125): an epic's C-11 closure artifact is its merge PR plus that PR's green CI run. PR #148 merged as `f3dd472`; its CI run `36360989332` concluded `success`, and the flake-rate store (the 2026-10-02 `flake_rates collect` shard `985e9282` (held uncommitted for slimming, item 144)) shows 0 reruns and 0 failures across its 8 pytest sessions.
