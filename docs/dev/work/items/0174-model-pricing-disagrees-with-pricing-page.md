```toml
schema = 1
id = 174
kind = "item"
title = "MODEL_PRICING disagrees with the published pricing page for two live pins, claude-sonnet-5 and claude-haiku-4-5"
status = "closed"
decision_owner = "agent"
resolution = "2026-10-17: fixed on fix/model-pricing-rates. Sonnet 5 now 2/10 (cache 2.50/0.20) and Haiku 4.5 1/5 (cache 1.25/0.10) in hardening.MODEL_PRICING, per the pricing page rows read 2026-10-17; the updated assertions failed on HEAD first (docs/dev/diagnosis/model-pricing-rates.md). A new test requires every model pin to have a complete entry. Published figures computed at the old rates are left as dated records (owner decision); the 5.5 keys and Haiku 5.5's prompt-length tiers belong to item 137."
verified_by = [
  "tests/test_hardening.py::TestCallCost::test_known_sonnet5_record (failed on HEAD with 3.0 == 2.0, passes on the fixed tree)",
  "tests/test_hardening.py::TestCallCost::test_haiku_with_cache (failed on HEAD with 0.08 == 0.1, passes on the fixed tree)",
  "tests/test_hardening.py::TestCallCost::test_every_model_pin_has_complete_pricing",
]
branches = ["docs/model-55-eval-item", "fix/model-pricing-rates"]
refs = [
  "hardening.py:439-465",
  "hardening.py:1710-1740",
  "CHANGELOG.md:5487-5491",
  "docs/dev/diagnosis/model-pricing-rates.md",
  "docs/dev/work/items/0173-evaluate-claude-5-5-generation-models.md",
  "docs/dev/work/items/0137-review-models-and-settings-for-performance-and-cost.md",
  "scripts/enforcement/blast_radius.py:199-208",
]
summary = "MODEL_PRICING has Sonnet 5 at $3/$15 and Haiku 4.5 at $0.80/$4; the pricing page reads $2/$10 and $1/$5."
```

**Filed 2026-10-17 by the session that ran item 173's first step, the turn it found it (C-8).** Not a 5.5 problem:
it concerns the two models the product runs on today.

## What was observed

Source: the Anthropic pricing page, `https://platform.claude.com/docs/en/about-claude/pricing`, fetched on
2026-10-17 with the `WebFetch` tool (the full page text was saved to a file and the rows below were read from it, not
from a summary), compared with `hardening.py:446-465` at `main` `e490683`.

| model | field | `MODEL_PRICING` | pricing page |
|---|---|---|---|
| `claude-sonnet-5` | input | `3.00` | `$2 / MTok` |
| `claude-sonnet-5` | output | `15.00` | `$10 / MTok` |
| `claude-sonnet-5` | cache write | `3.75` | `$2.50 / MTok` (5m); `$4 / MTok` (1h) |
| `claude-sonnet-5` | cache read | `0.30` | `$0.20 / MTok` |
| `claude-haiku-4-5-20251001` | input | `0.80` | `$1 / MTok` |
| `claude-haiku-4-5-20251001` | output | `4.00` | `$5 / MTok` |
| `claude-haiku-4-5-20251001` | cache write | `1.00` | `$1.25 / MTok` (5m); `$2 / MTok` (1h) |
| `claude-haiku-4-5-20251001` | cache read | `0.08` | `$0.10 / MTok` |

- **Sonnet 5.** The page's footnote 3 reads: "The $2/$10 per million input/output token pricing for Claude Sonnet 5,
  announced at launch as introductory pricing through August 31, 2026, is now the standard price. The previously
  scheduled increase to $3/$15 per million input/output tokens on September 1, 2026 will not occur." The code comment
  at `hardening.py:443-445` chose `$3/$15` as "the durable rate ... rather than re-staling on Sept 1"; that premise is
  now false. The table overstates Sonnet 5 cost by 1.5 times on input and output.
- **Haiku 4.5.** The table's four numbers (`0.80`, `4.00`, `1.00`, `0.08`) equal the page's row for **Claude Haiku
  3.5** (`$0.80 / $1 / $0.08 / $4`), not Haiku 4.5's (`$1 / $1.25 / $0.10 / $5`). Whether they were copied from the
  wrong row is **not established**; the observation is only that they match that row. The table understates Haiku 4.5
  cost by 20 percent on input and output.
