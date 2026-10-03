```toml
schema = 1
id = 39
kind = "epic"
title = "Final March epic D - documentation + information architecture"
status = "closed"
decision_owner = "agent"
depends_on = [38]
branches = ["epic/d-docs-ia"]
refs = ["docs/dev/RELEASE_ARC.md"]
summary = "IA research + design; full user/dev docs split; user + dev content; screenshots, links, doc-governance lints."
resolution = "Merged to main as PR #150 (merge commit f66d3a9). Closed on the owner's item-125 rule: merge PR plus its green CI run."
verified_by = [
  "PR #150 merge commit f66d3a9 on main",
  "CI run 37038411124 (ci.yml, PR head): conclusion success; 8 pytest sessions, 0 reruns, 0 failures; re-check: gh run view 37038411124 --log | grep -c '[ux] RERUN' -> 0 (verified 2026-10-02)",
]
```

Fourth Final March epic. Briefs in `RELEASE_ARC.md` §"v1.1.0 Final March" (D1
research + IA design, D2 mechanical split, D3 content, D4 assets + enforcement).
Child: item 9 (visual assets, sprint D4). The D1/D4 wordmark lint must inherit
item 2's exclusions.

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff

### 2026-09-27 — unblocked; D1 started (`feat/docs-ia-design` off `epic/d-docs-ia`)

Epic C (item 38) merged to `main` as PR #148 (`f3dd472`). Owner chose the epic
integration-branch shape (`epic/d-docs-ia`, one PR per epic) and D1 before the
overdue reduction sprint (session `84995956`).

### 2026-10-02 — closed (`chore/release-v1.1.0`, E1 pre-flight)

Owner decision 2026-10-02 (item 125): an epic's C-11 closure artifact is its merge PR plus that PR's green CI run. PR #150 merged as `f66d3a9`; its CI run `37038411124` concluded `success`, and the flake-rate store (the 2026-10-02 `flake_rates collect` shard `985e9282` (held uncommitted for slimming, item 144)) shows 0 reruns and 0 failures across its 8 pytest sessions.
