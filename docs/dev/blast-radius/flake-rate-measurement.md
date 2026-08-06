# Blast radius — flake-rate-measurement

> **Branch:** `feat/flake-rate-measurement`
> **Status:** enumeration complete — written before the first edit to a gated surface.

---

## Surface

One gated surface is edited on this branch:

- **`scripts/wiki_relevance.py`** — the `IRRELEVANT_PREFIXES` frozenset literal
  (`scripts/wiki_relevance.py:40-67`), adding one new entry:
  `"docs/dev/flake-rates/"`. No other symbol in the file changes — `MIXED_PREFIXES`,
  `RELEVANT_OVERRIDES`, `KNOWN_RELEVANT_TOP_LEVEL`, and `is_wiki_relevant()`/
  `filter_relevant()`'s bodies are untouched.

New, ungated, no existing consumers: `scripts/flake_rates.py`,
`tests/test_flake_rates.py`, `docs/dev/flake-rates/README.md`,
`docs/dev/flake-rates/runs/*.jsonl`.

**Why this edit is required, not optional.** A committed store creates a new immediate
child of `docs/dev/`. `tests/test_wiki_relevance_classification.py::
test_every_top_level_entry_is_classified` walks the committed tree at three levels
(`""`, `"docs"`, `"docs/dev"`) and fails on any entry that is neither `IRRELEVANT_PREFIXES`/
`IRRELEVANT_FILES`/`MIXED_PREFIXES` nor `KNOWN_RELEVANT_TOP_LEVEL`. Left unclassified,
`docs/dev/flake-rates/` would default to **relevant**, and every `collect` commit
(each touching one or more `runs/<uuid>.jsonl` shards) would count toward
`wiki_freshness.py`'s merge-blocking drift counter — the exact defect item 35
(`docs/dev/work/items/0035-wiki-freshness-gate-counts-non-wiki-churn-as-drift.md`) exists
to describe, and this module was built specifically to stop.

---

## Enumeration

Ripgrep over the whole tree via the `Grep` tool (a shelled `grep -r` was tried first and
timed out at 120 s walking `node_modules/`/`.git/` — `ci-wait-wrapper.md`'s dossier
already recorded this exact trap; confirmed again here rather than re-learned the hard
way):

```
rg "from scripts\.wiki_relevance|from scripts import wiki_relevance|import scripts\.wiki_relevance"
  -> 3 hits, 3 files

rg "IRRELEVANT_PREFIXES|MIXED_PREFIXES|KNOWN_RELEVANT_TOP_LEVEL|RELEVANT_OVERRIDES" --glob "*.py"
  -> 21 hits, 2 files (scripts/wiki_relevance.py itself, tests/test_wiki_relevance_classification.py)

rg "is_wiki_relevant\(|filter_relevant\("
  -> 18 hits across code, docs, and handoffs

rg -l "wiki_relevance"
  -> 25 files total
```

Partitioned:

| Set | Count | What it is |
|---|---|---|
| **Real importers of the symbol** (`from scripts.wiki_relevance import is_wiki_relevant` / `from scripts import wiki_relevance`) | 3 | `hooks/wiki-freshness-reminder.sh:56` (embedded `python3 -c`), `scripts/wiki_freshness.py:47`, `tests/test_wiki_relevance_classification.py:20` |
| **References to the exact frozenset being edited** (`IRRELEVANT_PREFIXES`) | 2 files | the module itself, and the anti-rot audit test |
| Prose mentions of `is_wiki_relevant()` in handoffs / templates | 8 | all a single reused sentence in the close-out checklist ("if this branch's own diff touches any path `scripts/wiki_relevance.py` classifies…") — historical, never re-validated against current code |
| `blast_radius.py`'s own registry entry for this surface | 1 | `scripts/enforcement/blast_radius.py:158-162`, kind `helper` |
| `docs/wiki/log.md`, `docs/governance/enforcement.md`, `docs/dev/RELEASE_ARC.md`, `docs/dev/work/BOARD.md`, `docs/dev/diagnosis/wiki-freshness-relevance-classification.md` | 5 | narrative/history mentions, no executable coupling |

**Negative results, recorded as findings:**

- **No site references `IRRELEVANT_PREFIXES`'s *contents* by string** — every consumer
  goes through `is_wiki_relevant(path)` / `filter_relevant(paths)`, never inspects the
  frozenset directly except the module's own `test_wiki_relevance_classification.py`
  anti-rot checks. Adding one string literal to the set cannot break a caller's call
  shape.
- **`scripts/wiki_freshness.py`'s `BLOCK_THRESHOLD = 75`** (referenced from memory —
  verified present, unchanged) is not itself edited; classifying
  `docs/dev/flake-rates/` only *removes* future churn from its numerator. No behavior
  change for any existing counted path.
