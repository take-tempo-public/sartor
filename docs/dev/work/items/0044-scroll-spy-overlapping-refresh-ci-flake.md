```toml
schema = 1
id = 44
kind = "item"
title = "CI flake: test_scroll_spy_attributes_overlapping_refresh_corpus_calls rerun-exhausted on a docs-only PR"
status = "open"
decision_owner = "agent"
refs = [
  "tests/ux/regression/test_20260708_busy_states_and_chip.py",
  "docs/dev/diagnosis/ux-scroll-spy-overlapping-refresh.md",
  "docs/dev/diagnosis/ux-scroll-position-flake.md",
  "https://github.com/take-tempo-public/sartor/actions/runs/30924821284/job/92044338685",
]
summary = "PROVEN harness defect: the clear was gated on refreshCorpus-exit, which precedes that invocation's own -fired. Fixed."
```

Observed 2026-08-04 on PR #98 (`chore/v11-march-kickoff`, a docs-only diff — zero
production JS/Python changes, so the branch cannot be the cause). The UX CI job
failed after exhausting all three attempts (fail-fail-fail — worse than the known
~42% single-rerun pattern) on
`test_scroll_spy_attributes_overlapping_refresh_corpus_calls`:
`assert len(fired) == 2` got 3 — a third `_restoreScrollY-fired` event with
`ordinal: 2, scheduledDuring: [2]` landing ~46ms AFTER the ordinal-3 event (full
event list preserved in the linked run log). The same local gate run on the same
tree passed the full UX tier (137 passed, only the known pre-existing
xfail/xpass pair in this same file).

