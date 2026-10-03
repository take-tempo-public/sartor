```toml
schema = 1
id = 37
kind = "epic"
title = "Final March epic B - rendering + ATS correctness"
status = "closed"
decision_owner = "agent"
depends_on = [36]
branches = ["epic/b-render-ats"]
refs = ["docs/dev/RELEASE_ARC.md"]
summary = "Template companion staleness, education discipline, font capture; MM/YYYY dates, month hard block, approved fonts."
resolution = "Merged to main as PR #128 (merge commit 86dee5c). Closed on the owner's item-125 rule: merge PR plus its green CI run."
verified_by = [
  "PR #128 merge commit 86dee5c on main",
  "CI run 31922065281 (ci.yml, PR head): conclusion success; 8 pytest sessions, 0 reruns, 0 failures; re-check: gh run view 31922065281 --log | grep -c '[ux] RERUN' -> 0 (verified 2026-10-02)",
]
```

Second Final March epic. Briefs in `RELEASE_ARC.md` §"v1.1.0 Final March" (B1
template rendering bugs — evidence-first; B2 ATS conformance incl. the import-path
month surfacing).

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff

### 2026-10-02 — closed (`chore/release-v1.1.0`, E1 pre-flight)

Owner decision 2026-10-02 (item 125): an epic's C-11 closure artifact is its merge PR plus that PR's green CI run. PR #128 merged as `86dee5c`; its CI run `31922065281` concluded `success`, and the flake-rate store (the 2026-10-02 `flake_rates collect` shard `985e9282` (held uncommitted for slimming, item 144)) shows 0 reruns and 0 failures across its 8 pytest sessions.
