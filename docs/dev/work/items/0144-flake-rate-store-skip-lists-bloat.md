```toml
schema = 1
id = 144
kind = "item"
title = "flake_rates store: skipped_nodeids from the UX-skip leg is 63% of every shard"
status = "closed"
decision_owner = "agent"
branches = ["chore/release-v1.1.0", "chore/flake-shard-slim"]
refs = ["scripts/flake_rates.py", "docs/dev/flake-rates/README.md"]
summary = "8 MB shard from 123 runs: 5.0 MB is skipped_nodeids (full UX list per skip-only session); README says always small."
resolution = "Done on chore/flake-shard-slim (2026-10-03). Parser v2 stores skip sets by digest as roster records and de-duplicates rosters per shard (v1 did it per run, the 1.96 MB roster share). The held shard 985e9282 was rewritten offline with the new slim subcommand, 8,063,786 -> 1,236,557 bytes, and committed; report --json output was byte-identical before and after, and a check against a pre-slim copy recovered every session's skip list."
verified_by = [
  "tests/test_flake_rates.py::TestSlimV1Records::test_skip_lists_become_digests_with_one_roster_per_distinct_set",
  "tests/test_flake_rates.py::TestSlimV1Records::test_slim_preserves_compute_rates",
  "tests/test_flake_rates.py::TestEncodeSessionRosterPolicy::test_skipped_set_is_stored_by_digest_not_inline",
]
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

### 2026-10-03 — slimmed and committed on `chore/flake-shard-slim`
- **Second bloat found while reading `_collect`:** `seen_digests` was reset per *run*, so the
  same UX roster was rewritten once per run (237 roster records in this shard; 10 distinct).
  That is the 1.96 MB `roster.nodeids` row above. De-duplication is now per shard.
- **Encoding (parser v2):** `session.skipped_digest` + `skipped_size`, the set stored as a
  content-addressed `roster` record. New `slim` subcommand rewrites a v1 shard offline
  (`scripts/flake_rates.py` `slim_v1_records`).
- **The shard:** `python -m scripts.flake_rates slim docs/dev/flake-rates/runs/985e9282-….jsonl`
  → `1214 -> 987 record(s), 8063786 -> 1236557 bytes`.
- **Nothing lost (checked, not assumed):**
  - `report --json --min-attempts 1` output is byte-identical before and after (SHA-256 equal,
    71,358 bytes; exit 3 both times, the pre-existing PARTIAL from 1 unreconciled session).
  - A check script against a hash-verified pre-slim copy: 854 sessions and 123 runs in both;
    every session's skip list equals the roster its digest names; every other field equal;
    every v1 roster digest still present.
- Tests: `tests/test_flake_rates.py` `TestSlimV1Records` + two `TestEncodeSessionRosterPolicy`
  cases. The older committed shard `2a086ca2` (2.1 MB) stays v1; `report` reads both.
