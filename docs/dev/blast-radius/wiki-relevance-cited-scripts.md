# Blast radius — wiki-relevance-cited-scripts

> **Branch:** `fix/wiki-relevance-cited-scripts`
> **Status:** enumeration complete. It was written after the instrument commit `701278c` and
> before the first edit to `scripts/wiki_relevance.py`.

---

## Surface

`scripts/wiki_relevance.py`, gated as a "helper" in `scripts/enforcement/blast_radius.py:160`:
"the classifier behind a merge-blocking freshness gate".

- **`RELEVANT_OVERRIDES`** (frozenset): 20 entries are added and 2 dropped, to equal the
  wiki-cited set the instrument test derives. This is a data change. Every
  `is_wiki_relevant()` answer for a `scripts/` path changes with it.
- **The module docstring:** its sentence naming the four "cited" overrides is replaced by a
  pointer to the derivation test, plus the measured reason the list stays explicit.
- **Unchanged:** `is_wiki_relevant()`, `filter_relevant()`, `MIXED_PREFIXES`,
  `IRRELEVANT_*` and `KNOWN_RELEVANT_TOP_LEVEL`.

---

## Enumeration

The searches were run with ripgrep (the Grep tool) over the whole tree, 2026-10-06, on
`main` 542da4a / this branch.

1. **Code consumers.** Pattern `RELEVANT_OVERRIDES|MIXED_PREFIXES|is_wiki_relevant|filter_relevant|wiki_freshness import|import wiki_freshness|from scripts import wiki_relevance`
   over `*.{py,sh,mjs}` found 5 files outside the module itself:
   - `hooks/wiki-freshness-reminder.sh`
   - `scripts/wiki_freshness.py`
   - `scripts/enforcement/guards/block_merge_to_main.py` (via `wiki_freshness`)
   - `tests/test_enforcement_core.py` (via `wiki_freshness`)
   - `tests/test_wiki_relevance_classification.py`

   Plus `tests/test_wiki_freshness_gate.py`, which imports `wiki_freshness` by a bare-path
   `import wiki_freshness`.
2. **Every name, prose included.** Pattern `RELEVANT_OVERRIDES|MIXED_PREFIXES|is_wiki_relevant|filter_relevant|wiki_relevance|perf_baseline|export_corpus_seed`,
   whole tree, excluding records (`docs/dev/{ledger,handoffs,diagnosis,blast-radius,archive,work/items,flake-rates}/**`,
   `docs/wiki/log.md`, `CHANGELOG*.md`, `BOARD.md`) and `docs-site/node_modules/**`.
   - **Live prose naming the module:** `.claude/workflows/n1-baseline.mjs:593`,
     `docs/dev/maintainer-lane.md:68`, `docs/dev/AGENT_HANDOFF_TEMPLATE.md:308`,
     `docs/dev/architecture.md:347`, `docs/dev/docs-ia-design.md:368,374,456`,
     `docs/dev/RELEASE_ARC.md:1706,2005`, `docs/governance/enforcement.md:108`,
     `scripts/enforcement/blast_radius.py:23,160`.
   - **`perf_baseline` / `export_corpus_seed` hits** are all about the scripts themselves
     (their CLI usage, importers, perf docs). **None restates them as wiki-cited.**
3. **Restatements of the override list.** Search: the four override names together, in live
   docs. Results:
   - the module docstring (`scripts/wiki_relevance.py:28-29`), which is changed here;
   - `docs/dev/diagnosis/wiki-freshness-relevance-classification.md:113-116`, a record (see
     Deferred).

   Nothing else (negative result).
4. **Negative results:**
   - No wiki page cites `wiki_relevance` (`grep` over `docs/wiki` excluding `log.md`: 0 hits).
     The branch's own change is therefore not wiki-relevant.
   - `static/`, `templates/` and `dashboard/`: 0 hits for the classifier's names
     (`RELEVANT_OVERRIDES`, `MIXED_PREFIXES`, `is_wiki_relevant`, `filter_relevant`,
     `wiki_relevance`). `dashboard/templates/dashboard.html:663,1432` do name
     `scripts.export_corpus_seed`, as CLI usage text, which is unrelated to classification.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py` (`RELEVANT_OVERRIDES`, docstring) | update | The surface itself. |
| 2 | `scripts/wiki_freshness.py:47,109` (`drift_count`) | no change | It calls `is_wiki_relevant()` per diff path. The count rises 8 → 9 at checkpoint `3798e2d1` (measured; diagnosis `## Observed`), under the 75-file `BLOCK_THRESHOLD`. |
| 3 | `scripts/enforcement/guards/block_merge_to_main.py:109-110` | no change | It consumes `wiki_freshness.check()`. Drift stays far under the block, so no new merge block follows. |
| 4 | `hooks/wiki-freshness-reminder.sh:56-57` | no change | The same call per diff path. 9 is still under its 10-file escalation threshold, so the wording tier is unchanged. |
| 5 | `tests/test_wiki_freshness_gate.py` | no change | It runs the CLI. Drift 9 still passes. |
| 6 | `tests/test_enforcement_core.py:51` | no change | It imports `BLOCK_THRESHOLD` only. |
| 7 | `tests/test_wiki_relevance_classification.py` | updated in `701278c` | The instrument. `test_no_stale_classification_entries` and `test_relevant_overrides_live_inside_a_mixed_prefix` also iterate `RELEVANT_OVERRIDES`, and every new entry is an existing file under `scripts/`, so both still hold. |
| 8 | Maintainer-lane close-out wiki-relevance check (`docs/dev/maintainer-lane.md:68`, `AGENT_HANDOFF_TEMPLATE.md:308`, `n1-baseline.mjs:593`) | no change | These are prose pointers to `is_wiki_relevant()`. They now get the right answer for cited scripts, which is the point of the item. |
| 9 | `scripts/enforcement/blast_radius.py:160` and its test `tests/test_blast_radius_classification.py` | no change | The registry entry stays: the module is still a gated helper. |
| 10 | `docs/dev/architecture.md:347`, `docs-ia-design.md`, `RELEASE_ARC.md`, `enforcement.md:108` | no change | They name the module or its audit test. None restates the override list. |

---

## Deferred

- **`docs/dev/diagnosis/wiki-freshness-relevance-classification.md:113-116`** names
  `perf_baseline.py` / `export_corpus_seed.py` as wiki-cited. That is false (diagnosis
  `## Falsified`), but the file is a dated evidence record, and records are not rewritten.
  The correction lives in this branch's diagnosis.
- **Transitive relevance is not modelled.** `docs/dev/perf/PERFORMANCE_HISTORY.md:177` (a
  wiki-cited file) mentions `scripts/perf_baseline.py`, but the wiki does not. The rule stays
  "the wiki cites it directly": a change that makes PERFORMANCE_HISTORY stale already counts
  through PERFORMANCE_HISTORY itself. Widening to transitive cites is out of item 153's scope.

---

## Verification

- `test_relevant_overrides_equal_wiki_cited_mixed_files` is an exact-set assertion, so a
  missed or extra entry fails it.
- Re-run the targeted suites after the edit with `-p no:rerunfailures`:
  `test_wiki_relevance_classification`, `test_wiki_freshness_gate`, `test_enforcement_core`,
  `test_blast_radius_classification` and `test_consumer_enumeration_gate`.
- Run `python -m scripts.wiki_freshness` and confirm it reports 9.
