```toml
schema = 1
id = 115
kind = "item"
title = "UX-8 test asserts .err-link failing-state color via getComputedStyle, not just CSS rules read"
status = "closed"
decision_owner = "agent"
branches = ["feat/run-detail-modal", "test/assertion-strength"]
refs = [
  "tests/ux/regression/test_20260924_run_detail_modal.py",
  "dashboard/templates/dashboard.html",
]
summary = "Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring."
resolution = "2026-10-10, test/assertion-strength: a new UX test resolves --danger, --info and --brand in the button's own cascade scope and asserts computed color is danger at rest and brand on hover. By measurement, removing dashboard.html:54 from the served page renders the count in rgb(96, 165, 250) (--info, F3's original defect) and removing :55 shows rgb(248, 113, 113) on hover; both fail the new test and both passed the old UX-8 test."
verified_by = [
  "tests/ux/regression/test_20260924_run_detail_modal.py::test_failing_error_count_keeps_danger_color_and_hover_affordance",
  "docs/dev/diagnosis/assertion-strength.md (A2 before, A4 after: css-no-fail-rule, css-no-fail-hover)",
]
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

### 2026-10-10 — closed on `test/assertion-strength`

Built as suggested, as a separate test so a lost cue fails under its own name. The three
tokens are resolved by a probe in the button's own `<td>`, and the test first requires them to
be distinct. Both halves were proven by mutation of the served page: each rule's removal
passed the old UX-8 test and fails the new one with the measured color
(`docs/dev/diagnosis/assertion-strength.md` A2, A4).
