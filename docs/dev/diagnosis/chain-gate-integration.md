# Diagnosis: `fix/chain-gate-integration` — unclassified new doc fails the wiki-relevance audit on CI

> Dossier opened at the chain-close stage of this branch, when PR #105's CI
> failed. The branch's original two fixes (F1 mode bit, F2 doc-links) have
> their evidence in the predecessor's dossier and handoff; this dossier covers
> the third, post-push defect only.

## Observed

1. **CI failure, PR #105:** required check `Lint, type-check, test (py3.13)`
   FAILURE — run `31114143878`, job `92659255622`, step "Quality gate". Job
   log (fetched via `gh api .../jobs/92659255622/logs`):

   ```
   FAILED tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified
   AssertionError: Unclassified top-level entr(y/ies) for wiki-relevance:
   ['docs/dev/gate-window-class-study.md']. Add each to one of
   scripts/wiki_relevance.py's IRRELEVANT_PREFIXES / IRRELEVANT_FILES /
   MIXED_PREFIXES / KNOWN_RELEVANT_TOP_LEVEL on purpose — never let it fall
   through unreviewed.
   1 failed, 2323 passed, 6 skipped in 44.99s
   gate: FAILED at `pytest -m "not ux" -n auto` (exit 1)
   ```

2. **Local reproduction, this tree (commit `f34967c`), 2026-08-06:**

   ```
   $ python -m pytest tests/test_wiki_relevance_classification.py -q
   E   assert not ['docs/dev/gate-window-class-study.md']
   FAILED tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified
   1 failed, 4 passed in 20.65s
   ```

3. **Provenance of the unclassified file:** `docs/dev/gate-window-class-study.md`
   was created by this branch's own chain-close commit `f34967c` — after the
   branch's full gate had already run (Case 4's gate ran at `247089c`; the two
   close-pass commits `f240042`/`f34967c` were checked only against a
   hand-picked structural subset that did not include
   `tests/test_wiki_relevance_classification.py`).

## Inferred

None needed for the fix — the audit's own assertion message names the
mechanism and the remedy. One inference worth recording for item 52: this is
a **seventh instance of the gate-window class the very file in question
documents** (post-gate artifacts never re-gated; the hand-picked re-check
subset had a coverage hole), observed while shipping the class study itself.
The class study's candidate mechanism 1 must therefore *derive* its check
subset rather than hand-pick it — recorded as an update in the study.

## Falsified

Nothing — first hypothesis (unclassified new top-level entry) confirmed by
the audit's own message and the local reproduction.

## The fix

Classify `docs/dev/gate-window-class-study.md` as `IRRELEVANT_FILES` in
`scripts/wiki_relevance.py` (dev-process record, same character as
`docs/dev/diagnosis/` — never cited by a wiki page). C-10 consumer
enumeration for the gated surface: `docs/dev/blast-radius/chain-gate-integration.md`.
Verification: the failing test flips green; full `pytest -m "not ux"` green on
the final committed tree (not a subset — the lesson this defect just taught).
