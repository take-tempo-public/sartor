# Diagnosis — `loadComposition()`'s scroll-restore fails once, untested by any prior scroll-flake fix

> **Status:** NOT reproduced — closed on a 24-run campaign, not on a proven mechanism. The
> `## Inferred` hypothesis below was never confirmed OR definitively killed; it stays on record
> for a future occurrence, not built upon.
> **Branch:** `fix/ux-compose-reload-scroll-restore`

---

## Symptom

`test_compose_reload_preserves_scroll_position`
(`tests/ux/regression/test_20260708_busy_states_and_chip.py:527-555`) scrolls the Compose
panel to `y=400`, calls `loadComposition()` directly, waits for the settle marker plus a
fixed 100ms, then asserts `window.scrollY` is unchanged. It failed once, historically,
`before=400 after=796`, during a `python -m scripts.gate` run believed uncontended
(`docs/dev/diagnosis/ux-scroll-position-flake.md` O-13). Neither of the two prior scroll-flake
fixes (`ux-scroll-position-flake.md`'s Chip 3, `ux-restore-scroll-y-resource-contention.md`'s
item-29 two-phase fix) targets this call site or was validated against this test as its
subject.

---

## Observed

**O-13's own record** (`docs/dev/diagnosis/ux-scroll-position-flake.md:709-724`, quoted in
full): `test_compose_reload_preserves_scroll_position` failed once, `before=400 after=796`, at
the `loadComposition` call site of the same `_captureScrollY`/`_restoreScrollY` primitive item
29's dossier patches. At the time, no other heavy process was intentionally or (as far as
could be confirmed) unintentionally running concurrently. Neither O-10 nor O-11 (the tests
underlying item 29's fix) exercises this call site — both are written directly against
`refreshCorpus`'s capture/restore only. One sample; not attributed to any mechanism at the
time it was logged.

**The target test has zero instrumentation, confirmed by direct read**
(`tests/ux/regression/test_20260708_busy_states_and_chip.py:525-555`, quoted in full):

```python
@pytest.mark.ux
@pytest.mark.slow
def test_compose_reload_preserves_scroll_position(
    page: Page, live_server: str, ux_app: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepting/pinning a bullet re-enters `loadComposition()`, which clears
    + rebuilds #composeList — the owner's "scrolls to top" report. Seed enough
    experiences that the list is genuinely scrollable, scroll down, trigger a
    reload via the JS entry point itself (deterministic — no dependency on a
    specific card's on-screen position), and assert the position survives."""
    cid = seed_user(ux_app, "alice")
    for i in range(8):
        seed_exp_with_bullets(cid, company=f"Company {i}")
    install_llm_stubs(ux_app, monkeypatch)

    BasePage(page, live_server).load()
    UserPickerPage(page, live_server).select("alice")
    WizardJobPage(page, live_server).open().analyze(_JD)
    WizardComposePage(page, live_server).open()

    page.evaluate("() => window.scrollTo(0, 400)")
    before = page.evaluate("() => window.scrollY")
    assert before > 0, "test setup didn't actually scroll the page"

    page.evaluate("() => loadComposition()")
    page.wait_for_selector(Compose.SETTLED, state="attached", timeout=15_000)
    # _restoreScrollY runs on a requestAnimationFrame after the terminal
    # render — give the browser one frame to paint before reading it back.
    page.wait_for_timeout(100)
    after = page.evaluate("() => window.scrollY")
    assert after == before, f"scroll position not preserved: {before} -> {after}"
```

Bare `window.scrollY` reads at 546 and 554 — no `scrollHeight`, no `innerHeight`, no card
count, no scroll spy attached anywhere in the test, no `SCROLL_READ_LOG` write. A failure here
prints exactly two integers. Every sibling test in this file (the O-10/O-12/O-14 test and its
neighbors) has at least the geometry read; this one was never upgraded.

**`loadComposition`'s capture/restore, current line numbers** (`static/app.js`, the handoff's
`~7036` cite has drifted): declared at `7211`, capture at `7220`, terminal render at
`7348-7351`:

```js
7348	  // Terminal render reached — re-set the settle marker cleared at entry (above).
7349	  list.setAttribute('data-compose-ready', '1');
7350	  _restoreScrollY(_scrollY);
7351	}
```

