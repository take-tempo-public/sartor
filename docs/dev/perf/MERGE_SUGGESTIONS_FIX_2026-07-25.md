# merge-suggestions gate-first fix — A/B (2026-07-25)

> **Purpose:** A/B `fix/merge-suggestions-cost` (carry-forward ledger item 10)
> against the committed baseline in
> [`LARGE_CORPUS_BENCHMARK_2026-07-24.md`](LARGE_CORPUS_BENCHMARK_2026-07-24.md).
> **Method:** `scripts/bench_corpus_scale.py`, same sizes/profiles as the
> baseline. "Before" numbers are cited from that committed doc, not
> re-measured — the code they describe hasn't changed.
> **Diagnosis dossier:** `docs/dev/diagnosis/merge-suggestions-cost.md`.

---

## The fix

`onboarding/experience_match.py::score_experiences` now computes
`company_similarity` first and returns `DISTINCT` immediately when it is
below `COMPANY_GATE`, skipping `_best_title_similarity`, `date_similarity`,
and `bullet_overlap` entirely for those pairs. This session measured (before
building the fix) that the company gate rejects 78.6% of the real corpus's
pairs and 94.5–100% of the synthetic `realistic` profile's pairs — see the
diagnosis dossier's `## Observed` for the measurement.

## realistic profile — synthetic curve

| size | before (median) | after (median) | reduction |
|---|---|---|---|
| 1x (8 exp) | 647.49 ms | 17.30 ms | **37.4x** |
| 3x (24 exp) | 10 168 ms | 488.04 ms | **20.8x** |
| 6x (48 exp) | 41 952 ms | 1 785.06 ms | **23.5x** |

Query counts and response sizes are unchanged from baseline at every point
(19 → 51 → 99 queries at 1x/3x/6x; 29 B / 4 456 B / 27 646 B) — the fix
changes what `score_experiences` computes, not which pairs end up `SIMILAR`,
so the suggestion set returned is identical. Only the CPU cost of getting
there dropped.

## duplicate profile — sanity check (should be roughly unchanged)

The `duplicate` profile's pairs are mostly same-company-family and so mostly
survive the gate under both old and new code — this is the negative control
confirming the fix targets the right pairs, not a blanket speedup.

| size | before (median) | after (median) |
|---|---|---|
| 1x (8 exp) | 54 ms | 49.33 ms |
| 6x (48 exp) | 1 605 ms | 1 298.89 ms |

Small improvement, not a regression, from the minority of duplicate-profile
pairs that are cross-family and now get skipped. Confirms the fix is not
silently changing duplicate-profile behavior.

## Real corpus

Measured against a throwaway working copy of the same read-only real-corpus
snapshot the baseline's O-4 measurement used (untracked, gitignored scratch;
no path or company name recorded here — same data-handling policy as the
baseline doc). The snapshot is dated 2026-07-24 and may not reflect the
current state of the owner's live corpus; it is used because it is the exact
snapshot the 6 930 ms baseline figure was measured against, making this an
apples-to-apples A/B against that committed number specifically, not a claim
about today's live corpus.

| surface | before (median) | after (median) | reduction |
|---|---|---|---|
| merge suggestions | 6 930.30 ms | 225.20 ms | **30.8x** |

Response body unchanged at 29 bytes (`{"suggestions": [], "count": 0}`) both
before and after — same result, returned in ~1/31st the time.

## What this does not change

- Ledger item 11 (uncapped client render at 142 682 px on duplicate-heavy
  corpora) is untouched, per the handoff's explicit instruction to keep it a
  separate row.
- The `corpus list` ~2N+2 N+1 noted alongside item 10 is untouched — latent,
  not urgent, same as the baseline doc found it.
- The suggestion set returned by `/corpus/merge-suggestions` is byte-for-byte
  identical to before at every measured point — this is a pure cost fix, not
  a behavior change.

## Data handling

The real-corpus figure above was measured against a throwaway copy of a
read-only snapshot of the owner's real corpus DB. Neither the snapshot nor
the working copy is staged or referenced by path in any committed file. Per
owner instruction, both are deleted as part of this branch's close-out sweep
once these results are confirmed reliable.
