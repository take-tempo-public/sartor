```toml
schema = 1
id = 19
kind = "item"
title = "UX-suite flakiness solution sprint - mode-C residual + newly observed instances"
status = "open"
decision_owner = "agent"
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
  "tests/ux/regression/test_20260604_bullet_drag_reorder.py",
  "tests/ux/regression/test_20260708_review_surface_and_flows.py",
]
summary = "Scheduled sprint: mode-C's own-flagged ~17% residual, plus 3 newly observed single-sample UX flakes from 2026-07-28."
```

Owner-directed 2026-07-28: "make sure you add any discoveries to the documentation of this
flake and schedule a solution sprint for it," after this session's gate-performance
investigation incidentally surfaced several UX-tier failures. Documentation landed in
`docs/dev/diagnosis/ux-scroll-position-flake.md` (O-12, O-13) for the two scroll-family
instances. This item is the scheduled follow-on to actually investigate and fix, not a
diagnosis in itself — none of what's below has been root-caused.

**Explicitly not one mechanism — do not conflate them.** This document's own existing
discipline (Observed/Inferred kept strictly separate, F-3's falsification of "all four modes
are one race") is the reason for treating each of these as a separate candidate until proven
otherwise:

1. **Mode C's own already-flagged residual** (`ux-scroll-position-flake.md`'s Acceptance bar
   section, ~17%/attempt, `_wizardRender`'s smooth-scroll racing a `refreshCorpus` baseline
   read) — explicitly scoped out of the original fix, explicitly flagged there as "worth a
   deliberate, separate pickup." The oldest, best-understood item in this sprint.
2. **O-13 (new):** `test_compose_reload_preserves_scroll_position` failed once
   (`before=400 after=796`) at the `loadComposition` call site (`app.js:7036`) of the *same*
   `_captureScrollY`/`_restoreScrollY` primitive — a call site neither of the existing fix's
   regression tests (O-10, O-11) exercises. One sample; plausibly mode-C-class recurring at an
   untested site, not proven.
3. **O-12 (new):** the O-10 regression test itself (`test_restore_scroll_y_stale_invocation_
   overwrites_later_scroll`) failed twice under confirmed resource contention (once under
   deliberate `-n 2` parallelism, once during an accidental process/CPU-contention overlap),
   then passed 5/5 in verified isolation. A new load-generation vector (real concurrent
   processes / a stray orphaned server) distinct from every existing campaign in that document
   (all pure CPU busy-loop). Needs its own busy-loop-style campaign using this vector before
   concluding anything about mechanism.
4. **New, unrelated to scroll:** `test_keyboard_reorder_persists_and_reset_reverts`
   (`tests/ux/regression/test_20260604_bullet_drag_reorder.py`) — one Playwright
   `wait_for_load_state` 30s timeout, single sample, believed-uncontended run. No diagnosis
   exists yet.
5. **New, unrelated to scroll:** `test_surgical_refinement_network_failure_surfaces_error_
   with_retry` (`tests/ux/regression/test_20260708_review_surface_and_flows.py`) — one
   assertion failure (`'error' not in status_text`), observed only under deliberate `-n 2`
   contention so far; not yet reproduced in isolation. No diagnosis exists yet.

**Context this sprint should start from:** this project's own CI data already shows ~42% of
real CI runs fire a rerun across "5 distinct settle/restore-family tests" (per
`RELEASE_ARC.md`'s scroll-flake-ci-data note) — none of today's 5 observations are evidence of
a NEW regression; they're samples of an already-known, already-partially-mitigated
(`--reruns 2` in CI) class that has never been fully closed out. The sprint's job is to narrow
"5 distinct tests flake sometimes" into named, individually falsified-or-confirmed mechanisms,
the same rigor `ux-scroll-position-flake.md` already modeled for the original bug.

**Suggested first step, not prescriptive:** this item may want to become an epic once scoped —
items 2-5 above are plausibly 3-4 independent investigations, not one. Do not pick a shape
before reading the existing diagnosis doc in full and deciding with the owner whether to split.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking, per explicit owner direction

### 2026-07-29 — new evidence on candidates #3 and #5, owner directs v1.1.0-blocking priority

During `fix/eval-judge-parse-failure` (an unrelated dashboard/eval fix)'s quality gate,
candidate #3 (`test_restore_scroll_y_stale_invocation_overwrites_later_scroll`) recurred a
fourth time, logged as O-14 in `docs/dev/diagnosis/ux-scroll-position-flake.md`. New this
time: a stash-based A/B confirmed it is unrelated to that branch's own diff (fails at the same
rate with the diff entirely absent), and the process check found no orphaned same-project
server (ruling out O-12's specific second-occurrence vector) but did find genuine concurrent
load from an unrelated project's python processes on the same machine — widening "resource
contention" to a cross-project vector, not just an orphaned sartor server or deliberate `-n 2`.

Candidate #5 (`test_surgical_refinement_network_failure_surfaces_error_with_retry`) also
recurred once, in the same gate run (not under deliberate `-n 2` this time — a plain serial
`pytest -m ux` run), and **passed cleanly on an immediate isolated rerun** — the first
isolation data point for this candidate (previously "not yet reproduced in isolation"); still
one sample, not a diagnosis.

**Owner direction (2026-07-29): this item must be solved before the v1.1.0 cut.** Item 10
(`chore/release-v1.1.0`) now lists `19` in `depends_on` to make this explicit and enforced by
the schema's sequencing semantics, rather than left as a same-priority parallel `open` item.
