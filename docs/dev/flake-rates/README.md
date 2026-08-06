# CI flake-rate store

Per-test, per-attempt CI failure rates, extracted from GitHub Actions job logs by
[`scripts/flake_rates.py`](../../../scripts/flake_rates.py). Built so epic 19
(UX-suite flake sprint) and item 30 (its recurring child) can close on a falsifiable
`verified_by` artifact — charter **C-11**'s closure bar refuses a prose-only close, and
this store is the thing that can produce one. Design rationale, the real-log
observations (O-1…O-13) that shaped every regex here, and the traps a first-draft
parser hit silently are all in the module's own docstring — read that before extending
this store, not this file.

**This is an instrument, not a gate (C-0 / C-12).** Nothing here fails closed on a
test's rate. A threshold cannot be set before there is data; a follow-on
`report --check` failing above a committed budget is a **future item**, not something
this branch built or implied.

## Layout

```
docs/dev/flake-rates/
├── README.md          -- this file
└── runs/
    ├── <uuid>.jsonl    -- one shard per `collect` invocation
    └── ...
```

Sharded per invocation, never a single shared tail file — mirrors
[`docs/dev/ledger/README.md`](../ledger/README.md)'s identical rule: two `collect`
runs (from different branches, or a scheduled job and a human) appending to one file
would conflict on the tail. `report` joins every `runs/*.jsonl` shard on read; there is
no second, aggregated copy of this data anywhere.

## Record schema

One JSON object per line. `kind` discriminates three shapes:

### `kind: "run"`

One per run **listed**, ingested or not. An un-ingested row is what keeps the
run-level denominator knowable — a run that could not be fetched still counts as
"we saw it and could not read it," never silently vanishes from the picture.

| field | type | note |
|---|---|---|
| `run_id`, `run_attempt`, `run_number` | `str`, `int`, `int` | `gh run view --log` reads only the **latest** attempt — a red attempt superseded by a green retry is unrecoverable |
| `workflow`, `event`, `head_branch`, `head_sha` | `str` | the flake-vs-regression discriminators |
| `created_at`, `status`, `conclusion`, `url` | `str` | `url` is the citable anchor for a `verified_by` reference |
| `ingested` | `bool` | `false` means `skip_reason` explains why |
| `skip_reason` | `str` | `""` \| `"status=<x>"` (not yet completed) \| `"log-unavailable: <err>"` (retried on next `collect`) |
| `log_lines`, `jobs_seen` | `int`, `list[str]` | inertness canaries — a 17057→40 collapse across runs is visible here before it's visible anywhere else |
| `parser_version` | `int` | bump in `scripts/flake_rates.py` forces a conscious re-derive decision, never a silent semantic drift |

### `kind: "session"`

One per pytest invocation found in a run's log (a job can run pytest more than once —
see the module docstring's O-8).

| field | type | note |
|---|---|---|
| `run_id`, `run_attempt`, `head_sha`, `head_branch` | — | join keys back to the `run` record |
| `job`, `session_index` | `str`, `int` | which pytest invocation, in order, within that job |
| `tier`, `tier_source` | `str` | `ux` \| `pdf` \| `quality-not-ux` \| `quality-ux-skip` \| `unknown` |
| `complete`, `reconciled` | `bool` | `complete`: a summary line was found. `reconciled`: the executed-roster count agrees with the summary's declared passed+failed+error+xfailed+xpassed. **Unreconciled sessions are excluded from rate computation** — this is the load-bearing guard against a silently broken parser |
| `summary_raw`, `duration_s`, `counts` | `str`, `float\|null`, `dict` | verbatim summary text (the falsifiability anchor) + its parsed counts |
| `roster_digest`, `roster_size` | `str`, `int` | joins to a `roster` record |
| `skipped_nodeids`, `failed_nodeids`, `error_nodeids`, `xpassed_nodeids` | `list[str]` | always small, always stored inline regardless of tier |
| `rerun_attempts` | `list[[nodeid, count]]` | **primary** rerun signal, from `[ux] RERUN` marker lines |
| `alarm_declared`, `alarm_detail` | — | cross-check via `ci_wait.scan_reruns`, never reconciled away — a disagreement is reported, not resolved by picking one |
| `unparsed_lines`, `swallowed_traceback_lines`, `anomalies` | `int`, `int`, `list[str]` | `unparsed_lines > 0` also excludes the session; `swallowed_traceback_lines` is a rerun's own captured failure body (expected, not an anomaly) |

### `kind: "roster"`

Content-addressed: `{digest, size, nodeids}`, written once per distinct digest across
the **whole store**. Positional forward-carry was considered and rejected — rosters
oscillate as branches with different test sets interleave in CI history, so a
positional carry would silently mis-attribute one branch's roster to another's session.

Full rosters are stored for the **ux and pdf tiers only**. The quality tier
(`quality-not-ux`, `quality-ux-skip`) is single-attempt — `scripts/gate.py`'s pytest
steps never pass `--reruns` — so its per-test rate quantises to 0 or 1 per run and
needs hundreds of runs to be estimable at all. It is a **control arm** (does "the whole
suite is flaky" survive, or is it ux-specific?), not a per-test series: only its
`failed_nodeids`/`error_nodeids`/`xpassed_nodeids` (always small, inline on the
`session` record) are tracked, never a full 2200+-entry roster body.

## Dedup keys (on read)

- `run`: `(run_id, run_attempt)`
- `session`: `(run_id, run_attempt, job, session_index)`
- `roster`: `digest`

`collect` skips fetching a run only once a `kind: "run"` record with `ingested: true`
exists for its `(run_id, run_attempt)` — a listed-but-not-ingested run (transient fetch
error, or not yet `completed` when listed) is retried on every future `collect`. This
never gets stuck: it either eventually succeeds or keeps costing one cheap `gh` call.

## Usage

```bash
python -m scripts.flake_rates collect --limit 30      # fetch new runs into the store
python -m scripts.flake_rates report                  # ranked table, all tiers
python -m scripts.flake_rates report --tier ux --json  # machine-readable, one tier
```

Ranking is by **Wilson 95% lower bound** on the failure rate, not the raw rate — a test
at 1/1 must not outrank one at 12/300. Anything below `--min-attempts` (default 20)
goes to a separate "insufficient data" section, never silently dropped.

## LIMITS (C-0 / C-12 — read before citing a number from this store)

- **No intrinsic per-test flake probability is computable.** Every rate is conditional
  on tier, runner, and concurrent CI load — not a property of the test in isolation.
- **A rate does not distinguish "flaky" from "broken since commit X."** Use
  `distinct_shas_failed` as the cheapest available discriminator (≥3 distinct SHAs
  failing suggests genuine flake rather than a single regression), but this is a
  heuristic, not a proof.
- **Superseded workflow attempts are unrecoverable.** `gh run view --log` reads only
  the latest attempt; a red attempt retried to green loses its failure data permanently
  (O-10). Runs with `run_attempt > 1` are flagged in the `run` record, not silently
  averaged in.
- **Nothing before GitHub's ~90-day log retention window can ever be collected.** The
  store's history starts wherever the first `collect` happened to run, not wherever the
  flake class actually began.
- **The `report` output ranks; it does not attribute a mechanism.** A high Wilson bound
  says "look here first," never "this is why." Charter C-7 (evidence before mechanism)
  still applies to whatever investigation follows a number from this store.
- **This store cannot detect invention.** A parser bug that fabricates a plausible
  but wrong count would pass every reconciliation check that count happens to satisfy —
  reconciliation catches *inconsistency*, not *correctness* of an internally-consistent
  wrong parse.
