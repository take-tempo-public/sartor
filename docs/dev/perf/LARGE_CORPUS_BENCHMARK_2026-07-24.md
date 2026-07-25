# Large-corpus scalability — re-observation benchmark (2026-07-24)

> **Purpose:** the per-surface cost table carry-forward ledger item 10 asks for,
> measured before any optimization is designed.
> **Status:** Tier 1 (server-side) in progress. Tier 2 (browser render) not started.
> **Method + raw data:** `scripts/bench_corpus_scale.py`;
> results in `docs/dev/perf/data/large-corpus-curve.json`.
> **Authoritative for:** what the corpus surfaces actually cost at size. It does
> **not** set targets or thresholds — those are an [OWNER DECISION] the table
> exists to make decidable.

---

## O-1 — the real corpus is not large

Ledger item 10 was filed on one measurement: `#mergeSuggestionsList` rendering
**~25000px** at **20 near-identical seeded roles**. A read-only copy of the
owner's real corpus DB reports a very different shape:

| entity | rows |
|---|---|
| `experience` (roles) | **8** |
| `bullet` | 122 |
| `application` | 20 |
| `application_bullet` | 341 |
| `clarification` | 53 |
| `skill` | 34 |
| `merge_dismissal` | 4 |
| `experience_title` | 14 |
| schema revision | alembic `0014` (head is `0015`) |

**8 roles is 28 possible pairs.** The 20-seeded-role instrument maximized
near-duplicate pairs by construction, so it is very unlikely to describe the
owner's experience. The uncapped render remains a real *scaling* risk; it is not,
on this evidence, the owner's current pain.

Consequence for method: the curve scales **applications and bullets alongside
roles**, ratio-preserving, rather than scaling roles in isolation. Scaling roles
alone would reproduce the original instrument's bias and confirm its theory by
hiding rivals.

## O-2 — at the real corpus shape, merge-suggestions costs 647ms to return nothing

Tier 1, `1x` point (8 experiences / 122 bullets / 20 applications), `realistic`
profile, 3 timed repeats after a warm-up, Flask test client, no browser, no LLM:

| surface | route | median | min / max | SQL queries | response |
|---|---|---|---|---|---|
| corpus list | `GET /api/users/<u>/experiences` | 9.22 ms | 9.02 / 9.30 | 18 | 1 750 B |
| **merge suggestions** | `GET /api/users/<u>/corpus/merge-suggestions` | **647.49 ms** | 622.22 / 682.41 | 19 | **29 B** |
| applications | `GET /api/users/<u>/applications` | 6.10 ms | 5.09 / 7.01 | **3** | 6 606 B |
| Compose composition | `GET /api/applications/<id>/composition` | 21.17 ms | 20.26 / 22.46 | 12 | 35 926 B |

Two readings, both load-bearing:

- **Merge suggestions is ~70× the next-most-expensive surface and returns a
  29-byte empty result.** A 29-byte body is `{"suggestions": [], "count": 0}` —
  the entire 647 ms is CPU spent deciding there was nothing to show. This is not
  a large-corpus problem. It is already the dominant server cost at the owner's
  actual corpus size.
- **The `list_applications` N+1 fix is holding.** 3 queries for 20 applications,
  matching the documented 1+2N → ~3 collapse. No regression.

`corpus_list` at 18 queries for 8 experiences is a mild per-experience query
pattern worth a look, but at 9 ms it is not currently a cost problem.

## Inferred (unproven) — why merge-suggestions is expensive

**This is a hypothesis from reading the code, not an observation.** It predicts
the curve's shape; the curve is what will confirm or refute it.

`list_merge_suggestions` (`blueprints/corpus/curation.py:320-342`) walks every
experience pair — O(n²) — and calls `score_experiences` on each. That scorer
computes `bullet_overlap` **unconditionally** (`onboarding/experience_match.py:222`),
*before* the company gate can reject the pair. `bullet_overlap` and
`shared_bullet_count` both fall back to `difflib.SequenceMatcher` per bullet pair
(`experience_match.py:196-198`), so a single experience pair costs up to
O(b_a × b_b) fuzzy string comparisons over full-length bullet text.

