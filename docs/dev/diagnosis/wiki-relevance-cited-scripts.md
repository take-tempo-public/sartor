# Diagnosis — `is_wiki_relevant()` treats wiki-cited `scripts/` files as irrelevant (item 153)

> **Status:** root cause PROVEN — the instrument test fails on `main` 542da4a and names every
> misclassified file. Why the hand list drifted is still only inferred (see `## Inferred`).
> **Branch:** `fix/wiki-relevance-cited-scripts`

---

## Symptom

On `fix/hook-guard-false-blocks` (2026-10-05) the branch changed `scripts/gate.py`. The
close-out wiki-relevance check did not flag it, though wiki pages cite that file. The stale
`code-module-map` row was found by grepping the wiki, not by the classifier
(`docs/dev/work/items/0153-wiki-relevance-misses-cited-scripts.md`).

---

## Observed

All on `main` 542da4a or this branch's instrument commit, 2026-10-06.

- **Instrument, failing on HEAD.**
  `python -m pytest tests/test_wiki_relevance_classification.py -p no:rerunfailures -q`
  gives `2 failed, 4 passed in 107.59s`. The failures:
  - `test_is_wiki_relevant_matches_known_shapes`, at the new assertion
    `is_wiki_relevant("scripts/gate.py") is True`: `AssertionError: assert False is True`.
  - `test_relevant_overrides_equal_wiki_cited_mixed_files`. Its re-run (`1 failed in 86.89s`,
    pytest exit 1) printed both directions:

    ```
    MISSING (cited by the wiki, but is_wiki_relevant() is False, so a change never counts as drift) - add each:
      scripts/build_vector_index.py            <- pages/machine-capability-preflight.md (dotted: `scripts.build_vector_index`)
      scripts/capture_screenshots.py           <- pages/code-module-map.md
      scripts/check_doc_frontmatter.py         <- pages/docs-information-architecture.md (bare name)
      scripts/check_doc_links.py               <- pages/docs-information-architecture.md (bare name)
      scripts/check_doc_single_home.py         <- pages/docs-information-architecture.md (bare name)
      scripts/check_docs_projection_fresh.py   <- pages/code-module-map.md
      scripts/check_docs_site_mermaid.py       <- pages/code-module-map.md
      scripts/ci_wait.py                       <- pages/code-module-map.md
      scripts/doc_corpus.py                    <- code-module-map, docs-information-architecture
      scripts/doc_lints.py                     <- code-module-map, docs-information-architecture, governance-extraction
      scripts/doc_registry.py                  <- code-module-map, docs-information-architecture
      scripts/docs_move.py                     <- docs-information-architecture
      scripts/enforcement/adapters/git_hook.py <- governance-extraction (bare name)
      scripts/enforcement/ci_backstop.py       <- consistency-tracks-enforcement (bare name)
      scripts/enforcement/guards/block_subagent_git_stash.py <- consistency-tracks-enforcement, governance-extraction
      scripts/gate.py                          <- code-module-map, consistency-tracks-enforcement, docs-information-architecture, engineering-workstreams, governance-extraction
      scripts/project_docs_to_mdx.py           <- code-module-map, docs-information-architecture
      scripts/release_version.py               <- code-module-map
      scripts/verify_doc_template.py           <- consistency-tracks-enforcement, eval-harness
      scripts/work_items.py                    <- code-module-map, consistency-tracks-enforcement
    STALE (listed, but no wiki page cites it) - drop each: ['scripts/export_corpus_seed.py', 'scripts/perf_baseline.py']
    ```

    That is 20 missing and 2 stale. The derivation found 23 cited mixed-prefix files, with no
    ambiguous cites (`cited=23 ambiguous={}`). The other 3 cited files were already overridden:
    `generate_openapi_spec.py`, `enforcement/guards/route_security_lint.py` and
    `docs/dev/perf/PERFORMANCE_HISTORY.md`.
- **The item's count was low.** It counted 13 distinct cited scripts by full path, of which
  9 were misclassified. Its grep (`scripts/[a-z_]+\.py`) stops at `/`, so it cannot match
  `scripts/enforcement/...`. It also misses bare-name and dotted cites. The derived figure is
  20 misclassified.
- **The two stale overrides were never cited.** `git log --oneline -S"perf_baseline" --
  docs/wiki/pages` and the same for `export_corpus_seed` both return nothing.
  `docs/dev/diagnosis/wiki-freshness-relevance-classification.md:113-116` listed both as files
  "a wiki page genuinely cites". (`docs/dev/perf/PERFORMANCE_HISTORY.md:177`, a wiki-cited
  file, mentions `perf_baseline.py`. The wiki pages themselves do not.)
