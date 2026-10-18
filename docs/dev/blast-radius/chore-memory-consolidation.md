# Blast radius — chore-memory-consolidation

> **Branch:** `chore/memory-consolidation`
> **Status:** enumeration complete. Written before the first edit to `scripts/wiki_relevance.py`
> (the new doc and this edit do not exist yet when this is committed).

---

## Surface

`scripts/wiki_relevance.py`, gated as a "helper" in `scripts/enforcement/blast_radius.py:167-172`: "the classifier behind a
merge-blocking freshness gate; a wrong answer here blocks merges or hides real drift."

- **`IRRELEVANT_FILES`** (frozenset): **one entry is added**, `docs/dev/engineering-recipes.md`, the new maintainer how-to
  that item 7 folds out of memory (seam-move and lint/typing-ratchet recipes). It is an addition to a data set; no function
  changes.
- **Unchanged:** `is_wiki_relevant()`, `filter_relevant()`, `RELEVANT_OVERRIDES`, `MIXED_PREFIXES`, `IRRELEVANT_PREFIXES`
  and `KNOWN_RELEVANT_TOP_LEVEL`.
- **Why `IRRELEVANT_FILES` and not `KNOWN_RELEVANT_TOP_LEVEL`.** The file is a maintainer runbook, the same character as
  `docs/dev/screenshot-capture.md` and `docs/dev/n1-baseline-pipeline.md`, which are already in `IRRELEVANT_FILES`
  (`scripts/wiki_relevance.py:88-97`). No wiki page cites it. Measured today: `python -m scripts.wiki_freshness` reads
  **65 files changed since the last ingest** (threshold 75). This branch also edits `docs/dev/README.md`,
  `scripts/doc_registry.py` and `scripts/doc_lints.py`, all of which `is_wiki_relevant()` returns `True` for (checked
  2026-10-18). A relevant new doc would add a fourth file to a count that is already 10 from blocking.

---

## Enumeration

Run 2026-10-18 on `chore/memory-consolidation` (HEAD `8f679f8`, one docs commit past `main` `de47905`), with `git grep`
(tracked files only; a first attempt with `grep -r` walked `node_modules` and was abandoned).

1. **The module by name, tracked non-docs files**
   (`git grep -c wiki_relevance -- . ':!docs' ':!CHANGELOG.md'`): 10 files.
   - `.claude/workflows/n1-baseline.mjs:1` (a prompt string, `:593`)
   - `scripts/enforcement/blast_radius.py:2` (a comment and the gated-surface entry)
   - `scripts/wiki_freshness.py:2`
   - `scripts/wiki_relevance.py:2` (itself)
   - `tests/test_blast_radius_classification.py:1` (docstring)
   - `tests/test_ci_wait.py:1` (comment)
   - `tests/test_consumer_enumeration_gate.py:1` (comment)
   - `tests/test_hook_witnesses.py:1`
   - `tests/test_tree_walk_gate.py:1`
   - `tests/test_wiki_relevance_classification.py:28`
2. **Every symbol the module exports**
   (`is_wiki_relevant|filter_relevant|RELEVANT_OVERRIDES|IRRELEVANT_FILES|KNOWN_RELEVANT_TOP_LEVEL|MIXED_PREFIXES|IRRELEVANT_PREFIXES`,
   excluding the module and its own classification test, and excluding `docs/` and `CHANGELOG.md`): **3 hits in 2 files** outside
   those: `scripts/wiki_freshness.py:47,87,109` and `tests/test_hook_witnesses.py:16,66`.
3. **Indirect consumers, through `wiki_freshness`**
   (`git grep -n wiki_freshness -- '*.py' '*.mjs' '*.yml' '*.sh' ':!docs'`):
   - `scripts/enforcement/adapters/wiki_reminder_hook.py:45`
   - `scripts/enforcement/guards/block_merge_to_main.py:109-110,155-172,317,372`
   - `scripts/flake_rates.py:206` (a comment)
   - `tests/test_enforcement_core.py:53,415-431`
   - `tests/test_wiki_freshness_gate.py:23-26,85-204`
   - `tests/test_wiki_cites.py:6` (a comment)
4. **Workflow files and extensionless hooks**
   (`git grep -n "wiki_relevance\|wiki_freshness" -- .githooks .github .claude/settings.json`): **0 hits.** CI reaches the
   classifier only through `pytest` (`tests/test_wiki_freshness_gate.py`, `tests/test_wiki_relevance_classification.py`).
