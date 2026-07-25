# merge-suggestions render cap — A/B (2026-07-25)

> **Purpose:** A/B `fix/merge-suggestions-render-cap` (carry-forward ledger
> item 11) against the committed O-6 baseline in
> [`LARGE_CORPUS_BENCHMARK_2026-07-24.md`](LARGE_CORPUS_BENCHMARK_2026-07-24.md).
> **Method:** `scripts/bench_corpus_scale.py --render`, same size/profile
> point as the baseline (6x / duplicate — the worst case O-6 measured).
> "Before" numbers are cited from that committed doc, not re-measured — the
> code they describe (pre-fix `refreshMergeSuggestions`) hasn't changed.
> **Diagnosis dossier:** `docs/dev/diagnosis/merge-suggestions-render-cap.md`.

---

## The fix

`blueprints/corpus/curation.py::list_merge_suggestions` now accepts
`limit`/`offset` (default page size 25, clamped to 1000) and returns
`total_count` + `has_more` alongside the existing paginated `suggestions`
list. `static/app.js::refreshMergeSuggestions` renders one page through the
existing per-card render path and appends a "Show N more" control instead of
appending every match in a single synchronous DOM pass — bounding DOM node
count and response payload size to the page size regardless of corpus size.
Item 10's fix (already landed, `fix/merge-suggestions-cost`) is unrelated to
this change: it made the per-pair *scoring* cheap; this caps the *render*.

## 6x duplicate-heavy profile — the O-6 worst case

| metric | before (O-6) | after | reduction |
|---|---|---|---|
| `#mergeSuggestionsList` height | 142,682 px | 3,277 px | **43.5x** |
| `#mergeSuggestionsList` children (cards) | 1,086 | 25 | **43.4x** |
| document height | 146,798 px | 7,438 px | **19.7x** |
| document nodes | — | 2,089 | — |
| settle time | 4,908 ms | 2,471 ms | 2.0x |

Document height drops less than the list's own height because
`#corpusExperienceList` (48 cards, 3,156px) is unaffected by this fix — it
was never the defect (per O-12). The remaining 7,438px is a normal,
navigable page instead of ~163x the viewport.

Settle time improves too, though this fix doesn't target it directly (item
10 already made the *server* fast at this point, 4.9s in O-6): the browser no
longer has to construct and lay out 1,086 cards before the page is
interactive, so the client-side settle window shrinks along with the DOM.

Raw data: `docs/dev/perf/data/merge-suggestions-render-cap.json`.

## What this does not change

- The suggestion computation itself (`onboarding.experience_match.score_experiences`,
  the sort order) is untouched — pagination slices the same sorted list,
  it does not change which pairs are SIMILAR or their ranking.
- Ledger item 2 (the still-open mode-C scroll-anchoring investigation): this
  branch does not attempt to fix it. The one existing regression test tied to
  it (`test_merge_suggestions_growth_shifts_scroll_deterministically`) was
  updated to pass an explicit unbounded `limit` override so its single-call,
  full-growth reproduction technique — and the coverage it provides for that
  unrelated open item — is unchanged by this fix. Whether capping the render
  by default also removes the flake's real-world driver remains a hypothesis,
  not tested here (per O-6's own framing).
- The "possible duplicate roles" UX itself (Merge / Keep separate actions,
  card contents) is unchanged — only how many render at once and the addition
  of a "Show more" control.

## Data handling

No real user data involved — this measurement uses
`scripts/bench_corpus_scale.py`'s synthetic seeded profiles only, same as the
O-6 baseline it's compared against.
