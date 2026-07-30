# Diagnosis — cross-item review: does one pattern span items 27/28/29 (the scroll-position flake family)?

> **Status:** hypothesis only. This is a review branch, not a fix branch — no production code
> changed here. The concrete finding: the "mode-C/D scroll-anchoring bleed-in" explanation
> `ux-restore-scroll-y-resource-contention.md`'s own `## Round 2` floated for item 29's
> `291`/`306` landing values is **falsified by dated git evidence**, not merely unconfirmed —
> the document-level anchoring fix (`27d349b`, merged `90e495d`, 2026-07-26) was already live in
> every tree these captures ran against. A different, untested explanation — a transient
> max-scroll **clamp** hit while the corpus tab is still mid-render — fits the numbers better and
> is laid out below as a hypothesis, not a proof.
> **Branch:** `fix/ux-scroll-flake-cross-item-review` (review only; base `main`)

<!-- Keep ## Observed (facts with artifacts) strictly apart from ## Inferred (hypothesis).
     Conflating them is the failure this document exists to prevent (charter C-7). -->

---

## Symptom

Three separate diagnosis dossiers have now been written, in three separate sessions, about
scroll-position bugs sharing the same `_captureScrollY`/`_restoreScrollY` primitive
(`app.js:5601-5630`) and/or the same seeded-corpus test fixture:

- `docs/dev/diagnosis/ux-scroll-position-flake.md` — the original dossier (modes A-D), fixed at
  the capture/restore layer (Chip 3, 2026-07-16); modes A/B/D closed there, mode C explicitly
  scoped out.
- `docs/dev/diagnosis/ux-scroll-wizard-rail-flake.md` — mode C's own dossier (item 27),
  root-caused to Chromium scroll anchoring on `refreshMergeSuggestions()`'s async growth, fixed
  round 7 via document-level `overflow-anchor: none` (O-19, 2026-07-26).
- `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` — item 29's own dossier (this
  branch's predecessor), still open, no proven mechanism.

Per the handoff that opened this branch: read all three together and look for a pattern that
explains gaps *across* items, before starting a fourth per-item round. This document is that
review's write-up, not a new bug report.

---

## Observed

### R-1. The document-level anchoring fix predates every capture this review re-examined

```
27d349b  2026-07-26  fix(scroll-flake): round 7 -- document-level overflow-anchor:none fixes mode C (O-19)
         merged via 90e495d (PR #72)
```

`git merge-base --is-ancestor 27d349b <commit>` is true for every commit that added the
captures below, confirmed directly (not inferred from dates in prose):

| capture | doc | commit that added it | date | is `27d349b` an ancestor? |
|---|---|---|---|---|
| O-12 (both occurrences) | `ux-scroll-position-flake.md` | `6bb7d47` | 2026-07-28 | **yes** |
| O-13 (`loadComposition`, item 28) | `ux-scroll-position-flake.md` | `6bb7d47` | 2026-07-28 | **yes** |
| O-14 | `ux-scroll-position-flake.md` | `23b916e` | 2026-07-29 | **yes** |
| this branch's full campaign (item 29) | `ux-restore-scroll-y-resource-contention.md` | (uncommitted, this session) | 2026-07-30 | **yes** (branched off `19d5532`, which contains `27d349b`) |

`static/style.css:122` (`html, body { overflow-anchor: none; }`) is present, unmodified, in the
current tree (`git blame` attributes the line to `27d349b` with no later edits).

Independently, item 27's own closure text (`docs/dev/work/items/0027-mode-c-scroll-residual.md`,
resolved 2026-07-30 — the **same day** as this branch's own campaign) re-verified the fix is
still effective **today**: 20/20 clean runs at the identical 6-loader/8-core calibration that
produced 6/20 (30%) failures on the unfixed control in round 7's own A/B.

**Conclusion, directly from the above:** no capture examined in this review — O-12, O-13, O-14,
or this branch's own — ran against a tree where document-level scroll anchoring was still live.
Whatever explains their landing values, it is **not** the `dy == dh` anchoring mechanism O-19
fixed; that mechanism was confirmed dead, on the same calibration, on the same day as this
branch's own campaign.

### R-2. A cross-item timeline of every captured `before`/`after` pair with a `window.innerHeight` of 900px

Built from the three dossiers' own `## Observed` sections. `maxScroll` is derived
(`scrollHeight - 900`, the viewport height every `tests/ux/conftest.py` context uses —
confirmed `tests/ux/conftest.py:205`, `viewport={"width": 1440, "height": 900}`), shown only
where the source entry logged `h` directly or a value is fully determined by it.