- **The old test pinned the defect.** `tests/test_wiki_relevance_classification.py:147` (on
  `main`) asserted `is_wiki_relevant("scripts/gate.py") is False  # mixed, not overridden`.
- **Drift effect, measured with a read-only probe.** It ran `git diff --name-only <checkpoint>
  HEAD` through the classifier and its corrected form.
  - The checkpoint is `3798e2d1`; 104 files changed since then.
  - `drift_now=8`. One file is newly counted after the fix (`scripts/gate.py`); none are
    dropped. The result is 9, under the 75-file block (`scripts/wiki_freshness.py`
    `BLOCK_THRESHOLD`) and the 10-file reminder.
- **Cost of a runtime derivation (the rejected design).** A warm read plus regex of
  `docs/wiki/pages/*.md` measured 84.7, 103.1 and 201.5 ms over three runs. `python -X
  importtime -c "import scripts.wiki_relevance"` measured 7.4 ms self. Free RAM was about
  0.8 GB throughout.
- **Cost of the test-time derivation.**
  - It is one `git ls-files` (1265 tracked files), a read of 45 wiki files (408 KB), and
    about 838 regex tokens.
  - One run measured: ls-files 5238 ms, read 199 ms, regex 196 ms.
  - The whole helper took 1781 ms on another run.
  - The figures swing 2–3x run to run on this machine, so they bound the cost but do not
    characterize it. A regex lookbehind anchor tried as a speedup measured 99 ms then 330 ms
    against 155 ms then 114 ms for the original. That is no demonstrable win, so it was
    reverted.

- **After the fix (this branch).**
  - **Targeted suites, no reruns.** `python -m pytest tests/test_wiki_relevance_classification.py tests/test_wiki_freshness_gate.py tests/test_enforcement_core.py tests/test_blast_radius_classification.py tests/test_consumer_enumeration_gate.py -p no:rerunfailures -q`
    gives `198 passed in 781.46s`, pytest exit 0. Free RAM was about 0.5 GB, hence the 13 minutes.
  - **Spot check.** `is_wiki_relevant('scripts/gate.py'), is_wiki_relevant('scripts/perf_baseline.py')`
    gives `True False`.
  - **Drift.** `python -m scripts.wiki_freshness` gives `OK — 9 file(s) changed since the
    last ingest (< 75-file block threshold)`.
  - **Mutation check.** `RELEVANT_OVERRIDES` was swapped in-process and the test called
    directly. With the baseline it passes. Removing `scripts/gate.py` fails it on
    `MISSING … {'scripts/gate.py': …}`. Adding the uncited `scripts/perf_baseline.py` fails it
    on `STALE … ['scripts/perf_baseline.py']`.
- **Item 143 recurred, seventh instance.** The background-test notification re-armed the
  interrogative witness. Its PAUSE refused the Edit that added the bullet above, while the
  `git commit` batched in the same message ran. So commit `6238fe8` cites this evidence
  before the file held it. This follow-up commit adds the evidence.

---

## Falsified

- **"The overrides were accurate when written and only went stale as cites grew."** Two of
  the four were never cited by any wiki page (`git log -S`, above). The list was partly wrong
  from the start.
- **"Full-path grep finds every cite."** 5 cited files appear only by bare name (for example
  `check_doc_links.py`), and 1 only in dotted module form. A full-path-only instrument would
  have reported 14 misclassified, not 20.

---

## Inferred

*Unproven:* the list was written once, in the 2026-07 relevance-classification branch. Nothing
compared it with the wiki, so each `/wiki-self-update` that added a `scripts/` cite widened
the gap silently. That fits the timeline (the doc-tooling scripts are Epic D, after July) but
I have not walked each cite's introducing commit.

---

## Falsification

`test_relevant_overrides_equal_wiki_cited_mixed_files` derives the cited mixed-prefix set
from the wiki. It asserts set equality with `RELEVANT_OVERRIDES` in both directions.

- **Fails on HEAD (observed above):** the classifier disagrees with the wiki, so the defect is
  confirmed.
- **Had it passed on HEAD,** the item would have been wrong. It did not pass.

---

## The fix

`RELEVANT_OVERRIDES` becomes exactly the derived set: 20 added, 2 dropped. The list stays
explicit, by the owner's choice of 2026-10-06, so no wiki scan runs at classification time.
The test above is the mechanism that keeps the list equal to the wiki and fails closed.

---

## Acceptance bar

- Every node id in `tests/test_wiki_relevance_classification.py` passes with
  `-p no:rerunfailures`.
- Mutation check: removing one override fails the test with MISSING, and adding an uncited
  `scripts/` path fails it with STALE.
- `python -m scripts.wiki_freshness` reports 9 files of drift, OK.
