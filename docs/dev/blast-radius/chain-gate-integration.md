# Blast radius: `fix/chain-gate-integration` — classifying a new file in `scripts/wiki_relevance.py`

**Gated surface being edited:** `scripts/wiki_relevance.py` (registry entry:
the single source of truth for wiki-staleness relevance; consumed by the
freshness gate and the post-commit reminder, so a misclassification silently
changes what counts as drift).

**Change:** add `docs/dev/gate-window-class-study.md` to `IRRELEVANT_FILES` —
the chain-close pass created this file (a dev-process failure-class study,
same character as the already-irrelevant `docs/dev/diagnosis/` dossiers and
`docs/dev/flake-rates/` store) without classifying it, and
`tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`
correctly failed closed on CI (PR #105, run 31114143878, py3.13 job).

## Consumers

Derived by grep (`wiki_relevance` across `*.py` / `*.sh`, whole tree),
2026-08-06:

1. `scripts/wiki_freshness.py` — imports `is_wiki_relevant()` for
   `drift_count()`; adding an IRRELEVANT file *reduces* future drift counts by
   at most this one file. Behavior change: intended, none beyond that.
2. `hooks/wiki-freshness-reminder.sh` — calls into the same classification for
   the post-commit nudge; same intended effect.
3. `tests/test_wiki_relevance_classification.py` — the audit that fired; goes
   green once the entry is classified in either direction (it enforces
   *classified*, not *irrelevant*).
4. `scripts/enforcement/blast_radius.py` — names `wiki_relevance.py` as a
   gated surface (this dossier's own trigger); no behavioral coupling.
5. `tests/test_blast_radius_classification.py`, `tests/test_ci_wait.py`,
   `tests/test_consumer_enumeration_gate.py` — reference the module in
   fixtures/registry assertions only; unaffected by a data-row addition.

## Deferred

None — one additive data row, every consumer decided above.
