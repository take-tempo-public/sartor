# Blast radius — eval-redesign

> **Branch:** `docs/eval-redesign`
> **Status:** enumeration complete, written before the one gated edit below.

---

## Surface

One gated file, one line: `scripts/wiki_relevance.py`, the `KNOWN_RELEVANT_TOP_LEVEL` frozenset (`:159`). Add
`"docs/dev/eval-redesign-design.md"` between `docs/dev/documentation-architecture.md` and `docs/dev/handoff-integrity-design.md`
(sorted position). Nothing else in the file changes: no function, no other set.

**Why the edit is needed (observed).** The full gate failed on this branch at `pytest -m "not ux" -n auto` with exactly one failure,
`tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`, and the assertion read
`assert not ['docs/dev/eval-redesign-design.md']`: a new top-level `docs/dev/` file has to be acknowledged on purpose. Run record:
`python -m scripts.gate --result` read `FAILED -- ... failed step 'pytest -m "not ux" -n auto'` at the commit that first added the design doc; 3687 passed, 1 failed.

**Why this set and not `IRRELEVANT_FILES`.** The two sibling design docs (`docs/dev/docs-ia-design.md`,
`docs/dev/handoff-integrity-design.md`) are in `KNOWN_RELEVANT_TOP_LEVEL`, and `is_wiki_relevant` already returns `True` for the new file
(observed: `is_wiki_relevant('docs/dev/eval-redesign-design.md')` printed `True` before the edit). Adding it acknowledges the file and
changes no classification. `IRRELEVANT_FILES` would change the answer to `False` and the drift count with it.

---

## Enumeration

Run on `docs/eval-redesign` before the edit, whole tree, `git grep`, every name the surface goes by.

```
for n in wiki_relevance is_wiki_relevant filter_relevant KNOWN_RELEVANT_TOP_LEVEL IRRELEVANT_FILES \
         IRRELEVANT_PREFIXES RELEVANT_OVERRIDES MIXED_PREFIXES; do git grep -lE "$n" -- '*.py' '*.mjs' '*.js' '*.yml' '*.yaml' '*.toml' '*.sh' '*.json'; done
```

| Name | Files (code, CI, hook, workflow) |
|---|---|
| `wiki_relevance` | `.claude/workflows/n1-baseline.mjs`, `scripts/enforcement/blast_radius.py`, `scripts/wiki_freshness.py`, `scripts/wiki_relevance.py`, `tests/test_blast_radius_classification.py`, `tests/test_ci_wait.py`, `tests/test_consumer_enumeration_gate.py`, `tests/test_hook_witnesses.py`, `tests/test_tree_walk_gate.py`, `tests/test_wiki_relevance_classification.py` (10) |
| `is_wiki_relevant` | `scripts/wiki_freshness.py`, `scripts/wiki_relevance.py`, `tests/test_hook_witnesses.py`, `tests/test_wiki_relevance_classification.py` (4) |
| `filter_relevant` | `scripts/wiki_relevance.py`, `tests/test_wiki_relevance_classification.py` (2) |
| `KNOWN_RELEVANT_TOP_LEVEL` | `scripts/wiki_relevance.py` (definition only), `tests/test_wiki_relevance_classification.py:66,118,124` (2) |
| `IRRELEVANT_FILES`, `IRRELEVANT_PREFIXES`, `RELEVANT_OVERRIDES`, `MIXED_PREFIXES` | `scripts/wiki_relevance.py`, `tests/test_wiki_relevance_classification.py` (2 each) |

Negative results: no `.github/` workflow, no `.claude/settings.json` hook and no `scripts/gate.py` step names the module directly; they reach
it through `scripts/wiki_freshness.py` (`:47` import, `:109` call) and the tests. `grep` for `KNOWN_RELEVANT_TOP_LEVEL` in non-test code
returns only its definition, so **no function reads the set**; it is an acknowledgement list read by the audit test alone.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py:159` (`KNOWN_RELEVANT_TOP_LEVEL`) | **update** | add the one entry; the audit test requires it |
| 2 | `scripts/wiki_relevance.py:250` (`is_wiki_relevant`) | no change | does not read the set; returns `True` for the file before and after |
| 3 | `scripts/wiki_relevance.py:263` (`filter_relevant`) | no change | calls `is_wiki_relevant` |
| 4 | `scripts/wiki_freshness.py:47,109` (`drift_count`) | no change | counts `is_wiki_relevant` paths; the new file already counted, so the count does not move |
| 5 | `scripts/enforcement/adapters/wiki_reminder_hook.py:45` | no change | calls `drift_count` |
| 6 | `scripts/enforcement/guards/block_merge_to_main.py:109` | no change | imports the freshness threshold, not the classification |
| 7 | `tests/test_wiki_relevance_classification.py:66,94,118,124` | no change | the failing audit test passes once the entry exists; `test_no_stale_classification_entries` needs the file to exist, and it does |
| 8 | `tests/test_hook_witnesses.py`, `tests/test_ci_wait.py`, `tests/test_blast_radius_classification.py`, `tests/test_consumer_enumeration_gate.py` | no change | name the module in text or call `is_wiki_relevant` on fixed paths; none lists docs/dev entries |
| 9 | `tests/test_tree_walk_gate.py` | no change | lists tree walks with exact counts; this edit adds no walk |
| 10 | `scripts/enforcement/blast_radius.py:168` | no change | the registry row that gates this file |
| 11 | `.claude/workflows/n1-baseline.mjs:593` | no change | prose mention of the classifier |
| 12 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md:308`, `docs/dev/maintainer-lane.md:68`, `docs/dev/RELEASE_ARC.md:1709,2008`, `docs/dev/docs-ia-design.md:368-374` | no change | prose that describes the rule; the rule is unchanged |

---

## Deferred

- **Whether a proposal-only design doc should count toward wiki drift at all.** It does today, by default, and this edit keeps that: it
  follows the two sibling design docs rather than introducing a new class. Reclassifying design docs as irrelevant would change the drift
  count for those siblings too and is not this branch's decision. Not filed as an item (the board is over its ceiling); recorded here.
