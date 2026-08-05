```toml
schema = 1
id = 19
kind = "epic"
title = "UX-suite flakiness solution sprint - mode-C residual + newly observed instances"
status = "open"
resolution = "All 5 children closed 2026-07-31 (spanning 27-31): 27 already-fixed-before-filing (no code change); 28 not-reproduced (24-run campaign, owner-directed close); 29 mechanism observed + two-phase fix landed; 30 capability-proven mechanism + harness fix landed; 31 (last child) capability-proven mechanism + two-phase app+harness fix landed. Not one mechanism, as the original filing itself predicted -- five independent investigations, five different dispositions. Unblocks item 10's depends_on = [3, 6, 7, 9, 19] (still gated on 3/6/7/9)."
decision_owner = "agent"
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
]
summary = "Epic umbrella for 5 independent UX-suite flake candidates (items 27-31) - not one mechanism, see children. CLOSED."
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

### 2026-07-31 — child item 28 closed (not reproduced, 24-run campaign)

`fix/ux-compose-reload-scroll-restore` instrumented the previously-bare
`test_compose_reload_preserves_scroll_position` (geometry read + scroll-spy stack, new dossier
`docs/dev/diagnosis/ux-compose-reload-scroll-restore.md`), confirmed by direct code read that
item 29's fix does not reach this call site, then ran a 24-iteration campaign under the same
`-n2`-within-suite vector that elevated item 29's own target test to 25%: zero failures, fully
invariant geometry every run. Owner-directed close on that evidence — not proven fixed, not
proven absent; disclosed confounds on record in the dossier's `## Acceptance bar`. Epic
children remaining: 30, 31.

### 2026-07-31 (same day, cont'd) — child item 30 closed (capability-proven mechanism, fixed)

`fix/ux-keyboard-reorder-timeout` first found the item's own filing had drifted: the
`wait_for_load_state` specificity was an unsourced narrowing one document downstream of the
original record, which said only "a plain Playwright 30s timeout" — no traceback for the
failure exists anywhere in the repo. Wide instrument (all three `_wait_settled` sub-waits, full
network census) never caught a live recurrence in 7 baseline runs, but found one reach
consistently ~15-20x every sibling's cost on every run. Two pre-registered deterministic
capability probes: the Compose-cascade-retry candidate came back dead (a code-read correction —
its failure paths don't recurse, confirmed empirically); the live-preview-iframe candidate was
confirmed — a stalled iframe load reproduces the exact symptom, a genuine `networkidle`
`TimeoutError` at ~31s, at the exact flagged call site. An app-side alternative (cancel the
iframe nav on leaving Step 4) was investigated and rejected (no existing mechanism reaches
wizard-step transitions; would trade away a plausible pre-load benefit for no product-side win).
Fixed in the harness: `ui_pages/wizard_compose.py::_wait_settled` bounds the pre-drain wait to
5s instead of leaving it open to Playwright's 30s default; the real settle gate is unchanged.
Verified against the proven mechanism (not just the repro) and a full clean `pytest -m ux` run.
Not claimed as confirmed proof of item 30's one historical sample's cause — no artifact from
that sample survives to check — but the demonstrated vulnerability with the identical symptom
is closed. Dossier: `docs/dev/diagnosis/ux-keyboard-reorder-timeout.md`. Epic children
remaining: 31.

### 2026-07-31 (same day, cont'd) — child item 31 closed, epic 19 closed (last child)

`fix/ux-surgical-refinement-network-retry-flake` first corrected this epic's own filing: the
"-n 2 contention" attribution on item 31's first occurrence was an unsourced downstream
narrowing (added by this epic's own split filing, `6bb7d47`) — both surviving artifacts confirm
plain serial runs, the same drift shape item 30 found for `wait_for_load_state`. A direct code
read of `onUserSelect`/`setStatus` (`static/app.js`) produced a specific candidate mechanism —
a stale async tail's `setStatus('READY')` clobbering a more meaningful status set while it was
still in flight — and a deterministic `page.route()` capability probe confirmed it on the first
run, reproducing the exact historical pill text (`"ready"`) byte-for-byte; a reverse control
confirmed the race is necessary, not just sufficient. Two-phase fix (owner-approved, same
pattern item 29 used): an app-side `_statusGen` generation guard (mirrors item 29's own
`_navGen`) plus a harness settle contract (`UserPicker.SELECT_READY`, mirrors `data-compose-ready`)
so `UserPickerPage.select()` waits for the real cascade instead of just the `<select>` value.
One collateral regression (item 29's own `test_smart_landing_tail_defers_to_user_navigation`,
which relied on the old narrow contract to hold part of the cascade open on purpose) found and
fixed. Full `pytest -m ux` clean (136 passed, 2 xfailed, zero reruns); full gate green. Dossier:
`docs/dev/diagnosis/ux-surgical-refinement-network-retry-flake.md`.

**Epic 19 closes here — item 31 was the last open child.** Final disposition across all five:
27 already-fixed-before-filing (no code change); 28 not-reproduced (owner-directed close); 29
mechanism observed, two-phase fix; 30 capability-proven mechanism, harness fix; 31
capability-proven mechanism, two-phase app+harness fix. The epic's own original framing —
"explicitly not one mechanism, do not conflate them" — held throughout: five independent
investigations, five different dispositions, zero shared root cause. Unblocks one of item 10's
five `depends_on` entries (still gated on 3, 6, 7, 9).

### 2026-08-05 — REOPENED (child 30 recurred in CI)

Status `closed` → `open`. Child **30** recurred in CI on PR #102 five days after its
closure, with a captured instrument artifact showing a 30s timeout while every quiescence
signal read ready — a mechanism the 2026-07-31 fix does not cover. See item 30's
2026-08-05 update for the raw evidence.

The `resolution` line above is left unedited as the record of what was believed on
2026-07-31. Reading it now, the disposition mix is itself the finding: of five children,
**27** was already fixed before it was filed, **28** was closed as *not reproduced* (not
proven fixed), and **30** was closed on a fix for *a* vulnerability with a matching symptom
that its own text admitted was "not confirmed as the historical cause." Only **29** and
**31** were closed on an observed-and-reproduced mechanism.

So three of five closures rested on something weaker than "we saw this fail, we fixed that,
it stopped failing" — and the one that came back is one of the three. That is a
**systematic** weakness in the closure bar, not bad luck on a single item.

**Consequence for item 10** (`depends_on = [3, 6, 7, 9, 19]`): the v1.1.0 release chain is
gated on 19 again. This is not a scheduling technicality — it is the correct signal, and it
should not be routed around by re-closing 19 without evidence.
