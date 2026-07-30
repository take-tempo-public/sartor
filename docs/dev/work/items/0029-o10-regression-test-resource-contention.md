```toml
schema = 1
id = 29
kind = "item"
title = "O-12/O-14: the O-10 regression test itself fails under resource contention"
status = "open"
decision_owner = "agent"
epic = 19
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
]
summary = "O-10's own regression test fails 4x under contention (CPU load, -n2, cross-project procs); 5/5 in isolation."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 3 of that epic's original 5, and the one with the most
accumulated evidence (4 occurrences to date).

`test_restore_scroll_y_stale_invocation_overwrites_later_scroll` — the O-10 deterministic
reproduction that forces exact event ordering by construction, not CPU-load timing — has failed
four times under confirmed resource contention and passed cleanly in isolation every time it was
retried isolated:
- O-12, occurrence 1: deliberate `pytest tests/ux -n 2` parallelism (`before=59 after=306`).
- O-12, occurrence 2: unintentional overlap with a separate concurrently-running full-suite
  pytest invocation (`before=59 after=0`); both O-12 runs also found sharing the machine with two
  orphaned `python app.py` processes.
- O-14: next day, on an unrelated branch's (`fix/eval-judge-parse-failure`) plain serial
  `pytest -m ux` gate step — no deliberate `-n 2`, no orphaned same-project server this time, but
  genuine concurrent load from an unrelated project's (`spolia`) `python.exe` processes on the
  same machine. A stash-based A/B confirmed the failure rate is materially unchanged with that
  branch's entire diff removed from the tree (1 pass / 3 fail across 4 serial reruns on the clean
  base commit), ruling out interaction with that branch's own change.

See `docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-12 and O-14 entries for full detail. The
"resource contention" vector has now widened from "deliberate `-n 2`" to "any orphaned same-
project server OR genuine cross-project load" — needs its own busy-loop-style campaign using this
vector (per the diagnosis doc's own suggested next step) before concluding anything about
mechanism. No dedicated diagnosis dossier exists yet beyond the shared document's O-12/O-14
entries.

## Updates

### 2026-07-29 — filed, split from epic 19

### 2026-07-30 — dedicated resource-contention campaign run, inconclusive (`fix/ux-restore-scroll-y-resource-contention`)

Built a dedicated load harness (distinct from every prior CPU-busy-loop campaign) and ran the
target test 8x each under: no deliberate load (ambient only), a genuine concurrent unrelated
`pytest -m "not ux" -n auto` process, and an idle orphaned same-project `python app.py`
server. Full detail: `docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md`.

Result: 23/24 passed overall; the one failure (`before=59 after=306`, matching O-12's exact
landing value) occurred in the ambient-only arm, NOT either constructed contention arm — even
though both constructed arms independently confirmed real added load (test durations up to
~2.5-4x baseline). Neither tested vector clearly reproduces or amplifies the failure at n=8.

Not yet tested: O-12 occurrence 1's actual literal vector (`pytest tests/ux/regression/test_20260708_busy_states_and_chip.py -n 2`
— the SAME suite file under xdist, a second concurrent Playwright/werkzeug pair in-process —
qualitatively different from an external unrelated process or an idle server). Dossier
recommends instrumenting the `_restoreScrollY` rAF callback's fire-time directly as the next
step, independent of load vector, over further blind contention campaigns.

### 2026-07-30 (same day, cont'd) — `-n 2`-within-suite vector CONFIRMED elevated (owner-directed next step)

Ran the previously-untested vector: pytest-xdist `-n 2` on a 4-test subset of the same file
(target + 3 others exercising the same primitive), narrower than O-12 occurrence 1's full-tree
`-n 2` for cost reasons (disclosed in the dossier, not silently narrowed). 8 iterations:
**target test 6 passed / 2 failed (25%)** — the highest rate of any vector tested, versus 0/8
for both external-process vectors from the same session. Failures: `before=59 after=291` and
`before=59 after=306` (the second is byte-identical to O-12 occurrence 1's own logged value).
A secondary, already-known failure class (`#panelCorpus` load-timeout, O-8) also recurred 3/8
times on a different test in the subset — unrelated mechanism, not chased.

**This falsifies "generic resource contention" as the explanation** (the two heavier,
confirmed-real-load vectors produced zero target failures) and narrows it to something
specific about a second concurrent Playwright/werkzeug pair in the same process tree. Still no
PROVEN mechanism — the dossier's `## Falsification` section lays out the next step (instrument
the `_restoreScrollY` rAF callback's fire-time directly, now runnable against a ~25%-reliable
repro instead of blind) before any fix is attempted.

### 2026-07-30 (same day, cont'd) — instrumented re-run, caught a THIRD failure mode instead

Hand-traced `_restoreScrollY`'s actual current implementation (`static/app.js:5601-5630`)
before instrumenting: the generation-mismatch check has no fixed time budget, and this test's
own `scrollTo(0,300)` bumps the generation BEFORE the stale restore is even scheduled — so the
docstring's "races a fixed margin" framing doesn't hold up under direct code reading. Wired
the file's existing scroll-spy suite (previously used by sibling tests, not this one) into the
target test and re-ran the confirmed `-n 2` vector 16x (4 batches).

Result: 15 passed / 1 failed. The failure was NOT the `after != before` shape this dossier has
been chasing — it was the test's OWN setup assertion (`before > 0`) failing, `before=0`,
meaning the page hadn't grown its usual small scrollable amount by the time `scrollTo(0,300)`
ran. A new, real, unexplained failure mode, earlier in the sequence than everything examined
so far. Also unresolved: the instrumented failure rate (1/16) was well below the
un-instrumented rate for the identical vector (2/8) — possibly small-sample noise, possibly a
probe effect from the spy's own overhead. Full detail:
`docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md` `## Round 2`.

### 2026-07-30 (cont'd) — cross-item review corrects the mode-C/D bleed-in inference; new hypothesis + concrete next step

`fix/ux-scroll-flake-cross-item-review` (a deliberate pause on the per-item approach, reading
this dossier alongside the original and item 27's own) found Round 2's "looks more like the
already-documented mode-C/D scroll-anchoring shape... bleeding into this test" inference is
**falsified**: the document-level anchoring fix (`27d349b`, 2026-07-26) was already merged and
re-verified effective on 2026-07-30 (the same day this test's captures ran), 2-4 days before
every capture the inference was based on. That mechanism cannot explain `291`/`306`/`273`.

New hypothesis, evidence-linked but untested: `before=59`/`after=306` back-calculate
(`scrollHeight - 900`) to document heights `959` and `1206` — both exact matches to heights
already logged elsewhere in the record (the corpus tab's just-entered height, and the flat
height of doc1's mode-B captures / doc2's isolated instrument) — consistent with a transient
max-scroll **clamp** hit while this test's held-open-fetch construction keeps the corpus DOM in
a small, partially-rendered state, not a restore-ordering or anchoring defect. `291`/`273` are
close-but-not-identical, consistent with a still-settling height rather than one fixed value.

**Concrete next step (supersedes the previous "instrument the rAF callback" plan):** capture
`documentElement.scrollHeight` at the moment of the final `after` read (the spy suite already
wired in for Round 2 can carry this — it just needs the field), re-run the confirmed `-n2`
vector until an `after != before` failure lands with it attached. If `scrollHeight` is in the
~1170-1210 range at that moment, the clamp hypothesis is confirmed and the fix target becomes a
render-sequencing question, not restore-ordering or anchoring. Full detail, including the
full cross-item timeline table and item 28/30/31 cross-checks:
`docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`.