- **`docs/dev/blast-radius/` is itself already `IRRELEVANT_PREFIXES`-classified**
  (`scripts/wiki_relevance.py:47`) — this dossier file does not need its own
  classification decision.
- **No code globs `docs/dev/*/README.md`** — `rg "docs/dev.*README|README.*docs/dev"
  --glob "*.py"` → **0 hits**. `docs/dev/flake-rates/README.md` (task 6) has no
  additional consumer beyond the directory-prefix classification already covering it.
- **`scripts/enforcement/blast_radius.py`'s `ACKNOWLEDGED_NOT_GATED` / `GATED`
  registries are unaffected** — `scripts/flake_rates.py` is a new file with zero
  existing importers (fan-in 0, `FAN_IN_THRESHOLD = 8`), so it needs no registry entry
  on this branch. Named as a future trigger in its own module docstring instead (see
  the design's "Reuse vs duplicate" section): promote to a shared `gh`-wrapper module
  only when a third `gh`-consuming script appears, and classify that module then.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py:40-67` (`IRRELEVANT_PREFIXES`) | **update** | the surface — add `"docs/dev/flake-rates/"` |
| 2 | `scripts/wiki_relevance.py:201-211` (`is_wiki_relevant`) | **no change** | already iterates `IRRELEVANT_PREFIXES` generically; a new member needs no new branch |
| 3 | `hooks/wiki-freshness-reminder.sh:56-57` | **no change** | imports the function, not the set; behavior for the new prefix falls out of #1 automatically |
| 4 | `scripts/wiki_freshness.py:47,109` | **no change** | same — calls `is_wiki_relevant()` per changed path, no hardcoded prefix list of its own |
| 5 | `tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified` | **no change (satisfied by #1)** | this is the test that currently fails without #1; it walks the committed tree, so it goes green only once `docs/dev/flake-rates/` both exists on disk (task 6) and is classified (#1) |
| 6 | `tests/test_wiki_relevance_classification.py::test_no_stale_classification_entries` | **no change** | asserts every classified prefix exists as a real directory — must be true by the time `python -m scripts.gate` runs, so task 6 (README, creates the directory) lands no later than #1's commit |
| 7 | `scripts/enforcement/blast_radius.py:158-162` (registry entry for `wiki_relevance.py`) | **no change** | the registry's *reason* for gating ("a wrong answer here blocks merges or hides real drift") is exactly why this dossier exists; the entry itself needs no edit |
| 8 | 8 × handoff/template prose mentions of `is_wiki_relevant()` | **no change (deliberate)** | historical/canonical restatements of the close-out checklist sentence, not executable, not about `IRRELEVANT_PREFIXES`'s contents |
| 9 | `docs/dev/work/items/0035-…md` | **no change** | the item this module already answers; nothing here reopens or contradicts it |

---

## Deferred

**Not promoting a shared `gh`-wrapper module for `scripts/flake_rates.py` and
`scripts/ci_wait.py`.** Both scripts independently define a private `_gh()` subprocess
seam. Fan-in for a shared module would be 2, far below `FAN_IN_THRESHOLD = 8`, and
creating one now would mean editing `scripts/ci_wait.py` — a module merged 3 commits ago
and cited across multiple handoffs — for a ~10-line function, on a branch whose actual
job is measurement. Deferred with a stated trigger (in `scripts/flake_rates.py`'s own
module docstring): promote when a third `gh`-consuming script appears, and register the
new module in `blast_radius.py` at that time. A scheduled decision beats a silent
default; not tracked as a separate carry-forward item because the trigger condition is
self-evident (a third script either appears or it doesn't).

---

## Verification

How a missed consumer would surface:

1. `python -m scripts.gate` runs `pytest -m "not ux" -n auto`, which includes
   `tests/test_wiki_relevance_classification.py`. `test_every_top_level_entry_is_classified`
   fails loudly (naming the exact unclassified path) if #1 is missing or misspelled;
   `test_no_stale_classification_entries` fails loudly if the directory doesn't exist on
   disk when #1 lands. Together these are the exact-set assertion for this surface.
2. `python -m scripts.work_items check` — unaffected by this surface; run anyway as part
   of the standard gate.
3. `hooks/wiki-freshness-reminder.sh` has no committed test (`hooks/` is itself
   `IRRELEVANT_PREFIXES`-classified, so it is not wiki-cited and not part of the pytest
   suite) — its correctness rests entirely on consumer #3's "no change" holding, which
   is true by construction (`is_wiki_relevant` is a black box to the hook). Stated as a
   known gap, not claimed as tested.
