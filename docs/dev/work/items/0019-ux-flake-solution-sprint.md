```toml
schema = 1
id = 19
kind = "epic"
title = "UX-suite flakiness solution sprint - mode-C residual + newly observed instances"
status = "open"
decision_owner = "agent"
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
]
summary = "Epic umbrella for 5 independent UX-suite flake candidates (items 27-31) - not one mechanism, see children."
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

### 2026-07-29 — promoted to epic, split into 5 children, per explicit owner direction

Owner confirmed (on `chore/ux-flake-epic-split`, handling the `fix/eval-judge-parse-failure`
handoff's recommendation) that this item's own "explicitly not one mechanism" framing above
should become 5 separately tracked children rather than one sprint branch: items 27-31, one per
candidate in the "Explicitly not one mechanism" list above (27 = candidate 1 / mode C's own
residual, 28 = candidate 2 / O-13, 29 = candidate 3 / O-12+O-14, 30 = candidate 4 / keyboard
reorder, 31 = candidate 5 / network-failure retry). This item's `kind` changed to `"epic"`;
`refs` trimmed to the diagnosis doc only since the per-test-file refs now live on the relevant
child. Per schema §4, this epic cannot close while any child is non-terminal — item 10's
existing `depends_on = [3, 6, 7, 9, 19]` therefore still gates the v1.1.0 cut correctly on all
five investigations closing, with no further edit needed there. Next step (not decided this
branch): which child to instrument first — a separate decision, deferred to whichever session
opens the first `fix/*` branch against one of these children.

### 2026-07-30 — child 27 closed as already-resolved (stale filing, not new work)

`fix/ux-mode-c-scroll-residual` found that candidate 1 (item 27) had already been root-caused
and fixed on a separate branch, `fix/ux-scroll-wizard-rail-flake` (merged `27d349b`/`90e495d`,
2026-07-26) — three days before this epic's own filing (2026-07-28) and four before the split
(2026-07-29). Neither filing cross-referenced that dossier. See item 27's own Updates for the
full evidence chain and live re-verification. Epic 19 stays open — items 28-31 remain
non-terminal — but the "oldest, best-understood" candidate closed with no code change, not by
being solved on this branch.

### 2026-07-30 — cross-item review (owner-directed pause on the per-item approach)

`fix/ux-scroll-flake-cross-item-review` read all three scroll-family diagnosis docs together
(the original, item 27's own, and item 29's own) rather than continuing item 29 in isolation.
Finding: item 29's dossier had inferred its `291`/`306` landing values might be the
already-fixed mode-C/D anchoring mechanism (item 27) bleeding into a different test — that
inference is **falsified by dated git evidence**, not merely unconfirmed: the anchoring fix
(`27d349b`, 2026-07-26) predates every capture it was applied to by 2-4 days, and was
independently re-verified effective on the same day (2026-07-30) as this branch's own campaign.
A different, untested hypothesis (a transient max-scroll clamp hit while the corpus DOM is
still mid-render) fits the observed values better and comes with a concrete next instrument.
Full detail: `docs/dev/diagnosis/ux-scroll-flake-cross-item-review.md`. No item closed; item 29
gets a corrected, sharper next step (see its own Updates); items 28/30/31 unchanged.

### 2026-07-30 — child item 29 closed (mechanism observed, two-phase fix landed)

`fix/ux-restore-scroll-y-resource-contention` round 3 closed item 29: the writer behind the
O-12/O-14 family was the user-select tail's stale smart-landing (tab flip + wizard smooth
scroll) plus that smooth animation surviving an explicit tab switch — geometry, not
restore-logic, end to end. Epic children remaining: 28 (has a concrete inherited first
check — see its Updates), 30, 31. The O-8 `#panel*` visibility-timeout load class recurred
once during this branch's gate (test_compose_skills_card_drop_persists, 2/2 clean isolated)
— logged as the known class, no new item.
