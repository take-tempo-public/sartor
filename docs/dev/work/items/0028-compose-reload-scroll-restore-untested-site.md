```toml
schema = 1
id = 28
kind = "item"
title = "O-13: loadComposition scroll-restore call site fails once, untested by O-10/O-11"
status = "closed"
resolution = "Not reproduced, owner-directed close 2026-07-31 (fix/ux-compose-reload-scroll-restore): instrumented the previously-bare test (geometry read + full scroll-spy stack, new dossier docs/dev/diagnosis/ux-compose-reload-scroll-restore.md), confirmed by code read that item 29's fix does not reach this call site (the writer it proved -- _wizardRender's unguarded smooth scrollIntoView -- is still live here), then ran a 24-iteration campaign under the confirmed -n2-within-suite vector: zero failures, item 28's own geometry read fully invariant across every run (sh=5391, cards=9, no jitter). Closed as not-reproduced-at-a-concerning-rate, not as proven-fixed or proven-absent -- both disclosed confounds (item 29's own spy-attached rate-drop; a low true rate cannot be distinguished from zero at n=24) are on record. Dossier + instrument remain as the citable record and reusable probe if O-13 recurs."
decision_owner = "agent"
epic = 19
refs = [
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "docs/dev/diagnosis/ux-compose-reload-scroll-restore.md",
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
]
summary = "O-13: test_compose_reload_preserves_scroll_position failed once at loadComposition, a call site O-10/O-11 don't cover."
```

Split out of epic 19 (`docs/dev/work/items/0019-ux-flake-solution-sprint.md`) 2026-07-29, per
explicit owner direction — candidate 2 of that epic's original 5.

`test_compose_reload_preserves_scroll_position` failed once (`before=400 after=796`) at the
`loadComposition` call site (`app.js:7036`) of the same `_captureScrollY`/`_restoreScrollY`
primitive the O-10/O-11 fix patches, during a believed-uncontended run — see
`docs/dev/diagnosis/ux-scroll-position-flake.md`'s O-13 entry. Neither O-10 nor O-11 exercises
this call site; both are written directly against `refreshCorpus`'s capture/restore only. One
sample is not enough to attribute this to the mode-C residual (item 27) or to anything else —
logged as a fact, not a conclusion, per that document's own discipline. No diagnosis dossier
exists yet.

## Updates

### 2026-07-29 — filed, split from epic 19

### 2026-07-30 — concrete first check inherited from item 29's resolution

Item 29's writer is now observed (`docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md`
Round 3): a stale user-select tail (`_activateTab` + `_wizardRender`'s smooth scrollIntoView).
First check for THIS item, when picked up: was the same select/landing-tail write in flight at
O-13's read moment, on the Tailor/Compose tab's own geometry? Not investigated — one sample,
different call site, per the cross-item review's scope rule.

### 2026-07-31 — instrumented, campaigned, closed as not-reproduced

`fix/ux-compose-reload-scroll-restore`. First commit instrumented the target test (it had zero
scroll-mutation visibility — two bare `window.scrollY` reads) with a new
`_READ_COMPOSE_SCROLL_STATE_JS` geometry read plus the existing scroll-spy stack, and opened a
new dossier `docs/dev/diagnosis/ux-compose-reload-scroll-restore.md`. Exploration found, by
direct code read (not inference), that item 29's fix structurally cannot reach this call site
(`_navGen` only gates `onUserSelect`'s tail; `switchTopTab`'s cancel never fires on the Compose
reload path; `{scroll:false}` never reaches `_wizardRender` from `wizardGoTo`/`_wizardAdvanceTo`)
— so the inherited first check above resolves to "no, not gated," and the smooth-scroll-survival
theory stays a live, untested hypothesis (dossier `## Inferred`).

Ran a 24-iteration campaign (`capture_contention_n2.sh`, the same 4 nodeids and vector as item
29's own campaign) in 6 foreground batches, no process incidents: **zero failures across all
24 runs**, item 28's own geometry read fully invariant every time (`sh=5391, cards=9`, before
and after, no jitter at all — unlike item 29's own bimodal passing-run heights). Owner reviewed
the 16-run result, directed extending to 24, then directed closing on that evidence. Closed as
not-reproduced-at-a-concerning-rate — not proven fixed, not proven absent; both confounds
(possible spy-attached suppression, a low true rate being indistinguishable from zero at n=24)
are disclosed in the dossier's `## Acceptance bar`, not resolved by it.