`data-compose-ready` (the settle marker the test's `wait_for_selector` gates on) is set at
7349 — **one statement before** `_restoreScrollY` is even scheduled (7350). The test's 100ms
sleep is the entire budget for `_restoreScrollY`'s settle loop, which is specced for up to
`SCROLL_RESTORE_MAX_MS = 3000` / `SCROLL_RESTORE_STABLE_TICKS = 4` (`static/app.js:5625-5626`).

**Item 29's fix does not reach this call site — confirmed by direct read of every call site,
not inferred:**

- `_navGen` (`static/app.js:3582-3588`) is consumed only in `onUserSelect`
  (`static/app.js:416,437-451`) — it gates the post-select landing tail, not any Compose
  reload path.
- `switchTopTab`'s cancel (`static/app.js:3590-3612`, the raw
  `_scrollRestoreNative.scrollTo(window.scrollX, window.scrollY)` at line 3599) fires only
  inside `switchTopTab` itself. The complete caller set of `switchTopTab` is
  `templates/index.html:77,80,83,86,92,713` (inline `onclick`), `static/app.js:269,570`, and
  `_activateTab` (`static/app.js:2505-2509`, itself only called from `onUserSelect:440` and
  `goHome:517`). **Nothing in the Compose reload path calls `switchTopTab`.** Both of the
  test's own `switchTopTab` firings (via `UserPickerPage.select` and
  `WizardJobPage.open`'s tab click) complete before `window.scrollTo(0, 400)` at line 545 —
  before the measured window even opens.
- `{scroll:false}` (`static/app.js:7090-7096`) reaches `wizardInit`/`_wizardRender` only via
  `onUserSelect:451`. Both of the Compose-reload entry points that call `_wizardRender()` pass
  no opts and therefore keep the smooth-scroll behavior: `wizardGoTo(3)` →
  `_wizardRender()` (`static/app.js:7002`, itself calling `loadComposition()` at `7016`), and
  `_wizardAdvanceTo` → `_wizardRender()` (`static/app.js:7105`).

**The writer item 29 proved is therefore still live and ungated on this path** — the smooth
`scrollIntoView` call itself, `static/app.js:7093-7095`:

```js
  if (active && !(opts && opts.scroll === false)) {
    active.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
```

fires unconditionally whenever `_wizardRender()` is called with no opts, which is every call
in the Compose reload path.

**O-13's number fits the same arithmetic family item 29's Round 3 established**
(`docs/dev/diagnosis/ux-restore-scroll-y-resource-contention.md`'s R-3/R3-2:
`maxScroll = scrollHeight - innerHeight`, viewport `900` per `tests/ux/conftest.py:205`):
`after=796` implies `scrollHeight=1696` at the moment of read. This is an arithmetic
observation about the one existing number, not a proof of mechanism — no `scrollHeight` was
ever logged for O-13's capture (the test had no geometry read at the time), so it cannot be
distinguished from a different transient height.

**Stale comment cites found in the same test file, unrelated to this item's mechanism, noted
for close-out:** comments at `tests/ux/regression/test_20260708_busy_states_and_chip.py:126`
(`_restoreScrollY` cited as `app.js:5491-5493`, actually `5637-5657`), `:220` (`_wizardRender`
cited as `6974`, actually `7043`), `:665` (`wizardInit` cited as `6906`, actually `6969`),
`:1354` (the primitive cited as `5601-5630`, actually `5600-5657`).

---

## Falsified

_(Nothing yet — no experiment has been run on this branch.)_

---

## Inferred

**This is a hypothesis. It is not fact.**