| # | source | date | pre/post anchoring-fix | test | call site | before → after | height (`h`) if logged | shape |
|---|---|---|---|---|---|---|---|---|
| 1 | doc1 O-8 | ~07-15 | pre | `test_corpus_reload...` | refreshCorpus | `300→0` (×2) | flat 1206 | stale-restore stomp (mode B) |
| 2 | doc1 O-9 | 07-16 | pre | same | refreshCorpus | `369→25423` | 2170→27224 | anchoring (mode D) |
| 3 | doc1 acceptance-bar campaign | 07-16 | pre | same | refreshCorpus | `300→369` (×4) | — | mode C (wizard residual, per that era's understanding) |
| 4 | doc2 O-6/O-9/O-18 | pre-07-26 | pre | same | refreshCorpus | `300→369`, `369→25423` | dy==dh confirmed both scales | mode C, mechanism proven (O-18) |
| 5 | doc2 O-19 control arm | 07-26 (pre-fix side of the same A/B) | pre | same | refreshCorpus | `300→369`(×2), `369→1368`, `416→485`, **`300→306`** | not logged per-run | mode C family, dy==dh |
| 6 | doc1 O-12 occ.1 | 07-28 | **post** | `test_restore_scroll_y_stale_invocation...` | refreshCorpus (forced) | `59→306` | not logged | unexplained |
| 7 | doc1 O-12 occ.2 | 07-28 | **post** | same | refreshCorpus (forced) | `59→0` | not logged | stale-restore-shaped |
| 8 | doc1 O-13 (item 28) | 07-28 | **post** | `test_compose_reload...` | **loadComposition** | `400→796` | not logged | unexplained, "well above baseline" |
| 9 | doc1 O-14 | 07-29 | **post** | `test_restore_scroll_y_stale_invocation...` | refreshCorpus (forced) | `59→306` (identical to #6) | not logged | unexplained |
| 10 | doc1 O-14 stash-A/B rerun | 07-29 | **post** | same | refreshCorpus (forced) | `59→273` | not logged | unexplained |
| 11 | this branch, `none` arm | 07-30 | **post** | same | refreshCorpus (forced) | `59→306` (identical to #6/#9) | not logged | unexplained |
| 12 | this branch, `-n2` vector RUN batch2-2 | 07-30 | **post** | same | refreshCorpus (forced) | `59→291` | not logged | unexplained |
| 13 | this branch, `-n2` vector RUN batch2-4 | 07-30 | **post** | same | refreshCorpus (forced) | `59→306` (identical to #6/#9/#11) | not logged | unexplained |
| 14 | this branch, round-2 instrumented | 07-30 | **post** | same | refreshCorpus (forced) | `before=0` (setup assert failed, no `after` reached) | spy attached, never fired (failed before the dump point) | new, 3rd shape |

**Landing-value cluster, exact:** `after=306` recurs **four times** (#5, #6, #9, #11/#13 — five
occurrences counting both `-n2` runs), across **two different tests** (`test_corpus_reload...`
and `test_restore_scroll_y_stale_invocation...`) and **two different starting baselines** (`300`
and `59`). Row #5 is the one **pre-fix** occurrence — its `306` is legitimately explained by
`dy == dh` anchoring (a `+6` shift from a `300`-height document, consistent with O-9's relation).
Rows #6/#9/#11/#13 are **post-fix** and cannot share that mechanism (R-1). Rows #8, #12, #14 are
each a single sample of a nearby-but-not-identical shape (`796`, `291`, `before=0`).

### R-3. The `59`/`306` pair matches known clamp values from elsewhere in the record, arithmetically

`maxScroll = scrollHeight - 900`. Working backward from the observed values:

- `before=59` → implied `scrollHeight = 959`. `h=959` is not a guess — it is the **exact**
  value doc1's O-9 spy dump logs at `refreshCorpus-enter`/`_captureScrollY`, immediately after
  the corpus tab is clicked and before any card attaches (`{'t': 2213, 'y': 0, 'h': 959, ...
  'source': 'refreshCorpus-enter'}`). It is the corpus tab's just-entered, nothing-rendered-yet
  height.
- `after=306` → implied `scrollHeight = 1206`. `h=1206` is likewise not a guess — it is the
  **exact, flat** height doc1's O-8 mode-B captures record throughout ("height FLAT at h=1206
  throughout... the run aborts... before the reload that would grow the page") and the exact
  page height of doc2's O-1/O-2 **isolated instrument**, which "never clicks the Corpus tab and
  so never grows the document" (doc2 O-8). `1206 - 900 = 306` is doc2's own O-4 clamp
  measurement, on a page height doc2 explicitly said would **not** generalize to the real
  (fully-grown, 27224px) corpus test — but item 29's forced-ordering construction never lets
  the page reach that fully-grown state; it holds the `/experiences` fetch open specifically to
  block `_renderCorpusList()` (doc1 O-10's own text: "the held-open fetch blocks
  `_renderCorpusList()` too, not just the restore"). A held-open-fetch test and O-4's
  never-clicked-corpus-tab instrument may be landing in the **same partially-rendered height
  band** for unrelated structural reasons — both never reach the 20-card/merge-suggestion
  growth that anchoring needed to matter.
- `after=291` → implied `scrollHeight = 1191`; `after=273` → implied `scrollHeight = 1173`. Both
  are close to, not identical to, 1206 — consistent with a height that is still **settling**
  (partial card/skeleton attachment) at the moment of read, landing at a slightly different
  point run to run, rather than one fixed constant.

**This is an inference, not a proof — see `## Inferred` for what it would take to confirm.**

---

## Falsified

### F-1 — "item 29's `291`/`306` landing values look like the already-documented mode-C/D
### scroll-anchoring shape bleeding into this test" (`ux-restore-scroll-y-resource-contention.md`, `## Round 2`)

**Falsified by R-1.** That inference was stated as a plausible-by-code-inspection read, correctly
labeled as inference at the time (not asserted as fact) — but it is inconsistent with dated git
evidence: the document-level anchoring fix that produces the `dy == dh` mode-C/D shape was merged
four days before the earliest of these captures (O-12, 2026-07-28) and re-verified effective, at
the identical calibration, on the **same day** as this branch's own campaign (item 27's closure,
2026-07-30). A mechanism that was off for the entire capture window cannot be the explanation.
This does not mean the two families are definitely unrelated in every sense (both ultimately
trace to the same corpus-render-timing sensitivity) — it means the *specific* mechanism named
(browser scroll anchoring) is ruled out for every post-fix capture. **Do not build on this
inference going forward; the corrective note has been added to that dossier's own Round 2
section, pointing here.**

---

## Inferred

**This is a hypothesis. It is not fact.**

Item 29's `291`/`306`/`273`/`796` family (and possibly item 28's `796`, though that call site
was not examined in the same depth — see below) may be explained by a **transient max-scroll
clamp**, not by any restore-ordering defect and not by scroll anchoring:

`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` deliberately holds the corpus
`/experiences` fetch open to force a specific invocation ordering — but this also means, for as
long as the fetch is held, the corpus tab's DOM stays in a **small, partially-rendered state**
(≈1206px, matching both O-8's flat mode-B height and doc2's isolated-instrument height, per R-3).
`window.scrollTo(0, y)` — both the test's own explicit call and `_restoreScrollY`'s internal
one — **clamps to `scrollHeight - viewportHeight`** at the moment it executes (doc2 O-4 already
established this clamping behavior is real, just scoped it to "the isolated instrument only").
If the corpus tab's DOM is still mid-attachment at the moment a clamped `scrollTo`/settle tick
fires — landing on whatever height the DOM happens to be at that instant — the result would be
exactly this family: a value **well above the near-zero "stale restore" target**, **well below
the fully-grown 25000px+ anchoring target**, clustering in a narrow band (~1170-1210px document
height → ~270-310px `scrollY`) that shifts slightly run to run with render-timing jitter, and
occasionally lands on the *exact same* value (`306`) when the DOM happens to hit the identical
milestone height (`1206`) more than once.

**What would need to be SEEN to actually know:** none of the existing `291`/`306`/`273` captures
logged `document.documentElement.scrollHeight` at the moment of the final read — the spy suite
that would have captured it (added in this branch's own Round 2) was wired into the test, but
the one failure that round caught was a different, earlier failure mode (`before=0`) that never
reached the dump. **The height data needed to confirm or refute this hypothesis does not exist
yet for any `after != before` capture in this whole family.**

**Item 28's O-13 (`loadComposition`, `before=400 after=796`) is a separate call site** — never
exercised by any of this branch's constructions — and was **not** independently checked against
this clamp hypothesis in this review. `796` does not fall in the same ~270-310 band as item 29's
captures, so if a shared mechanism exists it is not "the same clamp value," at most "the same
*class* of mechanism" (a transient height at read time) applied to a structurally different call
site (`loadComposition`, Tailor/Compose tab, not Corpus) with its own, unmeasured height
baseline. Treat this as an open question, not a confirmed link — the concrete next step (below)
covers both sites.

**Probe-effect question, reframed (not resolved) by this hypothesis:** `ux-restore-scroll-y-
resource-contention.md`'s Round 2 left open why the instrumented `-n2` re-run (1/16 failures)
landed a materially lower rate than the un-instrumented run of the identical vector (2/8). If the
underlying mechanism is "a read races a still-settling DOM," the spy suite's own added function-
call overhead on every wrapped call could plausibly shift *how far* the corpus tab has rendered
by the time each read fires — which could shift which failure mode a given run lands in (the
`before=0` shape that Round 2 actually caught is arguably *earlier* in the same render race,
not a separate mechanism) rather than suppressing a rate outright. This is offered as a
plausible reframing that would make three so-far-separate "unexplained" observations
(`291`/`306`, `before=0`, the rate discrepancy) instances of one race rather than three, **not**
as a resolution — it has the same evidentiary gap as the main hypothesis above: no height data
was captured at the moment of any of these reads.

---

## Item 30 / item 31 sanity check

Read both item files directly (`docs/dev/work/items/0030-...md`,
`0031-...md`). Neither mentions scroll, `_captureScrollY`/`_restoreScrollY`, `refreshCorpus`,
`loadComposition`, or document height anywhere in their text or `refs`. Item 30 is a Playwright
`wait_for_load_state` timeout in a keyboard drag-reorder test (`test_20260604_bullet_drag_reorder.py`);
item 31 is an assertion flake in a network-retry-error test
(`test_20260708_review_surface_and_flows.py`), unrelated code paths, no shared call site or
primitive. One coincidental overlap noted and dismissed as circumstantial: item 31's second
occurrence and doc1's O-14 both surfaced during the same `fix/eval-judge-parse-failure` gate
run — expected, since a full `pytest -m ux` run exercises every flaky test in the suite in one
pass; it is not evidence of a shared mechanism. **This still holds** — no new evidence surfaced
by this review changes their "unrelated" classification. Per the handoff's own scope note, no
deeper diagnosis was invested here.

---

## Falsification

**The experiment that would actually confirm or kill the clamp hypothesis.** Add
`documentElement.scrollHeight` (and, for completeness, `window.innerHeight`) to the value(s)
captured at the exact moment of the final `after` read in
`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` — not just on failure, since a
passing run's height at that instant is equally informative (a passing run should show
`scrollHeight` already at its fully-grown or intended value, not the ~1206 band). Re-run under
the confirmed `-n2`-within-suite vector (`capture_contention_n2.sh`, ~25% un-instrumented rate)
until an `after != before` failure (not the `before=0` shape) is caught with height data
attached.

- **If a captured `291`/`306`/`273`-shaped failure shows `scrollHeight` in the ~1170-1210 range
  at the moment of read:** the clamp hypothesis is confirmed for this call site. The right fix
  target becomes "why does `_restoreScrollY`'s settle loop or the test's own `scrollTo` fire
  while the corpus DOM is still mid-attachment" — a render-sequencing question, not a
  restore-ordering or anchoring one — and item 29's dossier should be corrected accordingly
  before any fix is attempted.
- **If `scrollHeight` at read time is NOT in that band (e.g., already fully grown, or some other
  value):** the clamp hypothesis is dead. Widen the instrument further rather than guessing
  again — per C-7, do not scope the next instrument to a third narrow theory without new
  evidence pointing at it.
- **Item 28's `loadComposition` call site** should get the same height-at-read instrumentation
  independently before assuming it shares whatever item 29 turns out to show — it is a
  structurally different call site and code path (per `## Inferred` above), and one sample
  (`796`) is not enough to extend a conclusion from one site to the other.

This experiment was **not run in this review** — this branch is scoped to the cross-item read
and whatever new, evidence-backed next step it produces, not to a new instrumentation campaign.
Whoever picks up item 29 next should run it before writing any new hypothesis, per this
dossier's own `## Round 2` lesson: the spy suite that was already wired in for a different
purpose came within one dump-point of catching this by accident.

---

## The fix

Not applicable — no mechanism proven. See `## Falsification` for the next step.

---

## Recommendation for what comes next

Per the handoff's own framing ("resuming item 29, starting item 28, or something the review
itself surfaces"): **resume item 29**, on a continuation of this branch or a fresh
`fix/*` branch off this one's findings, with the single falsification experiment above as the
first move — it directly supersedes item 29's own dossier's previous "instrument the rAF
callback's fire-time" plan, since a height-clamp race would not need rAF timing to explain it,
and is cheaper to test first (one more field logged in an already-working spy dump, no new
timing instrumentation). Item 28 stays open with its single sample; do not invest a dedicated
campaign there until item 29's experiment either confirms or kills the shared-mechanism
question. Items 30/31 remain correctly classified as unrelated and out of scope.
