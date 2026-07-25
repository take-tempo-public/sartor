# Diagnosis — GET /corpus/merge-suggestions costs seconds and returns nothing

> **Status:** root cause PROVEN — instrumented and falsification-tested this session.
> **Branch:** `fix/merge-suggestions-cost`

---

## Symptom

`GET /api/users/<u>/corpus/merge-suggestions` costs multi-second wall-clock
time on an ordinary corpus and, at the owner's real corpus size, returns an
empty `{"suggestions": [], "count": 0}`.

---

## Observed

Carried forward from `chore/large-corpus-re-observation` (merged `main` at
`f32eec6`), committed table:
`docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md` — median 6930.30 ms
(min/max 4700.91 / 9127.19) against the owner's real 8-experience / 87-active-
bullet corpus, response body 29 bytes. Synthetic `realistic` profile curve:
647 ms / 10.2 s / 42 s / 97 s at 8 / 24 / 48 / 96 experiences. That branch's
own honesty caveat: the fraction of pairs the company gate would reject was
not measured there.

This session measured that fraction directly, two ways:

1. Synthetic `realistic` profile (the exact company-assignment logic in
   `scripts/bench_corpus_scale.py`'s `_seed`, reproduced in
   `tests/test_experience_match.py::test_company_gate_rejects_most_pairs_on_realistic_profile`):
   at 8 experiences, 28/28 pairs (100%) score below `COMPANY_GATE` (0.6); at
   24 experiences, 266/276 (96.4%). This test is committed and passes on HEAD
   (it measures a fact about the corpus shape, not about the scorer's
   internal short-circuiting, so it is unaffected by whether the fix below
   has landed).
2. A read-only local copy of the owner's real corpus (untracked, gitignored
   scratch — same handling as the prior branch's O-1/O-4; no path or company
   name is recorded here): 22/28 pairs (78.6%) score below `COMPANY_GATE`.

Both measurements show a large majority of pairs are destined for `DISTINCT`
purely on company mismatch, before any bullet text is examined.

Reading `onboarding/experience_match.py:211-259`
(`score_experiences`), the company gate is checked only after `company`,
`title`, `dates`, and `bullets` (the `bullet_overlap` call, the expensive
O(b_a x b_b) `difflib.SequenceMatcher` term) have all already been computed
unconditionally. This is a direct code read, stated as an observation because
it is a reading of the actual dispatch order in the current source, not a
guess about what the code might do.

A regression test written to pin the desired behavior —
`tests/test_experience_match.py::test_score_experiences_short_circuits_below_company_gate`
— **fails on HEAD** with `TypeError: '>=' not supported between instances of
'MagicMock' and 'float'` at `onboarding/experience_match.py:244` (the `title
>= 0.6` check), because `_best_title_similarity`, `date_similarity`, and
`bullet_overlap` are all invoked even though the pair's `company_similarity`
is already below `COMPANY_GATE`. The mocked calls proved they run; the crash
is incidental (mocks aren't comparable to floats) but the invocation itself —
which the test asserts against via `assert_not_called()` — is the fact this
records.

---

## Falsified

Nothing falsified this session — the "gate first" direction filed by the
prior branch was the first hypothesis tested and it is confirmed by both
measurements above (large gate-rejection fraction on both real and synthetic
data), so the rival directions the handoff named (memoizing
`_normalized_bullets` per experience, capping the pairwise scan) were not
needed and were not attempted.

---

## Inferred

Cutting the unconditional `bullet_overlap`/`_best_title_similarity`/
`date_similarity` calls for company-gated pairs should reduce
`merge-suggestions` wall-clock roughly in proportion to the measured
rejection fraction (a rough expectation, not a proven bound — `bullet_overlap`
is the dominant cost per O-4/O-5 of the prior branch's table, but title/date
scoring also currently runs unconditionally and their removal contributes
some additional saving on top of the bullet-dominated total). This is a
prediction the A/B step below will confirm or correct against the committed
baseline numbers — record the actual delta, don't assume the fraction
predicts the wall-clock saving exactly.

---

## Falsification

**Experiment:** `tests/test_experience_match.py::test_score_experiences_short_circuits_below_company_gate`.

- **Fails on HEAD** (confirmed above): the hypothesis — that `score_experiences`
  computes title/date/bullet signals unconditionally, even for pairs the
  company gate would reject — is confirmed. Building the fix is warranted.
- **After the fix:** this test must pass (title/date/bullet scoring mocked
  and asserted never called for a below-gate pair), and all pre-existing
  tests in the file must continue to pass unchanged.

---

## The fix

`onboarding/experience_match.py::score_experiences` computes
`company_similarity` first; if it is below `COMPANY_GATE`, returns
`MatchScore(band="DISTINCT", ...)` immediately without calling
`_best_title_similarity`, `date_similarity`, or `bullet_overlap`. This
addresses the exact mechanism proven above: the unconditional computation of
signals whose result cannot change the verdict once the company gate has
already rejected the pair.

---

## Acceptance bar

- `tests/test_experience_match.py` fully green, including the new
  gate-rejection-fraction instrument and the short-circuit regression test —
  no reruns (a rerun masking a real flake is not evidence; N/A here since
  this suite has no browser/timing dependency).
- `python -m scripts.gate` green (ruff, ruff format, mypy, pytest), run in
  stages per the known wall-clock ceiling.
- A/B against `docs/dev/perf/LARGE_CORPUS_BENCHMARK_2026-07-24.md`'s
  committed numbers shows a large reduction on the `realistic` profile and
  the real-corpus figure, with the `duplicate` profile (few gate-rejected
  pairs) roughly unchanged — recorded in a new
  `docs/dev/perf/MERGE_SUGGESTIONS_FIX_2026-07-25.md` before this branch
  closes.