The unguarded smooth `scrollIntoView` (`static/app.js:7093-7095`), fired by `_wizardRender()`
somewhere in the Compose-reload cascade, may be the writer that moved `y` from `400` to `796`
in O-13's single capture — the same *class* of mechanism item 29's R3-2/R3-3 proved for the
corpus-tab test (a smooth animation targeting a transient, not-yet-fully-grown geometry,
landing at that geometry's own clamped max-scroll). Item 29's R3-6 bench additionally
established that an **instant** `scrollTo` does not reliably abort an in-flight smooth scroll
in this Chromium — relevant here because `_restoreScrollY`'s own tick loop
(`static/app.js:5643-5655`) uses the raw instant `scrollTo`, so even a correctly-scheduled,
non-abandoned restore tick might not be able to stop an in-flight smooth animation if one
happens to be running concurrently.

**What would need to be SEEN to actually know:** whether `_wizardRender`'s `scrollIntoView`
(or any other write) is actually in flight at the moment of this test's `after` read, and what
`documentElement.scrollHeight` is at that instant. Neither exists for the historical O-13
sample — it predates any geometry or spy instrumentation on this test. The falsification
experiment below is designed to capture both, or to positively rule the theory out.

**Explicitly not assumed:** that this is the *same* mechanism as item 29's, merely the same
*class* (a call site this campaign has not yet exercised, on a structurally different tab and
render path). `ux-scroll-flake-cross-item-review.md`'s own scope rule (its `## Inferred`,
last paragraph) makes the same caveat for this exact item — one sample is not enough to
extend a conclusion from one call site to another.

---

## Falsification

**The experiment that settles it.** Instrument
`test_compose_reload_preserves_scroll_position` with the same class of probe item 29's Round 3
used for its own test — a single-evaluate geometry read (`y`, `scrollHeight`, `innerHeight`,
compose-card count) replacing both bare `window.scrollY` reads, plus the existing scroll-spy
stack (`_SCROLL_SPY_JS`, `_SCROLL_SPY_NAMED_HOOKS_JS`, `_WIZARD_RENDER_SPY_JS`,
`_HEIGHT_ATTRIBUTION_JS`) already defined in the same test file, dumped on failure via
`_dump_scroll_spy`, plus a `SCROLL_READ_LOG` line (durable under `-n2`, which swallows passing
stdout). Run under the confirmed `-n2`-within-suite vector
(`capture_contention_n2.sh`, the same 4 nodeids as item 29's campaign — this test is one of
them) for 16-24 iterations.