5. **Docs that name it** (prose, not behavior): `docs/dev/maintainer-lane.md` (the close-out wiki-relevance step),
   `docs/governance/enforcement.md`, `docs/dev/architecture.md`, `docs/dev/RELEASE_ARC.md`,
   `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, plus records (diagnosis, blast-radius, handoffs, items). None restates the
   `IRRELEVANT_FILES` set.
6. **Classification of the paths this branch touches** (`python -c` over `is_wiki_relevant`, 2026-10-18):
   - `docs/dev/README.md` `True`
   - `scripts/doc_registry.py` `True`
   - `scripts/doc_lints.py` `True`
   - `scripts/wiki_relevance.py` `False`
   - `CHANGELOG.md` `False`
   - `docs/dev/work/items/0007-px46-memory-consolidation.md` `False`
   - `docs/dev/engineering-recipes.md` `True` today (default), `False` once the entry exists.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py` `IRRELEVANT_FILES` (`:77-101`) | **update** | Add `docs/dev/engineering-recipes.md` with a comment naming this dossier, as the three existing runbook entries do. |
| 2 | `tests/test_wiki_relevance_classification.py:56-99` (every immediate child of `docs/dev/` must be classified) | no change | Fails today only if the new file is committed unclassified; the new entry satisfies it. It passes `entry_rel_posix in IRRELEVANT_FILES` at `:62`. |
| 3 | `tests/test_wiki_relevance_classification.py:102-124` (stale-entry check) | no change | The entry names a file that exists once step 4 lands. It must land in the same commit as the file, or the check fails the other way. |
| 4 | `tests/test_wiki_relevance_classification.py:141-165` (spot assertions) | no change | They name other paths. |
| 5 | `scripts/wiki_freshness.py:47,109` (`drift_count`) | no change | Reads the classification; the new file is not counted, which is the intent. |
| 6 | `scripts/enforcement/guards/block_merge_to_main.py:109-172,317,372` | no change | Consumes `check()` and `BLOCK_THRESHOLD` only. |
| 7 | `scripts/enforcement/adapters/wiki_reminder_hook.py:45` | no change | Same. |
| 8 | `tests/test_wiki_freshness_gate.py` | no change | Builds its own throwaway repos; independent of this file's contents. |
| 9 | `tests/test_hook_witnesses.py:16,66` | no change | Asserts only `analyzer.py` is relevant. |
| 10 | `tests/test_tree_walk_gate.py:47` | no change | Its allowlist names `tests/test_wiki_relevance_classification.py` as a walker of `docs/wiki`; the file is untouched. |
| 11 | `.claude/workflows/n1-baseline.mjs:593` | no change | A prompt string that points at the module; no list is restated. |
| 12 | `scripts/enforcement/blast_radius.py:167-172` | no change | The gated-surface entry; its reason text stays true. |
| 13 | `tests/test_blast_radius_classification.py`, `tests/test_consumer_enumeration_gate.py`, `tests/test_ci_wait.py` | no change | Comments only. |
| 14 | `docs/dev/maintainer-lane.md`, `docs/governance/enforcement.md`, `docs/dev/architecture.md`, `docs/dev/RELEASE_ARC.md`, `docs/dev/AGENT_HANDOFF_TEMPLATE.md` | no change | Prose that names the module; none lists its entries. |

---

## Deferred

- **Registering the new doc touches two more wiki-relevant files** (`scripts/doc_registry.py`, `scripts/doc_lints.py:25`'s
  "39 registered docs" docstring), and `docs/dev/README.md`. They are not gated surfaces
  (`git grep -n "doc_registry\|doc_lints\|docs/dev/README" scripts/enforcement/blast_radius.py` printed **0 hits**), so they
  need no entry here. They do count toward wiki drift and trigger the close-out wiki-relevance check; that check is a
  step of the branch, not of this dossier.
- **No gate or test is added** for the recurrence behind the item (`MEMORY.md` growing until a hook flags it): the memory
  directory is outside the repo, so no committed test can fail on it (stated, charter C-11).

---

## Verification

- `python -m pytest tests/test_wiki_relevance_classification.py tests/test_wiki_freshness_gate.py tests/test_blast_radius_classification.py tests/test_consumer_enumeration_gate.py -q`
  after the edit. A missed classification surfaces as the "unclassified entry" failure at
  `tests/test_wiki_relevance_classification.py:96`; a premature entry as the stale-entry failure at `:104-124`.
- `python -c` over `is_wiki_relevant("docs/dev/engineering-recipes.md")` returns `False`, and
  `python -m scripts.wiki_freshness` still reads 65 plus the relevant files this branch edits, not 66 plus all four.
- Full `python -m scripts.gate`, cited with `python -m scripts.gate --result`.
