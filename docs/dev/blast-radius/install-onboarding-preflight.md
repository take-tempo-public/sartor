# Blast radius — install-onboarding-preflight

> **Branch:** `feat/install-onboarding-preflight`
> **Status:** enumeration complete (2026-09-22), written before the edit.

---

## Surface

`scripts/wiki_relevance.py` — `KNOWN_RELEVANT_TOP_LEVEL` (a frozenset of top-level repo
entries). The change **adds one member**, `"preflight.py"`, under "repo root — production
code". No function, signature, prefix list or other member changes.

Why: `preflight.py` is a new root module on this branch, and
`tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`
fails on any unclassified top-level entry. Observed: CI run `33904964073` (py3.11/3.12/3.13)
and the local gate log `scratchpad/gate-20260922.log` both fail with
`Unclassified top-level entr(y/ies) for wiki-relevance: ['preflight.py']`. It is production
code with its own wiki page (`docs/wiki/pages/machine-capability-preflight.md`), so
"relevant" is the correct class, the same class as every sibling root module (`app.py`,
`pdf_render.py`, …).

---

## Enumeration

Grep for `wiki_relevance`, `is_wiki_relevant`, `KNOWN_RELEVANT_TOP_LEVEL` across the repo
(excluding historical `docs/wiki/`, handoffs, diagnosis, ledger and reviews):

## Consumers

- **`scripts/wiki_relevance.py`** — the surface itself. One frozenset member added; no
  logic change.
- `scripts/wiki_freshness.py:47,109` — `drift_count()` counts changed paths where
  `is_wiki_relevant()` is true. **Effect:** a future change to `preflight.py` now counts
  toward wiki drift. Intended (the module has a wiki page). Before this change the
  path was unclassified, and the audit test refused that state, so there is no earlier
  behavior to preserve.
- `hooks/wiki-freshness-reminder.sh:56-57` — the same count feeds the post-commit nudge.
  The effect is the same as above and intended.
- `tests/test_wiki_relevance_classification.py` — the audit that this change makes pass.
  It is not edited.
- `.claude/workflows/n1-baseline.mjs:587`: prose only, a closer instruction to run the
  classification. It does not read the set. No change needed.
- `tests/test_ci_wait.py:15`: a docstring naming the module as a design precedent. No change needed.
- `scripts/enforcement/blast_radius.py`, `tests/test_blast_radius_classification.py` and
  `tests/test_consumer_enumeration_gate.py` name the file as a gated path. They do not
  depend on the set's members. No change needed.
- Docs that mention the module (`AGENTS.md`, `CHANGELOG.md`, `docs/governance/enforcement.md`,
  `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, `RELEASE_ARC.md`, items 35/65/98, older dossiers)
  describe the classifier generically. None lists the members. No change needed.

**Negative results:** the member set is not imported by name anywhere except its own module
and its audit test. No JS, template or CI-YAML consumer reads it.

## Deferred

None.