- **If a captured failure shows `_wizardRender`'s `scrollIntoView` (or another write) in the
  spy timeline between the `before` and `after` reads:** the smooth-scroll-survival hypothesis
  is confirmed for this call site. The fix target becomes gating `_wizardRender`'s scroll for
  the Compose-reload cascade specifically (mirroring item 29's `{scroll:false}` shape) — an
  owner-approved, user-visible behavior change, same bar as item 29's two fixes.
- **If a captured failure shows no such write, or shows a fully-grown `scrollHeight` at read
  time:** the hypothesis is dead. Widen the instrument rather than proposing a third theory
  from code inspection alone, per this project's C-7 discipline.
- **If no failure is captured across the full sample:** this is a data point, not closure —
  report it with two disclosed confounds: (1) item 29's own Round 2 observed an unexplained
  failure-rate drop with the spy attached, so a clean instrumented sample understates the
  bare failure rate; (2) the structural finding above (item 29's fix does not protect this
  path) means a clean run cannot be attributed to that fix. Take the close/extend decision to
  the owner.

### Campaign results (2026-07-30)

Shakedown (single isolation run, before the campaign): **PASSED**, `before_read={'y': 400,
'sh': 5391, 'ih': 900, 'cards': 9}` / `after_read=` identical — fully-grown geometry, not in
any clamp band. Confirms the probe itself does not perturb the test.

**Batch A (`capture_contention_n2.sh 4`, foreground, 2026-07-30): 4/4 clean, all four
nodeids.** Item 28's own reads, byte-identical across all 4 runs:
`before_read={'y': 400, 'sh': 5391, 'ih': 900, 'cards': 9}` /
`after_read={'y': 400, 'sh': 5391, 'ih': 900, 'cards': 9}`. Log:
`scratchpad/contention_n2_item28_batchA_20260730.log` (+ `.reads`), gitignored. Ambient state
at launch: the owner's e2e clone's werkzeug parent/child pair present (untouched, confirmed
via `Get-CimInstance Win32_Process` before starting); no other python/pytest/bash processes.

**Batches B, C, D (3 × 4 iterations, foreground, 2026-07-30): 12/12 clean, every one of the
16 total runs' all-four-nodeids pytest invocation reporting `4 passed` — zero failures
anywhere, target or neighbor, across the whole 16-run sample.** Item 28's own geometry stayed
byte-identical to batch A on every single run, all 16: `before_read={'y': 400, 'sh': 5391,
'ih': 900, 'cards': 9}` / `after_read=` the same. Logs:
`scratchpad/contention_n2_item28_batch{B,C,D}_20260730.log` (+ `.reads`), gitignored.
Process hygiene checked after every batch (`Get-CimInstance Win32_Process` filtered to this
project): clean teardown each time, no leaked bash/pytest trees. (One unrelated process tree
observed after batch A — a separate `C:\Dev\spolia` project's own `scripts/gate.py`/pytest
run, a different repository entirely, not touched.) No kills were needed this campaign — every
batch completed within the foreground call.

**Batches E, F (2 × 4 iterations, foreground, 2026-07-30, extending the sample per owner
direction): 8/8 clean, same `4 passed` shape, same byte-identical item-28 geometry as every
prior batch.** Logs: `scratchpad/contention_n2_item28_batch{E,F}_20260730.log` (+ `.reads`),
gitignored. Process hygiene clean after both batches.

**Final tally: 24/24 runs, zero failures anywhere (target or any of the 3 neighbors), across
6 foreground batches with no process incidents.** Item 28's own read is the identical
`{'y': 400, 'sh': 5391, 'ih': 900, 'cards': 9}` at both `before` and `after`, on every single
one of the 24 runs — no variance at all, not even the kind of run-to-run jitter item 29's own
campaign saw in its passing-run heights (bimodal `sh=2170`/`sh=5590`). That invariance is
itself informative: this call site's page is fully grown and geometrically stable by the time
`loadComposition()` fires in this construction, unlike item 29's corpus-tab test where the
`before` read routinely lands mid-render.

**Net:** 24/24 is a materially stronger sample than the historical n=1 (O-13) this item was
opened on. It is evidence that this call site does not reproduce under the confirmed vector at
a rate anywhere near item 29's pre-fix ~25% — **not** evidence that item 29's fix protects it
(the dossier's `## Observed` already established the fix cannot reach this path), and not
proof the underlying mechanism is absent (a rate this low, if real, would need a much larger
sample to distinguish from zero). The disclosed confounds stand: item 29's Round 2 spy-attached
rate-drop (possible suppression here too, unquantified) and the geometry invariance above
(this test's own construction may simply not create the transient-height window item 29's test
does). **Reported to the owner as a stronger data point; the close/extend decision remains
theirs.**

---

## The fix

**Not applicable — closed as not-reproduced, owner-directed (2026-07-31), not as fixed.**
This is a deliberately different closure shape from item 29's: no writer was ever caught in a
spy timeline, so nothing was gated or cancelled. The dossier and its instrument stay in place
as the citable record and reusable probe if O-13 recurs — the geometry-invariance finding
below is the concrete reason a future occurrence would be easy to re-investigate quickly (the
instrument already exists, and item 29's own writer/fix pattern is the first thing to check
again).

---

## Acceptance bar

**Closure bar met, stated plainly:** one historical sample (O-13, `before=400 after=796`,
no instrumentation) opened this item. A 24-run campaign under the confirmed `-n2`-within-suite
vector — the same vector that raised item 29's own target test's failure rate to 25% — produced
**zero** failures of any kind (target or neighbor) across all 24 runs, with item 28's own
geometry read completely invariant (`sh=5391, cards=9` at both `before` and `after`, every
single run — no jitter at all). That invariance, not just the zero-failure count, is the
substance of the bar: it means this call site's page is reliably fully-grown by the time
`loadComposition()` fires in this test's construction, unlike item 29's corpus-tab test where
the analogous read routinely lands mid-render. Two confounds are disclosed, not resolved, and
this closure does not claim to have resolved them: (1) item 29's own Round 2 saw an unexplained
failure-rate drop with the scroll spy attached, so a clean instrumented sample understates the
true bare-probe failure rate by an unquantified amount; (2) 24 clean runs cannot rule out a
much lower true rate than item 29's ~25% — it can only bound it well below that. This is closed
as "not reproduced at a materially concerning rate, on real evidence," not as "proven absent."
