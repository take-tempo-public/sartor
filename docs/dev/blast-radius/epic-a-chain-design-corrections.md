# Blast radius: `docs/epic-a-chain-design-corrections` — classifying a new file in `scripts/wiki_relevance.py`

**Gated surface being edited:** `scripts/wiki_relevance.py` (registry entry: the single
source of truth for wiki-staleness relevance; consumed by the freshness gate and the
post-commit reminder, so a misclassification silently changes what counts as drift).

**Change:** add `docs/dev/epic-a-chain-design-corrections.md` to `IRRELEVANT_FILES` — this
branch created that file (a dev-process errata record, same character as the
already-irrelevant `docs/dev/diagnosis/` dossiers and the already-listed
`docs/dev/gate-window-class-study.md`) without classifying it, and
`tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`
correctly failed closed on CI (PR #115, run 31267919219 — all three of the py3.11 /
py3.12 / py3.13 quality jobs).

**This is a recurrence, not a first sighting.** `docs/dev/blast-radius/chain-gate-integration.md`
records the identical failure on PR #105 (run 31114143878): a chain-close pass created a
dev-process doc at `docs/dev/*.md` top level and did not classify it. Same guard, same
cause, same fix shape, nine days apart. See "Recurrence note" below.

## Consumers

Re-derived by grep on 2026-08-08 — **not** copied from the precedent dossier, per C-10
("treat any hand-maintained consumer list as stale until you re-derive it"). Queries run:
`from scripts.wiki_relevance|import wiki_relevance` across `*.py`; `is_wiki_relevant(|filter_relevant(`
across `*.py`/`*.sh`; `wiki_relevance` across `hooks/` and `.github/`. The re-derived set
matched the precedent's, which is a confirmation, not a reason to have skipped the check.

1. **`scripts/wiki_freshness.py:47`** — imports `is_wiki_relevant()`; used at `:109` for the
   drift count behind the merge-blocking 75-file threshold. **Measured, not reasoned:**
   drift is **20/75 before and after** this change. The classified-away file was one this
   branch created, and the branch's only other wiki-relevant path
   (`docs/dev/RELEASE_ARC.md`) was **already** in the drift set from earlier branches —
   verified by piping `git diff --name-only 65b0f88 HEAD` through `is_wiki_relevant()`.
   An earlier draft of this dossier asserted "22 → 21" from arithmetic; that was wrong in
   both terms and is corrected here rather than quietly restated. **Decision: intended;
   no behavior change beyond removing this one file from future counts.**
2. **`hooks/wiki-freshness-reminder.sh:57`** — calls the same classifier for the
   post-commit nudge. **Decision: same intended effect, no edit needed.**
3. **`tests/test_wiki_relevance_classification.py:20`** — the audit that fired. It enforces
   *classified*, not *irrelevant*, so it goes green once the entry exists in either
   direction. Its `:142-157` behavioral assertions pin other paths and are untouched by an
   additive data row. **Decision: satisfied by the edit; no test change needed.**
4. **`scripts/enforcement/blast_radius.py`** — names `wiki_relevance.py` as a gated surface;
   this dossier's own trigger. **Decision: no behavioral coupling, no edit.**
5. **`AGENTS.md:222` and `docs/dev/AGENT_HANDOFF_TEMPLATE.md:308`** — prose citing
   `is_wiki_relevant()` as the close-out check's classifier. **Decision: no edit — they
   cite the function, not any particular row.**

Negative results, recorded because C-10 counts them as findings:

- **No raw-string reference to `IRRELEVANT_FILES`** anywhere outside the module and its own
  test — no consumer reaches into the frozenset by name.
- **No `.yml` / workflow reference** to `wiki_relevance` — CI reaches it only transitively
  through `scripts/gate.py` → pytest.
- **No JS, Jinja, or CSS consumer** — the classifier is Python-only. (This is inside the
  computed audit's stated blind spot for non-Python consumers; checked by hand here.)

## Consequential correction to this branch's own wiki log entry

`docs/wiki/log.md`'s entry for this branch was written **before** this classification and
claimed **2 wiki-relevant paths** and **drift 22/75**. Measured truth: **1 path**
(`docs/dev/RELEASE_ARC.md`) and **drift 20/75, unchanged by this branch**. That entry is
corrected in the same commit rather than left standing — an uncorrected log entry is a
false provenance record, which is exactly what the log exists to prevent.

## Recurrence note (charter C-11)

The guard fired and failed closed both times, which is the mechanism working. What has now
recurred twice is an **author-side** gap: nothing tells you at authoring time that a new
`docs/dev/*.md` file needs a classification row — you find out from a red CI job minutes
after opening the PR.

**No new mechanism is authored on this branch,** and the reason is not "it didn't seem worth
it": a pre-commit check that classifies new `docs/dev/` entries would itself be a new gate
touching the same gated surface, and this branch is a documentation recovery whose gate is
currently red. Building it here would compound an unproven change onto an unfinished one.
**Filed as the C-11 obligation against item 55's neighbourhood and surfaced to the owner**
rather than left implicit.

## Deferred

None — one additive data row, every consumer decided above.
