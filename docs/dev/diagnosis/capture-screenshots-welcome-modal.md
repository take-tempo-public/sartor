# Diagnosis — `capture_screenshots.py` fails on a fresh Playwright context

> **Status:** root cause PROVEN
> **Branch:** `fix/capture-screenshots-welcome-modal`

---

## Symptom

`python -m scripts.capture_screenshots --headless`, run on unmodified
`main`, fails during step 2 ("Capturing S02 — user picker section") with
a `Playwright.TimeoutError` clicking the `#btnNewUser` ("New user")
button — never reaches any later capture step, never makes an LLM call.

---

## Observed

Full traceback from the actual run (`python -m scripts.capture_screenshots
--headless`, this session, on clean `main` before any edits):

```
playwright._impl._errors.TimeoutError: Page.click: Timeout 15000ms exceeded.
Call log:
  - waiting for locator("text=New user")
    - locator resolved to <button id="btnNewUser" class="cb-btn cb-bg-amber" onclick="showNewUserForm()">New user</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div data-help-dismiss="" class="cb-modal-backdrop"></div> from <div role="dialog" id="helpModal" class="cb-modal" aria-modal="true" ...>…</div> subtree intercepts pointer events
    - retrying click action
      [... repeats with increasing backoff until 15s timeout ...]
```

Independently, minutes earlier in the same session, an unrelated ad hoc
Playwright probe script (`scratchpad/probe_computed_styles.py`, written
to check computed CSS values on the live app — nothing to do with the
capture script) hit the *exact same* intercept signature on a plain
`page.hover()` call against `.top-tab-btn`:

```
playwright._impl._errors.TimeoutError: ElementHandle.hover: Timeout 30000ms exceeded.
...
      - <div data-help-dismiss="" class="cb-modal-backdrop"></div> from <div role="dialog" id="helpModal" ...>…</div> subtree intercepts pointer events
```

Two independent scripts, two independent Playwright browser launches
(each a fresh, empty-localStorage context), same failure signature. The
probe script's failure was worked around with `page.keyboard.press("Escape")`
before interacting — after which the intercept did not recur in that
session.

`grep -n "helpModal\|help-modal\|dismiss" scripts/capture_screenshots.py`
returns zero matches — the capture script contains no code path that
waits for, dismisses, or otherwise accounts for `#helpModal` at any point.

`grep -n "First-view auto-open" static/app.js` confirms the mechanism
exists in-app: `static/app.js:2313` — "First-view auto-open: the welcome
block opens once-ever (localStorage gate)." — a documented, intentional
feature of `_HELP_REGISTRY` (`static/app.js:2078` onward).

`git log -1 --format=%cd -- docs/screenshots` / the manifest images
themselves are dated 2026-05-28 — the last successful capture run
predates today by ~7 weeks, consistent with (not proof of) this having
broken sometime after that and never been re-run since.

---

## Falsified

_(Nothing yet — first pass on this branch.)_

---

## Inferred

The welcome help-modal auto-opens once-ever, gated on a `localStorage`
flag (`static/app.js:2313-2317`). A brand-new Playwright browser context
— which is what both `capture_screenshots.py` and any other automation
script get by default — always starts with empty `localStorage`, so the
auto-open condition is met on literally every fresh-context page load,
not intermittently. This predicts the failure is **deterministic**, not
a flake — testable below before touching any code.

---

## Falsification

**Experiment:** launch a fresh, isolated Playwright context (no
persistent profile, matching how `capture_screenshots.py` launches),
navigate to `/`, and check whether `#helpModal` is visible with zero
prior interaction. Cheap, fast, no LLM cost, no dependency on the full
capture flow.

- **If `#helpModal` is visible on a fresh context, unconditionally:** the
  hypothesis is confirmed — the fix is to dismiss it before the script's
  first interactive click, not a flaky retry or an unrelated cause.
- **If it is NOT visible:** hypothesis is dead — something else caused
  the two observed failures (investigate `--keep-user` state or a race
  instead) — do not patch based on an unconfirmed guess.

Result (this session, run immediately before writing "The fix" below):

```
$ PYTHONIOENCODING=utf-8 python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()  # fresh context, empty localStorage, same as capture_screenshots.py
    pg.goto('http://127.0.0.1:5000/', wait_until='networkidle')
    modal = pg.query_selector('#helpModal')
    print('helpModal present:', modal is not None)
    print('helpModal visible:', modal.is_visible() if modal else None)
    b.close()
"
helpModal present: True
helpModal visible: True
```

Confirmed on a genuinely fresh context, zero prior interaction: **the
modal is visible immediately, unconditionally.** Hypothesis confirmed —
proceeding to the fix.

---

## The fix

