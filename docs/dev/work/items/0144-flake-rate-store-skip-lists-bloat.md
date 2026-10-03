```toml
schema = 1
id = 144
kind = "item"
title = "flake_rates store: skipped_nodeids from the UX-skip leg is 63% of every shard"
status = "open"
decision_owner = "agent"
branches = ["chore/release-v1.1.0"]
refs = ["scripts/flake_rates.py", "docs/dev/flake-rates/README.md"]
summary = "8 MB shard from 123 runs: 5.0 MB is skipped_nodeids (full UX list per skip-only session); README says always small."
```

**Observed (2026-10-02, `chore/release-v1.1.0`).**
- **The shard:** `python -m scripts.flake_rates collect --workflow ci.yml --limit 130` wrote
  `docs/dev/flake-rates/runs/985e9282-2087-41c0-8aa9-f111fd748852.jsonl`, 8.06 MB for 123 runs.
- **Bytes per field:**

  | field | MB |
  |---|---|
  | `session.skipped_nodeids` | 5.04 |
  | `roster.nodeids` | 1.96 |
  | `session.counts` | 0.12 |
  | `run` records, all fields | 0.08 |

- **The cause:** the quality job's `pytest -m ux` skip-only leg skips every UX test. So each of
  those sessions stores the whole UX test list inline.
- **What the README says:** `docs/dev/flake-rates/README.md` describes `skipped_nodeids` as
  "always small, always stored inline". That is false for this tier.

**Owner decision (2026-10-02): slim, then commit.**
- The shard is **held uncommitted** in the working tree.
- **It is the only copy.** GitHub keeps CI logs for about 90 days. Four runs in this window had
  already expired, so the shard can't simply be re-collected later.
- **The fix:** store skip lists by digest, the way rosters already are (or drop them for the
  `quality-ux-skip` tier). Bump `parser_version`, re-write this shard from the local file
  rather than re-fetching, then commit it.
- **Risk until then:** a clean of the working tree loses the measurement that items 19, 30, 37,
  38 and 39 cite.

## Updates

### 2026-10-02 — filed on `chore/release-v1.1.0`