- **A second source agrees.** The `claude-api` skill's cached model table (dated 2026-10-06) also lists Sonnet 5 at
  `$2.00 / $10.00` and Haiku 4.5 at `$1.00 / $5.00`. It is not independent of Anthropic's docs, only a second copy.
- **The comment says "Source: anthropic.com pricing as of 2026-07-05"** (`hardening.py:439`), so the table was never
  re-read after that date.

## Not verified

- Against an actual invoice or the Console usage page. The page and the skill table agree with each other, not with a bill.
- Which figures already published or recorded used these rates: `compute_call_cost` (`hardening.py:1710-1727`) feeds
  the dashboard and the telemetry-window spend numbers (for example item 140b's `$0.6678` for 8 runs, which mixes both
  models), and `evals/TUNING_LOG.md`, `CHANGELOG.md` and handoff cost lines quote such figures. **None was recomputed.**
  `CHANGELOG.md:5468` (2026-07-05) states the `$3/$15` choice and is a dated record that should not be edited.
- Whether `tests/test_hardening.py` pins the wrong numbers (it names these model strings; **not read**).

## Why it matters

Every Sonnet 5 cost figure the repo computes is 1.5 times the published price, and every Haiku 4.5 figure is 20 percent
under it, in opposite directions. Item 173 (absorbed into 137) needs correct costs to compare models at all, and
spend caps set from `compute_call_cost` windows inherit the error.

## Candidate fix (not chosen)

A small branch that corrects the two entries, keeps every existing key (historical `llm_calls.jsonl` records still name
them), updates the comment's date and source, and adds a test that every `SONNET_MODEL`/`HAIKU_MODEL` constant has a
`MODEL_PRICING` key. **`hardening.py` is a C-10 gated surface** (`scripts/enforcement/blast_radius.py:204`), so the
consumer enumeration comes first. It is a `fix/*` branch, so the C-7 diagnosis dossier needs a filled `## Observed`
first: the first commit is the comparison above, re-run against a real telemetry record. Adding the 5.5 keys is
item 137's work, not this item's; Haiku 5.5's prompt-length tiers (`$0.10/$0.50` up to 100,000 prompt tokens, `$0.50/$2.50`
above) cannot be expressed by the flat per-model rates `compute_call_cost` reads today, so that change needs a function
change, not only a new key.

## Updates

### 2026-10-17 - filed during docs/model-55-eval-item

Found while running item 173's first step. Nothing changed in `hardening.py`; no code was edited on this branch.

### 2026-10-17 - fixed on fix/model-pricing-rates

- **Done:** the two entries are corrected, the comment rewritten (source, date read, 5-minute cache-write), the two stale
  price/"no Haiku 5" comments in `analyzer.py` corrected (comments only, no `PROMPT_VERSION` bump), `CHANGELOG.md`
  `[Unreleased]` entry added. The record is `docs/dev/diagnosis/model-pricing-rates.md`; it holds the page rows, two real
  telemetry rows costed both ways (Sonnet `0.0504` -> `0.0336`, Haiku `0.0064` -> `0.008`) and the failing-on-HEAD run.
- **Two statements in this item as filed were wrong, corrected in the frontmatter `refs`:** `hardening.py` is **not** a
  C-10 gated surface (`hardening.py` and `analyzer.py` are in `ACKNOWLEDGED_NOT_GATED`, `scripts/enforcement/blast_radius.py:199-208`);
  and the Sonnet 5 pricing entry is `CHANGELOG.md:5487-5491`, not `:5468`. The body above is kept as filed. Item 173 repeats
  the gated claim in its own record; not edited.
- **Not done, on purpose:** figures already published at the old rates are left as dated records (owner, 2026-10-17); a
  dated note in `evals/TUNING_LOG.md` says which rates they used. `evals/README.md:977-986` estimates belong to item 134.
- **Still open elsewhere:** keys for the 5.5 models and Haiku 5.5's prompt-length tiers (a `compute_call_cost` change) are
  item 137's.
