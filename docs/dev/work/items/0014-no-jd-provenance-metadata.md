```toml
schema = 1
id = 14
kind = "item"
title = "No JD-identifying metadata anywhere in bootstrap/eval artifacts"
status = "open"
decision_owner = "agent"
depends_on = [11]
refs = ["evals/results/20260728_164119Z.jsonl"]
summary = "Eval result records only fixture/fixture_hash, no JD name - had to open jd.txt prose to learn what a run graded."
```

Found 2026-07-28 (owner's own observation mid-session: "there is no
identifying information in the bootstraps, so I have no idea what JDs they
were run against"). `evals/results/*.jsonl` records `fixture`,
`fixture_hash`, `eval_mode`, `prompt_version`, etc. — no field names the JD
by title/company. Same gap in the bootstrap artifacts themselves: nothing
short of opening `jd.txt`'s raw prose tells you what job posting a given run
was against. Likely the same underlying fix as item 11 (a provenance-bearing
manifest/naming scheme for bootstrap runs) — a manifest field naming the
JD(s) per run would close both gaps together.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking
