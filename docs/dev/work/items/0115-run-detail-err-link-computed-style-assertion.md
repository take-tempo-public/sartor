```toml
schema = 1
id = 115
kind = "item"
title = "UX-8 test asserts .err-link failing-state color via getComputedStyle, not just CSS rules read"
status = "open"
decision_owner = "agent"
branches = ["feat/run-detail-modal"]
refs = [
  "tests/ux/regression/test_20260924_run_detail_modal.py",
  "dashboard/templates/dashboard.html",
]
summary = "Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring."
```

**Filed by the closer (F3, `feat/run-detail-modal`), per the reviewer's own rationale.**
The reviewer confirmed a CSS-cascade regression (F3): `.cb-dash button.err-link`'s explicit
`color: var(--info)` (specificity 0,3,1) outranked the inherited `.fail { color:
var(--danger) }` on the failing call kind's `<td>`, silently dropping the red "this call
kind is failing" cue. The closer fixed it with a higher-specificity `.cb-dash td.fail
button.err-link` rule plus a matching `:hover` rule (to avoid shadowing the existing hover
affordance) — see `dashboard/templates/dashboard.html`'s CSS block near `.run-link`/`.err-link`.

**What the reviewer explicitly separated from the required fix:** "Verify the result against
getComputedStyle rather than by reading the rules, per this project's own
css-cascade-per-property learning. Adding a getComputedStyle color assertion to the UX-8 test
is worth doing in the same edit but is not a blocker." The closer applied the CSS fix (it was
the blocking correctness defect) but did **not** add the test assertion — per this project's
own `css-cascade-per-property-not-per-rule` learning, the only way to actually confirm the
fix (rather than a second reading of the same rules) is a computed-style check in the live
browser, which needs a UX test, not a closer-side static read.

**Suggested shape:** in `tests/ux/regression/test_20260924_run_detail_modal.py`, after
opening the reliability detail and locating a `.err-link` button on a failing call kind,
assert `page.eval_on_selector(...)` / Playwright's computed-style read of `color` matches
`var(--danger)`'s resolved value (not `var(--info)`), and ideally a second assertion for the
`:hover` state so a future edit can't silently re-shadow it the same way.

## Updates

### 2026-09-24 — filed during `feat/run-detail-modal` close-out (Epic C C2 rerun, judge F3)