Predicted total: **O(n² × b² × L²)** — quadratic in roles, quadratic in bullets
per role, quadratic in bullet text length. At the 1x point that is 28 pairs ×
~15×15 bullets ≈ 6 300 `SequenceMatcher` calls, which matches the observed
~100 µs per call.

If true, the wasted work is specifically the fuzzy bullet comparison performed on
pairs the company gate will discard anyway. **Not verified. No fix is designed on
this branch.**

---

## Curve (in progress)

Sizes anchored on the real shape and scaled ratio-preserving:

| point | experiences | bullets | applications | pairs |
|---|---|---|---|---|
| 1x | 8 | 122 | 20 | 28 |
| 3x | 24 | 366 | 60 | 276 |
| 6x | 48 | 732 | 120 | 1 128 |
| 12x | 96 | 1 464 | 240 | 4 560 |

A `duplicate` profile (near-identical companies/titles/dates) isolates the
pairwise SIMILAR band that actually renders cards, separately from the main
curve.

### O-3 — cost tracks the PAIR count, reaching 97 seconds at 96 roles

`realistic` profile. 1x/3x/6x at 3 repeats, 12x at 1 repeat; medians.

| surface | 1x (8) | 3x (24) | 6x (48) | 12x (96) |
|---|---|---|---|---|
| corpus list | 9.22 ms | 24.53 ms | 63.21 ms | 271.09 ms |
| **merge suggestions** | **647 ms** | **10 168 ms** | **41 952 ms** | **97 043 ms** |
| applications | 6.10 ms | 9.05 ms | 17.61 ms | 29.36 ms |
| Compose composition | 21.17 ms | 44.49 ms | 113.41 ms | 218.05 ms |

| surface | queries 1x | 3x | 6x | 12x | pattern |
|---|---|---|---|---|---|
| corpus list | 18 | 50 | 98 | 194 | **~2N+2 — N+1** |
| merge suggestions | 19 | 51 | 99 | 195 | ~2N+2 — N+1 |
| applications | **3** | **3** | **3** | **3** | flat ✓ |
| Compose composition | 12 | 12 | 13 | 14 | flat ✓ |

**Cost per pair is the stable quantity.** Pairs go 28 → 276 → 1 128 → 4 560.
Using the **minimum** (least CPU-contended) sample at each point, cost per pair
is roughly constant across a 163× range in pair count:

| point | pairs | min ms | **ms / pair** |
|---|---|---|---|
| 1x | 28 | 622 | 22.2 |
| 3x | 276 | 6 802 | 24.6 |
| 6x | 1 128 | 30 788 | 27.3 |
| 12x | 4 560 | 97 043 | 21.3 |

A roughly flat per-pair cost over a quadratically-growing pair count means total
cost is **O(n²) in experiences** — the Inferred prediction, now supported by
measurement rather than by reading alone.

**What this data does NOT pin down, stated plainly.** The medians are noisy:
6x ranged 30.8–42.9 s, a 39 % spread, and 3x ranged 6.8–10.4 s. On medians the
6x→12x step grows only 2.31× where pair count grows 4.04×, which taken alone
would suggest *sub*-quadratic. The per-pair table above reconciles that as
contention rather than a genuine exponent change — but with this spread, and a
single sample at 12x, **the exponent is bounded to "tracks pair count, within
measurement noise", not fixed to a precise power.** The headline result does not
depend on resolving it: the surface costs seconds at every size measured.

The 1x→3x jump (15.7× for 9.86× pair growth) is where the SIMILAR band starts
firing — 1x returns 29 B (zero suggestions) while 3x returns 4 456 B, and matched
pairs pay `shared_bullet_count` on top of the scoring already done.

**Honesty caveat on suggestion COUNT (not on timing).** The generator draws from
a 14-company pool, so at 24+ experiences companies repeat and genuinely similar
pairs appear. A real corpus with all-distinct employers would produce *fewer
suggestions* — but **not less work**, because `bullet_overlap` runs on every pair
before the company gate can reject it. The timing result is therefore
conservative for the realistic case; the suggestion counts are not.