**Revised from the original sketch above** (a single post-`goto` Escape
dismiss) after the narrower fix was implemented and immediately hit the
*same* intercept signature again later in the run — at the Tailor-tab
click during Step 1. Investigating showed the welcome modal is only one
of 17 `cb_help_seen:<block>`-gated auto-firing help blocks:
`static/app.js`'s "KW3 first-run tour" (`_maybeFireTourStop`) fires a
different once-ever modal at each onboarding milestone (add-user, corpus
landing, each wizard step, first Generate, first cover letter, plus
`/_dashboard`'s per-tab explainers). Because this script always creates a
brand-new demo user, it satisfies every "new user" arming condition
throughout its whole walkthrough — reactively dismissing one intercept at
a time doesn't scale to an indeterminate number of future stops.

`tests/ux/conftest.py`'s `_help_welcome_default_seen` autouse fixture
already solves exactly this problem for the UX suite: a
`page.add_init_script(...)` that seeds all 17 `cb_help_seen:<block>`
localStorage keys *before* any navigation, so no auto-modal ever fires.
Extracted that block list + its seeding-JS builder into
`ui_pages/selectors.py::Help` (`TOUR_STOP_BLOCKS`,
`suppress_tour_init_script()`) — already the documented shared registry
for both the test suite and this script — so both consumers share one
definition instead of `capture_screenshots.py` growing its own
independent copy. `conftest.py` now imports from there too (pure
extraction, behavior unchanged, verified via a full `pytest -m ux` run).
`capture_screenshots.py` calls
`page.add_init_script(S.Help.suppress_tour_init_script())` once, right
after `page = ctx.new_page()`, before any navigation — unconditionally
seeding all 17 blocks, since this script never wants any tour stop.

---

## Second, independent defect found while verifying the fix above

After the welcome-modal/tour-stop fix above, a full end-to-end run of
`python -m scripts.capture_screenshots --headless` got much further —
past the user picker, demo-user creation, a real corpus-import LLM call,
and a real Analyze (Sonnet) call, with zero modal intercepts anywhere —
then failed with a *different* signature at Step 2 (Clarify):

```
playwright._impl._errors.TimeoutError: Page.click: Timeout 15000ms exceeded.
Call log:
  - waiting for locator("#btnClarify")
    - locator resolved to <button disabled id="btnClarify" onclick="runClarify()" class="cb-btn cb-bg-violet">Get clarifying questions</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not visible
      [... repeats to 15s timeout ...]
```

**Observed:** `scripts/capture_screenshots.py:run_step2` (line 283) calls
`WizardJobPage.continue_to_clarify()` — the in-flow "Continue to Clarify →"
CTA — then (line 288) calls `WizardClarifyPage.request_questions()`, which
clicks `#btnClarify` manually. `static/app.js:1254-1259`'s
`continueToClarify()` (dated "Finding #6" in its own comment) already
auto-calls `runClarify()` when reached via that CTA — and `runClarify()`
(app.js:1274-1275) immediately sets `btn.disabled = true` and hides its
row while the LLM call is in flight. So by the time the script's second,
manual click arrives, the button is already disabled/hidden by the app's
own auto-trigger — a second click was never valid on this path.

Confirming this is pre-existing (not caused by anything in this session):
`ui_pages/wizard_clarify.py` already has a *second* method,
`wait_for_questions()` (lines 19-27), whose docstring states verbatim:
*"The 'Continue to Clarify →' CTA fetches them directly (finding #6), so
the manual #btnClarify is bypassed on that path."* — i.e. the correct
fix was already known and half-implemented (the right method exists);
`capture_screenshots.py`'s `run_step2` simply never got updated to call
it. Independent evidence this predates today: `git log -1 --format=%cd
-- ui_pages/wizard_clarify.py` and the "Finding #6" comment both point to
this being an existing UI redesign the capture script never tracked —
same underlying cause (an unmaintained script drifting behind app
changes) as the welcome-modal defect, but a distinct code path and a
distinct fix.

**The fix:** in `scripts/capture_screenshots.py::run_step2`, replace the
`clarify.request_questions()` call with `clarify.wait_for_questions()` —
the method that already exists for exactly this CTA path, per
`wizard_clarify.py`'s own docstring. No changes needed to
`ui_pages/wizard_clarify.py` itself.

**Acceptance bar for this defect:** the same full-script run reaches
Step 3 (Compose) without a `#btnClarify` timeout.

---

## Acceptance bar

`python -m scripts.capture_screenshots --headless` runs past step 2
(the "New user" click) without a timeout, on a genuinely fresh
Playwright context (no `--keep-user`, no pre-existing profile) — the
exact condition that reproduced the failure. Not "CI is green" — this
script isn't in CI; the bar is a real, observed, unmodified successful
run of the actual command that failed, on the same fresh-context
precondition that caused the failure.

**Result — all three defects (welcome modal, clarify double-click,
cover-letter drawer visibility) verified together in one final,
unmodified, genuinely-fresh-context run:**

```
✓ capture complete in 148.3s
```

All 10 manifest screenshots written
(`install_setup_user-picker.png`, `walkthrough_setup_corpus-empty.png`,
`walkthrough_step1pre_jd-textarea.png`, `walkthrough_step1post_analysis-filled.png`,
`readme_hero_wizard-step1-filled.png`, `walkthrough_step2_clarify-questions.png`,
`walkthrough_step3_compose-experience-card.png`,
`walkthrough_step4_template-modern-preview.png`,
`walkthrough_step6_download-with-refine.png`,
`walkthrough_coverletter_first-generation.png`), zero modal intercepts,
zero disabled-button timeouts, zero visibility timeouts. This same run's
output serves as `refactor/css-cascade-collapse`'s (PX-51's) required
before-baseline, preserved outside the repo before the working tree's
`docs/screenshots/*.png` were reverted to their committed state (out of
scope for this branch — see the branch's own scoping note).
