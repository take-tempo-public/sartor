# Blast radius — n1-baseline-pipeline

> **Branch:** `feat/n1-baseline-pipeline`
> **Status:** enumeration complete

---

## Surface

`scripts/wiki_relevance.py` — the `IRRELEVANT_FILES` frozenset literal
(`scripts/wiki_relevance.py:75-90`), adding one new entry:
`"docs/dev/n1-baseline-pipeline.md"` (this branch's new contract/runbook doc),
beside `"docs/dev/epic-a-chain-design-corrections.md"` whose rationale-comment
convention it follows. No function, signature, or other set changes.

Why this bucket and not `KNOWN_RELEVANT_TOP_LEVEL`: the doc describes **agent
orchestration tooling** — the same character as the `hooks/`, `commands/`,
`agents/`, and `.claude/` prefixes, all already classified irrelevant ("agent
tooling, not product") — and the pipeline it documents has zero validated runs.
Revisit on the first authorized run (recorded in the entry's comment).

---

## Enumeration

Re-derived this session (2026-08-11), not carried from the prior dossier for
this surface (`docs/dev/blast-radius/flake-rate-measurement.md` — its counts
were re-checked, not trusted):

```
rg -n "wiki_relevance|is_wiki_relevant" --glob "*.{py,sh,yml,yaml,json,toml}"
  -> 41 hits across 8 files (full listing read; three are real importers, below)
rg -n "wiki_relevance" --glob "*.md"
  -> hits confined to: AGENTS.md:222, CHANGELOG.md:438,
     docs/dev/AGENT_HANDOFF_TEMPLATE.md:308, docs/governance/enforcement.md:108,
     docs/dev/blast-radius/flake-rate-measurement.md (prior dossier),
     docs/wiki/log.md (historical log entries), handoffs (historical)
```

Negative result recorded: no importer outside the three below; no JS/Jinja/CSS
consumer exists for this module (0 hits outside `*.py`/`*.sh`/`*.md`).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py:75-90` (`IRRELEVANT_FILES`) | **update** | the surface — add `"docs/dev/n1-baseline-pipeline.md"` with rationale comment |
| 2 | `scripts/wiki_relevance.py:212-225` (`is_wiki_relevant` / `filter_relevant`) | **no change** | iterate the sets generically; a new member needs no new branch |
| 3 | `scripts/wiki_freshness.py:47,109` (imports `is_wiki_relevant`) | **no change** | additive entry correctly excludes the new doc from the drift count |
| 4 | `hooks/wiki-freshness-reminder.sh:56` (embedded `python3 -c` import) | **no change** | same generic consumption as #3 |
| 5 | `tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified` | **no change (satisfied by #1)** | the consumer this edit exists FOR: it walks `git ls-tree HEAD`, so it reddens post-commit unless the new `docs/dev/` child is classified in the same commit that creates it (the PR #105 / corrections-doc recurrence, `epic-a-chain-design-corrections.md:262-296`) |
| 6 | `tests/test_wiki_relevance_classification.py::test_no_stale_classification_entries` | **no change** | asserts classified files exist in the tree — true because the doc and the entry land in the same commit |
| 7 | `scripts/enforcement/blast_radius.py:158-163` (registry entry gating this surface) | **no change** | its stated reason ("a wrong answer here blocks merges or hides real drift") is why this dossier exists; the entry needs no edit |
| 8 | Prose mirrors (`AGENTS.md:222`, `AGENT_HANDOFF_TEMPLATE.md:308`, `enforcement.md:108`, docstring mentions in `tests/test_blast_radius_classification.py:3`, `tests/test_ci_wait.py:15`, `tests/test_consumer_enumeration_gate.py:7`) | **no change** | all reference the module generically ("any path `is_wiki_relevant()` classifies…"), none enumerate set members |

---

## Deferred

Nothing deferred.

---

## Verification

`tests/test_wiki_relevance_classification.py` is the exact-set assertion that
fails loudly in both directions: unclassified new `docs/dev/` child →
`test_every_top_level_entry_is_classified` red; entry without the file →
`test_no_stale_classification_entries` red. Both run inside
`python -m scripts.gate` (pytest step) and in CI. A missed consumer of the
*module* would surface as an import error in the same gate.