**Extrapolation to 12x** (96 roles / 4 560 pairs) from the fitted quadratic:
~170 s. Being measured directly rather than asserted.

### O-4 — on the REAL corpus, merge suggestions takes 6.9 seconds to return nothing

The synthetic curve is calibrated to the real corpus's *shape*, but the pairwise
scorer runs `difflib` over bullet **text**, and `difflib` is quadratic in string
length. Measuring the real database directly (a copy, migrated `0014 → 0015` by
`init_db`; `scripts/bench_corpus_scale.py --db <copy> --username <user>`, 3
repeats):

| surface | median | min / max | queries | response |
|---|---|---|---|---|
| corpus list | 20.51 ms | 17.99 / 22.15 | 18 | 2 000 B |
| **merge suggestions** | **6 930.30 ms** | **4 700.91 / 9 127.19** | 19 | **29 B** |
| applications | 42.45 ms | 17.42 / 114.92 | 4 | 3 735 B |
| Compose composition | 95.32 ms | 77.09 / 109.23 | 38 | 44 757 B |

**This is the finding of the branch.** On the owner's genuine corpus — 8 roles,
87 active bullets, 20 applications — one `GET /corpus/merge-suggestions` costs
**~5 to 9 seconds of pure CPU** and returns `{"suggestions": [], "count": 0}`.
Nothing is rendered. Nothing is displayed. The entire cost is the decision that
there was nothing to show.

**Why it is 10.7× the shape-matched synthetic estimate (647 ms → 6 930 ms),
predicted before it was measured:**

| | synthetic 1x | real |
|---|---|---|
| active bullets | 120 | 87 |
| bullet-pair comparisons (Σ over pairs of bₐ×b_b) | 6 300 | 3 100 |
| mean bullet length | ~100 chars | **222 chars** (min 101, max 408) |

The real corpus has **half** the bullet-pair comparisons but each compares text
**2.2× longer**. Under `SequenceMatcher`'s O(L²), that is ~4.9× per comparison —
net ≈ 2.4× predicted, and the gap beyond that is the long tail of 408-char
bullets, since the quadratic punishes the longest strings hardest. **Bullet text
length, not corpus size, is the dominant term at the owner's scale.**

This reframes ledger item 10 completely: it was filed as a *large-corpus*
scalability risk, and the measurement says the surface is **already pathological
at a small, ordinary corpus**. Corpus growth makes an existing problem worse; it
did not create it.

**Secondary observation:** Compose composition issues **38 queries** on real data
versus 12 on the synthetic corpus of the same shape — real applications carry
`application_bullet` / clarification rows the synthetic seeder does not create.
At 95 ms this is not a live cost problem, but the query count scales with content
the synthetic curve understates, so the Tier 1 Compose numbers above are a
**floor**, not an estimate.

### What is *not* a problem

- **`applications` is clean** — flat 3 queries across an 12× range, 6 → 17.6 ms.
  The documented 1+2N → ~3 `selectinload` collapse is holding with no regression.
- **Compose composition** is flat on queries (12 → 13) and grows with payload
  size, not query count. 214 KB at 48 roles is worth watching for render cost
  (Tier 2), but the server side is not the bottleneck.

### The second finding — corpus list N+1

`corpus list` and `merge suggestions` both issue **~2N+2** queries (18 → 50 → 98
for 8 → 24 → 48 experiences): one titles query and one bullets query per
experience, lazily loaded. At current sizes the wall-clock impact is small
(9 → 63 ms), so this is a **latent** N+1, not a live cost problem — but it is the
same shape `list_applications` already fixed once with `selectinload`.

---

## Data handling

The owner's corpus copy was read **only** to establish the shape table in O-1.
It lives in gitignored scratch, is never staged, and no committed file references
its source location. All measurements are against synthetic corpora generated by
`scripts/bench_corpus_scale.py`, calibrated to the real shape at the 1x point.
