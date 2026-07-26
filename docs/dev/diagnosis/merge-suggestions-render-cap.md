# Diagnosis — merge-suggestions panel renders every match with no cap

> **Status:** root cause PROVEN (measured on `chore/large-corpus-re-observation`,
> not this branch — this branch cites that evidence rather than
> re-instrumenting a defect that is already directly observed).
> **Branch:** `fix/merge-suggestions-render-cap`

---

## Symptom

The Career Corpus tab's "possible duplicate roles" panel
(`#mergeSuggestionsList`) can grow the page to many times the viewport height
on a duplicate-heavy corpus, with no pagination, cap, or virtualization. At
48 near-identical roles the panel alone is ~163× the viewport tall. This is
carry-forward ledger item 11 (`docs/dev/RELEASE_CHECKLIST.md`).

---

## Observed

`scripts/bench_corpus_scale.py --render` (headless Chromium, 1280×900,
synchronized on the merge-suggestions response + two animation frames — not
`networkidle`), from `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md` O-6:

```
| point | profile   | settle    | #mergeSuggestionsList | cards | DOM nodes | document height |
|-------|-----------|-----------|------------------------|-------|-----------|------------------|
| 1x    | realistic | 1 740 ms  | 0 px                   | 0     | 868       | 1 378 px         |
| 1x    | duplicate | 888 ms    | 3 671 px               | 28    | 1 092     | 5 147 px         |
| 6x    | realistic | 47 613 ms | 8 138 px               | 62    | 2 384     | 12 254 px        |
| 6x    | duplicate | 4 908 ms  | 142 682 px             | 1 086 | 10 576    | 146 798 px       |
```

At 6x duplicate: **1,086 cards / 142,682px** inside `#mergeSuggestionsList`,
producing a **146,798px document** (~163× the 900px viewport). The server
side is fast here (4.908s settle) — "the server was fast, the page is the
defect" (O-6). This rules out a backend/query cause: the cost is entirely
client-side DOM construction and layout.

Precursor measurement, `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md`
O-12 (round 5 step 0, a per-frame `documentElement.scrollHeight` watcher with
no pre-named suspect list, `_HEIGHT_ATTRIBUTION_JS`), at 20 seeded
near-identical companies:

```
height-change from=2170 to=27224 delta=+25054
  tall: [['tab-corpus', 27046], ['panelCorpus', 26958],
         ['mergeSuggestionsSection', 25044], ['mergeSuggestionsList', 24956],
         ['corpusExperienceList', 1308], ...]
```

`#corpusExperienceList` is 1,308px and never grows; the entire +25,054px
delta is `#mergeSuggestionsList` — confirming the growth is this one panel,
not the corpus card list, at a smaller scale (20 roles vs. O-6's 48).

Source of the render: `static/app.js:5212-5234` (`refreshMergeSuggestions`)
does `suggestions.forEach(s => listEl.appendChild(_renderMergeSuggestion(s)))`
in one synchronous pass over the full response; `blueprints/corpus/curation.py`
`list_merge_suggestions` (lines 282-346) returns every `SIMILAR`-band pair
with no `limit`/`offset`.

---

## Falsified

Not applicable — no fix has been attempted on this specific defect yet. (A
different branch's round-4 fix placed a scroll-anchoring workaround on
`.corpus-experience-list` on the unmeasured assumption that the corpus list
was what grew; O-12 above is the measurement that refuted that assumption
for the *scroll-flake* investigation. That is item 2's history, not this
item's — noted here only because it is what produced O-12.)

---

## Inferred

**Hypothesis, not yet tested by this branch:** capping this render may also
remove the driver behind the still-open mode-C scroll-anchoring flake
(ledger item 2), since that flake's reproduction depends on a large,
same-direction DOM insertion above the current scroll anchor — exactly what
`#mergeSuggestionsList`'s uncapped render produces. O-6 states this
explicitly as a hypothesis: "fixing the render cap would remove the flake's
driver... that is a hypothesis about the flake, not a result: no flake run
was performed on this branch." **This branch does not claim to fix item 2**
and will not close it. The existing regression test that guards item 2's
interim mitigation
(`tests/ux/regression/test_20260708_busy_states_and_chip.py::test_merge_suggestions_growth_shifts_scroll_deterministically`)
is preserved unchanged in behavior via an explicit unbounded `limit` override
at its two call sites, specifically so this branch's fix cannot silently
invalidate that coverage.

---

## Falsification

**Experiment:** a Playwright test that seeds enough near-duplicate
experiences to exceed the render cap (e.g. 8+ near-identical companies,
comfortably over the `MERGE_SUGGESTIONS_PAGE_SIZE` default), calls the real
`refreshMergeSuggestions()` once with no override, and asserts
`#mergeSuggestionsList`'s child element count stays at or below the page
size (e.g. ≤ `MERGE_SUGGESTIONS_PAGE_SIZE`), rather than one node per match.

- **If it fails on HEAD:** confirmed — HEAD renders every match with no cap,
  so child count scales with match count, not a fixed ceiling. Build the fix.
- **If it passes on HEAD:** the hypothesis is dead — something already caps
  this render. Stop, re-open the investigation.

This is the first commit on this branch, before any production edit.

---

## The fix

Server-side `limit`/`offset` pagination in `list_merge_suggestions`
(default page size, `total_count` + `has_more` added to the response) and
client-side incremental rendering in `refreshMergeSuggestions()` (renders one
page, appends a "Show more" control that fetches and appends the next page on
demand). Bounds both DOM node count and response payload size to the page
size regardless of corpus size, addressing the client-side render cost
directly (not a CSS `overflow`/`max-height` visual trick, which would still
construct every node).

---

## Acceptance bar

- The falsification test above passes (child count bounded regardless of
  match count).
- `scripts/bench_corpus_scale.py --size 6x --profile duplicate --render`
  re-run post-fix shows `#mergeSuggestionsList` DOM nodes/height bounded to
  one page's worth, independent of the 1,086-card worst case measured in
  O-6.
- The existing scroll-flake regression test
  (`test_merge_suggestions_growth_shifts_scroll_deterministically`) still
  passes, using its explicit unbounded-`limit` override — i.e. its coverage
  of item 2's interim mitigation is provably unchanged, not merely assumed.
- Full quality gate green (`ruff` + `mypy` + `pytest`), no reruns.