This test is NOT one of epic 19's five closed children (27: mode-C residual, 28:
compose-reload restore, 29: restore-scroll-y stale invocation, 30: keyboard
reorder, 31: refinement retry) — a sixth candidate in the settle/restore family,
filed rather than diagnosed. One CI sample; watching until it recurs or a session
picks it up with the `ux-scroll-position-flake.md` rigor. Do not patch around it
in a march sprint — if it blocks a march PR again, that is the escalation signal
to schedule its own `fix/*` investigation.

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff (CI observation on this branch's own PR)

### 2026-08-04 — RECURRED on PR #99; escalation signal fired; status watching -> open

Second occurrence, on `feat/consumer-enumeration-gate` (PR #99, run
30943537217/job/92107687397). This is exactly the condition the original filing named
as the escalation trigger: *"if it blocks a march PR again, that is the escalation
signal to schedule its own `fix/*` investigation."* Status raised to `open`.

**Same signature as PR #98, confirmed by comparing the event lists rather than by
memory** — 3 `_restoreScrollY-fired` events instead of 2, and the extra one is an
`ordinal: 2, scheduledDuring: [2]` event landing *after* the `ordinal: 3` event:

```
t=470.9  ordinal 1  scheduledDuring [1]
t=518.8  ordinal 3  scheduledDuring [2, 3]
t=596.9  ordinal 2  scheduledDuring [2]     <-- late, out of order
assert 3 == 2
```

PR #98's instance had the same inversion with a ~46ms lag; this one is ~78ms.

**Rerun-exhausted again — all 3 attempts failed** (`2 rerun` + final `FAILED`; the job
log carries the explicit `needed a retry (2 of 3 attempts failed)` warning). Under C-7
that is a genuine failure signal, not a retry lottery. Two rerun-exhausted occurrences
in two consecutive PRs is hard to reconcile with the "~42% single-attempt" rate the
original filing assumed — if that rate held, three consecutive failures would be ~7%,
twice in a row ~0.5%. **Either the per-attempt rate is materially higher than believed,
or something changed.** That arithmetic is itself a finding and should be the
investigation's starting point rather than an assumption carried forward.

**Neither PR could plausibly be the cause.** #98 was docs-only. #99 touches no JS, no
CSS, no Jinja template, and nothing under `ui_pages/` — verified with
`git diff --name-only origin/main..HEAD` (26 files, none of those categories). Both PRs
also passed the same UX tier locally: #99's local gate ran `pytest -m ux` to
137 passed / 1 xfailed / 1 xpassed with **zero reruns**.

Still **not** patched around here, per the original filing's own instruction.

### 2026-08-04 — per-attempt rate measured across 4 CI runs: it fails on EVERY run

Checked every CI run on PR #99 for `RERUN` markers rather than trusting the
`gh pr checks` bucket. **The two runs reported as `pass` had each needed a retry** —
`gh pr checks` reports bucket=`pass` for a fail-then-pass, exactly the C-7 rule-3 masking
the charter warns about. Full record:

| Run | UX result | Attempts failed |
|---|---|---|
| PR #98 (30924821284) | FAIL | 3 of 3 |
| PR #99 run 2 (30943537217) | FAIL | 3 of 3 |
| PR #99 run 3 (30953100089) | reported `pass` | **1 of 3** |
| PR #99 run 4 (30955415008) | reported `pass` | **1 of 3** |

**This test has failed at least one attempt on every CI run for which we have data
(4/4).** The original filing's assumed ~42% per-attempt rate is not merely wrong, it is
optimistic — 8 failed attempts across 12 gives ~67%, and the two 3/3 exhaustions are
entirely unremarkable at that rate rather than the ~0.5% coincidence the previous update
computed. **Supersede that arithmetic; do not carry it forward.** The only thing keeping
this test nominally green is `--reruns 2`.

Two consequences for the investigation:

1. **Reproduction should be easy, not hard.** At ~67% per attempt this is not a rare
   race — a local loop should reproduce it within a handful of runs, with no CPU-saturation
   trick needed. If it does NOT reproduce locally at that rate, that difference is itself
   the finding (points at a CI-environment factor, not a code race).
2. **The repo's own rerun-rate alarm already fires** (`[ux] rerun-rate alarm: 1 test(s)
   needed a retry this run`) and was landing in the job log unread on every run. Whatever
   surfaces that alarm is not reaching a human or an agent. Worth folding into the
   deterministic-CI-wait work rather than treating as separate.

### 2026-08-04 — CORRECTION: the updates above name the wrong event as the anomaly

Filed from `fix/ux-scroll-spy-overlapping-refresh`. Full record:
`docs/dev/diagnosis/ux-scroll-spy-overlapping-refresh.md`.

**The two updates above are wrong on this specific point, and the error was propagated into
the outgoing handoff.** They describe the anomaly as *"the extra being an `ordinal: 2`
landing after `ordinal: 3`"*. Reading this filing's own recorded table again:

```
t=470.9  ordinal 1  scheduledDuring [1]
t=518.8  ordinal 3  scheduledDuring [2, 3]
t=596.9  ordinal 2  scheduledDuring [2]
```

- The spy's `_rcCounter` is a closure variable that the timeline clear does **not** reset,
  and the Corpus tab click's own fire-and-forget `refreshCorpus` consumes id 1. So the two
  invocations the test tracks are ids **2 and 3**.
- `assert len(enters) == 2` passes in every recorded failure — the failure is always the
  *next* assertion. So both tracked invocations are present and accounted for.
- The `t=596.9` row (`ordinal 2`, singleton `scheduledDuring [2]`) is exactly what the
  test's final assertion **requires**: `assert last_fired["scheduledDuring"] == [id_a]`.
  Invocation A is the one whose `/experiences` fetch is deliberately held open, so it
  *must* restore last. **That row is the designed behaviour, not the defect.**
- The genuine extra is `t=470.9` — `ordinal 1 / scheduledDuring [1]` — from the tab-click
  invocation, which the test is not tracking at all.

**Why it matters:** a session starting from the inherited framing would investigate
`_restoreScrollY`'s ordinal/scrollGen supersede guard (`static/app.js:5703`), which the
evidence shows is working correctly. That is a wrong and expensive starting point.

**Root cause (proven, reproduced deterministically).** A test-harness defect. The test
cleared the spy timeline after waiting for `refreshCorpus-exit`; the instrument's own
header has recorded since Chip 1a that `_restoreScrollY` is a fire-and-forget rAF which
`refreshCorpus` never awaits, so the invocation is marked closed *"a full microtask-drain
before the rAF actually fires."* The tab click's restore therefore lands in the
freshly-emptied timeline and is counted as a third event.

**Fixed** by gating the clear on that invocation's own `_restoreScrollY-fired` as well as
its `-exit`, in a shared `_settle_and_clear_spy_timeline()` helper. `assert len(fired) == 2`
is unchanged. No production code changed.

**Also measured here, worth carrying:** it does not reproduce locally at all (20/20 pass vs
CI's ~67% per attempt), so the rate lottery was not an available instrument; and headless
Chromium in this harness runs at **~11-13fps**, which makes a frame-count delay a
non-portable unit and gives the CI-cadence explanation room to be real.
