```toml
schema = 1
id = 80
kind = "item"
title = "Merging to main while a long-running PR is open goes stale under strict branch protection -- sequencing guidance, not a defect"
status = "watching"
decision_owner = "agent"
refs = [
  "docs/dev/RELEASE_ARC.md",
]
summary = "Dependabot merges staled Epic A's open PR under strict:true, costing an update-branch cycle plus ~6 min CI."
```

**What happened.** Branch protection on `main` is `strict: true`, so
merging Dependabot PRs #116 and #101 while Epic A's PR #117 was open and
green made #117 stale, requiring `gh pr update-branch` plus a full second
CI cycle (roughly 6 minutes) before #117 could merge.

**This is not a defect.** `strict: true` is working as designed --
protecting `main` from merging a PR whose CI ran against a since-moved base
is exactly the point. The cost here is a real, observed **ordering** cost,
not a bug: two independent, unrelated merge streams (routine dependency
bumps vs. a long-running feature epic) collided under a policy that is
correct in isolation.

**Existing guidance already covers the resolution mechanism.**
`docs/dev/RELEASE_ARC.md` already documents that staleness is resolved
server-side with `gh pr update-branch`, never a local merge naming `main`
-- that part of the process worked as intended here and needs no change.
What's missing is **sequencing guidance**: batch `main`-moving merges
(Dependabot or otherwise) either before a long-running PR opens or after
it lands, rather than interleaving them mid-flight.

**Candidate directions -- record, do not design or endorse here:**

- A written norm: hold routine/Dependabot merges while a long-running
  feature PR is open, batching them for immediately before or after it
  lands.
- Alternatively, treat the `gh pr update-branch` + re-wait cost as
  acceptable and not worth process overhead, given it's a bounded,
  mechanical ~6-minute cost with a known resolution path already in
  `RELEASE_ARC.md`.

## Updates

### 2026-08-10 -- filed following Epic A close-out (PR #117, merge commit 162c1dc)

Filed as a sequencing-cost observation from the post-Epic-A review; both
staleness events (Dependabot #116, #101 vs. PR #117) were observed directly
during Epic A's close-out. `decision_owner = "agent"` -- whether to adopt a
batching norm is a process-mechanics call within existing release
discipline, not a product or governance decision.
