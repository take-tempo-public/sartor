# Blast radius — docs-ia-design

> **Branch:** `feat/docs-ia-design`
> **Status:** enumeration complete (written before the edit)

---

## Surface

`scripts/wiki_relevance.py` — the `KNOWN_RELEVANT_TOP_LEVEL` frozenset only. The change
adds one string, `"docs/dev/docs-ia-design.md"`, in alphabetical position among the
`docs/dev/*.md` entries (next to `docs/dev/docs-site-deploy.md` /
`docs/dev/documentation-architecture.md`). No function body, no other set, and no
prefix list changes.

**Why:** the gate run on this branch failed with exactly this:
`tests/test_wiki_relevance_classification.py:91` →
`AssertionError: Unclassified top-level entr(y/ies) for wiki-relevance: ['docs/dev/docs-ia-design.md']`
(`1 failed, 2866 passed, 6 skipped in 954.79s`). The new D1 design doc is a live reference
doc, so it gets the same classification as its sibling `documentation-architecture.md`
(`scripts/wiki_relevance.py:211`), which is relevant.

**Behaviour change: none.** `is_wiki_relevant("docs/dev/docs-ia-design.md")` already
returns `True` before the edit, because unclassified paths default to relevant. This
session ran it and printed `docs/dev/docs-ia-design.md True`. The edit only records that
classification on purpose, which is the audit test's contract.

---

## Enumeration

Grep across the whole tree, excluding frozen record directories (their mentions are
history, not callers):

```
git grep -n "wiki_relevance\|KNOWN_RELEVANT_TOP_LEVEL\|is_wiki_relevant" -- \
  ':!docs/dev/handoffs' ':!docs/dev/ledger' ':!docs/wiki/log.md' ':!docs/dev/reviews' \
  ':!docs/dev/diagnosis' ':!docs/dev/blast-radius' | grep -v "^scripts/wiki_relevance.py"
```

**Code importers of the module (3):**
- `scripts/wiki_freshness.py:47`, `:109`
- `hooks/wiki-freshness-reminder.sh:56-57`
- `tests/test_wiki_relevance_classification.py:20`

**Direct reads of `KNOWN_RELEVANT_TOP_LEVEL`:** only
`tests/test_wiki_relevance_classification.py:63`, `:115`.

**Everything else (prose and registry mentions):**
- `scripts/enforcement/blast_radius.py:23`, `:160` (docstring + the gated-surface registry
  row)
- `tests/test_blast_radius_classification.py:3`, `tests/test_ci_wait.py:16`,
  `tests/test_consumer_enumeration_gate.py:7` (docstrings)
- `.claude/workflows/n1-baseline.mjs:593`, `AGENTS.md:222`,
  `docs/dev/AGENT_HANDOFF_TEMPLATE.md:308`, `docs/dev/RELEASE_ARC.md:1705,2004`,
  `docs/dev/docs-ia-design.md:368,374,441`, work items 0035/0065/0098, `BOARD.md:159`,
  `CHANGELOG.md:813`, `docs/governance/enforcement.md:108`,
  `docs/dev/epic-a-chain-design-corrections.md`, `docs/dev/gate-window-class-study.md`
  (prose)

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py` (`KNOWN_RELEVANT_TOP_LEVEL`) | update | Add the one entry; the surface itself |
| 2 | `tests/test_wiki_relevance_classification.py:63,91,115` | no change | Reads the set. `:91` passes once the entry exists. `:115` (stale-entry check) passes because the file exists |
| 3 | `scripts/wiki_freshness.py:109` | no change | Calls `is_wiki_relevant()`; the return value for this path is unchanged (`True` before and after) |
| 4 | `hooks/wiki-freshness-reminder.sh:57` | no change | Same call, same unchanged return value |
| 5 | `scripts/enforcement/blast_radius.py:160` | no change | Registry row gating this file; describes why, not what the set contains |
| 6 | Prose mentions (Enumeration list above) | no change | None enumerates the set's members |

---

## Deferred

Nothing deferred.

---

## Verification

`python -m pytest tests/test_wiki_relevance_classification.py` must pass, covering both
directions: no unclassified entry, and no stale one. The full gate is then re-run. A missed
consumer would have to read set membership directly, and the grep above shows the audit test
is the only such reader.
