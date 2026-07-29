```toml
schema = 1
id = 16
kind = "item"
title = "evals/runner.py --suite real is non-functional - no fixtures exist"
status = "watching"
decision_owner = "user"
refs = ["evals/runner.py:163-196", "evals/fixtures/real/"]
summary = "No jd.txt/expected.json under evals/fixtures/real/ anywhere in this project - --suite real exits 1, zero LLM spend."
```

Found 2026-07-28 during PX-39 research. `_load_fixture` unconditionally
reads `jd.txt` and `expected.json` from every subdirectory of
`evals/fixtures/real/`; both `robert/` and `testuser/` currently have only
`seed.json`. Running `--suite real --seed ...` fails via the RH-2
zero-result-records guard. The documented workaround (`evals/README.md`)
pairs `--seed` with the synthetic suite instead. Needs a real JD + a
hand-authored `expected.json` (ground-truth `must_keywords`/
`forbidden_inventions`) to fix properly — owner-gated since it needs real
data the agent can't invent, not scheduled.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking
